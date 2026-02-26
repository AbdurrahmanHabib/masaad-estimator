"""Ingestion API — project intake, file upload, pipeline dispatch."""
import os
import shutil
import uuid
import logging
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import get_current_user, get_db
from app.models.orm_models import Project, Estimate, User

logger = logging.getLogger("masaad-ingestion")

router = APIRouter(prefix="/api/ingestion", tags=["Project Ingestion"])

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


def _save_upload(file: UploadFile, dest_dir: str) -> str:
    """Save an uploaded file and return its absolute path."""
    ext = os.path.splitext(file.filename or "")[-1].lower()
    filename = f"{uuid.uuid4().hex}{ext}"
    path = os.path.join(dest_dir, filename)
    os.makedirs(dest_dir, exist_ok=True)
    with open(path, "wb") as fh:
        shutil.copyfileobj(file.file, fh)
    return path


# ─── New Project (main intake endpoint) ──────────────────────────────────────

@router.post("/new-project")
async def new_project(
    request: Request,
    project_name: str = Form(...),
    client_name: str = Form(""),
    project_location: str = Form("Dubai, UAE"),
    project_country: str = Form("UAE"),
    complexity_multiplier: float = Form(1.0),
    scope_boundary: str = Form("Panels + Substructure"),
    dwg_file: Optional[UploadFile] = File(None),
    spec_file: Optional[UploadFile] = File(None),
    extra_file: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Main project intake endpoint.
    Accepts DWG + PDF spec (+ optional extra file).
    Creates Project + Estimate records, dispatches Celery pipeline.
    Returns estimate_id immediately — client polls /api/ingestion/status/{id}.
    """
    if not dwg_file and not spec_file:
        raise HTTPException(400, "At least one file (DWG or PDF spec) is required.")

    estimate_id = str(uuid.uuid4())
    project_dir = os.path.join(UPLOAD_DIR, estimate_id)
    os.makedirs(project_dir, exist_ok=True)

    # --- Save uploaded files ---
    dwg_path: Optional[str] = None
    spec_path: Optional[str] = None
    extra_path: Optional[str] = None

    if dwg_file and dwg_file.filename:
        ext = os.path.splitext(dwg_file.filename)[-1].lower()
        if ext not in (".dwg", ".dxf"):
            raise HTTPException(400, "DWG/DXF file required for drawing upload.")
        dwg_path = _save_upload(dwg_file, project_dir)
        logger.info(f"[{estimate_id}] DWG saved: {dwg_path}")

    if spec_file and spec_file.filename:
        ext = os.path.splitext(spec_file.filename)[-1].lower()
        if ext not in (".pdf", ".docx", ".doc"):
            raise HTTPException(400, "PDF or DOCX file required for spec upload.")
        spec_path = _save_upload(spec_file, project_dir)
        logger.info(f"[{estimate_id}] Spec saved: {spec_path}")

    if extra_file and extra_file.filename:
        extra_path = _save_upload(extra_file, project_dir)
        logger.info(f"[{estimate_id}] Extra file saved: {extra_path}")

    tenant_id = str(current_user.tenant_id) if current_user.tenant_id else None

    # --- Create Project ---
    project = Project(
        id=uuid.UUID(estimate_id[:32].ljust(32, "0")),  # deterministic project UUID from estimate
        tenant_id=uuid.UUID(tenant_id) if tenant_id else None,
        name=project_name,
        client_name=client_name,
        location=project_location,
        project_country=project_country,
        status="Active",
        created_by=current_user.id,
    )
    db.add(project)
    await db.flush()

    # --- Create Estimate ---
    estimate = Estimate(
        id=uuid.UUID(estimate_id),
        project_id=project.id,
        tenant_id=project.tenant_id,
        created_by=current_user.id,
        status="Queued",
        progress_pct=0,
        current_step="Queued — waiting for worker",
        reasoning_log=[],
        raw_data_json={
            "dwg_path": dwg_path,
            "spec_path": spec_path,
            "extra_path": extra_path,
            "project_name": project_name,
            "client_name": client_name,
            "project_location": project_location,
            "project_country": project_country,
            "complexity_multiplier": complexity_multiplier,
            "scope_boundary": scope_boundary,
        },
    )
    db.add(estimate)
    await db.commit()
    logger.info(f"[{estimate_id}] Project + Estimate created in DB.")

    # --- Dispatch Celery task ---
    try:
        from app.workers.tasks import run_full_pipeline
        run_full_pipeline.delay(estimate_id)
        logger.info(f"[{estimate_id}] Celery task dispatched.")
        worker_available = True
    except Exception as exc:
        logger.warning(f"[{estimate_id}] Celery not available ({exc}). Pipeline will not run automatically.")
        worker_available = False

    return {
        "estimate_id": estimate_id,
        "project_id": str(project.id),
        "status": "queued" if worker_available else "queued_no_worker",
        "message": "Processing started. Poll /api/ingestion/status/{estimate_id} for progress.",
        "files_received": {
            "dwg": os.path.basename(dwg_path) if dwg_path else None,
            "spec": os.path.basename(spec_path) if spec_path else None,
            "extra": os.path.basename(extra_path) if extra_path else None,
        },
    }


# ─── Execute pipeline for an existing estimate ───────────────────────────────

@router.post("/execute-fusion")
async def execute_fusion(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Re-run or trigger the full pipeline for an existing estimate_id."""
    estimate_id = payload.get("estimate_id")
    if not estimate_id:
        raise HTTPException(400, "estimate_id required")

    result = await db.execute(select(Estimate).where(Estimate.id == uuid.UUID(estimate_id)))
    estimate = result.scalar_one_or_none()
    if not estimate:
        raise HTTPException(404, "Estimate not found")

    # Reset status
    estimate.status = "Queued"
    estimate.progress_pct = 0
    estimate.current_step = "Re-queued"
    estimate.reasoning_log = []
    await db.commit()

    try:
        from app.workers.tasks import run_full_pipeline
        run_full_pipeline.delay(estimate_id)
        return {"estimate_id": estimate_id, "status": "queued", "message": "Pipeline re-dispatched."}
    except Exception as exc:
        logger.warning(f"Celery unavailable: {exc}")
        return {"estimate_id": estimate_id, "status": "queued_no_worker", "warning": str(exc)}


# ─── Standalone file upload (backward compat) ─────────────────────────────────

@router.post("/upload-drawings")
async def upload_drawings(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a DWG/DXF and get raw geometry extraction (no full pipeline)."""
    if not file.filename or not file.filename.lower().endswith((".dwg", ".dxf")):
        raise HTTPException(400, "Only DWG/DXF files accepted.")

    temp_id = str(uuid.uuid4())
    temp_dir = os.path.join(UPLOAD_DIR, "temp", temp_id)
    dwg_path = _save_upload(file, temp_dir)

    try:
        from app.services.dwg_parser import DWGParserService
        oda_path = os.getenv("ODA_CONVERTER_PATH", "/usr/bin/ODAFileConverter")
        svc = DWGParserService(oda_path)

        if dwg_path.endswith(".dwg"):
            dxf_path = svc.convert_dwg_to_dxf(dwg_path, temp_dir)
        else:
            dxf_path = dwg_path

        geometry = svc.extract_geometry(dxf_path)
        return {"status": "success", "file_id": temp_id, "extraction": geometry}
    except Exception as exc:
        logger.error(f"DWG parse error: {exc}")
        raise HTTPException(500, f"DWG parsing failed: {exc}")


@router.post("/upload-specs")
async def upload_specs(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a spec PDF and extract text (no full pipeline)."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files accepted.")

    temp_id = str(uuid.uuid4())
    temp_dir = os.path.join(UPLOAD_DIR, "temp", temp_id)
    pdf_path = _save_upload(file, temp_dir)

    try:
        from app.services.pdf_parser import PDFParserService
        yolo_path = os.getenv("YOLO_MODEL_PATH", "")
        svc = PDFParserService(yolo_path)
        specs = svc.extract_specs_with_llm(pdf_path)
        return {"status": "success", "file_id": temp_id, "specs": specs}
    except Exception as exc:
        logger.error(f"PDF parse error: {exc}")
        raise HTTPException(500, f"PDF parsing failed: {exc}")


# ─── Upload additional file to existing estimate ──────────────────────────────

@router.post("/upload-additional-file")
async def upload_additional_file(
    estimate_id: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add an extra file (Excel BOQ, site photo, etc.) to an existing estimate."""
    result = await db.execute(select(Estimate).where(Estimate.id == uuid.UUID(estimate_id)))
    estimate = result.scalar_one_or_none()
    if not estimate:
        raise HTTPException(404, "Estimate not found")

    dest_dir = os.path.join(UPLOAD_DIR, estimate_id)
    file_path = _save_upload(file, dest_dir)

    raw = dict(estimate.raw_data_json or {})
    extra_files = raw.get("extra_files", [])
    extra_files.append({"filename": file.filename, "path": file_path})
    raw["extra_files"] = extra_files
    estimate.raw_data_json = raw
    await db.commit()

    return {
        "status": "success",
        "estimate_id": estimate_id,
        "file_saved": os.path.basename(file_path),
        "message": "File added. Re-run pipeline to incorporate.",
    }


# ─── List estimates ───────────────────────────────────────────────────────────

@router.get("/estimates")
async def list_estimates(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all estimates for the current user's tenant."""
    from sqlalchemy import desc

    query = select(Estimate).where(
        Estimate.tenant_id == current_user.tenant_id
    ).order_by(desc(Estimate.created_at)).limit(50)
    result = await db.execute(query)
    estimates = result.scalars().all()
    return [
        {
            "estimate_id": str(e.id),
            "project_id": str(e.project_id),
            "status": e.status,
            "progress_pct": e.progress_pct,
            "current_step": e.current_step,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in estimates
    ]


@router.get("/estimate/{estimate_id}")
async def get_estimate(
    estimate_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get full estimate data for the workspace."""
    result = await db.execute(select(Estimate).where(Estimate.id == uuid.UUID(estimate_id)))
    estimate = result.scalar_one_or_none()
    if not estimate:
        raise HTTPException(404, "Estimate not found")

    return {
        "estimate_id": str(estimate.id),
        "project_id": str(estimate.project_id),
        "status": estimate.status,
        "progress_pct": estimate.progress_pct,
        "current_step": estimate.current_step,
        "reasoning_log": estimate.reasoning_log or [],
        "project_scope": estimate.project_scope_json or {},
        "opening_schedule": estimate.opening_schedule_json or {},
        "bom_output": estimate.bom_output_json or {},
        "cutting_list": estimate.cutting_list_json or {},
        "boq": estimate.boq_json or {},
        "rfi_register": estimate.rfi_register_json or [],
        "ve_opportunities": estimate.ve_opportunities_json or [],
        "structural_results": estimate.structural_results_json or [],
        "financial_summary": estimate.financial_summary_json or {},
    }

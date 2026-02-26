"""Ingestion API — project intake, file upload, pipeline dispatch."""
import os
import shutil
import uuid
import logging
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Request, BackgroundTasks
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
    contract_type: str = Form("Supply + Fabricate + Install"),
    site_conditions: str = Form(""),
    specification_notes: str = Form(""),
    known_exclusions: str = Form(""),
    estimator_notes: str = Form(""),
    budget_cap_aed: Optional[float] = Form(None),
    delivery_weeks: Optional[int] = Form(None),
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
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        name=project_name,
        client_name=client_name,
        location_zone=project_location,
        project_country=project_country,
        is_international=(project_country.upper() != "UAE"),
        contract_type=contract_type,
        scope_boundary=scope_boundary,
        complexity_multiplier=complexity_multiplier,
        created_by=current_user.id,
    )
    db.add(project)
    await db.flush()

    # --- Create Estimate ---
    estimate = Estimate(
        id=estimate_id,
        project_id=project.id,
        tenant_id=project.tenant_id,
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
            "contract_type": contract_type,
            "site_conditions": site_conditions,
            "specification_notes": specification_notes,
            "known_exclusions": known_exclusions,
            "estimator_notes": estimator_notes,
            "budget_cap_aed": budget_cap_aed,
            "delivery_weeks": delivery_weeks,
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

    result = await db.execute(select(Estimate).where(Estimate.id == estimate_id))
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


# ─── Run pipeline directly (no Celery/Redis required) ─────────────────────────

async def _run_pipeline_inline(estimate_id: str, user_id: str):
    """Run the LangGraph pipeline directly in the FastAPI process."""
    from datetime import datetime, timezone
    from app.agents.estimator_graph import estimator_graph
    from app.db import AsyncSessionLocal
    from app.models.orm_models import Estimate, FinancialRates

    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Estimate).where(Estimate.id == estimate_id)
            )
            estimate = result.scalar_one_or_none()
            if not estimate:
                logger.error(f"[{estimate_id}] Estimate not found for pipeline")
                return

            estimate.status = "ESTIMATING"
            estimate.current_step = "Pipeline starting..."
            estimate.progress_pct = 5
            await session.commit()

            # Get LME rate
            lme_rate = 7.0
            try:
                rates_result = await session.execute(
                    select(FinancialRates).where(
                        FinancialRates.tenant_id == estimate.tenant_id
                    )
                )
                rates = rates_result.scalar_one_or_none()
                if rates and rates.lme_aluminum_usd_mt and rates.usd_aed:
                    lme_rate = float(rates.lme_aluminum_usd_mt) * float(rates.usd_aed) / 1000
            except Exception:
                pass

            raw = estimate.raw_data_json or {}
            state = {
                "estimate_id": estimate_id,
                "tenant_id": estimate.tenant_id,
                "user_id": user_id,
                "current_node": "IngestionNode",
                "status": "ESTIMATING",
                "progress_pct": 5,
                "checkpoint_key": f"ckpt:{estimate_id}",
                "last_completed_node": "",
                "hitl_pending": False,
                "hitl_triage_ids": [],
                "confidence_score": 1.0,
                "drawing_paths": [raw.get("dwg_path")] if raw.get("dwg_path") else [],
                "spec_text": "",
                "revision_number": estimate.revision_number or 0,
                "extracted_openings": [],
                "catalog_matches": [],
                "bom_items": [],
                "bom_summary": None,
                "cutting_list": [],
                "pricing_data": {},
                "ve_suggestions": [],
                "lme_aed_per_kg": lme_rate,
                "project_currency": "AED",
                "is_international": raw.get("project_country", "UAE").upper() != "UAE",
                "prev_bom_snapshot": estimate.bom_snapshot_json,
                "variation_order_delta": None,
                "approval_required": True,
                "approved_by": None,
                "engineering_results": None,
                "compliance_report": None,
                "scurve_cashflow": None,
                "milestone_schedule": None,
                "yield_report": None,
                "ve_menu": None,
                "rfi_log": [],
                "error": None,
                "error_node": None,
            }

        # Run graph outside session context
        logger.info(f"[{estimate_id}] Starting inline pipeline execution")
        final_state = await estimator_graph.ainvoke(state)
        logger.info(f"[{estimate_id}] Pipeline complete, status={final_state.get('status')}")

        # Persist results
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Estimate).where(Estimate.id == estimate_id)
            )
            estimate = result.scalar_one_or_none()
            if estimate:
                estimate.status = final_state.get("status", "REVIEW_REQUIRED")
                estimate.progress_pct = final_state.get("progress_pct", 100)
                estimate.current_step = final_state.get("current_node", "Complete")
                estimate.bom_output_json = {
                    "items": final_state.get("bom_items", []),
                    "summary": final_state.get("bom_summary", {}),
                }
                estimate.project_scope_json = final_state.get("project_scope") if isinstance(final_state.get("project_scope"), dict) else {}
                estimate.opening_schedule_json = {"openings": final_state.get("extracted_openings", [])}
                estimate.cutting_list_json = {"items": final_state.get("cutting_list", [])}
                estimate.financial_json = final_state.get("pricing_data", {})
                estimate.reasoning_log = final_state.get("reasoning_log", []) if isinstance(final_state.get("reasoning_log"), list) else []
                if final_state.get("bom_items"):
                    estimate.bom_snapshot_json = {
                        "items": final_state.get("bom_items", []),
                        "revision": final_state.get("revision_number", 0),
                        "snapshot_at": datetime.now(timezone.utc).isoformat(),
                    }
                await session.commit()
                logger.info(f"[{estimate_id}] Results persisted to DB")

    except Exception as e:
        logger.error(f"[{estimate_id}] Pipeline failed: {e}", exc_info=True)
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(Estimate).where(Estimate.id == estimate_id)
                )
                estimate = result.scalar_one_or_none()
                if estimate:
                    estimate.status = "Failed"
                    estimate.current_step = f"Error: {str(e)[:200]}"
                    estimate.reasoning_log = (estimate.reasoning_log or []) + [
                        {"event": "pipeline_error", "error": str(e)}
                    ]
                    await session.commit()
        except Exception:
            pass


@router.post("/run-pipeline")
async def run_pipeline_direct(
    payload: dict,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Run the estimation pipeline directly (no Celery/Redis required).
    Executes asynchronously in a background task.
    """
    estimate_id = payload.get("estimate_id")
    if not estimate_id:
        raise HTTPException(400, "estimate_id required")

    result = await db.execute(select(Estimate).where(Estimate.id == estimate_id))
    estimate = result.scalar_one_or_none()
    if not estimate:
        raise HTTPException(404, "Estimate not found")

    estimate.status = "Queued"
    estimate.progress_pct = 0
    estimate.current_step = "Pipeline queued (direct)"
    await db.commit()

    background_tasks.add_task(_run_pipeline_inline, estimate_id, str(current_user.id))

    return {
        "estimate_id": estimate_id,
        "status": "running",
        "message": "Pipeline started directly. Poll /api/ingestion/estimate/{estimate_id} for progress.",
    }


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
        svc = DWGParserService()
        result = svc.parse_file(dwg_path)
        return {"status": "success", "file_id": temp_id, "extraction": result}
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
    result = await db.execute(select(Estimate).where(Estimate.id == estimate_id))
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


@router.get("/recent")
async def recent_estimates(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Return the last 10 estimates with joined project name, location, and status.
    Used by the dashboard to populate the recent projects table.
    Route: GET /api/ingestion/recent
    Also accessible as GET /api/v1/estimates/recent via the alias registered in main.py.
    """
    from sqlalchemy import desc

    query = (
        select(Estimate, Project)
        .join(Project, Estimate.project_id == Project.id)
        .where(Estimate.tenant_id == current_user.tenant_id)
        .order_by(desc(Estimate.created_at))
        .limit(10)
    )
    result = await db.execute(query)
    rows = result.all()

    return [
        {
            "estimate_id": str(e.id),
            "project_id": str(e.project_id),
            "project_name": p.name or "",
            "client_name": p.client_name or "",
            "location": p.location_zone or "",
            "status": e.status,
            "progress_pct": e.progress_pct,
            "current_step": e.current_step,
            "created_at": e.created_at.isoformat() if e.created_at else None,
            "updated_at": e.updated_at.isoformat() if e.updated_at else None,
            "bom_summary": (e.bom_output_json or {}).get("summary", {}),
        }
        for e, p in rows
    ]


@router.post("/approve/{estimate_id}")
async def approve_estimate_ingestion(
    estimate_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Approval endpoint on the ingestion router.
    Transitions estimate from REVIEW_REQUIRED to APPROVED.
    """
    from datetime import datetime, timezone

    result = await db.execute(select(Estimate).where(Estimate.id == estimate_id))
    estimate = result.scalar_one_or_none()
    if not estimate:
        raise HTTPException(404, "Estimate not found")
    if estimate.status not in ("REVIEW_REQUIRED", "Processing"):
        raise HTTPException(
            400,
            f"Estimate status is '{estimate.status}' -- can only approve REVIEW_REQUIRED estimates"
        )
    estimate.status = "APPROVED"
    if hasattr(estimate, 'approved_at'):
        estimate.approved_at = datetime.now(timezone.utc)
    snap = dict(estimate.state_snapshot or {})
    snap["approved_by"] = str(current_user.id)
    snap["approved_at"] = datetime.now(timezone.utc).isoformat()
    estimate.state_snapshot = snap
    await db.commit()
    return {"estimate_id": estimate_id, "status": "APPROVED", "approved_by": str(current_user.id)}


@router.get("/estimate/{estimate_id}")
async def get_estimate(
    estimate_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get full estimate data for the workspace."""
    from app.models.orm_models import Project

    result = await db.execute(select(Estimate).where(Estimate.id == estimate_id))
    estimate = result.scalar_one_or_none()
    if not estimate:
        raise HTTPException(404, "Estimate not found")

    # Join with Project to get real name and location
    project_name = ""
    project_location = ""
    proj_result = await db.execute(select(Project).where(Project.id == estimate.project_id))
    project = proj_result.scalar_one_or_none()
    if project:
        project_name = project.name or ""
        project_location = project.location_zone or ""

    bom = estimate.bom_output_json or {}
    state_snap = estimate.state_snapshot or {}

    return {
        "estimate_id": str(estimate.id),
        "project_id": str(estimate.project_id),
        "project_name": project_name,
        "location": project_location,
        "status": estimate.status,
        "progress_pct": estimate.progress_pct,
        "current_step": estimate.current_step,
        "reasoning_log": estimate.reasoning_log or [],
        "project_scope": estimate.project_scope_json or {},
        "opening_schedule": estimate.opening_schedule_json or {},
        "bom_output": bom,
        "cutting_list": estimate.cutting_list_json or {},
        # boq: synthesise from bom_output_json fields for backward compat
        "boq": {
            "summary": bom.get("summary", {}),
            "line_items": bom.get("items", []),
            "financial_rates": bom.get("financial_rates", {}),
        },
        "engineering_results": state_snap.get("engineering_results", {}),
        "rfi_register": state_snap.get("rfi_log", []),
        "ve_opportunities": state_snap.get("ve_suggestions", bom.get("ve_opportunities", [])),
        "structural_results": state_snap.get("engineering_results", {}).get("deflection_checks", bom.get("structural_results", [])),
        "financial_summary": bom.get("summary", estimate.financial_json or {}),
    }

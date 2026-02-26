"""Catalog API routes — upload, review, confirm, search."""
import io
import re
import logging
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from app.db import get_db
from app.api.deps import get_current_user, require_admin, get_tenant_id
import json
from app.models.orm_models import CatalogItem, SmartProfileDie, User
from app.services.catalog_pdf_parser import CatalogPDFParser, CatalogEntry

router = APIRouter(prefix="/api/catalog", tags=["Catalog"])
logger = logging.getLogger("masaad-catalog")

_PARSER = CatalogPDFParser()


class CatalogEntryPreview(BaseModel):
    die_number: str
    system_series: str = ""
    description: str = ""
    weight_kg_m: Optional[float] = None
    perimeter_mm: Optional[float] = None
    price_aed_per_kg: Optional[float] = None
    price_absent: bool = False
    source_page: int = 0
    extraction_method: str = "digital"
    # New universal fields
    material_type: str = "ALUMINUM_EXTRUSION"
    confidence_score: float = 1.0
    hitl_required: bool = False
    hitl_reason: str = ""
    # Glass performance
    u_value_w_m2k: Optional[float] = None
    shading_coefficient_sc: Optional[float] = None
    visible_light_transmittance_vlt: Optional[float] = None
    acoustic_rating_rw_db: Optional[int] = None
    glass_makeup: Optional[str] = None
    fire_rating_minutes: Optional[int] = None
    price_aed_sqm: Optional[float] = None
    # Hardware
    hardware_category: Optional[str] = None
    price_aed_per_unit: Optional[float] = None
    # Procurement
    supplier_name: str = ""
    lead_time_days: Optional[int] = None
    supplier_payment_terms: Optional[str] = None
    # Stage 4 DXF extraction fields (ALUMINUM_EXTRUSION only)
    dxf_path: Optional[str] = None
    anchor_origin_xy: Optional[list] = None    # [x, y] in mm
    glazing_pocket_xy: Optional[list] = None   # [x, y] in mm
    bead_snap_xy: Optional[list] = None        # [x, y] in mm
    scale_factor: Optional[float] = None       # mm per PDF point
    die_status: str = "RAW"                    # RAW | VERIFIED | DRAFT_REQUIRES_VERIFICATION


class CatalogConfirmRequest(BaseModel):
    supplier_name: str = "Gulf Extrusions"
    entries: List[CatalogEntryPreview]
    price_date: Optional[str] = None  # ISO date string


def _make_item_code(die_number: str, supplier_name: str = "") -> str:
    """Generate a stable item_code from die_number and supplier prefix."""
    prefix = (supplier_name[:3].upper() if supplier_name else "CAT")
    safe_die = re.sub(r'[^A-Za-z0-9\-]', '', die_number)
    return f"{prefix}-{safe_die}"


@router.post("/upload-preview")
async def upload_catalog_preview(
    file: UploadFile = File(...),
    supplier_name: str = "Gulf Extrusions",
    user: User = Depends(require_admin),
):
    """Extract catalog entries from PDF — returns preview WITHOUT saving."""
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files accepted")

    try:
        contents = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read uploaded file: {e}")

    if len(contents) > 50 * 1024 * 1024:  # 50 MB limit
        raise HTTPException(status_code=400, detail="File too large (max 50MB)")

    if len(contents) < 100:
        raise HTTPException(status_code=400, detail="File appears empty or corrupted (too small)")

    # Verify it's actually a PDF (check magic bytes %PDF)
    if not contents[:10].startswith(b'%PDF'):
        raise HTTPException(
            status_code=400,
            detail="File does not appear to be a valid PDF (missing %PDF header)"
        )

    try:
        entries = await _PARSER.parse(contents, source_name=file.filename)
    except Exception as e:
        logger.error(f"PDF parsing failed for {file.filename}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"PDF parsing failed: {e}")

    if not entries:
        raise HTTPException(
            status_code=422,
            detail="No catalog entries could be extracted from this PDF. "
                   "The file may be scanned/image-only or contain no recognizable catalog data."
        )

    previews = [
        CatalogEntryPreview(
            die_number=e.item_code,
            system_series=e.system_series,
            description=e.description,
            weight_kg_m=e.weight_kg_m,
            perimeter_mm=e.perimeter_mm,
            price_aed_per_kg=e.price_aed_per_kg,
            price_absent=e.price_absent,
            source_page=e.source_page,
            extraction_method=e.extraction_method,
            material_type=e.material_type,
            confidence_score=e.confidence_score,
            hitl_required=e.hitl_required,
            hitl_reason=e.hitl_reason,
            u_value_w_m2k=e.u_value_w_m2k,
            shading_coefficient_sc=e.shading_coefficient_sc,
            visible_light_transmittance_vlt=e.visible_light_transmittance_vlt,
            acoustic_rating_rw_db=e.acoustic_rating_rw_db,
            glass_makeup=e.glass_makeup,
            fire_rating_minutes=e.fire_rating_minutes,
            price_aed_sqm=e.price_aed_sqm,
            hardware_category=e.hardware_category,
            price_aed_per_unit=e.price_aed_per_unit,
            supplier_name=e.supplier_name,
            lead_time_days=e.lead_time_days,
            # Stage 4 DXF fields
            dxf_path=e.dxf_path,
            anchor_origin_xy=list(e.anchor_origin_xy) if e.anchor_origin_xy else None,
            glazing_pocket_xy=list(e.glazing_pocket_xy) if e.glazing_pocket_xy else None,
            bead_snap_xy=list(e.bead_snap_xy) if e.bead_snap_xy else None,
            scale_factor=e.scale_factor,
            die_status=e.die_status,
        )
        for e in entries
    ]

    return {
        "filename": file.filename,
        "supplier_name": supplier_name,
        "total_extracted": len(previews),
        "digital_extracted": sum(1 for e in previews if e.extraction_method == "digital"),
        "vision_extracted": sum(1 for e in previews if e.extraction_method == "vision"),
        "with_price": sum(1 for e in previews if not e.price_absent),
        "without_price": sum(1 for e in previews if e.price_absent),
        "entries": previews,
    }


@router.post("/confirm")
async def confirm_catalog(
    req: CatalogConfirmRequest,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Bulk UPSERT confirmed catalog entries into the database."""
    tenant_id = str(user.tenant_id)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="User has no tenant")

    saved = 0
    updated = 0

    for entry in req.entries:
        # Find existing by die_number + tenant
        result = await db.execute(
            select(CatalogItem).where(
                CatalogItem.tenant_id == tenant_id,
                CatalogItem.die_number == entry.die_number,
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.system_series = entry.system_series or existing.system_series
            existing.description = entry.description or existing.description
            existing.material_type = entry.material_type
            # ORM column is weight_per_meter (not weight_kg_m)
            if entry.weight_kg_m is not None:
                existing.weight_per_meter = entry.weight_kg_m
            if entry.perimeter_mm is not None:
                existing.perimeter_mm = entry.perimeter_mm
            if entry.price_aed_per_kg is not None:
                existing.price_aed_per_kg = entry.price_aed_per_kg
                existing.price_absent = False
                existing.price_source = "catalog_pdf"
                if req.price_date:
                    existing.price_notes = f"{req.supplier_name} pricelist {req.price_date}"
            # Glass performance fields
            if entry.u_value_w_m2k is not None:
                existing.u_value_w_m2k = entry.u_value_w_m2k
            if entry.shading_coefficient_sc is not None:
                existing.shading_coefficient_sc = entry.shading_coefficient_sc
            if entry.visible_light_transmittance_vlt is not None:
                existing.visible_light_transmittance_vlt = entry.visible_light_transmittance_vlt
            if entry.acoustic_rating_rw_db is not None:
                existing.acoustic_rating_rw_db = entry.acoustic_rating_rw_db
            if entry.glass_makeup:
                existing.glass_makeup = entry.glass_makeup
            if entry.fire_rating_minutes is not None:
                existing.fire_rating_minutes = entry.fire_rating_minutes
            # Procurement
            if entry.supplier_name:
                existing.supplier_name = entry.supplier_name
            if entry.lead_time_days is not None:
                existing.lead_time_days = entry.lead_time_days
            if entry.supplier_payment_terms:
                existing.supplier_payment_terms = entry.supplier_payment_terms
            updated += 1
        else:
            # item_code is NOT NULL — derive it from die_number + supplier prefix
            item_code = _make_item_code(entry.die_number, req.supplier_name)
            item = CatalogItem(
                tenant_id=tenant_id,
                item_code=item_code,
                die_number=entry.die_number,
                system_series=entry.system_series,
                description=entry.description,
                material_type=entry.material_type,
                # ORM column is weight_per_meter
                weight_per_meter=entry.weight_kg_m,
                perimeter_mm=entry.perimeter_mm,
                price_aed_per_kg=entry.price_aed_per_kg,
                price_absent=entry.price_absent,
                price_source="catalog_pdf" if entry.price_aed_per_kg else None,
                price_notes=(
                    f"{req.supplier_name} pricelist {req.price_date}"
                    if req.price_date else None
                ),
                extraction_method=entry.extraction_method,
                source_page=entry.source_page,
                source_file=req.supplier_name,
                # Glass fields
                u_value_w_m2k=entry.u_value_w_m2k,
                shading_coefficient_sc=entry.shading_coefficient_sc,
                visible_light_transmittance_vlt=entry.visible_light_transmittance_vlt,
                acoustic_rating_rw_db=entry.acoustic_rating_rw_db,
                glass_makeup=entry.glass_makeup,
                fire_rating_minutes=entry.fire_rating_minutes,
                # Procurement
                supplier_name=entry.supplier_name or req.supplier_name or None,
                lead_time_days=entry.lead_time_days,
                supplier_payment_terms=entry.supplier_payment_terms,
            )
            db.add(item)
            saved += 1

    await db.commit()

    # Upsert SmartProfileDie records for aluminum entries that have DXF geometry
    dies_saved = 0
    dies_updated = 0
    for entry in req.entries:
        if entry.material_type != "ALUMINUM_EXTRUSION" or not entry.dxf_path:
            continue

        item_code = _make_item_code(entry.die_number, req.supplier_name)
        die_result = await db.execute(
            select(SmartProfileDie).where(
                SmartProfileDie.tenant_id == tenant_id,
                SmartProfileDie.item_code == item_code,
            )
        )
        existing_die = die_result.scalar_one_or_none()

        anchor_json = json.dumps(list(entry.anchor_origin_xy)) if entry.anchor_origin_xy else None
        glazing_json = json.dumps(list(entry.glazing_pocket_xy)) if entry.glazing_pocket_xy else None
        bead_json = json.dumps(list(entry.bead_snap_xy)) if entry.bead_snap_xy else None

        if existing_die:
            existing_die.dxf_path = entry.dxf_path
            if anchor_json:
                existing_die.anchor_origin_xy = anchor_json
            if glazing_json:
                existing_die.glazing_pocket_xy = glazing_json
            if bead_json:
                existing_die.bead_snap_xy = bead_json
            dies_updated += 1
        else:
            die = SmartProfileDie(
                tenant_id=tenant_id,
                item_code=item_code,
                die_number=entry.die_number,
                system_series=entry.system_series or "",
                description=entry.description or "",
                dxf_path=entry.dxf_path,
                anchor_origin_xy=anchor_json,
                glazing_pocket_xy=glazing_json,
                bead_snap_xy=bead_json,
            )
            db.add(die)
            dies_saved += 1

    if dies_saved or dies_updated:
        await db.commit()

    return {
        "status": "saved",
        "new_entries": saved,
        "updated_entries": updated,
        "total": saved + updated,
        "dies_registered": dies_saved,
        "dies_updated": dies_updated,
    }


@router.get("/search")
async def search_catalog(
    q: str = Query("", description="Search query"),
    system_series: str = Query("", description="Filter by system series"),
    die_number: str = Query("", description="Exact die number lookup"),
    limit: int = Query(50, le=500),
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Search catalog items for the current tenant."""
    query = select(CatalogItem).where(CatalogItem.tenant_id == tenant_id)

    if die_number:
        query = query.where(CatalogItem.die_number == die_number)
    elif system_series:
        query = query.where(CatalogItem.system_series.ilike(f"%{system_series}%"))
    elif q:
        query = query.where(or_(
            CatalogItem.die_number.ilike(f"%{q}%"),
            CatalogItem.description.ilike(f"%{q}%"),
            CatalogItem.system_series.ilike(f"%{q}%"),
        ))

    query = query.limit(limit)
    result = await db.execute(query)
    items = result.scalars().all()

    return {
        "total": len(items),
        "items": [
            {
                "id": str(item.id),
                "die_number": item.die_number,
                "system_series": item.system_series,
                "description": item.description,
                # Expose as weight_kg_m for API consistency; ORM field is weight_per_meter
                "weight_kg_m": float(item.weight_per_meter) if item.weight_per_meter else None,
                "perimeter_mm": float(item.perimeter_mm) if item.perimeter_mm else None,
                "price_aed_per_kg": (
                    float(item.price_aed_per_kg) if item.price_aed_per_kg else None
                ),
                "price_absent": item.price_aed_per_kg is None,
                "price_source": item.price_source,
                "price_notes": item.price_notes,
            }
            for item in items
        ],
    }


@router.get("/list")
async def list_catalog(
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """List all catalog items for the current tenant."""
    result = await db.execute(
        select(CatalogItem)
        .where(CatalogItem.tenant_id == tenant_id)
        .order_by(CatalogItem.system_series, CatalogItem.die_number)
    )
    items = result.scalars().all()
    return {
        "total": len(items),
        "items": [
            {
                "id": str(item.id),
                "die_number": item.die_number,
                "system_series": item.system_series,
                "description": item.description,
                "weight_kg_m": float(item.weight_per_meter) if item.weight_per_meter else None,
                "perimeter_mm": float(item.perimeter_mm) if item.perimeter_mm else None,
                "price_aed_per_kg": (
                    float(item.price_aed_per_kg) if item.price_aed_per_kg else None
                ),
                "price_absent": item.price_aed_per_kg is None,
            }
            for item in items
        ],
    }

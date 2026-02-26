"""
DraftingNode API routes.
The LLM submits a DraftingRecipe JSON; this endpoint runs the DXF compiler
and returns the compiled section detail as a downloadable .dxf file.
"""
import json
import os
import tempfile
import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db import get_db
from app.api.deps import require_role, get_tenant_id
from app.models.orm_models import SmartProfileDie as SmartProfileDieORM, User
from app.services.drafting.smart_die import (
    DraftingRecipe, SmartProfileDie as SmartProfileDiePydantic
)
from app.services.drafting.dxf_compiler import assemble_section_detail, GeometryCollisionError

router = APIRouter(prefix="/api/v1/drafting", tags=["Drafting Engine"])
logger = logging.getLogger("masaad-drafting-routes")


def _orm_to_pydantic(row: SmartProfileDieORM) -> SmartProfileDiePydantic | None:
    """Convert ORM row to Pydantic SmartProfileDie for the compiler."""
    try:
        anchor = json.loads(row.anchor_origin_xy) if row.anchor_origin_xy else [0, 0]
        glazing = json.loads(row.glazing_pocket_xy) if row.glazing_pocket_xy else [0, 0]
        bead = json.loads(row.bead_snap_xy) if row.bead_snap_xy else [0, 0]
        bbox = json.loads(row.bounding_box_polygon) if row.bounding_box_polygon else []
        return SmartProfileDiePydantic(
            item_code=row.item_code,
            die_number=row.die_number,
            dxf_path=row.dxf_path or "",
            anchor_origin_xy=tuple(anchor),
            glazing_pocket_xy=tuple(glazing),
            bead_snap_xy=tuple(bead),
            max_glass_thickness=float(row.max_glass_thickness or 28.0),
            bounding_box_polygon=[tuple(pt) for pt in bbox],
            description=row.description or "",
            system_series=row.system_series or "",
        )
    except Exception as e:
        logger.warning(f"Failed to parse SmartProfileDie ORM row {row.item_code}: {e}")
        return None


@router.post("/compile-section")
async def compile_section(
    recipe: DraftingRecipe,
    user: User = Depends(require_role("Senior_Estimator")),
    db: AsyncSession = Depends(get_db),
):
    """
    Compile a DXF section detail from a DraftingRecipe.

    The LLM calls this endpoint with a DraftingRecipe JSON.
    Returns: DXF file download on success.
    Returns: 409 Conflict with GeometryCollisionError details on collision.
    """
    tenant_id = str(user.tenant_id)
    required_codes = list({p.item_code for p in recipe.profiles})

    result = await db.execute(
        select(SmartProfileDieORM).where(
            SmartProfileDieORM.tenant_id == tenant_id,
            SmartProfileDieORM.item_code.in_(required_codes),
        )
    )
    rows = result.scalars().all()

    die_registry = {}
    for row in rows:
        pydantic = _orm_to_pydantic(row)
        if pydantic:
            die_registry[pydantic.item_code] = pydantic

    missing = [c for c in required_codes if c not in die_registry]
    if missing:
        raise HTTPException(
            status_code=404,
            detail=f"SmartProfileDie not found for item codes: {missing}",
        )

    output_file = tempfile.NamedTemporaryFile(
        suffix=".dxf",
        prefix=f"section_{recipe.estimate_id}_",
        delete=False,
    )
    output_file.close()

    try:
        path = assemble_section_detail(recipe, die_registry, output_file.name)
    except GeometryCollisionError as e:
        os.unlink(output_file.name)
        raise HTTPException(
            status_code=409,
            detail={
                "error": "GEOMETRY_COLLISION",
                "message": str(e),
                "colliding_profiles": e.colliding_profiles,
                "overlap_area_mm2": e.overlap_area,
                "hint": "Retry with reduced glass_thickness_mm or choose a bead with a deeper pocket",
            },
        )
    except ValueError as e:
        os.unlink(output_file.name)
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        os.unlink(output_file.name)
        logger.error(f"DXF compilation failed: {e}")
        raise HTTPException(status_code=500, detail=f"DXF compilation failed: {e}")

    filename = f"{recipe.section_name.replace(' ', '_')}.dxf"
    return FileResponse(
        path=path,
        media_type="application/octet-stream",
        filename=filename,
        background=None,  # File cleanup handled after response
    )


@router.get("/dies")
async def list_dies(
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """List all registered Smart Profile Dies for this tenant."""
    result = await db.execute(
        select(SmartProfileDieORM)
        .where(SmartProfileDieORM.tenant_id == tenant_id)
        .order_by(SmartProfileDieORM.system_series, SmartProfileDieORM.die_number)
    )
    rows = result.scalars().all()
    return {
        "total": len(rows),
        "dies": [
            {
                "id": row.id,
                "item_code": row.item_code,
                "die_number": row.die_number,
                "system_series": row.system_series,
                "description": row.description,
                "max_glass_thickness": float(row.max_glass_thickness) if row.max_glass_thickness else None,
                "has_dxf": bool(row.dxf_path),
                "has_constraints": bool(row.anchor_origin_xy and row.bounding_box_polygon),
            }
            for row in rows
        ],
    }

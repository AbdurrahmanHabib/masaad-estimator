"""
HITL Triage Queue routes.
Exposes pending low-confidence items to human reviewers and accepts resolutions
that resume the suspended LangGraph pipeline.
"""
import json
import logging
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db import get_db
from app.api.deps import get_current_user, get_tenant_id, require_role
from app.models.orm_models import TriageItem, User

router = APIRouter(prefix="/api/v1/triage", tags=["HITL Triage"])
logger = logging.getLogger("masaad-triage")


class TriageResolutionRequest(BaseModel):
    resolution: dict                       # Corrected field values from human reviewer
    action: str = "resolve"               # "resolve" | "skip"


@router.get("/pending")
async def list_pending(
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """List all pending HITL triage items for the current tenant."""
    result = await db.execute(
        select(TriageItem)
        .where(TriageItem.tenant_id == tenant_id, TriageItem.status == "pending")
        .order_by(TriageItem.created_at)
    )
    items = result.scalars().all()
    return {
        "total": len(items),
        "items": [
            {
                "id": item.id,
                "estimate_id": item.estimate_id,
                "node_name": item.node_name,
                "confidence_score": float(item.confidence_score),
                "context": json.loads(item.context_json) if item.context_json else {},
                "created_at": item.created_at.isoformat() if item.created_at else None,
            }
            for item in items
        ],
    }


@router.post("/resolve/{triage_id}")
async def resolve_triage(
    triage_id: str,
    req: TriageResolutionRequest,
    user: User = Depends(require_role("Senior_Estimator")),
    db: AsyncSession = Depends(get_db),
):
    """
    Resolve a pending triage item.

    The human reviewer provides corrected field values in `resolution`.
    This marks the item resolved so the graph can resume from its checkpoint.
    The Celery task polling on `hitl_pending` will detect this and continue.
    """
    result = await db.execute(select(TriageItem).where(TriageItem.id == triage_id))
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=404, detail="Triage item not found")
    if item.tenant_id != str(user.tenant_id):
        raise HTTPException(status_code=403, detail="Access denied")
    if item.status != "pending":
        raise HTTPException(status_code=400, detail=f"Item already {item.status}")

    item.status = req.action if req.action in ("resolved", "skipped") else "resolved"
    item.resolution_json = json.dumps(req.resolution)
    item.resolved_at = datetime.now(timezone.utc)
    item.resolved_by = str(user.id)

    await db.commit()
    logger.info(
        f"Triage item {triage_id} {item.status} by user {user.id} "
        f"for estimate {item.estimate_id}"
    )

    return {
        "id": triage_id,
        "status": item.status,
        "estimate_id": item.estimate_id,
        "resolved_at": item.resolved_at.isoformat(),
    }


@router.get("/item/{triage_id}")
async def get_triage_item(
    triage_id: str,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Fetch a single triage item with full context (for review UI)."""
    result = await db.execute(select(TriageItem).where(TriageItem.id == triage_id))
    item = result.scalar_one_or_none()
    if not item or item.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Triage item not found")

    return {
        "id": item.id,
        "estimate_id": item.estimate_id,
        "node_name": item.node_name,
        "confidence_score": float(item.confidence_score),
        "status": item.status,
        "context": json.loads(item.context_json) if item.context_json else {},
        "resolution": json.loads(item.resolution_json) if item.resolution_json else None,
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "resolved_at": item.resolved_at.isoformat() if item.resolved_at else None,
    }

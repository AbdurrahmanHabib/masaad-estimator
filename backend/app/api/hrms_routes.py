"""
HRMS Integration routes.
Allows the Flask HRMS system to push the calculated fully-burdened labor rate
into the Masaad Estimator database via a secured webhook endpoint.
"""
import logging
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db import get_db
from app.api.deps import require_admin, get_tenant_id
from app.models.orm_models import FinancialRates, User

router = APIRouter(prefix="/api/v1/hrms", tags=["HRMS Integration"])
logger = logging.getLogger("masaad-hrms")


class BurnRateUpdateRequest(BaseModel):
    rate_aed: float = Field(..., gt=0, description="Fully burdened hourly rate in AED")
    effective_month: Optional[str] = None    # ISO month string, e.g. "2026-01"
    source: str = Field("hrms_push", description="Source identifier")


class BurnRateUpdateResponse(BaseModel):
    updated_rate: float
    previous_rate: Optional[float]
    timestamp: str
    effective_month: Optional[str]


@router.post("/update-burn-rate", response_model=BurnRateUpdateResponse)
async def update_burn_rate(
    req: BurnRateUpdateRequest,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Upsert the fully burdened labor burn rate for this tenant.

    Called by the Flask HRMS after calculating:
        burn_rate = total_factory_payroll_aed / (factory_worker_count × 6 days × 8 hrs × 4.33 weeks)

    HRMS does the arithmetic; this endpoint just stores the result.
    Returns the previous rate so HRMS can log the delta on its side.
    """
    tenant_id = str(user.tenant_id)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="User has no tenant")

    result = await db.execute(
        select(FinancialRates).where(FinancialRates.tenant_id == tenant_id)
    )
    rates = result.scalar_one_or_none()

    previous_rate = None
    now = datetime.now(timezone.utc)

    if rates:
        previous_rate = float(rates.baseline_labor_burn_rate_aed) if rates.baseline_labor_burn_rate_aed else None
        rates.baseline_labor_burn_rate_aed = req.rate_aed
        rates.burn_rate_last_updated = now
        rates.burn_rate_updated_by_source = req.source
    else:
        rates = FinancialRates(
            tenant_id=tenant_id,
            baseline_labor_burn_rate_aed=req.rate_aed,
            burn_rate_last_updated=now,
            burn_rate_updated_by_source=req.source,
        )
        db.add(rates)

    await db.commit()
    logger.info(
        f"Burn rate updated for tenant {tenant_id}: "
        f"{previous_rate} → {req.rate_aed} AED/hr (source: {req.source})"
    )

    return BurnRateUpdateResponse(
        updated_rate=req.rate_aed,
        previous_rate=previous_rate,
        timestamp=now.isoformat(),
        effective_month=req.effective_month,
    )

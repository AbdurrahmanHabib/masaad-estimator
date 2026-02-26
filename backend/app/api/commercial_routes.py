"""
Phase 6B — Commercial Director API Routes

C4:  POST /api/commercial/level-quotes     — supplier quote leveling matrix
C5:  GET  /api/commercial/{id}/cashflow    — S-curve cash flow for an estimate
C6:  POST /api/commercial/redline-contract — automated contract redlining
C7:  GET  /api/commercial/{id}/milestones  — milestone payment schedule
C8:  GET  /api/commercial/{id}/yield       — yield & scrap optimization report
C9:  POST /api/commercial/{id}/pe-stamp    — submit to PE stamping webhook
C10: GET  /api/commercial/{id}/rfi-log     — tender clarification log
     POST /api/commercial/{id}/rfi-log     — add manual RFI entry
     PUT  /api/commercial/{id}/rfi/{rfi_id}/respond — mark RFI as responded
C11: GET  /api/commercial/{id}/ve-menu     — dynamic VE menu
     PUT  /api/commercial/{id}/ve/{ve_id}  — accept/reject VE item
"""
import logging
from typing import Optional, List
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db import get_db
from app.api.deps import get_current_user, require_admin, get_tenant_id
from app.models.orm_models import User, Estimate

router = APIRouter(prefix="/api/commercial", tags=["Commercial Director"])
logger = logging.getLogger("masaad-commercial-routes")


# ── Pydantic Models ─────────────────────────────────────────────────────────

class SupplierQuote(BaseModel):
    supplier_name: str
    total_price_aed: float
    weight_kg: float
    delivery_weeks: int = 8
    payment_terms: str = ""
    currency: str = "AED"
    forex_rate: float = 1.0


class QuoteLevelingRequest(BaseModel):
    quotes: List[SupplierQuote]


class ContractRedlineRequest(BaseModel):
    contract_text: str


class RFIAddRequest(BaseModel):
    rfi_text: str
    reference: str = ""
    source: str = "manual"


class RFIRespondRequest(BaseModel):
    response_text: str


class VEDecisionRequest(BaseModel):
    decision: str           # "ACCEPTED" | "REJECTED"
    decided_by: str = ""
    rejection_reason: str = ""


class PEStampRequest(BaseModel):
    pe_webhook_url: str


# ── Helper: load estimate state ──────────────────────────────────────────────

async def _get_estimate_state(estimate_id: str, tenant_id: str, db: AsyncSession) -> dict:
    result = await db.execute(
        select(Estimate).where(
            Estimate.id == estimate_id,
            Estimate.tenant_id == tenant_id,
        )
    )
    est = result.scalar_one_or_none()
    if not est:
        raise HTTPException(status_code=404, detail=f"Estimate {estimate_id} not found")
    return est.state_snapshot or {}


async def _save_estimate_state(
    estimate_id: str, tenant_id: str, db: AsyncSession, updates: dict
) -> None:
    result = await db.execute(
        select(Estimate).where(
            Estimate.id == estimate_id,
            Estimate.tenant_id == tenant_id,
        )
    )
    est = result.scalar_one_or_none()
    if est:
        snap = dict(est.state_snapshot or {})
        snap.update(updates)
        est.state_snapshot = snap
        await db.commit()


# ── C4: Supplier Quote Leveling ──────────────────────────────────────────────

@router.post("/level-quotes")
async def level_supplier_quotes(
    req: QuoteLevelingRequest,
    user: User = Depends(get_current_user),
):
    """C4: Normalize ≥2 supplier quotes to per-kg rate for side-by-side comparison."""
    from app.services.commercial_director import level_supplier_quotes as _level

    if len(req.quotes) < 2:
        raise HTTPException(status_code=400, detail="At least 2 supplier quotes required")

    quotes_dicts = [q.dict() for q in req.quotes]
    result = _level(quotes_dicts)
    return result


# ── C5: S-Curve Cash Flow ────────────────────────────────────────────────────

@router.get("/{estimate_id}/cashflow")
async def get_cashflow(
    estimate_id: str,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """C5: Retrieve S-curve cash flow schedule for an estimate."""
    state = await _get_estimate_state(estimate_id, tenant_id, db)
    scurve = state.get("scurve_cashflow")
    if not scurve:
        raise HTTPException(status_code=404, detail="Cash flow not yet generated — run estimate first")
    return scurve


# ── C6: Contract Redlining ───────────────────────────────────────────────────

@router.post("/redline-contract")
async def redline_contract(
    req: ContractRedlineRequest,
    user: User = Depends(get_current_user),
):
    """C6: Automated contract redlining via Groq — flags hostile/non-standard clauses."""
    from app.services.commercial_director import redline_contract as _redline

    if len(req.contract_text) < 100:
        raise HTTPException(status_code=400, detail="Contract text too short (min 100 chars)")

    result = await _redline(req.contract_text)
    return result


# ── C7: Milestone Payment Schedule ──────────────────────────────────────────

@router.get("/{estimate_id}/milestones")
async def get_milestones(
    estimate_id: str,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """C7: Retrieve milestone payment schedule for an estimate."""
    state = await _get_estimate_state(estimate_id, tenant_id, db)
    sched = state.get("milestone_schedule")
    if not sched:
        raise HTTPException(status_code=404, detail="Milestone schedule not yet generated")
    return sched


# ── C8: Yield & Scrap ────────────────────────────────────────────────────────

@router.get("/{estimate_id}/yield")
async def get_yield_report(
    estimate_id: str,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """C8: Retrieve yield & scrap optimization report."""
    state = await _get_estimate_state(estimate_id, tenant_id, db)
    report = state.get("yield_report")
    if not report:
        raise HTTPException(status_code=404, detail="Yield report not yet generated")
    return report


# ── C9: PE Stamping ──────────────────────────────────────────────────────────

@router.post("/{estimate_id}/pe-stamp")
async def submit_pe_stamp(
    estimate_id: str,
    req: PEStampRequest,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    """C9: POST structural report PDF to PE webhook for stamping."""
    from app.services.commercial_director import submit_for_pe_stamp

    state = await _get_estimate_state(estimate_id, tenant_id, db)
    report_paths = state.get("pricing_data", {}).get("report_paths", [])

    # Find the structural report PDF
    structural_report = next(
        (p for p in report_paths if "structural" in str(p).lower() or "quote" in str(p).lower()),
        report_paths[0] if report_paths else None,
    )

    if not structural_report:
        raise HTTPException(status_code=404, detail="No report found — generate estimate report first")

    result = await submit_for_pe_stamp(
        estimate_id=estimate_id,
        report_path=structural_report,
        pe_webhook_url=req.pe_webhook_url,
        tenant_id=tenant_id,
    )

    # Persist stamp status to state
    await _save_estimate_state(estimate_id, tenant_id, db, {
        "pe_stamp_status": result,
        "pe_stamp_submitted_at": datetime.now(timezone.utc).isoformat(),
    })

    return result


# ── C10: RFI / Tender Clarification Log ──────────────────────────────────────

@router.get("/{estimate_id}/rfi-log")
async def get_rfi_log(
    estimate_id: str,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """C10: Retrieve tender clarification (RFI) log with overdue alerts."""
    from app.services.commercial_director import audit_rfi_log

    state = await _get_estimate_state(estimate_id, tenant_id, db)
    rfi_log = list(state.get("rfi_log") or [])
    audit = audit_rfi_log(rfi_log)

    return {
        "estimate_id": estimate_id,
        "rfi_log": rfi_log,
        "audit": audit,
    }


@router.post("/{estimate_id}/rfi-log")
async def add_rfi_entry(
    estimate_id: str,
    req: RFIAddRequest,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """C10: Add a manual RFI entry to the tender clarification log."""
    from app.services.commercial_director import create_rfi_log_entry

    state = await _get_estimate_state(estimate_id, tenant_id, db)
    rfi_log = list(state.get("rfi_log") or [])

    new_rfi = create_rfi_log_entry(
        rfi_text=req.rfi_text,
        source=req.source,
        estimate_id=estimate_id,
        reference=req.reference,
    )
    rfi_log.append(new_rfi)

    await _save_estimate_state(estimate_id, tenant_id, db, {"rfi_log": rfi_log})
    return new_rfi


@router.put("/{estimate_id}/rfi/{rfi_id}/respond")
async def respond_to_rfi(
    estimate_id: str,
    rfi_id: str,
    req: RFIRespondRequest,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """C10: Mark an RFI as responded."""
    state = await _get_estimate_state(estimate_id, tenant_id, db)
    rfi_log = list(state.get("rfi_log") or [])

    updated = False
    for rfi in rfi_log:
        if rfi.get("rfi_id") == rfi_id:
            rfi["status"] = "RESPONDED"
            rfi["response_text"] = req.response_text
            rfi["responded_at"] = datetime.now(timezone.utc).isoformat()
            updated = True
            break

    if not updated:
        raise HTTPException(status_code=404, detail=f"RFI {rfi_id} not found")

    await _save_estimate_state(estimate_id, tenant_id, db, {"rfi_log": rfi_log})
    return {"status": "responded", "rfi_id": rfi_id}


# ── C11: Dynamic VE Menu ──────────────────────────────────────────────────────

@router.get("/{estimate_id}/ve-menu")
async def get_ve_menu(
    estimate_id: str,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """C11: Get the dynamic VE menu with running savings total."""
    state = await _get_estimate_state(estimate_id, tenant_id, db)
    ve_menu = state.get("ve_menu")
    if not ve_menu:
        raise HTTPException(status_code=404, detail="VE menu not yet generated")
    return ve_menu


@router.put("/{estimate_id}/ve/{ve_id}")
async def decide_ve_item(
    estimate_id: str,
    ve_id: str,
    req: VEDecisionRequest,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """C11: Accept or reject a VE menu item. Recalculates running savings."""
    from app.services.commercial_director import apply_ve_decision

    if req.decision not in ("ACCEPTED", "REJECTED"):
        raise HTTPException(status_code=400, detail="decision must be 'ACCEPTED' or 'REJECTED'")

    state = await _get_estimate_state(estimate_id, tenant_id, db)
    ve_menu = state.get("ve_menu")
    if not ve_menu:
        raise HTTPException(status_code=404, detail="VE menu not found")

    updated_menu = apply_ve_decision(
        ve_menu=ve_menu,
        ve_id=ve_id,
        decision=req.decision,
        decided_by=req.decided_by or str(user.id),
        rejection_reason=req.rejection_reason,
    )

    await _save_estimate_state(estimate_id, tenant_id, db, {"ve_menu": updated_menu})
    return {
        "ve_id": ve_id,
        "decision": req.decision,
        "accepted_savings_aed": updated_menu["accepted_savings_aed"],
        "total_potential_savings_aed": updated_menu["total_potential_savings_aed"],
    }


# ── Compliance Report ─────────────────────────────────────────────────────────

@router.get("/{estimate_id}/compliance")
async def get_compliance_report(
    estimate_id: str,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Phase 3B: Retrieve compliance report (C1 structural, C2 thermal/acoustic, C3 fire)."""
    state = await _get_estimate_state(estimate_id, tenant_id, db)
    report = state.get("compliance_report")
    if not report:
        raise HTTPException(status_code=404, detail="Compliance report not yet generated")
    return report

"""
Phase 6B — Commercial Director Engine

C4: Supplier Quote Leveling Matrix (≥2 suppliers → normalized cost comparison)
C5: Project Cash Flow S-Curve (30/60/10 split, week-by-week 12-month lock)
C6: Automated Contract Redlining (Groq reads draft → flags deviations → annotated)
C7: Milestone Payment Schedule (LOA→SD Approval→Procurement→Fabrication→Delivery→Install→Handover)
C8: Yield & Scrap Optimization (CSP offcut register, LME recycle revenue, yield%)
C9: Third-Party Stamping API (POST structural report to PE webhook, track stamp status)
C10: Tender Clarification Log (persistent RFI log, auto-flag unresponded items)
C11: Dynamic VE Menu (per-item accept/reject with running savings total)

All functions return plain dicts suitable for GraphState / API response.
"""
from __future__ import annotations
import math
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

logger = logging.getLogger("masaad-commercial")


# ── C4: Supplier Quote Leveling ───────────────────────────────────────────────

def level_supplier_quotes(supplier_quotes: list[dict]) -> dict:
    """
    C4: Normalize ≥2 supplier quotes to a per-kg rate for side-by-side comparison.

    Each quote dict: {
        "supplier_name": str,
        "total_price_aed": float,
        "weight_kg": float,
        "delivery_weeks": int,
        "payment_terms": str,
        "currency": str (default "AED"),
        "forex_rate": float (default 1.0 for AED)
    }

    Returns leveling matrix with winner and savings potential.
    """
    if len(supplier_quotes) < 2:
        return {"error": "Need ≥2 supplier quotes to level", "matrix": []}

    leveled = []
    for q in supplier_quotes:
        total = float(q.get("total_price_aed", 0) or 0)
        weight = float(q.get("weight_kg", 1) or 1)
        forex = float(q.get("forex_rate", 1.0) or 1.0)

        # Normalize to AED
        total_aed = total * forex
        rate_per_kg = total_aed / weight if weight > 0 else 0

        # Delivery premium: add 500 AED/week over 8 weeks baseline
        delivery_premium = max(0, (int(q.get("delivery_weeks", 8)) - 8)) * 500

        leveled.append({
            "supplier_name": q.get("supplier_name", "Unknown"),
            "total_aed": round(total_aed, 2),
            "weight_kg": weight,
            "rate_per_kg_aed": round(rate_per_kg, 4),
            "delivery_weeks": q.get("delivery_weeks", 8),
            "delivery_premium_aed": delivery_premium,
            "adjusted_total_aed": round(total_aed + delivery_premium, 2),
            "payment_terms": q.get("payment_terms", ""),
            "currency": q.get("currency", "AED"),
        })

    # Sort by adjusted total
    leveled_sorted = sorted(leveled, key=lambda x: x["adjusted_total_aed"])
    winner = leveled_sorted[0]
    runner_up = leveled_sorted[1]

    savings = runner_up["adjusted_total_aed"] - winner["adjusted_total_aed"]
    savings_pct = (savings / runner_up["adjusted_total_aed"] * 100) if runner_up["adjusted_total_aed"] > 0 else 0

    return {
        "matrix": leveled_sorted,
        "recommended_supplier": winner["supplier_name"],
        "savings_vs_runner_up_aed": round(savings, 2),
        "savings_pct": round(savings_pct, 2),
        "note": (
            f"Award to {winner['supplier_name']}: saves AED {savings:,.0f} "
            f"({savings_pct:.1f}%) vs {runner_up['supplier_name']}"
        ),
    }


# ── C5: S-Curve Cash Flow ─────────────────────────────────────────────────────

def generate_scurve_cashflow(
    contract_value_aed: float,
    start_date: datetime,
    duration_weeks: int = 52,
    advance_pct: float = 0.30,
    progress_pct: float = 0.60,
    retention_pct: float = 0.10,
    vat_rate: float = 0.05,
) -> dict:
    """
    C5: Generate week-by-week S-curve cash flow projection.

    Standard UAE facade payment structure:
    - 30% advance on LOA/signing
    - 60% milestone-based (delivery/installation)
    - 10% retention (locked 12 months post-handover)

    S-curve follows a sigmoid distribution for milestone payments.
    VAT at 5% applied to all payments (UAE VAT law).
    Returns 12-month (52-week) schedule by default.
    """
    assert abs(advance_pct + progress_pct + retention_pct - 1.0) < 0.001, \
        "Percentages must sum to 1.0"

    base = contract_value_aed

    # Week 0: Advance payment
    advance_amount = base * advance_pct
    retention_amount = base * retention_pct
    progress_amount = base * progress_pct

    # S-curve sigmoid distribution across 80% of duration (weeks 1 to 0.8*duration)
    # Uses cumulative normal distribution approximation
    active_weeks = int(duration_weeks * 0.80)
    weekly_schedule = []

    cumulative_disbursed = advance_amount  # LOA advance on week 0
    cumulative_vat = advance_amount * vat_rate

    weekly_schedule.append({
        "week": 0,
        "date": start_date.strftime("%Y-%m-%d"),
        "milestone": "LOA / Contract Signing — Advance Payment",
        "payment_aed": round(advance_amount, 2),
        "vat_aed": round(advance_amount * vat_rate, 2),
        "total_incl_vat_aed": round(advance_amount * (1 + vat_rate), 2),
        "cumulative_pct": round(advance_pct * 100, 1),
        "payment_type": "ADVANCE",
    })

    # S-curve for progress payments
    def sigmoid_weight(x: float) -> float:
        """Sigmoid: S-curve weight for week x in [0, 1] range."""
        return 1 / (1 + math.exp(-10 * (x - 0.5)))

    # Pre-compute cumulative sigmoid values
    sigmoid_vals = [sigmoid_weight(w / active_weeks) for w in range(active_weeks + 1)]
    total_sigmoid = sigmoid_vals[-1] - sigmoid_vals[0]

    cumulative_progress = 0.0

    for w in range(1, duration_weeks + 1):
        date = start_date + timedelta(weeks=w)

        if w <= active_weeks:
            # Progress payments weighted by sigmoid
            sig_curr = sigmoid_weight(w / active_weeks)
            sig_prev = sigmoid_weight((w - 1) / active_weeks)
            week_weight = (sig_curr - sig_prev) / total_sigmoid if total_sigmoid > 0 else 0
            payment = progress_amount * week_weight
        else:
            payment = 0.0

        # Retention release at week duration_weeks (12-month lock)
        is_retention_release = (w == duration_weeks)
        if is_retention_release:
            payment += retention_amount

        cumulative_progress += payment
        cumulative_disbursed += payment
        cumulative_pct = (cumulative_disbursed / base * 100) if base > 0 else 0

        if payment > 1.0:  # Only include weeks with meaningful payments
            weekly_schedule.append({
                "week": w,
                "date": date.strftime("%Y-%m-%d"),
                "milestone": (
                    "Retention Release — 12-Month DLP Complete"
                    if is_retention_release
                    else f"Progress Payment — Week {w}"
                ),
                "payment_aed": round(payment, 2),
                "vat_aed": round(payment * vat_rate, 2),
                "total_incl_vat_aed": round(payment * (1 + vat_rate), 2),
                "cumulative_pct": round(cumulative_pct, 1),
                "payment_type": "RETENTION" if is_retention_release else "PROGRESS",
            })

    total_ex_vat = sum(w["payment_aed"] for w in weekly_schedule)
    total_vat = sum(w["vat_aed"] for w in weekly_schedule)

    return {
        "contract_value_aed": contract_value_aed,
        "advance_aed": round(advance_amount, 2),
        "progress_aed": round(progress_amount, 2),
        "retention_aed": round(retention_amount, 2),
        "total_vat_aed": round(total_vat, 2),
        "total_incl_vat_aed": round(total_ex_vat + total_vat, 2),
        "duration_weeks": duration_weeks,
        "weekly_schedule": weekly_schedule,
        "note": (
            f"Retention AED {retention_amount:,.0f} locked until Week {duration_weeks} "
            f"(12-month Defects Liability Period). Never include in operating cashflow."
        ),
    }


# ── C6: Contract Redlining ────────────────────────────────────────────────────

async def redline_contract(draft_text: str, llm_client=None) -> dict:
    """
    C6: Automated contract redlining via Groq LLM.

    Reads client contract draft → flags clauses that deviate from:
    - UAE standard construction contract norms (FIDIC Silver / NEC3)
    - Madinat Al Saada standard terms (unlimited liability, back-to-back risk)
    - Known hostile clauses (liquidated damages > 5%, no EOT for force majeure, etc.)

    Returns structured list of flagged clauses with severity and suggested text.
    """
    REDLINE_PROMPT = """You are a construction contract legal analyst for a UAE facade subcontractor.

Analyze this contract draft and identify ALL clauses that are:
1. HOSTILE: Unfair risk allocation (e.g. unlimited LD, no force majeure EOT, pay-when-paid)
2. NON-STANDARD: Deviations from FIDIC Silver / NEC3 UAE norms
3. MISSING: Clauses the subcontractor should insist on (retention bond, access windows, back-charge process)
4. AMBIGUOUS: Terms that could be interpreted against the subcontractor

For each issue, provide:
- clause_ref: The clause number/section
- issue_type: HOSTILE | NON_STANDARD | MISSING | AMBIGUOUS
- severity: HIGH | MEDIUM | LOW
- description: What the problem is (1-2 sentences)
- suggested_text: Recommended replacement or addition (concise)

Return as JSON array: [{clause_ref, issue_type, severity, description, suggested_text}]

CONTRACT DRAFT:
"""
    if llm_client is None:
        try:
            from app.services.llm_client import LLMClient
            llm_client = LLMClient()
        except Exception:
            return {"error": "LLM client unavailable", "flags": []}

    if not draft_text or len(draft_text) < 100:
        return {"error": "Contract text too short", "flags": []}

    try:
        import json
        response = await llm_client.chat(
            messages=[{"role": "user", "content": REDLINE_PROMPT + draft_text[:8000]}],
            json_mode=True,
        )
        flags = json.loads(response) if isinstance(response, str) else response
        if isinstance(flags, list):
            high_count = sum(1 for f in flags if f.get("severity") == "HIGH")
            return {
                "total_flags": len(flags),
                "high_severity": high_count,
                "flags": flags,
                "recommendation": (
                    "REJECT — resolve HIGH severity items before signing"
                    if high_count > 0
                    else "APPROVE WITH NOTES — review MEDIUM items with legal team"
                ),
            }
    except Exception as e:
        logger.warning(f"Contract redlining LLM error: {e}")

    return {"error": "Redlining failed", "flags": []}


# ── C7: Milestone Payment Schedule ───────────────────────────────────────────

def generate_milestone_schedule(
    contract_value_aed: float,
    loa_date: datetime,
    project_duration_weeks: int = 52,
) -> dict:
    """
    C7: Generate structured milestone payment schedule.
    Standard facade project milestones (UAE construction norms).
    """
    milestones = [
        {"name": "LOA / Contract Award",         "week_offset": 0,   "pct": 0.30, "type": "ADVANCE"},
        {"name": "Shop Drawing Approval",         "week_offset": 4,   "pct": 0.05, "type": "MILESTONE"},
        {"name": "Material Procurement Delivery", "week_offset": 10,  "pct": 0.20, "type": "MILESTONE"},
        {"name": "Fabrication Complete",          "week_offset": 20,  "pct": 0.15, "type": "MILESTONE"},
        {"name": "Site Delivery",                 "week_offset": 26,  "pct": 0.10, "type": "MILESTONE"},
        {"name": "Installation 50% Complete",     "week_offset": 36,  "pct": 0.08, "type": "MILESTONE"},
        {"name": "Installation 100% / Snagging",  "week_offset": 46,  "pct": 0.02, "type": "MILESTONE"},
        {"name": "Practical Completion",          "week_offset": 52,  "pct": 0.00, "type": "COMPLETION"},
        {"name": "Retention Release (12-month DLP)", "week_offset": 104, "pct": 0.10, "type": "RETENTION"},
    ]

    schedule = []
    running_pct = 0.0
    for m in milestones:
        date = loa_date + timedelta(weeks=m["week_offset"])
        payment = contract_value_aed * m["pct"]
        running_pct += m["pct"]
        schedule.append({
            "milestone": m["name"],
            "target_date": date.strftime("%Y-%m-%d"),
            "week_from_loa": m["week_offset"],
            "payment_pct": m["pct"] * 100,
            "payment_aed": round(payment, 2),
            "payment_incl_vat_aed": round(payment * 1.05, 2),
            "cumulative_pct": round(running_pct * 100, 1),
            "payment_type": m["type"],
        })

    return {
        "contract_value_aed": contract_value_aed,
        "loa_date": loa_date.strftime("%Y-%m-%d"),
        "handover_date": (loa_date + timedelta(weeks=52)).strftime("%Y-%m-%d"),
        "retention_release_date": (loa_date + timedelta(weeks=104)).strftime("%Y-%m-%d"),
        "milestones": schedule,
        "total_scheduled_pct": round(running_pct * 100, 1),
    }


# ── C8: Yield & Scrap Optimization ──────────────────────────────────────────

def optimize_yield_and_scrap(
    cutting_list: list[dict],
    bar_length_mm: float = 6000.0,
    lme_aed_per_kg: float = 7.0,
    density_kg_mm3: float = 2.7e-6,    # Aluminum density
    offcut_usable_threshold_mm: float = 800.0,  # Blind Spot Rule #5
) -> dict:
    """
    C8: Analyze cutting list for scrap optimization.
    - Identifies usable offcuts (> 800mm) → flags for ERP inventory
    - Identifies dead scrap (≤ 800mm) → computes LME recycle revenue
    - Computes yield % per profile
    - Recommends bar allocation optimization

    cutting_list item: {
        "item_code": str, "length_mm": float, "quantity": int,
        "weight_kg_m": float, "bar_assignments": list[list[float]]
    }
    """
    profile_results = []
    total_material_kg = 0.0
    total_scrap_kg = 0.0
    total_usable_offcut_kg = 0.0
    total_dead_scrap_kg = 0.0

    for item in cutting_list:
        length_mm = float(item.get("length_mm", 0) or 0)
        quantity = int(item.get("quantity", 1) or 1)
        weight_kg_m = float(item.get("weight_kg_m", 1.5) or 1.5)
        bar_assignments = item.get("bar_assignments", [])

        weight_per_mm = weight_kg_m / 1000.0

        # Total material consumed (full bars)
        bars_used = len(bar_assignments) if bar_assignments else math.ceil(
            (length_mm * quantity) / bar_length_mm
        )
        material_kg = bars_used * bar_length_mm * weight_per_mm

        # Total cut length
        cut_kg = length_mm * quantity * weight_per_mm

        # Scrap = material - cuts (plus saw kerf ~3mm per cut)
        kerf_mm = 3.0
        total_kerf_kg = quantity * kerf_mm * weight_per_mm
        scrap_kg = material_kg - cut_kg - total_kerf_kg

        # Classify offcuts from bar_assignments
        usable_kg = 0.0
        dead_kg = 0.0
        usable_offcuts = []

        if bar_assignments:
            for bar in bar_assignments:
                bar_used = sum(float(x) for x in bar)
                bar_remaining = bar_length_mm - bar_used - (len(bar) * kerf_mm)
                if bar_remaining > offcut_usable_threshold_mm:
                    offcut_kg = bar_remaining * weight_per_mm
                    usable_kg += offcut_kg
                    usable_offcuts.append({
                        "length_mm": round(bar_remaining, 1),
                        "weight_kg": round(offcut_kg, 3),
                        "item_code": item.get("item_code", ""),
                        "erpStatus": "USABLE_INVENTORY",   # Blind Spot Rule #5
                    })
                else:
                    dead_kg += max(0, bar_remaining) * weight_per_mm
        else:
            # Estimate if no detailed bar assignments
            usable_kg = max(0, scrap_kg * 0.40)    # 40% of scrap is usable (est.)
            dead_kg = scrap_kg - usable_kg

        yield_pct = (cut_kg / material_kg * 100) if material_kg > 0 else 0

        profile_results.append({
            "item_code": item.get("item_code", ""),
            "bars_used": bars_used,
            "material_kg": round(material_kg, 3),
            "cut_kg": round(cut_kg, 3),
            "scrap_kg": round(scrap_kg, 3),
            "usable_offcut_kg": round(usable_kg, 3),
            "dead_scrap_kg": round(dead_kg, 3),
            "yield_pct": round(yield_pct, 1),
            "usable_offcuts": usable_offcuts,
        })

        total_material_kg += material_kg
        total_scrap_kg += scrap_kg
        total_usable_offcut_kg += usable_kg
        total_dead_scrap_kg += dead_kg

    # LME recycle revenue on dead scrap
    # Dead scrap sold at 60% of LME (typical UAE scrap buyer discount)
    scrap_value_aed = total_dead_scrap_kg * lme_aed_per_kg * 0.60
    overall_yield_pct = (
        (total_material_kg - total_scrap_kg) / total_material_kg * 100
        if total_material_kg > 0 else 0
    )

    return {
        "total_material_kg": round(total_material_kg, 2),
        "total_scrap_kg": round(total_scrap_kg, 2),
        "total_usable_offcut_kg": round(total_usable_offcut_kg, 2),
        "total_dead_scrap_kg": round(total_dead_scrap_kg, 2),
        "overall_yield_pct": round(overall_yield_pct, 1),
        "scrap_recycle_revenue_aed": round(scrap_value_aed, 2),
        "lme_rate_used_aed_kg": lme_aed_per_kg,
        "profiles": profile_results,
        "erp_usable_inventory": [
            offcut
            for p in profile_results
            for offcut in p.get("usable_offcuts", [])
        ],
        "recommendation": (
            f"Overall yield: {overall_yield_pct:.1f}%. "
            f"Recycle revenue: AED {scrap_value_aed:,.0f}. "
            + (
                f"WARNING: Yield below 80% — review bar nesting strategy."
                if overall_yield_pct < 80 else
                "Yield acceptable."
            )
        ),
    }


# ── C9: Third-Party Stamping API ─────────────────────────────────────────────

async def submit_for_pe_stamp(
    estimate_id: str,
    report_path: str,
    pe_webhook_url: str,
    tenant_id: str,
    db=None,
) -> dict:
    """
    C9: POST structural report to PE (Professional Engineer) webhook for stamping.
    Tracks stamp status in DB (stamping_requests table or JSON column).
    """
    if not pe_webhook_url:
        return {"error": "PE webhook URL not configured", "status": "NOT_SUBMITTED"}

    try:
        import httpx
        import os

        # Read the report file
        if not os.path.exists(report_path):
            return {"error": f"Report not found: {report_path}", "status": "NOT_SUBMITTED"}

        with open(report_path, "rb") as f:
            report_bytes = f.read()

        payload = {
            "estimate_id": estimate_id,
            "tenant_id": tenant_id,
            "submission_type": "structural_facade_report",
            "standard": "BS 6399-2 / ASCE 7",
            "submitted_at": datetime.now(timezone.utc).isoformat(),
        }

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                pe_webhook_url,
                data=payload,
                files={"report_pdf": ("structural_report.pdf", report_bytes, "application/pdf")},
            )

        if resp.status_code in (200, 201, 202):
            result = resp.json() if resp.content else {}
            return {
                "status": "SUBMITTED",
                "pe_reference": result.get("reference", "PENDING"),
                "submitted_at": payload["submitted_at"],
                "webhook_response": result,
            }
        else:
            return {
                "status": "FAILED",
                "http_status": resp.status_code,
                "error": resp.text[:500],
            }

    except Exception as e:
        logger.error(f"PE stamp submission failed: {e}")
        return {"status": "ERROR", "error": str(e)}


# ── C10: Tender Clarification Log ─────────────────────────────────────────────

def create_rfi_log_entry(
    rfi_text: str,
    source: str = "auto",
    estimate_id: str = "",
    reference: str = "",
) -> dict:
    """
    C10: Create a new RFI log entry.
    Persistent log stored in Estimate.state_snapshot["rfi_log"].
    Auto-flag unresponded items older than 7 days.
    """
    return {
        "rfi_id": f"RFI-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        "estimate_id": estimate_id,
        "reference": reference,
        "text": rfi_text,
        "source": source,       # "auto" | "compliance" | "manual"
        "status": "OPEN",
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "responded_at": None,
        "response_text": None,
        "days_open": 0,
        "overdue": False,       # True if > 7 days without response
    }


def audit_rfi_log(rfi_log: list[dict], overdue_days: int = 7) -> dict:
    """
    C10: Scan existing RFI log for overdue items.
    Updates overdue flag and returns summary.
    """
    now = datetime.now(timezone.utc)
    overdue_items = []

    for rfi in rfi_log:
        if rfi.get("status") == "OPEN":
            submitted_str = rfi.get("submitted_at", "")
            try:
                submitted = datetime.fromisoformat(submitted_str.replace("Z", "+00:00"))
                days_open = (now - submitted).days
                rfi["days_open"] = days_open
                rfi["overdue"] = days_open >= overdue_days
                if rfi["overdue"]:
                    overdue_items.append(rfi["rfi_id"])
            except Exception:
                pass

    return {
        "total_rfis": len(rfi_log),
        "open_rfis": sum(1 for r in rfi_log if r.get("status") == "OPEN"),
        "overdue_rfis": len(overdue_items),
        "overdue_rfi_ids": overdue_items,
        "alert": (
            f"WARNING: {len(overdue_items)} RFI(s) unanswered > {overdue_days} days — escalate to client"
            if overdue_items else "All RFIs within response window"
        ),
    }


# ── C11: Dynamic VE Menu ─────────────────────────────────────────────────────

def build_ve_menu(
    ve_suggestions: list[dict],
    bom_items: list[dict],
) -> dict:
    """
    C11: Build interactive VE menu for frontend.
    Each VE item has accept/reject state + running savings total calculation.

    Returns menu structure that frontend can render as interactive checklist.
    """
    menu_items = []
    total_potential_savings_aed = 0.0

    for i, ve in enumerate(ve_suggestions):
        saving_aed = float(ve.get("saving_aed", 0) or ve.get("estimated_saving_aed", 0) or 0)
        total_potential_savings_aed += saving_aed

        menu_items.append({
            "ve_id": f"VE-{i+1:03d}",
            "description": ve.get("description", ""),
            "category": ve.get("category", "GENERAL"),
            "saving_aed": round(saving_aed, 2),
            "saving_pct": round(ve.get("saving_pct", 0) or 0, 1),
            "technical_impact": ve.get("technical_impact", "None"),
            "risk_level": ve.get("risk_level", "LOW"),
            "status": "PENDING",        # PENDING | ACCEPTED | REJECTED
            "accepted_by": None,
            "rejected_reason": None,
            # What changes in BOM if accepted
            "affected_item_codes": ve.get("affected_item_codes", []),
            "substitute_item_code": ve.get("substitute_item_code"),
        })

    return {
        "total_ve_items": len(menu_items),
        "total_potential_savings_aed": round(total_potential_savings_aed, 2),
        "accepted_savings_aed": 0.0,    # Updated as user accepts items
        "items": menu_items,
        "instructions": (
            "Review each VE option. Accepted items automatically update the BOQ and reduce contract value. "
            "Rejected items are logged for tender response. All decisions require estimator sign-off."
        ),
    }


def apply_ve_decision(
    ve_menu: dict,
    ve_id: str,
    decision: str,  # "ACCEPTED" | "REJECTED"
    decided_by: str = "",
    rejection_reason: str = "",
) -> dict:
    """
    C11: Apply accept/reject decision to a VE menu item.
    Recalculates running accepted savings total.
    """
    updated_items = []
    accepted_savings = 0.0

    for item in ve_menu.get("items", []):
        if item["ve_id"] == ve_id:
            item["status"] = decision
            item["accepted_by"] = decided_by if decision == "ACCEPTED" else None
            item["rejected_reason"] = rejection_reason if decision == "REJECTED" else None

        if item["status"] == "ACCEPTED":
            accepted_savings += item["saving_aed"]

        updated_items.append(item)

    ve_menu["items"] = updated_items
    ve_menu["accepted_savings_aed"] = round(accepted_savings, 2)
    ve_menu["revised_contract_value_aed"] = round(
        ve_menu.get("contract_value_aed", 0) - accepted_savings, 2
    )

    return ve_menu

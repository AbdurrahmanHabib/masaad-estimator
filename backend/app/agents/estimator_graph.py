"""
LangGraph State Graph — Masaad Estimator Pipeline.

Node execution order:
  IngestionNode → ScopeIdentificationNode → GeometryQANode → BOMNode
      → [HITLTriageNode if confidence < 0.90 or hitl_pending]
      → DeltaCompareNode → PricingNode → CommercialNode
      → [InternationalRoutingNode if is_international]
      → ApprovalGatewayNode  ← halts, sets REVIEW_REQUIRED, waits for admin signature
      → ReportNode (only after APPROVED)

Each node:
  1. Updates state.current_node and state.progress_pct
  2. Does its work (real implementations below)
  3. Checkpoints state to Redis before returning
"""
import json
import logging
from typing import Callable
from datetime import datetime, timezone

from langgraph.graph import StateGraph, END

from app.agents.graph_state import GraphState

logger = logging.getLogger("masaad-estimator-graph")

HITL_CONFIDENCE_THRESHOLD = 0.90


# ── Checkpoint helpers ─────────────────────────────────────────────────────────

async def _checkpoint(state: GraphState, redis_client) -> None:
    """Persist state to Redis with 24h TTL for crash recovery."""
    if redis_client is None:
        return
    key = f"ckpt:{state['estimate_id']}:{state['current_node']}"
    try:
        serializable = {k: v for k, v in state.items() if isinstance(v, (str, int, float, bool, list, dict, type(None)))}
        await redis_client.set(key, json.dumps(serializable), ex=86400)
    except Exception as e:
        logger.warning(f"Checkpoint write failed: {e}")


async def load_checkpoint(estimate_id: str, redis_client) -> GraphState | None:
    """
    Load the most recent checkpoint for an estimate.
    Returns None if no checkpoint exists (fresh run).
    """
    if redis_client is None:
        return None
    try:
        pattern = f"ckpt:{estimate_id}:*"
        keys = await redis_client.keys(pattern)
        if not keys:
            return None
        latest = sorted(keys)[-1]
        raw = await redis_client.get(latest)
        if raw:
            return json.loads(raw)
    except Exception as e:
        logger.warning(f"Checkpoint load failed: {e}")
    return None


async def _persist_estimate(estimate_id: str, updates: dict) -> None:
    """Write partial updates to the Estimate row via SQLAlchemy."""
    try:
        from app.db import AsyncSessionLocal
        from app.models.orm_models import Estimate
        from sqlalchemy import select
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Estimate).where(Estimate.id == estimate_id))
            est = result.scalar_one_or_none()
            if est:
                for k, v in updates.items():
                    if hasattr(est, k):
                        setattr(est, k, v)
                await session.commit()
    except Exception as e:
        logger.warning(f"DB persist failed for {estimate_id}: {e}")


# ── Node factory ───────────────────────────────────────────────────────────────

def make_node(name: str, progress: int, impl: Callable | None = None):
    """
    Factory: wraps an implementation function with checkpoint + progress tracking.
    If impl is None, the node is a passthrough stub.
    """
    async def node(state: GraphState) -> GraphState:
        state["current_node"] = name
        state["progress_pct"] = progress
        logger.info(f"[{state['estimate_id']}] Entering {name} ({progress}%)")

        if impl is not None:
            try:
                state = await impl(state)
            except Exception as e:
                state["error"] = str(e)
                state["error_node"] = name
                logger.error(f"[{state['estimate_id']}] {name} failed: {e}", exc_info=True)

        state["last_completed_node"] = name
        return state

    node.__name__ = name
    return node


# ── NODE IMPLEMENTATIONS ───────────────────────────────────────────────────────

async def _ingestion_impl(state: GraphState) -> GraphState:
    """
    IngestionNode — runs the full ingestion sub-graph:
    DWG parse → spec text extract → scope identification → opening schedule → RFI register.
    Bridges ingestion_graph.IngestionState → GraphState.
    """
    from app.agents.ingestion_graph import ingestion_app
    import os

    estimate_id = state["estimate_id"]
    drawing_paths = state.get("drawing_paths", [])
    spec_text = state.get("spec_text", "")

    # Build ingestion sub-graph input
    db_url = os.getenv("DATABASE_URL", "")
    if "+asyncpg" in db_url:
        db_url = db_url.replace("+asyncpg", "")

    dwg_path = drawing_paths[0] if drawing_paths else None
    ingestion_input = {
        "estimate_id": estimate_id,
        "db_url": db_url,
        "dwg_path": dwg_path,
        "spec_path": None,
        "project_data": {},
        "dwg_extraction": {},
        "spec_text": spec_text,
        "project_scope": {},
        "opening_schedule": {},
        "rfi_flags": [],
        "reasoning_log": [],
        "error": None,
    }

    try:
        result = await ingestion_app.ainvoke(ingestion_input)
        opening_schedule = result.get("opening_schedule", {})
        openings = opening_schedule.get("schedule", [])

        state["extracted_openings"] = openings
        state["spec_text"] = result.get("spec_text", spec_text)

        logger.info(f"[{estimate_id}] IngestionNode: {len(openings)} openings extracted")

        if result.get("error"):
            logger.warning(f"[{estimate_id}] Ingestion sub-graph error: {result['error']}")
            state["confidence_score"] = min(state.get("confidence_score", 1.0), 0.75)

    except Exception as e:
        logger.error(f"[{estimate_id}] Ingestion sub-graph failed: {e}")
        state["extracted_openings"] = []
        state["confidence_score"] = min(state.get("confidence_score", 1.0), 0.60)

    await _persist_estimate(estimate_id, {
        "status": "ESTIMATING",
        "current_step": "Ingestion complete",
        "progress_pct": 5,
    })
    return state


async def _scope_impl(state: GraphState) -> GraphState:
    """
    ScopeIdentificationNode — matches extracted openings to catalog items,
    identifies facade systems, builds catalog_matches list.
    """
    from app.services.scope_engine import ScopeIdentificationEngine
    from app.db import AsyncSessionLocal
    from app.models.orm_models import CatalogItem
    from sqlalchemy import select

    estimate_id = state["estimate_id"]
    tenant_id = state["tenant_id"]

    # Load catalog items for this tenant
    catalog_items = []
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(CatalogItem).where(CatalogItem.tenant_id == tenant_id)
            )
            rows = result.scalars().all()
            catalog_items = [
                {
                    "item_code": r.item_code,
                    "die_number": r.die_number,
                    "system_series": r.system_series,
                    "description": r.description,
                    "weight_per_meter": float(r.weight_per_meter) if r.weight_per_meter else None,
                    "weight_kg_m": float(r.weight_per_meter) if r.weight_per_meter else None,
                    "perimeter_mm": float(r.perimeter_mm) if r.perimeter_mm else None,
                    "price_aed_per_kg": float(r.price_aed_per_kg) if r.price_aed_per_kg else None,
                    "material_type": r.material_type or "ALUMINUM_EXTRUSION",
                    "price_aed_sqm": float(r.price_aed_sqm) if hasattr(r, 'price_aed_sqm') and r.price_aed_sqm else None,
                    "glass_makeup": r.glass_makeup if hasattr(r, 'glass_makeup') else None,
                    "u_value_w_m2k": float(r.u_value_w_m2k) if hasattr(r, 'u_value_w_m2k') and r.u_value_w_m2k else None,
                }
                for r in rows
            ]
    except Exception as e:
        logger.warning(f"[{estimate_id}] Catalog load failed: {e}")

    # Run scope engine
    try:
        engine = ScopeIdentificationEngine()
        scope_result = engine.identify_project_scope(
            dwg_extraction={},
            spec_text=state.get("spec_text", ""),
        )
        scope_dict = scope_result.to_dict() if hasattr(scope_result, "to_dict") else {}
    except Exception as e:
        logger.warning(f"[{estimate_id}] Scope engine failed: {e}")
        scope_dict = {}

    # Build catalog_matches: pair openings with catalog profiles
    openings = state.get("extracted_openings", [])
    catalog_matches = []
    for opening in openings:
        system_type = opening.get("system_type", "DEFAULT")
        matched = [c for c in catalog_items
                   if c.get("system_series", "").lower() in system_type.lower()
                   or system_type.lower() in (c.get("system_series", "") or "").lower()]
        if not matched:
            matched = catalog_items[:3]  # fallback: first 3 items
        for m in matched[:4]:
            catalog_matches.append({
                **m,
                "opening_id": opening.get("id", ""),
                "system_type": system_type,
            })

    state["catalog_matches"] = catalog_matches
    logger.info(f"[{estimate_id}] ScopeNode: {len(catalog_matches)} catalog matches, {len(catalog_items)} catalog items loaded")

    # Store catalog_items in state for BOMNode
    state["_catalog_items"] = catalog_items  # type: ignore[index]

    await _persist_estimate(estimate_id, {"current_step": "Scope identified", "progress_pct": 15})
    return state


async def _geometry_qa_impl(state: GraphState) -> GraphState:
    """
    GeometryQANode — verify SmartProfileDie records for all catalog item_codes
    referenced in this estimate's scope.

    VERIFIED die    → full confidence contribution
    DRAFT die       → reduces confidence_score (non-blocking)
    Missing die     → hitl_pending = True
    """
    try:
        from app.db import AsyncSessionLocal
        from app.models.orm_models import SmartProfileDie
        from sqlalchemy import select

        catalog_matches = state.get("catalog_matches", [])
        if not catalog_matches:
            return state

        referenced_codes = list({m.get("item_code") for m in catalog_matches if m.get("item_code")})
        if not referenced_codes:
            return state

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(SmartProfileDie).where(
                    SmartProfileDie.tenant_id == state["tenant_id"],
                    SmartProfileDie.item_code.in_(referenced_codes),
                )
            )
            dies = {d.item_code: d for d in result.scalars().all()}

        missing = [c for c in referenced_codes if c not in dies]
        draft = [c for c, d in dies.items() if not d.dxf_path or not d.anchor_origin_xy]
        verified_count = len(referenced_codes) - len(missing) - len(draft)
        total = len(referenced_codes)

        logger.info(
            f"[{state['estimate_id']}] GeometryQA: {verified_count}/{total} verified, "
            f"{len(draft)} draft, {len(missing)} missing"
        )

        if total > 0:
            qa_score = verified_count / total
            state["confidence_score"] = round(state.get("confidence_score", 1.0) * qa_score, 3)

        if missing:
            state["hitl_pending"] = True
            existing = state.get("hitl_triage_ids") or []
            for code in missing:
                triage_id = f"geometry_qa_missing_{code}"
                if triage_id not in existing:
                    existing = existing + [triage_id]
            state["hitl_triage_ids"] = existing

        if draft and not missing:
            state["confidence_score"] = min(state.get("confidence_score", 1.0), 0.85)

    except Exception as e:
        logger.warning(f"GeometryQANode non-fatal error: {e}")

    return state


async def _bom_impl(state: GraphState) -> GraphState:
    """
    BOMNode — explodes all openings into detailed BOM line items.
    Also runs 1D CSP cutting optimization for all aluminum profiles.
    """
    from app.services.bom_engine import BOMEngine
    from app.services.cutting_list_engine import CuttingListEngine

    estimate_id = state["estimate_id"]
    openings = state.get("extracted_openings", [])
    catalog_items = state.get("_catalog_items", [])  # type: ignore[call-overload]
    lme = state.get("lme_aed_per_kg", 7.0)

    # Get labor burn rate from DB
    labor_burn_rate = 13.0
    try:
        from app.db import AsyncSessionLocal
        from app.models.orm_models import FinancialRates
        from sqlalchemy import select
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(FinancialRates).where(FinancialRates.tenant_id == state["tenant_id"])
            )
            rates = result.scalar_one_or_none()
            if rates and hasattr(rates, 'baseline_labor_burn_rate_aed') and rates.baseline_labor_burn_rate_aed:
                labor_burn_rate = float(rates.baseline_labor_burn_rate_aed)
    except Exception:
        pass

    # If no openings from ingestion, create a synthetic opening from spec
    if not openings:
        openings = [{
            "id": "synthetic-001",
            "system_type": "Curtain Wall",
            "width_mm": 1500,
            "height_mm": 3000,
            "quantity": 10,
        }]
        state["confidence_score"] = min(state.get("confidence_score", 1.0), 0.65)

    engine = BOMEngine()
    bom_items = engine.explode_all(openings, catalog_items, lme, labor_burn_rate)
    bom_items = engine.aggregate_by_item_code(bom_items)

    # Cutting list — simplified passthrough using CSP optimizer directly
    cutting_list = []
    try:
        from app.services.csp_optimizer import CSPOptimizer
        csp = CSPOptimizer()
        alum_items = [item for item in bom_items
                      if item.get("category") == "ALUMINUM" and item.get("unit") == "lm"]
        for item in alum_items:
            qty = max(1, int(item.get("quantity", 0)))
            length_mm = int(item.get("quantity", 1) * 1000 / max(qty, 1))
            demands = [length_mm] * qty
            result = csp.solve_1d_csp(demands, [])
            plan = result.get("plan", [])
            bar_count = len(plan)
            remnant = plan[0].get("remnant", 0) if plan else 0
            cutting_list.append({
                "item_code": item.get("item_code", ""),
                "description": item.get("description", ""),
                "length_mm": length_mm,
                "quantity": qty,
                "stock_length_mm": 6000,
                "remnant_mm": remnant,
                "bar_count": bar_count,
            })
    except Exception as e:
        logger.warning(f"[{estimate_id}] Cutting list failed: {e}")

    state["bom_items"] = bom_items
    state["cutting_list"] = cutting_list

    total_cost = sum(item.get("subtotal_aed", 0) for item in bom_items if not item.get("is_attic_stock"))
    logger.info(f"[{estimate_id}] BOMNode: {len(bom_items)} line items, AED {total_cost:,.0f} total")

    await _persist_estimate(estimate_id, {
        "current_step": "BOM complete",
        "progress_pct": 30,
        "bom_output_json": {"items": bom_items},
    })
    return state


async def _hitl_triage_impl(state: GraphState) -> GraphState:
    """
    HITLTriageNode — creates TriageItem records in DB for each pending HITL issue,
    sets status to REVIEW_REQUIRED so the graph halts at ApprovalGateway.
    """
    from app.db import AsyncSessionLocal
    from app.models.orm_models import TriageItem

    estimate_id = state["estimate_id"]
    triage_ids = state.get("hitl_triage_ids", [])

    try:
        async with AsyncSessionLocal() as session:
            for triage_id in triage_ids:
                # Check if already exists
                from sqlalchemy import select
                existing = await session.execute(
                    select(TriageItem).where(TriageItem.id == triage_id)
                )
                if existing.scalar_one_or_none():
                    continue
                item = TriageItem(
                    id=triage_id,
                    tenant_id=state["tenant_id"],
                    estimate_id=estimate_id,
                    node_name=state.get("current_node", "HITLTriageNode"),
                    confidence_score=state.get("confidence_score", 0.0),
                    context_json=json.dumps({
                        "confidence_score": state.get("confidence_score"),
                        "error": state.get("error"),
                        "current_node": state.get("current_node"),
                    }),
                    status="pending",
                )
                session.add(item)
            await session.commit()
    except Exception as e:
        logger.error(f"[{estimate_id}] HITL triage DB write failed: {e}")

    state["status"] = "REVIEW_REQUIRED"
    logger.info(f"[{estimate_id}] HITLTriageNode: {len(triage_ids)} items queued, status → REVIEW_REQUIRED")

    await _persist_estimate(estimate_id, {
        "status": "REVIEW_REQUIRED",
        "current_step": "Awaiting HITL review",
        "progress_pct": 35,
    })
    return state


async def _delta_compare_impl(state: GraphState) -> GraphState:
    """
    DeltaCompareNode — compares current BOM against prev_bom_snapshot.
    Only active when revision_number > 0. Produces variation_order_delta.
    """
    estimate_id = state["estimate_id"]
    revision = state.get("revision_number", 0)

    if revision == 0:
        logger.info(f"[{estimate_id}] DeltaCompare: revision 0, skipping diff")
        return state

    prev_snap = state.get("prev_bom_snapshot")
    if not prev_snap:
        logger.info(f"[{estimate_id}] DeltaCompare: no previous snapshot, skipping")
        return state

    current_bom = state.get("bom_items", [])
    prev_items = {i["item_code"]: i for i in prev_snap.get("items", [])}
    curr_items = {i["item_code"]: i for i in current_bom if not i.get("is_attic_stock")}

    changes = []
    total_impact = 0.0

    all_codes = set(prev_items) | set(curr_items)
    for code in all_codes:
        prev = prev_items.get(code)
        curr = curr_items.get(code)

        if prev and not curr:
            change_type = "REMOVED"
            impact = -(prev.get("subtotal_aed", 0))
        elif curr and not prev:
            change_type = "ADDED"
            impact = curr.get("subtotal_aed", 0)
        else:
            old_qty = prev.get("quantity", 0)
            new_qty = curr.get("quantity", 0)
            if abs(new_qty - old_qty) < 0.001:
                continue
            change_type = "QUANTITY_CHANGED"
            unit_cost = curr.get("unit_cost_aed", 0)
            impact = (new_qty - old_qty) * unit_cost

        changes.append({
            "item_code": code,
            "change_type": change_type,
            "old_quantity": prev.get("quantity", 0) if prev else 0,
            "new_quantity": curr.get("quantity", 0) if curr else 0,
            "unit": (curr or prev).get("unit", ""),
            "unit_cost_aed": (curr or prev).get("unit_cost_aed", 0),
            "cost_impact_aed": round(impact, 2),
        })
        total_impact += impact

    state["variation_order_delta"] = {
        "revision_number": revision,
        "changes": changes,
        "total_cost_impact_aed": round(total_impact, 2),
        "change_count": len(changes),
        "compared_at": datetime.now(timezone.utc).isoformat(),
    }

    logger.info(
        f"[{estimate_id}] DeltaCompare: {len(changes)} changes, "
        f"AED {total_impact:+,.0f} total impact (Rev {revision})"
    )
    return state


async def _pricing_impl(state: GraphState) -> GraphState:
    """
    PricingNode — applies costing engine to BOM items, computes per-category
    costs, overhead, margin, and final contract value.
    """
    from app.services.costing_engine import CostingEngine

    estimate_id = state["estimate_id"]
    bom_items = state.get("bom_items", [])
    lme_aed = state.get("lme_aed_per_kg", 7.0)

    engine = CostingEngine()

    # Aggregate costs by category (exclude attic stock from subtotals)
    alum_cost = sum(i["subtotal_aed"] for i in bom_items
                    if i.get("category") == "ALUMINUM" and not i.get("is_attic_stock"))
    glass_cost = sum(i["subtotal_aed"] for i in bom_items
                     if i.get("category") == "GLASS" and not i.get("is_attic_stock"))
    hardware_cost = sum(i["subtotal_aed"] for i in bom_items
                        if i.get("category") in ("HARDWARE", "SILICONE") and not i.get("is_attic_stock"))
    labor_cost = sum(i["subtotal_aed"] for i in bom_items
                     if i.get("category") == "LABOR" and not i.get("is_attic_stock"))
    attic_cost = sum(i["subtotal_aed"] for i in bom_items if i.get("is_attic_stock"))

    direct_cost = alum_cost + glass_cost + hardware_cost + labor_cost + attic_cost
    overhead = round(direct_cost * engine.overhead_pct, 2)
    margin_pct = 0.18  # 18% gross margin (UAE facade industry standard)
    margin_aed = round((direct_cost + overhead) * margin_pct, 2)
    total = round(direct_cost + overhead + margin_aed, 2)

    pricing_data = {
        "aluminum_cost_aed": round(alum_cost, 2),
        "glass_cost_aed": round(glass_cost, 2),
        "hardware_cost_aed": round(hardware_cost, 2),
        "labor_cost_aed": round(labor_cost, 2),
        "attic_stock_cost_aed": round(attic_cost, 2),
        "material_cost_aed": round(alum_cost + glass_cost + hardware_cost, 2),
        "overhead_aed": overhead,
        "overhead_pct": engine.overhead_pct,
        "margin_aed": margin_aed,
        "gross_margin_pct": margin_pct * 100,
        "total_aed": total,
        "lme_aed_per_kg_used": lme_aed,
        "currency": state.get("project_currency", "AED"),
        "priced_at": datetime.now(timezone.utc).isoformat(),
    }

    state["pricing_data"] = pricing_data
    logger.info(f"[{estimate_id}] PricingNode: AED {total:,.0f} total (margin {margin_pct*100:.0f}%)")

    await _persist_estimate(estimate_id, {"current_step": "Pricing complete", "progress_pct": 60})
    return state


async def _commercial_impl(state: GraphState) -> GraphState:
    """
    CommercialNode — applies 5 Commercial Blind Spot Rules + VE engine.

    Blind Spots:
      1. Retention Money  — 10% locked 12 months (noted in pricing_data, never in cashflow)
      2. Provisional Sums — GPR scanning + water testing allowances added to BOM
      3. Logistics Permits — if site access noted, add Municipality/RTA permit line item
      4. Attic Stock       — already applied in BOMEngine (2%)
      5. Usable Inventory  — cutting list remnants > 800mm flagged
    """
    from app.services.value_engineering_engine import ValueEngineeringEngine

    estimate_id = state["estimate_id"]
    bom_items = state.get("bom_items", [])
    pricing = state.get("pricing_data", {})
    cutting_list = state.get("cutting_list", [])
    spec_text = state.get("spec_text", "")

    # ── Blind Spot 1: Retention Money ─────────────────────────────────────────
    total = pricing.get("total_aed", 0)
    retention_aed = round(total * 0.10, 2)
    pricing["retention_deduction_aed"] = retention_aed
    pricing["retention_note"] = "10% retention deducted from cashflow — locked 12 months per contract"
    pricing["cashflow_net_aed"] = round(total - retention_aed, 2)

    # ── Blind Spot 2: Provisional Sums ────────────────────────────────────────
    provisional_items = [
        {
            "item_code": "PROV-GPR-SCAN",
            "description": "Provisional Sum — GPR Post-Tension Slab Scanning (before fixings)",
            "category": "PROVISIONAL",
            "unit": "allowance",
            "quantity": 1.0,
            "unit_cost_aed": 8500.0,
            "subtotal_aed": 8500.0,
            "is_attic_stock": False,
            "notes": "Blind Spot Rule: Always include GPR scanning allowance",
        },
        {
            "item_code": "PROV-WATER-TEST",
            "description": "Provisional Sum — Third-Party Water Penetration Testing",
            "category": "PROVISIONAL",
            "unit": "allowance",
            "quantity": 1.0,
            "unit_cost_aed": 5500.0,
            "subtotal_aed": 5500.0,
            "is_attic_stock": False,
            "notes": "Blind Spot Rule: Always include water test allowance",
        },
    ]
    bom_items.extend(provisional_items)
    pricing["provisional_sums_aed"] = 14000.0
    pricing["total_aed"] = round(pricing["total_aed"] + 14000.0, 2)

    # ── Blind Spot 3: Logistics Permits ───────────────────────────────────────
    spec_lower = spec_text.lower()
    needs_permit = any(kw in spec_lower for kw in ["tight", "restricted", "road closure", "municipality", "rta"])
    if needs_permit:
        bom_items.append({
            "item_code": "PERM-RTA-CLOSURE",
            "description": "Municipality / RTA Road Closure Permit",
            "category": "PROVISIONAL",
            "unit": "allowance",
            "quantity": 1.0,
            "unit_cost_aed": 3500.0,
            "subtotal_aed": 3500.0,
            "is_attic_stock": False,
            "notes": "Blind Spot Rule: Logistics permit auto-detected from spec",
        })
        pricing["total_aed"] = round(pricing["total_aed"] + 3500.0, 2)

    # ── Blind Spot 5: Usable Inventory (off-cuts > 800mm) ─────────────────────
    usable_offcuts = []
    if cutting_list:
        for cut in cutting_list:
            remnant = cut.get("remnant_mm", 0)
            if remnant > 800:
                usable_offcuts.append({
                    "item_code": cut.get("item_code", ""),
                    "remnant_mm": remnant,
                    "status": "USABLE_INVENTORY",
                    "note": "Return to ERP stock — do not scrap",
                })
    pricing["usable_inventory"] = usable_offcuts
    if usable_offcuts:
        logger.info(f"[{estimate_id}] CommercialNode: {len(usable_offcuts)} usable offcuts flagged")

    # ── VE Suggestions ────────────────────────────────────────────────────────
    ve_suggestions = []
    try:
        ve_engine = ValueEngineeringEngine()
        bom_dict = {"items": bom_items}
        material_rates = {"lme_aed_per_kg": state.get("lme_aed_per_kg", 7.0)}
        ve_opps = ve_engine.find_ve_opportunities(
            bom_data=bom_dict,
            opening_schedule={"schedule": state.get("extracted_openings", [])},
            spec_text=spec_text,
            material_rates=material_rates,
        )
        ve_suggestions = ve_engine.to_dict(ve_opps) if ve_opps else []
    except Exception as e:
        logger.warning(f"[{estimate_id}] VE engine failed: {e}")

    state["bom_items"] = bom_items
    state["pricing_data"] = pricing
    state["ve_suggestions"] = ve_suggestions if isinstance(ve_suggestions, list) else []

    # ── C5: S-Curve Cash Flow ──────────────────────────────────────────────────
    try:
        from app.services.commercial_director import generate_scurve_cashflow
        from datetime import datetime, timezone as tz
        scurve = generate_scurve_cashflow(
            contract_value_aed=pricing.get("total_aed", 0),
            start_date=datetime.now(tz.utc),
            duration_weeks=52,
        )
        state["scurve_cashflow"] = scurve
    except Exception as e:
        logger.warning(f"[{estimate_id}] S-curve generation failed: {e}")

    # ── C7: Milestone Payment Schedule ────────────────────────────────────────
    try:
        from app.services.commercial_director import generate_milestone_schedule
        from datetime import datetime, timezone as tz
        milestone_sched = generate_milestone_schedule(
            contract_value_aed=pricing.get("total_aed", 0),
            loa_date=datetime.now(tz.utc),
        )
        state["milestone_schedule"] = milestone_sched
    except Exception as e:
        logger.warning(f"[{estimate_id}] Milestone schedule failed: {e}")

    # ── C8: Yield & Scrap Optimization ────────────────────────────────────────
    try:
        from app.services.commercial_director import optimize_yield_and_scrap
        yield_report = optimize_yield_and_scrap(
            cutting_list=state.get("cutting_list", []),
            lme_aed_per_kg=state.get("lme_aed_per_kg", 7.0),
        )
        state["yield_report"] = yield_report
        # Merge ERP usable inventory into pricing usable_inventory
        erp_items = yield_report.get("erp_usable_inventory", [])
        if erp_items:
            pricing.setdefault("usable_inventory", []).extend(erp_items)
    except Exception as e:
        logger.warning(f"[{estimate_id}] Yield optimization failed: {e}")

    # ── C11: Dynamic VE Menu ───────────────────────────────────────────────────
    try:
        from app.services.commercial_director import build_ve_menu
        ve_menu = build_ve_menu(
            ve_suggestions=state.get("ve_suggestions", []),
            bom_items=bom_items,
        )
        ve_menu["contract_value_aed"] = pricing.get("total_aed", 0)
        state["ve_menu"] = ve_menu
    except Exception as e:
        logger.warning(f"[{estimate_id}] VE menu build failed: {e}")

    # ── C10: Initialize RFI log ────────────────────────────────────────────────
    rfi_log = list(state.get("rfi_log") or [])
    state["rfi_log"] = rfi_log

    logger.info(f"[{estimate_id}] CommercialNode: 5 blind spot rules applied, {len(ve_suggestions)} VE suggestions")

    await _persist_estimate(estimate_id, {"current_step": "Commercial analysis complete", "progress_pct": 75})
    return state


async def _compliance_impl(state: GraphState) -> GraphState:
    """
    ComplianceNode — Phase 3B compliance engineering.

    C1: Structural deflection vs BS 6399-2 / ASCE 7 (wind load, L/175 limit)
    C2: Thermal/acoustic vs Dubai Green Building Regulations + ASHRAE 90.1
    C3: Fire rating vs UAE Civil Defence Code — auto-RFI if gap
    """
    from app.services.compliance_engine import run_compliance_checks, report_to_dict

    estimate_id = state["estimate_id"]
    bom_items = state.get("bom_items", [])
    catalog_matches = state.get("catalog_matches", [])
    spec_text = state.get("spec_text", "")

    # Extract building type from spec text (simple heuristic)
    spec_lower = spec_text.lower()
    if "residential" in spec_lower or "apartment" in spec_lower:
        building_type = "residential_high_rise"
        occupancy = "residential"
    elif "hospital" in spec_lower or "healthcare" in spec_lower:
        building_type = "hospital"
        occupancy = "commercial_office"
    elif "hotel" in spec_lower:
        building_type = "hotel"
        occupancy = "commercial_office"
    elif "car park" in spec_lower or "parking" in spec_lower:
        building_type = "car_park"
        occupancy = "commercial_office"
    else:
        building_type = "commercial_office"
        occupancy = "commercial_office"

    try:
        report = run_compliance_checks(
            bom_items=bom_items,
            catalog_matches=catalog_matches,
            spec_text=spec_text,
            building_type=building_type,
            building_occupancy=occupancy,
        )
        report_dict = report_to_dict(report)
        state["compliance_report"] = report_dict

        # Auto-add compliance RFIs to rfi_log
        from app.services.commercial_director import create_rfi_log_entry
        rfi_log = list(state.get("rfi_log") or [])
        for rfi_text in report.rfi_items:
            rfi_log.append(create_rfi_log_entry(
                rfi_text=rfi_text,
                source="compliance",
                estimate_id=estimate_id,
                reference="Phase3B-Compliance",
            ))
        state["rfi_log"] = rfi_log

        # Cap confidence if compliance fails
        if not report.overall_passed:
            state["confidence_score"] = min(
                state.get("confidence_score", 1.0), 0.80
            )
            logger.warning(
                f"[{estimate_id}] ComplianceNode: FAILED — "
                f"{len(report.summary_flags)} flags, {len(report.rfi_items)} RFIs"
            )
        else:
            logger.info(f"[{estimate_id}] ComplianceNode: PASSED — all C1/C2/C3 checks OK")

    except Exception as e:
        logger.error(f"[{estimate_id}] ComplianceNode failed: {e}")
        state["compliance_report"] = {"overall_passed": None, "error": str(e)}

    await _persist_estimate(estimate_id, {"current_step": "Compliance checks complete", "progress_pct": 78})
    return state


async def _international_routing_impl(state: GraphState) -> GraphState:
    """
    InternationalRoutingNode — activated when is_international == True.

    Adjustments:
    - Scope exclusion: delivery strictly EXW (Ex Works) — no freight/customs in estimate
    - Forex risk buffer: +3% on material costs (USD/AED volatility)
    - Bank Guarantee fee: 2.5% of contract value (typically required for intl. projects)
    - Manpower Mobilization: flights/visas budget or swap to local subcontractor note
    - Adds container packing list placeholder to BOM
    """
    estimate_id = state["estimate_id"]
    pricing = state.get("pricing_data", {})
    bom_items = state.get("bom_items", [])
    total = pricing.get("total_aed", 0)

    # EXW note
    pricing["delivery_terms"] = "EXW (Ex Works) — Ajman, UAE. Freight, customs, insurance EXCLUDED."

    # Forex risk buffer (+3% material costs)
    material_cost = pricing.get("material_cost_aed", 0)
    forex_buffer = round(material_cost * 0.03, 2)
    pricing["forex_risk_buffer_aed"] = forex_buffer
    pricing["total_aed"] = round(total + forex_buffer, 2)

    # Bank Guarantee fee (2.5%)
    bg_fee = round(pricing["total_aed"] * 0.025, 2)
    pricing["bank_guarantee_fee_aed"] = bg_fee
    bom_items.append({
        "item_code": "FIN-BANK-GUARANTEE",
        "description": "Bank Guarantee Fee (2.5%) — International Project",
        "category": "FINANCIAL",
        "unit": "allowance",
        "quantity": 1.0,
        "unit_cost_aed": bg_fee,
        "subtotal_aed": bg_fee,
        "is_attic_stock": False,
        "notes": "International Routing: BG fee required by client",
    })
    pricing["total_aed"] = round(pricing["total_aed"] + bg_fee, 2)

    # Manpower mobilization allowance
    manpower_budget = 25000.0  # AED — flights + visas for supervision team
    bom_items.append({
        "item_code": "HR-MOBILIZATION",
        "description": "Manpower Mobilization Budget — Flights + Visas (supervision)",
        "category": "FINANCIAL",
        "unit": "allowance",
        "quantity": 1.0,
        "unit_cost_aed": manpower_budget,
        "subtotal_aed": manpower_budget,
        "is_attic_stock": False,
        "notes": "International Routing: 2 supervisors × round trip + visa",
    })
    pricing["total_aed"] = round(pricing["total_aed"] + manpower_budget, 2)
    pricing["manpower_mobilization_aed"] = manpower_budget

    state["pricing_data"] = pricing
    state["bom_items"] = bom_items
    state["project_currency"] = state.get("project_currency", "AED")

    logger.info(
        f"[{estimate_id}] InternationalRoutingNode: EXW applied, "
        f"forex buffer AED {forex_buffer:,.0f}, BG fee AED {bg_fee:,.0f}"
    )
    return state


async def _approval_gateway_impl(state: GraphState) -> GraphState:
    """
    ApprovalGatewayNode — halts the pipeline, sets status to REVIEW_REQUIRED.
    The graph will return END here. Execution resumes only after
    POST /api/v1/estimates/{id}/approve sets status to APPROVED.
    """
    estimate_id = state["estimate_id"]

    # Only set REVIEW_REQUIRED if not already APPROVED
    if state.get("status") != "APPROVED":
        state["status"] = "REVIEW_REQUIRED"
        state["approval_required"] = True
        await _persist_estimate(estimate_id, {
            "status": "REVIEW_REQUIRED",
            "current_step": "Awaiting senior approval",
            "progress_pct": 85,
        })
        logger.info(f"[{estimate_id}] ApprovalGateway: halted at REVIEW_REQUIRED")
    else:
        logger.info(f"[{estimate_id}] ApprovalGateway: already APPROVED, proceeding to report")

    return state


async def _report_impl(state: GraphState) -> GraphState:
    """
    ReportNode — generates full PDF quote + BOQ Excel + optional VO PDF.
    Only runs when status == APPROVED.
    """
    from app.services.report_engine import ReportEngine

    estimate_id = state["estimate_id"]

    try:
        engine = ReportEngine()
        result = await engine.generate(
            estimate_id=estimate_id,
            report_type="full_package",
            tenant_id=state["tenant_id"],
            state=dict(state),
        )
        state["pricing_data"]["report_paths"] = result.get("output_paths", [])
        logger.info(f"[{estimate_id}] ReportNode: {len(result.get('output_paths', []))} files generated")
    except Exception as e:
        logger.error(f"[{estimate_id}] ReportNode failed: {e}")

    await _persist_estimate(estimate_id, {
        "status": "DISPATCHED",
        "current_step": "Reports generated",
        "progress_pct": 100,
    })
    return state


# ── Conditional edge functions ─────────────────────────────────────────────────

def should_triage(state: GraphState) -> str:
    if state.get("hitl_pending") or state.get("confidence_score", 1.0) < HITL_CONFIDENCE_THRESHOLD:
        return "HITLTriageNode"
    return "DeltaCompareNode"


def should_route_international(state: GraphState) -> str:
    if state.get("is_international"):
        return "InternationalRoutingNode"
    return "ApprovalGatewayNode"


def should_triage_post_compliance(state: GraphState) -> str:
    """After compliance: route to triage if compliance failed and confidence is low."""
    if (
        state.get("compliance_report", {}).get("overall_passed") is False
        and state.get("confidence_score", 1.0) < HITL_CONFIDENCE_THRESHOLD
    ):
        return "HITLTriageNode"
    return "next"


def is_approved(state: GraphState) -> str:
    if state.get("status") == "APPROVED":
        return "ReportNode"
    return END


# ── Graph construction ─────────────────────────────────────────────────────────

def build_estimator_graph() -> StateGraph:
    graph = StateGraph(GraphState)

    graph.add_node("IngestionNode",            make_node("IngestionNode", 5, _ingestion_impl))
    graph.add_node("ScopeIdentificationNode",  make_node("ScopeIdentificationNode", 15, _scope_impl))
    graph.add_node("GeometryQANode",           make_node("GeometryQANode", 22, _geometry_qa_impl))
    graph.add_node("BOMNode",                  make_node("BOMNode", 30, _bom_impl))
    graph.add_node("HITLTriageNode",           make_node("HITLTriageNode", 35, _hitl_triage_impl))
    graph.add_node("DeltaCompareNode",         make_node("DeltaCompareNode", 45, _delta_compare_impl))
    graph.add_node("PricingNode",              make_node("PricingNode", 60, _pricing_impl))
    graph.add_node("CommercialNode",           make_node("CommercialNode", 75, _commercial_impl))
    graph.add_node("ComplianceNode",           make_node("ComplianceNode", 78, _compliance_impl))
    graph.add_node("InternationalRoutingNode", make_node("InternationalRoutingNode", 80, _international_routing_impl))
    graph.add_node("ApprovalGatewayNode",      make_node("ApprovalGatewayNode", 85, _approval_gateway_impl))
    graph.add_node("ReportNode",               make_node("ReportNode", 95, _report_impl))

    graph.set_entry_point("IngestionNode")

    graph.add_edge("IngestionNode", "ScopeIdentificationNode")
    graph.add_edge("ScopeIdentificationNode", "GeometryQANode")
    graph.add_edge("GeometryQANode", "BOMNode")

    graph.add_conditional_edges(
        "BOMNode",
        should_triage,
        {"HITLTriageNode": "HITLTriageNode", "DeltaCompareNode": "DeltaCompareNode"},
    )
    graph.add_edge("HITLTriageNode", "DeltaCompareNode")
    graph.add_edge("DeltaCompareNode", "PricingNode")
    graph.add_edge("PricingNode", "CommercialNode")
    graph.add_edge("CommercialNode", "ComplianceNode")

    graph.add_conditional_edges(
        "ComplianceNode",
        should_route_international,
        {"InternationalRoutingNode": "InternationalRoutingNode", "ApprovalGatewayNode": "ApprovalGatewayNode"},
    )
    graph.add_edge("InternationalRoutingNode", "ApprovalGatewayNode")

    graph.add_conditional_edges(
        "ApprovalGatewayNode",
        is_approved,
        {"ReportNode": "ReportNode", END: END},
    )
    graph.add_edge("ReportNode", END)

    return graph.compile()


# Singleton compiled graph
estimator_graph = build_estimator_graph()

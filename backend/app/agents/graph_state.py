"""
LangGraph State definition for the Masaad Estimator pipeline.

All graph nodes read and write this TypedDict. The state is checkpointed
to Redis after every node completes so crashed workers can resume mid-run.
"""
from typing import TypedDict, Optional, List, Literal


class GraphState(TypedDict):
    # ── Core identity ─────────────────────────────────────────────────────────
    estimate_id: str
    tenant_id: str
    user_id: str

    # ── Workflow control ──────────────────────────────────────────────────────
    current_node: str
    status: Literal["ESTIMATING", "REVIEW_REQUIRED", "APPROVED", "DISPATCHED"]
    progress_pct: int                       # 0–100

    # ── Checkpointing ─────────────────────────────────────────────────────────
    checkpoint_key: str                     # Redis key prefix
    last_completed_node: str               # Resume point after crash

    # ── HITL ──────────────────────────────────────────────────────────────────
    hitl_pending: bool
    hitl_triage_ids: List[str]             # DB IDs of open triage items
    confidence_score: float                # Most recent extraction confidence (0–1)

    # ── Input documents ───────────────────────────────────────────────────────
    drawing_paths: List[str]               # DWG/DXF file paths on disk
    spec_text: str                         # Extracted specification text
    revision_number: int                   # 0 = initial; >0 triggers DeltaCompareNode

    # ── Partial results (accumulated as nodes complete) ───────────────────────
    extracted_openings: List[dict]         # From IngestionNode
    catalog_matches: List[dict]            # From ScopeIdentificationNode
    bom_items: List[dict]                  # From BOMNode
    bom_summary: Optional[dict]            # Financial summary from BOMEngine.generate_summary()
    cutting_list: List[dict]               # From CuttingListNode
    pricing_data: dict                     # From PricingNode
    ve_suggestions: List[dict]             # From CommercialNode

    # ── Commercial / financial ────────────────────────────────────────────────
    lme_aed_per_kg: float                  # From daily Celery Beat task
    project_currency: str                  # Always "AED" — we always bill in AED
    is_international: bool                 # Triggers InternationalRoutingNode

    # ── Delta Engine ──────────────────────────────────────────────────────────
    prev_bom_snapshot: Optional[dict]      # Rev N-1 BOQ (None on first run)
    variation_order_delta: Optional[dict]  # Cost impact diff vs Rev N-1

    # ── Approval Gateway ──────────────────────────────────────────────────────
    approval_required: bool
    approved_by: Optional[str]             # user_id who signed off

    # ── 41-Point Engineering Analysis ──────────────────────────────────────
    engineering_results: Optional[dict]    # From EngineeringNode (wind/thermal/acoustic/deflection/glass)

    # ── Compliance Engineering (Phase 3B) ────────────────────────────────────
    compliance_report: Optional[dict]      # From ComplianceNode (C1+C2+C3)

    # ── Commercial Director (Phase 6B) ───────────────────────────────────────
    scurve_cashflow: Optional[dict]        # C5: S-curve schedule
    milestone_schedule: Optional[dict]    # C7: Milestone payment schedule
    yield_report: Optional[dict]          # C8: Scrap optimization
    ve_menu: Optional[dict]               # C11: Dynamic VE menu for frontend
    rfi_log: Optional[List[dict]]         # C10: Tender clarification log

    # ── Error tracking ────────────────────────────────────────────────────────
    error: Optional[str]
    error_node: Optional[str]              # Which node raised the error

"""
Agent pipeline configuration — single source of truth for node ordering,
thresholds, tool routing, and financial defaults.

Import from here in all nodes and services rather than hardcoding values.
"""
from __future__ import annotations

# ── Node execution order ───────────────────────────────────────────────────────
# Defines the canonical pipeline sequence for documentation and validation.
# Actual wiring is in estimator_graph.build_estimator_graph().
NODE_ORDER: list[str] = [
    "IngestionNode",
    "ScopeIdentificationNode",
    "GeometryQANode",
    "BOMNode",
    "HITLTriageNode",          # Conditional — inserted between BOMNode and DeltaCompareNode
    "DeltaCompareNode",
    "PricingNode",
    "CommercialNode",
    "ComplianceNode",
    "InternationalRoutingNode", # Conditional — inserted between ComplianceNode and ApprovalGatewayNode
    "ApprovalGatewayNode",
    "ReportNode",
]

# Progress percentages assigned to each node (used for frontend progress bar)
NODE_PROGRESS: dict[str, int] = {
    "IngestionNode":            5,
    "ScopeIdentificationNode":  15,
    "GeometryQANode":           22,
    "BOMNode":                  30,
    "HITLTriageNode":           35,
    "DeltaCompareNode":         45,
    "PricingNode":              60,
    "CommercialNode":           75,
    "ComplianceNode":           80,   # Widened from 78 to give clearer progress band
    "InternationalRoutingNode": 83,
    "ApprovalGatewayNode":      85,
    "ReportNode":               95,
}


# ── Confidence thresholds ──────────────────────────────────────────────────────

# Primary HITL threshold: if confidence < this after BOMNode, route to HITLTriageNode
HITL_CONFIDENCE_THRESHOLD: float = 0.90

# Post-compliance HITL threshold: if compliance fails AND confidence < this, re-triage
HITL_POST_COMPLIANCE_THRESHOLD: float = 0.85

# Geometry QA: if a die is DRAFT (not VERIFIED), cap confidence at this value
GEOMETRY_QA_DRAFT_CONFIDENCE_CAP: float = 0.85

# Minimum confidence to proceed without HITL (below this, always triage)
CONFIDENCE_FLOOR: float = 0.60

# Catalog match confidence below this → requires_hitl = True
CATALOG_MATCH_HITL_THRESHOLD: float = 0.75


# ── Node-specific timeouts (seconds) ──────────────────────────────────────────
# Used by Celery task wrappers and async timeout decorators.
NODE_TIMEOUTS: dict[str, int] = {
    "IngestionNode":            120,  # DWG parsing + sub-graph can be slow
    "ScopeIdentificationNode":  60,
    "GeometryQANode":           90,   # DB queries per referenced die
    "BOMNode":                  45,
    "HITLTriageNode":           30,
    "DeltaCompareNode":         20,
    "PricingNode":              30,
    "CommercialNode":           60,   # VE engine + S-curve generation
    "ComplianceNode":           45,
    "InternationalRoutingNode": 30,
    "ApprovalGatewayNode":      10,
    "ReportNode":               90,   # PDF + Excel generation
}


# ── LLM routing — which model handles each node ───────────────────────────────
# Vision-capable nodes use Gemini. Text-heavy nodes use Groq LLaMA 3.1 70B.
LLM_ROUTING: dict[str, str] = {
    "IngestionNode":            "groq/llama-3.1-70b-versatile",
    "ScopeIdentificationNode":  "groq/llama-3.1-70b-versatile",
    "GeometryQANode":           "gemini/gemini-1.5-flash",       # Vision: drawing review
    "BOMNode":                  "groq/llama-3.1-70b-versatile",
    "CommercialNode":           "groq/llama-3.1-70b-versatile",
    "ComplianceNode":           "groq/llama-3.1-70b-versatile",
    "ReportNode":               "gemini/gemini-1.5-flash",        # Good at structured output
}

# Tool schema mapping: which tools each node is permitted to call
NODE_ALLOWED_TOOLS: dict[str, list[str]] = {
    "IngestionNode":            ["extract_facade_systems"],
    "ScopeIdentificationNode":  ["extract_facade_systems", "match_catalog_item"],
    "GeometryQANode":           ["match_catalog_item"],
    "BOMNode":                  ["match_catalog_item", "classify_material"],
    "ComplianceNode":           ["check_compliance"],
    "CommercialNode":           ["suggest_ve_opportunity"],
}


# ── International project configuration ───────────────────────────────────────

INTERNATIONAL_CONFIG: dict[str, object] = {
    # Delivery terms — always Ex Works for international projects
    "delivery_terms": "EXW (Ex Works) — Ajman, UAE. Freight, customs, insurance EXCLUDED.",

    # Forex risk buffer applied to material costs
    "forex_buffer_pct": 0.03,          # 3% on material cost (USD/AED volatility)

    # Bank guarantee fee applied to total contract value
    "bank_guarantee_pct": 0.025,       # 2.5%

    # Manpower mobilization budget (flights + visas for supervision team)
    "mobilization_budget_aed": 25_000.0,

    # Container shipping costs (reference only — not added to estimate, EXW excludes freight)
    "container_20ft_cost_usd": 2_500.0,
    "container_40ft_cost_usd": 4_200.0,

    # Default project currency for international projects
    "default_currency": "AED",          # AED quoted; buyer handles conversion
}


# ── Financial defaults ─────────────────────────────────────────────────────────

FINANCIAL_DEFAULTS: dict[str, float] = {
    # Overhead: covers factory rent, utilities, admin, depreciation
    "overhead_pct": 0.12,              # 12%

    # Gross margin target (UAE facade industry standard for competitive tendering)
    "margin_pct": 0.18,                # 18%

    # Attic stock buffer applied to all aluminum profiles (Blind Spot Rule #4)
    "attic_stock_pct": 0.02,           # 2%

    # Retention: deducted from contractor cashflow, locked for DLP period
    "retention_pct": 0.10,             # 10%
    "retention_lock_months": 12.0,     # 12-month Defects Liability Period

    # Retention release — expressed as weeks from LOA (52 weeks build + 52 weeks DLP)
    "retention_release_week": 104.0,

    # VAT — UAE standard rate (applicable to all domestic invoices)
    "vat_pct": 0.05,                   # 5%

    # Labor burn rate: fully burdened (salary + visa + insurance + transport)
    "burn_rate_aed": 13.00,            # AED per man-hour

    # S-curve payment structure
    "advance_pct": 0.30,               # 30% advance on LOA
    "progress_pct": 0.60,              # 60% milestone-based
    # retention_pct = 0.10 (above) completes the 30/60/10 split

    # Scrap recycle discount — dead scrap sold at 60% of LME to UAE scrap buyers
    "scrap_lme_discount_pct": 0.60,

    # Provisional sums (always included per Blind Spot Rules)
    "gpr_scan_allowance_aed": 8_500.0,
    "water_test_allowance_aed": 5_500.0,
    "logistics_permit_allowance_aed": 3_500.0,
}


# ── Cutting list / CSP optimizer settings ─────────────────────────────────────

CUTTING_LIST_CONFIG: dict[str, object] = {
    # Standard aluminium bar stock length purchased from Gulf Extrusions
    "bar_length_mm": 6_000.0,

    # Offcut minimum length to be classified as USABLE_INVENTORY (Blind Spot Rule #5)
    "offcut_usable_threshold_mm": 800.0,

    # Saw kerf per cut (blade width loss)
    "kerf_mm": 3.0,

    # Aluminum density for weight calculations
    "density_kg_mm3": 2.7e-6,

    # Yield warning threshold — log WARNING if yield falls below this
    "yield_warning_pct": 80.0,
}


# ── Checkpoint configuration ───────────────────────────────────────────────────

CHECKPOINT_CONFIG: dict[str, object] = {
    # Redis key TTL for checkpoints (24 hours)
    "ttl_seconds": 86_400,

    # Key format: ckpt:{estimate_id}:{node_index:02d}:{node_name}
    # Using zero-padded index prefix ensures correct sort order on resume
    "key_format": "ckpt:{estimate_id}:{node_index:02d}:{node_name}",
}

# Map node name to its index for use in checkpoint keys
NODE_INDEX: dict[str, int] = {name: i for i, name in enumerate(NODE_ORDER)}


# ── Blind Spot Rules reference ─────────────────────────────────────────────────
# Documentation only — actual implementation is in bom_engine and commercial node

BLIND_SPOT_RULES: list[dict] = [
    {
        "id": 1,
        "name": "Retention Money",
        "description": "10% retention locked 12 months post-handover. Never include in operating cashflow.",
        "implemented_in": "CommercialNode (_commercial_impl)",
    },
    {
        "id": 2,
        "name": "Provisional Sums",
        "description": "Always include GPR scanning (AED 8,500) and water penetration testing (AED 5,500).",
        "implemented_in": "CommercialNode (_commercial_impl)",
    },
    {
        "id": 3,
        "name": "Logistics Permits",
        "description": "Auto-detect site access constraints from spec; add Municipality/RTA permit allowance.",
        "implemented_in": "CommercialNode (_commercial_impl)",
    },
    {
        "id": 4,
        "name": "Attic Stock",
        "description": "2% buffer on all aluminum profiles for breakage/offcuts during installation.",
        "implemented_in": "BOMEngine (bom_engine.py)",
    },
    {
        "id": 5,
        "name": "Usable Inventory",
        "description": "Cutting list offcuts > 800mm returned to ERP stock rather than scrapped.",
        "implemented_in": "CommercialNode + C8 optimize_yield_and_scrap()",
    },
]

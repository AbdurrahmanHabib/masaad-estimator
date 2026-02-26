"""
Standardized WebSocket / SSE payload models.

All server-sent events from /api/ingestion/progress/{estimate_id}
MUST serialize AgentProgressPayload so the frontend Split-Pane Workspace
can render live state without branching on payload shape.
"""
from typing import Optional
from pydantic import BaseModel


class AgentProgressPayload(BaseModel):
    """Strict contract for every SSE event emitted by the pipeline."""
    estimate_id: str
    current_agent: str              # LangGraph node name, e.g. "BOMNode"
    status_message: str             # Human-readable, e.g. "Extracting die 4540-F..."
    confidence_score: float = 1.0   # 0.0–1.0; <0.90 indicates HITL trigger
    progress_pct: int = 0           # 0–100
    partial_results: dict = {}      # Live partial data (BOQ rows, pricing, etc.)
    hitl_required: bool = False
    hitl_triage_id: Optional[str] = None  # DB triage_queue.id if HITL triggered
    error: Optional[str] = None

    model_config = {"json_schema_extra": {
        "example": {
            "estimate_id": "abc-123",
            "current_agent": "BOMNode",
            "status_message": "Computing BOM for 47 openings...",
            "confidence_score": 0.97,
            "progress_pct": 42,
            "partial_results": {"bom_rows": 12},
            "hitl_required": False,
        }
    }}

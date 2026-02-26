"""
Ingestion Graph — Stage 1 of 4.
Validates inputs, identifies scope, extracts opening schedule, runs spec RFIs.
Nodes: validate_inputs → extract_spec_text → scope_identification → opening_schedule → rfi_spec_analysis → persist_project
"""
import logging
import json
from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, END

logger = logging.getLogger("masaad-ingestion-graph")


class IngestionState(TypedDict):
    estimate_id: str
    db_url: str
    dwg_path: Optional[str]
    spec_path: Optional[str]
    project_data: Dict[str, Any]
    dwg_extraction: Dict[str, Any]
    spec_text: str
    project_scope: Dict[str, Any]
    opening_schedule: Dict[str, Any]
    rfi_flags: List[Dict[str, Any]]
    reasoning_log: List[str]
    error: Optional[str]


# ─── Helpers ──────────────────────────────────────────────────────────────────

async def _update_estimate(db_url: str, estimate_id: str, updates: dict):
    """Write partial progress update to the Estimate row."""
    try:
        import asyncpg
        conn = await asyncpg.connect(db_url)
        try:
            set_clauses = []
            values = []
            i = 1
            for col, val in updates.items():
                set_clauses.append(f"{col} = ${i}")
                values.append(json.dumps(val) if isinstance(val, (dict, list)) else val)
                i += 1
            values.append(estimate_id)
            sql = f"UPDATE estimates SET {', '.join(set_clauses)} WHERE id = ${i}::uuid"
            await conn.execute(sql, *values)
        finally:
            await conn.close()
    except Exception as exc:
        logger.warning(f"DB update failed for {estimate_id}: {exc}")


# ─── Nodes ────────────────────────────────────────────────────────────────────

async def validate_inputs(state: IngestionState) -> IngestionState:
    """Parse DWG/DXF file and extract raw geometry."""
    eid = state["estimate_id"]
    log = list(state.get("reasoning_log", []))
    log.append("⚙️ Validating input files and parsing DWG geometry...")

    await _update_estimate(state["db_url"], eid, {
        "status": "Processing",
        "current_step": "Parsing DWG geometry",
        "progress_pct": 5,
        "reasoning_log": log,
    })

    dwg_path = state.get("dwg_path")
    dwg_extraction: Dict[str, Any] = {"blocks": [], "layers": [], "entities": []}

    if dwg_path and dwg_path.endswith((".dwg", ".dxf")):
        try:
            from app.services.dwg_parser import DWGParserService
            svc = DWGParserService()
            dwg_extraction = svc.parse_file(dwg_path)
            n_blocks = len(dwg_extraction.get("blocks", []))
            n_panels = len(dwg_extraction.get("panels", []))
            n_layouts = len(dwg_extraction.get("layouts", []))
            n_warnings = len(dwg_extraction.get("warnings", []))
            log.append(
                f"DWG parsed: {n_layouts} layouts, {n_panels} panels, "
                f"{n_blocks} blocks extracted"
                + (f" ({n_warnings} warnings)" if n_warnings else "")
            )
        except Exception as exc:
            log.append(f"DWG parse warning: {exc} -- continuing with empty geometry")
    else:
        log.append("No DWG provided -- scope will be derived from spec text only")

    return {**state, "dwg_extraction": dwg_extraction, "reasoning_log": log}


async def extract_spec_text(state: IngestionState) -> IngestionState:
    """Extract text from specification PDF."""
    eid = state["estimate_id"]
    log = list(state.get("reasoning_log", []))
    log.append("⚙️ Extracting specification text...")

    await _update_estimate(state["db_url"], eid, {
        "current_step": "Reading specification document",
        "progress_pct": 12,
        "reasoning_log": log,
    })

    spec_path = state.get("spec_path")
    spec_text = ""

    if spec_path:
        try:
            import pdfplumber
            with pdfplumber.open(spec_path) as pdf:
                pages = [p.extract_text() or "" for p in pdf.pages]
                spec_text = "\n\n".join(pages)
            log.append(f"✅ Spec extracted: {len(spec_text):,} characters from {len(pages)} pages")

            if not spec_text.strip():
                # Try vision extraction for image-only PDFs
                log.append("ℹ️ No digital text found — PDF may be image-only. Using Groq Vision...")
                try:
                    from app.services.catalog_pdf_parser import _pdf_to_images
                    from app.services.llm_client import complete_with_vision
                    import base64
                    images = _pdf_to_images(spec_path, max_pages=5)
                    if images:
                        prompt = ("You are a Senior Estimator reviewing a UAE facade project specification or rendering. "
                                  "Describe all facade systems visible, materials, finishes, and any technical requirements mentioned. "
                                  "Be detailed and specific.")
                        spec_text = await complete_with_vision(images, prompt)
                        log.append(f"✅ Vision extraction: {len(spec_text):,} characters from images")
                except Exception as ve:
                    log.append(f"⚠️ Vision extraction failed: {ve}")
        except Exception as exc:
            log.append(f"⚠️ Spec text extraction warning: {exc}")

    return {**state, "spec_text": spec_text, "reasoning_log": log}


async def scope_identification(state: IngestionState) -> IngestionState:
    """Identify all facade systems present in the project."""
    eid = state["estimate_id"]
    log = list(state.get("reasoning_log", []))
    log.append("⚙️ Identifying facade scope — analysing DWG layers and spec text...")

    await _update_estimate(state["db_url"], eid, {
        "current_step": "Identifying facade scope",
        "progress_pct": 22,
        "reasoning_log": log,
    })

    try:
        from app.services.scope_engine import ScopeIdentificationEngine
        engine = ScopeIdentificationEngine()
        scope_result = engine.identify_project_scope(
            dwg_extraction=state["dwg_extraction"],
            spec_text=state["spec_text"],
        )
        scope_dict = scope_result.to_dict() if hasattr(scope_result, "to_dict") else {}
        systems_found = len(scope_dict.get("systems_identified", []))
        total_sqm = scope_dict.get("scope_summary", {}).get("total_facade_sqm", 0)
        log.append(f"✅ Scope identified: {systems_found} facade systems, ~{total_sqm:.0f} SQM total")

        # Log each system found
        for sys_info in scope_dict.get("systems_identified", []):
            log.append(f"   • {sys_info.get('system_type', '?')} — {sys_info.get('total_sqm', 0):.0f} SQM")
    except Exception as exc:
        logger.error(f"Scope identification error: {exc}")
        scope_dict = {"systems_identified": [], "scope_summary": {}, "error": str(exc)}
        log.append(f"⚠️ Scope identification warning: {exc}")

    return {**state, "project_scope": scope_dict, "reasoning_log": log}


async def extract_opening_schedule(state: IngestionState) -> IngestionState:
    """Extract all openings from the DWG with dimensions, types, and locations."""
    eid = state["estimate_id"]
    log = list(state.get("reasoning_log", []))
    log.append("⚙️ Extracting opening schedule from DWG blocks...")

    await _update_estimate(state["db_url"], eid, {
        "current_step": "Extracting opening schedule",
        "progress_pct": 35,
        "reasoning_log": log,
    })

    try:
        from app.services.opening_schedule_engine import OpeningScheduleEngine
        engine = OpeningScheduleEngine()

        # Build scope result mock for system mapping
        scope = state.get("project_scope", {})
        systems_info = scope.get("systems_identified", [])

        # Create a minimal scope_result object that OpeningScheduleEngine can use
        class _ScopeProxy:
            def __init__(self, systems):
                self.systems = systems
        scope_proxy = _ScopeProxy(systems_info)

        schedule = engine.extract_opening_schedule(
            dwg_extraction=state["dwg_extraction"],
            scope_result=None,  # engine handles None gracefully
            spec_text=state["spec_text"],
        )
        schedule_dict = engine.to_dict(schedule)
        total = schedule_dict.get("summary", {}).get("total_openings", 0)
        area = schedule_dict.get("summary", {}).get("total_gross_sqm", 0)
        log.append(f"✅ Opening schedule: {total} openings, {area:.1f} SQM gross area")
    except Exception as exc:
        logger.error(f"Opening schedule error: {exc}")
        schedule_dict = {"schedule": [], "summary": {}, "rfi_flags": [], "error": str(exc)}
        log.append(f"⚠️ Opening schedule warning: {exc}")

    return {**state, "opening_schedule": schedule_dict, "reasoning_log": log}


async def rfi_spec_analysis(state: IngestionState) -> IngestionState:
    """Run automated RFI generation on spec text and project data."""
    eid = state["estimate_id"]
    log = list(state.get("reasoning_log", []))
    log.append("⚙️ Running risk analysis and generating RFI register...")

    await _update_estimate(state["db_url"], eid, {
        "current_step": "Generating RFI register",
        "progress_pct": 45,
        "reasoning_log": log,
    })

    rfi_flags: List[Dict] = []
    try:
        from app.services.risk_engine import RiskFlaggingEngine
        engine = RiskFlaggingEngine()
        rfis = engine.analyze_project_risks(
            opening_schedule=state["opening_schedule"],
            spec_text=state["spec_text"],
        )
        rfi_flags = engine.to_dict(rfis)
        critical = sum(1 for r in rfi_flags if r.get("severity") == "CRITICAL")
        high = sum(1 for r in rfi_flags if r.get("severity") == "HIGH")
        log.append(f"✅ RFI register: {len(rfi_flags)} items "
                   f"({critical} CRITICAL, {high} HIGH)")

        # Also include RFIs from opening schedule
        opening_rfis = state["opening_schedule"].get("rfi_flags", [])
        rfi_flags.extend(opening_rfis)
    except Exception as exc:
        logger.error(f"RFI analysis error: {exc}")
        log.append(f"⚠️ RFI analysis warning: {exc}")

    return {**state, "rfi_flags": rfi_flags, "reasoning_log": log}


async def persist_project(state: IngestionState) -> IngestionState:
    """Persist all ingestion outputs to the Estimate record."""
    eid = state["estimate_id"]
    log = list(state.get("reasoning_log", []))
    log.append("💾 Saving ingestion results to database...")

    await _update_estimate(state["db_url"], eid, {
        "current_step": "Ingestion complete — starting BOM",
        "progress_pct": 50,
        "status": "Processing",
        "project_scope_json": state.get("project_scope", {}),
        "opening_schedule_json": state.get("opening_schedule", {}),
        "rfi_register_json": state.get("rfi_flags", []),
        "reasoning_log": log,
    })

    log.append("✅ Ingestion stage complete.")
    return {**state, "reasoning_log": log}


# ─── Build graph ──────────────────────────────────────────────────────────────

def build_ingestion_graph():
    workflow = StateGraph(IngestionState)
    workflow.add_node("validate_inputs", validate_inputs)
    workflow.add_node("extract_spec_text", extract_spec_text)
    workflow.add_node("scope_identification", scope_identification)
    workflow.add_node("opening_schedule", extract_opening_schedule)
    workflow.add_node("rfi_spec_analysis", rfi_spec_analysis)
    workflow.add_node("persist_project", persist_project)

    workflow.set_entry_point("validate_inputs")
    workflow.add_edge("validate_inputs", "extract_spec_text")
    workflow.add_edge("extract_spec_text", "scope_identification")
    workflow.add_edge("scope_identification", "opening_schedule")
    workflow.add_edge("opening_schedule", "rfi_spec_analysis")
    workflow.add_edge("rfi_spec_analysis", "persist_project")
    workflow.add_edge("persist_project", END)
    return workflow.compile()


ingestion_app = build_ingestion_graph()

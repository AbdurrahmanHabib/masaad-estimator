"""
Structured Tool Schemas for the Masaad Estimator LLM Pipeline.

These Pydantic models define the input/output contract for every LLM tool call.
They are used in two ways:
  1. As litellm/OpenAI function-calling schemas (via .model_json_schema())
  2. As validation models for LLM response parsing

Usage:
    from app.agents.tool_schemas import ExtractFacadeSystemsTool, MatchCatalogItemTool

    # Build the tools list for litellm
    tools = [
        {
            "type": "function",
            "function": {
                "name": "extract_facade_systems",
                "description": ExtractFacadeSystemsTool.__doc__,
                "parameters": ExtractFacadeSystemsTool.Input.model_json_schema(),
            }
        }
    ]

    # Validate LLM output
    output = ExtractFacadeSystemsTool.Output.model_validate_json(llm_response)
"""

from __future__ import annotations

from typing import List, Literal, Optional
from pydantic import BaseModel, Field


# ── Tool 1: Extract Facade Systems ────────────────────────────────────────────

class FacadeSystem(BaseModel):
    """A single identified facade system from the drawing."""
    system_type: Literal[
        "CURTAIN_WALL",
        "WINDOW",
        "DOOR",
        "ACP_CLADDING",
        "SHOPFRONT",
        "SKYLIGHT",
        "LOUVRE",
        "HANDRAIL",
        "OTHER",
    ] = Field(..., description="Type of facade or glazing system")
    quantity: float = Field(..., ge=0, description="Number of units or total area")
    unit: Literal["sqm", "lm", "nr", "set"] = Field(
        ..., description="Unit of measure: sqm=square metres, lm=linear metres, nr=number, set=complete set"
    )
    location: str = Field(
        ..., description="Where on the building (e.g., 'North Elevation, Level 3-8')"
    )
    width_mm: Optional[float] = Field(
        None, ge=0, description="Typical unit width in millimetres (for window/door systems)"
    )
    height_mm: Optional[float] = Field(
        None, ge=0, description="Typical unit height in millimetres (for window/door systems)"
    )
    notes: Optional[str] = Field(
        None, description="Any special requirements, finishes, or constraints noted in drawing"
    )


class ExtractFacadeSystemsTool(BaseModel):
    """
    Extract facade system types and quantities from an architectural drawing description.
    Identifies all aluminium & glass systems visible on the elevation with quantities and locations.
    """

    class Input(BaseModel):
        drawing_description: str = Field(
            ...,
            description="Text description of the architectural drawing, including any OCR text, layer names, dimension annotations, and block names extracted from the DWG/DXF file",
        )
        elevation_name: str = Field(
            ...,
            description="Which building elevation this drawing shows (e.g., 'North Elevation', 'South Elevation', 'Section A-A')",
        )
        building_height_m: float = Field(
            ...,
            ge=0,
            le=1000,
            description="Total building height in metres",
        )
        floor_count: Optional[int] = Field(
            None,
            ge=1,
            description="Number of floors if known from drawing",
        )
        project_type: Optional[str] = Field(
            None,
            description="Project type if known (e.g., 'commercial office', 'residential', 'hotel', 'retail')",
        )

    class Output(BaseModel):
        systems: List[FacadeSystem] = Field(
            ...,
            description="List of all identified facade systems with quantities",
        )
        confidence: float = Field(
            ...,
            ge=0,
            le=1,
            description="Confidence score for the extraction (0=no data, 1=complete certainty). Use < 0.85 when drawing quality is poor or annotations are ambiguous.",
        )
        rfi_flags: List[str] = Field(
            default_factory=list,
            description="List of ambiguities or missing data that require RFI clarification from the client",
        )
        total_glazed_area_sqm: Optional[float] = Field(
            None,
            description="Total estimated glazed facade area in sqm if calculable",
        )


# ── Tool 2: Match Catalog Item ────────────────────────────────────────────────

class MatchCatalogItemTool(BaseModel):
    """
    Match a textual description of an aluminium profile or glass unit to a specific
    item code in the Gulf Extrusions / Elite Aluminium catalog. Returns the best
    matching item code and confidence score.
    """

    class Input(BaseModel):
        description: str = Field(
            ...,
            description="Free-text description of the profile, unit, or component to match (e.g., 'thermally broken casement window frame 65mm system')",
        )
        system_type: Literal[
            "CURTAIN_WALL",
            "WINDOW",
            "DOOR",
            "ACP_CLADDING",
            "SHOPFRONT",
            "SKYLIGHT",
            "LOUVRE",
            "HANDRAIL",
            "HARDWARE",
            "GLASS",
            "OTHER",
        ] = Field(
            ...,
            description="Broad category of the component",
        )
        spec_requirements: Optional[str] = Field(
            None,
            description="Performance requirements from spec (e.g., 'thermal break required', 'Uf ≤ 1.6 W/m²K', 'AAMA 2605 powder coat')",
        )
        series_hint: Optional[str] = Field(
            None,
            description="Known or suspected system series from drawing (e.g., 'GE-65', 'Elite W50', 'CW75TB')",
        )

    class Output(BaseModel):
        item_code: str = Field(
            ...,
            description="Best matching catalog item code (e.g., 'GE-CW-75TB-MULLION-VERT')",
        )
        description: str = Field(
            ...,
            description="Full catalog item description",
        )
        system_series: str = Field(
            ...,
            description="System series name (e.g., 'CW75TB', 'W50', 'D65')",
        )
        confidence: float = Field(
            ...,
            ge=0,
            le=1,
            description="Match confidence. < 0.75 = flag for HITL review",
        )
        alternatives: List[str] = Field(
            default_factory=list,
            description="Up to 3 alternative item codes if confidence < 0.90",
        )
        match_rationale: str = Field(
            ...,
            description="Brief explanation of why this item code was selected",
        )
        requires_hitl: bool = Field(
            ...,
            description="True if confidence < 0.75 or if multiple equally valid matches exist",
        )


# ── Tool 3: Classify Material ─────────────────────────────────────────────────

class ClassifyMaterialTool(BaseModel):
    """
    Classify a material type from a PDF catalog page or specification text.
    Used by catalog_pdf_parser to route pages to the correct parsing pipeline
    (aluminium extrusion, glass, ACP, hardware, sealant/silicone).
    """

    class Input(BaseModel):
        page_text: str = Field(
            ...,
            description="Raw text extracted from a PDF catalog page (may include OCR noise)",
        )
        page_number: int = Field(
            ...,
            ge=1,
            description="Page number within the PDF for reference",
        )
        document_title: Optional[str] = Field(
            None,
            description="Title of the source document if known",
        )

    class Output(BaseModel):
        material_type: Literal[
            "ALUMINUM_EXTRUSION",
            "GLASS",
            "ACP_PANEL",
            "HARDWARE",
            "SILICONE_SEALANT",
            "STRUCTURAL_SILICONE",
            "THERMAL_BREAK",
            "FASTENER",
            "COMPOSITE_PANEL",
            "OTHER",
            "COVER_PAGE",
            "TABLE_OF_CONTENTS",
            "NOT_APPLICABLE",
        ] = Field(
            ...,
            description="Classified material type for this page",
        )
        confidence: float = Field(
            ...,
            ge=0,
            le=1,
            description="Classification confidence",
        )
        key_identifiers: List[str] = Field(
            default_factory=list,
            description="Key words or phrases from the page that drove the classification decision",
        )
        skip_page: bool = Field(
            ...,
            description="True if this page should be skipped (cover, ToC, blank, non-catalog content)",
        )
        sub_classification: Optional[str] = Field(
            None,
            description="More specific sub-type if applicable (e.g., 'THERMALLY_BROKEN' for aluminium, 'DGU' for glass)",
        )


# ── Tool 4: Check Compliance ──────────────────────────────────────────────────

class ComplianceCheckResult(BaseModel):
    """Result of a single compliance code check."""
    code_reference: str = Field(
        ...,
        description="Standard code referenced (e.g., 'BS 6399-2:1997 Cl 4.1', 'ASHRAE 90.1-2019 Table 5.5')",
    )
    check_description: str = Field(
        ...,
        description="What was checked (e.g., 'Wind load deflection limit L/175 at mid-span')",
    )
    result: Literal["PASS", "FAIL", "MARGINAL", "DATA_INSUFFICIENT"] = Field(
        ...,
        description="Compliance result",
    )
    actual_value: Optional[str] = Field(
        None,
        description="Actual computed or stated value (e.g., 'U-value = 1.8 W/m²K')",
    )
    required_value: Optional[str] = Field(
        None,
        description="Code-required value (e.g., 'U-value ≤ 2.0 W/m²K per Dubai GBR')",
    )
    recommendation: Optional[str] = Field(
        None,
        description="Corrective action if FAIL or MARGINAL",
    )
    rfi_required: bool = Field(
        ...,
        description="True if an RFI must be raised to the structural engineer or client",
    )


class CheckComplianceTool(BaseModel):
    """
    Check a facade system specification against UAE and international building codes.
    Covers: structural (BS 6399-2 / ASCE 7), thermal/acoustic (Dubai GBR / ASHRAE 90.1),
    and fire (UAE Civil Defence Code).
    """

    class Input(BaseModel):
        system_description: str = Field(
            ...,
            description="Description of the facade system being checked (e.g., 'CW75TB curtain wall, 6+12+6 DGU, thermal break, mullion span 3.6m')",
        )
        building_type: Literal[
            "commercial_office",
            "residential_high_rise",
            "hotel",
            "hospital",
            "retail",
            "car_park",
            "industrial",
        ] = Field(
            ...,
            description="Building occupancy type — affects fire rating and thermal requirements",
        )
        building_height_m: float = Field(
            ...,
            ge=0,
            description="Building height in metres — affects wind load zone and fire rating",
        )
        wind_speed_ms: Optional[float] = Field(
            None,
            description="Design wind speed in m/s (default Dubai = 45 m/s if not provided)",
        )
        u_value_w_m2k: Optional[float] = Field(
            None,
            description="Facade thermal transmittance U-value in W/m²K",
        )
        fire_rating_minutes: Optional[int] = Field(
            None,
            description="Specified fire rating in minutes (e.g., 60, 90, 120)",
        )
        mullion_span_mm: Optional[float] = Field(
            None,
            description="Maximum unsupported mullion span in millimetres",
        )
        glazing_makeup: Optional[str] = Field(
            None,
            description="Glass unit specification (e.g., '6mm tempered + 16mm Argon + 6mm low-e')",
        )

    class Output(BaseModel):
        overall_result: Literal["PASS", "FAIL", "MARGINAL", "INSUFFICIENT_DATA"] = Field(
            ...,
            description="Overall compliance verdict across all checks",
        )
        checks: List[ComplianceCheckResult] = Field(
            ...,
            description="Individual compliance check results",
        )
        critical_failures: List[str] = Field(
            default_factory=list,
            description="List of FAIL checks that must be resolved before project can proceed",
        )
        rfi_items: List[str] = Field(
            default_factory=list,
            description="RFI texts that must be raised to relevant parties",
        )
        summary: str = Field(
            ...,
            description="Plain English compliance summary for the estimate file",
        )


# ── Tool 5: Suggest VE Opportunity ────────────────────────────────────────────

class SuggestVEOpportunityTool(BaseModel):
    """
    Suggest value engineering alternatives for a BOM line item.
    Evaluates cost savings, technical risk, and specification compliance impact
    of substituting or eliminating a facade component.
    """

    class Input(BaseModel):
        item_code: str = Field(
            ...,
            description="Current BOM item code to find alternatives for",
        )
        item_description: str = Field(
            ...,
            description="Full description of the current item",
        )
        category: Literal[
            "ALUMINUM_EXTRUSION",
            "GLASS",
            "ACP_PANEL",
            "HARDWARE",
            "SILICONE_SEALANT",
            "LABOR",
            "OTHER",
        ] = Field(
            ...,
            description="Material category",
        )
        current_unit_cost_aed: float = Field(
            ...,
            ge=0,
            description="Current unit cost in AED",
        )
        quantity: float = Field(
            ...,
            ge=0,
            description="Quantity used in this estimate",
        )
        unit: str = Field(
            ...,
            description="Unit of measure (sqm, lm, kg, nr)",
        )
        spec_requirement: Optional[str] = Field(
            None,
            description="Specification requirement this item must meet (constrains substitution options)",
        )
        alternatives: List[dict] = Field(
            default_factory=list,
            description="Known alternative items from catalog: [{item_code, description, unit_cost_aed}]",
        )
        lme_aed_per_kg: Optional[float] = Field(
            None,
            description="Current LME aluminium price in AED/kg (used for aluminium-specific calculations)",
        )

    class Output(BaseModel):
        has_opportunity: bool = Field(
            ...,
            description="True if a meaningful VE saving is available",
        )
        saving_aed: float = Field(
            ...,
            ge=0,
            description="Estimated saving in AED if VE is accepted",
        )
        saving_pct: float = Field(
            ...,
            ge=0,
            le=100,
            description="Saving as a percentage of the original line item cost",
        )
        substitute_item_code: Optional[str] = Field(
            None,
            description="Recommended substitute item code from catalog",
        )
        substitute_description: Optional[str] = Field(
            None,
            description="Description of the substitute item",
        )
        rationale: str = Field(
            ...,
            description="Why this VE opportunity exists and how the saving is achieved",
        )
        technical_impact: str = Field(
            ...,
            description="Any technical performance impact of accepting this VE (e.g., 'No impact', 'Reduces Uf by 0.1 W/m²K — still within spec')",
        )
        risk_level: Literal["LOW", "MEDIUM", "HIGH"] = Field(
            ...,
            description="Risk level of accepting this VE: LOW=no spec risk, MEDIUM=needs engineer review, HIGH=may require spec variance",
        )
        spec_compliance_maintained: bool = Field(
            ...,
            description="True if the substitute still meets the specification requirement",
        )
        requires_client_approval: bool = Field(
            ...,
            description="True if the substitute requires written client consent before ordering",
        )


# ── Tool registry — maps tool names to schema classes ─────────────────────────

TOOL_REGISTRY: dict[str, type] = {
    "extract_facade_systems": ExtractFacadeSystemsTool,
    "match_catalog_item": MatchCatalogItemTool,
    "classify_material": ClassifyMaterialTool,
    "check_compliance": CheckComplianceTool,
    "suggest_ve_opportunity": SuggestVEOpportunityTool,
}


def get_litellm_tools(tool_names: list[str] | None = None) -> list[dict]:
    """
    Build a list of tool dicts in OpenAI function-calling format.
    Pass to litellm.acompletion(tools=...) alongside messages.

    Args:
        tool_names: Subset of TOOL_REGISTRY keys to include.
                    If None, all tools are included.

    Returns:
        List of dicts compatible with OpenAI/litellm tool-calling format.

    Example:
        tools = get_litellm_tools(["extract_facade_systems", "match_catalog_item"])
        response = await litellm.acompletion(
            model="groq/llama-3.1-70b-versatile",
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )
    """
    names = tool_names if tool_names is not None else list(TOOL_REGISTRY.keys())
    result = []
    for name in names:
        schema_class = TOOL_REGISTRY.get(name)
        if schema_class is None:
            continue
        # Grab the docstring as function description
        description = (schema_class.__doc__ or "").strip()
        # Get the Input schema
        input_cls = getattr(schema_class, "Input", None)
        if input_cls is None:
            continue
        result.append({
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": input_cls.model_json_schema(),
            },
        })
    return result


def parse_tool_output(tool_name: str, raw_json: str | dict) -> BaseModel:
    """
    Parse and validate LLM tool output against the Output schema.

    Args:
        tool_name: Key in TOOL_REGISTRY
        raw_json:  JSON string or dict from LLM tool call result

    Returns:
        Validated Output Pydantic model

    Raises:
        KeyError: If tool_name not in registry
        ValidationError: If LLM output does not match Output schema
    """
    import json as _json

    schema_class = TOOL_REGISTRY[tool_name]
    output_cls = getattr(schema_class, "Output", None)
    if output_cls is None:
        raise ValueError(f"Tool '{tool_name}' has no Output schema defined")

    if isinstance(raw_json, str):
        data = _json.loads(raw_json)
    else:
        data = raw_json

    return output_cls.model_validate(data)

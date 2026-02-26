"""Risk flagging engine — auto-generates RFIs from project data."""
import re
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("masaad-risk")


@dataclass
class RFIItem:
    rfi_id: str
    category: str  # STRUCTURAL | FIRE_COMPLIANCE | SPECIFICATION | CATALOG_MISMATCH | THERMAL | ACOUSTIC | MISSING_DATA
    severity: str  # CRITICAL | HIGH | MEDIUM | LOW
    description: str
    affected_element: str = ""
    recommendation: str = ""
    requires_client_approval: bool = False
    auto_resolvable: bool = False


class RiskFlaggingEngine:
    """Generates RFI register from project data using rule-based + LLM analysis."""

    # Wind pressure thresholds for UAE
    UAE_STANDARD_WIND_KPA = 2.0
    HIGH_WIND_KPA = 2.5

    def __init__(self):
        self.rfi_counter = 0

    def analyze_project_risks(
        self,
        opening_schedule: dict,
        structural_results: list = None,
        spec_text: str = "",
        catalog_items: list = None,
        bom_data: dict = None,
    ) -> list:
        """
        Run all risk checks and return RFI list.
        """
        rfis = []
        self.rfi_counter = 0

        # Rule-based checks (deterministic)
        rfis.extend(self._check_structural(structural_results or []))
        rfis.extend(self._check_specification(spec_text))
        rfis.extend(self._check_catalog_coverage(opening_schedule, catalog_items or []))
        rfis.extend(self._check_glass_handling(opening_schedule))
        rfis.extend(self._check_openings(opening_schedule))

        # LLM-based analysis for free-text risks
        if spec_text:
            rfis.extend(self._analyze_spec_with_llm(spec_text))

        logger.info(f"Risk analysis: {len(rfis)} RFIs generated")
        return rfis

    def _next_rfi(self) -> str:
        self.rfi_counter += 1
        return f"RFI-{self.rfi_counter:03d}"

    # ─── Structural checks ────────────────────────────────────────────────

    def _check_structural(self, structural_results: list) -> list:
        rfis = []
        for result in structural_results:
            # Ixx check
            ixx_provided = result.get("ixx_cm4_provided", 0)
            ixx_required = result.get("ixx_cm4_required", 0)
            profile_id = result.get("profile_id", "Unknown")
            span_m = result.get("span_m", 0)

            if ixx_provided and ixx_required:
                ratio = ixx_provided / ixx_required if ixx_required > 0 else 999
                if ratio < 1.05:
                    rfis.append(RFIItem(
                        rfi_id=self._next_rfi(),
                        category="STRUCTURAL",
                        severity="CRITICAL",
                        description=f"Profile {profile_id}: Ixx provided ({ixx_provided:.1f} cm⁴) is BELOW required ({ixx_required:.1f} cm⁴) by {(1-ratio)*100:.1f}%",
                        affected_element=profile_id,
                        recommendation=f"Upgrade to next profile in series with Ixx ≥ {ixx_required*1.1:.1f} cm⁴ (10% safety margin)",
                        requires_client_approval=False,
                        auto_resolvable=True,
                    ))

            # Span check
            if span_m > 4.0:
                rfis.append(RFIItem(
                    rfi_id=self._next_rfi(),
                    category="STRUCTURAL",
                    severity="HIGH",
                    description=f"Profile {profile_id}: Span {span_m:.1f}m exceeds 4.0m unsupported limit",
                    affected_element=profile_id,
                    recommendation="Add intermediate bracket or upgrade profile. Provide structural calculation to consultant.",
                    requires_client_approval=True,
                ))

            # Wind pressure
            wind_kpa = result.get("design_wind_kpa", 0)
            if wind_kpa > self.HIGH_WIND_KPA:
                rfis.append(RFIItem(
                    rfi_id=self._next_rfi(),
                    category="STRUCTURAL",
                    severity="HIGH",
                    description=f"Unusual wind pressure {wind_kpa:.2f} kPa (UAE standard ~{self.UAE_STANDARD_WIND_KPA} kPa)",
                    affected_element=f"All facades — {profile_id} zone",
                    recommendation="Verify wind load source. Obtain wind study if not available. All profiles must be rechecked.",
                    requires_client_approval=True,
                ))

        return rfis

    # ─── Specification checks ─────────────────────────────────────────────

    def _check_specification(self, spec_text: str) -> list:
        rfis = []
        if not spec_text:
            rfis.append(RFIItem(
                rfi_id=self._next_rfi(),
                category="SPECIFICATION",
                severity="HIGH",
                description="No specification document provided — pricing based on drawings only",
                affected_element="All systems",
                recommendation="Request project specification from consultant before submitting bid",
                requires_client_approval=True,
            ))
            return rfis

        spec_lower = spec_text.lower()

        # Fire rating check
        fire_keywords = ["fire resistance", "fire rating", "fr ", "fire-rated", "2hr", "1hr", "60 minutes", "120 minutes"]
        if not any(kw in spec_lower for kw in fire_keywords):
            rfis.append(RFIItem(
                rfi_id=self._next_rfi(),
                category="FIRE_COMPLIANCE",
                severity="HIGH",
                description="No fire resistance rating specified in project documents",
                affected_element="All facade systems",
                recommendation="UAE Civil Defence requires fire compartmentation at floor levels. Confirm if fire-rated curtain wall is required.",
                requires_client_approval=True,
            ))

        # Thermal/U-value check for curtain wall
        cw_keywords = ["curtain wall", "cw-50", "curtain-wall"]
        thermal_keywords = ["u-value", "u value", "thermal", "k-value", "heat transfer", "energy"]
        if any(kw in spec_lower for kw in cw_keywords):
            if not any(kw in spec_lower for kw in thermal_keywords):
                rfis.append(RFIItem(
                    rfi_id=self._next_rfi(),
                    category="THERMAL",
                    severity="MEDIUM",
                    description="Curtain wall specified but no thermal performance (U-value) requirement stated",
                    affected_element="Curtain Wall system",
                    recommendation="Confirm if thermal break profiles are required. Dubai Green Building Regulations require U ≤ 2.6 W/m²K.",
                ))

        # Hardware brand check
        hardware_generic = ["hardware to be provided", "hardware as specified", "hardware by others"]
        if any(kw in spec_lower for kw in hardware_generic):
            rfis.append(RFIItem(
                rfi_id=self._next_rfi(),
                category="SPECIFICATION",
                severity="MEDIUM",
                description="Hardware specification is generic — no brand or model specified",
                affected_element="Hardware for all openings",
                recommendation="Request hardware schedule from consultant showing brand, model, finish, and test certification.",
            ))

        # Finish specification
        finish_keywords = ["powder coat", "pvdf", "anodize", "anodised", "polyester", "colour", "ral"]
        if not any(kw in spec_lower for kw in finish_keywords):
            rfis.append(RFIItem(
                rfi_id=self._next_rfi(),
                category="SPECIFICATION",
                severity="LOW",
                description="Aluminum finish not specified — assumed standard powder coat silver",
                affected_element="All aluminum profiles",
                recommendation="Confirm finish type (powder coat/PVDF/anodize) and colour reference before ordering.",
            ))

        # Water tightness class
        water_keywords = ["water tightness", "watertight", "astm e331", "e331", "bs en 12208", "permeability"]
        if not any(kw in spec_lower for kw in water_keywords):
            rfis.append(RFIItem(
                rfi_id=self._next_rfi(),
                category="SPECIFICATION",
                severity="MEDIUM",
                description="No water tightness class specified",
                affected_element="All glazed systems",
                recommendation="Confirm required water tightness class (ASTM E331 or equivalent). Standard Dubai: 300 Pa test pressure.",
            ))

        # ACP specification check
        acp_keywords = ["acp", "aluminum composite", "aluminium composite", "cladding"]
        if any(kw in spec_lower for kw in acp_keywords):
            thickness_in_spec = re.search(r'(\d)mm\s+(?:acp|aluminum composite|cladding)', spec_lower)
            if not thickness_in_spec:
                rfis.append(RFIItem(
                    rfi_id=self._next_rfi(),
                    category="SPECIFICATION",
                    severity="HIGH",
                    description="ACP system specified but thickness not stated",
                    affected_element="ACP Cladding",
                    recommendation="Confirm ACP thickness (3mm or 4mm) and core type (polyester or fire-retardant FR). UAE requires FR core for buildings >15m.",
                ))

        return rfis

    # ─── Catalog coverage checks ──────────────────────────────────────────

    def _check_catalog_coverage(self, opening_schedule: dict, catalog_items: list) -> list:
        rfis = []
        if not opening_schedule or not opening_schedule.get("schedule"):
            return rfis

        catalog_die_numbers = {str(item.get("die_number", "")).strip() for item in catalog_items}

        uncatalogued_systems = set()
        for opening in opening_schedule.get("schedule", []):
            system_series = opening.get("system_series", "")
            # If we have a catalog but this system has no matching die numbers
            if catalog_items and system_series and system_series not in catalog_die_numbers:
                uncatalogued_systems.add(system_series)

        for series in uncatalogued_systems:
            rfis.append(RFIItem(
                rfi_id=self._next_rfi(),
                category="CATALOG_MISMATCH",
                severity="CRITICAL",
                description=f"Profile series '{series}' has no matching entries in the uploaded catalog",
                affected_element=f"System series: {series}",
                recommendation="Upload current Gulf Extrusions/Elite catalog PDF or manually add the die numbers with weights and prices.",
                auto_resolvable=False,
            ))

        if not catalog_items:
            rfis.append(RFIItem(
                rfi_id=self._next_rfi(),
                category="CATALOG_MISMATCH",
                severity="HIGH",
                description="No profile catalog uploaded — aluminum pricing uses LME formula estimate only",
                affected_element="All aluminum profiles",
                recommendation="Upload Gulf Extrusions or Elite Aluminium catalog PDF for accurate pricing.",
                auto_resolvable=False,
            ))

        return rfis

    # ─── Glass handling checks ────────────────────────────────────────────

    def _check_glass_handling(self, opening_schedule: dict) -> list:
        rfis = []
        if not opening_schedule:
            return rfis

        heavy_panes = []
        for opening in opening_schedule.get("schedule", []):
            weight = opening.get("glass_pane_weight_kg", 0)
            if weight > 150:
                heavy_panes.append((opening.get("opening_id", "?"), weight))

        if heavy_panes:
            rfis.append(RFIItem(
                rfi_id=self._next_rfi(),
                category="SPECIFICATION",
                severity="HIGH",
                description=f"{len(heavy_panes)} glass pane(s) exceed 150kg — crane lift required: {', '.join(f'{id}({w:.0f}kg)' for id, w in heavy_panes[:3])}",
                affected_element=", ".join(id for id, _ in heavy_panes[:5]),
                recommendation="Include crane hire in site preliminaries. Prepare lift plan per UAE OSH regulations.",
                requires_client_approval=False,
            ))

        return rfis

    # ─── Opening dimension checks ─────────────────────────────────────────

    def _check_openings(self, opening_schedule: dict) -> list:
        rfis = []
        if not opening_schedule:
            return rfis

        no_dimensions = []
        for opening in opening_schedule.get("schedule", []):
            w = opening.get("width_mm", 0)
            h = opening.get("height_mm", 0)
            if not w or not h:
                no_dimensions.append(opening.get("opening_id", "?"))

        if no_dimensions:
            rfis.append(RFIItem(
                rfi_id=self._next_rfi(),
                category="SPECIFICATION",
                severity="MEDIUM",
                description=f"{len(no_dimensions)} opening(s) have no dimensions extracted from DWG",
                affected_element=", ".join(no_dimensions[:5]),
                recommendation="Verify DWG blocks have correct attribute data. Dimensions required for BOM calculation.",
            ))

        return rfis

    # ─── LLM-based spec analysis ──────────────────────────────────────────

    def _analyze_spec_with_llm(self, spec_text: str) -> list:
        """Use Groq LLaMA to analyze spec text for non-obvious risks."""
        try:
            import asyncio
            from app.services.llm_client import complete

            prompt = f"""You are a Senior Estimator reviewing project specifications for aluminium and glass facade works in UAE.

Review this specification text and identify:
1. Missing performance specifications (acoustic, thermal, blast resistance)
2. Non-standard or unusual requirements
3. Conflicting information
4. Items that may significantly increase cost vs a standard facade

Return a JSON array of risk items. Each item:
{{
  "severity": "HIGH" | "MEDIUM" | "LOW",
  "category": "SPECIFICATION" | "FIRE_COMPLIANCE" | "THERMAL" | "ACOUSTIC" | "STRUCTURAL",
  "description": "concise description of the risk",
  "recommendation": "what the estimator should do"
}}

Return ONLY valid JSON array. If no risks found, return empty array [].

SPECIFICATION TEXT (first 3000 chars):
{spec_text[:3000]}"""

            import json
            result = asyncio.run(complete(
                [{"role": "user", "content": prompt}],
                temperature=0.1,
                json_mode=True,
            ))

            # Parse response
            json_match = re.search(r'\[.*?\]', result, re.DOTALL)
            if not json_match:
                return []

            llm_rfis = json.loads(json_match.group())
            rfis = []
            for item in llm_rfis:
                if not isinstance(item, dict):
                    continue
                rfis.append(RFIItem(
                    rfi_id=self._next_rfi(),
                    category=item.get("category", "SPECIFICATION"),
                    severity=item.get("severity", "MEDIUM"),
                    description=item.get("description", ""),
                    recommendation=item.get("recommendation", ""),
                    requires_client_approval=item.get("severity") == "HIGH",
                ))
            return rfis

        except Exception as e:
            logger.debug(f"LLM risk analysis failed: {e}")
            return []

    def to_dict(self, rfis: list) -> list:
        """Serialize RFI list to dicts."""
        return [
            {
                "rfi_id": r.rfi_id,
                "category": r.category,
                "severity": r.severity,
                "description": r.description,
                "affected_element": r.affected_element,
                "recommendation": r.recommendation,
                "requires_client_approval": r.requires_client_approval,
                "auto_resolvable": r.auto_resolvable,
            }
            for r in rfis
        ]

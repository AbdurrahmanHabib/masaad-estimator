"""Value Engineering Engine — identifies over-engineered elements and cost savings."""
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("masaad-ve")


@dataclass
class VEOpportunity:
    ve_id: str
    category: str  # PROFILE_UPGRADE | ACP_FINISH | GLASS_THICKNESS | HARDWARE | OTHER
    description: str
    current_spec: str
    proposed_spec: str
    saving_aed: float
    saving_pct: float
    affected_items: list = field(default_factory=list)
    confidence: str = "MEDIUM"  # HIGH | MEDIUM | LOW
    risk_note: str = ""


class ValueEngineeringEngine:
    """Identifies value engineering opportunities in the estimate."""

    # Over-engineering threshold: if Ixx_provided > Ixx_required × this factor
    OVER_ENGINEERING_THRESHOLD = 1.5

    def find_ve_opportunities(
        self,
        bom_data: dict = None,
        structural_results: list = None,
        catalog_items: list = None,
        material_rates: dict = None,
        spec_text: str = "",
        opening_schedule: dict = None,
    ) -> list:
        """Find all VE opportunities and return sorted by savings."""
        opportunities = []
        ve_counter = [0]

        def next_ve():
            ve_counter[0] += 1
            return f"VE-{ve_counter[0]:03d}"

        # Check over-engineered profiles
        if structural_results and catalog_items:
            profile_ve = self._check_profile_overengineering(
                structural_results, catalog_items, material_rates or {}, next_ve
            )
            opportunities.extend(profile_ve)

        # Check ACP finish grade
        if spec_text and bom_data:
            acp_ve = self._check_acp_finish(spec_text, bom_data, material_rates or {}, next_ve)
            opportunities.extend(acp_ve)

        # Check glass thickness
        if opening_schedule and spec_text:
            glass_ve = self._check_glass_thickness(opening_schedule, spec_text, material_rates or {}, next_ve)
            opportunities.extend(glass_ve)

        # Check hardware specification
        if spec_text and bom_data:
            hw_ve = self._check_hardware_spec(spec_text, bom_data, material_rates or {}, next_ve)
            opportunities.extend(hw_ve)

        # Sort by saving (highest first)
        opportunities.sort(key=lambda x: x.saving_aed, reverse=True)

        total_saving = sum(v.saving_aed for v in opportunities)
        logger.info(f"VE analysis: {len(opportunities)} opportunities, AED {total_saving:,.0f} potential saving")

        return opportunities

    def _check_profile_overengineering(
        self, structural_results: list, catalog_items: list, material_rates: dict, next_ve
    ) -> list:
        """Check if profiles are over-specified vs structural requirement."""
        opportunities = []
        effective_aed_per_kg = material_rates.get("factory_hourly_rate_aed", 85.0)
        catalog_by_series = {}
        for item in catalog_items:
            series = item.get("system_series", "")
            if series:
                catalog_by_series.setdefault(series, []).append(item)

        for result in structural_results:
            ixx_provided = result.get("ixx_cm4_provided", 0)
            ixx_required = result.get("ixx_cm4_required", 0)
            current_die = result.get("die_number", "")
            series = result.get("system_series", "")
            weight_current = result.get("weight_kg_m", 0)
            total_lm = result.get("total_lm", 0)

            if not ixx_provided or not ixx_required or not total_lm:
                continue

            ratio = ixx_provided / ixx_required if ixx_required > 0 else 0

            if ratio > self.OVER_ENGINEERING_THRESHOLD:
                # Find lighter profile in same series that still passes
                target_ixx = ixx_required * 1.1  # 10% safety margin
                alternatives = []
                for item in catalog_by_series.get(series, []):
                    item_ixx = item.get("ixx_cm4", 0)
                    item_weight = item.get("weight_kg_m", 0)
                    if item_ixx and item_ixx >= target_ixx and item_weight < weight_current:
                        alternatives.append(item)

                if alternatives:
                    best = min(alternatives, key=lambda x: x.get("weight_kg_m", 999))
                    weight_saving_kg_m = weight_current - best.get("weight_kg_m", 0)
                    catalog_price = best.get("price_aed_per_kg") or effective_aed_per_kg
                    saving_aed = weight_saving_kg_m * total_lm * catalog_price

                    if saving_aed > 500:  # Only flag if saving is meaningful
                        opportunities.append(VEOpportunity(
                            ve_id=next_ve(),
                            category="PROFILE_UPGRADE",
                            description=f"Profile {current_die} is over-specified by {(ratio-1)*100:.0f}% (Ixx ratio {ratio:.1f}×)",
                            current_spec=f"Die {current_die} ({weight_current:.3f} kg/m, Ixx {ixx_provided:.1f} cm⁴)",
                            proposed_spec=f"Die {best.get('die_number','?')} ({best.get('weight_kg_m',0):.3f} kg/m, Ixx {best.get('ixx_cm4',0):.1f} cm⁴)",
                            saving_aed=round(saving_aed, 0),
                            saving_pct=round(weight_saving_kg_m / weight_current * 100, 1),
                            affected_items=[current_die],
                            confidence="HIGH",
                            risk_note="Verify with structural engineer before substituting",
                        ))

        return opportunities

    def _check_acp_finish(self, spec_text: str, bom_data: dict, material_rates: dict, next_ve) -> list:
        """Check if PVDF finish is specified for sheltered/internal areas."""
        opportunities = []
        spec_lower = spec_text.lower()

        acp_sqm = bom_data.get("acp_total_sqm", 0)
        if not acp_sqm:
            return []

        pvdf_rate = material_rates.get("acp_pvdf_aed_sqm", 185.0)
        powder_rate = material_rates.get("acp_powder_coat_aed_sqm", 160.0)

        if "pvdf" in spec_lower and ("internal" in spec_lower or "sheltered" in spec_lower or "covered" in spec_lower):
            # PVDF specified but internal — can use powder coat
            saving_per_sqm = pvdf_rate - powder_rate
            # Conservative: assume 20% of ACP area is internal/sheltered
            internal_sqm = acp_sqm * 0.2
            saving_aed = internal_sqm * saving_per_sqm

            if saving_aed > 200:
                opportunities.append(VEOpportunity(
                    ve_id=next_ve(),
                    category="ACP_FINISH",
                    description="PVDF finish specified for internal/sheltered ACP areas — powder coat is sufficient",
                    current_spec=f"PVDF finish (AED {pvdf_rate}/SQM) on all {acp_sqm:.0f} SQM",
                    proposed_spec=f"Powder coat (AED {powder_rate}/SQM) on sheltered areas (~{internal_sqm:.0f} SQM)",
                    saving_aed=round(saving_aed, 0),
                    saving_pct=round(saving_per_sqm / pvdf_rate * 100, 1),
                    confidence="MEDIUM",
                    risk_note="Only applicable to internal/sheltered areas — external PVDF must remain",
                ))

        return opportunities

    def _check_glass_thickness(self, opening_schedule: dict, spec_text: str, material_rates: dict, next_ve) -> list:
        """Check if glass is specified thicker than structural requirement."""
        opportunities = []
        spec_lower = spec_text.lower()

        # If spec says 8mm but no acoustic/security requirement, 6mm may suffice
        if "8mm" in spec_lower and "acoustic" not in spec_lower and "security" not in spec_lower:
            glass_6_rate = material_rates.get("glass_tempered_clear_aed_sqm", 85.0)
            glass_8_rate = glass_6_rate * 1.15  # 8mm ~15% more

            total_glazed = opening_schedule.get("summary", {}).get("total_glazed_sqm", 0)
            if total_glazed > 0:
                saving_aed = total_glazed * (glass_8_rate - glass_6_rate)
                opportunities.append(VEOpportunity(
                    ve_id=next_ve(),
                    category="GLASS_THICKNESS",
                    description="8mm glass specified — 6mm may be structurally sufficient for standard spans",
                    current_spec=f"8mm toughened glass ({total_glazed:.0f} SQM)",
                    proposed_spec=f"6mm toughened glass (verify structural calcs first)",
                    saving_aed=round(saving_aed, 0),
                    saving_pct=13.0,
                    confidence="LOW",
                    risk_note="Must verify structural calculation for glass spans before reducing thickness",
                ))

        return opportunities

    def _check_hardware_spec(self, spec_text: str, bom_data: dict, material_rates: dict, next_ve) -> list:
        """Check if premium hardware brands can be substituted."""
        opportunities = []
        spec_lower = spec_text.lower()

        # If floor spring specified for lightweight doors (under 60kg)
        if "floor spring" in spec_lower:
            floor_spring_rate = material_rates.get("hardware_floor_spring_aed", 680.0)
            door_closer_rate = material_rates.get("hardware_door_closer_aed", 245.0)
            door_count = bom_data.get("door_count", 0)

            if door_count > 0:
                saving_aed = door_count * (floor_spring_rate - door_closer_rate)
                if saving_aed > 500:
                    opportunities.append(VEOpportunity(
                        ve_id=next_ve(),
                        category="HARDWARE",
                        description=f"Floor springs specified for {door_count} doors — door closers may be sufficient for lightweight doors",
                        current_spec=f"Floor spring (AED {floor_spring_rate:.0f}/unit × {door_count} doors)",
                        proposed_spec=f"DORMA TS83 overhead closer (AED {door_closer_rate:.0f}/unit) for doors <60kg",
                        saving_aed=round(saving_aed, 0),
                        saving_pct=round((floor_spring_rate - door_closer_rate) / floor_spring_rate * 100, 1),
                        confidence="MEDIUM",
                        risk_note="Floor springs required if specified by architect — verify intent. Confirm door weights.",
                    ))

        return opportunities

    def calculate_total_saving(self, opportunities: list) -> float:
        """Sum all VE savings."""
        return sum(v.saving_aed for v in opportunities)

    def to_dict(self, opportunities: list) -> list:
        """Serialize VE list to dicts."""
        return [
            {
                "ve_id": v.ve_id,
                "category": v.category,
                "description": v.description,
                "current_spec": v.current_spec,
                "proposed_spec": v.proposed_spec,
                "saving_aed": v.saving_aed,
                "saving_pct": v.saving_pct,
                "confidence": v.confidence,
                "risk_note": v.risk_note,
            }
            for v in opportunities
        ]

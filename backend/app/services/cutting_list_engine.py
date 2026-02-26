"""Cutting list engine — generates the complete 7-section cutting list."""
import math
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("masaad-cutting-list")

# Fabrication operation norms (minutes per action)
FABRICATION_NORMS_MINUTES = {
    "saw_cut_straight": 0.5,
    "saw_cut_double_mitre": 0.5,
    "cnc_drill_per_hole": 1.0,
    "corner_crimp": 2.5,
    "gasket_insertion_per_lm": 0.5,
    "frame_assembly_per_joint": 8.0,
    "acp_cassette_fold": 3.0,
    "glass_install_factory": 15.0,
    "hardware_fitting": 20.0,
    "qc_check_per_opening": 8.0,
    "packaging_per_batch": 30.0,
}

# Hardware rules per opening type
HARDWARE_RULES = {
    "Window - Casement": [
        {"item": "Espagnolette Handle", "spec": "ROTO NT or equiv", "qty_per_unit": 1, "price_field": "hardware_casement_handle_aed"},
        {"item": "Friction Stay Hinge Pair", "spec": "ROTO NT 200N", "qty_per_unit": 2, "price_field": "hardware_casement_hinge_pair_aed"},
        {"item": "Multi-Point Lock", "spec": "ROTO L=800mm", "qty_per_unit": 1, "price_field": "hardware_casement_lock_aed"},
        {"item": "Window Restrictor", "spec": "Safety restrictor 100mm", "qty_per_unit": 1, "price_field": "hardware_casement_restrictor_aed"},
    ],
    "Window - Fixed": [
        {"item": "Setting Blocks", "spec": "EPDM 100×25×6mm", "qty_formula": "2", "price_field": "setting_block_each_aed"},
        {"item": "Distance Pieces", "spec": "Neoprene 100×20×4mm", "qty_formula": "4", "price_field": "distance_piece_each_aed"},
    ],
    "Door - Single Swing": [
        {"item": "Lever Handle Set", "spec": "Grade 304 SS", "qty_per_unit": 1, "price_field": "hardware_door_handle_set_aed"},
        {"item": "Mortice Lock", "spec": "Abloy or equiv", "qty_per_unit": 1, "price_field": "hardware_mortice_lock_aed"},
        {"item": "Door Closer", "spec": "DORMA TS83 size 4", "qty_per_unit": 1, "price_field": "hardware_door_closer_aed"},
        {"item": "Door Hinge Set (3×)", "spec": "180° SS A2", "qty_per_unit": 1, "price_field": "hardware_door_hinge_set_aed"},
    ],
    "Door - Double Swing": [
        {"item": "Lever Handle Set", "spec": "Grade 304 SS", "qty_per_unit": 2, "price_field": "hardware_door_handle_set_aed"},
        {"item": "Mortice Lock", "spec": "Abloy or equiv", "qty_per_unit": 1, "price_field": "hardware_mortice_lock_aed"},
        {"item": "Door Closer", "spec": "DORMA TS83 size 4", "qty_per_unit": 2, "price_field": "hardware_door_closer_aed"},
        {"item": "Door Hinge Set (3×)", "spec": "180° SS A2", "qty_per_unit": 2, "price_field": "hardware_door_hinge_set_aed"},
    ],
    "Door - Automatic Sliding": [
        {"item": "Auto Sliding Operator", "spec": "DORMA ES200 or equiv", "qty_per_unit": 1, "price_field": "hardware_door_closer_aed"},
    ],
}

# Sealant consumption rules
SEALANT_RULES = [
    {"item": "Weatherseal Silicone (310ml sausage)", "spec": "Dow Corning 895 or equiv", "coverage_lm_per_sausage": 10, "joint_lm_formula": "perimeter × 2", "price_field": "sealant_weatherseal_310ml_aed"},
    {"item": "Structural Silicone (600ml sausage)", "spec": "Dow Corning 983 or equiv", "coverage_lm_per_sausage": 7, "joint_lm_formula": "glass_perimeter", "price_field": "sealant_structural_600ml_aed"},
    {"item": "Backer Rod ∅10mm", "spec": "Polyethylene closed-cell", "unit": "LM", "joint_lm_formula": "glass_perimeter", "price_field": "backer_rod_10mm_per_lm_aed"},
    {"item": "Silicone Primer (500ml bottle)", "spec": "Dow Corning 1200", "coverage_lm_per_bottle": 50, "joint_lm_formula": "glass_perimeter", "price_field": "sealant_primer_500ml_aed"},
    {"item": "Setting Blocks (EPDM 100×25×6mm)", "spec": "Neoprene 70 Shore", "qty_formula": "glass_panes × 2", "price_field": "setting_block_each_aed"},
    {"item": "Distance Pieces (100×20×4mm)", "spec": "Neoprene", "qty_formula": "glass_panes × 4", "price_field": "distance_piece_each_aed"},
]

# Profile accessory rules (per system type)
PROFILE_ACCESSORY_RULES = {
    "Curtain Wall (Stick)": {
        "t_connector": {"formula": "mullion_transom_junctions", "price_field": "t_connector_each_aed"},
        "l_connector": {"formula": "corner_junctions", "price_field": "l_connector_each_aed"},
        "end_cap": {"formula": "exposed_profile_ends", "price_field": "end_cap_each_aed"},
        "expansion_joint": {"formula": "ceil(facade_run_m / 4.0)", "price_field": "expansion_joint_each_aed"},
        "fire_stop_lm": {"formula": "floor_line_perimeter × floors", "price_field": "fire_stop_per_lm_aed"},
        "drainage_insert": {"formula": "ceil(sill_run_m / 0.6)", "price_field": "drainage_insert_each_aed"},
    },
}


@dataclass
class ProfileBarPlan:
    bar_id: str
    die_number: str
    stock_length_mm: float = 6000
    start_trim_mm: float = 50
    cuts: list = field(default_factory=list)  # [{length_mm, piece_id, opening_id}]
    end_remnant_mm: float = 0
    kerf_total_mm: float = 0
    waste_pct: float = 0
    yield_pct: float = 0
    offcut_reuse: bool = False


@dataclass
class ProfileSummary:
    die_number: str
    system_series: str = ""
    description: str = ""
    net_lm: float = 0
    wastage_pct: float = 0.05
    gross_lm: float = 0
    stock_length_mm: float = 6000
    bars_required: int = 0
    weight_kg_m: float = 0
    total_weight_kg: float = 0
    catalog_price_aed_per_kg: Optional[float] = None
    lme_price_aed_per_kg: Optional[float] = None
    effective_price_aed_per_kg: float = 0
    total_cost_aed: float = 0
    bar_plans: list = field(default_factory=list)


@dataclass
class GlassPaneRecord:
    pane_id: str
    opening_id: str
    glass_type: str
    nominal_w_mm: float
    nominal_h_mm: float
    net_area_sqm: float
    weight_kg: float
    handling_note: str = ""
    quantity: int = 1
    total_sqm: float = 0
    total_kg: float = 0
    unit_price_aed_sqm: float = 0
    total_cost_aed: float = 0


@dataclass
class ACPPanelRecord:
    panel_id: str
    zone: str
    floor: str
    nominal_w_mm: float
    nominal_h_mm: float
    effective_w_mm: float  # +50mm fold each side
    effective_h_mm: float  # +50mm fold each side
    gross_sqm: float
    finish: str = ""
    quantity: int = 1
    sheet_assignment: str = ""
    unit_price_aed_sqm: float = 0
    total_cost_aed: float = 0


@dataclass
class FabricationLaborSummary:
    operation_counts: dict = field(default_factory=dict)
    total_hours: float = 0
    burn_rate_aed_hr: float = 85.0
    total_cost_aed: float = 0


@dataclass
class CompleteCuttingList:
    # Section A: Aluminum profiles
    profile_summaries: list = field(default_factory=list)
    # Section B: ACP panels
    acp_panels: list = field(default_factory=list)
    # Section C: Glass schedule
    glass_schedule: list = field(default_factory=list)
    # Section D: Hardware
    hardware_schedule: list = field(default_factory=list)
    # Section E: Sealants
    sealant_schedule: list = field(default_factory=list)
    # Section F: Fixings
    fixing_schedule: list = field(default_factory=list)
    # Section G: Fabrication labor
    fabrication_labor: FabricationLaborSummary = field(default_factory=FabricationLaborSummary)

    # Cost totals
    total_aluminum_cost_aed: float = 0
    total_glass_cost_aed: float = 0
    total_acp_cost_aed: float = 0
    total_hardware_cost_aed: float = 0
    total_sealant_cost_aed: float = 0
    total_fixing_cost_aed: float = 0
    total_fabrication_cost_aed: float = 0
    grand_total_direct_cost_aed: float = 0

    # Weight summary
    aluminum_kg: float = 0
    glass_kg: float = 0
    acp_kg: float = 0
    total_kg: float = 0
    truck_loads: int = 0


class CuttingListEngine:
    """Generates the complete 7-section cutting list from BOM and CSP output."""

    KERF_MM = 4.0  # Saw blade width

    def generate_complete_cutting_list(
        self,
        bom_output: dict,
        csp_result: dict,
        nesting_result: dict,
        opening_schedule: dict,
        material_rates: dict,
        market_rates: dict,
        catalog_items: list = None,
    ) -> CompleteCuttingList:
        """Generate the complete cutting list."""
        cl = CompleteCuttingList()

        # Section A: Aluminum profiles
        cl.profile_summaries = self._build_profile_summaries(
            bom_output, csp_result, material_rates, market_rates, catalog_items or []
        )
        cl.total_aluminum_cost_aed = sum(p.total_cost_aed for p in cl.profile_summaries)
        cl.aluminum_kg = sum(p.total_weight_kg for p in cl.profile_summaries)

        # Section B: ACP panels
        cl.acp_panels = self._build_acp_schedule(bom_output, nesting_result, material_rates)
        cl.total_acp_cost_aed = sum(p.total_cost_aed for p in cl.acp_panels)
        cl.acp_kg = sum(p.gross_sqm * 5.5 * p.quantity for p in cl.acp_panels)  # 5.5 kg/m2 for 4mm ACP

        # Section C: Glass schedule
        cl.glass_schedule = self._build_glass_schedule(opening_schedule, material_rates)
        cl.total_glass_cost_aed = sum(g.total_cost_aed for g in cl.glass_schedule)
        cl.glass_kg = sum(g.total_kg for g in cl.glass_schedule)

        # Section D: Hardware
        cl.hardware_schedule = self._build_hardware_schedule(opening_schedule, material_rates)
        cl.total_hardware_cost_aed = sum(h.get("total_cost_aed", 0) for h in cl.hardware_schedule)

        # Section E: Sealants
        cl.sealant_schedule = self._build_sealant_schedule(opening_schedule, material_rates)
        cl.total_sealant_cost_aed = sum(s.get("total_cost_aed", 0) for s in cl.sealant_schedule)

        # Section F: Fixings
        cl.fixing_schedule = self._build_fixing_schedule(bom_output, material_rates)
        cl.total_fixing_cost_aed = sum(f.get("total_cost_aed", 0) for f in cl.fixing_schedule)

        # Section G: Fabrication labor
        cl.fabrication_labor = self._calculate_fabrication_labor(
            cl, opening_schedule, material_rates
        )
        cl.total_fabrication_cost_aed = cl.fabrication_labor.total_cost_aed

        # Totals
        cl.total_kg = cl.aluminum_kg + cl.glass_kg + cl.acp_kg
        cl.truck_loads = max(1, math.ceil(cl.total_kg / 5000))
        cl.grand_total_direct_cost_aed = (
            cl.total_aluminum_cost_aed + cl.total_glass_cost_aed + cl.total_acp_cost_aed +
            cl.total_hardware_cost_aed + cl.total_sealant_cost_aed + cl.total_fixing_cost_aed +
            cl.total_fabrication_cost_aed
        )

        logger.info(
            f"Cutting list: {len(cl.profile_summaries)} profiles, "
            f"{len(cl.glass_schedule)} glass types, "
            f"total AED {cl.grand_total_direct_cost_aed:,.0f}"
        )

        return cl

    def _build_profile_summaries(
        self, bom_output: dict, csp_result: dict, material_rates: dict, market_rates: dict, catalog_items: list
    ) -> list:
        """Build Section A: Aluminum profile summary + bar plans."""
        summaries = []
        catalog_by_die = {str(item.get("die_number", "")): item for item in catalog_items}

        for die_data in bom_output.get("profiles", []):
            die_number = str(die_data.get("die_number", ""))
            net_lm = float(die_data.get("net_lm", 0) or 0)
            weight_kg_m = float(die_data.get("weight_kg_m", 0) or 0)

            if not net_lm or not weight_kg_m:
                continue

            # Wastage factor
            has_mitre = die_data.get("has_mitre", False)
            wastage_pct = 0.08 if has_mitre else 0.05
            gross_lm = net_lm * (1 + wastage_pct)

            stock_length_mm = float(die_data.get("stock_length_mm", 6000))
            bars_required = math.ceil(gross_lm * 1000 / stock_length_mm)

            total_weight_kg = gross_lm * weight_kg_m

            # Pricing: catalog first, then LME formula
            cat_item = catalog_by_die.get(die_number)
            catalog_price = float(cat_item.get("price_aed_per_kg") or 0) if cat_item else 0

            lme_price = self._calculate_lme_price(market_rates)

            effective_price = catalog_price if catalog_price > 0 else lme_price
            total_cost = total_weight_kg * effective_price

            # Get bar plans from CSP
            bar_plans = []
            csp_profile_data = (csp_result or {}).get("profiles", {}).get(die_number, {})
            for bar_idx, bar in enumerate(csp_profile_data.get("bars", []), 1):
                cuts = bar.get("cuts", [])
                kerf_total = len(cuts) * self.KERF_MM
                cut_total = sum(c.get("length_mm", 0) for c in cuts)
                remnant = stock_length_mm - 50 - kerf_total - cut_total  # 50mm start trim

                plan = ProfileBarPlan(
                    bar_id=f"{die_number}-BAR-{bar_idx:03d}",
                    die_number=die_number,
                    stock_length_mm=stock_length_mm,
                    cuts=cuts,
                    end_remnant_mm=max(0, remnant),
                    kerf_total_mm=kerf_total,
                    offcut_reuse=remnant >= 1000,
                )
                if stock_length_mm > 0:
                    plan.yield_pct = cut_total / stock_length_mm * 100
                bar_plans.append(plan)

            ps = ProfileSummary(
                die_number=die_number,
                system_series=die_data.get("system_series", ""),
                description=die_data.get("description", ""),
                net_lm=round(net_lm, 2),
                wastage_pct=wastage_pct,
                gross_lm=round(gross_lm, 2),
                stock_length_mm=stock_length_mm,
                bars_required=bars_required,
                weight_kg_m=weight_kg_m,
                total_weight_kg=round(total_weight_kg, 2),
                catalog_price_aed_per_kg=catalog_price or None,
                lme_price_aed_per_kg=round(lme_price, 2),
                effective_price_aed_per_kg=round(effective_price, 2),
                total_cost_aed=round(total_cost, 2),
                bar_plans=bar_plans,
            )
            summaries.append(ps)

        return summaries

    def _calculate_lme_price(self, market_rates: dict) -> float:
        """Calculate aluminum price from LME formula."""
        lme = float(market_rates.get("lme_aluminum_usd_mt", 2485) or 2485)
        billet = float(market_rates.get("billet_premium_usd_mt", 400) or 400)
        extrusion = float(market_rates.get("extrusion_premium_usd_mt", 800) or 800)
        usd_aed = float(market_rates.get("usd_aed", 3.6725) or 3.6725)
        powder_coat = 15.0  # AED/kg default

        raw_cost_aed_per_kg = ((lme + billet) * usd_aed) / 1000
        total = raw_cost_aed_per_kg + (extrusion * usd_aed / 1000) + powder_coat
        return round(total, 2)

    def _build_acp_schedule(self, bom_output: dict, nesting_result: dict, material_rates: dict) -> list:
        """Build Section B: ACP panel schedule."""
        panels = []
        finish = bom_output.get("acp_finish", "PVDF Standard")
        price_field_map = {
            "Polyester": "acp_polyester_aed_sqm",
            "Powder Coat": "acp_powder_coat_aed_sqm",
            "PVDF": "acp_pvdf_aed_sqm",
            "PVDF Metallic": "acp_metallic_pvdf_aed_sqm",
        }
        price_field = next((v for k, v in price_field_map.items() if k.lower() in finish.lower()), "acp_pvdf_aed_sqm")
        unit_price = float(material_rates.get(price_field, 185.0) or 185.0)

        nesting_panels = (nesting_result or {}).get("panels", bom_output.get("acp_panels", []))

        for idx, panel in enumerate(nesting_panels, 1):
            nominal_w = float(panel.get("nominal_w_mm", panel.get("width_mm", 1200)) or 1200)
            nominal_h = float(panel.get("nominal_h_mm", panel.get("height_mm", 2800)) or 2800)
            effective_w = nominal_w + 100  # +50mm fold each side
            effective_h = nominal_h + 100
            gross_sqm = (effective_w * effective_h) / 1_000_000
            qty = int(panel.get("quantity", panel.get("count", 1)) or 1)
            total_cost = gross_sqm * qty * unit_price

            rec = ACPPanelRecord(
                panel_id=panel.get("panel_id", f"ACP-{idx:03d}"),
                zone=panel.get("zone", panel.get("elevation", "")),
                floor=panel.get("floor", panel.get("level", "")),
                nominal_w_mm=nominal_w,
                nominal_h_mm=nominal_h,
                effective_w_mm=effective_w,
                effective_h_mm=effective_h,
                gross_sqm=round(gross_sqm, 4),
                finish=finish,
                quantity=qty,
                unit_price_aed_sqm=unit_price,
                total_cost_aed=round(total_cost, 2),
            )
            panels.append(rec)

        return panels

    def _build_glass_schedule(self, opening_schedule: dict, material_rates: dict) -> list:
        """Build Section C: Glass schedule."""
        glass_types = {}
        GLASS_DENSITY = 2.5  # kg/m2 per mm thickness

        for opening in (opening_schedule or {}).get("schedule", []):
            glass_type = opening.get("glass_type", "6mm Clear Tempered")
            thickness = float(opening.get("glass_thickness_mm", 6.0) or 6.0)
            nominal_w = float(opening.get("width_mm", 0) or 0)
            nominal_h = float(opening.get("height_mm", 0) or 0)

            if not nominal_w or not nominal_h:
                continue

            # Net glazed dimensions (bite deducted)
            net_w = max(0, nominal_w - 30)
            net_h = max(0, nominal_h - 30)
            net_area = (net_w * net_h) / 1_000_000
            weight_kg = net_area * thickness * GLASS_DENSITY
            qty = int(opening.get("count", 1))

            # Handling note
            if weight_kg > 300:
                handling = "CRANE LIFT REQUIRED"
            elif weight_kg > 150:
                handling = "Mechanical assist required"
            elif weight_kg > 100:
                handling = "2-man lift required"
            else:
                handling = "Standard"

            key = (glass_type, round(net_w), round(net_h))
            if key in glass_types:
                glass_types[key]["quantity"] += qty
                glass_types[key]["total_sqm"] += net_area * qty
                glass_types[key]["total_kg"] += weight_kg * qty
            else:
                glass_types[key] = {
                    "pane_id": f"G-{len(glass_types)+1:03d}",
                    "opening_id": opening.get("opening_id", ""),
                    "glass_type": glass_type,
                    "thickness_mm": thickness,
                    "nominal_w_mm": net_w,
                    "nominal_h_mm": net_h,
                    "net_area_sqm": round(net_area, 4),
                    "weight_kg": round(weight_kg, 2),
                    "handling_note": handling,
                    "quantity": qty,
                    "total_sqm": round(net_area * qty, 4),
                    "total_kg": round(weight_kg * qty, 2),
                    "unit_price_aed_sqm": 0,
                    "total_cost_aed": 0,
                }

        # Apply pricing
        result = []
        for pane in glass_types.values():
            price = self._get_glass_price(pane["glass_type"], material_rates)
            pane["unit_price_aed_sqm"] = price
            pane["total_cost_aed"] = round(pane["total_sqm"] * price, 2)
            result.append(GlassPaneRecord(
                pane_id=pane["pane_id"],
                opening_id=pane["opening_id"],
                glass_type=pane["glass_type"],
                nominal_w_mm=pane["nominal_w_mm"],
                nominal_h_mm=pane["nominal_h_mm"],
                net_area_sqm=pane["net_area_sqm"],
                weight_kg=pane["weight_kg"],
                handling_note=pane["handling_note"],
                quantity=pane["quantity"],
                total_sqm=pane["total_sqm"],
                total_kg=pane["total_kg"],
                unit_price_aed_sqm=price,
                total_cost_aed=pane["total_cost_aed"],
            ))

        return result

    def _get_glass_price(self, glass_type: str, material_rates: dict) -> float:
        """Map glass type string to price field."""
        glass_lower = glass_type.lower()
        if "dgu" in glass_lower and "low" in glass_lower:
            return float(material_rates.get("glass_dgu_low_e_aed_sqm", 225.0) or 225.0)
        if "dgu" in glass_lower:
            return float(material_rates.get("glass_dgu_6_12_6_clear_aed_sqm", 175.0) or 175.0)
        if "laminated" in glass_lower:
            return float(material_rates.get("glass_laminated_6_6_aed_sqm", 145.0) or 145.0)
        if "low" in glass_lower and "e" in glass_lower:
            return float(material_rates.get("glass_low_e_aed_sqm", 120.0) or 120.0)
        if "tinted" in glass_lower and ("tempered" in glass_lower or "toughened" in glass_lower):
            return float(material_rates.get("glass_tempered_tinted_aed_sqm", 95.0) or 95.0)
        if "tempered" in glass_lower or "toughened" in glass_lower:
            return float(material_rates.get("glass_tempered_clear_aed_sqm", 85.0) or 85.0)
        if "tinted" in glass_lower:
            return float(material_rates.get("glass_tinted_aed_sqm", 75.0) or 75.0)
        if "structural" in glass_lower:
            return float(material_rates.get("glass_structural_dgu_aed_sqm", 280.0) or 280.0)
        if "spandrel" in glass_lower or "opaque" in glass_lower:
            return float(material_rates.get("glass_opaque_spandrel_aed_sqm", 95.0) or 95.0)
        return float(material_rates.get("glass_clear_float_aed_sqm", 65.0) or 65.0)

    def _build_hardware_schedule(self, opening_schedule: dict, material_rates: dict) -> list:
        """Build Section D: Hardware schedule."""
        schedule = []
        type_counts = {}

        for opening in (opening_schedule or {}).get("schedule", []):
            sys_type = opening.get("system_type", "")
            count = int(opening.get("count", 1))
            type_counts[sys_type] = type_counts.get(sys_type, 0) + count

        for sys_type, total_count in type_counts.items():
            rules = HARDWARE_RULES.get(sys_type, [])
            for rule in rules:
                qty_per_unit = int(rule.get("qty_per_unit", 1))
                total_qty = qty_per_unit * total_count
                unit_price = float(material_rates.get(rule["price_field"], 0) or 0)
                total_cost = total_qty * unit_price

                schedule.append({
                    "opening_type": sys_type,
                    "item": rule["item"],
                    "spec": rule.get("spec", ""),
                    "qty_per_unit": qty_per_unit,
                    "total_units": total_count,
                    "total_qty": total_qty,
                    "unit_price_aed": unit_price,
                    "total_cost_aed": round(total_cost, 2),
                })

        return schedule

    def _build_sealant_schedule(self, opening_schedule: dict, material_rates: dict) -> list:
        """Build Section E: Sealants and consumables."""
        schedule = []
        summary = (opening_schedule or {}).get("summary", {})
        total_perimeter_lm = summary.get("total_glazed_sqm", 0) ** 0.5 * 4 * summary.get("total_openings", 1)
        if total_perimeter_lm <= 0:
            total_perimeter_lm = summary.get("total_glazed_sqm", 100) * 4  # rough estimate
        glass_panes = summary.get("total_openings", 0)

        for rule in SEALANT_RULES:
            price = float(material_rates.get(rule["price_field"], 0) or 0)
            formula = rule.get("joint_lm_formula", "")

            if "perimeter × 2" in formula:
                joint_lm = total_perimeter_lm * 2
            elif "glass_perimeter" in formula:
                joint_lm = total_perimeter_lm
            elif "glass_panes" in formula:
                pane_count = int(formula.split("×")[1].strip()) if "×" in formula else 2
                total_qty = glass_panes * pane_count
                unit = rule.get("unit", "nr")
                schedule.append({
                    "item": rule["item"],
                    "spec": rule.get("spec", ""),
                    "quantity": total_qty,
                    "unit": unit,
                    "unit_price_aed": price,
                    "total_cost_aed": round(total_qty * price, 2),
                })
                continue
            else:
                continue

            coverage = rule.get("coverage_lm_per_sausage", rule.get("coverage_lm_per_bottle", 10))
            total_units = math.ceil(joint_lm / coverage) if coverage > 0 else 0

            if rule.get("unit") == "LM":
                total_units = joint_lm

            schedule.append({
                "item": rule["item"],
                "spec": rule.get("spec", ""),
                "quantity": total_units,
                "unit": rule.get("unit", "sausage"),
                "joint_lm": round(joint_lm, 1),
                "unit_price_aed": price,
                "total_cost_aed": round(total_units * price, 2),
            })

        return schedule

    def _build_fixing_schedule(self, bom_output: dict, material_rates: dict) -> list:
        """Build Section F: Fixings and anchors."""
        schedule = []
        brackets = bom_output.get("brackets", [])
        total_brackets = sum(int(b.get("quantity", 0)) for b in brackets) if brackets else 0

        if total_brackets == 0:
            total_brackets = int(bom_output.get("total_brackets", 0) or 0)

        if total_brackets > 0:
            anchors_per_bracket = 4
            total_anchors = total_brackets * anchors_per_bracket

            items = [
                ("Hilti HST3 M12×110 Anchor", "anchor_m12_each_aed", total_anchors, "nr"),
                ("MS Galv. Bracket 80mm", "bracket_80mm_each_aed", math.ceil(total_brackets * 0.4), "nr"),
                ("MS Galv. Bracket 120mm", "bracket_120mm_each_aed", math.ceil(total_brackets * 0.6), "nr"),
                ("Shim Plates 50×50×3mm", "shim_plate_each_aed", total_brackets * 3, "nr"),
                ("Thermal Break Pad", "thermal_pad_each_aed", total_brackets, "nr"),
                ("T-Connector (profile)", "t_connector_each_aed", bom_output.get("t_connectors", 0), "nr"),
                ("L-Connector (profile)", "l_connector_each_aed", bom_output.get("l_connectors", 0), "nr"),
                ("End Cap (profile)", "end_cap_each_aed", bom_output.get("end_caps", 0), "nr"),
                ("Expansion Joint Assembly", "expansion_joint_each_aed", bom_output.get("expansion_joints", 0), "nr"),
                ("Fire Stop Strip", "fire_stop_per_lm_aed", bom_output.get("fire_stop_lm", 0), "LM"),
                ("Drainage Insert ∅10mm", "drainage_insert_each_aed", bom_output.get("drainage_inserts", 0), "nr"),
            ]

            for item_name, price_field, qty, unit in items:
                qty = int(qty or 0)
                if qty <= 0:
                    continue
                price = float(material_rates.get(price_field, 0) or 0)
                schedule.append({
                    "item": item_name,
                    "quantity": qty,
                    "unit": unit,
                    "unit_price_aed": price,
                    "total_cost_aed": round(qty * price, 2),
                })

        return schedule

    def _calculate_fabrication_labor(
        self, cl: CompleteCuttingList, opening_schedule: dict, material_rates: dict
    ) -> FabricationLaborSummary:
        """Calculate fabrication labor from operation counts."""
        fab = FabricationLaborSummary()
        burn_rate = float(material_rates.get("factory_hourly_rate_aed", 85.0) or 85.0)
        fab.burn_rate_aed_hr = burn_rate

        summary = (opening_schedule or {}).get("summary", {})
        total_openings = int(summary.get("total_openings", 0))
        total_glazed_sqm = float(summary.get("total_glazed_sqm", 0))

        # Estimate action counts from cutting list data
        total_cuts = sum(len(p.bar_plans) * max(1, len(p.bar_plans[0].cuts if p.bar_plans else [])) for p in cl.profile_summaries)
        total_bars = sum(p.bars_required for p in cl.profile_summaries)

        fab.operation_counts = {
            "Straight saw cuts": {"count": total_bars * 6, "mins_each": FABRICATION_NORMS_MINUTES["saw_cut_straight"]},
            "Double mitre cuts": {"count": total_openings * 4, "mins_each": FABRICATION_NORMS_MINUTES["saw_cut_double_mitre"]},
            "CNC holes per bar": {"count": total_bars * 8, "mins_each": FABRICATION_NORMS_MINUTES["cnc_drill_per_hole"]},
            "Frame assembly joints": {"count": total_openings * 4, "mins_each": FABRICATION_NORMS_MINUTES["frame_assembly_per_joint"]},
            "ACP cassette folds": {"count": len(cl.acp_panels) * 4, "mins_each": FABRICATION_NORMS_MINUTES["acp_cassette_fold"]},
            "Glass installation": {"count": total_openings, "mins_each": FABRICATION_NORMS_MINUTES["glass_install_factory"]},
            "Hardware fitting": {"count": total_openings, "mins_each": FABRICATION_NORMS_MINUTES["hardware_fitting"]},
            "QC inspection": {"count": total_openings, "mins_each": FABRICATION_NORMS_MINUTES["qc_check_per_opening"]},
            "Packaging": {"count": max(1, total_openings // 20), "mins_each": FABRICATION_NORMS_MINUTES["packaging_per_batch"]},
        }

        total_minutes = sum(
            op["count"] * op["mins_each"]
            for op in fab.operation_counts.values()
        )
        fab.total_hours = round(total_minutes / 60, 2)
        fab.total_cost_aed = round(fab.total_hours * burn_rate, 2)

        return fab

    def to_dict(self, cl: CompleteCuttingList) -> dict:
        """Serialize cutting list to dict for JSON storage."""
        return {
            "section_a_aluminum": [
                {
                    "die_number": p.die_number,
                    "system_series": p.system_series,
                    "description": p.description,
                    "net_lm": p.net_lm,
                    "wastage_pct": p.wastage_pct,
                    "gross_lm": p.gross_lm,
                    "bars_required": p.bars_required,
                    "weight_kg_m": p.weight_kg_m,
                    "total_weight_kg": p.total_weight_kg,
                    "catalog_price_aed_per_kg": p.catalog_price_aed_per_kg,
                    "lme_price_aed_per_kg": p.lme_price_aed_per_kg,
                    "effective_price_aed_per_kg": p.effective_price_aed_per_kg,
                    "total_cost_aed": p.total_cost_aed,
                }
                for p in cl.profile_summaries
            ],
            "section_b_acp": [
                {
                    "panel_id": p.panel_id,
                    "zone": p.zone,
                    "floor": p.floor,
                    "nominal_w_mm": p.nominal_w_mm,
                    "nominal_h_mm": p.nominal_h_mm,
                    "effective_w_mm": p.effective_w_mm,
                    "effective_h_mm": p.effective_h_mm,
                    "gross_sqm": p.gross_sqm,
                    "finish": p.finish,
                    "quantity": p.quantity,
                    "unit_price_aed_sqm": p.unit_price_aed_sqm,
                    "total_cost_aed": p.total_cost_aed,
                }
                for p in cl.acp_panels
            ],
            "section_c_glass": [
                {
                    "pane_id": g.pane_id,
                    "opening_id": g.opening_id,
                    "glass_type": g.glass_type,
                    "nominal_w_mm": g.nominal_w_mm,
                    "nominal_h_mm": g.nominal_h_mm,
                    "net_area_sqm": g.net_area_sqm,
                    "weight_kg": g.weight_kg,
                    "handling_note": g.handling_note,
                    "quantity": g.quantity,
                    "total_sqm": g.total_sqm,
                    "total_kg": g.total_kg,
                    "unit_price_aed_sqm": g.unit_price_aed_sqm,
                    "total_cost_aed": g.total_cost_aed,
                }
                for g in cl.glass_schedule
            ],
            "section_d_hardware": cl.hardware_schedule,
            "section_e_sealants": cl.sealant_schedule,
            "section_f_fixings": cl.fixing_schedule,
            "section_g_fabrication": {
                "operations": cl.fabrication_labor.operation_counts,
                "total_hours": cl.fabrication_labor.total_hours,
                "burn_rate_aed_hr": cl.fabrication_labor.burn_rate_aed_hr,
                "total_cost_aed": cl.fabrication_labor.total_cost_aed,
            },
            "cost_summary": {
                "aluminum": round(cl.total_aluminum_cost_aed, 2),
                "glass": round(cl.total_glass_cost_aed, 2),
                "acp": round(cl.total_acp_cost_aed, 2),
                "hardware": round(cl.total_hardware_cost_aed, 2),
                "sealants": round(cl.total_sealant_cost_aed, 2),
                "fixings": round(cl.total_fixing_cost_aed, 2),
                "fabrication": round(cl.total_fabrication_cost_aed, 2),
                "grand_total": round(cl.grand_total_direct_cost_aed, 2),
            },
            "weight_summary": {
                "aluminum_kg": round(cl.aluminum_kg, 1),
                "glass_kg": round(cl.glass_kg, 1),
                "acp_kg": round(cl.acp_kg, 1),
                "total_kg": round(cl.total_kg, 1),
                "total_tonnes": round(cl.total_kg / 1000, 2),
                "truck_loads": cl.truck_loads,
            },
        }

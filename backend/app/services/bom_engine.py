"""
BOM Explosion Engine — generates comprehensive line-item Bill of Materials from opening schedule.

For each opening (width x height x system_type), queries catalog_items to find
matched profile item_codes and explodes them into quantities using parametric formulas.

Covers ALL material categories required for a real UAE facade estimate:
- Aluminum extrusions (mullions, transoms, pressure plates, capping, thermal breaks)
- Glass (DGU, tempered, laminated, spandrel)
- ACP cladding (panels, substructure, brackets)
- Glass balustrades (tempered/laminated glass, SS posts, handrails)
- Spider glazing (point-fixed glass, spider fittings, structural rods)
- Shopfront / ground floor retail glazing
- Structural steel substructure (brackets, angles, channels, anchors)
- Sealants & gaskets (weather seals, fire-rated, expansion joints)
- Hardware (handles, locks, hinges, restrictors, closers)
- Fixings (chemical anchors, expansion bolts, self-drilling screws, rivets)
- Surface treatment (powder coating, anodizing)
- Fabrication labor
- Installation labor (site)
- Site mobilization, scaffolding, lifting equipment
- Testing & commissioning (water test, air infiltration)
- Protective film, packaging, transport
- Provisional sums (GPR, water test)
- Attic stock (2% Blind Spot Rule)

Fallback: if no catalog items matched, uses standard UAE facade industry ratios.
"""
import logging
import math
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger("masaad-bom")


# ── UAE Market Rates (AED) — realistic 2025/2026 prices ───────────────────────
# These are default fallbacks; catalog-driven rates take priority when available.

UAE_RATES = {
    # Aluminum
    "aluminum_extrusion_aed_kg": 9.45,          # LME ~7 + extrusion + coating
    "aluminum_mullion_aed_kg": 9.80,
    "aluminum_transom_aed_kg": 9.80,
    "aluminum_pressure_plate_aed_kg": 10.50,
    "aluminum_capping_aed_kg": 11.00,
    "thermal_break_aed_lm": 8.50,

    # Glass
    "glass_dgu_6_12_6_aed_sqm": 175.0,          # clear DGU
    "glass_dgu_low_e_aed_sqm": 220.0,           # low-E DGU
    "glass_tempered_clear_aed_sqm": 95.0,        # 10mm tempered
    "glass_tempered_tinted_aed_sqm": 110.0,
    "glass_laminated_6_6_aed_sqm": 135.0,        # 6+6 laminated
    "glass_spandrel_aed_sqm": 145.0,             # opaque spandrel
    "glass_structural_dgu_aed_sqm": 285.0,       # structural glazing DGU
    "glass_balustrade_aed_sqm": 185.0,           # 12mm tempered/laminated
    "glass_spider_aed_sqm": 310.0,               # point-fixed

    # ACP
    "acp_pvdf_4mm_aed_sqm": 85.0,               # PVDF-coated 4mm ACP
    "acp_pe_4mm_aed_sqm": 55.0,                 # PE-coated (fire-rated not allowed)
    "acp_fr_4mm_aed_sqm": 105.0,                # fire-rated A2 core
    "acp_substructure_aed_sqm": 45.0,            # aluminum top-hat/omega profiles
    "acp_bracket_aed_nr": 12.0,                  # L-bracket per fixing point

    # Structural Steel / Substructure
    "ms_bracket_aed_kg": 6.50,                   # mild steel brackets
    "ss_post_aed_nr": 280.0,                     # stainless steel balustrade post
    "ss_handrail_aed_lm": 95.0,                  # SS handrail per lm
    "spider_fitting_aed_nr": 450.0,              # 4-arm spider fitting
    "structural_cable_aed_lm": 85.0,             # structural cable/rod

    # Sealants & Gaskets
    "silicone_structural_600ml_aed": 28.0,       # structural silicone per tube
    "silicone_weather_310ml_aed": 15.0,          # weather seal per tube
    "silicone_fire_rated_aed": 42.0,             # fire-rated sealant per tube
    "epdm_gasket_aed_lm": 4.50,                 # EPDM gasket per lm
    "expansion_joint_aed_lm": 35.0,              # expansion joint profile
    "backer_rod_aed_lm": 1.20,                   # backer rod per lm

    # Hardware
    "handle_casement_aed": 25.0,
    "hinge_pair_casement_aed": 35.0,
    "lock_casement_aed": 45.0,
    "restrictor_aed": 18.0,
    "door_handle_set_aed": 85.0,
    "mortice_lock_aed": 120.0,
    "door_closer_aed": 175.0,
    "door_hinge_set_aed": 55.0,
    "floor_spring_aed": 650.0,
    "patch_fitting_set_aed": 320.0,
    "auto_door_operator_aed": 4500.0,

    # Fixings
    "chemical_anchor_m12_aed": 8.50,
    "expansion_bolt_m10_aed": 3.50,
    "self_drill_screw_aed": 0.35,
    "rivet_aed": 0.15,
    "bracket_80mm_aed": 4.50,
    "bracket_120mm_aed": 6.50,
    "shim_plate_aed": 2.50,
    "thermal_pad_aed": 3.00,

    # Surface Treatment
    "powder_coating_aed_sqm": 22.0,              # standard RAL color
    "anodizing_aed_sqm": 35.0,                   # 20-micron anodizing

    # EPDM / Spacer / Gasket
    "setting_block_aed": 3.50,                   # EPDM setting block each
    "spacer_bar_aed_lm": 12.0,                   # warm-edge spacer bar
    "distance_piece_aed": 2.00,

    # Labor
    "fab_labor_aed_hr": 13.0,                    # factory fabrication
    "install_labor_aed_hr": 18.0,                # site installation

    # Site / Logistics
    "scaffolding_aed_sqm_month": 12.0,           # per sqm per month
    "crane_hire_aed_day": 1800.0,
    "transport_aed_per_truck": 850.0,
    "protective_film_aed_sqm": 3.50,
    "packaging_aed_sqm": 5.00,

    # Testing & Commissioning
    "water_test_aed_per_test": 2500.0,
    "air_test_aed_per_test": 3500.0,

    # Provisional Sums
    "gpr_provisional_aed": 15000.0,              # ground penetrating radar
    "water_test_provisional_aed": 25000.0,

    # Mobilization
    "site_mobilization_aed": 35000.0,
}


# ── Standard material ratios (fallback when no catalog match) ─────────────────
# Based on UAE facade industry norms for aluminum curtain wall / window systems

SYSTEM_RATIOS: Dict[str, Dict] = {
    "Curtain Wall": {
        "aluminum_kg_sqm": 12.5,       # kg of aluminum extrusion per SQM
        "glass_sqm_per_sqm": 0.85,     # 85% glazing ratio
        "silicone_ml_per_lm": 120,     # structural silicone per linear metre
        "setting_block_per_sqm": 4,    # EPDM setting blocks
        "spacer_lm_per_sqm": 1.2,     # thermal spacer bar
        "fab_labor_hr_per_sqm": 3.5,   # fabrication hours
        "install_labor_hr_per_sqm": 2.5,  # installation hours
        # Curtain wall specific breakdowns (% of total aluminum weight)
        "mullion_pct": 0.35,
        "transom_pct": 0.25,
        "pressure_plate_pct": 0.15,
        "capping_pct": 0.10,
        "thermal_break_lm_per_sqm": 2.0,
        # Hardware per opening
        "handle_per_opening": 0,       # curtain wall has no operable hardware
        "lock_per_opening": 0,
        "hinge_per_opening": 0,
        # Fixings
        "anchor_per_sqm": 2.0,
        "bracket_per_sqm": 1.5,
        "screw_per_sqm": 8,
        # Sealants breakdown
        "weatherseal_ml_per_lm": 40,
        "fire_sealant_ml_per_floor": 600,
        "epdm_gasket_lm_per_sqm": 3.0,
        "backer_rod_lm_per_sqm": 2.0,
        # Surface treatment
        "surface_sqm_per_sqm": 0.85,   # powder-coated aluminum surface
    },
    "Sliding Door": {
        "aluminum_kg_sqm": 9.8,
        "glass_sqm_per_sqm": 0.80,
        "silicone_ml_per_lm": 80,
        "setting_block_per_sqm": 4,
        "spacer_lm_per_sqm": 1.0,
        "fab_labor_hr_per_sqm": 4.2,
        "install_labor_hr_per_sqm": 3.0,
        "mullion_pct": 0.30,
        "transom_pct": 0.20,
        "pressure_plate_pct": 0.10,
        "capping_pct": 0.10,
        "thermal_break_lm_per_sqm": 1.5,
        "handle_per_opening": 1,
        "lock_per_opening": 1,
        "hinge_per_opening": 0,
        "anchor_per_sqm": 1.5,
        "bracket_per_sqm": 1.0,
        "screw_per_sqm": 6,
        "weatherseal_ml_per_lm": 30,
        "fire_sealant_ml_per_floor": 0,
        "epdm_gasket_lm_per_sqm": 2.5,
        "backer_rod_lm_per_sqm": 1.5,
        "surface_sqm_per_sqm": 0.70,
    },
    "Casement Window": {
        "aluminum_kg_sqm": 11.2,
        "glass_sqm_per_sqm": 0.78,
        "silicone_ml_per_lm": 80,
        "setting_block_per_sqm": 4,
        "spacer_lm_per_sqm": 1.0,
        "fab_labor_hr_per_sqm": 4.8,
        "install_labor_hr_per_sqm": 2.8,
        "mullion_pct": 0.30,
        "transom_pct": 0.20,
        "pressure_plate_pct": 0.10,
        "capping_pct": 0.10,
        "thermal_break_lm_per_sqm": 1.8,
        "handle_per_opening": 1,
        "lock_per_opening": 1,
        "hinge_per_opening": 1,
        "anchor_per_sqm": 1.5,
        "bracket_per_sqm": 1.0,
        "screw_per_sqm": 6,
        "weatherseal_ml_per_lm": 30,
        "fire_sealant_ml_per_floor": 0,
        "epdm_gasket_lm_per_sqm": 2.5,
        "backer_rod_lm_per_sqm": 1.5,
        "surface_sqm_per_sqm": 0.75,
    },
    "Fixed Window": {
        "aluminum_kg_sqm": 8.5,
        "glass_sqm_per_sqm": 0.88,
        "silicone_ml_per_lm": 100,
        "setting_block_per_sqm": 4,
        "spacer_lm_per_sqm": 1.1,
        "fab_labor_hr_per_sqm": 2.8,
        "install_labor_hr_per_sqm": 2.0,
        "mullion_pct": 0.30,
        "transom_pct": 0.25,
        "pressure_plate_pct": 0.15,
        "capping_pct": 0.10,
        "thermal_break_lm_per_sqm": 1.5,
        "handle_per_opening": 0,
        "lock_per_opening": 0,
        "hinge_per_opening": 0,
        "anchor_per_sqm": 1.5,
        "bracket_per_sqm": 1.0,
        "screw_per_sqm": 6,
        "weatherseal_ml_per_lm": 30,
        "fire_sealant_ml_per_floor": 0,
        "epdm_gasket_lm_per_sqm": 2.0,
        "backer_rod_lm_per_sqm": 1.5,
        "surface_sqm_per_sqm": 0.65,
    },
    "ACP Cladding": {
        "aluminum_kg_sqm": 6.0,        # sub-frame only (ACP itself priced separately)
        "glass_sqm_per_sqm": 0.0,
        "silicone_ml_per_lm": 60,
        "setting_block_per_sqm": 0,
        "spacer_lm_per_sqm": 0,
        "fab_labor_hr_per_sqm": 2.2,
        "install_labor_hr_per_sqm": 2.5,
        "mullion_pct": 0,
        "transom_pct": 0,
        "pressure_plate_pct": 0,
        "capping_pct": 0,
        "thermal_break_lm_per_sqm": 0,
        "handle_per_opening": 0,
        "lock_per_opening": 0,
        "hinge_per_opening": 0,
        "anchor_per_sqm": 2.5,
        "bracket_per_sqm": 3.0,        # ACP needs more brackets
        "screw_per_sqm": 12,
        "weatherseal_ml_per_lm": 20,
        "fire_sealant_ml_per_floor": 0,
        "epdm_gasket_lm_per_sqm": 0,
        "backer_rod_lm_per_sqm": 1.0,
        "surface_sqm_per_sqm": 0,      # ACP is pre-finished
    },
    "Glass Balustrade": {
        "aluminum_kg_sqm": 3.0,        # minimal framing
        "glass_sqm_per_sqm": 0.95,
        "silicone_ml_per_lm": 60,
        "setting_block_per_sqm": 2,
        "spacer_lm_per_sqm": 0,
        "fab_labor_hr_per_sqm": 3.0,
        "install_labor_hr_per_sqm": 3.5,
        "mullion_pct": 0,
        "transom_pct": 0,
        "pressure_plate_pct": 0,
        "capping_pct": 0,
        "thermal_break_lm_per_sqm": 0,
        "handle_per_opening": 0,
        "lock_per_opening": 0,
        "hinge_per_opening": 0,
        "anchor_per_sqm": 3.0,
        "bracket_per_sqm": 0,
        "screw_per_sqm": 4,
        "weatherseal_ml_per_lm": 20,
        "fire_sealant_ml_per_floor": 0,
        "epdm_gasket_lm_per_sqm": 1.0,
        "backer_rod_lm_per_sqm": 0.5,
        "surface_sqm_per_sqm": 0.2,
        # Balustrade-specific
        "ss_post_per_lm": 0.8,         # SS posts every 1.2m
        "handrail_lm_per_sqm": 0.5,
    },
    "Spider Glazing": {
        "aluminum_kg_sqm": 2.0,
        "glass_sqm_per_sqm": 0.92,
        "silicone_ml_per_lm": 80,
        "setting_block_per_sqm": 0,
        "spacer_lm_per_sqm": 0,
        "fab_labor_hr_per_sqm": 4.0,
        "install_labor_hr_per_sqm": 5.0,
        "mullion_pct": 0,
        "transom_pct": 0,
        "pressure_plate_pct": 0,
        "capping_pct": 0,
        "thermal_break_lm_per_sqm": 0,
        "handle_per_opening": 0,
        "lock_per_opening": 0,
        "hinge_per_opening": 0,
        "anchor_per_sqm": 2.0,
        "bracket_per_sqm": 0,
        "screw_per_sqm": 4,
        "weatherseal_ml_per_lm": 30,
        "fire_sealant_ml_per_floor": 0,
        "epdm_gasket_lm_per_sqm": 0.5,
        "backer_rod_lm_per_sqm": 0.5,
        "surface_sqm_per_sqm": 0.1,
        # Spider-specific
        "spider_fitting_per_sqm": 0.25,  # ~1 per 4 sqm
        "structural_cable_lm_per_sqm": 0.5,
    },
    "Shopfront": {
        "aluminum_kg_sqm": 10.0,
        "glass_sqm_per_sqm": 0.82,
        "silicone_ml_per_lm": 90,
        "setting_block_per_sqm": 4,
        "spacer_lm_per_sqm": 1.0,
        "fab_labor_hr_per_sqm": 4.5,
        "install_labor_hr_per_sqm": 3.5,
        "mullion_pct": 0.30,
        "transom_pct": 0.25,
        "pressure_plate_pct": 0.10,
        "capping_pct": 0.10,
        "thermal_break_lm_per_sqm": 1.5,
        "handle_per_opening": 1,
        "lock_per_opening": 1,
        "hinge_per_opening": 0,
        "anchor_per_sqm": 2.0,
        "bracket_per_sqm": 1.5,
        "screw_per_sqm": 8,
        "weatherseal_ml_per_lm": 35,
        "fire_sealant_ml_per_floor": 0,
        "epdm_gasket_lm_per_sqm": 2.5,
        "backer_rod_lm_per_sqm": 1.5,
        "surface_sqm_per_sqm": 0.75,
        # Shopfront-specific
        "auto_door_per_opening": 0,     # set to 1 if entrance has automatic doors
        "floor_spring_per_opening": 1,
    },
    "DEFAULT": {
        "aluminum_kg_sqm": 10.0,
        "glass_sqm_per_sqm": 0.82,
        "silicone_ml_per_lm": 100,
        "setting_block_per_sqm": 4,
        "spacer_lm_per_sqm": 1.0,
        "fab_labor_hr_per_sqm": 3.5,
        "install_labor_hr_per_sqm": 2.5,
        "mullion_pct": 0.30,
        "transom_pct": 0.25,
        "pressure_plate_pct": 0.15,
        "capping_pct": 0.10,
        "thermal_break_lm_per_sqm": 1.5,
        "handle_per_opening": 0,
        "lock_per_opening": 0,
        "hinge_per_opening": 0,
        "anchor_per_sqm": 1.5,
        "bracket_per_sqm": 1.0,
        "screw_per_sqm": 6,
        "weatherseal_ml_per_lm": 30,
        "fire_sealant_ml_per_floor": 0,
        "epdm_gasket_lm_per_sqm": 2.0,
        "backer_rod_lm_per_sqm": 1.5,
        "surface_sqm_per_sqm": 0.70,
    },
}

# Attic stock factor (Blind Spot Rule: 2% added to all quantities)
ATTIC_STOCK_PCT = 0.02


@dataclass
class BOMLineItem:
    item_code: str
    description: str
    category: str           # ALUMINUM | GLASS | ACP | HARDWARE | SEALANT | FIXING | SURFACE | LABOR | SITE | TESTING | PROVISIONAL
    unit: str               # kg / sqm / lm / nr / hr / lot / set / month
    quantity: float
    unit_cost_aed: float = 0.0
    subtotal_aed: float = 0.0
    is_attic_stock: bool = False
    source_opening_id: str = ""
    notes: str = ""


def _r(val: float, digits: int = 2) -> float:
    """Round helper."""
    return round(val, digits)


class BOMEngine:

    def explode_opening(
        self,
        opening: Dict[str, Any],
        catalog_items: List[Dict[str, Any]],
        lme_aed_per_kg: float = 7.0,
        labor_burn_rate: float = 13.0,
        rates: Optional[Dict[str, float]] = None,
    ) -> List[BOMLineItem]:
        """
        Explode a single opening into comprehensive BOM line items.

        Args:
            opening: dict with keys: id, width_mm, height_mm, system_type, quantity
            catalog_items: list of CatalogItem dicts for this tenant
            lme_aed_per_kg: current LME aluminum price in AED/kg
            labor_burn_rate: fully burdened labor rate in AED/hr
            rates: optional dict overriding UAE_RATES defaults

        Returns:
            List of BOMLineItem objects
        """
        R = dict(UAE_RATES)
        if rates:
            R.update(rates)

        width_mm = float(opening.get("width_mm", 1000))
        height_mm = float(opening.get("height_mm", 2000))
        qty = int(opening.get("quantity", 1))
        system_type = opening.get("system_type", "DEFAULT")
        opening_id = str(opening.get("id", ""))
        floors = int(opening.get("floors", 1))

        width_m = width_mm / 1000
        height_m = height_mm / 1000
        sqm_each = width_m * height_m
        sqm_total = sqm_each * qty
        perimeter_m_each = 2 * (width_m + height_m)
        perimeter_m = perimeter_m_each * qty

        # Get ratio for this system type (fuzzy match)
        ratio = self._get_ratio(system_type)
        items: List[BOMLineItem] = []

        # Effective aluminum rate: LME-derived or from rates dict
        alu_rate = lme_aed_per_kg * 1.35  # LME + extrusion + coating margin

        # ══════════════════════════════════════════════════════════════════════
        # 1. ALUMINUM EXTRUSIONS — detailed breakdown
        # ══════════════════════════════════════════════════════════════════════
        alum_kg_total = _r(sqm_total * ratio["aluminum_kg_sqm"], 3)
        alum_catalog = [c for c in catalog_items if c.get("material_type") == "ALUMINUM_EXTRUSION"]

        if alum_catalog:
            profiles_for_system = self._match_profiles(alum_catalog, system_type)
            if profiles_for_system:
                kg_per_profile = alum_kg_total / len(profiles_for_system)
                for profile in profiles_for_system:
                    weight_per_m = float(profile.get("weight_per_meter") or profile.get("weight_kg_m") or 1.5)
                    length_m = _r(kg_per_profile / weight_per_m, 3)
                    unit_cost = float(profile.get("price_aed_per_kg") or alu_rate)
                    items.append(BOMLineItem(
                        item_code=profile.get("item_code", "ALU-UNKNOWN"),
                        description=profile.get("description") or profile.get("system_series", ""),
                        category="ALUMINUM",
                        unit="lm",
                        quantity=length_m,
                        unit_cost_aed=_r(unit_cost * weight_per_m),
                        subtotal_aed=_r(length_m * unit_cost * weight_per_m),
                        source_opening_id=opening_id,
                    ))
            else:
                self._add_generic_alu_breakdown(items, alum_kg_total, ratio, alu_rate, opening_id, system_type)
        else:
            self._add_generic_alu_breakdown(items, alum_kg_total, ratio, alu_rate, opening_id, system_type)

        # Thermal breaks
        tb_lm = _r(sqm_total * ratio.get("thermal_break_lm_per_sqm", 0), 2)
        if tb_lm > 0:
            tb_rate = R["thermal_break_aed_lm"]
            items.append(BOMLineItem(
                item_code="ALU-THERMAL-BREAK",
                description="Polyamide thermal break strip",
                category="ALUMINUM",
                unit="lm",
                quantity=tb_lm,
                unit_cost_aed=tb_rate,
                subtotal_aed=_r(tb_lm * tb_rate),
                source_opening_id=opening_id,
            ))

        # ══════════════════════════════════════════════════════════════════════
        # 2. GLASS
        # ══════════════════════════════════════════════════════════════════════
        glass_sqm = _r(sqm_total * ratio["glass_sqm_per_sqm"], 3)
        if glass_sqm > 0:
            glass_catalog = [c for c in catalog_items if c.get("material_type") == "GLASS_PERFORMANCE"]
            sys_lower = system_type.lower()

            if "balustrade" in sys_lower:
                glass_rate = R["glass_balustrade_aed_sqm"]
                glass_code = "GLS-BALUSTRADE"
                glass_desc = "Tempered/laminated balustrade glass 12mm"
            elif "spider" in sys_lower:
                glass_rate = R["glass_spider_aed_sqm"]
                glass_code = "GLS-SPIDER"
                glass_desc = "Point-fixed structural glass (DGU)"
            elif "shopfront" in sys_lower or "retail" in sys_lower:
                glass_rate = R["glass_tempered_clear_aed_sqm"]
                glass_code = "GLS-SHOPFRONT"
                glass_desc = "Toughened clear glass 10mm (shopfront)"
            elif glass_catalog:
                g = glass_catalog[0]
                glass_rate = float(g.get("price_aed_sqm") or R["glass_dgu_6_12_6_aed_sqm"])
                glass_code = g.get("item_code", "GLS-CATALOG")
                glass_desc = g.get("glass_makeup") or g.get("description") or "Performance glazing (DGU)"
            else:
                glass_rate = R["glass_dgu_6_12_6_aed_sqm"]
                glass_code = "GLS-DGU-6-12-6"
                glass_desc = "Double glazed unit 6-12Ar-6mm clear"

            items.append(BOMLineItem(
                item_code=glass_code,
                description=glass_desc,
                category="GLASS",
                unit="sqm",
                quantity=glass_sqm,
                unit_cost_aed=glass_rate,
                subtotal_aed=_r(glass_sqm * glass_rate),
                source_opening_id=opening_id,
            ))

            # Spandrel glass (10% of curtain wall glazing area for vision/spandrel mix)
            if "curtain" in sys_lower:
                spandrel_sqm = _r(glass_sqm * 0.10, 3)
                if spandrel_sqm > 0:
                    sp_rate = R["glass_spandrel_aed_sqm"]
                    items.append(BOMLineItem(
                        item_code="GLS-SPANDREL",
                        description="Opaque spandrel glass (back-painted)",
                        category="GLASS",
                        unit="sqm",
                        quantity=spandrel_sqm,
                        unit_cost_aed=sp_rate,
                        subtotal_aed=_r(spandrel_sqm * sp_rate),
                        source_opening_id=opening_id,
                    ))

        # ══════════════════════════════════════════════════════════════════════
        # 3. ACP CLADDING (only for ACP system type)
        # ══════════════════════════════════════════════════════════════════════
        if "acp" in system_type.lower():
            acp_sqm = _r(sqm_total * 1.05, 3)  # 5% waste allowance
            acp_rate = R["acp_pvdf_4mm_aed_sqm"]
            items.append(BOMLineItem(
                item_code="ACP-PVDF-4MM",
                description="ACP panel 4mm PVDF coated (fire-rated A2 core)",
                category="ACP",
                unit="sqm",
                quantity=acp_sqm,
                unit_cost_aed=acp_rate,
                subtotal_aed=_r(acp_sqm * acp_rate),
                source_opening_id=opening_id,
            ))

            # ACP substructure (top-hat/omega profiles)
            sub_rate = R["acp_substructure_aed_sqm"]
            items.append(BOMLineItem(
                item_code="ACP-SUBSTRUCTURE",
                description="ACP aluminum substructure (top-hat/omega profiles)",
                category="ACP",
                unit="sqm",
                quantity=sqm_total,
                unit_cost_aed=sub_rate,
                subtotal_aed=_r(sqm_total * sub_rate),
                source_opening_id=opening_id,
            ))

            # ACP brackets
            bracket_count = _r(sqm_total * ratio.get("bracket_per_sqm", 3.0))
            if bracket_count > 0:
                brk_rate = R["acp_bracket_aed_nr"]
                items.append(BOMLineItem(
                    item_code="ACP-BRACKET-L",
                    description="ACP L-bracket fixing (galvanized)",
                    category="ACP",
                    unit="nr",
                    quantity=bracket_count,
                    unit_cost_aed=brk_rate,
                    subtotal_aed=_r(bracket_count * brk_rate),
                    source_opening_id=opening_id,
                ))

        # ══════════════════════════════════════════════════════════════════════
        # 4. GLASS BALUSTRADE specifics
        # ══════════════════════════════════════════════════════════════════════
        if "balustrade" in system_type.lower():
            # Stainless steel posts
            post_per_lm = ratio.get("ss_post_per_lm", 0.8)
            total_length_lm = _r(width_m * qty, 2)
            post_count = max(math.ceil(total_length_lm * post_per_lm), qty * 2)
            items.append(BOMLineItem(
                item_code="SS-POST-BALUSTRADE",
                description="Stainless steel 316 balustrade post (50x50mm)",
                category="HARDWARE",
                unit="nr",
                quantity=float(post_count),
                unit_cost_aed=R["ss_post_aed_nr"],
                subtotal_aed=_r(post_count * R["ss_post_aed_nr"]),
                source_opening_id=opening_id,
            ))

            # Handrail
            hr_lm = _r(total_length_lm * ratio.get("handrail_lm_per_sqm", 1.0), 2)
            if hr_lm > 0:
                items.append(BOMLineItem(
                    item_code="SS-HANDRAIL",
                    description="Stainless steel 316 handrail (round 50mm)",
                    category="HARDWARE",
                    unit="lm",
                    quantity=hr_lm,
                    unit_cost_aed=R["ss_handrail_aed_lm"],
                    subtotal_aed=_r(hr_lm * R["ss_handrail_aed_lm"]),
                    source_opening_id=opening_id,
                ))

        # ══════════════════════════════════════════════════════════════════════
        # 5. SPIDER GLAZING specifics
        # ══════════════════════════════════════════════════════════════════════
        if "spider" in system_type.lower():
            # Spider fittings
            fitting_count = max(math.ceil(sqm_total * ratio.get("spider_fitting_per_sqm", 0.25)), qty)
            items.append(BOMLineItem(
                item_code="HW-SPIDER-4ARM",
                description="Spider fitting 4-arm (stainless steel 316)",
                category="HARDWARE",
                unit="nr",
                quantity=float(fitting_count),
                unit_cost_aed=R["spider_fitting_aed_nr"],
                subtotal_aed=_r(fitting_count * R["spider_fitting_aed_nr"]),
                source_opening_id=opening_id,
            ))

            # Structural cables/rods
            cable_lm = _r(sqm_total * ratio.get("structural_cable_lm_per_sqm", 0.5), 2)
            if cable_lm > 0:
                items.append(BOMLineItem(
                    item_code="STR-CABLE-SS",
                    description="Structural stainless steel cable/rod",
                    category="HARDWARE",
                    unit="lm",
                    quantity=cable_lm,
                    unit_cost_aed=R["structural_cable_aed_lm"],
                    subtotal_aed=_r(cable_lm * R["structural_cable_aed_lm"]),
                    source_opening_id=opening_id,
                ))

        # ══════════════════════════════════════════════════════════════════════
        # 6. SHOPFRONT specifics
        # ══════════════════════════════════════════════════════════════════════
        if "shopfront" in system_type.lower() or "retail" in system_type.lower():
            # Floor spring (1 per door opening)
            fs_count = ratio.get("floor_spring_per_opening", 0) * qty
            if fs_count > 0:
                items.append(BOMLineItem(
                    item_code="HW-FLOOR-SPRING",
                    description="Floor spring (heavy duty, concealed)",
                    category="HARDWARE",
                    unit="nr",
                    quantity=float(fs_count),
                    unit_cost_aed=R["floor_spring_aed"],
                    subtotal_aed=_r(fs_count * R["floor_spring_aed"]),
                    source_opening_id=opening_id,
                ))

            # Patch fittings
            patch_count = qty * 2  # top + bottom per door
            items.append(BOMLineItem(
                item_code="HW-PATCH-SET",
                description="Patch fitting set (top + bottom, stainless)",
                category="HARDWARE",
                unit="set",
                quantity=float(patch_count),
                unit_cost_aed=R["patch_fitting_set_aed"],
                subtotal_aed=_r(patch_count * R["patch_fitting_set_aed"]),
                source_opening_id=opening_id,
            ))

        # ══════════════════════════════════════════════════════════════════════
        # 7. SEALANTS & GASKETS
        # ══════════════════════════════════════════════════════════════════════
        # Structural silicone
        silicone_ml = round(perimeter_m * ratio["silicone_ml_per_lm"])
        silicone_tubes = math.ceil(silicone_ml / 600) if silicone_ml > 0 else 0
        if silicone_tubes > 0:
            items.append(BOMLineItem(
                item_code="SIL-STRUCTURAL",
                description="Structural silicone sealant (600ml cartridge)",
                category="SEALANT",
                unit="nr",
                quantity=float(silicone_tubes),
                unit_cost_aed=R["silicone_structural_600ml_aed"],
                subtotal_aed=_r(silicone_tubes * R["silicone_structural_600ml_aed"]),
                source_opening_id=opening_id,
            ))

        # Weather seal silicone
        ws_ml = round(perimeter_m * ratio.get("weatherseal_ml_per_lm", 30))
        ws_tubes = math.ceil(ws_ml / 310) if ws_ml > 0 else 0
        if ws_tubes > 0:
            items.append(BOMLineItem(
                item_code="SIL-WEATHERSEAL",
                description="Weather seal silicone sealant (310ml)",
                category="SEALANT",
                unit="nr",
                quantity=float(ws_tubes),
                unit_cost_aed=R["silicone_weather_310ml_aed"],
                subtotal_aed=_r(ws_tubes * R["silicone_weather_310ml_aed"]),
                source_opening_id=opening_id,
            ))

        # Fire-rated sealant (per floor for curtain wall)
        fire_ml = ratio.get("fire_sealant_ml_per_floor", 0) * max(floors, 1)
        fire_tubes = math.ceil(fire_ml / 310) if fire_ml > 0 else 0
        if fire_tubes > 0:
            items.append(BOMLineItem(
                item_code="SIL-FIRE-RATED",
                description="Fire-rated sealant (intumescent, 310ml)",
                category="SEALANT",
                unit="nr",
                quantity=float(fire_tubes),
                unit_cost_aed=R["silicone_fire_rated_aed"],
                subtotal_aed=_r(fire_tubes * R["silicone_fire_rated_aed"]),
                source_opening_id=opening_id,
            ))

        # EPDM gaskets
        epdm_lm = _r(sqm_total * ratio.get("epdm_gasket_lm_per_sqm", 2.0), 2)
        if epdm_lm > 0:
            items.append(BOMLineItem(
                item_code="GSK-EPDM",
                description="EPDM rubber gasket (continuous)",
                category="SEALANT",
                unit="lm",
                quantity=epdm_lm,
                unit_cost_aed=R["epdm_gasket_aed_lm"],
                subtotal_aed=_r(epdm_lm * R["epdm_gasket_aed_lm"]),
                source_opening_id=opening_id,
            ))

        # Backer rod
        br_lm = _r(sqm_total * ratio.get("backer_rod_lm_per_sqm", 1.5), 2)
        if br_lm > 0:
            items.append(BOMLineItem(
                item_code="GSK-BACKER-ROD",
                description="Backer rod 10mm (polyethylene)",
                category="SEALANT",
                unit="lm",
                quantity=br_lm,
                unit_cost_aed=R["backer_rod_aed_lm"],
                subtotal_aed=_r(br_lm * R["backer_rod_aed_lm"]),
                source_opening_id=opening_id,
            ))

        # Expansion joints (1 per 6m for curtain wall)
        if "curtain" in system_type.lower() and sqm_total > 50:
            exp_lm = _r(height_m * math.ceil(width_m * qty / 6), 2)
            if exp_lm > 0:
                items.append(BOMLineItem(
                    item_code="GSK-EXPANSION",
                    description="Expansion joint profile (EPDM + aluminum)",
                    category="SEALANT",
                    unit="lm",
                    quantity=exp_lm,
                    unit_cost_aed=R["expansion_joint_aed_lm"],
                    subtotal_aed=_r(exp_lm * R["expansion_joint_aed_lm"]),
                    source_opening_id=opening_id,
                ))

        # ══════════════════════════════════════════════════════════════════════
        # 8. HARDWARE (handles, locks, hinges, restrictors)
        # ══════════════════════════════════════════════════════════════════════
        handle_count = ratio.get("handle_per_opening", 0) * qty
        if handle_count > 0:
            is_door = any(kw in system_type.lower() for kw in ["door", "entrance", "shopfront"])
            if is_door:
                items.append(BOMLineItem(
                    item_code="HW-DOOR-HANDLE",
                    description="Door handle set (lever, SS finish)",
                    category="HARDWARE",
                    unit="set",
                    quantity=float(handle_count),
                    unit_cost_aed=R["door_handle_set_aed"],
                    subtotal_aed=_r(handle_count * R["door_handle_set_aed"]),
                    source_opening_id=opening_id,
                ))
            else:
                items.append(BOMLineItem(
                    item_code="HW-CASEMENT-HANDLE",
                    description="Casement window handle (espagnolette)",
                    category="HARDWARE",
                    unit="nr",
                    quantity=float(handle_count),
                    unit_cost_aed=R["handle_casement_aed"],
                    subtotal_aed=_r(handle_count * R["handle_casement_aed"]),
                    source_opening_id=opening_id,
                ))

        lock_count = ratio.get("lock_per_opening", 0) * qty
        if lock_count > 0:
            is_door = any(kw in system_type.lower() for kw in ["door", "entrance", "shopfront"])
            if is_door:
                items.append(BOMLineItem(
                    item_code="HW-MORTICE-LOCK",
                    description="Mortice lock (5-lever, SS)",
                    category="HARDWARE",
                    unit="nr",
                    quantity=float(lock_count),
                    unit_cost_aed=R["mortice_lock_aed"],
                    subtotal_aed=_r(lock_count * R["mortice_lock_aed"]),
                    source_opening_id=opening_id,
                ))
            else:
                items.append(BOMLineItem(
                    item_code="HW-CASEMENT-LOCK",
                    description="Casement window multi-point lock",
                    category="HARDWARE",
                    unit="nr",
                    quantity=float(lock_count),
                    unit_cost_aed=R["lock_casement_aed"],
                    subtotal_aed=_r(lock_count * R["lock_casement_aed"]),
                    source_opening_id=opening_id,
                ))

        hinge_count = ratio.get("hinge_per_opening", 0) * qty
        if hinge_count > 0:
            items.append(BOMLineItem(
                item_code="HW-HINGE-PAIR",
                description="Friction hinge pair (stainless steel)",
                category="HARDWARE",
                unit="pair",
                quantity=float(hinge_count),
                unit_cost_aed=R["hinge_pair_casement_aed"],
                subtotal_aed=_r(hinge_count * R["hinge_pair_casement_aed"]),
                source_opening_id=opening_id,
            ))

        # Window restrictor for casement windows
        if "casement" in system_type.lower():
            restrictor_count = qty
            items.append(BOMLineItem(
                item_code="HW-RESTRICTOR",
                description="Window opening restrictor (safety)",
                category="HARDWARE",
                unit="nr",
                quantity=float(restrictor_count),
                unit_cost_aed=R["restrictor_aed"],
                subtotal_aed=_r(restrictor_count * R["restrictor_aed"]),
                source_opening_id=opening_id,
            ))

        # Door closer for doors
        if any(kw in system_type.lower() for kw in ["door", "entrance"]) and "sliding" not in system_type.lower():
            closer_count = qty
            items.append(BOMLineItem(
                item_code="HW-DOOR-CLOSER",
                description="Overhead door closer (EN 1154 size 3-5)",
                category="HARDWARE",
                unit="nr",
                quantity=float(closer_count),
                unit_cost_aed=R["door_closer_aed"],
                subtotal_aed=_r(closer_count * R["door_closer_aed"]),
                source_opening_id=opening_id,
            ))

        # EPDM setting blocks
        setting_blocks = round(sqm_total * ratio["setting_block_per_sqm"])
        if setting_blocks > 0:
            items.append(BOMLineItem(
                item_code="HW-EPDM-BLOCK",
                description="EPDM setting block 100x28x6mm",
                category="HARDWARE",
                unit="nr",
                quantity=float(setting_blocks),
                unit_cost_aed=R["setting_block_aed"],
                subtotal_aed=_r(setting_blocks * R["setting_block_aed"]),
                source_opening_id=opening_id,
            ))

        # Warm-edge spacer bar
        spacer_lm = _r(sqm_total * ratio["spacer_lm_per_sqm"], 2)
        if spacer_lm > 0:
            items.append(BOMLineItem(
                item_code="HW-SPACER-BAR",
                description="Warm-edge spacer bar (stainless)",
                category="HARDWARE",
                unit="lm",
                quantity=spacer_lm,
                unit_cost_aed=R["spacer_bar_aed_lm"],
                subtotal_aed=_r(spacer_lm * R["spacer_bar_aed_lm"]),
                source_opening_id=opening_id,
            ))

        # Distance pieces
        dist_pcs = round(sqm_total * 2)  # ~2 per sqm
        if dist_pcs > 0 and glass_sqm > 0:
            items.append(BOMLineItem(
                item_code="HW-DIST-PIECE",
                description="Distance piece (nylon)",
                category="HARDWARE",
                unit="nr",
                quantity=float(dist_pcs),
                unit_cost_aed=R["distance_piece_aed"],
                subtotal_aed=_r(dist_pcs * R["distance_piece_aed"]),
                source_opening_id=opening_id,
            ))

        # ══════════════════════════════════════════════════════════════════════
        # 9. FIXINGS
        # ══════════════════════════════════════════════════════════════════════
        anchor_count = round(sqm_total * ratio.get("anchor_per_sqm", 1.5))
        if anchor_count > 0:
            items.append(BOMLineItem(
                item_code="FIX-CHEM-ANCHOR",
                description="Chemical anchor M12 (stainless steel, resin capsule)",
                category="FIXING",
                unit="nr",
                quantity=float(anchor_count),
                unit_cost_aed=R["chemical_anchor_m12_aed"],
                subtotal_aed=_r(anchor_count * R["chemical_anchor_m12_aed"]),
                source_opening_id=opening_id,
            ))

        bracket_count = round(sqm_total * ratio.get("bracket_per_sqm", 1.0))
        if bracket_count > 0:
            items.append(BOMLineItem(
                item_code="FIX-BRACKET-120",
                description="Aluminum bracket 120mm (anodized)",
                category="FIXING",
                unit="nr",
                quantity=float(bracket_count),
                unit_cost_aed=R["bracket_120mm_aed"],
                subtotal_aed=_r(bracket_count * R["bracket_120mm_aed"]),
                source_opening_id=opening_id,
            ))

        screw_count = round(sqm_total * ratio.get("screw_per_sqm", 6))
        if screw_count > 0:
            items.append(BOMLineItem(
                item_code="FIX-SDS",
                description="Self-drilling screw 4.8x25mm (stainless A2)",
                category="FIXING",
                unit="nr",
                quantity=float(screw_count),
                unit_cost_aed=R["self_drill_screw_aed"],
                subtotal_aed=_r(screw_count * R["self_drill_screw_aed"]),
                source_opening_id=opening_id,
            ))

        # Rivets (for curtain wall pressure plates)
        if "curtain" in system_type.lower() or "fixed" in system_type.lower():
            rivet_count = round(perimeter_m * 5)  # ~5 per lm
            if rivet_count > 0:
                items.append(BOMLineItem(
                    item_code="FIX-RIVET",
                    description="Blind rivet 4.8x12mm (aluminum/SS mandrel)",
                    category="FIXING",
                    unit="nr",
                    quantity=float(rivet_count),
                    unit_cost_aed=R["rivet_aed"],
                    subtotal_aed=_r(rivet_count * R["rivet_aed"]),
                    source_opening_id=opening_id,
                ))

        # Shim plates
        shim_count = round(sqm_total * 0.5)
        if shim_count > 0:
            items.append(BOMLineItem(
                item_code="FIX-SHIM",
                description="Packing shim plate (stainless steel)",
                category="FIXING",
                unit="nr",
                quantity=float(shim_count),
                unit_cost_aed=R["shim_plate_aed"],
                subtotal_aed=_r(shim_count * R["shim_plate_aed"]),
                source_opening_id=opening_id,
            ))

        # Thermal pads
        thermal_pad_count = anchor_count  # 1 per anchor point
        if thermal_pad_count > 0:
            items.append(BOMLineItem(
                item_code="FIX-THERMAL-PAD",
                description="Thermal isolating pad (neoprene 6mm)",
                category="FIXING",
                unit="nr",
                quantity=float(thermal_pad_count),
                unit_cost_aed=R["thermal_pad_aed"],
                subtotal_aed=_r(thermal_pad_count * R["thermal_pad_aed"]),
                source_opening_id=opening_id,
            ))

        # ══════════════════════════════════════════════════════════════════════
        # 10. SURFACE TREATMENT
        # ══════════════════════════════════════════════════════════════════════
        surface_sqm = _r(sqm_total * ratio.get("surface_sqm_per_sqm", 0.70), 2)
        if surface_sqm > 0:
            pc_rate = R["powder_coating_aed_sqm"]
            items.append(BOMLineItem(
                item_code="SRF-POWDER-COAT",
                description="Powder coating (standard RAL color, 60-80 micron)",
                category="SURFACE",
                unit="sqm",
                quantity=surface_sqm,
                unit_cost_aed=pc_rate,
                subtotal_aed=_r(surface_sqm * pc_rate),
                source_opening_id=opening_id,
            ))

        # ══════════════════════════════════════════════════════════════════════
        # 11. PROTECTIVE FILM & PACKAGING
        # ══════════════════════════════════════════════════════════════════════
        if glass_sqm > 0:
            items.append(BOMLineItem(
                item_code="PKG-PROTECT-FILM",
                description="Protective film (glass + aluminum profiles)",
                category="SITE",
                unit="sqm",
                quantity=_r(sqm_total * 1.1, 2),  # 10% overlap
                unit_cost_aed=R["protective_film_aed_sqm"],
                subtotal_aed=_r(sqm_total * 1.1 * R["protective_film_aed_sqm"]),
                source_opening_id=opening_id,
            ))

        items.append(BOMLineItem(
            item_code="PKG-PACKAGING",
            description="Packaging material (timber crates, foam, strapping)",
            category="SITE",
            unit="sqm",
            quantity=sqm_total,
            unit_cost_aed=R["packaging_aed_sqm"],
            subtotal_aed=_r(sqm_total * R["packaging_aed_sqm"]),
            source_opening_id=opening_id,
        ))

        # ══════════════════════════════════════════════════════════════════════
        # 12. LABOR — Fabrication + Installation
        # ══════════════════════════════════════════════════════════════════════
        fab_hrs = _r(sqm_total * ratio.get("fab_labor_hr_per_sqm", ratio.get("labor_hr_per_sqm", 3.5)), 2)
        items.append(BOMLineItem(
            item_code="LABOR-FAB",
            description=f"Factory fabrication labor -- {system_type}",
            category="LABOR",
            unit="hr",
            quantity=fab_hrs,
            unit_cost_aed=labor_burn_rate,
            subtotal_aed=_r(fab_hrs * labor_burn_rate),
            source_opening_id=opening_id,
        ))

        install_hrs = _r(sqm_total * ratio.get("install_labor_hr_per_sqm", 2.5), 2)
        items.append(BOMLineItem(
            item_code="LABOR-INSTALL",
            description=f"Site installation labor -- {system_type}",
            category="LABOR",
            unit="hr",
            quantity=install_hrs,
            unit_cost_aed=R["install_labor_aed_hr"],
            subtotal_aed=_r(install_hrs * R["install_labor_aed_hr"]),
            source_opening_id=opening_id,
        ))

        # ══════════════════════════════════════════════════════════════════════
        # 13. ATTIC STOCK (+2% on material quantities) — Blind Spot Rule
        # ══════════════════════════════════════════════════════════════════════
        material_categories = {"ALUMINUM", "GLASS", "ACP", "HARDWARE", "SEALANT", "FIXING", "SURFACE"}
        attic_items = []
        for item in items:
            if item.category in material_categories:
                attic_qty = _r(item.quantity * ATTIC_STOCK_PCT, 4)
                if attic_qty > 0:
                    attic_items.append(BOMLineItem(
                        item_code=item.item_code + "-ATTIC",
                        description=f"Attic stock 2% -- {item.description}",
                        category=item.category,
                        unit=item.unit,
                        quantity=attic_qty,
                        unit_cost_aed=item.unit_cost_aed,
                        subtotal_aed=_r(attic_qty * item.unit_cost_aed),
                        is_attic_stock=True,
                        source_opening_id=opening_id,
                        notes="Blind Spot: 2% attic stock per company policy",
                    ))
        items.extend(attic_items)

        return items

    def explode_all(
        self,
        openings: List[Dict[str, Any]],
        catalog_items: List[Dict[str, Any]],
        lme_aed_per_kg: float = 7.0,
        labor_burn_rate: float = 13.0,
        rates: Optional[Dict[str, float]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Explode all openings and return aggregated BOM as list of dicts.
        Also adds project-level items (site mobilization, testing, transport, provisional sums).
        """
        all_items: List[BOMLineItem] = []
        total_sqm = 0.0
        total_floors = 1
        has_curtain_wall = False

        for opening in openings:
            try:
                items = self.explode_opening(opening, catalog_items, lme_aed_per_kg, labor_burn_rate, rates)
                all_items.extend(items)
                w = float(opening.get("width_mm", 1000)) / 1000
                h = float(opening.get("height_mm", 2000)) / 1000
                q = int(opening.get("quantity", 1))
                total_sqm += w * h * q
                fl = int(opening.get("floors", 1))
                if fl > total_floors:
                    total_floors = fl
                if "curtain" in str(opening.get("system_type", "")).lower():
                    has_curtain_wall = True
            except Exception as e:
                logger.error(f"BOM explosion failed for opening {opening.get('id')}: {e}")

        R = dict(UAE_RATES)
        if rates:
            R.update(rates)

        # ══════════════════════════════════════════════════════════════════════
        # PROJECT-LEVEL ITEMS (not per-opening)
        # ══════════════════════════════════════════════════════════════════════

        # Site mobilization
        all_items.append(BOMLineItem(
            item_code="SITE-MOB",
            description="Site mobilization & demobilization",
            category="SITE",
            unit="lot",
            quantity=1.0,
            unit_cost_aed=R["site_mobilization_aed"],
            subtotal_aed=R["site_mobilization_aed"],
        ))

        # Scaffolding (estimate 3 months for a typical project)
        if total_sqm > 0:
            scaffolding_months = min(max(total_floors * 0.5, 2), 12)
            scaff_cost = _r(total_sqm * R["scaffolding_aed_sqm_month"] * scaffolding_months)
            all_items.append(BOMLineItem(
                item_code="SITE-SCAFFOLDING",
                description=f"Scaffolding rental ({int(scaffolding_months)} months)",
                category="SITE",
                unit="lot",
                quantity=1.0,
                unit_cost_aed=scaff_cost,
                subtotal_aed=scaff_cost,
                notes=f"Based on {_r(total_sqm)} sqm x {int(scaffolding_months)} months",
            ))

        # Crane/lifting equipment (1 day per 100 sqm, min 3 days)
        crane_days = max(math.ceil(total_sqm / 100), 3)
        all_items.append(BOMLineItem(
            item_code="SITE-CRANE",
            description=f"Mobile crane hire ({crane_days} days)",
            category="SITE",
            unit="day",
            quantity=float(crane_days),
            unit_cost_aed=R["crane_hire_aed_day"],
            subtotal_aed=_r(crane_days * R["crane_hire_aed_day"]),
        ))

        # Transport (1 truck per 50 sqm, min 2)
        truck_count = max(math.ceil(total_sqm / 50), 2)
        all_items.append(BOMLineItem(
            item_code="SITE-TRANSPORT",
            description=f"Transport to site ({truck_count} truck loads)",
            category="SITE",
            unit="trip",
            quantity=float(truck_count),
            unit_cost_aed=R["transport_aed_per_truck"],
            subtotal_aed=_r(truck_count * R["transport_aed_per_truck"]),
        ))

        # Testing & commissioning
        test_count = max(math.ceil(total_sqm / 500), 1)
        all_items.append(BOMLineItem(
            item_code="TEST-WATER",
            description=f"Water penetration test ({test_count} zones)",
            category="TESTING",
            unit="test",
            quantity=float(test_count),
            unit_cost_aed=R["water_test_aed_per_test"],
            subtotal_aed=_r(test_count * R["water_test_aed_per_test"]),
        ))

        if has_curtain_wall:
            air_count = max(math.ceil(total_sqm / 500), 1)
            all_items.append(BOMLineItem(
                item_code="TEST-AIR",
                description=f"Air infiltration test ({air_count} zones)",
                category="TESTING",
                unit="test",
                quantity=float(air_count),
                unit_cost_aed=R["air_test_aed_per_test"],
                subtotal_aed=_r(air_count * R["air_test_aed_per_test"]),
            ))

        # Provisional sums (Blind Spot: GPR survey + water testing allowance)
        all_items.append(BOMLineItem(
            item_code="PROV-GPR",
            description="Provisional sum: Ground penetrating radar (GPR) survey",
            category="PROVISIONAL",
            unit="lot",
            quantity=1.0,
            unit_cost_aed=R["gpr_provisional_aed"],
            subtotal_aed=R["gpr_provisional_aed"],
            notes="Blind Spot: GPR survey for anchor locations",
        ))

        all_items.append(BOMLineItem(
            item_code="PROV-WATER-TEST",
            description="Provisional sum: Independent water testing",
            category="PROVISIONAL",
            unit="lot",
            quantity=1.0,
            unit_cost_aed=R["water_test_provisional_aed"],
            subtotal_aed=R["water_test_provisional_aed"],
            notes="Blind Spot: Independent 3rd-party water test",
        ))

        return [self._item_to_dict(i) for i in all_items]

    def aggregate_by_item_code(self, bom_items: List[Dict]) -> List[Dict]:
        """Roll up duplicate item_codes into single lines with summed quantities."""
        rolled: Dict[str, Dict] = {}
        for item in bom_items:
            code = item["item_code"]
            if code not in rolled:
                rolled[code] = dict(item)
            else:
                rolled[code]["quantity"] = _r(rolled[code]["quantity"] + item["quantity"], 4)
                rolled[code]["subtotal_aed"] = _r(
                    rolled[code]["quantity"] * rolled[code]["unit_cost_aed"]
                )
        return list(rolled.values())

    def generate_summary(self, bom_items: List[Dict]) -> Dict[str, Any]:
        """Generate financial summary from BOM items."""
        totals_by_cat: Dict[str, float] = {}
        grand_total = 0.0

        for item in bom_items:
            cat = item.get("category", "OTHER")
            sub = float(item.get("subtotal_aed", 0))
            totals_by_cat[cat] = totals_by_cat.get(cat, 0) + sub
            grand_total += sub

        return {
            "material_cost_aed": _r(sum(v for k, v in totals_by_cat.items() if k not in ("LABOR", "SITE", "TESTING", "PROVISIONAL"))),
            "aluminum_cost_aed": _r(totals_by_cat.get("ALUMINUM", 0)),
            "glass_cost_aed": _r(totals_by_cat.get("GLASS", 0)),
            "acp_cost_aed": _r(totals_by_cat.get("ACP", 0)),
            "hardware_cost_aed": _r(totals_by_cat.get("HARDWARE", 0)),
            "sealant_cost_aed": _r(totals_by_cat.get("SEALANT", 0)),
            "fixing_cost_aed": _r(totals_by_cat.get("FIXING", 0)),
            "surface_cost_aed": _r(totals_by_cat.get("SURFACE", 0)),
            "labor_cost_aed": _r(totals_by_cat.get("LABOR", 0)),
            "site_cost_aed": _r(totals_by_cat.get("SITE", 0)),
            "testing_cost_aed": _r(totals_by_cat.get("TESTING", 0)),
            "provisional_sums_aed": _r(totals_by_cat.get("PROVISIONAL", 0)),
            "subtotal_aed": _r(grand_total),
            "total_line_items": len(bom_items),
            "category_breakdown": {k: _r(v) for k, v in totals_by_cat.items()},
        }

    def _add_generic_alu_breakdown(
        self, items: List[BOMLineItem], total_kg: float,
        ratio: Dict, alu_rate: float, opening_id: str, system_type: str,
    ):
        """Add broken-down aluminum extrusion lines (mullion, transom, pressure plate, capping)."""
        mullion_pct = ratio.get("mullion_pct", 0.30)
        transom_pct = ratio.get("transom_pct", 0.25)
        pp_pct = ratio.get("pressure_plate_pct", 0.15)
        cap_pct = ratio.get("capping_pct", 0.10)
        other_pct = 1.0 - mullion_pct - transom_pct - pp_pct - cap_pct

        breakdown = [
            ("ALU-MULLION", f"Aluminum mullion profile -- {system_type}", mullion_pct, UAE_RATES["aluminum_mullion_aed_kg"]),
            ("ALU-TRANSOM", f"Aluminum transom profile -- {system_type}", transom_pct, UAE_RATES["aluminum_transom_aed_kg"]),
            ("ALU-PRESS-PLATE", f"Pressure plate -- {system_type}", pp_pct, UAE_RATES["aluminum_pressure_plate_aed_kg"]),
            ("ALU-CAPPING", f"Snap-on capping -- {system_type}", cap_pct, UAE_RATES["aluminum_capping_aed_kg"]),
            ("ALU-MISC", f"Misc aluminum profiles (sill, head, adapter) -- {system_type}", other_pct, alu_rate),
        ]

        for code, desc, pct, rate in breakdown:
            if pct <= 0:
                continue
            kg = _r(total_kg * pct, 3)
            if kg <= 0:
                continue
            items.append(BOMLineItem(
                item_code=code,
                description=desc,
                category="ALUMINUM",
                unit="kg",
                quantity=kg,
                unit_cost_aed=rate,
                subtotal_aed=_r(kg * rate),
                source_opening_id=opening_id,
                notes="No catalog loaded -- using UAE market rates",
            ))

    def _get_ratio(self, system_type: str) -> Dict:
        for key in SYSTEM_RATIOS:
            if key.lower() in system_type.lower() or system_type.lower() in key.lower():
                return SYSTEM_RATIOS[key]
        return SYSTEM_RATIOS["DEFAULT"]

    def _match_profiles(self, catalog: List[Dict], system_type: str) -> List[Dict]:
        """Return catalog profiles that match the given system type."""
        matches = []
        for item in catalog:
            series = (item.get("system_series") or "").lower()
            desc = (item.get("description") or "").lower()
            if any(kw in series or kw in desc for kw in ["mullion", "transom", "frame", "sill", "head"]):
                matches.append(item)
        return matches[:6]  # cap at 6 profiles per opening type

    def _item_to_dict(self, item: BOMLineItem) -> Dict:
        return {
            "item_code": item.item_code,
            "description": item.description,
            "category": item.category,
            "unit": item.unit,
            "quantity": item.quantity,
            "unit_rate": item.unit_cost_aed,       # alias for frontend compat
            "unit_cost_aed": item.unit_cost_aed,
            "subtotal_aed": item.subtotal_aed,
            "is_attic_stock": item.is_attic_stock,
            "source_opening_id": item.source_opening_id,
            "notes": item.notes,
        }

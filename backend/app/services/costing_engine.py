"""
CostingEngine — Production-grade costing engine for facade estimation.

Covers:
  - LME-based aluminium pricing
  - Glass costing by type + processing surcharges
  - Hardware costing
  - Fabrication labour costing by operation
  - Installation labour with height premiums
  - Full estimate rollup (overhead, margin, provisional sums, attic stock)
  - Variation Order (VO) costing
  - International mode (forex buffer, BG fee, mobilization)
"""

import math
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Fallback financial defaults (overridden by financial_rates dict at runtime)
# ---------------------------------------------------------------------------
_DEFAULT_LME_USD_MT: float = 2350.0          # approximate LME spot
_DEFAULT_BILLET_PREMIUM: float = 400.0        # USD/mt
_DEFAULT_EXTRUSION_PREMIUM: float = 800.0     # USD/mt
_DEFAULT_POWDER_COATING: float = 15.0         # AED/kg
_DEFAULT_USD_AED: float = 3.6725

# Overhead & margin defaults
_DEFAULT_OVERHEAD_PCT: float = 0.12           # 12 %
_DEFAULT_MARGIN_PCT: float = 0.18             # 18 %
_DEFAULT_ATTIC_STOCK_PCT: float = 0.02        # 2 %

# Burn rate for internal labour cost tracking
_BURN_RATE_AED_HR: float = 85.0              # fully-burdened factory rate

# International cost additions
_FOREX_BUFFER_PCT: float = 0.03              # 3 %
_BG_FEE_PCT: float = 0.025                  # 2.5 %
_MOBILIZATION_AED: float = 25_000.0          # AED fixed


# ---------------------------------------------------------------------------
# Glass sqm base rates (AED/sqm)
# ---------------------------------------------------------------------------
_GLASS_BASE_RATES: Dict[str, float] = {
    "6mm_clear": 45.0,
    "8mm_clear": 58.0,
    "10mm_clear": 72.0,
    "10mm_tempered": 85.0,
    "12mm_tempered": 105.0,
    "lam_6_6": 120.0,          # Laminated 6+6
    "lam_8_8": 145.0,          # Laminated 8+8
    "igu_6_12a_6": 150.0,      # IGU 6+12A+6
    "igu_lowe": 195.0,         # Low-E IGU
    "igu_triple": 280.0,       # Triple IGU
    "igu_lowe_triple": 320.0,  # Low-E Triple
    "spandrel": 90.0,
    "back_painted": 95.0,
}

# Glass processing surcharge multipliers (stacked on base rate)
_GLASS_PROCESSING_SURCHARGES: Dict[str, float] = {
    "tempering": 0.30,         # +30 %
    "heat_soak": 0.15,         # +15 %
    "ceramic_frit": 0.25,      # +25 %
    "acid_etch": 0.20,         # +20 %
    "silk_screen": 0.18,       # +18 %
    "bent": 0.45,              # +45 %
    "polished_edge": 0.10,     # +10 %
}


# ---------------------------------------------------------------------------
# Hardware unit rates (AED per unit unless stated)
# ---------------------------------------------------------------------------
_HARDWARE_RATES: Dict[str, float] = {
    "handle": 45.0,
    "hinge": 35.0,
    "lock": 85.0,
    "multipoint_lock": 220.0,
    "operator": 350.0,            # window operator / chain drive
    "floor_spring": 680.0,
    "door_closer": 320.0,
    "patch_fitting": 195.0,
    "spider_fitting": 280.0,
    "gasket_m": 8.0,              # AED/lm
    "seal_m": 12.0,               # AED/lm — structural silicone bead
    "weather_strip_m": 6.5,       # AED/lm
    "anchor_bolt": 18.0,
    "chemical_anchor": 32.0,
    "bracket": 65.0,
    "transom_cleat": 28.0,
    "mullion_cleat": 28.0,
    "expansion_joint_m": 55.0,    # AED/lm
    "thermal_break_m": 22.0,      # AED/lm
    "cap_bead_m": 9.0,            # AED/lm
    "drain_tube": 14.0,
    "vent_plug": 8.0,
}


# ---------------------------------------------------------------------------
# Fabrication time constants (minutes)
# ---------------------------------------------------------------------------
_FAB_TIMES: Dict[str, float] = {
    "cnc_cut_min": 3.0,           # per cut
    "manual_cut_min": 5.0,        # per cut
    "drill_min_per_hole": 1.5,    # per hole
    "assembly_min_per_joint": 15.0,
    "glazing_cw_min_per_sqm": 12.0,  # curtain wall — sqm
    "glazing_window_min": 8.0,        # per window unit
    "glazing_door_min": 14.0,         # per door unit
    "silicone_min_per_lm": 2.0,       # per linear meter
    "quality_check_min_per_unit": 5.0,
    "packing_min_per_unit": 6.0,
    "cnc_setup_min": 30.0,            # per batch
}


# ---------------------------------------------------------------------------
# Installation rates (AED) and height premium multipliers
# ---------------------------------------------------------------------------
_INSTALL_RATES: Dict[str, float] = {
    "curtain_wall_sqm": 180.0,
    "window_unit": 120.0,
    "door_unit": 250.0,
    "acp_sqm": 85.0,
    "louvre_sqm": 110.0,
    "skylight_sqm": 240.0,
    "balustrade_lm": 320.0,
    "structural_glazing_sqm": 210.0,
    "shopfront_lm": 195.0,
}

# Height premium: {threshold_m: multiplier_addition}
_HEIGHT_PREMIUMS: List[Tuple[float, float]] = [
    (50.0, 0.60),   # >50 m → +60 %
    (30.0, 0.40),   # >30 m → +40 %
    (15.0, 0.20),   # >15 m → +20 %
    (0.0, 0.00),    # ground level
]


def _height_premium_factor(building_height_m: float) -> float:
    """Return the height premium multiplier addition (e.g. 0.20 for 20 %)."""
    for threshold, premium in _HEIGHT_PREMIUMS:
        if building_height_m > threshold:
            return premium
    return 0.0


class CostingEngine:
    """
    Full-featured costing engine for aluminium & glass facade estimation.

    All monetary values are in AED unless explicitly stated otherwise.
    """

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def __init__(
        self,
        financial_rates: Optional[Dict[str, Any]] = None,
        project_config: Optional[Dict[str, Any]] = None,
    ) -> None:
        rates = financial_rates or {}
        cfg = project_config or {}

        # LME & aluminium pricing
        self.lme_usd_mt: float = float(rates.get("lme_usd_mt", _DEFAULT_LME_USD_MT))
        self.billet_premium: float = float(rates.get("billet_premium", _DEFAULT_BILLET_PREMIUM))
        self.extrusion_premium: float = float(rates.get("extrusion_premium", _DEFAULT_EXTRUSION_PREMIUM))
        self.powder_coating: float = float(rates.get("powder_coating_aed_kg", _DEFAULT_POWDER_COATING))
        self.usd_aed: float = float(rates.get("usd_aed", _DEFAULT_USD_AED))
        self.anodizing_aed_kg: float = float(rates.get("anodizing_aed_kg", 18.0))

        # Labour
        self.factory_hourly_rate: float = float(
            cfg.get("factory_hourly_rate", rates.get("factory_hourly_rate", _BURN_RATE_AED_HR))
        )
        self.site_hourly_rate: float = float(
            cfg.get("site_hourly_rate", rates.get("site_hourly_rate", 75.0))
        )

        # Overhead & margin
        self.overhead_pct: float = float(cfg.get("overhead_pct", _DEFAULT_OVERHEAD_PCT))
        self.margin_pct: float = float(cfg.get("margin_pct", _DEFAULT_MARGIN_PCT))
        self.attic_stock_pct: float = float(cfg.get("attic_stock_pct", _DEFAULT_ATTIC_STOCK_PCT))

        # International mode
        self.is_international: bool = bool(cfg.get("is_international", False))

        # Provisional sum defaults (AED)
        self.provisional_gpr: float = float(cfg.get("provisional_gpr_aed", 15_000.0))
        self.provisional_water_test: float = float(cfg.get("provisional_water_test_aed", 8_500.0))
        self.provisional_logistics_permits: float = float(
            cfg.get("provisional_logistics_permits_aed", 5_000.0)
        )

    # ------------------------------------------------------------------
    # 1. Aluminium material costing
    # ------------------------------------------------------------------

    def aluminium_rate_per_kg(self) -> float:
        """
        Compute the all-in AED/kg rate for extruded, powder-coated aluminium.

        Formula:
            rate = ((LME + billet_premium + extrusion_premium) / 1000 * USD_AED) + powder_coating
        """
        metal_rate_aed_kg = (
            (self.lme_usd_mt + self.billet_premium + self.extrusion_premium)
            / 1000.0
            * self.usd_aed
        )
        return round(metal_rate_aed_kg + self.powder_coating, 4)

    def calculate_aluminum_material_cost(
        self,
        total_weight_kg: float,
        lme_usd_mt: Optional[float] = None,
        finish: str = "powder_coat",
    ) -> Dict[str, Any]:
        """
        Calculate aluminium material cost for a given total weight.

        Args:
            total_weight_kg: Total weight of extruded profiles in kg.
            lme_usd_mt:      Override LME price (USD/mt). Uses instance default if None.
            finish:          Surface finish — 'powder_coat' | 'anodize' | 'mill'

        Returns:
            Dict with rate_per_kg, total_cost, finish_surcharge, grand_total.
        """
        if lme_usd_mt is not None:
            # Temporary override without mutating instance state
            original_lme = self.lme_usd_mt
            self.lme_usd_mt = float(lme_usd_mt)
            rate = self.aluminium_rate_per_kg()
            self.lme_usd_mt = original_lme
        else:
            rate = self.aluminium_rate_per_kg()

        base_cost = total_weight_kg * rate

        # Finish surcharge
        finish_surcharge = 0.0
        if finish == "anodize":
            # Anodizing replaces powder coat; net delta applied
            finish_surcharge = total_weight_kg * (self.anodizing_aed_kg - self.powder_coating)
        elif finish == "mill":
            # Mill finish — remove powder coat cost
            finish_surcharge = -(total_weight_kg * self.powder_coating)

        grand_total = base_cost + finish_surcharge

        return {
            "total_weight_kg": round(total_weight_kg, 3),
            "rate_per_kg_aed": round(rate, 4),
            "base_cost_aed": round(base_cost, 2),
            "finish": finish,
            "finish_surcharge_aed": round(finish_surcharge, 2),
            "grand_total_aed": round(grand_total, 2),
        }

    # ------------------------------------------------------------------
    # 2. Glass costing
    # ------------------------------------------------------------------

    def calculate_glass_cost(self, glass_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate glass supply cost for a list of glass line items.

        Each item dict may contain:
            glass_type (str)        — key into _GLASS_BASE_RATES
            area_sqm (float)        — total area for this line item
            width_mm, height_mm     — alternative to area_sqm (used if area_sqm absent)
            quantity (int)          — number of panes (used with width_mm/height_mm)
            processing (List[str])  — list of processing surcharge keys
            wastage_pct (float)     — optional per-item wastage override (default 0.10)

        Returns:
            Dict with line_items breakdown and totals.
        """
        line_items: List[Dict[str, Any]] = []
        total_area_sqm = 0.0
        total_cost_aed = 0.0

        for idx, item in enumerate(glass_items):
            glass_type = item.get("glass_type", "6mm_clear").lower().replace(" ", "_")
            base_rate = _GLASS_BASE_RATES.get(glass_type, _GLASS_BASE_RATES["6mm_clear"])

            # Determine area
            if "area_sqm" in item:
                area_sqm = float(item["area_sqm"])
            elif "width_mm" in item and "height_mm" in item:
                qty = int(item.get("quantity", 1))
                area_sqm = (float(item["width_mm"]) / 1000.0) * (float(item["height_mm"]) / 1000.0) * qty
            else:
                area_sqm = 0.0

            # Wastage
            wastage_pct = float(item.get("wastage_pct", 0.10))
            area_with_wastage = area_sqm * (1.0 + wastage_pct)

            # Processing surcharges — stacked on base rate
            processing: List[str] = item.get("processing", [])
            surcharge_total_pct = 0.0
            surcharge_breakdown: Dict[str, float] = {}
            for proc in processing:
                proc_key = proc.lower().replace(" ", "_")
                pct = _GLASS_PROCESSING_SURCHARGES.get(proc_key, 0.0)
                surcharge_total_pct += pct
                surcharge_breakdown[proc_key] = pct

            effective_rate = base_rate * (1.0 + surcharge_total_pct)
            line_cost = area_with_wastage * effective_rate

            line_items.append({
                "line": idx + 1,
                "glass_type": glass_type,
                "area_net_sqm": round(area_sqm, 3),
                "wastage_pct": wastage_pct,
                "area_with_wastage_sqm": round(area_with_wastage, 3),
                "base_rate_aed_sqm": round(base_rate, 2),
                "processing": surcharge_breakdown,
                "surcharge_pct": round(surcharge_total_pct, 4),
                "effective_rate_aed_sqm": round(effective_rate, 2),
                "line_cost_aed": round(line_cost, 2),
            })

            total_area_sqm += area_sqm
            total_cost_aed += line_cost

        return {
            "line_items": line_items,
            "total_area_sqm": round(total_area_sqm, 3),
            "total_cost_aed": round(total_cost_aed, 2),
        }

    # ------------------------------------------------------------------
    # 3. Hardware costing
    # ------------------------------------------------------------------

    def calculate_hardware_cost(self, hardware_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate hardware supply cost.

        Each item dict may contain:
            hardware_type (str)   — key into _HARDWARE_RATES
            quantity (float)      — units (or lm for linear items)
            unit_rate_override (float) — override standard rate

        Returns:
            Dict with line_items breakdown and total.
        """
        line_items: List[Dict[str, Any]] = []
        total_cost_aed = 0.0

        for idx, item in enumerate(hardware_items):
            hw_type = item.get("hardware_type", "").lower().replace(" ", "_")
            quantity = float(item.get("quantity", 1))
            rate = float(item.get("unit_rate_override", _HARDWARE_RATES.get(hw_type, 0.0)))
            line_cost = quantity * rate

            line_items.append({
                "line": idx + 1,
                "hardware_type": hw_type,
                "quantity": quantity,
                "unit_rate_aed": round(rate, 2),
                "line_cost_aed": round(line_cost, 2),
            })
            total_cost_aed += line_cost

        return {
            "line_items": line_items,
            "total_cost_aed": round(total_cost_aed, 2),
        }

    # ------------------------------------------------------------------
    # 4. Fabrication labour costing
    # ------------------------------------------------------------------

    def calculate_fabrication_cost(
        self,
        operations: Dict[str, Any],
        hourly_rate: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Calculate fabrication labour cost by operation type.

        operations dict keys (all optional, default 0):
            cnc_cuts (int)            — number of CNC cuts
            manual_cuts (int)         — number of manual cuts
            drill_holes (int)         — total drill holes
            assembly_joints (int)     — total joints assembled
            glazing_cw_sqm (float)    — curtain wall glazing area
            glazing_windows (int)     — window units glazed
            glazing_doors (int)       — door units glazed
            silicone_lm (float)       — linear meters of silicone
            units_qc (int)            — units quality-checked
            units_packed (int)        — units packed
            cnc_batches (int)         — CNC machine setup events

        Returns:
            Dict with operation breakdown (minutes, cost) and totals.
        """
        rate = hourly_rate if hourly_rate is not None else self.factory_hourly_rate
        rate_per_min = rate / 60.0

        breakdown: Dict[str, Dict[str, float]] = {}
        total_minutes = 0.0
        total_cost_aed = 0.0

        def _add_op(key: str, minutes: float) -> None:
            nonlocal total_minutes, total_cost_aed
            cost = minutes * rate_per_min
            breakdown[key] = {"minutes": round(minutes, 2), "cost_aed": round(cost, 2)}
            total_minutes += minutes
            total_cost_aed += cost

        _add_op("cnc_cuts",
                int(operations.get("cnc_cuts", 0)) * _FAB_TIMES["cnc_cut_min"])
        _add_op("manual_cuts",
                int(operations.get("manual_cuts", 0)) * _FAB_TIMES["manual_cut_min"])
        _add_op("drill_holes",
                int(operations.get("drill_holes", 0)) * _FAB_TIMES["drill_min_per_hole"])
        _add_op("assembly_joints",
                int(operations.get("assembly_joints", 0)) * _FAB_TIMES["assembly_min_per_joint"])
        _add_op("glazing_cw",
                float(operations.get("glazing_cw_sqm", 0.0)) * _FAB_TIMES["glazing_cw_min_per_sqm"])
        _add_op("glazing_windows",
                int(operations.get("glazing_windows", 0)) * _FAB_TIMES["glazing_window_min"])
        _add_op("glazing_doors",
                int(operations.get("glazing_doors", 0)) * _FAB_TIMES["glazing_door_min"])
        _add_op("silicone",
                float(operations.get("silicone_lm", 0.0)) * _FAB_TIMES["silicone_min_per_lm"])
        _add_op("quality_check",
                int(operations.get("units_qc", 0)) * _FAB_TIMES["quality_check_min_per_unit"])
        _add_op("packing",
                int(operations.get("units_packed", 0)) * _FAB_TIMES["packing_min_per_unit"])
        _add_op("cnc_setup",
                int(operations.get("cnc_batches", 0)) * _FAB_TIMES["cnc_setup_min"])

        total_hours = total_minutes / 60.0

        return {
            "hourly_rate_aed": round(rate, 2),
            "operations": breakdown,
            "total_minutes": round(total_minutes, 2),
            "total_hours": round(total_hours, 3),
            "total_cost_aed": round(total_cost_aed, 2),
        }

    # ------------------------------------------------------------------
    # 5. Installation labour costing
    # ------------------------------------------------------------------

    def calculate_installation_cost(
        self,
        items: List[Dict[str, Any]],
        building_height_m: float = 10.0,
    ) -> Dict[str, Any]:
        """
        Calculate installation labour cost with height premiums.

        Each item dict may contain:
            install_type (str)   — key into _INSTALL_RATES
            quantity (float)     — units or sqm or lm as appropriate
            height_m (float)     — optional per-item height override

        Returns:
            Dict with line_items breakdown and total.
        """
        height_premium = _height_premium_factor(building_height_m)
        line_items: List[Dict[str, Any]] = []
        total_cost_aed = 0.0

        for idx, item in enumerate(items):
            install_type = item.get("install_type", "").lower().replace(" ", "_")
            quantity = float(item.get("quantity", 1))

            # Allow per-item height override
            item_height = float(item.get("height_m", building_height_m))
            item_premium = _height_premium_factor(item_height)

            base_rate = float(item.get("rate_override", _INSTALL_RATES.get(install_type, 0.0)))
            effective_rate = base_rate * (1.0 + item_premium)
            line_cost = quantity * effective_rate

            line_items.append({
                "line": idx + 1,
                "install_type": install_type,
                "quantity": quantity,
                "height_m": item_height,
                "height_premium_pct": round(item_premium * 100, 1),
                "base_rate_aed": round(base_rate, 2),
                "effective_rate_aed": round(effective_rate, 2),
                "line_cost_aed": round(line_cost, 2),
            })
            total_cost_aed += line_cost

        return {
            "building_height_m": building_height_m,
            "default_height_premium_pct": round(height_premium * 100, 1),
            "line_items": line_items,
            "total_cost_aed": round(total_cost_aed, 2),
        }

    # ------------------------------------------------------------------
    # 6. Full estimate rollup
    # ------------------------------------------------------------------

    def calculate_full_estimate(
        self,
        bom_items: List[Dict[str, Any]],
        financial_rates: Optional[Dict[str, Any]] = None,
        project_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Complete estimate rollup from BOM items.

        Each BOM item may contain:
            category (str)           — 'aluminium' | 'glass' | 'hardware' | 'fabrication' | 'installation'
            description (str)
            quantity (float)
            unit (str)               — 'kg' | 'sqm' | 'lm' | 'unit' | 'nr'
            unit_rate_aed (float)    — direct rate (glass/hardware items may use this)
            weight_kg (float)        — for aluminium items
            glass_type (str)         — for glass items
            area_sqm (float)         — for glass/ACP/curtain-wall items
            install_type (str)       — for installation items
            operations (dict)        — for fabrication items

        Applies:
            - Direct costs (aluminium, glass, hardware, fabrication, installation)
            - Attic stock 2% on aluminium material
            - Overhead 12% on direct costs
            - Provisional sums (GPR, water test, logistics)
            - Margin 18% on (direct + overhead + provisional)
            - International adjustments if is_international=True

        Returns a comprehensive cost summary dict.
        """
        # Allow per-call overrides
        if financial_rates:
            _merge_rates(self, financial_rates)
        if project_config:
            _merge_config(self, project_config)

        # Separate BOM by category
        aluminium_items = [i for i in bom_items if i.get("category", "").lower() == "aluminium"]
        glass_items = [i for i in bom_items if i.get("category", "").lower() == "glass"]
        hardware_items = [i for i in bom_items if i.get("category", "").lower() == "hardware"]
        fab_items = [i for i in bom_items if i.get("category", "").lower() == "fabrication"]
        install_items = [i for i in bom_items if i.get("category", "").lower() == "installation"]
        other_items = [
            i for i in bom_items
            if i.get("category", "").lower()
            not in {"aluminium", "glass", "hardware", "fabrication", "installation"}
        ]

        # --- Aluminium ---
        total_weight_kg = sum(
            float(i.get("weight_kg", float(i.get("quantity", 0)) * float(i.get("kg_per_unit", 1))))
            for i in aluminium_items
        )
        al_result = self.calculate_aluminum_material_cost(total_weight_kg)
        al_cost = al_result["grand_total_aed"]
        attic_stock_cost = round(al_cost * self.attic_stock_pct, 2)
        al_total = al_cost + attic_stock_cost

        # --- Glass ---
        # Build glass_items list from BOM entries
        glass_bom: List[Dict[str, Any]] = []
        for g in glass_items:
            glass_bom.append({
                "glass_type": g.get("glass_type", g.get("description", "6mm_clear")),
                "area_sqm": float(g.get("area_sqm", float(g.get("quantity", 0)))),
                "processing": g.get("processing", []),
                "wastage_pct": float(g.get("wastage_pct", 0.10)),
            })
        glass_result = self.calculate_glass_cost(glass_bom)
        glass_cost = glass_result["total_cost_aed"]

        # --- Hardware ---
        hardware_bom: List[Dict[str, Any]] = []
        for h in hardware_items:
            hardware_bom.append({
                "hardware_type": h.get("hardware_type", h.get("description", "")),
                "quantity": float(h.get("quantity", 1)),
                "unit_rate_override": float(h.get("unit_rate_aed", 0.0)) or None,
            })
        hardware_result = self.calculate_hardware_cost(hardware_bom)
        hardware_cost = hardware_result["total_cost_aed"]

        # --- Fabrication ---
        # Merge all fabrication operations across items
        merged_ops: Dict[str, float] = {}
        for f in fab_items:
            ops = f.get("operations", {})
            for k, v in ops.items():
                merged_ops[k] = merged_ops.get(k, 0.0) + float(v)
        fab_result = self.calculate_fabrication_cost(merged_ops)
        fab_cost = fab_result["total_cost_aed"]

        # --- Installation ---
        building_height_m = float(
            (project_config or {}).get("building_height_m", 10.0)
        )
        install_bom: List[Dict[str, Any]] = []
        for inst in install_items:
            install_bom.append({
                "install_type": inst.get("install_type", inst.get("description", "")),
                "quantity": float(inst.get("quantity", 1)),
                "height_m": float(inst.get("height_m", building_height_m)),
                "rate_override": float(inst.get("unit_rate_aed", 0.0)) or None,
            })
        install_result = self.calculate_installation_cost(install_bom, building_height_m)
        install_cost = install_result["total_cost_aed"]

        # --- Other / direct supply items ---
        other_cost = sum(
            float(i.get("quantity", 1)) * float(i.get("unit_rate_aed", 0.0))
            for i in other_items
        )

        # --- Direct cost subtotal ---
        direct_cost = al_total + glass_cost + hardware_cost + fab_cost + install_cost + other_cost

        # --- Provisional sums (5 Blind Spot Rules) ---
        provisional_sums: Dict[str, float] = {
            "gpr_test": self.provisional_gpr,
            "water_test": self.provisional_water_test,
            "logistics_permits": self.provisional_logistics_permits,
        }
        total_provisional = sum(provisional_sums.values())

        # --- Overhead ---
        overhead_cost = round((direct_cost + total_provisional) * self.overhead_pct, 2)

        # --- Pre-margin subtotal ---
        pre_margin = direct_cost + total_provisional + overhead_cost

        # --- Margin ---
        margin_cost = round(pre_margin * self.margin_pct, 2)
        selling_price = pre_margin + margin_cost

        # --- International adjustments ---
        intl_adjustments: Dict[str, float] = {}
        if self.is_international:
            forex_buffer = round(selling_price * _FOREX_BUFFER_PCT, 2)
            bg_fee = round(selling_price * _BG_FEE_PCT, 2)
            mobilization = _MOBILIZATION_AED
            intl_adjustments = {
                "forex_buffer_3pct": forex_buffer,
                "bg_fee_2_5pct": bg_fee,
                "mobilization_aed": mobilization,
            }
            selling_price = round(
                selling_price + forex_buffer + bg_fee + mobilization, 2
            )

        # --- Retention note (never in cashflow) ---
        retention_pct = float((project_config or {}).get("retention_pct", 0.10))
        retention_amount = round(selling_price * retention_pct, 2)

        return {
            "bom_summary": {
                "aluminium_items": len(aluminium_items),
                "glass_items": len(glass_items),
                "hardware_items": len(hardware_items),
                "fabrication_items": len(fab_items),
                "installation_items": len(install_items),
                "other_items": len(other_items),
            },
            "cost_breakdown": {
                "aluminium_material_aed": round(al_cost, 2),
                "attic_stock_2pct_aed": attic_stock_cost,
                "aluminium_total_aed": round(al_total, 2),
                "glass_aed": round(glass_cost, 2),
                "hardware_aed": round(hardware_cost, 2),
                "fabrication_labour_aed": round(fab_cost, 2),
                "installation_labour_aed": round(install_cost, 2),
                "other_aed": round(other_cost, 2),
                "direct_cost_aed": round(direct_cost, 2),
            },
            "provisional_sums": provisional_sums,
            "total_provisional_aed": round(total_provisional, 2),
            "overhead": {
                "rate_pct": round(self.overhead_pct * 100, 1),
                "overhead_aed": overhead_cost,
            },
            "pre_margin_subtotal_aed": round(pre_margin, 2),
            "margin": {
                "rate_pct": round(self.margin_pct * 100, 1),
                "margin_aed": margin_cost,
            },
            "international_adjustments": intl_adjustments,
            "selling_price_aed": round(selling_price, 2),
            "retention": {
                "rate_pct": round(retention_pct * 100, 1),
                "amount_aed": retention_amount,
                "note": "Retention locked 12 months — excluded from cashflow projections",
            },
            "aluminium_detail": al_result,
            "glass_detail": glass_result,
            "hardware_detail": hardware_result,
            "fabrication_detail": fab_result,
            "installation_detail": install_result,
        }

    # ------------------------------------------------------------------
    # 7. VO costing
    # ------------------------------------------------------------------

    def calculate_vo_cost(
        self,
        delta_items: List[Dict[str, Any]],
        base_costs: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Calculate the cost of a Variation Order (VO) from delta BOM items.

        delta_items: list of dicts like BOM items but with a 'change_type' key:
            'add'     — new item being added
            'remove'  — existing item being deleted (negative cost impact)
            'modify'  — change from base quantity; must include 'base_quantity' and 'new_quantity'

        base_costs: optional dict carrying base estimate rates for cross-check.

        Returns a VO cost summary including additive, deductive, and net values.
        """
        additions: List[Dict[str, Any]] = []
        deductions: List[Dict[str, Any]] = []

        total_addition_aed = 0.0
        total_deduction_aed = 0.0

        for item in delta_items:
            change_type = item.get("change_type", "add").lower()
            category = item.get("category", "other").lower()
            description = item.get("description", "")
            unit_rate = float(item.get("unit_rate_aed", 0.0))

            if change_type == "add":
                qty = float(item.get("quantity", 0.0))
                cost = qty * unit_rate
                additions.append({
                    "description": description,
                    "category": category,
                    "quantity": qty,
                    "unit_rate_aed": round(unit_rate, 2),
                    "cost_aed": round(cost, 2),
                })
                total_addition_aed += cost

            elif change_type == "remove":
                qty = float(item.get("quantity", 0.0))
                cost = qty * unit_rate
                deductions.append({
                    "description": description,
                    "category": category,
                    "quantity": qty,
                    "unit_rate_aed": round(unit_rate, 2),
                    "cost_aed": round(cost, 2),
                })
                total_deduction_aed += cost

            elif change_type == "modify":
                base_qty = float(item.get("base_quantity", 0.0))
                new_qty = float(item.get("new_quantity", 0.0))
                delta_qty = new_qty - base_qty
                cost = delta_qty * unit_rate
                if cost >= 0:
                    additions.append({
                        "description": f"MODIFY: {description}",
                        "category": category,
                        "base_qty": base_qty,
                        "new_qty": new_qty,
                        "delta_qty": delta_qty,
                        "unit_rate_aed": round(unit_rate, 2),
                        "cost_aed": round(cost, 2),
                    })
                    total_addition_aed += cost
                else:
                    deductions.append({
                        "description": f"MODIFY: {description}",
                        "category": category,
                        "base_qty": base_qty,
                        "new_qty": new_qty,
                        "delta_qty": delta_qty,
                        "unit_rate_aed": round(unit_rate, 2),
                        "cost_aed": round(abs(cost), 2),
                    })
                    total_deduction_aed += abs(cost)

        net_cost = total_addition_aed - total_deduction_aed

        # Apply overhead and margin to the net VO value
        overhead_aed = round(net_cost * self.overhead_pct, 2)
        pre_margin = net_cost + overhead_aed
        margin_aed = round(pre_margin * self.margin_pct, 2)
        vo_selling_price = pre_margin + margin_aed

        # International adjustments
        intl_adjustments: Dict[str, float] = {}
        if self.is_international:
            forex_buffer = round(vo_selling_price * _FOREX_BUFFER_PCT, 2)
            bg_fee = round(vo_selling_price * _BG_FEE_PCT, 2)
            intl_adjustments = {
                "forex_buffer_3pct": forex_buffer,
                "bg_fee_2_5pct": bg_fee,
            }
            vo_selling_price = round(vo_selling_price + forex_buffer + bg_fee, 2)

        return {
            "additions": additions,
            "deductions": deductions,
            "total_addition_aed": round(total_addition_aed, 2),
            "total_deduction_aed": round(total_deduction_aed, 2),
            "net_direct_cost_aed": round(net_cost, 2),
            "overhead_aed": overhead_aed,
            "margin_aed": margin_aed,
            "international_adjustments": intl_adjustments,
            "vo_selling_price_aed": round(vo_selling_price, 2),
            "vo_type": "additive" if net_cost >= 0 else "deductive",
        }

    # ------------------------------------------------------------------
    # 8. Utility: apply margins to any direct cost
    # ------------------------------------------------------------------

    def apply_margins(
        self,
        direct_cost: float,
        margin_pct: Optional[float] = None,
        overhead_pct: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Apply overhead and margin to a direct cost figure.

        Returns a dict with all intermediate values.
        """
        ohd_pct = overhead_pct if overhead_pct is not None else self.overhead_pct
        mgn_pct = margin_pct if margin_pct is not None else self.margin_pct

        overhead_aed = round(direct_cost * ohd_pct, 2)
        pre_margin = direct_cost + overhead_aed
        margin_aed = round(pre_margin * mgn_pct, 2)
        selling_price = round(pre_margin + margin_aed, 2)

        return {
            "direct_cost_aed": round(direct_cost, 2),
            "overhead_pct": round(ohd_pct * 100, 2),
            "overhead_aed": overhead_aed,
            "pre_margin_aed": round(pre_margin, 2),
            "margin_pct": round(mgn_pct * 100, 2),
            "margin_aed": margin_aed,
            "selling_price_aed": selling_price,
        }

    # ------------------------------------------------------------------
    # 9. Rate card export (useful for quoting sub-items)
    # ------------------------------------------------------------------

    def get_rate_card(self) -> Dict[str, Any]:
        """
        Export the current rate card (glass, hardware, install, aluminium).
        """
        return {
            "aluminium": {
                "lme_usd_mt": self.lme_usd_mt,
                "billet_premium_usd_mt": self.billet_premium,
                "extrusion_premium_usd_mt": self.extrusion_premium,
                "powder_coating_aed_kg": self.powder_coating,
                "anodizing_aed_kg": self.anodizing_aed_kg,
                "usd_aed": self.usd_aed,
                "all_in_rate_aed_kg": self.aluminium_rate_per_kg(),
            },
            "glass_base_rates_aed_sqm": dict(_GLASS_BASE_RATES),
            "glass_processing_surcharges": dict(_GLASS_PROCESSING_SURCHARGES),
            "hardware_rates_aed": dict(_HARDWARE_RATES),
            "installation_rates_aed": dict(_INSTALL_RATES),
            "fabrication_times_min": dict(_FAB_TIMES),
            "factory_hourly_rate_aed": self.factory_hourly_rate,
            "site_hourly_rate_aed": self.site_hourly_rate,
            "overhead_pct": round(self.overhead_pct * 100, 1),
            "margin_pct": round(self.margin_pct * 100, 1),
            "attic_stock_pct": round(self.attic_stock_pct * 100, 1),
        }


# ---------------------------------------------------------------------------
# Internal helpers (module-private)
# ---------------------------------------------------------------------------

def _merge_rates(engine: CostingEngine, rates: Dict[str, Any]) -> None:
    """Merge financial_rates dict into an existing CostingEngine instance."""
    if "lme_usd_mt" in rates:
        engine.lme_usd_mt = float(rates["lme_usd_mt"])
    if "billet_premium" in rates:
        engine.billet_premium = float(rates["billet_premium"])
    if "extrusion_premium" in rates:
        engine.extrusion_premium = float(rates["extrusion_premium"])
    if "powder_coating_aed_kg" in rates:
        engine.powder_coating = float(rates["powder_coating_aed_kg"])
    if "usd_aed" in rates:
        engine.usd_aed = float(rates["usd_aed"])
    if "anodizing_aed_kg" in rates:
        engine.anodizing_aed_kg = float(rates["anodizing_aed_kg"])
    if "factory_hourly_rate" in rates:
        engine.factory_hourly_rate = float(rates["factory_hourly_rate"])


def _merge_config(engine: CostingEngine, cfg: Dict[str, Any]) -> None:
    """Merge project_config dict into an existing CostingEngine instance."""
    if "overhead_pct" in cfg:
        engine.overhead_pct = float(cfg["overhead_pct"])
    if "margin_pct" in cfg:
        engine.margin_pct = float(cfg["margin_pct"])
    if "attic_stock_pct" in cfg:
        engine.attic_stock_pct = float(cfg["attic_stock_pct"])
    if "is_international" in cfg:
        engine.is_international = bool(cfg["is_international"])
    if "provisional_gpr_aed" in cfg:
        engine.provisional_gpr = float(cfg["provisional_gpr_aed"])
    if "provisional_water_test_aed" in cfg:
        engine.provisional_water_test = float(cfg["provisional_water_test_aed"])
    if "provisional_logistics_permits_aed" in cfg:
        engine.provisional_logistics_permits = float(cfg["provisional_logistics_permits_aed"])
    if "factory_hourly_rate" in cfg:
        engine.factory_hourly_rate = float(cfg["factory_hourly_rate"])
    if "site_hourly_rate" in cfg:
        engine.site_hourly_rate = float(cfg["site_hourly_rate"])

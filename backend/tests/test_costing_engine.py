"""
test_costing_engine.py — Comprehensive unit tests for CostingEngine.

Tests cover:
  - Aluminium material cost calculation (LME-based pricing, finish surcharges)
  - Glass cost for different types (IGU, Low-E, laminated) with processing surcharges
  - Hardware cost calculation with standard and override rates
  - Fabrication cost with multiple operations
  - Installation cost with height premiums (>15 m, >30 m, >50 m)
  - Full estimate rollup (overhead 12%, margin 18%, attic stock 2%)
  - International mode (3% forex, 2.5% BG fee, AED 25k mobilization)
  - Variation Order (VO) costing — additive, deductive, modify
  - apply_margins utility
  - Edge cases: empty BOM, zero weight, negative/zero values

All tests are pure unit tests; no database or external services required.
"""

import math
import pytest


# ---------------------------------------------------------------------------
# Module-level constants mirrored from costing_engine (for assertion math)
# ---------------------------------------------------------------------------
_DEFAULT_LME_USD_MT = 2350.0
_DEFAULT_BILLET_PREMIUM = 400.0
_DEFAULT_EXTRUSION_PREMIUM = 800.0
_DEFAULT_POWDER_COATING = 15.0
_DEFAULT_USD_AED = 3.6725
_DEFAULT_OVERHEAD_PCT = 0.12
_DEFAULT_MARGIN_PCT = 0.18
_DEFAULT_ATTIC_STOCK_PCT = 0.02
_FOREX_BUFFER_PCT = 0.03
_BG_FEE_PCT = 0.025
_MOBILIZATION_AED = 25_000.0


# ===========================================================================
# Class 1: Aluminium Material Cost
# ===========================================================================

class TestAluminiumMaterialCost:
    """Tests for calculate_aluminum_material_cost and aluminium_rate_per_kg."""

    def test_default_rate_per_kg_formula(self, default_costing_engine):
        """
        Verify the all-in AED/kg rate uses the correct formula:
            rate = ((LME + billet + extrusion) / 1000 * USD_AED) + powder_coat
        """
        engine = default_costing_engine
        expected = (
            (_DEFAULT_LME_USD_MT + _DEFAULT_BILLET_PREMIUM + _DEFAULT_EXTRUSION_PREMIUM)
            / 1000.0
            * _DEFAULT_USD_AED
        ) + _DEFAULT_POWDER_COATING
        assert abs(engine.aluminium_rate_per_kg() - expected) < 0.001

    def test_basic_aluminium_cost_100kg(self, default_costing_engine):
        """
        100 kg at default rates should produce grand_total = 100 × rate_per_kg.
        Result keys: total_weight_kg, rate_per_kg_aed, base_cost_aed,
                     finish, finish_surcharge_aed, grand_total_aed.
        """
        result = default_costing_engine.calculate_aluminum_material_cost(100.0)
        assert result["total_weight_kg"] == 100.0
        assert result["finish"] == "powder_coat"
        assert result["finish_surcharge_aed"] == 0.0
        expected_rate = default_costing_engine.aluminium_rate_per_kg()
        assert abs(result["rate_per_kg_aed"] - expected_rate) < 0.001
        assert abs(result["grand_total_aed"] - 100.0 * expected_rate) < 0.1

    def test_lme_override_raises_rate(self, default_costing_engine):
        """
        Passing lme_usd_mt override should increase the rate proportionally.
        Higher LME price → higher cost. Instance LME must be unchanged after call.
        """
        original_lme = default_costing_engine.lme_usd_mt
        result_high = default_costing_engine.calculate_aluminum_material_cost(
            100.0, lme_usd_mt=3000.0
        )
        result_normal = default_costing_engine.calculate_aluminum_material_cost(100.0)
        assert result_high["grand_total_aed"] > result_normal["grand_total_aed"]
        # Instance state must not be mutated
        assert default_costing_engine.lme_usd_mt == original_lme

    def test_mill_finish_reduces_cost(self, default_costing_engine):
        """
        'mill' finish removes the powder coat cost → grand_total < powder_coat result.
        finish_surcharge_aed should be negative (deduction of powder cost).
        """
        result_pc = default_costing_engine.calculate_aluminum_material_cost(200.0, finish="powder_coat")
        result_mill = default_costing_engine.calculate_aluminum_material_cost(200.0, finish="mill")
        assert result_mill["grand_total_aed"] < result_pc["grand_total_aed"]
        assert result_mill["finish_surcharge_aed"] < 0.0

    def test_anodize_finish_surcharge(self, default_costing_engine):
        """
        'anodize' finish applies delta (anodizing_rate - powder_coat_rate) per kg.
        With anodizing=18 AED/kg and powder=15 AED/kg, surcharge = +3 AED/kg.
        """
        weight = 100.0
        result = default_costing_engine.calculate_aluminum_material_cost(weight, finish="anodize")
        expected_surcharge = weight * (default_costing_engine.anodizing_aed_kg - default_costing_engine.powder_coating)
        assert abs(result["finish_surcharge_aed"] - expected_surcharge) < 0.01

    def test_zero_weight_returns_zero_cost(self, default_costing_engine):
        """Zero weight input should return zero total cost (no division by zero)."""
        result = default_costing_engine.calculate_aluminum_material_cost(0.0)
        assert result["grand_total_aed"] == 0.0
        assert result["base_cost_aed"] == 0.0

    def test_deterministic_with_known_lme(self):
        """
        With LME=2000, billet=400, extrusion=800, powder=15, USD/AED=3.6725,
        rate = (2000+400+800)/1000*3.6725+15 = 3.2*3.6725+15 = 11.752+15 = 26.752 AED/kg.
        1000 kg → 26 752 AED.
        """
        from app.services.costing_engine import CostingEngine
        engine = CostingEngine(
            financial_rates={
                "lme_usd_mt": 2000.0,
                "billet_premium": 400.0,
                "extrusion_premium": 800.0,
                "powder_coating_aed_kg": 15.0,
                "usd_aed": 3.6725,
            }
        )
        result = engine.calculate_aluminum_material_cost(1000.0)
        expected_rate = (2000.0 + 400.0 + 800.0) / 1000.0 * 3.6725 + 15.0
        assert abs(result["rate_per_kg_aed"] - expected_rate) < 0.001
        assert abs(result["grand_total_aed"] - 1000.0 * expected_rate) < 0.5


# ===========================================================================
# Class 2: Glass Cost
# ===========================================================================

class TestGlassCost:
    """Tests for calculate_glass_cost with different glass types and processing."""

    def test_single_clear_glass_item(self, default_costing_engine):
        """
        10 sqm of 6mm_clear at 45.0 AED/sqm with 10% wastage:
        area_with_wastage = 10 × 1.10 = 11.0 sqm
        line_cost = 11.0 × 45.0 = 495.0 AED
        """
        items = [{"glass_type": "6mm_clear", "area_sqm": 10.0}]
        result = default_costing_engine.calculate_glass_cost(items)
        assert result["total_area_sqm"] == 10.0
        # 10 sqm × 1.10 wastage × 45.0 AED/sqm
        assert abs(result["total_cost_aed"] - 495.0) < 0.01
        assert len(result["line_items"]) == 1
        assert result["line_items"][0]["base_rate_aed_sqm"] == 45.0

    def test_igu_lowe_glass_rate(self, default_costing_engine):
        """
        igu_lowe has a base rate of 195.0 AED/sqm.
        50 sqm with 10% wastage = 55 sqm × 195 = 10 725 AED.
        """
        items = [{"glass_type": "igu_lowe", "area_sqm": 50.0}]
        result = default_costing_engine.calculate_glass_cost(items)
        assert result["line_items"][0]["base_rate_aed_sqm"] == 195.0
        assert abs(result["total_cost_aed"] - 50.0 * 1.10 * 195.0) < 0.1

    def test_laminated_glass_rate(self, default_costing_engine):
        """lam_6_6 has base rate 120 AED/sqm; verify line cost calculation."""
        items = [{"glass_type": "lam_6_6", "area_sqm": 20.0, "wastage_pct": 0.05}]
        result = default_costing_engine.calculate_glass_cost(items)
        # 20 × 1.05 × 120 = 2520
        assert abs(result["total_cost_aed"] - 20.0 * 1.05 * 120.0) < 0.1

    def test_tempering_surcharge_applied(self, default_costing_engine):
        """
        tempering surcharge = +30%.  10mm_clear at 72 AED/sqm → effective = 72 × 1.30 = 93.60.
        10 sqm × 1.10 wastage × 93.60 = 1 029.60 AED.
        """
        items = [
            {
                "glass_type": "10mm_clear",
                "area_sqm": 10.0,
                "processing": ["tempering"],
            }
        ]
        result = default_costing_engine.calculate_glass_cost(items)
        expected_rate = 72.0 * 1.30
        expected_cost = 10.0 * 1.10 * expected_rate
        assert abs(result["line_items"][0]["effective_rate_aed_sqm"] - expected_rate) < 0.01
        assert abs(result["total_cost_aed"] - expected_cost) < 0.1

    def test_multiple_processing_surcharges_stacked(self, default_costing_engine):
        """
        heat_soak (+15%) + ceramic_frit (+25%) = +40% stacked on base rate.
        igu_triple at 280 AED/sqm → 280 × 1.40 = 392 AED/sqm.
        """
        items = [
            {
                "glass_type": "igu_triple",
                "area_sqm": 5.0,
                "processing": ["heat_soak", "ceramic_frit"],
                "wastage_pct": 0.0,
            }
        ]
        result = default_costing_engine.calculate_glass_cost(items)
        expected_rate = 280.0 * (1.0 + 0.15 + 0.25)
        assert abs(result["line_items"][0]["effective_rate_aed_sqm"] - expected_rate) < 0.01
        assert abs(result["total_cost_aed"] - 5.0 * expected_rate) < 0.1

    def test_area_from_width_height_quantity(self, default_costing_engine):
        """
        Width/height/quantity form: 1000mm × 2000mm × 5 panes.
        area = (1.0 × 2.0) × 5 = 10 sqm before wastage.
        """
        items = [
            {
                "glass_type": "6mm_clear",
                "width_mm": 1000.0,
                "height_mm": 2000.0,
                "quantity": 5,
            }
        ]
        result = default_costing_engine.calculate_glass_cost(items)
        assert abs(result["total_area_sqm"] - 10.0) < 0.001

    def test_empty_glass_items(self, default_costing_engine):
        """Empty glass_items list must return zero totals without error."""
        result = default_costing_engine.calculate_glass_cost([])
        assert result["total_area_sqm"] == 0.0
        assert result["total_cost_aed"] == 0.0
        assert result["line_items"] == []

    def test_unknown_glass_type_falls_back_to_6mm_clear(self, default_costing_engine):
        """Unknown glass type must fall back to 6mm_clear base rate (45 AED/sqm)."""
        items = [{"glass_type": "nonexistent_glass", "area_sqm": 10.0}]
        result = default_costing_engine.calculate_glass_cost(items)
        assert result["line_items"][0]["base_rate_aed_sqm"] == 45.0


# ===========================================================================
# Class 3: Hardware Cost
# ===========================================================================

class TestHardwareCost:
    """Tests for calculate_hardware_cost."""

    def test_handle_rate_standard(self, default_costing_engine):
        """10 handles at 45 AED each = 450 AED total."""
        items = [{"hardware_type": "handle", "quantity": 10}]
        result = default_costing_engine.calculate_hardware_cost(items)
        assert abs(result["total_cost_aed"] - 450.0) < 0.01

    def test_multipoint_lock_rate(self, default_costing_engine):
        """5 multipoint locks at 220 AED = 1100 AED."""
        items = [{"hardware_type": "multipoint_lock", "quantity": 5}]
        result = default_costing_engine.calculate_hardware_cost(items)
        assert abs(result["total_cost_aed"] - 1100.0) < 0.01

    def test_linear_hardware_items(self, default_costing_engine):
        """
        Gasket at 8 AED/lm for 50 lm = 400 AED.
        Seal at 12 AED/lm for 30 lm = 360 AED.
        Total = 760 AED.
        """
        items = [
            {"hardware_type": "gasket_m", "quantity": 50.0},
            {"hardware_type": "seal_m", "quantity": 30.0},
        ]
        result = default_costing_engine.calculate_hardware_cost(items)
        assert abs(result["total_cost_aed"] - 760.0) < 0.01
        assert len(result["line_items"]) == 2

    def test_unit_rate_override(self, default_costing_engine):
        """
        unit_rate_override supersedes the catalog rate.
        1 bracket with override 200 AED (catalog = 65) → 200 AED.
        """
        items = [{"hardware_type": "bracket", "quantity": 1, "unit_rate_override": 200.0}]
        result = default_costing_engine.calculate_hardware_cost(items)
        assert result["line_items"][0]["unit_rate_aed"] == 200.0
        assert abs(result["total_cost_aed"] - 200.0) < 0.01

    def test_unknown_hardware_type_zero_rate(self, default_costing_engine):
        """Unknown hardware type (no override) must produce a 0.0 rate without error."""
        items = [{"hardware_type": "UNKNOWN_PART_XYZ", "quantity": 5}]
        result = default_costing_engine.calculate_hardware_cost(items)
        assert result["line_items"][0]["unit_rate_aed"] == 0.0
        assert result["total_cost_aed"] == 0.0

    def test_empty_hardware_items(self, default_costing_engine):
        """Empty list must return 0.0 total cost."""
        result = default_costing_engine.calculate_hardware_cost([])
        assert result["total_cost_aed"] == 0.0


# ===========================================================================
# Class 4: Fabrication Cost
# ===========================================================================

class TestFabricationCost:
    """Tests for calculate_fabrication_cost."""

    def test_cnc_cuts_only(self, default_costing_engine):
        """
        100 CNC cuts × 3.0 min/cut = 300 min.
        Factory rate = 85 AED/hr = 85/60 AED/min.
        Cost = 300 × (85/60) = 425.0 AED.
        """
        result = default_costing_engine.calculate_fabrication_cost({"cnc_cuts": 100})
        assert abs(result["operations"]["cnc_cuts"]["minutes"] - 300.0) < 0.01
        expected_cost = 300.0 * (85.0 / 60.0)
        assert abs(result["operations"]["cnc_cuts"]["cost_aed"] - expected_cost) < 0.1

    def test_assembly_joints(self, default_costing_engine):
        """
        20 assembly joints × 15 min/joint = 300 min = 5 hours.
        Cost at 85 AED/hr = 425.0 AED.
        """
        result = default_costing_engine.calculate_fabrication_cost({"assembly_joints": 20})
        assert abs(result["operations"]["assembly_joints"]["minutes"] - 300.0) < 0.01
        assert abs(result["total_hours"] - 5.0) < 0.01

    def test_multiple_operations_total(self, default_costing_engine):
        """
        Mixed operations: cnc_cuts=10 (30 min) + drill_holes=20 (30 min) + glazing_windows=5 (40 min).
        Total = 100 min at 85/60 AED/min.
        """
        ops = {"cnc_cuts": 10, "drill_holes": 20, "glazing_windows": 5}
        result = default_costing_engine.calculate_fabrication_cost(ops)
        # cnc: 10×3=30, drill: 20×1.5=30, glazing_windows: 5×8=40
        assert abs(result["total_minutes"] - 100.0) < 0.01
        expected_cost = 100.0 * (85.0 / 60.0)
        assert abs(result["total_cost_aed"] - expected_cost) < 0.1

    def test_hourly_rate_override(self, default_costing_engine):
        """
        Custom hourly_rate=60 AED applied to 60 minutes of work = 60 AED.
        (60 min × 60/60 AED/min = 60 AED)
        """
        ops = {"manual_cuts": 12}  # 12 × 5 min = 60 min
        result = default_costing_engine.calculate_fabrication_cost(ops, hourly_rate=60.0)
        assert result["hourly_rate_aed"] == 60.0
        assert abs(result["total_minutes"] - 60.0) < 0.01
        assert abs(result["total_cost_aed"] - 60.0) < 0.1

    def test_cnc_setup_batch(self, default_costing_engine):
        """
        3 CNC batches × 30 min/batch = 90 minutes of setup time.
        """
        result = default_costing_engine.calculate_fabrication_cost({"cnc_batches": 3})
        assert abs(result["operations"]["cnc_setup"]["minutes"] - 90.0) < 0.01

    def test_empty_operations_zero_cost(self, default_costing_engine):
        """Empty operations dict must return zero cost and minutes."""
        result = default_costing_engine.calculate_fabrication_cost({})
        assert result["total_minutes"] == 0.0
        assert result["total_cost_aed"] == 0.0

    def test_silicone_per_lm(self, default_costing_engine):
        """
        100 lm of silicone × 2.0 min/lm = 200 minutes.
        """
        result = default_costing_engine.calculate_fabrication_cost({"silicone_lm": 100.0})
        assert abs(result["operations"]["silicone"]["minutes"] - 200.0) < 0.01


# ===========================================================================
# Class 5: Installation Cost with Height Premiums
# ===========================================================================

class TestInstallationCost:
    """Tests for calculate_installation_cost and height premium logic."""

    def test_ground_level_no_premium(self, default_costing_engine):
        """
        At 10 m height (≤ 15 m), no height premium should be applied (0%).
        100 sqm curtain wall at 180 AED/sqm = 18 000 AED.
        """
        items = [{"install_type": "curtain_wall_sqm", "quantity": 100.0}]
        result = default_costing_engine.calculate_installation_cost(items, building_height_m=10.0)
        assert result["default_height_premium_pct"] == 0.0
        assert abs(result["total_cost_aed"] - 18_000.0) < 0.1

    def test_height_above_15m_20pct_premium(self, default_costing_engine):
        """
        At 20 m height (>15 m, ≤ 30 m), premium = +20%.
        100 sqm × 180 × 1.20 = 21 600 AED.
        """
        items = [{"install_type": "curtain_wall_sqm", "quantity": 100.0}]
        result = default_costing_engine.calculate_installation_cost(items, building_height_m=20.0)
        assert result["default_height_premium_pct"] == 20.0
        assert abs(result["total_cost_aed"] - 100.0 * 180.0 * 1.20) < 0.1

    def test_height_above_30m_40pct_premium(self, default_costing_engine):
        """
        At 35 m height (>30 m, ≤ 50 m), premium = +40%.
        50 window units at 120 AED each × 1.40 = 8 400 AED.
        """
        items = [{"install_type": "window_unit", "quantity": 50.0}]
        result = default_costing_engine.calculate_installation_cost(items, building_height_m=35.0)
        assert result["default_height_premium_pct"] == 40.0
        assert abs(result["total_cost_aed"] - 50.0 * 120.0 * 1.40) < 0.1

    def test_height_above_50m_60pct_premium(self, default_costing_engine):
        """
        At 55 m height (>50 m), premium = +60%.
        10 door units at 250 AED × 1.60 = 4 000 AED.
        """
        items = [{"install_type": "door_unit", "quantity": 10.0}]
        result = default_costing_engine.calculate_installation_cost(items, building_height_m=55.0)
        assert result["default_height_premium_pct"] == 60.0
        assert abs(result["total_cost_aed"] - 10.0 * 250.0 * 1.60) < 0.1

    def test_per_item_height_override(self, default_costing_engine):
        """
        Two items: one at 10 m (0% premium), one at 55 m (60% premium).
        Line costs should differ by 60%.
        """
        items = [
            {"install_type": "acp_sqm", "quantity": 100.0, "height_m": 10.0},
            {"install_type": "acp_sqm", "quantity": 100.0, "height_m": 55.0},
        ]
        result = default_costing_engine.calculate_installation_cost(items, building_height_m=10.0)
        line1 = result["line_items"][0]
        line2 = result["line_items"][1]
        assert line1["height_premium_pct"] == 0.0
        assert line2["height_premium_pct"] == 60.0
        expected_ratio = 1.60 / 1.00
        assert abs(line2["effective_rate_aed"] / line1["effective_rate_aed"] - expected_ratio) < 0.01

    def test_skylight_and_balustrade(self, default_costing_engine):
        """
        Skylight 30 sqm at 240 AED/sqm + balustrade 50 lm at 320 AED/lm, ground level.
        Total = 7200 + 16000 = 23 200 AED.
        """
        items = [
            {"install_type": "skylight_sqm", "quantity": 30.0},
            {"install_type": "balustrade_lm", "quantity": 50.0},
        ]
        result = default_costing_engine.calculate_installation_cost(items, building_height_m=5.0)
        assert abs(result["total_cost_aed"] - (30.0 * 240.0 + 50.0 * 320.0)) < 0.1


# ===========================================================================
# Class 6: Full Estimate Rollup
# ===========================================================================

class TestFullEstimateRollup:
    """Tests for calculate_full_estimate — overhead, margin, attic stock, provisionals."""

    def test_full_estimate_returns_required_keys(self, default_costing_engine, simple_bom):
        """Full estimate result must contain the mandatory top-level keys."""
        result = default_costing_engine.calculate_full_estimate(simple_bom)
        for key in [
            "bom_summary", "cost_breakdown", "provisional_sums",
            "overhead", "margin", "selling_price_aed", "retention",
        ]:
            assert key in result, f"Missing key: {key}"

    def test_overhead_is_12pct_of_direct_plus_provisional(self, default_costing_engine, simple_bom):
        """
        Overhead = 12% × (direct_cost + total_provisional).
        Verify using the values returned by the engine itself.
        """
        result = default_costing_engine.calculate_full_estimate(simple_bom)
        direct = result["cost_breakdown"]["direct_cost_aed"]
        provisional = result["total_provisional_aed"]
        expected_overhead = round((direct + provisional) * 0.12, 2)
        assert abs(result["overhead"]["overhead_aed"] - expected_overhead) < 0.5

    def test_margin_is_18pct_of_pre_margin(self, default_costing_engine, simple_bom):
        """
        Margin = 18% × (direct + provisional + overhead).
        Verify using pre_margin_subtotal_aed from the result.
        """
        result = default_costing_engine.calculate_full_estimate(simple_bom)
        pre_margin = result["pre_margin_subtotal_aed"]
        expected_margin = round(pre_margin * 0.18, 2)
        assert abs(result["margin"]["margin_aed"] - expected_margin) < 0.5

    def test_attic_stock_is_2pct_of_aluminium_material(self, default_costing_engine, simple_bom):
        """
        Attic stock = 2% of aluminium material cost (before attic addition).
        cost_breakdown must report both aluminium_material_aed and attic_stock_2pct_aed.
        """
        result = default_costing_engine.calculate_full_estimate(simple_bom)
        al_material = result["cost_breakdown"]["aluminium_material_aed"]
        attic = result["cost_breakdown"]["attic_stock_2pct_aed"]
        assert abs(attic - round(al_material * 0.02, 2)) < 0.01

    def test_provisional_sums_included(self, default_costing_engine, simple_bom):
        """
        Default provisionals: GPR=15000, water_test=8500, logistics=5000 = 28500 AED.
        """
        result = default_costing_engine.calculate_full_estimate(simple_bom)
        assert abs(result["total_provisional_aed"] - 28_500.0) < 1.0

    def test_selling_price_equals_pre_margin_plus_margin(self, default_costing_engine, simple_bom):
        """
        Selling price (domestic) = pre_margin + margin.
        Arithmetic identity must hold to within 1 AED rounding.
        """
        result = default_costing_engine.calculate_full_estimate(simple_bom)
        expected = result["pre_margin_subtotal_aed"] + result["margin"]["margin_aed"]
        assert abs(result["selling_price_aed"] - expected) < 1.0

    def test_empty_bom_returns_zero_material_costs(self, default_costing_engine):
        """
        An empty BOM should produce zero aluminium/glass/hardware costs but
        still include provisional sums, overhead on provisionals, and margin.
        """
        result = default_costing_engine.calculate_full_estimate([])
        assert result["cost_breakdown"]["aluminium_material_aed"] == 0.0
        assert result["cost_breakdown"]["glass_aed"] == 0.0
        assert result["cost_breakdown"]["hardware_aed"] == 0.0
        # Provisionals still non-zero
        assert result["total_provisional_aed"] > 0

    def test_retention_10pct_note(self, default_costing_engine, simple_bom):
        """
        Retention at default 10% must be reported in the retention dict
        and its note must mention 'excluded from cashflow'.
        """
        result = default_costing_engine.calculate_full_estimate(simple_bom)
        retention = result["retention"]
        assert retention["rate_pct"] == 10.0
        assert "cashflow" in retention["note"].lower()
        expected_retention = round(result["selling_price_aed"] * 0.10, 2)
        assert abs(retention["amount_aed"] - expected_retention) < 1.0


# ===========================================================================
# Class 7: International Mode
# ===========================================================================

class TestInternationalMode:
    """Tests for international cost additions (forex buffer, BG fee, mobilization)."""

    def test_international_mode_adds_forex_buffer(self, international_costing_engine, simple_bom):
        """
        international_adjustments dict must contain forex_buffer_3pct key.
        Its value should be ~3% of the domestic selling price.
        """
        result = international_costing_engine.calculate_full_estimate(simple_bom)
        intl = result["international_adjustments"]
        assert "forex_buffer_3pct" in intl
        assert intl["forex_buffer_3pct"] > 0

    def test_international_mode_adds_bg_fee(self, international_costing_engine, simple_bom):
        """BG fee of 2.5% must appear in international_adjustments."""
        result = international_costing_engine.calculate_full_estimate(simple_bom)
        intl = result["international_adjustments"]
        assert "bg_fee_2_5pct" in intl
        assert intl["bg_fee_2_5pct"] > 0

    def test_international_mode_includes_mobilization(self, international_costing_engine, simple_bom):
        """AED 25 000 mobilization fee must appear in international_adjustments."""
        result = international_costing_engine.calculate_full_estimate(simple_bom)
        intl = result["international_adjustments"]
        assert intl.get("mobilization_aed") == 25_000.0

    def test_international_selling_price_higher_than_domestic(
        self, default_costing_engine, international_costing_engine, simple_bom
    ):
        """
        International selling price must exceed domestic selling price by the
        sum of forex buffer + BG fee + mobilization.
        """
        domestic = default_costing_engine.calculate_full_estimate(simple_bom)
        intl = international_costing_engine.calculate_full_estimate(simple_bom)
        # International selling price must be strictly higher
        assert intl["selling_price_aed"] > domestic["selling_price_aed"]

    def test_domestic_mode_no_international_adjustments(self, default_costing_engine, simple_bom):
        """Domestic mode must return an empty international_adjustments dict."""
        result = default_costing_engine.calculate_full_estimate(simple_bom)
        assert result["international_adjustments"] == {}


# ===========================================================================
# Class 8: Variation Order Costing
# ===========================================================================

class TestVOCosting:
    """Tests for calculate_vo_cost — additive, deductive, and modify delta items."""

    def test_additive_vo(self, default_costing_engine):
        """
        Adding 10 sqm of curtain wall at 180 AED/sqm = 1800 AED direct cost.
        After overhead (12%) and margin (18%):
          overhead = 1800 × 0.12 = 216
          pre_margin = 2016
          margin = 2016 × 0.18 = 362.88
          vo_selling_price ≈ 2378.88
        """
        delta = [
            {
                "change_type": "add",
                "category": "installation",
                "description": "Extra CW panel",
                "quantity": 10.0,
                "unit_rate_aed": 180.0,
            }
        ]
        result = default_costing_engine.calculate_vo_cost(delta)
        assert result["vo_type"] == "additive"
        assert abs(result["net_direct_cost_aed"] - 1800.0) < 0.01
        assert len(result["additions"]) == 1
        assert len(result["deductions"]) == 0
        # Verify overhead
        expected_overhead = round(1800.0 * 0.12, 2)
        assert abs(result["overhead_aed"] - expected_overhead) < 0.01

    def test_deductive_vo(self, default_costing_engine):
        """
        Removing 5 door units at 250 AED each = -1250 AED net.
        VO type must be 'deductive'; net direct cost is negative.
        """
        delta = [
            {
                "change_type": "remove",
                "category": "installation",
                "description": "Deleted entrance doors",
                "quantity": 5.0,
                "unit_rate_aed": 250.0,
            }
        ]
        result = default_costing_engine.calculate_vo_cost(delta)
        assert result["vo_type"] == "deductive"
        assert result["net_direct_cost_aed"] < 0
        assert len(result["deductions"]) == 1

    def test_modify_increase_vo(self, default_costing_engine):
        """
        Modifying quantity from 50 to 80 sqm at 45 AED/sqm:
        delta_qty = 30, cost = 30 × 45 = 1350 AED (additive).
        """
        delta = [
            {
                "change_type": "modify",
                "description": "Increased glass area",
                "category": "glass",
                "base_quantity": 50.0,
                "new_quantity": 80.0,
                "unit_rate_aed": 45.0,
            }
        ]
        result = default_costing_engine.calculate_vo_cost(delta)
        assert abs(result["net_direct_cost_aed"] - 1350.0) < 0.01
        assert result["vo_type"] == "additive"

    def test_modify_decrease_vo(self, default_costing_engine):
        """
        Modifying from 100 sqm to 70 sqm at 45 AED/sqm:
        delta_qty = -30, cost = -1350 (deductive).
        """
        delta = [
            {
                "change_type": "modify",
                "description": "Reduced glass area",
                "category": "glass",
                "base_quantity": 100.0,
                "new_quantity": 70.0,
                "unit_rate_aed": 45.0,
            }
        ]
        result = default_costing_engine.calculate_vo_cost(delta)
        assert result["vo_type"] == "deductive"
        assert result["net_direct_cost_aed"] < 0

    def test_vo_international_mode(self, international_costing_engine):
        """
        International VO must include forex_buffer_3pct and bg_fee_2_5pct
        but NOT mobilization (mobilization is a one-time project cost, not per VO).
        """
        delta = [
            {
                "change_type": "add",
                "description": "Extra panel",
                "quantity": 100.0,
                "unit_rate_aed": 100.0,
            }
        ]
        result = international_costing_engine.calculate_vo_cost(delta)
        intl = result["international_adjustments"]
        assert "forex_buffer_3pct" in intl
        assert "bg_fee_2_5pct" in intl
        # VOs do not carry mobilization
        assert "mobilization_aed" not in intl


# ===========================================================================
# Class 9: apply_margins Utility
# ===========================================================================

class TestApplyMargins:
    """Tests for the apply_margins utility method."""

    def test_default_margins_12_overhead_18_margin(self, default_costing_engine):
        """
        apply_margins(1000) with defaults:
          overhead = 1000 × 0.12 = 120
          pre_margin = 1120
          margin = 1120 × 0.18 = 201.60
          selling_price = 1321.60
        """
        result = default_costing_engine.apply_margins(1000.0)
        assert abs(result["overhead_aed"] - 120.0) < 0.01
        assert abs(result["pre_margin_aed"] - 1120.0) < 0.01
        assert abs(result["margin_aed"] - 201.60) < 0.01
        assert abs(result["selling_price_aed"] - 1321.60) < 0.01

    def test_custom_overhead_and_margin(self, default_costing_engine):
        """
        apply_margins(1000, margin_pct=0.20, overhead_pct=0.10):
          overhead = 100, pre_margin = 1100, margin = 220, selling = 1320.
        """
        result = default_costing_engine.apply_margins(
            1000.0, margin_pct=0.20, overhead_pct=0.10
        )
        assert abs(result["overhead_aed"] - 100.0) < 0.01
        assert abs(result["pre_margin_aed"] - 1100.0) < 0.01
        assert abs(result["margin_aed"] - 220.0) < 0.01
        assert abs(result["selling_price_aed"] - 1320.0) < 0.01

    def test_zero_direct_cost(self, default_costing_engine):
        """apply_margins(0) must return all zeros without error."""
        result = default_costing_engine.apply_margins(0.0)
        assert result["overhead_aed"] == 0.0
        assert result["margin_aed"] == 0.0
        assert result["selling_price_aed"] == 0.0

    def test_result_keys_present(self, default_costing_engine):
        """Result dict must have all expected keys."""
        result = default_costing_engine.apply_margins(5000.0)
        for key in [
            "direct_cost_aed", "overhead_pct", "overhead_aed",
            "pre_margin_aed", "margin_pct", "margin_aed", "selling_price_aed",
        ]:
            assert key in result, f"Missing key: {key}"

    def test_overhead_pct_reported_as_percentage(self, default_costing_engine):
        """overhead_pct and margin_pct in result must be expressed as % (e.g. 12.0 not 0.12)."""
        result = default_costing_engine.apply_margins(1000.0)
        assert result["overhead_pct"] == 12.0
        assert result["margin_pct"] == 18.0

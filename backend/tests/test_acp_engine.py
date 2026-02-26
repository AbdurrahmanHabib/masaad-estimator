"""
test_acp_engine.py — Comprehensive unit tests for ACPEngine.

Tests cover:
  - optimize_panel_layout: panel grid optimisation, gross area, waste%
  - get_production_specs: legacy wrapper — production size, weight, frame quantities
  - get_fold_details: V-groove depth, gross sheet dimensions, groove coordinates
  - check_fire_compliance: UAE fire regulations by height and building type
  - calculate_subframe: runner/rail/bracket quantities from layout
  - calculate_sealant_quantities: joint lm, sealant volume, fire sealant
  - calculate_material_yield: sheet count, yield%, scrap recovery
  - calculate_dead_load: kN per sqm and per bracket

All tests are pure unit tests; no database or external services required.
"""

import math
import pytest


# ---------------------------------------------------------------------------
# ACP_VARIANTS constants mirrored for assertion math
# ---------------------------------------------------------------------------
ACP_VARIANTS = {
    "PE_4mm": {"thickness_mm": 4.0, "weight_kg_sqm": 5.5, "fire_class": "B2", "price_aed_sqm": 55.0},
    "FR_4mm": {"thickness_mm": 4.0, "weight_kg_sqm": 5.8, "fire_class": "B1", "price_aed_sqm": 85.0},
    "A2_4mm": {"thickness_mm": 4.0, "weight_kg_sqm": 7.2, "fire_class": "A2", "price_aed_sqm": 165.0},
    "A2_6mm": {"thickness_mm": 6.0, "weight_kg_sqm": 10.5, "fire_class": "A2", "price_aed_sqm": 220.0},
}


# ===========================================================================
# Class 1: Panel Layout Optimisation
# ===========================================================================

class TestOptimizePanelLayout:
    """Tests for optimize_panel_layout."""

    def test_small_facade_single_panel(self, acp_engine):
        """
        Facade 1200 × 2000 mm — fits entirely within 1500 × 4000 max → 1 panel.
        Grid: 1 col × 1 row = 1 panel total.
        """
        result = acp_engine.optimize_panel_layout(1200.0, 2000.0)
        assert result["grid"]["total_panels"] == 1
        assert result["grid"]["total_cols"] == 1
        assert result["grid"]["total_rows"] == 1

    def test_exact_multiple_panels(self, acp_engine):
        """
        Facade 3000 × 4000 mm with max_panel_width=1500, max_panel_height=4000.
        3000/1500 = 2 cols exactly, 4000/4000 = 1 row exactly → 2 panels.
        """
        result = acp_engine.optimize_panel_layout(
            3000.0, 4000.0, max_panel_width=1500.0, max_panel_height=4000.0
        )
        assert result["grid"]["total_cols"] == 2
        assert result["grid"]["total_rows"] == 1
        assert result["grid"]["total_panels"] == 2

    def test_facade_with_remainder_column(self, acp_engine):
        """
        Facade 3700 × 3000 mm with max_panel_width=1500.
        Full cols = floor(3700/1500) = 2, remainder = 700 mm → 3 cols total.
        """
        result = acp_engine.optimize_panel_layout(3700.0, 3000.0, max_panel_width=1500.0)
        assert result["grid"]["total_cols"] == 3

    def test_facade_area_correct(self, acp_engine):
        """
        Facade 5000 × 4000 mm → area = 5.0 × 4.0 = 20.0 sqm.
        """
        result = acp_engine.optimize_panel_layout(5000.0, 4000.0)
        assert abs(result["facade_area_sqm"] - 20.0) < 0.001

    def test_fold_added_to_gross_dimensions(self, acp_engine):
        """
        50 mm fold on 4 sides: standard panel 1500 × 4000 mm gross = 1600 × 4100 mm.
        Check first panel_type has correct gross dimensions.
        """
        result = acp_engine.optimize_panel_layout(
            3000.0, 4000.0, max_panel_width=1500.0, max_panel_height=4000.0
        )
        std = result["panel_types"][0]
        assert abs(std["gross_width_mm"] - (1500.0 + 2 * 50.0)) < 0.1
        assert abs(std["gross_height_mm"] - (4000.0 + 2 * 50.0)) < 0.1

    def test_ordered_area_exceeds_facade_area(self, acp_engine):
        """
        Gross area (including folds) must always exceed net facade area.
        """
        result = acp_engine.optimize_panel_layout(4000.0, 8000.0)
        assert result["ordered_gross_area_sqm"] > result["facade_area_sqm"]

    def test_waste_pct_non_negative(self, acp_engine):
        """Waste percentage must be ≥ 0 (panels include fold area beyond facade)."""
        result = acp_engine.optimize_panel_layout(3000.0, 6000.0)
        assert result["waste_pct"] >= 0.0

    def test_invalid_dimensions_raise(self, acp_engine):
        """Zero or negative facade dimensions must raise ValueError."""
        with pytest.raises(ValueError):
            acp_engine.optimize_panel_layout(0.0, 2000.0)
        with pytest.raises(ValueError):
            acp_engine.optimize_panel_layout(1000.0, -500.0)

    def test_30mm_fold_engine_gross_dimensions(self, acp_engine_30mm):
        """
        30 mm fold engine: panel 1000 × 2000 → gross = 1060 × 2060.
        """
        result = acp_engine_30mm.optimize_panel_layout(1000.0, 2000.0)
        std = result["panel_types"][0]
        assert abs(std["gross_width_mm"] - (1000.0 + 2 * 30.0)) < 0.1
        assert abs(std["gross_height_mm"] - (2000.0 + 2 * 30.0)) < 0.1


# ===========================================================================
# Class 2: get_production_specs (legacy wrapper)
# ===========================================================================

class TestProductionSpecs:
    """Tests for get_production_specs."""

    def test_gross_size_includes_fold(self, acp_engine):
        """
        Net 1000 × 2000 mm with 50 mm fold → production size = 1100 × 2100 mm.
        """
        result = acp_engine.get_production_specs(1000.0, 2000.0, "PE_4mm")
        assert abs(result["production_size"]["width"] - 1100.0) < 0.1
        assert abs(result["production_size"]["height"] - 2100.0) < 0.1

    def test_net_face_size_preserved(self, acp_engine):
        """net_face_size must equal the input width and height exactly."""
        result = acp_engine.get_production_specs(800.0, 1600.0, "FR_4mm")
        assert result["net_face_size"]["width"] == 800.0
        assert result["net_face_size"]["height"] == 1600.0

    def test_weight_calculation(self, acp_engine):
        """
        PE_4mm weight = 5.5 kg/sqm.  Panel 1100 × 2100 mm gross = 2.31 sqm.
        net_weight_kg = 2.31 × 5.5 ≈ 12.705 kg.
        """
        result = acp_engine.get_production_specs(1000.0, 2000.0, "PE_4mm")
        gross_area = result["gross_area_sqm"]
        expected_weight = round(gross_area * 5.5, 2)
        assert abs(result["net_weight_kg"] - expected_weight) < 0.1

    def test_fire_class_reported(self, acp_engine):
        """fire_class must match the ACP variant specification."""
        for acp_type, variant in ACP_VARIANTS.items():
            result = acp_engine.get_production_specs(1000.0, 2000.0, acp_type)
            assert result["fire_class"] == variant["fire_class"]

    def test_panel_cost_calculation(self, acp_engine):
        """
        panel_cost_aed = gross_area_sqm × price_aed_sqm.
        PE_4mm at 55 AED/sqm.
        """
        result = acp_engine.get_production_specs(1000.0, 2000.0, "PE_4mm")
        expected_cost = round(result["gross_area_sqm"] * 55.0, 2)
        assert abs(result["panel_cost_aed"] - expected_cost) < 0.1

    def test_unknown_acp_type_falls_back_to_pe_4mm(self, acp_engine):
        """Unknown acp_type must fall back to PE_4mm silently."""
        result = acp_engine.get_production_specs(1000.0, 1000.0, "INVALID_TYPE")
        assert result["acp_type"] == "PE_4mm"


# ===========================================================================
# Class 3: Fold Details (V-groove Geometry)
# ===========================================================================

class TestFoldDetails:
    """Tests for get_fold_details (V-groove routing and fold geometry)."""

    def test_gross_sheet_dimensions(self, acp_engine):
        """
        Panel 1000 × 2000 with 50 mm fold → gross = 1100 × 2100 mm.
        """
        result = acp_engine.get_fold_details(1000.0, 2000.0, "PE_4mm")
        assert abs(result["gross_sheet_width_mm"] - 1100.0) < 0.1
        assert abs(result["gross_sheet_height_mm"] - 2100.0) < 0.1

    def test_groove_depth_leaves_0_3mm_skin(self, acp_engine):
        """
        Groove depth = thickness - 0.3 mm.
        PE_4mm: depth = 4.0 - 0.3 = 3.7 mm. Skin = 0.3 mm.
        """
        result = acp_engine.get_fold_details(1000.0, 2000.0, "PE_4mm")
        assert abs(result["groove_depth_mm"] - 3.7) < 0.01
        assert result["remaining_skin_mm"] == 0.3

    def test_a2_6mm_groove_depth(self, acp_engine):
        """A2_6mm: thickness=6.0, groove_depth = 6.0 - 0.3 = 5.7 mm."""
        result = acp_engine.get_fold_details(800.0, 1600.0, "A2_6mm")
        assert abs(result["groove_depth_mm"] - 5.7) < 0.01

    def test_four_v_grooves_returned(self, acp_engine):
        """Exactly 4 V-grooves must be returned (left, right, bottom, top)."""
        result = acp_engine.get_fold_details(1200.0, 2400.0, "PE_4mm")
        assert len(result["v_grooves"]) == 4
        sides = {g["side"] for g in result["v_grooves"]}
        assert sides == {"left", "right", "bottom", "top"}

    def test_left_groove_x_position(self, acp_engine):
        """Left groove centreline must be at x = fold_mm (50.0)."""
        result = acp_engine.get_fold_details(1000.0, 2000.0, "PE_4mm")
        left_groove = next(g for g in result["v_grooves"] if g["side"] == "left")
        assert left_groove["x_start"] == 50.0

    def test_four_fold_flanges(self, acp_engine):
        """Exactly 4 fold flanges must be described in fold_pattern."""
        result = acp_engine.get_fold_details(1000.0, 2000.0, "PE_4mm")
        assert len(result["fold_pattern"]) == 4

    def test_corner_notch_4_count(self, acp_engine):
        """corner_notch must describe 4 corner notches."""
        result = acp_engine.get_fold_details(800.0, 1600.0, "PE_4mm")
        assert result["corner_notch"]["count"] == 4

    def test_invalid_acp_type_raises(self, acp_engine):
        """Unknown acp_type in get_fold_details must raise ValueError."""
        with pytest.raises(ValueError):
            acp_engine.get_fold_details(1000.0, 2000.0, "MYSTERY_TYPE")


# ===========================================================================
# Class 4: Fire Compliance
# ===========================================================================

class TestFireCompliance:
    """Tests for check_fire_compliance (UAE Civil Defence rules)."""

    def test_pe_4mm_fails_above_15m(self, acp_engine):
        """
        PE_4mm is B2 class.  Above 15 m requires B1 minimum → NON-COMPLIANT.
        """
        result = acp_engine.check_fire_compliance(20.0, "office", "PE_4mm")
        assert result["compliant"] is False
        assert result["provided_fire_class"] == "B2"
        assert result["required_fire_class"] == "B1"

    def test_fr_4mm_passes_up_to_28m(self, acp_engine):
        """
        FR_4mm is B1 class.  Height 20 m (>15 m, ≤ 28 m) requires B1 → COMPLIANT.
        """
        result = acp_engine.check_fire_compliance(20.0, "office", "FR_4mm")
        assert result["compliant"] is True

    def test_pe_4mm_fails_above_28m(self, acp_engine):
        """PE_4mm (B2) at 30 m height requires A2 → NON-COMPLIANT."""
        result = acp_engine.check_fire_compliance(30.0, "office", "PE_4mm")
        assert result["compliant"] is False
        assert result["required_fire_class"] == "A2"

    def test_a2_4mm_passes_any_height(self, acp_engine):
        """A2_4mm satisfies any height requirement — always COMPLIANT."""
        for height in [5.0, 20.0, 50.0, 100.0]:
            result = acp_engine.check_fire_compliance(height, "office", "A2_4mm")
            assert result["compliant"] is True, f"Expected COMPLIANT at height {height}m"

    def test_hospital_always_requires_a2(self, acp_engine):
        """
        Hospital building type requires A2 regardless of height.
        FR_4mm (B1) must fail even at 5 m height.
        """
        result = acp_engine.check_fire_compliance(5.0, "hospital", "FR_4mm")
        assert result["required_fire_class"] == "A2"
        assert result["compliant"] is False

    def test_escape_route_always_a2(self, acp_engine):
        """'escape' building type forces A2 requirement at any height."""
        result = acp_engine.check_fire_compliance(3.0, "escape", "PE_4mm")
        assert result["required_fire_class"] == "A2"
        assert result["compliant"] is False

    def test_pe_4mm_passes_at_or_below_15m(self, acp_engine):
        """
        PE_4mm (B2) at 15 m or below: B2 is the minimum → COMPLIANT.
        """
        result = acp_engine.check_fire_compliance(10.0, "office", "PE_4mm")
        assert result["compliant"] is True
        assert result["required_fire_class"] == "B2"

    def test_upgrade_recommendation_when_noncompliant(self, acp_engine):
        """
        Non-compliant result must include a recommended_upgrade (non-None).
        """
        result = acp_engine.check_fire_compliance(35.0, "office", "PE_4mm")
        assert result["recommended_upgrade"] is not None

    def test_compliant_no_upgrade_needed(self, acp_engine):
        """Compliant result must report recommended_upgrade as None."""
        result = acp_engine.check_fire_compliance(10.0, "office", "A2_4mm")
        assert result["recommended_upgrade"] is None

    def test_invalid_acp_type_raises(self, acp_engine):
        """Unknown acp_type must raise ValueError."""
        with pytest.raises(ValueError):
            acp_engine.check_fire_compliance(10.0, "office", "UNKNOWN_PANEL")


# ===========================================================================
# Class 5: Subframe Calculation
# ===========================================================================

class TestSubframeCalculation:
    """Tests for calculate_subframe."""

    def _make_layout(self, cols=2, rows=3, panel_w=1500.0, panel_h=1333.0):
        """Helper: create a minimal panel_layout dict for subframe tests."""
        return {
            "facade_area_sqm": (cols * panel_w * rows * panel_h) / 1_000_000.0,
            "grid": {"total_cols": cols, "total_rows": rows},
            "panel_types": [
                {
                    "qty": cols * rows,
                    "net_width_mm": panel_w,
                    "net_height_mm": panel_h,
                    "gross_width_mm": panel_w + 100.0,
                    "gross_height_mm": panel_h + 100.0,
                    "net_area_sqm": (panel_w * panel_h) / 1_000_000.0,
                    "gross_area_sqm": ((panel_w + 100.0) * (panel_h + 100.0)) / 1_000_000.0,
                }
            ],
        }

    def test_runner_spacing_at_low_wind(self, acp_engine):
        """
        Wind = 0.5 kPa → runner spacing = 600 mm (maximum).
        """
        layout = self._make_layout()
        result = acp_engine.calculate_subframe(layout, 10.0, 0.5)
        assert result["runner_spacing_mm"] == 600.0

    def test_runner_spacing_at_high_wind(self, acp_engine):
        """
        Wind = 2.0 kPa → runner spacing = 400 mm (minimum).
        """
        layout = self._make_layout()
        result = acp_engine.calculate_subframe(layout, 10.0, 2.0)
        assert result["runner_spacing_mm"] == 400.0

    def test_bracket_spacing_reduced_above_15m(self, acp_engine):
        """
        Above 15 m: bracket spacing = 900 mm.
        At or below 15 m: bracket spacing = 1200 mm.
        """
        layout = self._make_layout()
        high = acp_engine.calculate_subframe(layout, 20.0, 1.0)
        low = acp_engine.calculate_subframe(layout, 10.0, 1.0)
        assert high["brackets"]["bracket_spacing_mm"] == 900.0
        assert low["brackets"]["bracket_spacing_mm"] == 1200.0

    def test_chemical_anchors_2_per_bracket(self, acp_engine):
        """Total chemical anchors must equal total_brackets × 2."""
        layout = self._make_layout()
        result = acp_engine.calculate_subframe(layout, 10.0, 1.0)
        assert result["chemical_anchors"]["total_pcs"] == result["brackets"]["total_pcs"] * 2

    def test_subframe_weight_per_sqm_positive(self, acp_engine):
        """Subframe weight per sqm must be a positive number."""
        layout = self._make_layout()
        result = acp_engine.calculate_subframe(layout, 10.0, 1.0)
        assert result["subframe_kg_per_sqm"] > 0.0

    def test_invalid_layout_raises(self, acp_engine):
        """Layout with zero facade_area_sqm must raise ValueError."""
        bad_layout = {"facade_area_sqm": 0.0, "grid": {}, "panel_types": []}
        with pytest.raises(ValueError):
            acp_engine.calculate_subframe(bad_layout, 10.0, 1.0)


# ===========================================================================
# Class 6: Sealant Quantities
# ===========================================================================

class TestSealantQuantities:
    """Tests for calculate_sealant_quantities."""

    def _simple_layout(self, cols=2, rows=2, panel_w=1500.0, panel_h=1500.0):
        return {
            "facade_area_sqm": (cols * panel_w * rows * panel_h) / 1_000_000.0,
            "grid": {"total_cols": cols, "total_rows": rows},
            "panel_types": [
                {
                    "qty": cols * rows,
                    "net_width_mm": panel_w,
                    "net_height_mm": panel_h,
                    "gross_width_mm": panel_w + 100.0,
                    "gross_height_mm": panel_h + 100.0,
                    "net_area_sqm": (panel_w * panel_h) / 1_000_000.0,
                    "gross_area_sqm": ((panel_w + 100.0) * (panel_h + 100.0)) / 1_000_000.0,
                }
            ],
        }

    def test_total_joint_lm_positive(self, acp_engine):
        """Total joint length must be positive for any valid facade layout."""
        layout = self._simple_layout()
        result = acp_engine.calculate_sealant_quantities(layout)
        assert result["total_joint_lm"] > 0.0

    def test_sealant_cartridges_sufficient(self, acp_engine):
        """
        Sealant cartridges must cover total sealant volume (volume / 0.6L rounded up).
        """
        layout = self._simple_layout()
        result = acp_engine.calculate_sealant_quantities(layout)
        ws = result["weather_silicone"]
        required = math.ceil(ws["volume_litres"] / 0.6)
        assert ws["cartridges_600ml"] == required

    def test_backer_rod_5pct_waste(self, acp_engine):
        """backer_rod length must be total_joint_lm × 1.05 (5% waste)."""
        layout = self._simple_layout()
        result = acp_engine.calculate_sealant_quantities(layout)
        expected = round(result["total_joint_lm"] * 1.05, 2)
        assert abs(result["backer_rod"]["length_lm"] - expected) < 0.1

    def test_perimeter_seal_included(self, acp_engine):
        """perimeter_seal_lm must be included in total_joint_lm."""
        layout = self._simple_layout()
        result = acp_engine.calculate_sealant_quantities(layout)
        assert result["perimeter_seal_lm"] > 0.0
        total_check = (
            result["vertical_joints_lm"]
            + result["horizontal_joints_lm"]
            + result["perimeter_seal_lm"]
        )
        assert abs(result["total_joint_lm"] - total_check) < 0.01

    def test_invalid_layout_raises(self, acp_engine):
        """Layout with zero facade_area_sqm must raise ValueError."""
        with pytest.raises(ValueError):
            acp_engine.calculate_sealant_quantities({"facade_area_sqm": 0.0, "grid": {}})


# ===========================================================================
# Class 7: Material Yield
# ===========================================================================

class TestMaterialYield:
    """Tests for calculate_material_yield.

    The engine uses a conservative 1-panel-per-sheet model by default.
    Raw sheet default = 1220 × 2440 mm.  Gross panel must be SMALLER than
    the raw sheet for yield_pct < 100% and ordered_area >= gross_panel_area.

    We therefore use small panels (net 500 × 1000 mm, gross 600 × 1100 mm)
    so that multiple panels fit on each 1220 × 2440 raw sheet, giving a
    well-defined yield < 100%.
    """

    def _make_layout_for_yield(self, cols=3, rows=4, panel_w=500.0, panel_h=1000.0):
        """
        Small panels (net 500×1000 mm, gross 600×1100 mm with 50 mm fold)
        that comfortably fit 2 per standard 1220×2440 raw sheet.
        """
        gross_w = panel_w + 100.0   # 600 mm
        gross_h = panel_h + 100.0   # 1100 mm
        qty = cols * rows
        return {
            "facade_area_sqm": (cols * panel_w * rows * panel_h) / 1_000_000.0,
            "grid": {"total_cols": cols, "total_rows": rows},
            "panel_types": [
                {
                    "qty": qty,
                    "net_width_mm": panel_w,
                    "net_height_mm": panel_h,
                    "gross_width_mm": gross_w,
                    "gross_height_mm": gross_h,
                    "gross_sheet_height_mm": gross_h,
                    "net_area_sqm": (panel_w * panel_h) / 1_000_000.0,
                    "gross_area_sqm": (gross_w * gross_h) / 1_000_000.0,
                }
            ],
        }

    def test_total_sheets_positive(self, acp_engine):
        """At least 1 sheet must be required for any non-empty layout."""
        layout = self._make_layout_for_yield()
        result = acp_engine.calculate_material_yield(layout, acp_type="PE_4mm")
        assert result["total_sheets_required"] >= 1

    def test_yield_pct_between_0_and_100(self, acp_engine):
        """
        Yield percentage must be ≤ 100% when gross panels fit within raw sheets.
        Gross 600×1100 fits on 1220×2440 sheet (2 panels per sheet),
        so material yield = used_area / sheet_area < 100%.
        """
        layout = self._make_layout_for_yield()
        result = acp_engine.calculate_material_yield(layout, acp_type="PE_4mm")
        assert 0.0 <= result["yield_pct"] <= 100.0

    def test_ordered_area_gte_gross_panel_area(self, acp_engine):
        """
        Ordered sheet area must be >= total gross panel area.
        (You order whole sheets; partial sheets count as full sheets.)
        """
        layout = self._make_layout_for_yield()
        result = acp_engine.calculate_material_yield(layout, acp_type="PE_4mm")
        assert result["ordered_sheet_area_sqm"] >= result["total_gross_panel_area_sqm"]

    def test_scrap_recovery_value_non_negative(self, acp_engine):
        """
        scrap_sqm = ordered_area - gross_panel_area.
        When ordered_area >= gross_panel_area, scrap >= 0 and recovery >= 0.
        """
        layout = self._make_layout_for_yield()
        result = acp_engine.calculate_material_yield(layout, acp_type="A2_4mm")
        assert result["scrap_sqm"] >= 0.0
        assert result["scrap_recovery_value_aed"] >= 0.0

    def test_material_cost_uses_sheet_area(self, acp_engine):
        """material_cost_aed = ordered_sheet_area × price_aed_sqm."""
        layout = self._make_layout_for_yield()
        result = acp_engine.calculate_material_yield(layout, acp_type="PE_4mm")
        expected_cost = round(result["ordered_sheet_area_sqm"] * 55.0, 2)
        assert abs(result["material_cost_aed"] - expected_cost) < 0.5

    def test_invalid_acp_type_raises(self, acp_engine):
        """Unknown acp_type must raise ValueError."""
        layout = self._make_layout_for_yield()
        with pytest.raises(ValueError):
            acp_engine.calculate_material_yield(layout, acp_type="BAD_TYPE")


# ===========================================================================
# Class 8: Dead Load Calculation
# ===========================================================================

class TestDeadLoadCalculation:
    """Tests for calculate_dead_load."""

    def _make_layout_with_panels(self, area_sqm=100.0, total_panels=20):
        return {
            "facade_area_sqm": area_sqm,
            "grid": {"total_panels": total_panels},
            "panel_types": [
                {
                    "qty": total_panels,
                    "net_width_mm": 1500.0,
                    "net_height_mm": round(area_sqm * 1_000_000.0 / (total_panels * 1500.0), 1),
                    "gross_width_mm": 1600.0,
                    "gross_height_mm": 1500.0,
                    "net_area_sqm": area_sqm / total_panels,
                    "gross_area_sqm": 2.4,
                }
            ],
        }

    def test_acp_total_kg_formula(self, acp_engine):
        """
        PE_4mm weighs 5.5 kg/sqm.  100 sqm → total_acp_kg = 550 kg.
        """
        layout = self._make_layout_with_panels()
        result = acp_engine.calculate_dead_load(layout, "PE_4mm", 3.5)
        assert abs(result["acp_total_kg"] - 100.0 * 5.5) < 0.1

    def test_subframe_kg_formula(self, acp_engine):
        """
        subframe_weight_kg_sqm=3.5 × 100 sqm = 350 kg subframe.
        """
        layout = self._make_layout_with_panels()
        result = acp_engine.calculate_dead_load(layout, "PE_4mm", 3.5)
        assert abs(result["subframe_total_kg"] - 100.0 * 3.5) < 0.1

    def test_total_system_kn_correct(self, acp_engine):
        """
        total_system_kg = acp + subframe = 550 + 350 = 900 kg.
        total_dead_load_kN = 900 × 9.81 / 1000 = 8.829 kN.
        """
        layout = self._make_layout_with_panels()
        result = acp_engine.calculate_dead_load(layout, "PE_4mm", 3.5)
        expected_kN = round(900.0 * 9.81 / 1000.0, 3)
        assert abs(result["total_dead_load_kN"] - expected_kN) < 0.01

    def test_load_per_bracket_positive(self, acp_engine):
        """load_per_bracket_kN must be a positive value."""
        layout = self._make_layout_with_panels()
        result = acp_engine.calculate_dead_load(layout, "A2_4mm", 3.5)
        assert result["load_per_bracket_kN"] > 0.0

    def test_surface_load_kpa_formula(self, acp_engine):
        """surface_load_kpa = total_dead_load_kN / facade_area_sqm."""
        layout = self._make_layout_with_panels()
        result = acp_engine.calculate_dead_load(layout, "PE_4mm", 3.5)
        expected_kpa = round(result["total_dead_load_kN"] / 100.0, 3)
        assert abs(result["surface_load_kpa"] - expected_kpa) < 0.001

    def test_standard_key_in_result(self, acp_engine):
        """Result must cite BS EN 1991-1-1 in the standard key."""
        layout = self._make_layout_with_panels()
        result = acp_engine.calculate_dead_load(layout, "PE_4mm")
        assert "BS EN 1991-1-1" in result["standard"]

    def test_invalid_layout_raises(self, acp_engine):
        """facade_area_sqm of 0 must raise ValueError."""
        bad_layout = {"facade_area_sqm": 0.0, "grid": {}}
        with pytest.raises(ValueError):
            acp_engine.calculate_dead_load(bad_layout, "PE_4mm")

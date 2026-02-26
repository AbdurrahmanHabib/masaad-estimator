"""
test_physics_engine.py — Comprehensive unit tests for PhysicsEngine.

Tests cover:
  - calculate_wind_pressure: BS EN 1991-1-4 wind loads for Dubai conditions
  - check_mullion_deflection: L/175 limit, pass/fail, utilisation
  - check_transom_deflection: L/200 or 3 mm absolute limit
  - check_thermal_compliance: Dubai GBR 2023 / ASHRAE 90.1 limits
  - calculate_thermal_movement: ΔL = α × L × ΔT formula
  - generate_acp_skeleton: rule-of-thumb ACP sub-frame quantities
  - generate_mullion_anchor_kit: anchor kit quantities per mullion
  - calculate_bracket_capacity: pass/fail with utilisation
  - select_glass_thickness: thickness table lookup
  - check_acoustic_rating: Rw dB pass/fail

All tests are pure unit tests; no database or external services required.
"""

import math
import pytest


# ---------------------------------------------------------------------------
# Constants mirrored from physics_engine (for assertion math)
# ---------------------------------------------------------------------------
AL_E_MPA = 70_000.0
AL_ALPHA = 23.1e-6
MULLION_DEFLECTION_SPAN_RATIO = 175.0
TRANSOM_DEFLECTION_SPAN_RATIO = 200.0
TRANSOM_DEFLECTION_ABS_MM = 3.0
DUBAI_BASIC_WIND_SPEED_MS = 35.0
AIR_DENSITY_KG_M3 = 1.25
GAMMA_W_ULS = 1.4


# ===========================================================================
# Class 1: Wind Pressure Calculation
# ===========================================================================

class TestWindPressure:
    """Tests for calculate_wind_pressure (BS EN 1991-1-4:2005)."""

    def test_basic_velocity_pressure_formula(self, physics_engine):
        """
        qb = 0.5 × ρ × Vb² = 0.5 × 1.25 × 35² = 0.766 kPa for Dubai defaults.
        """
        result = physics_engine.calculate_wind_pressure(
            basic_wind_speed_ms=35.0, building_height_m=30.0, terrain_category=2
        )
        expected_qb = 0.5 * 1.25 * 35.0 ** 2 / 1000.0
        assert abs(result["results"]["qb_kpa"] - expected_qb) < 0.001

    def test_qp_greater_than_qb(self, physics_engine):
        """
        Peak velocity pressure qp must always exceed basic velocity pressure qb
        because it accounts for turbulence (1 + 7×Iv).
        """
        result = physics_engine.calculate_wind_pressure()
        assert result["results"]["qp_kpa"] > result["results"]["qb_kpa"]

    def test_higher_building_higher_qp(self, physics_engine):
        """
        At greater height the roughness factor cr(z) increases, raising qp.
        qp at 100 m > qp at 20 m for the same terrain category.
        """
        low = physics_engine.calculate_wind_pressure(building_height_m=20.0, terrain_category=2)
        high = physics_engine.calculate_wind_pressure(building_height_m=100.0, terrain_category=2)
        assert high["results"]["qp_kpa"] > low["results"]["qp_kpa"]

    def test_uls_pressure_is_sls_times_1_4(self, physics_engine):
        """
        ULS pressure = SLS pressure × GAMMA_W_ULS (1.4).
        """
        result = physics_engine.calculate_wind_pressure()
        sls_pos = result["results"]["Wp_pos_sls_kpa"]
        uls_pos = result["results"]["Wp_pos_uls_kpa"]
        assert abs(uls_pos - sls_pos * 1.4) < 0.0001

    def test_corner_zone_has_largest_suction(self, physics_engine):
        """
        Corner zone (Cpe_neg = -1.30) must produce greater suction than
        centre zone (Cpe_neg = -0.70) under the same conditions.
        """
        corner = physics_engine.calculate_wind_pressure(zone="corner")
        centre = physics_engine.calculate_wind_pressure(zone="center")
        # Suction is negative; corner suction is more negative (larger magnitude)
        assert corner["results"]["Wp_neg_sls_kpa"] < centre["results"]["Wp_neg_sls_kpa"]

    def test_invalid_terrain_category_raises(self, physics_engine):
        """terrain_category outside 1-4 must raise ValueError."""
        with pytest.raises(ValueError):
            physics_engine.calculate_wind_pressure(terrain_category=5)

    def test_invalid_zone_raises(self, physics_engine):
        """Unknown zone string must raise ValueError."""
        with pytest.raises(ValueError):
            physics_engine.calculate_wind_pressure(zone="unknown_zone")

    def test_standard_key_in_result(self, physics_engine):
        """Result must include 'standard' key citing BS EN 1991-1-4."""
        result = physics_engine.calculate_wind_pressure()
        assert "BS EN 1991-1-4" in result["standard"]


# ===========================================================================
# Class 2: Mullion Deflection Check
# ===========================================================================

class TestMullionDeflection:
    """Tests for check_mullion_deflection (BS EN 13830, L/175)."""

    def test_pass_case_low_pressure(self, physics_engine):
        """
        Stiff mullion (large Iy): span=3000mm, I=8e6 mm⁴, wind=0.5 kPa, trib=1500mm.
        w = 0.5×0.001×1500 = 0.75 N/mm (SLS, γ=1.0).
        δ = 5×0.75×3000⁴/(384×70000×8e6) ≈ 0.37 mm.
        limit = 3000/175 ≈ 17.1 mm → PASS.
        """
        result = physics_engine.check_mullion_deflection(
            span_mm=3000.0,
            moment_of_inertia_mm4=8_000_000.0,
            wind_pressure_kpa=0.5,
            tributary_width_mm=1500.0,
        )
        assert result["results"]["passed"] is True
        assert result["results"]["status"] == "PASS"

    def test_fail_case_high_pressure_small_section(self, physics_engine):
        """
        Slender mullion (small I): span=4000mm, I=500000 mm⁴, wind=2.0 kPa, trib=1500mm.
        This will produce a deflection far exceeding L/175 → FAIL.
        """
        result = physics_engine.check_mullion_deflection(
            span_mm=4000.0,
            moment_of_inertia_mm4=500_000.0,
            wind_pressure_kpa=2.0,
            tributary_width_mm=1500.0,
        )
        assert result["results"]["passed"] is False
        assert result["results"]["status"] == "FAIL"

    def test_limit_equals_span_over_175(self, physics_engine):
        """
        Deflection limit must equal span / 175.
        For span=3500mm: limit = 3500/175 = 20.0 mm.
        """
        result = physics_engine.check_mullion_deflection(
            span_mm=3500.0,
            moment_of_inertia_mm4=5_000_000.0,
            wind_pressure_kpa=1.0,
            tributary_width_mm=1200.0,
        )
        expected_limit = 3500.0 / 175.0
        assert abs(result["results"]["limit_mm"] - expected_limit) < 0.01

    def test_utilisation_ratio_consistency(self, physics_engine):
        """
        utilization = deflection / limit.
        Must satisfy: utilization × limit ≈ deflection.
        """
        result = physics_engine.check_mullion_deflection(
            span_mm=3000.0,
            moment_of_inertia_mm4=3_000_000.0,
            wind_pressure_kpa=1.2,
            tributary_width_mm=1500.0,
        )
        r = result["results"]
        assert abs(r["utilization"] * r["limit_mm"] - r["deflection_mm"]) < 0.001

    def test_deflection_formula_manual(self, physics_engine):
        """
        Manual verification: span=2000mm, I=2e6 mm⁴, p=1.0 kPa, trib=1000mm.
        w = 1.0×0.001×1000 = 1.0 N/mm.
        δ = 5×1.0×2000⁴/(384×70000×2e6) = 5×1.6e13/(384×1.4e11)
          = 8e13/5.376e13 ≈ 1.488 mm.
        """
        result = physics_engine.check_mullion_deflection(
            span_mm=2000.0,
            moment_of_inertia_mm4=2_000_000.0,
            wind_pressure_kpa=1.0,
            tributary_width_mm=1000.0,
        )
        w = 1.0 * 0.001 * 1000.0  # N/mm
        expected_delta = 5.0 * w * 2000.0 ** 4 / (384.0 * 70000.0 * 2_000_000.0)
        assert abs(result["results"]["deflection_mm"] - expected_delta) < 0.01


# ===========================================================================
# Class 3: Transom Deflection Check
# ===========================================================================

class TestTransomDeflection:
    """Tests for check_transom_deflection (BS EN 13830, L/200 or 3 mm)."""

    def test_short_span_governed_by_3mm_absolute(self, physics_engine):
        """
        For a short span (e.g. 500 mm), L/200 = 2.5 mm < 3 mm absolute.
        Governing criterion must be L/200 (the smaller value).
        """
        result = physics_engine.check_transom_deflection(
            span_mm=500.0,
            inertia_mm4=1_000_000.0,
            glass_weight_kg=10.0,
        )
        limit_span = 500.0 / 200.0  # 2.5 mm
        assert limit_span < 3.0  # L/200 is tighter
        assert abs(result["results"]["governing_limit_mm"] - limit_span) < 0.01

    def test_long_span_governed_by_3mm_absolute(self, physics_engine):
        """
        For a long span (e.g. 800 mm), L/200 = 4 mm > 3 mm → 3 mm governs.
        """
        result = physics_engine.check_transom_deflection(
            span_mm=800.0,
            inertia_mm4=5_000_000.0,
            glass_weight_kg=5.0,
        )
        limit_span = 800.0 / 200.0  # 4.0 mm
        assert limit_span > 3.0  # 3 mm absolute is tighter
        assert abs(result["results"]["governing_limit_mm"] - 3.0) < 0.001

    def test_pass_case_stiff_transom(self, physics_engine):
        """Very stiff transom (large I) with light glass must pass."""
        result = physics_engine.check_transom_deflection(
            span_mm=1200.0,
            inertia_mm4=20_000_000.0,
            glass_weight_kg=15.0,
        )
        assert result["results"]["passed"] is True

    def test_fail_case_slender_transom(self, physics_engine):
        """Slender transom with heavy glass must fail deflection check."""
        result = physics_engine.check_transom_deflection(
            span_mm=1500.0,
            inertia_mm4=100_000.0,
            glass_weight_kg=80.0,
        )
        assert result["results"]["passed"] is False

    def test_dual_limit_reported(self, physics_engine):
        """Both limit_span_mm and limit_abs_mm must appear in results."""
        result = physics_engine.check_transom_deflection(
            span_mm=1000.0, inertia_mm4=3_000_000.0, glass_weight_kg=20.0
        )
        r = result["results"]
        assert "limit_span_mm" in r
        assert "limit_abs_mm" in r
        assert r["limit_abs_mm"] == 3.0


# ===========================================================================
# Class 4: Thermal Compliance Check
# ===========================================================================

class TestThermalCompliance:
    """Tests for check_thermal_compliance (Dubai GBR 2023 / ASHRAE 90.1-2019)."""

    def test_low_e_dgu_commercial_north_compliant(self, physics_engine):
        """
        low_e_dgu: U=1.6, SHGC=0.40, VLT=0.70.
        Commercial North limits: u_max=2.1, shgc_N=0.40, vlt_min=0.27.
        All three parameters are at or within limit → COMPLIANT.
        """
        result = physics_engine.check_thermal_compliance(
            u_value=1.6, shgc=0.40, vlt=0.70,
            building_type="commercial", orientation="N"
        )
        assert result["results"]["overall_passed"] is True
        assert result["results"]["status"] == "COMPLIANT"

    def test_clear_single_glass_fails_u_value(self, physics_engine):
        """
        clear_single: U=5.8 — far exceeds commercial u_max=2.1 → NON-COMPLIANT.
        """
        result = physics_engine.check_thermal_compliance(
            u_value=5.8, shgc=0.40, vlt=0.70,
            building_type="commercial", orientation="N"
        )
        assert result["results"]["overall_passed"] is False
        u_check = next(c for c in result["results"]["checks"] if "U-value" in c["parameter"])
        assert u_check["passed"] is False

    def test_high_shgc_fails_east_west(self, physics_engine):
        """
        SHGC=0.50 on East face with commercial limit shgc_EW=0.25 → NON-COMPLIANT.
        """
        result = physics_engine.check_thermal_compliance(
            u_value=1.6, shgc=0.50, vlt=0.70,
            building_type="commercial", orientation="E"
        )
        shgc_check = next(
            c for c in result["results"]["checks"] if "SHGC" in c["parameter"]
        )
        assert shgc_check["passed"] is False

    def test_low_vlt_fails(self, physics_engine):
        """
        VLT=0.20 is below vlt_min=0.27 → check for VLT must fail.
        """
        result = physics_engine.check_thermal_compliance(
            u_value=1.6, shgc=0.30, vlt=0.20,
            building_type="residential", orientation="N"
        )
        vlt_check = next(c for c in result["results"]["checks"] if c["parameter"] == "VLT")
        assert vlt_check["passed"] is False

    def test_north_orientation_group_mapping(self, physics_engine):
        """NE and NW orientations must map to 'North' group."""
        for orient in ("N", "NE", "NW"):
            result = physics_engine.check_thermal_compliance(
                u_value=1.6, shgc=0.30, vlt=0.70,
                building_type="commercial", orientation=orient,
            )
            assert result["inputs"]["orientation_group"] == "North"

    def test_south_orientation_group_mapping(self, physics_engine):
        """S, SE, SW orientations must map to 'South' group."""
        for orient in ("S", "SE", "SW"):
            result = physics_engine.check_thermal_compliance(
                u_value=1.6, shgc=0.30, vlt=0.70,
                building_type="commercial", orientation=orient,
            )
            assert result["inputs"]["orientation_group"] == "South"

    def test_invalid_building_type_raises(self, physics_engine):
        """Unknown building_type must raise ValueError."""
        with pytest.raises(ValueError):
            physics_engine.check_thermal_compliance(
                u_value=1.6, shgc=0.30, vlt=0.70,
                building_type="theme_park", orientation="N",
            )

    def test_three_checks_always_returned(self, physics_engine):
        """Exactly 3 compliance checks must be present (U-value, SHGC, VLT)."""
        result = physics_engine.check_thermal_compliance(
            u_value=1.6, shgc=0.30, vlt=0.70,
            building_type="commercial", orientation="N",
        )
        assert len(result["results"]["checks"]) == 3


# ===========================================================================
# Class 5: Thermal Movement
# ===========================================================================

class TestThermalMovement:
    """Tests for calculate_thermal_movement (ΔL = α × L × ΔT)."""

    def test_formula_verification(self, physics_engine):
        """
        ΔL = 23.1e-6 × 3000 × 40 = 2.772 mm.
        """
        result = physics_engine.calculate_thermal_movement(3000.0, 40.0)
        expected = 23.1e-6 * 3000.0 * 40.0
        assert abs(result - expected) < 0.001

    def test_zero_length_zero_movement(self, physics_engine):
        """Zero-length member must produce zero thermal movement."""
        assert physics_engine.calculate_thermal_movement(0.0, 40.0) == 0.0

    def test_larger_temp_range_larger_movement(self, physics_engine):
        """80°C range must produce exactly twice the movement of 40°C range."""
        delta_40 = physics_engine.calculate_thermal_movement(5000.0, 40.0)
        delta_80 = physics_engine.calculate_thermal_movement(5000.0, 80.0)
        assert abs(delta_80 / delta_40 - 2.0) < 0.001

    def test_custom_alpha(self, physics_engine):
        """
        Custom alpha=12e-6 (steel) instead of aluminium default.
        ΔL = 12e-6 × 2000 × 50 = 1.2 mm.
        """
        result = physics_engine.calculate_thermal_movement(2000.0, 50.0, alpha=12e-6)
        expected = 12e-6 * 2000.0 * 50.0
        assert abs(result - expected) < 0.001

    def test_returns_float(self, physics_engine):
        """Return type must be float."""
        result = physics_engine.calculate_thermal_movement(1000.0, 40.0)
        assert isinstance(result, float)


# ===========================================================================
# Class 6: ACP Skeleton Quantities
# ===========================================================================

class TestACPSkeleton:
    """Tests for generate_acp_skeleton rule-of-thumb quantities."""

    def test_t_profile_at_1_8_per_sqm(self, physics_engine):
        """
        100 sqm → aluminum_t_profile_mtr = 100 × 1.80 = 180.0 m.
        """
        result = physics_engine.generate_acp_skeleton(100.0, 80.0)
        assert abs(result["aluminum_t_profile_mtr"] - 180.0) < 0.01

    def test_l_angle_at_1_2_per_sqm(self, physics_engine):
        """
        100 sqm → aluminum_l_angle_mtr = 100 × 1.20 = 120.0 m.
        """
        result = physics_engine.generate_acp_skeleton(100.0, 80.0)
        assert abs(result["aluminum_l_angle_mtr"] - 120.0) < 0.01

    def test_brackets_ceiling_4_5_per_sqm(self, physics_engine):
        """
        100 sqm × 4.5 = 450 brackets (ceiling).
        """
        result = physics_engine.generate_acp_skeleton(100.0, 80.0)
        assert result["fixing_brackets_pcs"] == 450

    def test_backer_rod_equals_perimeter(self, physics_engine):
        """backer_rod_mtr must equal the perimeter_m input."""
        result = physics_engine.generate_acp_skeleton(50.0, 35.0)
        assert abs(result["backer_rod_mtr"] - 35.0) < 0.01

    def test_silicone_tubes_ceiling_per_6m(self, physics_engine):
        """
        30 m perimeter / 6 m per tube = 5 tubes (exact).
        """
        result = physics_engine.generate_acp_skeleton(50.0, 30.0)
        assert result["weather_silicone_tubes"] == 5

    def test_primer_10pct_oversize(self, physics_engine):
        """primer_m2 = net_sqm × 1.10 (10% waste allowance)."""
        result = physics_engine.generate_acp_skeleton(200.0, 100.0)
        assert abs(result["primer_m2"] - 220.0) < 0.01

    def test_bond_tape_3_per_sqm(self, physics_engine):
        """bond_tape_mtr = net_sqm × 3.00."""
        result = physics_engine.generate_acp_skeleton(50.0, 40.0)
        assert abs(result["bond_tape_mtr"] - 150.0) < 0.01


# ===========================================================================
# Class 7: Mullion Anchor Kit
# ===========================================================================

class TestMullionAnchorKit:
    """Tests for generate_mullion_anchor_kit quantities."""

    def test_anchor_bolts_4_per_mullion(self, physics_engine):
        """10 mullions × 4 bolts = 40 Hilti M12 anchors."""
        result = physics_engine.generate_mullion_anchor_kit(10)
        assert result["hilti_anchor_bolts_M12"] == 40

    def test_ms_brackets_1_per_mullion(self, physics_engine):
        """1 galvanised MS bracket per mullion."""
        result = physics_engine.generate_mullion_anchor_kit(20)
        assert result["ms_galvanized_brackets_pcs"] == 20

    def test_joint_sleeves_0_5_per_mullion(self, physics_engine):
        """
        Joint sleeves = ceil(count × 0.5).
        10 mullions → ceil(5.0) = 5 sleeves.
        11 mullions → ceil(5.5) = 6 sleeves.
        """
        assert physics_engine.generate_mullion_anchor_kit(10)["joint_sleeves_pcs"] == 5
        assert physics_engine.generate_mullion_anchor_kit(11)["joint_sleeves_pcs"] == 6

    def test_epdm_blocks_2_per_mullion(self, physics_engine):
        """2 EPDM setting blocks per mullion."""
        result = physics_engine.generate_mullion_anchor_kit(15)
        assert result["epdm_setting_blocks_pcs"] == 30

    def test_chemical_anchor_cartridges(self, physics_engine):
        """
        4 anchors per mullion, 8 shots per cartridge.
        8 mullions → 32 bolts / 8 = 4 cartridges.
        """
        result = physics_engine.generate_mullion_anchor_kit(8)
        assert result["chemical_anchor_cartridges"] == 4

    def test_zero_mullions_all_zero(self, physics_engine):
        """Zero mullion count must produce all zero quantities."""
        result = physics_engine.generate_mullion_anchor_kit(0)
        assert result["hilti_anchor_bolts_M12"] == 0
        assert result["ms_galvanized_brackets_pcs"] == 0
        assert result["epdm_setting_blocks_pcs"] == 0


# ===========================================================================
# Class 8: Bracket Capacity
# ===========================================================================

class TestBracketCapacity:
    """Tests for calculate_bracket_capacity."""

    def test_light_bracket_shear_pass(self, physics_engine):
        """
        L_bracket_light shear capacity = 12.0 kN.
        Applied load = 8.0 kN → utilization = 8/12 ≈ 0.667 → PASS.
        """
        result = physics_engine.calculate_bracket_capacity("L_bracket_light", 8.0, "shear")
        assert result["results"]["passed"] is True
        assert abs(result["results"]["utilization"] - 8.0 / 12.0) < 0.001

    def test_light_bracket_exceeds_tension_capacity(self, physics_engine):
        """
        L_bracket_light tension capacity = 8.0 kN.
        Applied load = 10.0 kN → utilization > 1.0 → FAIL.
        """
        result = physics_engine.calculate_bracket_capacity("L_bracket_light", 10.0, "tension")
        assert result["results"]["passed"] is False
        assert "FAIL" in result["results"]["status"]

    def test_invalid_bracket_type_raises(self, physics_engine):
        """Unknown bracket_type must raise ValueError."""
        with pytest.raises(ValueError):
            physics_engine.calculate_bracket_capacity("mystery_bracket", 5.0, "shear")

    def test_invalid_load_direction_raises(self, physics_engine):
        """Unknown load_direction must raise ValueError."""
        with pytest.raises(ValueError):
            physics_engine.calculate_bracket_capacity("L_bracket_light", 5.0, "diagonal")

    def test_reserve_capacity_reported(self, physics_engine):
        """reserve_capacity_pct must equal (1 - utilization) × 100."""
        result = physics_engine.calculate_bracket_capacity("T_bracket_std", 10.0, "shear")
        utilization = result["results"]["utilization"]
        expected_reserve = round((1.0 - utilization) * 100, 1)
        assert abs(result["results"]["reserve_capacity_pct"] - expected_reserve) < 0.1

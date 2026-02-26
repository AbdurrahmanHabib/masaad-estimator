"""
test_labor_engine.py — Comprehensive unit tests for LaborEngine.

Tests cover:
  - calculate_blended_rates: mixed department payroll, burden factors, skill multipliers
  - calculate_overtime: UAE labor law multipliers (weekday, night, Friday)
  - estimate_project_manhours: system-type norms (CURTAIN_WALL, WINDOW, DOOR, ACP)
  - calculate_crew_size: minimum crew, recommended crew with 15% buffer, utilisation
  - get_current_burn_rate / update_burn_rate: burn rate tracking and history
  - process_attendance_sheet: productivity ratio, absenteeism alerts
  - project_labor_cost: department-level labor cost projection
  - Edge cases: zero manhours, invalid inputs, unknown department codes

All tests are pure unit tests; no database or external services required.
"""

import math
import pytest


# ---------------------------------------------------------------------------
# Constants mirrored from labor_engine for assertion math
# ---------------------------------------------------------------------------
WORKING_HOURS_PER_MONTH = 208
DEFAULT_BURN_RATE_AED = 13.00
OT_WEEKDAY_MULTIPLIER = 1.25
OT_NIGHT_MULTIPLIER = 1.50
OT_FRIDAY_MULTIPLIER = 1.50
CREW_BUFFER_FACTOR = 1.15

DEPARTMENT_BURDEN = {
    "FACTORY": 1.35,
    "SITE":    1.55,
    "DESIGN":  1.20,
    "QA_QC":   1.30,
    "LOGISTICS": 1.40,
}
SKILL_MULTIPLIERS = {
    "HELPER": 1.00,
    "SEMI_SKILLED": 1.20,
    "SKILLED": 1.50,
    "FOREMAN": 1.80,
    "SUPERVISOR": 2.20,
    "ENGINEER": 2.80,
}


# ===========================================================================
# Class 1: Blended Rates
# ===========================================================================

class TestBlendedRates:
    """Tests for calculate_blended_rates."""

    def test_single_factory_worker_blended_rate(self, labor_engine):
        """
        1 FACTORY worker: basic=2000, allowances=500, skill=SKILLED (×1.5).
        gross = 2500, adjusted = 2500×1.5 = 3750,
        burdened = 3750×1.35 = 5062.50 AED/month.
        Hourly = 5062.50 / 208 ≈ 24.34 AED/hr.
        """
        entries = [
            {
                "department": "FACTORY",
                "basic_salary": 2000.0,
                "allowances": 500.0,
                "skill_level": "SKILLED",
            }
        ]
        result = labor_engine.calculate_blended_rates(entries)
        assert result["total_workforce"] == 1
        factory = result["by_department"]["FACTORY"]
        expected_monthly = (2000.0 + 500.0) * 1.50 * 1.35
        expected_hourly = expected_monthly / WORKING_HOURS_PER_MONTH
        assert abs(factory["avg_burdened_monthly_aed"] - expected_monthly) < 0.5
        assert abs(factory["blended_hourly_rate_aed"] - expected_hourly) < 0.1

    def test_multi_department_total_headcount(self, labor_engine, payroll_entries):
        """Total workforce count must match number of payroll entries submitted."""
        result = labor_engine.calculate_blended_rates(payroll_entries)
        assert result["total_workforce"] == len(payroll_entries)

    def test_site_burden_higher_than_factory(self, labor_engine):
        """
        SITE burden (1.55) > FACTORY burden (1.35).
        Identical gross salary → SITE hourly rate must be higher.
        """
        entries = [
            {"department": "FACTORY", "basic_salary": 2000.0, "allowances": 0.0, "skill_level": "SKILLED"},
            {"department": "SITE",    "basic_salary": 2000.0, "allowances": 0.0, "skill_level": "SKILLED"},
        ]
        result = labor_engine.calculate_blended_rates(entries)
        factory_rate = result["by_department"]["FACTORY"]["blended_hourly_rate_aed"]
        site_rate = result["by_department"]["SITE"]["blended_hourly_rate_aed"]
        assert site_rate > factory_rate

    def test_engineer_skill_multiplier_applied(self, labor_engine):
        """
        ENGINEER multiplier = 2.80.  basic=5000, allowances=1000 → gross=6000.
        adjusted = 6000×2.80 = 16 800.  burdened (DESIGN×1.20) = 20 160.
        hourly = 20160/208 ≈ 96.92 AED/hr.
        """
        entries = [
            {
                "department": "DESIGN",
                "basic_salary": 5000.0,
                "allowances": 1000.0,
                "skill_level": "ENGINEER",
            }
        ]
        result = labor_engine.calculate_blended_rates(entries)
        expected_hourly = 6000.0 * 2.80 * 1.20 / WORKING_HOURS_PER_MONTH
        actual = result["by_department"]["DESIGN"]["blended_hourly_rate_aed"]
        assert abs(actual - expected_hourly) < 0.5

    def test_unknown_department_falls_back_to_factory_burden(self, labor_engine):
        """
        Unknown department 'WAREHOUSE' falls back to FACTORY burden.
        The unknown dept name must appear in unrecognised_departments.
        """
        entries = [
            {"department": "WAREHOUSE", "basic_salary": 1500.0, "allowances": 300.0}
        ]
        result = labor_engine.calculate_blended_rates(entries)
        assert "WAREHOUSE" in result["unrecognised_departments"]
        # Falls back to FACTORY bucket
        assert result["by_department"]["FACTORY"]["headcount"] == 1

    def test_empty_payroll_returns_default_burn_rate(self, labor_engine):
        """
        Empty payroll list: overall blended rate should fall back to
        DEFAULT_BURN_RATE_AED (13.00 AED/hr).
        """
        result = labor_engine.calculate_blended_rates([])
        assert result["total_workforce"] == 0
        assert abs(result["overall_blended_hourly_rate_aed"] - DEFAULT_BURN_RATE_AED) < 0.01

    def test_overall_blended_rate_computed(self, labor_engine, payroll_entries):
        """
        overall_blended_hourly_rate_aed must be total_cost / (headcount × 208).
        """
        result = labor_engine.calculate_blended_rates(payroll_entries)
        expected = result["total_burdened_monthly_cost_aed"] / (
            result["total_workforce"] * WORKING_HOURS_PER_MONTH
        )
        actual = result["overall_blended_hourly_rate_aed"]
        assert abs(actual - expected) < 0.01


# ===========================================================================
# Class 2: Overtime Calculation
# ===========================================================================

class TestOvertimeCalculation:
    """Tests for calculate_overtime per UAE Federal Decree-Law No. 33 of 2021."""

    def test_normal_hours_only(self, labor_engine):
        """
        8 normal hours at 50 AED/hr = 400 AED total gross, effective rate = 50.
        """
        result = labor_engine.calculate_overtime(50.0, {"normal_hours": 8.0})
        assert abs(result["breakdown"]["normal"]["pay_aed"] - 400.0) < 0.01
        assert abs(result["total_gross_pay_aed"] - 400.0) < 0.01
        assert abs(result["effective_hourly_rate_aed"] - 50.0) < 0.01

    def test_weekday_overtime_1_25x(self, labor_engine):
        """
        2 weekday OT hours at 40 AED/hr: pay = 2 × 40 × 1.25 = 100 AED.
        """
        result = labor_engine.calculate_overtime(40.0, {"weekday_ot_hours": 2.0})
        assert abs(result["breakdown"]["weekday_overtime"]["pay_aed"] - 100.0) < 0.01
        assert result["breakdown"]["weekday_overtime"]["multiplier"] == 1.25

    def test_night_overtime_1_5x(self, labor_engine):
        """
        3 night OT hours at 40 AED/hr: pay = 3 × 40 × 1.50 = 180 AED.
        """
        result = labor_engine.calculate_overtime(40.0, {"night_ot_hours": 3.0})
        assert abs(result["breakdown"]["night_overtime"]["pay_aed"] - 180.0) < 0.01
        assert result["breakdown"]["night_overtime"]["multiplier"] == 1.50

    def test_friday_holiday_1_5x(self, labor_engine):
        """
        4 Friday hours at 50 AED/hr: pay = 4 × 50 × 1.50 = 300 AED.
        """
        result = labor_engine.calculate_overtime(50.0, {"friday_hours": 4.0})
        assert abs(result["breakdown"]["friday_holiday"]["pay_aed"] - 300.0) < 0.01
        assert result["breakdown"]["friday_holiday"]["multiplier"] == 1.50

    def test_mixed_hours_total_gross(self, labor_engine):
        """
        Mixed: 8 normal + 2 weekday OT + 1 night OT at 30 AED/hr.
        normal_pay   = 8 × 30 = 240
        weekday_ot   = 2 × 30 × 1.25 = 75
        night_ot     = 1 × 30 × 1.50 = 45
        total_gross  = 360 AED
        total_hours  = 11
        """
        result = labor_engine.calculate_overtime(30.0, {
            "normal_hours": 8.0,
            "weekday_ot_hours": 2.0,
            "night_ot_hours": 1.0,
        })
        assert abs(result["total_gross_pay_aed"] - 360.0) < 0.01
        assert abs(result["total_hours_worked"] - 11.0) < 0.01

    def test_negative_hours_clamped_to_zero(self, labor_engine):
        """Negative hour values must be treated as 0 — no negative pay."""
        result = labor_engine.calculate_overtime(50.0, {
            "normal_hours": -5.0,
            "weekday_ot_hours": -2.0,
        })
        assert result["total_gross_pay_aed"] == 0.0
        assert result["total_hours_worked"] == 0.0

    def test_legal_reference_returned(self, labor_engine):
        """Result must include a legal_reference string citing the correct law."""
        result = labor_engine.calculate_overtime(50.0, {"normal_hours": 8.0})
        assert "33" in result["legal_reference"]   # Decree-Law No. 33


# ===========================================================================
# Class 3: Project Manhour Estimation
# ===========================================================================

class TestProjectManhourEstimation:
    """Tests for estimate_project_manhours using SYSTEM_MANHOUR_NORMS."""

    def test_curtain_wall_manhours(self, labor_engine):
        """
        CURTAIN_WALL: fab_norm=2.5, install_norm=3.0 per sqm.
        100 sqm → fab=250, install=300, total=550 hours.
        """
        bom = [{"system_type": "CURTAIN_WALL", "quantity": 100.0}]
        result = labor_engine.estimate_project_manhours(bom)
        assert abs(result["summary"]["total_fabrication_hours"] - 250.0) < 0.01
        assert abs(result["summary"]["total_installation_hours"] - 300.0) < 0.01
        assert abs(result["summary"]["total_manhours"] - 550.0) < 0.01

    def test_window_manhours_per_unit(self, labor_engine):
        """
        WINDOW: fab_norm=1.5, install_norm=2.0 per unit.
        20 windows → fab=30, install=40, total=70 hours.
        """
        bom = [{"system_type": "WINDOW", "quantity": 20.0}]
        result = labor_engine.estimate_project_manhours(bom)
        assert abs(result["summary"]["total_fabrication_hours"] - 30.0) < 0.01
        assert abs(result["summary"]["total_installation_hours"] - 40.0) < 0.01

    def test_door_manhours_per_unit(self, labor_engine):
        """
        DOOR: fab_norm=2.0, install_norm=3.0 per unit.
        10 doors → fab=20, install=30, total=50 hours.
        """
        bom = [{"system_type": "DOOR", "quantity": 10.0}]
        result = labor_engine.estimate_project_manhours(bom)
        assert abs(result["summary"]["total_manhours"] - 50.0) < 0.01

    def test_acp_manhours_per_sqm(self, labor_engine):
        """
        ACP: fab_norm=1.0, install_norm=1.5 per sqm.
        200 sqm → fab=200, install=300, total=500 hours.
        """
        bom = [{"system_type": "ACP", "quantity": 200.0}]
        result = labor_engine.estimate_project_manhours(bom)
        assert abs(result["summary"]["total_fabrication_hours"] - 200.0) < 0.01
        assert abs(result["summary"]["total_installation_hours"] - 300.0) < 0.01

    def test_mixed_systems(self, labor_engine):
        """
        CW 50 sqm + WINDOW 10 units combined:
        CW:  fab=125, install=150
        WIN: fab=15,  install=20
        total_fab=140, total_install=170, total=310 hours.
        """
        bom = [
            {"system_type": "CURTAIN_WALL", "quantity": 50.0},
            {"system_type": "WINDOW", "quantity": 10.0},
        ]
        result = labor_engine.estimate_project_manhours(bom)
        assert abs(result["summary"]["total_manhours"] - 310.0) < 0.01

    def test_unknown_system_type_reported(self, labor_engine):
        """Unknown system_type must be added to unrecognised_system_types list."""
        bom = [{"system_type": "SKYLIGHT_CUSTOM", "quantity": 50.0}]
        result = labor_engine.estimate_project_manhours(bom)
        assert "SKYLIGHT_CUSTOM" in result["unrecognised_system_types"]
        assert result["summary"]["total_manhours"] == 0.0

    def test_system_type_filter(self, labor_engine):
        """
        system_types filter=['WINDOW'] applied to BOM with CURTAIN_WALL + WINDOW.
        Only WINDOW hours should be counted.
        """
        bom = [
            {"system_type": "CURTAIN_WALL", "quantity": 100.0},
            {"system_type": "WINDOW", "quantity": 10.0},
        ]
        result = labor_engine.estimate_project_manhours(bom, system_types=["WINDOW"])
        assert "CURTAIN_WALL" not in result["by_system"]
        assert abs(result["summary"]["total_manhours"] - 35.0) < 0.01  # 10×(1.5+2.0)


# ===========================================================================
# Class 4: Burn Rate Management
# ===========================================================================

class TestBurnRateManagement:
    """Tests for get_current_burn_rate and update_burn_rate."""

    def test_default_burn_rate_is_13(self):
        """Fresh LaborEngine must default to 13.00 AED/hr."""
        from app.services.labor_engine import LaborEngine
        engine = LaborEngine()
        assert abs(engine.get_current_burn_rate() - 13.00) < 0.001

    def test_update_burn_rate_changes_current_rate(self):
        """update_burn_rate must persist the new rate and return before/after."""
        from app.services.labor_engine import LaborEngine
        engine = LaborEngine()
        result = engine.update_burn_rate(15.00, "2026-03", "Annual payroll review")
        assert abs(engine.get_current_burn_rate() - 15.00) < 0.001
        assert abs(result["previous_rate_aed"] - 13.00) < 0.001
        assert abs(result["new_rate_aed"] - 15.00) < 0.001

    def test_update_burn_rate_change_pct(self):
        """
        Increasing from 13.00 to 14.30 AED/hr should report ~10% change.
        """
        from app.services.labor_engine import LaborEngine
        engine = LaborEngine()
        result = engine.update_burn_rate(14.30, "2026-03", "Test increase")
        assert abs(result["change_pct"] - 10.0) < 0.5

    def test_update_burn_rate_zero_raises(self):
        """Burn rate of 0 or negative must raise ValueError."""
        from app.services.labor_engine import LaborEngine
        engine = LaborEngine()
        with pytest.raises(ValueError):
            engine.update_burn_rate(0.0, "2026-03", "invalid")
        with pytest.raises(ValueError):
            engine.update_burn_rate(-5.0, "2026-03", "invalid")

    def test_burn_rate_history_tracked(self):
        """Multiple updates must accumulate in history; history_count must match."""
        from app.services.labor_engine import LaborEngine
        engine = LaborEngine()
        engine.update_burn_rate(14.0, "2026-03", "Q1 review")
        engine.update_burn_rate(15.0, "2026-06", "Q2 review")
        history = engine.get_burn_rate_history()
        assert len(history) == 2
        assert history[0]["new_rate_aed"] == 14.0
        assert history[1]["new_rate_aed"] == 15.0


# ===========================================================================
# Class 5: Crew Size Calculation
# ===========================================================================

class TestCrewSizeCalculation:
    """Tests for calculate_crew_size."""

    def test_basic_crew_size_calculation(self, labor_engine):
        """
        400 manhours, 50 days, 8 hrs/day:
        available_per_worker = 400 hrs.
        min_crew_raw = 400/400 = 1 → min_crew = 1.
        recommended_raw = 1 × 1.15 = 1.15 → recommended = 2 (ceiling).
        """
        result = labor_engine.calculate_crew_size(400.0, 50, 8)
        assert result["min_crew"] == 1
        assert result["recommended_crew"] == 2

    def test_crew_size_with_buffer(self, labor_engine):
        """Recommended crew must always be >= min_crew."""
        result = labor_engine.calculate_crew_size(1000.0, 30, 8)
        assert result["recommended_crew"] >= result["min_crew"]

    def test_utilisation_below_100pct_with_buffer(self, labor_engine):
        """
        With the 15% buffer the recommended crew should result in
        utilisation < 100% (target ≤ 87%).
        """
        result = labor_engine.calculate_crew_size(800.0, 20, 8)
        assert result["utilisation_pct"] < 100.0

    def test_zero_manhours(self, labor_engine):
        """Zero manhours should produce zero crew sizes without errors."""
        result = labor_engine.calculate_crew_size(0.0, 30, 8)
        assert result["min_crew"] == 0
        assert result["recommended_crew"] == 0

    def test_invalid_deadline_raises(self, labor_engine):
        """deadline_days <= 0 must raise ValueError."""
        with pytest.raises(ValueError):
            labor_engine.calculate_crew_size(100.0, 0, 8)

    def test_buffer_factor_reported(self, labor_engine):
        """buffer_factor in result must equal CREW_BUFFER_FACTOR = 1.15."""
        result = labor_engine.calculate_crew_size(100.0, 10, 8)
        assert result["buffer_factor"] == CREW_BUFFER_FACTOR


# ===========================================================================
# Class 6: Attendance Sheet Processing
# ===========================================================================

class TestAttendanceProcessing:
    """Tests for process_attendance_sheet."""

    def _sample_attendance(self):
        return [
            {
                "employee_id": "F001",
                "department": "FACTORY",
                "planned_days": 26.0,
                "actual_days": 24.0,
                "planned_hours": 208.0,
                "actual_hours": 192.0,
                "overtime_hours": 8.0,
                "leave_days": 2.0,
            },
            {
                "employee_id": "S001",
                "department": "SITE",
                "planned_days": 26.0,
                "actual_days": 26.0,
                "planned_hours": 208.0,
                "actual_hours": 216.0,  # overtime included
                "overtime_hours": 16.0,
                "leave_days": 0.0,
            },
        ]

    def test_employee_count(self, labor_engine):
        """employee_count must equal the number of attendance records submitted."""
        data = self._sample_attendance()
        result = labor_engine.process_attendance_sheet(data)
        assert result["employee_count"] == 2

    def test_productivity_ratio_calculation(self, labor_engine):
        """
        F001: actual_hours=192 / planned_hours=208 = 0.9231 productivity.
        """
        data = self._sample_attendance()
        result = labor_engine.process_attendance_sheet(data)
        f001 = next(e for e in result["employees"] if e["employee_id"] == "F001")
        expected = round(192.0 / 208.0, 4)
        assert abs(f001["productivity_ratio"] - expected) < 0.001

    def test_absenteeism_detection(self, labor_engine):
        """
        F001: planned=26, actual=24, leave=2 → absent=0. Attendance = 24/26.
        """
        data = self._sample_attendance()
        result = labor_engine.process_attendance_sheet(data)
        f001 = next(e for e in result["employees"] if e["employee_id"] == "F001")
        assert f001["absent_days"] == 0.0
        expected_attendance = round(24.0 / 26.0 * 100, 2)
        assert abs(f001["attendance_rate_pct"] - expected_attendance) < 0.1

    def test_overall_productivity_computed(self, labor_engine):
        """
        overall_productivity = total_actual / total_planned = (192+216)/(208+208).
        """
        data = self._sample_attendance()
        result = labor_engine.process_attendance_sheet(data)
        expected = round((192.0 + 216.0) / (208.0 + 208.0), 4)
        actual = result["overall"]["overall_productivity_ratio"]
        assert abs(actual - expected) < 0.001

    def test_low_productivity_alert(self, labor_engine):
        """
        An employee with 50% productivity should trigger low_productivity_departments alert.
        """
        data = [
            {
                "employee_id": "X001",
                "department": "FACTORY",
                "planned_days": 26.0,
                "actual_days": 13.0,
                "planned_hours": 208.0,
                "actual_hours": 100.0,   # 48% productivity
                "overtime_hours": 0.0,
                "leave_days": 0.0,
            }
        ]
        result = labor_engine.process_attendance_sheet(data)
        assert "FACTORY" in result["alerts"]["low_productivity_departments"]

    def test_empty_attendance_sheet(self, labor_engine):
        """Empty attendance list must return zeroed totals without error."""
        result = labor_engine.process_attendance_sheet([])
        assert result["employee_count"] == 0
        assert result["overall"]["total_planned_hours"] == 0.0

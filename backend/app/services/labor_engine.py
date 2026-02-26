"""
labor_engine.py — Production-grade Labor & Payroll Engine
Entity: Madinat Al Saada Aluminium & Glass Works LLC

Covers:
  - Department-level blended rates with UAE burden factors
  - Skill-level multipliers
  - UAE Labor Law overtime (Federal Decree-Law No. 33 of 2021)
  - Project manhour estimation by system type (curtain wall, windows, doors, ACP)
  - Burn rate management (default 13.00 AED/hr fully burdened)
  - Crew allocation with buffer
  - Labor cost projection by department
  - Attendance sheet processing with productivity ratio
"""

from typing import List, Dict, Any, Optional, Tuple
import math


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

WORKING_HOURS_PER_MONTH: int = 208          # UAE standard: 8 hrs × 26 days
STANDARD_HOURS_PER_DAY: int = 8
STANDARD_HOURS_PER_WEEK: int = 48

# UAE Labor Law overtime multipliers
OT_WEEKDAY_MULTIPLIER: float = 1.25         # Art. 19 — weekday extra hours
OT_NIGHT_MULTIPLIER: float = 1.50           # Art. 19 — 10 pm – 4 am night shift
OT_FRIDAY_HOLIDAY_MULTIPLIER: float = 1.50  # Art. 21 — Friday / public holiday

# Department burden factors (visa + accommodation + insurance + EOSB accrual)
DEPARTMENT_BURDEN: Dict[str, float] = {
    "FACTORY":   1.35,
    "SITE":      1.55,
    "DESIGN":    1.20,
    "QA_QC":     1.30,
    "LOGISTICS": 1.40,
}

# Skill-level pay multipliers applied on top of base rate
SKILL_MULTIPLIERS: Dict[str, float] = {
    "HELPER":      1.00,
    "SEMI_SKILLED": 1.20,
    "SKILLED":     1.50,
    "FOREMAN":     1.80,
    "SUPERVISOR":  2.20,
    "ENGINEER":    2.80,
}

# Manhour norms per system type (hours per unit / sqm)
#   format: (fabrication, installation)
SYSTEM_MANHOUR_NORMS: Dict[str, Tuple[float, float]] = {
    "CURTAIN_WALL":  (2.5, 3.0),   # per sqm
    "WINDOW":        (1.5, 2.0),   # per unit
    "DOOR":          (2.0, 3.0),   # per unit
    "ACP":           (1.0, 1.5),   # per sqm
}

# Crew allocation productivity buffer (15 %)
CREW_BUFFER_FACTOR: float = 1.15

# Default burn rate (AED/hr fully burdened, agreed in master plan)
DEFAULT_BURN_RATE_AED: float = 13.00


# ---------------------------------------------------------------------------
# LaborEngine
# ---------------------------------------------------------------------------

class LaborEngine:
    """
    Production-grade labor cost and workforce planning engine for
    Madinat Al Saada Aluminium & Glass Works LLC.

    All monetary values are in AED unless stated otherwise.
    """

    ENTITY: str = "Madinat Al Saada Aluminium & Glass Works LLC"

    def __init__(self) -> None:
        # In-memory burn rate store; replace with DB-backed store in production
        self._burn_rate_aed: float = DEFAULT_BURN_RATE_AED
        self._burn_rate_history: List[Dict[str, Any]] = []

    # -----------------------------------------------------------------------
    # 1. Department-Level Blended Rates
    # -----------------------------------------------------------------------

    def calculate_blended_rates(
        self, payroll_entries: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Compute blended hourly rates per department using actual payroll data.

        Each entry in ``payroll_entries`` must contain:
            - basic_salary   (float)  — monthly basic, AED
            - allowances     (float)  — housing + transport + other, AED
            - department     (str)    — one of DEPARTMENT_BURDEN keys
            - skill_level    (str)    — one of SKILL_MULTIPLIERS keys  [optional]

        Returns a dict with per-department blended rates plus a workforce summary.
        """
        dept_totals: Dict[str, Dict[str, Any]] = {
            dept: {"headcount": 0, "monthly_cost": 0.0}
            for dept in DEPARTMENT_BURDEN
        }
        unrecognised_depts: List[str] = []
        total_headcount: int = 0
        total_monthly_cost: float = 0.0

        for emp in payroll_entries:
            dept = str(emp.get("department", "")).upper()
            basic = float(emp.get("basic_salary", 0.0))
            allowances = float(emp.get("allowances", 0.0))
            skill = str(emp.get("skill_level", "SKILLED")).upper()

            gross_monthly = basic + allowances
            skill_mult = SKILL_MULTIPLIERS.get(skill, 1.0)
            adjusted_monthly = gross_monthly * skill_mult

            if dept not in DEPARTMENT_BURDEN:
                if dept not in unrecognised_depts:
                    unrecognised_depts.append(dept)
                # Fall back to FACTORY burden for unknown dept
                dept = "FACTORY"

            burden = DEPARTMENT_BURDEN[dept]
            burdened_monthly = adjusted_monthly * burden

            dept_totals[dept]["headcount"] += 1
            dept_totals[dept]["monthly_cost"] += burdened_monthly
            total_headcount += 1
            total_monthly_cost += burdened_monthly

        # Derive per-hour rates
        dept_rates: Dict[str, Dict[str, Any]] = {}
        for dept, data in dept_totals.items():
            hc = data["headcount"]
            cost = data["monthly_cost"]
            if hc > 0:
                avg_monthly = cost / hc
                hourly = avg_monthly / WORKING_HOURS_PER_MONTH
            else:
                hourly = 0.0
                avg_monthly = 0.0

            dept_rates[dept] = {
                "headcount": hc,
                "burden_factor": DEPARTMENT_BURDEN[dept],
                "avg_burdened_monthly_aed": round(avg_monthly, 2),
                "blended_hourly_rate_aed": round(hourly, 2),
            }

        # Overall blended rate across all departments
        overall_hourly = (
            total_monthly_cost / (total_headcount * WORKING_HOURS_PER_MONTH)
            if total_headcount > 0
            else DEFAULT_BURN_RATE_AED
        )

        return {
            "entity": self.ENTITY,
            "total_workforce": total_headcount,
            "total_burdened_monthly_cost_aed": round(total_monthly_cost, 2),
            "overall_blended_hourly_rate_aed": round(overall_hourly, 2),
            "by_department": dept_rates,
            "unrecognised_departments": unrecognised_depts,
            "working_hours_per_month": WORKING_HOURS_PER_MONTH,
            "currency": "AED",
        }

    # -----------------------------------------------------------------------
    # 2. Skill-Level Multipliers — utility
    # -----------------------------------------------------------------------

    def get_skill_multiplier(self, skill_level: str) -> float:
        """Return the pay multiplier for a given skill level (case-insensitive)."""
        return SKILL_MULTIPLIERS.get(skill_level.upper(), 1.0)

    def apply_skill_to_rate(self, base_hourly_aed: float, skill_level: str) -> float:
        """Apply skill multiplier to a base hourly rate and return adjusted rate."""
        return round(base_hourly_aed * self.get_skill_multiplier(skill_level), 4)

    # -----------------------------------------------------------------------
    # 3. UAE Labor Law Overtime Calculation
    # -----------------------------------------------------------------------

    def calculate_overtime(
        self,
        base_hourly: float,
        hours_breakdown: Dict[str, float],
    ) -> Dict[str, Any]:
        """
        Calculate gross pay including UAE-legal overtime for one employee.

        ``hours_breakdown`` keys (all values in decimal hours):
            - normal_hours        — regular weekday hours (≤ 8 hrs/day, ≤ 48/week)
            - weekday_ot_hours    — extra hours on normal working days
            - night_ot_hours      — hours between 22:00 – 04:00 (applied on top of weekday OT if overlapping)
            - friday_hours        — all hours worked on Friday or public holiday

        Returns itemised pay components and total gross pay.
        """
        normal_h = max(0.0, float(hours_breakdown.get("normal_hours", 0.0)))
        weekday_ot = max(0.0, float(hours_breakdown.get("weekday_ot_hours", 0.0)))
        night_ot = max(0.0, float(hours_breakdown.get("night_ot_hours", 0.0)))
        friday_h = max(0.0, float(hours_breakdown.get("friday_hours", 0.0)))

        normal_pay = normal_h * base_hourly
        weekday_ot_pay = weekday_ot * base_hourly * OT_WEEKDAY_MULTIPLIER
        # Night OT uses 1.50x; if it overlaps with weekday OT the higher rate applies.
        # Convention here: night_ot_hours are the subset already counted at night rate.
        night_ot_pay = night_ot * base_hourly * OT_NIGHT_MULTIPLIER
        friday_pay = friday_h * base_hourly * OT_FRIDAY_HOLIDAY_MULTIPLIER

        total_hours = normal_h + weekday_ot + night_ot + friday_h
        total_gross = normal_pay + weekday_ot_pay + night_ot_pay + friday_pay

        effective_rate = total_gross / total_hours if total_hours > 0 else base_hourly

        return {
            "base_hourly_rate_aed": round(base_hourly, 4),
            "breakdown": {
                "normal": {
                    "hours": round(normal_h, 2),
                    "multiplier": 1.00,
                    "pay_aed": round(normal_pay, 2),
                },
                "weekday_overtime": {
                    "hours": round(weekday_ot, 2),
                    "multiplier": OT_WEEKDAY_MULTIPLIER,
                    "pay_aed": round(weekday_ot_pay, 2),
                },
                "night_overtime": {
                    "hours": round(night_ot, 2),
                    "multiplier": OT_NIGHT_MULTIPLIER,
                    "pay_aed": round(night_ot_pay, 2),
                },
                "friday_holiday": {
                    "hours": round(friday_h, 2),
                    "multiplier": OT_FRIDAY_HOLIDAY_MULTIPLIER,
                    "pay_aed": round(friday_pay, 2),
                },
            },
            "total_hours_worked": round(total_hours, 2),
            "total_gross_pay_aed": round(total_gross, 2),
            "effective_hourly_rate_aed": round(effective_rate, 4),
            "legal_reference": "UAE Federal Decree-Law No. 33 of 2021, Arts. 19 & 21",
        }

    # -----------------------------------------------------------------------
    # 4. Project Manhour Estimation
    # -----------------------------------------------------------------------

    def estimate_project_manhours(
        self,
        bom_items: List[Dict[str, Any]],
        system_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Estimate total fabrication and installation manhours from the BOM.

        Each ``bom_item`` must contain:
            - system_type  (str)   — CURTAIN_WALL | WINDOW | DOOR | ACP
            - quantity     (float) — sqm for area-based, units for unit-based

        ``system_types`` (optional) filters to specified systems only.

        Returns totals and per-system breakdown.
        """
        system_filter = (
            {s.upper() for s in system_types} if system_types else None
        )

        by_system: Dict[str, Dict[str, Any]] = {}
        total_fab_hours: float = 0.0
        total_install_hours: float = 0.0
        unrecognised: List[str] = []

        for item in bom_items:
            sys_type = str(item.get("system_type", "")).upper()
            qty = max(0.0, float(item.get("quantity", 0.0)))

            if system_filter and sys_type not in system_filter:
                continue

            if sys_type not in SYSTEM_MANHOUR_NORMS:
                if sys_type not in unrecognised:
                    unrecognised.append(sys_type)
                continue

            fab_norm, install_norm = SYSTEM_MANHOUR_NORMS[sys_type]
            fab_hrs = qty * fab_norm
            install_hrs = qty * install_norm

            if sys_type not in by_system:
                by_system[sys_type] = {
                    "quantity": 0.0,
                    "unit": "sqm" if sys_type in ("CURTAIN_WALL", "ACP") else "units",
                    "fab_norm_hrs_per_unit": fab_norm,
                    "install_norm_hrs_per_unit": install_norm,
                    "fab_hours": 0.0,
                    "install_hours": 0.0,
                    "total_hours": 0.0,
                }

            by_system[sys_type]["quantity"] += qty
            by_system[sys_type]["fab_hours"] += fab_hrs
            by_system[sys_type]["install_hours"] += install_hrs
            by_system[sys_type]["total_hours"] += (fab_hrs + install_hrs)

            total_fab_hours += fab_hrs
            total_install_hours += install_hrs

        # Round for readability
        for sys_data in by_system.values():
            for k in ("quantity", "fab_hours", "install_hours", "total_hours"):
                sys_data[k] = round(sys_data[k], 2)

        total_manhours = total_fab_hours + total_install_hours

        return {
            "by_system": by_system,
            "summary": {
                "total_fabrication_hours": round(total_fab_hours, 2),
                "total_installation_hours": round(total_install_hours, 2),
                "total_manhours": round(total_manhours, 2),
            },
            "unrecognised_system_types": unrecognised,
            "manhour_norms_reference": {
                k: {"fab": v[0], "install": v[1]}
                for k, v in SYSTEM_MANHOUR_NORMS.items()
            },
        }

    # -----------------------------------------------------------------------
    # 5. Burn Rate Management
    # -----------------------------------------------------------------------

    def get_current_burn_rate(self) -> float:
        """
        Return the current fully-burdened burn rate in AED per hour.
        Default is 13.00 AED as per Madinat Al Saada standard costing.
        """
        return self._burn_rate_aed

    def update_burn_rate(
        self,
        rate_aed: float,
        effective_month: str,
        source: str,
    ) -> Dict[str, Any]:
        """
        Update the burn rate and record the change in history.

        Args:
            rate_aed        — New fully-burdened rate in AED/hr
            effective_month — ISO month string, e.g. "2026-03"
            source          — Rationale / approval reference

        Returns a confirmation dict with before/after values.
        """
        if rate_aed <= 0:
            raise ValueError(f"Burn rate must be positive; received {rate_aed}")

        previous = self._burn_rate_aed
        self._burn_rate_aed = float(rate_aed)

        record: Dict[str, Any] = {
            "previous_rate_aed": round(previous, 4),
            "new_rate_aed": round(self._burn_rate_aed, 4),
            "effective_month": effective_month,
            "source": source,
            "change_pct": round((self._burn_rate_aed - previous) / previous * 100, 2),
        }
        self._burn_rate_history.append(record)

        return {
            "status": "updated",
            "entity": self.ENTITY,
            **record,
            "history_count": len(self._burn_rate_history),
        }

    def get_burn_rate_history(self) -> List[Dict[str, Any]]:
        """Return the full audit trail of burn rate changes."""
        return list(self._burn_rate_history)

    # -----------------------------------------------------------------------
    # 6. Crew Allocation
    # -----------------------------------------------------------------------

    def calculate_crew_size(
        self,
        total_manhours: float,
        deadline_days: int,
        working_hours_per_day: int = STANDARD_HOURS_PER_DAY,
    ) -> Dict[str, Any]:
        """
        Calculate minimum and recommended crew sizes for a project.

        Recommended crew includes a 15 % productivity buffer to absorb
        absenteeism, rework, and site disruption (Madinat standard).

        Args:
            total_manhours          — Total estimated manhours for the scope
            deadline_days           — Calendar days until completion deadline
            working_hours_per_day   — Productive hours per worker per day (default 8)

        Returns min_crew, recommended_crew, and utilisation metadata.
        """
        if deadline_days <= 0:
            raise ValueError("deadline_days must be a positive integer")
        if working_hours_per_day <= 0:
            raise ValueError("working_hours_per_day must be positive")

        available_hours_per_worker = float(deadline_days * working_hours_per_day)
        manhours = max(0.0, float(total_manhours))

        # Minimum crew to finish exactly on time (no buffer)
        min_crew_raw = manhours / available_hours_per_worker if available_hours_per_worker > 0 else 0.0
        min_crew = math.ceil(min_crew_raw)

        # Recommended crew includes 15 % buffer for real-world inefficiency
        recommended_raw = min_crew_raw * CREW_BUFFER_FACTOR
        recommended_crew = math.ceil(recommended_raw)

        # Hours each worker in the recommended crew will actually work
        hours_per_worker_recommended = (
            manhours / recommended_crew if recommended_crew > 0 else 0.0
        )

        # Utilisation: how busy is the recommended crew (target ≤ 87 %)
        utilisation_pct = (
            hours_per_worker_recommended / available_hours_per_worker * 100
            if available_hours_per_worker > 0
            else 0.0
        )

        return {
            "total_manhours": round(manhours, 2),
            "deadline_days": deadline_days,
            "working_hours_per_day": working_hours_per_day,
            "available_hours_per_worker": round(available_hours_per_worker, 2),
            "min_crew": min_crew,
            "recommended_crew": recommended_crew,
            "buffer_factor": CREW_BUFFER_FACTOR,
            "hours_per_worker_recommended": round(hours_per_worker_recommended, 2),
            "utilisation_pct": round(utilisation_pct, 1),
            "note": (
                "Recommended crew includes 15 % buffer for absenteeism, "
                "rework, and site disruption per Madinat Al Saada standard."
            ),
        }

    # -----------------------------------------------------------------------
    # 7. Labor Cost Projection
    # -----------------------------------------------------------------------

    def project_labor_cost(
        self,
        manhours_breakdown: Dict[str, float],
        blended_rates: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Project total labor cost by department given manhour allocation and
        blended hourly rates.

        Args:
            manhours_breakdown — {department: manhours} e.g. {"FACTORY": 1200.0, "SITE": 800.0}
            blended_rates      — Output of ``calculate_blended_rates()`` or a
                                 dict with key "by_department" → {dept: {"blended_hourly_rate_aed": float}}
                                 OR a flat dict {dept: rate_aed (float)}

        Returns per-department cost lines plus grand total.
        """
        # Accept both the rich output of calculate_blended_rates() and a simple flat dict
        by_dept_raw: Dict[str, Any] = blended_rates.get(
            "by_department", blended_rates
        )

        cost_lines: Dict[str, Dict[str, Any]] = {}
        grand_total: float = 0.0
        grand_manhours: float = 0.0
        warnings: List[str] = []

        for dept, manhours in manhours_breakdown.items():
            dept_key = dept.upper()
            manhours = max(0.0, float(manhours))

            # Extract rate — handle both rich dict and plain float
            dept_data = by_dept_raw.get(dept_key, by_dept_raw.get(dept, None))
            if dept_data is None:
                warnings.append(
                    f"No blended rate found for department '{dept_key}'. "
                    f"Using default burn rate {DEFAULT_BURN_RATE_AED} AED/hr."
                )
                hourly_rate = DEFAULT_BURN_RATE_AED
            elif isinstance(dept_data, dict):
                hourly_rate = float(
                    dept_data.get("blended_hourly_rate_aed", DEFAULT_BURN_RATE_AED)
                )
            else:
                hourly_rate = float(dept_data)

            line_cost = manhours * hourly_rate
            grand_total += line_cost
            grand_manhours += manhours

            cost_lines[dept_key] = {
                "manhours": round(manhours, 2),
                "blended_hourly_rate_aed": round(hourly_rate, 4),
                "line_cost_aed": round(line_cost, 2),
                "pct_of_total": 0.0,  # filled below
            }

        # Compute percentage share
        for dept_key, line in cost_lines.items():
            line["pct_of_total"] = (
                round(line["line_cost_aed"] / grand_total * 100, 2)
                if grand_total > 0
                else 0.0
            )

        effective_blended_rate = (
            grand_total / grand_manhours if grand_manhours > 0 else 0.0
        )

        return {
            "entity": self.ENTITY,
            "by_department": cost_lines,
            "summary": {
                "total_manhours": round(grand_manhours, 2),
                "total_labor_cost_aed": round(grand_total, 2),
                "effective_blended_hourly_rate_aed": round(effective_blended_rate, 4),
            },
            "warnings": warnings,
            "currency": "AED",
        }

    # -----------------------------------------------------------------------
    # 8. Attendance Sheet Processing
    # -----------------------------------------------------------------------

    def process_attendance_sheet(
        self, attendance_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Process an attendance data sheet and compute productivity metrics.

        Each record in ``attendance_data`` should contain:
            - employee_id      (str)
            - employee_name    (str)             [optional]
            - department       (str)
            - planned_days     (int/float)       — scheduled working days in period
            - actual_days      (int/float)       — days actually present
            - planned_hours    (float)           — target productive hours
            - actual_hours     (float)           — hours logged
            - overtime_hours   (float)           [optional, default 0]
            - leave_days       (float)           [optional, default 0]

        Returns:
            - per-employee summary
            - per-department aggregates
            - overall productivity ratio
            - absenteeism rate
            - overtime intensity
        """
        by_dept: Dict[str, Dict[str, Any]] = {}
        employee_summaries: List[Dict[str, Any]] = []

        total_planned_hours: float = 0.0
        total_actual_hours: float = 0.0
        total_ot_hours: float = 0.0
        total_planned_days: float = 0.0
        total_actual_days: float = 0.0

        for rec in attendance_data:
            emp_id = str(rec.get("employee_id", "UNKNOWN"))
            emp_name = str(rec.get("employee_name", emp_id))
            dept = str(rec.get("department", "UNASSIGNED")).upper()

            planned_days = max(0.0, float(rec.get("planned_days", 0.0)))
            actual_days = max(0.0, float(rec.get("actual_days", 0.0)))
            planned_hours = max(0.0, float(rec.get("planned_hours", 0.0)))
            actual_hours = max(0.0, float(rec.get("actual_hours", 0.0)))
            ot_hours = max(0.0, float(rec.get("overtime_hours", 0.0)))
            leave_days = max(0.0, float(rec.get("leave_days", 0.0)))

            absent_days = max(0.0, planned_days - actual_days - leave_days)
            attendance_rate = (
                actual_days / planned_days * 100 if planned_days > 0 else 0.0
            )
            productivity_ratio = (
                actual_hours / planned_hours if planned_hours > 0 else 0.0
            )

            emp_summary: Dict[str, Any] = {
                "employee_id": emp_id,
                "employee_name": emp_name,
                "department": dept,
                "planned_days": planned_days,
                "actual_days": actual_days,
                "leave_days": leave_days,
                "absent_days": round(absent_days, 1),
                "attendance_rate_pct": round(attendance_rate, 2),
                "planned_hours": round(planned_hours, 2),
                "actual_hours": round(actual_hours, 2),
                "overtime_hours": round(ot_hours, 2),
                "productivity_ratio": round(productivity_ratio, 4),
                "productivity_pct": round(productivity_ratio * 100, 2),
            }
            employee_summaries.append(emp_summary)

            # Aggregate by department
            if dept not in by_dept:
                by_dept[dept] = {
                    "headcount": 0,
                    "planned_days": 0.0,
                    "actual_days": 0.0,
                    "absent_days": 0.0,
                    "planned_hours": 0.0,
                    "actual_hours": 0.0,
                    "overtime_hours": 0.0,
                }
            d = by_dept[dept]
            d["headcount"] += 1
            d["planned_days"] += planned_days
            d["actual_days"] += actual_days
            d["absent_days"] += absent_days
            d["planned_hours"] += planned_hours
            d["actual_hours"] += actual_hours
            d["overtime_hours"] += ot_hours

            total_planned_hours += planned_hours
            total_actual_hours += actual_hours
            total_ot_hours += ot_hours
            total_planned_days += planned_days
            total_actual_days += actual_days

        # Derive department-level ratios
        dept_summaries: Dict[str, Dict[str, Any]] = {}
        for dept, d in by_dept.items():
            ph = d["planned_hours"]
            ah = d["actual_hours"]
            pd_ = d["planned_days"]
            ad = d["actual_days"]
            dept_summaries[dept] = {
                "headcount": d["headcount"],
                "planned_hours": round(ph, 2),
                "actual_hours": round(ah, 2),
                "overtime_hours": round(d["overtime_hours"], 2),
                "productivity_ratio": round(ah / ph, 4) if ph > 0 else 0.0,
                "productivity_pct": round(ah / ph * 100, 2) if ph > 0 else 0.0,
                "absenteeism_rate_pct": round(
                    d["absent_days"] / pd_ * 100, 2
                ) if pd_ > 0 else 0.0,
                "attendance_rate_pct": round(ad / pd_ * 100, 2) if pd_ > 0 else 0.0,
            }

        overall_productivity = (
            total_actual_hours / total_planned_hours
            if total_planned_hours > 0
            else 0.0
        )
        overall_absenteeism = (
            (total_planned_days - total_actual_days) / total_planned_days * 100
            if total_planned_days > 0
            else 0.0
        )
        ot_intensity = (
            total_ot_hours / total_actual_hours * 100
            if total_actual_hours > 0
            else 0.0
        )

        # Flag departments with productivity below 85 %
        low_productivity_depts = [
            dept
            for dept, ds in dept_summaries.items()
            if ds["productivity_pct"] < 85.0
        ]

        return {
            "entity": self.ENTITY,
            "employee_count": len(employee_summaries),
            "employees": employee_summaries,
            "by_department": dept_summaries,
            "overall": {
                "total_planned_hours": round(total_planned_hours, 2),
                "total_actual_hours": round(total_actual_hours, 2),
                "total_overtime_hours": round(total_ot_hours, 2),
                "overall_productivity_ratio": round(overall_productivity, 4),
                "overall_productivity_pct": round(overall_productivity * 100, 2),
                "overall_absenteeism_rate_pct": round(overall_absenteeism, 2),
                "overtime_intensity_pct": round(ot_intensity, 2),
            },
            "alerts": {
                "low_productivity_departments": low_productivity_depts,
                "high_absenteeism": overall_absenteeism > 10.0,
                "high_overtime": ot_intensity > 20.0,
            },
        }

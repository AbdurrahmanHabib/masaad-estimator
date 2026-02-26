"""
Phase 3B — Compliance Engineering

C1: Structural & Wind Load Math (BS 6399-2 / ASCE 7)
      Inertia Ixx/Iyy + span → max deflection vs L/175 limit
C2: Thermal / Acoustic Certification (ASHRAE 90.1 + Dubai Green Building Code)
      U-value, SHGCvalue, VLT, Rw → pass/fail vs zone thresholds
C3: Fire & Life Safety Matrix (UAE Civil Defence Code + NFPA 101)
      Fire rating minutes + building type → required FRL; auto-RFI if gap

Results fed into GraphState.compliance_report and surfaced in Quote PDF.
"""
from __future__ import annotations
import math
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("masaad-compliance")


# ── C1 Constants ─────────────────────────────────────────────────────────────

# Material properties — Aluminium 6063-T5 (default UAE extrusion alloy)
E_ALUMINIUM_MPA = 68_900        # Elastic modulus, MPa
E_STEEL_MPA = 200_000           # For steel inserts / composite sections

# Dubai Mean Annual Wind Pressure (ASCE 7 / BS 6399-2 equiv.) — kPa
# Zone 3 coastal (default); conservative for Abu Dhabi / Dubai high-rise
DUBAI_DESIGN_WIND_PRESSURE_KPA = 1.80   # 50-year return period, Exposure B/C

# Deflection limit (UAE/BS): L/175 for glazing frames; BS EN 13830 §4.5
DEFLECTION_LIMIT_DIVISOR = 175

# ── C2 Constants ─────────────────────────────────────────────────────────────

# Dubai Green Building Regulations (DM 2017) + ASHRAE 90.1-2019 — CZ Zone 1
DUBAI_U_VALUE_MAX_W_M2K = 1.9           # Max allowable U-value W/m²K (fenestration)
DUBAI_SHGC_MAX = 0.25                   # Max SHGC (Solar Heat Gain Coefficient)
DUBAI_VLT_MIN = 0.27                    # Min visible light transmittance (DM guideline)
ACOUSTIC_OFFICE_RW_MIN_DB = 38         # Rw ≥ 38 dB for office curtain wall (ISO 140-3)
ACOUSTIC_RESIDENTIAL_RW_MIN_DB = 42    # Rw ≥ 42 dB for residential facade

# ── C3 Constants ─────────────────────────────────────────────────────────────

# UAE Civil Defence Code + NFPA 101 fire rating requirements by building type
FIRE_RATING_REQUIREMENTS: dict[str, int] = {
    "residential_low_rise":   30,   # ≤ 3 floors
    "residential_high_rise":  60,   # > 3 floors
    "commercial_office":      60,
    "hotel":                  60,
    "hospital":               90,
    "car_park":               120,
    "industrial":             60,
    "assembly":               60,
    "mixed_use":              60,
    "unknown":                60,   # Conservative default
}


# ── Data Classes ──────────────────────────────────────────────────────────────

@dataclass
class StructuralCheckResult:
    profile_ref: str
    span_mm: float
    wind_pressure_kpa: float
    inertia_ixx_cm4: float
    inertia_iyy_cm4: float
    deflection_allowable_mm: float
    deflection_actual_mm: float
    passed: bool
    utilisation_ratio: float    # actual / allowable (< 1.0 = pass)
    note: str = ""


@dataclass
class ThermalAcousticResult:
    u_value_w_m2k: Optional[float]
    shgc: Optional[float]
    vlt: Optional[float]
    acoustic_rw_db: Optional[int]
    u_value_passed: Optional[bool]
    shgc_passed: Optional[bool]
    vlt_passed: Optional[bool]
    acoustic_passed: Optional[bool]
    overall_passed: bool
    gaps: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass
class FireSafetyResult:
    building_type: str
    required_fire_rating_minutes: int
    provided_fire_rating_minutes: Optional[int]
    passed: bool
    rfi_required: bool
    rfi_text: Optional[str] = None


@dataclass
class ComplianceReport:
    structural: list[StructuralCheckResult]
    thermal_acoustic: ThermalAcousticResult
    fire_safety: FireSafetyResult
    overall_passed: bool
    summary_flags: list[str]       # Human-readable flags for Quote PDF
    rfi_items: list[str]           # Auto-generated RFI texts


# ── C1: Structural & Wind Load ─────────────────────────────────────────────

def _deflection_simply_supported_mm(
    wind_pressure_kpa: float,
    span_mm: float,
    tributary_width_mm: float,
    inertia_cm4: float,
    e_mpa: float = E_ALUMINIUM_MPA,
) -> float:
    """
    Maximum mid-span deflection for a simply-supported beam under UDL.

    δ_max = (5 × w × L⁴) / (384 × E × I)

    Args:
        wind_pressure_kpa: Design wind pressure in kPa
        span_mm: Unsupported span in mm
        tributary_width_mm: Width of facade panel contributing load to this member
        inertia_cm4: Second moment of area in cm⁴
        e_mpa: Elastic modulus in MPa (N/mm²)

    Returns:
        Max deflection in mm
    """
    # Convert units
    w_n_mm2 = wind_pressure_kpa * 1e-3                         # kPa → N/mm²
    w_n_mm = w_n_mm2 * tributary_width_mm                      # UDL in N/mm
    L = span_mm                                                 # mm
    E = e_mpa                                                   # N/mm² = MPa
    I = inertia_cm4 * 1e4                                       # cm⁴ → mm⁴

    deflection_mm = (5 * w_n_mm * L**4) / (384 * E * I)
    return deflection_mm


def check_structural(
    bom_items: list[dict],
    spec_text: str = "",
    wind_pressure_kpa: float = DUBAI_DESIGN_WIND_PRESSURE_KPA,
) -> list[StructuralCheckResult]:
    """
    C1: Run structural deflection checks for all aluminum extrusion BOM items.

    Falls back to conservative 'L/175' rule if Ixx/Iyy not in catalog.
    Extracts span from opening schedule where possible; defaults to 3000mm.
    """
    results = []

    # Try to extract a dominant span from spec text (e.g. "3600mm span")
    import re
    span_match = re.search(r'(\d{3,5})\s*mm?\s*(span|height|floor.to.floor)', spec_text, re.I)
    default_span_mm = float(span_match.group(1)) if span_match else 3000.0

    for item in bom_items:
        # Only check aluminum extrusion structural members
        if item.get("category") != "ALUMINUM":
            continue
        if item.get("is_attic_stock"):
            continue

        # Get inertia from item or use conservative defaults for typical profiles
        ixx = item.get("inertia_ixx_cm4") or _estimate_inertia(item)
        iyy = item.get("inertia_iyy_cm4") or ixx * 0.3      # Approx for I-section

        span = item.get("span_mm", default_span_mm)
        # Tributary width: assume panel width 1200mm or from opening data
        tributary = item.get("tributary_width_mm", 1200.0)

        # Check strong axis (Ixx) under wind load
        deflection_actual = _deflection_simply_supported_mm(
            wind_pressure_kpa, span, tributary, ixx
        )
        deflection_allowable = span / DEFLECTION_LIMIT_DIVISOR
        ratio = deflection_actual / deflection_allowable if deflection_allowable > 0 else 999.0

        result = StructuralCheckResult(
            profile_ref=item.get("item_code", item.get("description", "Unknown")),
            span_mm=span,
            wind_pressure_kpa=wind_pressure_kpa,
            inertia_ixx_cm4=ixx,
            inertia_iyy_cm4=iyy,
            deflection_allowable_mm=deflection_allowable,
            deflection_actual_mm=deflection_actual,
            passed=ratio <= 1.0,
            utilisation_ratio=round(ratio, 3),
            note=(
                f"FAIL: {deflection_actual:.2f}mm > L/{DEFLECTION_LIMIT_DIVISOR} "
                f"({deflection_allowable:.2f}mm) — REINFORCE or REDUCE SPAN"
                if ratio > 1.0
                else f"PASS: {deflection_actual:.2f}mm ≤ {deflection_allowable:.2f}mm"
            ),
        )
        results.append(result)

    return results


def _estimate_inertia(item: dict) -> float:
    """
    Estimate Ixx from weight_kg_m as a conservative proxy.
    Heavier profiles have larger cross-sections → higher inertia.
    This is a first-pass estimate — replace with real catalog values when available.
    """
    weight_kg_m = item.get("weight_kg_m", 1.5)     # Default: light mullion
    # Empirical: Ixx ≈ 20 × weight_kg_m^2 (cm⁴) for typical aluminum facade profiles
    return max(5.0, 20.0 * (weight_kg_m ** 2))


# ── C2: Thermal / Acoustic ──────────────────────────────────────────────────

def check_thermal_acoustic(
    bom_items: list[dict],
    catalog_matches: list[dict],
    spec_text: str = "",
    building_occupancy: str = "commercial_office",
) -> ThermalAcousticResult:
    """
    C2: Validate thermal and acoustic performance against Dubai / ASHRAE thresholds.
    Reads glass performance data from catalog_matches (GLASS_PERFORMANCE material type).
    """
    gaps = []
    notes = []

    # Extract glass specs from catalog matches
    u_value = None
    shgc = None
    vlt = None
    rw_db = None

    for match in catalog_matches:
        if match.get("material_type") == "GLASS_PERFORMANCE":
            u_value = u_value or match.get("u_value_w_m2k")
            shgc = shgc or match.get("shading_coefficient_sc")   # SC ≈ SHGC / 0.87
            vlt = vlt or match.get("visible_light_transmittance_vlt")
            rw_db = rw_db or match.get("acoustic_rating_rw_db")

    # Fallback: scan spec_text for performance values
    import re
    if u_value is None:
        m = re.search(r'U[- ]?value[:\s=]+([0-9.]+)', spec_text, re.I)
        if m:
            u_value = float(m.group(1))
    if shgc is None:
        m = re.search(r'SHGC[:\s=]+([0-9.]+)', spec_text, re.I)
        if m:
            shgc = float(m.group(1))
    if rw_db is None:
        m = re.search(r'R[wW][:\s=]+(\d+)\s*dB', spec_text)
        if m:
            rw_db = int(m.group(1))

    # Acoustic threshold by building type
    acoustic_min_rw = (
        ACOUSTIC_RESIDENTIAL_RW_MIN_DB
        if "residential" in building_occupancy
        else ACOUSTIC_OFFICE_RW_MIN_DB
    )

    # Run checks
    u_passed = (u_value is not None and u_value <= DUBAI_U_VALUE_MAX_W_M2K)
    shgc_passed = (shgc is not None and shgc <= DUBAI_SHGC_MAX)
    vlt_passed = (vlt is not None and vlt >= DUBAI_VLT_MIN)
    acoustic_passed = (rw_db is not None and rw_db >= acoustic_min_rw)

    if u_value is None:
        gaps.append("U-value not specified — cannot verify DM 2017 §4.3 compliance")
    elif not u_passed:
        gaps.append(f"U-value {u_value} W/m²K exceeds Dubai limit {DUBAI_U_VALUE_MAX_W_M2K} W/m²K")

    if shgc is None:
        gaps.append("SHGC not specified — cannot verify ASHRAE 90.1 solar gain limit")
    elif not shgc_passed:
        gaps.append(f"SHGC {shgc:.3f} exceeds Dubai GBR limit {DUBAI_SHGC_MAX}")

    if vlt is None:
        notes.append("VLT not specified — assumed compliant pending glass schedule")
    elif not vlt_passed:
        gaps.append(f"VLT {vlt:.2f} below Dubai GBR minimum {DUBAI_VLT_MIN}")

    if rw_db is None:
        gaps.append(f"Acoustic rating not specified — {acoustic_min_rw} dB Rw required for {building_occupancy}")
    elif not acoustic_passed:
        gaps.append(f"Rw {rw_db} dB < {acoustic_min_rw} dB required for {building_occupancy}")
    else:
        notes.append(f"Acoustic: Rw {rw_db} dB ✓ ({acoustic_min_rw} dB required)")

    overall = all([
        u_passed if u_value is not None else True,
        shgc_passed if shgc is not None else True,
        vlt_passed if vlt is not None else True,
        acoustic_passed if rw_db is not None else True,
    ])

    return ThermalAcousticResult(
        u_value_w_m2k=u_value,
        shgc=shgc,
        vlt=vlt,
        acoustic_rw_db=rw_db,
        u_value_passed=u_passed if u_value is not None else None,
        shgc_passed=shgc_passed if shgc is not None else None,
        vlt_passed=vlt_passed if vlt is not None else None,
        acoustic_passed=acoustic_passed if rw_db is not None else None,
        overall_passed=overall,
        gaps=gaps,
        notes=notes,
    )


# ── C3: Fire & Life Safety ──────────────────────────────────────────────────

def check_fire_safety(
    catalog_matches: list[dict],
    bom_items: list[dict],
    spec_text: str = "",
    building_type: str = "unknown",
) -> FireSafetyResult:
    """
    C3: Verify fire rating against UAE Civil Defence Code requirements.
    Generates auto-RFI text if gap detected.
    """
    import re

    required_minutes = FIRE_RATING_REQUIREMENTS.get(building_type, 60)

    # Extract fire rating from catalog (ALUMINUM_EXTRUSION or GLASS_PERFORMANCE)
    provided_minutes = None
    for match in catalog_matches:
        fr = match.get("fire_rating_minutes")
        if fr is not None:
            provided_minutes = max(provided_minutes or 0, int(fr))

    # Fallback: scan spec text
    if provided_minutes is None:
        m = re.search(r'fire[- ]?rated?\s+(\d+)\s*(min|minute)', spec_text, re.I)
        if m:
            provided_minutes = int(m.group(1))

    passed = (provided_minutes is not None and provided_minutes >= required_minutes)
    rfi_required = not passed

    rfi_text = None
    if rfi_required:
        if provided_minutes is None:
            rfi_text = (
                f"RFI — Fire Rating Clarification Required:\n"
                f"Building type '{building_type}' requires {required_minutes} min FRL per UAE Civil Defence Code.\n"
                f"No fire rating data found in glass or aluminum specifications.\n"
                f"Please confirm: (a) Is facade system fire-rated? "
                f"(b) Provide third-party test report (BS 476 or ASTM E119).\n"
                f"Estimate excludes fire-rated cost premium pending clarification."
            )
        else:
            rfi_text = (
                f"RFI — Insufficient Fire Rating:\n"
                f"Specified system: {provided_minutes} min FRL.\n"
                f"Required by UAE Civil Defence for '{building_type}': {required_minutes} min.\n"
                f"Gap: {required_minutes - provided_minutes} minutes.\n"
                f"Action: Upgrade glass specification to {required_minutes} min fire-rated "
                f"glazing OR obtain deviation approval from Civil Defence."
            )

    return FireSafetyResult(
        building_type=building_type,
        required_fire_rating_minutes=required_minutes,
        provided_fire_rating_minutes=provided_minutes,
        passed=passed,
        rfi_required=rfi_required,
        rfi_text=rfi_text,
    )


# ── Main Entry Point ──────────────────────────────────────────────────────────

def run_compliance_checks(
    bom_items: list[dict],
    catalog_matches: list[dict],
    spec_text: str = "",
    building_type: str = "unknown",
    building_occupancy: str = "commercial_office",
    wind_pressure_kpa: float = DUBAI_DESIGN_WIND_PRESSURE_KPA,
) -> ComplianceReport:
    """
    Run C1 + C2 + C3 compliance checks.
    Returns a ComplianceReport with all results and serializable summary flags.
    """
    # C1 — Structural
    structural_results = check_structural(bom_items, spec_text, wind_pressure_kpa)

    # C2 — Thermal / Acoustic
    thermal_result = check_thermal_acoustic(
        bom_items, catalog_matches, spec_text, building_occupancy
    )

    # C3 — Fire Safety
    fire_result = check_fire_safety(
        catalog_matches, bom_items, spec_text, building_type
    )

    # Aggregate flags
    flags = []
    rfi_items = []

    structural_fails = [r for r in structural_results if not r.passed]
    if structural_fails:
        flags.append(
            f"STRUCTURAL: {len(structural_fails)} profile(s) exceed L/175 deflection limit"
        )
        for r in structural_fails:
            flags.append(f"  → {r.profile_ref}: {r.note}")

    if thermal_result.gaps:
        flags.extend([f"THERMAL/ACOUSTIC: {g}" for g in thermal_result.gaps])

    if fire_result.rfi_required:
        flags.append(
            f"FIRE SAFETY: {fire_result.building_type} requires "
            f"{fire_result.required_fire_rating_minutes} min FRL — gap detected"
        )
        if fire_result.rfi_text:
            rfi_items.append(fire_result.rfi_text)

    overall = (
        all(r.passed for r in structural_results)
        and thermal_result.overall_passed
        and fire_result.passed
    )

    return ComplianceReport(
        structural=structural_results,
        thermal_acoustic=thermal_result,
        fire_safety=fire_result,
        overall_passed=overall,
        summary_flags=flags,
        rfi_items=rfi_items,
    )


def report_to_dict(report: ComplianceReport) -> dict:
    """Serialize ComplianceReport to a plain dict for GraphState storage."""
    return {
        "overall_passed": report.overall_passed,
        "summary_flags": report.summary_flags,
        "rfi_items": report.rfi_items,
        "structural": [
            {
                "profile_ref": r.profile_ref,
                "span_mm": r.span_mm,
                "inertia_ixx_cm4": r.inertia_ixx_cm4,
                "deflection_actual_mm": round(r.deflection_actual_mm, 3),
                "deflection_allowable_mm": round(r.deflection_allowable_mm, 3),
                "utilisation_ratio": r.utilisation_ratio,
                "passed": r.passed,
                "note": r.note,
            }
            for r in report.structural
        ],
        "thermal_acoustic": {
            "u_value_w_m2k": report.thermal_acoustic.u_value_w_m2k,
            "shgc": report.thermal_acoustic.shgc,
            "vlt": report.thermal_acoustic.vlt,
            "acoustic_rw_db": report.thermal_acoustic.acoustic_rw_db,
            "overall_passed": report.thermal_acoustic.overall_passed,
            "gaps": report.thermal_acoustic.gaps,
            "notes": report.thermal_acoustic.notes,
        },
        "fire_safety": {
            "building_type": report.fire_safety.building_type,
            "required_minutes": report.fire_safety.required_fire_rating_minutes,
            "provided_minutes": report.fire_safety.provided_fire_rating_minutes,
            "passed": report.fire_safety.passed,
            "rfi_required": report.fire_safety.rfi_required,
        },
    }

"""
physics_engine.py — Production-grade structural/facade physics calculations.

Standards referenced:
  - BS EN 1991-1-4:2005 (Wind Actions) / BS 6399-2:1997
  - BS EN 13830:2003 (Curtain Walling — deflection limits)
  - BS EN 12150 / BS EN 14179 (Glass in building)
  - ASHRAE 90.1-2019 (Energy Standard)
  - Dubai Green Building Regulations 2023 (GBR)
  - BS EN ISO 140-3 (Acoustic)
  - UAE Civil Defence Fire Code

UAE / GCC market parameters:
  - Dubai basic wind speed: 35 m/s (Vb,0)
  - Aluminium E-modulus: 70 000 N/mm² (70 GPa)
  - Aluminium thermal expansion: 23.1 × 10⁻⁶ /°C
  - ULS partial factors: γW=1.4 (wind), γG=1.4 (dead), γQ=1.6 (imposed)
  - SLS partial factors: 1.0 (all)
"""

import math
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

# Aluminium properties
AL_E_MPA: float = 70_000.0          # Young's modulus  [N/mm²]
AL_ALPHA: float = 23.1e-6           # Thermal expansion coefficient [/°C]

# Safety / partial factors (ULS / SLS)
GAMMA_W_ULS: float = 1.4            # Wind (ULS)
GAMMA_W_SLS: float = 1.0            # Wind (SLS)
GAMMA_G_ULS: float = 1.4            # Dead load (ULS)
GAMMA_G_SLS: float = 1.0            # Dead load (SLS)
GAMMA_Q_ULS: float = 1.6            # Imposed (ULS)
GAMMA_Q_SLS: float = 1.0            # Imposed (SLS)

# BS EN 13830 deflection limits
MULLION_DEFLECTION_SPAN_RATIO: float = 175.0   # L/175
TRANSOM_DEFLECTION_SPAN_RATIO: float = 200.0   # L/200
TRANSOM_DEFLECTION_ABS_MM: float = 3.0         # 3 mm absolute

# Dubai / UAE wind reference
DUBAI_BASIC_WIND_SPEED_MS: float = 35.0
AIR_DENSITY_KG_M3: float = 1.25                # ρ = 1.25 kg/m³ (Dubai, sea level, warm)

# Glass density
GLASS_DENSITY_KG_M3: float = 2500.0

# ---------------------------------------------------------------------------
# Terrain category tables  (BS EN 1991-1-4 Table 4.1)
#   terrain_category: 1=open sea/flat, 2=suburban, 3=urban, 4=dense city
# ---------------------------------------------------------------------------
#   cr(z) = kr × ln(z/z0)   for z >= z_min
#   z0 = roughness length [m],  z_min = minimum height [m],  kr = roughness factor

_TERRAIN_PARAMS: Dict[int, Dict[str, float]] = {
    1: {"z0": 0.01, "z_min": 1.0,  "kr": 0.17},   # Open (sea/flat terrain)
    2: {"z0": 0.05, "z_min": 2.0,  "kr": 0.19},   # Suburban
    3: {"z0": 0.30, "z_min": 5.0,  "kr": 0.22},   # Urban
    4: {"z0": 1.00, "z_min": 10.0, "kr": 0.24},   # Dense city centre
}

# ---------------------------------------------------------------------------
# External pressure coefficients Cpe (BS EN 1991-1-4 Table 7.1)
#   Zones: A (corner), B (edge), C/D (centre), E (windward/leeward facade)
#   Using simplified values for vertical walls h/d >= 1 (tall buildings)
# ---------------------------------------------------------------------------
_CPE_ZONES: Dict[str, Dict[str, float]] = {
    "corner":  {"Cpe_pos": +0.80, "Cpe_neg": -1.30},
    "edge":    {"Cpe_pos": +0.80, "Cpe_neg": -1.10},
    "center":  {"Cpe_pos": +0.80, "Cpe_neg": -0.70},
    "leeward": {"Cpe_pos": +0.00, "Cpe_neg": -0.50},
    "roof":    {"Cpe_pos": +0.20, "Cpe_neg": -1.80},   # Typical parapet / roof edge
}

# ---------------------------------------------------------------------------
# Glass thickness selection tables
#   Keyed by (support_condition, panel_area_m2_bracket) → (thickness_mm, makeup)
#   Simplified lookup per BS EN 12150 / CWCT Technical Note 31
# ---------------------------------------------------------------------------
_GLASS_THICKNESS_TABLE: List[Dict[str, Any]] = [
    # area_max (m²), wind_max (kPa), support_edges, thickness_mm, makeup
    {"area_max": 1.0,  "wind_max": 1.5, "edges": 4, "thickness": 6,  "makeup": "6 mm toughened"},
    {"area_max": 1.5,  "wind_max": 1.5, "edges": 4, "thickness": 8,  "makeup": "8 mm toughened"},
    {"area_max": 2.0,  "wind_max": 2.0, "edges": 4, "thickness": 10, "makeup": "10 mm toughened"},
    {"area_max": 2.5,  "wind_max": 2.0, "edges": 4, "thickness": 12, "makeup": "12 mm toughened"},
    {"area_max": 3.5,  "wind_max": 2.5, "edges": 4, "thickness": 6,  "makeup": "6+12A+6 DGU toughened"},
    {"area_max": 5.0,  "wind_max": 3.0, "edges": 4, "thickness": 8,  "makeup": "8+12A+8 DGU toughened"},
    {"area_max": 6.0,  "wind_max": 3.5, "edges": 4, "thickness": 10, "makeup": "10+12A+10 DGU toughened"},
    {"area_max": 8.0,  "wind_max": 4.0, "edges": 4, "thickness": 12, "makeup": "12+12A+12 DGU toughened"},
    # 3-edge support — effectively longer unsupported span, thicker glass needed
    {"area_max": 1.0,  "wind_max": 1.5, "edges": 3, "thickness": 8,  "makeup": "8 mm toughened"},
    {"area_max": 2.0,  "wind_max": 2.0, "edges": 3, "thickness": 10, "makeup": "10 mm toughened"},
    {"area_max": 3.0,  "wind_max": 2.5, "edges": 3, "thickness": 12, "makeup": "12 mm toughened"},
    {"area_max": 4.0,  "wind_max": 3.0, "edges": 3, "thickness": 8,  "makeup": "8+12A+8 DGU toughened"},
    {"area_max": 6.0,  "wind_max": 3.5, "edges": 3, "thickness": 10, "makeup": "10+12A+10 DGU toughened"},
    # 2-edge support (top + bottom only, structurally glazed sides)
    {"area_max": 1.0,  "wind_max": 1.0, "edges": 2, "thickness": 10, "makeup": "10 mm toughened"},
    {"area_max": 2.0,  "wind_max": 1.5, "edges": 2, "thickness": 12, "makeup": "12 mm toughened"},
    {"area_max": 3.0,  "wind_max": 2.0, "edges": 2, "thickness": 10, "makeup": "10+12A+10 DGU toughened"},
    {"area_max": 5.0,  "wind_max": 2.5, "edges": 2, "thickness": 12, "makeup": "12+12A+12 DGU toughened"},
]

# Glass type U-value / SHGC lookup (indicative, mid-range product specs)
_GLASS_TYPE_PROPERTIES: Dict[str, Dict[str, float]] = {
    "clear_single":         {"u_value": 5.8,  "shgc": 0.86, "vlt": 0.90, "rw_db": 28},
    "tinted_single":        {"u_value": 5.7,  "shgc": 0.55, "vlt": 0.50, "rw_db": 28},
    "clear_dgu":            {"u_value": 2.8,  "shgc": 0.75, "vlt": 0.82, "rw_db": 32},
    "low_e_dgu":            {"u_value": 1.6,  "shgc": 0.40, "vlt": 0.70, "rw_db": 33},
    "low_e_tinted_dgu":     {"u_value": 1.6,  "shgc": 0.25, "vlt": 0.45, "rw_db": 33},
    "triple_low_e":         {"u_value": 0.7,  "shgc": 0.20, "vlt": 0.55, "rw_db": 36},
    "laminated_dgu":        {"u_value": 2.7,  "shgc": 0.72, "vlt": 0.78, "rw_db": 38},
    "acoustic_laminated":   {"u_value": 2.6,  "shgc": 0.72, "vlt": 0.76, "rw_db": 45},
}

# ---------------------------------------------------------------------------
# Dubai GBR / ASHRAE 90.1 thermal limits
# ---------------------------------------------------------------------------
_THERMAL_LIMITS: Dict[str, Dict[str, float]] = {
    "residential": {"u_max": 1.9, "shgc_N": 0.40, "shgc_EW": 0.25, "shgc_S": 0.30, "vlt_min": 0.27},
    "commercial":  {"u_max": 2.1, "shgc_N": 0.40, "shgc_EW": 0.25, "shgc_S": 0.30, "vlt_min": 0.27},
    "mixed_use":   {"u_max": 2.0, "shgc_N": 0.40, "shgc_EW": 0.25, "shgc_S": 0.30, "vlt_min": 0.27},
    "industrial":  {"u_max": 2.5, "shgc_N": 0.50, "shgc_EW": 0.40, "shgc_S": 0.40, "vlt_min": 0.20},
}

# ---------------------------------------------------------------------------
# Bracket capacity table (mild-steel hot-dip galvanised, M12 grade 8.8 anchors)
# ---------------------------------------------------------------------------
_BRACKET_CAPACITIES: Dict[str, Dict[str, float]] = {
    "L_bracket_light":    {"tension_kn": 8.0,  "shear_kn": 12.0, "moment_knm": 1.5,  "mass_kg": 0.8},
    "L_bracket_heavy":    {"tension_kn": 20.0, "shear_kn": 30.0, "moment_knm": 4.0,  "mass_kg": 2.5},
    "T_bracket_std":      {"tension_kn": 15.0, "shear_kn": 25.0, "moment_knm": 3.0,  "mass_kg": 1.8},
    "Z_bracket_adj":      {"tension_kn": 12.0, "shear_kn": 18.0, "moment_knm": 2.0,  "mass_kg": 1.2},
    "cast_in_channel":    {"tension_kn": 35.0, "shear_kn": 50.0, "moment_knm": 8.0,  "mass_kg": 4.5},
    "plate_bracket_weld": {"tension_kn": 60.0, "shear_kn": 80.0, "moment_knm": 15.0, "mass_kg": 8.0},
    "hilti_anchor_m12":   {"tension_kn": 18.5, "shear_kn": 14.0, "moment_knm": 0.0,  "mass_kg": 0.1},
    "hilti_anchor_m16":   {"tension_kn": 32.0, "shear_kn": 24.0, "moment_knm": 0.0,  "mass_kg": 0.2},
}


class PhysicsEngine:
    """
    Production-grade facade / structural physics engine for aluminium & glass
    facade systems operating under UAE / GCC climatic and regulatory conditions.

    All calculations return typed dictionaries with inputs echoed back, intermediate
    values exposed, and a clear pass/fail verdict plus utilization ratio.

    Standards:
      BS EN 1991-1-4:2005, BS EN 13830:2003, BS EN 12150-1:2015,
      ASHRAE 90.1-2019, Dubai GBR 2023, BS EN ISO 140-3.
    """

    # ------------------------------------------------------------------
    # 1. Wind load  (BS EN 1991-1-4 / BS 6399-2)
    # ------------------------------------------------------------------

    def calculate_wind_pressure(
        self,
        basic_wind_speed_ms: float = DUBAI_BASIC_WIND_SPEED_MS,
        building_height_m: float = 30.0,
        terrain_category: int = 2,
        zone: str = "center",
    ) -> Dict[str, Any]:
        """
        Calculate peak velocity pressure qp and net design wind pressure
        for a facade zone per BS EN 1991-1-4.

        Parameters
        ----------
        basic_wind_speed_ms : float
            10-minute mean basic wind speed Vb,0 [m/s]. Dubai default = 35 m/s.
        building_height_m : float
            Reference height ze for external pressure [m].
        terrain_category : int
            1 = open flat / sea coast
            2 = suburban
            3 = urban
            4 = dense city centre
        zone : str
            Facade zone. One of: 'corner', 'edge', 'center', 'leeward', 'roof'.

        Returns
        -------
        Dict with inputs, intermediate values, and:
          qb_kpa          — basic velocity pressure [kPa]
          cr_z            — roughness factor at height z
          vm_z_ms         — mean wind velocity at height z [m/s]
          Iv_z            — turbulence intensity at height z
          qp_kpa          — peak velocity pressure [kPa]
          Cpe_pos/neg     — external pressure coefficients
          Wp_pos_kpa      — positive design pressure (SLS) [kPa]
          Wp_neg_kpa      — negative design pressure / suction (SLS) [kPa]
          Wp_pos_uls_kpa  — positive design pressure (ULS) [kPa]
          Wp_neg_uls_kpa  — negative design pressure (ULS) [kPa]
        """
        if terrain_category not in _TERRAIN_PARAMS:
            raise ValueError(
                f"terrain_category must be 1-4, got {terrain_category}"
            )
        if zone not in _CPE_ZONES:
            valid = list(_CPE_ZONES.keys())
            raise ValueError(f"zone must be one of {valid}, got '{zone}'")

        tp = _TERRAIN_PARAMS[terrain_category]
        z0: float = tp["z0"]
        z_min: float = tp["z_min"]
        kr: float = tp["kr"]

        # Reference height — apply z_min floor
        z_ref: float = max(building_height_m, z_min)

        # Directional / seasonal factor — set to 1.0 (conservative, Dubai)
        c_dir: float = 1.0
        c_season: float = 1.0
        Vb: float = basic_wind_speed_ms * c_dir * c_season

        # Basic velocity pressure qb = 0.5 ρ Vb²
        qb_pa: float = 0.5 * AIR_DENSITY_KG_M3 * Vb ** 2
        qb_kpa: float = qb_pa / 1000.0

        # Roughness factor cr(z) = kr × ln(z/z0)
        cr_z: float = kr * math.log(z_ref / z0)

        # Mean wind velocity vm(z) = cr(z) × Vb
        vm_z_ms: float = cr_z * Vb

        # Turbulence intensity Iv(z) = σv / vm = 1 / (c0 × ln(z/z0))
        # c0 = orography factor = 1.0 (flat terrain)
        c0: float = 1.0
        Iv_z: float = 1.0 / (c0 * math.log(z_ref / z0))

        # Peak velocity pressure
        # qp(z) = [1 + 7 Iv(z)] × 0.5 ρ vm(z)²
        qp_pa: float = (1.0 + 7.0 * Iv_z) * 0.5 * AIR_DENSITY_KG_M3 * vm_z_ms ** 2
        qp_kpa: float = qp_pa / 1000.0

        # External pressure coefficients for chosen zone
        zone_cpe = _CPE_ZONES[zone]
        Cpe_pos: float = zone_cpe["Cpe_pos"]
        Cpe_neg: float = zone_cpe["Cpe_neg"]

        # Internal pressure coefficient Cpi (assume dominant openings → ±0.2)
        Cpi_pos: float = +0.20
        Cpi_neg: float = -0.20

        # Net pressure: We = qp × (Cpe − Cpi)
        # Positive pressure (outward on facade) — worst case suction on inside
        Wp_pos_sls_kpa: float = qp_kpa * (Cpe_pos - Cpi_neg)
        # Negative pressure (inward suction on facade) — worst case pressure on inside
        Wp_neg_sls_kpa: float = qp_kpa * (Cpe_neg - Cpi_pos)

        # ULS design pressures
        Wp_pos_uls_kpa: float = Wp_pos_sls_kpa * GAMMA_W_ULS
        Wp_neg_uls_kpa: float = Wp_neg_sls_kpa * GAMMA_W_ULS  # negative = suction

        return {
            "standard": "BS EN 1991-1-4:2005",
            "inputs": {
                "basic_wind_speed_ms": basic_wind_speed_ms,
                "building_height_m": building_height_m,
                "terrain_category": terrain_category,
                "zone": zone,
            },
            "intermediate": {
                "Vb_ms": round(Vb, 3),
                "z_ref_m": round(z_ref, 3),
                "z0_m": z0,
                "kr": kr,
                "cr_z": round(cr_z, 4),
                "vm_z_ms": round(vm_z_ms, 3),
                "Iv_z": round(Iv_z, 4),
                "Cpe_pos": Cpe_pos,
                "Cpe_neg": Cpe_neg,
                "Cpi_pos": Cpi_pos,
                "Cpi_neg": Cpi_neg,
            },
            "results": {
                "qb_kpa": round(qb_kpa, 4),
                "qp_kpa": round(qp_kpa, 4),
                "Wp_pos_sls_kpa": round(Wp_pos_sls_kpa, 4),
                "Wp_neg_sls_kpa": round(Wp_neg_sls_kpa, 4),
                "Wp_pos_uls_kpa": round(Wp_pos_uls_kpa, 4),
                "Wp_neg_uls_kpa": round(Wp_neg_uls_kpa, 4),
            },
        }

    # ------------------------------------------------------------------
    # 2. Mullion deflection  (BS EN 13830 — L/175)
    # ------------------------------------------------------------------

    def check_mullion_deflection(
        self,
        span_mm: float,
        moment_of_inertia_mm4: float,
        wind_pressure_kpa: float,
        tributary_width_mm: float,
        aluminum_E: float = AL_E_MPA,
    ) -> Dict[str, Any]:
        """
        Check mullion bending deflection under SLS wind load.

        Uses simply-supported beam model with uniformly distributed load (UDL):
          δ_max = 5 w L⁴ / (384 E I)

        Limit: L/175 per BS EN 13830:2003, clause 4.3.

        Parameters
        ----------
        span_mm              : Clear span between structural supports [mm]
        moment_of_inertia_mm4: Second moment of area of mullion section [mm⁴]
        wind_pressure_kpa    : SLS design wind pressure on facade [kPa]
        tributary_width_mm   : Tributary facade width carried by this mullion [mm]
        aluminum_E           : Young's modulus of aluminium [N/mm²], default 70 000

        Returns
        -------
        Dict with deflection [mm], limit [mm], utilization, pass/fail.
        """
        # Convert wind pressure to line load on mullion
        # w [N/mm] = pressure [kPa] × tributary_width [mm] × (1 kPa = 1 N/mm² × 10⁻³)
        # pressure [kPa] = [N/mm²] × 10⁻³ → 1 kPa = 0.001 N/mm²
        w_N_per_mm: float = wind_pressure_kpa * 0.001 * tributary_width_mm  # [N/mm]

        # SLS — use SLS factor (1.0), so no amplification
        w_sls: float = w_N_per_mm * GAMMA_W_SLS

        # δ = 5wL⁴ / 384EI
        delta_mm: float = (
            5.0 * w_sls * span_mm ** 4
        ) / (384.0 * aluminum_E * moment_of_inertia_mm4)

        # Deflection limit
        limit_mm: float = span_mm / MULLION_DEFLECTION_SPAN_RATIO

        utilization: float = delta_mm / limit_mm if limit_mm > 0 else float("inf")
        passed: bool = delta_mm <= limit_mm

        # Bending moment at mid-span (for reference / ULS check)
        M_max_Nmm_sls: float = w_sls * span_mm ** 2 / 8.0
        M_max_Nmm_uls: float = w_N_per_mm * GAMMA_W_ULS * span_mm ** 2 / 8.0

        return {
            "standard": "BS EN 13830:2003 cl.4.3",
            "inputs": {
                "span_mm": span_mm,
                "moment_of_inertia_mm4": moment_of_inertia_mm4,
                "wind_pressure_kpa": wind_pressure_kpa,
                "tributary_width_mm": tributary_width_mm,
                "aluminum_E_mpa": aluminum_E,
            },
            "intermediate": {
                "w_sls_N_per_mm": round(w_sls, 6),
                "M_max_sls_kNm": round(M_max_Nmm_sls / 1e6, 4),
                "M_max_uls_kNm": round(M_max_Nmm_uls / 1e6, 4),
            },
            "results": {
                "deflection_mm": round(delta_mm, 3),
                "limit_mm": round(limit_mm, 3),
                "limit_ratio": f"L/{int(MULLION_DEFLECTION_SPAN_RATIO)}",
                "utilization": round(utilization, 4),
                "passed": passed,
                "status": "PASS" if passed else "FAIL",
            },
        }

    # ------------------------------------------------------------------
    # 3. Transom deflection  (BS EN 13830 — L/200 or 3 mm)
    # ------------------------------------------------------------------

    def check_transom_deflection(
        self,
        span_mm: float,
        inertia_mm4: float,
        glass_weight_kg: float,
        dead_load_kpa: float = 0.5,
        aluminum_E: float = AL_E_MPA,
    ) -> Dict[str, Any]:
        """
        Check transom bending deflection under dead load (glass self-weight).

        Model: simply-supported beam, UDL from glass weight + dead-load component.
        Limit: lesser of L/200 or 3 mm (BS EN 13830:2003).

        Parameters
        ----------
        span_mm         : Transom clear span [mm]
        inertia_mm4     : Second moment of area of transom section [mm⁴]
        glass_weight_kg : Total weight of glass panel(s) supported by this transom [kg]
        dead_load_kpa   : Additional dead load (frame/infill) [kPa], default 0.5
        aluminum_E      : Young's modulus [N/mm²]

        Returns
        -------
        Dict with deflection, dual limit, utilization, pass/fail.
        """
        g: float = 9.81  # m/s²

        # Glass self-weight as UDL on transom
        glass_force_N: float = glass_weight_kg * g  # total point load treated as UDL
        w_glass_N_per_mm: float = glass_force_N / span_mm   # UDL [N/mm]

        # Dead load component (frame, secondary elements)
        # Treat as additional UDL: 0.5 kPa × tributary depth (assume 1 m = 1000 mm wide)
        # In practice caller provides dead_load_kpa already tributary-adjusted
        w_dead_N_per_mm: float = dead_load_kpa * 0.001 * 1000.0   # [N/mm] (1m tributary)

        w_total_sls: float = (w_glass_N_per_mm + w_dead_N_per_mm) * GAMMA_G_SLS

        # δ = 5wL⁴ / 384EI
        delta_mm: float = (
            5.0 * w_total_sls * span_mm ** 4
        ) / (384.0 * aluminum_E * inertia_mm4)

        # Dual limit
        limit_span_mm: float = span_mm / TRANSOM_DEFLECTION_SPAN_RATIO
        limit_abs_mm: float = TRANSOM_DEFLECTION_ABS_MM
        limit_mm: float = min(limit_span_mm, limit_abs_mm)

        utilization: float = delta_mm / limit_mm if limit_mm > 0 else float("inf")
        passed: bool = delta_mm <= limit_mm

        # ULS bending moment for information
        w_uls: float = (w_glass_N_per_mm + w_dead_N_per_mm) * GAMMA_G_ULS
        M_uls_Nmm: float = w_uls * span_mm ** 2 / 8.0

        return {
            "standard": "BS EN 13830:2003 cl.4.3",
            "inputs": {
                "span_mm": span_mm,
                "inertia_mm4": inertia_mm4,
                "glass_weight_kg": glass_weight_kg,
                "dead_load_kpa": dead_load_kpa,
                "aluminum_E_mpa": aluminum_E,
            },
            "intermediate": {
                "w_glass_N_per_mm": round(w_glass_N_per_mm, 6),
                "w_dead_N_per_mm": round(w_dead_N_per_mm, 6),
                "w_total_sls_N_per_mm": round(w_total_sls, 6),
                "M_uls_kNm": round(M_uls_Nmm / 1e6, 4),
            },
            "results": {
                "deflection_mm": round(delta_mm, 3),
                "limit_span_mm": round(limit_span_mm, 3),
                "limit_abs_mm": limit_abs_mm,
                "governing_limit_mm": round(limit_mm, 3),
                "governing_criterion": (
                    f"L/{int(TRANSOM_DEFLECTION_SPAN_RATIO)}"
                    if limit_span_mm < limit_abs_mm
                    else "3 mm absolute"
                ),
                "utilization": round(utilization, 4),
                "passed": passed,
                "status": "PASS" if passed else "FAIL",
            },
        }

    # ------------------------------------------------------------------
    # 4. Glass thickness selection  (BS EN 12150 / CWCT TN 31)
    # ------------------------------------------------------------------

    def select_glass_thickness(
        self,
        panel_width_mm: float,
        panel_height_mm: float,
        wind_pressure_kpa: float,
        glass_type: str = "low_e_dgu",
        support_condition: int = 4,
    ) -> Dict[str, Any]:
        """
        Select minimum glass thickness and makeup for a given panel geometry,
        wind pressure, glass type, and support condition.

        Parameters
        ----------
        panel_width_mm    : Panel width [mm]
        panel_height_mm   : Panel height [mm]
        wind_pressure_kpa : Design wind pressure (SLS) [kPa]
        glass_type        : Key from _GLASS_TYPE_PROPERTIES dict.
        support_condition : Number of supported edges: 2, 3, or 4.

        Returns
        -------
        Dict with selected thickness, makeup, weight/m², thermal properties.
        """
        if support_condition not in (2, 3, 4):
            raise ValueError(
                f"support_condition must be 2, 3, or 4 edges, got {support_condition}"
            )
        if glass_type not in _GLASS_TYPE_PROPERTIES:
            valid = list(_GLASS_TYPE_PROPERTIES.keys())
            raise ValueError(
                f"glass_type must be one of {valid}, got '{glass_type}'"
            )

        panel_area_m2: float = (panel_width_mm / 1000.0) * (panel_height_mm / 1000.0)
        aspect_ratio: float = (
            max(panel_width_mm, panel_height_mm) / min(panel_width_mm, panel_height_mm)
        )

        # Filter table rows for this support condition, sorted by area_max ascending
        candidates = sorted(
            [
                r for r in _GLASS_THICKNESS_TABLE
                if r["edges"] == support_condition
            ],
            key=lambda x: (x["area_max"], x["wind_max"]),
        )

        selected: Optional[Dict[str, Any]] = None
        for row in candidates:
            if panel_area_m2 <= row["area_max"] and wind_pressure_kpa <= row["wind_max"]:
                selected = row
                break

        # Fallback: use the heaviest option if nothing matched
        if selected is None:
            fallback_candidates = [
                r for r in candidates
                if r["edges"] == support_condition
            ]
            selected = (
                max(fallback_candidates, key=lambda x: x["thickness"])
                if fallback_candidates
                else {"thickness": 12, "makeup": "12+12A+12 DGU toughened (engineer review required)"}
            )
            engineer_review: bool = True
        else:
            engineer_review = False

        # Nominal glass thickness for weight calculation
        thickness_mm: int = selected["thickness"]
        makeup: str = selected["makeup"]

        # Weight per m² — sum thicknesses from makeup string
        # Parse digits from makeup: e.g. "8+12A+8" → glass plies are 8 and 8 mm
        glass_ply_thicknesses = self._parse_glass_plies_mm(makeup, thickness_mm)
        weight_kg_m2: float = sum(
            t * GLASS_DENSITY_KG_M3 / 1000.0 for t in glass_ply_thicknesses
        )

        # Total panel weight
        panel_weight_kg: float = weight_kg_m2 * panel_area_m2

        # Retrieve glass type optical/thermal properties
        props = _GLASS_TYPE_PROPERTIES[glass_type]

        return {
            "standard": "BS EN 12150-1:2015 / CWCT TN31",
            "inputs": {
                "panel_width_mm": panel_width_mm,
                "panel_height_mm": panel_height_mm,
                "panel_area_m2": round(panel_area_m2, 4),
                "aspect_ratio": round(aspect_ratio, 3),
                "wind_pressure_kpa": wind_pressure_kpa,
                "glass_type": glass_type,
                "support_condition_edges": support_condition,
            },
            "results": {
                "selected_thickness_mm": thickness_mm,
                "makeup": makeup,
                "glass_ply_thicknesses_mm": glass_ply_thicknesses,
                "weight_kg_per_m2": round(weight_kg_m2, 2),
                "panel_weight_kg": round(panel_weight_kg, 2),
                "u_value_W_m2K": props["u_value"],
                "shgc": props["shgc"],
                "vlt": props["vlt"],
                "rw_db": props["rw_db"],
                "engineer_review_required": engineer_review,
            },
        }

    def _parse_glass_plies_mm(self, makeup: str, fallback_mm: int) -> List[int]:
        """
        Extract glass ply thicknesses from makeup string such as '8+12A+8 DGU toughened'.
        Returns list of glass thicknesses (excludes cavity widths marked with 'A').
        """
        import re  # stdlib re is used only here, not a top-level import
        # Split on '+' and extract leading integer tokens that are NOT air gaps
        tokens = re.split(r"[+\s]", makeup)
        plies: List[int] = []
        for tok in tokens:
            # air cavity tokens end in 'A' e.g. '12A'
            if re.match(r"^\d+A$", tok):
                continue
            m = re.match(r"^(\d+)$", tok)
            if m:
                plies.append(int(m.group(1)))
        return plies if plies else [fallback_mm]

    # ------------------------------------------------------------------
    # 5. Thermal compliance  (ASHRAE 90.1 + Dubai GBR 2023)
    # ------------------------------------------------------------------

    def check_thermal_compliance(
        self,
        u_value: float,
        shgc: float,
        vlt: float,
        building_type: str = "commercial",
        orientation: str = "N",
    ) -> Dict[str, Any]:
        """
        Check whether glazing assembly meets thermal and solar control requirements
        per Dubai Green Building Regulations 2023 / ASHRAE 90.1-2019.

        Parameters
        ----------
        u_value      : Centre-of-glass or whole-window U-value [W/(m²·K)]
        shgc         : Solar Heat Gain Coefficient (0–1)
        vlt          : Visible Light Transmittance (0–1)
        building_type: 'residential', 'commercial', 'mixed_use', 'industrial'
        orientation  : Cardinal: 'N', 'S', 'E', 'W', 'NE', 'NW', 'SE', 'SW'

        Returns
        -------
        Dict with limit values, compliance per parameter, and overall verdict.
        """
        bt = building_type.lower()
        if bt not in _THERMAL_LIMITS:
            valid = list(_THERMAL_LIMITS.keys())
            raise ValueError(
                f"building_type must be one of {valid}, got '{building_type}'"
            )

        limits = _THERMAL_LIMITS[bt]

        # Map orientation to E/W/N/S group
        orient_upper = orientation.upper()
        if orient_upper in ("N", "NE", "NW"):
            shgc_limit = limits["shgc_N"]
            orient_group = "North"
        elif orient_upper in ("S", "SE", "SW"):
            shgc_limit = limits["shgc_S"]
            orient_group = "South"
        else:  # E, W
            shgc_limit = limits["shgc_EW"]
            orient_group = "East/West"

        u_pass: bool = u_value <= limits["u_max"]
        shgc_pass: bool = shgc <= shgc_limit
        vlt_pass: bool = vlt >= limits["vlt_min"]

        # Light-to-solar-gain ratio (LSG) — informational
        lsg: float = vlt / shgc if shgc > 0 else 0.0

        overall_pass: bool = u_pass and shgc_pass and vlt_pass

        checks: List[Dict[str, Any]] = [
            {
                "parameter": "U-value [W/(m²·K)]",
                "value": u_value,
                "limit": limits["u_max"],
                "operator": "<=",
                "passed": u_pass,
            },
            {
                "parameter": f"SHGC ({orient_group})",
                "value": shgc,
                "limit": shgc_limit,
                "operator": "<=",
                "passed": shgc_pass,
            },
            {
                "parameter": "VLT",
                "value": vlt,
                "limit": limits["vlt_min"],
                "operator": ">=",
                "passed": vlt_pass,
            },
        ]

        failing = [c["parameter"] for c in checks if not c["passed"]]

        return {
            "standard": "Dubai GBR 2023 / ASHRAE 90.1-2019",
            "inputs": {
                "u_value": u_value,
                "shgc": shgc,
                "vlt": vlt,
                "building_type": building_type,
                "orientation": orientation,
                "orientation_group": orient_group,
            },
            "limits": {
                "u_max_W_m2K": limits["u_max"],
                f"shgc_max_{orient_group.replace('/', '_')}": shgc_limit,
                "vlt_min": limits["vlt_min"],
            },
            "results": {
                "light_to_solar_gain_ratio": round(lsg, 3),
                "checks": checks,
                "failing_parameters": failing,
                "overall_passed": overall_pass,
                "status": "COMPLIANT" if overall_pass else "NON-COMPLIANT",
            },
        }

    # ------------------------------------------------------------------
    # 6. Acoustic rating  (BS EN ISO 140-3 / ISO 717-1)
    # ------------------------------------------------------------------

    def check_acoustic_rating(
        self,
        glass_makeup: str,
        rw_db: float,
        required_rw: float,
    ) -> Dict[str, Any]:
        """
        Check whether a glass assembly meets the minimum weighted sound
        reduction index Rw per project acoustic specification.

        Typical requirements (UAE):
          - Standard residential:      Rw ≥ 30 dB
          - Residential near highway:  Rw ≥ 40 dB
          - Commercial office:         Rw ≥ 35 dB
          - Hospital / classroom:      Rw ≥ 40 dB
          - Highway / airport noise:   Rw ≥ 45 dB

        Parameters
        ----------
        glass_makeup : Description of glass assembly (informational, for report)
        rw_db        : Achieved weighted sound reduction index Rw [dB]
        required_rw  : Minimum required Rw [dB]

        Returns
        -------
        Dict with margin, pass/fail, and grade classification.
        """
        margin_db: float = rw_db - required_rw
        passed: bool = rw_db >= required_rw

        # Performance grade
        if rw_db < 28:
            grade = "Poor"
        elif rw_db < 33:
            grade = "Standard"
        elif rw_db < 38:
            grade = "Enhanced"
        elif rw_db < 43:
            grade = "High"
        else:
            grade = "Superior"

        # Classify application suitability
        suitable_for: List[str] = []
        if rw_db >= 30:
            suitable_for.append("Standard residential")
        if rw_db >= 35:
            suitable_for.append("Commercial office / retail")
        if rw_db >= 40:
            suitable_for.append("Residential near arterial road / hospital")
        if rw_db >= 45:
            suitable_for.append("Highway / rail / airport adjacent")

        return {
            "standard": "BS EN ISO 140-3 / ISO 717-1",
            "inputs": {
                "glass_makeup": glass_makeup,
                "rw_achieved_db": rw_db,
                "rw_required_db": required_rw,
            },
            "results": {
                "margin_db": round(margin_db, 1),
                "passed": passed,
                "status": "PASS" if passed else "FAIL",
                "performance_grade": grade,
                "suitable_for_applications": suitable_for,
            },
        }

    # ------------------------------------------------------------------
    # 7. Thermal movement  (BS EN 1999-1-1)
    # ------------------------------------------------------------------

    def calculate_thermal_movement(
        self,
        member_length_mm: float,
        temp_range_c: float = 40.0,
        alpha: float = AL_ALPHA,
    ) -> float:
        """
        Calculate thermal elongation of an aluminium member.

        ΔL = α × L × ΔT

        Parameters
        ----------
        member_length_mm : Member length [mm]
        temp_range_c     : Temperature range ΔT [°C]. Dubai design range 40 °C
                           (day/night swing; use 80 °C for full seasonal range).
        alpha            : Coefficient of thermal expansion [/°C].
                           Default 23.1 × 10⁻⁶ /°C (aluminium, BS EN 1999-1-1).

        Returns
        -------
        float : Thermal movement ΔL [mm].
        """
        delta_L_mm: float = alpha * member_length_mm * temp_range_c
        return round(delta_L_mm, 3)

    def calculate_thermal_movement_detailed(
        self,
        member_length_mm: float,
        temp_range_c: float = 40.0,
        alpha: float = AL_ALPHA,
    ) -> Dict[str, Any]:
        """
        Detailed version of thermal movement calculation with expansion joint sizing
        guidance for aluminium facade members.

        Returns
        -------
        Dict including ΔL, recommended joint gap with 25% oversize factor, and notes.
        """
        delta_L_mm: float = self.calculate_thermal_movement(
            member_length_mm, temp_range_c, alpha
        )

        # Joint gap: ΔL × 1.25 safety margin, minimum 5 mm
        recommended_joint_mm: float = max(delta_L_mm * 1.25, 5.0)

        return {
            "standard": "BS EN 1999-1-1:2007",
            "inputs": {
                "member_length_mm": member_length_mm,
                "temp_range_c": temp_range_c,
                "alpha_per_C": alpha,
            },
            "results": {
                "delta_L_mm": delta_L_mm,
                "recommended_joint_gap_mm": round(recommended_joint_mm, 2),
                "notes": (
                    f"Design joint gap = ΔL × 1.25 safety factor. "
                    f"Minimum joint gap 5 mm. "
                    f"For {member_length_mm:.0f} mm member over {temp_range_c:.0f} °C "
                    f"range: ΔL = {delta_L_mm:.2f} mm."
                ),
            },
        }

    # ------------------------------------------------------------------
    # 8. Bracket capacity
    # ------------------------------------------------------------------

    def calculate_bracket_capacity(
        self,
        bracket_type: str,
        load_kn: float,
        load_direction: str = "shear",
    ) -> Dict[str, Any]:
        """
        Check bracket utilization against tabulated capacities for standard
        hot-dip galvanised mild steel brackets used in aluminium facade systems.

        Parameters
        ----------
        bracket_type    : Key from bracket capacity table. Options:
                          'L_bracket_light', 'L_bracket_heavy', 'T_bracket_std',
                          'Z_bracket_adj', 'cast_in_channel', 'plate_bracket_weld',
                          'hilti_anchor_m12', 'hilti_anchor_m16'
        load_kn         : Applied load [kN] (ULS factored)
        load_direction  : 'tension', 'shear', or 'moment'

        Returns
        -------
        Dict with capacity, utilization, pass/fail.
        """
        if bracket_type not in _BRACKET_CAPACITIES:
            valid = list(_BRACKET_CAPACITIES.keys())
            raise ValueError(
                f"bracket_type must be one of {valid}, got '{bracket_type}'"
            )
        if load_direction not in ("tension", "shear", "moment"):
            raise ValueError(
                "load_direction must be 'tension', 'shear', or 'moment'"
            )

        caps = _BRACKET_CAPACITIES[bracket_type]

        capacity_map: Dict[str, float] = {
            "tension": caps["tension_kn"],
            "shear":   caps["shear_kn"],
            "moment":  caps.get("moment_knm", 0.0),
        }
        unit_map: Dict[str, str] = {
            "tension": "kN",
            "shear":   "kN",
            "moment":  "kN·m",
        }

        capacity: float = capacity_map[load_direction]
        unit: str = unit_map[load_direction]

        utilization: float = load_kn / capacity if capacity > 0 else float("inf")
        passed: bool = utilization <= 1.0

        return {
            "inputs": {
                "bracket_type": bracket_type,
                "load_kn_or_knm": load_kn,
                "load_direction": load_direction,
            },
            "capacities": {
                "tension_kn": caps["tension_kn"],
                "shear_kn":   caps["shear_kn"],
                "moment_knm": caps.get("moment_knm", 0.0),
                "mass_kg":    caps["mass_kg"],
            },
            "results": {
                "applied_load": load_kn,
                "capacity": capacity,
                "unit": unit,
                "utilization": round(utilization, 4),
                "passed": passed,
                "status": "PASS" if passed else "FAIL — UPGRADE BRACKET",
                "reserve_capacity_pct": round((1.0 - utilization) * 100, 1),
            },
        }

    # ------------------------------------------------------------------
    # 9. ACP skeleton  (retained from original, extended)
    # ------------------------------------------------------------------

    def generate_acp_skeleton(
        self, net_sqm: float, perimeter_m: float
    ) -> Dict[str, Any]:
        """
        Quantify the sub-frame and sealing components for an ACP (Aluminium
        Composite Panel) cladding system.

        Rule-of-thumb quantities per market standard:
          - Vertical T-runners  @ 600 mm c/c  → 1.80 m/m²
          - Horizontal L-angle  @ 800 mm c/c  → 1.20 m/m²
          - Fixing brackets     @ 4–5 per m²
          - Backer rod along all perimeter joints
          - Weather silicone: approx 6 m per 600 mL tube

        Parameters
        ----------
        net_sqm     : Net facade area of ACP panels [m²]
        perimeter_m : Total perimeter of all panel joints [m]

        Returns
        -------
        Dict with quantities of skeleton components.
        """
        return {
            "aluminum_t_profile_mtr": round(net_sqm * 1.80, 2),    # Vertical runners @ 600 mm
            "aluminum_l_angle_mtr":   round(net_sqm * 1.20, 2),    # Horizontal bracing @ 800 mm
            "fixing_brackets_pcs":    int(math.ceil(net_sqm * 4.5)), # Runner brackets
            "backer_rod_mtr":         round(perimeter_m, 2),
            "weather_silicone_tubes": int(math.ceil(perimeter_m / 6.0)),  # 6 m/tube
            "primer_m2":              round(net_sqm * 1.10, 2),     # 10% overage for waste
            "bond_tape_mtr":          round(net_sqm * 3.00, 2),     # Structural tape for cassette
        }

    # ------------------------------------------------------------------
    # 10. Mullion anchor kit  (retained from original, extended)
    # ------------------------------------------------------------------

    def generate_mullion_anchor_kit(self, mullion_count: int) -> Dict[str, Any]:
        """
        Calculate heavy-duty anchoring hardware quantities for curtain wall
        aluminium mullions fixed to a concrete / steel structure.

        Standard kit per mullion:
          - 4 × Hilti HSA M12 × 110 mm anchors (top + bottom base plates)
          - 1 × MS galvanised adjustable bracket (3-way adjustment ±30 mm)
          - 0.5 × Joint sleeve splice per mullion (every 2nd mullion has a splice)
          - 2 × EPDM setting blocks per mullion base
          - 1 × Anti-walk clip set per mullion

        Parameters
        ----------
        mullion_count : Number of curtain wall mullions

        Returns
        -------
        Dict with anchor kit quantities.
        """
        return {
            "hilti_anchor_bolts_M12":    int(mullion_count * 4),
            "ms_galvanized_brackets_pcs": int(mullion_count * 1),
            "joint_sleeves_pcs":          int(math.ceil(mullion_count * 0.5)),
            "epdm_setting_blocks_pcs":    int(mullion_count * 2),
            "anti_walk_clip_sets":        int(mullion_count * 1),
            "chemical_anchor_cartridges": int(math.ceil(mullion_count * 4 / 8)),  # 8 shots/cartridge
        }

    # ------------------------------------------------------------------
    # 11. Combined facade system check  (convenience wrapper)
    # ------------------------------------------------------------------

    def run_full_facade_check(
        self,
        panel_width_mm: float,
        panel_height_mm: float,
        mullion_span_mm: float,
        mullion_inertia_mm4: float,
        transom_span_mm: float,
        transom_inertia_mm4: float,
        glass_weight_kg: float,
        building_height_m: float = 30.0,
        terrain_category: int = 2,
        glass_type: str = "low_e_dgu",
        building_type: str = "commercial",
        orientation: str = "N",
    ) -> Dict[str, Any]:
        """
        Run a complete facade system check: wind → glass selection → mullion
        deflection → transom deflection → thermal compliance.

        Returns a consolidated report dict.
        """
        # Step 1: Wind
        wind = self.calculate_wind_pressure(
            building_height_m=building_height_m,
            terrain_category=terrain_category,
            zone="edge",
        )
        qp_kpa: float = wind["results"]["qp_kpa"]
        Wp_sls: float = wind["results"]["Wp_neg_sls_kpa"]  # suction governs for facade

        # Step 2: Glass selection
        glass = self.select_glass_thickness(
            panel_width_mm=panel_width_mm,
            panel_height_mm=panel_height_mm,
            wind_pressure_kpa=abs(Wp_sls),
            glass_type=glass_type,
            support_condition=4,
        )

        # Step 3: Mullion deflection
        mullion = self.check_mullion_deflection(
            span_mm=mullion_span_mm,
            moment_of_inertia_mm4=mullion_inertia_mm4,
            wind_pressure_kpa=abs(Wp_sls),
            tributary_width_mm=panel_width_mm,
        )

        # Step 4: Transom deflection
        transom = self.check_transom_deflection(
            span_mm=transom_span_mm,
            inertia_mm4=transom_inertia_mm4,
            glass_weight_kg=glass_weight_kg,
        )

        # Step 5: Thermal compliance
        thermal = self.check_thermal_compliance(
            u_value=glass["results"]["u_value_W_m2K"],
            shgc=glass["results"]["shgc"],
            vlt=glass["results"]["vlt"],
            building_type=building_type,
            orientation=orientation,
        )

        # Step 6: Thermal movement for mullion span
        delta_L: float = self.calculate_thermal_movement(mullion_span_mm)

        all_passed: bool = (
            mullion["results"]["passed"]
            and transom["results"]["passed"]
            and thermal["results"]["overall_passed"]
        )

        return {
            "summary": {
                "overall_status": "ALL CHECKS PASS" if all_passed else "ONE OR MORE CHECKS FAIL",
                "all_passed": all_passed,
            },
            "wind_check": wind,
            "glass_selection": glass,
            "mullion_deflection": mullion,
            "transom_deflection": transom,
            "thermal_compliance": thermal,
            "thermal_movement_mm": delta_L,
        }

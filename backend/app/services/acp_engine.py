"""
ACP Engine — Production-grade Aluminium Composite Panel fabrication, layout,
compliance and costing module for Madinat Al Saada Aluminium & Glass Works LLC.

Only stdlib imports: typing, math.
"""

import math
from typing import Dict, List, Any, Tuple, Optional


# ---------------------------------------------------------------------------
# Material catalogue
# ---------------------------------------------------------------------------

ACP_VARIANTS: Dict[str, Dict[str, Any]] = {
    "PE_4mm": {
        "thickness_mm": 4.0,
        "weight_kg_sqm": 5.5,
        "fire_class": "B2",
        "price_aed_sqm": 55.0,
        "description": "Standard polyethylene core, 4 mm",
    },
    "FR_4mm": {
        "thickness_mm": 4.0,
        "weight_kg_sqm": 5.8,
        "fire_class": "B1",
        "price_aed_sqm": 85.0,
        "description": "Fire-retardant mineral core, 4 mm",
    },
    "A2_4mm": {
        "thickness_mm": 4.0,
        "weight_kg_sqm": 7.2,
        "fire_class": "A2",
        "price_aed_sqm": 165.0,
        "description": "Non-combustible A2-rated core, 4 mm",
    },
    "A2_6mm": {
        "thickness_mm": 6.0,
        "weight_kg_sqm": 10.5,
        "fire_class": "A2",
        "price_aed_sqm": 220.0,
        "description": "Non-combustible A2-rated core, 6 mm",
    },
}

# Fire class hierarchy: higher index = better fire performance
_FIRE_CLASS_RANK: Dict[str, int] = {"B2": 0, "B1": 1, "A2": 2, "A1": 3}

# Raw sheet standard size (mm)
DEFAULT_RAW_SHEET: Tuple[int, int] = (1220, 2440)


class ACPEngine:
    """
    Precision Cladding Production Engine.

    Handles panel layout optimisation, 50 mm fold fabrication details,
    fire compliance checks, subframe design, sealant schedules, CNC routing
    programs, dead-load calculations and material yield tracking.

    Only `typing` and `math` are used as imports.
    """

    def __init__(self, fold_mm: float = 50.0) -> None:
        self.fold: float = fold_mm  # Standard return fold on all four sides (mm)

    # ------------------------------------------------------------------
    # 1. Panel Layout Optimisation
    # ------------------------------------------------------------------

    def optimize_panel_layout(
        self,
        facade_width_mm: float,
        facade_height_mm: float,
        max_panel_width: float = 1500.0,
        max_panel_height: float = 4000.0,
    ) -> Dict[str, Any]:
        """
        Determine the optimal panel grid for a facade opening.

        Returns the number of panels in each direction, each panel's net face
        size (excluding folds), the gross production size (including 4-side fold),
        total facade area, total ACP area ordered, and waste percentage.

        Strategy: minimise the number of cuts while staying within the maximum
        panel dimensions.  Equal panel widths are preferred; a narrower offcut
        column is appended when the facade width is not evenly divisible.
        """
        if facade_width_mm <= 0 or facade_height_mm <= 0:
            raise ValueError("Facade dimensions must be positive.")

        # --- Columns (width direction) ---
        cols_full = math.floor(facade_width_mm / max_panel_width)
        remainder_w = facade_width_mm - cols_full * max_panel_width

        if cols_full == 0:
            # Facade narrower than one max-width panel
            cols_full = 1
            panel_width = facade_width_mm
            has_narrow_col = False
            narrow_width = 0.0
        elif remainder_w < 1.0:
            panel_width = max_panel_width
            has_narrow_col = False
            narrow_width = 0.0
        else:
            panel_width = max_panel_width
            has_narrow_col = True
            narrow_width = remainder_w

        total_cols = cols_full + (1 if has_narrow_col else 0)

        # --- Rows (height direction) ---
        rows_full = math.floor(facade_height_mm / max_panel_height)
        remainder_h = facade_height_mm - rows_full * max_panel_height

        if rows_full == 0:
            rows_full = 1
            panel_height = facade_height_mm
            has_narrow_row = False
            narrow_height = 0.0
        elif remainder_h < 1.0:
            panel_height = max_panel_height
            has_narrow_row = False
            narrow_height = 0.0
        else:
            panel_height = max_panel_height
            has_narrow_row = True
            narrow_height = remainder_h

        total_rows = rows_full + (1 if has_narrow_row else 0)

        # --- Area accounting ---
        facade_area_sqm = (facade_width_mm * facade_height_mm) / 1_000_000.0

        # Build panel type list for area calc
        panel_types: List[Dict[str, Any]] = []

        def _add_panel_type(qty: int, w: float, h: float) -> None:
            gross_w = w + 2 * self.fold
            gross_h = h + 2 * self.fold
            panel_types.append(
                {
                    "qty": qty,
                    "net_width_mm": round(w, 1),
                    "net_height_mm": round(h, 1),
                    "gross_width_mm": round(gross_w, 1),
                    "gross_height_mm": round(gross_h, 1),
                    "net_area_sqm": round((w * h) / 1_000_000.0, 4),
                    "gross_area_sqm": round((gross_w * gross_h) / 1_000_000.0, 4),
                }
            )

        # Standard panels (full col × full row)
        std_qty = cols_full * rows_full
        _add_panel_type(std_qty, panel_width, panel_height)

        # Right-edge column panels (narrow width, full height)
        if has_narrow_col and rows_full > 0:
            _add_panel_type(rows_full, narrow_width, panel_height)

        # Bottom-row panels (full width, narrow height)
        if has_narrow_row and cols_full > 0:
            _add_panel_type(cols_full, panel_width, narrow_height)

        # Corner panel (narrow width, narrow height)
        if has_narrow_col and has_narrow_row:
            _add_panel_type(1, narrow_width, narrow_height)

        total_panels = sum(pt["qty"] for pt in panel_types)
        ordered_area_sqm = sum(pt["qty"] * pt["gross_area_sqm"] for pt in panel_types)
        waste_pct = round(
            (ordered_area_sqm - facade_area_sqm) / ordered_area_sqm * 100.0, 2
        )

        return {
            "grid": {
                "total_cols": total_cols,
                "total_rows": total_rows,
                "total_panels": total_panels,
            },
            "panel_types": panel_types,
            "facade_area_sqm": round(facade_area_sqm, 3),
            "ordered_gross_area_sqm": round(ordered_area_sqm, 3),
            "waste_pct": waste_pct,
            "fold_mm": self.fold,
            "status": "optimised",
        }

    # ------------------------------------------------------------------
    # 2. 50 mm Fold — V-groove routing & return fold geometry
    # ------------------------------------------------------------------

    def get_fold_details(
        self,
        panel_width_mm: float,
        panel_height_mm: float,
        acp_type: str = "PE_4mm",
    ) -> Dict[str, Any]:
        """
        Full 4-side fold-return geometry and V-groove routing parameters.

        V-groove depth = thickness - 0.3 mm (leaves 0.3 mm aluminium skin).
        Returns fold coordinates in panel-local space (origin = bottom-left of
        gross sheet, x→right, y→up).
        """
        if acp_type not in ACP_VARIANTS:
            raise ValueError(f"Unknown ACP type '{acp_type}'. Choose from {list(ACP_VARIANTS)}")

        variant = ACP_VARIANTS[acp_type]
        thickness = variant["thickness_mm"]
        groove_depth = round(thickness - 0.3, 2)  # mm, keep 0.3 mm skin intact

        f = self.fold  # fold return dimension (mm)

        # Gross sheet dimensions
        gross_w = panel_width_mm + 2 * f
        gross_h = panel_height_mm + 2 * f

        # V-groove positions (centreline of groove, measured from gross sheet edge)
        # Left groove:   x = f
        # Right groove:  x = gross_w - f
        # Bottom groove: y = f
        # Top groove:    y = gross_h - f

        grooves = [
            {
                "side": "left",
                "orientation": "vertical",
                "x_start": f,
                "y_start": 0.0,
                "x_end": f,
                "y_end": gross_h,
                "depth_mm": groove_depth,
            },
            {
                "side": "right",
                "orientation": "vertical",
                "x_start": gross_w - f,
                "y_start": 0.0,
                "x_end": gross_w - f,
                "y_end": gross_h,
                "depth_mm": groove_depth,
            },
            {
                "side": "bottom",
                "orientation": "horizontal",
                "x_start": 0.0,
                "y_start": f,
                "x_end": gross_w,
                "y_end": f,
                "depth_mm": groove_depth,
            },
            {
                "side": "top",
                "orientation": "horizontal",
                "x_start": 0.0,
                "y_start": gross_h - f,
                "x_end": gross_w,
                "y_end": gross_h - f,
                "depth_mm": groove_depth,
            },
        ]

        # Fold return pattern: the four flanges after bending
        # Each flange is described by which edge it belongs to, its length, and
        # the net face dimension it borders.
        fold_pattern = [
            {"side": "left",   "flange_width_mm": f, "runs_along_mm": gross_h},
            {"side": "right",  "flange_width_mm": f, "runs_along_mm": gross_h},
            {"side": "bottom", "flange_width_mm": f, "runs_along_mm": gross_w},
            {"side": "top",    "flange_width_mm": f, "runs_along_mm": gross_w},
        ]

        # Corner notch squares (cut before folding to avoid double-thickness corners)
        corner_notch = {
            "size_mm": f,
            "count": 4,
            "description": f"{f}×{f} mm corner squares removed prior to folding",
        }

        return {
            "acp_type": acp_type,
            "thickness_mm": thickness,
            "groove_depth_mm": groove_depth,
            "remaining_skin_mm": 0.3,
            "net_panel_width_mm": panel_width_mm,
            "net_panel_height_mm": panel_height_mm,
            "gross_sheet_width_mm": round(gross_w, 1),
            "gross_sheet_height_mm": round(gross_h, 1),
            "fold_mm": f,
            "v_grooves": grooves,
            "fold_pattern": fold_pattern,
            "corner_notch": corner_notch,
        }

    # ------------------------------------------------------------------
    # 3. Fire Compliance — UAE Civil Defence rules
    # ------------------------------------------------------------------

    def check_fire_compliance(
        self,
        building_height_m: float,
        building_type: str,
        acp_type: str,
    ) -> Dict[str, Any]:
        """
        Check whether the specified ACP type meets UAE Civil Defence / DM
        cladding fire requirements.

        Rules applied:
          - All buildings:            B2 minimum
          - Height > 15 m:           B1 minimum
          - Height > 28 m:           A2 minimum
          - Escape routes / stairs:  A2 always (regardless of height)
          - Hospitals, schools:      A2 always
          - Building type 'escape'   forces A2
        """
        if acp_type not in ACP_VARIANTS:
            raise ValueError(f"Unknown ACP type '{acp_type}'.")

        provided_class = ACP_VARIANTS[acp_type]["fire_class"]
        provided_rank = _FIRE_CLASS_RANK[provided_class]

        # Determine minimum required class
        high_risk_types = {"hospital", "school", "escape", "staircase", "refuge"}
        bt_lower = building_type.lower().strip()

        if bt_lower in high_risk_types:
            required_class = "A2"
            reason = f"Building type '{building_type}' mandates A2 per UAE Civil Defence"
        elif building_height_m > 28.0:
            required_class = "A2"
            reason = f"Height {building_height_m} m > 28 m: UAE CD requires A2"
        elif building_height_m > 15.0:
            required_class = "B1"
            reason = f"Height {building_height_m} m > 15 m: UAE CD requires minimum B1"
        else:
            required_class = "B2"
            reason = f"Height {building_height_m} m ≤ 15 m: B2 acceptable"

        required_rank = _FIRE_CLASS_RANK[required_class]
        compliant = provided_rank >= required_rank

        # Recommend upgrade path if non-compliant
        upgrade: Optional[str] = None
        if not compliant:
            for variant_name, variant_data in ACP_VARIANTS.items():
                if _FIRE_CLASS_RANK[variant_data["fire_class"]] >= required_rank:
                    upgrade = variant_name
                    break

        return {
            "compliant": compliant,
            "acp_type": acp_type,
            "provided_fire_class": provided_class,
            "required_fire_class": required_class,
            "building_height_m": building_height_m,
            "building_type": building_type,
            "reason": reason,
            "recommended_upgrade": upgrade if not compliant else None,
            "uae_standard": "UAE Civil Defence Fire Code + Dubai Municipality Circular 198",
        }

    # ------------------------------------------------------------------
    # 4. Subframe Calculation
    # ------------------------------------------------------------------

    def calculate_subframe(
        self,
        panel_layout: Dict[str, Any],
        building_height_m: float,
        wind_pressure_kpa: float,
    ) -> Dict[str, Any]:
        """
        Design the ACP subframe (vertical runners, horizontal rails, brackets).

        Vertical runner spacing: linearly interpolated between 600 mm at
        0.5 kPa wind and 400 mm at 2.0 kPa+ wind, capped at 400–600 mm range.

        Bracket type: L-bracket for cavity ≤ 100 mm, Z-bracket otherwise.
        Bracket spacing along runners: 1200 mm (standard), reduced to 900 mm
        above 15 m height.

        Returns quantities in linear metres (runners, rails) and pieces
        (brackets, fixings) together with a materials summary.
        """
        facade_area_sqm: float = panel_layout.get("facade_area_sqm", 0.0)
        if facade_area_sqm <= 0:
            raise ValueError("panel_layout must contain a positive 'facade_area_sqm'.")

        # Derive approximate facade width and height from panel count / types
        grid = panel_layout.get("grid", {})
        total_cols: int = grid.get("total_cols", 1)
        total_rows: int = grid.get("total_rows", 1)

        # Fallback: derive dimensions from area (assume square-ish)
        panel_types = panel_layout.get("panel_types", [])
        if panel_types:
            # Sum widths of first row panels
            first_row_panels = [pt for pt in panel_types if pt.get("qty", 0) >= total_rows]
            facade_width_m = sum(
                pt["net_width_mm"] / 1000.0 for pt in first_row_panels
            ) if first_row_panels else math.sqrt(facade_area_sqm)
            facade_height_m = facade_area_sqm / facade_width_m if facade_width_m > 0 else math.sqrt(facade_area_sqm)
        else:
            facade_width_m = math.sqrt(facade_area_sqm)
            facade_height_m = facade_area_sqm / facade_width_m

        # --- Vertical runner spacing (mm) ---
        wind_kpa = max(0.5, min(wind_pressure_kpa, 2.0))
        # Linear interpolation: 600 mm @ 0.5 kPa → 400 mm @ 2.0 kPa
        runner_spacing_mm = 600.0 - (wind_kpa - 0.5) / 1.5 * 200.0
        runner_spacing_mm = round(max(400.0, min(600.0, runner_spacing_mm)), 0)

        # Number of vertical runners across facade width
        num_runners = math.ceil(facade_width_m * 1000.0 / runner_spacing_mm) + 1
        runner_length_each_m = building_height_m
        total_runner_lm = round(num_runners * runner_length_each_m, 2)

        # --- Horizontal rail spacing (mm) ---
        # Rails at each panel joint — derive from panel heights in layout
        if panel_types:
            # Collect unique net panel heights
            heights_mm = list({pt["net_height_mm"] for pt in panel_types})
            rail_spacing_mm = min(heights_mm)  # most frequent joint spacing
        else:
            rail_spacing_mm = 1200.0  # default

        num_rail_rows = math.ceil(building_height_m * 1000.0 / rail_spacing_mm) + 1
        rail_length_each_m = facade_width_m
        total_rail_lm = round(num_rail_rows * rail_length_each_m, 2)

        # --- Bracket spacing along runners ---
        bracket_spacing_mm = 900.0 if building_height_m > 15.0 else 1200.0

        # Assumed cavity depth: 100 mm standard for ACP facades
        cavity_depth_mm = 100.0
        bracket_type = "L-bracket" if cavity_depth_mm <= 100.0 else "Z-bracket"

        # Brackets per runner
        brackets_per_runner = math.ceil(runner_length_each_m * 1000.0 / bracket_spacing_mm) + 1
        total_brackets = num_runners * brackets_per_runner

        # Chemical anchors: 2 per bracket into concrete/steel
        total_anchors = total_brackets * 2

        # --- Self-weight of subframe per sqm ---
        # Aluminium runners ~1.2 kg/lm, rails ~0.9 kg/lm, brackets ~0.35 kg each
        subframe_kg = (
            total_runner_lm * 1.2
            + total_rail_lm * 0.9
            + total_brackets * 0.35
        )
        subframe_kg_sqm = round(subframe_kg / facade_area_sqm, 2) if facade_area_sqm > 0 else 0.0

        return {
            "wind_pressure_kpa": wind_pressure_kpa,
            "runner_spacing_mm": runner_spacing_mm,
            "bracket_type": bracket_type,
            "cavity_depth_mm": cavity_depth_mm,
            "vertical_runners": {
                "count": num_runners,
                "length_each_m": round(runner_length_each_m, 2),
                "total_lm": total_runner_lm,
                "profile": "65×35×3 mm Aluminium T/C-section",
            },
            "horizontal_rails": {
                "count": num_rail_rows,
                "length_each_m": round(rail_length_each_m, 2),
                "total_lm": total_rail_lm,
                "profile": "40×40×3 mm Aluminium SHS",
            },
            "brackets": {
                "type": bracket_type,
                "bracket_spacing_mm": bracket_spacing_mm,
                "brackets_per_runner": brackets_per_runner,
                "total_pcs": total_brackets,
                "profile": "3 mm galvanised steel, hot-dip zinc coated",
            },
            "chemical_anchors": {
                "total_pcs": total_anchors,
                "type": "M10×100 mm epoxy anchor",
            },
            "subframe_weight_kg": round(subframe_kg, 1),
            "subframe_kg_per_sqm": subframe_kg_sqm,
            "standard": "BS 8298-4 / ETAG 034 Part 2",
        }

    # ------------------------------------------------------------------
    # 5. Sealant Quantities
    # ------------------------------------------------------------------

    def calculate_sealant_quantities(
        self,
        panel_layout: Dict[str, Any],
        joint_width_mm: float = 12.0,
    ) -> Dict[str, Any]:
        """
        Calculate sealant and backer rod quantities.

        Joint sealant depth = 8 mm (standard weatherseal ratio 1.5:1 width:depth).
        Backer rod diameter = joint_width + 2 mm (compression fit).
        Fire sealant applied at every floor line (assumed every 3 m of height).

        Returns volumes in litres, lengths in linear metres, and approximate
        cost at market rates.
        """
        facade_area_sqm: float = panel_layout.get("facade_area_sqm", 0.0)
        if facade_area_sqm <= 0:
            raise ValueError("panel_layout must contain a positive 'facade_area_sqm'.")

        grid = panel_layout.get("grid", {})
        total_cols: int = max(1, grid.get("total_cols", 1))
        total_rows: int = max(1, grid.get("total_rows", 1))

        # Linear joint length (mm converted to m)
        # Vertical joints: (total_cols - 1) joints × facade_height
        # Horizontal joints: (total_rows - 1) joints × facade_width
        panel_types = panel_layout.get("panel_types", [])
        if panel_types:
            std = panel_types[0]
            facade_width_m = (std["net_width_mm"] * total_cols) / 1000.0
            facade_height_m = (std["net_height_mm"] * total_rows) / 1000.0
        else:
            facade_width_m = math.sqrt(facade_area_sqm)
            facade_height_m = facade_area_sqm / facade_width_m

        vertical_joints_lm = (total_cols - 1) * facade_height_m
        horizontal_joints_lm = (total_rows - 1) * facade_width_m
        perimeter_seal_lm = 2 * (facade_width_m + facade_height_m)
        total_joint_lm = vertical_joints_lm + horizontal_joints_lm + perimeter_seal_lm

        # Sealant volume: cross-section = width × depth (mm²) → m² per lm
        sealant_depth_mm = joint_width_mm * 0.5  # depth:width = 0.5 for movement joints
        sealant_depth_mm = max(6.0, min(sealant_depth_mm, 10.0))  # clamp 6–10 mm
        sealant_xsec_m2 = (joint_width_mm / 1000.0) * (sealant_depth_mm / 1000.0)
        sealant_volume_l = round(total_joint_lm * sealant_xsec_m2 * 1000.0, 2)  # litres
        # Standard 600 ml sausage cartridge
        sealant_cartridges = math.ceil(sealant_volume_l / 0.6)

        # Backer rod: diameter = joint_width + 2 mm; supplied in 30 m coils
        backer_rod_dia_mm = joint_width_mm + 2.0
        backer_rod_lm = round(total_joint_lm * 1.05, 2)  # 5% waste
        backer_rod_coils = math.ceil(backer_rod_lm / 30.0)

        # Fire sealant at floor lines (every 3 m of height)
        num_floor_lines = max(0, math.floor(facade_height_m / 3.0) - 1)
        fire_sealant_lm = round(num_floor_lines * facade_width_m, 2)
        # Fire sealant is 20 mm wide × 20 mm deep intumescent strip
        fire_seal_xsec_m2 = 0.02 * 0.02
        fire_seal_volume_l = round(fire_sealant_lm * fire_seal_xsec_m2 * 1000.0, 2)
        fire_seal_cartridges = math.ceil(fire_seal_volume_l / 0.4)  # 400 ml tubes

        # Approximate costs (AED)
        weather_silicone_cost_aed = round(sealant_cartridges * 18.0, 2)   # 18 AED/600 ml
        backer_rod_cost_aed = round(backer_rod_lm * 0.80, 2)               # 0.80 AED/lm
        fire_sealant_cost_aed = round(fire_seal_cartridges * 55.0, 2)      # 55 AED/400 ml

        return {
            "joint_width_mm": joint_width_mm,
            "joint_depth_mm": round(sealant_depth_mm, 1),
            "total_joint_lm": round(total_joint_lm, 2),
            "vertical_joints_lm": round(vertical_joints_lm, 2),
            "horizontal_joints_lm": round(horizontal_joints_lm, 2),
            "perimeter_seal_lm": round(perimeter_seal_lm, 2),
            "weather_silicone": {
                "volume_litres": sealant_volume_l,
                "cartridges_600ml": sealant_cartridges,
                "cost_aed": weather_silicone_cost_aed,
                "specification": "Dow Corning 791 or equal neutral-cure silicone",
            },
            "backer_rod": {
                "diameter_mm": backer_rod_dia_mm,
                "length_lm": backer_rod_lm,
                "coils_30m": backer_rod_coils,
                "cost_aed": backer_rod_cost_aed,
                "material": "Closed-cell polyethylene foam",
            },
            "fire_sealant": {
                "floor_lines": num_floor_lines,
                "length_lm": fire_sealant_lm,
                "volume_litres": fire_seal_volume_l,
                "cartridges_400ml": fire_seal_cartridges,
                "cost_aed": fire_sealant_cost_aed,
                "specification": "Intumescent fire sealant, 2-hour rating",
            },
            "total_sealant_cost_aed": round(
                weather_silicone_cost_aed + backer_rod_cost_aed + fire_sealant_cost_aed, 2
            ),
        }

    # ------------------------------------------------------------------
    # 6. CNC Routing Program
    # ------------------------------------------------------------------

    def generate_routing_program(
        self,
        panel_width_mm: float,
        panel_height_mm: float,
        fold_mm: Optional[float] = None,
        groove_depth_mm: Optional[float] = None,
        acp_type: str = "PE_4mm",
    ) -> Dict[str, Any]:
        """
        Generate an ordered CNC router operation sequence for a single panel.

        Operations (in order):
          1. Load / datum set — origin at bottom-left of gross sheet
          2. Corner notch cuts (4 off) — square pocket f×f at each corner
          3. V-groove routing — 4 passes (left, right, bottom, top)
          4. Unload / flip — fold bending (off-machine, noted)

        All coordinates in mm in gross-sheet space.
        Feed rates are indicative; operator should optimise per material.
        """
        f = fold_mm if fold_mm is not None else self.fold

        if acp_type not in ACP_VARIANTS:
            raise ValueError(f"Unknown ACP type '{acp_type}'.")
        thickness = ACP_VARIANTS[acp_type]["thickness_mm"]
        gd = groove_depth_mm if groove_depth_mm is not None else round(thickness - 0.3, 2)

        gross_w = panel_width_mm + 2 * f
        gross_h = panel_height_mm + 2 * f

        operations: List[Dict[str, Any]] = []
        op_no = 1

        # --- Op 1: Setup ---
        operations.append({
            "op": op_no,
            "description": "Datum set — clamp sheet, zero at bottom-left corner",
            "tool": None,
            "x": 0.0,
            "y": 0.0,
            "z_depth": 0.0,
            "feed_mm_min": None,
        })
        op_no += 1

        # --- Op 2–5: Corner notch pockets (f × f) ---
        corners = [
            ("bottom-left",  0.0,         0.0),
            ("bottom-right", gross_w - f, 0.0),
            ("top-left",     0.0,         gross_h - f),
            ("top-right",    gross_w - f, gross_h - f),
        ]
        for label, cx, cy in corners:
            operations.append({
                "op": op_no,
                "description": f"Corner notch pocket — {label}",
                "tool": "12 mm straight bit",
                "start_x": cx,
                "start_y": cy,
                "pocket_width": f,
                "pocket_height": f,
                "z_depth": thickness,  # full through-cut (aluminium skins + core)
                "feed_mm_min": 4000,
                "spindle_rpm": 18000,
            })
            op_no += 1

        # --- Op 6–9: V-groove passes ---
        groove_passes = [
            ("left",   f,          0.0,     f,          gross_h),
            ("right",  gross_w-f,  0.0,     gross_w-f,  gross_h),
            ("bottom", 0.0,        f,       gross_w,    f),
            ("top",    0.0,        gross_h-f, gross_w,  gross_h-f),
        ]
        for side, x1, y1, x2, y2 in groove_passes:
            operations.append({
                "op": op_no,
                "description": f"V-groove routing — {side} edge",
                "tool": "V-bit 135° (groove for ACP fold)",
                "x_start": x1,
                "y_start": y1,
                "x_end": x2,
                "y_end": y2,
                "z_depth": gd,
                "feed_mm_min": 3000,
                "spindle_rpm": 18000,
                "passes": 1,
            })
            op_no += 1

        # --- Op 10: Unload ---
        operations.append({
            "op": op_no,
            "description": "Unload panel — transfer to press-brake for 4-side folding",
            "tool": None,
            "x": None,
            "y": None,
            "z_depth": None,
            "feed_mm_min": None,
        })

        return {
            "panel_id": f"{int(panel_width_mm)}x{int(panel_height_mm)}-{acp_type}",
            "gross_sheet_width_mm": gross_w,
            "gross_sheet_height_mm": gross_h,
            "fold_mm": f,
            "groove_depth_mm": gd,
            "acp_type": acp_type,
            "acp_thickness_mm": thickness,
            "total_operations": len(operations),
            "operations": operations,
            "notes": [
                "Coordinate origin: bottom-left corner of gross sheet.",
                "Bending sequence after routing: bottom → top → left → right.",
                f"V-groove leaves {round(thickness - gd, 2)} mm skin for clean fold.",
                "Verify sheet orientation (coated face up) before clamping.",
            ],
        }

    # ------------------------------------------------------------------
    # 7. Dead Load Calculation
    # ------------------------------------------------------------------

    def calculate_dead_load(
        self,
        panel_layout: Dict[str, Any],
        acp_type: str,
        subframe_weight_kg_sqm: float = 3.5,
    ) -> Dict[str, Any]:
        """
        Calculate the total and per-bracket dead load imposed on the structure.

        Loads include: ACP panel self-weight + subframe weight.
        A 15 % tributary area factor is applied per bracket (conservative).

        Returns load per bracket in kN and total system dead load in kN.
        """
        if acp_type not in ACP_VARIANTS:
            raise ValueError(f"Unknown ACP type '{acp_type}'.")

        facade_area_sqm: float = panel_layout.get("facade_area_sqm", 0.0)
        if facade_area_sqm <= 0:
            raise ValueError("panel_layout must contain a positive 'facade_area_sqm'.")

        acp_kg_sqm = ACP_VARIANTS[acp_type]["weight_kg_sqm"]
        total_acp_kg = round(acp_kg_sqm * facade_area_sqm, 2)
        total_subframe_kg = round(subframe_weight_kg_sqm * facade_area_sqm, 2)
        total_system_kg = round(total_acp_kg + total_subframe_kg, 2)

        # Total dead load in kN (g = 9.81 m/s²)
        g = 9.81
        total_acp_kN = round(total_acp_kg * g / 1000.0, 3)
        total_subframe_kN = round(total_subframe_kg * g / 1000.0, 3)
        total_system_kN = round(total_system_kg * g / 1000.0, 3)

        # Per-bracket load estimate
        grid = panel_layout.get("grid", {})
        # Use subframe bracket count if available; estimate from area otherwise
        total_panels = grid.get("total_panels", 0)
        # Typical 2 brackets per panel per vertical row → 4 per panel (4 corners)
        estimated_brackets = max(1, total_panels * 4)

        load_per_bracket_kN = round(total_system_kN / estimated_brackets, 4)
        tributary_area_per_bracket_sqm = round(facade_area_sqm / estimated_brackets * 1.15, 4)

        # kPa surface loading
        surface_load_kpa = round(total_system_kN / facade_area_sqm, 3)

        return {
            "acp_type": acp_type,
            "acp_kg_sqm": acp_kg_sqm,
            "subframe_kg_sqm": subframe_weight_kg_sqm,
            "total_combined_kg_sqm": round(acp_kg_sqm + subframe_weight_kg_sqm, 2),
            "facade_area_sqm": facade_area_sqm,
            "acp_total_kg": total_acp_kg,
            "subframe_total_kg": total_subframe_kg,
            "total_system_kg": total_system_kg,
            "acp_dead_load_kN": total_acp_kN,
            "subframe_dead_load_kN": total_subframe_kN,
            "total_dead_load_kN": total_system_kN,
            "estimated_brackets": estimated_brackets,
            "load_per_bracket_kN": load_per_bracket_kN,
            "tributary_area_per_bracket_sqm": tributary_area_per_bracket_sqm,
            "surface_load_kpa": surface_load_kpa,
            "standard": "BS EN 1991-1-1 (Eurocode 1) — Permanent actions",
        }

    # ------------------------------------------------------------------
    # 8. Material Yield Tracking
    # ------------------------------------------------------------------

    def calculate_material_yield(
        self,
        panel_layout: Dict[str, Any],
        raw_sheet_size: Tuple[float, float] = DEFAULT_RAW_SHEET,
        acp_type: str = "PE_4mm",
    ) -> Dict[str, Any]:
        """
        Calculate how many standard raw sheets are required and the resulting
        material yield and scrap figures.

        Each gross panel is nested into raw sheets individually (no shared-sheet
        nesting — conservative, suitable for pre-painted panels where grain
        direction must be maintained).

        raw_sheet_size: (width_mm, height_mm) of the standard coil/sheet.
        """
        if acp_type not in ACP_VARIANTS:
            raise ValueError(f"Unknown ACP type '{acp_type}'.")

        sheet_w, sheet_h = raw_sheet_size
        sheet_area_sqm = (sheet_w * sheet_h) / 1_000_000.0

        panel_types = panel_layout.get("panel_types", [])
        if not panel_types:
            raise ValueError("panel_layout must contain at least one entry in 'panel_types'.")

        total_sheets = 0
        total_gross_area_sqm = 0.0
        breakdown: List[Dict[str, Any]] = []

        for pt in panel_types:
            qty = pt["qty"]
            g_w = pt["gross_width_mm"]
            g_h = pt["gross_sheet_height_mm"] if "gross_sheet_height_mm" in pt else pt["gross_height_mm"]

            # Panels per sheet: how many gross panels fit on one raw sheet?
            # Try both orientations; pick whichever fits more.
            def _panels_per_sheet(pw: float, ph: float, sw: float, sh: float) -> int:
                cols = math.floor(sw / pw)
                rows = math.floor(sh / ph)
                return max(0, cols * rows)

            orient_normal = _panels_per_sheet(g_w, g_h, sheet_w, sheet_h)
            orient_rotated = _panels_per_sheet(g_h, g_w, sheet_w, sheet_h)
            pps = max(orient_normal, orient_rotated, 1)  # at least 1 panel per sheet

            sheets_for_type = math.ceil(qty / pps)
            gross_area = round(qty * pt["gross_area_sqm"], 4)

            breakdown.append({
                "net_width_mm": pt["net_width_mm"],
                "net_height_mm": pt["net_height_mm"],
                "gross_width_mm": g_w,
                "gross_height_mm": g_h,
                "qty_panels": qty,
                "panels_per_sheet": pps,
                "sheets_required": sheets_for_type,
                "gross_area_sqm": gross_area,
            })

            total_sheets += sheets_for_type
            total_gross_area_sqm += gross_area

        ordered_sheet_area_sqm = round(total_sheets * sheet_area_sqm, 3)
        yield_pct = round(total_gross_area_sqm / ordered_sheet_area_sqm * 100.0, 2)
        scrap_sqm = round(ordered_sheet_area_sqm - total_gross_area_sqm, 3)

        price_per_sqm = ACP_VARIANTS[acp_type]["price_aed_sqm"]
        scrap_value_aed = round(scrap_sqm * price_per_sqm * 0.15, 2)  # 15% recovery on scrap

        return {
            "acp_type": acp_type,
            "raw_sheet_size_mm": {"width": sheet_w, "height": sheet_h},
            "raw_sheet_area_sqm": round(sheet_area_sqm, 4),
            "total_sheets_required": total_sheets,
            "ordered_sheet_area_sqm": ordered_sheet_area_sqm,
            "total_gross_panel_area_sqm": round(total_gross_area_sqm, 3),
            "yield_pct": yield_pct,
            "scrap_sqm": scrap_sqm,
            "scrap_recovery_value_aed": scrap_value_aed,
            "material_cost_aed": round(ordered_sheet_area_sqm * price_per_sqm, 2),
            "breakdown_by_panel_type": breakdown,
            "notes": [
                "Grain direction maintained — no cross-grain nesting applied.",
                "Scrap recovery rate assumed at 15% of material price.",
                f"Raw sheet: {sheet_w}×{sheet_h} mm ({round(sheet_area_sqm,4)} sqm).",
            ],
        }

    # ------------------------------------------------------------------
    # Legacy compatibility: get_production_specs (kept from original stub)
    # ------------------------------------------------------------------

    def get_production_specs(
        self, width: float, height: float, acp_type: str = "PE_4mm"
    ) -> Dict[str, Any]:
        """
        Backwards-compatible wrapper.  Returns a summary production spec sheet
        for a single panel.
        """
        if acp_type not in ACP_VARIANTS:
            acp_type = "PE_4mm"
        variant = ACP_VARIANTS[acp_type]

        cas_w = width + 2 * self.fold
        cas_h = height + 2 * self.fold
        area_sqm = (cas_w * cas_h) / 1_000_000.0

        frame_mtr = round(area_sqm * 1.5, 2)
        brackets = math.ceil(area_sqm * 2)

        return {
            "production_size": {"width": round(cas_w, 1), "height": round(cas_h, 1)},
            "net_face_size": {"width": width, "height": height},
            "gross_area_sqm": round(area_sqm, 4),
            "net_weight_kg": round(area_sqm * variant["weight_kg_sqm"], 2),
            "acp_type": acp_type,
            "fire_class": variant["fire_class"],
            "price_aed_sqm": variant["price_aed_sqm"],
            "panel_cost_aed": round(area_sqm * variant["price_aed_sqm"], 2),
            "carrier_frame": {
                "t_profile_mtr": frame_mtr,
                "l_brackets_pcs": brackets,
            },
            "status": "Production_Optimised",
        }

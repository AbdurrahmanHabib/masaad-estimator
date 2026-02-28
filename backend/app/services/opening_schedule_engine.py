"""Opening schedule engine — extracts and structures all facade openings from DWG.

Supports Glazetech thermal break sliding systems:
- Glazetech Lift and Slide Thermal Break (GT-LSTB)
- Glazetech Slim Sliding System (GT-SS)
- Glazetech Eco 500 Sliding Thermal Break (GT-E500TB)

Supplier: Elite Extrusion L.L.C, RAK, UAE
"""
import re
import logging
from dataclasses import dataclass, field
from typing import Optional
from app.services.scope_engine import ELEVATION_MAP, FLOOR_ABBREVIATIONS

logger = logging.getLogger("masaad-opening-schedule")

# Standard sightline deductions per system type (mm per side)
SIGHTLINE_DEDUCTIONS = {
    "Curtain Wall (Stick)": {"horizontal": 50, "vertical": 60},
    "Window - Casement": {"horizontal": 35, "vertical": 40},
    "Window - Fixed": {"horizontal": 30, "vertical": 30},
    "Window - Sliding": {"horizontal": 40, "vertical": 40},
    "Window - Sliding (Lift & Slide TB)": {"horizontal": 55, "vertical": 50},
    "Window - Sliding (Eco 500 TB)": {"horizontal": 40, "vertical": 40},
    "Door - Single Swing": {"horizontal": 40, "vertical": 40},
    "Door - Double Swing": {"horizontal": 40, "vertical": 40},
    "Door - Sliding": {"horizontal": 55, "vertical": 50},
    "Structural Glazing": {"horizontal": 15, "vertical": 15},
    "Shopfront": {"horizontal": 50, "vertical": 60},
    "Glass Railing": {"horizontal": 20, "vertical": 0},
    "default": {"horizontal": 35, "vertical": 35},
}

# Glass density kg/m2 per mm of thickness
GLASS_DENSITY_KG_M2_PER_MM = 2.5


# Aluminum weight per LM (kg/m) by system type — from Glazetech catalog specs
ALUMINUM_WEIGHT_NORMS = {
    "Curtain Wall (Stick)": 12.5,    # kg/sqm of facade area
    "Curtain Wall (Unitised)": 14.0,
    "Window - Casement": 4.8,        # kg/lm of perimeter
    "Window - Fixed": 3.5,
    "Window - Sliding": 4.2,         # Glazetech Slim Sliding
    "Window - Sliding (Lift & Slide TB)": 7.8,  # Glazetech Lift & Slide TB
    "Window - Sliding (Eco 500 TB)": 5.2,       # Glazetech Eco 500 TB
    "Door - Single Swing": 6.5,
    "Door - Double Swing": 6.5,
    "Door - Sliding": 7.8,           # Same as Lift & Slide
    "Structural Glazing": 8.0,
    "Shopfront": 10.0,
    "Glass Railing": 3.5,
    "default": 5.0,
}

# Gasket length multiplier (lm of gasket per lm of opening perimeter)
GASKET_MULTIPLIERS = {
    "Curtain Wall (Stick)": 2.0,     # inner + outer gasket run
    "Curtain Wall (Unitised)": 2.2,
    "Window - Casement": 1.5,
    "Window - Fixed": 1.0,
    "Window - Sliding": 1.8,         # Glazetech Slim Sliding
    "Window - Sliding (Lift & Slide TB)": 2.2,  # Glazetech Lift & Slide TB — extra seals
    "Window - Sliding (Eco 500 TB)": 2.0,       # Glazetech Eco 500 TB
    "Door - Single Swing": 1.5,
    "Door - Double Swing": 1.5,
    "Door - Sliding": 2.2,
    "Structural Glazing": 0.5,       # minimal — silicone joint
    "Shopfront": 1.8,
    "Glass Railing": 0.5,
    "default": 1.5,
}

# Hardware sets per opening (number of hardware units)
HARDWARE_SETS_NORMS = {
    "Curtain Wall (Stick)": 0,        # no operable hardware
    "Curtain Wall (Unitised)": 0,
    "Window - Casement": 1,           # 1 handle + 1 hinge pair + 1 lock
    "Window - Fixed": 0,
    "Window - Sliding": 1,            # 1 roller set + 1 crescent lock
    "Window - Sliding (Lift & Slide TB)": 1,  # 1 lift & slide roller set + 1 lock
    "Window - Sliding (Eco 500 TB)": 1,       # 1 roller set + TB lock
    "Door - Single Swing": 1,         # 1 handle set + 1 closer + 1 hinge set + 1 lock
    "Door - Double Swing": 2,         # 2× hardware sets
    "Door - Sliding": 1,              # Lift & slide hardware
    "Structural Glazing": 0,
    "Shopfront": 1,
    "Glass Railing": 0,
    "default": 0,
}

# Glass specification for thermal break systems (DGU required for TB)
GLASS_SPEC_BY_SYSTEM = {
    "Window - Sliding (Lift & Slide TB)": {
        "type": "DGU 6+16Ar+6mm Low-E Tempered",
        "thickness_mm": 28,
        "description": "Double Glazed Unit, 6mm Low-E outer + 16mm Argon + 6mm Clear Tempered inner",
    },
    "Window - Sliding": {
        "type": "6mm Clear Tempered",
        "thickness_mm": 6,
        "description": "6mm Clear Toughened Safety Glass (Glazetech Slim Sliding)",
    },
    "Window - Sliding (Eco 500 TB)": {
        "type": "DGU 6+12Ar+6mm Low-E Tempered",
        "thickness_mm": 24,
        "description": "Double Glazed Unit, 6mm Low-E outer + 12mm Argon + 6mm Clear Tempered inner",
    },
    "Door - Sliding": {
        "type": "DGU 8+16Ar+8mm Low-E Tempered",
        "thickness_mm": 32,
        "description": "Double Glazed Unit, 8mm Low-E outer + 16mm Argon + 8mm Clear Tempered inner",
    },
    "Glass Railing": {
        "type": "12mm Clear Tempered Laminated",
        "thickness_mm": 12,
        "description": "12mm Clear Toughened Laminated Safety Glass",
    },
}

# Facade distribution rules for typical residential tower
# When DXF has 4 named facades, distribute openings across them
FACADE_DISTRIBUTION = {
    "FRONT": 0.30,   # 30% of openings on front facade
    "BACK": 0.30,    # 30% on back
    "LEFT": 0.20,    # 20% on left
    "RIGHT": 0.20,   # 20% on right
}


# ── Panel Subdivision Engine ──────────────────────────────────────────────────
# Breaks each opening into individual panels (Fixed/Sliding) based on system rules.
# Calculates real glass pane sizes, weights, and profile cut lengths per panel.

# Panel subdivision rules per Glazetech system
# Configuration notation: F = Fixed, S = Sliding, e.g. "F-S-S" = 1 fixed + 2 sliding
PANEL_SUBDIVISION_RULES = {
    "Window - Sliding (Lift & Slide TB)": {
        # Lift & Slide: max sash width 3200mm. For wide openings, use multi-panel.
        "max_sash_width_mm": 3200,
        "configurations": [
            # (max_opening_width, config, description)
            (4000, "S-S", "2-panel: both sliding"),
            (6500, "F-S-S", "3-panel: 1 fixed + 2 sliding"),
            (9000, "F-S-S-F", "4-panel: 2 fixed + 2 sliding"),
            (12000, "F-S-S-S-F", "5-panel: 2 fixed + 3 sliding"),
        ],
        "interlock_width_mm": 30,  # overlap between sliding panels
        "frame_deduction_mm": {    # deduct from opening for frame profiles
            "left": 55, "right": 55, "top": 50, "bottom": 60,
        },
        "sash_deduction_mm": {     # deduct from panel for sash profiles
            "left": 25, "right": 25, "top": 22, "bottom": 30,
        },
        "glazing_bead_mm": 18,    # glazing bead on each side of glass
    },
    "Window - Sliding": {
        # Slim Sliding: max sash width 2500mm
        "max_sash_width_mm": 2500,
        "configurations": [
            (3000, "S-S", "2-panel: both sliding"),
            (5500, "S-S-S", "3-panel: 3 sliding"),
            (8000, "F-S-S-F", "4-panel: 2 fixed + 2 sliding"),
        ],
        "interlock_width_mm": 22,
        "frame_deduction_mm": {
            "left": 40, "right": 40, "top": 40, "bottom": 45,
        },
        "sash_deduction_mm": {
            "left": 20, "right": 20, "top": 18, "bottom": 22,
        },
        "glazing_bead_mm": 15,
    },
    "Window - Sliding (Eco 500 TB)": {
        # Eco 500: max sash width 2000mm
        "max_sash_width_mm": 2000,
        "configurations": [
            (2500, "S-S", "2-panel: both sliding"),
            (4500, "S-S-S", "3-panel: 3 sliding"),
            (6000, "F-S-S-F", "4-panel: 2 fixed + 2 sliding"),
        ],
        "interlock_width_mm": 25,
        "frame_deduction_mm": {
            "left": 40, "right": 40, "top": 40, "bottom": 45,
        },
        "sash_deduction_mm": {
            "left": 22, "right": 22, "top": 20, "bottom": 25,
        },
        "glazing_bead_mm": 16,
    },
    "Door - Sliding": {
        # Same as Lift & Slide TB but for doors
        "max_sash_width_mm": 3200,
        "configurations": [
            (2500, "S", "1-panel: single sliding door leaf"),
            (4000, "S-S", "2-panel: both sliding"),
            (6500, "F-S-S", "3-panel: 1 fixed + 2 sliding"),
        ],
        "interlock_width_mm": 30,
        "frame_deduction_mm": {
            "left": 55, "right": 55, "top": 50, "bottom": 60,
        },
        "sash_deduction_mm": {
            "left": 25, "right": 25, "top": 22, "bottom": 30,
        },
        "glazing_bead_mm": 18,
    },
}


@dataclass
class PanelDetail:
    """Individual panel within a multi-panel opening."""
    panel_id: str          # e.g. "LSTB-FRONT-GF-001-P1"
    panel_type: str        # "F" (Fixed) or "S" (Sliding)
    panel_index: int       # 0-based index within opening
    panel_width_mm: float  # outer panel dimension
    panel_height_mm: float
    glass_width_mm: float  # actual glass pane size (after sash + bead deductions)
    glass_height_mm: float
    glass_area_sqm: float
    glass_weight_kg: float
    panel_area_sqm: float
    # Profile cut lengths for this panel
    frame_top_mm: float = 0.0     # only for fixed panels or end-of-track
    frame_bottom_mm: float = 0.0
    frame_left_mm: float = 0.0
    frame_right_mm: float = 0.0
    sash_top_mm: float = 0.0      # only for sliding panels
    sash_bottom_mm: float = 0.0
    sash_left_mm: float = 0.0
    sash_right_mm: float = 0.0
    interlock_mm: float = 0.0     # interlock/meeting stile length
    track_length_mm: float = 0.0  # bottom track length (shared across opening)
    requires_mechanical_handling: bool = False


@dataclass
class SubdividedOpening:
    """An opening with its panel breakdown."""
    opening_id: str
    system_type: str
    system_series: str
    configuration: str         # e.g. "F-S-S"
    config_description: str    # e.g. "3-panel: 1 fixed + 2 sliding"
    opening_width_mm: float
    opening_height_mm: float
    num_panels: int
    num_fixed: int
    num_sliding: int
    panels: list               # list of PanelDetail
    total_glass_area_sqm: float
    total_glass_weight_kg: float
    max_pane_weight_kg: float
    max_pane_area_sqm: float
    track_length_mm: float
    # Aggregate profile lengths
    total_frame_length_mm: float
    total_sash_length_mm: float
    total_interlock_length_mm: float
    # Per-opening hardware
    hardware_sets: int
    roller_sets: int


def subdivide_opening(
    opening_width_mm: float,
    opening_height_mm: float,
    system_type: str,
    system_series: str,
    opening_id: str,
    glass_type: str = "",
    glass_thickness_mm: float = 6.0,
) -> SubdividedOpening:
    """
    Subdivide a single opening into individual panels based on Glazetech system rules.

    Returns a SubdividedOpening with full panel breakdown including:
    - Individual glass pane sizes and weights
    - Profile cut lengths per panel
    - Track length
    - Hardware count
    """
    rules = PANEL_SUBDIVISION_RULES.get(system_type)

    if not rules:
        # Fallback: treat as single panel (casement, fixed, etc.)
        glass_area = (opening_width_mm * opening_height_mm) / 1_000_000
        glass_weight = glass_area * glass_thickness_mm * GLASS_DENSITY_KG_M2_PER_MM
        panel = PanelDetail(
            panel_id=f"{opening_id}-P1",
            panel_type="F",
            panel_index=0,
            panel_width_mm=opening_width_mm,
            panel_height_mm=opening_height_mm,
            glass_width_mm=opening_width_mm - 70,  # generic deduction
            glass_height_mm=opening_height_mm - 70,
            glass_area_sqm=round(glass_area, 4),
            glass_weight_kg=round(glass_weight, 2),
            panel_area_sqm=round(glass_area, 4),
            requires_mechanical_handling=glass_weight > 80,
        )
        return SubdividedOpening(
            opening_id=opening_id,
            system_type=system_type,
            system_series=system_series,
            configuration="F",
            config_description="1-panel: single fixed",
            opening_width_mm=opening_width_mm,
            opening_height_mm=opening_height_mm,
            num_panels=1,
            num_fixed=1,
            num_sliding=0,
            panels=[panel],
            total_glass_area_sqm=panel.glass_area_sqm,
            total_glass_weight_kg=panel.glass_weight_kg,
            max_pane_weight_kg=panel.glass_weight_kg,
            max_pane_area_sqm=panel.glass_area_sqm,
            track_length_mm=0,
            total_frame_length_mm=2 * (opening_width_mm + opening_height_mm),
            total_sash_length_mm=0,
            total_interlock_length_mm=0,
            hardware_sets=0,
            roller_sets=0,
        )

    # Select configuration based on opening width
    config = "S-S"
    config_desc = "2-panel: default"
    for max_w, cfg, desc in rules["configurations"]:
        if opening_width_mm <= max_w:
            config = cfg
            config_desc = desc
            break
    else:
        # Opening wider than all configs — use the largest
        _, config, config_desc = rules["configurations"][-1]

    panel_types = config.split("-")
    num_panels = len(panel_types)
    num_fixed = sum(1 for p in panel_types if p == "F")
    num_sliding = sum(1 for p in panel_types if p == "S")

    frame_ded = rules["frame_deduction_mm"]
    sash_ded = rules["sash_deduction_mm"]
    bead = rules["glazing_bead_mm"]
    interlock_w = rules["interlock_width_mm"]

    # Calculate clear width inside frame
    clear_width = opening_width_mm - frame_ded["left"] - frame_ded["right"]
    clear_height = opening_height_mm - frame_ded["top"] - frame_ded["bottom"]

    # Total interlock width between panels
    num_interlocks = num_panels - 1
    total_interlock = num_interlocks * interlock_w

    # Available width for panels (after interlocks)
    available_width = clear_width - total_interlock

    # Distribute width equally across panels
    panel_width = available_width / num_panels

    # Build individual panels
    panels = []
    total_glass_area = 0
    total_glass_weight = 0
    max_pane_weight = 0
    max_pane_area = 0
    total_frame_len = 0
    total_sash_len = 0
    total_interlock_len = 0

    for i, ptype in enumerate(panel_types):
        pid = f"{opening_id}-P{i + 1}"

        if ptype == "F":
            # Fixed panel: glass sits directly in frame with glazing bead
            gw = panel_width - 2 * bead
            gh = clear_height - 2 * bead
            # Frame profiles for this panel
            fl = frame_ded["left"] if i == 0 else interlock_w / 2
            fr = frame_ded["right"] if i == num_panels - 1 else interlock_w / 2
            frame_top = panel_width + fl + fr
            frame_bottom = frame_top
            frame_left = clear_height
            frame_right = clear_height
            total_frame_len += 2 * (frame_top + frame_left)
            sash_top = sash_bottom = sash_left = sash_right = 0
        else:
            # Sliding panel: glass sits in sash frame
            gw = panel_width - 2 * sash_ded["left"] - 2 * bead
            gh = clear_height - sash_ded["top"] - sash_ded["bottom"] - 2 * bead
            sash_top = panel_width
            sash_bottom = panel_width
            sash_left = clear_height - sash_ded["top"] - sash_ded["bottom"]
            sash_right = sash_left
            total_sash_len += 2 * (sash_top + sash_left)
            frame_top = frame_bottom = frame_left = frame_right = 0

        gw = max(gw, 0)
        gh = max(gh, 0)
        g_area = round(gw * gh / 1_000_000, 4)
        g_weight = round(g_area * glass_thickness_mm * GLASS_DENSITY_KG_M2_PER_MM, 2)

        total_glass_area += g_area
        total_glass_weight += g_weight
        max_pane_weight = max(max_pane_weight, g_weight)
        max_pane_area = max(max_pane_area, g_area)

        # Interlock between panels
        il = clear_height if i < num_panels - 1 else 0
        total_interlock_len += il

        panel = PanelDetail(
            panel_id=pid,
            panel_type=ptype,
            panel_index=i,
            panel_width_mm=round(panel_width, 1),
            panel_height_mm=round(clear_height, 1),
            glass_width_mm=round(gw, 1),
            glass_height_mm=round(gh, 1),
            glass_area_sqm=g_area,
            glass_weight_kg=g_weight,
            panel_area_sqm=round(panel_width * clear_height / 1_000_000, 4),
            frame_top_mm=round(frame_top, 1),
            frame_bottom_mm=round(frame_bottom, 1),
            frame_left_mm=round(frame_left, 1),
            frame_right_mm=round(frame_right, 1),
            sash_top_mm=round(sash_top, 1),
            sash_bottom_mm=round(sash_bottom, 1),
            sash_left_mm=round(sash_left, 1),
            sash_right_mm=round(sash_right, 1),
            interlock_mm=round(il, 1),
            track_length_mm=0,  # set at opening level
            requires_mechanical_handling=g_weight > 80,
        )
        panels.append(panel)

    # Track runs the full opening width (shared)
    track_length = opening_width_mm

    # Outer frame perimeter
    outer_frame = 2 * (opening_width_mm + opening_height_mm)
    total_frame_len += outer_frame

    return SubdividedOpening(
        opening_id=opening_id,
        system_type=system_type,
        system_series=system_series,
        configuration=config,
        config_description=config_desc,
        opening_width_mm=opening_width_mm,
        opening_height_mm=opening_height_mm,
        num_panels=num_panels,
        num_fixed=num_fixed,
        num_sliding=num_sliding,
        panels=panels,
        total_glass_area_sqm=round(total_glass_area, 4),
        total_glass_weight_kg=round(total_glass_weight, 2),
        max_pane_weight_kg=round(max_pane_weight, 2),
        max_pane_area_sqm=round(max_pane_area, 4),
        track_length_mm=round(track_length, 1),
        total_frame_length_mm=round(total_frame_len, 1),
        total_sash_length_mm=round(total_sash_len, 1),
        total_interlock_length_mm=round(total_interlock_len, 1),
        hardware_sets=num_sliding,  # 1 hardware set per sliding panel
        roller_sets=num_sliding,    # 1 roller set per sliding panel
    )


@dataclass
class OpeningRecord:
    opening_id: str
    system_type: str
    system_series: str = ""
    width_mm: float = 0.0
    height_mm: float = 0.0
    gross_area_sqm: float = 0.0
    net_glazed_sqm: float = 0.0
    elevation: str = ""
    floor: str = ""
    count: int = 1
    total_gross_sqm: float = 0.0
    total_glazed_sqm: float = 0.0
    item_code: str = ""
    dwg_handle: str = ""
    glass_type: str = ""
    glass_thickness_mm: float = 6.0
    glass_pane_weight_kg: float = 0.0
    # MODULE 3: Forensic deliverable fields
    aluminum_weight_kg: float = 0.0
    gasket_length_lm: float = 0.0
    hardware_sets: int = 0
    perimeter_lm: float = 0.0
    remarks: str = ""
    # Panel subdivision
    subdivision: Optional[SubdividedOpening] = None


@dataclass
class OpeningSchedule:
    schedule: list = field(default_factory=list)
    total_openings: int = 0
    total_gross_sqm: float = 0.0
    total_glazed_sqm: float = 0.0
    by_type: dict = field(default_factory=dict)
    by_elevation: dict = field(default_factory=dict)
    by_floor: dict = field(default_factory=dict)
    rfi_flags: list = field(default_factory=list)


class OpeningScheduleEngine:
    """Extracts opening schedule from DWG data."""

    def __init__(self, system_mapping: dict = None):
        """
        system_mapping: dict of {layer_name: system_type} from scope engine
        """
        self.system_mapping = system_mapping or {}

    def extract_opening_schedule(
        self,
        dwg_extraction: dict,
        scope_result=None,
        spec_text: str = "",
        cluster_map: dict = None,
    ) -> OpeningSchedule:
        """
        Extract full opening schedule from DWG extraction.
        """
        schedule = OpeningSchedule()
        opening_counters = {}  # (system_prefix, elevation, floor) → counter
        rfi_counter = [0]

        # Build cluster_map from DWG metadata if not provided
        if cluster_map is None:
            metadata = dwg_extraction.get("metadata", {})
            classifications = metadata.get("cluster_classification", [])
            if classifications:
                cluster_map = {c["cluster_index"]: c for c in classifications}

        # Build layer → system_type map
        layer_map = {}
        if scope_result:
            for sys_info in scope_result.systems:
                for layer in sys_info.dwg_layers:
                    layer_map[layer.upper()] = sys_info
        elif self.system_mapping:
            layer_map = {k.upper(): v for k, v in self.system_mapping.items()}

        # Extract glass type from spec
        glass_type_from_spec = self._extract_glass_type(spec_text)
        glass_thickness = self._extract_glass_thickness(spec_text)

        # Process all block insertions (opening instances)
        for block in dwg_extraction.get("blocks", []):
            layer = block.get("layer", "").upper()
            sys_info = layer_map.get(layer)

            if not sys_info:
                continue

            if hasattr(sys_info, 'system_type'):
                system_type = sys_info.system_type
                item_prefix = sys_info.item_prefix
            else:
                system_type = str(sys_info)
                item_prefix = "X"

            # Get dimensions
            width = float(block.get("width_mm", block.get("width", 0)) or 0)
            height = float(block.get("height_mm", block.get("height", 0)) or 0)

            if width <= 0 or height <= 0:
                # Try bounding box
                bbox = block.get("bounding_box", {})
                width = float(bbox.get("width", 0) or 0)
                height = float(bbox.get("height", 0) or 0)

            # Get position info
            elevation = self._infer_elevation(block, cluster_map)
            if not elevation:
                # Auto-generate RFI for unknown elevation
                cluster_idx = block.get("cluster_index")
                best_guess = f"E{cluster_idx + 1}" if cluster_idx is not None else "E1"
                schedule.rfi_flags.append({
                    "rfi_id": f"RFI-ELEV-{len(schedule.rfi_flags) + 1:03d}",
                    "category": "MISSING_DATA",
                    "severity": "HIGH",
                    "description": (
                        f"Elevation not identified for opening on layer '{layer}'. "
                        f"DWG may contain multiple views but no metadata to distinguish them."
                    ),
                    "recommendation": "Please confirm which elevation this opening belongs to.",
                    "affected_element": block.get("name", layer),
                })
                elevation = best_guess
            floor = self._normalize_floor(block.get("floor", block.get("level", ""))) or "GF"

            # Generate opening ID
            key = (item_prefix, elevation, floor)
            opening_counters[key] = opening_counters.get(key, 0) + 1
            seq = opening_counters[key]
            opening_id = f"{item_prefix}-{elevation}-{floor}-{seq:03d}"

            # Calculate areas
            sightlines = SIGHTLINE_DEDUCTIONS.get(system_type, SIGHTLINE_DEDUCTIONS["default"])
            net_w = max(0, width - 2 * sightlines["horizontal"])
            net_h = max(0, height - 2 * sightlines["vertical"])

            gross_area = (width * height) / 1_000_000 if width and height else 0
            net_glazed = (net_w * net_h) / 1_000_000 if net_w and net_h else 0

            # Glass weight calculation
            gt = glass_thickness or 6.0
            glass_weight = net_glazed * gt * GLASS_DENSITY_KG_M2_PER_MM

            # MODULE 3: Forensic fields — aluminum weight, gasket length, hardware sets
            perimeter_mm = 2 * (width + height) if width > 0 and height > 0 else 0
            perimeter_lm = perimeter_mm / 1000.0

            al_norm = ALUMINUM_WEIGHT_NORMS.get(system_type, ALUMINUM_WEIGHT_NORMS["default"])
            # For area-based systems (curtain wall), use sqm; for unit-based, use perimeter
            if "Curtain Wall" in system_type or "Structural" in system_type:
                aluminum_weight = gross_area * al_norm
            else:
                aluminum_weight = perimeter_lm * al_norm

            gasket_mult = GASKET_MULTIPLIERS.get(system_type, GASKET_MULTIPLIERS["default"])
            gasket_length = perimeter_lm * gasket_mult

            hw_sets = HARDWARE_SETS_NORMS.get(system_type, HARDWARE_SETS_NORMS["default"])

            record = OpeningRecord(
                opening_id=opening_id,
                system_type=system_type,
                system_series=getattr(sys_info, 'system_series', '') or "",
                width_mm=width,
                height_mm=height,
                gross_area_sqm=round(gross_area, 4),
                net_glazed_sqm=round(net_glazed, 4),
                elevation=elevation,
                floor=floor,
                count=1,
                total_gross_sqm=round(gross_area, 4),
                total_glazed_sqm=round(net_glazed, 4),
                item_code=opening_id,
                dwg_handle=block.get("handle", ""),
                glass_type=glass_type_from_spec or "6mm Clear Tempered",
                glass_thickness_mm=gt,
                glass_pane_weight_kg=round(glass_weight, 2),
                aluminum_weight_kg=round(aluminum_weight, 2),
                gasket_length_lm=round(gasket_length, 2),
                hardware_sets=hw_sets,
                perimeter_lm=round(perimeter_lm, 3),
            )

            schedule.schedule.append(record)

        # ── Also process DWG openings (from Turkish/enhanced extraction) ─────
        # The DWG parser may return window/door openings directly in the
        # "openings" key (in addition to or instead of "blocks").
        # These have a total count across all floors. We distribute per floor.
        dwg_openings = dwg_extraction.get("openings", [])

        # Determine floor list from text annotations
        floor_list = self._detect_floors_from_text(dwg_extraction)

        # Get building data for facade distribution
        building_data = dwg_extraction.get("metadata", {}).get("building_data", {})
        facades = building_data.get("facades", [])
        if not facades:
            facades = ["FRONT", "BACK", "LEFT", "RIGHT"]

        for opening in dwg_openings:
            o_type = opening.get("type", "window")
            width = float(opening.get("width_mm", 0) or 0)
            height = float(opening.get("height_mm", 0) or 0)
            total_count = int(opening.get("count", 1) or 1)

            if width <= 0 or height <= 0:
                continue

            # Use Glazetech system type from DWG parser if available, else classify
            system_type = opening.get("system_type", "")
            system_series = opening.get("system_series", "")

            if not system_type:
                # Fallback: classify by type and size using Glazetech rules
                if o_type == "door":
                    system_type = "Door - Sliding"
                    item_prefix = "DS"
                    system_series = "GT-LSTB"
                else:
                    # Import and use Glazetech classifier
                    from app.services.dwg_parser import classify_glazetech_system
                    glazetech = classify_glazetech_system(width, height)
                    system_type = glazetech["system_type"]
                    system_series = glazetech["series"]

            # Generate item prefix from system series
            if system_series == "GT-LSTB":
                item_prefix = "LSTB"
            elif system_series == "GT-SS":
                item_prefix = "SS"
            elif system_series == "GT-E500TB":
                item_prefix = "E5TB"
            elif o_type == "door":
                item_prefix = "DS"
            else:
                item_prefix = "WS"

            # Get correct glass spec for this system type
            glass_spec = GLASS_SPEC_BY_SYSTEM.get(system_type, {})
            glass_type_for_opening = glass_spec.get("type", glass_type_from_spec or "6mm Clear Tempered")
            gt = glass_spec.get("thickness_mm", glass_thickness or 6.0)

            # Calculate per-unit metrics
            sightlines = SIGHTLINE_DEDUCTIONS.get(system_type, SIGHTLINE_DEDUCTIONS["default"])
            net_w = max(0, width - 2 * sightlines["horizontal"])
            net_h = max(0, height - 2 * sightlines["vertical"])
            gross_area = (width * height) / 1_000_000 if width and height else 0
            net_glazed = (net_w * net_h) / 1_000_000 if net_w and net_h else 0
            glass_weight = net_glazed * gt * GLASS_DENSITY_KG_M2_PER_MM
            perimeter_mm = 2 * (width + height)
            perimeter_lm = perimeter_mm / 1000.0
            al_norm = ALUMINUM_WEIGHT_NORMS.get(system_type, ALUMINUM_WEIGHT_NORMS["default"])
            if "Curtain Wall" in system_type or "Structural" in system_type:
                aluminum_weight = gross_area * al_norm
            else:
                aluminum_weight = perimeter_lm * al_norm
            gasket_mult = GASKET_MULTIPLIERS.get(system_type, GASKET_MULTIPLIERS["default"])
            gasket_length = perimeter_lm * gasket_mult
            hw_sets = HARDWARE_SETS_NORMS.get(system_type, HARDWARE_SETS_NORMS["default"])

            # Distribute across floors AND facades
            if floor_list and total_count >= len(floor_list):
                per_floor = total_count // len(floor_list)
                remainder = total_count % len(floor_list)
                for fi, floor_name in enumerate(floor_list):
                    floor_qty = per_floor + (1 if fi < remainder else 0)
                    if floor_qty <= 0:
                        continue

                    # Distribute this floor's qty across facades
                    for facade_name in facades:
                        facade_pct = FACADE_DISTRIBUTION.get(facade_name, 0.25)
                        facade_qty = max(1, round(floor_qty * facade_pct))

                        # Clamp to not exceed floor_qty total
                        key = (item_prefix, facade_name, floor_name)
                        opening_counters[key] = opening_counters.get(key, 0) + 1
                        seq = opening_counters[key]
                        opening_id = f"{item_prefix}-{facade_name}-{floor_name}-{seq:03d}"

                        record = OpeningRecord(
                            opening_id=opening_id,
                            system_type=system_type,
                            system_series=system_series,
                            width_mm=width,
                            height_mm=height,
                            gross_area_sqm=round(gross_area, 4),
                            net_glazed_sqm=round(net_glazed, 4),
                            elevation=facade_name,
                            floor=floor_name,
                            count=facade_qty,
                            total_gross_sqm=round(gross_area * facade_qty, 4),
                            total_glazed_sqm=round(net_glazed * facade_qty, 4),
                            item_code=opening_id,
                            glass_type=glass_type_for_opening,
                            glass_thickness_mm=gt,
                            glass_pane_weight_kg=round(glass_weight, 2),
                            aluminum_weight_kg=round(aluminum_weight, 2),
                            gasket_length_lm=round(gasket_length, 2),
                            hardware_sets=hw_sets,
                            perimeter_lm=round(perimeter_lm, 3),
                        )
                        schedule.schedule.append(record)
            else:
                # No floor list or small count — single entry per facade
                floor = opening.get("floor", "") or "TYP"
                for facade_name in facades:
                    facade_pct = FACADE_DISTRIBUTION.get(facade_name, 0.25)
                    facade_qty = max(1, round(total_count * facade_pct))

                    key = (item_prefix, facade_name, floor)
                    opening_counters[key] = opening_counters.get(key, 0) + 1
                    seq = opening_counters[key]
                    opening_id = f"{item_prefix}-{facade_name}-{floor}-{seq:03d}"

                    record = OpeningRecord(
                        opening_id=opening_id,
                        system_type=system_type,
                        system_series=system_series,
                        width_mm=width,
                        height_mm=height,
                        gross_area_sqm=round(gross_area, 4),
                        net_glazed_sqm=round(net_glazed, 4),
                        elevation=facade_name,
                        floor=floor,
                        count=facade_qty,
                        total_gross_sqm=round(gross_area * facade_qty, 4),
                        total_glazed_sqm=round(net_glazed * facade_qty, 4),
                        item_code=opening_id,
                        glass_type=glass_type_for_opening,
                        glass_thickness_mm=gt,
                        glass_pane_weight_kg=round(glass_weight, 2),
                        aluminum_weight_kg=round(aluminum_weight, 2),
                        gasket_length_lm=round(gasket_length, 2),
                        hardware_sets=hw_sets,
                        perimeter_lm=round(perimeter_lm, 3),
                    )
                    schedule.schedule.append(record)

        # Deduplicate identical openings (same size + same system + same elevation/floor)
        schedule.schedule = self._deduplicate_openings(schedule.schedule)

        # ── Panel subdivision: compute per-pane glass sizes and weights ────────
        for rec in schedule.schedule:
            sub = subdivide_opening(
                opening_width_mm=rec.width_mm,
                opening_height_mm=rec.height_mm,
                system_type=rec.system_type,
                system_series=rec.system_series,
                opening_id=rec.opening_id,
                glass_type=rec.glass_type,
                glass_thickness_mm=rec.glass_thickness_mm,
            )
            rec.subdivision = sub
            # Update glass weight to use real per-pane max (not whole opening)
            rec.glass_pane_weight_kg = sub.max_pane_weight_kg
            # Update net glazed area to sum of actual pane areas
            rec.net_glazed_sqm = sub.total_glass_area_sqm
            rec.total_glazed_sqm = round(sub.total_glass_area_sqm * rec.count, 4)
            # Update hardware sets from subdivision (per sliding panel)
            rec.hardware_sets = sub.hardware_sets

        # Build summaries
        for rec in schedule.schedule:
            schedule.total_openings += rec.count
            schedule.total_gross_sqm += rec.total_gross_sqm
            schedule.total_glazed_sqm += rec.total_glazed_sqm

            schedule.by_type[rec.system_type] = schedule.by_type.get(rec.system_type, 0) + rec.count
            schedule.by_elevation[rec.elevation] = (
                schedule.by_elevation.get(rec.elevation, 0) + rec.total_gross_sqm
            )
            schedule.by_floor[rec.floor] = (
                schedule.by_floor.get(rec.floor, 0) + rec.total_gross_sqm
            )

        # Generate RFIs for unusual openings (extend, don't overwrite — elevation RFIs already added above)
        schedule.rfi_flags.extend(self._generate_opening_rfis(schedule.schedule, rfi_counter))

        logger.info(
            f"Opening schedule: {schedule.total_openings} openings, "
            f"{schedule.total_gross_sqm:.1f} SQM gross, "
            f"{schedule.total_glazed_sqm:.1f} SQM glazed"
        )

        return schedule

    def _deduplicate_openings(self, records: list) -> list:
        """Group identical openings (same system + size) and set count > 1."""
        groups = {}

        for rec in records:
            key = (
                rec.system_type,
                round(rec.width_mm),
                round(rec.height_mm),
                rec.elevation,
                rec.floor,
            )
            if key in groups:
                groups[key].count += 1
                groups[key].total_gross_sqm += rec.gross_area_sqm
                groups[key].total_glazed_sqm += rec.net_glazed_sqm
            else:
                groups[key] = rec

        return list(groups.values())

    def _generate_opening_rfis(self, records: list, rfi_counter: list) -> list:
        """Generate RFIs for unusual opening conditions using per-pane subdivision data."""
        rfis = []

        def next_rfi():
            rfi_counter[0] += 1
            return f"RFI-{rfi_counter[0]:03d}"

        for rec in records:
            sub = rec.subdivision

            if sub:
                max_pane_area = sub.max_pane_area_sqm
                max_pane_weight = sub.max_pane_weight_kg
                config = sub.configuration
                num_panels = sub.num_panels
            else:
                max_pane_area = rec.net_glazed_sqm
                max_pane_weight = rec.glass_pane_weight_kg
                config = "?"
                num_panels = 1

            # Large individual pane (after subdivision)
            if max_pane_area > 4.0:
                rfis.append({
                    "rfi_id": next_rfi(),
                    "category": "SPECIFICATION",
                    "severity": "MEDIUM",
                    "description": (
                        f"Opening {rec.opening_id} ({config}, {num_panels}-panel): "
                        f"Largest pane {max_pane_area:.2f} SQM — confirm glass thickness and handling"
                    ),
                    "affected_element": rec.opening_id,
                    "recommendation": "Verify glass specification. Consider 8mm or 10mm for panes >4 SQM.",
                })

            # Heavy individual pane (after subdivision)
            if max_pane_weight > 80:
                if max_pane_weight > 150:
                    severity = "HIGH"
                    handling = "Crane or vacuum lifter mandatory"
                elif max_pane_weight > 100:
                    severity = "MEDIUM"
                    handling = "Vacuum lifter recommended"
                else:
                    severity = "LOW"
                    handling = "Two-person manual handling or vacuum lifter"
                rfis.append({
                    "rfi_id": next_rfi(),
                    "category": "HANDLING",
                    "severity": severity,
                    "description": (
                        f"Opening {rec.opening_id} ({config}, {num_panels}-panel): "
                        f"Heaviest pane {max_pane_weight:.1f} kg — {handling}"
                    ),
                    "affected_element": rec.opening_id,
                    "recommendation": f"{handling}. Include in prelims. Floor: {rec.floor}, Facade: {rec.elevation}.",
                })

            # Very narrow opening
            if 0 < rec.width_mm < 300:
                rfis.append({
                    "rfi_id": next_rfi(),
                    "category": "SPECIFICATION",
                    "severity": "LOW",
                    "description": f"Opening {rec.opening_id}: Width {rec.width_mm:.0f}mm — very narrow, verify with drawings",
                    "affected_element": rec.opening_id,
                    "recommendation": "Confirm opening dimensions — may be a DWG scaling issue.",
                })

            # Sash width exceeds system maximum
            if sub and sub.panels:
                for panel in sub.panels:
                    if panel.panel_type == "S":
                        rules = PANEL_SUBDIVISION_RULES.get(rec.system_type)
                        if rules and panel.panel_width_mm > rules["max_sash_width_mm"]:
                            rfis.append({
                                "rfi_id": next_rfi(),
                                "category": "ENGINEERING",
                                "severity": "HIGH",
                                "description": (
                                    f"Opening {rec.opening_id} panel {panel.panel_id}: "
                                    f"Sash width {panel.panel_width_mm:.0f}mm exceeds "
                                    f"{rec.system_type} max {rules['max_sash_width_mm']}mm"
                                ),
                                "affected_element": panel.panel_id,
                                "recommendation": (
                                    f"Increase panel count or use a heavier system. "
                                    f"Current config: {sub.configuration}"
                                ),
                            })
                        break  # Only flag once per opening

            # High-rise handling premium (floor > 8F)
            floor_num = 0
            if rec.floor and rec.floor[:-1].isdigit():
                floor_num = int(rec.floor[:-1])
            if floor_num >= 8 and max_pane_weight > 60:
                rfis.append({
                    "rfi_id": next_rfi(),
                    "category": "LOGISTICS",
                    "severity": "MEDIUM",
                    "description": (
                        f"Opening {rec.opening_id}: Floor {rec.floor} ({floor_num}F) — "
                        f"pane weight {max_pane_weight:.1f}kg at height requires crane/hoist"
                    ),
                    "affected_element": rec.opening_id,
                    "recommendation": "Include tower crane or material hoist in prelims for high-floor glazing.",
                })

        return rfis

    def _detect_floors_from_text(self, dwg_extraction: dict) -> list[str]:
        """Detect floor names from DWG text annotations."""
        texts = dwg_extraction.get("text_annotations", [])
        floors = set()

        for text in texts:
            text_upper = str(text).upper()
            # "1,2,3,4,5,6,7,8,9TH FLOOR PLAN" → floors 1-9
            multi_match = re.match(r'([\d,]+)\s*(ST|ND|RD|TH)\s+FLOOR', text_upper)
            if multi_match:
                for n in multi_match.group(1).split(','):
                    n = n.strip()
                    if n.isdigit():
                        floors.add(f"{n}F")
                continue

            # "GROUND FLOOR"
            if 'GROUND' in text_upper and 'FLOOR' in text_upper:
                floors.add('GF')
            # "LAST FLOOR"
            elif 'LAST' in text_upper and 'FLOOR' in text_upper:
                floors.add('LAST')
            # "1ST FLOOR", "2ND FLOOR", etc.
            else:
                single = re.match(r'(\d+)\s*(ST|ND|RD|TH)\s+FLOOR', text_upper)
                if single:
                    floors.add(f"{single.group(1)}F")

        if not floors:
            return []

        # Sort: GF first, then numeric, then LAST
        def floor_sort_key(f):
            if f == 'GF':
                return (0, 0)
            elif f == 'LAST':
                return (2, 0)
            elif f.endswith('F') and f[:-1].isdigit():
                return (1, int(f[:-1]))
            return (1, 999)

        return sorted(floors, key=floor_sort_key)

    def _extract_glass_type(self, spec_text: str) -> str:
        """Extract predominant glass type from spec text."""
        if not spec_text:
            return ""

        spec_lower = spec_text.lower()
        if "low-e" in spec_lower or "low e" in spec_lower:
            if "dgu" in spec_lower or "double glazed" in spec_lower or "insulated" in spec_lower:
                return "DGU 6+12+6mm Low-E"
            return "6mm Low-E"
        if "dgu" in spec_lower or "double glazed" in spec_lower or "insulating glass" in spec_lower:
            return "DGU 6+12+6mm Clear"
        if "laminated" in spec_lower:
            return "6+6mm Laminated"
        if "tinted" in spec_lower:
            return "6mm Tinted Tempered"
        if "tempered" in spec_lower or "toughened" in spec_lower:
            return "6mm Clear Tempered"
        return "6mm Clear Tempered"

    def _extract_glass_thickness(self, spec_text: str) -> Optional[float]:
        """Extract glass thickness from spec text."""
        if not spec_text:
            return None

        match = re.search(r'(\d+)\s*mm\s*(?:thick|toughened|tempered|glass)', spec_text, re.IGNORECASE)
        if match:
            thickness = float(match.group(1))
            if 4 <= thickness <= 25:
                return thickness
        return None

    def _infer_elevation(self, entity: dict, cluster_map: dict = None) -> str:
        """Infer elevation code from entity data, with cluster-based fallback."""
        # Priority 1: entity metadata (layer name, block attribute)
        for field_name in ["elevation", "view", "layer", "block_name"]:
            val = str(entity.get(field_name, "")).lower()
            if val:
                for code, keywords in ELEVATION_MAP.items():
                    if any(kw in val for kw in keywords):
                        return code

        # Priority 2: cluster-based assignment from DWG spatial analysis
        if cluster_map and entity.get("cluster_index") is not None:
            cluster = cluster_map.get(entity["cluster_index"])
            if cluster and cluster.get("elevation_code"):
                return cluster["elevation_code"]

        return ""

    def _normalize_floor(self, floor_str: str) -> str:
        """Normalize floor designation."""
        if not floor_str:
            return ""
        floor_lower = str(floor_str).lower().strip()

        if floor_lower in FLOOR_ABBREVIATIONS:
            return FLOOR_ABBREVIATIONS[floor_lower]

        match = re.match(r'(?:level|floor|l|f)\s*(\d+)', floor_lower)
        if match:
            return f"L{match.group(1)}"

        if floor_lower.isdigit():
            n = int(floor_lower)
            return "GF" if n == 0 else f"L{n}"

        return floor_str.upper()[:4]

    def to_dict(self, schedule: OpeningSchedule) -> dict:
        """Serialize OpeningSchedule to dict for JSON storage."""
        # MODULE 3: Compute forensic totals
        total_al_weight = sum(r.aluminum_weight_kg * r.count for r in schedule.schedule)
        total_gasket = sum(r.gasket_length_lm * r.count for r in schedule.schedule)
        total_hw_sets = sum(r.hardware_sets * r.count for r in schedule.schedule)
        # Glass weight now uses per-pane max × panel count × opening qty
        total_glass_weight = 0
        total_panels = 0
        for r in schedule.schedule:
            if r.subdivision:
                total_glass_weight += r.subdivision.total_glass_weight_kg * r.count
                total_panels += r.subdivision.num_panels * r.count
            else:
                total_glass_weight += r.glass_pane_weight_kg * r.count

        def _subdivision_dict(sub):
            if not sub:
                return None
            return {
                "configuration": sub.configuration,
                "config_description": sub.config_description,
                "num_panels": sub.num_panels,
                "num_fixed": sub.num_fixed,
                "num_sliding": sub.num_sliding,
                "max_pane_weight_kg": sub.max_pane_weight_kg,
                "max_pane_area_sqm": sub.max_pane_area_sqm,
                "total_glass_area_sqm": sub.total_glass_area_sqm,
                "total_glass_weight_kg": sub.total_glass_weight_kg,
                "track_length_mm": sub.track_length_mm,
                "total_frame_length_mm": sub.total_frame_length_mm,
                "total_sash_length_mm": sub.total_sash_length_mm,
                "total_interlock_length_mm": sub.total_interlock_length_mm,
                "hardware_sets": sub.hardware_sets,
                "roller_sets": sub.roller_sets,
                "panels": [
                    {
                        "panel_id": p.panel_id,
                        "panel_type": p.panel_type,
                        "panel_index": p.panel_index,
                        "panel_width_mm": p.panel_width_mm,
                        "panel_height_mm": p.panel_height_mm,
                        "glass_width_mm": p.glass_width_mm,
                        "glass_height_mm": p.glass_height_mm,
                        "glass_area_sqm": p.glass_area_sqm,
                        "glass_weight_kg": p.glass_weight_kg,
                        "requires_mechanical_handling": p.requires_mechanical_handling,
                        "frame_lengths_mm": {
                            "top": p.frame_top_mm, "bottom": p.frame_bottom_mm,
                            "left": p.frame_left_mm, "right": p.frame_right_mm,
                        } if p.panel_type == "F" else None,
                        "sash_lengths_mm": {
                            "top": p.sash_top_mm, "bottom": p.sash_bottom_mm,
                            "left": p.sash_left_mm, "right": p.sash_right_mm,
                        } if p.panel_type == "S" else None,
                        "interlock_mm": p.interlock_mm,
                    }
                    for p in sub.panels
                ],
            }

        return {
            "schedule": [
                {
                    "opening_id": r.opening_id,
                    "id": r.opening_id,  # BOM engine compatibility
                    "mark_id": r.item_code,
                    "system_type": r.system_type,
                    "system_series": r.system_series,
                    "qty": r.count,
                    "quantity": r.count,  # BOM engine compatibility
                    "width_mm": r.width_mm,
                    "height_mm": r.height_mm,
                    "gross_area_sqm": r.gross_area_sqm,
                    "net_glazed_sqm": r.net_glazed_sqm,
                    "perimeter_lm": r.perimeter_lm,
                    "elevation": r.elevation,
                    "floor": r.floor,
                    "count": r.count,
                    "total_gross_sqm": r.total_gross_sqm,
                    "total_glazed_sqm": r.total_glazed_sqm,
                    "item_code": r.item_code,
                    "glass_type": r.glass_type,
                    "glass_thickness_mm": r.glass_thickness_mm,
                    "glass_pane_weight_kg": r.glass_pane_weight_kg,
                    # MODULE 3: Forensic deliverable fields
                    "aluminum_weight_kg": r.aluminum_weight_kg,
                    "gasket_length_lm": r.gasket_length_lm,
                    "hardware_sets": r.hardware_sets,
                    # Panel subdivision
                    "subdivision": _subdivision_dict(r.subdivision),
                }
                for r in schedule.schedule
            ],
            "summary": {
                "total_openings": schedule.total_openings,
                "total_gross_sqm": round(schedule.total_gross_sqm, 2),
                "total_glazed_sqm": round(schedule.total_glazed_sqm, 2),
                "total_aluminum_weight_kg": round(total_al_weight, 2),
                "total_gasket_length_lm": round(total_gasket, 2),
                "total_hardware_sets": total_hw_sets,
                "total_glass_weight_kg": round(total_glass_weight, 2),
                "total_panels": total_panels,
                "by_type": schedule.by_type,
                "by_elevation": {k: round(v, 2) for k, v in schedule.by_elevation.items()},
                "by_floor": {k: round(v, 2) for k, v in schedule.by_floor.items()},
            },
            "rfi_flags": schedule.rfi_flags,
        }

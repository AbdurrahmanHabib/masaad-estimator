"""Opening schedule engine — extracts and structures all facade openings from DWG."""
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
    "Door - Single Swing": {"horizontal": 40, "vertical": 40},
    "Door - Double Swing": {"horizontal": 40, "vertical": 40},
    "Structural Glazing": {"horizontal": 15, "vertical": 15},
    "Shopfront": {"horizontal": 50, "vertical": 60},
    "default": {"horizontal": 35, "vertical": 35},
}

# Glass density kg/m2 per mm of thickness
GLASS_DENSITY_KG_M2_PER_MM = 2.5


# Aluminum weight per LM (kg/m) by system type — fallback when no catalog match
ALUMINUM_WEIGHT_NORMS = {
    "Curtain Wall (Stick)": 12.5,    # kg/sqm of facade area
    "Curtain Wall (Unitised)": 14.0,
    "Window - Casement": 4.8,        # kg/lm of perimeter
    "Window - Fixed": 3.5,
    "Window - Sliding": 5.2,
    "Door - Single Swing": 6.5,
    "Door - Double Swing": 6.5,
    "Structural Glazing": 8.0,
    "Shopfront": 10.0,
    "default": 5.0,
}

# Gasket length multiplier (lm of gasket per lm of opening perimeter)
GASKET_MULTIPLIERS = {
    "Curtain Wall (Stick)": 2.0,     # inner + outer gasket run
    "Curtain Wall (Unitised)": 2.2,
    "Window - Casement": 1.5,
    "Window - Fixed": 1.0,
    "Window - Sliding": 1.8,
    "Door - Single Swing": 1.5,
    "Door - Double Swing": 1.5,
    "Structural Glazing": 0.5,       # minimal — silicone joint
    "Shopfront": 1.8,
    "default": 1.5,
}

# Hardware sets per opening (number of hardware units)
HARDWARE_SETS_NORMS = {
    "Curtain Wall (Stick)": 0,        # no operable hardware
    "Curtain Wall (Unitised)": 0,
    "Window - Casement": 1,           # 1 handle + 1 hinge pair + 1 lock
    "Window - Fixed": 0,
    "Window - Sliding": 1,            # 1 roller set + 1 lock
    "Door - Single Swing": 1,         # 1 handle set + 1 closer + 1 hinge set + 1 lock
    "Door - Double Swing": 2,         # 2× hardware sets
    "Structural Glazing": 0,
    "Shopfront": 1,
    "default": 0,
}


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
    ) -> OpeningSchedule:
        """
        Extract full opening schedule from DWG extraction.
        """
        schedule = OpeningSchedule()
        opening_counters = {}  # (system_prefix, elevation, floor) → counter
        rfi_counter = [0]

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
            elevation = self._infer_elevation(block) or "E1"
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

        # Deduplicate identical openings (same size + same system + same elevation/floor)
        schedule.schedule = self._deduplicate_openings(schedule.schedule)

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

        # Generate RFIs for unusual openings
        schedule.rfi_flags = self._generate_opening_rfis(schedule.schedule, rfi_counter)

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
        """Generate RFIs for unusual opening conditions."""
        rfis = []

        def next_rfi():
            rfi_counter[0] += 1
            return f"RFI-{rfi_counter[0]:03d}"

        for rec in records:
            # Very large single pane
            if rec.net_glazed_sqm > 4.0:
                rfis.append({
                    "rfi_id": next_rfi(),
                    "category": "SPECIFICATION",
                    "severity": "MEDIUM",
                    "description": f"Opening {rec.opening_id}: Large pane {rec.net_glazed_sqm:.1f} SQM — confirm glass thickness and handling method",
                    "affected_element": rec.opening_id,
                    "recommendation": "Verify glass specification. Consider 8mm or 10mm for panes >4 SQM.",
                })

            # Heavy glass
            if rec.glass_pane_weight_kg > 100:
                severity = "HIGH" if rec.glass_pane_weight_kg > 150 else "MEDIUM"
                rfis.append({
                    "rfi_id": next_rfi(),
                    "category": "SPECIFICATION",
                    "severity": severity,
                    "description": f"Opening {rec.opening_id}: Glass weight {rec.glass_pane_weight_kg:.0f} kg — mechanical handling required",
                    "affected_element": rec.opening_id,
                    "recommendation": "Crane or vacuum lifter required. Include mechanical handling in prelims.",
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

        return rfis

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

    def _infer_elevation(self, entity: dict) -> str:
        """Infer elevation code from entity data."""
        for field_name in ["elevation", "view", "layer", "block_name"]:
            val = str(entity.get(field_name, "")).lower()
            if val:
                for code, keywords in ELEVATION_MAP.items():
                    if any(kw in val for kw in keywords):
                        return code
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
        total_glass_weight = sum(r.glass_pane_weight_kg * r.count for r in schedule.schedule)

        return {
            "schedule": [
                {
                    "opening_id": r.opening_id,
                    "mark_id": r.item_code,
                    "system_type": r.system_type,
                    "system_series": r.system_series,
                    "qty": r.count,
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
                "by_type": schedule.by_type,
                "by_elevation": {k: round(v, 2) for k, v in schedule.by_elevation.items()},
                "by_floor": {k: round(v, 2) for k, v in schedule.by_floor.items()},
            },
            "rfi_flags": schedule.rfi_flags,
        }

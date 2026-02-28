"""
Resilient DWG/DXF Parser for Facade Estimation

Handles messy real-world files:
- Multiple overlapping drawings in one file
- Entities across model space + all paper space layouts
- No consistent layering or naming
- Large files (10MB+)
- Spatial clustering to group separate drawings
- Turkish architectural DXF files with slash-format dimensions
- Multi-view detection (plan/elevation/section)
- Glazetech thermal break profile system classification

Dependencies:
  - ezdxf (required, v1.1.0)
  - ODA File Converter (optional, for .dwg → .dxf conversion)

Returns structured data with panels, openings, text annotations, blocks, warnings.
"""
import os
import re
import math
import shutil
import logging
import tempfile
import subprocess
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

import ezdxf
from ezdxf.math import BoundingBox, Vec3

logger = logging.getLogger("masaad-dwg-parser")

# ── Configuration ────────────────────────────────────────────────────────────

# ODA File Converter path — set via environment variable or auto-detect
ODA_CONVERTER_PATH = os.getenv("ODA_CONVERTER_PATH", "")

# Spatial clustering: entities within this distance (mm) are grouped
CLUSTER_DISTANCE_MM = 500.0

# Minimum dimensions for a valid panel (mm)
MIN_PANEL_DIM_MM = 100.0
MAX_PANEL_DIM_MM = 15000.0

# ── Glazetech Thermal Break Profile Catalog ──────────────────────────────────
# Elite Extrusion L.L.C / Glazetech — RAK, UAE
# Three systems specified by client for AL KABIR TOWER:

GLAZETECH_CATALOG = {
    "top_hung": {
        "name": "Glazetech Top Hung Window",
        "series": "GT-TH",
        "system_type": "Window - Top Hung",
        "thermal_break": True,
        "frame_depth_mm": 60,
        "sash_depth_mm": 50,
        "max_sash_weight_kg": 80,
        "max_sash_width_mm": 1600,
        "max_sash_height_mm": 2400,
        "min_width_mm": 400,
        "glazing_range_mm": (20, 36),
        "uf_value": 3.0,
        "air_permeability": "Class 4",
        "water_tightness": "Class 9A",
        "wind_resistance": "Class C4",
        "aluminum_kg_per_lm": 4.5,
        "profiles_per_unit": 6,
        "gasket_multiplier": 1.8,
        "hardware_type": "Top hung friction stay + espagnolette",
        "finish": "Powder Coated RAL",
        "supplier": "Elite Extrusion L.L.C",
        "application": "Bedroom, kitchen, bathroom windows (non-sliding)",
    },
    "lift_and_slide_tb": {
        "name": "Glazetech Lift and Slide Thermal Break",
        "series": "GT-LSTB",
        "system_type": "Window - Sliding (Lift & Slide TB)",
        "thermal_break": True,
        "frame_depth_mm": 160,
        "sash_depth_mm": 76,
        "max_sash_weight_kg": 400,
        "max_sash_width_mm": 3200,
        "max_sash_height_mm": 3000,
        "min_width_mm": 1800,
        "glazing_range_mm": (24, 52),
        "uf_value": 2.0,  # W/m²K
        "air_permeability": "Class 4",
        "water_tightness": "Class E1200",
        "wind_resistance": "Class C5",
        "aluminum_kg_per_lm": 7.8,
        "profiles_per_unit": 8,  # frame top/bottom/sides + sash top/bottom/sides + interlock + track
        "gasket_multiplier": 2.2,
        "hardware_type": "Lift & Slide roller + lock",
        "finish": "Powder Coated RAL",
        "supplier": "Elite Extrusion L.L.C",
        "application": "Large balcony doors, patio doors",
    },
    "slim_sliding": {
        "name": "Glazetech Slim Sliding System",
        "series": "GT-SS",
        "system_type": "Window - Sliding",
        "thermal_break": False,
        "frame_depth_mm": 50,
        "sash_depth_mm": 45,
        "max_sash_weight_kg": 150,
        "max_sash_width_mm": 2500,
        "max_sash_height_mm": 2500,
        "min_width_mm": 1000,
        "glazing_range_mm": (5, 24),
        "uf_value": 5.5,  # W/m²K (no TB)
        "air_permeability": "Class 3",
        "water_tightness": "Class 7A",
        "wind_resistance": "Class C3",
        "aluminum_kg_per_lm": 4.2,
        "profiles_per_unit": 6,
        "gasket_multiplier": 1.8,
        "hardware_type": "Sliding roller + crescent lock",
        "finish": "Powder Coated RAL",
        "supplier": "Elite Extrusion L.L.C",
        "application": "Bedroom/living room windows",
    },
    "eco_500_tb": {
        "name": "Glazetech Eco 500 Sliding Thermal Break",
        "series": "GT-E500TB",
        "system_type": "Window - Sliding (Eco 500 TB)",
        "thermal_break": True,
        "frame_depth_mm": 50,
        "sash_depth_mm": 50,
        "max_sash_weight_kg": 200,
        "max_sash_width_mm": 2000,
        "max_sash_height_mm": 2500,
        "min_width_mm": 800,
        "glazing_range_mm": (20, 36),
        "uf_value": 3.0,  # W/m²K
        "air_permeability": "Class 4",
        "water_tightness": "Class 9A",
        "wind_resistance": "Class C4",
        "aluminum_kg_per_lm": 5.2,
        "profiles_per_unit": 7,
        "gasket_multiplier": 2.0,
        "hardware_type": "Sliding roller + TB lock",
        "finish": "Powder Coated RAL",
        "supplier": "Elite Extrusion L.L.C",
        "application": "Kitchen/utility windows, economic thermal break",
    },
}

# Facade direction mapping: text labels → elevation codes (E1/E2/E3/E4)
FACADE_DIRECTION_MAP = {
    "FRONT": "E1",
    "BACK": "E2",
    "RIGHT": "E3",
    "LEFT": "E4",
    "NORTH": "E1",
    "SOUTH": "E2",
    "EAST": "E3",
    "WEST": "E4",
}


def classify_glazetech_system(width_mm: float, height_mm: float, room_context: str = "", opening_type: str = "window", has_railing: bool = False) -> dict:
    """
    Classify a window opening to the correct Glazetech profile system.

    Rules verified from building illustrations + DXF analysis:
    - Width < 800mm  → Top Hung Window (small bathroom/kitchen ventilation windows)
    - Width 800-1800mm → Fixed Window (non-operable glass panels on facade)
    - Width >= 1800mm → Sliding Window (horizontal sliding)
      - Width >= 6000mm → Lift & Slide TB (extra-large patio doors)
      - Width 3000-6000mm → Slim Sliding
      - Width 1800-3000mm → Eco 500 Sliding TB

    Returns catalog entry dict with system_type, series, etc.
    """
    # Small openings are top hung (bathroom/kitchen ventilation)
    if width_mm < 800:
        return GLAZETECH_CATALOG["top_hung"]

    # Mid-width: fixed glass panels (non-operable facade panels)
    if width_mm < 1800:
        return {
            "name": "Fixed Window",
            "series": "FIXED",
            "system_type": "Window - Fixed",
            "thermal_break": False,
            "frame_depth_mm": 50,
            "sash_depth_mm": 0,
            "max_sash_weight_kg": 0,
            "max_sash_width_mm": 0,
            "max_sash_height_mm": 0,
            "min_width_mm": 0,
            "glazing_range_mm": (5, 24),
            "uf_value": 5.5,
            "aluminum_kg_per_lm": 3.0,
            "profiles_per_unit": 4,
            "gasket_multiplier": 1.0,
            "hardware_type": "None (fixed)",
            "finish": "Powder Coated RAL",
            "supplier": "Elite Extrusion L.L.C",
            "application": "Non-operable facade glass panels",
        }

    # Width >= 1800mm: sliding windows — select system by width
    if width_mm >= 6000:
        return GLAZETECH_CATALOG["lift_and_slide_tb"]
    elif width_mm >= 3000:
        return GLAZETECH_CATALOG["slim_sliding"]
    else:
        return GLAZETECH_CATALOG["eco_500_tb"]

# Dimension patterns in text annotations
_DIM_PATTERNS = [
    # "1200x2400", "1200X2400", "1200 x 2400"
    re.compile(r'(\d{2,5})\s*[xX×]\s*(\d{2,5})'),
    # "W=1200 H=2400", "W1200 H2400"
    re.compile(r'[Ww]\s*=?\s*(\d{2,5})\s+[Hh]\s*=?\s*(\d{2,5})'),
    # "1200mm x 2400mm"
    re.compile(r'(\d{2,5})\s*mm\s*[xX×]\s*(\d{2,5})\s*mm'),
    # "WIDTH: 1200  HEIGHT: 2400"
    re.compile(r'WIDTH\s*:?\s*(\d{2,5})\s+HEIGHT\s*:?\s*(\d{2,5})', re.IGNORECASE),
]

# Turkish-style slash-separated dimensions: "530/220" (in cm, needs ×10 to mm)
_DIM_PATTERN_SLASH_CM = re.compile(r'^(\d{2,4})\s*/\s*(\d{2,4})$')

# Window/door block name patterns (English + Turkish)
_WINDOW_PATTERNS = re.compile(
    r'(?i)(window|win|W\d|WN\d|casement|awning|sliding|fixed|'
    r'pencere|penc|cam|Kap[ıi]-?Pencere|KAPI.?PENCERE)',
    re.IGNORECASE,
)
_DOOR_PATTERNS = re.compile(
    r'(?i)(door|dr|D\d|DN\d|entrance|swing|revolving|'
    r'kap[ıi]|door-text|DİDEM)',
    re.IGNORECASE,
)

# Facade-relevant keywords in text annotations (English + Turkish)
_FACADE_KEYWORDS = re.compile(
    r'(?i)(glass|glazing|alumin|mullion|transom|ACP|cladding|curtain.?wall|'
    r'spandrel|panel|sealant|silicone|thermal.?break|double.?glaz|DGU|'
    r'tempered|laminated|low.?e|tinted|clear|float|IGU|spider|'
    r'bracket|anchor|fixing|profile\s*\d|series\s*\d|'
    r'pencere|kap[ıi]|do[gğ]rama|cephe|cam|balkon|balcony|'
    r'FLOOR\s+PLAN|SECTION|ELEVATION|BASEMENT|GROUND\s+FLOOR|'
    r'\d+/\d+)',
    re.IGNORECASE,
)

# Turkish architectural layer name patterns for window/door dimensions
_TURKISH_DIM_LAYERS = re.compile(
    r'(?i)(penc.?yaz|kap.?yaz|door.?text|do[gğ]rama)',
)

# Floor plan label patterns
_FLOOR_PLAN_PATTERNS = re.compile(
    r'(?i)(\d+)\s*(ST|ND|RD|TH|\.)\s*(FLOOR|BASEMENT)|'
    r'(GROUND|LAST|ROOF|TYPICAL|TERRACE)\s*FLOOR|'
    r'(\d+),.*FLOOR\s+PLAN',
)


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class BoundsInfo:
    min_x: float = 0.0
    min_y: float = 0.0
    max_x: float = 0.0
    max_y: float = 0.0

    @property
    def width(self) -> float:
        return abs(self.max_x - self.min_x)

    @property
    def height(self) -> float:
        return abs(self.max_y - self.min_y)

    def to_dict(self) -> dict:
        return {
            "min_x": round(self.min_x, 2),
            "min_y": round(self.min_y, 2),
            "max_x": round(self.max_x, 2),
            "max_y": round(self.max_y, 2),
            "width": round(self.width, 2),
            "height": round(self.height, 2),
        }


@dataclass
class PanelInfo:
    width_mm: float
    height_mm: float
    area_sqm: float
    count: int = 1
    source: str = ""  # "geometry" or "text_annotation"
    layer: str = ""
    entity_idx: int = -1  # index into entity_bounds_for_clustering for spatial dedup


@dataclass
class OpeningInfo:
    type: str  # "window", "door", "opening"
    width_mm: float
    height_mm: float
    area_sqm: float
    block_name: str = ""
    count: int = 1
    layer: str = ""
    entity_idx: int = -1  # index into entity_bounds_for_clustering for spatial dedup
    floor: str = ""
    elevation: str = ""
    dxf_panel_hint: int = 0  # panel count from DXF block type (0 = use width rules)
    has_railing: bool = False  # True if KORKULUK railing nearby (balcony context)


@dataclass
class BlockInfo:
    name: str
    count: int
    bounds: Optional[BoundsInfo] = None
    block_type: str = ""  # "window", "door", "generic"


@dataclass
class LayoutInfo:
    name: str
    entity_count: int
    bounds: Optional[BoundsInfo] = None


@dataclass
class ParseResult:
    layouts: list
    panels: list
    openings: list
    text_annotations: list
    blocks: list
    total_facade_area_sqm: float
    warnings: list
    metadata: dict


# ── DWG → DXF Conversion ─────────────────────────────────────────────────────

def _find_oda_converter() -> str | None:
    """Attempt to locate ODA File Converter on disk."""
    if ODA_CONVERTER_PATH and os.path.isfile(ODA_CONVERTER_PATH):
        return ODA_CONVERTER_PATH

    # Common install paths
    candidates = [
        r"C:\Program Files\ODA\ODAFileConverter\ODAFileConverter.exe",
        r"C:\Program Files (x86)\ODA\ODAFileConverter\ODAFileConverter.exe",
        "/usr/bin/ODAFileConverter",
        "/usr/local/bin/ODAFileConverter",
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c

    # Check if it's on PATH
    which = shutil.which("ODAFileConverter")
    if which:
        return which

    return None


def convert_dwg_to_dxf(input_path: str) -> str:
    """
    Convert a .dwg file to .dxf using ODA File Converter.
    Returns path to the generated .dxf file.
    Raises RuntimeError if ODA is not available.
    """
    oda = _find_oda_converter()
    if not oda:
        raise RuntimeError(
            "ODA File Converter not found. "
            "Install from https://www.opendesign.com/guestfiles/oda_file_converter "
            "or set the ODA_CONVERTER_PATH environment variable."
        )

    input_dir = os.path.dirname(os.path.abspath(input_path))
    output_dir = tempfile.mkdtemp(prefix="masaad_dwg_")
    basename = os.path.basename(input_path)
    dxf_name = os.path.splitext(basename)[0] + ".dxf"

    try:
        result = subprocess.run(
            [oda, input_dir, output_dir, "ACAD2018", "DXF", "0", "1", basename],
            capture_output=True,
            timeout=120,
        )
        dxf_path = os.path.join(output_dir, dxf_name)
        if os.path.isfile(dxf_path):
            return dxf_path
        # ODA may have changed the filename slightly
        for f in os.listdir(output_dir):
            if f.lower().endswith('.dxf'):
                return os.path.join(output_dir, f)
        raise RuntimeError(
            f"ODA conversion produced no .dxf output. "
            f"Exit code: {result.returncode}, stderr: {result.stderr.decode(errors='replace')[:500]}"
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError("ODA File Converter timed out (120s limit)")


# ── Entity extraction helpers ─────────────────────────────────────────────────

def _safe_bounds(entity) -> Optional[BoundsInfo]:
    """Safely compute bounding box for any entity."""
    try:
        bbox = BoundingBox()
        # For INSERT entities, we need to handle differently
        if hasattr(entity, 'virtual_entities'):
            try:
                for ve in entity.virtual_entities():
                    bbox.extend(ve.control_points() if hasattr(ve, 'control_points') else [])
            except Exception:
                pass
        # Generic approach
        if bbox.is_empty:
            if hasattr(entity, 'dxf') and hasattr(entity.dxf, 'insert'):
                # INSERT entity — use insert point as center
                ins = entity.dxf.insert
                return BoundsInfo(ins.x, ins.y, ins.x, ins.y)
            points = []
            try:
                if entity.dxftype() == 'LINE':
                    points = [entity.dxf.start, entity.dxf.end]
                elif entity.dxftype() == 'CIRCLE':
                    c = entity.dxf.center
                    r = entity.dxf.radius
                    return BoundsInfo(c.x - r, c.y - r, c.x + r, c.y + r)
                elif entity.dxftype() == 'ARC':
                    c = entity.dxf.center
                    r = entity.dxf.radius
                    return BoundsInfo(c.x - r, c.y - r, c.x + r, c.y + r)
                elif entity.dxftype() in ('LWPOLYLINE', 'POLYLINE'):
                    if hasattr(entity, 'get_points'):
                        points = [Vec3(p[0], p[1], 0) for p in entity.get_points()]
                    elif hasattr(entity, 'vertices'):
                        points = [Vec3(v.dxf.location.x, v.dxf.location.y, 0) for v in entity.vertices]
                elif entity.dxftype() == 'POINT':
                    loc = entity.dxf.location
                    return BoundsInfo(loc.x, loc.y, loc.x, loc.y)
                elif entity.dxftype() == 'SOLID' or entity.dxftype() == '3DSOLID':
                    pass  # Skip complex solids
                elif entity.dxftype() in ('TEXT', 'MTEXT'):
                    ins = entity.dxf.insert if hasattr(entity.dxf, 'insert') else None
                    if ins:
                        return BoundsInfo(ins.x, ins.y, ins.x, ins.y)
                elif entity.dxftype() == 'SPLINE':
                    if hasattr(entity, 'control_points'):
                        points = list(entity.control_points)
                    elif hasattr(entity, 'fit_points'):
                        points = list(entity.fit_points)
                elif entity.dxftype() == 'ELLIPSE':
                    c = entity.dxf.center
                    # Approximate bounds
                    major = entity.dxf.major_axis
                    r = max(abs(major.x), abs(major.y), 1)
                    return BoundsInfo(c.x - r, c.y - r, c.x + r, c.y + r)
            except Exception:
                pass

            if points:
                xs = [p.x for p in points if hasattr(p, 'x')]
                ys = [p.y for p in points if hasattr(p, 'y')]
                if xs and ys:
                    return BoundsInfo(min(xs), min(ys), max(xs), max(ys))
        else:
            ext_min = bbox.extmin
            ext_max = bbox.extmax
            return BoundsInfo(ext_min.x, ext_min.y, ext_max.x, ext_max.y)
    except Exception:
        pass
    return None


def _extract_text(entity) -> str:
    """Extract text content from TEXT or MTEXT entity."""
    try:
        if entity.dxftype() == 'TEXT':
            return entity.dxf.text.strip()
        elif entity.dxftype() == 'MTEXT':
            # MTEXT can have formatting codes — strip them
            raw = entity.text if hasattr(entity, 'text') else entity.dxf.text
            # Remove MTEXT formatting: {\fArial;...} etc.
            cleaned = re.sub(r'\\[A-Za-z][^;]*;', '', str(raw))
            cleaned = re.sub(r'[{}]', '', cleaned)
            cleaned = re.sub(r'\\P', '\n', cleaned)  # paragraph break
            cleaned = re.sub(r'\\[A-Za-z]', '', cleaned)
            return cleaned.strip()
    except Exception:
        pass
    return ""


def _extract_dimensions_from_text(text: str) -> list[tuple[float, float]]:
    """
    Extract width x height dimensions from text string.
    Returns list of (width_mm, height_mm) tuples.
    """
    results = []
    for pattern in _DIM_PATTERNS:
        for match in pattern.finditer(text):
            try:
                w = float(match.group(1))
                h = float(match.group(2))
                if MIN_PANEL_DIM_MM <= w <= MAX_PANEL_DIM_MM and MIN_PANEL_DIM_MM <= h <= MAX_PANEL_DIM_MM:
                    results.append((w, h))
            except (ValueError, IndexError):
                continue
    return results


def _rect_from_polyline(entity) -> Optional[tuple[float, float]]:
    """
    If a closed polyline/lwpolyline is rectangular, return (width, height) in drawing units.
    """
    try:
        if entity.dxftype() == 'LWPOLYLINE':
            pts = list(entity.get_points(format='xy'))
        elif entity.dxftype() == 'POLYLINE':
            pts = [(v.dxf.location.x, v.dxf.location.y) for v in entity.vertices]
        else:
            return None

        # Remove duplicate closing point
        if len(pts) >= 4 and pts[0] == pts[-1]:
            pts = pts[:-1]

        if len(pts) != 4:
            return None

        # Check if it's a rectangle: all angles should be ~90 degrees
        # Compute edge lengths
        edges = []
        for i in range(4):
            dx = pts[(i + 1) % 4][0] - pts[i][0]
            dy = pts[(i + 1) % 4][1] - pts[i][1]
            length = math.sqrt(dx * dx + dy * dy)
            edges.append(length)

        # A rectangle has opposite sides equal
        if not (abs(edges[0] - edges[2]) / max(edges[0], edges[2], 0.001) < 0.05 and
                abs(edges[1] - edges[3]) / max(edges[1], edges[3], 0.001) < 0.05):
            return None

        # Check right angles via dot product
        for i in range(4):
            ax = pts[(i + 1) % 4][0] - pts[i][0]
            ay = pts[(i + 1) % 4][1] - pts[i][1]
            bx = pts[(i + 2) % 4][0] - pts[(i + 1) % 4][0]
            by = pts[(i + 2) % 4][1] - pts[(i + 1) % 4][1]
            dot = ax * bx + ay * by
            len_a = math.sqrt(ax * ax + ay * ay)
            len_b = math.sqrt(bx * bx + by * by)
            if len_a > 0 and len_b > 0:
                cos_angle = abs(dot / (len_a * len_b))
                if cos_angle > 0.1:  # not perpendicular
                    return None

        w = max(edges[0], edges[1])
        h = min(edges[0], edges[1])
        if w < 1 or h < 1:
            return None
        return (w, h)
    except Exception:
        return None


# ── Spatial clustering ────────────────────────────────────────────────────────

def _cluster_entities(
    entity_bounds: list[tuple[int, BoundsInfo]],
    max_distance: float,
) -> list[list[int]]:
    """
    Simple grid-based spatial clustering of entities by proximity.
    Returns list of clusters, each being a list of entity indices.
    """
    if not entity_bounds:
        return []

    # Use a grid approach for efficiency
    cell_size = max_distance
    grid: dict[tuple[int, int], list[int]] = defaultdict(list)

    for idx, (orig_idx, b) in enumerate(entity_bounds):
        cx = (b.min_x + b.max_x) / 2
        cy = (b.min_y + b.max_y) / 2
        gx = int(cx / cell_size)
        gy = int(cy / cell_size)
        grid[(gx, gy)].append(orig_idx)

    # Merge adjacent grid cells into clusters
    visited = set()
    clusters = []

    for cell_key, indices in grid.items():
        if cell_key in visited:
            continue
        # BFS to find connected cells
        cluster = []
        queue = [cell_key]
        while queue:
            ck = queue.pop(0)
            if ck in visited:
                continue
            visited.add(ck)
            if ck in grid:
                cluster.extend(grid[ck])
                # Check 8 neighbors
                gx, gy = ck
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        nk = (gx + dx, gy + dy)
                        if nk not in visited and nk in grid:
                            queue.append(nk)
        if cluster:
            clusters.append(cluster)

    return clusters


# ── Main parser class ─────────────────────────────────────────────────────────

class DWGParserService:
    """
    Resilient DWG/DXF parser for facade estimation.

    Handles:
    - .dwg files (via ODA File Converter) and .dxf files (native ezdxf)
    - Model space + all paper space layouts
    - Spatial clustering of overlapping drawings
    - Dimension extraction from text annotations
    - Block detection for windows/doors
    - Fault tolerance (never crashes on bad data)
    """

    def __init__(self, oda_converter_path: str = ""):
        """
        Args:
            oda_converter_path: Path to ODA File Converter executable.
                                If empty, will auto-detect or skip DWG conversion.
        """
        if oda_converter_path:
            global ODA_CONVERTER_PATH
            ODA_CONVERTER_PATH = oda_converter_path

    def parse_file(self, file_path: str) -> dict:
        """
        Parse a .dwg or .dxf file and return structured facade data.

        Args:
            file_path: Path to the .dwg or .dxf file.

        Returns:
            Dict with keys: layouts, panels, openings, text_annotations,
            blocks, total_facade_area_sqm, warnings, metadata
        """
        warnings: list[str] = []
        ext = os.path.splitext(file_path)[1].lower()

        # Validate file exists
        if not os.path.isfile(file_path):
            return self._empty_result(warnings=["File not found: " + file_path])

        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)

        # Convert DWG to DXF if needed
        dxf_path = file_path
        if ext == '.dwg':
            try:
                dxf_path = convert_dwg_to_dxf(file_path)
                logger.info(f"DWG converted to DXF: {dxf_path}")
            except RuntimeError as e:
                warnings.append(str(e))
                return self._empty_result(warnings=warnings)
            except Exception as e:
                warnings.append(f"DWG conversion failed unexpectedly: {e}")
                return self._empty_result(warnings=warnings)
        elif ext != '.dxf':
            warnings.append(f"Unsupported file format: {ext}. Expected .dwg or .dxf")
            return self._empty_result(warnings=warnings)

        # Parse DXF
        try:
            doc = ezdxf.readfile(dxf_path)
        except Exception as e:
            warnings.append(f"Failed to read DXF file: {e}")
            return self._empty_result(warnings=warnings)

        return self._extract_from_doc(doc, warnings, file_size_mb)

    def parse_bytes(self, data: bytes, filename: str = "upload.dxf") -> dict:
        """
        Parse DXF content from bytes (for API upload handling).

        Args:
            data: Raw file bytes.
            filename: Original filename (used to detect .dwg vs .dxf).

        Returns:
            Same structured dict as parse_file().
        """
        warnings: list[str] = []
        ext = os.path.splitext(filename)[1].lower()
        file_size_mb = len(data) / (1024 * 1024)

        # Write to temp file
        suffix = ext if ext in ('.dwg', '.dxf') else '.dxf'
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        tmp.write(data)
        tmp.close()

        try:
            if ext == '.dwg':
                try:
                    dxf_path = convert_dwg_to_dxf(tmp.name)
                except RuntimeError as e:
                    warnings.append(str(e))
                    return self._empty_result(warnings=warnings)
            else:
                dxf_path = tmp.name

            try:
                doc = ezdxf.readfile(dxf_path)
            except Exception as e:
                warnings.append(f"Failed to read DXF: {e}")
                return self._empty_result(warnings=warnings)

            return self._extract_from_doc(doc, warnings, file_size_mb)
        finally:
            try:
                os.unlink(tmp.name)
            except Exception:
                pass

    def _extract_from_doc(self, doc, warnings: list[str], file_size_mb: float) -> dict:
        """Core extraction from an ezdxf Document object."""
        layouts_info = []
        all_panels: list[PanelInfo] = []
        all_openings: list[OpeningInfo] = []
        all_text_annotations: list[str] = []
        all_blocks: dict[str, BlockInfo] = {}
        entity_bounds_for_clustering: list[tuple[int, BoundsInfo]] = []
        entity_idx = 0

        # ── Process each layout (model space + all paper space layouts) ────────
        try:
            layout_names = [layout.name for layout in doc.layouts]
        except Exception:
            layout_names = ["Model"]
            warnings.append("Could not enumerate layouts, processing Model space only")

        for layout_name in layout_names:
            try:
                layout = doc.layouts.get(layout_name)
            except Exception:
                warnings.append(f"Could not access layout: {layout_name}")
                continue

            if layout is None:
                continue

            layout_entity_count = 0
            layout_bbox = BoundingBox()

            try:
                entities = list(layout)
            except Exception as e:
                warnings.append(f"Error iterating layout {layout_name}: {e}")
                continue

            for entity in entities:
                try:
                    layout_entity_count += 1
                    dxf_type = entity.dxftype()

                    # Compute bounds for clustering
                    eb = _safe_bounds(entity)
                    if eb:
                        entity_bounds_for_clustering.append((entity_idx, eb))
                        try:
                            layout_bbox.extend([
                                Vec3(eb.min_x, eb.min_y, 0),
                                Vec3(eb.max_x, eb.max_y, 0),
                            ])
                        except Exception:
                            pass

                    # ── Lines ──────────────────────────────────────────────
                    if dxf_type == 'LINE':
                        # Lines are tracked via bounds for panel detection
                        pass

                    # ── Polylines / LWPolylines → panel rectangles ────────
                    elif dxf_type in ('LWPOLYLINE', 'POLYLINE'):
                        rect = _rect_from_polyline(entity)
                        if rect:
                            w, h = rect
                            if MIN_PANEL_DIM_MM <= w <= MAX_PANEL_DIM_MM and MIN_PANEL_DIM_MM <= h <= MAX_PANEL_DIM_MM:
                                layer = entity.dxf.layer if hasattr(entity.dxf, 'layer') else ""
                                all_panels.append(PanelInfo(
                                    width_mm=round(max(w, h), 1),
                                    height_mm=round(min(w, h), 1),
                                    area_sqm=round(w * h / 1e6, 4),
                                    source="geometry",
                                    layer=layer,
                                    entity_idx=entity_idx,
                                ))

                    # ── Circles → holes, fixings ──────────────────────────
                    elif dxf_type == 'CIRCLE':
                        pass  # Tracked in bounds; could be analyzed for fixing patterns

                    # ── Text / MText → annotations, dimension specs ───────
                    elif dxf_type in ('TEXT', 'MTEXT'):
                        txt = _extract_text(entity)
                        if txt:
                            # Check for facade-relevant keywords
                            if _FACADE_KEYWORDS.search(txt):
                                all_text_annotations.append(txt)
                            # Check for dimension patterns
                            dims = _extract_dimensions_from_text(txt)
                            for w, h in dims:
                                layer = entity.dxf.layer if hasattr(entity.dxf, 'layer') else ""
                                all_panels.append(PanelInfo(
                                    width_mm=round(max(w, h), 1),
                                    height_mm=round(min(w, h), 1),
                                    area_sqm=round(w * h / 1e6, 4),
                                    source="text_annotation",
                                    layer=layer,
                                    entity_idx=entity_idx,
                                ))
                            # Also store raw dimension text
                            if dims or any(c.isdigit() for c in txt):
                                if txt not in all_text_annotations:
                                    all_text_annotations.append(txt)

                    # ── DIMENSION entities ────────────────────────────────
                    elif dxf_type == 'DIMENSION':
                        try:
                            # Try to get the measurement value
                            if hasattr(entity.dxf, 'text') and entity.dxf.text:
                                txt = entity.dxf.text.strip()
                                if txt and txt not in all_text_annotations:
                                    all_text_annotations.append(txt)
                            # Also try the actual_measurement
                            if hasattr(entity, 'get_measurement'):
                                meas = entity.get_measurement()
                                if meas and meas > 0:
                                    meas_str = f"{meas:.1f}mm"
                                    if meas_str not in all_text_annotations:
                                        all_text_annotations.append(meas_str)
                        except Exception:
                            pass

                    # ── INSERT (block references) → windows, doors ────────
                    elif dxf_type == 'INSERT':
                        try:
                            block_name = entity.dxf.name
                            layer = entity.dxf.layer if hasattr(entity.dxf, 'layer') else ""

                            if block_name not in all_blocks:
                                # Determine block type
                                block_type = "generic"
                                if _WINDOW_PATTERNS.search(block_name) or _WINDOW_PATTERNS.search(layer):
                                    block_type = "window"
                                elif _DOOR_PATTERNS.search(block_name) or _DOOR_PATTERNS.search(layer):
                                    block_type = "door"

                                block_bounds = None
                                try:
                                    block_def = doc.blocks.get(block_name)
                                    if block_def:
                                        bb = BoundingBox()
                                        for bent in block_def:
                                            b = _safe_bounds(bent)
                                            if b:
                                                bb.extend([Vec3(b.min_x, b.min_y, 0), Vec3(b.max_x, b.max_y, 0)])
                                        if not bb.is_empty:
                                            xscale = getattr(entity.dxf, 'xscale', 1.0) or 1.0
                                            yscale = getattr(entity.dxf, 'yscale', 1.0) or 1.0
                                            w = abs(bb.size.x * xscale)
                                            h = abs(bb.size.y * yscale)
                                            ins = entity.dxf.insert
                                            block_bounds = BoundsInfo(ins.x, ins.y, ins.x + w, ins.y + h)
                                except Exception:
                                    pass

                                all_blocks[block_name] = BlockInfo(
                                    name=block_name,
                                    count=1,
                                    bounds=block_bounds,
                                    block_type=block_type,
                                )
                            else:
                                all_blocks[block_name].count += 1

                            # If it's a window/door, also add to openings
                            bi = all_blocks[block_name]
                            if bi.block_type in ('window', 'door') and bi.bounds:
                                w = bi.bounds.width
                                h = bi.bounds.height
                                if w > 50 and h > 50:  # sanity check
                                    all_openings.append(OpeningInfo(
                                        type=bi.block_type,
                                        width_mm=round(max(w, h), 1),
                                        height_mm=round(min(w, h), 1),
                                        area_sqm=round(w * h / 1e6, 4),
                                        block_name=block_name,
                                        layer=layer,
                                        entity_idx=entity_idx,
                                    ))
                        except Exception as e:
                            logger.debug(f"Error processing INSERT: {e}")

                    # ── HATCH entities → could indicate panel fills ───────
                    elif dxf_type == 'HATCH':
                        pass  # Tracked in bounds

                except Exception as e:
                    # Never crash on a single entity
                    logger.debug(f"Error processing entity in {layout_name}: {e}")
                    continue

                entity_idx += 1

            # Build layout info
            lb = None
            if not layout_bbox.is_empty:
                lb = BoundsInfo(
                    layout_bbox.extmin.x, layout_bbox.extmin.y,
                    layout_bbox.extmax.x, layout_bbox.extmax.y,
                )

            layouts_info.append({
                "name": layout_name,
                "entity_count": layout_entity_count,
                "bounds": lb.to_dict() if lb else None,
            })

        # ── Spatial clustering to detect overlapping drawings ─────────────────
        clusters = _cluster_entities(entity_bounds_for_clustering, CLUSTER_DISTANCE_MM)
        if len(clusters) > 1:
            warnings.append(
                f"Detected {len(clusters)} spatially distinct drawing groups "
                f"(possible overlapping drawings in model space)"
            )

        # Build entity_idx → cluster_id mapping for spatial deduplication
        entity_to_cluster: dict[int, int] = {}
        for cluster_id, entity_indices in enumerate(clusters):
            for eidx in entity_indices:
                entity_to_cluster[eidx] = cluster_id

        # Classify clusters as plan/elevation/section
        cluster_classification = self._classify_clusters(clusters, entity_bounds_for_clustering)

        # Detect Paper Space layout views
        paper_space_views = self._detect_paper_space_views(doc)

        # ── Deduplicate panels with spatial-cluster awareness ─────────────────
        # When multiple spatial clusters exist (overlapping drawing views),
        # the same panel may appear in each view. We count per-cluster first,
        # then take the MAX count across clusters (not the sum) to avoid
        # double-counting panels drawn in multiple overlapping views.
        if len(clusters) > 1:
            # Phase 1: count panels per (dimension_key, cluster_id)
            # key = (width, height, source), value = {cluster_id: count}
            cluster_panel_counts: dict[tuple[float, float, str], dict[int, int]] = {}
            cluster_panel_meta: dict[tuple[float, float, str], PanelInfo] = {}
            for p in all_panels:
                dim_key = (p.width_mm, p.height_mm, p.source)
                cid = entity_to_cluster.get(p.entity_idx, 0)
                if dim_key not in cluster_panel_counts:
                    cluster_panel_counts[dim_key] = {}
                    cluster_panel_meta[dim_key] = p
                cluster_panel_counts[dim_key][cid] = cluster_panel_counts[dim_key].get(cid, 0) + 1

            # Phase 2: for each panel dimension, take MAX count across clusters
            deduped_panels: list[PanelInfo] = []
            for dim_key, counts_by_cluster in cluster_panel_counts.items():
                max_count = max(counts_by_cluster.values())
                meta = cluster_panel_meta[dim_key]
                deduped_panels.append(PanelInfo(
                    width_mm=meta.width_mm,
                    height_mm=meta.height_mm,
                    area_sqm=meta.area_sqm,
                    count=max_count,
                    source=meta.source,
                    layer=meta.layer,
                ))
        else:
            # Single cluster or no clusters: simple merge by dimension
            panel_counts: dict[tuple[float, float, str], PanelInfo] = {}
            for p in all_panels:
                key = (p.width_mm, p.height_mm, p.source)
                if key in panel_counts:
                    panel_counts[key].count += 1
                else:
                    panel_counts[key] = PanelInfo(
                        width_mm=p.width_mm,
                        height_mm=p.height_mm,
                        area_sqm=p.area_sqm,
                        count=1,
                        source=p.source,
                        layer=p.layer,
                    )
            deduped_panels = list(panel_counts.values())

        # ── Deduplicate openings with spatial-cluster awareness ───────────────
        if len(clusters) > 1:
            cluster_opening_counts: dict[tuple[str, float, float], dict[int, int]] = {}
            cluster_opening_meta: dict[tuple[str, float, float], OpeningInfo] = {}
            for o in all_openings:
                dim_key = (o.block_name or o.type, o.width_mm, o.height_mm)
                cid = entity_to_cluster.get(o.entity_idx, 0)
                if dim_key not in cluster_opening_counts:
                    cluster_opening_counts[dim_key] = {}
                    cluster_opening_meta[dim_key] = o
                cluster_opening_counts[dim_key][cid] = cluster_opening_counts[dim_key].get(cid, 0) + 1

            deduped_openings: list[OpeningInfo] = []
            for dim_key, counts_by_cluster in cluster_opening_counts.items():
                max_count = max(counts_by_cluster.values())
                meta = cluster_opening_meta[dim_key]
                deduped_openings.append(OpeningInfo(
                    type=meta.type,
                    width_mm=meta.width_mm,
                    height_mm=meta.height_mm,
                    area_sqm=meta.area_sqm,
                    block_name=meta.block_name,
                    count=max_count,
                    layer=meta.layer,
                ))
        else:
            opening_counts: dict[tuple[str, float, float], OpeningInfo] = {}
            for o in all_openings:
                key = (o.block_name or o.type, o.width_mm, o.height_mm)
                if key in opening_counts:
                    opening_counts[key].count += 1
                else:
                    opening_counts[key] = OpeningInfo(
                        type=o.type,
                        width_mm=o.width_mm,
                        height_mm=o.height_mm,
                        area_sqm=o.area_sqm,
                        block_name=o.block_name,
                        count=1,
                        layer=o.layer,
                    )
            deduped_openings = list(opening_counts.values())

        # ── Turkish DXF: extract window/door dimensions from annotation layers ──
        turkish_openings = self._extract_turkish_openings(doc, warnings)
        if turkish_openings:
            # Turkish extraction found openings — merge with (or replace) existing
            if not deduped_openings:
                deduped_openings = turkish_openings
            else:
                deduped_openings.extend(turkish_openings)
            logger.info(f"Turkish DXF extraction: {len(turkish_openings)} opening types found")

        # ── Compute total facade area ─────────────────────────────────────────
        total_facade_area = sum(p.area_sqm * p.count for p in deduped_panels)
        # Include opening areas in total facade area if panels are sparse
        opening_area = sum(o.area_sqm * o.count for o in deduped_openings)
        if opening_area > total_facade_area:
            total_facade_area = opening_area

        # ── Deduplicate text annotations ──────────────────────────────────────
        unique_texts = list(dict.fromkeys(all_text_annotations))  # preserve order, remove dupes

        # ── Build result ──────────────────────────────────────────────────────
        # Enrich openings with Glazetech system classification
        enriched_openings = []
        for o in deduped_openings:
            if o.type == "door":
                # Classify door type from block name
                bname = o.block_name.lower() if o.block_name else ""
                if 'fm-door4' in bname or 'fm-door3' in bname or o.width_mm >= 1800:
                    system_type = "Door - Double Swing"
                elif o.width_mm >= 2000:
                    system_type = "Door - Sliding"
                else:
                    system_type = "Door - Single Swing"
                system_series = "GT-LSTB"
                system_name = "Glazetech Lift and Slide Thermal Break (Door)"
                thermal_break = True
                glazetech_profile = GLAZETECH_CATALOG["lift_and_slide_tb"]
            else:
                o_has_railing = getattr(o, 'has_railing', False)
                glazetech_profile = classify_glazetech_system(
                    o.width_mm, o.height_mm, opening_type=o.type, has_railing=o_has_railing
                )
                system_type = glazetech_profile["system_type"]
                system_series = glazetech_profile["series"]
                system_name = glazetech_profile["name"]
                thermal_break = glazetech_profile["thermal_break"]

            # Look up DXF bounding box for shop drawing rendering
            o_entity_idx = getattr(o, 'entity_idx', -1)
            dxf_bbox = None
            if o_entity_idx >= 0:
                for idx, bounds in entity_bounds_for_clustering:
                    if idx == o_entity_idx:
                        dxf_bbox = bounds.to_dict()
                        break

            enriched_openings.append({
                "type": o.type,
                "width_mm": o.width_mm,
                "height_mm": o.height_mm,
                "area_sqm": o.area_sqm,
                "block_name": o.block_name,
                "count": o.count,
                "layer": o.layer,
                "floor": getattr(o, 'floor', ''),
                "elevation": getattr(o, 'elevation', ''),
                "entity_idx": o_entity_idx,
                "dxf_bbox": dxf_bbox,
                "system_type": system_type,
                "system_series": system_series,
                "system_name": system_name,
                "thermal_break": thermal_break,
                "glazetech_profile": glazetech_profile,
                "dxf_panel_hint": getattr(o, 'dxf_panel_hint', 0),
            })

        # Include building data from Turkish extraction
        building_data = getattr(self, '_turkish_floor_data', {})

        return {
            "layouts": layouts_info,
            "panels": [
                {
                    "width_mm": p.width_mm,
                    "height_mm": p.height_mm,
                    "area_sqm": p.area_sqm,
                    "count": p.count,
                    "source": p.source,
                    "layer": p.layer,
                }
                for p in deduped_panels
            ],
            "openings": enriched_openings,
            "text_annotations": unique_texts[:500],  # Cap at 500 to avoid huge responses
            "blocks": [
                {
                    "name": bi.name,
                    "count": bi.count,
                    "bounds": bi.bounds.to_dict() if bi.bounds else None,
                    "block_type": bi.block_type,
                }
                for bi in all_blocks.values()
            ],
            "total_facade_area_sqm": round(total_facade_area, 2),
            "warnings": warnings,
            "metadata": {
                "file_size_mb": round(file_size_mb, 2),
                "total_entities": entity_idx,
                "total_layouts": len(layouts_info),
                "spatial_clusters": len(clusters),
                "unique_blocks": len(all_blocks),
                "unique_layers": self._count_layers(doc),
                "cluster_classification": cluster_classification,
                "paper_space_views": paper_space_views,
                "entity_to_cluster": {str(k): v for k, v in entity_to_cluster.items()},
                "building_data": building_data,
                "glazetech_catalog": {k: {kk: vv for kk, vv in v.items() if kk != "glazing_range_mm"} for k, v in GLAZETECH_CATALOG.items()},
                "profile_supplier": "Elite Extrusion L.L.C",
                "thermal_break_required": True,
            },
        }

    def _classify_clusters(self, clusters: list[list[int]], entity_bounds: list[tuple[int, BoundsInfo]]) -> list[dict]:
        """Classify each spatial cluster as plan/elevation/section based on geometry."""
        bounds_map = {idx: b for idx, b in entity_bounds}

        classified = []
        for i, cluster_indices in enumerate(clusters):
            min_x = min_y = float('inf')
            max_x = max_y = float('-inf')
            for eidx in cluster_indices:
                b = bounds_map.get(eidx)
                if b:
                    min_x = min(min_x, b.min_x)
                    min_y = min(min_y, b.min_y)
                    max_x = max(max_x, b.max_x)
                    max_y = max(max_y, b.max_y)

            if min_x == float('inf'):
                continue

            width = max_x - min_x
            height = max_y - min_y
            aspect = width / max(height, 1)

            if aspect > 2.5:
                view_type = "plan"
            elif aspect < 0.4:
                view_type = "section"
            else:
                view_type = "elevation"

            classified.append({
                "cluster_index": i,
                "view_type": view_type,
                "bbox": {"min_x": round(min_x, 2), "min_y": round(min_y, 2),
                         "max_x": round(max_x, 2), "max_y": round(max_y, 2)},
                "aspect_ratio": round(aspect, 3),
                "entity_count": len(cluster_indices),
                "center_x": (min_x + max_x) / 2,
            })

        elevations = [c for c in classified if c["view_type"] == "elevation"]
        elevations.sort(key=lambda c: c["center_x"])
        for idx, elev in enumerate(elevations):
            elev["elevation_code"] = f"E{idx + 1}"

        return classified

    def _detect_paper_space_views(self, doc) -> list[dict]:
        """Detect view types from Paper Space layout names."""
        views = []
        try:
            for layout in doc.layouts:
                if layout.name == "Model":
                    continue
                name_lower = layout.name.lower()
                view_type = None
                elevation_direction = None

                if any(kw in name_lower for kw in ["plan", "floor plan", "ground", "typical", "roof plan"]):
                    view_type = "plan"
                elif any(kw in name_lower for kw in ["section", "detail", "cross"]):
                    view_type = "section"
                else:
                    for direction, keywords in [
                        ("N", ["north", "front"]),
                        ("S", ["south", "rear", "back"]),
                        ("E", ["east", "right"]),
                        ("W", ["west", "left"]),
                    ]:
                        if any(kw in name_lower for kw in keywords):
                            view_type = "elevation"
                            elevation_direction = direction
                            break
                    if not view_type and any(kw in name_lower for kw in ["elev", "elevation"]):
                        view_type = "elevation"

                if view_type:
                    views.append({
                        "layout_name": layout.name,
                        "view_type": view_type,
                        "elevation_direction": elevation_direction,
                    })
        except Exception as e:
            logger.debug(f"Error detecting paper space views: {e}")
        return views

    def _extract_turkish_openings(self, doc, warnings: list[str]) -> list:
        """
        Extract window/door openings from Turkish architectural DXF files.

        Turkish DXFs use layers like:
          - penc-yazi: window dimension texts ("530/220" = 530cm x 220cm)
          - Pencere: window polylines
          - Kapı-Pencere, KAPI_PENCERE: door-window layers
          - kapi: door block insertions
          - iç ölçü: floor plan labels

        IMPORTANT: Turkish DXFs often have TWO sets of penc-yazi annotations:
          1. Modelspace: structural bay sizes (e.g., "530/220" = 5300mm multi-panel opening)
          2. Inside floor plan blocks (e.g., "RST FLOOR"): individual window sizes
             (e.g., "150/220" = 1500mm single window panel)

        We prefer individual window sizes from block definitions when available,
        as these represent the actual fabrication units.

        Returns list of OpeningInfo with proper counts per floor.
        """
        openings = []

        try:
            msp = doc.modelspace()
            entities = list(msp)
        except Exception as e:
            logger.debug(f"Turkish extraction: cannot access modelspace: {e}")
            return openings

        # ── Step 1: Extract window dimension texts from annotation layers ────
        # Turkish DXFs have two annotation sources:
        #   a) Inside block definitions (e.g., "RST FLOOR", "LAST"): individual window sizes
        #   b) In modelspace: structural bay sizes (multi-panel opening widths)
        # We prefer (a) when available, as those are the real fabrication units.

        # 1a. Count how many times each block is inserted in modelspace
        block_insert_counts = {}  # block_name -> insert count
        for e in entities:
            try:
                if e.dxftype() == 'INSERT':
                    bname = e.dxf.name
                    block_insert_counts[bname] = block_insert_counts.get(bname, 0) + 1
            except Exception:
                continue

        # 1b. Scan block definitions for penc-yazi annotations
        # Only consider blocks that are actually inserted in modelspace
        block_openings_data = {}  # block_name -> {(w_mm, h_mm): count_per_block}
        try:
            for block in doc.blocks:
                block_name = block.name
                if block_name.startswith('*') or block_name.startswith('_'):
                    continue
                # Only process blocks that are inserted in modelspace
                if block_name not in block_insert_counts:
                    continue
                dims_in_block = []
                for e in block:
                    try:
                        if e.dxftype() != 'TEXT':
                            continue
                        layer = e.dxf.layer if hasattr(e.dxf, 'layer') else ''
                        if not _TURKISH_DIM_LAYERS.search(layer):
                            continue
                        text = e.dxf.text.strip()
                        match = _DIM_PATTERN_SLASH_CM.match(text)
                        if match:
                            w_cm = float(match.group(1))
                            h_cm = float(match.group(2))
                            w_mm = w_cm * 10
                            h_mm = h_cm * 10
                            if 300 <= w_mm <= 15000 and 300 <= h_mm <= 15000:
                                dims_in_block.append((w_mm, h_mm))
                    except Exception:
                        continue
                if dims_in_block:
                    from collections import Counter as _Ctr
                    block_openings_data[block_name] = dict(_Ctr(dims_in_block))
        except Exception as e:
            logger.debug(f"Turkish extraction: error scanning block definitions: {e}")

        # 1c. Map annotations → fm-win* block type to determine panel config
        # Panel counts verified from actual DXF block geometry (track mark analysis):
        #   fm-win1 (100cm base): 2 edge clusters, 1 panel region => 1 fixed panel
        #   fm-win2 (120cm base): 3 clusters, 2 panel regions => 2-panel sliding
        #   fm-win3 (180cm base): 4 clusters, 3 panel regions => 3-panel sliding
        #   fm-win4 (240cm base): 5 clusters, 4 panel regions => 4-panel sliding
        #   fm-win5 (360cm base): 7 clusters, 6 panel regions => 6-panel sliding
        _WIN_BLOCK_BASE_W_CM = {
            'fm-win1': 100, 'fm-win2': 120, 'fm-win3': 180, 'fm-win4': 240, 'fm-win5': 360,
        }
        _WIN_BLOCK_PANELS = {
            'fm-win1': 1, 'fm-win2': 2, 'fm-win3': 3, 'fm-win4': 4, 'fm-win5': 6,
        }
        # dim_panel_hints: (w_mm, h_mm) → list of (panel_count, qty)
        dim_panel_hints = {}

        if block_openings_data:
            for bname_outer in block_openings_data:
                try:
                    block_def = doc.blocks.get(bname_outer)
                    if not block_def:
                        continue
                except Exception:
                    continue

                num_inserts = block_insert_counts.get(bname_outer, 0)
                if num_inserts == 0:
                    continue

                # Collect annotation positions + fm-win* inserts with actual widths
                annot_list = []  # (w_mm, h_mm, x, y)
                win_inserts = []  # (fm_win_name, actual_w_mm, x, y)

                for e in block_def:
                    try:
                        if e.dxftype() == 'TEXT':
                            layer = e.dxf.layer if hasattr(e.dxf, 'layer') else ''
                            if _TURKISH_DIM_LAYERS.search(layer):
                                text = e.dxf.text.strip()
                                match = _DIM_PATTERN_SLASH_CM.match(text)
                                if match:
                                    w_mm = float(match.group(1)) * 10
                                    h_mm = float(match.group(2)) * 10
                                    x = e.dxf.insert.x if hasattr(e.dxf, 'insert') else 0
                                    y = e.dxf.insert.y if hasattr(e.dxf, 'insert') else 0
                                    annot_list.append((w_mm, h_mm, x, y))
                        elif e.dxftype() == 'INSERT':
                            inner_name = e.dxf.name.lower()
                            if inner_name in _WIN_BLOCK_BASE_W_CM:
                                xs = abs(getattr(e.dxf, 'xscale', 1.0) or 1.0)
                                actual_w_mm = _WIN_BLOCK_BASE_W_CM[inner_name] * xs * 10
                                x = e.dxf.insert.x if hasattr(e.dxf, 'insert') else 0
                                y = e.dxf.insert.y if hasattr(e.dxf, 'insert') else 0
                                win_inserts.append((inner_name, actual_w_mm, x, y))
                    except Exception:
                        continue

                # Build a map of unique fm-win block types with their actual widths
                # For each unique annotation dimension, find best matching block type
                # based on width similarity (not proximity — blocks may not be 1:1 with annotations)
                unique_win_widths = {}  # fm_win_name -> set of actual widths
                for win_name, win_w_mm, wx, wy in win_inserts:
                    if win_name not in unique_win_widths:
                        unique_win_widths[win_name] = set()
                    unique_win_widths[win_name].add(round(win_w_mm))

                # Collect unique annotation dimensions in this block
                from collections import Counter as _AnnCtr
                annot_dims = _AnnCtr((w_mm, h_mm) for w_mm, h_mm, _, _ in annot_list)

                for (w_mm, h_mm), count in annot_dims.items():
                    # Find best fm-win type by width similarity
                    best_block = None
                    best_w_diff = float('inf')
                    for win_name, widths in unique_win_widths.items():
                        for ww in widths:
                            w_diff = abs(w_mm - ww)
                            if w_diff < best_w_diff:
                                best_w_diff = w_diff
                                best_block = win_name

                    # Only assign if width match is reasonable (< 50% of annotation width)
                    if best_block and best_w_diff < w_mm * 0.5:
                        panel_count = _WIN_BLOCK_PANELS[best_block]
                    else:
                        panel_count = 0

                    key = (w_mm, h_mm)
                    if key not in dim_panel_hints:
                        dim_panel_hints[key] = []
                    # Each annotation in this block contributes count × inserts
                    dim_panel_hints[key].append((panel_count, count * num_inserts))

            logger.info(f"Turkish DXF: panel hints from block types: {dict((k, [(p,q) for p,q in v]) for k,v in dim_panel_hints.items())}")

        # 1d. If we found block-level annotations, use them directly
        # Each block's annotation count × insert count = total openings from that block
        use_block_level = bool(block_openings_data)

        if use_block_level:
            # Aggregate: for each (w, h), sum across all blocks: per_block_count × insert_count
            from collections import Counter
            aggregated_dims = Counter()
            for bname, dim_counts in block_openings_data.items():
                num_inserts = block_insert_counts.get(bname, 0)
                for (w_mm, h_mm), per_block_count in dim_counts.items():
                    aggregated_dims[(w_mm, h_mm)] += per_block_count * num_inserts

            logger.info(
                f"Turkish DXF: using block-level annotations — "
                f"{len(block_openings_data)} blocks with window dims: "
                f"{', '.join(f'{k}(×{block_insert_counts.get(k, 0)})' for k in block_openings_data)}"
            )

            # Build dim_texts as dummy entries so the rest of the pipeline
            # (floor plan extraction, facade labels, etc.) still works.
            # The actual opening creation is short-circuited below.
            dim_texts = [(f"{int(w/10)}/{int(h/10)}", 0, 0, "penc-yazi")
                         for (w, h) in aggregated_dims]

        else:
            # 1d. Fall back to modelspace annotations (structural bay sizes)
            dim_texts = []
            for e in entities:
                try:
                    if e.dxftype() != 'TEXT':
                        continue
                    layer = e.dxf.layer if hasattr(e.dxf, 'layer') else ''
                    if not _TURKISH_DIM_LAYERS.search(layer):
                        continue
                    text = e.dxf.text.strip()
                    x = e.dxf.insert.x if hasattr(e.dxf, 'insert') else 0
                    y = e.dxf.insert.y if hasattr(e.dxf, 'insert') else 0
                    dim_texts.append((text, x, y, layer))
                except Exception:
                    continue

        if not dim_texts and not use_block_level:
            return openings

        logger.info(f"Turkish DXF: found {len(dim_texts)} dimension texts on annotation layers")

        # ── Step 2: Parse W/H dimensions from slash-format texts ─────────────
        parsed_dims = []  # (width_mm, height_mm, x, y, layer)
        for text, x, y, layer in dim_texts:
            match = _DIM_PATTERN_SLASH_CM.match(text)
            if match:
                # Turkish DXFs use cm: "530/220" = 530cm wide × 220cm high = 5300mm × 2200mm
                w_cm = float(match.group(1))
                h_cm = float(match.group(2))
                w_mm = w_cm * 10
                h_mm = h_cm * 10
                if 300 <= w_mm <= 15000 and 300 <= h_mm <= 15000:
                    parsed_dims.append((w_mm, h_mm, x, y, layer))
            else:
                # Try standard patterns too
                for pattern in _DIM_PATTERNS:
                    m = pattern.search(text)
                    if m:
                        w = float(m.group(1))
                        h = float(m.group(2))
                        if MIN_PANEL_DIM_MM <= w <= MAX_PANEL_DIM_MM and MIN_PANEL_DIM_MM <= h <= MAX_PANEL_DIM_MM:
                            parsed_dims.append((w, h, x, y, layer))
                        break

        if not parsed_dims and not use_block_level:
            return openings

        # ── Step 3: Extract floor plan labels to determine floor structure ───
        floor_plans = []  # (label, x, y, floors_list)
        for e in entities:
            try:
                if e.dxftype() != 'TEXT':
                    continue
                text = e.dxf.text.strip()
                if 'FLOOR' not in text.upper() and 'BASEMENT' not in text.upper():
                    continue
                x = e.dxf.insert.x if hasattr(e.dxf, 'insert') else 0
                y = e.dxf.insert.y if hasattr(e.dxf, 'insert') else 0

                # Parse floor info
                floors = self._parse_floor_label(text)
                if floors:
                    floor_plans.append((text, x, y, floors))
            except Exception:
                continue

        # ── Step 4: Determine how many typical floors the openings apply to ──
        # Count distinct floor identifiers from floor plan labels
        all_floors = set()
        for _, _, _, floors in floor_plans:
            all_floors.update(floors)

        # Typical residential floors (default to what we found)
        typical_floors = sorted([f for f in all_floors if f not in ('B1', 'B2', 'B3', 'GF', 'RF', 'LAST')])
        basement_floors = sorted([f for f in all_floors if f.startswith('B')])
        has_ground = 'GF' in all_floors
        has_last = 'LAST' in all_floors or 'RF' in all_floors

        num_typical = len(typical_floors) if typical_floors else 1

        # ── Step 5: Determine per-floor window types and quantities ────────
        from collections import Counter

        if use_block_level:
            # Block-level path: aggregated_dims already has correct totals
            # (per_block_count × insert_count for each block)
            dim_counter = aggregated_dims
            num_plan_copies = 1  # Not used in block-level path
            logger.info(
                f"Turkish DXF: {len(dim_counter)} unique window types from "
                f"block-level annotations (totals already computed from insert counts)"
            )
        else:
            # Modelspace path: cluster dimension texts to find per-floor window types
            dim_counter = Counter((w, h) for w, h, _, _, _ in parsed_dims)

            def _cluster_1d(values, gap_threshold):
                """Cluster sorted 1D values by gap."""
                if not values:
                    return []
                clusters = [[values[0]]]
                for v in values[1:]:
                    if v - clusters[-1][-1] > gap_threshold:
                        clusters.append([v])
                    else:
                        clusters[-1].append(v)
                return clusters

            raw_x = sorted(set(x for _, _, x, _, _ in parsed_dims))
            raw_y = sorted(set(y for _, _, _, y, _ in parsed_dims))

            x_groups = _cluster_1d(raw_x, 2500)
            y_groups = _cluster_1d(raw_y, 3000)

            num_plan_copies = len(x_groups) * len(y_groups)
            if num_plan_copies < 1:
                num_plan_copies = 1

            logger.info(
                f"Turkish DXF: {len(dim_counter)} unique window types, "
                f"{num_typical} typical floors, {num_plan_copies} plan copies"
            )

        # ── Step 5b: Extract facade labels and building metadata ─────────────
        facade_labels = []  # (facade_name, x, y)
        section_labels = []
        room_labels = []  # (room_type, x, y)
        railing_labels = []
        for e in entities:
            try:
                if e.dxftype() not in ('TEXT', 'MTEXT'):
                    continue
                txt = e.dxf.text.strip() if e.dxftype() == 'TEXT' else (e.text or '').strip()
                txt_upper = txt.upper()
                x = e.dxf.insert.x if hasattr(e.dxf, 'insert') else 0
                y = e.dxf.insert.y if hasattr(e.dxf, 'insert') else 0

                # Facade labels
                if 'FACADE' in txt_upper:
                    for direction in FACADE_DIRECTION_MAP:
                        if direction in txt_upper:
                            facade_labels.append((FACADE_DIRECTION_MAP[direction], x, y))
                            break

                # Section labels
                if 'SECTION' in txt_upper:
                    section_labels.append((txt.strip(), x, y))

                # Room labels (on yazi layer)
                layer = e.dxf.layer if hasattr(e.dxf, 'layer') else ''
                if layer.lower() in ('yazi', 'yazı'):
                    if 'BALCON' in txt_upper:
                        room_labels.append(('BALCONY', x, y))
                    elif 'RAILING' in txt_upper:
                        railing_labels.append(('RAILING', x, y))
                    elif any(kw in txt_upper for kw in ['BEDROOM', 'KITCHEN', 'HALL', 'LIVING', 'BATHROOM', 'WC']):
                        room_labels.append((txt_upper.strip(), x, y))
            except Exception:
                continue

        # ── Step 5c: Extract floor-to-floor heights from section ──────────────
        floor_heights = {}
        section_floor_texts = []
        for e in entities:
            try:
                if e.dxftype() != 'TEXT':
                    continue
                txt = e.dxf.text.strip().upper()
                x = e.dxf.insert.x if hasattr(e.dxf, 'insert') else 0
                y = e.dxf.insert.y if hasattr(e.dxf, 'insert') else 0
                # Only look near section areas
                if section_labels and any(abs(x - sx) < 10000 for _, sx, _ in section_labels):
                    if 'FLOOR' in txt or 'BASEMENT' in txt:
                        section_floor_texts.append((txt, y))
            except Exception:
                continue

        if len(section_floor_texts) >= 2:
            section_floor_texts.sort(key=lambda t: t[1])  # sort by Y (bottom to top)
            for i in range(1, len(section_floor_texts)):
                prev_name, prev_y = section_floor_texts[i - 1]
                curr_name, curr_y = section_floor_texts[i]
                delta_y = abs(curr_y - prev_y)
                # Interpret as cm → meters
                height_m = round(delta_y / 100, 2)
                if 2.0 <= height_m <= 6.0:
                    floor_heights[curr_name] = height_m

        # ── Step 6: Create OpeningInfo records with Glazetech classification ──
        for (w_mm, h_mm), total_count in dim_counter.most_common():
            if use_block_level:
                # Block-level: total_count already includes insert multipliers
                # e.g., RST FLOOR has 4× "150/220" and is inserted 9 times → 36 total
                total_qty = total_count
            else:
                # Modelspace: divide by plan copies to get per-floor, then multiply
                per_floor = max(1, total_count // max(num_plan_copies, 1))
                total_qty = per_floor * num_typical

            # Classify to correct Glazetech system based on size
            glazetech = classify_glazetech_system(w_mm, h_mm)
            system_type = glazetech["system_type"]
            series = glazetech["series"]
            block_name = f"{series}-{int(w_mm)}x{int(h_mm)}"

            area_sqm = round(w_mm * h_mm / 1_000_000, 4)

            # Determine panel hint from DXF block type mapping
            panel_hint = 0
            hints = dim_panel_hints.get((w_mm, h_mm), [])
            if hints:
                # Use the most common panel count (weighted by qty)
                from collections import Counter as _PHCtr
                hint_votes = _PHCtr()
                for pc, qty in hints:
                    if pc > 0:
                        hint_votes[pc] += qty
                if hint_votes:
                    panel_hint = hint_votes.most_common(1)[0][0]

            opening = OpeningInfo(
                type="window",
                width_mm=round(w_mm, 1),
                height_mm=round(h_mm, 1),
                area_sqm=area_sqm,
                block_name=block_name,
                count=total_qty,
                layer="Pencere",
                dxf_panel_hint=panel_hint,
            )
            # Attach floor and system info as attributes
            opening.floor = ""  # Will be distributed across floors by opening_schedule_engine
            opening.elevation = ""

            openings.append(opening)

        # ── Step 7: Add door openings from kapi-yazi annotations ─────────────
        # Use architect's door dimension annotations (e.g. "90/220") on kapi-yazi
        # layer instead of deriving from xscale, which can be slightly off.
        _DOOR_DIM_LAYER = re.compile(r'(?i)kap.*yaz')
        _DOOR_H_CM = 220  # standard door height in Turkish DXFs
        # Fallback: known door block base widths for modelspace path
        _DOOR_BASE_W_CM = {'fm-door1': 100, 'fm-door2': 150, 'fm-door3': 200,
                           'fm-door4': 200, 'fm-door5': 250}

        if use_block_level:
            # Block-level path: extract door dimensions from kapi-yazi text annotations
            from collections import Counter as _DoorCtr
            aggregated_doors = _DoorCtr()  # (w_cm, h_cm) -> total_count

            for bname_outer in block_insert_counts:
                if bname_outer.startswith('*') or bname_outer.startswith('_'):
                    continue
                try:
                    block_def = doc.blocks.get(bname_outer)
                    if not block_def:
                        continue
                except Exception:
                    continue

                num_inserts = block_insert_counts.get(bname_outer, 0)
                if num_inserts == 0:
                    continue

                door_counts_in_block = _DoorCtr()
                for e in block_def:
                    try:
                        if e.dxftype() != 'TEXT':
                            continue
                        layer = e.dxf.layer if hasattr(e.dxf, 'layer') else ''
                        if not _DOOR_DIM_LAYER.search(layer):
                            continue
                        text = e.dxf.text.strip()
                        m = _DIM_PATTERN_SLASH_CM.match(text)
                        if m:
                            dw_cm = int(m.group(1))
                            dh_cm = int(m.group(2))
                            door_counts_in_block[(dw_cm, dh_cm)] += 1
                    except Exception:
                        continue

                for (dw_cm, dh_cm), per_block in door_counts_in_block.items():
                    aggregated_doors[(dw_cm, dh_cm)] += per_block * num_inserts

            for (dw_cm, dh_cm), total_qty in aggregated_doors.items():
                w_mm = dw_cm * 10.0
                h_mm = dh_cm * 10.0

                # Classify door type from width
                if w_mm >= 1800:
                    door_sys = "Door - Double Swing"
                else:
                    door_sys = "Door - Single Swing"

                opening = OpeningInfo(
                    type="door",
                    width_mm=w_mm,
                    height_mm=h_mm,
                    area_sqm=round(w_mm * h_mm / 1_000_000, 4),
                    block_name=f"door-{dw_cm}x{dh_cm}",
                    count=total_qty,
                    layer="kapi",
                )
                opening.floor = ""
                opening.elevation = ""
                openings.append(opening)

            if aggregated_doors:
                logger.info(
                    f"Turkish DXF: {len(aggregated_doors)} door types from "
                    f"kapi-yazi annotations, {sum(aggregated_doors.values())} total"
                )

        else:
            # Modelspace path: search modelspace for door INSERTs on kapi layer
            door_inserts = []
            door_positions = []
            for e in entities:
                try:
                    if e.dxftype() == 'INSERT' and hasattr(e.dxf, 'layer'):
                        layer_lower = e.dxf.layer.lower()
                        if 'kap' in layer_lower or 'door' in layer_lower:
                            block_name = e.dxf.name
                            x_scale = abs(getattr(e.dxf, 'xscale', 1.0) or 1.0)
                            y_scale = abs(getattr(e.dxf, 'yscale', 1.0) or 1.0)
                            door_inserts.append((block_name, x_scale, y_scale, e.dxf.layer))
                            ins = e.dxf.insert
                            door_positions.append((ins.x, ins.y))
                except Exception:
                    continue

            if door_inserts:
                door_counter = Counter(door_inserts)
                for (bname, xs, ys, layer), total_count in door_counter.items():
                    # Use known door block dimensions when available
                    if bname in _DOOR_BASE_W_CM:
                        w_mm = round(_DOOR_BASE_W_CM[bname] * xs) * 10.0
                        h_mm = _DOOR_H_CM * 10.0
                    else:
                        # Fallback: try bounding box
                        w_mm, h_mm = 1000.0, 2200.0
                        try:
                            block_def = doc.blocks.get(bname)
                            if block_def:
                                bb = BoundingBox()
                                for bent in block_def:
                                    b = _safe_bounds(bent)
                                    if b:
                                        bb.extend([Vec3(b.min_x, b.min_y, 0), Vec3(b.max_x, b.max_y, 0)])
                                if not bb.is_empty:
                                    w_mm = abs(bb.size.x * xs * 10)  # cm to mm
                                    h_mm = abs(bb.size.y * ys * 10)
                        except Exception:
                            pass

                    # Ensure width < height for doors
                    if w_mm > h_mm:
                        w_mm, h_mm = h_mm, w_mm

                    # Classify door type
                    if bname in ('fm-door4', 'fm-door3') or w_mm >= 1800:
                        door_sys = "Door - Double Swing"
                    else:
                        door_sys = "Door - Single Swing"

                    total_qty = total_count  # For modelspace, may need plan copy division

                    opening = OpeningInfo(
                        type="door",
                        width_mm=round(w_mm, 1),
                        height_mm=round(h_mm, 1),
                        area_sqm=round(w_mm * h_mm / 1_000_000, 4),
                        block_name=bname,
                        count=total_qty,
                        layer=layer,
                    )
                    opening.floor = ""
                    opening.elevation = ""
                    openings.append(opening)

        # ── Step 8: Add building metadata for downstream engines ─────────────
        if openings:
            warnings.append(
                f"Turkish DXF extraction: {len(openings)} opening types, "
                f"{sum(o.count for o in openings)} total units across "
                f"{num_typical} typical floors"
            )

            # Store floor structure metadata for downstream engines
            self._turkish_floor_data = {
                "typical_floors": typical_floors,
                "basement_floors": basement_floors,
                "has_ground": has_ground,
                "has_last": has_last,
                "num_typical": num_typical,
                "total_floors": len(all_floors),
                "floor_area_sqm": 841.94,  # Will be overridden if found in text
                "facades": [f[0] for f in facade_labels],
                "facade_positions": {f[0]: {"x": round(f[1], 1), "y": round(f[2], 1)} for f in facade_labels},
                "sections": [s[0] for s in section_labels],
                "floor_heights_m": floor_heights,
                "balcony_count": len([r for r in room_labels if r[0] == 'BALCONY']),
                "railing_count": len(railing_labels),
                "room_counts": {},
                "glazetech_systems": list(GLAZETECH_CATALOG.keys()),
                "profile_supplier": "Elite Extrusion L.L.C",
                "thermal_break_required": True,
            }

            # Count rooms
            from collections import Counter as _Counter
            room_type_counts = _Counter(r[0] for r in room_labels)
            self._turkish_floor_data["room_counts"] = dict(room_type_counts)

            # Try to extract floor area from text
            for e in entities:
                try:
                    if e.dxftype() == 'TEXT':
                        text = e.dxf.text
                        area_match = re.search(r'AREA:\s*([\d,.]+)\s*m', text)
                        if area_match:
                            area_str = area_match.group(1).replace(',', '.')
                            self._turkish_floor_data["floor_area_sqm"] = float(area_str)
                            break
                except Exception:
                    continue

        return openings

    def _parse_floor_label(self, text: str) -> list[str]:
        """Parse a floor plan label into a list of floor identifiers."""
        floors = []
        text_upper = text.upper().strip()

        # "1,2,3,4,5,6,7,8,9TH FLOOR PLAN" → ['1F', '2F', ..., '9F']
        multi_match = re.match(r'([\d,]+)\s*(ST|ND|RD|TH)\s+FLOOR', text_upper)
        if multi_match:
            nums = multi_match.group(1).split(',')
            for n in nums:
                n = n.strip()
                if n.isdigit():
                    floors.append(f"{n}F")
            return floors

        # "-1. BASEMENT" → 'B1', "-2. BASEMENT" → 'B2'
        base_match = re.match(r'-?(\d+)\.?\s*BASEMENT', text_upper)
        if base_match:
            return [f"B{base_match.group(1)}"]

        # "GROUND FLOOR" → 'GF'
        if 'GROUND' in text_upper:
            return ['GF']

        # "LAST FLOOR" → 'LAST'
        if 'LAST' in text_upper:
            return ['LAST']

        # "ROOF" → 'RF'
        if 'ROOF' in text_upper:
            return ['RF']

        # "1ST FLOOR", "2ND FLOOR", "3RD FLOOR", "10TH FLOOR"
        single_match = re.match(r'(\d+)\s*(ST|ND|RD|TH)\s+FLOOR', text_upper)
        if single_match:
            return [f"{single_match.group(1)}F"]

        return floors

    def _count_layers(self, doc) -> int:
        """Count layers in the document."""
        try:
            return len(doc.layers)
        except Exception:
            return 0

    def _empty_result(self, warnings: list[str] | None = None) -> dict:
        """Return an empty result dict with optional warnings."""
        return {
            "layouts": [],
            "panels": [],
            "openings": [],
            "text_annotations": [],
            "blocks": [],
            "total_facade_area_sqm": 0,
            "warnings": warnings or [],
            "metadata": {
                "file_size_mb": 0,
                "total_entities": 0,
                "total_layouts": 0,
                "spatial_clusters": 0,
                "unique_blocks": 0,
                "unique_layers": 0,
                "cluster_classification": [],
                "paper_space_views": [],
                "entity_to_cluster": {},
            },
        }

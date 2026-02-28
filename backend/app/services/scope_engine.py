"""
Scope Identification Engine — Facade system discovery and item code assignment.

Consumes DWG layer geometry (output of DWGParserService.extract_geometry) and
optional spec text, then produces a structured ProjectScope with:
  - Per-system totals (SQM, LM, opening count)
  - Item codes in format {TYPE}-{ELEVATION}-{FLOOR}-{SEQ:03d}
  - RFI flags for cross-reference gaps (system in DWG but not spec, vice versa)
  - Confidence rating per system (HIGH / MEDIUM / LOW)

Public API (backward-compatible):
    engine = ScopeIdentificationEngine(consultant_dictionary=[...])
    scope  = engine.identify_project_scope(dwg_extraction, spec_text)
"""
from __future__ import annotations

import os
import re
import logging
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Optional

logger = logging.getLogger("masaad-scope")


# ── FACADE SYSTEM TAXONOMY (35 types) ─────────────────────────────────────────
#
# Schema per entry:
#   layer_patterns  — lower-case substrings to match against DWG layer names
#   spec_keywords   — lower-case phrases expected in specification documents
#   item_prefix     — prefix used in item codes (e.g. "CW", "WIN", "DR")
#   unit            — primary quantity unit: "sqm" | "lm" | "nr"
#   typical_layers  — reference layer names (for documentation / consultant dict seeding)

FACADE_TAXONOMY: dict[str, dict] = {
    # ── Curtain Wall ──────────────────────────────────────────────────────────
    "Curtain Wall (Stick)": {
        "layer_patterns": [
            "a-cw-", "cwall", "curtain-wall", "curtainwall", "cw-ext",
            "cw-int", "a-ucw", "stick cw", "stick-built",
        ],
        "spec_keywords": [
            "curtain wall", "cw-50", "cw50", "stick system", "stick-built",
            "stick curtain", "pressure cap",
        ],
        "item_prefix": "CW",
        "unit": "sqm",
        "typical_layers": ["A-CW-EXT", "A-CW-INT", "CWALL", "CURTAIN-WALL"],
    },
    "Curtain Wall (Unitised)": {
        "layer_patterns": [
            "unitised", "unitized", "ucw", "unit-cw", "unitcw",
        ],
        "spec_keywords": [
            "unitised", "unitized", "unit curtain wall", "cassette facade",
            "factory glazed unit",
        ],
        "item_prefix": "UCW",
        "unit": "sqm",
        "typical_layers": ["A-UCW-EXT", "UCW", "UNITISED-CW"],
    },
    "Curtain Wall (SSG)": {
        "layer_patterns": [
            "ssg", "structural sil", "str-glaz", "structural-glaz", "a-sg-",
        ],
        "spec_keywords": [
            "structural silicone", "ssg", "bonded glazing", "structural glazing",
            "silicone face-sealed", "dgu bonded",
        ],
        "item_prefix": "SSG",
        "unit": "sqm",
        "typical_layers": ["A-SGF-01", "A-SSG-01", "STR-GLAZ"],
    },
    "Curtain Wall (Point-Fix / Spider)": {
        "layer_patterns": [
            "point fix", "point-fix", "spider", "patch fit", "all-glass",
        ],
        "spec_keywords": [
            "point-fixed", "spider fitting", "patch fitting", "patch-plate",
            "all-glass wall", "bolted glass",
        ],
        "item_prefix": "PF",
        "unit": "sqm",
        "typical_layers": ["A-PF-01", "SPIDER-CW"],
    },
    "Curtain Wall (Double-Skin)": {
        "layer_patterns": [
            "double skin", "double-skin", "dsf", "second skin", "buffer facade",
        ],
        "spec_keywords": [
            "double skin facade", "dsf", "second skin", "buffer zone facade",
            "active facade",
        ],
        "item_prefix": "DSF",
        "unit": "sqm",
        "typical_layers": ["A-DSF-01", "DOUBLE-SKIN"],
    },

    # ── Windows ───────────────────────────────────────────────────────────────
    "Window - Casement": {
        "layer_patterns": [
            "a-win-c", "casement", "a-win-01", "a-win-ext",
            "side-hung", "side hung",
            "pencere", "penc-yazi", ".pencereler",
        ],
        "spec_keywords": [
            "casement window", "side-hung", "side hung", "ge-c50", "gc-50",
            "outward opening", "inward opening",
        ],
        "item_prefix": "WC",
        "unit": "nr",
        "typical_layers": ["A-WIN-C", "A-WIN-01"],
    },
    "Window - Fixed": {
        "layer_patterns": [
            "a-win-f", "fixed light", "a-win-02", "fixed-window", "picture win",
            "kapi_pencere", "kapi-pencere", "dograma", "doğrama",
        ],
        "spec_keywords": [
            "fixed glazing", "fixed light", "non-opening", "picture window",
            "fixed window",
        ],
        "item_prefix": "WF",
        "unit": "nr",
        "typical_layers": ["A-WIN-F", "WINDOW-FX"],
    },
    "Window - Sliding": {
        "layer_patterns": [
            "a-win-s", "sliding win", "a-win-03", "slide-win",
        ],
        "spec_keywords": [
            "sliding window", "horizontal sliding", "hs window",
        ],
        "item_prefix": "WS",
        "unit": "nr",
        "typical_layers": ["A-WIN-S", "WIN-SLIDE"],
    },
    "Window - Awning / Top-Hung": {
        "layer_patterns": [
            "a-win-a", "awning", "a-win-04", "top-hung win", "top hung win",
        ],
        "spec_keywords": [
            "top-hung", "awning window", "projected window", "top hung",
        ],
        "item_prefix": "WA",
        "unit": "nr",
        "typical_layers": ["A-WIN-A", "WIN-AWN"],
    },
    "Window - Tilt-and-Turn": {
        "layer_patterns": [
            "tilt turn", "tilt-turn", "a-win-05",
        ],
        "spec_keywords": [
            "tilt-and-turn", "tilt turn", "dreh-kipp",
        ],
        "item_prefix": "WTT",
        "unit": "nr",
        "typical_layers": ["A-WIN-TT"],
    },
    "Window - Louvre": {
        "layer_patterns": [
            "louvre win", "louvre-win", "jalousie", "a-win-06",
        ],
        "spec_keywords": [
            "louvre window", "jalousie window", "glass louvre",
        ],
        "item_prefix": "WLV",
        "unit": "nr",
        "typical_layers": ["A-WIN-LV"],
    },

    # ── Doors ─────────────────────────────────────────────────────────────────
    "Door - Single Swing": {
        "layer_patterns": [
            "a-dr-ss", "a-dr-01", "a-dr-ext", "single-door", "swing door",
            "kapi", "kapı", "b_kapi", "door",
        ],
        "spec_keywords": [
            "single swing door", "single leaf", "hinged door", "single-leaf",
        ],
        "item_prefix": "DSS",
        "unit": "nr",
        "typical_layers": ["A-DR-SS", "A-DR-01"],
    },
    "Door - Double Swing": {
        "layer_patterns": [
            "a-dr-ds", "a-dr-02", "double-door", "dble-dr", "double swing",
        ],
        "spec_keywords": [
            "double swing", "double leaf", "pair of doors", "french door",
        ],
        "item_prefix": "DDS",
        "unit": "nr",
        "typical_layers": ["A-DR-DS"],
    },
    "Door - Sliding": {
        "layer_patterns": [
            "a-dr-sl", "a-dr-03", "slide-dr", "sliding door",
        ],
        "spec_keywords": [
            "sliding door", "patio door", "bi-parting", "bypass door",
        ],
        "item_prefix": "DSL",
        "unit": "nr",
        "typical_layers": ["A-DR-SL", "DOOR-SLIDE"],
    },
    "Door - Frameless (Patch-Fit)": {
        "layer_patterns": [
            "frameless door", "patch-fit door", "a-dr-gl", "glass door",
        ],
        "spec_keywords": [
            "frameless glass door", "patch fitting door", "all-glass door",
            "point-fixed door",
        ],
        "item_prefix": "DPF",
        "unit": "nr",
        "typical_layers": ["A-DR-GL"],
    },
    "Door - Fire-Rated": {
        "layer_patterns": [
            "fire door", "fr door", "fire-rated door", "a-dr-fr",
        ],
        "spec_keywords": [
            "fire door", "fire-rated door", "fire resistance", "frd",
            "30 min fire", "60 min fire", "90 min fire",
        ],
        "item_prefix": "DFR",
        "unit": "nr",
        "typical_layers": ["A-DR-FR", "FIRE-DOOR"],
    },
    "Door - Automatic Sliding": {
        "layer_patterns": [
            "a-dr-auto", "a-dr-04", "auto-door", "auto sliding door",
        ],
        "spec_keywords": [
            "automatic door", "sensor door", "auto sliding", "autodoor",
            "motion sensor",
        ],
        "item_prefix": "DAU",
        "unit": "nr",
        "typical_layers": ["A-DR-AUTO", "AUTO-DOOR"],
    },
    "Door - Revolving": {
        "layer_patterns": [
            "revolving door", "revolv-dr", "a-dr-rev",
        ],
        "spec_keywords": [
            "revolving door", "3-wing", "4-wing", "circular door",
        ],
        "item_prefix": "DRV",
        "unit": "nr",
        "typical_layers": ["A-DR-REV"],
    },
    "Door - Folding / Bi-Fold": {
        "layer_patterns": [
            "folding door", "bifold", "bi-fold door", "a-dr-bf",
        ],
        "spec_keywords": [
            "folding door", "bi-fold", "bifolding", "accordion door",
        ],
        "item_prefix": "DBF",
        "unit": "nr",
        "typical_layers": ["A-DR-BF", "BIFOLD"],
    },

    # ── Cladding ──────────────────────────────────────────────────────────────
    "ACP Cladding": {
        "layer_patterns": [
            "a-acp-", "a-acp", "acp", "cladding", "alucobond", "alupanel",
            "composite panel", "acm",
        ],
        "spec_keywords": [
            "acp", "aluminum composite", "acm", "cladding",
            "aluminium composite", "alucobond", "reynobond",
        ],
        "item_prefix": "ACP",
        "unit": "sqm",
        "typical_layers": ["A-ACP-01", "A-ACP-EXT", "CLADDING"],
    },
    "Solid Aluminium Panel": {
        "layer_patterns": [
            "solid al panel", "solid-al", "solid panel", "a-alp-",
        ],
        "spec_keywords": [
            "solid aluminium panel", "solid aluminum panel", "3mm aluminium",
            "solid al", "solid panel cladding",
        ],
        "item_prefix": "SAP",
        "unit": "sqm",
        "typical_layers": ["A-ALP-01"],
    },
    "HPL Cladding": {
        "layer_patterns": [
            "hpl", "high pressure lam", "trespa",
        ],
        "spec_keywords": [
            "hpl", "high pressure laminate", "trespa", "compact laminate",
        ],
        "item_prefix": "HPL",
        "unit": "sqm",
        "typical_layers": ["A-HPL-01"],
    },
    "Spandrel Panel": {
        "layer_patterns": [
            "a-sp-", "spandrel", "a-sp-01", "opaque panel",
        ],
        "spec_keywords": [
            "spandrel", "opaque panel", "infill panel", "spandrel glass",
        ],
        "item_prefix": "SP",
        "unit": "sqm",
        "typical_layers": ["A-SP-01", "SPANDREL"],
    },
    "Rainscreen Cladding": {
        "layer_patterns": [
            "a-rs-", "rainscreen", "ventilated facade", "vf-",
        ],
        "spec_keywords": [
            "rainscreen", "ventilated facade", "open-jointed",
            "pressure equalized", "drained-ventilated",
        ],
        "item_prefix": "RS",
        "unit": "sqm",
        "typical_layers": ["A-RS-01", "RAINSCREEN"],
    },
    "Terracotta Cladding": {
        "layer_patterns": [
            "terracotta", "terra cotta", "a-tc-",
        ],
        "spec_keywords": [
            "terracotta", "terra cotta", "ceramic cladding", "sintered stone",
        ],
        "item_prefix": "TC",
        "unit": "sqm",
        "typical_layers": ["A-TC-01"],
    },

    # ── Rooflight / Skylight / Atrium ─────────────────────────────────────────
    "Skylight (Fixed)": {
        "layer_patterns": [
            "a-sky-", "skylight", "rooflight", "roof light", "a-sky-01",
        ],
        "spec_keywords": [
            "skylight", "rooflight", "roof glazing", "fixed skylight",
        ],
        "item_prefix": "SKF",
        "unit": "sqm",
        "typical_layers": ["A-SKY-01", "SKYLIGHT"],
    },
    "Skylight (Opening)": {
        "layer_patterns": [
            "opening skylight", "opng skylight", "aov skylight", "motorised sky",
        ],
        "spec_keywords": [
            "opening rooflight", "motorised skylight", "aov",
            "automatic opening vent",
        ],
        "item_prefix": "SKO",
        "unit": "nr",
        "typical_layers": ["A-SKY-OP"],
    },
    "Atrium Glazed Roof": {
        "layer_patterns": [
            "atrium", "a-at-", "barrel vault", "vaulted roof",
        ],
        "spec_keywords": [
            "atrium glazing", "barrel vault", "vaulted glazed roof",
            "glazed atrium",
        ],
        "item_prefix": "ATR",
        "unit": "sqm",
        "typical_layers": ["A-AT-01", "ATRIUM"],
    },
    "Canopy / Entrance Canopy": {
        "layer_patterns": [
            "a-cp-", "canopy", "entrance canopy", "weather canopy",
        ],
        "spec_keywords": [
            "canopy", "entrance canopy", "weather canopy", "glazed canopy",
            "walkway canopy",
        ],
        "item_prefix": "CAN",
        "unit": "sqm",
        "typical_layers": ["A-CP-01", "CANOPY"],
    },

    # ── Louvre / Screen / Sunshade ────────────────────────────────────────────
    "Louvre System": {
        "layer_patterns": [
            "a-lv-", "louver", "louvre", "a-lv-01", "louvre screen",
        ],
        "spec_keywords": [
            "louvre", "louver", "louvered panel", "ventilation louvre",
        ],
        "item_prefix": "LV",
        "unit": "sqm",
        "typical_layers": ["A-LV-01", "LOUVER", "LOUVRE"],
    },
    "Sun Shading (Blades / Fins)": {
        "layer_patterns": [
            "a-ss-", "sunshade", "sun-shade", "brise", "aerofoil fin",
            "aerofoil", "fin blade", "solar fin",
        ],
        "spec_keywords": [
            "brise soleil", "sun shading", "solar shading", "blade",
            "aerofoil fin", "horizontal fin", "vertical fin", "sunshade",
        ],
        "item_prefix": "SHD",
        "unit": "lm",
        "typical_layers": ["A-SS-01", "SUNSHADE", "AEROFOIL"],
    },
    "Perforated Panel Screen": {
        "layer_patterns": [
            "a-fp-", "perforated", "feature panel", "decorative panel",
            "screen panel", "mesh screen",
        ],
        "spec_keywords": [
            "perforated panel", "feature cladding", "decorative panel",
            "screen panel", "parametric screen",
        ],
        "item_prefix": "PPS",
        "unit": "sqm",
        "typical_layers": ["A-FP-01", "PERFORATED"],
    },

    # ── Balustrade / Railing ──────────────────────────────────────────────────
    "Glass Balustrade": {
        "layer_patterns": [
            "a-gr-", "railing", "balustrade", "glass-rail", "glass rail",
        ],
        "spec_keywords": [
            "glass railing", "balustrade", "glass balustrade",
            "frameless railing", "structural glass railing",
        ],
        "item_prefix": "GBL",
        "unit": "lm",
        "typical_layers": ["A-GR-01", "RAILING", "BALUSTRADE"],
    },
    "Aluminium Handrail": {
        "layer_patterns": [
            "a-hr-", "handrail", "a-hr-01", "tubular rail", "al-rail",
        ],
        "spec_keywords": [
            "handrail", "tubular rail", "aluminum rail", "aluminium handrail",
        ],
        "item_prefix": "AHR",
        "unit": "lm",
        "typical_layers": ["A-HR-01", "HANDRAIL"],
    },

    # ── Specialist ────────────────────────────────────────────────────────────
    "Shopfront": {
        "layer_patterns": [
            "a-sf-", "shopfront", "shop-front", "retail facade",
            "dograma-gorunus", "rol_cephe",
        ],
        "spec_keywords": [
            "shopfront", "shop front", "retail facade", "display window",
        ],
        "item_prefix": "SHF",
        "unit": "sqm",
        "typical_layers": ["A-SHF-01", "SHOPFRONT"],
    },
    "Entrance Lobby / Portal": {
        "layer_patterns": [
            "entrance lobby", "lobby glazing", "a-el-", "portal",
        ],
        "spec_keywords": [
            "entrance lobby", "glazed lobby", "entrance portal",
            "bespoke entrance",
        ],
        "item_prefix": "ELB",
        "unit": "sqm",
        "typical_layers": ["A-EL-01", "ENTRANCE"],
    },
    "Parapet Coping": {
        "layer_patterns": [
            "a-par-", "parapet", "coping", "coping-cap",
        ],
        "spec_keywords": [
            "parapet coping", "coping cap", "aluminium coping", "coping flashings",
        ],
        "item_prefix": "PAR",
        "unit": "lm",
        "typical_layers": ["A-PAR-01", "PARAPET"],
    },
    "Column Cladding": {
        "layer_patterns": [
            "a-cc-", "col-clad", "column-clad", "column wrap",
        ],
        "spec_keywords": [
            "column cladding", "column wrap", "column cover",
        ],
        "item_prefix": "CCL",
        "unit": "sqm",
        "typical_layers": ["A-CC-01", "COL-CLAD"],
    },
    "Soffit / Fascia": {
        "layer_patterns": [
            "a-sof-", "soffit", "fascia", "eaves", "soffit panel",
        ],
        "spec_keywords": [
            "soffit cladding", "fascia", "eaves cladding", "soffit panel",
        ],
        "item_prefix": "SOF",
        "unit": "sqm",
        "typical_layers": ["A-SOF-01", "SOFFIT", "FASCIA"],
    },
    "Smoke Vent (AOV)": {
        "layer_patterns": [
            "a-sv-", "smkvent", "smoke-vent", "aov", "smoke vent",
        ],
        "spec_keywords": [
            "smoke vent", "aov", "automatic opening vent", "smoke extract",
        ],
        "item_prefix": "SVT",
        "unit": "nr",
        "typical_layers": ["A-SV-01", "SMOKE-VENT"],
    },
    "Roller Shutter": {
        "layer_patterns": [
            "a-sh-", "shutter", "roller-shutter", "rollerdoor", "roller door",
        ],
        "spec_keywords": [
            "roller shutter", "roller door", "shutters", "sectional door",
        ],
        "item_prefix": "RSH",
        "unit": "nr",
        "typical_layers": ["A-SH-01", "ROLLER-SHUTTER"],
    },
}

# ── ELEVATION & FLOOR NORMALIZATION ───────────────────────────────────────────

ELEVATION_MAP: dict[str, list[str]] = {
    "N":  ["north", "n-elev", "elev-n", "elevation-1", "e1"],
    "S":  ["south", "s-elev", "elev-s", "elevation-2", "e2"],
    "E":  ["east",  "e-elev", "elev-e", "elevation-3", "e3"],
    "W":  ["west",  "w-elev", "elev-w", "elevation-4", "e4"],
    "NE": ["northeast", "ne-elev"],
    "NW": ["northwest", "nw-elev"],
    "SE": ["southeast", "se-elev"],
    "SW": ["southwest", "sw-elev"],
    "F":  ["front", "front-elev", "main facade"],
    "R":  ["rear",  "back",  "rear-elev"],
}

FLOOR_ABBREVIATIONS: dict[str, str] = {
    "ground": "GF", "gf": "GF", "g": "GF", "0": "GF", "g/f": "GF",
    "basement": "B1", "b1": "B1", "b": "B1", "b2": "B2", "b3": "B3",
    "mezzanine": "MZ", "mz": "MZ", "m": "MZ",
    "roof": "RF", "r": "RF", "rooftop": "RF", "top": "RF",
    "podium": "PD", "pod": "PD",
    "penthouse": "PH", "ph": "PH",
    "transfer": "TR", "plant": "PL",
}


# ── DATA CLASSES ──────────────────────────────────────────────────────────────

@dataclass
class SystemInfo:
    """Aggregate quantities and metadata for one facade system type."""
    system_type: str
    system_series: str = ""
    dwg_layers: list = field(default_factory=list)
    total_sqm: float = 0.0
    total_lm: float = 0.0
    total_openings: int = 0
    by_elevation: dict = field(default_factory=dict)
    by_floor: dict = field(default_factory=dict)
    spec_reference: str = ""
    confidence: str = "MEDIUM"   # HIGH | MEDIUM | LOW
    item_prefix: str = ""
    unit: str = "sqm"


@dataclass
class RFIFlag:
    rfi_id: str
    category: str                # "SPECIFICATION" | "CATALOG_MISMATCH" | "GEOMETRY" | "UNKNOWN_LAYER"
    severity: str                # "HIGH" | "MEDIUM" | "LOW"
    description: str
    affected_element: str = ""
    recommendation: str = ""


@dataclass
class ProjectScope:
    """Complete facade scope produced by ScopeIdentificationEngine."""
    systems: list = field(default_factory=list)               # list[SystemInfo]
    rfi_flags: list = field(default_factory=list)             # list[RFIFlag]
    total_systems: int = 0
    total_facade_sqm: float = 0.0
    total_linear_lm: float = 0.0
    item_code_registry: dict = field(default_factory=dict)    # item_code → details

    # Cross-reference metadata
    in_dwg_not_in_spec: list = field(default_factory=list)
    in_spec_not_in_dwg: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "total_systems": self.total_systems,
            "total_facade_sqm": round(self.total_facade_sqm, 2),
            "total_linear_lm": round(self.total_linear_lm, 2),
            "rfi_count": len(self.rfi_flags),
            "in_dwg_not_in_spec": self.in_dwg_not_in_spec,
            "in_spec_not_in_dwg": self.in_spec_not_in_dwg,
            "systems": [
                {
                    "system_type": s.system_type,
                    "item_prefix": s.item_prefix,
                    "unit": s.unit,
                    "total_sqm": round(s.total_sqm, 2),
                    "total_lm": round(s.total_lm, 2),
                    "total_openings": s.total_openings,
                    "confidence": s.confidence,
                    "layers": s.dwg_layers,
                    "spec_reference": s.spec_reference,
                    "by_elevation": s.by_elevation,
                    "by_floor": s.by_floor,
                }
                for s in self.systems
            ],
            "item_code_registry": self.item_code_registry,
            "rfis": [
                {
                    "rfi_id": r.rfi_id,
                    "category": r.category,
                    "severity": r.severity,
                    "description": r.description,
                    "affected_element": r.affected_element,
                    "recommendation": r.recommendation,
                }
                for r in self.rfi_flags
            ],
        }


# ── PDF VECTOR DETECTION ─────────────────────────────────────────────────────

def _pdf_has_vector_content(pdf_path: str) -> bool:
    """
    Detect whether a PDF contains vector drawing content (lines, paths, rects)
    vs. only raster images (renders, photos, scanned pages).

    Uses pdfplumber to inspect page objects. Returns True if any page has
    meaningful vector geometry (lines, rects, curves) beyond trivial decoration.
    """
    try:
        import pdfplumber
    except ImportError:
        logger.warning("pdfplumber not installed — skipping PDF vector check")
        return False

    if not pdf_path or not os.path.isfile(pdf_path):
        return False

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages[:10]:  # Check first 10 pages max
                lines = page.lines or []
                rects = page.rects or []
                curves = page.curves or []
                # Count meaningful vector objects (exclude trivial borders/frames)
                vector_count = len(lines) + len(rects) + len(curves)
                if vector_count > 15:
                    return True
                # Also check for text-based dimension annotations
                text = page.extract_text() or ""
                # Dimension patterns: "1200mm", "2.4m", "1200 x 2400"
                dim_matches = re.findall(
                    r'\b\d{2,5}\s*(?:mm|m)\b|\b\d+\s*x\s*\d+\b', text, re.IGNORECASE
                )
                if dim_matches and vector_count > 5:
                    return True
        return False
    except Exception as e:
        logger.warning(f"PDF vector check failed for {pdf_path}: {e}")
        return False


# ── SCOPE IDENTIFICATION ENGINE ───────────────────────────────────────────────

class ScopeIdentificationEngine:
    """
    Identifies all facade systems in a project from DWG layers and spec text.

    Usage::

        engine = ScopeIdentificationEngine(consultant_dictionary=[
            {"raw_layer_name": "A-UNITISED-EXT", "mapped_internal_type": "Curtain Wall (Unitised)"},
        ])
        scope = engine.identify_project_scope(dwg_extraction, spec_text)
    """

    FUZZY_THRESHOLD = 0.52   # minimum SequenceMatcher ratio for fuzzy layer fallback

    def __init__(self, consultant_dictionary: Optional[list] = None):
        """
        consultant_dictionary: list of dicts with keys
            ``raw_layer_name`` and ``mapped_internal_type``.
        Populated from ConsultantDictionary ORM table by the caller.
        """
        self.consultant_dict: dict[str, str] = {}
        for entry in (consultant_dictionary or []):
            raw = entry.get("raw_layer_name", "").upper().strip()
            mapped = entry.get("mapped_internal_type", "").strip()
            if raw and mapped:
                self.consultant_dict[raw] = mapped

    # ── NO-VECTOR FAILSAFE ─────────────────────────────────────────────────────

    @staticmethod
    def check_vector_data_available(
        dwg_extraction: dict,
        has_dwg_files: bool = False,
        spec_pdf_paths: list = None,
    ) -> dict:
        """
        Pre-check: detect if uploaded data contains measurable CAD geometry.

        Returns dict:
            {"has_vectors": True/False, "reason": str, "should_halt": bool}

        If the PDF contains ONLY raster images (renders) and NO vector data,
        AND no .dwg is provided, the pipeline MUST halt with NEEDS_INFO.
        """
        result = {"has_vectors": False, "reason": "", "should_halt": False}

        # 1. If DWG files were uploaded, vectors are available
        if has_dwg_files:
            result["has_vectors"] = True
            result["reason"] = "DWG/DXF files provided — vector geometry available"
            return result

        # 2. Check if DWG extraction produced usable geometry
        if dwg_extraction:
            layers = dwg_extraction.get("layers_data", {})
            blocks = dwg_extraction.get("blocks", [])
            polylines = dwg_extraction.get("polylines", [])
            lines = dwg_extraction.get("lines", [])
            panels = dwg_extraction.get("panels", [])
            openings = dwg_extraction.get("openings", [])

            entity_count = len(blocks) + len(polylines) + len(lines) + len(panels) + len(openings)
            layer_count = len(layers)

            if entity_count > 5 or layer_count > 2:
                result["has_vectors"] = True
                result["reason"] = f"DWG extraction contains {entity_count} entities across {layer_count} layers"
                return result

        # 3. Check PDF specs for vector content (not just raster images)
        if spec_pdf_paths:
            for pdf_path in (spec_pdf_paths or []):
                if _pdf_has_vector_content(pdf_path):
                    result["has_vectors"] = True
                    result["reason"] = f"Vector content detected in {os.path.basename(pdf_path)}"
                    return result

        # NO vector data anywhere — halt
        result["should_halt"] = True
        result["reason"] = (
            "No measurable CAD geometry detected. The uploaded PDFs contain only "
            "raster images (renders/photos). Please upload .dwg files or vector PDFs "
            "to generate accurate quantities."
        )
        return result

    # ── Main entry point ──────────────────────────────────────────────────────

    def identify_project_scope(
        self,
        dwg_extraction: dict,
        spec_text: str = "",
        visual_analysis: Optional[dict] = None,
    ) -> ProjectScope:
        """
        Produce a complete ProjectScope from DWG extraction output and spec text.

        Parameters
        ----------
        dwg_extraction:
            Output of ``DWGParserService.extract_geometry``.  Expects keys:
            ``layers_data`` (dict layer → {blocks, areas}) or flat entity lists
            such as ``blocks`` and ``polylines``.
        spec_text:
            Free text extracted from the project specification PDF.
        visual_analysis:
            Optional dict from vision-model rendering analysis; may contain a
            ``systems`` key with a list of ``{system_type: str}`` items.
        """
        scope = ProjectScope()
        rfi_counter = [0]

        # ── 1. Collect DWG layer names ────────────────────────────────────────
        dwg_layers = self._extract_dwg_layers(dwg_extraction)
        logger.info(f"DWG layers found: {len(dwg_layers)}")

        # ── 2. Match layers → system types ────────────────────────────────────
        layer_to_system = self._match_layers_to_systems(dwg_layers)

        # ── 3. Extract spec systems ───────────────────────────────────────────
        spec_systems = self._extract_spec_systems(spec_text)

        # ── 4. Build system map ───────────────────────────────────────────────
        system_map: dict[str, SystemInfo] = {}

        for layer, system_type in layer_to_system.items():
            if system_type not in system_map:
                taxonomy = FACADE_TAXONOMY.get(system_type, {})
                system_map[system_type] = SystemInfo(
                    system_type=system_type,
                    item_prefix=taxonomy.get("item_prefix", "X"),
                    unit=taxonomy.get("unit", "sqm"),
                    confidence=(
                        "HIGH" if layer.upper() in self.consultant_dict else "MEDIUM"
                    ),
                )
            system_map[system_type].dwg_layers.append(layer)

        # ── 5. Inject vision-identified systems (LOW confidence) ──────────────
        if visual_analysis and visual_analysis.get("systems"):
            for vis_sys in visual_analysis["systems"]:
                sys_type = vis_sys.get("system_type", "")
                if sys_type and sys_type not in system_map:
                    taxonomy = FACADE_TAXONOMY.get(sys_type, {})
                    system_map[sys_type] = SystemInfo(
                        system_type=sys_type,
                        item_prefix=taxonomy.get("item_prefix", "X"),
                        unit=taxonomy.get("unit", "sqm"),
                        confidence="LOW",
                    )

        # ── 6. Calculate quantities from DWG geometry ─────────────────────────
        self._calculate_quantities(system_map, dwg_extraction)

        # ── 7. Match spec references ──────────────────────────────────────────
        self._match_spec_references(system_map, spec_systems, spec_text)

        # ── 8. Cross-reference checks → RFIs ─────────────────────────────────
        rfis = self._cross_reference_check(
            system_map, spec_systems, dwg_layers, rfi_counter
        )
        scope.rfi_flags = rfis

        # ── 9. Record cross-reference lists ───────────────────────────────────
        dwg_types = set(system_map.keys())
        scope.in_dwg_not_in_spec = sorted(
            t for t in dwg_types if spec_systems and t not in spec_systems
        )
        scope.in_spec_not_in_dwg = sorted(
            t for t in spec_systems if t not in dwg_types
        )

        # ── 10. Assign item codes ─────────────────────────────────────────────
        item_registry = self._assign_item_codes(system_map, dwg_extraction)
        scope.item_code_registry = item_registry

        # ── 11. Finalise scope ────────────────────────────────────────────────
        scope.systems = list(system_map.values())
        scope.total_systems = len(scope.systems)
        scope.total_facade_sqm = sum(
            s.total_sqm for s in scope.systems if s.unit in ("sqm", "nr")
        )
        scope.total_linear_lm = sum(
            s.total_lm for s in scope.systems if s.unit == "lm"
        )

        logger.info(
            f"Scope identified: {scope.total_systems} systems, "
            f"{scope.total_facade_sqm:.1f} SQM, {scope.total_linear_lm:.1f} LM, "
            f"{len(scope.rfi_flags)} RFIs"
        )
        return scope

    # ── Layer extraction ──────────────────────────────────────────────────────

    def _extract_dwg_layers(self, dwg_extraction: dict) -> list[str]:
        """Collect all unique layer names from the DWG extraction dict."""
        layers: set[str] = set()

        # Dict keyed by layer name (output of extract_geometry)
        if isinstance(dwg_extraction, dict):
            for key in dwg_extraction:
                if isinstance(key, str) and key not in ("blocks", "polylines", "entities", "lines"):
                    layers.add(key.upper())

            # Flat entity lists
            for entity_key in ("blocks", "polylines", "lines", "entities"):
                for entity in dwg_extraction.get(entity_key, []):
                    if isinstance(entity, dict):
                        lname = entity.get("layer", "")
                        if lname:
                            layers.add(lname.upper())

            # Nested layers_data format
            layers_data = dwg_extraction.get("layers_data", {})
            if isinstance(layers_data, dict):
                for lname in layers_data:
                    layers.add(lname.upper())

        # Remove common non-facade layers (Defpoints, viewport, etc.)
        ignore = {"DEFPOINTS", "0", "VIEWPORT", "VPORT", "TITLEBLOCK", "BORDER"}
        layers -= ignore

        return list(layers)

    # ── Layer → system matching ───────────────────────────────────────────────

    def _match_layers_to_systems(self, layers: list[str]) -> dict[str, str]:
        """Map each DWG layer name to a facade system type string."""
        layer_to_system: dict[str, str] = {}

        for layer in layers:
            layer_upper = layer.upper()
            layer_lower = layer.lower()

            # 1. Consultant dictionary (tenant-trained, exact)
            if layer_upper in self.consultant_dict:
                layer_to_system[layer] = self.consultant_dict[layer_upper]
                continue

            # Also check partial consultant dict matches
            for dict_key, dict_type in self.consultant_dict.items():
                if dict_key in layer_upper or layer_upper in dict_key:
                    layer_to_system[layer] = dict_type
                    break
            if layer in layer_to_system:
                continue

            # 2. Pattern matching against taxonomy (longest pattern wins = most specific)
            best_match: Optional[str] = None
            best_score = 0
            for system_type, taxonomy in FACADE_TAXONOMY.items():
                for pattern in taxonomy["layer_patterns"]:
                    if pattern in layer_lower:
                        score = len(pattern)
                        if score > best_score:
                            best_score = score
                            best_match = system_type
            if best_match:
                layer_to_system[layer] = best_match
                continue

            # 3. Fuzzy match against system type strings and known layer names
            best_fuzzy: Optional[str] = None
            best_ratio = 0.0
            for system_type, taxonomy in FACADE_TAXONOMY.items():
                for known_layer in taxonomy.get("typical_layers", []):
                    ratio = SequenceMatcher(
                        None, layer_lower, known_layer.lower()
                    ).ratio()
                    if ratio > best_ratio:
                        best_ratio = ratio
                        best_fuzzy = system_type
                # Also compare against system type name itself
                ratio = SequenceMatcher(
                    None, layer_lower, system_type.lower()
                ).ratio()
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_fuzzy = system_type

            if best_fuzzy and best_ratio >= self.FUZZY_THRESHOLD:
                logger.debug(
                    f"Fuzzy matched layer '{layer}' → '{best_fuzzy}' "
                    f"(ratio={best_ratio:.2f})"
                )
                layer_to_system[layer] = best_fuzzy
            # else: layer stays unmatched (excluded from system_map)

        return layer_to_system

    # ── Spec system extraction ────────────────────────────────────────────────

    def _extract_spec_systems(self, spec_text: str) -> set[str]:
        """Return set of system type strings mentioned in spec text."""
        if not spec_text:
            return set()

        found: set[str] = set()
        spec_lower = spec_text.lower()

        for system_type, taxonomy in FACADE_TAXONOMY.items():
            for keyword in taxonomy["spec_keywords"]:
                if keyword.lower() in spec_lower:
                    found.add(system_type)
                    break

        return found

    # ── Quantity calculation ──────────────────────────────────────────────────

    def _calculate_quantities(self, system_map: dict, dwg_extraction: dict):
        """Populate total_sqm, total_lm, total_openings, by_elevation, by_floor."""

        def _layer_matches_system(layer: str, sys_info: SystemInfo) -> bool:
            return layer.upper() in [l.upper() for l in sys_info.dwg_layers]

        # ── Process blocks (windows / doors = discrete openings) ──────────────
        for block in dwg_extraction.get("blocks", []):
            layer = block.get("layer", "").upper()
            w = float(block.get("width_mm", block.get("width", 0)) or 0)
            h = float(block.get("height_mm", block.get("height", 0)) or 0)
            elevation = self._infer_elevation(block)
            floor = self._normalize_floor(
                str(block.get("floor", block.get("level", "")) or "")
            )

            for sys_type, sys_info in system_map.items():
                if not _layer_matches_system(layer, sys_info):
                    continue
                area = (w * h) / 1_000_000 if w and h else 0.0
                sys_info.total_sqm += area
                sys_info.total_openings += 1
                if elevation:
                    sys_info.by_elevation[elevation] = (
                        sys_info.by_elevation.get(elevation, 0.0) + area
                    )
                if floor:
                    sys_info.by_floor[floor] = (
                        sys_info.by_floor.get(floor, 0.0) + area
                    )
                break

        # ── Process polylines / areas (curtain wall, ACP, etc.) ───────────────
        for poly in dwg_extraction.get("polylines", []):
            layer = poly.get("layer", "").upper()
            area = float(poly.get("area_sqm", poly.get("area", 0)) or 0)
            length_raw = float(poly.get("length_mm", poly.get("length", 0)) or 0)
            length = length_raw / 1000 if length_raw > 1000 else length_raw  # mm → m
            elevation = self._infer_elevation(poly)
            floor = self._normalize_floor(
                str(poly.get("floor", poly.get("level", "")) or "")
            )

            for sys_type, sys_info in system_map.items():
                if not _layer_matches_system(layer, sys_info):
                    continue
                if sys_info.unit == "sqm" and area:
                    sys_info.total_sqm += area
                    if elevation:
                        sys_info.by_elevation[elevation] = (
                            sys_info.by_elevation.get(elevation, 0.0) + area
                        )
                    if floor:
                        sys_info.by_floor[floor] = (
                            sys_info.by_floor.get(floor, 0.0) + area
                        )
                elif sys_info.unit == "lm" and length:
                    sys_info.total_lm += length
                break

        # ── Consume layers_data format (from DWGParserService.extract_geometry) ──
        layers_data: dict = dwg_extraction.get("layers_data", {})
        if not layers_data and isinstance(dwg_extraction, dict):
            # The dict itself may BE the layers_data
            maybe_layer_data = {
                k: v for k, v in dwg_extraction.items()
                if isinstance(v, dict) and ("blocks" in v or "areas" in v)
            }
            if maybe_layer_data:
                layers_data = maybe_layer_data

        for layer_name, layer_content in layers_data.items():
            layer_upper = layer_name.upper()
            for sys_type, sys_info in system_map.items():
                if not _layer_matches_system(layer_upper, sys_info):
                    continue
                for area_info in layer_content.get("areas", []):
                    net_area = float(area_info.get("net_area", 0) or 0)
                    if sys_info.unit == "lm":
                        sys_info.total_lm += net_area  # treat as LM for linear types
                    else:
                        sys_info.total_sqm += net_area
                for blk in layer_content.get("blocks", []):
                    w = float(blk.get("width", 0) or 0)
                    h = float(blk.get("height", 0) or 0)
                    sys_info.total_openings += 1
                    sys_info.total_sqm += (w * h) / 1_000_000 if w and h else 0.0
                break

        # Systems with zero quantities → downgrade confidence
        for sys_info in system_map.values():
            if (sys_info.total_sqm == 0 and sys_info.total_lm == 0
                    and sys_info.total_openings == 0):
                sys_info.confidence = "LOW"

    # ── Spec reference matching ───────────────────────────────────────────────

    def _match_spec_references(
        self, system_map: dict, spec_systems: set, spec_text: str
    ):
        """Attach spec clause reference strings to matching systems."""
        if not spec_text:
            return
        spec_lower = spec_text.lower()
        for sys_type, sys_info in system_map.items():
            taxonomy = FACADE_TAXONOMY.get(sys_type, {})
            for kw in taxonomy.get("spec_keywords", []):
                if kw.lower() in spec_lower:
                    sys_info.spec_reference = kw
                    if sys_info.confidence == "MEDIUM":
                        sys_info.confidence = "HIGH"
                    break

    # ── Cross-reference RFI generation ───────────────────────────────────────

    def _cross_reference_check(
        self,
        system_map: dict,
        spec_systems: set,
        all_layers: list,
        rfi_counter: list,
    ) -> list[RFIFlag]:
        """Produce RFI flags for spec/DWG mismatches and unrecognised layers."""
        rfis: list[RFIFlag] = []

        def next_rfi_id() -> str:
            rfi_counter[0] += 1
            return f"RFI-{rfi_counter[0]:03d}"

        dwg_systems = set(system_map.keys())

        # Systems in DWG but not in spec
        if spec_systems:
            for sys_type in dwg_systems:
                if sys_type not in spec_systems:
                    rfis.append(RFIFlag(
                        rfi_id=next_rfi_id(),
                        category="SPECIFICATION",
                        severity="MEDIUM",
                        description=(
                            f"System '{sys_type}' found in drawings but no "
                            "specification clause identified."
                        ),
                        affected_element=", ".join(
                            system_map[sys_type].dwg_layers[:4]
                        ),
                        recommendation=(
                            "Request specification section for this system from "
                            "consultant before pricing."
                        ),
                    ))

        # Systems in spec but not in DWG
        for sys_type in spec_systems:
            if sys_type not in dwg_systems:
                rfis.append(RFIFlag(
                    rfi_id=next_rfi_id(),
                    category="SPECIFICATION",
                    severity="HIGH",
                    description=(
                        f"System '{sys_type}' referenced in specification "
                        "but NOT found in DWG layers."
                    ),
                    affected_element="Spec reference",
                    recommendation=(
                        "Quantities cannot be confirmed. "
                        "Request drawings showing this system."
                    ),
                ))

        # Unmatched A- layers (typically facade layers by convention)
        all_mapped: set[str] = set()
        for sys_info in system_map.values():
            all_mapped.update(l.upper() for l in sys_info.dwg_layers)

        facade_convention = [l for l in all_layers if l.startswith("A-")]
        unmatched = [l for l in facade_convention if l not in all_mapped]
        if unmatched:
            rfis.append(RFIFlag(
                rfi_id=next_rfi_id(),
                category="UNKNOWN_LAYER",
                severity="LOW",
                description=(
                    f"Unrecognised facade layer(s): "
                    f"{', '.join(unmatched[:6])}"
                    f"{'…' if len(unmatched) > 6 else ''}"
                ),
                affected_element=", ".join(unmatched[:6]),
                recommendation=(
                    "Verify these layers — may represent additional facade "
                    "systems not in standard taxonomy. Add to Consultant "
                    "Dictionary if confirmed."
                ),
            ))

        return rfis

    # ── Item code assignment ──────────────────────────────────────────────────

    def _assign_item_codes(
        self, system_map: dict, dwg_extraction: dict
    ) -> dict[str, dict]:
        """
        Assign item codes to all opening blocks.
        Format: ``{ITEM_PREFIX}-{ELEVATION}-{FLOOR}-{SEQ:03d}``
        e.g. ``WC-N-03-001``, ``CW-E1-GF-012``.
        """
        registry: dict[str, dict] = {}
        counters: dict[tuple, int] = {}

        all_blocks = list(dwg_extraction.get("blocks", []))

        # Also scan blocks nested inside layers_data
        layers_data = dwg_extraction.get("layers_data", {})
        if not layers_data:
            layers_data = {
                k: v for k, v in dwg_extraction.items()
                if isinstance(v, dict) and "blocks" in v
            }
        for layer_content in layers_data.values():
            all_blocks.extend(layer_content.get("blocks", []))

        for block in all_blocks:
            layer = block.get("layer", "").upper()
            system_type: Optional[str] = None
            item_prefix = "X"
            for sys_type, sys_info in system_map.items():
                if layer in [l.upper() for l in sys_info.dwg_layers]:
                    system_type = sys_type
                    item_prefix = sys_info.item_prefix
                    break
            if not system_type:
                continue

            elevation = self._infer_elevation(block) or "E1"
            floor = self._normalize_floor(
                str(block.get("floor", block.get("level", "")) or "")
            ) or "GF"

            key = (item_prefix, elevation, floor)
            counters[key] = counters.get(key, 0) + 1
            seq = counters[key]
            item_code = f"{item_prefix}-{elevation}-{floor}-{seq:03d}"

            registry[item_code] = {
                "system_type": system_type,
                "elevation": elevation,
                "floor": floor,
                "width_mm": float(
                    block.get("width_mm", block.get("width", 0)) or 0
                ),
                "height_mm": float(
                    block.get("height_mm", block.get("height", 0)) or 0
                ),
                "layer": layer,
                "dwg_handle": block.get("handle", ""),
            }

        return registry

    # ── Helper utilities ──────────────────────────────────────────────────────

    def _infer_elevation(self, entity: dict) -> str:
        """Infer elevation code (N/S/E/W/NE/…) from entity metadata."""
        elevation = str(entity.get("elevation", entity.get("view", "")) or "")
        if elevation:
            for elev_code, keywords in ELEVATION_MAP.items():
                if any(kw in elevation.lower() for kw in keywords):
                    return elev_code
        layer = str(entity.get("layer", entity.get("name", "")) or "")
        for elev_code, keywords in ELEVATION_MAP.items():
            if any(kw in layer.lower() for kw in keywords):
                return elev_code
        return ""

    def _normalize_floor(self, floor_str: str) -> str:
        """Normalise a floor/level string to a short abbreviation."""
        if not floor_str:
            return ""
        floor_lower = floor_str.lower().strip()
        if floor_lower in FLOOR_ABBREVIATIONS:
            return FLOOR_ABBREVIATIONS[floor_lower]
        match = re.match(r'(?:level|floor|l|f|lv|lvl)\s*(\d+)', floor_lower)
        if match:
            return f"L{match.group(1)}"
        # Bare number → zero-padded level (e.g. "3" → "03")
        if re.match(r'^\d+$', floor_lower):
            return f"{int(floor_lower):02d}"
        return floor_str.upper()[:4]

    # ── Report generator ──────────────────────────────────────────────────────

    def generate_scope_report_text(
        self, scope: ProjectScope, project_name: str = "PROJECT"
    ) -> str:
        """Return a plain-text scope-of-works summary."""
        lines = [
            f"SCOPE OF WORKS — {project_name.upper()}",
            "=" * 70,
            "Identified Facade Systems:",
            "",
        ]
        for idx, sys_info in enumerate(scope.systems, 1):
            unit_label = "SQM" if sys_info.unit in ("sqm", "nr") else "LM"
            qty = (
                f"{sys_info.total_sqm:.1f} {unit_label}"
                if sys_info.unit in ("sqm", "nr")
                else f"{sys_info.total_lm:.1f} LM"
            )
            openings = (
                f"  ({sys_info.total_openings} openings)"
                if sys_info.total_openings else ""
            )
            confidence_tag = (
                "[HIGH]" if sys_info.confidence == "HIGH"
                else "[MED]" if sys_info.confidence == "MEDIUM"
                else "[LOW]"
            )
            layers_str = ", ".join(sys_info.dwg_layers[:3])
            lines.append(
                f"  {idx:>2}. {sys_info.system_type:<40} "
                f"{layers_str:<25} {qty}{openings}  {confidence_tag}"
            )
        lines.extend([
            "",
            "-" * 70,
            f"  TOTAL FACADE AREA:      {scope.total_facade_sqm:.1f} SQM",
            f"  TOTAL LINEAR ELEMENTS:  {scope.total_linear_lm:.1f} LM",
            f"  SYSTEMS IDENTIFIED:     {scope.total_systems}",
            f"  TOTAL ITEM CODES:       {len(scope.item_code_registry)}",
        ])
        if scope.in_dwg_not_in_spec:
            lines.append("")
            lines.append("  IN DWG / NOT IN SPEC:   " + ", ".join(scope.in_dwg_not_in_spec))
        if scope.in_spec_not_in_dwg:
            lines.append("  IN SPEC / NOT IN DWG:   " + ", ".join(scope.in_spec_not_in_dwg))
        if scope.rfi_flags:
            lines.extend(["", "UNRESOLVED RFIs:"])
            for rfi in scope.rfi_flags:
                lines.append(
                    f"  [{rfi.severity}] {rfi.rfi_id}: {rfi.description}"
                )
        return "\n".join(lines)

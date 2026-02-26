"""
Universal Semantic PDF Catalog Parser
Supports: ALUMINUM_EXTRUSION | GLASS_PERFORMANCE | HARDWARE

Four-stage pipeline:
  Stage 1 — Material Router: classify document type via LLM + keyword fallback
  Stage 2 — Schema-Specific Extraction: digital (pdfplumber) → vision fallback (Groq)
  Stage 3 — Confidence Scoring + HITL Flagging
  Stage 4 — DXF Extraction Pipeline (ALUMINUM_EXTRUSION only):
    4A  extract_profile_dxf_from_pdf()  — PyMuPDF vector rip → ezdxf block file
                                           Auto-scaling via Vision LLM dimension annotation
                                           Anchor point semantic tagging (anchor_origin_xy, glazing_pocket_xy)
                                           Raster fallback → HITL if < 5 meaningful vector paths
    4B  _extract_geometric_constraints() — Vision QA Agent scans drawing for ALL dimension
                                            annotations → list[GeometricConstraint]
    4C  apply_geometric_constraints()    — Python constraint solver: snaps/rounds DXF vertices
                                            to match text dimensions
    4D  Auto-verification:
          max_adjustment < 1.0mm  → die_status = "VERIFIED"   (zero-human)
          max_adjustment ≥ 1.0mm  → die_status = "DRAFT_REQUIRES_VERIFICATION" + HITL push

Async-native: parse() is async def, called from Celery task via _run_async() helper.
No nested asyncio.run() calls.
"""
import io
import os
import json
import math
import logging
import base64
import tempfile
from dataclasses import dataclass, field
from typing import Optional, List, Tuple, Literal

import pdfplumber
import fitz          # PyMuPDF
import ezdxf
from ezdxf.math import Vec2

from app.services.llm_client import LLMClient

logger = logging.getLogger("masaad-catalog-parser")

MaterialType = Literal["ALUMINUM_EXTRUSION", "GLASS_PERFORMANCE", "HARDWARE"]

# Required fields per material type — missing any triggers HITL
REQUIRED_FIELDS: dict = {
    "ALUMINUM_EXTRUSION": ["item_code", "weight_kg_m"],
    "GLASS_PERFORMANCE":  ["item_code", "u_value_w_m2k"],
    "HARDWARE":           ["item_code"],
}
# Optional fields that contribute to the confidence score (0.3 weight)
OPTIONAL_SCORED_FIELDS: dict = {
    "ALUMINUM_EXTRUSION": ["system_series", "perimeter_mm", "inertia_ix", "inertia_iy", "price_aed_per_kg"],
    "GLASS_PERFORMANCE":  ["glass_makeup", "shading_coefficient_sc", "visible_light_transmittance_vlt",
                           "acoustic_rating_rw_db", "price_aed_sqm"],
    "HARDWARE":           ["description", "hardware_category", "applicable_system", "price_aed_per_unit"],
}
HITL_CONFIDENCE_THRESHOLD = 0.90

# Render matrix for Vision LLM calls: 2× resolution (144 DPI effective)
_RENDER_MATRIX = fitz.Matrix(2.0, 2.0)
_PIXELS_PER_PDF_UNIT = 2.0  # matches Matrix(2.0, 2.0)

# Minimum number of non-trivial vector paths to consider a page as vector (not raster)
_MIN_VECTOR_PATHS = 5
# A "meaningful" path has a bounding rect larger than this in PDF points (~2mm at 1pt≈0.353mm)
_MIN_PATH_SIZE_PT = 6.0
# DXF output directory (temp dir if not configured)
_DXF_OUTPUT_DIR = os.getenv("DXF_OUTPUT_DIR", tempfile.gettempdir())


# ── Extraction schema JSON definitions (passed to LLM as prompt context) ─────

_ALUMINUM_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "profile_item_code": {"type": "string"},
            "system_series": {"type": ["string", "null"]},
            "description": {"type": ["string", "null"]},
            "weight_kg_per_m": {"type": ["number", "null"]},
            "outer_perimeter_mm": {"type": ["number", "null"]},
            "inertia_ix": {"type": ["number", "null"]},
            "inertia_iy": {"type": ["number", "null"]},
            "face_dimension_mm": {"type": ["number", "null"]},
            "structural_depth_mm": {"type": ["number", "null"]},
            "is_thermal_break": {"type": "boolean"},
            "price_aed_per_kg": {"type": ["number", "null"]},
            "supplier_name": {"type": ["string", "null"]},
            "lead_time_days": {"type": ["integer", "null"]},
        },
        "required": ["profile_item_code"],
    },
}

_GLASS_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "profile_item_code": {"type": "string"},
            "glass_makeup": {"type": ["string", "null"]},
            "u_value_w_m2k": {"type": ["number", "null"]},
            "shading_coefficient_sc": {"type": ["number", "null"]},
            "visible_light_transmittance_vlt": {"type": ["number", "null"]},
            "acoustic_rating_rw_db": {"type": ["integer", "null"]},
            "fire_rating_minutes": {"type": ["integer", "null"]},
            "thickness_mm": {"type": ["number", "null"]},
            "price_aed_sqm": {"type": ["number", "null"]},
            "supplier_name": {"type": ["string", "null"]},
            "lead_time_days": {"type": ["integer", "null"]},
        },
        "required": ["profile_item_code"],
    },
}

_HARDWARE_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "profile_item_code": {"type": "string"},
            "description": {"type": ["string", "null"]},
            "hardware_category": {"type": ["string", "null"]},
            "applicable_system": {"type": ["string", "null"]},
            "price_aed_per_unit": {"type": ["number", "null"]},
            "supplier_name": {"type": ["string", "null"]},
            "lead_time_days": {"type": ["integer", "null"]},
        },
        "required": ["profile_item_code"],
    },
}

_SCHEMAS: dict = {
    "ALUMINUM_EXTRUSION": _ALUMINUM_SCHEMA,
    "GLASS_PERFORMANCE": _GLASS_SCHEMA,
    "HARDWARE": _HARDWARE_SCHEMA,
}


# ── Output dataclasses ────────────────────────────────────────────────────────

@dataclass
class GeometricConstraint:
    """One annotated dimension found in a drawing by the Vision QA Agent."""
    dimension_mm: float
    label: str = ""
    start_px: Optional[Tuple[float, float]] = None   # pixel coords in rendered image
    end_px: Optional[Tuple[float, float]] = None


@dataclass
class CatalogEntry:
    # Universal
    item_code: str
    material_type: str = "ALUMINUM_EXTRUSION"
    description: str = ""
    supplier_name: str = ""
    price_absent: bool = True
    source_page: int = 0
    extraction_method: str = "digital"
    confidence_score: float = 1.0
    hitl_required: bool = False
    hitl_reason: str = ""
    # Aluminum-specific
    system_series: str = ""
    weight_kg_m: Optional[float] = None
    perimeter_mm: Optional[float] = None
    inertia_ix: Optional[float] = None
    inertia_iy: Optional[float] = None
    price_aed_per_kg: Optional[float] = None
    is_thermal_break: bool = False
    # Glass-specific
    glass_makeup: Optional[str] = None
    u_value_w_m2k: Optional[float] = None
    shading_coefficient_sc: Optional[float] = None
    visible_light_transmittance_vlt: Optional[float] = None
    acoustic_rating_rw_db: Optional[int] = None
    fire_rating_minutes: Optional[int] = None
    price_aed_sqm: Optional[float] = None
    # Hardware-specific
    hardware_category: Optional[str] = None
    price_aed_per_unit: Optional[float] = None
    # Procurement
    lead_time_days: Optional[int] = None
    supplier_payment_terms: Optional[str] = None
    # DXF extraction fields (ALUMINUM_EXTRUSION Stage 4)
    dxf_path: Optional[str] = None
    anchor_origin_xy: Optional[Tuple[float, float]] = None
    glazing_pocket_xy: Optional[Tuple[float, float]] = None
    bead_snap_xy: Optional[Tuple[float, float]] = None
    scale_factor: Optional[float] = None            # mm per PDF point
    die_status: str = "RAW"                         # RAW | VERIFIED | DRAFT_REQUIRES_VERIFICATION


# ── DXF Extraction Pipeline (Stage 4) ─────────────────────────────────────────

def _pixel_distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    return math.sqrt((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2)


def _count_meaningful_paths(drawings: list) -> int:
    """Count PyMuPDF drawing paths whose bounding rect exceeds the minimum size."""
    count = 0
    for d in drawings:
        r = d.get("rect")
        if r and (r.width > _MIN_PATH_SIZE_PT or r.height > _MIN_PATH_SIZE_PT):
            count += 1
    return count


def _pdf_point_to_mm(coord: float, scale_factor: float) -> float:
    return coord * scale_factor


def _paths_to_dxf(
    drawings: list,
    page_height_pt: float,
    scale_factor: float,
    item_code: str,
) -> ezdxf.document.Drawing:
    """
    Convert PyMuPDF vector paths to an ezdxf document (modelspace block).
    Coordinate system: PDF uses bottom-left origin, Y up.
    fitz uses top-left origin, Y down → flip Y: y_mm = (page_height - y_pt) * scale
    """
    doc = ezdxf.new("R2010")
    doc.layers.add("PROFILE", color=7)

    msp = doc.modelspace()

    for d in drawings:
        items = d.get("items", [])
        for item in items:
            kind = item[0]
            try:
                if kind == "l":
                    # Line segment: ('l', p1, p2)
                    p1, p2 = item[1], item[2]
                    x1 = _pdf_point_to_mm(p1.x, scale_factor)
                    y1 = _pdf_point_to_mm(page_height_pt - p1.y, scale_factor)
                    x2 = _pdf_point_to_mm(p2.x, scale_factor)
                    y2 = _pdf_point_to_mm(page_height_pt - p2.y, scale_factor)
                    msp.add_line(
                        start=(x1, y1, 0),
                        end=(x2, y2, 0),
                        dxfattribs={"layer": "PROFILE"},
                    )

                elif kind == "re":
                    # Rectangle: ('re', rect, line_width)
                    r = item[1]
                    x0 = _pdf_point_to_mm(r.x0, scale_factor)
                    y0 = _pdf_point_to_mm(page_height_pt - r.y1, scale_factor)
                    x1 = _pdf_point_to_mm(r.x1, scale_factor)
                    y1 = _pdf_point_to_mm(page_height_pt - r.y0, scale_factor)
                    pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]
                    msp.add_lwpolyline(pts, dxfattribs={"layer": "PROFILE"})

                elif kind == "c":
                    # Cubic Bezier: ('c', p1, p2, p3, p4)
                    # Approximate with a 6-point polyline
                    pts_raw = [item[1], item[2], item[3], item[4]]
                    t_steps = [i / 5.0 for i in range(6)]
                    poly_pts = []
                    for t in t_steps:
                        mt = 1 - t
                        bx = (mt**3 * pts_raw[0].x
                              + 3 * mt**2 * t * pts_raw[1].x
                              + 3 * mt * t**2 * pts_raw[2].x
                              + t**3 * pts_raw[3].x)
                        by = (mt**3 * pts_raw[0].y
                              + 3 * mt**2 * t * pts_raw[1].y
                              + 3 * mt * t**2 * pts_raw[2].y
                              + t**3 * pts_raw[3].y)
                        poly_pts.append((
                            _pdf_point_to_mm(bx, scale_factor),
                            _pdf_point_to_mm(page_height_pt - by, scale_factor),
                        ))
                    if len(poly_pts) >= 2:
                        msp.add_lwpolyline(poly_pts, dxfattribs={"layer": "PROFILE"})

                elif kind == "qu":
                    # Quad: ('qu', quad)
                    quad = item[1]
                    pts = []
                    for corner in [quad.ul, quad.ur, quad.lr, quad.ll, quad.ul]:
                        pts.append((
                            _pdf_point_to_mm(corner.x, scale_factor),
                            _pdf_point_to_mm(page_height_pt - corner.y, scale_factor),
                        ))
                    msp.add_lwpolyline(pts, dxfattribs={"layer": "PROFILE"})

            except Exception as seg_err:
                logger.debug(f"Skipping segment {kind} for {item_code}: {seg_err}")

    return doc


def apply_geometric_constraints(
    dxf_doc: ezdxf.document.Drawing,
    constraints: List[GeometricConstraint],
) -> Tuple[float, ezdxf.document.Drawing]:
    """
    Stage 4C — Python Constraint Solver.

    Iterates all LINE entities in the DXF modelspace. For each GeometricConstraint,
    finds the closest-length LINE and snaps its endpoint so the line length exactly
    matches the annotated dimension.

    Returns:
        (max_adjustment_mm, adjusted_doc)

    max_adjustment_mm is used for auto-verification gating:
        < 1.0mm  → VERIFIED
        ≥ 1.0mm  → DRAFT_REQUIRES_VERIFICATION + HITL
    """
    if not constraints:
        return 0.0, dxf_doc

    msp = dxf_doc.modelspace()

    # Build a list of (entity, actual_length_mm) for LINE entities only
    line_data: List[Tuple] = []
    for entity in msp:
        if entity.dxftype() == "LINE":
            try:
                start = Vec2(entity.dxf.start[:2])
                end = Vec2(entity.dxf.end[:2])
                length = (end - start).magnitude
                if length > 0.1:  # skip degenerate near-zero lines
                    line_data.append((entity, start, end, length))
            except Exception:
                continue

    max_adjustment = 0.0

    for constraint in constraints:
        target_mm = constraint.dimension_mm
        if target_mm <= 0:
            continue

        # Find closest-length line (within 30% of target to avoid false matches)
        best_entity = None
        best_start = None
        best_end = None
        best_actual = 0.0
        best_delta = float("inf")

        for entity, start, end, length in line_data:
            delta = abs(length - target_mm)
            ratio = delta / target_mm
            if ratio < 0.30 and delta < best_delta:
                best_delta = delta
                best_entity = entity
                best_start = start
                best_end = end
                best_actual = length

        if best_entity is None or best_delta < 0.005:
            # No match within tolerance or already exact
            continue

        adjustment = abs(best_delta)  # = |target_mm - best_actual|
        max_adjustment = max(max_adjustment, adjustment)

        # Snap: scale the line uniformly about its start point so length == target_mm
        if best_actual > 0:
            correction = target_mm / best_actual
            direction = best_end - best_start
            new_end = best_start + direction * correction
            best_entity.dxf.end = (new_end.x, new_end.y, 0)
            logger.debug(
                f"Constraint snap: '{constraint.label}' "
                f"{best_actual:.3f}mm → {target_mm:.3f}mm "
                f"(Δ={adjustment:.3f}mm)"
            )

    return max_adjustment, dxf_doc


# ── Main parser class ─────────────────────────────────────────────────────────

class CatalogPDFParser:

    def __init__(self):
        self._llm = LLMClient()

    # ── Stage 1: Material Router ──────────────────────────────────────────────

    async def _classify_material_type(self, pdf_bytes: bytes) -> MaterialType:
        """Classify PDF as ALUMINUM_EXTRUSION, GLASS_PERFORMANCE, or HARDWARE."""
        sample = ""
        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                for page in pdf.pages[:2]:
                    t = page.extract_text() or ""
                    sample += t[:600]
        except Exception:
            pass

        if sample.strip():
            try:
                resp = await self._llm.complete(
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are a construction materials classifier. "
                                "Reply with EXACTLY one word — one of: "
                                "ALUMINUM_EXTRUSION, GLASS_PERFORMANCE, HARDWARE. "
                                "No other text."
                            ),
                        },
                        {
                            "role": "user",
                            "content": f"Catalog text sample:\n{sample[:1200]}",
                        },
                    ],
                    temperature=0.0,
                    max_tokens=10,
                )
                classification = resp.strip().upper().split()[0]
                if classification in ("ALUMINUM_EXTRUSION", "GLASS_PERFORMANCE", "HARDWARE"):
                    logger.info(f"LLM classified document as: {classification}")
                    return classification  # type: ignore[return-value]
            except Exception as e:
                logger.warning(f"LLM classification failed, using keyword fallback: {e}")

        # Keyword fallback
        lower = sample.lower()
        if any(k in lower for k in ("u-value", "u value", "transmittance", "vlt",
                                     "shading coefficient", "low-e", "ug value")):
            return "GLASS_PERFORMANCE"
        if any(k in lower for k in ("handle", "hinge", "lock", "restrictor",
                                     "geze", "roto", "dorma", "siegenia", "hardware")):
            return "HARDWARE"
        return "ALUMINUM_EXTRUSION"

    # ── Stage 2A: Digital extraction ─────────────────────────────────────────

    async def _extract_page_digital(
        self, page, material_type: MaterialType, page_num: int
    ) -> List[CatalogEntry]:
        """pdfplumber table/text → LLM structured JSON extraction."""
        tables = page.extract_tables()
        text = page.extract_text() or ""
        if not tables and not text.strip():
            return []

        raw_content = json.dumps(tables[:5]) if tables else text[:3000]
        schema = _SCHEMAS[material_type]

        prompt = (
            f"You are extracting {material_type} catalog data from a PDF page.\n"
            f"Return a JSON array following this schema exactly:\n"
            f"{json.dumps(schema, indent=2)}\n\n"
            f"Rules:\n"
            f"- Use null for any field you cannot find\n"
            f"- NEVER invent or hallucinate values\n"
            f"- Skip rows that are clearly headers or empty\n\n"
            f"Source content (page {page_num + 1}):\n{raw_content}"
        )
        try:
            raw = await self._llm.complete(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                json_mode=True,
                max_tokens=4096,
            )
            parsed = json.loads(raw) if isinstance(raw, str) else raw
            items = parsed if isinstance(parsed, list) else [parsed]
        except Exception as e:
            logger.warning(f"Digital extraction failed page {page_num + 1}: {e}")
            return []

        return [
            self._dict_to_entry(item, material_type, page_num, "digital")
            for item in items
            if isinstance(item, dict) and item.get("profile_item_code")
        ]

    # ── Stage 2B: Vision fallback ─────────────────────────────────────────────

    async def _extract_page_vision(
        self, pdf_bytes: bytes, page_num: int, material_type: MaterialType
    ) -> List[CatalogEntry]:
        """Render page to image, use Groq Vision for scanned/complex layouts."""
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            pix = doc[page_num].get_pixmap(matrix=_RENDER_MATRIX)
            img_b64 = base64.b64encode(pix.tobytes("png")).decode()
            doc.close()
        except Exception as e:
            logger.error(f"Vision render failed page {page_num + 1}: {e}")
            return []

        schema = _SCHEMAS[material_type]
        prompt = (
            f"Extract {material_type} catalog entries from this image.\n"
            f"Return JSON array following this schema:\n"
            f"{json.dumps(schema, indent=2)}\n"
            f"Use null for missing fields. Never invent values."
        )
        try:
            raw = await self._llm.complete_with_vision(
                images_base64=[img_b64], prompt=prompt
            )
            parsed = json.loads(raw) if isinstance(raw, str) else raw
            items = parsed if isinstance(parsed, list) else [parsed]
        except Exception as e:
            logger.warning(f"Vision extraction failed page {page_num + 1}: {e}")
            return []

        return [
            self._dict_to_entry(item, material_type, page_num, "vision")
            for item in items
            if isinstance(item, dict) and item.get("profile_item_code")
        ]

    # ── Dict → CatalogEntry ───────────────────────────────────────────────────

    def _dict_to_entry(
        self, item: dict, material_type: MaterialType, page_num: int, method: str
    ) -> CatalogEntry:
        code = item.get("profile_item_code", "UNKNOWN")
        entry = CatalogEntry(
            item_code=code,
            material_type=material_type,
            description=item.get("description") or "",
            supplier_name=item.get("supplier_name") or "",
            source_page=page_num,
            extraction_method=method,
            lead_time_days=item.get("lead_time_days"),
        )
        if material_type == "ALUMINUM_EXTRUSION":
            entry.system_series = item.get("system_series") or ""
            entry.weight_kg_m = item.get("weight_kg_per_m")
            entry.perimeter_mm = item.get("outer_perimeter_mm")
            entry.inertia_ix = item.get("inertia_ix")
            entry.inertia_iy = item.get("inertia_iy")
            entry.price_aed_per_kg = item.get("price_aed_per_kg")
            entry.is_thermal_break = bool(item.get("is_thermal_break", False))
            entry.price_absent = entry.price_aed_per_kg is None
        elif material_type == "GLASS_PERFORMANCE":
            entry.glass_makeup = item.get("glass_makeup")
            entry.u_value_w_m2k = item.get("u_value_w_m2k")
            entry.shading_coefficient_sc = item.get("shading_coefficient_sc")
            entry.visible_light_transmittance_vlt = item.get("visible_light_transmittance_vlt")
            entry.acoustic_rating_rw_db = item.get("acoustic_rating_rw_db")
            entry.fire_rating_minutes = item.get("fire_rating_minutes")
            entry.price_aed_sqm = item.get("price_aed_sqm")
            entry.price_absent = entry.price_aed_sqm is None
        elif material_type == "HARDWARE":
            entry.hardware_category = item.get("hardware_category")
            entry.price_aed_per_unit = item.get("price_aed_per_unit")
            entry.price_absent = entry.price_aed_per_unit is None
        return entry

    # ── Stage 3: Confidence + HITL flagging ───────────────────────────────────

    def _compute_confidence(self, entry: CatalogEntry) -> float:
        mt = entry.material_type
        required = REQUIRED_FIELDS.get(mt, [])
        optional = OPTIONAL_SCORED_FIELDS.get(mt, [])
        req_score = (
            sum(1 for f in required if getattr(entry, f, None) is not None) / len(required)
            if required else 1.0
        )
        opt_score = (
            sum(1 for f in optional if getattr(entry, f, None) is not None) / len(optional)
            if optional else 1.0
        )
        return round(req_score * 0.7 + opt_score * 0.3, 3)

    def _flag_hitl(self, entry: CatalogEntry) -> CatalogEntry:
        mt = entry.material_type
        missing = [
            f for f in REQUIRED_FIELDS.get(mt, [])
            if getattr(entry, f, None) is None
        ]
        if missing:
            entry.hitl_required = True
            entry.hitl_reason = f"Missing required fields: {', '.join(missing)}"
        elif entry.confidence_score < HITL_CONFIDENCE_THRESHOLD:
            entry.hitl_required = True
            entry.hitl_reason = f"Low confidence: {entry.confidence_score:.2f} < {HITL_CONFIDENCE_THRESHOLD}"
        return entry

    # ── Stage 4A: PDF → DXF Extraction ───────────────────────────────────────

    async def extract_profile_dxf_from_pdf(
        self,
        pdf_bytes: bytes,
        page_num: int,
        item_code: str,
    ) -> dict:
        """
        Stage 4A — Extract aluminum profile geometry from a Vector PDF page.

        Pipeline:
          1. Detect whether the page has meaningful vector paths (≥ _MIN_VECTOR_PATHS).
             If raster → return hitl signal immediately.
          2. Render page to high-res PNG for Vision LLM.
          3. Vision LLM Agent 1 (scale + anchor detection):
             - Finds one annotated dimension (e.g. "50.0") and its pixel endpoints
               → calculates mm-per-PDF-point scale factor
             - Returns anchor_origin_xy, glazing_pocket_xy, bead_snap_xy in pixel coords
               → converts to mm
          4. Convert vector paths to ezdxf document using scale factor.
          5. Save .dxf file to _DXF_OUTPUT_DIR.

        Returns dict with keys:
          success (bool), dxf_path, anchor_origin_xy, glazing_pocket_xy, bead_snap_xy,
          scale_factor, is_raster (bool), hitl_reason (str if raster)
        """
        try:
            fitz_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            page = fitz_doc[page_num]
            page_height_pt = page.rect.height
            drawings = page.get_drawings()
            fitz_doc.close()
        except Exception as e:
            logger.error(f"PyMuPDF failed on page {page_num + 1} for {item_code}: {e}")
            return {
                "success": False,
                "is_raster": False,
                "hitl_reason": f"PDF read error: {e}",
            }

        meaningful = _count_meaningful_paths(drawings)
        logger.info(
            f"[{item_code}] Page {page_num + 1}: {meaningful} meaningful vector paths found"
        )

        if meaningful < _MIN_VECTOR_PATHS:
            return {
                "success": False,
                "is_raster": True,
                "hitl_reason": (
                    "Raster PDF detected — no vector paths found. "
                    "Please upload a manual .dxf file for this die."
                ),
            }

        # Render page to PNG for Vision LLM
        try:
            fitz_doc2 = fitz.open(stream=pdf_bytes, filetype="pdf")
            pix = fitz_doc2[page_num].get_pixmap(matrix=_RENDER_MATRIX)
            img_b64 = base64.b64encode(pix.tobytes("png")).decode()
            img_width_px = pix.width
            img_height_px = pix.height
            fitz_doc2.close()
        except Exception as e:
            logger.error(f"Vision render failed for {item_code}: {e}")
            return {
                "success": False,
                "is_raster": False,
                "hitl_reason": f"Image render failed: {e}",
            }

        # Vision LLM Agent 1: scale detection + anchor point tagging
        scale_prompt = f"""You are analyzing an aluminum extrusion profile drawing (item code: {item_code}).
Image dimensions: {img_width_px} × {img_height_px} pixels.

Task: Return a JSON object with the following structure:
{{
  "scale_reference": {{
    "dimension_mm": <float — the numeric value of ONE dimension annotation you can read clearly>,
    "start_pixel": [<x>, <y>],
    "end_pixel": [<x>, <y>],
    "label": "<the text you read, e.g. '50.0'>"
  }},
  "anchor_origin_xy": [<x>, <y>],
  "glazing_pocket_xy": [<x>, <y>],
  "bead_snap_xy": [<x>, <y>]
}}

Rules:
- scale_reference: pick the longest visible dimension line with a clearly readable mm value.
  start_pixel and end_pixel are the pixel coordinates of the two ends of that dimension line.
- anchor_origin_xy: the PRIMARY mating point — typically the outermost face corner where
  this profile would mate with adjacent profiles in an assembly.
- glazing_pocket_xy: the center of the glazing pocket / glass channel where glass rests.
- bead_snap_xy: the clip-in point for the glazing bead. If not visible, set to null.
- All coordinates are in pixel space of THIS rendered image.
- Return null for glazing_pocket_xy or bead_snap_xy if the profile has no such feature.
- NEVER invent dimension values — only report what you can clearly read from text annotations."""

        scale_data = {}
        try:
            raw = await self._llm.complete_with_vision(
                images_base64=[img_b64],
                prompt=scale_prompt,
            )
            scale_data = json.loads(raw) if isinstance(raw, str) else raw
        except Exception as e:
            logger.warning(f"Vision scale detection failed for {item_code}: {e}")

        # Compute scale factor from Vision LLM response
        scale_factor = None
        ref = scale_data.get("scale_reference") or {}
        known_dim_mm = ref.get("dimension_mm")
        start_px = ref.get("start_pixel")
        end_px = ref.get("end_pixel")

        if known_dim_mm and start_px and end_px and known_dim_mm > 0:
            px_dist = _pixel_distance(tuple(start_px), tuple(end_px))
            if px_dist > 1.0:
                # px_dist pixels = known_dim_mm mm
                # px_dist / _PIXELS_PER_PDF_UNIT = PDF points for that distance
                pdf_units = px_dist / _PIXELS_PER_PDF_UNIT
                scale_factor = known_dim_mm / pdf_units
                logger.info(
                    f"[{item_code}] Scale factor: {scale_factor:.5f} mm/pt "
                    f"(ref: {known_dim_mm}mm over {pdf_units:.1f} pt)"
                )

        if scale_factor is None or scale_factor <= 0:
            # Fallback: 1 PDF pt = 0.3528 mm (standard PDF at 72dpi in mm)
            scale_factor = 0.3528
            logger.warning(
                f"[{item_code}] Vision scale detection failed — using default 0.3528 mm/pt"
            )

        # Convert anchor pixel coords to mm
        def px_to_mm(px_coord):
            if not px_coord:
                return None
            px_x, px_y = px_coord[0], px_coord[1]
            pdf_x = px_x / _PIXELS_PER_PDF_UNIT
            pdf_y = px_y / _PIXELS_PER_PDF_UNIT
            return (
                round(_pdf_point_to_mm(pdf_x, scale_factor), 3),
                round(_pdf_point_to_mm(page_height_pt - pdf_y, scale_factor), 3),
            )

        anchor_xy = px_to_mm(scale_data.get("anchor_origin_xy"))
        glazing_xy = px_to_mm(scale_data.get("glazing_pocket_xy"))
        bead_xy = px_to_mm(scale_data.get("bead_snap_xy"))

        # Convert vector paths to DXF
        try:
            dxf_doc = _paths_to_dxf(drawings, page_height_pt, scale_factor, item_code)
        except Exception as e:
            logger.error(f"DXF path conversion failed for {item_code}: {e}")
            return {
                "success": False,
                "is_raster": False,
                "hitl_reason": f"DXF conversion error: {e}",
            }

        # Save DXF file
        os.makedirs(_DXF_OUTPUT_DIR, exist_ok=True)
        safe_code = "".join(c if c.isalnum() or c in "-_" else "_" for c in item_code)
        dxf_filename = f"die_{safe_code}_p{page_num}.dxf"
        dxf_path = os.path.join(_DXF_OUTPUT_DIR, dxf_filename)
        try:
            dxf_doc.saveas(dxf_path)
            logger.info(f"[{item_code}] DXF saved: {dxf_path}")
        except Exception as e:
            logger.error(f"DXF save failed for {item_code}: {e}")
            return {
                "success": False,
                "is_raster": False,
                "hitl_reason": f"DXF save error: {e}",
            }

        return {
            "success": True,
            "is_raster": False,
            "dxf_path": dxf_path,
            "dxf_doc": dxf_doc,     # kept in memory for Stage 4B/4C
            "anchor_origin_xy": anchor_xy,
            "glazing_pocket_xy": glazing_xy,
            "bead_snap_xy": bead_xy,
            "scale_factor": scale_factor,
            "hitl_reason": "",
        }

    # ── Stage 4B: Vision QA Agent — Geometric Constraints Extraction ──────────

    async def _extract_geometric_constraints(
        self,
        pdf_bytes: bytes,
        page_num: int,
        item_code: str,
        img_b64: Optional[str] = None,
    ) -> List[GeometricConstraint]:
        """
        Stage 4B — Vision QA Agent (Agent 2).

        Scans the rendered drawing image for ALL written dimension annotations
        and returns them as a list of GeometricConstraint objects.
        Each constraint includes the mm value and pixel coordinates of the
        dimension line endpoints.
        """
        if img_b64 is None:
            try:
                fitz_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                pix = fitz_doc[page_num].get_pixmap(matrix=_RENDER_MATRIX)
                img_b64 = base64.b64encode(pix.tobytes("png")).decode()
                fitz_doc.close()
            except Exception as e:
                logger.error(f"QA Agent render failed for {item_code}: {e}")
                return []

        qa_prompt = f"""You are a precision engineering QA agent inspecting an aluminum extrusion profile drawing.
Item code: {item_code}

Task: Find EVERY visible dimension annotation in this drawing.
For each annotation, return the numeric value AND the pixel coordinates of the dimension line endpoints.

Return a JSON object:
{{
  "constraints": [
    {{
      "dimension_mm": <float — the number printed in the annotation>,
      "label": "<exact text as printed, e.g. '50.0' or '6.35'>",
      "start_pixel": [<x>, <y>],
      "end_pixel": [<x>, <y>]
    }},
    ...
  ]
}}

Rules:
- Include EVERY annotated dimension you can see, even if you see them multiple times
- dimension_mm must be the number as written — do NOT convert or round
- start_pixel/end_pixel are the pixel endpoints of the dimension witness lines
- If you cannot determine precise pixel locations, use the approximate center of the dimension text for both
- Return an empty constraints array if no dimension annotations are visible
- NEVER invent values — only report what is clearly printed"""

        try:
            raw = await self._llm.complete_with_vision(
                images_base64=[img_b64],
                prompt=qa_prompt,
            )
            data = json.loads(raw) if isinstance(raw, str) else raw
            raw_constraints = data.get("constraints", [])
        except Exception as e:
            logger.warning(f"QA Agent constraint extraction failed for {item_code}: {e}")
            return []

        result = []
        for c in raw_constraints:
            try:
                dim = float(c.get("dimension_mm", 0))
                if dim <= 0:
                    continue
                sp = c.get("start_pixel")
                ep = c.get("end_pixel")
                result.append(GeometricConstraint(
                    dimension_mm=dim,
                    label=str(c.get("label", dim)),
                    start_px=tuple(sp) if sp else None,
                    end_px=tuple(ep) if ep else None,
                ))
            except Exception:
                continue

        logger.info(f"[{item_code}] QA Agent found {len(result)} geometric constraints")
        return result

    # ── Stage 4: Full DXF pipeline (4A + 4B + 4C + 4D) ──────────────────────

    async def _run_dxf_pipeline(
        self,
        pdf_bytes: bytes,
        page_num: int,
        item_code: str,
        entries: List[CatalogEntry],
    ) -> None:
        """
        Runs the full 4-stage DXF extraction and QA pipeline for an aluminum page.
        Mutates the CatalogEntry objects in `entries` in-place with DXF metadata.
        """
        # Stage 4A: Extract DXF from vector PDF
        result_4a = await self.extract_profile_dxf_from_pdf(pdf_bytes, page_num, item_code)

        if not result_4a["success"]:
            # Raster or error — flag all entries on this page for HITL
            reason = result_4a.get("hitl_reason", "DXF extraction failed")
            for e in entries:
                e.hitl_required = True
                e.hitl_reason = reason
                e.die_status = "RAW"
            logger.warning(f"[{item_code}] Stage 4A failed: {reason}")
            return

        dxf_path = result_4a["dxf_path"]
        dxf_doc = result_4a["dxf_doc"]
        anchor_xy = result_4a["anchor_origin_xy"]
        glazing_xy = result_4a["glazing_pocket_xy"]
        bead_xy = result_4a["bead_snap_xy"]
        scale_factor = result_4a["scale_factor"]

        # Stage 4B: Vision QA Agent — extract all dimension annotations
        constraints = await self._extract_geometric_constraints(
            pdf_bytes, page_num, item_code
        )

        # Stage 4C: Apply constraints — snap vertices to annotated dimensions
        max_adjustment_mm, dxf_doc = apply_geometric_constraints(dxf_doc, constraints)

        # Stage 4D: Auto-verification gating
        if max_adjustment_mm < 1.0:
            die_status = "VERIFIED"
            logger.info(
                f"[{item_code}] Auto-verified: max vertex adjustment {max_adjustment_mm:.3f}mm < 1.0mm"
            )
        else:
            die_status = "DRAFT_REQUIRES_VERIFICATION"
            logger.warning(
                f"[{item_code}] Requires verification: max vertex adjustment "
                f"{max_adjustment_mm:.3f}mm ≥ 1.0mm"
            )

        # Save the constraint-corrected DXF (overwrite the raw version)
        try:
            dxf_doc.saveas(dxf_path)
        except Exception as e:
            logger.error(f"Failed to save corrected DXF for {item_code}: {e}")

        # Mutate all catalog entries from this page with DXF metadata
        for e in entries:
            e.dxf_path = dxf_path
            e.anchor_origin_xy = anchor_xy
            e.glazing_pocket_xy = glazing_xy
            e.bead_snap_xy = bead_xy
            e.scale_factor = scale_factor
            e.die_status = die_status

            # For DRAFT status, also flag HITL so a human reviews the drawing
            if die_status == "DRAFT_REQUIRES_VERIFICATION":
                e.hitl_required = True
                e.hitl_reason = (
                    f"DXF geometry requires verification: max dimension deviation "
                    f"{max_adjustment_mm:.2f}mm ≥ 1.0mm threshold. "
                    f"Please review and approve the extracted .dxf before use."
                )

    # ── Main entry point ──────────────────────────────────────────────────────

    async def parse(
        self, pdf_bytes: bytes, source_name: str = "unknown"
    ) -> List[CatalogEntry]:
        """
        Async-native parse. Called from Celery task via _run_async() helper.
        Returns ALL entries including HITL-flagged ones (never discards).

        For ALUMINUM_EXTRUSION documents, also runs the Stage 4 DXF pipeline
        per page to extract profile geometry, anchor points, and auto-verify
        the extracted DXF against written dimension annotations.
        """
        material_type = await self._classify_material_type(pdf_bytes)
        logger.info(f"[{source_name}] Classified as: {material_type}")

        all_entries: List[CatalogEntry] = []

        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            total_pages = len(pdf.pages)
            for i, page in enumerate(pdf.pages):
                logger.debug(f"[{source_name}] Processing page {i + 1}/{total_pages}")
                entries = await self._extract_page_digital(page, material_type, i)

                if not entries:
                    # Fallback to vision for image-heavy or scanned pages
                    entries = await self._extract_page_vision(pdf_bytes, i, material_type)

                for e in entries:
                    e.confidence_score = self._compute_confidence(e)
                    e = self._flag_hitl(e)
                    all_entries.append(e)

                # Stage 4: DXF extraction for aluminum pages that yielded entries
                if material_type == "ALUMINUM_EXTRUSION" and entries:
                    # Use the item_code of the first entry on this page as the die identifier
                    representative_code = entries[0].item_code
                    try:
                        await self._run_dxf_pipeline(
                            pdf_bytes, i, representative_code, entries
                        )
                    except Exception as dxf_err:
                        logger.error(
                            f"[{source_name}] DXF pipeline error page {i + 1}: {dxf_err}"
                        )

        hitl_count = sum(1 for e in all_entries if e.hitl_required)
        verified_count = sum(1 for e in all_entries if e.die_status == "VERIFIED")
        draft_count = sum(
            1 for e in all_entries if e.die_status == "DRAFT_REQUIRES_VERIFICATION"
        )
        logger.info(
            f"[{source_name}] Extracted {len(all_entries)} items "
            f"({hitl_count} HITL | {verified_count} DXF-verified | {draft_count} DXF-draft)"
        )
        return all_entries

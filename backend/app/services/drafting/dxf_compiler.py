"""
Parametric Constraint Assembly Engine.

Compiles Shop Drawing section details from a DraftingRecipe + SmartProfileDie registry.
Uses ezdxf for DXF generation and Shapely for geometric collision validation.

Key guarantee: if GeometryCollisionError is raised, the LLM receives a structured
error message and retries with a different bead/gasket combination or thinner glass.
"""
import math
import logging
from typing import Dict, List, Tuple

import ezdxf
from ezdxf.math import Vec2
from shapely.geometry import Polygon
from shapely.affinity import translate, rotate

from app.services.drafting.smart_die import DraftingRecipe, SmartProfileDie

logger = logging.getLogger("masaad-dxf-compiler")

COLLISION_TOLERANCE_MM2 = 0.05  # Intersections smaller than this are ignored (manufacturing fit)


class GeometryCollisionError(Exception):
    """
    Raised when the glass infill polygon intersects aluminum profile bounding boxes.

    The message is structured so the LangGraph retry loop can parse it:
        GEOMETRY_COLLISION: Glass infill intersects profiles [...] (overlap=X mm²).
        Action required: reduce glass_thickness_mm or select a bead with deeper pocket.
    """
    def __init__(self, colliding_profiles: List[str], overlap_area: float):
        self.colliding_profiles = colliding_profiles
        self.overlap_area = overlap_area
        super().__init__(
            f"GEOMETRY_COLLISION: Glass infill intersects profiles {colliding_profiles} "
            f"(overlap={overlap_area:.3f} mm²). "
            f"Action required: reduce glass_thickness_mm or select a bead with deeper pocket."
        )


def assemble_section_detail(
    recipe: DraftingRecipe,
    die_registry: Dict[str, SmartProfileDie],
    output_path: str,
) -> str:
    """
    Compile a DXF section detail from a DraftingRecipe.

    Args:
        recipe: The LLM-generated assembly specification (DraftingRecipe JSON).
        die_registry: Dict[item_code → SmartProfileDie] loaded for this tenant.
        output_path: Absolute path where the output .dxf file will be written.

    Returns:
        output_path on success.

    Raises:
        GeometryCollisionError: If glass polygon intersects any aluminum bounding box.
        ValueError: If a referenced item_code is not in die_registry.
    """
    doc = ezdxf.new("R2010")
    doc.layers.add("ALUMINUM", color=7)       # white/black
    doc.layers.add("GLASS", color=4)          # cyan
    doc.layers.add("ANNOTATIONS", color=3)    # green

    msp = doc.modelspace()
    placed_shapes: List[Tuple[str, Polygon]] = []  # (item_code, world-space polygon)

    # ── STAGE 1: Insert profile blocks ───────────────────────────────────────
    for placement in recipe.profiles:
        die = die_registry.get(placement.item_code)
        if die is None:
            raise ValueError(
                f"SmartProfileDie not found for item_code='{placement.item_code}'. "
                f"Available: {list(die_registry.keys())}"
            )

        # Hard constraint: glass must fit this die's pocket
        if recipe.glass_thickness_mm > die.max_glass_thickness:
            raise GeometryCollisionError(
                colliding_profiles=[placement.item_code],
                overlap_area=0.0,
            )

        # Compute translation: move die.anchor_origin_xy → placement.position_xy
        anchor = Vec2(die.anchor_origin_xy)
        target = Vec2(placement.position_xy)
        offset = target - anchor

        # Try to import the die's block from its source .dxf
        final_block_name = _import_die_block(die, doc)

        if final_block_name:
            msp.add_blockref(
                final_block_name,
                insert=placement.position_xy,
                dxfattribs={
                    "layer": "ALUMINUM",
                    "rotation": placement.rotation_deg,
                    "xscale": 1.0,
                    "yscale": 1.0,
                },
            )
        else:
            # Fallback: draw bounding box outline
            world_pts = _transform_points(die.bounding_box_polygon, offset.x, offset.y, placement.rotation_deg)
            msp.add_lwpolyline(
                world_pts + [world_pts[0]],
                dxfattribs={"layer": "ALUMINUM"},
            )

        # Build Shapely polygon in world space for collision checking
        raw_poly = Polygon(die.bounding_box_polygon)
        world_poly = translate(raw_poly, xoff=offset.x, yoff=offset.y)
        if placement.rotation_deg != 0.0:
            world_poly = rotate(
                world_poly,
                placement.rotation_deg,
                origin=placement.position_xy,
                use_radians=False,
            )
        placed_shapes.append((placement.item_code, world_poly))

    # ── STAGE 2: Compute glass infill polygon ─────────────────────────────────
    mullion = next(
        (p for p in recipe.profiles if p.role == "mullion"),
        recipe.profiles[0],
    )
    mullion_die = die_registry[mullion.item_code]

    anchor_dx = mullion.position_xy[0] - mullion_die.anchor_origin_xy[0]
    anchor_dy = mullion.position_xy[1] - mullion_die.anchor_origin_xy[1]
    glass_cx = mullion_die.glazing_pocket_xy[0] + anchor_dx
    glass_cy = mullion_die.glazing_pocket_xy[1] + anchor_dy

    half_t = recipe.glass_thickness_mm / 2.0
    gap = recipe.glass_gap_clearance_mm
    h = recipe.glass_section_height_mm

    glass_corners = [
        (glass_cx - half_t + gap, glass_cy),
        (glass_cx + half_t - gap, glass_cy),
        (glass_cx + half_t - gap, glass_cy + h),
        (glass_cx - half_t + gap, glass_cy + h),
    ]
    glass_poly = Polygon(glass_corners)

    # ── STAGE 3: Shapely collision validation ─────────────────────────────────
    collisions: List[str] = []
    total_overlap = 0.0
    for item_code, alum_poly in placed_shapes:
        intersection = glass_poly.intersection(alum_poly)
        if intersection.area > COLLISION_TOLERANCE_MM2:
            collisions.append(item_code)
            total_overlap += intersection.area

    if collisions:
        raise GeometryCollisionError(
            colliding_profiles=collisions,
            overlap_area=total_overlap,
        )

    # ── STAGE 4: Draw glass in DXF ────────────────────────────────────────────
    msp.add_lwpolyline(
        glass_corners + [glass_corners[0]],
        dxfattribs={"layer": "GLASS"},
    )
    hatch = msp.add_hatch(color=4, dxfattribs={"layer": "GLASS"})
    hatch.set_pattern_fill("ANSI31", scale=0.5, angle=45)
    hatch.paths.add_polyline_path(
        [Vec2(pt) for pt in glass_corners],
        is_closed=True,
    )

    # ── STAGE 5: Auto-annotation — leader lines to centroids ─────────────────
    placed_map = {code: poly for code, poly in placed_shapes}

    for i, placement in enumerate(recipe.profiles):
        alum_poly = placed_map.get(placement.item_code)
        if alum_poly is None:
            continue

        cx = alum_poly.centroid.x
        cy = alum_poly.centroid.y

        # Alternate leader direction to prevent label pile-up
        side = 1 if i % 2 == 0 else -1
        label_x = cx + side * 35.0
        label_y = cy + 10.0

        msp.add_leader(
            vertices=[Vec2(cx, cy), Vec2(label_x, label_y)],
            dxfattribs={"layer": "ANNOTATIONS"},
        )
        msp.add_text(
            f"{placement.item_code} ({placement.role})",
            dxfattribs={
                "layer": "ANNOTATIONS",
                "height": 2.5,
                "insert": (label_x + (2 if side > 0 else -30), label_y),
            },
        )

    doc.saveas(output_path)
    logger.info(f"Section detail compiled: {output_path}")
    return output_path


# ── Helpers ───────────────────────────────────────────────────────────────────

def _import_die_block(die: SmartProfileDie, target_doc) -> str | None:
    """Import die's DXF block into target document. Returns block name or None."""
    if not die.dxf_path:
        return None
    try:
        source_doc = ezdxf.readfile(die.dxf_path)
        block_name = f"DIE_{die.die_number}"

        # Find the first usable block in source
        source_block = source_doc.blocks.get(block_name)
        if source_block is None:
            source_block = next(
                (b for b in source_doc.blocks if not b.name.startswith("*")),
                None,
            )

        if source_block:
            importer = ezdxf.xref.Importer(source_doc, target_doc)
            importer.import_block(source_block.name)
            return source_block.name
    except Exception as e:
        logger.warning(f"Could not import block from {die.dxf_path}: {e}")
    return None


def _transform_points(
    points: List[Tuple[float, float]],
    dx: float,
    dy: float,
    angle_deg: float,
) -> List[Tuple[float, float]]:
    """Translate then rotate a list of 2D points."""
    rad = math.radians(angle_deg)
    cos_a, sin_a = math.cos(rad), math.sin(rad)
    result = []
    for x, y in points:
        tx, ty = x + dx, y + dy
        rx = tx * cos_a - ty * sin_a
        ry = tx * sin_a + ty * cos_a
        result.append((rx, ry))
    return result

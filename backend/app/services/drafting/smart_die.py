"""
Smart Die schema definitions for the Parametric Constraint Assembly Engine.

Design principle:
  The LLM NEVER writes raw DXF code or geometry coordinates.
  The LLM's only job is to output a DraftingRecipe JSON specifying WHICH Smart Dies
  to use and WHERE to place them. The Python DXF compiler handles all geometry.
"""
from typing import List, Tuple, Optional
from pydantic import BaseModel


class SmartProfileDie(BaseModel):
    """
    One aluminum extrusion die with full constraint metadata.
    Loaded from the smart_profile_dies DB table.
    """
    item_code: str
    die_number: str
    dxf_path: str                                     # Absolute path to source .dxf block
    anchor_origin_xy: Tuple[float, float]             # Primary mating anchor (mm, world space)
    glazing_pocket_xy: Tuple[float, float]            # Where glass edge rests
    bead_snap_xy: Tuple[float, float]                 # Where glazing bead clips in
    max_glass_thickness: float                        # mm — hard upper bound for glass
    bounding_box_polygon: List[Tuple[float, float]]   # Profile silhouette for Shapely collision
    description: str = ""
    system_series: str = ""


class ProfilePlacement(BaseModel):
    """One die positioned in the assembly."""
    item_code: str                          # Must exist in die_registry
    role: str                               # mullion | transom | bead | sill | head
    position_xy: Tuple[float, float]        # Where anchor_origin_xy lands in world space
    rotation_deg: float = 0.0


class DraftingRecipe(BaseModel):
    """
    LLM output contract.

    The LLM provides WHICH dies to use and WHERE to place them.
    It never writes raw DXF coordinates or bounding box geometry.
    All geometric validation and DXF assembly happens in dxf_compiler.py.
    """
    estimate_id: str
    section_name: str           # e.g. "Typical Mullion-Transom Junction - Grid A1"
    system_type: str            # curtain_wall | sliding_door | casement_window
    profiles: List[ProfilePlacement]
    glass_thickness_mm: float
    glass_gap_clearance_mm: float = 2.0      # Edge clearance from pocket face
    glass_section_height_mm: float = 100.0  # Visible glass height in section detail
    output_scale: float = 1.0
    paper_size: str = "A3"

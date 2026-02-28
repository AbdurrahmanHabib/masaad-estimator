"""
Shop Drawing Engine — generates professional facade shop drawings as PDF.

Format follows UAE industry standard (GINCO/ALUMIL style):
  - A3 landscape pages (420×297mm)
  - Each unique opening type gets a schedule sheet with:
    • Info box (type, description, location, glass, finish, qty)
    • Front elevation view with panel layout and dimensions
    • Plan view (horizontal section through frame)
    • Section view (vertical section through frame)
    • Glass mark table
  - Title block with company branding, drawing number, revision, date

Supplier: Elite Extrusion L.L.C / Glazetech — RAK, UAE
"""
import io
import os
import math
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib.units import mm, cm
from reportlab.lib.colors import (
    HexColor, black, white, Color,
    lightgrey, darkgrey, grey,
)
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics

logger = logging.getLogger("masaad-shop-drawing")

# ── Constants ────────────────────────────────────────────────────────────────

PAGE_SIZE = landscape(A3)  # 420mm × 297mm
PAGE_W, PAGE_H = PAGE_SIZE

BRAND_NAVY = HexColor("#002147")
BRAND_DARK = HexColor("#1e293b")
BRAND_GREY = HexColor("#64748b")
BRAND_LIGHT = HexColor("#f1f5f9")
ACCENT_BLUE = HexColor("#3b82f6")
DIM_LINE_COLOR = HexColor("#333333")
GLASS_FILL = HexColor("#cce6ff")
GLASS_FILL_SLIDING = HexColor("#b3d9ff")
FRAME_COLOR = HexColor("#4a4a4a")
PANEL_FIXED_COLOR = HexColor("#d4e8ff")
PANEL_SLIDING_COLOR = HexColor("#b8e0d2")

DEFAULT_COMPANY = "MADINAT AL SAADA ALUMINIUM & GLASS WORKS LLC"
DEFAULT_SUB = "Ajman, UAE  |  www.madinatalsaada.ae"

# Glazetech system descriptions
SYSTEM_DESCRIPTIONS = {
    "Window - Sliding (Lift & Slide TB)": "GLAZETECH LIFT & SLIDE THERMAL BREAK WINDOW",
    "Window - Sliding (Eco 500 TB)": "GLAZETECH ECO 500 SLIDING THERMAL BREAK WINDOW",
    "Window - Sliding": "GLAZETECH SLIM SLIDING WINDOW",
    "Door - Sliding": "GLAZETECH LIFT & SLIDE THERMAL BREAK DOOR",
    "Glass Railing": "FRAMELESS GLASS RAILING SYSTEM",
}

FRAME_DEPTHS = {
    "Window - Sliding (Lift & Slide TB)": 160,
    "Window - Sliding (Eco 500 TB)": 70,
    "Window - Sliding": 48,
    "Door - Sliding": 160,
    "Glass Railing": 50,
}


# ── Title Block ──────────────────────────────────────────────────────────────

def _draw_title_block(c, page_w, page_h, drawing_info: dict):
    """Draw professional title block at bottom-right of page."""
    tb_w = 180 * mm
    tb_h = 45 * mm
    tb_x = page_w - tb_w - 10 * mm
    tb_y = 10 * mm

    # Outer border
    c.setStrokeColor(black)
    c.setLineWidth(1.5)
    c.rect(tb_x, tb_y, tb_w, tb_h)

    # Company section (top half)
    mid_y = tb_y + tb_h / 2
    c.setLineWidth(0.5)
    c.line(tb_x, mid_y, tb_x + tb_w, mid_y)

    # Company name
    c.setFillColor(BRAND_NAVY)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(tb_x + 3 * mm, tb_y + tb_h - 6 * mm,
                 drawing_info.get("company", DEFAULT_COMPANY))
    c.setFont("Helvetica", 5.5)
    c.setFillColor(BRAND_GREY)
    c.drawString(tb_x + 3 * mm, tb_y + tb_h - 11 * mm,
                 drawing_info.get("company_sub", DEFAULT_SUB))

    # Drawing title
    c.setFont("Helvetica-Bold", 7)
    c.setFillColor(black)
    c.drawString(tb_x + 3 * mm, tb_y + tb_h - 17 * mm, "SHOP DRAWING")
    c.setFont("Helvetica", 6)
    c.drawString(tb_x + 3 * mm, tb_y + tb_h - 22 * mm,
                 drawing_info.get("title", "ALUMINIUM WINDOWS & DOORS SCHEDULE"))

    # Info grid (bottom half)
    cols = [
        ("Project:", drawing_info.get("project", "")),
        ("Drawing No:", drawing_info.get("drawing_no", "")),
        ("Sheet:", drawing_info.get("sheet", "")),
        ("Rev:", drawing_info.get("revision", "00")),
        ("Date:", drawing_info.get("date", datetime.now().strftime("%d-%m-%Y"))),
        ("Scale:", drawing_info.get("scale", "NTS")),
    ]

    col_w = tb_w / 3
    row_h = (mid_y - tb_y) / 2
    c.setFont("Helvetica", 5)
    c.setFillColor(BRAND_GREY)
    for i, (label, value) in enumerate(cols):
        col = i % 3
        row = i // 3
        x = tb_x + col * col_w + 2 * mm
        y = mid_y - (row + 1) * row_h + row_h - 5 * mm

        c.setFont("Helvetica", 5)
        c.setFillColor(BRAND_GREY)
        c.drawString(x, y + 4 * mm, label)
        c.setFont("Helvetica-Bold", 6)
        c.setFillColor(black)
        c.drawString(x, y, str(value))

    # Grid lines
    c.setLineWidth(0.3)
    for i in range(1, 3):
        c.line(tb_x + i * col_w, tb_y, tb_x + i * col_w, mid_y)
    c.line(tb_x, tb_y + row_h, tb_x + tb_w, tb_y + row_h)


# ── Page Border ──────────────────────────────────────────────────────────────

def _draw_page_border(c, page_w, page_h):
    """Draw page border with margin."""
    margin = 8 * mm
    c.setStrokeColor(black)
    c.setLineWidth(1.0)
    c.rect(margin, margin, page_w - 2 * margin, page_h - 2 * margin)
    # Inner line
    c.setLineWidth(0.3)
    c.rect(margin + 1 * mm, margin + 1 * mm,
           page_w - 2 * margin - 2 * mm, page_h - 2 * margin - 2 * mm)


# ── Info Box ─────────────────────────────────────────────────────────────────

def _draw_info_box(c, x, y, w, h, info: dict):
    """Draw opening info box (type, description, location, glass, finish, qty)."""
    # Box border
    c.setStrokeColor(black)
    c.setLineWidth(0.8)
    c.rect(x, y, w, h)

    # Header
    header_h = 8 * mm
    c.setFillColor(BRAND_NAVY)
    c.rect(x, y + h - header_h, w, header_h, fill=1, stroke=1)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(x + w / 2, y + h - header_h + 2.5 * mm,
                        info.get("type_code", ""))

    # Fields
    fields = [
        ("DESCRIPTION:", info.get("description", "")),
        ("SYSTEM:", info.get("system_series", "")),
        ("LOCATION:", info.get("location", "")),
        ("GLASS TYPE:", info.get("glass_type", "")),
        ("FINISH:", info.get("finish", "POWDER COATED ALUMINIUM")),
        ("TOTAL QTY:", info.get("qty", "")),
        ("CONFIG:", info.get("configuration", "")),
    ]

    row_h = (h - header_h) / len(fields)
    c.setLineWidth(0.3)
    for i, (label, value) in enumerate(fields):
        fy = y + h - header_h - (i + 1) * row_h
        # Horizontal line
        if i > 0:
            c.setStrokeColor(lightgrey)
            c.line(x, fy + row_h, x + w, fy + row_h)

        c.setFillColor(BRAND_GREY)
        c.setFont("Helvetica", 5)
        c.drawString(x + 2 * mm, fy + row_h - 3.5 * mm, label)
        c.setFillColor(black)
        c.setFont("Helvetica-Bold", 6.5)
        c.drawString(x + 28 * mm, fy + row_h - 3.5 * mm, str(value))


# ── Dimension Lines ──────────────────────────────────────────────────────────

def _draw_dim_horizontal(c, x1, x2, y, label, offset=8*mm, above=True):
    """Draw a horizontal dimension line with arrows and label."""
    c.setStrokeColor(DIM_LINE_COLOR)
    c.setLineWidth(0.4)

    dy = offset if above else -offset

    # Extension lines
    c.line(x1, y, x1, y + dy)
    c.line(x2, y, x2, y + dy)

    # Dimension line
    dim_y = y + dy
    c.line(x1, dim_y, x2, dim_y)

    # Arrows
    arrow_len = 2 * mm
    # Left arrow
    c.line(x1, dim_y, x1 + arrow_len, dim_y + 0.8 * mm)
    c.line(x1, dim_y, x1 + arrow_len, dim_y - 0.8 * mm)
    # Right arrow
    c.line(x2, dim_y, x2 - arrow_len, dim_y + 0.8 * mm)
    c.line(x2, dim_y, x2 - arrow_len, dim_y - 0.8 * mm)

    # Label
    c.setFillColor(DIM_LINE_COLOR)
    c.setFont("Helvetica", 5.5)
    mid_x = (x1 + x2) / 2
    c.drawCentredString(mid_x, dim_y + 1.2 * mm, str(label))


def _draw_dim_vertical(c, x, y1, y2, label, offset=8*mm, right=True):
    """Draw a vertical dimension line with arrows and label."""
    c.setStrokeColor(DIM_LINE_COLOR)
    c.setLineWidth(0.4)

    dx = offset if right else -offset

    # Extension lines
    c.line(x, y1, x + dx, y1)
    c.line(x, y2, x + dx, y2)

    # Dimension line
    dim_x = x + dx
    c.line(dim_x, y1, dim_x, y2)

    # Arrows
    arrow_len = 2 * mm
    c.line(dim_x, y1, dim_x + 0.8 * mm, y1 + arrow_len)
    c.line(dim_x, y1, dim_x - 0.8 * mm, y1 + arrow_len)
    c.line(dim_x, y2, dim_x + 0.8 * mm, y2 - arrow_len)
    c.line(dim_x, y2, dim_x - 0.8 * mm, y2 - arrow_len)

    # Label (rotated)
    c.saveState()
    mid_y = (y1 + y2) / 2
    c.setFillColor(DIM_LINE_COLOR)
    c.setFont("Helvetica", 5.5)
    c.translate(dim_x + 2.5 * mm, mid_y)
    c.rotate(90)
    c.drawCentredString(0, 0, str(label))
    c.restoreState()


# ── Elevation View ───────────────────────────────────────────────────────────

def _draw_elevation_view(c, cx, cy, draw_w, draw_h, opening: dict, subdivision: dict):
    """
    Draw front elevation of opening with panel layout.
    cx, cy = center of drawing area.
    draw_w, draw_h = available drawing area dimensions.
    """
    panels = subdivision.get("panels", [])
    config = subdivision.get("configuration", "F")
    ow = max(float(opening.get("width_mm", 1000) or 1000), 100)
    oh = max(float(opening.get("height_mm", 1000) or 1000), 100)

    # Calculate scale to fit in drawing area with margin
    margin = 15 * mm
    avail_w = draw_w - 2 * margin
    avail_h = draw_h - 2 * margin
    scale_x = avail_w / ow
    scale_y = avail_h / oh
    scale = min(scale_x, scale_y, 0.15)  # Cap at 0.15 mm/mm to avoid huge drawings

    # Drawing dimensions in page units
    dw = ow * scale
    dh = oh * scale

    # Origin (bottom-left of opening)
    ox = cx - dw / 2
    oy = cy - dh / 2

    # Outer frame
    c.setStrokeColor(FRAME_COLOR)
    c.setLineWidth(1.5)
    c.rect(ox, oy, dw, dh)

    # Draw panels
    if panels:
        panel_x = ox
        for panel in panels:
            pw = float(panel.get("panel_width_mm", ow / len(panels))) * scale
            ph = dh
            p_type = panel.get("panel_type", "F")

            # Panel fill
            if p_type == "S":
                c.setFillColor(PANEL_SLIDING_COLOR)
            else:
                c.setFillColor(PANEL_FIXED_COLOR)

            c.setStrokeColor(FRAME_COLOR)
            c.setLineWidth(0.8)
            c.rect(panel_x, oy, pw, ph, fill=1, stroke=1)

            # Glass pane inside panel (with sash/bead deduction shown)
            gw_mm = float(panel.get("glass_width_mm", 0))
            gh_mm = float(panel.get("glass_height_mm", 0))
            if gw_mm > 0 and gh_mm > 0:
                gw = gw_mm * scale
                gh = gh_mm * scale
                gx = panel_x + (pw - gw) / 2
                gy = oy + (ph - gh) / 2

                c.setFillColor(GLASS_FILL if p_type == "F" else GLASS_FILL_SLIDING)
                c.setStrokeColor(HexColor("#666666"))
                c.setLineWidth(0.5)
                c.rect(gx, gy, gw, gh, fill=1, stroke=1)

                # Glass cross for fixed panels
                if p_type == "F":
                    c.setStrokeColor(HexColor("#aaccee"))
                    c.setLineWidth(0.3)
                    c.line(gx, gy, gx + gw, gy + gh)
                    c.line(gx + gw, gy, gx, gy + gh)

                # Sliding arrow for sliding panels
                if p_type == "S":
                    arrow_y = gy + gh / 2
                    arrow_x1 = gx + gw * 0.3
                    arrow_x2 = gx + gw * 0.7
                    c.setStrokeColor(HexColor("#4a7a6a"))
                    c.setLineWidth(0.6)
                    c.line(arrow_x1, arrow_y, arrow_x2, arrow_y)
                    # Arrow head
                    c.line(arrow_x2, arrow_y, arrow_x2 - 2*mm, arrow_y + 1.2*mm)
                    c.line(arrow_x2, arrow_y, arrow_x2 - 2*mm, arrow_y - 1.2*mm)

            # Panel label
            c.setFillColor(black)
            c.setFont("Helvetica-Bold", 6)
            label = f"{p_type}"
            c.drawCentredString(panel_x + pw / 2, oy + ph + 2 * mm, label)

            # Panel glass size label
            if gw_mm > 0 and gh_mm > 0:
                c.setFont("Helvetica", 4.5)
                c.setFillColor(BRAND_GREY)
                c.drawCentredString(panel_x + pw / 2, oy + ph / 2 + 1.5 * mm,
                                    f"{gw_mm:.0f} × {gh_mm:.0f}")
                weight = float(panel.get("glass_weight_kg", 0))
                c.drawCentredString(panel_x + pw / 2, oy + ph / 2 - 2.5 * mm,
                                    f"{weight:.1f} kg")

            panel_x += pw

            # Interlock line between panels
            if panel != panels[-1]:
                c.setStrokeColor(HexColor("#999999"))
                c.setLineWidth(0.3)
                c.setDash(2, 2)
                c.line(panel_x, oy, panel_x, oy + dh)
                c.setDash()
    else:
        # No subdivision — single glass pane
        c.setFillColor(GLASS_FILL)
        c.setStrokeColor(HexColor("#666666"))
        c.setLineWidth(0.5)
        glass_margin = 3 * mm
        c.rect(ox + glass_margin, oy + glass_margin,
               dw - 2 * glass_margin, dh - 2 * glass_margin, fill=1, stroke=1)

    # F.F.L label at bottom
    c.setFillColor(black)
    c.setFont("Helvetica", 5)
    c.drawString(ox - 12 * mm, oy - 1 * mm, "F.F.L")
    c.setStrokeColor(black)
    c.setLineWidth(0.5)
    c.line(ox - 14 * mm, oy, ox + dw + 5 * mm, oy)  # floor line

    # Overall width dimension (above)
    _draw_dim_horizontal(c, ox, ox + dw, oy + dh, f"{ow:.0f}", offset=12 * mm, above=True)

    # Overall height dimension (right)
    _draw_dim_vertical(c, ox + dw, oy, oy + dh, f"{oh:.0f}", offset=12 * mm, right=True)

    # Panel width dimensions (below)
    if panels and len(panels) > 1:
        panel_x = ox
        for panel in panels:
            pw_mm = float(panel.get("panel_width_mm", 0))
            pw = pw_mm * scale
            _draw_dim_horizontal(c, panel_x, panel_x + pw, oy,
                                 f"{pw_mm:.0f}", offset=7 * mm, above=False)
            panel_x += pw

    # Configuration label
    c.setFont("Helvetica-Bold", 7)
    c.setFillColor(BRAND_NAVY)
    config_label = subdivision.get("config_description", config)
    c.drawCentredString(cx, oy - 14 * mm, f"Configuration: {config}")

    # View label
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(black)
    c.drawCentredString(cx, oy + dh + 18 * mm, "ELEVATION")
    c.setFont("Helvetica", 5.5)
    c.drawCentredString(cx, oy + dh + 14 * mm, drawing_info_scale(ow))

    return scale, ox, oy, dw, dh


def drawing_info_scale(width_mm: float) -> str:
    """Calculate appropriate display scale."""
    if width_mm > 5000:
        return "Scale: 1:50"
    elif width_mm > 2000:
        return "Scale: 1:20"
    else:
        return "Scale: 1:10"


# ── Plan View ────────────────────────────────────────────────────────────────

def _draw_plan_view(c, cx, cy, draw_w, draw_h, opening: dict, subdivision: dict):
    """Draw horizontal plan section through the opening."""
    ow = max(float(opening.get("width_mm", 1000) or 1000), 100)
    system_type = opening.get("system_type", "")
    frame_depth = FRAME_DEPTHS.get(system_type, 80)
    panels = subdivision.get("panels", [])

    # Scale
    avail_w = draw_w - 30 * mm
    scale = min(avail_w / ow, 0.15)
    depth_scale = min((draw_h - 20 * mm) / frame_depth, 0.8)
    actual_depth_scale = min(scale * 3, depth_scale)  # Exaggerate depth

    dw = ow * scale
    dd = frame_depth * actual_depth_scale

    ox = cx - dw / 2
    oy = cy - dd / 2

    # Outer frame (plan view)
    c.setStrokeColor(FRAME_COLOR)
    c.setLineWidth(1.2)
    c.rect(ox, oy, dw, dd)

    # Wall hatching on sides
    wall_w = 4 * mm
    c.setFillColor(HexColor("#e0e0e0"))
    c.rect(ox - wall_w, oy - 2 * mm, wall_w, dd + 4 * mm, fill=1, stroke=1)
    c.rect(ox + dw, oy - 2 * mm, wall_w, dd + 4 * mm, fill=1, stroke=1)

    # Draw panel tracks in plan
    if panels:
        panel_x = ox
        num_tracks = sum(1 for p in panels if p.get("panel_type") == "S")
        track_spacing = dd / max(num_tracks + 1, 2)

        for panel in panels:
            pw = float(panel.get("panel_width_mm", ow / len(panels))) * scale
            p_type = panel.get("panel_type", "F")

            if p_type == "F":
                # Fixed panel: single glass line in plan
                c.setFillColor(GLASS_FILL)
                c.setStrokeColor(FRAME_COLOR)
                c.setLineWidth(0.5)
                glass_y = oy + dd / 2 - 0.5 * mm
                c.rect(panel_x + 1 * mm, glass_y, pw - 2 * mm, 1 * mm, fill=1, stroke=1)
            else:
                # Sliding panel: glass line offset to show track
                c.setFillColor(GLASS_FILL_SLIDING)
                c.setStrokeColor(FRAME_COLOR)
                c.setLineWidth(0.5)
                glass_y = oy + dd * 0.35
                c.rect(panel_x + 1 * mm, glass_y, pw - 2 * mm, 1 * mm, fill=1, stroke=1)

                # Track lines
                c.setStrokeColor(HexColor("#aaaaaa"))
                c.setLineWidth(0.3)
                c.setDash(1, 1)
                c.line(panel_x, oy + dd * 0.3, panel_x + pw, oy + dd * 0.3)
                c.line(panel_x, oy + dd * 0.7, panel_x + pw, oy + dd * 0.7)
                c.setDash()

            panel_x += pw

    # Overall width dimension
    _draw_dim_horizontal(c, ox, ox + dw, oy + dd, f"{ow:.0f}",
                         offset=6 * mm, above=True)

    # Depth dimension
    _draw_dim_vertical(c, ox + dw, oy, oy + dd, f"{frame_depth}",
                       offset=8 * mm, right=True)

    # Labels
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(black)
    c.drawCentredString(cx, oy + dd + 12 * mm, "PLAN")

    c.setFont("Helvetica", 5)
    c.setFillColor(BRAND_GREY)
    c.drawString(ox - wall_w - 1 * mm, oy + dd + 1 * mm, "INSIDE")
    c.drawString(ox - wall_w - 1 * mm, oy - 4 * mm, "OUTSIDE")


# ── Section View ─────────────────────────────────────────────────────────────

def _draw_section_view(c, cx, cy, draw_w, draw_h, opening: dict, subdivision: dict):
    """Draw vertical section through the frame."""
    oh = max(float(opening.get("height_mm", 1000) or 1000), 100)
    system_type = opening.get("system_type", "")
    frame_depth = FRAME_DEPTHS.get(system_type, 80)

    # Scale
    avail_h = draw_h - 20 * mm
    scale = min(avail_h / oh, 0.12)
    depth_scale = min((draw_w - 20 * mm) / frame_depth, 0.8)
    actual_depth_scale = min(scale * 3, depth_scale)

    dh = oh * scale
    dd = frame_depth * actual_depth_scale

    ox = cx - dd / 2
    oy = cy - dh / 2

    # Outer frame (section view)
    c.setStrokeColor(FRAME_COLOR)
    c.setLineWidth(1.2)
    c.rect(ox, oy, dd, dh)

    # Glass line (vertical in section)
    c.setFillColor(GLASS_FILL)
    c.setStrokeColor(FRAME_COLOR)
    c.setLineWidth(0.5)
    glass_x = ox + dd / 2 - 0.5 * mm
    c.rect(glass_x, oy + 2 * mm, 1 * mm, dh - 4 * mm, fill=1, stroke=1)

    # Sill at bottom
    c.setFillColor(HexColor("#d0d0d0"))
    sill_h = 3 * mm
    c.rect(ox - 3 * mm, oy - sill_h, dd + 6 * mm, sill_h, fill=1, stroke=1)

    # Head at top
    c.rect(ox - 3 * mm, oy + dh, dd + 6 * mm, sill_h, fill=1, stroke=1)

    # Height dimension
    _draw_dim_vertical(c, ox + dd, oy, oy + dh, f"{oh:.0f}",
                       offset=8 * mm, right=True)

    # Depth dimension
    _draw_dim_horizontal(c, ox, ox + dd, oy, f"{frame_depth}",
                         offset=6 * mm, above=False)

    # F.F.L
    c.setFont("Helvetica", 5)
    c.setFillColor(black)
    c.drawString(ox - 10 * mm, oy - sill_h - 3 * mm, "F.F.L")
    c.setStrokeColor(black)
    c.setLineWidth(0.5)
    c.line(ox - 12 * mm, oy - sill_h, ox + dd + 8 * mm, oy - sill_h)

    # Labels
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(black)
    c.drawCentredString(cx, oy + dh + 10 * mm, "SECTION")


# ── Glass Schedule Table ─────────────────────────────────────────────────────

def _draw_glass_table(c, x, y, w, panels: list, glass_type: str):
    """Draw glass mark table for the opening."""
    c.setFont("Helvetica-Bold", 7)
    c.setFillColor(black)
    c.drawString(x, y, "GLASS SCHEDULE")

    y -= 4 * mm
    # Header
    col_widths = [15*mm, 12*mm, 22*mm, 22*mm, 15*mm, 18*mm, 30*mm]
    headers = ["Mark", "Type", "Width mm", "Height mm", "Area m²", "Weight kg", "Glass Spec"]

    c.setFillColor(BRAND_NAVY)
    c.rect(x, y - 5*mm, w, 5*mm, fill=1, stroke=0)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 5)
    col_x = x
    for i, h in enumerate(headers):
        cw = col_widths[i] if i < len(col_widths) else 20*mm
        c.drawCentredString(col_x + cw / 2, y - 3.5*mm, h)
        col_x += cw

    y -= 5 * mm
    c.setFont("Helvetica", 5)
    for i, panel in enumerate(panels):
        row_y = y - (i + 1) * 4.5 * mm
        if i % 2 == 1:
            c.setFillColor(BRAND_LIGHT)
            c.rect(x, row_y - 1*mm, w, 4.5*mm, fill=1, stroke=0)

        c.setFillColor(black)
        col_x = x
        values = [
            panel.get("panel_id", f"P{i+1}").split("-")[-1] if "-" in str(panel.get("panel_id", "")) else f"P{i+1}",
            panel.get("panel_type", "F"),
            f"{panel.get('glass_width_mm', 0):.0f}",
            f"{panel.get('glass_height_mm', 0):.0f}",
            f"{panel.get('glass_area_sqm', 0):.2f}",
            f"{panel.get('glass_weight_kg', 0):.1f}",
            glass_type,
        ]
        for j, val in enumerate(values):
            cw = col_widths[j] if j < len(col_widths) else 20*mm
            c.drawCentredString(col_x + cw / 2, row_y + 1*mm, str(val))
            col_x += cw

    # Totals row
    total_row_y = y - (len(panels) + 1) * 4.5 * mm
    c.setStrokeColor(black)
    c.setLineWidth(0.5)
    c.line(x, total_row_y + 4.5*mm, x + w, total_row_y + 4.5*mm)
    c.setFont("Helvetica-Bold", 5)
    total_area = sum(float(p.get("glass_area_sqm", 0)) for p in panels)
    total_weight = sum(float(p.get("glass_weight_kg", 0)) for p in panels)
    col_x = x
    totals = ["TOTAL", "", "", "", f"{total_area:.2f}", f"{total_weight:.1f}", ""]
    for j, val in enumerate(totals):
        cw = col_widths[j] if j < len(col_widths) else 20*mm
        c.drawCentredString(col_x + cw / 2, total_row_y + 1*mm, val)
        col_x += cw


# ── Profile Cut Length Table ─────────────────────────────────────────────────

def _draw_profile_table(c, x, y, w, subdivision: dict):
    """Draw profile cut length summary."""
    c.setFont("Helvetica-Bold", 7)
    c.setFillColor(black)
    c.drawString(x, y, "PROFILE CUT LENGTHS")

    y -= 4 * mm
    rows = [
        ("Frame Length (total)", f"{subdivision.get('total_frame_length_mm', 0):.0f} mm"),
        ("Sash Length (total)", f"{subdivision.get('total_sash_length_mm', 0):.0f} mm"),
        ("Interlock Length", f"{subdivision.get('total_interlock_length_mm', 0):.0f} mm"),
        ("Track Length", f"{subdivision.get('track_length_mm', 0):.0f} mm"),
        ("Hardware Sets", str(subdivision.get("hardware_sets", 0))),
        ("Roller Sets", str(subdivision.get("roller_sets", 0))),
    ]

    c.setFont("Helvetica", 5.5)
    for i, (label, value) in enumerate(rows):
        row_y = y - (i + 1) * 4 * mm
        if i % 2 == 0:
            c.setFillColor(BRAND_LIGHT)
            c.rect(x, row_y - 0.5*mm, w, 4*mm, fill=1, stroke=0)
        c.setFillColor(BRAND_GREY)
        c.drawString(x + 2*mm, row_y + 1*mm, label)
        c.setFillColor(black)
        c.setFont("Helvetica-Bold", 5.5)
        c.drawRightString(x + w - 2*mm, row_y + 1*mm, value)
        c.setFont("Helvetica", 5.5)


# ── Main Generator ───────────────────────────────────────────────────────────

def generate_shop_drawings(
    opening_schedule: dict,
    project_name: str = "",
    drawing_number_prefix: str = "MAS-SHD",
    company_name: str = None,
    company_sub: str = None,
) -> bytes:
    """
    Generate a multi-page shop drawing PDF from an opening schedule.

    Args:
        opening_schedule: Dict with "schedule" list and "summary" dict
            from OpeningScheduleEngine.to_dict()
        project_name: Project name for title block
        drawing_number_prefix: Drawing number prefix
        company_name: Company name override
        company_sub: Company subtitle override

    Returns:
        PDF bytes
    """
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=PAGE_SIZE)
    c.setTitle(f"Shop Drawings - {project_name}")
    c.setAuthor(company_name or DEFAULT_COMPANY)

    schedule_items = opening_schedule.get("schedule", [])
    if not schedule_items:
        logger.warning("No schedule items for shop drawings")
        # Generate a cover page even with no data
        _draw_page_border(c, PAGE_W, PAGE_H)
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(PAGE_W / 2, PAGE_H / 2, "No Opening Schedule Data Available")
        _draw_title_block(c, PAGE_W, PAGE_H, {
            "company": company_name or DEFAULT_COMPANY,
            "company_sub": company_sub or DEFAULT_SUB,
            "project": project_name,
            "drawing_no": f"{drawing_number_prefix}-000",
            "sheet": "1/1",
            "title": "SHOP DRAWING - NO DATA",
        })
        c.showPage()
        c.save()
        return buffer.getvalue()

    # Group by unique opening type (system_type + width + height)
    unique_types: dict[tuple, dict] = {}
    for item in schedule_items:
        key = (
            item.get("system_type", ""),
            round(float(item.get("width_mm", 0))),
            round(float(item.get("height_mm", 0))),
        )
        if key not in unique_types:
            unique_types[key] = {
                "opening": item,
                "total_qty": 0,
                "floors": set(),
                "elevations": set(),
                "items": [],
            }
        qty = int(item.get("count", item.get("qty", 1)) or 1)
        unique_types[key]["total_qty"] += qty
        unique_types[key]["floors"].add(item.get("floor", ""))
        unique_types[key]["elevations"].add(item.get("elevation", ""))
        unique_types[key]["items"].append(item)

    total_sheets = len(unique_types)
    sheet_num = 0

    for (system_type, w_mm, h_mm), type_data in unique_types.items():
        sheet_num += 1
        opening = type_data["opening"]
        subdivision = opening.get("subdivision", {})
        panels = subdivision.get("panels", [])

        # ── Page setup ───────────────────────────────────────────────
        _draw_page_border(c, PAGE_W, PAGE_H)

        # ── Drawing info ─────────────────────────────────────────────
        type_code = _generate_type_code(opening)
        description = SYSTEM_DESCRIPTIONS.get(system_type,
                          f"ALUMINIUM {system_type.upper()}")
        locations = ", ".join(sorted(type_data["floors"])) or "TYPICAL"
        elevations_str = ", ".join(sorted(type_data["elevations"])) or "ALL"
        glass_type = opening.get("glass_type", "")
        config = subdivision.get("configuration", "F")
        config_desc = subdivision.get("config_description", "")

        # ── Info Box (top-left) ──────────────────────────────────────
        info_box_w = 55 * mm
        info_box_h = 55 * mm
        info_box_x = 15 * mm
        info_box_y = PAGE_H - 15 * mm - info_box_h

        _draw_info_box(c, info_box_x, info_box_y, info_box_w, info_box_h, {
            "type_code": type_code,
            "description": description,
            "system_series": opening.get("system_series", ""),
            "location": f"Floors: {locations}",
            "glass_type": glass_type,
            "finish": "POWDER COATED ALUMINIUM\nCOLOR TO CLIENT APPROVAL",
            "qty": f"{type_data['total_qty']} NO.",
            "configuration": f"{config} ({config_desc})" if config_desc else config,
        })

        # ── Elevation View (center) ─────────────────────────────────
        elev_cx = PAGE_W * 0.42
        elev_cy = PAGE_H * 0.55
        elev_w = PAGE_W * 0.42
        elev_h = PAGE_H * 0.55

        _draw_elevation_view(c, elev_cx, elev_cy, elev_w, elev_h,
                             opening, subdivision)

        # ── Plan View (bottom-left) ──────────────────────────────────
        plan_cx = PAGE_W * 0.22
        plan_cy = PAGE_H * 0.15
        plan_w = PAGE_W * 0.35
        plan_h = PAGE_H * 0.18

        c.setFont("Helvetica-Bold", 8)
        c.setFillColor(black)
        _draw_plan_view(c, plan_cx, plan_cy, plan_w, plan_h,
                        opening, subdivision)

        # ── Section View (bottom-center) ─────────────────────────────
        section_cx = PAGE_W * 0.52
        section_cy = PAGE_H * 0.15
        section_w = PAGE_W * 0.15
        section_h = PAGE_H * 0.18

        _draw_section_view(c, section_cx, section_cy, section_w, section_h,
                           opening, subdivision)

        # ── Glass Schedule Table (right side) ────────────────────────
        table_x = PAGE_W * 0.66
        table_y = PAGE_H - 18 * mm
        table_w = PAGE_W * 0.30

        if panels:
            _draw_glass_table(c, table_x, table_y, table_w, panels, glass_type)

            # Profile cut lengths below glass table
            profile_y = table_y - (len(panels) + 3) * 4.5 * mm - 8 * mm
            _draw_profile_table(c, table_x, profile_y, table_w, subdivision)
        else:
            # No subdivision data — show basic info
            c.setFont("Helvetica-Bold", 7)
            c.setFillColor(black)
            c.drawString(table_x, table_y, "OPENING DATA")
            c.setFont("Helvetica", 6)
            y = table_y - 6 * mm
            for label, val in [
                ("Width:", f"{w_mm} mm"),
                ("Height:", f"{h_mm} mm"),
                ("Area:", f"{w_mm * h_mm / 1e6:.2f} m²"),
                ("Glass:", glass_type or "TBC"),
                ("Qty:", f"{type_data['total_qty']} NO."),
            ]:
                c.setFillColor(BRAND_GREY)
                c.drawString(table_x, y, label)
                c.setFillColor(black)
                c.drawString(table_x + 20*mm, y, val)
                y -= 4 * mm

        # ── Structural Opening note ──────────────────────────────────
        c.setFont("Helvetica", 5)
        c.setFillColor(BRAND_GREY)
        c.drawString(15*mm, 62*mm,
                     f"STRUCTURAL OPENING: {w_mm:.0f} × {h_mm:.0f} mm")
        c.drawString(15*mm, 58*mm,
                     f"Elevations: {elevations_str}")

        # ── Notes ────────────────────────────────────────────────────
        notes_y = 52 * mm
        c.setFont("Helvetica-Bold", 6)
        c.setFillColor(black)
        c.drawString(15*mm, notes_y, "GENERAL NOTES:")
        c.setFont("Helvetica", 5)
        c.setFillColor(BRAND_GREY)
        notes = [
            "1. All dimensions are in millimeters unless otherwise noted.",
            "2. Verify all structural openings on site before fabrication.",
            "3. Glass specification subject to thermal stress analysis.",
            "4. F = Fixed panel, S = Sliding panel.",
            f"5. Profile system: {opening.get('system_series', 'TBC')} "
            f"({description}).",
        ]
        for i, note in enumerate(notes):
            c.drawString(15*mm, notes_y - (i + 1) * 3.5*mm, note)

        # ── Title Block ──────────────────────────────────────────────
        _draw_title_block(c, PAGE_W, PAGE_H, {
            "company": company_name or DEFAULT_COMPANY,
            "company_sub": company_sub or DEFAULT_SUB,
            "project": project_name,
            "drawing_no": f"{drawing_number_prefix}-{sheet_num:03d}",
            "sheet": f"{sheet_num}/{total_sheets}",
            "revision": "00",
            "date": datetime.now().strftime("%d-%m-%Y"),
            "scale": "NTS",
            "title": f"ALUMINIUM WINDOWS & DOORS\nSCHEDULE-{sheet_num:02d}",
        })

        c.showPage()

    c.save()
    pdf_bytes = buffer.getvalue()
    buffer.close()

    logger.info(f"Generated shop drawing PDF: {total_sheets} sheets, "
                f"{len(pdf_bytes)} bytes")
    return pdf_bytes


def _generate_type_code(opening: dict) -> str:
    """Generate a type code for the opening (e.g. LSTB-01, SS-02)."""
    system_series = opening.get("system_series", "")
    item_code = opening.get("item_code", opening.get("opening_id", ""))

    # Extract prefix from item code
    if item_code:
        parts = str(item_code).split("-")
        if len(parts) >= 1:
            return parts[0] + "-" + (parts[1] if len(parts) > 1 else "01")

    # Fallback: use system series
    series_map = {
        "GT-LSTB": "LSTB",
        "GT-SS": "SS",
        "GT-E500TB": "E5TB",
    }
    prefix = series_map.get(system_series, "WIN")
    w = round(float(opening.get("width_mm", 0)))
    return f"{prefix}-{w}"


# ── Convenience: generate from estimate data ─────────────────────────────────

def generate_shop_drawings_from_estimate(estimate_data: dict) -> bytes:
    """
    Generate shop drawings from a full estimate data dict.
    Expects estimate_data to have "opening_schedule" key with schedule/summary.
    """
    opening_schedule = estimate_data.get("opening_schedule", {})
    project_name = estimate_data.get("project_name", "")

    # Get tenant info for branding
    tenant = estimate_data.get("tenant", {})
    company_name = tenant.get("company_name")
    drawing_prefix = f"MAS-SHD-{project_name[:10].upper().replace(' ', '')}" if project_name else "MAS-SHD"

    return generate_shop_drawings(
        opening_schedule=opening_schedule,
        project_name=project_name,
        drawing_number_prefix=drawing_prefix,
        company_name=company_name,
    )

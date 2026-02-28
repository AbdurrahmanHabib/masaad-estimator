"""
Shop Drawing Engine — generates professional facade shop drawings as PDF.

Matches UAE industry standard (GINCO/ALUMIL) architectural drawing style:
  - A3 landscape pages (420x297mm)
  - Clean B&W line drawings — NO color fills
  - Multiple openings per page (1/2/4 based on size)
  - Each opening: Elevation + Section + Plan + Info Table
  - Numbered glass mark circles inside panes
  - VP/SP/F labels inside each pane
  - Tick-mark dimension lines (not arrows)
  - "W (N EQ. DIV.)" structural opening annotations
  - Diagonal hatching for wall blockwork in section/plan
  - F.F.L as dashed line
  - Circled section/detail markers
  - Professional title block with consultant/contractor chain
"""
import io
import math
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib.units import mm
from reportlab.lib.colors import black, white, HexColor
from reportlab.pdfgen import canvas

logger = logging.getLogger("masaad-shop-drawing")

# ── Page Constants ──────────────────────────────────────────────────────────
PAGE_SIZE = landscape(A3)
PAGE_W, PAGE_H = PAGE_SIZE
MARGIN = 10 * mm
BORDER_IN = MARGIN + 1.5 * mm  # inner border offset

# ── Line weights (architectural standard) ──────────────────────────────────
LW_HEAVY = 1.2       # outer frame, structural opening
LW_MEDIUM = 0.7      # panel dividers, section profile
LW_LIGHT = 0.4       # dimension lines, extension lines
LW_THIN = 0.25       # hatching, glass lines, labels

# ── Fonts ──────────────────────────────────────────────────────────────────
FONT_TITLE = ("Helvetica-Bold", 9)
FONT_LABEL = ("Helvetica-Bold", 7)
FONT_DIM = ("Helvetica", 6)
FONT_SMALL = ("Helvetica", 5)
FONT_TINY = ("Helvetica", 4.5)
FONT_MARK = ("Helvetica-Bold", 5.5)

# ── Company defaults ───────────────────────────────────────────────────────
DEFAULT_COMPANY = "MADINAT AL SAADA ALUMINIUM & GLASS WORKS LLC"
DEFAULT_SUB = "Ajman, UAE  |  www.madinatalsaada.ae"

# ── Glazetech system info ──────────────────────────────────────────────────
SYSTEM_DESCRIPTIONS = {
    "Window - Sliding (Lift & Slide TB)": "GLAZETECH LIFT & SLIDE THERMAL BREAK WINDOW",
    "Window - Sliding (Eco 500 TB)": "GLAZETECH ECO 500 SLIDING THERMAL BREAK WINDOW",
    "Window - Sliding": "GLAZETECH SLIM SLIDING WINDOW",
    "Door - Sliding": "GLAZETECH LIFT & SLIDE THERMAL BREAK DOOR",
    "Glass Railing": "FRAMELESS GLASS RAILING SYSTEM",
    "Curtain Wall - Stick System": "ALUMINIUM FRAMED FULL GLAZED CURTAIN WALL",
    "Window - Fixed": "ALUMINIUM FRAMED FIXED WINDOW",
}

FRAME_DEPTHS = {
    "Window - Sliding (Lift & Slide TB)": 160,
    "Window - Sliding (Eco 500 TB)": 70,
    "Window - Sliding": 48,
    "Door - Sliding": 160,
    "Glass Railing": 50,
    "Curtain Wall - Stick System": 156,
    "Window - Fixed": 60,
}

def _sf(val, default=0):
    """Safe float conversion — handles None, empty string, non-numeric."""
    if val is None:
        return float(default)
    try:
        return float(val)
    except (ValueError, TypeError):
        return float(default)


SYSTEM_SERIES_MAP = {
    "GT-LSTB": "LSTB",
    "GT-SS": "SS",
    "GT-E500TB": "E5TB",
}


# ═══════════════════════════════════════════════════════════════════════════
#  DRAWING PRIMITIVES
# ═══════════════════════════════════════════════════════════════════════════

def _tick_dim_h(c, x1, x2, y, label: str, offset=8*mm, above=True):
    """Horizontal dimension with tick marks (architectural style)."""
    c.setStrokeColor(black)
    c.setLineWidth(LW_LIGHT)
    dy = offset if above else -offset
    dim_y = y + dy

    # Extension lines
    ext_overshoot = 1.5 * mm
    if above:
        c.line(x1, y, x1, dim_y + ext_overshoot)
        c.line(x2, y, x2, dim_y + ext_overshoot)
    else:
        c.line(x1, y, x1, dim_y - ext_overshoot)
        c.line(x2, y, x2, dim_y - ext_overshoot)

    # Dimension line
    c.line(x1, dim_y, x2, dim_y)

    # Tick marks (45-degree slash, 1.5mm each side)
    tick = 1.5 * mm
    c.setLineWidth(LW_MEDIUM)
    c.line(x1 - tick, dim_y - tick, x1 + tick, dim_y + tick)
    c.line(x2 - tick, dim_y - tick, x2 + tick, dim_y + tick)
    c.setLineWidth(LW_LIGHT)

    # Label centered on dimension line
    mid_x = (x1 + x2) / 2
    c.setFillColor(white)
    tw = c.stringWidth(str(label), *FONT_DIM)
    pad = 1 * mm
    c.rect(mid_x - tw / 2 - pad, dim_y - 2.5 * mm, tw + 2 * pad, 5 * mm, fill=1, stroke=0)
    c.setFillColor(black)
    c.setFont(*FONT_DIM)
    c.drawCentredString(mid_x, dim_y - 1.5 * mm, str(label))


def _tick_dim_v(c, x, y1, y2, label: str, offset=8*mm, right=True):
    """Vertical dimension with tick marks (architectural style)."""
    c.setStrokeColor(black)
    c.setLineWidth(LW_LIGHT)
    dx = offset if right else -offset
    dim_x = x + dx

    # Extension lines
    ext = 1.5 * mm
    if right:
        c.line(x, y1, dim_x + ext, y1)
        c.line(x, y2, dim_x + ext, y2)
    else:
        c.line(x, y1, dim_x - ext, y1)
        c.line(x, y2, dim_x - ext, y2)

    # Dimension line
    c.line(dim_x, y1, dim_x, y2)

    # Tick marks
    tick = 1.5 * mm
    c.setLineWidth(LW_MEDIUM)
    c.line(dim_x - tick, y1 - tick, dim_x + tick, y1 + tick)
    c.line(dim_x - tick, y2 - tick, dim_x + tick, y2 + tick)
    c.setLineWidth(LW_LIGHT)

    # Label (rotated)
    c.saveState()
    mid_y = (y1 + y2) / 2
    c.setFillColor(black)
    c.setFont(*FONT_DIM)
    c.translate(dim_x + 2 * mm, mid_y)
    c.rotate(90)
    c.drawCentredString(0, 0, str(label))
    c.restoreState()


def _glass_mark_circle(c, cx, cy, number: str, radius=3.5*mm):
    """Draw a numbered glass mark circle (e.g. 01, 02) at center point."""
    c.setStrokeColor(black)
    c.setLineWidth(LW_MEDIUM)
    c.setFillColor(white)
    c.circle(cx, cy, radius, fill=1, stroke=1)
    c.setFillColor(black)
    c.setFont(*FONT_MARK)
    c.drawCentredString(cx, cy - 1.8 * mm, str(number).zfill(2))


def _section_marker(c, cx, cy, number: str, radius=4*mm):
    """Draw a circled section/detail marker."""
    c.setStrokeColor(black)
    c.setLineWidth(LW_MEDIUM)
    c.setFillColor(white)
    c.circle(cx, cy, radius, fill=1, stroke=1)
    c.setFillColor(black)
    c.setFont(*FONT_LABEL)
    c.drawCentredString(cx, cy - 2 * mm, str(number))


def _hatching(c, x, y, w, h, spacing=2*mm, angle=45):
    """Draw diagonal line hatching inside a rectangle (wall blockwork)."""
    c.saveState()
    c.setStrokeColor(black)
    c.setLineWidth(LW_THIN)

    # Clip to rect
    p = c.beginPath()
    p.rect(x, y, w, h)
    c.clipPath(p, stroke=0)

    # Draw diagonal lines
    diag = math.sqrt(w * w + h * h) + spacing
    rad = math.radians(angle)
    cos_a, sin_a = math.cos(rad), math.sin(rad)

    num_lines = int(diag / spacing) + 2
    for i in range(-num_lines, num_lines + 1):
        offset = i * spacing
        # Line perpendicular to angle direction
        lx = x + w / 2 + offset * cos_a
        ly = y + h / 2 + offset * sin_a
        # Draw long line through this point at angle
        dx = diag * sin_a
        dy = diag * cos_a
        c.line(lx - dx, ly - dy, lx + dx, ly + dy)

    c.restoreState()


def _dashed_line(c, x1, y1, x2, y2, dash_on=3, dash_off=2):
    """Draw a dashed line."""
    c.setDash(dash_on, dash_off)
    c.line(x1, y1, x2, y2)
    c.setDash()


# ═══════════════════════════════════════════════════════════════════════════
#  PAGE FURNITURE
# ═══════════════════════════════════════════════════════════════════════════

def _draw_page_border(c):
    """Double-line page border."""
    c.setStrokeColor(black)
    c.setLineWidth(LW_HEAVY)
    c.rect(MARGIN, MARGIN, PAGE_W - 2 * MARGIN, PAGE_H - 2 * MARGIN)
    c.setLineWidth(LW_THIN)
    c.rect(BORDER_IN, BORDER_IN,
           PAGE_W - 2 * BORDER_IN, PAGE_H - 2 * BORDER_IN)


def _draw_title_block(c, info: dict):
    """Professional title block at bottom-right matching GINCO format."""
    tb_w = 170 * mm
    tb_h = 90 * mm
    tb_x = PAGE_W - MARGIN - tb_w
    tb_y = MARGIN + 1.5 * mm

    c.setStrokeColor(black)
    c.setLineWidth(LW_MEDIUM)
    c.rect(tb_x, tb_y, tb_w, tb_h)

    # ── Revision row (top of title block) ──
    rev_h = 8 * mm
    rev_y = tb_y + tb_h - rev_h
    c.setLineWidth(LW_LIGHT)
    c.line(tb_x, rev_y, tb_x + tb_w, rev_y)

    # Revision headers
    rev_cols = [25 * mm, 30 * mm, 55 * mm, 30 * mm, 30 * mm]
    rev_headers = ["No.", "Date", "Description", "Chk'd By", ""]
    cx = tb_x
    c.setFont("Helvetica", 4.5)
    c.setFillColor(black)
    for i, (w, h) in enumerate(zip(rev_cols, rev_headers)):
        c.drawCentredString(cx + w / 2, rev_y + rev_h - 3.5 * mm, h)
        if i < len(rev_cols) - 1:
            c.line(cx + w, rev_y, cx + w, rev_y + rev_h)
        cx += w

    # Revision data row
    rev_data_h = 6 * mm
    rev_data_y = rev_y - rev_data_h
    c.line(tb_x, rev_data_y, tb_x + tb_w, rev_data_y)
    rev = info.get("revision", "00")
    date = info.get("date", datetime.now().strftime("%d-%m-%Y"))
    rev_data = [rev, date, "ISSUED FOR APPROVAL", info.get("checked", ""), ""]
    cx = tb_x
    c.setFont("Helvetica", 4.5)
    for i, (w, val) in enumerate(zip(rev_cols, rev_data)):
        c.drawCentredString(cx + w / 2, rev_data_y + 1.5 * mm, str(val))
        if i < len(rev_cols) - 1:
            c.line(cx + w, rev_data_y, cx + w, rev_data_y + rev_data_h)
        cx += w

    # ── R E V I S I O N label ──
    c.setFont("Helvetica-Bold", 5)
    c.drawCentredString(tb_x + tb_w / 2, rev_y + rev_h + 0.5 * mm,
                        "R  E  V  I  S  I  O  N")

    # ── Project title section ──
    proj_h = 16 * mm
    proj_y = rev_data_y - proj_h
    c.line(tb_x, proj_y, tb_x + tb_w, proj_y)
    c.setFont("Helvetica", 4.5)
    c.drawString(tb_x + 2 * mm, rev_data_y - 4 * mm, "PROJECT TITLE:")
    c.setFont("Helvetica-Bold", 6)
    project = info.get("project", "")
    # Wrap project name
    if len(project) > 35:
        c.drawCentredString(tb_x + tb_w / 2, rev_data_y - 8 * mm, project[:35])
        c.drawCentredString(tb_x + tb_w / 2, rev_data_y - 12 * mm, project[35:70])
    else:
        c.drawCentredString(tb_x + tb_w / 2, rev_data_y - 9 * mm, project)

    # ── Location / Plot / District ──
    loc_h = 10 * mm
    loc_y = proj_y - loc_h
    c.line(tb_x, loc_y, tb_x + tb_w, loc_y)
    c.setFont("Helvetica", 4.5)
    c.drawString(tb_x + 2 * mm, proj_y - 3.5 * mm, "LOCATION:")
    c.setFont("Helvetica-Bold", 5)
    c.drawString(tb_x + 25 * mm, proj_y - 3.5 * mm,
                 info.get("location", "UAE"))

    half_w = tb_w / 2
    c.setFont("Helvetica", 4.5)
    c.drawString(tb_x + 2 * mm, proj_y - 7.5 * mm, "PLOT NO.:")
    c.setFont("Helvetica-Bold", 5)
    c.drawString(tb_x + 20 * mm, proj_y - 7.5 * mm,
                 info.get("plot_no", ""))
    c.setFont("Helvetica", 4.5)
    c.drawString(tb_x + half_w + 2 * mm, proj_y - 7.5 * mm, "DISTRICT:")
    c.setFont("Helvetica-Bold", 5)
    c.drawString(tb_x + half_w + 22 * mm, proj_y - 7.5 * mm,
                 info.get("district", ""))

    # ── Consultant / Contractor boxes ──
    box_h = 10 * mm
    # Design & Built Contractor
    cont_y = loc_y - box_h
    c.line(tb_x, cont_y, tb_x + tb_w, cont_y)
    c.setFont("Helvetica", 4)
    c.drawString(tb_x + 2 * mm, loc_y - 3.5 * mm, "DESIGN & BUILT CONTRACTOR:")
    c.setFont("Helvetica-Bold", 6)
    c.drawString(tb_x + 2 * mm, loc_y - 7.5 * mm,
                 info.get("company", DEFAULT_COMPANY))

    # Sub contractor
    sub_y = cont_y - box_h
    c.line(tb_x, sub_y, tb_x + tb_w, sub_y)
    c.setFont("Helvetica", 4)
    c.drawString(tb_x + 2 * mm, cont_y - 3.5 * mm, "SUB CONTRACTOR:")
    c.setFont("Helvetica-Bold", 5.5)
    c.drawString(tb_x + 2 * mm, cont_y - 7.5 * mm,
                 info.get("sub_contractor", info.get("company", DEFAULT_COMPANY)))

    # ── Drawing title section ──
    title_h = 14 * mm
    title_y = sub_y - title_h
    c.line(tb_x, title_y, tb_x + tb_w, title_y)
    c.setFont("Helvetica", 4)
    c.drawString(tb_x + 2 * mm, sub_y - 3 * mm, "DRAWING TITLE:")
    c.setFont("Helvetica-Bold", 6.5)
    c.drawCentredString(tb_x + tb_w / 2, sub_y - 7 * mm, "SHOP DRAWING")
    c.setFont("Helvetica-Bold", 5.5)
    c.drawCentredString(tb_x + tb_w / 2, sub_y - 11 * mm,
                        info.get("title", "ALUMINIUM WINDOWS & DOORS"))

    # ── Bottom info grid (Size/Drawn/Checked/Date + Scale/Project No/Sheet) ──
    grid_h = 6 * mm
    grid_y = title_y - grid_h
    c.line(tb_x, grid_y, tb_x + tb_w, grid_y)

    col4_w = tb_w / 4
    for i in range(1, 4):
        c.line(tb_x + i * col4_w, title_y, tb_x + i * col4_w, grid_y)

    labels_row1 = [
        ("Size", "A-3"),
        ("Drawn", info.get("drawn", "S.A")),
        ("Checked", info.get("checked", "")),
        ("Date", date),
    ]
    c.setFont("Helvetica", 4)
    for i, (lbl, val) in enumerate(labels_row1):
        x = tb_x + i * col4_w + 2 * mm
        c.setFillColor(black)
        c.drawString(x, title_y - 2.5 * mm, lbl)
        c.setFont("Helvetica-Bold", 5)
        c.drawString(x, title_y - 5 * mm, str(val))
        c.setFont("Helvetica", 4)

    # Second row
    grid_y2 = grid_y - grid_h
    c.line(tb_x, grid_y2, tb_x + tb_w, grid_y2)
    for i in range(1, 4):
        c.line(tb_x + i * col4_w, grid_y, tb_x + i * col4_w, grid_y2)

    labels_row2 = [
        ("Scale", "AS SHOWN"),
        ("Project No.", info.get("project_no", "")),
        ("Sheet", info.get("sheet", "")),
        ("Revision", info.get("revision", "00")),
    ]
    for i, (lbl, val) in enumerate(labels_row2):
        x = tb_x + i * col4_w + 2 * mm
        c.setFont("Helvetica", 4)
        c.drawString(x, grid_y - 2.5 * mm, lbl)
        c.setFont("Helvetica-Bold", 5)
        c.drawString(x, grid_y - 5 * mm, str(val))

    # Drawing number
    dn_y = grid_y2 - grid_h
    c.line(tb_x, dn_y, tb_x + tb_w, dn_y)
    c.setFont("Helvetica", 4)
    c.drawString(tb_x + 2 * mm, grid_y2 - 2.5 * mm, "Drawing No.")
    c.setFont("Helvetica-Bold", 6)
    c.drawString(tb_x + 30 * mm, grid_y2 - 4 * mm,
                 info.get("drawing_no", ""))


def _draw_general_notes(c, x, y, w):
    """General notes box (top-right)."""
    c.setStrokeColor(black)
    c.setLineWidth(LW_LIGHT)
    notes_h = 18 * mm
    c.rect(x, y - notes_h, w, notes_h)
    c.setFont("Helvetica-Bold", 6)
    c.setFillColor(black)
    c.drawString(x + 2 * mm, y - 4 * mm, "GENERAL NOTES")
    c.setFont("Helvetica", 4.5)
    notes = [
        "1.UNLESS OTHERWISE SPECIFIED ALL DIMENSIONS ARE IN MILLIMETERS.",
        "2.FOUNDATION DEPTH FROM THE AVERAGE NATURAL",
        "  GROUND LEVEL TO BE AS PER ELEVATION LEVELS TABLE.",
        "3.VERIFY ALL STRUCTURAL OPENINGS ON SITE.",
    ]
    for i, note in enumerate(notes):
        c.drawString(x + 2 * mm, y - 7 * mm - i * 3 * mm, note)


def _draw_info_table(c, x, y, w, info: dict):
    """
    Draw GINCO-style info table (SYSTEM/TYPE/DESCRIPTION/LOCATION/GLASS/FINISH/QTY).
    y = top of table.
    """
    rows = [
        ("SYSTEM:", info.get("system_series", "GLAZETECH")),
        ("TYPE:", info.get("type_code", "")),
        ("DESCRIPTION:", info.get("description", "")),
        ("LOCATION:", info.get("location", "")),
        ("GLASS TYPE:", info.get("glass_type", "TBC")),
        ("FINISH:", info.get("finish", "POWDER COATED ALUMINIUM\nCOLOR TO CLIENT APPROVAL")),
        ("TOTAL QTY:", info.get("qty", "1 NO.")),
    ]

    row_h = 4.5 * mm
    label_w = 28 * mm
    total_h = len(rows) * row_h

    c.setStrokeColor(black)
    c.setLineWidth(LW_LIGHT)
    c.rect(x, y - total_h, w, total_h)

    for i, (label, value) in enumerate(rows):
        ry = y - (i + 1) * row_h
        if i > 0:
            c.line(x, ry + row_h, x + w, ry + row_h)
        # Vertical separator
        c.line(x + label_w, ry, x + label_w, ry + row_h)

        c.setFont("Helvetica", 4.5)
        c.setFillColor(black)
        c.drawString(x + 1.5 * mm, ry + 1.2 * mm, label)
        c.setFont("Helvetica-Bold", 5)
        val_str = str(value).split("\n")[0]  # first line only
        c.drawString(x + label_w + 1.5 * mm, ry + 1.2 * mm, val_str)


# ═══════════════════════════════════════════════════════════════════════════
#  ELEVATION VIEW
# ═══════════════════════════════════════════════════════════════════════════

def _draw_elevation(c, cx, cy, avail_w, avail_h, opening: dict, subdiv: dict,
                    glass_mark_start: int = 1) -> Tuple[float, float, float, float, float, int]:
    """
    Draw front elevation view of an opening.
    Returns (scale, ox, oy, dw, dh, next_glass_mark).
    """
    panels = subdiv.get("panels", [])
    config = subdiv.get("configuration", "F")
    ow = max(_sf(opening.get("width_mm"), 1000), 100)
    oh = max(_sf(opening.get("height_mm"), 1000), 100)

    # Scale to fit with margin for dimensions
    dim_margin = 14 * mm
    fit_w = avail_w - 2 * dim_margin
    fit_h = avail_h - 2 * dim_margin
    scale = min(fit_w / ow, fit_h / oh, 0.12)

    dw = ow * scale
    dh = oh * scale
    ox = cx - dw / 2
    oy = cy - dh / 2

    # ── Outer frame (heavy line) ──
    c.setStrokeColor(black)
    c.setLineWidth(LW_HEAVY)
    c.rect(ox, oy, dw, dh)

    # ── Frame deduction lines (10mm offset shown as thin inner rectangle) ──
    frame_deduct = 10  # mm
    fd = frame_deduct * scale
    if fd > 1:
        c.setLineWidth(LW_THIN)
        c.rect(ox + fd, oy + fd, dw - 2 * fd, dh - 2 * fd)

    # ── Draw panels ──
    mark_num = glass_mark_start
    panel_x = ox + fd  # start inside frame deduction
    total_panel_w = dw - 2 * fd

    if panels:
        # Calculate total panel width from data
        total_pw_mm = sum(_sf(p.get("panel_width_mm"), ow / len(panels)) for p in panels)
        pw_scale = total_panel_w / max(total_pw_mm * scale, 1) if total_pw_mm > 0 else 1

        for pi, panel in enumerate(panels):
            pw_mm = _sf(panel.get("panel_width_mm"), ow / len(panels))
            pw = pw_mm * scale * pw_scale if total_pw_mm > 0 else total_panel_w / len(panels)
            ph = dh - 2 * fd
            p_type = panel.get("panel_type", "F")

            # Glass pane inside panel
            gw_mm = _sf(panel.get("glass_width_mm"), pw_mm - 20)
            gh_mm = _sf(panel.get("glass_height_mm"), _sf(opening.get("height_mm"), 1000) - 20)
            if gw_mm > 0 and gh_mm > 0:
                gw = gw_mm * scale * pw_scale if total_pw_mm > 0 else pw - 4 * mm
                gh = gh_mm * scale
                gx = panel_x + (pw - gw) / 2
                gy = oy + fd + (ph - gh) / 2

                # Glass outline (thin line, no fill)
                c.setStrokeColor(black)
                c.setLineWidth(LW_THIN)
                c.rect(gx, gy, gw, gh)

                # Glass mark circle at center of pane
                mark_cx = gx + gw / 2
                mark_cy = gy + gh / 2
                _glass_mark_circle(c, mark_cx, mark_cy,
                                   str(mark_num).zfill(2))
                mark_num += 1

                # VP/SP/F label below glass mark
                label_map = {"F": "F", "S": "VP"}
                vp_label = label_map.get(p_type, "VP")
                # If glass_height > 2000mm it might be spandrel+vision split
                c.setFont(*FONT_TINY)
                c.setFillColor(black)
                c.drawCentredString(mark_cx, mark_cy - 5.5 * mm, vp_label)

            # Mullion line between panels (medium weight)
            if pi < len(panels) - 1:
                c.setStrokeColor(black)
                c.setLineWidth(LW_MEDIUM)
                mx = panel_x + pw
                c.line(mx, oy + fd, mx, oy + dh - fd)

            panel_x += pw
    else:
        # Single pane — no panels
        gx = ox + fd + 2 * mm
        gy = oy + fd + 2 * mm
        gw = dw - 2 * fd - 4 * mm
        gh = dh - 2 * fd - 4 * mm
        c.setStrokeColor(black)
        c.setLineWidth(LW_THIN)
        c.rect(gx, gy, gw, gh)
        _glass_mark_circle(c, gx + gw / 2, gy + gh / 2, "01")
        c.setFont(*FONT_TINY)
        c.drawCentredString(gx + gw / 2, gy + gh / 2 - 5.5 * mm, "VP")
        mark_num = 2

    # ── F.F.L dashed line ──
    c.setStrokeColor(black)
    c.setLineWidth(LW_LIGHT)
    ffl_extend = 12 * mm
    _dashed_line(c, ox - ffl_extend, oy, ox + dw + 5 * mm, oy)
    c.setFont(*FONT_SMALL)
    c.setFillColor(black)
    c.drawString(ox - ffl_extend - 1 * mm, oy + 1 * mm, "F.F.L")

    # ── Overall width dimension (above) ──
    _tick_dim_h(c, ox, ox + dw, oy + dh, f"{ow:.0f}", offset=10 * mm, above=True)

    # ── Structural opening annotation ──
    num_panels = len(panels) if panels else 1
    if num_panels > 1:
        struct_label = f"{ow:.0f} ({num_panels} EQ. DIV.)"
    else:
        struct_label = f"{ow:.0f}"
    c.setFont(*FONT_DIM)
    c.setFillColor(black)
    c.drawCentredString(cx, oy + dh + 16 * mm, struct_label)

    # ── Overall height dimension (right) ──
    _tick_dim_v(c, ox + dw, oy, oy + dh, f"{oh:.0f}", offset=10 * mm, right=True)

    # ── Panel width dimensions (below elevation) ──
    if panels and len(panels) > 1:
        px = ox + fd
        total_pw_mm = sum(_sf(p.get("panel_width_mm"), ow / len(panels)) for p in panels)
        pw_scale_dim = total_panel_w / max(total_pw_mm * scale, 1) if total_pw_mm > 0 else 1
        for panel in panels:
            pw_mm = _sf(panel.get("panel_width_mm"), ow / len(panels))
            pw = pw_mm * scale * pw_scale_dim if total_pw_mm > 0 else total_panel_w / len(panels)
            _tick_dim_h(c, px, px + pw, oy, f"{pw_mm:.0f}",
                        offset=6 * mm, above=False)
            px += pw

    # ── View label ──
    c.setFont(*FONT_TITLE)
    c.setFillColor(black)
    c.drawCentredString(cx, oy - 14 * mm, "ELEVATION")

    return scale, ox, oy, dw, dh, mark_num


# ═══════════════════════════════════════════════════════════════════════════
#  SECTION VIEW
# ═══════════════════════════════════════════════════════════════════════════

def _draw_section(c, cx, cy, avail_w, avail_h, opening: dict, subdiv: dict):
    """
    Draw vertical cross-section through the frame.
    Shows wall blockwork hatching, glass DGU line, frame profile outline.
    """
    oh = max(_sf(opening.get("height_mm"), 1000), 100)
    system_type = opening.get("system_type") or ""
    frame_depth = FRAME_DEPTHS.get(system_type, 80)

    # Scale
    dim_margin = 10 * mm
    fit_h = avail_h - 2 * dim_margin
    scale_h = fit_h / oh
    scale = min(scale_h, 0.10)

    # Exaggerated depth for section clarity
    depth_draw = max(frame_depth * scale * 2.5, 12 * mm)
    depth_draw = min(depth_draw, avail_w - 2 * dim_margin)
    height_draw = oh * scale

    sx = cx - depth_draw / 2
    sy = cy - height_draw / 2

    # ── Wall blockwork (hatched rectangles at top and bottom) ──
    wall_thickness = min(depth_draw * 0.6, 15 * mm)
    wall_ext = 4 * mm  # how far wall extends beyond frame

    # Head wall (top)
    head_h = 6 * mm
    c.setStrokeColor(black)
    c.setLineWidth(LW_MEDIUM)
    c.rect(sx - wall_ext, sy + height_draw, depth_draw + 2 * wall_ext, head_h)
    _hatching(c, sx - wall_ext, sy + height_draw,
              depth_draw + 2 * wall_ext, head_h, spacing=1.8 * mm)

    # Sill wall (bottom)
    sill_h = 6 * mm
    c.rect(sx - wall_ext, sy - sill_h, depth_draw + 2 * wall_ext, sill_h)
    _hatching(c, sx - wall_ext, sy - sill_h,
              depth_draw + 2 * wall_ext, sill_h, spacing=1.8 * mm)

    # Label: AAC BLOCK
    c.setFont(*FONT_TINY)
    c.setFillColor(black)
    c.drawCentredString(sx + depth_draw / 2, sy + height_draw + head_h + 2 * mm,
                        "AAC BLOCK")

    # ── Frame profile (outer rectangle) ──
    c.setLineWidth(LW_HEAVY)
    c.rect(sx, sy, depth_draw, height_draw)

    # ── Glass line (DGU — two thin parallel lines in center) ──
    glass_x = sx + depth_draw * 0.45
    glass_gap = max(1.5 * mm, depth_draw * 0.06)  # DGU gap
    c.setLineWidth(LW_THIN)
    c.line(glass_x, sy + 3 * mm, glass_x, sy + height_draw - 3 * mm)
    c.line(glass_x + glass_gap, sy + 3 * mm,
           glass_x + glass_gap, sy + height_draw - 3 * mm)

    # ── DGU label ──
    dgu_label_x = glass_x + glass_gap + 2 * mm
    dgu_label_y = sy + height_draw / 2
    c.setFont(*FONT_TINY)
    c.saveState()
    c.translate(dgu_label_x, dgu_label_y)
    c.rotate(90)
    glass_type = opening.get("glass_type", "DGU")
    c.drawCentredString(0, 0, str(glass_type)[:20] if glass_type else "DGU")
    c.restoreState()

    # ── INSIDE / OUTSIDE labels ──
    c.setFont(*FONT_SMALL)
    c.setFillColor(black)
    c.drawCentredString(sx + depth_draw * 0.2, sy - sill_h - 4 * mm, "OUTSIDE")
    c.drawCentredString(sx + depth_draw * 0.8, sy - sill_h - 4 * mm, "INSIDE")

    # ── Height dimension ──
    _tick_dim_v(c, sx + depth_draw, sy, sy + height_draw, f"{oh:.0f}",
                offset=8 * mm, right=True)

    # ── Depth dimension ──
    _tick_dim_h(c, sx, sx + depth_draw, sy, f"{frame_depth}",
                offset=5 * mm, above=False)

    # ── Section label ──
    c.setFont(*FONT_TITLE)
    c.drawCentredString(cx, sy - sill_h - 8 * mm, "SECTION")


# ═══════════════════════════════════════════════════════════════════════════
#  PLAN VIEW
# ═══════════════════════════════════════════════════════════════════════════

def _draw_plan(c, cx, cy, avail_w, avail_h, opening: dict, subdiv: dict):
    """
    Draw horizontal plan section through the opening.
    Shows frame depth, mullion positions, glass lines, wall returns.
    """
    ow = max(_sf(opening.get("width_mm"), 1000), 100)
    system_type = opening.get("system_type") or ""
    frame_depth = FRAME_DEPTHS.get(system_type, 80)
    panels = subdiv.get("panels", [])
    frame_deduct = 10  # mm

    # Scale
    dim_margin = 10 * mm
    fit_w = avail_w - 2 * dim_margin
    scale = min(fit_w / ow, 0.10)
    depth_scale = min((avail_h - dim_margin) / frame_depth, 0.6)
    actual_depth_scale = min(scale * 2.5, depth_scale)

    dw = ow * scale
    dd = max(frame_depth * actual_depth_scale, 8 * mm)

    px = cx - dw / 2
    py = cy - dd / 2

    # ── Wall returns (hatched blocks at each end) ──
    wall_w = 4 * mm
    wall_ext = 3 * mm
    c.setStrokeColor(black)
    c.setLineWidth(LW_MEDIUM)

    # Left wall
    c.rect(px - wall_w, py - wall_ext, wall_w, dd + 2 * wall_ext)
    _hatching(c, px - wall_w, py - wall_ext, wall_w, dd + 2 * wall_ext,
              spacing=1.5 * mm)

    # Right wall
    c.rect(px + dw, py - wall_ext, wall_w, dd + 2 * wall_ext)
    _hatching(c, px + dw, py - wall_ext, wall_w, dd + 2 * wall_ext,
              spacing=1.5 * mm)

    # ── Frame outline (heavy) ──
    c.setLineWidth(LW_HEAVY)
    c.rect(px, py, dw, dd)

    # ── Frame deduction lines (10mm from each end) ──
    fd = frame_deduct * scale
    if fd > 0.5:
        c.setLineWidth(LW_THIN)
        # Left 10mm
        c.line(px + fd, py, px + fd, py + dd)
        # Right 10mm
        c.line(px + dw - fd, py, px + dw - fd, py + dd)

    # ── Draw panel glass lines and mullions in plan ──
    if panels:
        panel_x = px + fd
        total_panel_w = dw - 2 * fd
        total_pw_mm = sum(_sf(p.get("panel_width_mm"), ow / len(panels)) for p in panels)
        pw_scale = total_panel_w / max(total_pw_mm * scale, 1) if total_pw_mm > 0 else 1

        for pi, panel in enumerate(panels):
            pw_mm = _sf(panel.get("panel_width_mm"), ow / len(panels))
            pw = pw_mm * scale * pw_scale if total_pw_mm > 0 else total_panel_w / len(panels)

            # Glass line (thin horizontal line at center of depth)
            c.setLineWidth(LW_THIN)
            glass_y = py + dd * 0.5
            c.line(panel_x + 1 * mm, glass_y, panel_x + pw - 1 * mm, glass_y)

            # Second glass line for DGU
            dgu_gap = max(1 * mm, dd * 0.05)
            c.line(panel_x + 1 * mm, glass_y + dgu_gap,
                   panel_x + pw - 1 * mm, glass_y + dgu_gap)

            # Mullion between panels
            if pi < len(panels) - 1:
                c.setLineWidth(LW_MEDIUM)
                mx = panel_x + pw
                c.line(mx, py, mx, py + dd)

            panel_x += pw
    else:
        # Single glass line
        c.setLineWidth(LW_THIN)
        glass_y = py + dd * 0.5
        c.line(px + fd + 1 * mm, glass_y, px + dw - fd - 1 * mm, glass_y)

    # ── Structural opening annotation (above plan) ──
    c.setFont(*FONT_DIM)
    c.setFillColor(black)
    c.drawCentredString(cx, py + dd + 6 * mm, f"{ow:.0f}")
    c.drawCentredString(cx, py + dd + 2.5 * mm, "STRUCTURAL OPENING")

    # ── Section markers (circled numbers at each end) ──
    _section_marker(c, px - wall_w - 5 * mm, py + dd / 2, "A")
    _section_marker(c, px + dw + wall_w + 5 * mm, py + dd / 2, "B")

    # ── Width with 10mm deductions ──
    inner_w_mm = ow - 2 * frame_deduct
    # Show 10 | inner_w | 10 dimension chain
    if fd > 2:
        c.setFont(*FONT_TINY)
        c.setFillColor(black)
        c.drawCentredString(px + fd / 2, py - 3.5 * mm, f"{frame_deduct}")
        c.drawCentredString(px + dw / 2, py - 3.5 * mm, f"{inner_w_mm:.0f}")
        c.drawCentredString(px + dw - fd / 2, py - 3.5 * mm, f"{frame_deduct}")

        # Small tick marks for the chain
        c.setLineWidth(LW_LIGHT)
        chain_y = py - 2 * mm
        c.line(px, py, px, chain_y)
        c.line(px + fd, py, px + fd, chain_y)
        c.line(px + dw - fd, py, px + dw - fd, chain_y)
        c.line(px + dw, py, px + dw, chain_y)
        c.line(px, chain_y, px + dw, chain_y)

    # ── View label ──
    c.setFont(*FONT_TITLE)
    c.setFillColor(black)
    c.drawCentredString(cx, py - 8 * mm, "PLAN")


# ═══════════════════════════════════════════════════════════════════════════
#  OPENING GROUP (Elevation + Section + Plan + Info)
# ═══════════════════════════════════════════════════════════════════════════

def _draw_opening_group(c, cell_x, cell_y, cell_w, cell_h,
                        opening: dict, subdiv: dict, type_data: dict,
                        glass_mark_start: int = 1):
    """
    Draw a complete opening group within a cell:
      Top 60%: ELEVATION (left ~65%) + SECTION (right ~35%)
      Mid 20%: PLAN (full width)
      Bot 20%: INFO TABLE (full width)
    """
    # Layout proportions
    elev_h_ratio = 0.55
    plan_h_ratio = 0.22
    info_h_ratio = 0.23

    elev_area_h = cell_h * elev_h_ratio
    plan_area_h = cell_h * plan_h_ratio
    info_area_h = cell_h * info_h_ratio

    elev_split = 0.65  # elevation gets 65% width, section gets 35%

    # ── ELEVATION ──
    elev_cx = cell_x + (cell_w * elev_split) / 2
    elev_cy = cell_y + cell_h - elev_area_h / 2
    elev_w = cell_w * elev_split
    _draw_elevation(c, elev_cx, elev_cy, elev_w, elev_area_h,
                    opening, subdiv, glass_mark_start)

    # ── SECTION ──
    sec_cx = cell_x + cell_w * elev_split + (cell_w * (1 - elev_split)) / 2
    sec_cy = cell_y + cell_h - elev_area_h / 2
    sec_w = cell_w * (1 - elev_split)
    _draw_section(c, sec_cx, sec_cy, sec_w, elev_area_h,
                  opening, subdiv)

    # ── PLAN ──
    plan_cx = cell_x + cell_w / 2
    plan_cy = cell_y + info_area_h + plan_area_h / 2
    _draw_plan(c, plan_cx, plan_cy, cell_w, plan_area_h,
               opening, subdiv)

    # ── INFO TABLE ──
    info_w = min(cell_w - 4 * mm, 120 * mm)
    info_x = cell_x + 2 * mm
    info_y = cell_y + info_area_h  # top of info table
    type_code = _generate_type_code(opening)
    system_type = opening.get("system_type", "")
    description = SYSTEM_DESCRIPTIONS.get(system_type,
                      f"ALUMINIUM {system_type.upper()}" if system_type else "ALUMINIUM WINDOW")
    locations = ", ".join(sorted(s for s in type_data.get("floors", set()) if s)) or "TYPICAL"
    glass_type = opening.get("glass_type", "TBC")
    config = subdiv.get("configuration", "F")

    _draw_info_table(c, info_x, info_y, info_w, {
        "system_series": opening.get("system_series", "GLAZETECH"),
        "type_code": type_code,
        "description": description,
        "location": locations,
        "glass_type": glass_type,
        "finish": "POWDER COATED ALUMINIUM\nCOLOR TO CLIENT APPROVAL",
        "qty": f"{type_data.get('total_qty', 1)} NO.",
    })


# ═══════════════════════════════════════════════════════════════════════════
#  PAGE LAYOUT — 1, 2, or 4 openings per page
# ═══════════════════════════════════════════════════════════════════════════

def _group_openings_for_pages(unique_types: dict) -> List[List[tuple]]:
    """
    Group opening types into pages: 1 per page for large, 2 or 4 for smaller.
    Returns list of pages, each page is a list of (key, type_data) tuples.
    """
    pages = []
    # Sort by width descending
    sorted_types = sorted(unique_types.items(),
                          key=lambda kv: kv[0][1], reverse=True)

    buffer = []
    for key, data in sorted_types:
        w_mm = key[1]
        h_mm = key[2]

        if w_mm >= 5000 or h_mm >= 4000:
            # Large opening — 1 per page
            if buffer:
                pages.append(buffer)
                buffer = []
            pages.append([(key, data)])
        elif w_mm >= 3000:
            # Medium opening — 2 per page
            buffer.append((key, data))
            if len(buffer) >= 2:
                pages.append(buffer)
                buffer = []
        else:
            # Small opening — 4 per page
            buffer.append((key, data))
            if len(buffer) >= 4:
                pages.append(buffer)
                buffer = []

    if buffer:
        pages.append(buffer)

    return pages


def _cell_positions(count: int) -> List[Tuple[float, float, float, float]]:
    """
    Return (x, y, w, h) for each cell based on how many openings on the page.
    Drawing area = inside border, excluding title block area on right.
    """
    # Drawing area bounds
    tb_w = 175 * mm  # title block width
    draw_x = BORDER_IN + 2 * mm
    draw_y = BORDER_IN + 2 * mm
    draw_w = PAGE_W - 2 * BORDER_IN - tb_w - 4 * mm
    draw_h = PAGE_H - 2 * BORDER_IN - 4 * mm

    if count == 1:
        return [(draw_x, draw_y, draw_w, draw_h)]
    elif count == 2:
        half_h = draw_h / 2 - 1 * mm
        return [
            (draw_x, draw_y + draw_h / 2 + 1 * mm, draw_w, half_h),  # top
            (draw_x, draw_y, draw_w, half_h),  # bottom
        ]
    else:  # 3 or 4
        half_w = draw_w / 2 - 1 * mm
        half_h = draw_h / 2 - 1 * mm
        cells = [
            (draw_x, draw_y + draw_h / 2 + 1 * mm, half_w, half_h),  # top-left
            (draw_x + draw_w / 2 + 1 * mm, draw_y + draw_h / 2 + 1 * mm, half_w, half_h),  # top-right
            (draw_x, draw_y, half_w, half_h),  # bottom-left
            (draw_x + draw_w / 2 + 1 * mm, draw_y, half_w, half_h),  # bottom-right
        ]
        return cells[:count]


# ═══════════════════════════════════════════════════════════════════════════
#  TYPE CODE GENERATION
# ═══════════════════════════════════════════════════════════════════════════

def _generate_type_code(opening: dict) -> str:
    """Generate a type code (e.g. LSTB-01, SS-02)."""
    item_code = opening.get("item_code", opening.get("opening_id", ""))
    if item_code:
        parts = str(item_code).split("-")
        if len(parts) >= 2:
            return parts[0] + "-" + parts[1]
        return str(item_code)

    system_series = opening.get("system_series", "")
    prefix = SYSTEM_SERIES_MAP.get(system_series, "WIN")
    w = round(_sf(opening.get("width_mm")))
    return f"{prefix}-{w}"


# ═══════════════════════════════════════════════════════════════════════════
#  MAIN GENERATOR
# ═══════════════════════════════════════════════════════════════════════════

def generate_shop_drawings(
    opening_schedule: dict,
    project_name: str = "",
    drawing_number_prefix: str = "MAS-SHD",
    company_name: str = None,
    company_sub: str = None,
) -> bytes:
    """
    Generate multi-page shop drawing PDF from an opening schedule.

    Args:
        opening_schedule: Dict with "schedule" list from OpeningScheduleEngine
        project_name: Project name for title block
        drawing_number_prefix: Drawing number prefix
        company_name: Company name override
        company_sub: Company subtitle override

    Returns:
        PDF bytes
    """
    buffer = io.BytesIO()
    c_pdf = canvas.Canvas(buffer, pagesize=PAGE_SIZE)
    c_pdf.setTitle(f"Shop Drawings - {project_name}")
    c_pdf.setAuthor(company_name or DEFAULT_COMPANY)

    schedule_items = opening_schedule.get("schedule", [])
    if not schedule_items:
        logger.warning("No schedule items for shop drawings")
        _draw_page_border(c_pdf)
        c_pdf.setFont("Helvetica-Bold", 14)
        c_pdf.setFillColor(black)
        c_pdf.drawCentredString(PAGE_W / 2, PAGE_H / 2,
                                "No Opening Schedule Data Available")
        _draw_title_block(c_pdf, {
            "company": company_name or DEFAULT_COMPANY,
            "project": project_name,
            "drawing_no": f"{drawing_number_prefix}-000",
            "sheet": "1/1",
            "title": "SHOP DRAWING - NO DATA",
        })
        c_pdf.showPage()
        c_pdf.save()
        return buffer.getvalue()

    # ── Group by unique opening type (system_type + width + height) ──
    unique_types: dict = {}
    for item in schedule_items:
        key = (
            item.get("system_type") or "",
            round(_sf(item.get("width_mm"))),
            round(_sf(item.get("height_mm"))),
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

    # ── Arrange into pages ──
    pages = _group_openings_for_pages(unique_types)
    total_sheets = len(pages)

    for sheet_idx, page_openings in enumerate(pages):
        sheet_num = sheet_idx + 1

        # ── Page furniture ──
        _draw_page_border(c_pdf)

        # General notes (top-right, above title block)
        notes_x = PAGE_W - MARGIN - 170 * mm
        notes_y = PAGE_H - MARGIN - 2 * mm
        _draw_general_notes(c_pdf, notes_x, notes_y, 170 * mm)

        # Title block
        _draw_title_block(c_pdf, {
            "company": company_name or DEFAULT_COMPANY,
            "sub_contractor": company_name or DEFAULT_COMPANY,
            "project": project_name,
            "location": "UAE",
            "drawing_no": f"{drawing_number_prefix}-{sheet_num:03d}",
            "sheet": f"{sheet_num}/{total_sheets}",
            "revision": "00",
            "date": datetime.now().strftime("%d-%m-%Y"),
            "title": f"ALUMINIUM WINDOWS & DOORS\nSCHEDULE-{sheet_num:02d}",
        })

        # ── Draw openings in cells ──
        cells = _cell_positions(len(page_openings))
        for i, ((key, type_data), (cx, cy, cw, ch)) in enumerate(
                zip(page_openings, cells)):
            opening = type_data["opening"]
            subdiv = opening.get("subdivision", {})
            _draw_opening_group(c_pdf, cx, cy, cw, ch,
                                opening, subdiv, type_data)

        c_pdf.showPage()

    c_pdf.save()
    pdf_bytes = buffer.getvalue()
    buffer.close()

    logger.info(f"Generated shop drawing PDF: {total_sheets} sheets, "
                f"{len(pdf_bytes)} bytes")
    return pdf_bytes


# ── Convenience: generate from estimate data ─────────────────────────────

def generate_shop_drawings_from_estimate(estimate_data: dict) -> bytes:
    """Generate shop drawings from a full estimate data dict."""
    opening_schedule = estimate_data.get("opening_schedule", {})
    project_name = estimate_data.get("project_name", "")
    tenant = estimate_data.get("tenant", {})
    company_name = tenant.get("company_name")
    drawing_prefix = (
        f"MAS-SHD-{project_name[:10].upper().replace(' ', '')}"
        if project_name else "MAS-SHD"
    )
    return generate_shop_drawings(
        opening_schedule=opening_schedule,
        project_name=project_name,
        drawing_number_prefix=drawing_prefix,
        company_name=company_name,
    )

"""
Visual Drafting Engine — generates marked-up elevation PDFs and shop drawings.

Outputs:
  - Elevation markup PDF: shows facade elevation with each opening tagged by Mark ID
  - Shop drawing PDF: 1:1 cross-section details for each detected system type
  - ACP layout PDF: flat-sheet routing/folding dimensions for ACP panels

All output PDFs saved to DOWNLOAD_DIR.
"""
import os
import math
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

logger = logging.getLogger("masaad-drafting")

DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "/tmp/downloads")
DEFAULT_COMPANY_NAME = "MADINAT AL SAADA ALUMINIUM & GLASS WORKS LLC"

# Colors
NAVY = (0, 0.13, 0.28)      # #002147
GOLD = (0.83, 0.63, 0.09)   # #d4a017
LIGHT_BLUE = (0.75, 0.85, 0.95)
WHITE = (1, 1, 1)
DARK_GRAY = (0.2, 0.2, 0.2)
LIGHT_GRAY = (0.9, 0.9, 0.9)

# System type colors for elevation markup
SYSTEM_COLORS = {
    "Curtain Wall": (0.2, 0.4, 0.8),
    "Curtain Wall (Stick)": (0.2, 0.4, 0.8),
    "Window - Casement": (0.1, 0.7, 0.3),
    "Window - Fixed": (0.1, 0.6, 0.4),
    "Window - Sliding": (0.1, 0.5, 0.5),
    "Door - Single Swing": (0.8, 0.3, 0.1),
    "Door - Double Swing": (0.8, 0.3, 0.1),
    "ACP Cladding": (0.6, 0.6, 0.6),
    "Glass Balustrade": (0.5, 0.2, 0.7),
    "Spider Glazing": (0.3, 0.3, 0.8),
    "Structural Glazing": (0.2, 0.3, 0.9),
    "Shopfront": (0.4, 0.5, 0.2),
}


class VisualDraftingEngine:
    """Generates marked-up PDF drawings from opening schedule data."""

    def __init__(self, tenant_settings: Dict[str, Any] = None):
        """Initialize with optional tenant branding."""
        ts = tenant_settings or {}
        self.company_name = ts.get("company_name", DEFAULT_COMPANY_NAME)
        self.theme_color_hex = ts.get("theme_color_hex", "#002147")
        self.logo_url = ts.get("logo_url")
        # Parse theme color to RGB tuple
        try:
            hex_color = self.theme_color_hex.lstrip("#")
            self.theme_rgb = (
                int(hex_color[0:2], 16) / 255,
                int(hex_color[2:4], 16) / 255,
                int(hex_color[4:6], 16) / 255,
            )
        except Exception:
            self.theme_rgb = NAVY

    def _generate_placeholder_pdf(self, path: str, title: str, project_name: str) -> str:
        """Generate a valid PDF stating 'Awaiting CAD Data for Generation'."""
        try:
            from reportlab.pdfgen import canvas as rl_canvas
            from reportlab.lib.pagesizes import A3, landscape
            from reportlab.lib.units import cm

            page_w, page_h = landscape(A3)
            c = rl_canvas.Canvas(path, pagesize=landscape(A3))
            try:
                self._draw_title_block(c, page_w, page_h, title, project_name)

                center_x = page_w / 2
                center_y = page_h / 2 + 1 * cm

                # Warning icon (triangle)
                c.setStrokeColorRGB(*GOLD)
                c.setFillColorRGB(1.0, 0.95, 0.8)
                c.setLineWidth(2)
                tri_size = 2 * cm
                c.beginPath()
                c.moveTo(center_x, center_y + tri_size)
                c.lineTo(center_x - tri_size, center_y - tri_size * 0.5)
                c.lineTo(center_x + tri_size, center_y - tri_size * 0.5)
                c.closePath()
                c.drawPath(fill=1, stroke=1)

                c.setFillColorRGB(*GOLD)
                c.setFont("Helvetica-Bold", 18)
                c.drawCentredString(center_x, center_y - 0.1 * cm, "!")

                # Main message
                c.setFillColorRGB(*DARK_GRAY)
                c.setFont("Helvetica-Bold", 16)
                c.drawCentredString(center_x, center_y - 2 * cm,
                                    "AWAITING CAD DATA FOR GENERATION")

                c.setFont("Helvetica", 11)
                c.setFillColorRGB(0.4, 0.4, 0.4)
                c.drawCentredString(center_x, center_y - 3 * cm,
                                    "Please upload .DWG elevation/plan files to generate this drawing.")
                c.drawCentredString(center_x, center_y - 3.6 * cm,
                                    "This placeholder will be replaced automatically when geometry is available.")
            finally:
                c.save()
            logger.info(f"Placeholder PDF generated: {path}")
            return path
        except Exception as e:
            logger.error(f"Placeholder PDF generation failed: {e}")
            return None

    def generate_all(self, estimate_id: str, openings: List[Dict],
                     scope: Dict = None, project_name: str = "") -> Dict[str, Any]:
        """Generate all visual deliverables. Returns dict with output_paths."""
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)
        paths = []

        # If no openings at all, generate placeholder PDFs instead of empty/corrupted files
        if not openings:
            placeholder_path = os.path.join(DOWNLOAD_DIR, f"Elevations_{estimate_id[:8]}.pdf")
            p = self._generate_placeholder_pdf(
                placeholder_path, "Facade Elevation — Awaiting Data", project_name
            )
            if p:
                paths.append({"type": "elevation", "path": p, "name": "Elevation Markup (Awaiting Data)"})
            return {
                "estimate_id": estimate_id,
                "drawings": paths,
                "generated_at": datetime.utcnow().isoformat(),
                "drawing_count": len(paths),
            }

        # 1. Elevation markup
        elev_path = self._generate_elevation_pdf(estimate_id, openings, project_name)
        if elev_path:
            paths.append({"type": "elevation", "path": elev_path, "name": "Elevation Markup"})

        # 2. Shop drawings
        shop_path = self._generate_shop_drawings_pdf(estimate_id, openings, project_name)
        if shop_path:
            paths.append({"type": "shop_drawing", "path": shop_path, "name": "Shop Drawings"})

        # 3. ACP layouts (if ACP panels detected)
        acp_openings = [o for o in openings if "ACP" in (o.get("system_type", "") or "").upper()
                        or "CLADDING" in (o.get("system_type", "") or "").upper()]
        if acp_openings:
            acp_path = self._generate_acp_layout_pdf(estimate_id, acp_openings, project_name)
            if acp_path:
                paths.append({"type": "acp_layout", "path": acp_path, "name": "ACP Panel Layouts"})

        return {
            "estimate_id": estimate_id,
            "drawings": paths,
            "generated_at": datetime.utcnow().isoformat(),
            "drawing_count": len(paths),
        }

    def _draw_title_block(self, c, page_w, page_h, title: str, project_name: str,
                          sheet_no: int = 1, total_sheets: int = 1):
        """Draw professional title block at bottom of drawing."""
        from reportlab.lib.units import cm, mm

        tb_height = 2.5 * cm
        # Title block background
        c.setFillColorRGB(*NAVY)
        c.rect(0, 0, page_w, tb_height, fill=1, stroke=0)

        # Gold accent line
        c.setStrokeColorRGB(*GOLD)
        c.setLineWidth(2)
        c.line(0, tb_height, page_w, tb_height)
        c.setLineWidth(0.5)

        # Company name
        c.setFillColorRGB(*WHITE)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(1 * cm, tb_height - 0.8 * cm, self.company_name)

        # Drawing title
        c.setFont("Helvetica-Bold", 9)
        c.setFillColorRGB(*GOLD)
        c.drawString(1 * cm, tb_height - 1.5 * cm, title.upper())

        # Project name
        c.setFont("Helvetica", 8)
        c.setFillColorRGB(*WHITE)
        c.drawString(1 * cm, tb_height - 2.1 * cm, f"Project: {project_name}")

        # Sheet info (right side)
        c.setFont("Helvetica", 8)
        c.drawRightString(page_w - 1 * cm, tb_height - 0.8 * cm,
                          f"Date: {datetime.now().strftime('%d %b %Y')}")
        c.drawRightString(page_w - 1 * cm, tb_height - 1.5 * cm,
                          f"Sheet {sheet_no} of {total_sheets}")
        c.drawRightString(page_w - 1 * cm, tb_height - 2.1 * cm, "SCALE: NTS")

    def _generate_elevation_pdf(self, estimate_id: str, openings: List[Dict],
                                 project_name: str) -> Optional[str]:
        """Generate elevation markup PDF showing all openings tagged with Mark IDs."""
        c = None
        path = None
        try:
            from reportlab.pdfgen import canvas as rl_canvas
            from reportlab.lib.pagesizes import A3, landscape
            from reportlab.lib.units import cm, mm

            filename = f"Elevations_{estimate_id[:8]}.pdf"
            path = os.path.join(DOWNLOAD_DIR, filename)
            page_w, page_h = landscape(A3)
            c = rl_canvas.Canvas(path, pagesize=landscape(A3))

            # Group openings by elevation
            by_elevation = {}
            for op in openings:
                elev = op.get("elevation", "E1") or "E1"
                by_elevation.setdefault(elev, []).append(op)

            total_sheets = len(by_elevation) or 1
            sheet_no = 0

            for elev_name, elev_openings in sorted(by_elevation.items()):
                sheet_no += 1
                if sheet_no > 1:
                    c.showPage()

                self._draw_title_block(c, page_w, page_h,
                                       f"Facade Elevation - {elev_name}",
                                       project_name, sheet_no, total_sheets)

                # Drawing area (above title block)
                draw_area_bottom = 3.5 * cm
                draw_area_top = page_h - 1 * cm
                draw_area_left = 2 * cm
                draw_area_right = page_w - 2 * cm
                draw_w = draw_area_right - draw_area_left
                draw_h = draw_area_top - draw_area_bottom

                # Calculate scale to fit all openings
                # Arrange openings in a grid layout simulating an elevation
                total_w_mm = sum(float(o.get("width_mm", 1200)) for o in elev_openings)
                max_h_mm = max((float(o.get("height_mm", 2400)) for o in elev_openings), default=2400)

                if total_w_mm <= 0:
                    total_w_mm = 1200
                scale_x = (draw_w * 0.85) / total_w_mm
                scale_y = (draw_h * 0.7) / max_h_mm
                scale = min(scale_x, scale_y, 0.15)  # Cap scale

                # Draw grid and openings
                x_pos = draw_area_left + 1 * cm
                baseline_y = draw_area_bottom + 2 * cm

                # Ground line
                c.setStrokeColorRGB(*DARK_GRAY)
                c.setLineWidth(1.5)
                c.line(draw_area_left, baseline_y, draw_area_right, baseline_y)
                c.setFont("Helvetica", 6)
                c.setFillColorRGB(*DARK_GRAY)
                c.drawString(draw_area_left, baseline_y - 0.4 * cm, "GROUND LEVEL")

                for op in elev_openings:
                    w_mm = float(op.get("width_mm", 1200))
                    h_mm = float(op.get("height_mm", 2400))
                    w_pt = w_mm * scale
                    h_pt = h_mm * scale
                    opening_id = op.get("opening_id", op.get("id", op.get("item_code", "?")))
                    system_type = op.get("system_type", "Unknown")
                    qty = int(op.get("quantity", op.get("count", 1)))
                    area_sqm = round(w_mm * h_mm / 1_000_000, 2)

                    # Check if we need to wrap to next page
                    if x_pos + w_pt > draw_area_right - 1 * cm:
                        x_pos = draw_area_left + 1 * cm
                        baseline_y += h_pt + 3 * cm
                        if baseline_y + h_pt > draw_area_top - 2 * cm:
                            c.showPage()
                            sheet_no += 1
                            self._draw_title_block(c, page_w, page_h,
                                                   f"Facade Elevation - {elev_name} (cont.)",
                                                   project_name, sheet_no, total_sheets + 1)
                            baseline_y = draw_area_bottom + 2 * cm

                    # Draw opening rectangle
                    color = SYSTEM_COLORS.get(system_type, (0.5, 0.5, 0.5))
                    c.setStrokeColorRGB(*color)
                    c.setLineWidth(1.5)
                    # Light fill
                    c.setFillColorRGB(color[0] * 0.3 + 0.7, color[1] * 0.3 + 0.7, color[2] * 0.3 + 0.7)
                    c.rect(x_pos, baseline_y, w_pt, h_pt, fill=1, stroke=1)

                    # Glass cross pattern (indicates glazing)
                    c.setStrokeColorRGB(color[0] * 0.5 + 0.5, color[1] * 0.5 + 0.5, color[2] * 0.5 + 0.5)
                    c.setLineWidth(0.3)
                    c.line(x_pos, baseline_y, x_pos + w_pt, baseline_y + h_pt)
                    c.line(x_pos + w_pt, baseline_y, x_pos, baseline_y + h_pt)

                    # Mark ID tag (red bubble)
                    tag_x = x_pos + w_pt / 2
                    tag_y = baseline_y + h_pt + 0.3 * cm
                    c.setFillColorRGB(0.8, 0.1, 0.1)
                    tag_w = max(len(str(opening_id)) * 3.5 + 8, 25)
                    c.roundRect(tag_x - tag_w / 2, tag_y - 3, tag_w, 12, 3, fill=1, stroke=0)
                    c.setFillColorRGB(1, 1, 1)
                    c.setFont("Helvetica-Bold", 7)
                    c.drawCentredString(tag_x, tag_y, str(opening_id))

                    # Dimension annotations
                    c.setFillColorRGB(*DARK_GRAY)
                    c.setFont("Helvetica", 5.5)
                    # Width dimension (bottom)
                    c.drawCentredString(x_pos + w_pt / 2, baseline_y - 0.3 * cm,
                                        f"{int(w_mm)}mm")
                    # Height dimension (right)
                    c.saveState()
                    c.translate(x_pos + w_pt + 0.3 * cm, baseline_y + h_pt / 2)
                    c.rotate(90)
                    c.drawCentredString(0, 0, f"{int(h_mm)}mm")
                    c.restoreState()

                    # System type + area (inside)
                    if w_pt > 30 and h_pt > 20:
                        c.setFillColorRGB(*DARK_GRAY)
                        c.setFont("Helvetica", 5)
                        label = system_type[:20]
                        c.drawCentredString(x_pos + w_pt / 2, baseline_y + h_pt / 2 + 3, label)
                        c.setFont("Helvetica-Bold", 5.5)
                        c.drawCentredString(x_pos + w_pt / 2, baseline_y + h_pt / 2 - 5,
                                            f"{area_sqm} sqm x{qty}")

                    x_pos += w_pt + 0.8 * cm

                # Legend
                legend_y = draw_area_top - 0.5 * cm
                c.setFont("Helvetica-Bold", 7)
                c.setFillColorRGB(*NAVY)
                c.drawString(draw_area_left, legend_y, "LEGEND:")
                legend_x = draw_area_left + 3 * cm
                for sys_name, sys_color in sorted(SYSTEM_COLORS.items()):
                    if legend_x > draw_area_right - 5 * cm:
                        break
                    c.setFillColorRGB(*sys_color)
                    c.rect(legend_x, legend_y - 1, 8, 8, fill=1, stroke=0)
                    c.setFillColorRGB(*DARK_GRAY)
                    c.setFont("Helvetica", 5.5)
                    c.drawString(legend_x + 10, legend_y, sys_name)
                    legend_x += len(sys_name) * 3.5 + 20

            logger.info(f"Elevation PDF generated: {path}")
            return path
        except Exception as e:
            logger.error(f"Elevation PDF failed: {e}")
            if path:
                return self._generate_placeholder_pdf(
                    path, "Facade Elevation — Generation Error", project_name
                )
            return None
        finally:
            if c is not None:
                try:
                    c.save()
                except Exception:
                    pass

    def _generate_shop_drawings_pdf(self, estimate_id: str, openings: List[Dict],
                                      project_name: str) -> Optional[str]:
        """Generate shop drawing cross-sections for each system type."""
        c = None
        path = None
        try:
            from reportlab.pdfgen import canvas as rl_canvas
            from reportlab.lib.pagesizes import A3, landscape
            from reportlab.lib.units import cm

            filename = f"ShopDrawings_{estimate_id[:8]}.pdf"
            path = os.path.join(DOWNLOAD_DIR, filename)
            page_w, page_h = landscape(A3)
            c = rl_canvas.Canvas(path, pagesize=landscape(A3))

            # Group by system type
            by_type = {}
            for op in openings:
                st = op.get("system_type", "Unknown")
                by_type.setdefault(st, []).append(op)

            # Cross-section profiles (simplified schematic representations)
            PROFILES = {
                "Curtain Wall": {
                    "mullion_depth": 52, "mullion_width": 65,
                    "glass_spec": "28mm DGU: 6+12A+6mm Low-E",
                    "thermal_break": True, "pressure_plate": True,
                },
                "Curtain Wall (Stick)": {
                    "mullion_depth": 52, "mullion_width": 65,
                    "glass_spec": "28mm DGU: 6+12A+6mm",
                    "thermal_break": True, "pressure_plate": True,
                },
                "Structural Glazing": {
                    "mullion_depth": 65, "mullion_width": 80,
                    "glass_spec": "28mm DGU: 6+12A+6mm Structural",
                    "thermal_break": True, "pressure_plate": False,
                },
                "Window - Casement": {
                    "mullion_depth": 38, "mullion_width": 50,
                    "glass_spec": "24mm DGU: 6+12A+6mm",
                    "thermal_break": True, "pressure_plate": False,
                },
                "Window - Fixed": {
                    "mullion_depth": 35, "mullion_width": 45,
                    "glass_spec": "24mm DGU: 6+12A+6mm",
                    "thermal_break": False, "pressure_plate": False,
                },
                "Window - Sliding": {
                    "mullion_depth": 40, "mullion_width": 55,
                    "glass_spec": "24mm DGU: 6+12A+6mm",
                    "thermal_break": True, "pressure_plate": False,
                },
                "Door - Single Swing": {
                    "mullion_depth": 45, "mullion_width": 60,
                    "glass_spec": "12mm Tempered Clear",
                    "thermal_break": False, "pressure_plate": False,
                },
                "Door - Double Swing": {
                    "mullion_depth": 45, "mullion_width": 60,
                    "glass_spec": "12mm Tempered Clear",
                    "thermal_break": False, "pressure_plate": False,
                },
                "Shopfront": {
                    "mullion_depth": 55, "mullion_width": 70,
                    "glass_spec": "12mm Tempered Clear",
                    "thermal_break": False, "pressure_plate": True,
                },
                "Glass Balustrade": {
                    "mullion_depth": 0, "mullion_width": 0,
                    "glass_spec": "21.52mm Laminated: 10+1.52PVB+10mm",
                    "thermal_break": False, "pressure_plate": False,
                },
                "Spider Glazing": {
                    "mullion_depth": 0, "mullion_width": 0,
                    "glass_spec": "19mm Tempered + Spider Fittings",
                    "thermal_break": False, "pressure_plate": False,
                },
                "ACP Cladding": {
                    "mullion_depth": 40, "mullion_width": 40,
                    "glass_spec": "4mm ACP Panel (FR Grade)",
                    "thermal_break": False, "pressure_plate": False,
                },
            }

            total_sheets = len(by_type)
            sheet_no = 0

            for sys_type, sys_openings in sorted(by_type.items()):
                sheet_no += 1
                if sheet_no > 1:
                    c.showPage()

                self._draw_title_block(c, page_w, page_h,
                                       f"Shop Drawing - {sys_type} Cross Section",
                                       project_name, sheet_no, total_sheets)

                profile = PROFILES.get(sys_type, PROFILES.get("Curtain Wall (Stick)"))

                # Drawing area
                center_x = page_w / 2
                center_y = (page_h + 3.5 * cm) / 2

                # Draw cross-section at 5:1 scale
                scale = 5.0
                md = profile["mullion_depth"] * scale / 10  # Convert to points
                mw = profile["mullion_width"] * scale / 10

                if md > 0 and mw > 0:
                    # Mullion profile (simplified rectangle)
                    c.setStrokeColorRGB(*NAVY)
                    c.setFillColorRGB(0.85, 0.85, 0.85)
                    c.setLineWidth(1.5)
                    mullion_x = center_x - mw / 2
                    mullion_y = center_y - md * 2
                    c.rect(mullion_x, mullion_y, mw, md * 4, fill=1, stroke=1)

                    # Thermal break (polyamide strip)
                    if profile.get("thermal_break"):
                        tb_h = md * 0.3
                        c.setFillColorRGB(0.2, 0.2, 0.2)
                        c.rect(mullion_x + 2, mullion_y + md * 2 - tb_h / 2, mw - 4, tb_h, fill=1, stroke=0)
                        # Label
                        c.setFont("Helvetica", 6)
                        c.setFillColorRGB(0.8, 0.1, 0.1)
                        c.drawString(mullion_x + mw + 10, mullion_y + md * 2, "THERMAL BREAK")

                    # Pressure plate
                    if profile.get("pressure_plate"):
                        pp_x = mullion_x - mw * 0.4
                        c.setFillColorRGB(0.7, 0.7, 0.7)
                        c.rect(pp_x, mullion_y + md, mw * 0.35, md * 2, fill=1, stroke=1)
                        c.setFont("Helvetica", 5)
                        c.setFillColorRGB(*DARK_GRAY)
                        c.drawString(pp_x - 5, mullion_y + md * 2 + md + 5, "PRESSURE PLATE")

                    # Glass panes (on both sides)
                    glass_offset = mw / 2 + 3
                    glass_thickness = 4 * scale / 10
                    glass_height = md * 3.5

                    for side in [-1, 1]:
                        gx = center_x + side * glass_offset - (glass_thickness / 2 if side > 0 else -glass_thickness / 2)
                        c.setFillColorRGB(0.7, 0.85, 0.95)
                        c.setStrokeColorRGB(0.3, 0.5, 0.7)
                        c.rect(gx, mullion_y + md * 0.3, glass_thickness, glass_height, fill=1, stroke=1)

                    # Dimension lines
                    c.setStrokeColorRGB(*DARK_GRAY)
                    c.setLineWidth(0.5)
                    # Mullion depth dimension
                    dim_x = mullion_x + mw + 30
                    c.line(dim_x, mullion_y, dim_x, mullion_y + md * 4)
                    c.line(dim_x - 3, mullion_y, dim_x + 3, mullion_y)
                    c.line(dim_x - 3, mullion_y + md * 4, dim_x + 3, mullion_y + md * 4)
                    c.setFont("Helvetica", 7)
                    c.setFillColorRGB(*DARK_GRAY)
                    c.drawString(dim_x + 5, mullion_y + md * 2, f"{profile['mullion_depth']}mm")

                # Glass specification box
                spec_y = center_y + md * 3 + 20
                c.setFont("Helvetica-Bold", 9)
                c.setFillColorRGB(*NAVY)
                c.drawCentredString(center_x, spec_y + 20, f"GLASS: {profile['glass_spec']}")

                # System details table
                table_x = 3 * cm
                table_y = page_h - 2 * cm
                c.setFont("Helvetica-Bold", 8)
                c.setFillColorRGB(*NAVY)
                c.drawString(table_x, table_y, "SYSTEM DETAILS")
                c.setFont("Helvetica", 7)
                c.setFillColorRGB(*DARK_GRAY)
                details = [
                    f"System Type: {sys_type}",
                    f"Mullion Depth: {profile['mullion_depth']}mm",
                    f"Mullion Width: {profile['mullion_width']}mm",
                    f"Glass: {profile['glass_spec']}",
                    f"Thermal Break: {'Yes' if profile.get('thermal_break') else 'No'}",
                    f"Quantity in Project: {sum(int(o.get('quantity', o.get('count', 1))) for o in sys_openings)}",
                    f"Total Area: {sum(float(o.get('width_mm', 0)) * float(o.get('height_mm', 0)) / 1e6 for o in sys_openings):.1f} sqm",
                ]
                for i, line in enumerate(details):
                    c.drawString(table_x, table_y - (i + 1) * 12, line)

                # Opening schedule for this system type
                sched_x = page_w / 2 + 2 * cm
                c.setFont("Helvetica-Bold", 8)
                c.setFillColorRGB(*NAVY)
                c.drawString(sched_x, table_y, "OPENINGS OF THIS TYPE")

                c.setFont("Helvetica-Bold", 6)
                headers = ["Mark ID", "W (mm)", "H (mm)", "Qty", "Area (sqm)"]
                for j, h in enumerate(headers):
                    c.drawString(sched_x + j * 55, table_y - 15, h)

                c.setFont("Helvetica", 6)
                c.setFillColorRGB(*DARK_GRAY)
                for i, op in enumerate(sys_openings[:15]):
                    row_y = table_y - 27 - i * 11
                    if row_y < 4 * cm:
                        break
                    oid = op.get("opening_id", op.get("id", f"OP-{i+1}"))
                    w = int(float(op.get("width_mm", 0)))
                    h = int(float(op.get("height_mm", 0)))
                    qty = int(op.get("quantity", op.get("count", 1)))
                    area = round(w * h / 1e6 * qty, 2)
                    vals = [str(oid)[:12], str(w), str(h), str(qty), str(area)]
                    for j, v in enumerate(vals):
                        c.drawString(sched_x + j * 55, row_y, v)

            logger.info(f"Shop drawings PDF generated: {path}")
            return path
        except Exception as e:
            logger.error(f"Shop drawings PDF failed: {e}")
            if path:
                return self._generate_placeholder_pdf(
                    path, "Shop Drawings — Generation Error", project_name
                )
            return None
        finally:
            if c is not None:
                try:
                    c.save()
                except Exception:
                    pass

    def _generate_acp_layout_pdf(self, estimate_id: str, acp_openings: List[Dict],
                                   project_name: str) -> Optional[str]:
        """Generate ACP panel flat-sheet layouts with routing/folding dimensions."""
        c = None
        path = None
        try:
            from reportlab.pdfgen import canvas as rl_canvas
            from reportlab.lib.pagesizes import A3, landscape
            from reportlab.lib.units import cm

            filename = f"ACP_Layouts_{estimate_id[:8]}.pdf"
            path = os.path.join(DOWNLOAD_DIR, filename)
            page_w, page_h = landscape(A3)
            c = rl_canvas.Canvas(path, pagesize=landscape(A3))

            self._draw_title_block(c, page_w, page_h,
                                   "ACP Panel Flat-Sheet Layouts",
                                   project_name, 1, 1)

            draw_y = page_h - 2 * cm

            # ACP standard parameters
            FOLD_ALLOWANCE_MM = 50  # 50mm return on each side
            ROUTING_DEPTH_MM = 3   # 3mm V-groove routing depth

            c.setFont("Helvetica-Bold", 10)
            c.setFillColorRGB(*NAVY)
            c.drawString(2 * cm, draw_y, "ACP PANEL ROUTING & FOLDING SCHEDULE")
            draw_y -= 0.8 * cm

            # Table header
            c.setFont("Helvetica-Bold", 7)
            headers = ["Panel ID", "Flat W (mm)", "Flat H (mm)", "Fold Return",
                       "Route Lines", "Finished W", "Finished H", "Qty"]
            col_widths = [60, 55, 55, 50, 50, 55, 55, 30]
            col_x = [2 * cm]
            for w in col_widths[:-1]:
                col_x.append(col_x[-1] + w)

            # Header row
            c.setFillColorRGB(*NAVY)
            c.rect(2 * cm, draw_y - 3, sum(col_widths), 14, fill=1, stroke=0)
            c.setFillColorRGB(*WHITE)
            for i, h in enumerate(headers):
                c.drawString(col_x[i] + 2, draw_y, h)
            draw_y -= 18

            c.setFont("Helvetica", 7)
            c.setFillColorRGB(*DARK_GRAY)
            for op in acp_openings:
                w_mm = float(op.get("width_mm", 1200))
                h_mm = float(op.get("height_mm", 600))
                qty = int(op.get("quantity", op.get("count", 1)))
                oid = op.get("opening_id", op.get("id", "ACP-?"))

                flat_w = w_mm + 2 * FOLD_ALLOWANCE_MM
                flat_h = h_mm + 2 * FOLD_ALLOWANCE_MM
                route_lines = 4  # top, bottom, left, right folds

                vals = [str(oid)[:10], str(int(flat_w)), str(int(flat_h)),
                        f"{FOLD_ALLOWANCE_MM}mm", str(route_lines),
                        str(int(w_mm)), str(int(h_mm)), str(qty)]
                for i, v in enumerate(vals):
                    c.drawString(col_x[i] + 2, draw_y, v)
                draw_y -= 12

                if draw_y < 4 * cm:
                    break

            # Draw a sample ACP panel layout
            sample_y = 3.5 * cm + 3 * cm
            sample_x = page_w / 2 + 3 * cm
            panel_w = 8 * cm
            panel_h = 4 * cm

            c.setFont("Helvetica-Bold", 8)
            c.setFillColorRGB(*NAVY)
            c.drawString(sample_x, sample_y + panel_h + 1.5 * cm, "TYPICAL ACP PANEL - FLAT SHEET VIEW")

            # Flat sheet outline
            c.setStrokeColorRGB(*DARK_GRAY)
            c.setLineWidth(1)
            c.setFillColorRGB(0.92, 0.92, 0.92)
            c.rect(sample_x, sample_y, panel_w, panel_h, fill=1, stroke=1)

            # Routing lines (dashed)
            c.setDash(3, 2)
            c.setStrokeColorRGB(0.8, 0.1, 0.1)
            fold = 0.8 * cm  # scaled fold allowance
            # Top fold
            c.line(sample_x, sample_y + panel_h - fold, sample_x + panel_w, sample_y + panel_h - fold)
            # Bottom fold
            c.line(sample_x, sample_y + fold, sample_x + panel_w, sample_y + fold)
            # Left fold
            c.line(sample_x + fold, sample_y, sample_x + fold, sample_y + panel_h)
            # Right fold
            c.line(sample_x + panel_w - fold, sample_y, sample_x + panel_w - fold, sample_y + panel_h)
            c.setDash()

            # Labels
            c.setFont("Helvetica", 5)
            c.setFillColorRGB(0.8, 0.1, 0.1)
            c.drawString(sample_x + 2, sample_y + panel_h - fold + 3, "ROUTE LINE (V-groove 3mm)")
            c.drawString(sample_x + fold + 5, sample_y + fold + 5, "FINISHED FACE")

            logger.info(f"ACP layout PDF generated: {path}")
            return path
        except Exception as e:
            logger.error(f"ACP layout PDF failed: {e}")
            if path:
                return self._generate_placeholder_pdf(
                    path, "ACP Panel Layouts — Generation Error", project_name
                )
            return None
        finally:
            if c is not None:
                try:
                    c.save()
                except Exception:
                    pass

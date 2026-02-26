"""
Report Engine — generates branded PDF and Excel deliverables.

Outputs:
  - Commercial Quote PDF (A4, branded Madinat Al Saada header)
  - BOQ Excel workbook (multi-sheet: Summary / BOM / Cutting List / Compliance)
  - Variation Order PDF (when variation_order_delta is present)

All outputs saved to DOWNLOAD_DIR and path returned for FileResponse.
"""
import os
import math
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional

logger = logging.getLogger("masaad-report")

DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "/tmp/downloads")
COMPANY_NAME = "MADINAT AL SAADA ALUMINIUM & GLASS WORKS LLC"
COMPANY_SUB  = "Ajman, United Arab Emirates  |  Tel: +971-6-XXX-XXXX  |  www.madinatalsaada.ae"
VALIDITY_DAYS = 7


def _ensure_dir():
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)


# ── PDF helpers ───────────────────────────────────────────────────────────────

def _draw_header(c, page_w, page_h):
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    # Dark header bar
    c.setFillColorRGB(0.08, 0.08, 0.12)
    c.rect(0, page_h - 3*cm, page_w, 3*cm, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(1.5*cm, page_h - 1.5*cm, COMPANY_NAME)
    c.setFont("Helvetica", 8)
    c.drawString(1.5*cm, page_h - 2.1*cm, COMPANY_SUB)
    # Gold accent line
    c.setStrokeColorRGB(0.85, 0.65, 0.10)
    c.setLineWidth(2)
    c.line(0, page_h - 3*cm, page_w, page_h - 3*cm)
    c.setLineWidth(1)
    c.setStrokeColorRGB(0, 0, 0)


def _draw_footer(c, page_w, page_num: int):
    from reportlab.lib.units import cm
    c.setFillColorRGB(0.5, 0.5, 0.5)
    c.setFont("Helvetica", 7)
    c.drawString(1.5*cm, 0.8*cm, f"CONFIDENTIAL — {COMPANY_NAME}")
    c.drawRightString(page_w - 1.5*cm, 0.8*cm, f"Page {page_num}")
    c.setStrokeColorRGB(0.7, 0.7, 0.7)
    c.line(1.5*cm, 1.2*cm, page_w - 1.5*cm, 1.2*cm)


class ReportEngine:

    async def generate(
        self,
        estimate_id: str,
        report_type: str,
        tenant_id: str,
        state: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Main entry point called by Celery generate_report task and ReportNode.

        report_type: "full_package" | "quote_only" | "boq_excel" | "variation_order"

        Returns dict with output_paths list and summary.
        """
        _ensure_dir()
        output_paths = []

        if state is None:
            state = await self._load_state(estimate_id)

        if report_type in ("full_package", "quote_only"):
            pdf_path = self._generate_quote_pdf(estimate_id, state)
            if pdf_path:
                output_paths.append(pdf_path)

        if report_type in ("full_package", "boq_excel"):
            xlsx_path = self._generate_boq_excel(estimate_id, state)
            if xlsx_path:
                output_paths.append(xlsx_path)

        if report_type in ("full_package", "variation_order"):
            delta = state.get("variation_order_delta")
            if delta:
                vo_path = self._generate_vo_pdf(estimate_id, state, delta)
                if vo_path:
                    output_paths.append(vo_path)

        return {
            "status": "generated",
            "estimate_id": estimate_id,
            "report_type": report_type,
            "output_paths": output_paths,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    async def _load_state(self, estimate_id: str) -> Dict:
        """Load estimate state from DB as fallback when state not passed directly."""
        try:
            from app.db import AsyncSessionLocal
            from app.models.orm_models import Estimate
            from sqlalchemy import select
            async with AsyncSessionLocal() as session:
                result = await session.execute(select(Estimate).where(Estimate.id == estimate_id))
                est = result.scalar_one_or_none()
                if est and est.state_snapshot:
                    return est.state_snapshot
        except Exception as e:
            logger.warning(f"State load failed for {estimate_id}: {e}")
        return {}

    # ── Commercial Quote PDF ──────────────────────────────────────────────────

    def _generate_quote_pdf(self, estimate_id: str, state: Dict) -> Optional[str]:
        try:
            from reportlab.pdfgen import canvas as rl_canvas
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.units import cm

            filename = f"Quote_{estimate_id[:8]}.pdf"
            path = os.path.join(DOWNLOAD_DIR, filename)
            page_w, page_h = A4
            c = rl_canvas.Canvas(path, pagesize=A4)

            pricing = state.get("pricing_data", {})
            bom_items = state.get("bom_items", [])
            project_name = state.get("project_name", f"Project {estimate_id[:8]}")
            validity = (datetime.now() + timedelta(days=VALIDITY_DAYS)).strftime("%d %b %Y")

            # Page 1 — Cover
            _draw_header(c, page_w, page_h)
            _draw_footer(c, page_w, 1)

            y = page_h - 4.5*cm
            c.setFillColorRGB(0.08, 0.08, 0.12)
            c.setFont("Helvetica-Bold", 18)
            c.drawString(1.5*cm, y, "COMMERCIAL PROPOSAL")
            y -= 0.8*cm
            c.setFont("Helvetica-Bold", 13)
            c.setFillColorRGB(0.85, 0.65, 0.10)
            c.drawString(1.5*cm, y, project_name.upper())
            y -= 0.6*cm
            c.setFont("Helvetica", 9)
            c.setFillColorRGB(0.4, 0.4, 0.4)
            c.drawString(1.5*cm, y, f"Estimate Ref: {estimate_id[:8].upper()}  |  Date: {datetime.now().strftime('%d %b %Y')}")

            # LME Protection Clause
            y -= 1.5*cm
            c.setStrokeColorRGB(0.85, 0.65, 0.10)
            c.setLineWidth(1.5)
            c.rect(1.5*cm, y - 0.8*cm, page_w - 3*cm, 1.5*cm, fill=0)
            c.setLineWidth(1)
            c.setFillColorRGB(0.6, 0.1, 0.1)
            c.setFont("Helvetica-Bold", 9)
            c.drawString(2*cm, y, "PRICE VALIDITY & LME LOCK NOTICE")
            c.setFillColorRGB(0.2, 0.2, 0.2)
            c.setFont("Helvetica", 8)
            lme = state.get("lme_aed_per_kg", 7.0)
            c.drawString(2*cm, y - 0.5*cm,
                f"Valid until {validity} (7 days). LME Aluminum locked at {lme:.2f} AED/kg. "
                "Subject to revision if LME moves ±5%.")

            # Financial Summary
            y -= 2.5*cm
            total = pricing.get("total_aed", 0)
            material = pricing.get("material_cost_aed", 0)
            labor_cost = pricing.get("labor_cost_aed", 0)
            margin = pricing.get("gross_margin_pct", 0)

            c.setFont("Helvetica-Bold", 11)
            c.setFillColorRGB(0.08, 0.08, 0.12)
            c.drawString(1.5*cm, y, "FINANCIAL SUMMARY")
            y -= 0.4*cm
            c.setStrokeColorRGB(0.85, 0.65, 0.10)
            c.line(1.5*cm, y, page_w - 1.5*cm, y)
            y -= 0.5*cm

            rows = [
                ("Material Cost (Aluminum + Glass + Hardware)", f"AED {material:,.0f}"),
                ("Labor & Fabrication Cost", f"AED {labor_cost:,.0f}"),
                ("Gross Margin", f"{margin:.1f}%"),
                ("TOTAL CONTRACT VALUE (excl. VAT)", f"AED {total:,.0f}"),
            ]
            c.setFont("Helvetica", 10)
            for label, value in rows:
                c.setFillColorRGB(0.2, 0.2, 0.2)
                c.drawString(1.5*cm, y, label)
                c.setFillColorRGB(0.08, 0.08, 0.12)
                c.setFont("Helvetica-Bold", 10)
                c.drawRightString(page_w - 1.5*cm, y, value)
                c.setFont("Helvetica", 10)
                y -= 0.55*cm

            # VAT line
            vat = total * 0.05
            y -= 0.2*cm
            c.setFont("Helvetica-Bold", 10)
            c.setFillColorRGB(0.0, 0.4, 0.0)
            c.drawString(1.5*cm, y, "VAT (5%)")
            c.drawRightString(page_w - 1.5*cm, y, f"AED {vat:,.0f}")
            y -= 0.55*cm
            c.setFillColorRGB(0.85, 0.65, 0.10)
            c.drawString(1.5*cm, y, "TOTAL INCLUDING VAT")
            c.drawRightString(page_w - 1.5*cm, y, f"AED {total + vat:,.0f}")

            # BOQ Summary Table
            if bom_items:
                y -= 1.5*cm
                c.setFont("Helvetica-Bold", 11)
                c.setFillColorRGB(0.08, 0.08, 0.12)
                c.drawString(1.5*cm, y, "BILL OF QUANTITIES — SUMMARY")
                y -= 0.4*cm
                c.line(1.5*cm, y, page_w - 1.5*cm, y)
                y -= 0.5*cm

                # Group by category
                by_cat: Dict[str, float] = {}
                for item in bom_items:
                    if not item.get("is_attic_stock"):
                        cat = item.get("category", "OTHER")
                        by_cat[cat] = by_cat.get(cat, 0) + item.get("subtotal_aed", 0)

                c.setFont("Helvetica", 9)
                for cat, subtotal in sorted(by_cat.items()):
                    if y < 3*cm:
                        c.showPage()
                        _draw_header(c, page_w, page_h)
                        _draw_footer(c, page_w, c.getPageNumber())
                        y = page_h - 4.5*cm
                    c.setFillColorRGB(0.2, 0.2, 0.2)
                    c.drawString(2*cm, y, cat.title())
                    c.setFillColorRGB(0.08, 0.08, 0.12)
                    c.drawRightString(page_w - 1.5*cm, y, f"AED {subtotal:,.0f}")
                    y -= 0.45*cm

            # VE Suggestions
            ve = state.get("ve_suggestions", [])
            if ve:
                y -= 1.0*cm
                if y < 4*cm:
                    c.showPage()
                    _draw_header(c, page_w, page_h)
                    _draw_footer(c, page_w, c.getPageNumber())
                    y = page_h - 4.5*cm
                c.setFont("Helvetica-Bold", 11)
                c.setFillColorRGB(0.0, 0.4, 0.0)
                c.drawString(1.5*cm, y, "VALUE ENGINEERING OPPORTUNITIES")
                y -= 0.5*cm
                c.setFont("Helvetica", 9)
                total_savings = 0
                for suggestion in ve[:5]:
                    sav = suggestion.get("potential_saving_aed", 0)
                    total_savings += sav
                    desc = suggestion.get("description", "")[:80]
                    c.setFillColorRGB(0.2, 0.2, 0.2)
                    c.drawString(2*cm, y, f"• {desc}")
                    c.setFillColorRGB(0.0, 0.5, 0.0)
                    c.drawRightString(page_w - 1.5*cm, y, f"Save AED {sav:,.0f}")
                    y -= 0.45*cm
                c.setFont("Helvetica-Bold", 9)
                c.setFillColorRGB(0.0, 0.4, 0.0)
                c.drawString(2*cm, y, f"Total potential VE savings: AED {total_savings:,.0f}")

            c.save()
            logger.info(f"Quote PDF generated: {path}")
            return path

        except Exception as e:
            logger.error(f"Quote PDF generation failed: {e}")
            return None

    # ── BOQ Excel ─────────────────────────────────────────────────────────────

    def _generate_boq_excel(self, estimate_id: str, state: Dict) -> Optional[str]:
        try:
            import xlsxwriter

            filename = f"BOQ_{estimate_id[:8]}.xlsx"
            path = os.path.join(DOWNLOAD_DIR, filename)
            wb = xlsxwriter.Workbook(path)

            # Formats
            hdr = wb.add_format({"bold": True, "bg_color": "#14141E", "font_color": "#FFFFFF",
                                  "border": 1, "font_size": 10})
            money = wb.add_format({"num_format": "#,##0.00", "border": 1})
            qty_fmt = wb.add_format({"num_format": "#,##0.000", "border": 1})
            normal = wb.add_format({"border": 1, "font_size": 9})
            title_fmt = wb.add_format({"bold": True, "font_size": 14, "font_color": "#14141E"})
            gold = wb.add_format({"bold": True, "bg_color": "#D4A61A", "font_color": "#14141E",
                                   "border": 1, "font_size": 10})
            attic_fmt = wb.add_format({"italic": True, "font_color": "#888888", "border": 1, "font_size": 8})

            bom_items = state.get("bom_items", [])
            pricing = state.get("pricing_data", {})

            # ── Sheet 1: Summary ─────────────────────────────────────────────
            ws = wb.add_worksheet("Summary")
            ws.set_column("A:A", 40)
            ws.set_column("B:B", 20)
            ws.write("A1", COMPANY_NAME, title_fmt)
            ws.write("A2", f"Estimate: {estimate_id[:8].upper()}", normal)
            ws.write("A3", f"Generated: {datetime.now().strftime('%d %b %Y %H:%M')}", normal)
            ws.write_row(5, 0, ["Description", "Amount (AED)"], hdr)
            rows = [
                ("Material Cost — Aluminum", pricing.get("aluminum_cost_aed", 0)),
                ("Material Cost — Glass", pricing.get("glass_cost_aed", 0)),
                ("Material Cost — Hardware & Silicone", pricing.get("hardware_cost_aed", 0)),
                ("Labor & Fabrication", pricing.get("labor_cost_aed", 0)),
                ("Overhead (12%)", pricing.get("overhead_aed", 0)),
                ("Gross Margin", pricing.get("margin_aed", 0)),
                ("TOTAL CONTRACT VALUE (excl. VAT)", pricing.get("total_aed", 0)),
                ("VAT 5%", pricing.get("total_aed", 0) * 0.05),
                ("TOTAL INCLUDING VAT", pricing.get("total_aed", 0) * 1.05),
            ]
            for i, (label, val) in enumerate(rows):
                fmt = gold if "TOTAL" in label else money
                ws.write(6 + i, 0, label, normal)
                ws.write(6 + i, 1, val, fmt)

            # ── Sheet 2: BOM Detail ──────────────────────────────────────────
            ws2 = wb.add_worksheet("BOM Detail")
            ws2.set_column("A:A", 20)
            ws2.set_column("B:B", 35)
            ws2.set_column("C:C", 15)
            ws2.set_column("D:D", 10)
            ws2.set_column("E:E", 12)
            ws2.set_column("F:F", 12)
            ws2.set_column("G:G", 14)
            ws2.write_row(0, 0, [
                "Item Code", "Description", "Category", "Unit",
                "Quantity", "Unit Cost (AED)", "Subtotal (AED)"
            ], hdr)
            for i, item in enumerate(bom_items):
                fmt = attic_fmt if item.get("is_attic_stock") else normal
                ws2.write(i + 1, 0, item.get("item_code", ""), fmt)
                ws2.write(i + 1, 1, item.get("description", ""), fmt)
                ws2.write(i + 1, 2, item.get("category", ""), fmt)
                ws2.write(i + 1, 3, item.get("unit", ""), fmt)
                ws2.write(i + 1, 4, item.get("quantity", 0), qty_fmt)
                ws2.write(i + 1, 5, item.get("unit_cost_aed", 0), money)
                ws2.write(i + 1, 6, item.get("subtotal_aed", 0), money)

            # ── Sheet 3: Cutting List ────────────────────────────────────────
            ws3 = wb.add_worksheet("Cutting List")
            cutting_list = state.get("cutting_list", [])
            ws3.write_row(0, 0, [
                "Profile Code", "Required Length (mm)", "Quantity",
                "Stock Bar (mm)", "Remnant (mm)", "Bar Count"
            ], hdr)
            for i, cut in enumerate(cutting_list):
                ws3.write_row(i + 1, 0, [
                    cut.get("item_code", ""),
                    cut.get("length_mm", 0),
                    cut.get("quantity", 0),
                    cut.get("stock_length_mm", 6000),
                    cut.get("remnant_mm", 0),
                    cut.get("bar_count", 0),
                ], normal)

            # ── Sheet 4: VE Menu ─────────────────────────────────────────────
            ws4 = wb.add_worksheet("VE Opportunities")
            ws4.set_column("A:A", 40)
            ws4.set_column("B:B", 20)
            ws4.set_column("C:C", 15)
            ws4.write_row(0, 0, ["Description", "Category", "Potential Saving (AED)"], hdr)
            ve = state.get("ve_suggestions", [])
            total_ve = 0
            for i, v in enumerate(ve):
                sav = v.get("potential_saving_aed", 0)
                total_ve += sav
                ws4.write(i + 1, 0, v.get("description", ""), normal)
                ws4.write(i + 1, 1, v.get("category", ""), normal)
                ws4.write(i + 1, 2, sav, money)
            ws4.write(len(ve) + 2, 0, "TOTAL VE SAVINGS", gold)
            ws4.write(len(ve) + 2, 2, total_ve, gold)

            wb.close()
            logger.info(f"BOQ Excel generated: {path}")
            return path

        except Exception as e:
            logger.error(f"BOQ Excel generation failed: {e}")
            return None

    # ── Variation Order PDF ───────────────────────────────────────────────────

    def _generate_vo_pdf(self, estimate_id: str, state: Dict, delta: Dict) -> Optional[str]:
        try:
            from reportlab.pdfgen import canvas as rl_canvas
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.units import cm

            filename = f"VO_{estimate_id[:8]}_Rev{state.get('revision_number', 1)}.pdf"
            path = os.path.join(DOWNLOAD_DIR, filename)
            page_w, page_h = A4
            c = rl_canvas.Canvas(path, pagesize=A4)

            _draw_header(c, page_w, page_h)
            _draw_footer(c, page_w, 1)

            y = page_h - 4.5*cm
            c.setFont("Helvetica-Bold", 16)
            c.setFillColorRGB(0.08, 0.08, 0.12)
            c.drawString(1.5*cm, y, "VARIATION ORDER")
            y -= 0.6*cm
            c.setFont("Helvetica", 10)
            c.setFillColorRGB(0.4, 0.4, 0.4)
            rev = state.get("revision_number", 1)
            c.drawString(1.5*cm, y, f"Revision {rev}  |  Ref: {estimate_id[:8].upper()}  |  Date: {datetime.now().strftime('%d %b %Y')}")

            y -= 1.5*cm
            cost_impact = delta.get("total_cost_impact_aed", 0)
            c.setFont("Helvetica-Bold", 12)
            color = (0.7, 0.1, 0.1) if cost_impact > 0 else (0.0, 0.5, 0.0)
            c.setFillColorRGB(*color)
            direction = "INCREASE" if cost_impact >= 0 else "DECREASE"
            c.drawString(1.5*cm, y, f"NET COST {direction}: AED {abs(cost_impact):,.0f}")

            y -= 0.8*cm
            c.line(1.5*cm, y, page_w - 1.5*cm, y)
            y -= 0.5*cm

            headers = ["Item Code", "Change Type", "Old Qty", "New Qty", "Unit", "Cost Impact (AED)"]
            col_x = [1.5*cm, 5*cm, 9*cm, 11.5*cm, 14*cm, 16*cm]
            c.setFont("Helvetica-Bold", 8)
            c.setFillColorRGB(0.08, 0.08, 0.12)
            for i, h in enumerate(headers):
                c.drawString(col_x[i], y, h)
            y -= 0.4*cm

            changes = delta.get("changes", [])
            c.setFont("Helvetica", 8)
            for ch in changes:
                if y < 3*cm:
                    c.showPage()
                    _draw_header(c, page_w, page_h)
                    _draw_footer(c, page_w, c.getPageNumber())
                    y = page_h - 4.5*cm
                impact = ch.get("cost_impact_aed", 0)
                c.setFillColorRGB(0.7, 0.1, 0.1) if impact > 0 else c.setFillColorRGB(0.0, 0.5, 0.0)
                c.drawString(col_x[0], y, str(ch.get("item_code", ""))[:15])
                c.setFillColorRGB(0.2, 0.2, 0.2)
                c.drawString(col_x[1], y, str(ch.get("change_type", ""))[:12])
                c.drawString(col_x[2], y, str(round(ch.get("old_quantity", 0), 2)))
                c.drawString(col_x[3], y, str(round(ch.get("new_quantity", 0), 2)))
                c.drawString(col_x[4], y, str(ch.get("unit", "")))
                c.setFillColorRGB(0.7, 0.1, 0.1) if impact > 0 else c.setFillColorRGB(0.0, 0.5, 0.0)
                c.drawRightString(page_w - 1.5*cm, y, f"AED {impact:+,.0f}")
                y -= 0.4*cm

            c.save()
            logger.info(f"VO PDF generated: {path}")
            return path
        except Exception as e:
            logger.error(f"VO PDF generation failed: {e}")
            return None

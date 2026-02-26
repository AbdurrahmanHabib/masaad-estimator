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
DEFAULT_COMPANY_NAME = "MADINAT AL SAADA ALUMINIUM & GLASS WORKS LLC"
DEFAULT_COMPANY_SUB = "Ajman, United Arab Emirates  |  Tel: +971-6-XXX-XXXX  |  www.madinatalsaada.ae"
VALIDITY_DAYS = 7


def _ensure_dir():
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)


def _hex_to_rgb(hex_color: str) -> tuple:
    """Convert '#RRGGBB' to (r, g, b) floats 0-1."""
    h = hex_color.lstrip("#")
    if len(h) != 6:
        return (0.08, 0.08, 0.12)
    return (int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255)


# ── PDF helpers ───────────────────────────────────────────────────────────────

def _draw_header(c, page_w, page_h, company_name: str = None, company_sub: str = None, theme_rgb: tuple = None):
    from reportlab.lib.units import cm
    name = company_name or DEFAULT_COMPANY_NAME
    sub = company_sub or DEFAULT_COMPANY_SUB
    bg = theme_rgb or (0.08, 0.08, 0.12)
    # Dark header bar
    c.setFillColorRGB(*bg)
    c.rect(0, page_h - 3*cm, page_w, 3*cm, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(1.5*cm, page_h - 1.5*cm, name)
    c.setFont("Helvetica", 8)
    c.drawString(1.5*cm, page_h - 2.1*cm, sub)
    # Silver accent line
    c.setStrokeColorRGB(0.58, 0.64, 0.72)
    c.setLineWidth(2)
    c.line(0, page_h - 3*cm, page_w, page_h - 3*cm)
    c.setLineWidth(1)
    c.setStrokeColorRGB(0, 0, 0)


def _draw_footer(c, page_w, page_num: int, company_name: str = None):
    from reportlab.lib.units import cm
    name = company_name or DEFAULT_COMPANY_NAME
    c.setFillColorRGB(0.5, 0.5, 0.5)
    c.setFont("Helvetica", 7)
    c.drawString(1.5*cm, 0.8*cm, f"CONFIDENTIAL — {name}")
    c.setFillColorRGB(0.75, 0.75, 0.75)
    c.setFont("Helvetica", 5.5)
    c.drawCentredString(page_w / 2, 0.5*cm, "Powered by Masaad Systems Architect")
    c.setFillColorRGB(0.5, 0.5, 0.5)
    c.setFont("Helvetica", 7)
    c.drawRightString(page_w - 1.5*cm, 0.8*cm, f"Page {page_num}")
    c.setStrokeColorRGB(0.7, 0.7, 0.7)
    c.line(1.5*cm, 1.2*cm, page_w - 1.5*cm, 1.2*cm)


class ReportEngine:

    def __init__(self, tenant_settings: Optional[Dict[str, Any]] = None):
        ts = tenant_settings or {}
        self.company_name = ts.get("company_name", DEFAULT_COMPANY_NAME)
        self.company_sub = ts.get("report_header_text", DEFAULT_COMPANY_SUB)
        self.theme_color_hex = ts.get("theme_color_hex", "#002147")
        self.theme_rgb = _hex_to_rgb(self.theme_color_hex)
        self.base_currency = ts.get("base_currency", "AED")
        self.footer_text = ts.get("report_footer_text")
        # Company contact details for proposals
        self.company_address = ts.get("company_address", "")
        self.company_phone = ts.get("company_phone", "")
        self.company_email = ts.get("company_email", "")
        self.company_po_box = ts.get("company_po_box", "")
        self.company_cr_number = ts.get("company_cr_number", "")
        self.company_trn = ts.get("company_trn", "")

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

    def _generate_placeholder_pdf(self, path: str, title: str) -> Optional[str]:
        """Generate a valid PDF stating 'Awaiting Data' instead of a corrupted file."""
        try:
            from reportlab.pdfgen import canvas as rl_canvas
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.units import cm

            page_w, page_h = A4
            c = rl_canvas.Canvas(path, pagesize=A4)
            try:
                _draw_header(c, page_w, page_h, self.company_name, self.company_sub, self.theme_rgb)
                _draw_footer(c, page_w, 1, self.company_name)
                y = page_h / 2
                c.setFillColorRGB(0.4, 0.4, 0.4)
                c.setFont("Helvetica-Bold", 14)
                c.drawCentredString(page_w / 2, y, "AWAITING DATA FOR GENERATION")
                c.setFont("Helvetica", 10)
                c.drawCentredString(page_w / 2, y - 1 * cm, f"Document: {title}")
                c.drawCentredString(page_w / 2, y - 1.8 * cm,
                                    "This report will be regenerated when estimate data is available.")
            finally:
                c.save()
            return path
        except Exception as e:
            logger.error(f"Report placeholder PDF failed: {e}")
            return None

    def _generate_quote_pdf(self, estimate_id: str, state: Dict) -> Optional[str]:
        c = None
        path = None
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

            currency = self.base_currency

            # Page 1 — Cover
            _draw_header(c, page_w, page_h, self.company_name, self.company_sub, self.theme_rgb)
            _draw_footer(c, page_w, 1, self.company_name)

            y = page_h - 4.5*cm
            c.setFillColorRGB(0.08, 0.08, 0.12)
            c.setFont("Helvetica-Bold", 18)
            c.drawString(1.5*cm, y, "COMMERCIAL PROPOSAL")
            y -= 0.8*cm
            c.setFont("Helvetica-Bold", 13)
            c.setFillColorRGB(0.0, 0.13, 0.28)
            c.drawString(1.5*cm, y, project_name.upper())
            y -= 0.6*cm
            c.setFont("Helvetica", 9)
            c.setFillColorRGB(0.4, 0.4, 0.4)
            c.drawString(1.5*cm, y, f"Estimate Ref: {estimate_id[:8].upper()}  |  Date: {datetime.now().strftime('%d %b %Y')}")

            # LME Protection Clause
            y -= 1.5*cm
            c.setStrokeColorRGB(0.58, 0.64, 0.72)
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
            c.setStrokeColorRGB(0.58, 0.64, 0.72)
            c.line(1.5*cm, y, page_w - 1.5*cm, y)
            y -= 0.5*cm

            rows = [
                ("Material Cost (Aluminum + Glass + Hardware)", f"{currency} {material:,.0f}"),
                ("Labor & Fabrication Cost", f"{currency} {labor_cost:,.0f}"),
                ("Gross Margin", f"{margin:.1f}%"),
                ("TOTAL CONTRACT VALUE (excl. VAT)", f"{currency} {total:,.0f}"),
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
            c.drawRightString(page_w - 1.5*cm, y, f"{currency} {vat:,.0f}")
            y -= 0.55*cm
            c.setFillColorRGB(0.0, 0.13, 0.28)
            c.drawString(1.5*cm, y, "TOTAL INCLUDING VAT")
            c.drawRightString(page_w - 1.5*cm, y, f"{currency} {total + vat:,.0f}")

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
                        _draw_header(c, page_w, page_h, self.company_name, self.company_sub, self.theme_rgb)
                        _draw_footer(c, page_w, c.getPageNumber(), self.company_name)
                        y = page_h - 4.5*cm
                    c.setFillColorRGB(0.2, 0.2, 0.2)
                    c.drawString(2*cm, y, cat.title())
                    c.setFillColorRGB(0.08, 0.08, 0.12)
                    c.drawRightString(page_w - 1.5*cm, y, f"{currency} {subtotal:,.0f}")
                    y -= 0.45*cm

            # VE Suggestions
            ve = state.get("ve_suggestions", [])
            if ve:
                y -= 1.0*cm
                if y < 4*cm:
                    c.showPage()
                    _draw_header(c, page_w, page_h, self.company_name, self.company_sub, self.theme_rgb)
                    _draw_footer(c, page_w, c.getPageNumber(), self.company_name)
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
                    c.drawRightString(page_w - 1.5*cm, y, f"Save {currency} {sav:,.0f}")
                    y -= 0.45*cm
                c.setFont("Helvetica-Bold", 9)
                c.setFillColorRGB(0.0, 0.4, 0.0)
                c.drawString(2*cm, y, f"Total potential VE savings: {currency} {total_savings:,.0f}")

            # ══════════════════════════════════════════════════════════════════
            # Page — PAYMENT MILESTONES
            # ══════════════════════════════════════════════════════════════════
            c.showPage()
            _draw_header(c, page_w, page_h, self.company_name, self.company_sub, self.theme_rgb)
            _draw_footer(c, page_w, c.getPageNumber(), self.company_name)
            y = page_h - 4.5*cm

            c.setFont("Helvetica-Bold", 13)
            c.setFillColorRGB(0.08, 0.08, 0.12)
            c.drawString(1.5*cm, y, "PAYMENT MILESTONES")
            y -= 0.5*cm
            c.setStrokeColorRGB(0.58, 0.64, 0.72)
            c.line(1.5*cm, y, page_w - 1.5*cm, y)
            y -= 0.7*cm

            milestones = [
                ("1", "Advance Payment (upon LOA/PO)", "20%", total * 0.20),
                ("2", "Material Delivery to Site", "35%", total * 0.35),
                ("3", "50% Installation Completion", "20%", total * 0.20),
                ("4", "100% Installation & Snag-Free Handover", "15%", total * 0.15),
                ("5", "Retention (12-month Defects Liability)", "10%", total * 0.10),
            ]

            # Table header
            c.setFont("Helvetica-Bold", 9)
            c.setFillColorRGB(1, 1, 1)
            c.setFillColorRGB(0.08, 0.08, 0.12)
            c.rect(1.5*cm, y - 0.1*cm, page_w - 3*cm, 0.55*cm, fill=1, stroke=0)
            c.setFillColorRGB(1, 1, 1)
            c.drawString(1.8*cm, y + 0.05*cm, "#")
            c.drawString(2.5*cm, y + 0.05*cm, "Milestone Description")
            c.drawRightString(page_w - 5*cm, y + 0.05*cm, "%")
            c.drawRightString(page_w - 1.8*cm, y + 0.05*cm, f"Amount ({currency})")
            y -= 0.7*cm

            c.setFont("Helvetica", 9)
            for num, desc, pct, amt in milestones:
                c.setFillColorRGB(0.2, 0.2, 0.2)
                c.drawString(1.8*cm, y, num)
                c.drawString(2.5*cm, y, desc)
                c.setFillColorRGB(0.08, 0.08, 0.12)
                c.drawRightString(page_w - 5*cm, y, pct)
                c.setFont("Helvetica-Bold", 9)
                c.drawRightString(page_w - 1.8*cm, y, f"{amt:,.0f}")
                c.setFont("Helvetica", 9)
                y -= 0.55*cm

            # Total line
            y -= 0.2*cm
            c.setStrokeColorRGB(0.58, 0.64, 0.72)
            c.line(1.5*cm, y + 0.3*cm, page_w - 1.5*cm, y + 0.3*cm)
            c.setFont("Helvetica-Bold", 10)
            c.setFillColorRGB(0.08, 0.08, 0.12)
            c.drawString(2.5*cm, y, "TOTAL")
            c.drawRightString(page_w - 5*cm, y, "100%")
            c.drawRightString(page_w - 1.8*cm, y, f"{total:,.0f}")

            y -= 1.2*cm
            c.setFont("Helvetica", 8)
            c.setFillColorRGB(0.4, 0.4, 0.4)
            c.drawString(1.5*cm, y, "Note: Retention amount (10%) is held for 12 months from the date of provisional handover.")
            y -= 0.4*cm
            c.drawString(1.5*cm, y, "All payments are due within 30 days of invoice/milestone certification.")

            # ══════════════════════════════════════════════════════════════════
            # Page — INCLUSIONS & EXCLUSIONS
            # ══════════════════════════════════════════════════════════════════
            c.showPage()
            _draw_header(c, page_w, page_h, self.company_name, self.company_sub, self.theme_rgb)
            _draw_footer(c, page_w, c.getPageNumber(), self.company_name)
            y = page_h - 4.5*cm

            c.setFont("Helvetica-Bold", 13)
            c.setFillColorRGB(0.08, 0.08, 0.12)
            c.drawString(1.5*cm, y, "INCLUSIONS & EXCLUSIONS")
            y -= 0.5*cm
            c.setStrokeColorRGB(0.58, 0.64, 0.72)
            c.line(1.5*cm, y, page_w - 1.5*cm, y)
            y -= 0.8*cm

            # Inclusions
            c.setFont("Helvetica-Bold", 10)
            c.setFillColorRGB(0.0, 0.4, 0.0)
            c.drawString(1.5*cm, y, "INCLUSIONS")
            y -= 0.5*cm
            inclusions = [
                "Supply of all aluminum extrusions, glass panels, and sealants as per BOQ",
                "Factory fabrication, surface treatment (powder coating / anodizing)",
                "Transportation of materials to site (within UAE)",
                "Site installation labor, supervision, and project management",
                "All hardware and accessories as specified in the Bill of Quantities",
                "Standard quality testing (water spray test per floor completion)",
                "Protective film on all aluminum and glass surfaces",
                "12-month defects liability period from date of handover",
                "Shop drawings and structural calculations for approval",
                "Attic stock (2% spare materials) for glass, hardware, and accessories",
            ]
            c.setFont("Helvetica", 9)
            c.setFillColorRGB(0.2, 0.2, 0.2)
            for item in inclusions:
                c.drawString(2*cm, y, f"  {item}")
                y -= 0.42*cm

            y -= 0.5*cm
            # Exclusions
            c.setFont("Helvetica-Bold", 10)
            c.setFillColorRGB(0.6, 0.1, 0.1)
            c.drawString(1.5*cm, y, "EXCLUSIONS")
            y -= 0.5*cm
            exclusions = [
                "Civil works, blockwork, plastering, and painting by others",
                "Structural steel embedments and cast-in channels (by main contractor)",
                "Scaffolding and access equipment (by main contractor unless specified)",
                "Municipality permits, road closure permits, and NOCs",
                "Third-party structural PE stamping and certification fees",
                "Lightning protection and earthing connections",
                "Electrical conduits, wiring, and motorized operator controls",
                "Fire-rated framing and fire stopping (unless explicitly included in BOQ)",
                "Any works not explicitly listed in the Bill of Quantities",
                "VAT (5%) — shown separately on tax invoice",
            ]
            c.setFont("Helvetica", 9)
            c.setFillColorRGB(0.2, 0.2, 0.2)
            for item in exclusions:
                c.drawString(2*cm, y, f"  {item}")
                y -= 0.42*cm

            # ══════════════════════════════════════════════════════════════════
            # Page — TERMS & CONDITIONS
            # ══════════════════════════════════════════════════════════════════
            c.showPage()
            _draw_header(c, page_w, page_h, self.company_name, self.company_sub, self.theme_rgb)
            _draw_footer(c, page_w, c.getPageNumber(), self.company_name)
            y = page_h - 4.5*cm

            c.setFont("Helvetica-Bold", 13)
            c.setFillColorRGB(0.08, 0.08, 0.12)
            c.drawString(1.5*cm, y, "TERMS & CONDITIONS")
            y -= 0.5*cm
            c.setStrokeColorRGB(0.58, 0.64, 0.72)
            c.line(1.5*cm, y, page_w - 1.5*cm, y)
            y -= 0.7*cm

            terms = [
                ("1. Price Validity",
                 f"This quotation is valid for {VALIDITY_DAYS} days from the date of issue. "
                 "Prices are subject to revision if LME Aluminum moves more than ±5% from the locked rate."),
                ("2. Payment Terms",
                 "As per the Payment Milestone schedule. Invoices are payable within 30 calendar days. "
                 "Late payments attract 1.5% monthly interest."),
                ("3. Delivery Schedule",
                 "Material delivery: 8-12 weeks from receipt of approved shop drawings and advance payment. "
                 "Installation: as per mutually agreed programme."),
                ("4. Scope of Work",
                 "Limited strictly to the items described in the Bill of Quantities. "
                 "Any variation or addition shall be subject to a written Change Order."),
                ("5. Warranty",
                 "12 months defects liability from date of provisional handover. "
                 "10-year warranty on structural silicone. 5-year warranty on powder coating per Qualicoat."),
                ("6. Insurance",
                 "Contractor All Risk (CAR) insurance and third-party liability coverage maintained for the duration of the project."),
                ("7. Force Majeure",
                 "Neither party shall be liable for delays caused by events beyond reasonable control, "
                 "including but not limited to natural disasters, government actions, and supply chain disruptions."),
                ("8. Dispute Resolution",
                 "Any disputes shall be resolved amicably. Failing resolution, disputes shall be referred "
                 "to arbitration in the Emirate of Ajman, UAE, under local arbitration rules."),
                ("9. Acceptance",
                 "This proposal shall constitute a binding agreement upon issuance of a Letter of Award (LOA) "
                 "or Purchase Order (PO) referencing this quotation number."),
            ]

            c.setFont("Helvetica", 9)
            for title, body in terms:
                if y < 3.5*cm:
                    c.showPage()
                    _draw_header(c, page_w, page_h, self.company_name, self.company_sub, self.theme_rgb)
                    _draw_footer(c, page_w, c.getPageNumber(), self.company_name)
                    y = page_h - 4.5*cm
                c.setFont("Helvetica-Bold", 9)
                c.setFillColorRGB(0.08, 0.08, 0.12)
                c.drawString(1.5*cm, y, title)
                y -= 0.4*cm
                c.setFont("Helvetica", 8)
                c.setFillColorRGB(0.3, 0.3, 0.3)
                # Word-wrap body text
                words = body.split()
                line = ""
                max_w = page_w - 3.5*cm
                for word in words:
                    test = f"{line} {word}".strip()
                    if c.stringWidth(test, "Helvetica", 8) < max_w:
                        line = test
                    else:
                        c.drawString(2*cm, y, line)
                        y -= 0.35*cm
                        line = word
                if line:
                    c.drawString(2*cm, y, line)
                    y -= 0.35*cm
                y -= 0.25*cm

            # Signature block
            y -= 0.5*cm
            if y < 4*cm:
                c.showPage()
                _draw_header(c, page_w, page_h, self.company_name, self.company_sub, self.theme_rgb)
                _draw_footer(c, page_w, c.getPageNumber(), self.company_name)
                y = page_h - 4.5*cm

            c.setStrokeColorRGB(0.58, 0.64, 0.72)
            c.line(1.5*cm, y, page_w - 1.5*cm, y)
            y -= 0.8*cm
            c.setFont("Helvetica-Bold", 10)
            c.setFillColorRGB(0.08, 0.08, 0.12)
            c.drawString(1.5*cm, y, "FOR AND ON BEHALF OF:")
            y -= 0.6*cm
            c.setFont("Helvetica", 9)
            c.drawString(1.5*cm, y, self.company_name)
            y -= 1.5*cm
            c.setStrokeColorRGB(0.5, 0.5, 0.5)
            c.line(1.5*cm, y, 8*cm, y)
            c.drawString(1.5*cm, y - 0.4*cm, "Authorized Signatory")
            c.drawString(1.5*cm, y - 0.8*cm, "Date: ____________________")

            # Client acceptance block
            c.drawString(page_w / 2, y + 1.5*cm, "ACCEPTED BY (CLIENT):")
            c.line(page_w / 2, y, page_w - 1.5*cm, y)
            c.drawString(page_w / 2, y - 0.4*cm, "Authorized Signatory")
            c.drawString(page_w / 2, y - 0.8*cm, "Date: ____________________")

            logger.info(f"Quote PDF generated: {path}")
            return path

        except Exception as e:
            logger.error(f"Quote PDF generation failed: {e}")
            if path:
                return self._generate_placeholder_pdf(path, "Commercial Quote")
            return None
        finally:
            if c is not None:
                try:
                    c.save()
                except Exception:
                    pass

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
            gold = wb.add_format({"bold": True, "bg_color": "#002147", "font_color": "#FFFFFF",
                                   "border": 1, "font_size": 10})
            attic_fmt = wb.add_format({"italic": True, "font_color": "#888888", "border": 1, "font_size": 8})

            bom_items = state.get("bom_items", [])
            pricing = state.get("pricing_data", {})

            # ── Sheet 1: Summary ─────────────────────────────────────────────
            ws = wb.add_worksheet("Summary")
            ws.set_column("A:A", 40)
            ws.set_column("B:B", 20)
            currency = self.base_currency
            ws.write("A1", self.company_name, title_fmt)
            ws.write("A2", f"Estimate: {estimate_id[:8].upper()}", normal)
            ws.write("A3", f"Generated: {datetime.now().strftime('%d %b %Y %H:%M')}", normal)
            ws.write_row(5, 0, ["Description", f"Amount ({currency})"], hdr)
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
                "Quantity", f"Unit Cost ({currency})", f"Subtotal ({currency})"
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
            ws4.write_row(0, 0, ["Description", "Category", f"Potential Saving ({currency})"], hdr)
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
        c = None
        path = None
        try:
            from reportlab.pdfgen import canvas as rl_canvas
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.units import cm

            filename = f"VO_{estimate_id[:8]}_Rev{state.get('revision_number', 1)}.pdf"
            path = os.path.join(DOWNLOAD_DIR, filename)
            page_w, page_h = A4
            c = rl_canvas.Canvas(path, pagesize=A4)

            currency = self.base_currency
            _draw_header(c, page_w, page_h, self.company_name, self.company_sub, self.theme_rgb)
            _draw_footer(c, page_w, 1, self.company_name)

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
            c.drawString(1.5*cm, y, f"NET COST {direction}: {currency} {abs(cost_impact):,.0f}")

            y -= 0.8*cm
            c.line(1.5*cm, y, page_w - 1.5*cm, y)
            y -= 0.5*cm

            headers = ["Item Code", "Change Type", "Old Qty", "New Qty", "Unit", f"Cost Impact ({currency})"]
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
                    _draw_header(c, page_w, page_h, self.company_name, self.company_sub, self.theme_rgb)
                    _draw_footer(c, page_w, c.getPageNumber(), self.company_name)
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
                c.drawRightString(page_w - 1.5*cm, y, f"{currency} {impact:+,.0f}")
                y -= 0.4*cm

            logger.info(f"VO PDF generated: {path}")
            return path
        except Exception as e:
            logger.error(f"VO PDF generation failed: {e}")
            if path:
                return self._generate_placeholder_pdf(path, "Variation Order")
            return None
        finally:
            if c is not None:
                try:
                    c.save()
                except Exception:
                    pass

"""
Report Routes — PDF generation endpoints for estimate deliverables.

GET /api/reports/estimate/{estimate_id}/pdf  — generate and return full estimate PDF
"""
import os
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db import get_db
from app.api.deps import get_current_user, get_tenant_id
from app.models.orm_models import User, Estimate, Project

router = APIRouter(prefix="/api/reports", tags=["Reports"])
logger = logging.getLogger("masaad-report-routes")

DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "/tmp/downloads")
COMPANY_NAME = "MADINAT AL SAADA ALUMINIUM & GLASS WORKS LLC"
COMPANY_SUB = "Ajman, United Arab Emirates  |  Tel: +971-6-XXX-XXXX  |  www.madinatalsaada.ae"
VALIDITY_DAYS = 7

# Colors
NAVY = (15 / 255, 23 / 255, 42 / 255)       # #0f172a
GOLD = (0.85, 0.65, 0.10)
DARK_GRAY = (0.2, 0.2, 0.2)
MID_GRAY = (0.5, 0.5, 0.5)
LIGHT_GRAY = (0.7, 0.7, 0.7)
WHITE = (1, 1, 1)
GREEN = (0.0, 0.4, 0.0)
RED = (0.7, 0.1, 0.1)


def _ensure_dir():
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)


@router.get("/estimate/{estimate_id}/pdf")
async def generate_estimate_pdf(
    estimate_id: str,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Generate a full estimate PDF report and return it as a file download."""
    # Load estimate
    result = await db.execute(
        select(Estimate).where(
            Estimate.id == estimate_id,
            Estimate.tenant_id == tenant_id,
        )
    )
    estimate = result.scalar_one_or_none()
    if not estimate:
        raise HTTPException(status_code=404, detail=f"Estimate {estimate_id} not found")

    # Load project
    project_name = f"Project {estimate_id[:8]}"
    client_name = ""
    location = ""
    if estimate.project_id:
        proj_result = await db.execute(
            select(Project).where(Project.id == estimate.project_id)
        )
        project = proj_result.scalar_one_or_none()
        if project:
            project_name = project.name or project_name
            client_name = getattr(project, "client_name", "") or ""
            location = getattr(project, "location_zone", "") or ""

    state = estimate.state_snapshot or {}
    bom_output = estimate.bom_output_json or {}
    bom_items = bom_output.get("items", state.get("bom_items", []))
    pricing = bom_output.get("summary", state.get("pricing_data", {}))
    opening_schedule = estimate.opening_schedule_json or state.get("opening_schedule", {})
    scope = estimate.project_scope_json or state.get("project_scope", {})

    # Generate PDF
    _ensure_dir()
    pdf_path = _build_estimate_pdf(
        estimate_id=estimate_id,
        project_name=project_name,
        client_name=client_name,
        location=location,
        scope=scope,
        opening_schedule=opening_schedule,
        bom_items=bom_items,
        pricing=pricing,
        state=state,
    )

    if not pdf_path or not os.path.exists(pdf_path):
        raise HTTPException(status_code=500, detail="PDF generation failed")

    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=f"Estimate_{estimate_id[:8]}.pdf",
    )


def _build_estimate_pdf(
    estimate_id: str,
    project_name: str,
    client_name: str,
    location: str,
    scope: dict,
    opening_schedule: dict,
    bom_items: list,
    pricing: dict,
    state: dict,
) -> Optional[str]:
    """Build a full multi-page estimate PDF using ReportLab."""
    try:
        from reportlab.pdfgen import canvas as rl_canvas
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import cm
        from reportlab.lib import colors

        filename = f"Estimate_{estimate_id[:8]}.pdf"
        path = os.path.join(DOWNLOAD_DIR, filename)
        page_w, page_h = A4
        c = rl_canvas.Canvas(path, pagesize=A4)
        page_num = [1]  # mutable for nested functions

        def draw_header():
            """Draw navy header bar with company branding."""
            c.setFillColorRGB(*NAVY)
            c.rect(0, page_h - 3 * cm, page_w, 3 * cm, fill=1, stroke=0)
            c.setFillColorRGB(*WHITE)
            c.setFont("Helvetica-Bold", 13)
            c.drawString(1.5 * cm, page_h - 1.5 * cm, COMPANY_NAME)
            c.setFont("Helvetica", 8)
            c.drawString(1.5 * cm, page_h - 2.1 * cm, COMPANY_SUB)
            # Gold accent line
            c.setStrokeColorRGB(*GOLD)
            c.setLineWidth(2)
            c.line(0, page_h - 3 * cm, page_w, page_h - 3 * cm)
            c.setLineWidth(1)
            c.setStrokeColorRGB(0, 0, 0)

        def draw_footer():
            """Draw footer with page number and date."""
            c.setFillColorRGB(*MID_GRAY)
            c.setFont("Helvetica", 7)
            c.drawString(1.5 * cm, 0.8 * cm, f"CONFIDENTIAL - {COMPANY_NAME}")
            gen_date = datetime.now().strftime("%d %b %Y %H:%M")
            c.drawRightString(page_w - 1.5 * cm, 0.8 * cm, f"Page {page_num[0]}  |  Generated: {gen_date}")
            c.setStrokeColorRGB(*LIGHT_GRAY)
            c.line(1.5 * cm, 1.2 * cm, page_w - 1.5 * cm, 1.2 * cm)

        def new_page():
            c.showPage()
            page_num[0] += 1
            draw_header()
            draw_footer()
            return page_h - 4.5 * cm

        def check_page(y, needed=2.5):
            """Start new page if not enough room."""
            if y < needed * cm:
                return new_page()
            return y

        def section_title(y, title):
            y = check_page(y, 3.0)
            c.setFont("Helvetica-Bold", 11)
            c.setFillColorRGB(*NAVY)
            c.drawString(1.5 * cm, y, title)
            y -= 0.4 * cm
            c.setStrokeColorRGB(*GOLD)
            c.setLineWidth(1.5)
            c.line(1.5 * cm, y, page_w - 1.5 * cm, y)
            c.setLineWidth(1)
            y -= 0.5 * cm
            return y

        # ================================================================
        # PAGE 1 — COVER PAGE
        # ================================================================
        draw_header()
        draw_footer()

        y = page_h - 5.0 * cm

        # Large title
        c.setFillColorRGB(*NAVY)
        c.setFont("Helvetica-Bold", 22)
        c.drawString(1.5 * cm, y, "COMMERCIAL PROPOSAL")
        y -= 1.0 * cm

        # Project name in gold
        c.setFont("Helvetica-Bold", 16)
        c.setFillColorRGB(*GOLD)
        c.drawString(1.5 * cm, y, project_name.upper())
        y -= 0.7 * cm

        # Reference info
        c.setFont("Helvetica", 10)
        c.setFillColorRGB(*DARK_GRAY)
        ref_date = datetime.now().strftime("%d %b %Y")
        c.drawString(1.5 * cm, y, f"Estimate Ref: {estimate_id[:8].upper()}  |  Date: {ref_date}")
        y -= 0.5 * cm

        if client_name:
            c.drawString(1.5 * cm, y, f"Client: {client_name}")
            y -= 0.5 * cm
        if location:
            c.drawString(1.5 * cm, y, f"Location: {location}")
            y -= 0.5 * cm

        # LME Protection Clause box
        y -= 1.0 * cm
        validity = (datetime.now() + timedelta(days=VALIDITY_DAYS)).strftime("%d %b %Y")
        lme = state.get("lme_aed_per_kg", 7.0)

        c.setStrokeColorRGB(*GOLD)
        c.setLineWidth(1.5)
        c.rect(1.5 * cm, y - 1.0 * cm, page_w - 3 * cm, 1.8 * cm, fill=0)
        c.setLineWidth(1)

        c.setFillColorRGB(*RED)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(2.0 * cm, y + 0.3 * cm, "PRICE VALIDITY & LME LOCK NOTICE")
        c.setFillColorRGB(*DARK_GRAY)
        c.setFont("Helvetica", 8)
        c.drawString(
            2.0 * cm, y - 0.2 * cm,
            f"Valid until {validity} ({VALIDITY_DAYS} days). LME Aluminum locked at {lme:.2f} AED/kg."
        )
        c.drawString(
            2.0 * cm, y - 0.7 * cm,
            "Subject to revision if LME moves +/-5%. All prices in AED excl. VAT."
        )

        y -= 2.5 * cm

        # ================================================================
        # PROJECT DETAILS
        # ================================================================
        y = section_title(y, "PROJECT DETAILS")

        details = [
            ("Project Name", project_name),
            ("Client", client_name or "N/A"),
            ("Location", location or "N/A"),
            ("Estimate Reference", estimate_id[:8].upper()),
            ("Date Prepared", ref_date),
            ("Price Validity", f"{VALIDITY_DAYS} days (until {validity})"),
            ("Currency", "AED (United Arab Emirates Dirham)"),
        ]

        c.setFont("Helvetica", 9)
        for label, value in details:
            c.setFillColorRGB(*DARK_GRAY)
            c.drawString(2.0 * cm, y, f"{label}:")
            c.setFillColorRGB(*NAVY)
            c.setFont("Helvetica-Bold", 9)
            c.drawString(7.0 * cm, y, str(value))
            c.setFont("Helvetica", 9)
            y -= 0.45 * cm

        # ================================================================
        # PAGE 2 — SCOPE SUMMARY
        # ================================================================
        y = new_page()
        y = section_title(y, "SCOPE SUMMARY")

        scope_items = scope if isinstance(scope, dict) else {}
        scope_text_items = []

        # Extract scope data
        if scope_items.get("facade_systems"):
            for sys in scope_items["facade_systems"]:
                name = sys.get("system_type") or sys.get("name", "Unknown")
                area = sys.get("area_sqm", 0)
                scope_text_items.append(f"{name}: {area:.1f} sqm" if area else name)

        if scope_items.get("description"):
            scope_text_items.insert(0, str(scope_items["description"]))

        if scope_items.get("total_facade_area_sqm"):
            scope_text_items.append(f"Total Facade Area: {scope_items['total_facade_area_sqm']:.1f} sqm")

        if scope_items.get("total_openings"):
            scope_text_items.append(f"Total Openings: {scope_items['total_openings']}")

        if not scope_text_items:
            scope_text_items = ["Scope details extracted from project drawings and specifications."]

        c.setFont("Helvetica", 9)
        c.setFillColorRGB(*DARK_GRAY)
        for line in scope_text_items:
            y = check_page(y)
            c.drawString(2.0 * cm, y, f"- {line}")
            y -= 0.45 * cm

        # ================================================================
        # OPENING SCHEDULE TABLE
        # ================================================================
        y -= 0.5 * cm
        y = section_title(y, "OPENING SCHEDULE")

        openings = []
        if isinstance(opening_schedule, dict):
            openings = opening_schedule.get("openings", opening_schedule.get("items", []))
        elif isinstance(opening_schedule, list):
            openings = opening_schedule

        if openings:
            # Table headers
            col_x = [1.5 * cm, 4.5 * cm, 9.0 * cm, 11.5 * cm, 13.5 * cm, 15.5 * cm]
            headers = ["Ref", "System Type", "W x H (mm)", "Qty", "Area (sqm)", "Floors"]

            c.setFont("Helvetica-Bold", 8)
            c.setFillColorRGB(*NAVY)
            for i, h in enumerate(headers):
                c.drawString(col_x[i], y, h)
            y -= 0.15 * cm
            c.setStrokeColorRGB(*NAVY)
            c.line(1.5 * cm, y, page_w - 1.5 * cm, y)
            y -= 0.35 * cm

            c.setFont("Helvetica", 8)
            c.setFillColorRGB(*DARK_GRAY)
            for op in openings:
                y = check_page(y)
                ref = str(op.get("id", op.get("ref", "")))[:12]
                sys_type = str(op.get("system_type", ""))[:20]
                w = op.get("width_mm", 0)
                h_val = op.get("height_mm", 0)
                qty = op.get("quantity", 1)
                area = round((w / 1000) * (h_val / 1000) * qty, 2) if w and h_val else 0
                floors = op.get("floors", 1)

                c.drawString(col_x[0], y, ref)
                c.drawString(col_x[1], y, sys_type)
                c.drawString(col_x[2], y, f"{w} x {h_val}")
                c.drawString(col_x[3], y, str(qty))
                c.drawString(col_x[4], y, f"{area:.2f}")
                c.drawString(col_x[5], y, str(floors))
                y -= 0.4 * cm
        else:
            c.setFont("Helvetica-Oblique", 9)
            c.setFillColorRGB(*MID_GRAY)
            c.drawString(2.0 * cm, y, "Opening schedule will be confirmed upon drawing review.")
            y -= 0.5 * cm

        # ================================================================
        # BOM TABLE (grouped by category)
        # ================================================================
        y = new_page()
        y = section_title(y, "BILL OF QUANTITIES")

        if bom_items:
            # Group by category
            by_cat: Dict[str, list] = {}
            for item in bom_items:
                if not item.get("is_attic_stock"):
                    cat = item.get("category", "OTHER")
                    by_cat.setdefault(cat, []).append(item)

            cat_order = [
                "ALUMINUM", "GLASS", "ACP", "HARDWARE", "SEALANT",
                "FIXING", "SURFACE", "LABOR", "SITE", "TESTING", "PROVISIONAL",
            ]
            sorted_cats = [c for c in cat_order if c in by_cat]
            sorted_cats += [c for c in by_cat if c not in cat_order]

            for cat in sorted_cats:
                items = by_cat[cat]
                cat_total = sum(float(i.get("subtotal_aed", 0)) for i in items)

                y = check_page(y, 3.0)

                # Category header
                c.setFont("Helvetica-Bold", 9)
                c.setFillColorRGB(*NAVY)
                c.drawString(1.5 * cm, y, cat.title())
                c.drawRightString(page_w - 1.5 * cm, y, f"AED {cat_total:,.0f}")
                y -= 0.3 * cm
                c.setStrokeColorRGB(*LIGHT_GRAY)
                c.line(1.5 * cm, y, page_w - 1.5 * cm, y)
                y -= 0.3 * cm

                # Item rows
                c.setFont("Helvetica", 7.5)
                for item in items[:15]:  # Cap rows per category for readability
                    y = check_page(y)
                    desc = str(item.get("description", ""))[:45]
                    qty_val = item.get("quantity", 0)
                    unit = item.get("unit", "")
                    unit_cost = item.get("unit_cost_aed", 0)
                    subtotal = item.get("subtotal_aed", 0)

                    c.setFillColorRGB(*DARK_GRAY)
                    c.drawString(2.0 * cm, y, desc)
                    c.drawString(11.5 * cm, y, f"{qty_val:,.2f} {unit}")
                    c.drawString(14.0 * cm, y, f"{unit_cost:,.2f}")
                    c.setFillColorRGB(*NAVY)
                    c.drawRightString(page_w - 1.5 * cm, y, f"AED {subtotal:,.0f}")
                    y -= 0.35 * cm

                if len(items) > 15:
                    c.setFont("Helvetica-Oblique", 7)
                    c.setFillColorRGB(*MID_GRAY)
                    c.drawString(2.0 * cm, y, f"... and {len(items) - 15} more items in this category")
                    y -= 0.35 * cm

                y -= 0.3 * cm
        else:
            c.setFont("Helvetica-Oblique", 9)
            c.setFillColorRGB(*MID_GRAY)
            c.drawString(2.0 * cm, y, "BOM will be generated upon estimate processing.")
            y -= 0.5 * cm

        # ================================================================
        # FINANCIAL SUMMARY
        # ================================================================
        y = new_page()
        y = section_title(y, "FINANCIAL SUMMARY")

        total_aed = float(pricing.get("total_aed", 0))
        material_cost = float(pricing.get("material_cost_aed", 0))
        labor_cost = float(pricing.get("labor_cost_aed", 0))
        site_cost = float(pricing.get("site_cost_aed", 0))
        testing_cost = float(pricing.get("testing_cost_aed", 0))
        provisional = float(pricing.get("provisional_sums_aed", 0))
        overhead = float(pricing.get("overhead_aed", 0))
        margin_aed = float(pricing.get("margin_aed", 0))
        margin_pct = float(pricing.get("gross_margin_pct", 18))

        rows = [
            ("Material Cost (Aluminum + Glass + Hardware + Sealants)", material_cost, False),
            ("Labor & Fabrication", labor_cost, False),
            ("Site Works (Scaffolding, Crane, Transport)", site_cost, False),
            ("Testing & Commissioning", testing_cost, False),
            ("Provisional Sums (GPR, Water Test)", provisional, False),
            (None, None, None),  # separator
            ("Project Overhead (PM, Design, Insurance, Warranty)", overhead, False),
            (f"Gross Margin ({margin_pct:.0f}%)", margin_aed, False),
            (None, None, None),  # separator
            ("TOTAL CONTRACT VALUE (excl. VAT)", total_aed, True),
        ]

        c.setFont("Helvetica", 10)
        for row in rows:
            label, value, is_total = row
            if label is None:
                y -= 0.2 * cm
                c.setStrokeColorRGB(*LIGHT_GRAY)
                c.line(1.5 * cm, y, page_w - 1.5 * cm, y)
                y -= 0.3 * cm
                continue

            y = check_page(y)

            if is_total:
                c.setFont("Helvetica-Bold", 11)
                c.setFillColorRGB(*NAVY)
            else:
                c.setFont("Helvetica", 10)
                c.setFillColorRGB(*DARK_GRAY)

            c.drawString(1.5 * cm, y, label)

            if is_total:
                c.setFillColorRGB(*GOLD)
                c.setFont("Helvetica-Bold", 11)
            else:
                c.setFillColorRGB(*NAVY)
                c.setFont("Helvetica-Bold", 10)

            c.drawRightString(page_w - 1.5 * cm, y, f"AED {value:,.0f}")
            y -= 0.55 * cm

        # VAT
        y -= 0.3 * cm
        vat = total_aed * 0.05
        c.setFont("Helvetica-Bold", 10)
        c.setFillColorRGB(*GREEN)
        c.drawString(1.5 * cm, y, "VAT (5%)")
        c.drawRightString(page_w - 1.5 * cm, y, f"AED {vat:,.0f}")
        y -= 0.55 * cm

        c.setFillColorRGB(*GOLD)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(1.5 * cm, y, "TOTAL INCLUDING VAT")
        c.drawRightString(page_w - 1.5 * cm, y, f"AED {total_aed + vat:,.0f}")

        # ================================================================
        # TERMS & CONDITIONS
        # ================================================================
        y = new_page()
        y = section_title(y, "TERMS & CONDITIONS")

        terms = [
            f"1. This quotation is valid for {VALIDITY_DAYS} days from the date of issue.",
            "2. Payment Terms: 30% advance upon order confirmation, 30% upon material delivery,",
            "   30% upon installation completion, 10% retention (released after 12 months).",
            "3. Aluminum prices are subject to LME fluctuation clause (+/-5% tolerance).",
            "4. All prices are in AED (United Arab Emirates Dirham), exclusive of VAT.",
            "5. VAT at 5% will be applied as per UAE Federal Tax Authority regulations.",
            "6. Delivery timeline: To be confirmed upon order, typically 8-12 weeks for materials.",
            "7. Installation duration subject to site readiness and access confirmation.",
            "8. Warranty: 10 years structural, 5 years hardware, 10 years powder coating.",
            "9. Glass breakage during installation is covered under contractor's risk insurance.",
            "10. Any variation from the approved scope will be subject to a formal Variation Order.",
            "11. Testing & commissioning costs include water penetration test per AAMA 501.1.",
            "12. Scaffolding and crane access to be coordinated with main contractor.",
            "13. This proposal is based on drawings and specifications provided. Any discrepancies",
            "    discovered during shop drawing stage will be flagged as RFI.",
            "14. Provisional sums are included for GPR survey and independent water testing.",
            "    Actual costs will be reconciled upon completion.",
            "15. Attic stock (2%) is included per company policy for maintenance/replacement.",
        ]

        c.setFont("Helvetica", 8)
        c.setFillColorRGB(*DARK_GRAY)
        for line in terms:
            y = check_page(y)
            c.drawString(2.0 * cm, y, line)
            y -= 0.4 * cm

        # Signature block
        y -= 1.5 * cm
        y = check_page(y, 4.0)

        c.setStrokeColorRGB(*NAVY)
        c.setLineWidth(0.5)

        # Two columns for signatures
        left_x = 2.0 * cm
        right_x = page_w / 2 + 1.0 * cm

        c.setFont("Helvetica-Bold", 9)
        c.setFillColorRGB(*NAVY)
        c.drawString(left_x, y, "For and on behalf of:")
        c.drawString(right_x, y, "Accepted by Client:")
        y -= 0.4 * cm

        c.setFont("Helvetica-Bold", 9)
        c.setFillColorRGB(*GOLD)
        c.drawString(left_x, y, COMPANY_NAME)
        y -= 2.0 * cm

        c.setStrokeColorRGB(*NAVY)
        c.line(left_x, y, left_x + 6 * cm, y)
        c.line(right_x, y, right_x + 6 * cm, y)
        y -= 0.4 * cm

        c.setFont("Helvetica", 8)
        c.setFillColorRGB(*DARK_GRAY)
        c.drawString(left_x, y, "Authorized Signatory")
        c.drawString(right_x, y, "Name, Title & Company Stamp")
        y -= 0.4 * cm
        c.drawString(left_x, y, f"Date: {ref_date}")
        c.drawString(right_x, y, "Date: ________________")

        c.save()
        logger.info(f"Estimate PDF generated: {path}")
        return path

    except Exception as e:
        logger.error(f"Estimate PDF generation failed: {e}", exc_info=True)
        return None


# ════════════════════════════════════════════════════════════════════════
# VISUAL DRAFTING ENDPOINTS — Elevation, Shop Drawing, ACP Layout PDFs
# ════════════════════════════════════════════════════════════════════════


@router.get("/estimate/{estimate_id}/drawings")
async def download_drawings_package(
    estimate_id: str,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Generate and return list of available drawing files."""
    from app.services.drafting.visual_engine import VisualDraftingEngine

    # Load estimate
    result = await db.execute(
        select(Estimate).where(
            Estimate.id == estimate_id,
            Estimate.tenant_id == tenant_id,
        )
    )
    estimate = result.scalar_one_or_none()
    if not estimate:
        raise HTTPException(status_code=404, detail=f"Estimate {estimate_id} not found")

    # Extract openings and project name
    state = estimate.state_snapshot or {}
    opening_schedule = estimate.opening_schedule_json or state.get("opening_schedule", {})

    openings = []
    if isinstance(opening_schedule, dict):
        openings = opening_schedule.get("openings", opening_schedule.get("items", []))
    elif isinstance(opening_schedule, list):
        openings = opening_schedule

    project_name = f"Project {estimate_id[:8]}"
    if estimate.project_id:
        proj_result = await db.execute(
            select(Project).where(Project.id == estimate.project_id)
        )
        project = proj_result.scalar_one_or_none()
        if project:
            project_name = project.name or project_name

    _ensure_dir()
    engine = VisualDraftingEngine()
    drawing_result = engine.generate_all(estimate_id, openings, project_name=project_name)
    return drawing_result


@router.get("/estimate/{estimate_id}/drawing/{drawing_type}")
async def download_specific_drawing(
    estimate_id: str,
    drawing_type: str,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Download a specific drawing file (elevation, shop_drawing, acp_layout)."""
    from app.services.drafting.visual_engine import VisualDraftingEngine

    type_map = {
        "elevation": f"Elevations_{estimate_id[:8]}.pdf",
        "shop_drawing": f"ShopDrawings_{estimate_id[:8]}.pdf",
        "acp_layout": f"ACP_Layouts_{estimate_id[:8]}.pdf",
    }
    filename = type_map.get(drawing_type)
    if not filename:
        raise HTTPException(status_code=400, detail=f"Unknown drawing type: {drawing_type}")

    filepath = os.path.join(DOWNLOAD_DIR, filename)
    if not os.path.exists(filepath):
        # Generate on demand — load estimate data first
        result = await db.execute(
            select(Estimate).where(
                Estimate.id == estimate_id,
                Estimate.tenant_id == tenant_id,
            )
        )
        estimate = result.scalar_one_or_none()
        if not estimate:
            raise HTTPException(status_code=404, detail=f"Estimate {estimate_id} not found")

        state = estimate.state_snapshot or {}
        opening_schedule = estimate.opening_schedule_json or state.get("opening_schedule", {})

        openings = []
        if isinstance(opening_schedule, dict):
            openings = opening_schedule.get("openings", opening_schedule.get("items", []))
        elif isinstance(opening_schedule, list):
            openings = opening_schedule

        project_name = f"Project {estimate_id[:8]}"
        if estimate.project_id:
            proj_result = await db.execute(
                select(Project).where(Project.id == estimate.project_id)
            )
            project = proj_result.scalar_one_or_none()
            if project:
                project_name = project.name or project_name

        _ensure_dir()
        engine = VisualDraftingEngine()
        engine.generate_all(estimate_id, openings, project_name=project_name)

    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Drawing generation failed")

    return FileResponse(filepath, media_type="application/pdf", filename=filename)

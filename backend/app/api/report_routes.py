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
from app.models.orm_models import User, Estimate, Project, Tenant

router = APIRouter(prefix="/api/reports", tags=["Reports"])
logger = logging.getLogger("masaad-report-routes")

DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "/tmp/downloads")
DEFAULT_COMPANY_NAME = "MADINAT AL SAADA ALUMINIUM & GLASS WORKS LLC"
DEFAULT_COMPANY_SUB = "Ajman, United Arab Emirates  |  Tel: +971-6-XXX-XXXX  |  www.madinatalsaada.ae"
VALIDITY_DAYS = 7


def _hex_to_rgb(hex_color: str) -> tuple:
    """Convert '#RRGGBB' to (r, g, b) floats 0-1."""
    h = hex_color.lstrip("#")
    if len(h) != 6:
        return (15 / 255, 23 / 255, 42 / 255)
    return (int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255)


# Default Colors (overridden by tenant settings)
SILVER = (0.58, 0.64, 0.72)
GOLD = SILVER  # Legacy alias — brand uses silver/navy, not gold
DARK_GRAY = (0.2, 0.2, 0.2)
MID_GRAY = (0.5, 0.5, 0.5)
LIGHT_GRAY = (0.7, 0.7, 0.7)
WHITE = (1, 1, 1)
GREEN = (0.0, 0.4, 0.0)
RED = (0.7, 0.1, 0.1)


def _ensure_dir():
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)


@router.get("/estimate/{estimate_id}/excel")
async def generate_estimate_excel(
    estimate_id: str,
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Generate a per-estimate Excel workbook with Opening Schedule + BOM + Financial sheets."""
    result = await db.execute(
        select(Estimate).where(Estimate.id == estimate_id, Estimate.tenant_id == tenant_id)
    )
    estimate = result.scalar_one_or_none()
    if not estimate:
        raise HTTPException(status_code=404, detail=f"Estimate {estimate_id} not found")

    # Extract data
    state = estimate.state_snapshot or {}
    bom_output = estimate.bom_output_json or {}
    bom_items = bom_output.get("items", state.get("bom_items", []))
    pricing = bom_output.get("summary", state.get("pricing_data", {}))
    opening_schedule = estimate.opening_schedule_json or state.get("opening_schedule", {})
    scope = estimate.project_scope_json or state.get("project_scope", {})

    openings = []
    if isinstance(opening_schedule, dict):
        openings = opening_schedule.get("openings", opening_schedule.get("items", []))
    elif isinstance(opening_schedule, list):
        openings = opening_schedule

    # Project name
    project_name = f"Project {estimate_id[:8]}"
    if estimate.project_id:
        proj_result = await db.execute(select(Project).where(Project.id == estimate.project_id))
        project = proj_result.scalar_one_or_none()
        if project:
            project_name = project.name or project_name

    _ensure_dir()
    filename = f"Estimate_{estimate_id[:8]}.xlsx"
    path = os.path.join(DOWNLOAD_DIR, filename)

    try:
        import xlsxwriter
        wb = xlsxwriter.Workbook(path)
        bold = wb.add_format({"bold": True})
        money = wb.add_format({"num_format": "#,##0.00"})

        # Sheet 1: Opening Schedule
        ws1 = wb.add_worksheet("Opening Schedule")
        headers = ["Item Code", "System Type", "Width (mm)", "Height (mm)", "Qty", "Area (sqm)", "Floor", "Elevation", "Glass Type"]
        for c, h in enumerate(headers):
            ws1.write(0, c, h, bold)
        for r, op in enumerate(openings, 1):
            w = op.get("width_mm", 0)
            h_val = op.get("height_mm", 0)
            qty = op.get("quantity", 1)
            area = round((w / 1000) * (h_val / 1000) * qty, 2) if w and h_val else 0
            ws1.write(r, 0, op.get("mark_id", op.get("id", op.get("item_code", ""))))
            ws1.write(r, 1, op.get("system_type", ""))
            ws1.write(r, 2, w)
            ws1.write(r, 3, h_val)
            ws1.write(r, 4, qty)
            ws1.write(r, 5, area)
            ws1.write(r, 6, op.get("floor", ""))
            ws1.write(r, 7, op.get("elevation", ""))
            ws1.write(r, 8, op.get("glass_type", ""))

        # Sheet 2: BOM
        ws2 = wb.add_worksheet("Bill of Quantities")
        bom_headers = ["Category", "Description", "Qty", "Unit", "Unit Cost", "Subtotal"]
        for c, h in enumerate(bom_headers):
            ws2.write(0, c, h, bold)
        for r, item in enumerate(bom_items, 1):
            ws2.write(r, 0, item.get("category", ""))
            ws2.write(r, 1, item.get("description", ""))
            ws2.write(r, 2, item.get("quantity", 0))
            ws2.write(r, 3, item.get("unit", ""))
            ws2.write(r, 4, float(item.get("unit_cost_aed", 0)), money)
            ws2.write(r, 5, float(item.get("subtotal_aed", 0)), money)

        # Sheet 3: Financial Summary
        ws3 = wb.add_worksheet("Financial Summary")
        ws3.write(0, 0, "Project", bold)
        ws3.write(0, 1, project_name)
        ws3.write(1, 0, "Estimate ID", bold)
        ws3.write(1, 1, estimate_id[:8])
        fin_rows = [
            ("Material Cost", float(pricing.get("material_cost_aed", 0))),
            ("Labor Cost", float(pricing.get("labor_cost_aed", 0))),
            ("Site Cost", float(pricing.get("site_cost_aed", 0))),
            ("Overhead", float(pricing.get("overhead_aed", 0))),
            ("Margin", float(pricing.get("margin_aed", 0))),
            ("Total (excl VAT)", float(pricing.get("total_aed", 0))),
        ]
        for r, (label, val) in enumerate(fin_rows, 3):
            ws3.write(r, 0, label, bold)
            ws3.write(r, 1, val, money)

        wb.close()
        return FileResponse(path, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", filename=filename)
    except Exception as e:
        logger.error(f"Estimate Excel generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Excel generation failed: {e}")


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

    # Load tenant for white-label branding
    tenant_settings = {}
    if estimate.tenant_id:
        t_result = await db.execute(
            select(Tenant).where(Tenant.id == estimate.tenant_id)
        )
        tenant = t_result.scalar_one_or_none()
        if tenant:
            tenant_settings = {
                "company_name": tenant.company_name,
                "theme_color_hex": tenant.theme_color_hex,
                "base_currency": tenant.base_currency,
                "logo_url": tenant.logo_url,
                "report_header_text": tenant.report_header_text,
                "report_footer_text": tenant.report_footer_text,
            }

    state = estimate.state_snapshot or {}
    bom_output = estimate.bom_output_json or {}
    bom_items = bom_output.get("items", state.get("bom_items", []))
    pricing = bom_output.get("summary", state.get("pricing_data", {}))
    opening_schedule = estimate.opening_schedule_json or state.get("opening_schedule", {})
    scope = estimate.project_scope_json or state.get("project_scope", {})
    engineering_results = getattr(estimate, "engineering_results_json", None) or state.get("engineering_results", {})
    compliance_results = getattr(estimate, "compliance_results_json", None) or state.get("compliance_results", {})

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
        tenant_settings=tenant_settings,
        engineering_results=engineering_results,
        compliance_results=compliance_results,
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
    tenant_settings: dict = None,
    engineering_results: dict = None,
    compliance_results: dict = None,
) -> Optional[str]:
    """Build a full multi-page estimate PDF using ReportLab with white-label tenant branding."""
    try:
        from reportlab.pdfgen import canvas as rl_canvas
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import cm
        from reportlab.lib import colors

        # White-label tenant branding
        ts = tenant_settings or {}
        company_name = ts.get("company_name", DEFAULT_COMPANY_NAME)
        company_sub = ts.get("report_header_text", DEFAULT_COMPANY_SUB)
        theme_hex = ts.get("theme_color_hex", "#0f172a")
        NAVY = _hex_to_rgb(theme_hex)
        currency = ts.get("base_currency", "AED")
        footer_text = ts.get("report_footer_text")

        filename = f"Estimate_{estimate_id[:8]}.pdf"
        path = os.path.join(DOWNLOAD_DIR, filename)
        page_w, page_h = A4
        c = rl_canvas.Canvas(path, pagesize=A4)
        page_num = [1]  # mutable for nested functions

        def draw_header():
            """Draw themed header bar with tenant company branding."""
            c.setFillColorRGB(*NAVY)
            c.rect(0, page_h - 3 * cm, page_w, 3 * cm, fill=1, stroke=0)
            c.setFillColorRGB(*WHITE)
            c.setFont("Helvetica-Bold", 13)
            c.drawString(1.5 * cm, page_h - 1.5 * cm, company_name)
            c.setFont("Helvetica", 8)
            c.drawString(1.5 * cm, page_h - 2.1 * cm, company_sub)
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
            ft = footer_text or f"CONFIDENTIAL - {company_name}"
            c.drawString(1.5 * cm, 0.8 * cm, ft)
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
            f"Subject to revision if LME moves +/-5%. All prices in {currency} excl. VAT."
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
            ("Currency", f"{currency}"),
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
            # Detect if forensic fields are available (MODULE 3)
            has_forensic = any(
                op.get("aluminum_weight_kg") or op.get("gasket_length_lm") or op.get("hardware_sets")
                for op in openings
            )

            if has_forensic:
                # Extended table with forensic fields
                col_x = [1.5 * cm, 3.2 * cm, 6.0 * cm, 8.5 * cm, 10.0 * cm, 11.5 * cm, 13.2 * cm, 15.0 * cm, 17.0 * cm]
                headers = ["Mark", "System", "W x H", "Qty", "Area", "Al.kg", "Gasket", "HW", "Floors"]
            else:
                col_x = [1.5 * cm, 4.5 * cm, 9.0 * cm, 11.5 * cm, 13.5 * cm, 15.5 * cm]
                headers = ["Ref", "System Type", "W x H (mm)", "Qty", "Area (sqm)", "Floors"]

            c.setFont("Helvetica-Bold", 7 if has_forensic else 8)
            c.setFillColorRGB(*NAVY)
            for i, h in enumerate(headers):
                c.drawString(col_x[i], y, h)
            y -= 0.15 * cm
            c.setStrokeColorRGB(*NAVY)
            c.line(1.5 * cm, y, page_w - 1.5 * cm, y)
            y -= 0.35 * cm

            c.setFont("Helvetica", 7 if has_forensic else 8)
            c.setFillColorRGB(*DARK_GRAY)
            total_al_kg = 0
            total_gasket_lm = 0
            total_hw = 0
            for op in openings:
                y = check_page(y)
                ref = str(op.get("mark_id", op.get("id", op.get("ref", ""))))[:10]
                sys_type = str(op.get("system_type", ""))[:15 if has_forensic else 20]
                w = op.get("width_mm", 0)
                h_val = op.get("height_mm", 0)
                qty = op.get("quantity", 1)
                area = round((w / 1000) * (h_val / 1000) * qty, 2) if w and h_val else 0
                floors = op.get("floors", 1)

                c.drawString(col_x[0], y, ref)
                c.drawString(col_x[1], y, sys_type)
                c.drawString(col_x[2], y, f"{w}x{h_val}")
                c.drawString(col_x[3], y, str(qty))
                c.drawString(col_x[4], y, f"{area:.1f}")

                if has_forensic:
                    al_kg = float(op.get("aluminum_weight_kg", 0))
                    gasket = float(op.get("gasket_length_lm", 0))
                    hw = int(op.get("hardware_sets", 0))
                    total_al_kg += al_kg
                    total_gasket_lm += gasket
                    total_hw += hw
                    c.drawString(col_x[5], y, f"{al_kg:.1f}")
                    c.drawString(col_x[6], y, f"{gasket:.1f}")
                    c.drawString(col_x[7], y, str(hw))
                    c.drawString(col_x[8], y, str(floors))
                else:
                    c.drawString(col_x[5], y, str(floors))
                y -= 0.35 * cm

            # Totals row for forensic data
            if has_forensic:
                y -= 0.1 * cm
                c.setStrokeColorRGB(*NAVY)
                c.line(1.5 * cm, y + 0.15 * cm, page_w - 1.5 * cm, y + 0.15 * cm)
                c.setFont("Helvetica-Bold", 7)
                c.setFillColorRGB(*NAVY)
                c.drawString(col_x[0], y, "TOTALS")
                c.drawString(col_x[5], y, f"{total_al_kg:.1f}")
                c.drawString(col_x[6], y, f"{total_gasket_lm:.1f}")
                c.drawString(col_x[7], y, str(total_hw))
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
                c.drawRightString(page_w - 1.5 * cm, y, f"{currency} {cat_total:,.0f}")
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
                    c.drawRightString(page_w - 1.5 * cm, y, f"{currency} {subtotal:,.0f}")
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

            c.drawRightString(page_w - 1.5 * cm, y, f"{currency} {value:,.0f}")
            y -= 0.55 * cm

        # VAT
        y -= 0.3 * cm
        vat = total_aed * 0.05
        c.setFont("Helvetica-Bold", 10)
        c.setFillColorRGB(*GREEN)
        c.drawString(1.5 * cm, y, "VAT (5%)")
        c.drawRightString(page_w - 1.5 * cm, y, f"{currency} {vat:,.0f}")
        y -= 0.55 * cm

        c.setFillColorRGB(*GOLD)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(1.5 * cm, y, "TOTAL INCLUDING VAT")
        c.drawRightString(page_w - 1.5 * cm, y, f"{currency} {total_aed + vat:,.0f}")

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
            f"4. All prices are in {currency}, exclusive of VAT.",
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

        # ================================================================
        # ENGINEERING PROOFS (from physics engine forensic analysis)
        # ================================================================
        eng = engineering_results or {}
        if eng.get("per_opening_checks") or eng.get("summary"):
            y = new_page()
            y = section_title(y, "ENGINEERING PROOFS & COMPLIANCE")

            eng_summary = eng.get("summary", {})
            if eng_summary:
                summary_rows = [
                    ("Total Openings Analyzed", str(eng_summary.get("total_openings_checked", 0))),
                    ("Wind Load Compliance", f"{eng_summary.get('wind_load_pass_count', 0)}/{eng_summary.get('total_openings_checked', 0)} PASS"),
                    ("Deflection Compliance", f"{eng_summary.get('deflection_pass_count', 0)}/{eng_summary.get('total_openings_checked', 0)} PASS"),
                    ("Glass Stress Compliance", f"{eng_summary.get('glass_stress_pass_count', 0)}/{eng_summary.get('total_openings_checked', 0)} PASS"),
                    ("Thermal U-Value Compliance", f"{eng_summary.get('thermal_pass_count', 0)}/{eng_summary.get('total_openings_checked', 0)} PASS"),
                ]
                c.setFont("Helvetica", 9)
                for label, value in summary_rows:
                    y = check_page(y)
                    c.setFillColorRGB(*DARK_GRAY)
                    c.drawString(2.0 * cm, y, f"{label}:")
                    # Color code pass/fail
                    if "PASS" in value:
                        parts = value.split("/")
                        passed = int(parts[0]) if parts[0].isdigit() else 0
                        total_str = parts[1].split(" ")[0] if len(parts) > 1 else "0"
                        total_checks = int(total_str) if total_str.isdigit() else 0
                        if passed == total_checks and total_checks > 0:
                            c.setFillColorRGB(*GREEN)
                        else:
                            c.setFillColorRGB(*RED)
                    else:
                        c.setFillColorRGB(*NAVY)
                    c.setFont("Helvetica-Bold", 9)
                    c.drawString(9.0 * cm, y, value)
                    c.setFont("Helvetica", 9)
                    y -= 0.45 * cm

            # Per-opening check matrix (compact)
            per_opening = eng.get("per_opening_checks", [])
            if per_opening:
                y -= 0.5 * cm
                y = check_page(y, 3.0)
                c.setFont("Helvetica-Bold", 9)
                c.setFillColorRGB(*NAVY)
                c.drawString(1.5 * cm, y, "PER-OPENING CHECK MATRIX")
                y -= 0.3 * cm
                c.setStrokeColorRGB(*GOLD)
                c.line(1.5 * cm, y, page_w - 1.5 * cm, y)
                y -= 0.4 * cm

                # Headers
                chk_cols = [1.5 * cm, 4.0 * cm, 7.5 * cm, 10.5 * cm, 13.5 * cm, 16.0 * cm]
                chk_hdrs = ["Opening", "System", "Wind", "Deflect.", "Glass", "Thermal"]
                c.setFont("Helvetica-Bold", 7)
                for i, h in enumerate(chk_hdrs):
                    c.drawString(chk_cols[i], y, h)
                y -= 0.35 * cm

                c.setFont("Helvetica", 7)
                for chk in per_opening[:25]:  # Cap at 25 rows
                    y = check_page(y)
                    c.setFillColorRGB(*DARK_GRAY)
                    c.drawString(chk_cols[0], y, str(chk.get("opening_id", ""))[:10])
                    c.drawString(chk_cols[1], y, str(chk.get("system_type", ""))[:15])
                    # Pass/fail indicators
                    for idx, field in enumerate(["wind_load_pass", "deflection_pass", "glass_stress_pass", "thermal_pass"]):
                        val = chk.get(field)
                        if val is True:
                            c.setFillColorRGB(*GREEN)
                            c.drawString(chk_cols[2 + idx], y, "PASS")
                        elif val is False:
                            c.setFillColorRGB(*RED)
                            c.drawString(chk_cols[2 + idx], y, "FAIL")
                        else:
                            c.setFillColorRGB(*MID_GRAY)
                            c.drawString(chk_cols[2 + idx], y, "N/A")
                    y -= 0.3 * cm

                if len(per_opening) > 25:
                    c.setFont("Helvetica-Oblique", 7)
                    c.setFillColorRGB(*MID_GRAY)
                    c.drawString(2.0 * cm, y, f"... and {len(per_opening) - 25} more openings (see full report)")
                    y -= 0.3 * cm

        # ================================================================
        # COMPLIANCE RESULTS (thermal/acoustic/fire)
        # ================================================================
        comp = compliance_results or {}
        if comp:
            if not (eng.get("per_opening_checks") or eng.get("summary")):
                y = new_page()
            else:
                y -= 0.8 * cm
                y = check_page(y, 3.0)

            y = section_title(y, "COMPLIANCE CERTIFICATION SUMMARY")

            comp_rows = []
            if comp.get("thermal_compliance"):
                tc = comp["thermal_compliance"]
                comp_rows.append(("Thermal (ASHRAE 90.1)", tc.get("status", "N/A"), tc.get("u_value", "")))
            if comp.get("acoustic_compliance"):
                ac = comp["acoustic_compliance"]
                comp_rows.append(("Acoustic Rating", ac.get("status", "N/A"), ac.get("rw_db", "")))
            if comp.get("fire_compliance"):
                fc = comp["fire_compliance"]
                comp_rows.append(("Fire Rating (UAE Civil Defence)", fc.get("status", "N/A"), fc.get("rating_minutes", "")))

            c.setFont("Helvetica", 9)
            for label, status, detail in comp_rows:
                y = check_page(y)
                c.setFillColorRGB(*DARK_GRAY)
                c.drawString(2.0 * cm, y, f"{label}:")
                if "PASS" in str(status).upper() or "COMPLIANT" in str(status).upper():
                    c.setFillColorRGB(*GREEN)
                elif "FAIL" in str(status).upper():
                    c.setFillColorRGB(*RED)
                else:
                    c.setFillColorRGB(*NAVY)
                c.setFont("Helvetica-Bold", 9)
                detail_str = f" ({detail})" if detail else ""
                c.drawString(9.0 * cm, y, f"{status}{detail_str}")
                c.setFont("Helvetica", 9)
                y -= 0.45 * cm

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
        c.drawString(left_x, y, company_name)
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

    # Load tenant for branding
    tenant_settings = {}
    if estimate.tenant_id:
        t_result = await db.execute(select(Tenant).where(Tenant.id == estimate.tenant_id))
        t = t_result.scalar_one_or_none()
        if t:
            tenant_settings = {
                "company_name": t.company_name,
                "theme_color_hex": t.theme_color_hex,
                "logo_url": t.logo_url,
            }

    _ensure_dir()
    engine = VisualDraftingEngine(tenant_settings=tenant_settings)
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


@router.get("/estimate/{estimate_id}/shop-drawings")
async def get_shop_drawings(
    estimate_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate and return professional shop drawing PDF for an estimate."""
    from app.services.shop_drawing_engine import generate_shop_drawings
    from fastapi.responses import Response

    result = await db.execute(select(Estimate).where(Estimate.id == estimate_id))
    estimate = result.scalar_one_or_none()
    if not estimate:
        raise HTTPException(status_code=404, detail="Estimate not found")

    opening_schedule = estimate.opening_schedule_json or {}

    # Get project name
    project_name = f"Project {estimate_id[:8]}"
    if estimate.project_id:
        proj_result = await db.execute(
            select(Project).where(Project.id == estimate.project_id)
        )
        project = proj_result.scalar_one_or_none()
        if project:
            project_name = project.name or project_name

    # Get tenant branding
    company_name = None
    if estimate.tenant_id:
        tenant_result = await db.execute(
            select(Tenant).where(Tenant.id == estimate.tenant_id)
        )
        tenant = tenant_result.scalar_one_or_none()
        if tenant:
            company_name = tenant.company_name

    try:
        pdf_bytes = generate_shop_drawings(
            opening_schedule=opening_schedule,
            project_name=project_name,
            drawing_number_prefix=f"MAS-SHD-{estimate_id[:8].upper()}",
            company_name=company_name,
        )
    except Exception as e:
        logger.error(f"Shop drawing generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Shop drawing generation failed: {str(e)[:200]}")

    filename = f"shop_drawings_{estimate_id[:8]}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

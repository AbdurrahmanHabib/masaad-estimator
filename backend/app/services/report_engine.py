from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from datetime import datetime, timedelta

class ReportEngine:
    """
    Generates Professional Madinat Al Saada PDFs.
    Ensures technical specs and LME lock clauses are included.
    """
    def generate_quote(self, project_name: str, total_weight: float, total_area: float, boq_items: list):
        filename = f"Quote_{project_name.replace(' ', '_')}.pdf"
        c = canvas.Canvas(f"downloads/{filename}", pagesize=A4)
        
        # 1. Corporate Identity
        c.setFont("Helvetica-Bold", 12)
        c.drawString(2*cm, 27*cm, "MADINAT AL SAADA ALUMINIUM & GLASS WORKS LLC")
        c.setFont("Helvetica", 10)
        c.drawString(2*cm, 26.5*cm, "Ajman, UAE | www.madinatalsaada.ae")

        # 2. Project Metadata
        c.setFont("Helvetica-Bold", 16)
        c.drawString(2*cm, 24.5*cm, f"PROPOSAL: {project_name.upper()}")
        
        c.setFont("Helvetica", 10)
        c.drawString(2*cm, 23.5*cm, f"Date: {datetime.now().strftime('%d %b %Y')}")
        c.drawString(2*cm, 23.0*cm, f"Total Surface Area: {total_area} SQM")
        c.drawString(2*cm, 22.5*cm, f"Projected Material Tonnage: {total_weight/1000} MT")

        # 3. Technical Specs / Clause
        c.setFont("Helvetica-Oblique", 9)
        c.drawString(2*cm, 21.0*cm, "Note: All aluminum profiles mapped to Gulf Extrusions technical catalog.")
        c.setFont("Helvetica-Bold", 9)
        c.drawString(2*cm, 20.5*cm, f"LME LOCK: This quote is valid for 7 days based on current LME pricing.")

        # 4. Final Footer
        c.setFont("Helvetica", 8)
        c.drawString(2*cm, 2*cm, "Madinat Al Saada Aluminium & Glass Works LLC - Engineering Department")
        
        c.save()
        return filename

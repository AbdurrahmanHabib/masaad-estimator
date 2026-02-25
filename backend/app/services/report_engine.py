from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from datetime import datetime, timedelta

class ReportEngine:
    """
    Unified Group Reporting Engine.
    Produces high-stakes commercial submittals.
    """
    def generate_branded_quote(self, project_data: dict, items: list) -> str:
        filename = f"Commercial_Quote_{project_data['id']}.pdf"
        c = canvas.Canvas(f"downloads/{filename}", pagesize=A4)
        
        # 1. Official Corporate Identity
        c.setFont("Helvetica-Bold", 12)
        c.drawString(2*cm, 27.5*cm, "MADINAT AL SAADA ALUMINIUM & GLASS WORKS LLC")
        c.setFont("Helvetica", 9)
        c.drawString(2*cm, 27*cm, "Ajman, United Arab Emirates | www.madinatalsaada.ae")
        c.line(2*cm, 26.5*cm, 19*cm, 26.5*cm)

        # 2. Project Context
        c.setFont("Helvetica-Bold", 16)
        c.drawString(2*cm, 25*cm, f"PROPOSAL: {project_data['name'].upper()}")
        
        c.setFont("Helvetica", 10)
        c.drawString(2*cm, 24*cm, f"Total Surface Area: {project_data['total_area']} SQM")
        c.drawString(2*cm, 23.5*cm, f"Estimated Material Weight: {project_data['total_weight']} KG")

        # 3. LME Protection Clause
        c.setFillColorRGB(0.1, 0.1, 0.1)
        c.rect(2*cm, 21*cm, 17*cm, 1.5*cm, fill=0)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(2.5*cm, 22*cm, "CRITICAL: LME PRICE LOCK & VALIDITY")
        c.setFont("Helvetica", 8)
        validity_date = (datetime.now() + timedelta(days=7)).strftime('%d %b %Y')
        c.drawString(2.5*cm, 21.5*cm, f"This proposal is valid for 7 days (until {validity_date}). Aluminum prices are locked to current LME index.")

        # 4. Technical Mapping
        c.setFont("Helvetica-Oblique", 8)
        c.drawString(2*cm, 2*cm, "Engineering Note: All profiles are mapped to Gulf Extrusions or Elite Extrusion technical standards.")
        
        c.showPage()
        c.save()
        return filename

import fitz
import pdfplumber
from ultralytics import YOLO
from litellm import completion
from typing import Dict, Any, List

class PDFParserService:
    def __init__(self, yolo_model_path: str):
        self.model = YOLO(yolo_model_path)

    def extract_specs_with_llm(self, pdf_path: str) -> Dict[str, Any]:
        text = ""
        with fitz.open(pdf_path) as doc:
            for page in doc: text += page.get_text()
        response = completion(
            model="gpt-4-turbo",
            messages=[{"role": "system", "content": "Extract facade specs. Output JSON."}, {"role": "user", "content": text}]
        )
        return response.choices[0].message.content

    def extract_boq_tables(self, pdf_path: str) -> List[Dict]:
        tables = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                extracted = page.extract_table()
                if extracted: tables.append({"page": page.page_number, "data": extracted})
        return tables

    def run_vision_inference(self, pdf_path: str, calibration: Dict[str, Any]) -> List[Dict]:
        results_out = []
        scale_factor = calibration["real_mm"] / calibration["pixel_dist"]
        doc = fitz.open(pdf_path)
        page = doc.load_page(calibration["page_number"])
        pix = page.get_pixmap(dpi=300)
        img_path = "tmp_page.png"
        pix.save(img_path)
        results = self.model(img_path)
        for r in results:
            for box in r.boxes:
                b = box.xyxy[0].cpu().numpy()
                px_w, px_h = b[2] - b[0], b[3] - b[1]
                results_out.append({
                    "class": self.model.names[int(box.cls)],
                    "real_width_mm": px_w * scale_factor,
                    "real_height_mm": px_h * scale_factor
                })
        return results_out
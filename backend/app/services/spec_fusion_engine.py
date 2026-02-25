import fitz
import json
from litellm import completion
from typing import Dict, Any, List

class SpecFusionEngine:
    def __init__(self):
        self.model = "gpt-4-turbo" # Can be swapped to Gemini 1.5 Pro

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extracts raw text from Specification Documents."""
        text = ""
        with fitz.open(pdf_path) as doc:
            for page in doc:
                text += page.get_text()
        return text

    def cross_reference(self, dwg_entities: List[Dict[str, Any]], pdf_text: str) -> Dict[str, Any]:
        """
        The Omniscient Matcher: Finds specs for systems detected in the DWG.
        Generates RFI warnings if critical data is missing.
        """
        system_names = [e.get('name') for e in dwg_entities]
        
        prompt = f"""
        You are a Senior Facade Estimator for Madinat Al Saada.
        We extracted the following system tags from the architectural DWG:
        {system_names}
        
        Analyze the following text from the project specifications:
        {pdf_text[:15000]} 
        
        For each system tag, extract the exact requirements for:
        1. Glass U-Value & Type
        2. Hardware Brand (e.g., Giesse, Savio, Roto)
        3. Paint/Finish type and Micron thickness (e.g., PVDF 40 microns)
        4. Fire-rating (if any)
        
        CRITICAL RULE: If a requirement is not explicitly mentioned in the text for a specific system, 
        you MUST output "RFI_REQUIRED" for that specific field.
        
        Output as a strict JSON object where keys are the system tags.
        """
        
        try:
            response = completion(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={ "type": "json_object" }
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            return {"error": f"Fusion Engine Failed: {str(e)}"}
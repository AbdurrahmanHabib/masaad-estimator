from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
import os
import shutil
import uuid
from typing import Dict, Any
from app.services.dwg_parser import DWGParserService
from app.services.pdf_parser import PDFParserService
from app.agents.ingestion_graph import ingestion_app

router = APIRouter(prefix="/api/ingestion", tags=["Project Ingestion"])

# Initialize services (these paths should be in .env)
ODA_PATH = os.getenv("ODA_CONVERTER_PATH", "/usr/bin/ODAFileConverter")
YOLO_PATH = os.getenv("YOLO_MODEL_PATH", "resources/models/best.pt")

dwg_service = DWGParserService(ODA_PATH)
pdf_service = PDFParserService(YOLO_PATH)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload-drawings")
async def upload_drawings(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    if not file.filename.lower().endswith(('.dwg', '.dxf')):
        raise HTTPException(status_code=400, detail="Invalid file type. Only DWG/DXF allowed.")
    
    file_id = str(uuid.uuid4())
    file_ext = os.path.splitext(file.filename)[1]
    file_path = os.path.join(UPLOAD_DIR, f"{file_id}{file_ext}")
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Process in background or return initial extraction
    try:
        if file_ext.lower() == ".dwg":
            dxf_path = dwg_service.convert_dwg_to_dxf(file_path, UPLOAD_DIR)
            geometry = dwg_service.extract_geometry(dxf_path)
        else:
            geometry = dwg_service.extract_geometry(file_path)
            
        return {
            "status": "success",
            "file_id": file_id,
            "extraction": geometry
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload-specs")
async def upload_specs(file: UploadFile = File(...)):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Invalid file type. Only PDF allowed.")
    
    file_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{file_id}.pdf")
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    try:
        specs = pdf_service.extract_specs_with_llm(file_path)
        return {
            "status": "success",
            "file_id": file_id,
            "specs": specs
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/execute-fusion")
async def execute_fusion(payload: Dict[str, Any]):
    # This would trigger the LangGraph workflow
    # initial_state = IngestionState(...)
    # result = await ingestion_app.ainvoke(initial_state)
    return {"status": "processing", "message": "Fusion Engine started"}

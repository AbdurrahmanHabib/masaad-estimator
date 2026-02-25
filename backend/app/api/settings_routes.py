from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from pydantic import BaseModel
import pandas as pd
import io
import logging
# from app.db.session import db 

router = APIRouter(prefix="/api/settings", tags=["Tenant Settings"])
logger = logging.getLogger("masaad-api")

# Persistent state for mock calculation (In production, this would be in DB)
class GroupFinancialState:
    total_group_overhead = 0.0
    direct_payroll_cost = 0.0
    active_factory_hours = 0.0

fin_state = GroupFinancialState()

class MarketUpdate(BaseModel):
    lme_rate: float
    billet_premium: float
    stock_length: float

@router.post("/upload-payroll")
async def upload_payroll(file: UploadFile = File(...)):
    """
    Ingests Payroll CSV. Filters strictly for Site/Job Location == 'FACTORY'.
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed.")
    
    try:
        contents = await file.read()
        df = pd.read_csv(io.StringIO(contents.decode('utf-8')))
        df.columns = df.columns.str.upper().str.replace(' ', '_')
        
        # Mandatory Filter: Job Location == FACTORY
        # Check both possible column names for robust ingestion
        loc_col = next((c for c in ['SITE_LOCATION', 'JOB_LOCATION', 'LOCATION'] if c in df.columns), None)
        if not loc_col:
             raise HTTPException(status_code=400, detail="CSV missing Location column (SITE_LOCATION or JOB_LOCATION)")
        
        factory_df = df[df[loc_col].str.upper() == 'FACTORY']
        
        if len(factory_df) == 0:
            raise HTTPException(status_code=400, detail="No 'FACTORY' location employees found.")
            
        # Calculation: Direct Payroll + Hours
        salary_col = next((c for c in ['BASIC_SALARY', 'TOTAL_PAY', 'GROSS'] if c in df.columns), 'BASIC_SALARY')
        hours_col = next((c for c in ['WORKING_HOURS', 'ACTIVE_HOURS', 'HOURS'] if c in df.columns), None)
        
        fin_state.direct_payroll_cost = pd.to_numeric(factory_df[salary_col], errors='coerce').sum()
        
        # If hours not provided, assume standard 208 hrs/worker
        if hours_col:
            fin_state.active_factory_hours = pd.to_numeric(factory_df[hours_col], errors='coerce').sum()
        else:
            fin_state.active_factory_hours = len(factory_df) * 208
            
        # Calculate Burdened Rate
        true_shop_rate = 0.0
        if fin_state.active_factory_hours > 0:
            true_shop_rate = (fin_state.total_group_overhead + fin_state.direct_payroll_cost) / fin_state.active_factory_hours
        
        return {
            "status": "success",
            "metrics": {
                "factory_headcount": len(factory_df),
                "direct_payroll_cost": round(float(fin_state.direct_payroll_cost), 2),
                "active_factory_hours": float(fin_state.active_factory_hours),
                "true_shop_rate_aed": round(float(true_shop_rate), 2)
            }
        }
    except Exception as e:
        logger.error(f"Payroll upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload-expenses")
async def upload_expenses(file: UploadFile = File(...)):
    """
    Ingests admin expenses CSV. Sums MADINAT, AL JAZEERA, and MADINAT AL JAZEERA.
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed.")
        
    try:
        contents = await file.read()
        df = pd.read_csv(io.StringIO(contents.decode('utf-8')))
        df.columns = df.columns.str.upper().str.strip()
        
        required_cols = ['MADINAT', 'AL JAZEERA', 'MADINAT AL JAZEERA']
        for col in required_cols:
            if col not in df.columns:
                raise HTTPException(status_code=400, detail=f"CSV missing group entity column: {col}")
            
        # Unified Group Model: Sum across all 3 entities
        fin_state.total_group_overhead = df[required_cols].apply(pd.to_numeric, errors='coerce').sum().sum()
        
        return {
            "status": "success",
            "total_group_overhead_aed": round(float(fin_state.total_group_overhead), 2),
            "entities_aggregated": required_cols
        }
    except Exception as e:
        logger.error(f"Expense upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/update-market")
async def update_market(payload: MarketUpdate):
    return {
        "status": "success",
        "message": "Market variables updated.",
        "data": payload.model_dump()
    }
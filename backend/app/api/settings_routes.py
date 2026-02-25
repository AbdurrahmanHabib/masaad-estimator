from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from pydantic import BaseModel
import pandas as pd
import io
import logging
# from app.db.session import db  # Assuming a DB pool is available

router = APIRouter(prefix="/api/settings", tags=["Tenant Settings"])
logger = logging.getLogger("masaad-api")

class MarketUpdate(BaseModel):
    lme_rate: float
    billet_premium: float
    stock_length: float

@router.post("/upload-payroll")
async def upload_payroll(file: UploadFile = File(...)):
    """
    Ingests the monthly payroll CSV.
    Filters by 'FACTORY' department and calculates the True Shop Rate.
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed.")
    
    try:
        contents = await file.read()
        df = pd.read_csv(io.StringIO(contents.decode('utf-8')))
        
        # Ensure required columns exist
        if not {'department', 'basic_salary', 'allowances'}.issubset(df.columns.str.lower()):
             raise HTTPException(status_code=400, detail="CSV missing required columns: department, basic_salary, allowances")
        
        # Filter for Factory Workers
        factory_df = df[df['department'].str.upper() == 'FACTORY']
        total_factory_workers = len(factory_df)
        
        if total_factory_workers == 0:
            raise HTTPException(status_code=400, detail="No 'FACTORY' employees found in payroll data.")
            
        total_monthly_payroll = factory_df['basic_salary'].sum() + factory_df['allowances'].sum()
        
        # Calculate Blended Hourly Rate (Assumes 208 working hours/month + 1.35 Burden Factor)
        avg_monthly_salary = total_monthly_payroll / total_factory_workers
        uae_burden_factor = 1.35
        true_shop_rate = (avg_monthly_salary * uae_burden_factor) / 208
        
        # TODO: Save to Database
        # await db.execute("UPDATE tenant_settings SET true_shop_rate = $1, factory_headcount = $2", true_shop_rate, total_factory_workers)
        
        return {
            "status": "success",
            "message": "Payroll processed successfully.",
            "data": {
                "factory_headcount": total_factory_workers,
                "total_monthly_payroll": float(total_monthly_payroll),
                "true_shop_rate_aed": round(float(true_shop_rate), 2)
            }
        }
    except Exception as e:
        logger.error(f"Payroll upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload-expenses")
async def upload_expenses(file: UploadFile = File(...)):
    """
    Ingests the admin expenses CSV.
    Sums the 'MADINAT' column to calculate total administrative overhead.
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed.")
        
    try:
        contents = await file.read()
        df = pd.read_csv(io.StringIO(contents.decode('utf-8')))
        
        # Normalize column names to uppercase for robust matching
        df.columns = df.columns.str.upper()
        
        if 'MADINAT' not in df.columns:
            raise HTTPException(status_code=400, detail="CSV missing required column: MADINAT")
            
        # Sum the Madinat column, coercing non-numeric to NaN then dropping them
        total_admin_expenses = pd.to_numeric(df['MADINAT'], errors='coerce').sum()
        
        # TODO: Save to Database
        # await db.execute("UPDATE tenant_settings SET total_admin_expenses = $1", total_admin_expenses)
        
        return {
            "status": "success",
            "message": "Admin expenses processed successfully.",
            "data": {
                "total_admin_expenses_aed": round(float(total_admin_expenses), 2)
            }
        }
    except Exception as e:
        logger.error(f"Expense upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/update-market")
async def update_market(payload: MarketUpdate):
    """
    Updates the live market variables for the tenant.
    """
    # TODO: Save to Database
    # await db.execute("UPDATE tenant_settings SET lme_rate = $1, billet_premium = $2, stock_length = $3", 
    #                 payload.lme_rate, payload.billet_premium, payload.stock_length)
    
    return {
        "status": "success",
        "message": "Market variables updated successfully.",
        "data": payload.model_dump()
    }
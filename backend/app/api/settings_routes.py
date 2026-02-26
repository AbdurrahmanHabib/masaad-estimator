"""Settings routes — financial rates, material rates, catalog, LME refresh."""
import os
import io
import logging
import httpx
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db import get_db
from app.api.deps import get_current_user, require_admin
from app.models.orm_models import FinancialRates, MaterialRates, Tenant, User

router = APIRouter(prefix="/api/settings", tags=["Tenant Settings"])
logger = logging.getLogger("masaad-api")


# ─── Pydantic schemas ────────────────────────────────────────────────────────

class FinancialRatesUpdate(BaseModel):
    lme_aluminum_usd_mt: Optional[float] = None
    billet_premium_usd_mt: Optional[float] = None
    extrusion_premium_usd_mt: Optional[float] = None
    usd_aed: Optional[float] = None
    factory_overhead_pct: Optional[float] = None
    admin_overhead_pct: Optional[float] = None
    risk_contingency_pct: Optional[float] = None
    default_profit_margin_pct: Optional[float] = None


class MaterialRatesUpdate(BaseModel):
    # Glass
    glass_clear_float_aed_sqm: Optional[float] = None
    glass_tinted_aed_sqm: Optional[float] = None
    glass_tempered_clear_aed_sqm: Optional[float] = None
    glass_tempered_tinted_aed_sqm: Optional[float] = None
    glass_laminated_6_6_aed_sqm: Optional[float] = None
    glass_low_e_aed_sqm: Optional[float] = None
    glass_dgu_6_12_6_clear_aed_sqm: Optional[float] = None
    glass_dgu_low_e_aed_sqm: Optional[float] = None
    glass_opaque_spandrel_aed_sqm: Optional[float] = None
    glass_structural_dgu_aed_sqm: Optional[float] = None
    # ACP
    acp_polyester_aed_sqm: Optional[float] = None
    acp_powder_coat_aed_sqm: Optional[float] = None
    acp_pvdf_aed_sqm: Optional[float] = None
    acp_metallic_pvdf_aed_sqm: Optional[float] = None
    acp_mirror_aed_sqm: Optional[float] = None
    # Hardware
    hardware_casement_handle_aed: Optional[float] = None
    hardware_casement_hinge_pair_aed: Optional[float] = None
    hardware_casement_lock_aed: Optional[float] = None
    hardware_casement_restrictor_aed: Optional[float] = None
    hardware_door_handle_set_aed: Optional[float] = None
    hardware_mortice_lock_aed: Optional[float] = None
    hardware_door_closer_aed: Optional[float] = None
    hardware_door_hinge_set_aed: Optional[float] = None
    hardware_floor_spring_aed: Optional[float] = None
    hardware_patch_fitting_set_aed: Optional[float] = None
    hardware_spider_fitting_aed: Optional[float] = None
    # Sealants
    sealant_weatherseal_310ml_aed: Optional[float] = None
    sealant_structural_600ml_aed: Optional[float] = None
    sealant_primer_500ml_aed: Optional[float] = None
    backer_rod_10mm_per_lm_aed: Optional[float] = None
    backer_rod_15mm_per_lm_aed: Optional[float] = None
    setting_block_each_aed: Optional[float] = None
    distance_piece_each_aed: Optional[float] = None
    # Fixings
    anchor_m10_each_aed: Optional[float] = None
    anchor_m12_each_aed: Optional[float] = None
    bracket_80mm_each_aed: Optional[float] = None
    bracket_120mm_each_aed: Optional[float] = None
    shim_plate_each_aed: Optional[float] = None
    thermal_pad_each_aed: Optional[float] = None
    t_connector_each_aed: Optional[float] = None
    l_connector_each_aed: Optional[float] = None
    end_cap_each_aed: Optional[float] = None
    expansion_joint_each_aed: Optional[float] = None
    fire_stop_per_lm_aed: Optional[float] = None
    drainage_insert_each_aed: Optional[float] = None
    # Labor
    factory_hourly_rate_aed: Optional[float] = None
    site_installation_rate_aed: Optional[float] = None
    # Overheads
    factory_overhead_pct: Optional[float] = None
    admin_overhead_pct: Optional[float] = None
    risk_contingency_pct: Optional[float] = None
    default_profit_margin_pct: Optional[float] = None


# ─── Helpers ────────────────────────────────────────────────────────────────

async def _get_tenant_id(user: User) -> str:
    if not user.tenant_id:
        raise HTTPException(status_code=400, detail="User has no tenant assigned")
    return str(user.tenant_id)


async def _fetch_live_lme() -> float:
    """Fetch live LME aluminum price from free metals API."""
    try:
        # Try metals-api.com (500 free calls/month)
        metals_api_key = os.getenv("METALS_API_KEY", "")
        if metals_api_key:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(
                    f"https://metals-api.com/api/latest?access_key={metals_api_key}&base=USD&symbols=ALU"
                )
                if r.status_code == 200:
                    data = r.json()
                    if data.get("success") and "ALU" in data.get("rates", {}):
                        # metals-api returns price per troy oz; LME is per metric ton
                        # ALU in metals-api is USD per metric ton directly
                        return float(data["rates"]["ALU"])

        # Fallback: use a public commodities API
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                "https://api.stlouisfed.org/fred/series/observations?series_id=ALUM&api_key=demo&file_type=json&limit=1&sort_order=desc",
                headers={"Accept": "application/json"}
            )
            if r.status_code == 200:
                data = r.json()
                obs = data.get("observations", [])
                if obs:
                    return float(obs[0]["value"]) * 1000  # convert from USD/kg to USD/MT

    except Exception as e:
        logger.warning(f"LME fetch failed: {e}")

    return None  # Caller will use cached value


# ─── Endpoints ──────────────────────────────────────────────────────────────

@router.get("/current-rates")
async def get_current_rates(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return current financial + material rates for the tenant."""
    tenant_id = await _get_tenant_id(user)

    fin_result = await db.execute(select(FinancialRates).where(FinancialRates.tenant_id == tenant_id))
    fin = fin_result.scalar_one_or_none()

    mat_result = await db.execute(select(MaterialRates).where(MaterialRates.tenant_id == tenant_id))
    mat = mat_result.scalar_one_or_none()

    return {
        "financial_rates": {c.name: getattr(fin, c.name) for c in FinancialRates.__table__.columns} if fin else {},
        "material_rates": {c.name: getattr(mat, c.name) for c in MaterialRates.__table__.columns} if mat else {},
    }


@router.post("/financial-rates")
async def upsert_financial_rates(
    payload: FinancialRatesUpdate,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """UPSERT financial rates for the tenant."""
    tenant_id = await _get_tenant_id(user)

    result = await db.execute(select(FinancialRates).where(FinancialRates.tenant_id == tenant_id))
    fin = result.scalar_one_or_none()

    if not fin:
        fin = FinancialRates(tenant_id=tenant_id)
        db.add(fin)

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(fin, field, value)

    await db.commit()
    return {"status": "updated", "financial_rates": payload.model_dump(exclude_none=True)}


@router.get("/material-rates")
async def get_material_rates(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return material rates for the tenant."""
    tenant_id = await _get_tenant_id(user)
    result = await db.execute(select(MaterialRates).where(MaterialRates.tenant_id == tenant_id))
    mat = result.scalar_one_or_none()
    if not mat:
        return {}
    return {c.name: getattr(mat, c.name) for c in MaterialRates.__table__.columns}


@router.post("/material-rates")
async def upsert_material_rates(
    payload: MaterialRatesUpdate,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """UPSERT material rates for the tenant."""
    tenant_id = await _get_tenant_id(user)

    result = await db.execute(select(MaterialRates).where(MaterialRates.tenant_id == tenant_id))
    mat = result.scalar_one_or_none()

    if not mat:
        mat = MaterialRates(tenant_id=tenant_id)
        db.add(mat)

    updates = payload.model_dump(exclude_none=True)
    for field, value in updates.items():
        setattr(mat, field, value)

    if updates:
        mat.rates_last_updated = datetime.utcnow()
        mat.updated_by = user.id

    await db.commit()
    return {"status": "updated", "fields_updated": list(updates.keys())}


@router.get("/refresh-lme")
async def refresh_lme(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Refresh live LME aluminum price. Uses 6-hour cache."""
    tenant_id = await _get_tenant_id(user)

    result = await db.execute(select(FinancialRates).where(FinancialRates.tenant_id == tenant_id))
    fin = result.scalar_one_or_none()

    # Check cache: if updated within 6 hours, return cached
    if fin and fin.lme_last_updated:
        age_hours = (datetime.utcnow() - fin.lme_last_updated).total_seconds() / 3600
        if age_hours < 6 and fin.lme_aluminum_usd_mt:
            return {
                "lme_usd_mt": float(fin.lme_aluminum_usd_mt),
                "source": "cached",
                "cache_age_hours": round(age_hours, 1),
                "last_updated": fin.lme_last_updated.isoformat(),
            }

    # Fetch live
    live_price = await _fetch_live_lme()

    if live_price and fin:
        fin.lme_aluminum_usd_mt = live_price
        fin.lme_last_updated = datetime.utcnow()
        fin.lme_source = "live"
        await db.commit()
        return {
            "lme_usd_mt": live_price,
            "source": "live",
            "cache_age_hours": 0,
            "last_updated": fin.lme_last_updated.isoformat(),
        }
    elif fin and fin.lme_aluminum_usd_mt:
        return {
            "lme_usd_mt": float(fin.lme_aluminum_usd_mt),
            "source": "cached_fallback",
            "note": "Live fetch failed — returning last known value",
            "last_updated": fin.lme_last_updated.isoformat() if fin.lme_last_updated else None,
        }

    return {"lme_usd_mt": 2485.0, "source": "default", "note": "No cached value — using default"}


@router.post("/upload-payroll")
async def upload_payroll(
    file: UploadFile = File(...),
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Ingest payroll Excel (multi-sheet: MADINAT, AL JAZEERA, MADINAT AL JAZEERA).
    Filters for FACTORY job location. Calculates hourly burn rate.
    """
    import pandas as pd

    if not (file.filename.endswith('.xlsx') or file.filename.endswith('.xls') or file.filename.endswith('.csv')):
        raise HTTPException(status_code=400, detail="Upload Excel (.xlsx/.xls) or CSV file")

    try:
        contents = await file.read()

        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.StringIO(contents.decode('utf-8')))
            all_factory = _filter_factory_workers(df)
        else:
            xls = pd.read_excel(io.BytesIO(contents), sheet_name=None)
            factory_dfs = []
            for sheet_name, df in xls.items():
                factory_df = _filter_factory_workers(df)
                if len(factory_df) > 0:
                    factory_df["_sheet"] = sheet_name
                    factory_dfs.append(factory_df)
            if not factory_dfs:
                raise HTTPException(status_code=400, detail="No FACTORY workers found in any sheet")
            all_factory = pd.concat(factory_dfs, ignore_index=True)

        if len(all_factory) == 0:
            raise HTTPException(status_code=400, detail="No FACTORY workers found")

        # Calculate burn rate
        salary_col = next(
            (c for c in all_factory.columns if any(kw in c.upper() for kw in ['SALARY', 'PAY', 'GROSS', 'TOTAL'])),
            None
        )
        if not salary_col:
            raise HTTPException(status_code=400, detail="Could not find salary column")

        total_monthly_payroll = pd.to_numeric(all_factory[salary_col], errors='coerce').sum()
        total_workers = len(all_factory)
        # 6 days/week × 8 hrs/day × 4.33 weeks/month
        monthly_hours_per_worker = 6 * 8 * 4.33
        total_available_hours = monthly_hours_per_worker * total_workers
        burn_rate = total_monthly_payroll / total_available_hours if total_available_hours > 0 else 0

        # Update material rates with factory hourly rate
        tenant_id = await _get_tenant_id(user)
        mat_result = await db.execute(select(MaterialRates).where(MaterialRates.tenant_id == tenant_id))
        mat = mat_result.scalar_one_or_none()
        if mat:
            mat.factory_hourly_rate_aed = round(burn_rate, 2)
            mat.rates_last_updated = datetime.utcnow()
            await db.commit()

        return {
            "status": "success",
            "metrics": {
                "factory_headcount": int(total_workers),
                "total_monthly_payroll_aed": round(float(total_monthly_payroll), 2),
                "monthly_hours_per_worker": monthly_hours_per_worker,
                "total_available_hours": round(float(total_available_hours), 1),
                "burn_rate_aed_per_hr": round(float(burn_rate), 2),
            },
            "note": "Factory hourly rate saved to material rates settings",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Payroll upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _filter_factory_workers(df):
    """Filter dataframe for factory workers across any column naming convention."""
    import pandas as pd
    df = df.copy()
    df.columns = df.columns.str.strip()
    loc_col = next(
        (c for c in df.columns if any(kw in c.upper() for kw in ['LOCATION', 'SITE', 'JOB'])),
        None
    )
    if loc_col:
        return df[df[loc_col].astype(str).str.upper().str.strip() == 'FACTORY']
    return pd.DataFrame()


@router.post("/upload-expenses")
async def upload_expenses(
    file: UploadFile = File(...),
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Ingest admin expenses CSV/Excel. Aggregates across MADINAT, AL JAZEERA entities."""
    import pandas as pd

    try:
        contents = await file.read()
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.StringIO(contents.decode('utf-8')))
        else:
            df = pd.read_excel(io.BytesIO(contents))

        df.columns = df.columns.str.upper().str.strip()

        entity_cols = ['MADINAT', 'AL JAZEERA', 'MADINAT AL JAZEERA']
        found_cols = [c for c in entity_cols if c in df.columns]
        if not found_cols:
            # Try to sum a single AMOUNT/TOTAL column
            amount_col = next((c for c in df.columns if 'AMOUNT' in c or 'TOTAL' in c or 'EXPENSE' in c), None)
            if amount_col:
                total = pd.to_numeric(df[amount_col], errors='coerce').sum()
                return {"status": "success", "total_group_overhead_aed": round(float(total), 2)}
            raise HTTPException(status_code=400, detail="Could not find expense columns")

        total = df[found_cols].apply(pd.to_numeric, errors='coerce').sum().sum()

        # Update financial rates
        tenant_id = await _get_tenant_id(user)
        fin_result = await db.execute(select(FinancialRates).where(FinancialRates.tenant_id == tenant_id))
        fin = fin_result.scalar_one_or_none()
        if fin:
            fin.total_group_overhead_aed = float(total)
            await db.commit()

        return {
            "status": "success",
            "total_group_overhead_aed": round(float(total), 2),
            "entities_aggregated": found_cols,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Expense upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/update-market")
async def update_market(
    payload: FinancialRatesUpdate,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update market variables (LME, billet premium, etc.)."""
    return await upsert_financial_rates(payload, user, db)

"""
Celery Tasks — All CPU-heavy operations run here, off the FastAPI main thread.

Key changes from original:
- parse_catalog_pdf: now reads file bytes and calls async parse() correctly
- refresh_lme_prices: new Celery Beat task (daily 08:00 GST)
- run_full_pipeline: checkpoint/resume logic for crash recovery
"""
import os
import json
import logging
import asyncio
from datetime import datetime, timezone
from app.workers.celery_app import celery_app

logger = logging.getLogger("masaad-celery")


def _run_async(coro):
    """Run an async coroutine in a sync Celery task context (new event loop)."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, name="tasks.process_dwg_upload")
def process_dwg_upload(self, file_path: str, estimate_id: str):
    """Parse DWG/DXF file and extract geometry."""
    from app.services.dwg_parser import DWGParserService
    oda_path = os.getenv("ODA_CONVERTER_PATH", "/usr/bin/ODAFileConverter")
    service = DWGParserService(oda_path)

    self.update_state(state="PROGRESS", meta={"step": "Parsing DWG file", "pct": 10})
    try:
        if file_path.lower().endswith(".dwg"):
            upload_dir = os.path.dirname(file_path)
            dxf_path = service.convert_dwg_to_dxf(file_path, upload_dir)
        else:
            dxf_path = file_path

        self.update_state(state="PROGRESS", meta={"step": "Extracting geometry", "pct": 40})
        geometry = service.extract_geometry(dxf_path)

        self.update_state(state="PROGRESS", meta={"step": "Complete", "pct": 100})
        return {"status": "success", "estimate_id": estimate_id, "geometry": geometry}
    except Exception as e:
        logger.error(f"DWG processing failed for estimate {estimate_id}: {e}")
        raise


@celery_app.task(bind=True, name="tasks.run_full_pipeline")
def run_full_pipeline(self, estimate_id: str, user_id: str):
    """
    Run the complete AI estimation pipeline via LangGraph.
    Supports checkpoint/resume: if a previous run died mid-graph,
    the state is loaded from Redis and execution resumes from the last node.
    """
    self.update_state(state="PROGRESS", meta={"step": "Starting pipeline", "pct": 0})

    async def _run():
        try:
            from app.agents.graph_state import GraphState
            from app.agents.estimator_graph import estimator_graph, load_checkpoint
            from app.db import AsyncSessionLocal
            from app.models.orm_models import Estimate, FinancialRates
            from sqlalchemy import select

            # Try to get a Redis client
            redis_client = None
            try:
                import redis.asyncio as aioredis
                redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
                redis_client = aioredis.from_url(redis_url)
            except Exception:
                pass

            # Check for existing checkpoint (crash recovery)
            state = await load_checkpoint(estimate_id, redis_client)

            if state is None:
                # Fresh run — build initial state from DB
                async with AsyncSessionLocal() as session:
                    result = await session.execute(
                        select(Estimate).where(Estimate.id == estimate_id)
                    )
                    estimate = result.scalar_one_or_none()
                    if not estimate:
                        raise ValueError(f"Estimate {estimate_id} not found")

                    # Get LME rate
                    lme_rate = 7.0  # fallback AED/kg
                    try:
                        rates_result = await session.execute(
                            select(FinancialRates).where(
                                FinancialRates.tenant_id == estimate.tenant_id
                            )
                        )
                        rates = rates_result.scalar_one_or_none()
                        if rates and rates.lme_aluminum_usd_mt and rates.usd_aed:
                            lme_rate = float(rates.lme_aluminum_usd_mt) * float(rates.usd_aed) / 1000
                    except Exception:
                        pass

                    state: GraphState = {
                        "estimate_id": estimate_id,
                        "tenant_id": estimate.tenant_id,
                        "user_id": user_id,
                        "current_node": "IngestionNode",
                        "status": "ESTIMATING",
                        "progress_pct": 0,
                        "checkpoint_key": f"ckpt:{estimate_id}",
                        "last_completed_node": "",
                        "hitl_pending": False,
                        "hitl_triage_ids": [],
                        "confidence_score": 1.0,
                        "drawing_paths": [],
                        "spec_text": "",
                        "revision_number": estimate.revision_number or 0,
                        "extracted_openings": [],
                        "catalog_matches": [],
                        "bom_items": [],
                        "cutting_list": [],
                        "pricing_data": {},
                        "ve_suggestions": [],
                        "lme_aed_per_kg": lme_rate,
                        "project_currency": "AED",
                        "is_international": False,
                        "prev_bom_snapshot": estimate.bom_snapshot_json,
                        "variation_order_delta": None,
                        "approval_required": True,
                        "approved_by": None,
                        # Phase 3B / 6B fields
                        "compliance_report": None,
                        "scurve_cashflow": None,
                        "milestone_schedule": None,
                        "yield_report": None,
                        "ve_menu": None,
                        "rfi_log": [],
                        "error": None,
                        "error_node": None,
                    }
            else:
                logger.info(
                    f"[{estimate_id}] Resuming from checkpoint: {state.get('last_completed_node')}"
                )

            # Run the graph
            final_state = await estimator_graph.ainvoke(state)

            # Persist final state to DB
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(Estimate).where(Estimate.id == estimate_id)
                )
                estimate = result.scalar_one_or_none()
                if estimate:
                    estimate.status = final_state.get("status", "REVIEW_REQUIRED")
                    estimate.progress_pct = final_state.get("progress_pct", 100)
                    estimate.state_snapshot = dict(final_state)
                    estimate.bom_output_json = {
                        "items": final_state.get("bom_items", []),
                        "summary": final_state.get("bom_summary", {}),
                    }
                    if final_state.get("bom_items"):
                        estimate.bom_snapshot_json = {
                            "items": final_state.get("bom_items", []),
                            "revision": final_state.get("revision_number", 0),
                            "snapshot_at": datetime.now(timezone.utc).isoformat(),
                        }
                    await session.commit()

            return {"status": "success", "estimate_id": estimate_id}
        except Exception as e:
            logger.error(f"Pipeline failed for estimate {estimate_id}: {e}")
            raise

    try:
        return _run_async(_run())
    except Exception as e:
        logger.error(f"Pipeline task failed: {e}")
        raise


@celery_app.task(bind=True, name="tasks.generate_report")
def generate_report(self, estimate_id: str, report_type: str, tenant_id: str):
    """Generate a PDF report for an estimate."""
    self.update_state(state="PROGRESS", meta={"step": f"Generating {report_type}", "pct": 10})
    try:
        from app.services.report_engine import ReportEngine
        result = _run_async(ReportEngine().generate(estimate_id, report_type, tenant_id))
        self.update_state(state="PROGRESS", meta={"step": "Complete", "pct": 100})
        return result
    except Exception as e:
        logger.error(f"Report generation failed for estimate {estimate_id}: {e}")
        raise


@celery_app.task(bind=True, name="tasks.parse_catalog_pdf")
def parse_catalog_pdf(self, file_path: str, tenant_id: str):
    """
    Extract catalog items from supplier PDF.
    Calls async CatalogPDFParser.parse() via _run_async().
    Returns serializable list of entry dicts (not dataclass instances).
    """
    self.update_state(state="PROGRESS", meta={"step": "Reading catalog PDF", "pct": 10})

    async def _parse():
        from app.services.catalog_pdf_parser import CatalogPDFParser
        with open(file_path, "rb") as f:
            pdf_bytes = f.read()
        entries = await CatalogPDFParser().parse(pdf_bytes, source_name=os.path.basename(file_path))
        # Convert dataclasses to dicts for JSON serialization
        return [
            {k: v for k, v in e.__dict__.items()}
            for e in entries
        ]

    try:
        result = _run_async(_parse())
        self.update_state(state="PROGRESS", meta={"step": "Complete", "pct": 100})
        return {"status": "success", "items": result, "tenant_id": tenant_id}
    except Exception as e:
        logger.error(f"Catalog parsing failed: {e}")
        raise


@celery_app.task(name="tasks.refresh_lme_prices")
def refresh_lme_prices():
    """
    Daily Celery Beat task (08:00 GST) — fetch live LME Aluminum price.
    Sources: metals-api.com → St. Louis Fed FRED API fallback.
    Converts USD/MT → AED/kg using stored USD/AED rate.
    Updates financial_rates for all active tenants.
    """
    async def _refresh():
        import httpx
        from app.db import AsyncSessionLocal
        from app.models.orm_models import FinancialRates
        from sqlalchemy import select

        lme_usd_mt = None

        # Source 1: metals-api.com
        metals_api_key = os.getenv("METALS_API_KEY")
        if metals_api_key:
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.get(
                        "https://metals-api.com/api/latest",
                        params={"access_key": metals_api_key, "base": "USD", "symbols": "ALU"},
                    )
                    data = resp.json()
                    if data.get("success") and data.get("rates", {}).get("ALU"):
                        # metals-api returns per troy oz — convert to USD/MT
                        # ALU in metals-api is USD per metric tonne directly
                        lme_usd_mt = float(data["rates"]["ALU"])
                        logger.info(f"LME from metals-api: {lme_usd_mt} USD/MT")
            except Exception as e:
                logger.warning(f"metals-api fetch failed: {e}")

        # Source 2: St. Louis Fed FRED (ALUM1 = LME Aluminum USD/MT)
        if lme_usd_mt is None:
            fred_api_key = os.getenv("FRED_API_KEY")
            if fred_api_key:
                try:
                    async with httpx.AsyncClient(timeout=10) as client:
                        resp = await client.get(
                            "https://api.stlouisfed.org/fred/series/observations",
                            params={
                                "series_id": "ALUM1",
                                "api_key": fred_api_key,
                                "file_type": "json",
                                "sort_order": "desc",
                                "limit": 1,
                            },
                        )
                        data = resp.json()
                        obs = data.get("observations", [])
                        if obs and obs[0].get("value") not in (".", None):
                            lme_usd_mt = float(obs[0]["value"])
                            logger.info(f"LME from FRED: {lme_usd_mt} USD/MT")
                except Exception as e:
                    logger.warning(f"FRED API fetch failed: {e}")

        if lme_usd_mt is None:
            logger.warning("LME refresh: all sources failed, keeping existing rate")
            return {"status": "no_update"}

        updated = 0
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(FinancialRates))
            all_rates = result.scalars().all()
            for rates in all_rates:
                rates.lme_aluminum_usd_mt = lme_usd_mt
                rates.lme_last_fetched = datetime.now(timezone.utc)
                rates.lme_source = "daily_beat"
                updated += 1
            await session.commit()

        logger.info(f"LME refresh complete: {lme_usd_mt} USD/MT, updated {updated} tenant(s)")
        return {"status": "updated", "lme_usd_mt": lme_usd_mt, "tenants_updated": updated}

    return _run_async(_refresh())

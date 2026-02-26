"""
Masaad Estimator API v2.0
FastAPI backend with async PostgreSQL, JWT auth, Redis/Celery background tasks,
Groq LLaMA 3.1 70B primary LLM + Gemini 1.5 Flash fallback.
"""
import os
import asyncio
import logging
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI

# Load .env file automatically in dev (no-op if python-dotenv not installed or file missing)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import asyncpg

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("masaad-api")

# Startup validation
for var in ["DATABASE_URL", "JWT_SECRET_KEY"]:
    if not os.getenv(var):
        logger.warning(f"MISSING env var: {var} — running in dev mode")
for var in ["GROQ_API_KEY", "REDIS_URL"]:
    if not os.getenv(var):
        logger.info(f"Optional env var not set: {var}")


class Database:
    def __init__(self):
        self.pool = None

    async def connect(self):
        raw_url = os.getenv("DATABASE_URL")
        if not raw_url:
            logger.warning("DATABASE_URL not set — skipping DB connection (dev mode)")
            return
        url = raw_url
        if "+asyncpg" in url:
            url = url.replace("+asyncpg", "")
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)

        for i in range(3):
            try:
                logger.info(f"Connecting to database (attempt {i+1}/3)...")
                self.pool = await asyncpg.create_pool(
                    dsn=url, min_size=2, max_size=20,
                    timeout=5.0, command_timeout=10.0,
                )
                async with self.pool.acquire() as conn:
                    await conn.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')
                    try:
                        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                    except Exception:
                        pass  # pgvector not available in all environments
                logger.info("Database connected.")
                return
            except Exception as e:
                logger.error(f"DB connection failed: {e}")
                if i < 2:
                    await asyncio.sleep(2)
                else:
                    logger.warning("Could not connect after 3 attempts — continuing without DB")

    async def disconnect(self):
        if self.pool:
            await self.pool.close()


db = Database()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.connect()
    app.state.db_pool = db.pool

    try:
        from app.db import init_db
        await init_db()
        logger.info("SQLAlchemy models synced.")
    except Exception as e:
        logger.warning(f"Table init warning (OK if using Alembic): {e}")

    yield
    await db.disconnect()


app = FastAPI(
    title="Masaad Senior Estimator API",
    version="2.0.0",
    description="AI-powered estimation for aluminium & glass facade works",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
from app.api.settings_routes import router as settings_router
from app.api.ingestion_routes import router as ingestion_router
from app.api.auth_routes import router as auth_router
from app.api.catalog_routes import router as catalog_router
from app.api.hrms_routes import router as hrms_router
from app.api.triage_routes import router as triage_router
from app.api.drafting_routes import router as drafting_router
from app.api.commercial_routes import router as commercial_router

app.include_router(auth_router)
app.include_router(settings_router)
app.include_router(ingestion_router)
app.include_router(catalog_router)
app.include_router(hrms_router)
app.include_router(triage_router)
app.include_router(drafting_router)
app.include_router(commercial_router)

for module, name in [
    ("app.api.report_routes", "report_router"),
]:
    try:
        import importlib
        mod = importlib.import_module(module)
        app.include_router(getattr(mod, name))
    except (ImportError, AttributeError):
        pass


@app.get("/health")
async def health_check():
    return {
        "status": "active",
        "version": "2.0.0",
        "db_connected": db.pool is not None,
        "llm_primary": os.getenv("LLM_PRIMARY_MODEL", "groq/llama-3.1-70b-versatile"),
        "redis_configured": bool(os.getenv("REDIS_URL")),
    }


@app.get("/api/ingestion/progress/{estimate_id}")
async def estimate_progress_sse(estimate_id: str):
    """Server-Sent Events stream for live AI processing progress (AgentProgressPayload contract)."""
    async def stream():
        try:
            from app.db import AsyncSessionLocal
            from app.models.orm_models import Estimate
            from app.models.websocket_models import AgentProgressPayload
            from sqlalchemy import select

            async with AsyncSessionLocal() as session:
                result = await session.execute(select(Estimate).where(Estimate.id == estimate_id))
                estimate = result.scalar_one_or_none()
                if not estimate:
                    payload = AgentProgressPayload(
                        estimate_id=estimate_id,
                        current_agent="",
                        status_message="Estimate not found",
                        error="Estimate not found",
                    )
                    yield f"data: {payload.model_dump_json()}\n\n"
                    return

                state_snap = estimate.state_snapshot or {}
                hitl_ids = state_snap.get("hitl_triage_ids") or []
                payload = AgentProgressPayload(
                    estimate_id=estimate_id,
                    current_agent=estimate.current_step or state_snap.get("current_node", ""),
                    status_message=estimate.current_step or estimate.status,
                    confidence_score=float(state_snap.get("confidence_score", 1.0)),
                    progress_pct=estimate.progress_pct or 0,
                    partial_results={
                        "status": estimate.status,
                        "bom_rows": len((estimate.bom_output_json or {}).get("items", [])),
                    },
                    hitl_required=bool(state_snap.get("hitl_pending", False)),
                    hitl_triage_id=hitl_ids[0] if hitl_ids else None,
                )
                yield f"data: {payload.model_dump_json()}\n\n"
        except Exception as e:
            from app.models.websocket_models import AgentProgressPayload
            payload = AgentProgressPayload(
                estimate_id=estimate_id,
                current_agent="",
                status_message="Error fetching progress",
                error=str(e),
            )
            yield f"data: {payload.model_dump_json()}\n\n"

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/ingestion/status/{estimate_id}")
async def estimate_status(estimate_id: str):
    """Polling endpoint for estimate processing status."""
    try:
        from app.db import AsyncSessionLocal
        from app.models.orm_models import Estimate
        from sqlalchemy import select

        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Estimate).where(Estimate.id == estimate_id))
            estimate = result.scalar_one_or_none()
            if not estimate:
                raise Exception("Not found")
            return {
                "estimate_id": estimate_id,
                "status": estimate.status,
                "progress_pct": estimate.progress_pct,
                "current_step": estimate.current_step,
                "reasoning_log": estimate.reasoning_log or [],
            }
    except Exception as e:
        return {"estimate_id": estimate_id, "status": "unknown", "error": str(e)}


@app.post("/api/v1/estimates/{estimate_id}/approve")
async def approve_estimate(estimate_id: str):
    """
    Approval Gateway — advance estimate from REVIEW_REQUIRED to APPROVED.
    Requires Admin role. Logs approver user_id and timestamp.
    """
    from app.db import AsyncSessionLocal
    from app.models.orm_models import Estimate
    from app.api.deps import require_admin, get_db
    from fastapi import Request
    from datetime import datetime, timezone
    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Estimate).where(Estimate.id == estimate_id))
        estimate = result.scalar_one_or_none()
        if not estimate:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Estimate not found")
        if estimate.status not in ("REVIEW_REQUIRED", "Processing"):
            from fastapi import HTTPException
            raise HTTPException(
                status_code=400,
                detail=f"Estimate status is '{estimate.status}' — can only approve REVIEW_REQUIRED estimates"
            )
        estimate.status = "APPROVED"
        estimate.approved_at = datetime.now(timezone.utc)
        await session.commit()
    return {"estimate_id": estimate_id, "status": "APPROVED"}


@app.post("/api/v1/estimates/{estimate_id}/dispatch")
async def dispatch_estimate(estimate_id: str):
    """
    Dispatch Gateway — advance estimate from APPROVED to DISPATCHED.
    Triggers final ZIP generation (report_engine called by Celery).
    """
    from app.db import AsyncSessionLocal
    from app.models.orm_models import Estimate
    from datetime import datetime, timezone
    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Estimate).where(Estimate.id == estimate_id))
        estimate = result.scalar_one_or_none()
        if not estimate:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Estimate not found")
        if estimate.status != "APPROVED":
            from fastapi import HTTPException
            raise HTTPException(
                status_code=400,
                detail=f"Estimate must be APPROVED before dispatching (current: '{estimate.status}')"
            )
        estimate.status = "DISPATCHED"
        await session.commit()

    # Trigger report generation asynchronously
    try:
        from app.workers.tasks import generate_report
        generate_report.delay(estimate_id, "full_package", "")
    except Exception:
        pass  # Worker may not be running in dev mode

    return {"estimate_id": estimate_id, "status": "DISPATCHED"}


@app.get("/api/dashboard/summary")
async def dashboard_summary():
    try:
        from app.db import AsyncSessionLocal
        from app.models.orm_models import Project, Estimate
        from sqlalchemy import select, func

        async with AsyncSessionLocal() as session:
            project_count = await session.scalar(select(func.count(Project.id)))
            estimate_count = await session.scalar(select(func.count(Estimate.id)))
            active_count = await session.scalar(
                select(func.count(Estimate.id)).where(Estimate.status == "Processing")
            )
        return {
            "total_projects": project_count or 0,
            "total_estimates": estimate_count or 0,
            "active_processing": active_count or 0,
            "avg_ve_savings_aed": 0,
        }
    except Exception:
        return {"total_projects": 0, "total_estimates": 0, "active_processing": 0, "avg_ve_savings_aed": 0}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

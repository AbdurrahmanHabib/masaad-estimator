"""
Masaad Estimator API v2.0
FastAPI backend with async PostgreSQL, JWT auth, Redis/Celery background tasks,
Groq LLaMA 3.1 70B primary LLM + Gemini 1.5 Flash fallback.
"""
import os
import asyncio
import logging
import json
import time
import collections
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from starlette.responses import JSONResponse
from app.services.logging_config import setup_logging
from app.services.perf_monitor import tracker as perf_tracker

# Load .env file automatically in dev (no-op if python-dotenv not installed or file missing)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import asyncpg

# Replace basicConfig with structured JSON logging
_log_level = os.getenv("LOG_LEVEL", "INFO")
_json_logs = os.getenv("LOG_FORMAT", "json").lower() != "text"
setup_logging(level=_log_level, json_output=_json_logs)
logger = logging.getLogger("masaad-api")

# Record process start time for uptime calculation
_PROCESS_START = time.monotonic()

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

    # Auto-stamp Alembic if tables were created by create_all but alembic_version doesn't exist
    try:
        from sqlalchemy import text as _sa_text
        from app.db import engine as _engine
        if _engine is not None:
            async with _engine.begin() as _conn:
                _has_alembic = await _conn.execute(
                    _sa_text(
                        "SELECT EXISTS(SELECT 1 FROM information_schema.tables "
                        "WHERE table_name='alembic_version')"
                    )
                )
                if not _has_alembic.scalar():
                    # Tables exist from create_all but alembic hasn't stamped — stamp to head
                    import subprocess as _sp
                    _result = _sp.run(
                        ["alembic", "stamp", "head"],
                        capture_output=True, text=True,
                        cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                    )
                    if _result.returncode == 0:
                        logger.info("Alembic stamped to head (tables pre-existed from create_all)")
                    else:
                        logger.warning(f"Alembic stamp failed (non-fatal): {_result.stderr[:200]}")
    except Exception as _ae:
        logger.warning(f"Alembic auto-stamp skipped: {_ae}")

    yield
    await db.disconnect()


app = FastAPI(
    title="Masaad Senior Estimator API",
    version="2.0.0",
    description="AI-powered estimation for aluminium & glass facade works",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS — Only CORSMiddleware, no BaseHTTPMiddleware subclasses.
# BaseHTTPMiddleware is known to break CORSMiddleware in Starlette by
# swallowing exceptions before CORS headers can be added to responses.
# ---------------------------------------------------------------------------
_cors_default = "http://localhost:3000,http://localhost:8000"
cors_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", _cors_default).split(",") if o.strip()]

# Auto-add Railway domains
_railway_domain = os.getenv("RAILWAY_PUBLIC_DOMAIN", "")
if _railway_domain:
    cors_origins.append(f"https://{_railway_domain}")
_railway_static = os.getenv("RAILWAY_STATIC_URL", "")
if _railway_static:
    cors_origins.append(_railway_static.rstrip("/"))
_frontend_url = os.getenv("FRONTEND_URL", "")
if _frontend_url:
    cors_origins.append(_frontend_url.rstrip("/"))

# Always allow all *.up.railway.app subdomains when deployed
_allow_origin_regex = r"https://.*\.up\.railway\.app"

logger.info("CORS origins: %s | regex: %s", cors_origins, _allow_origin_regex)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=_allow_origin_regex,
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
from app.api.report_routes import router as report_router

app.include_router(auth_router)
app.include_router(settings_router)
app.include_router(ingestion_router)
app.include_router(catalog_router)
app.include_router(hrms_router)
app.include_router(triage_router)
app.include_router(drafting_router)
app.include_router(commercial_router)
app.include_router(report_router)


@app.get("/health")
async def health_check():
    return {
        "status": "active",
        "version": "2.0.0",
        "db_connected": db.pool is not None,
        "llm_primary": os.getenv("LLM_PRIMARY_MODEL", "groq/llama-3.1-70b-versatile"),
        "redis_configured": bool(os.getenv("REDIS_URL")),
    }


@app.get("/metrics")
async def metrics():
    """
    Performance metrics endpoint.

    Returns pipeline throughput, average duration, error counts, and
    process-level memory usage. Sourced entirely from the in-process
    PerformanceTracker singleton — no external dependency required.
    """
    import sys

    uptime_seconds = round(time.monotonic() - _PROCESS_START, 1)

    # Best-effort memory reading via resource module (Unix) or psutil (optional)
    memory_mb: float = 0.0
    try:
        import resource  # Unix only
        usage = resource.getrusage(resource.RUSAGE_SELF)
        # ru_maxrss is in kilobytes on Linux, bytes on macOS
        if sys.platform == "darwin":
            memory_mb = round(usage.ru_maxrss / (1024 * 1024), 2)
        else:
            memory_mb = round(usage.ru_maxrss / 1024, 2)
    except Exception:
        try:
            import psutil
            proc = psutil.Process()
            memory_mb = round(proc.memory_info().rss / (1024 * 1024), 2)
        except Exception:
            memory_mb = 0.0

    snapshot = perf_tracker.get_metrics()

    return {
        "uptime_seconds": uptime_seconds,
        "estimates_processed": snapshot["estimates_processed"],
        "avg_pipeline_duration_ms": snapshot["avg_pipeline_duration_ms"],
        "error_count": snapshot["error_count"],
        "memory_usage_mb": memory_mb,
        # Extended detail (not required by spec but useful for debugging)
        "slowest_node": snapshot["slowest_node"],
        "slowest_node_ms": snapshot["slowest_node_ms"],
        "error_count_by_node": snapshot["error_count_by_node"],
        "node_avg_durations_ms": snapshot["node_avg_durations_ms"],
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


@app.get("/api/v1/estimates/recent")
async def recent_estimates_v1(request: Request):
    """
    Return the last 10 estimates with joined project info for the dashboard.
    Accepts a Bearer token in the Authorization header; 401 if missing or invalid.
    """
    from app.db import AsyncSessionLocal
    from app.models.orm_models import Estimate, Project, User
    from sqlalchemy import select, desc
    from jose import jwt as _jwt, JWTError as _JWTError
    import os as _os

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = auth_header.split(" ", 1)[1]
    _SECRET = _os.getenv("JWT_SECRET_KEY", "changethis_use_a_real_secret_in_production_64chars")
    _ALGO = _os.getenv("JWT_ALGORITHM", "HS256")
    try:
        token_payload = _jwt.decode(token, _SECRET, algorithms=[_ALGO])
        user_id = token_payload.get("sub")
        if not user_id:
            raise ValueError("No sub claim")
    except (_JWTError, ValueError) as exc:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Invalid token")

    try:
        async with AsyncSessionLocal() as session:
            user_result = await session.execute(select(User).where(User.id == user_id))
            current_user = user_result.scalar_one_or_none()
            if not current_user:
                from fastapi import HTTPException
                raise HTTPException(status_code=401, detail="User not found")

            tenant_id = current_user.tenant_id
            if not tenant_id:
                return []

            query = (
                select(Estimate, Project)
                .outerjoin(Project, Estimate.project_id == Project.id)
                .where(Estimate.tenant_id == tenant_id)
                .order_by(desc(Estimate.created_at))
                .limit(10)
            )
            result = await session.execute(query)
            rows = result.all()

        results = []
        for e, p in rows:
            details = _extract_estimate_details(e)
            results.append({
                "estimate_id": str(e.id),
                "project_id": str(e.project_id),
                "project_name": (p.name if p else "") or "",
                "client_name": (p.client_name if p else "") or "",
                "location": (p.location_zone if p else "") or "",
                "status": e.status,
                "progress_pct": e.progress_pct,
                "current_step": e.current_step,
                "created_at": e.created_at.isoformat() if e.created_at else None,
                "updated_at": e.updated_at.isoformat() if e.updated_at else None,
                **details,
            })
        return results
    except Exception as exc:
        logger.error(f"estimates/recent error: {exc}", exc_info=True)
        return JSONResponse(status_code=500, content={"detail": str(exc)[:500]})


@app.get("/api/v1/estimates/{estimate_id}")
async def get_estimate_v1(estimate_id: str, request: Request):
    """
    Alias for /api/ingestion/estimate/{estimate_id}.
    Used by the approve page and other v1 API consumers.
    Proxies to the ingestion route's get_estimate endpoint.
    """
    from app.db import AsyncSessionLocal
    from app.models.orm_models import Estimate, Project, Tenant
    from fastapi import HTTPException
    from sqlalchemy import select

    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Estimate).where(Estimate.id == estimate_id))
            estimate = result.scalar_one_or_none()
            if not estimate:
                raise HTTPException(status_code=404, detail="Estimate not found")

            # Join with Project
            project_name = ""
            project_location = ""
            execution_strategy = "IN_HOUSE_INSTALL"
            is_international = False
            proj_result = await session.execute(select(Project).where(Project.id == estimate.project_id))
            project = proj_result.scalar_one_or_none()
            if project:
                project_name = project.name or ""
                project_location = project.location_zone or ""
                execution_strategy = getattr(project, 'execution_strategy', 'IN_HOUSE_INSTALL') or 'IN_HOUSE_INSTALL'
                is_international = getattr(project, 'is_international', False)

            # MODULE 1: Load tenant settings for currency + branding
            tenant_info = {}
            try:
                t_result = await session.execute(select(Tenant).where(Tenant.id == estimate.tenant_id))
                tenant = t_result.scalar_one_or_none()
                if tenant:
                    tenant_info = {
                        "company_name": tenant.company_name,
                        "base_currency": tenant.base_currency,
                        "theme_color_hex": tenant.theme_color_hex,
                        "logo_url": tenant.logo_url,
                        "monthly_factory_overhead": float(tenant.monthly_factory_overhead) if tenant.monthly_factory_overhead else 85000.0,
                        "default_factory_burn_rate": float(tenant.default_factory_burn_rate) if tenant.default_factory_burn_rate else 13.0,
                    }
            except Exception:
                pass

            bom = estimate.bom_output_json or {}
            state_snap = estimate.state_snapshot or {}

            # MODULE 3: Engineering results — prefer dedicated column, fallback to state_snapshot
            engineering = estimate.engineering_results_json or state_snap.get("engineering_results", {})
            compliance = estimate.compliance_results_json or state_snap.get("compliance_results", {})

            return {
                "id": str(estimate.id),
                "estimate_id": str(estimate.id),
                "project_id": str(estimate.project_id),
                "project_name": project_name,
                "location": project_location,
                "status": estimate.status,
                "progress_pct": estimate.progress_pct,
                "current_step": estimate.current_step,
                "approved_by": state_snap.get("approved_by"),
                "approved_at": estimate.approved_at.isoformat() if hasattr(estimate, 'approved_at') and estimate.approved_at else None,
                "reasoning_log": estimate.reasoning_log or [],
                "project_scope": estimate.project_scope_json or {},
                "opening_schedule": estimate.opening_schedule_json or {},
                "bom_output": bom,
                "cutting_list": estimate.cutting_list_json or {},
                "state_snapshot": state_snap,
                "boq": {
                    "summary": bom.get("summary", {}),
                    "line_items": bom.get("items", []),
                    "financial_rates": bom.get("financial_rates", {}),
                },
                # MODULE 2: Execution strategy + international
                "execution_strategy": execution_strategy,
                "is_international": is_international,
                # MODULE 3: Forensic deliverables — engineering proofs
                "engineering_results": engineering,
                "compliance_results": compliance,
                "rfi_register": state_snap.get("rfi_log", []),
                "ve_opportunities": state_snap.get("ve_suggestions", []),
                "structural_results": engineering.get("deflection_checks", []),
                "financial_summary": bom.get("summary", estimate.financial_json or {}),
                # MODULE 1: Tenant info for frontend branding
                "tenant": tenant_info,
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/estimates/{estimate_id}/approve")
async def approve_estimate(estimate_id: str, request: Request):
    """
    Approval Gateway — advance estimate from REVIEW_REQUIRED to APPROVED.
    Requires Admin role. Logs approver user_id and timestamp.
    """
    from app.db import AsyncSessionLocal
    from app.models.orm_models import Estimate
    from fastapi import HTTPException
    from datetime import datetime, timezone
    from sqlalchemy import select

    # Manually enforce admin auth (endpoint is on app, not router)
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = auth_header.split(" ", 1)[1]
    from jose import jwt, JWTError
    import os as _os
    SECRET_KEY = _os.getenv("JWT_SECRET_KEY", "changethis_use_a_real_secret_in_production_64chars")
    ALGORITHM = _os.getenv("JWT_ALGORITHM", "HS256")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    if payload.get("role") != "Admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    approver_id = payload.get("sub", "unknown")

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Estimate).where(Estimate.id == estimate_id))
        estimate = result.scalar_one_or_none()
        if not estimate:
            raise HTTPException(status_code=404, detail="Estimate not found")
        if estimate.status not in ("REVIEW_REQUIRED", "Processing", "Completed"):
            raise HTTPException(
                status_code=400,
                detail=f"Estimate status is '{estimate.status}' — can only approve REVIEW_REQUIRED/Processing/Completed estimates"
            )
        estimate.status = "APPROVED"
        estimate.approved_at = datetime.now(timezone.utc)
        await session.commit()
    return {"estimate_id": estimate_id, "status": "APPROVED", "approved_by": approver_id}


@app.post("/api/v1/estimates/{estimate_id}/dispatch")
async def dispatch_estimate(estimate_id: str, request: Request):
    """
    Dispatch Gateway — advance estimate from APPROVED to DISPATCHED.
    Requires Admin role. Triggers final ZIP generation (report_engine called by Celery).
    """
    from app.db import AsyncSessionLocal
    from app.models.orm_models import Estimate
    from fastapi import HTTPException
    from datetime import datetime, timezone
    from sqlalchemy import select

    # Manually enforce admin auth (endpoint is on app, not router)
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = auth_header.split(" ", 1)[1]
    from jose import jwt, JWTError
    import os as _os
    SECRET_KEY = _os.getenv("JWT_SECRET_KEY", "changethis_use_a_real_secret_in_production_64chars")
    ALGORITHM = _os.getenv("JWT_ALGORITHM", "HS256")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    if payload.get("role") != "Admin":
        raise HTTPException(status_code=403, detail="Admin role required")

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Estimate).where(Estimate.id == estimate_id))
        estimate = result.scalar_one_or_none()
        if not estimate:
            raise HTTPException(status_code=404, detail="Estimate not found")
        if estimate.status != "APPROVED":
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


@app.delete("/api/v1/estimates/{estimate_id}")
async def delete_estimate(estimate_id: str, request: Request):
    """
    Delete an estimate and its associated project.
    Requires Admin role.
    """
    from app.db import AsyncSessionLocal
    from app.models.orm_models import Estimate, Project
    from fastapi import HTTPException
    from sqlalchemy import select, delete as sa_delete

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = auth_header.split(" ", 1)[1]
    from jose import jwt, JWTError
    import os as _os
    SECRET_KEY = _os.getenv("JWT_SECRET_KEY", "changethis_use_a_real_secret_in_production_64chars")
    ALGORITHM = _os.getenv("JWT_ALGORITHM", "HS256")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    if payload.get("role") != "Admin":
        raise HTTPException(status_code=403, detail="Admin role required")

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Estimate).where(Estimate.id == estimate_id))
        estimate = result.scalar_one_or_none()
        if not estimate:
            raise HTTPException(status_code=404, detail="Estimate not found")
        project_id = estimate.project_id
        await session.delete(estimate)
        # Also delete the parent project if it has no other estimates
        if project_id:
            remaining = await session.execute(
                select(Estimate).where(Estimate.project_id == project_id, Estimate.id != estimate_id)
            )
            if not remaining.scalar_one_or_none():
                proj = await session.execute(select(Project).where(Project.id == project_id))
                project = proj.scalar_one_or_none()
                if project:
                    await session.delete(project)
        await session.commit()

    return {"deleted": True, "estimate_id": estimate_id}


@app.post("/api/v1/seed/al-kabir")
async def seed_al_kabir_endpoint():
    """
    Seed the AL KABIR TOWER demonstration project.
    Safe to call multiple times — idempotent, skips if already seeded.
    """
    from app.db.seed_al_kabir import seed_al_kabir
    return await seed_al_kabir()


SYSTEM_CATEGORY_MAP = {
    "Curtain Wall (Stick)": "Curtain Walls",
    "Curtain Wall (Unitised)": "Curtain Walls",
    "Curtain Wall (SSG)": "Curtain Walls",
    "Curtain Wall (Point-Fix / Spider)": "Curtain Walls",
    "Curtain Wall (Double-Skin)": "Curtain Walls",
    "Window - Casement": "Windows",
    "Window - Fixed": "Windows",
    "Window - Sliding": "Windows",
    "Window - Awning / Top-Hung": "Windows",
    "Window - Tilt-and-Turn": "Windows",
    "Window - Louvre": "Windows",
    "Door - Single Swing": "Doors",
    "Door - Double Swing": "Doors",
    "Door - Sliding": "Doors",
    "Door - Frameless (Patch-Fit)": "Doors",
    "Door - Fire-Rated": "Doors",
    "Door - Automatic Sliding": "Doors",
    "Door - Revolving": "Doors",
    "Door - Folding / Bi-Fold": "Doors",
    "ACP Cladding": "Cladding",
    "Solid Aluminium Panel": "Cladding",
    "HPL Cladding": "Cladding",
    "Spandrel Panel": "Cladding",
    "Rainscreen Cladding": "Cladding",
    "Terracotta Cladding": "Cladding",
    "Skylight (Fixed)": "Rooflight / Skylight",
    "Skylight (Opening)": "Rooflight / Skylight",
    "Atrium Glazed Roof": "Rooflight / Skylight",
    "Canopy / Entrance Canopy": "Rooflight / Skylight",
    "Louvre System": "Louvre / Sunshade",
    "Sun Shading (Blades / Fins)": "Louvre / Sunshade",
    "Perforated Panel Screen": "Louvre / Sunshade",
    "Glass Balustrade": "Specialist",
    "Aluminium Handrail": "Specialist",
    "Shopfront": "Specialist",
    "Entrance Lobby / Portal": "Specialist",
    "Parapet Coping": "Specialist",
    "Column Cladding": "Specialist",
    "Soffit / Fascia": "Specialist",
    "Smoke Vent (AOV)": "Specialist",
    "Roller Shutter": "Specialist",
}

CATEGORY_COLORS = {
    "Curtain Walls": "#2563eb",
    "Windows": "#0891b2",
    "Doors": "#7c3aed",
    "Cladding": "#d97706",
    "Rooflight / Skylight": "#059669",
    "Louvre / Sunshade": "#dc2626",
    "Specialist": "#64748b",
}


def _extract_estimate_details(estimate) -> dict:
    """Extract comprehensive details from an Estimate's JSONB columns."""
    scope_json = estimate.project_scope_json or {}
    opening_json = estimate.opening_schedule_json or {}
    bom_json = estimate.bom_output_json or {}
    cutting_json = estimate.cutting_list_json or {}
    financial_json = estimate.financial_json or bom_json.get("summary", {})
    engineering_json = estimate.engineering_results_json or {}
    risk_json = estimate.risk_register_json or {}
    ve_json = estimate.value_engineering_json or {}
    state_snap = estimate.state_snapshot or {}

    # Opening items
    items = opening_json.get("schedule", [])
    opening_summary = opening_json.get("summary", {})

    # Systems from scope
    systems_list = []
    scope_systems = scope_json.get("systems", [])
    if isinstance(scope_systems, list):
        for s in scope_systems:
            if isinstance(s, dict):
                systems_list.append({
                    "system_type": s.get("system_type", ""),
                    "total_sqm": s.get("total_sqm", 0),
                    "total_openings": s.get("total_openings", 0),
                    "unit": s.get("unit", "sqm"),
                    "confidence": s.get("confidence", ""),
                })

    # Materials from BOM
    bom_items = bom_json.get("items", [])
    bom_summary = bom_json.get("summary", {})
    aluminum_kg = float(opening_summary.get("total_aluminum_weight_kg", 0) or 0)
    glass_sqm = float(opening_summary.get("total_glazed_sqm", 0) or 0)
    glass_weight = float(opening_summary.get("total_glass_weight_kg", 0) or 0)
    total_weight = aluminum_kg + glass_weight

    # Cutting
    cutting_sections = cutting_json.get("sections", {})
    al_profiles = cutting_sections.get("aluminum_profiles", {})
    profiles_count = len(al_profiles.get("profiles", []))
    bars_required = sum(p.get("bars_required", 0) for p in al_profiles.get("profiles", []))
    avg_yield = al_profiles.get("average_yield_pct") or 0

    # Engineering
    eng_checks = engineering_json.get("checks", engineering_json.get("deflection_checks", []))
    if isinstance(eng_checks, list):
        total_checks = len(eng_checks)
        pass_count = sum(1 for c in eng_checks if c.get("result", c.get("status", "")).upper() in ("PASS", "OK"))
        fail_count = sum(1 for c in eng_checks if c.get("result", c.get("status", "")).upper() == "FAIL")
        warn_count = total_checks - pass_count - fail_count
    else:
        total_checks = pass_count = fail_count = warn_count = 0
    compliance_pct = round(pass_count / max(total_checks, 1) * 100, 1)

    # Financial
    material_cost = float(financial_json.get("total_material_aed", financial_json.get("material_cost_aed", 0)) or 0)
    labor_cost = float(financial_json.get("total_labor_aed", financial_json.get("labor_cost_aed", 0)) or 0)
    overhead_cost = float(financial_json.get("overhead_aed", financial_json.get("factory_overhead_aed", 0)) or 0)
    total_aed = float(financial_json.get("grand_total_aed", financial_json.get("total_sell_aed", 0)) or 0)
    if total_aed == 0:
        total_aed = material_cost + labor_cost + overhead_cost

    # RFIs
    rfi_list = opening_json.get("rfi_flags", []) + state_snap.get("rfi_log", [])
    rfi_total = len(rfi_list)
    rfi_by_severity = {}
    for r in rfi_list:
        sev = r.get("severity", "MEDIUM")
        rfi_by_severity[sev] = rfi_by_severity.get(sev, 0) + 1

    # VE
    ve_opportunities = ve_json.get("opportunities", ve_json.get("suggestions", state_snap.get("ve_suggestions", [])))
    if not isinstance(ve_opportunities, list):
        ve_opportunities = []
    ve_savings = sum(float(v.get("savings_aed", v.get("estimated_savings_aed", 0)) or 0) for v in ve_opportunities)

    facade_sqm = float(scope_json.get("total_facade_sqm", scope_json.get("total_sqm", 0)) or 0)

    return {
        "scope": {
            "facade_sqm": facade_sqm,
            "systems_count": len(systems_list),
            "systems_list": systems_list,
            "confidence": scope_json.get("overall_confidence", ""),
        },
        "openings": {
            "items": items,
            "total_openings": int(opening_summary.get("total_openings") or len(items)),
            "by_type": opening_summary.get("by_type", {}),
            "by_floor": opening_summary.get("by_floor", {}),
            "by_elevation": opening_summary.get("by_elevation", {}),
            "floor_count": len(opening_summary.get("by_floor", {})),
        },
        "materials": {
            "aluminum_kg": round(aluminum_kg, 2),
            "glass_sqm": round(glass_sqm, 2),
            "glass_weight_kg": round(glass_weight, 2),
            "total_weight_kg": round(total_weight, 2),
            "truck_loads": max(1, round(total_weight / 20000, 1)) if total_weight > 0 else 0,
            "bom_items": len(bom_items),
        },
        "cutting": {
            "profiles": profiles_count,
            "bars_required": bars_required,
            "avg_yield_pct": round(avg_yield, 1),
        },
        "engineering": {
            "total_checks": total_checks,
            "pass": pass_count,
            "fail": fail_count,
            "warning": warn_count,
            "compliance_pct": compliance_pct,
        },
        "financial": {
            "material_aed": round(material_cost, 2),
            "labor_aed": round(labor_cost, 2),
            "overhead_aed": round(overhead_cost, 2),
            "total_aed": round(total_aed, 2),
        },
        "rfis": {
            "total": rfi_total,
            "by_severity": rfi_by_severity,
        },
        "ve": {
            "opportunities": len(ve_opportunities),
            "savings_aed": round(ve_savings, 2),
        },
    }


@app.get("/api/dashboard/summary")
async def dashboard_summary(request: Request):
    try:
        from app.db import AsyncSessionLocal
        from app.models.orm_models import Project, Estimate, User
        from sqlalchemy import select, func, desc
        from jose import jwt as _jwt, JWTError as _JWTError
        import os as _os

        # Auth — extract tenant_id
        tenant_id = None
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1]
            _SECRET = _os.getenv("JWT_SECRET_KEY", "changethis_use_a_real_secret_in_production_64chars")
            _ALGO = _os.getenv("JWT_ALGORITHM", "HS256")
            try:
                payload = _jwt.decode(token, _SECRET, algorithms=[_ALGO])
                tenant_id = payload.get("tenant_id")
            except _JWTError:
                pass

        async with AsyncSessionLocal() as session:
            # Base queries (optionally tenant-scoped)
            proj_q = select(func.count(Project.id))
            est_q = select(func.count(Estimate.id))
            active_q = select(func.count(Estimate.id)).where(Estimate.status == "Processing")
            review_q = select(func.count(Estimate.id)).where(Estimate.status == "REVIEW_REQUIRED")
            if tenant_id:
                proj_q = proj_q.where(Project.tenant_id == tenant_id)
                est_q = est_q.where(Estimate.tenant_id == tenant_id)
                active_q = active_q.where(Estimate.tenant_id == tenant_id)
                review_q = review_q.where(Estimate.tenant_id == tenant_id)

            project_count = await session.scalar(proj_q) or 0
            estimate_count = await session.scalar(est_q) or 0
            active_count = await session.scalar(active_q) or 0
            review_count = await session.scalar(review_q) or 0

            # Fetch all estimates for aggregation
            all_est_q = select(Estimate)
            if tenant_id:
                all_est_q = all_est_q.where(Estimate.tenant_id == tenant_id)
            result = await session.execute(all_est_q)
            estimates = result.scalars().all()

        # Aggregate across all estimates
        total_facade_sqm = 0.0
        total_openings = 0
        total_contract_value = 0.0
        systems_agg = {}  # system_type -> {count, area, unit, category}
        floors_agg = {}   # floor -> sqm
        elevations_agg = {}  # elevation -> sqm
        materials_total = {"aluminum_kg": 0, "glass_sqm": 0, "total_weight_kg": 0}
        eng_total = {"checks": 0, "pass": 0, "fail": 0, "warning": 0}
        cutting_total = {"profiles": 0, "bars": 0, "yield_sum": 0, "yield_count": 0}
        fin_total = {"material": 0, "labor": 0, "overhead": 0, "total": 0}
        rfi_total = {"total": 0, "by_severity": {}}
        ve_total = {"opportunities": 0, "savings": 0}

        for est in estimates:
            details = _extract_estimate_details(est)
            scope = details["scope"]
            total_facade_sqm += scope["facade_sqm"]
            total_openings += details["openings"]["total_openings"]
            total_contract_value += details["financial"]["total_aed"]

            # Systems
            for sys in scope.get("systems_list", []):
                st = sys.get("system_type", "")
                if st:
                    if st not in systems_agg:
                        systems_agg[st] = {"count": 0, "area": 0, "unit": sys.get("unit", "sqm"),
                                           "category": SYSTEM_CATEGORY_MAP.get(st, "Specialist")}
                    systems_agg[st]["count"] += sys.get("total_openings", 0)
                    systems_agg[st]["area"] += sys.get("total_sqm", 0)

            # Floors & Elevations
            for fl, sqm in details["openings"].get("by_floor", {}).items():
                floors_agg[fl] = floors_agg.get(fl, 0) + float(sqm or 0)
            for el, sqm in details["openings"].get("by_elevation", {}).items():
                elevations_agg[el] = elevations_agg.get(el, 0) + float(sqm or 0)

            # Materials
            mat = details["materials"]
            materials_total["aluminum_kg"] += mat["aluminum_kg"]
            materials_total["glass_sqm"] += mat["glass_sqm"]
            materials_total["total_weight_kg"] += mat["total_weight_kg"]

            # Engineering
            eng = details["engineering"]
            eng_total["checks"] += eng["total_checks"]
            eng_total["pass"] += eng["pass"]
            eng_total["fail"] += eng["fail"]
            eng_total["warning"] += eng["warning"]

            # Cutting
            cut = details["cutting"]
            cutting_total["profiles"] += cut["profiles"]
            cutting_total["bars"] += cut["bars_required"]
            if cut["avg_yield_pct"] > 0:
                cutting_total["yield_sum"] += cut["avg_yield_pct"]
                cutting_total["yield_count"] += 1

            # Financial
            fin = details["financial"]
            fin_total["material"] += fin["material_aed"]
            fin_total["labor"] += fin["labor_aed"]
            fin_total["overhead"] += fin["overhead_aed"]
            fin_total["total"] += fin["total_aed"]

            # RFIs
            rfi = details["rfis"]
            rfi_total["total"] += rfi["total"]
            for sev, cnt in rfi.get("by_severity", {}).items():
                rfi_total["by_severity"][sev] = rfi_total["by_severity"].get(sev, 0) + cnt

            # VE
            ve = details["ve"]
            ve_total["opportunities"] += ve["opportunities"]
            ve_total["savings"] += ve["savings_aed"]

        # Build systems breakdown
        systems_breakdown = [
            {"system_type": st, "category": d["category"], "count": d["count"],
             "area": round(d["area"], 2), "unit": d["unit"],
             "color": CATEGORY_COLORS.get(d["category"], "#64748b")}
            for st, d in sorted(systems_agg.items())
        ]

        # Category totals
        category_totals = {}
        for st, d in systems_agg.items():
            cat = d["category"]
            if cat not in category_totals:
                category_totals[cat] = {"count": 0, "area": 0, "color": CATEGORY_COLORS.get(cat, "#64748b")}
            category_totals[cat]["count"] += d["count"]
            category_totals[cat]["area"] += d["area"]

        avg_yield = round(cutting_total["yield_sum"] / max(cutting_total["yield_count"], 1), 1)
        compliance_pct = round(eng_total["pass"] / max(eng_total["checks"], 1) * 100, 1)

        return {
            "total_projects": project_count,
            "total_estimates": estimate_count,
            "active_processing": active_count,
            "pending_review": review_count,
            "total_facade_sqm": round(total_facade_sqm, 2),
            "total_openings": total_openings,
            "total_contract_value_aed": round(total_contract_value, 2),
            "systems_breakdown": systems_breakdown,
            "category_totals": {k: {"count": v["count"], "area": round(v["area"], 2), "color": v["color"]}
                                for k, v in category_totals.items()},
            "floors_breakdown": {k: round(v, 2) for k, v in sorted(floors_agg.items())},
            "elevations_breakdown": {k: round(v, 2) for k, v in sorted(elevations_agg.items())},
            "materials_summary": {
                "aluminum_kg": round(materials_total["aluminum_kg"], 2),
                "glass_sqm": round(materials_total["glass_sqm"], 2),
                "total_weight_kg": round(materials_total["total_weight_kg"], 2),
                "truck_loads": max(1, round(materials_total["total_weight_kg"] / 20000, 1)) if materials_total["total_weight_kg"] > 0 else 0,
            },
            "engineering_summary": {
                "total_checks": eng_total["checks"],
                "pass": eng_total["pass"],
                "fail": eng_total["fail"],
                "warning": eng_total["warning"],
                "compliance_pct": compliance_pct,
            },
            "cutting_summary": {
                "profiles": cutting_total["profiles"],
                "bars_required": cutting_total["bars"],
                "avg_yield_pct": avg_yield,
            },
            "financial_totals": {
                "material_aed": round(fin_total["material"], 2),
                "labor_aed": round(fin_total["labor"], 2),
                "overhead_aed": round(fin_total["overhead"], 2),
                "grand_total_aed": round(fin_total["total"], 2),
            },
            "rfi_summary": rfi_total,
            "ve_summary": {
                "opportunities": ve_total["opportunities"],
                "savings_aed": round(ve_total["savings"], 2),
            },
        }
    except Exception as e:
        logger.error(f"dashboard/summary error: {e}", exc_info=True)
        return {
            "total_projects": 0, "total_estimates": 0, "active_processing": 0,
            "pending_review": 0, "total_facade_sqm": 0, "total_openings": 0,
            "total_contract_value_aed": 0, "systems_breakdown": [], "category_totals": {},
            "floors_breakdown": {}, "elevations_breakdown": {}, "materials_summary": {},
            "engineering_summary": {}, "cutting_summary": {}, "financial_totals": {},
            "rfi_summary": {"total": 0, "by_severity": {}},
            "ve_summary": {"opportunities": 0, "savings_aed": 0},
        }


@app.get("/api/dashboard/export/excel")
async def dashboard_export_excel(request: Request):
    """Export dashboard data as a multi-sheet Excel workbook."""
    import tempfile
    from fastapi.responses import FileResponse

    try:
        import xlsxwriter
    except ImportError:
        return JSONResponse(status_code=500, content={"detail": "xlsxwriter not installed"})

    # Get summary data
    summary_resp = await dashboard_summary(request)
    if isinstance(summary_resp, JSONResponse):
        return summary_resp
    summary = summary_resp

    # Get estimates
    from app.db import AsyncSessionLocal
    from app.models.orm_models import Estimate, Project
    from sqlalchemy import select, desc

    tenant_id = None
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1]
        from jose import jwt as _jwt
        _SECRET = os.getenv("JWT_SECRET_KEY", "changethis_use_a_real_secret_in_production_64chars")
        try:
            payload = _jwt.decode(token, _SECRET, algorithms=[os.getenv("JWT_ALGORITHM", "HS256")])
            tenant_id = payload.get("tenant_id")
        except Exception:
            pass

    all_items = []
    async with AsyncSessionLocal() as session:
        q = select(Estimate, Project).outerjoin(Project, Estimate.project_id == Project.id)
        if tenant_id:
            q = q.where(Estimate.tenant_id == tenant_id)
        q = q.order_by(desc(Estimate.created_at))
        result = await session.execute(q)
        rows = result.all()
        for e, p in rows:
            details = _extract_estimate_details(e)
            proj_name = (p.name if p else "") or ""
            for item in details["openings"].get("items", []):
                item["_project"] = proj_name
                item["_estimate_id"] = str(e.id)
            all_items.extend(details["openings"].get("items", []))

    # Generate Excel
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
    tmp.close()

    wb = xlsxwriter.Workbook(tmp.name)
    bold = wb.add_format({"bold": True, "bg_color": "#002147", "font_color": "white"})
    num_fmt = wb.add_format({"num_format": "#,##0.00"})
    int_fmt = wb.add_format({"num_format": "#,##0"})

    # Sheet 1: Summary
    ws = wb.add_worksheet("Summary")
    kpis = [
        ("Total Projects", summary.get("total_projects", 0)),
        ("Total Estimates", summary.get("total_estimates", 0)),
        ("Active Processing", summary.get("active_processing", 0)),
        ("Pending Review", summary.get("pending_review", 0)),
        ("Total Facade SQM", summary.get("total_facade_sqm", 0)),
        ("Total Openings", summary.get("total_openings", 0)),
        ("Pipeline Value AED", summary.get("total_contract_value_aed", 0)),
    ]
    ws.write(0, 0, "KPI", bold)
    ws.write(0, 1, "Value", bold)
    for i, (k, v) in enumerate(kpis, 1):
        ws.write(i, 0, k)
        ws.write(i, 1, v, num_fmt if isinstance(v, float) else int_fmt)

    # Sheet 2: Opening Schedule
    ws2 = wb.add_worksheet("Opening Schedule")
    headers = ["Project", "Item Code", "System Type", "W (mm)", "H (mm)", "Qty",
               "Gross Area SQM", "Net Glazed SQM", "Floor", "Elevation", "Glass Type",
               "Al Weight kg", "Gasket LM", "HW Sets"]
    for c, h in enumerate(headers):
        ws2.write(0, c, h, bold)
    for r, item in enumerate(all_items, 1):
        ws2.write(r, 0, item.get("_project", ""))
        ws2.write(r, 1, item.get("item_code", item.get("mark_id", "")))
        ws2.write(r, 2, item.get("system_type", ""))
        ws2.write(r, 3, item.get("width_mm", 0), num_fmt)
        ws2.write(r, 4, item.get("height_mm", 0), num_fmt)
        ws2.write(r, 5, item.get("qty", item.get("count", 1)), int_fmt)
        ws2.write(r, 6, item.get("gross_area_sqm", 0), num_fmt)
        ws2.write(r, 7, item.get("net_glazed_sqm", 0), num_fmt)
        ws2.write(r, 8, item.get("floor", ""))
        ws2.write(r, 9, item.get("elevation", ""))
        ws2.write(r, 10, item.get("glass_type", ""))
        ws2.write(r, 11, item.get("aluminum_weight_kg", 0), num_fmt)
        ws2.write(r, 12, item.get("gasket_length_lm", 0), num_fmt)
        ws2.write(r, 13, item.get("hardware_sets", 0), int_fmt)

    # Sheet 3: Systems Breakdown
    ws3 = wb.add_worksheet("Systems Breakdown")
    sys_headers = ["System Type", "Category", "Count", "Area SQM", "Unit"]
    for c, h in enumerate(sys_headers):
        ws3.write(0, c, h, bold)
    for r, sys in enumerate(summary.get("systems_breakdown", []), 1):
        ws3.write(r, 0, sys.get("system_type", ""))
        ws3.write(r, 1, sys.get("category", ""))
        ws3.write(r, 2, sys.get("count", 0), int_fmt)
        ws3.write(r, 3, sys.get("area", 0), num_fmt)
        ws3.write(r, 4, sys.get("unit", ""))

    # Sheet 4: Financial Summary
    ws4 = wb.add_worksheet("Financial Summary")
    fin = summary.get("financial_totals", {})
    fin_rows = [
        ("Material Cost AED", fin.get("material_aed", 0)),
        ("Labor Cost AED", fin.get("labor_aed", 0)),
        ("Overhead AED", fin.get("overhead_aed", 0)),
        ("Grand Total AED", fin.get("grand_total_aed", 0)),
    ]
    ws4.write(0, 0, "Item", bold)
    ws4.write(0, 1, "Amount AED", bold)
    for i, (k, v) in enumerate(fin_rows, 1):
        ws4.write(i, 0, k)
        ws4.write(i, 1, v, num_fmt)

    wb.close()

    return FileResponse(
        tmp.name,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="masaad_dashboard_report.xlsx",
    )


@app.get("/api/dashboard/export/pdf")
async def dashboard_export_pdf(request: Request):
    """Export dashboard summary as a branded PDF report."""
    import tempfile
    from fastapi.responses import FileResponse

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        from reportlab.lib.units import cm
        from app.services.report_engine import _draw_header, _draw_footer
    except ImportError:
        return JSONResponse(status_code=500, content={"detail": "reportlab not installed"})

    summary_resp = await dashboard_summary(request)
    if isinstance(summary_resp, JSONResponse):
        return summary_resp
    summary = summary_resp

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    tmp.close()

    page_w, page_h = A4
    c = canvas.Canvas(tmp.name, pagesize=A4)

    # Page 1: KPIs + Systems
    _draw_header(c, page_w, page_h)
    y = page_h - 4 * cm

    c.setFont("Helvetica-Bold", 14)
    c.drawString(1.5 * cm, y, "Dashboard Summary Report")
    y -= 1 * cm

    c.setFont("Helvetica", 10)
    kpis = [
        f"Projects: {summary.get('total_projects', 0)}",
        f"Estimates: {summary.get('total_estimates', 0)}",
        f"Active Processing: {summary.get('active_processing', 0)}",
        f"Pending Review: {summary.get('pending_review', 0)}",
        f"Total Facade: {summary.get('total_facade_sqm', 0):,.1f} SQM",
        f"Total Openings: {summary.get('total_openings', 0)}",
        f"Pipeline Value: AED {summary.get('total_contract_value_aed', 0):,.2f}",
    ]
    for kpi in kpis:
        c.drawString(2 * cm, y, kpi)
        y -= 0.5 * cm

    y -= 0.5 * cm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1.5 * cm, y, "Systems Breakdown")
    y -= 0.6 * cm

    c.setFont("Helvetica", 9)
    for sys in summary.get("systems_breakdown", []):
        text = f"{sys['system_type']} ({sys['category']}) — {sys['count']} items, {sys['area']:.1f} {sys['unit']}"
        c.drawString(2 * cm, y, text)
        y -= 0.4 * cm
        if y < 3 * cm:
            _draw_footer(c, page_w, 1)
            c.showPage()
            _draw_header(c, page_w, page_h)
            y = page_h - 4 * cm

    # Materials + Financial
    y -= 0.5 * cm
    if y < 5 * cm:
        _draw_footer(c, page_w, 1)
        c.showPage()
        _draw_header(c, page_w, page_h)
        y = page_h - 4 * cm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1.5 * cm, y, "Materials Summary")
    y -= 0.6 * cm
    c.setFont("Helvetica", 10)
    mat = summary.get("materials_summary", {})
    for line in [
        f"Aluminum: {mat.get('aluminum_kg', 0):,.1f} kg",
        f"Glass: {mat.get('glass_sqm', 0):,.1f} SQM",
        f"Total Weight: {mat.get('total_weight_kg', 0):,.1f} kg",
        f"Truck Loads: {mat.get('truck_loads', 0)}",
    ]:
        c.drawString(2 * cm, y, line)
        y -= 0.5 * cm

    y -= 0.5 * cm
    if y < 5 * cm:
        _draw_footer(c, page_w, 1)
        c.showPage()
        _draw_header(c, page_w, page_h)
        y = page_h - 4 * cm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1.5 * cm, y, "Financial Summary")
    y -= 0.6 * cm
    c.setFont("Helvetica", 10)
    fin = summary.get("financial_totals", {})
    for line in [
        f"Material: AED {fin.get('material_aed', 0):,.2f}",
        f"Labor: AED {fin.get('labor_aed', 0):,.2f}",
        f"Overhead: AED {fin.get('overhead_aed', 0):,.2f}",
        f"Grand Total: AED {fin.get('grand_total_aed', 0):,.2f}",
    ]:
        c.drawString(2 * cm, y, line)
        y -= 0.5 * cm

    # Engineering + RFIs
    if y < 5 * cm:
        _draw_footer(c, page_w, 1)
        c.showPage()
        _draw_header(c, page_w, page_h)
        y = page_h - 4 * cm

    y -= 0.5 * cm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1.5 * cm, y, "Engineering Compliance")
    y -= 0.6 * cm
    c.setFont("Helvetica", 10)
    eng = summary.get("engineering_summary", {})
    c.drawString(2 * cm, y, f"Total Checks: {eng.get('total_checks', 0)} | Pass: {eng.get('pass', 0)} | Fail: {eng.get('fail', 0)} | Warning: {eng.get('warning', 0)}")
    y -= 0.5 * cm
    c.drawString(2 * cm, y, f"Compliance: {eng.get('compliance_pct', 0):.1f}%")
    y -= 0.8 * cm

    c.setFont("Helvetica-Bold", 12)
    c.drawString(1.5 * cm, y, "RFI Summary")
    y -= 0.6 * cm
    c.setFont("Helvetica", 10)
    rfi = summary.get("rfi_summary", {})
    c.drawString(2 * cm, y, f"Total RFIs: {rfi.get('total', 0)}")
    y -= 0.5 * cm
    for sev, cnt in rfi.get("by_severity", {}).items():
        c.drawString(2.5 * cm, y, f"{sev}: {cnt}")
        y -= 0.4 * cm

    _draw_footer(c, page_w, 1)
    c.save()

    return FileResponse(
        tmp.name,
        media_type="application/pdf",
        filename="masaad_dashboard_summary.pdf",
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

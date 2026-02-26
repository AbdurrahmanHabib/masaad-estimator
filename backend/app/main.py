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
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from app.services.logging_config import setup_logging
from app.services.middleware import RequestTimingMiddleware
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
# Rate Limiting Middleware
# ---------------------------------------------------------------------------
class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    In-memory sliding-window rate limiter.
    Buckets:
      - /api/auth/login, /api/auth/register : 5 req/min per IP
      - file upload endpoints (multipart)   : 10 req/min per IP
      - everything else                     : 60 req/min per IP
    """
    def __init__(self, app):
        super().__init__(app)
        # {bucket_key: deque of timestamps}
        self._windows: dict = collections.defaultdict(collections.deque)

    def _get_limit(self, path: str) -> int:
        if path in ("/api/auth/login", "/api/auth/register"):
            return 5
        if path.startswith("/api/ingestion/upload") or "upload" in path:
            return 10
        return 60

    async def dispatch(self, request: Request, call_next):
        ip = request.client.host if request.client else "unknown"
        path = request.url.path
        limit = self._get_limit(path)
        bucket = f"{ip}:{path if limit <= 10 else 'general'}"
        now = time.monotonic()
        window = self._windows[bucket]
        # Remove entries older than 60 seconds
        while window and now - window[0] > 60:
            window.popleft()
        if len(window) >= limit:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please slow down."},
                headers={"Retry-After": "60"},
            )
        window.append(now)
        return await call_next(request)


# ---------------------------------------------------------------------------
# Security Headers Middleware
# ---------------------------------------------------------------------------
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds standard security headers to every response."""
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response


# ---------------------------------------------------------------------------
# CORS — restricted to allowed origins from env; auto-adds Railway domains
# ---------------------------------------------------------------------------
_cors_default = "http://localhost:3000,http://localhost:8000"
cors_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", _cors_default).split(",") if o.strip()]
# Auto-add Railway public domain if deployed on Railway
_railway_domain = os.getenv("RAILWAY_PUBLIC_DOMAIN", "")
if _railway_domain:
    cors_origins.append(f"https://{_railway_domain}")
# Auto-add Railway static domain patterns (e.g. *.up.railway.app)
_railway_static = os.getenv("RAILWAY_STATIC_URL", "")
if _railway_static:
    cors_origins.append(_railway_static.rstrip("/"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-Requested-With"],
)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)
# Request timing + X-Request-ID must be outermost so it wraps all other middleware
app.add_middleware(RequestTimingMiddleware)

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
        if estimate.status not in ("REVIEW_REQUIRED", "Processing"):
            raise HTTPException(
                status_code=400,
                detail=f"Estimate status is '{estimate.status}' — can only approve REVIEW_REQUIRED estimates"
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


@app.post("/api/v1/seed/al-kabir")
async def seed_al_kabir_endpoint():
    """
    Seed the AL KABIR TOWER demonstration project.
    Safe to call multiple times — idempotent, skips if already seeded.
    """
    from app.db.seed_al_kabir import seed_al_kabir
    return await seed_al_kabir()


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

    async with AsyncSessionLocal() as session:
        user_result = await session.execute(select(User).where(User.id == user_id))
        current_user = user_result.scalar_one_or_none()
        if not current_user:
            from fastapi import HTTPException
            raise HTTPException(status_code=401, detail="User not found")

        query = (
            select(Estimate, Project)
            .join(Project, Estimate.project_id == Project.id)
            .where(Estimate.tenant_id == current_user.tenant_id)
            .order_by(desc(Estimate.created_at))
            .limit(10)
        )
        result = await session.execute(query)
        rows = result.all()

    return [
        {
            "estimate_id": str(e.id),
            "project_id": str(e.project_id),
            "project_name": p.name or "",
            "client_name": p.client_name or "",
            "location": p.location_zone or "",
            "status": e.status,
            "progress_pct": e.progress_pct,
            "current_step": e.current_step,
            "created_at": e.created_at.isoformat() if e.created_at else None,
            "updated_at": e.updated_at.isoformat() if e.updated_at else None,
            "bom_summary": (e.bom_output_json or {}).get("summary", {}),
        }
        for e, p in rows
    ]


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

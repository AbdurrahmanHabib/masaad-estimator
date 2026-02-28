"""
Database Layer - Async SQLAlchemy engine + session factory.
"""
import os
import logging
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy.orm import DeclarativeBase

logger = logging.getLogger("masaad-db")

_raw_db_url = os.getenv("DATABASE_URL", "")
if not _raw_db_url:
    # Dev mode: no DB configured — use a placeholder URL so SQLAlchemy doesn't crash at import
    _raw_db_url = "postgresql+asyncpg://masaad_admin:dev_placeholder@localhost:5432/masaad_estimator"

DATABASE_URL = _raw_db_url
if DATABASE_URL.startswith("postgresql://") and "+asyncpg" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)


class Base(DeclarativeBase):
    pass


engine = create_async_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=False,
    # Use lazy connect so import doesn't immediately try to connect
    pool_timeout=5,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db():
    """Initialize DB tables. Skips gracefully in dev mode when no DB is available."""
    if not os.getenv("DATABASE_URL"):
        logger.warning("DATABASE_URL not set — skipping init_db() (dev mode)")
        return
    from app.models import orm_models  # noqa: F401
    try:
        async with engine.begin() as conn:
            # Drop and recreate to pick up schema changes (safe during early dev)
            if os.getenv("DB_RESET_ON_STARTUP", "").lower() in ("1", "true", "yes"):
                logger.warning("DB_RESET_ON_STARTUP=true — dropping all tables")
                await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

            # Add any missing columns (safe ALTER TABLE IF NOT EXISTS pattern)
            _migrations = [
                "ALTER TABLE projects ADD COLUMN IF NOT EXISTS client_name VARCHAR(255)",
                "ALTER TABLE projects ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'Active'",
                "ALTER TABLE projects ADD COLUMN IF NOT EXISTS location_zone VARCHAR(100)",
                "ALTER TABLE projects ADD COLUMN IF NOT EXISTS project_country VARCHAR(100) DEFAULT 'UAE'",
                "ALTER TABLE projects ADD COLUMN IF NOT EXISTS is_international BOOLEAN DEFAULT FALSE",
                "ALTER TABLE projects ADD COLUMN IF NOT EXISTS consultant_name VARCHAR(255)",
                "ALTER TABLE projects ADD COLUMN IF NOT EXISTS contract_type VARCHAR(50) DEFAULT 'Supply + Fabricate + Install'",
                "ALTER TABLE projects ADD COLUMN IF NOT EXISTS execution_strategy VARCHAR(30) DEFAULT 'IN_HOUSE_INSTALL'",
                "ALTER TABLE projects ADD COLUMN IF NOT EXISTS complexity_multiplier NUMERIC(4,2) DEFAULT 1.0",
                "ALTER TABLE projects ADD COLUMN IF NOT EXISTS scope_boundary VARCHAR(100) DEFAULT 'Panels + Substructure'",
                # Tenant columns added after initial schema
                "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS company_name VARCHAR(255) DEFAULT 'Madinat Al Saada'",
                "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS theme_color_hex VARCHAR(10) DEFAULT '#002147'",
                "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS base_currency VARCHAR(3) DEFAULT 'AED'",
                "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS monthly_factory_overhead NUMERIC(14,2) DEFAULT 200000",
                "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS default_factory_burn_rate NUMERIC(14,2) DEFAULT 13.00",
                "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS report_header_text VARCHAR(255)",
                "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS report_footer_text VARCHAR(255)",
                "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS company_address VARCHAR(500)",
                "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS company_phone VARCHAR(50)",
                "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS company_email VARCHAR(255)",
                "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS company_po_box VARCHAR(50)",
                "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS company_cr_number VARCHAR(50)",
                "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS company_trn VARCHAR(50)",
                # Estimate columns added after initial schema
                "ALTER TABLE estimates ADD COLUMN IF NOT EXISTS raw_data_json JSONB",
                "ALTER TABLE estimates ADD COLUMN IF NOT EXISTS project_scope_json JSONB",
                "ALTER TABLE estimates ADD COLUMN IF NOT EXISTS opening_schedule_json JSONB",
                "ALTER TABLE estimates ADD COLUMN IF NOT EXISTS bom_output_json JSONB",
                "ALTER TABLE estimates ADD COLUMN IF NOT EXISTS cutting_list_json JSONB",
                "ALTER TABLE estimates ADD COLUMN IF NOT EXISTS glass_schedule_json JSONB",
                "ALTER TABLE estimates ADD COLUMN IF NOT EXISTS financial_json JSONB",
                "ALTER TABLE estimates ADD COLUMN IF NOT EXISTS drawings_json JSONB",
                "ALTER TABLE estimates ADD COLUMN IF NOT EXISTS risk_register_json JSONB",
                "ALTER TABLE estimates ADD COLUMN IF NOT EXISTS value_engineering_json JSONB",
                "ALTER TABLE estimates ADD COLUMN IF NOT EXISTS procurement_json JSONB",
                "ALTER TABLE estimates ADD COLUMN IF NOT EXISTS installation_plan_json JSONB",
                "ALTER TABLE estimates ADD COLUMN IF NOT EXISTS fabrication_plan_json JSONB",
                "ALTER TABLE estimates ADD COLUMN IF NOT EXISTS engineering_results_json JSONB",
                "ALTER TABLE estimates ADD COLUMN IF NOT EXISTS compliance_results_json JSONB",
                "ALTER TABLE estimates ADD COLUMN IF NOT EXISTS reasoning_log JSONB",
                "ALTER TABLE estimates ADD COLUMN IF NOT EXISTS lme_snapshot_at TIMESTAMP",
                "ALTER TABLE estimates ADD COLUMN IF NOT EXISTS lme_usd_at_estimate NUMERIC(12,4)",
                "ALTER TABLE estimates ADD COLUMN IF NOT EXISTS dxf_override_url TEXT",
                "ALTER TABLE estimates ADD COLUMN IF NOT EXISTS state_snapshot JSONB",
                "ALTER TABLE estimates ADD COLUMN IF NOT EXISTS approved_by VARCHAR(255)",
                "ALTER TABLE estimates ADD COLUMN IF NOT EXISTS approved_at TIMESTAMP",
                "ALTER TABLE estimates ADD COLUMN IF NOT EXISTS bom_snapshot_json JSONB",
                "ALTER TABLE estimates ADD COLUMN IF NOT EXISTS revision_number INTEGER DEFAULT 0",
                "ALTER TABLE estimates ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW()",
                # Financial rates columns
                "ALTER TABLE financial_rates ADD COLUMN IF NOT EXISTS baseline_labor_burn_rate_aed NUMERIC(14,2) DEFAULT 13.00",
                "ALTER TABLE financial_rates ADD COLUMN IF NOT EXISTS burn_rate_last_updated TIMESTAMP",
                "ALTER TABLE financial_rates ADD COLUMN IF NOT EXISTS burn_rate_updated_by_source VARCHAR(50) DEFAULT 'manual'",
            ]
            for sql in _migrations:
                try:
                    await conn.execute(__import__('sqlalchemy').text(sql))
                except Exception:
                    pass  # Column already exists or table not yet created

        # Run seed data SQL using raw asyncpg (avoids SQLAlchemy text() interpreting
        # $ signs in bcrypt hashes as bind parameters).
        # Execute each statement separately so one failure doesn't roll back the rest.
        seed_path = os.path.join(os.path.dirname(__file__), "seed_data.sql")
        _db_url = os.getenv("DATABASE_URL", "")
        if os.path.exists(seed_path) and _db_url:
            try:
                with open(seed_path, "r") as f:
                    seed_sql = f.read()
                import re as _re
                # Remove SQL line comments
                cleaned = _re.sub(r'--[^\n]*', '', seed_sql)
                # asyncpg needs postgresql:// not postgresql+asyncpg://
                _raw_url = _db_url.replace("postgresql+asyncpg://", "postgresql://")
                import asyncpg as _apg
                _raw_conn = await _apg.connect(_raw_url)
                try:
                    for stmt in cleaned.split(";"):
                        stmt = stmt.strip()
                        if stmt:
                            try:
                                await _raw_conn.execute(stmt)
                            except Exception as stmt_err:
                                logger.debug("Seed stmt skipped: %s", str(stmt_err)[:120])
                    logger.info("Seed data applied.")
                finally:
                    await _raw_conn.close()
            except Exception as seed_err:
                logger.warning("Seed data failed: %s", seed_err)

        logger.info("Database tables initialized.")
    except Exception as e:
        logger.warning(f"init_db skipped (DB not available): {e}")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

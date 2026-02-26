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

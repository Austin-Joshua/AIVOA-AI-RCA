import os
import sys
import logging
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.core.config import settings

logger = logging.getLogger(__name__)

Base = declarative_base()

# Engine and session maker placeholders
engine = None
AsyncSessionLocal = None

def get_engine():
    global engine, AsyncSessionLocal
    if engine is not None:
        return engine

    database_url = settings.DATABASE_URL
    is_sqlite = database_url.startswith("sqlite")

    # Strict check: only PostgreSQL or explicit isolated SQLite test URLs are allowed
    if not is_sqlite and not (database_url.startswith("postgresql") or database_url.startswith("postgres")):
        raise ValueError(
            f"Unsupported database scheme in DATABASE_URL: {database_url}. "
            "AIVOA.AI RCA Intelligence strictly requires PostgreSQL 16."
        )

    try:
        engine_kwargs = {
            "echo": False,
            "future": True,
        }
        if not is_sqlite:
            engine_kwargs["pool_pre_ping"] = True
            if "pytest" in sys.modules or os.getenv("TESTING") == "1":
                from sqlalchemy.pool import NullPool
                engine_kwargs["poolclass"] = NullPool

        engine = create_async_engine(database_url, **engine_kwargs)
        AsyncSessionLocal = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False
        )
        safe_url = database_url.split("@")[-1] if "@" in database_url else database_url
        logger.info(f"Database engine created for target: {safe_url}")
        return engine
    except Exception as e:
        safe_url = database_url.split("@")[-1] if "@" in database_url else database_url
        logger.critical(
            f"Failed to initialize database engine for {safe_url}: {e}. "
            "Ensure PostgreSQL 16 service is active (docker compose up -d db)."
        )
        raise RuntimeError(
            f"Database engine initialization failed for {safe_url}: {e}. "
            "Ensure PostgreSQL 16 is accessible."
        ) from e

async def check_database_connection():
    """
    Verifies connectivity to the target database on normal application startup.
    Does NOT modify schemas or execute migrations.
    Authoritative schema changes must be applied explicitly via Alembic migrations.
    """
    from sqlalchemy import text
    global engine
    eng = get_engine()
    database_url = settings.DATABASE_URL
    safe_url = settings.safe_database_url

    try:
        async with eng.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info(f"Database connectivity verified on target: {safe_url}")
    except Exception as e:
        logger.critical(
            f"CRITICAL DATABASE ERROR: Could not connect to mandatory database ({safe_url}): {e}. "
            "Action required: Ensure PostgreSQL 16 is running ('docker compose up -d db') "
            "and migrations have been applied ('alembic upgrade head')."
        )
        raise RuntimeError(
            f"Database connection failed on {safe_url}: {e}. "
            "PostgreSQL 16 is mandatory. Start the database via: docker compose up -d db"
        ) from e

async def init_test_db(force: bool = False):
    """
    Explicit test-only schema initialization utility for ephemeral test suites.
    Strictly blocked in production environments.
    """
    if settings.is_production and not force:
        raise RuntimeError(
            "CRITICAL LIFECYCLE ERROR: Direct DDL execution via init_test_db() is prohibited in production. "
            "Alembic migrations are the authoritative schema management mechanism. "
            "Run 'alembic upgrade head' to apply migrations."
        )
    global engine
    eng = get_engine()
    safe_url = settings.safe_database_url

    try:
        async with eng.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info(f"Test database schema verified/created via test-only mechanism on: {safe_url}")
    except Exception as e:
        logger.critical(f"Failed to initialize test database on {safe_url}: {e}")
        raise RuntimeError(
            f"Test database initialization failed on {safe_url}: {e}."
        ) from e

async def init_db():
    """
    Backward-compatible test utility.
    Normal application startup MUST NOT invoke this function.
    Direct DDL table creation is prohibited in production.
    """
    if settings.is_production:
        raise RuntimeError(
            "CRITICAL LIFECYCLE ERROR: Direct DDL table creation (init_db) is prohibited in production. "
            "Alembic migrations are the authoritative schema management mechanism. "
            "Run 'alembic upgrade head' to apply migrations."
        )
    await init_test_db()

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    if AsyncSessionLocal is None:
        get_engine()
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


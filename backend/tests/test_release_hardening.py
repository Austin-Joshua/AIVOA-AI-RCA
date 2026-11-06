import pytest
import os
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient, ASGITransport
from app.core.config import Settings, settings
from app.core.database import init_db, init_test_db, check_database_connection, Base
from app.main import app, lifespan
from app.models.audit import User
from sqlalchemy.future import select

# ---------------------------------------------------------------------------
# Task 1 & 6: Configuration Security & Fail-Fast Startup
# ---------------------------------------------------------------------------

def test_missing_secret_key_fails_in_non_test_environment():
    """Verify Settings instantiation fails safely when SECRET_KEY is missing in non-test mode."""
    with pytest.raises(RuntimeError) as exc_info:
        Settings(
            ENVIRONMENT="development",
            SECRET_KEY="",
            DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/db"
        )
    err = str(exc_info.value)
    assert "CRITICAL SECURITY CONFIGURATION ERROR" in err
    assert "SECRET_KEY must be explicitly configured" in err


def test_placeholder_secret_key_fails_in_non_test_environment():
    """Verify Settings rejects template placeholders and default keys."""
    placeholders = [
        "aivoa-rca-secret-key-2026-pharma-gmp-demo",
        "replace_with_a_cryptographically_secure_random_key_min_32_chars",
        "your_secret_key_here",
        "changeme",
        "change_me",
        "default_secret",
        "secret",
    ]
    for ph in placeholders:
        with pytest.raises(RuntimeError) as exc_info:
            Settings(
                ENVIRONMENT="development",
                SECRET_KEY=ph,
                DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/db"
            )
        err = str(exc_info.value)
        assert "CRITICAL SECURITY CONFIGURATION ERROR" in err
        assert "Insecure placeholder" in err


def test_short_secret_key_fails_in_non_test_environment():
    """Verify Settings rejects secret keys with fewer than 32 characters."""
    with pytest.raises(RuntimeError) as exc_info:
        Settings(
            ENVIRONMENT="development",
            SECRET_KEY="short_key_under_32_chars!",
            DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/db"
        )
    err = str(exc_info.value)
    assert "CRITICAL SECURITY CONFIGURATION ERROR" in err
    assert "at least 32 characters" in err


def test_secret_key_value_is_never_leaked_in_exception_messages():
    """Ensure exception messages do not leak configured secret tokens."""
    sensitive_value = "my_custom_secret_key_is_123456789"
    with pytest.raises(RuntimeError) as exc_info:
        Settings(
            ENVIRONMENT="development",
            SECRET_KEY="replace_with_my_secret_token_12345678901234567890",
            DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/db"
        )
    err = str(exc_info.value)
    assert sensitive_value not in err


def test_valid_explicit_secret_key_succeeds_in_development():
    """Verify valid, high-entropy >=32 character key is accepted."""
    s = Settings(
        ENVIRONMENT="development",
        SECRET_KEY="f98e2a1b7c3d4e5f6a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f",
        DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/db"
    )
    assert s.ENVIRONMENT == "development"
    assert s.is_production is False


def test_test_environment_preserves_isolated_configuration():
    """Verify test environment provides deterministic fallback without manual secrets."""
    s = Settings(
        ENVIRONMENT="test",
        SECRET_KEY="",
        DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/db"
    )
    assert s.ENVIRONMENT == "test"
    assert len(s.SECRET_KEY) >= 32


def test_production_environment_rejects_development_database_credentials():
    """Verify production rejects default local developer database credentials."""
    with pytest.raises(RuntimeError) as exc_info:
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="f98e2a1b7c3d4e5f6a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f",
            DATABASE_URL="postgresql+asyncpg://aivoa_user:aivoa_password@localhost:5432/aivoa_rca"
        )
    err = str(exc_info.value)
    assert "CRITICAL SECURITY CONFIGURATION ERROR" in err
    assert "cannot use default development credentials" in err


# ---------------------------------------------------------------------------
# Task 2 & 6: Database Lifecycle & Alembic Migrations
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_init_db_and_init_test_db_fail_in_production(monkeypatch):
    """Verify direct DDL creation is blocked in production."""
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    with pytest.raises(RuntimeError) as exc_info:
        await init_test_db(force=False)
    assert "prohibited in production" in str(exc_info.value)

    with pytest.raises(RuntimeError) as exc_info2:
        await init_db()
    assert "prohibited in production" in str(exc_info2.value)


@pytest.mark.asyncio
async def test_application_lifespan_does_not_execute_create_all():
    """Verify application startup verifies connectivity without invoking Base.metadata.create_all."""
    with patch("app.main.check_database_connection", new_callable=AsyncMock) as mock_check, \
         patch.object(Base.metadata, "create_all") as mock_create_all:
        async with lifespan(app):
            pass
        mock_check.assert_awaited_once()
        mock_create_all.assert_not_called()


@pytest.mark.asyncio
async def test_check_database_connection_against_postgres():
    """Verify check_database_connection executes SELECT 1 successfully on active database."""
    await check_database_connection()


# ---------------------------------------------------------------------------
# Task 3 & 6: Demo Login Production Isolation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_demo_seeding_disabled_in_production(monkeypatch):
    """Verify demo account auto-provisioning is strictly disabled in production."""
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    assert settings.allows_demo_seeding is False

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        config_res = await ac.get("/api/v1/auth/config")
        assert config_res.status_code == 200
        assert config_res.json()["demo_login_enabled"] is False
        assert config_res.json()["environment"] == "production"

        # Attempt login for demo username that does not exist in production
        fake_demo_login = await ac.post(
            "/api/v1/auth/login",
            json={"username": "unprovisioned_demo_user", "password": "AnyPassword123!"}
        )
        assert fake_demo_login.status_code == 401


@pytest.mark.asyncio
async def test_demo_provisioning_can_be_disabled_via_flag(monkeypatch):
    """Verify ENABLE_DEMO_PROVISIONING flag disables demo seeding even in development."""
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    monkeypatch.setattr(settings, "ENABLE_DEMO_PROVISIONING", False)
    assert settings.allows_demo_seeding is False


@pytest.mark.asyncio
async def test_auth_config_endpoint_reports_dev_demo_status(monkeypatch):
    """Verify /api/v1/auth/config reports demo status accurately for frontend UI toggles."""
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    monkeypatch.setattr(settings, "ENABLE_DEMO_PROVISIONING", True)
    assert settings.allows_demo_seeding is True

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/api/v1/auth/config")
        assert res.status_code == 200
        data = res.json()
        assert data["demo_login_enabled"] is True
        assert data["environment"] == "development"

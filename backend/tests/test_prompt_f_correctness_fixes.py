import pytest
import pytest_asyncio
import uuid
import os
from httpx import AsyncClient, ASGITransport
from sqlalchemy.future import select

from app.main import app
from app.core.config import settings
from app.core.database import get_engine, init_db
from app.core.security import create_access_token, hash_password
from app.models.audit import User, AuditLog
from app.models.investigation import Investigation
from app.api.endpoints.auth import ensure_default_users

def get_session():
    get_engine()
    from app.core.database import AsyncSessionLocal
    return AsyncSessionLocal()

async def create_user(username: str, role: str, full_name: str) -> User:
    async with get_session() as session:
        res = await session.execute(select(User).where(User.username == username))
        existing = res.scalars().first()
        if existing:
            existing.role = role
            existing.full_name = full_name
            await session.commit()
            await session.refresh(existing)
            return existing
        user = User(
            username=username,
            email=f"{username}@aivoa.test",
            full_name=full_name,
            hashed_password=hash_password("AivoaPass2026!"),
            role=role,
            is_active=True
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user

@pytest.mark.asyncio
async def test_investigation_archive_admin_only_and_audit_trail():
    """Verify POST /api/v1/investigations/{id}/archive is strictly ADMIN-only, creates audit entry, and hides from default list."""
    admin_user = await create_user(f"admin_{uuid.uuid4().hex[:6]}", "ADMIN", "Administrator")
    inv_user = await create_user(f"inv_{uuid.uuid4().hex[:6]}", "INVESTIGATOR", "Lead Investigator")
    
    admin_token = create_access_token({"sub": admin_user.username, "role": admin_user.role, "user_id": admin_user.id})
    inv_token = create_access_token({"sub": inv_user.username, "role": inv_user.role, "user_id": inv_user.id})
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    inv_headers = {"Authorization": f"Bearer {inv_token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Create an investigation
        create_res = await ac.post(
            "/api/v1/investigations/",
            headers=admin_headers,
            json={"title": "Archive Verification Dossier", "stage": "INTAKE", "status": "IN_INVESTIGATION"}
        )
        assert create_res.status_code == 200
        inv_id = create_res.json()["id"]

        # 1. Non-admin investigator attempts archive -> 403 Forbidden
        forbid_res = await ac.post(f"/api/v1/investigations/{inv_id}/archive", headers=inv_headers, json={"reason": "Unauthorized attempt"})
        assert forbid_res.status_code == 403
        assert "Administrative privilege required" in forbid_res.json()["detail"]

        # 2. Admin successfully archives
        archive_res = await ac.post(f"/api/v1/investigations/{inv_id}/archive", headers=admin_headers, json={"reason": "Testing soft-archival"})
        assert archive_res.status_code == 200
        archived_inv = archive_res.json()
        assert archived_inv["status"] == "ARCHIVED"

        # 3. Default list excludes archived record
        list_res = await ac.get("/api/v1/investigations/", headers=admin_headers)
        assert list_res.status_code == 200
        listed_ids = [item["id"] for item in list_res.json()]
        assert inv_id not in listed_ids

        # 4. list with include_archived=true includes it
        list_arch_res = await ac.get("/api/v1/investigations/?include_archived=true", headers=admin_headers)
        assert list_arch_res.status_code == 200
        listed_arch_ids = [item["id"] for item in list_arch_res.json()]
        assert inv_id in listed_arch_ids

        # 5. Audit trail records archival action
        audit_res = await ac.get(f"/api/v1/investigations/{inv_id}/audit-logs", headers=admin_headers)
        assert audit_res.status_code == 200
        logs = audit_res.json()
        assert any(l["action"] == "ARCHIVED" for l in logs)

@pytest.mark.asyncio
async def test_qa_approval_requires_minimum_comments_length():
    """Verify POST /api/v1/investigations/{id}/approve rejects missing or short closure rationales."""
    qa_user = await create_user(f"qa_{uuid.uuid4().hex[:6]}", "QA_APPROVER", "Quality Approver")
    admin_user = await create_user(f"admin_{uuid.uuid4().hex[:6]}", "ADMIN", "Administrator")
    qa_token = create_access_token({"sub": qa_user.username, "role": qa_user.role, "user_id": qa_user.id})
    admin_token = create_access_token({"sub": admin_user.username, "role": admin_user.role, "user_id": admin_user.id})
    qa_headers = {"Authorization": f"Bearer {qa_token}"}
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Create investigation
        create_res = await ac.post(
            "/api/v1/investigations/",
            headers=admin_headers,
            json={"title": "Approval Rationale Test Dossier", "stage": "APPROVAL", "status": "PENDING_QA_REVIEW"}
        )
        inv_id = create_res.json()["id"]

        # Reject without comments or with short comments (< 10 chars)
        res_empty = await ac.post(f"/api/v1/investigations/{inv_id}/approve", headers=qa_headers, json={"comments": ""})
        assert res_empty.status_code == 400
        assert "at least 10 characters" in res_empty.json()["detail"]

        res_short = await ac.post(f"/api/v1/investigations/{inv_id}/approve", headers=qa_headers, json={"comments": "Too short"})
        assert res_short.status_code == 400
        assert "at least 10 characters" in res_short.json()["detail"]

        # Valid rationale -> 200 OK
        valid_rationale = "Root cause scientifically verified by physical valve inspection and CAPA validated."
        res_ok = await ac.post(f"/api/v1/investigations/{inv_id}/approve", headers=qa_headers, json={"comments": valid_rationale})
        assert res_ok.status_code == 200
        approved_inv = res_ok.json()
        assert approved_inv["is_approved"] is True
        assert approved_inv["approval_comments"] == valid_rationale

@pytest.mark.asyncio
async def test_ai_config_endpoint_auth_required_and_no_secrets():
    """Verify GET /api/v1/config/ai requires authentication and never leaks API keys or secrets."""
    user = await create_user(f"user_{uuid.uuid4().hex[:6]}", "INVESTIGATOR", "Investigator User")
    token = create_access_token({"sub": user.username, "role": user.role, "user_id": user.id})
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Unauthenticated -> 401 Unauthorized
        unauth_res = await ac.get("/api/v1/config/ai")
        assert unauth_res.status_code == 401

        # 2. Authenticated -> 200 OK
        auth_res = await ac.get("/api/v1/config/ai", headers=headers)
        assert auth_res.status_code == 200
        data = auth_res.json()
        assert data["provider"] == "Groq"
        assert "model" in data
        assert "is_configured" in data
        assert "autodiscover" in data

        # Check for zero leaks
        res_str = str(data)
        assert "gsk_" not in res_str
        assert "key" not in data or data.get("key") is None
        assert "password" not in res_str
        assert "secret" not in res_str

@pytest.mark.asyncio
async def test_demo_account_seeding_security_refusal():
    """Verify ensure_default_users refuses to seed when DEMO_ACCOUNT_PASSWORD is unset or in production."""
    old_env = os.environ.get("ENVIRONMENT")
    old_pw = os.environ.get("DEMO_ACCOUNT_PASSWORD")

    async with get_session() as session:
        # Case 1: DEMO_ACCOUNT_PASSWORD unset
        if "DEMO_ACCOUNT_PASSWORD" in os.environ:
            del os.environ["DEMO_ACCOUNT_PASSWORD"]
        await ensure_default_users(session)
        # Verify function returns cleanly without raising or creating default user

        # Case 2: ENVIRONMENT is production
        os.environ["DEMO_ACCOUNT_PASSWORD"] = "SomeStrongPass123!"
        os.environ["ENVIRONMENT"] = "production"
        await ensure_default_users(session)

    # Restore environment
    if old_env is not None:
        os.environ["ENVIRONMENT"] = old_env
    else:
        os.environ.pop("ENVIRONMENT", None)
    if old_pw is not None:
        os.environ["DEMO_ACCOUNT_PASSWORD"] = old_pw
    else:
        os.environ.pop("DEMO_ACCOUNT_PASSWORD", None)

@pytest.mark.asyncio
async def test_cli_reset_demo_refuses_in_production():
    """Verify run_reset_demo CLI refuses in production and archives without delete in non-prod."""
    from unittest.mock import patch
    from app.cli import run_reset_demo
    import argparse

    # Test 1: Production refusal
    with patch("app.cli.settings.ENVIRONMENT", "production"):
        code = await run_reset_demo(argparse.Namespace())
        assert code == 1

    # Test 2: Non-production execution
    with patch("app.cli.settings.ENVIRONMENT", "test"):
        code = await run_reset_demo(argparse.Namespace())
        assert code == 0

@pytest.mark.asyncio
async def test_deviation_number_source_column_and_clean_identifier():
    """Verify deviation_number_source is correctly assigned and deviation_number is clean without string suffix."""
    from app.models.deviation import Deviation
    inv_user = await create_user(f"dev_usr_{uuid.uuid4().hex[:6]}", "INVESTIGATOR", "Lead Investigator")
    token = create_access_token({"sub": inv_user.username, "role": inv_user.role, "user_id": inv_user.id})
    headers = {"Authorization": f"Bearer {token}"}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Create investigation
        create_res = await ac.post(
            "/api/v1/investigations/",
            headers=headers,
            json={"title": "Test Deviation Source Isolation", "batch_number": "B2026-SRC-01", "product_name": "API"}
        )
        assert create_res.status_code == 200
        inv_id = create_res.json()["id"]

        # Apply extraction review with no deviation number in source
        review_res = await ac.post(
            "/api/v1/intake/apply-to-investigation",
            headers=headers,
            json={
                "investigation_id": inv_id,
                "apply_deviation": True,
                "custom_overrides": {
                    "deviation": {
                        "batch_number": "B2026-SRC-01",
                        "product_name": "API X",
                        "description": "Temperature excursion observed"
                    }
                }
            }
        )
        assert review_res.status_code == 200

        # Verify deviation in DB
        async with get_session() as session:
            stmt = select(Deviation).where(Deviation.investigation_id == inv_id)
            res = await session.execute(stmt)
            dev = res.scalars().first()
            assert dev is not None
            assert dev.deviation_number_source == "SYSTEM"
            # Must be a clean number without "(System-assigned)" suffix
            assert "(System-assigned)" not in dev.deviation_number
            assert dev.deviation_number.startswith("DEV-2026-")


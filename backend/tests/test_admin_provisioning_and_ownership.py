import pytest
import pytest_asyncio
import uuid
from httpx import AsyncClient, ASGITransport
from sqlalchemy.future import select
from sqlalchemy import delete

from app.main import app
from app.core.config import settings
from app.core.database import get_engine, init_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models.audit import User, AuditLog
from app.models.investigation import Investigation
from app.services.admin_provisioning import provision_admin_account

def get_session():
    get_engine()
    from app.core.database import AsyncSessionLocal
    return AsyncSessionLocal()

async def create_test_user(username: str, role: str = "INVESTIGATOR", full_name: str = "Test User", is_active: bool = True) -> User:
    async with get_session() as session:
        res = await session.execute(select(User).where(User.username == username))
        existing = res.scalars().first()
        if existing:
            existing.role = role
            existing.full_name = full_name
            existing.is_active = is_active
            await session.commit()
            await session.refresh(existing)
            return existing
        
        user = User(
            username=username,
            email=f"{username}@aivoa.test",
            full_name=full_name,
            hashed_password=hash_password("AivoaTestPass2026!"),
            role=role,
            department="Testing Department",
            is_active=is_active
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user

# -------------------------------------------------------------
# Test 1: Production login does not seed an ADMIN
# -------------------------------------------------------------
@pytest.mark.asyncio
async def test_production_login_does_not_seed_admin(monkeypatch):
    await init_db()
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    assert settings.allows_demo_seeding is False

    unique_admin = f"nonexistent_admin_{uuid.uuid4().hex[:6]}"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post("/api/v1/auth/login", json={"username": unique_admin, "password": "AnyPassword123!"})
        assert res.status_code == 401

    # Verify directly in PostgreSQL that the user was NOT created
    async with get_session() as session:
        res_user = await session.execute(select(User).where(User.username == unique_admin))
        assert res_user.scalars().first() is None

# -------------------------------------------------------------
# Test 2: Deleting an ADMIN does not cause login to recreate it
# -------------------------------------------------------------
@pytest.mark.asyncio
async def test_deleting_admin_is_not_recreated_by_login():
    unique_admin = f"del_admin_{uuid.uuid4().hex[:6]}"
    async with get_session() as session:
        new_admin = User(
            username=unique_admin,
            email=f"{unique_admin}@aivoa.test",
            full_name="Deleted Admin Test",
            hashed_password=hash_password("SecurePass2026!"),
            role="ADMIN",
            department="IT Quality Compliance",
            is_active=True
        )
        session.add(new_admin)
        await session.commit()

        # Now delete this admin
        await session.execute(delete(User).where(User.username == unique_admin))
        await session.commit()

    # Call login endpoint (even in development mode)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post("/api/v1/auth/login", json={"username": unique_admin, "password": "SecurePass2026!"})
        assert res.status_code == 401

    # Verify that ensure_default_users did NOT recreate this admin
    async with get_session() as session:
        res_check = await session.execute(select(User).where(User.username == unique_admin))
        assert res_check.scalars().first() is None

# -------------------------------------------------------------
# Test 3: Development/test demo seeding still works
# -------------------------------------------------------------
@pytest.mark.asyncio
async def test_development_demo_seeding_works(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    assert settings.allows_demo_seeding is True

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Trigger login to execute ensure_default_users
        await ac.post("/api/v1/auth/login", json={"username": "lead_investigator", "password": "AivoaPass2026!"})

    # Verify demo accounts exist
    async with get_session() as session:
        res_lead = await session.execute(select(User).where(User.username == "lead_investigator"))
        lead = res_lead.scalars().first()
        assert lead is not None
        assert lead.role == "INVESTIGATOR"

        res_qa = await session.execute(select(User).where(User.username == "qa_director"))
        qa = res_qa.scalars().first()
        assert qa is not None
        assert qa.role == "QA_APPROVER"

# -------------------------------------------------------------
# Test 4: Secure initial ADMIN provisioning works
# -------------------------------------------------------------
@pytest.mark.asyncio
async def test_secure_initial_admin_provisioning_works():
    unique_admin = f"provisioned_admin_{uuid.uuid4().hex[:6]}"
    async with get_session() as session:
        result = await provision_admin_account(
            db=session,
            username=unique_admin,
            password="StrongAdminPassword2026!",
            email=f"{unique_admin}@aivoa.pharma",
            full_name="Provisioned System Administrator"
        )
        assert result["success"] is True
        assert result["role"] == "ADMIN"
        assert result["username"] == unique_admin

        # Verify in DB
        res = await session.execute(select(User).where(User.username == unique_admin))
        db_admin = res.scalar_one()
        assert db_admin.role == "ADMIN"
        assert db_admin.is_active is True
        assert verify_password("StrongAdminPassword2026!", db_admin.hashed_password) is True

# -------------------------------------------------------------
# Test 5: Existing ADMIN password is never silently overwritten
# -------------------------------------------------------------
@pytest.mark.asyncio
async def test_existing_admin_password_never_overwritten():
    unique_admin = f"keep_pass_admin_{uuid.uuid4().hex[:6]}"
    original_pass = "FirstSecurePassword2026!"
    different_pass = "SecondOverwritingAttempt2026!"

    async with get_session() as session:
        # 1. Provision initial admin
        res1 = await provision_admin_account(
            db=session,
            username=unique_admin,
            password=original_pass,
            email=f"{unique_admin}@aivoa.pharma",
            full_name="Original Admin"
        )
        assert res1["success"] is True

        # 2. Attempt provisioning again with a different password
        res2 = await provision_admin_account(
            db=session,
            username=unique_admin,
            password=different_pass,
            email=f"{unique_admin}@aivoa.pharma",
            full_name="Overwritten Admin Attempt"
        )
        assert res2["success"] is False
        assert res2.get("already_exists") is True

        # 3. Verify original password remains valid and different password fails
        user_res = await session.execute(select(User).where(User.username == unique_admin))
        user_db = user_res.scalar_one()
        assert verify_password(original_pass, user_db.hashed_password) is True
        assert verify_password(different_pass, user_db.hashed_password) is False

# -------------------------------------------------------------
# Test 6: Missing provisioning secrets fail safely
# -------------------------------------------------------------
@pytest.mark.asyncio
async def test_missing_provisioning_secrets_fail_safely():
    async with get_session() as session:
        # Missing username
        res_no_user = await provision_admin_account(db=session, username="", password="ValidPassword2026!")
        assert res_no_user["success"] is False
        assert "Missing required administrator credentials" in res_no_user["error"]

        # Missing password
        res_no_pass = await provision_admin_account(db=session, username="some_admin", password="")
        assert res_no_pass["success"] is False
        assert "Missing required administrator credentials" in res_no_pass["error"]

        # Short password (< 10 chars)
        res_short_pass = await provision_admin_account(db=session, username="some_admin", password="short")
        assert res_short_pass["success"] is False
        assert "at least 10 characters" in res_short_pass["error"]

# -------------------------------------------------------------
# Test 7: Non-ADMIN users cannot assign owners
# -------------------------------------------------------------
@pytest.mark.asyncio
async def test_non_admin_users_cannot_assign_owners():
    investigator = await create_test_user("inv_regular_7", "INVESTIGATOR", "Dr. Regular Inv")
    qa_user = await create_test_user("qa_user_7", "QA_APPROVER", "Dr. QA Reviewer")
    target_user = await create_test_user("target_inv_7", "INVESTIGATOR", "Dr. Target Inv")

    token_inv = create_access_token({"sub": investigator.username, "role": investigator.role, "user_id": investigator.id})
    token_qa = create_access_token({"sub": qa_user.username, "role": qa_user.role, "user_id": qa_user.id})

    # Create investigation
    inv_num = f"INV-TEST7-{uuid.uuid4().hex[:6].upper()}"
    async with get_session() as session:
        inv = Investigation(
            investigation_number=inv_num,
            title="Ownership Authorization Test 7",
            status="IN_INVESTIGATION",
            stage="INTAKE"
        )
        session.add(inv)
        await session.commit()
        await session.refresh(inv)
        inv_id = inv.id

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Investigator attempt -> 403
        res1 = await ac.post(
            f"/api/v1/investigations/{inv_id}/assign-owner",
            headers={"Authorization": f"Bearer {token_inv}"},
            json={"new_investigator_id": target_user.id, "reason": "Investigator attempting owner assignment"}
        )
        assert res1.status_code == 403

        # QA Approver attempt -> 403
        res2 = await ac.post(
            f"/api/v1/investigations/{inv_id}/assign-owner",
            headers={"Authorization": f"Bearer {token_qa}"},
            json={"new_investigator_id": target_user.id, "reason": "QA Approver attempting owner assignment"}
        )
        assert res2.status_code == 403

# -------------------------------------------------------------
# Test 8: ADMIN cannot assign an inactive or nonexistent account
# -------------------------------------------------------------
@pytest.mark.asyncio
async def test_admin_cannot_assign_inactive_or_nonexistent_account():
    admin_user = await create_test_user("admin_user_8", "ADMIN", "Administrator Eight")
    inactive_inv = await create_test_user("inactive_inv_8", "INVESTIGATOR", "Inactive Investigator", is_active=False)

    token_admin = create_access_token({"sub": admin_user.username, "role": admin_user.role, "user_id": admin_user.id})

    inv_num = f"INV-TEST8-{uuid.uuid4().hex[:6].upper()}"
    async with get_session() as session:
        inv = Investigation(
            investigation_number=inv_num,
            title="Ownership Validation Test 8",
            status="IN_INVESTIGATION",
            stage="INTAKE"
        )
        session.add(inv)
        await session.commit()
        await session.refresh(inv)
        inv_id = inv.id

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Nonexistent user ID -> 404
        res_nonexistent = await ac.post(
            f"/api/v1/investigations/{inv_id}/assign-owner",
            headers={"Authorization": f"Bearer {token_admin}"},
            json={"new_investigator_id": 999999, "reason": "Assigning to nonexistent target user"}
        )
        assert res_nonexistent.status_code == 404
        assert "not found" in res_nonexistent.json()["detail"].lower()

        # 2. Inactive target user -> 400
        res_inactive = await ac.post(
            f"/api/v1/investigations/{inv_id}/assign-owner",
            headers={"Authorization": f"Bearer {token_admin}"},
            json={"new_investigator_id": inactive_inv.id, "reason": "Assigning to inactive investigator"}
        )
        assert res_inactive.status_code == 400
        assert "inactive" in res_inactive.json()["detail"].lower()

# -------------------------------------------------------------
# Test 9: ADMIN cannot assign QA_APPROVER as lead investigator
# -------------------------------------------------------------
@pytest.mark.asyncio
async def test_admin_cannot_assign_qa_approver_as_lead():
    admin_user = await create_test_user("admin_user_9", "ADMIN", "Administrator Nine")
    qa_user = await create_test_user("qa_user_9", "QA_APPROVER", "Dr. QA Approver Nine")

    token_admin = create_access_token({"sub": admin_user.username, "role": admin_user.role, "user_id": admin_user.id})

    inv_num = f"INV-TEST9-{uuid.uuid4().hex[:6].upper()}"
    async with get_session() as session:
        inv = Investigation(
            investigation_number=inv_num,
            title="Ownership Role Segregation Test 9",
            status="IN_INVESTIGATION",
            stage="INTAKE"
        )
        session.add(inv)
        await session.commit()
        await session.refresh(inv)
        inv_id = inv.id

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Assigning QA_APPROVER as lead investigator -> 400 Bad Request
        res = await ac.post(
            f"/api/v1/investigations/{inv_id}/assign-owner",
            headers={"Authorization": f"Bearer {token_admin}"},
            json={"new_investigator_id": qa_user.id, "reason": "Attempting to assign QA Approver as lead"}
        )
        assert res.status_code == 400
        assert "role 'QA_APPROVER'" in res.json()["detail"]
        assert "INVESTIGATOR" in res.json()["detail"]

# -------------------------------------------------------------
# Test 10: Missing, short or whitespace-only assignment reasons are rejected
# -------------------------------------------------------------
@pytest.mark.asyncio
async def test_rejection_of_invalid_assignment_reasons():
    admin_user = await create_test_user("admin_user_10", "ADMIN", "Administrator Ten")
    target_user = await create_test_user("target_inv_10", "INVESTIGATOR", "Dr. Target Ten")

    token_admin = create_access_token({"sub": admin_user.username, "role": admin_user.role, "user_id": admin_user.id})

    inv_num = f"INV-TEST10-{uuid.uuid4().hex[:6].upper()}"
    async with get_session() as session:
        inv = Investigation(
            investigation_number=inv_num,
            title="Ownership Reason Validation Test 10",
            status="IN_INVESTIGATION",
            stage="INTAKE"
        )
        session.add(inv)
        await session.commit()
        await session.refresh(inv)
        inv_id = inv.id

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Missing reason field -> 422
        res_missing = await ac.post(
            f"/api/v1/investigations/{inv_id}/assign-owner",
            headers={"Authorization": f"Bearer {token_admin}"},
            json={"new_investigator_id": target_user.id}
        )
        assert res_missing.status_code == 422

        # 2. Too short (< 10 chars) -> 422
        res_short = await ac.post(
            f"/api/v1/investigations/{inv_id}/assign-owner",
            headers={"Authorization": f"Bearer {token_admin}"},
            json={"new_investigator_id": target_user.id, "reason": "Too short"}
        )
        assert res_short.status_code == 422

        # 3. Whitespace-only -> 422
        res_whitespace = await ac.post(
            f"/api/v1/investigations/{inv_id}/assign-owner",
            headers={"Authorization": f"Bearer {token_admin}"},
            json={"new_investigator_id": target_user.id, "reason": "              "}
        )
        assert res_whitespace.status_code == 422

# -------------------------------------------------------------
# Test 11: Valid assignment succeeds and records a complete audit event
# -------------------------------------------------------------
@pytest.mark.asyncio
async def test_valid_assignment_succeeds_with_audit_trail():
    admin_user = await create_test_user("admin_user_11", "ADMIN", "Administrator Eleven")
    target_user = await create_test_user("target_inv_11", "INVESTIGATOR", "Dr. Assigned Investigator Eleven")

    token_admin = create_access_token({"sub": admin_user.username, "role": admin_user.role, "user_id": admin_user.id})

    inv_num = f"INV-TEST11-{uuid.uuid4().hex[:6].upper()}"
    async with get_session() as session:
        inv = Investigation(
            investigation_number=inv_num,
            title="Valid Ownership Assignment Test 11",
            status="IN_INVESTIGATION",
            stage="INTAKE",
            lead_investigator="Previous Lead",
            lead_investigator_id=None
        )
        session.add(inv)
        await session.commit()
        await session.refresh(inv)
        inv_id = inv.id

    assignment_reason = "Formal reassignment of lead role to qualified investigator Dr. Eleven due to shift rotation."
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post(
            f"/api/v1/investigations/{inv_id}/assign-owner",
            headers={"Authorization": f"Bearer {token_admin}"},
            json={"new_investigator_id": target_user.id, "reason": assignment_reason}
        )
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["lead_investigator_id"] == target_user.id
        assert data["lead_investigator"] == target_user.full_name

    # Verify audit event in PostgreSQL
    async with get_session() as session:
        audit_res = await session.execute(
            select(AuditLog).filter(
                AuditLog.investigation_id == inv_id,
                AuditLog.action == "OWNERSHIP_ASSIGNED"
            )
        )
        audit_log = audit_res.scalar_one_or_none()
        assert audit_log is not None, "OWNERSHIP_ASSIGNED audit log entry must exist"
        assert audit_log.user_id == admin_user.id
        assert audit_log.user_name == admin_user.full_name
        assert assignment_reason in audit_log.change_summary
        assert target_user.full_name in audit_log.change_summary

# -------------------------------------------------------------
# Test 12: Failed assignments do not mutate the database
# -------------------------------------------------------------
@pytest.mark.asyncio
async def test_failed_assignments_do_not_mutate_database():
    admin_user = await create_test_user("admin_user_12", "ADMIN", "Administrator Twelve")
    initial_owner = await create_test_user("initial_inv_12", "INVESTIGATOR", "Dr. Initial Owner Twelve")
    qa_user = await create_test_user("qa_user_12", "QA_APPROVER", "QA Non-Investigator")

    token_admin = create_access_token({"sub": admin_user.username, "role": admin_user.role, "user_id": admin_user.id})

    inv_num = f"INV-TEST12-{uuid.uuid4().hex[:6].upper()}"
    async with get_session() as session:
        inv = Investigation(
            investigation_number=inv_num,
            title="Database Immutability Test 12",
            status="IN_INVESTIGATION",
            stage="INTAKE",
            lead_investigator=initial_owner.full_name,
            lead_investigator_id=initial_owner.id
        )
        session.add(inv)
        await session.commit()
        await session.refresh(inv)
        inv_id = inv.id

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Attempt failed assignment (target is QA_APPROVER) -> 400
        res = await ac.post(
            f"/api/v1/investigations/{inv_id}/assign-owner",
            headers={"Authorization": f"Bearer {token_admin}"},
            json={"new_investigator_id": qa_user.id, "reason": "Invalid assignment attempt to QA user"}
        )
        assert res.status_code == 400

    # Verify database state in PostgreSQL remains completely untouched
    async with get_session() as session:
        inv_check = (await session.execute(
            select(Investigation).filter(Investigation.id == inv_id)
        )).scalar_one()
        assert inv_check.lead_investigator_id == initial_owner.id, "lead_investigator_id must not have changed!"
        assert inv_check.lead_investigator == initial_owner.full_name, "lead_investigator must not have changed!"

        # Verify no audit log was created for the failed attempt
        audit_check = (await session.execute(
            select(AuditLog).filter(
                AuditLog.investigation_id == inv_id,
                AuditLog.action == "OWNERSHIP_ASSIGNED"
            )
        )).scalar_one_or_none()
        assert audit_check is None, "No audit log should be written on failed assignment!"


import pytest
import io
import hashlib
import uuid
from httpx import AsyncClient, ASGITransport
from sqlalchemy.future import select

from app.main import app
from app.core import database
from app.models.investigation import Investigation
from app.models.evidence import Evidence
from app.models.root_cause import RootCause, RootCauseEvidenceLink
from app.models.audit import User, AuditLog
from app.core.security import create_access_token, hash_password

def get_session():
    if database.AsyncSessionLocal is None:
        database.get_engine()
    return database.AsyncSessionLocal()

async def get_or_create_user(username: str, role: str, full_name: str, password: str = "AivoaPass2026!"):
    async with get_session() as session:
        res = await session.execute(select(User).filter(User.username == username))
        user = res.scalar_one_or_none()
        if not user:
            user = User(
                username=username,
                email=f"{username}@aivoa.test",
                full_name=full_name,
                hashed_password=hash_password(password),
                role=role,
                department="Quality Assurance"
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
        return user

# -------------------------------------------------------------
# Test 1: Authenticate valid credentials, receive signed token
# -------------------------------------------------------------
@pytest.mark.asyncio
async def test_1_login_success():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Investigator login
        res_inv = await ac.post("/api/v1/auth/login", json={
            "username": "lead_investigator",
            "password": "AivoaPass2026!"
        })
        assert res_inv.status_code == 200, res_inv.text
        data_inv = res_inv.json()
        assert "access_token" in data_inv
        assert data_inv["token_type"].lower() == "bearer"
        assert data_inv["role"] == "INVESTIGATOR"

        # QA Approver login
        res_qa = await ac.post("/api/v1/auth/login", json={
            "username": "qa_director",
            "password": "AivoaPass2026!"
        })
        assert res_qa.status_code == 200
        data_qa = res_qa.json()
        assert "access_token" in data_qa
        assert data_qa["role"] == "QA_APPROVER"

# -------------------------------------------------------------
# Test 2: Reject invalid credentials with 401
# -------------------------------------------------------------
@pytest.mark.asyncio
async def test_2_login_invalid_credentials():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post("/api/v1/auth/login", json={
            "username": "lead_investigator",
            "password": "InvalidPasswordXYZ99!"
        })
        assert res.status_code == 401
        assert "Invalid username or password" in res.json()["detail"]

# -------------------------------------------------------------
# Test 3: Return profile for authenticated token
# -------------------------------------------------------------
@pytest.mark.asyncio
async def test_3_get_me_authenticated():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        login_res = await ac.post("/api/v1/auth/login", json={
            "username": "lead_investigator",
            "password": "AivoaPass2026!"
        })
        token = login_res.json()["access_token"]

        me_res = await ac.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me_res.status_code == 200
        assert me_res.json()["username"] == "lead_investigator"
        assert me_res.json()["role"] == "INVESTIGATOR"

# -------------------------------------------------------------
# Test 4: Reject unauthenticated profile access with 401
# -------------------------------------------------------------
@pytest.mark.asyncio
async def test_4_get_me_missing_token():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/api/v1/auth/me")
        assert res.status_code == 401

# -------------------------------------------------------------
# Test 5: Reject investigations list access without token (401)
# -------------------------------------------------------------
@pytest.mark.asyncio
async def test_5_investigations_list_requires_auth():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/api/v1/investigations/")
        assert res.status_code == 401

# -------------------------------------------------------------
# Test 6: Investigation creation sets lead_investigator_id
# -------------------------------------------------------------
@pytest.mark.asyncio
async def test_6_investigation_creation_sets_lead_investigator():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        login_res = await ac.post("/api/v1/auth/login", json={
            "username": "lead_investigator",
            "password": "AivoaPass2026!"
        })
        token = login_res.json()["access_token"]
        user_id = login_res.json()["user_id"]

        create_res = await ac.post(
            "/api/v1/investigations/",
            headers={"Authorization": f"Bearer {token}"},
            json={"title": "Ownership Binding Test Investigation"}
        )
        assert create_res.status_code == 200, create_res.text
        inv_data = create_res.json()
        assert inv_data["lead_investigator_id"] == user_id

# -------------------------------------------------------------
# Test 7: Investigation isolation (403 for other users)
# -------------------------------------------------------------
@pytest.mark.asyncio
async def test_7_investigation_isolation_forbidden_for_other_user():
    user_a = await get_or_create_user("inv_user_a", "INVESTIGATOR", "Dr. User A")
    user_b = await get_or_create_user("inv_user_b", "INVESTIGATOR", "Dr. User B")

    token_a = create_access_token({"sub": user_a.username, "role": user_a.role, "user_id": user_a.id})
    token_b = create_access_token({"sub": user_b.username, "role": user_b.role, "user_id": user_b.id})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # User A creates investigation
        res_a = await ac.post(
            "/api/v1/investigations/",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"title": "User A Private Investigation"}
        )
        assert res_a.status_code == 200
        inv_id = res_a.json()["id"]

        # User B attempts GET on User A's investigation -> 403 Forbidden
        res_b_get = await ac.get(
            f"/api/v1/investigations/{inv_id}",
            headers={"Authorization": f"Bearer {token_b}"}
        )
        assert res_b_get.status_code == 403

        # User B attempts PUT on User A's investigation -> 403 Forbidden
        res_b_put = await ac.put(
            f"/api/v1/investigations/{inv_id}",
            headers={"Authorization": f"Bearer {token_b}"},
            json={"title": "Tampered Title"}
        )
        assert res_b_put.status_code == 403

# -------------------------------------------------------------
# Test 8: Evidence creation requires investigation ownership
# -------------------------------------------------------------
@pytest.mark.asyncio
async def test_8_evidence_creation_requires_investigation_ownership():
    user_a = await get_or_create_user("inv_user_a", "INVESTIGATOR", "Dr. User A")
    user_b = await get_or_create_user("inv_user_b", "INVESTIGATOR", "Dr. User B")

    token_a = create_access_token({"sub": user_a.username, "role": user_a.role, "user_id": user_a.id})
    token_b = create_access_token({"sub": user_b.username, "role": user_b.role, "user_id": user_b.id})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res_a = await ac.post(
            "/api/v1/investigations/",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"title": "User A Evidence Ownership Test"}
        )
        inv_id = res_a.json()["id"]

        # User B attempts manual evidence creation on User A's investigation -> 403
        res_b_man = await ac.post(
            f"/api/v1/investigations/{inv_id}/evidences/manual",
            headers={"Authorization": f"Bearer {token_b}"},
            json={"title": "Unauthorized Evidence", "evidence_type": "LOG_ENTRY", "extracted_text": "Sample text"}
        )
        assert res_b_man.status_code == 403

        # User B attempts file upload on User A's investigation -> 403
        sample_pdf = b"%PDF-1.4\nSample Evidence PDF"
        res_b_upload = await ac.post(
            f"/api/v1/investigations/{inv_id}/evidences/upload",
            headers={"Authorization": f"Bearer {token_b}"},
            files={"file": ("unauth.pdf", sample_pdf, "application/pdf")},
            data={"title": "Unauthorized File"}
        )
        assert res_b_upload.status_code == 403

# -------------------------------------------------------------
# Test 9: Evidence download requires auth
# -------------------------------------------------------------
@pytest.mark.asyncio
async def test_9_evidence_download_requires_auth():
    user_a = await get_or_create_user("inv_user_a", "INVESTIGATOR", "Dr. User A")
    token_a = create_access_token({"sub": user_a.username, "role": user_a.role, "user_id": user_a.id})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res_a = await ac.post(
            "/api/v1/investigations/",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"title": "Download Auth Test Investigation"}
        )
        inv_id = res_a.json()["id"]

        sample_pdf = b"%PDF-1.4\nSample Download Evidence PDF"
        upload_res = await ac.post(
            f"/api/v1/investigations/{inv_id}/evidences/upload",
            headers={"Authorization": f"Bearer {token_a}"},
            files={"file": ("evidence_auth.pdf", sample_pdf, "application/pdf")},
            data={"title": "Auth Protected Evidence"}
        )
        ev_id = upload_res.json()["id"]

        # Download without Authorization header -> 401
        dl_res = await ac.get(f"/api/v1/evidences/{ev_id}/download")
        assert dl_res.status_code == 401

# -------------------------------------------------------------
# Test 10: Evidence download isolation
# -------------------------------------------------------------
@pytest.mark.asyncio
async def test_10_evidence_download_isolation():
    user_a = await get_or_create_user("inv_user_a", "INVESTIGATOR", "Dr. User A")
    user_b = await get_or_create_user("inv_user_b", "INVESTIGATOR", "Dr. User B")

    token_a = create_access_token({"sub": user_a.username, "role": user_a.role, "user_id": user_a.id})
    token_b = create_access_token({"sub": user_b.username, "role": user_b.role, "user_id": user_b.id})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res_a = await ac.post(
            "/api/v1/investigations/",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"title": "Isolation Download Test"}
        )
        inv_id = res_a.json()["id"]

        sample_pdf = b"%PDF-1.4\nConfidential Investigation Data"
        upload_res = await ac.post(
            f"/api/v1/investigations/{inv_id}/evidences/upload",
            headers={"Authorization": f"Bearer {token_a}"},
            files={"file": ("confidential.pdf", sample_pdf, "application/pdf")},
            data={"title": "Confidential Report"}
        )
        ev_id = upload_res.json()["id"]

        # User B attempts to download User A's evidence -> 403 Forbidden
        dl_res_b = await ac.get(
            f"/api/v1/evidences/{ev_id}/download",
            headers={"Authorization": f"Bearer {token_b}"}
        )
        assert dl_res_b.status_code == 403

        # User A downloads own evidence -> 200 OK
        dl_res_a = await ac.get(
            f"/api/v1/evidences/{ev_id}/download",
            headers={"Authorization": f"Bearer {token_a}"}
        )
        assert dl_res_a.status_code == 200
        assert dl_res_a.content == sample_pdf

# -------------------------------------------------------------
# Test 11: Evidence verification requires auth
# -------------------------------------------------------------
@pytest.mark.asyncio
async def test_11_evidence_verification_requires_auth():
    user_a = await get_or_create_user("inv_user_a", "INVESTIGATOR", "Dr. User A")
    token_a = create_access_token({"sub": user_a.username, "role": user_a.role, "user_id": user_a.id})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res_a = await ac.post(
            "/api/v1/investigations/",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"title": "Verify Requires Auth Investigation"}
        )
        inv_id = res_a.json()["id"]

        ev_res = await ac.post(
            f"/api/v1/investigations/{inv_id}/evidences/manual",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"title": "Evidence To Verify", "evidence_type": "LOG_ENTRY", "extracted_text": "Sample text"}
        )
        ev_id = ev_res.json()["id"]

        # Attempt verify without auth -> 401
        verify_res = await ac.post(
            f"/api/v1/evidences/{ev_id}/verify",
            json={"investigator_name": "Anonymous", "verification_notes": "Attempt without token"}
        )
        assert verify_res.status_code == 401

# -------------------------------------------------------------
# Test 12: Root cause confirmation requires auth
# -------------------------------------------------------------
@pytest.mark.asyncio
async def test_12_root_cause_confirmation_requires_auth():
    user_a = await get_or_create_user("inv_user_a", "INVESTIGATOR", "Dr. User A")
    token_a = create_access_token({"sub": user_a.username, "role": user_a.role, "user_id": user_a.id})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res_a = await ac.post(
            "/api/v1/investigations/",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"title": "RC Confirm Requires Auth"}
        )
        inv_id = res_a.json()["id"]

        async with get_session() as session:
            rc = RootCause(
                investigation_id=inv_id,
                cause_statement="Cooling jacket thermal expansion failure",
                category="EQUIPMENT_FAILURE",
                status="PROPOSED"
            )
            session.add(rc)
            await session.commit()
            await session.refresh(rc)
            rc_id = rc.id

        # Attempt confirmation without token -> 401
        confirm_res = await ac.post(
            f"/api/v1/root-causes/{rc_id}/confirm",
            json={"investigator_name": "Anonymous", "justification": "Trying unauthenticated confirm"}
        )
        assert confirm_res.status_code == 401

# -------------------------------------------------------------
# Test 13: Root cause confirmation identity from token
# -------------------------------------------------------------
@pytest.mark.asyncio
async def test_13_root_cause_confirmation_identity_from_token():
    user_a = await get_or_create_user("inv_user_a", "INVESTIGATOR", "Dr. User A")
    token_a = create_access_token({"sub": user_a.username, "role": user_a.role, "user_id": user_a.id})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res_a = await ac.post(
            "/api/v1/investigations/",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"title": "RC Identity Binding Test"}
        )
        inv_id = res_a.json()["id"]

        # Create verified supporting evidence and root cause
        async with get_session() as session:
            ev = Evidence(
                investigation_id=inv_id,
                title="Verified Sensor Log",
                evidence_type="LOG_ENTRY",
                classification="PRIMARY_SOURCE",
                extracted_text="Temperature spike confirmed",
                is_verified=True,
                verified_by=user_a.full_name
            )
            session.add(ev)
            await session.flush()

            rc = RootCause(
                investigation_id=inv_id,
                cause_statement="Cooling jacket thermal failure",
                category="EQUIPMENT_FAILURE",
                status="PROPOSED"
            )
            session.add(rc)
            await session.flush()

            link = RootCauseEvidenceLink(
                root_cause_id=rc.id,
                evidence_id=ev.id,
                relationship_type="SUPPORTING",
                relevance_explanation="Direct empirical proof"
            )
            session.add(link)
            await session.commit()
            rc_id = rc.id

        # User QA confirms RC but supplies a spoofed name in the JSON body
        user_qa = await get_or_create_user("qa_user_test13", "QA_APPROVER", "Dr. QA Reviewer Test 13")
        token_qa = create_access_token({"sub": user_qa.username, "role": user_qa.role, "user_id": user_qa.id})

        confirm_res = await ac.post(
            f"/api/v1/root-causes/{rc_id}/confirm",
            headers={"Authorization": f"Bearer {token_qa}"},
            json={
                "investigator_name": "Spoofed Impostor Name",
                "justification": "Valid empirical justification verified by investigator"
            }
        )
        assert confirm_res.status_code == 200, confirm_res.text
        rc_data = confirm_res.json()
        assert rc_data["status"] == "CONFIRMED"
        # Verify identity is bound to User QA, not the spoofed string
        assert user_qa.full_name in rc_data["investigator_notes"]
        assert f"User ID #{user_qa.id}" in rc_data["investigator_notes"]
        assert "Spoofed Impostor Name" not in rc_data["investigator_notes"]

# -------------------------------------------------------------
# Test 14: QA approval requires QA_APPROVER role
# -------------------------------------------------------------
@pytest.mark.asyncio
async def test_14_qa_approval_requires_qa_role():
    user_a = await get_or_create_user("inv_user_a", "INVESTIGATOR", "Dr. User A")
    token_a = create_access_token({"sub": user_a.username, "role": user_a.role, "user_id": user_a.id})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res_a = await ac.post(
            "/api/v1/investigations/",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"title": "QA Role Restriction Test"}
        )
        inv_id = res_a.json()["id"]

        # User A (INVESTIGATOR) attempts to approve investigation -> 403 Forbidden
        approve_res = await ac.post(
            f"/api/v1/investigations/{inv_id}/approve",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"comments": "Investigator attempting self-approval"}
        )
        assert approve_res.status_code == 403
        assert "QA_APPROVER or ADMIN" in approve_res.json()["detail"]

# -------------------------------------------------------------
# Test 15: QA approval success for QA_APPROVER
# -------------------------------------------------------------
@pytest.mark.asyncio
async def test_15_qa_approval_success_for_qa_approver():
    user_a = await get_or_create_user("inv_user_a", "INVESTIGATOR", "Dr. User A")
    user_qa = await get_or_create_user("qa_director", "QA_APPROVER", "Dr. Elena Rostova")

    token_a = create_access_token({"sub": user_a.username, "role": user_a.role, "user_id": user_a.id})
    token_qa = create_access_token({"sub": user_qa.username, "role": user_qa.role, "user_id": user_qa.id})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res_a = await ac.post(
            "/api/v1/investigations/",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"title": "Formal QA Approval Dossier"}
        )
        inv_id = res_a.json()["id"]

        # QA Approver approves the investigation
        approve_res = await ac.post(
            f"/api/v1/investigations/{inv_id}/approve",
            headers={"Authorization": f"Bearer {token_qa}"},
            json={"comments": "Formally approved and signed off under cGMP requirements."}
        )
        assert approve_res.status_code == 200, approve_res.text
        inv_data = approve_res.json()
        assert inv_data["is_approved"] is True
        assert inv_data["qa_approver_id"] == user_qa.id
        assert inv_data["qa_approver"] == user_qa.full_name
        assert inv_data["status"] in ("APPROVED", "CLOSED")

# -------------------------------------------------------------
# Test 16: Audit log records user_id and user_name
# -------------------------------------------------------------
@pytest.mark.asyncio
async def test_16_audit_log_records_user_id():
    user_a = await get_or_create_user("inv_user_a", "INVESTIGATOR", "Dr. User A")
    token_a = create_access_token({"sub": user_a.username, "role": user_a.role, "user_id": user_a.id})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res_a = await ac.post(
            "/api/v1/investigations/",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"title": "Audit User ID Test Investigation"}
        )
        inv_id = res_a.json()["id"]

        # Create manual evidence
        ev_res = await ac.post(
            f"/api/v1/investigations/{inv_id}/evidences/manual",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"title": "Audit Evidence Record", "evidence_type": "LOG_ENTRY", "extracted_text": "Calibration passed"}
        )
        assert ev_res.status_code == 200

        # Verify audit logs in database
        async with get_session() as session:
            logs_res = await session.execute(
                select(AuditLog)
                .filter(AuditLog.investigation_id == inv_id)
                .order_by(AuditLog.id.desc())
            )
            logs = logs_res.scalars().all()
            assert len(logs) >= 2
            evidence_log = next(log for log in logs if log.entity_type == "EVIDENCE")
            assert evidence_log.user_id == user_a.id
            assert evidence_log.user_name == user_a.full_name

# -------------------------------------------------------------
# Test 17: Unassigned investigation non-mutation on GET & access control
# -------------------------------------------------------------
@pytest.mark.asyncio
async def test_17_unassigned_investigation_no_mutation_and_access_control():
    # Setup users
    user_investigator = await get_or_create_user("inv_user_regular", "INVESTIGATOR", "Dr. Regular Investigator")
    user_qa = await get_or_create_user("qa_director", "QA_APPROVER", "Dr. Elena Rostova")
    user_admin = await get_or_create_user("admin_sec", "ADMIN", "System Administrator")

    token_inv = create_access_token({"sub": user_investigator.username, "role": user_investigator.role, "user_id": user_investigator.id})
    token_qa = create_access_token({"sub": user_qa.username, "role": user_qa.role, "user_id": user_qa.id})
    token_admin = create_access_token({"sub": user_admin.username, "role": user_admin.role, "user_id": user_admin.id})

    # Create unassigned legacy investigation directly in DB
    inv_num = f"INV-UNASSIGNED-{uuid.uuid4().hex[:8].upper()}"
    async with get_session() as session:
        unassigned_inv = Investigation(
            investigation_number=inv_num,
            title="Legacy Unassigned Investigation",
            lead_investigator=None,
            lead_investigator_id=None,
            status="IN_INVESTIGATION",
            stage="INTAKE"
        )
        session.add(unassigned_inv)
        await session.commit()
        await session.refresh(unassigned_inv)
        unassigned_id = unassigned_inv.id

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Ordinary investigator GET request -> 403 Forbidden
        res_inv = await ac.get(
            f"/api/v1/investigations/{unassigned_id}",
            headers={"Authorization": f"Bearer {token_inv}"}
        )
        assert res_inv.status_code == 403
        assert "not been assigned to a lead investigator" in res_inv.json()["detail"]

        # 2. Ordinary investigator child resource GET request -> 403 Forbidden
        res_child = await ac.get(
            f"/api/v1/investigations/{unassigned_id}/evidences",
            headers={"Authorization": f"Bearer {token_inv}"}
        )
        assert res_child.status_code == 403

        # 3. QA Approver GET request -> 200 OK (read-only allowed)
        res_qa = await ac.get(
            f"/api/v1/investigations/{unassigned_id}",
            headers={"Authorization": f"Bearer {token_qa}"}
        )
        assert res_qa.status_code == 200

        # Verify DB: lead_investigator_id must STILL be None (NO auto-claim mutation)
        async with get_session() as session:
            inv_db = (await session.execute(
                select(Investigation).filter(Investigation.id == unassigned_id)
            )).scalar_one()
            assert inv_db.lead_investigator_id is None, "GET request by QA must not mutate lead_investigator_id!"

        # 4. Admin GET request -> 200 OK
        res_admin = await ac.get(
            f"/api/v1/investigations/{unassigned_id}",
            headers={"Authorization": f"Bearer {token_admin}"}
        )
        assert res_admin.status_code == 200

        # Verify DB: lead_investigator_id must STILL be None
        async with get_session() as session:
            inv_db2 = (await session.execute(
                select(Investigation).filter(Investigation.id == unassigned_id)
            )).scalar_one()
            assert inv_db2.lead_investigator_id is None, "GET request by Admin must not mutate lead_investigator_id!"


# -------------------------------------------------------------
# Test 18: ADMIN dedicated ownership assignment endpoint & audit
# -------------------------------------------------------------
@pytest.mark.asyncio
async def test_18_admin_ownership_assignment_endpoint():
    user_investigator = await get_or_create_user("inv_user_assignee", "INVESTIGATOR", "Dr. Assigned Investigator")
    user_qa = await get_or_create_user("qa_director", "QA_APPROVER", "Dr. Elena Rostova")
    user_admin = await get_or_create_user("admin_sec", "ADMIN", "System Administrator")

    token_inv = create_access_token({"sub": user_investigator.username, "role": user_investigator.role, "user_id": user_investigator.id})
    token_qa = create_access_token({"sub": user_qa.username, "role": user_qa.role, "user_id": user_qa.id})
    token_admin = create_access_token({"sub": user_admin.username, "role": user_admin.role, "user_id": user_admin.id})

    # Create unassigned investigation
    inv_num_assign = f"INV-ASSIGN-{uuid.uuid4().hex[:8].upper()}"
    async with get_session() as session:
        unassigned_inv = Investigation(
            investigation_number=inv_num_assign,
            title="Unassigned For Admin Assignment Test",
            lead_investigator=None,
            lead_investigator_id=None,
            status="IN_INVESTIGATION",
            stage="INTAKE"
        )
        session.add(unassigned_inv)
        await session.commit()
        await session.refresh(unassigned_inv)
        target_inv_id = unassigned_inv.id

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Non-admin attempts to assign owner -> 403 Forbidden
        res_forbidden = await ac.post(
            f"/api/v1/investigations/{target_inv_id}/assign-owner",
            headers={"Authorization": f"Bearer {token_qa}"},
            json={"new_investigator_id": user_investigator.id, "reason": "QA attempted assignment"}
        )
        assert res_forbidden.status_code == 403
        assert "Only administrators can assign investigation ownership" in res_forbidden.json()["detail"]

        # Admin assigns owner -> 200 OK
        res_assigned = await ac.post(
            f"/api/v1/investigations/{target_inv_id}/assign-owner",
            headers={"Authorization": f"Bearer {token_admin}"},
            json={
                "new_investigator_id": user_investigator.id,
                "reason": "Assigning lead role to qualified investigator"
            }
        )
        assert res_assigned.status_code == 200, res_assigned.text
        data = res_assigned.json()
        assert data["lead_investigator_id"] == user_investigator.id
        assert data["lead_investigator"] == user_investigator.full_name

        # Verify DB audit log
        async with get_session() as session:
            logs = (await session.execute(
                select(AuditLog)
                .filter(AuditLog.investigation_id == target_inv_id)
                .order_by(AuditLog.id.desc())
            )).scalars().all()
            assign_log = next((l for l in logs if l.action == "OWNERSHIP_ASSIGNED"), None)
            assert assign_log is not None, "Audit log for OWNERSHIP_ASSIGNED must be created"
            assert assign_log.user_id == user_admin.id
            assert assign_log.user_name == user_admin.full_name
            assert "Dr. Assigned Investigator" in assign_log.change_summary
            assert "Assigning lead role" in assign_log.change_summary

        # Now the newly assigned investigator CAN access the investigation
        res_inv_now = await ac.get(
            f"/api/v1/investigations/{target_inv_id}",
            headers={"Authorization": f"Bearer {token_inv}"}
        )
        assert res_inv_now.status_code == 200


# -------------------------------------------------------------
# Test 19: CORS explicit allowlist & wildcard rejection
# -------------------------------------------------------------
@pytest.mark.asyncio
async def test_19_cors_allowlist_and_wildcard_rejection():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Preflight from allowed origin http://localhost:5173
        res_5173 = await ac.options(
            "/api/v1/auth/login",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            }
        )
        assert res_5173.status_code == 200
        assert res_5173.headers.get("access-control-allow-origin") == "http://localhost:5173"
        assert res_5173.headers.get("access-control-allow-credentials") == "true"
        # Must NEVER be wildcard '*' when credentials are true
        assert res_5173.headers.get("access-control-allow-origin") != "*"

        # Preflight from allowed origin http://localhost:3000
        res_3000 = await ac.options(
            "/api/v1/auth/login",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            }
        )
        assert res_3000.status_code == 200
        assert res_3000.headers.get("access-control-allow-origin") == "http://localhost:3000"

        # Preflight from untrusted origin -> Not allowed
        res_untrusted = await ac.options(
            "/api/v1/auth/login",
            headers={
                "Origin": "http://malicious-external-site.com",
                "Access-Control-Request-Method": "POST",
            }
        )
        # FastAPIs CORSMiddleware does not set Access-Control-Allow-Origin for untrusted origins
        assert res_untrusted.headers.get("access-control-allow-origin") != "http://malicious-external-site.com"


import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from datetime import datetime
from sqlalchemy.future import select

from app.main import app
from app.core.database import init_db, get_engine
from app.core.security import create_access_token
from app.models.audit import User, AuditLog
from app.models.evidence import Evidence
from app.models.root_cause import RootCause
from app.models.five_whys import FiveWhysStep
from app.models.fishbone import FishboneCause

def get_session():
    get_engine()
    from app.core import database
    return database.AsyncSessionLocal()


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
            email=f"{username}@pharmatest2d23.internal",
            full_name=full_name,
            role=role,
            is_active=is_active
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


def get_auth_client(transport, user_id=1, username="lead_investigator", role="INVESTIGATOR"):
    token = create_access_token({"sub": username, "role": role, "user_id": user_id})
    return AsyncClient(transport=transport, base_url="http://test", headers={"Authorization": f"Bearer {token}"})

def get_qa_client(transport, user_id=2, username="qa_director"):
    return get_auth_client(transport, user_id=user_id, username=username, role="QA_APPROVER")

def get_admin_client(transport, user_id=99, username="admin_user"):
    return get_auth_client(transport, user_id=user_id, username=username, role="ADMIN")


@pytest.mark.asyncio
async def test_priority_1_legacy_null_uploader_evidence_fail_closed():
    """
    Priority 1: Legacy Evidence Fail-Closed Authorization Policy (Tests 1, 2, 3, 4, 7, 8, 9, 10)
    1. Legacy NULL-uploader evidence: ordinary investigator denied (HTTP 403).
    2. Legacy NULL-uploader evidence: assigned lead investigator denied (HTTP 403).
    3. Legacy NULL-uploader evidence: authorized QA approver succeeds (HTTP 200).
    4. Legacy NULL-uploader evidence: authorized admin succeeds (HTTP 200).
    7. Unauthorized non-owner cannot verify legacy evidence (HTTP 403).
    8. Client-forged reviewer attribution is ignored (server identity bound).
    9. Successful verification creates the expected audit event and server-derived attribution.
    10. Repeated verification follows existing intended state-transition behavior.
    """
    await init_db()
    transport = ASGITransport(app=app)

    # Provision distinct test users with isolated IDs and roles
    lead_user = await create_test_user("lead_inv_2d23", role="INVESTIGATOR", full_name="Dr. Lead Investigator")
    other_inv_user = await create_test_user("other_inv_2d23", role="INVESTIGATOR", full_name="Dr. Other Investigator")
    qa_user = await create_test_user("qa_approver_2d23", role="QA_APPROVER", full_name="Dr. Senior QA Approver")
    admin_user = await create_test_user("admin_user_2d23", role="ADMIN", full_name="System Administrator")

    lead_ac = get_auth_client(transport, user_id=lead_user.id, username=lead_user.username, role=lead_user.role)
    other_inv_ac = get_auth_client(transport, user_id=other_inv_user.id, username=other_inv_user.username, role=other_inv_user.role)
    qa_ac = get_qa_client(transport, user_id=qa_user.id, username=qa_user.username)
    admin_ac = get_admin_client(transport, user_id=admin_user.id, username=admin_user.username)

    # Create investigation owned by lead_user
    inv_res = await lead_ac.post("/api/v1/investigations/", json={
        "title": "Phase 2D.2.3 Legacy Evidence Test",
        "lead_investigator": lead_user.full_name
    })
    assert inv_res.status_code == 200
    inv_id = inv_res.json()["id"]

    # Insert a genuine legacy Evidence record directly into PostgreSQL with uploaded_by_user_id = NULL
    async with get_session() as session:
        legacy_ev = Evidence(
            investigation_id=inv_id,
            title="Legacy SCADA Strip Chart 2024",
            evidence_type="SENSOR_LOG",
            classification="PRIMARY_SOURCE",
            extracted_text="Historical sensor log recorded before user attribution migration.",
            is_verified=False,
            verified_by=None,
            verified_by_user_id=None,
            uploaded_by_user_id=None,  # Legacy NULL uploader
            is_archived=False
        )
        session.add(legacy_ev)
        await session.commit()
        await session.refresh(legacy_ev)
        legacy_ev_id = legacy_ev.id

    # Test 1 & 7: Ordinary non-assigned investigator denied -> HTTP 403 Forbidden
    other_res = await other_inv_ac.post(f"/api/v1/evidences/{legacy_ev_id}/verify", json={
        "investigator_name": "Dr. Other Investigator",
        "verification_notes": "Attempting verification as non-owner ordinary investigator."
    })
    assert other_res.status_code == 403
    assert "permission to access or modify" in other_res.json()["detail"].lower() or "forbidden" in other_res.json()["detail"].lower()

    # Test 2: Assigned lead investigator denied -> HTTP 403 Forbidden (Fail-Closed Governance)
    lead_res = await lead_ac.post(f"/api/v1/evidences/{legacy_ev_id}/verify", json={
        "investigator_name": "Dr. Lead Investigator",
        "verification_notes": "Assigned lead investigator attempting to verify legacy record."
    })
    assert lead_res.status_code == 403
    assert "unattributable legacy evidence" in lead_res.json()["detail"].lower() or "requires explicit qa_approver or admin" in lead_res.json()["detail"].lower()

    # Test 8 & 3 & 9: Authorized QA Approver succeeds -> HTTP 200 OK (Client-forged name ignored)
    qa_res = await qa_ac.post(f"/api/v1/evidences/{legacy_ev_id}/verify", json={
        "investigator_name": "Malicious Spoofed Name",
        "verification_notes": "Independent QA verification of historical strip chart."
    })
    assert qa_res.status_code == 200
    ev_verified = qa_res.json()
    assert ev_verified["is_verified"] is True
    # Reviewer attribution must be bound to authenticated QA user, NOT the spoofed name!
    assert qa_user.full_name in ev_verified["verified_by"]
    assert "Malicious Spoofed Name" not in ev_verified["verified_by"]
    assert ev_verified["verified_by_user_id"] == qa_user.id
    assert ev_verified["uploaded_by_user_id"] is None  # Historical uploader is never fabricated

    # Test 9: Verify audit log entry created with server-derived attribution
    async with get_session() as session:
        audit_res = await session.execute(
            select(AuditLog)
            .filter(AuditLog.investigation_id == inv_id, AuditLog.entity_id == str(legacy_ev_id), AuditLog.action == "VERIFIED")
            .order_by(AuditLog.id.desc())
        )
        audit_entry = audit_res.scalars().first()
        assert audit_entry is not None
        assert audit_entry.user_id == qa_user.id
        assert audit_entry.user_name == qa_user.full_name

    # Test 10: Repeated verification follows existing intended state-transition behavior
    repeat_res = await qa_ac.post(f"/api/v1/evidences/{legacy_ev_id}/verify", json={
        "investigator_name": "Dr. Senior QA Approver",
        "verification_notes": "Secondary qualification review note."
    })
    assert repeat_res.status_code == 200
    assert repeat_res.json()["is_verified"] is True
    assert "Secondary qualification review note" in repeat_res.json()["investigator_notes"]

    # Test 4: Authorized Admin can also verify a legacy record on another investigation
    inv_admin_res = await admin_ac.post("/api/v1/investigations/", json={
        "title": "Admin Investigation",
        "lead_investigator": admin_user.full_name
    })
    admin_inv_id = inv_admin_res.json()["id"]

    async with get_session() as session:
        legacy_ev_2 = Evidence(
            investigation_id=admin_inv_id,
            title="Legacy Calibration Sheet 2023",
            evidence_type="CALIBRATION_CERT",
            extracted_text="Older calibration certificate without recorded uploader.",
            is_verified=False,
            uploaded_by_user_id=None
        )
        session.add(legacy_ev_2)
        await session.commit()
        await session.refresh(legacy_ev_2)
        legacy_ev_2_id = legacy_ev_2.id

    admin_verify_res = await admin_ac.post(f"/api/v1/evidences/{legacy_ev_2_id}/verify", json={
        "investigator_name": "System Administrator",
        "verification_notes": "Admin verified under cGMP governance."
    })
    assert admin_verify_res.status_code == 200
    assert admin_verify_res.json()["is_verified"] is True
    assert admin_verify_res.json()["verified_by_user_id"] == admin_user.id


@pytest.mark.asyncio
async def test_priority_1_attributable_evidence_separation_of_duties():
    """
    Priority 1: Attributable Evidence Authorization Policy (Tests 5, 6)
    5. Attributable evidence: uploader denied (HTTP 403).
    6. Attributable evidence: eligible independent reviewer succeeds (HTTP 200).
    """
    await init_db()
    transport = ASGITransport(app=app)

    operator_user = await create_test_user("operator_inv_2d23", role="INVESTIGATOR", full_name="John Doe (Lead Investigator)")
    lead_user = await create_test_user("reviewer_lead_2d23", role="INVESTIGATOR", full_name="Dr. Marcus Lead")
    qa_user = await create_test_user("qa_reviewer_2d23", role="QA_APPROVER", full_name="Dr. Elena QA")

    operator_ac = get_auth_client(transport, user_id=operator_user.id, username=operator_user.username, role=operator_user.role)
    qa_ac = get_qa_client(transport, user_id=qa_user.id, username=qa_user.username)

    inv_res = await operator_ac.post("/api/v1/investigations/", json={"title": "Attributable Evidence Inv"})
    inv_id = inv_res.json()["id"]

    # Operator uploads attributable evidence
    upload_res = await operator_ac.post(
        f"/api/v1/investigations/{inv_id}/evidences/upload",
        data={"title": "Centrifuge Vibration Telemetry", "evidence_type": "SENSOR_LOG"},
        files={"file": ("vibration.txt", b"Centrifuge peak RMS 4.2 mm/s at 14:00.", "text/plain")}
    )
    assert upload_res.status_code == 200
    ev_data = upload_res.json()
    ev_id = ev_data["id"]
    assert ev_data["uploaded_by_user_id"] == operator_user.id

    # Test 5: Original uploader cannot verify their own evidence -> HTTP 403 Forbidden
    self_verify = await operator_ac.post(f"/api/v1/evidences/{ev_id}/verify", json={
        "investigator_name": "John Doe",
        "verification_notes": "Attempting self verification."
    })
    assert self_verify.status_code == 403
    assert "separation of duties" in self_verify.json()["detail"].lower()

    # Test 6: Eligible independent reviewer (QA Approver) succeeds -> HTTP 200 OK
    qa_verify = await qa_ac.post(f"/api/v1/evidences/{ev_id}/verify", json={
        "investigator_name": "Dr. Elena QA",
        "verification_notes": "Independent verification by QA."
    })
    assert qa_verify.status_code == 200
    assert qa_verify.json()["is_verified"] is True
    assert qa_verify.json()["verified_by_user_id"] == qa_user.id


@pytest.mark.asyncio
async def test_priority_2_five_whys_provenance_concurrency_locking():
    """
    Priority 2: Provenance Concurrency Safety (Five Whys)
    Verifies that concurrent creation of a Root Cause referencing a Five Whys step
    and deletion of that Five Whys step cannot produce a dangling provenance reference.
    PostgreSQL SELECT ... FOR UPDATE serializes the transactions:
    - If deletion commits first, creation is safely rejected with HTTP 400.
    - If creation commits first, deletion is safely rejected with HTTP 409 Conflict.
    - Under no circumstances does a Root Cause point to a non-existent step.
    """
    await init_db()
    transport = ASGITransport(app=app)
    user = await create_test_user("why_concur_user", role="ADMIN", full_name="Concurrency Investigator")
    ac = get_admin_client(transport, user_id=user.id, username=user.username)

    inv_res = await ac.post("/api/v1/investigations/", json={"title": "Whys Concurrency Investigation"})
    inv_id = inv_res.json()["id"]

    # Create Five Whys step
    why_res = await ac.post(f"/api/v1/investigations/{inv_id}/five-whys", json={
        "step_number": 1,
        "question": "Why did the chiller freeze?",
        "answer": "Flow valve remained closed during cooling demand."
    })
    assert why_res.status_code == 200
    step_id = why_res.json()["id"]

    # Concurrent actions: create root cause referencing step vs delete step
    async def do_create_rc():
        return await ac.post(f"/api/v1/investigations/{inv_id}/root-causes", json={
            "cause_statement": "Flow valve jammed shut due to actuator freeze.",
            "source_type": "FIVE_WHYS",
            "source_id": step_id
        })

    async def do_delete_step():
        return await ac.delete(f"/api/v1/five-whys/{step_id}")

    res1, res2 = await asyncio.gather(do_create_rc(), do_delete_step(), return_exceptions=True)
    status_codes = [res1.status_code, res2.status_code]

    # Exactly one action must succeed (200), and the competing action must be safely rejected (400 or 409)
    # Never both 200!
    assert not (res1.status_code == 200 and res2.status_code == 200), f"Both cannot succeed: {status_codes}"
    assert 200 in status_codes, f"At least one must succeed: {status_codes}"
    if res1.status_code == 200:
        # Creation won: deletion must have been blocked by active dependency guard (409 Conflict)
        assert res2.status_code == 409, f"Deletion should be blocked with 409, got {res2.status_code}"
    else:
        # Deletion won: creation must have been blocked because step was deleted (400 Bad Request)
        assert res1.status_code == 400, f"Creation should fail with 400, got {res1.status_code}"
        assert res2.status_code == 200

    # Verify database integrity: if Root Cause exists, its referenced step MUST exist
    async with get_session() as session:
        rc_res = await session.execute(
            select(RootCause).filter(RootCause.investigation_id == inv_id, RootCause.source_type == "FIVE_WHYS", RootCause.source_id == step_id)
        )
        rc = rc_res.scalar_one_or_none()
        step_res = await session.execute(select(FiveWhysStep).filter(FiveWhysStep.id == step_id))
        step = step_res.scalar_one_or_none()
        if rc is not None:
            assert step is not None, "Dangling provenance detected! Root cause exists but referenced step was deleted!"


@pytest.mark.asyncio
async def test_priority_2_fishbone_provenance_concurrency_locking():
    """
    Priority 2: Provenance Concurrency Safety (Fishbone)
    Verifies that concurrent creation of a Root Cause referencing a Fishbone cause
    and deletion of that Fishbone cause cannot produce a dangling provenance reference.
    """
    await init_db()
    transport = ASGITransport(app=app)
    user = await create_test_user("fish_concur_user", role="ADMIN", full_name="Fishbone Concurrency Investigator")
    ac = get_admin_client(transport, user_id=user.id, username=user.username)

    inv_res = await ac.post("/api/v1/investigations/", json={"title": "Fishbone Concurrency Investigation"})
    inv_id = inv_res.json()["id"]

    # Create Fishbone cause
    cause_res = await ac.post(f"/api/v1/investigations/{inv_id}/fishbone", json={
        "category": "MACHINE",
        "cause_description": "Compressor inlet filter clogged with particulate.",
        "status": "HYPOTHESIS"
    })
    assert cause_res.status_code == 200
    cause_id = cause_res.json()["id"]

    async def do_create_rc():
        return await ac.post(f"/api/v1/investigations/{inv_id}/root-causes", json={
            "cause_statement": "Inlet air starvation caused compressor trip.",
            "source_type": "FISHBONE",
            "source_id": cause_id
        })

    async def do_delete_cause():
        return await ac.delete(f"/api/v1/fishbone/{cause_id}")

    res1, res2 = await asyncio.gather(do_create_rc(), do_delete_cause(), return_exceptions=True)
    status_codes = [res1.status_code, res2.status_code]

    assert not (res1.status_code == 200 and res2.status_code == 200), f"Both cannot succeed: {status_codes}"
    assert 200 in status_codes, f"At least one must succeed: {status_codes}"
    if res1.status_code == 200:
        assert res2.status_code == 409, f"Deletion should be blocked with 409, got {res2.status_code}"
    else:
        assert res1.status_code == 400, f"Creation should fail with 400, got {res1.status_code}"
        assert res2.status_code == 200

    async with get_session() as session:
        rc_res = await session.execute(
            select(RootCause).filter(RootCause.investigation_id == inv_id, RootCause.source_type == "FISHBONE", RootCause.source_id == cause_id)
        )
        rc = rc_res.scalar_one_or_none()
        cause_db = await session.execute(select(FishboneCause).filter(FishboneCause.id == cause_id))
        c_obj = cause_db.scalar_one_or_none()
        if rc is not None:
            assert c_obj is not None, "Dangling provenance detected! Root cause exists but referenced fishbone cause was deleted!"

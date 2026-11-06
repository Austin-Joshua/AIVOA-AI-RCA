import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from datetime import datetime
from sqlalchemy.future import select

from app.main import app
from app.core.database import init_db, get_engine
from app.core.security import create_access_token
from app.models.audit import User, AuditLog
from app.models.investigation import Investigation
from app.models.root_cause import RootCause
from app.models.capa import CapaAction


def get_session():
    get_engine()
    from app.core import database
    return database.AsyncSessionLocal()


async def create_user(username: str, role: str = "INVESTIGATOR", full_name: str = "Test User") -> User:
    async with get_session() as session:
        res = await session.execute(select(User).where(User.username == username))
        existing = res.scalars().first()
        if existing:
            existing.role = role
            existing.full_name = full_name
            existing.is_active = True
            await session.commit()
            await session.refresh(existing)
            return existing
        user = User(
            username=username,
            email=f"{username}@pharmatest-capa.internal",
            full_name=full_name,
            role=role,
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


def get_client(transport, user: User):
    token = create_access_token({"sub": user.username, "role": user.role, "user_id": user.id})
    return AsyncClient(transport=transport, base_url="http://test", headers={"Authorization": f"Bearer {token}"})


async def setup_investigation_and_causes():
    """Create test users, investigations, and root causes."""
    inv_user = await create_user("capa_inv_lead", "INVESTIGATOR", "Lead Inv Lead")
    qa_user = await create_user("capa_qa_approver", "QA_APPROVER", "Dr. QA Reviewer")
    qa_lead_user = await create_user("capa_qa_lead_dual", "QA_APPROVER", "QA Dual Lead")
    admin_user = await create_user("capa_admin", "ADMIN", "System Admin")
    other_inv_user = await create_user("capa_other_inv", "INVESTIGATOR", "Other Inv")

    async with get_session() as session:
        inv1 = Investigation(
            investigation_number=f"INV-CAPA-{datetime.utcnow().timestamp()}-1",
            title="Batch CV-301 Contamination RCA",
            status="IN_INVESTIGATION",
            stage="CAPA",
            lead_investigator="Lead Inv Lead",
            lead_investigator_id=inv_user.id,
        )
        inv2 = Investigation(
            investigation_number=f"INV-CAPA-{datetime.utcnow().timestamp()}-2",
            title="Unrelated Line B Temperature Anomaly",
            status="IN_INVESTIGATION",
            stage="CAPA",
            lead_investigator="Other Inv",
            lead_investigator_id=other_inv_user.id,
        )
        # Investigation where lead investigator is also a QA Approver
        inv3 = Investigation(
            investigation_number=f"INV-CAPA-{datetime.utcnow().timestamp()}-3",
            title="Line C Sterilization Deviation",
            status="IN_INVESTIGATION",
            stage="CAPA",
            lead_investigator="QA Dual Lead",
            lead_investigator_id=qa_lead_user.id,
        )
        session.add_all([inv1, inv2, inv3])
        await session.commit()
        await session.refresh(inv1)
        await session.refresh(inv2)
        await session.refresh(inv3)

        # Root causes for inv1
        rc1 = RootCause(
            investigation_id=inv1.id,
            cause_statement="Diaphragm micro-tear due to thermal fatigue in CV-301 valve.",
            category="EQUIPMENT_FAILURE",
            is_primary=True,
            status="CONFIRMED",
            rationale="SEM micrograph and maintenance logs confirm elastomeric stress fracture.",
        )
        rc_rejected = RootCause(
            investigation_id=inv1.id,
            cause_statement="Operator error in torque application during assembly.",
            category="HUMAN_ERROR",
            is_primary=False,
            status="REJECTED",
            rationale="Torque wrench logs showed calibration was current and values within spec.",
        )
        # Root cause for inv2 (cross-investigation target)
        rc_inv2 = RootCause(
            investigation_id=inv2.id,
            cause_statement="RTD sensor drift in Line B chiller.",
            category="EQUIPMENT_FAILURE",
            is_primary=True,
            status="CONFIRMED",
            rationale="Calibration bath test revealed -1.8C deviation.",
        )
        session.add_all([rc1, rc_rejected, rc_inv2])
        await session.commit()
        await session.refresh(rc1)
        await session.refresh(rc_rejected)
        await session.refresh(rc_inv2)

    return {
        "inv_user": inv_user,
        "qa_user": qa_user,
        "qa_lead_user": qa_lead_user,
        "admin_user": admin_user,
        "other_inv_user": other_inv_user,
        "inv1_id": inv1.id,
        "inv2_id": inv2.id,
        "inv3_id": inv3.id,
        "rc1_id": rc1.id,
        "rc_rejected_id": rc_rejected.id,
        "rc_inv2_id": rc_inv2.id,
    }


@pytest.mark.asyncio
async def test_01_valid_capa_creation():
    """Test 1: Valid CAPA creation starts in PROPOSED status and unverified."""
    env = await setup_investigation_and_causes()
    transport = ASGITransport(app=app)
    async with get_client(transport, env["inv_user"]) as client:
        res = await client.post(
            f"/api/v1/investigations/{env['inv1_id']}/capas",
            json={
                "action_type": "CORRECTIVE_ACTION",
                "description": "Replace all CV-301 valve diaphragms with reinforced PTFE-composite seals.",
                "rationale": "PTFE composite provides 3x higher thermal cycle durability.",
                "owner": "Maintenance Lead",
                "deadline": "14 Days",
                "effectiveness_criteria": "Zero pressure drops across 10 consecutive batches.",
                "effectiveness_review_period_days": 30,
                "root_cause_id": env["rc1_id"],
            },
        )
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["id"] is not None
        assert data["status"] == "PROPOSED"
        assert data["is_verified"] is False
        assert data["action_type"] == "CORRECTIVE_ACTION"
        assert data["root_cause_id"] == env["rc1_id"]
        assert data["owner"] == "Maintenance Lead"


@pytest.mark.asyncio
async def test_02_cross_investigation_root_cause_rejected():
    """Test 2: Cross-investigation root cause linking is rejected with HTTP 400."""
    env = await setup_investigation_and_causes()
    transport = ASGITransport(app=app)
    async with get_client(transport, env["inv_user"]) as client:
        # inv1 investigator attempts to link rc from inv2
        res = await client.post(
            f"/api/v1/investigations/{env['inv1_id']}/capas",
            json={
                "action_type": "CORRECTIVE_ACTION",
                "description": "Cross-investigation linkage attempt.",
                "root_cause_id": env["rc_inv2_id"],
            },
        )
        assert res.status_code == 400
        assert "Cross-investigation error" in res.json()["detail"]


@pytest.mark.asyncio
async def test_03_nonexistent_or_rejected_root_cause_rejected():
    """Test 3: Nonexistent or rejected root causes cannot be linked (HTTP 400)."""
    env = await setup_investigation_and_causes()
    transport = ASGITransport(app=app)
    async with get_client(transport, env["inv_user"]) as client:
        # Nonexistent root cause
        res_nonexistent = await client.post(
            f"/api/v1/investigations/{env['inv1_id']}/capas",
            json={
                "action_type": "CORRECTION",
                "description": "Link to nonexistent root cause.",
                "root_cause_id": 9999999,
            },
        )
        assert res_nonexistent.status_code == 400
        assert "does not exist" in res_nonexistent.json()["detail"]

        # Rejected root cause
        res_rejected = await client.post(
            f"/api/v1/investigations/{env['inv1_id']}/capas",
            json={
                "action_type": "CORRECTION",
                "description": "Link to rejected root cause.",
                "root_cause_id": env["rc_rejected_id"],
            },
        )
        assert res_rejected.status_code == 400
        assert "rejected root cause" in res_rejected.json()["detail"]


@pytest.mark.asyncio
async def test_04_client_forged_verification_metadata_rejected():
    """Test 4: Client-forged verification metadata is rejected with HTTP 400."""
    env = await setup_investigation_and_causes()
    transport = ASGITransport(app=app)
    async with get_client(transport, env["inv_user"]) as client:
        # Attempt to forge is_verified=True on creation
        res1 = await client.post(
            f"/api/v1/investigations/{env['inv1_id']}/capas",
            json={
                "action_type": "CORRECTIVE_ACTION",
                "description": "Forged verified CAPA attempt.",
                "is_verified": True,
            },
        )
        assert res1.status_code == 400
        assert "cannot forge verification" in res1.json()["detail"].lower()

        # Attempt to forge status=APPROVED on creation
        res2 = await client.post(
            f"/api/v1/investigations/{env['inv1_id']}/capas",
            json={
                "action_type": "CORRECTIVE_ACTION",
                "description": "Forged approved CAPA attempt.",
                "status": "APPROVED",
            },
        )
        assert res2.status_code == 400
        assert "pre-approved status" in res2.json()["detail"]

        # Create a valid CAPA first
        create_res = await client.post(
            f"/api/v1/investigations/{env['inv1_id']}/capas",
            json={
                "action_type": "CORRECTIVE_ACTION",
                "description": "Legitimate proposed CAPA.",
            },
        )
        capa_id = create_res.json()["id"]

        # Attempt to forge is_verified=True via PUT update
        res3 = await client.put(
            f"/api/v1/capas/{capa_id}",
            json={"is_verified": True},
        )
        assert res3.status_code == 400
        assert "is_verified" in res3.json()["detail"]


@pytest.mark.asyncio
async def test_05_investigator_approval_denied_403():
    """Test 5: Ordinary investigator cannot approve CAPA (HTTP 403 Forbidden)."""
    env = await setup_investigation_and_causes()
    transport = ASGITransport(app=app)
    async with get_client(transport, env["inv_user"]) as client:
        create_res = await client.post(
            f"/api/v1/investigations/{env['inv1_id']}/capas",
            json={
                "action_type": "PREVENTIVE_ACTION",
                "description": "Implement automated daily seal pressure integrity self-test.",
            },
        )
        capa_id = create_res.json()["id"]

        # Investigator tries to approve
        approve_res = await client.post(f"/api/v1/capas/{capa_id}/approve")
        assert approve_res.status_code == 403
        assert "QA_APPROVER or ADMIN" in approve_res.json()["detail"]


@pytest.mark.asyncio
async def test_06_qa_approval_success():
    """Test 6: Independent QA Approver can approve PROPOSED CAPA."""
    env = await setup_investigation_and_causes()
    transport = ASGITransport(app=app)

    # Investigator creates CAPA
    async with get_client(transport, env["inv_user"]) as inv_client:
        create_res = await inv_client.post(
            f"/api/v1/investigations/{env['inv1_id']}/capas",
            json={
                "action_type": "CORRECTIVE_ACTION",
                "description": "Recalibrate thermal cycle valve limiters.",
                "rationale": "Prevents over-compression during heating cycle.",
                "effectiveness_criteria": "Zero leakage over 30 days.",
            },
        )
        capa_id = create_res.json()["id"]

    # QA Approver approves CAPA
    async with get_client(transport, env["qa_user"]) as qa_client:
        approve_res = await qa_client.post(
            f"/api/v1/capas/{capa_id}/approve",
            json={"approval_notes": "Reviewed engineering calculations; approved for implementation."},
        )
        assert approve_res.status_code == 200, approve_res.text
        data = approve_res.json()
        assert data["status"] == "APPROVED"
        assert data["is_verified"] is True
        assert "[QA Approval]" in data["rationale"]


@pytest.mark.asyncio
async def test_07_lead_investigator_self_approval_prevented_403():
    """Test 7: Assigned lead investigator cannot approve their own CAPA (even with QA role)."""
    env = await setup_investigation_and_causes()
    transport = ASGITransport(app=app)

    # On inv3, qa_lead_user is BOTH the assigned lead investigator AND has role QA_APPROVER
    async with get_client(transport, env["qa_lead_user"]) as dual_client:
        create_res = await dual_client.post(
            f"/api/v1/investigations/{env['inv3_id']}/capas",
            json={
                "action_type": "CORRECTION",
                "description": "Line C self-proposed action.",
            },
        )
        capa_id = create_res.json()["id"]

        # Dual role user attempts to approve their own investigation's CAPA
        self_approve_res = await dual_client.post(f"/api/v1/capas/{capa_id}/approve")
        assert self_approve_res.status_code == 403
        assert "Separation of duties violation" in self_approve_res.json()["detail"]


@pytest.mark.asyncio
async def test_08_invalid_lifecycle_transition_rejected():
    """Test 8: Invalid lifecycle state transitions are rejected with HTTP 400."""
    env = await setup_investigation_and_causes()
    transport = ASGITransport(app=app)

    async with get_client(transport, env["inv_user"]) as inv_client:
        create_res = await inv_client.post(
            f"/api/v1/investigations/{env['inv1_id']}/capas",
            json={
                "action_type": "CORRECTIVE_ACTION",
                "description": "State transition test action.",
                "effectiveness_criteria": "Zero defects.",
            },
        )
        capa_id = create_res.json()["id"]

        # 1. Attempt to start work (IN_PROGRESS) on PROPOSED CAPA before QA approval
        res1 = await inv_client.put(
            f"/api/v1/capas/{capa_id}",
            json={"status": "IN_PROGRESS"},
        )
        assert res1.status_code == 400
        assert "must be formally APPROVED by QA" in res1.json()["detail"]

        # 2. Attempt to mark COMPLETED on PROPOSED CAPA before QA approval
        res2 = await inv_client.put(
            f"/api/v1/capas/{capa_id}",
            json={"status": "COMPLETED", "rationale": "Completed without QA approval."},
        )
        assert res2.status_code == 400
        assert "must be formally APPROVED by QA" in res2.json()["detail"]

        # 3. Attempt to set status=APPROVED via PUT
        res3 = await inv_client.put(
            f"/api/v1/capas/{capa_id}",
            json={"status": "APPROVED"},
        )
        assert res3.status_code == 400
        assert "qa approval endpoint" in res3.json()["detail"].lower()


@pytest.mark.asyncio
async def test_09_completion_requirements():
    """Test 9: Transition to COMPLETED requires prior approval and non-empty notes."""
    env = await setup_investigation_and_causes()
    transport = ASGITransport(app=app)

    # Create and QA approve
    async with get_client(transport, env["inv_user"]) as inv_client:
        create_res = await inv_client.post(
            f"/api/v1/investigations/{env['inv1_id']}/capas",
            json={
                "action_type": "CORRECTIVE_ACTION",
                "description": "Installation of high-pressure check valves.",
                "effectiveness_criteria": "Maintain 4.5 bar hold for 2 hours.",
            },
        )
        capa_id = create_res.json()["id"]

    async with get_client(transport, env["qa_user"]) as qa_client:
        await qa_client.post(f"/api/v1/capas/{capa_id}/approve")

    # Investigator attempts to complete with empty notes
    async with get_client(transport, env["inv_user"]) as inv_client:
        res_empty = await inv_client.post(
            f"/api/v1/capas/{capa_id}/complete",
            json={"completion_notes": "   "},
        )
        assert res_empty.status_code == 400
        assert "non-empty completion notes" in res_empty.json()["detail"]

        # Investigator transitions to IN_PROGRESS
        res_progress = await inv_client.put(
            f"/api/v1/capas/{capa_id}",
            json={"status": "IN_PROGRESS"},
        )
        assert res_progress.status_code == 200
        assert res_progress.json()["status"] == "IN_PROGRESS"

        # Investigator completes with valid completion notes
        res_complete = await inv_client.post(
            f"/api/v1/capas/{capa_id}/complete",
            json={"completion_notes": "Valves installed and torque-verified by technician team."},
        )
        assert res_complete.status_code == 200
        assert res_complete.json()["status"] == "COMPLETED"
        assert "[Completion Note]" in res_complete.json()["rationale"]


@pytest.mark.asyncio
async def test_10_effectiveness_verification_authorization_and_guards():
    """Test 10: Effectiveness verification requires QA role, COMPLETED status, and criteria."""
    env = await setup_investigation_and_causes()
    transport = ASGITransport(app=app)

    # 1. Create and approve CAPA
    async with get_client(transport, env["inv_user"]) as inv_client:
        create_res = await inv_client.post(
            f"/api/v1/investigations/{env['inv1_id']}/capas",
            json={
                "action_type": "PREVENTIVE_ACTION",
                "description": "Upgrade chiller software monitoring limits.",
                "effectiveness_criteria": "Zero temperature excursion alerts for 60 consecutive operational days.",
            },
        )
        capa_id = create_res.json()["id"]

    async with get_client(transport, env["qa_user"]) as qa_client:
        await qa_client.post(f"/api/v1/capas/{capa_id}/approve")

        # QA Approver attempts effectiveness verification on APPROVED (not yet COMPLETED) CAPA -> fails 400
        res_premature = await qa_client.post(f"/api/v1/capas/{capa_id}/verify-effectiveness")
        assert res_premature.status_code == 400
        assert "must be in COMPLETED status" in res_premature.json()["detail"]

    # Mark COMPLETED
    async with get_client(transport, env["inv_user"]) as inv_client:
        await inv_client.post(
            f"/api/v1/capas/{capa_id}/complete",
            json={"completion_notes": "Software patch v2.4 applied across all chiller controllers."},
        )

        # Investigator attempts effectiveness verification -> denied 403
        res_inv_eff = await inv_client.post(f"/api/v1/capas/{capa_id}/verify-effectiveness")
        assert res_inv_eff.status_code == 403
        assert "QA_APPROVER or ADMIN" in res_inv_eff.json()["detail"]

    # QA Approver performs effectiveness verification -> succeeds 200
    async with get_client(transport, env["qa_user"]) as qa_client:
        res_eff = await qa_client.post(
            f"/api/v1/capas/{capa_id}/verify-effectiveness",
            json={"verification_notes": "60 days elapsed. 18 commercial batches run with zero temperature alerts."},
        )
        assert res_eff.status_code == 200
        data = res_eff.json()
        assert data["status"] == "EFFECTIVENESS_VERIFIED"
        assert "[Effectiveness Verification]" in data["effectiveness_criteria"]


@pytest.mark.asyncio
async def test_11_effectiveness_verified_capa_deletion_and_modification_locked():
    """Test 11: Effectiveness-verified CAPAs are locked against modification and deletion."""
    env = await setup_investigation_and_causes()
    transport = ASGITransport(app=app)

    # Create, approve, complete, and verify effectiveness
    async with get_client(transport, env["inv_user"]) as inv_client:
        create_res = await inv_client.post(
            f"/api/v1/investigations/{env['inv1_id']}/capas",
            json={
                "action_type": "CORRECTIVE_ACTION",
                "description": "Lock testing action.",
                "effectiveness_criteria": "Criteria met.",
            },
        )
        capa_id = create_res.json()["id"]

    async with get_client(transport, env["qa_user"]) as qa_client:
        await qa_client.post(f"/api/v1/capas/{capa_id}/approve")

    async with get_client(transport, env["inv_user"]) as inv_client:
        await inv_client.post(
            f"/api/v1/capas/{capa_id}/complete",
            json={"completion_notes": "Action fully implemented and verified."},
        )

    async with get_client(transport, env["qa_user"]) as qa_client:
        await qa_client.post(f"/api/v1/capas/{capa_id}/verify-effectiveness")

    # Now attempt PUT update on locked CAPA
    async with get_client(transport, env["inv_user"]) as inv_client:
        put_res = await inv_client.put(
            f"/api/v1/capas/{capa_id}",
            json={"description": "Attempt to edit locked CAPA."},
        )
        assert put_res.status_code == 400
        assert "Cannot modify an effectiveness-verified CAPA" in put_res.json()["detail"]

        # Attempt to DELETE locked CAPA
        del_res = await inv_client.delete(f"/api/v1/capas/{capa_id}")
        assert del_res.status_code == 400
        assert "Cannot delete an effectiveness-verified CAPA" in del_res.json()["detail"]

    # Delete on a PROPOSED CAPA succeeds
    async with get_client(transport, env["inv_user"]) as inv_client:
        proposed_res = await inv_client.post(
            f"/api/v1/investigations/{env['inv1_id']}/capas",
            json={
                "action_type": "CORRECTION",
                "description": "Unneeded proposed action.",
            },
        )
        p_id = proposed_res.json()["id"]
        del_proposed_res = await inv_client.delete(f"/api/v1/capas/{p_id}")
        assert del_proposed_res.status_code == 200
        assert del_proposed_res.json()["ok"] is True


@pytest.mark.asyncio
async def test_12_audit_logging_and_database_persistence_reload():
    """Test 12: Complete audit logging and PostgreSQL 16 persistence after reload."""
    env = await setup_investigation_and_causes()
    transport = ASGITransport(app=app)

    async with get_client(transport, env["inv_user"]) as inv_client:
        create_res = await inv_client.post(
            f"/api/v1/investigations/{env['inv1_id']}/capas",
            json={
                "action_type": "CORRECTIVE_ACTION",
                "description": "Audit & persistence verification action.",
                "effectiveness_criteria": "Persistence verified.",
                "root_cause_id": env["rc1_id"],
            },
        )
        capa_id = create_res.json()["id"]

    async with get_client(transport, env["qa_user"]) as qa_client:
        await qa_client.post(
            f"/api/v1/capas/{capa_id}/approve",
            json={"approval_notes": "Audit verification note."},
        )

    # Verify directly against database in fresh session
    async with get_session() as session:
        # Check CAPA record persistence
        res = await session.execute(select(CapaAction).where(CapaAction.id == capa_id))
        persisted_capa = res.scalar_one_or_none()
        assert persisted_capa is not None
        assert persisted_capa.status == "APPROVED"
        assert persisted_capa.is_verified is True
        assert persisted_capa.root_cause_id == env["rc1_id"]
        assert persisted_capa.investigation_id == env["inv1_id"]

        # Check AuditLog records
        audit_res = await session.execute(
            select(AuditLog)
            .where(AuditLog.investigation_id == env["inv1_id"])
            .where(AuditLog.entity_type == "CAPA")
            .where(AuditLog.entity_id == str(capa_id))
            .order_by(AuditLog.timestamp.asc())
        )
        logs = audit_res.scalars().all()
        actions = [log.action for log in logs]
        assert "CREATED" in actions
        assert "APPROVED" in actions

        # Verify attribution
        approved_log = [log for log in logs if log.action == "APPROVED"][0]
        assert approved_log.user_id == env["qa_user"].id
        assert approved_log.user_name == env["qa_user"].full_name

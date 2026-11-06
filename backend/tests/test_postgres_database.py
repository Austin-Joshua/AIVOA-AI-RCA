import pytest
import pytest_asyncio
import asyncpg
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import text
from datetime import datetime
import os
import subprocess

from app.core.config import settings
from app.core.database import Base
from app.models.investigation import Investigation
from app.models.deviation import Deviation
from app.models.evidence import Evidence, InvestigationFinding
from app.models.five_whys import FiveWhysStep
from app.models.fishbone import FishboneCause
from app.models.root_cause import RootCause
from app.models.capa import CapaAction
from app.models.audit import AiInteraction, AuditLog, User

POSTGRES_URL = settings.DATABASE_URL
if POSTGRES_URL.startswith("sqlite"):
    POSTGRES_URL = "postgresql+asyncpg://aivoa_user:aivoa_password@localhost:5432/aivoa_rca"

# Helper to verify connectivity before tests
async def check_postgres_alive() -> bool:
    try:
        # Extract connection params
        clean_url = POSTGRES_URL.replace("postgresql+asyncpg://", "postgresql://")
        conn = await asyncpg.connect(clean_url)
        await conn.close()
        return True
    except Exception:
        return False

@pytest.mark.asyncio
async def test_postgresql_connectivity_and_version():
    """Verify live PostgreSQL 16 connectivity and version string."""
    is_alive = await check_postgres_alive()
    if not is_alive:
        pytest.fail("BLOCKED: PostgreSQL 16 is not reachable on localhost:5432. Start container via 'docker compose up -d db'.")

    clean_url = POSTGRES_URL.replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(clean_url)
    try:
        version = await conn.fetchval("SELECT version();")
        assert "PostgreSQL 16" in version, f"Expected PostgreSQL 16, got: {version}"
        
        # Verify active database name
        current_db = await conn.fetchval("SELECT current_database();")
        assert current_db == "aivoa_rca", f"Expected database 'aivoa_rca', got '{current_db}'"
    finally:
        await conn.close()

@pytest.mark.asyncio
async def test_alembic_migration_revision():
    """Verify Alembic migration revision on PostgreSQL matches current head."""
    clean_url = POSTGRES_URL.replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(clean_url)
    try:
        # Check that alembic_version table exists and has revision stamped
        table_exists = await conn.fetchval(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'alembic_version');"
        )
        assert table_exists is True, "Alembic migration version table does not exist in PostgreSQL."
        
        version_num = await conn.fetchval("SELECT version_num FROM alembic_version;")
        assert version_num in ("e9e38a07f832", "c89fbf7d80b8", "6d1518e3b3e9", "98ea1c729df4", "a1b2c3d4e5f6", "3f44c56e6733", "ae9dda31c187", "b2c3d4e5f6a7", "c3d4e5f6a7b8", "d4e5f6a7b8c9"), f"Unexpected Alembic revision: {version_num}"
    finally:
        await conn.close()

@pytest.mark.asyncio
async def test_postgresql_entities_persistence_and_relationships():
    """
    Verifies full relational lifecycle and persistence in PostgreSQL 16:
    - User creation (investigator & QA approver)
    - Investigation with Foreign Keys to User
    - Deviation persistence
    - Evidence & Findings persistence
    - 5 Whys & Fishbone persistence
    - Root Cause persistence
    - CAPA Action with FK to Investigation and RootCause
    - AuditLog with FK to Investigation and User
    """
    engine = create_async_engine(POSTGRES_URL, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    test_timestamp = int(datetime.utcnow().timestamp())
    inv_num = f"INV-PG16-{test_timestamp}"
    dev_num = f"DEV-PG16-{test_timestamp}"
    lead_username = f"lead_{test_timestamp}"
    qa_username = f"qa_{test_timestamp}"

    async with async_session() as session:
        # 1. Create Users
        investigator_user = User(
            username=lead_username,
            email=f"{lead_username}@pharma.corp",
            full_name="Dr. Alex Rivera, Senior Investigator",
            role="INVESTIGATOR",
            department="API Quality Investigation"
        )
        qa_user = User(
            username=qa_username,
            email=f"{qa_username}@pharma.corp",
            full_name="Dr. Marcus Vance, QA Director",
            role="QA_APPROVER",
            department="Quality Assurance"
        )
        session.add_all([investigator_user, qa_user])
        await session.flush()

        assert investigator_user.id is not None
        assert qa_user.id is not None

        # 2. Create Investigation linked to Users
        inv = Investigation(
            investigation_number=inv_num,
            title="PostgreSQL 16 Verification Investigation",
            status="IN_INVESTIGATION",
            stage="INVESTIGATION",
            lead_investigator="Dr. Alex Rivera",
            lead_investigator_id=investigator_user.id,
            qa_approver="Dr. Marcus Vance",
            qa_approver_id=qa_user.id,
            is_approved=False
        )
        session.add(inv)
        await session.flush()
        assert inv.id is not None

        # 3. Create Deviation
        dev = Deviation(
            investigation_id=inv.id,
            deviation_number=dev_num,
            deviation_type="CRITICAL",
            severity="Critical",
            batch_number=f"BATCH-PG16-{test_timestamp}",
            product_name="Atorvastatin Calcium Trihydrate API",
            unit_operation="Crystallization",
            equipment_id="RX-301",
            target_yield_kg=500.0,
            actual_yield_kg=412.5,
            description="Excursion test on PostgreSQL 16 backend.",
            immediate_containment="Quarantine batch in warehouse area C.",
            is_ai_populated=True,
            is_verified=False
        )
        session.add(dev)

        # 4. Create Evidence and Finding
        evidence = Evidence(
            investigation_id=inv.id,
            title="Cooling Water Temperature Trend Log",
            evidence_type="SENSOR_LOG",
            source="SCADA Trend Export",
            confidence_score=0.98,
            is_verified=True,
            verified_by="Dr. Alex Rivera"
        )
        finding = InvestigationFinding(
            investigation_id=inv.id,
            finding_text="Temperature excursion peaked at 38.4C for 42 minutes.",
            finding_type="FACTUAL_EVIDENCE",
            evidence_reference="SCADA-RX301-CHW-01",
            is_ai_suggested=False,
            is_verified=True
        )
        session.add_all([evidence, finding])

        # 5. Create 5 Whys and Fishbone
        why_step = FiveWhysStep(
            investigation_id=inv.id,
            step_number=1,
            question="Why did the crystallization temperature spike?",
            answer="Cooling water pneumatic valve CV-301 actuator diaphragm failed.",
            evidence_reference="Maintenance Work Order WO-2026-991",
            is_ai_suggested=True,
            is_verified=True
        )
        fishbone = FishboneCause(
            investigation_id=inv.id,
            category="MACHINE",
            cause_description="Cooling valve pneumatic actuator failure",
            status="CONFIRMED",
            rationale="Actuator seal ruptured causing loss of air pressure.",
            evidence_reference="WO-2026-991",
            is_ai_suggested=True,
            is_verified=True
        )
        session.add_all([why_step, fishbone])

        # 6. Create Root Cause
        root_cause = RootCause(
            investigation_id=inv.id,
            cause_statement="Pneumatic actuator diaphragm fatigue failure on cooling valve CV-301.",
            category="EQUIPMENT_FAILURE",
            is_primary=True,
            evidence_summary="Disassembly inspection confirmed 12mm tear along outer flexure rim.",
            is_ai_suggested=True,
            is_verified=True,
            investigator_notes="Diaphragm exceeded vendor recommended operating hours by 400 hrs."
        )
        session.add(root_cause)
        await session.flush()
        assert root_cause.id is not None

        # 7. Create CAPA Action linked to Root Cause
        capa = CapaAction(
            investigation_id=inv.id,
            root_cause_id=root_cause.id,
            action_type="CORRECTIVE_ACTION",
            description="Replace CV-301 diaphragm with high-durability fluorosilicone model.",
            rationale="Eliminates premature fatigue failure mode under thermal cycling.",
            owner="Engineering Lead",
            deadline="14 Days",
            effectiveness_criteria="Zero pressure leakage during 100-cycle cold glycol stress test.",
            effectiveness_review_period_days=30,
            status="OPEN",
            is_ai_suggested=True,
            is_verified=True
        )
        session.add(capa)

        # 8. Create Audit Log linked to User and Investigation
        audit = AuditLog(
            investigation_id=inv.id,
            user_id=investigator_user.id,
            user_name=investigator_user.full_name,
            action="VERIFIED",
            entity_type="ROOT_CAUSE",
            entity_id=str(root_cause.id),
            change_summary="Investigator verified primary root cause after diaphragm inspection."
        )
        session.add(audit)

        await session.commit()
        inv_id = inv.id

    # 9. Query back from PostgreSQL with fresh session and assert relational graph
    async with async_session() as session:
        query = (
            select(Investigation)
            .options(
                selectinload(Investigation.lead_investigator_user),
                selectinload(Investigation.qa_approver_user),
                selectinload(Investigation.deviation),
                selectinload(Investigation.evidences),
                selectinload(Investigation.findings),
                selectinload(Investigation.five_whys),
                selectinload(Investigation.fishbone_causes),
                selectinload(Investigation.root_causes),
                selectinload(Investigation.capa_actions),
                selectinload(Investigation.audit_logs)
            )
            .filter(Investigation.id == inv_id)
        )
        res = await session.execute(query)
        fetched_inv = res.scalars().first()

        assert fetched_inv is not None
        assert fetched_inv.investigation_number == inv_num
        assert fetched_inv.lead_investigator_user is not None
        assert fetched_inv.lead_investigator_user.username == lead_username
        assert fetched_inv.qa_approver_user is not None
        assert fetched_inv.qa_approver_user.username == qa_username

        # Verify child relations
        assert fetched_inv.deviation is not None
        assert fetched_inv.deviation.batch_number == f"BATCH-PG16-{test_timestamp}"
        assert len(fetched_inv.evidences) == 1
        assert len(fetched_inv.findings) == 1
        assert len(fetched_inv.five_whys) == 1
        assert len(fetched_inv.fishbone_causes) == 1
        assert len(fetched_inv.root_causes) == 1
        assert len(fetched_inv.capa_actions) == 1
        assert len(fetched_inv.audit_logs) == 1

        # Verify CAPA foreign key to root cause
        fetched_capa = fetched_inv.capa_actions[0]
        assert fetched_capa.root_cause_id == fetched_inv.root_causes[0].id

        # Verify Audit Log foreign key to user
        fetched_audit = fetched_inv.audit_logs[0]
        assert fetched_audit.user_id == investigator_user.id

        # 10. Update Investigation status and verify commit
        fetched_inv.status = "APPROVED"
        fetched_inv.is_approved = True
        fetched_inv.approval_date = datetime.utcnow()
        fetched_inv.approval_comments = "PostgreSQL 16 verified and approved."
        await session.commit()

    # 11. Confirm final state persisted
    async with async_session() as session:
        check_query = select(Investigation).filter(Investigation.id == inv_id)
        check_res = await session.execute(check_query)
        approved_inv = check_res.scalars().first()
        assert approved_inv.status == "APPROVED"
        assert approved_inv.is_approved is True
        assert approved_inv.approval_comments == "PostgreSQL 16 verified and approved."

    await engine.dispose()


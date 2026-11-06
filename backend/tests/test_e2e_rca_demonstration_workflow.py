import pytest
import asyncio
from unittest.mock import patch
from httpx import AsyncClient, ASGITransport
from datetime import datetime
from sqlalchemy.future import select

from app.main import app
from app.core.database import init_db, get_engine
from app.core.security import create_access_token
from app.models.audit import User, AuditLog
from app.models.investigation import Investigation
from app.models.deviation import Deviation
from app.models.evidence import Evidence
from app.models.five_whys import FiveWhysStep
from app.models.fishbone import FishboneCause
from app.models.root_cause import RootCause
from app.models.capa import CapaAction
from app.services.groq_service import groq_service


def get_session():
    get_engine()
    from app.core import database
    return database.AsyncSessionLocal()


async def get_or_create_user(username: str, role: str, full_name: str) -> User:
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
            email=f"{username}@pharmatest-e2e.internal",
            full_name=full_name,
            role=role,
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


def get_auth_client(transport, user: User):
    token = create_access_token({"sub": user.username, "role": user.role, "user_id": user.id})
    return AsyncClient(transport=transport, base_url="http://test", headers={"Authorization": f"Bearer {token}"})


@pytest.mark.asyncio
async def test_complete_end_to_end_rca_demonstration_workflow():
    """
    SAME-DAY TASK 3: Comprehensive End-to-End RCA Workflow Integration Test.
    Mandatory lifecycle flow:
    Deviation Identification -> Document Intake -> Evidence Review ->
    Methodological RCA (5-Whys/Fishbone) -> Root Cause Confirmation ->
    CAPA Creation -> QA Approval -> Execution & Completion -> Effectiveness Verification -> Final Dossier Closure.
    Demonstrates separate Lead Investigator and QA Approver roles with strict segregation of duties.
    """
    transport = ASGITransport(app=app)

    # 1. User Setup: Investigator and QA Approver
    investigator = await get_or_create_user(
        "e2e_lead_inv", "INVESTIGATOR", "Dr. Sarah Lin (Lead Investigator)"
    )
    qa_director = await get_or_create_user(
        "e2e_qa_director", "QA_APPROVER", "Dr. Elena Rostova (QA Director)"
    )

    # 2. Deviation Identification: Create Investigation Dossier
    async with get_auth_client(transport, investigator) as inv_client:
        create_inv_res = await inv_client.post(
            "/api/v1/investigations/",
            json={
                "title": "Fictional Demo: Paracetamol API Thermal Excursion (Batch API-2026-104)",
                "lead_investigator": investigator.full_name,
                "stage": "INTAKE",
                "status": "IN_INVESTIGATION",
            },
        )
        assert create_inv_res.status_code == 200, create_inv_res.text
        inv_data = create_inv_res.json()
        inv_id = inv_data["id"]
        assert inv_data["lead_investigator_id"] == investigator.id

    # 3. Document Intake: Parse Fictional Demonstration Report
    paracetamol_report_text = """PHARMACEUTICAL MANUFACTURING DEVIATION REPORT [FICTIONAL DEMONSTRATION DATA]
Plant: API Manufacturing Block 2
Incident Number: DEV-2026-104
Date of Occurrence: 05-Nov-2026 09:30 UTC
Product: Paracetamol API
Batch Number: API-2026-104
BPR Reference: BPR-PCM-104-REV1
Unit Operation: Crystallization (Reactor CR-104)
Equipment Tag: Crystallizer CR-104

DESCRIPTION OF DEVIATION:
During controlled crystallization of Paracetamol API batch API-2026-104 in reactor CR-104, thermal excursion occurred.
Approved operating temperature range: 75.0°C to 80.0°C.
Illustrative observed temperature: 86.0°C (exceeding upper limit by 6.0°C).
Illustrative excursion duration: 18 minutes.
SCADA telemetry indicates primary cooling loop bypass solenoid SV-104 failed to de-energize upon high temperature interlock trigger.

EVIDENCE OBSERVATIONS & GAPS:
- Observed: Physical inspection of solenoid SV-104 revealed mechanical stem binding.
- Observed: In-process sample IP-104 showed agglomeration; mother liquor yield impact pending HPLC purity test.
- Missing Evidence: Cooling valve calibration record for CV-104 is missing.
- Missing Evidence: Operator shift handover logbook is not attached.

IMMEDIATE CONTAINMENT:
Batch API-2026-104 immediately quarantined in mother liquor hold tank. Reactor CR-104 locked out pending mechanical inspection."""

    # 3. Document Intake: Parse Fictional Demonstration Report
    mock_intake = groq_service._fallback_intake_extraction(
        paracetamol_report_text,
        source_type="TEXT"
    )
    mock_intake["deviation"]["deviation_number"] = "DEV-2026-104"
    mock_intake["deviation"]["product_name"] = "Paracetamol API"
    mock_intake["deviation"]["batch_number"] = "API-2026-104"
    mock_intake["deviation"]["equipment_id"] = "Crystallizer CR-104"
    mock_intake["deviation"]["unit_operation"] = "Crystallization"
    mock_intake["deviation"]["description"] = (
        "During controlled crystallization of Paracetamol API batch API-2026-104 in reactor CR-104, thermal excursion occurred (86°C for 18 min)."
    )
    mock_intake["deviation"]["immediate_containment"] = "Batch API-2026-104 quarantined in mother liquor hold tank."
    fields, conflicts = groq_service._build_structured_fields(
        paracetamol_report_text,
        mock_intake["deviation"],
        mock_intake.get("fields", {}),
        None
    )
    mock_intake["extracted_fields"] = fields
    mock_intake["missing_information"] = [
        {
            "category": "SENSOR_CALIBRATION",
            "question": "Is the cooling valve calibration record for CV-104 available?",
            "impact_description": "Essential to rule out sensor calibration drift.",
            "urgency": "HIGH",
        },
        {
            "category": "LOGBOOK",
            "question": "Where is the operator shift handover logbook?",
            "impact_description": "Operator handover details required for procedural review.",
            "urgency": "MEDIUM",
        }
    ]

    mock_rca = {
        "status": "SUCCESS",
        "five_whys": [
            {
                "step_number": 1,
                "question": "Why did reactor CR-104 temperature exceed 80°C?",
                "answer": "Primary cooling bypass solenoid SV-104 failed to de-energize upon high temperature interlock trigger.",
                "evidence_reference": "SCADA trend telemetry log",
                "is_ai_suggested": True,
                "is_verified": False,
            },
            {
                "step_number": 2,
                "question": "Why did solenoid SV-104 fail to de-energize?",
                "answer": "Mechanical stem binding occurred inside the solenoid valve body.",
                "evidence_reference": "Physical inspection report",
                "is_ai_suggested": True,
                "is_verified": False,
            },
        ],
        "fishbone_causes": [
            {
                "category": "MACHINE",
                "cause_description": "Mechanical stem binding in solenoid SV-104 due to galling under thermal cycling.",
                "status": "HYPOTHESIS",
                "rationale": "High temperature cycling caused thermal galling.",
                "evidence_reference": "Teardown report",
                "is_ai_suggested": True,
                "is_verified": False,
            }
        ],
        "root_causes": [
            {
                "cause_statement": "Mechanical stem binding in solenoid valve SV-104 resulting in cooling bypass failure during crystallization.",
                "category": "EQUIPMENT_FAILURE",
                "is_primary": True,
                "evidence_summary": "Teardown confirmed stem galling matching SCADA temperature excursion curve.",
                "status": "PROPOSED",
                "is_ai_suggested": True,
                "is_verified": False,
            }
        ],
        "capa_actions": [
            {
                "action_type": "CORRECTIVE_ACTION",
                "description": "Replace SV-104 solenoid with high-temperature galling-resistant alloy valve.",
                "rationale": "Eliminates mechanical binding failure under crystallization thermal cycling.",
                "owner": "Maintenance Lead",
                "deadline": "14 Days",
                "effectiveness_criteria": "Zero temperature excursions (>80°C) across next 20 consecutive commercial batches.",
                "effectiveness_review_period_days": 60,
                "is_ai_suggested": True,
                "is_verified": False,
            }
        ],
    }

    with patch.object(groq_service, "is_available", return_value=True), \
         patch.object(groq_service, "extract_intake_data", return_value=mock_intake), \
         patch.object(groq_service, "generate_rca_analysis", return_value=mock_rca):
        async with get_auth_client(transport, investigator) as inv_client:
            parse_res = await inv_client.post(
                "/api/v1/intake/parse-text",
                json={"content": paracetamol_report_text, "source_type": "TEXT"},
            )
            assert parse_res.status_code == 200, parse_res.text
            extracted = parse_res.json()
            assert extracted["deviation"]["batch_number"] == "API-2026-104"
            assert extracted["deviation"]["deviation_number"] == "DEV-2026-104"
            assert extracted["deviation"]["product_name"] == "Paracetamol API"
            assert len(extracted["extracted_fields"]) >= 10
            assert len(extracted["missing_information"]) >= 1

    # 4. Review & Apply Extraction to Investigation Dossier
    # Reviewer accepts all source-grounded findings
    reviewed_fields = []
    for f in extracted["extracted_fields"]:
        reviewed_fields.append({
            "field_name": f["field_name"],
            "label": f.get("label", f["field_name"]),
            "value": f["value"],
            "source_reference": f.get("source_reference", ""),
            "page_number": f.get("page_number"),
            "status": f.get("status", "SOURCE_FACT"),
            "is_accepted": True,
            "user_edited": False,
        })

    async with get_auth_client(transport, investigator) as inv_client:
        apply_res = await inv_client.post(
            "/api/v1/intake/apply-to-investigation",
            json={
                "investigation_id": inv_id,
                "apply_deviation": True,
                "apply_evidence": True,
                "reviewed_fields": reviewed_fields,
                "custom_overrides": {
                    "deviation": extracted["deviation"],
                    "extracted_findings": extracted.get("extracted_findings", []),
                    "missing_information": extracted.get("missing_information", []),
                    "raw_document_preview": paracetamol_report_text,
                    "source_metadata": {
                        "filename": "fictional_demo_dev_2026_104.txt",
                        "file_hash_sha256": "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
                        "file_size_bytes": len(paracetamol_report_text),
                    },
                },
                "evidence_metadata": {
                    "filename": "fictional_demo_dev_2026_104.txt",
                    "file_hash_sha256": "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
                    "file_size_bytes": len(paracetamol_report_text),
                },
            },
        )
        assert apply_res.status_code == 200, apply_res.text
        applied_inv = apply_res.json()
        assert applied_inv["deviation"]["batch_number"] == "API-2026-104"
        assert len(applied_inv["evidences"]) >= 1
        assert len(applied_inv["evidence_gaps"]) >= 1
        primary_ev_id = applied_inv["evidences"][0]["id"]
        gap_id = applied_inv["evidence_gaps"][0]["id"]

    # 5. Evidence Review & Verification Separation of Duties
    # Lead investigator (original uploader) cannot self-verify evidence (403 Forbidden)
    async with get_auth_client(transport, investigator) as inv_client:
        self_ver_res = await inv_client.post(
            f"/api/v1/evidences/{primary_ev_id}/verify",
            json={
                "investigator_name": investigator.full_name,
                "verification_notes": "Attempting self verification.",
            },
        )
        assert self_ver_res.status_code == 403
        assert "Separation of duties violation" in self_ver_res.json()["detail"]

    # Independent QA Director formally verifies the evidence (200 OK)
    async with get_auth_client(transport, qa_director) as qa_client:
        qa_ver_res = await qa_client.post(
            f"/api/v1/evidences/{primary_ev_id}/verify",
            json={
                "investigator_name": qa_director.full_name,
                "verification_notes": "Verified against shift physical plant inspection log.",
            },
        )
        assert qa_ver_res.status_code == 200, qa_ver_res.text
        assert qa_ver_res.json()["is_verified"] is True
        assert qa_ver_res.json()["verified_by_user_id"] == qa_director.id

    # 6. Evidence Gap Response
    async with get_auth_client(transport, investigator) as inv_client:
        gap_res = await inv_client.post(
            f"/api/v1/evidence-gaps/{gap_id}/respond",
            json={
                "responder_name": investigator.full_name,
                "response": "Requested calibration log from Block 2 instrument workshop.",
            },
        )
        assert gap_res.status_code == 200, gap_res.text
        assert gap_res.json()["investigator_response"] is not None

    # 7. Methodological RCA: Five Whys & Fishbone Cause Promotion
    async with get_auth_client(transport, investigator) as inv_client:
        # Step 1: Why did temperature rise?
        step_res = await inv_client.post(
            f"/api/v1/investigations/{inv_id}/five-whys",
            json={
                "step_number": 1,
                "question": "Why did reactor CR-104 temperature exceed 80°C?",
                "answer": "Primary cooling bypass solenoid SV-104 failed to open upon demand.",
                "evidence_reference": "SCADA trend telemetry log",
            },
        )
        assert step_res.status_code == 200, step_res.text
        step_id = step_res.json()["id"]

        # Link verified evidence to Five Whys step and verify
        link_step_res = await inv_client.post(
            f"/api/v1/five-whys/{step_id}/evidence",
            json={"evidence_id": primary_ev_id, "relationship_type": "SUPPORTING"},
        )
        assert link_step_res.status_code == 200, link_step_res.text

        ver_step_res = await inv_client.post(
            f"/api/v1/five-whys/{step_id}/verify",
            json={"is_verified": True, "verification_notes": "Corroborated by verified SCADA trend and physical teardown."},
        )
        assert ver_step_res.status_code == 200, ver_step_res.text
        assert ver_step_res.json()["is_verified"] is True

        # Fishbone: Machine factor
        fish_res = await inv_client.post(
            f"/api/v1/investigations/{inv_id}/fishbone",
            json={
                "category": "MACHINE",
                "cause_description": "Mechanical stem binding in solenoid SV-104 due to galling under thermal cycling.",
                "evidence_reference": "Teardown report",
            },
        )
        assert fish_res.status_code == 200, fish_res.text
        fish_id = fish_res.json()["id"]

        # Link verified evidence to Fishbone cause and verify
        link_fish_res = await inv_client.post(
            f"/api/v1/fishbone/{fish_id}/evidence",
            json={"evidence_id": primary_ev_id, "relationship_type": "SUPPORTING"},
        )
        assert link_fish_res.status_code == 200, link_fish_res.text

        ver_fish_res = await inv_client.post(
            f"/api/v1/fishbone/{fish_id}/verify",
            json={"status": "VERIFIED", "verification_notes": "Mechanical galling confirmed by maintenance technician."},
        )
        assert ver_fish_res.status_code == 200, ver_fish_res.text

        # Promote verified Fishbone cause to Root Cause proposal
        promote_res = await inv_client.post(
            f"/api/v1/fishbone/{fish_id}/promote",
            json={"is_primary": True, "category": "EQUIPMENT_FAILURE"},
        )
        assert promote_res.status_code == 200, promote_res.text
        rc_data = promote_res.json()
        rc_id = rc_data["id"]
        assert rc_data["status"] == "PROPOSED"
        assert rc_data["source_type"] == "FISHBONE"
        assert rc_data["is_verified"] is False

    # 8. Root Cause Evidence Linking & QA Confirmation Barrier
    # Lead investigator cannot confirm root cause (403 Forbidden)
    async with get_auth_client(transport, investigator) as inv_client:
        self_conf_res = await inv_client.post(
            f"/api/v1/root-causes/{rc_id}/confirm",
            json={
                "investigator_name": investigator.full_name,
                "justification": "Attempting confirmation as lead investigator.",
            },
        )
        assert self_conf_res.status_code == 403
        assert "QA_APPROVER or ADMIN" in self_conf_res.json()["detail"] or "Separation of duties" in self_conf_res.json()["detail"]

    # Independent QA Director formally confirms root cause
    async with get_auth_client(transport, qa_director) as qa_client:
        confirm_res = await qa_client.post(
            f"/api/v1/root-causes/{rc_id}/confirm",
            json={
                "justification": "Confirmed based on verified physical stem teardown and SCADA telemetry correlation.",
                "investigator_name": qa_director.full_name,
            },
        )
        assert confirm_res.status_code == 200, confirm_res.text
        confirmed_rc = confirm_res.json()
        assert confirmed_rc["status"] == "CONFIRMED"
        assert confirmed_rc["is_verified"] is True
        assert confirmed_rc["confirmed_by_user_id"] == qa_director.id

    # 9. CAPA Creation: Link to confirmed Root Cause
    async with get_auth_client(transport, investigator) as inv_client:
        capa_res = await inv_client.post(
            f"/api/v1/investigations/{inv_id}/capas",
            json={
                "action_type": "CORRECTIVE_ACTION",
                "description": "Replace SV-104 solenoid with high-temperature galling-resistant alloy valve.",
                "rationale": "Eliminates mechanical binding failure under crystallization thermal cycling.",
                "owner": "Maintenance Lead",
                "deadline": "14 Days",
                "effectiveness_criteria": "Zero temperature excursions (>80°C) across next 20 consecutive commercial batches.",
                "effectiveness_review_period_days": 60,
                "root_cause_id": rc_id,
            },
        )
        assert capa_res.status_code == 200, capa_res.text
        capa_data = capa_res.json()
        capa_id = capa_data["id"]
        assert capa_data["status"] == "PROPOSED"
        assert capa_data["is_verified"] is False
        assert capa_data["root_cause_id"] == rc_id

    # 10. CAPA QA Approval
    # Lead investigator cannot approve CAPA (403 Forbidden)
    async with get_auth_client(transport, investigator) as inv_client:
        self_capa_app = await inv_client.post(f"/api/v1/capas/{capa_id}/approve")
        assert self_capa_app.status_code == 403

    # QA Director formally approves CAPA
    async with get_auth_client(transport, qa_director) as qa_client:
        capa_app_res = await qa_client.post(
            f"/api/v1/capas/{capa_id}/approve",
            json={"approval_notes": "Reviewed engineering spec; authorized for installation."},
        )
        assert capa_app_res.status_code == 200, capa_app_res.text
        assert capa_app_res.json()["status"] == "APPROVED"
        assert capa_app_res.json()["is_verified"] is True

    # 11. CAPA Implementation & Completion
    async with get_auth_client(transport, investigator) as inv_client:
        # Start work
        start_res = await inv_client.put(
            f"/api/v1/capas/{capa_id}",
            json={"status": "IN_PROGRESS"},
        )
        assert start_res.status_code == 200
        assert start_res.json()["status"] == "IN_PROGRESS"

        # Complete work with documented execution notes
        comp_res = await inv_client.post(
            f"/api/v1/capas/{capa_id}/complete",
            json={"completion_notes": "New alloy solenoid installed, wired to DCS, and cycle-tested 50 times."},
        )
        assert comp_res.status_code == 200, comp_res.text
        assert comp_res.json()["status"] == "COMPLETED"

    # 12. CAPA Effectiveness Verification & Locking
    # Investigator cannot verify effectiveness (403 Forbidden)
    async with get_auth_client(transport, investigator) as inv_client:
        inv_eff_res = await inv_client.post(f"/api/v1/capas/{capa_id}/verify-effectiveness")
        assert inv_eff_res.status_code == 403

    # QA Director verifies effectiveness
    async with get_auth_client(transport, qa_director) as qa_client:
        eff_res = await qa_client.post(
            f"/api/v1/capas/{capa_id}/verify-effectiveness",
            json={"verification_notes": "60 days elapsed. 22 consecutive batches crystallized with 100% in-spec temperatures."},
        )
        assert eff_res.status_code == 200, eff_res.text
        assert eff_res.json()["status"] == "EFFECTIVENESS_VERIFIED"

    # Locked against modification or deletion (400 Bad Request)
    async with get_auth_client(transport, investigator) as inv_client:
        lock_put = await inv_client.put(f"/api/v1/capas/{capa_id}", json={"description": "Tamper"})
        assert lock_put.status_code == 400
        lock_del = await inv_client.delete(f"/api/v1/capas/{capa_id}")
        assert lock_del.status_code == 400

    # 13. Final Investigation QA Sign-Off & Closure
    # Investigator cannot close investigation (403 Forbidden)
    async with get_auth_client(transport, investigator) as inv_client:
        inv_close_res = await inv_client.post(f"/api/v1/investigations/{inv_id}/approve")
        assert inv_close_res.status_code == 403

    # QA Director formally closes investigation dossier
    async with get_auth_client(transport, qa_director) as qa_client:
        close_res = await qa_client.post(
            f"/api/v1/investigations/{inv_id}/approve",
            params={"comments": "Full RCA and CAPA completed. Causality verified, corrective actions implemented and verified effective."},
        )
        assert close_res.status_code == 200, close_res.text
        closed_inv = close_res.json()
        assert closed_inv["is_approved"] is True
        assert closed_inv["status"] in ("APPROVED", "CLOSED")
        assert closed_inv["qa_approver_id"] == qa_director.id

    # 14. PostgreSQL 16 Persistence & Audit Trail Reload
    async with get_session() as session:
        # Reload investigation in fresh session
        res = await session.execute(select(Investigation).where(Investigation.id == inv_id))
        persisted_inv = res.scalar_one_or_none()
        assert persisted_inv is not None
        assert persisted_inv.is_approved is True
        assert persisted_inv.qa_approver_id == qa_director.id

        # Verify CAPA action
        capa_res = await session.execute(select(CapaAction).where(CapaAction.id == capa_id))
        persisted_capa = capa_res.scalar_one_or_none()
        assert persisted_capa is not None
        assert persisted_capa.status == "EFFECTIVENESS_VERIFIED"
        assert persisted_capa.is_verified is True
        assert persisted_capa.root_cause_id == rc_id

        # Verify Root Cause
        rc_db = await session.execute(select(RootCause).where(RootCause.id == rc_id))
        persisted_rc = rc_db.scalar_one_or_none()
        assert persisted_rc is not None
        assert persisted_rc.status == "CONFIRMED"
        assert persisted_rc.confirmed_by_user_id == qa_director.id

        # Verify Audit Log Trail
        audit_res = await session.execute(
            select(AuditLog)
            .where(AuditLog.investigation_id == inv_id)
            .order_by(AuditLog.timestamp.asc())
        )
        audit_records = audit_res.scalars().all()
        logged_actions = [a.action for a in audit_records]
        assert "CREATED" in logged_actions
        assert "VERIFIED" in logged_actions
        assert "CONFIRMED" in logged_actions
        assert "APPROVED" in logged_actions
        assert "COMPLETED" in logged_actions
        assert "EFFECTIVENESS_VERIFIED" in logged_actions

import pytest
import io
import pypdf
from httpx import AsyncClient, ASGITransport
from datetime import datetime

from app.main import app
from app.core import database
from app.core.database import init_db
from app.models.investigation import Investigation
from app.models.deviation import Deviation
from app.models.evidence import Evidence, EvidenceGap, InvestigationFinding
from app.models.root_cause import RootCause, RootCauseEvidenceLink
from app.services.document_parser import document_parser
from app.core.security import create_access_token

def get_auth_client(transport):
    token = create_access_token({"sub": "lead_investigator", "role": "INVESTIGATOR", "user_id": 1})
    return AsyncClient(transport=transport, base_url="http://test", headers={"Authorization": f"Bearer {token}"})

def get_qa_client(transport):
    token = create_access_token({"sub": "qa_director", "role": "QA_APPROVER", "user_id": 2})
    return AsyncClient(transport=transport, base_url="http://test", headers={"Authorization": f"Bearer {token}"})

def get_session():
    if database.AsyncSessionLocal is None:
        database.get_engine()
    return database.AsyncSessionLocal()

@pytest.mark.asyncio
async def test_evidence_ingestion_and_metadata_persistence():
    await init_db()
    transport = ASGITransport(app=app)
    async with get_auth_client(transport) as ac:
        # Create investigation
        inv_res = await ac.post("/api/v1/investigations/", json={
            "title": "Evidence Ingestion Test Investigation",
            "lead_investigator": "Dr. Sarah Lin (QA Lead)"
        })
        assert inv_res.status_code == 200
        inv_id = inv_res.json()["id"]

        # Upload evidence file
        content = b"Batch B2026-API-044 RTD Temperature Sensor Calibration Certificate. Tag: TT-301. Status: PASS."
        files = {
            "file": ("CAL-2026-88.txt", content, "text/plain")
        }
        data = {
            "title": "RTD Sensor Calibration Certificate CAL-2026-88",
            "evidence_type": "CALIBRATION_CERT",
            "classification": "ANALYTICAL_DATA"
        }
        upload_res = await ac.post(f"/api/v1/investigations/{inv_id}/evidences/upload", data=data, files=files)
        assert upload_res.status_code == 200
        ev = upload_res.json()

        assert ev["investigation_id"] == inv_id
        assert ev["original_filename"] == "CAL-2026-88.txt"
        assert ev["evidence_type"] == "CALIBRATION_CERT"
        assert ev["classification"] == "ANALYTICAL_DATA"
        assert ev["file_size_bytes"] == len(content)
        assert len(ev["file_hash_sha256"]) == 64  # SHA-256 hex string
        assert "Batch B2026-API-044" in ev["extracted_text"]
        assert ev["is_verified"] is False

# -------------------------------------------------------------
# Test 2: Page-Level Source Traceability
# -------------------------------------------------------------
@pytest.mark.asyncio
async def test_page_level_source_traceability():
    # Build 2-page in-memory PDF
    writer = pypdf.PdfWriter()
    p1 = writer.add_blank_page(width=200, height=200)
    p2 = writer.add_blank_page(width=200, height=200)

    stream = io.BytesIO()
    writer.write(stream)
    pdf_bytes = stream.getvalue()

    parsed = document_parser.parse_pdf_structured(pdf_bytes)
    assert parsed["page_count"] == 2
    assert len(parsed["pages"]) == 2
    assert parsed["pages"][0]["page_number"] == 1
    assert parsed["pages"][1]["page_number"] == 2
    assert len(parsed["file_hash_sha256"]) == 64

    # Validate non-hallucination verification utility
    source_sample = "Crystallization temperature spiked to 68C exceeding specification limit of 50C due to stuck valve actuator."
    assert document_parser.validate_source_reference("stuck valve actuator", source_sample) is True
    assert document_parser.validate_source_reference("operator forgot to turn on power", source_sample) is False

# -------------------------------------------------------------
# Test 3: Evidence Gap Auto-Detection & Persistence
# -------------------------------------------------------------
@pytest.mark.asyncio
async def test_evidence_gap_persistence():
    transport = ASGITransport(app=app)
    async with get_auth_client(transport) as ac:
        inv_res = await ac.post("/api/v1/investigations/", json={
            "title": "Evidence Gap Detection Test",
            "lead_investigator": "Dr. Sarah Lin (QA Lead)"
        })
        inv_id = inv_res.json()["id"]

        # Apply extraction containing missing information
        apply_res = await ac.post("/api/v1/intake/apply-to-investigation", json={
            "investigation_id": inv_id,
            "apply_deviation": True,
            "custom_overrides": {
                "deviation": {
                    "deviation_number": "DEV-2026-GAP-1",
                    "batch_number": "B2026-API-099",
                    "product_name": "Atorvastatin API",
                    "description": "Temperature spike during crystallization phase"
                },
                "extracted_findings": ["Thermal excursion lasted 42 minutes"],
                "missing_information": [
                    {
                        "category": "CALIBRATION_RECORDS",
                        "question": "Provide recent RTD calibration certificate for TT-301",
                        "impact_description": "Rules out sensor drift",
                        "suggested_record": "CAL-2026-88",
                        "urgency": "HIGH"
                    }
                ]
            }
        })
        assert apply_res.status_code == 200

        # Query evidence gaps endpoint
        gaps_res = await ac.get(f"/api/v1/investigations/{inv_id}/evidence-gaps")
        assert gaps_res.status_code == 200
        gaps = gaps_res.json()
        assert len(gaps) >= 1
        assert gaps[0]["category"] == "CALIBRATION_RECORDS"
        assert gaps[0]["urgency"] == "HIGH"
        assert gaps[0]["is_resolved"] is False

# -------------------------------------------------------------
# Test 4: Investigator Gap Response Persistence
# -------------------------------------------------------------
@pytest.mark.asyncio
async def test_investigator_gap_response_persistence():
    transport = ASGITransport(app=app)
    async with get_auth_client(transport) as ac:
        inv_res = await ac.post("/api/v1/investigations/", json={
            "title": "Gap Response Test",
            "lead_investigator": "Dr. Sarah Lin"
        })
        inv_id = inv_res.json()["id"]

        # Create gap
        gap_res = await ac.post(f"/api/v1/investigations/{inv_id}/evidence-gaps", json={
            "category": "RAW_MATERIAL_COA",
            "question": "Was solvent certificate of analysis verified?",
            "impact_description": "Excludes raw material contamination",
            "urgency": "MEDIUM"
        })
        gap_id = gap_res.json()["id"]

        # Submit response
        resp_res = await ac.post(f"/api/v1/evidence-gaps/{gap_id}/respond", json={
            "response": "Reviewed CoA Lot #SOLV-9921; moisture content was 0.02% (spec <= 0.05%).",
            "responder_name": "Dr. Sarah Lin (QA Lead)"
        })
        assert resp_res.status_code == 200
        updated_gap = resp_res.json()
        assert "Reviewed CoA Lot #SOLV-9921" in updated_gap["investigator_response"]
        assert "Dr. Sarah Lin" in updated_gap["responded_by"]
        assert updated_gap["response_timestamp"] is not None
        assert updated_gap["is_resolved"] is False  # Response alone does NOT automatically resolve

# -------------------------------------------------------------
# Test 5: Explicit Human Gap Resolution
# -------------------------------------------------------------
@pytest.mark.asyncio
async def test_explicit_human_gap_resolution():
    transport = ASGITransport(app=app)
    async with get_auth_client(transport) as ac:
        inv_res = await ac.post("/api/v1/investigations/", json={
            "title": "Gap Resolution Workflow Test"
        })
        inv_id = inv_res.json()["id"]

        gap_res = await ac.post(f"/api/v1/investigations/{inv_id}/evidence-gaps", json={
            "category": "OPERATOR_LOGS",
            "question": "Verify shift handover entry",
            "impact_description": "Validates manual override status",
            "urgency": "HIGH"
        })
        gap_id = gap_res.json()["id"]

        # Explicit human action to resolve
        resolve_res = await ac.post(f"/api/v1/evidence-gaps/{gap_id}/resolve", json={
            "resolver_name": "Lead Investigator Lin",
            "resolution_notes": "Log verified and confirmed normal cascade mode."
        })
        assert resolve_res.status_code == 200
        resolved_gap = resolve_res.json()
        assert resolved_gap["is_resolved"] is True

# -------------------------------------------------------------
# Test 6: Relational Root-Cause Evidence Links
# -------------------------------------------------------------
@pytest.mark.asyncio
async def test_root_cause_evidence_links_and_isolation():
    transport = ASGITransport(app=app)
    async with get_auth_client(transport) as ac:
        # Create Investigation A
        invA_res = await ac.post("/api/v1/investigations/", json={"title": "Investigation A"})
        invA_id = invA_res.json()["id"]

        # Create Evidence in Investigation A
        evA_res = await ac.post(f"/api/v1/investigations/{invA_id}/evidences/manual", json={
            "title": "Actuator Inspection Note",
            "evidence_type": "LOGBOOK",
            "classification": "PRIMARY_SOURCE",
            "extracted_text": "Actuator diaphragm was found ruptured upon disassembly."
        })
        evA_id = evA_res.json()["id"]

        # Create Investigation B
        invB_res = await ac.post("/api/v1/investigations/", json={"title": "Investigation B"})
        invB_id = invB_res.json()["id"]

        # Manually create root cause in Investigation A
        async with get_session() as session:
            rcA = RootCause(
                investigation_id=invA_id,
                cause_statement="Cooling valve CV-301 actuator diaphragm mechanical rupture",
                category="EQUIPMENT_FAILURE",
                is_primary=True,
                status="PROPOSED",
                is_ai_suggested=True,
                is_verified=False
            )
            session.add(rcA)
            await session.commit()
            await session.refresh(rcA)
            rcA_id = rcA.id

        # Link Evidence A to Root Cause A (SUPPORTING)
        link_res = await ac.post(f"/api/v1/root-causes/{rcA_id}/evidence-links", json={
            "evidence_id": evA_id,
            "relationship_type": "SUPPORTING",
            "relevance_explanation": "Direct physical inspection confirms diaphragm rupture"
        })
        assert link_res.status_code == 200
        link_data = link_res.json()
        assert link_data["relationship_type"] == "SUPPORTING"
        assert link_data["evidence_id"] == evA_id

        # Cross-investigation isolation guard test:
        # Attempt to link Evidence from Inv A to a cause in Inv B must fail
        async with get_session() as session:
            rcB = RootCause(
                investigation_id=invB_id,
                cause_statement="Unrelated cause in investigation B",
                is_primary=True,
                status="PROPOSED"
            )
            session.add(rcB)
            await session.commit()
            await session.refresh(rcB)
            rcB_id = rcB.id

        cross_res = await ac.post(f"/api/v1/root-causes/{rcB_id}/evidence-links", json={
            "evidence_id": evA_id,
            "relationship_type": "SUPPORTING"
        })
        assert cross_res.status_code == 400
        assert "Forbidden" in cross_res.json()["detail"]

# -------------------------------------------------------------
# Test 7: Contradictory Evidence Safety Enforcement
# -------------------------------------------------------------
@pytest.mark.asyncio
async def test_contradictory_evidence_safety_rejection():
    transport = ASGITransport(app=app)
    async with get_auth_client(transport) as ac:
        inv_res = await ac.post("/api/v1/investigations/", json={"title": "Contradiction Safety Test"})
        inv_id = inv_res.json()["id"]

        # Supporting evidence (verified by QA for separation of duties)
        ev1_res = await ac.post(f"/api/v1/investigations/{inv_id}/evidences/manual", json={
            "title": "SCADA trend showing valve closed",
            "extracted_text": "Valve position feedback 0% for 35 mins"
        })
        ev1_id = ev1_res.json()["id"]
        async with get_qa_client(transport) as qa_ac:
            v_res = await qa_ac.post(f"/api/v1/evidences/{ev1_id}/verify", json={
                "investigator_name": "Dr. Elena Rostova"
            })
            assert v_res.status_code == 200

        # Contradictory evidence
        ev2_res = await ac.post(f"/api/v1/investigations/{inv_id}/evidences/manual", json={
            "title": "Operator log contradicting valve failure",
            "extracted_text": "Operator notes manual cooling bypass was active"
        })
        ev2_id = ev2_res.json()["id"]

        # Root cause
        async with get_session() as session:
            rc = RootCause(
                investigation_id=inv_id,
                cause_statement="Cooling valve jammed closed",
                status="PROPOSED",
                is_primary=True,
                is_ai_suggested=True,
                is_verified=False
            )
            session.add(rc)
            await session.commit()
            await session.refresh(rc)
            rc_id = rc.id

        # Link supporting and contradictory evidence
        await ac.post(f"/api/v1/root-causes/{rc_id}/evidence-links", json={
            "evidence_id": ev1_id,
            "relationship_type": "SUPPORTING"
        })
        link2_res = await ac.post(f"/api/v1/root-causes/{rc_id}/evidence-links", json={
            "evidence_id": ev2_id,
            "relationship_type": "CONTRADICTORY",
            "relevance_explanation": "Log suggests manual override was used, contradicting automatic valve seizure"
        })
        assert link2_res.status_code == 200

        # Attempt to confirm root cause must be rejected due to unresolved contradiction!
        async with get_qa_client(transport) as qa_ac:
            confirm_res = await qa_ac.post(f"/api/v1/root-causes/{rc_id}/confirm", json={
                "investigator_name": "Dr. Elena Rostova",
                "justification": "Sufficient evidence available in SCADA."
            })
            assert confirm_res.status_code == 400
            assert "contradictory evidence" in confirm_res.json()["detail"].lower()

# -------------------------------------------------------------
# Test 8: Human Review & Root Cause Confirmation
# -------------------------------------------------------------
@pytest.mark.asyncio
async def test_human_root_cause_confirmation_workflow():
    transport = ASGITransport(app=app)
    async with get_auth_client(transport) as ac:
        inv_res = await ac.post("/api/v1/investigations/", json={"title": "Confirmation Workflow Test"})
        inv_id = inv_res.json()["id"]

        # Create and verify supporting evidence (verified by QA approver)
        ev_res = await ac.post(f"/api/v1/investigations/{inv_id}/evidences/manual", json={
            "title": "Calibration Lab Failure Report",
            "extracted_text": "Bench stroke testing confirmed actuator diaphragm ruptured."
        })
        ev_id = ev_res.json()["id"]
        async with get_qa_client(transport) as qa_ac:
            verify_res = await qa_ac.post(f"/api/v1/evidences/{ev_id}/verify", json={
                "investigator_name": "Dr. Elena Rostova (QA Approver)",
                "verification_notes": "Examined calibration bench test data sheet."
            })
            assert verify_res.status_code == 200
            assert verify_res.json()["is_verified"] is True

        # Create root cause
        async with get_session() as session:
            rc = RootCause(
                investigation_id=inv_id,
                cause_statement="Actuator diaphragm mechanical fatigue and rupture",
                status="PROPOSED",
                is_primary=True,
                is_ai_suggested=True,
                is_verified=False
            )
            session.add(rc)
            await session.commit()
            await session.refresh(rc)
            rc_id = rc.id

        # Link supporting verified evidence
        await ac.post(f"/api/v1/root-causes/{rc_id}/evidence-links", json={
            "evidence_id": ev_id,
            "relationship_type": "SUPPORTING",
            "relevance_explanation": "Bench stroke testing confirms mechanical diaphragm failure"
        })

        # Confirm root cause as QA approver (independent review)
        async with get_qa_client(transport) as qa_ac:
            confirm_res = await qa_ac.post(f"/api/v1/root-causes/{rc_id}/confirm", json={
                "investigator_name": "Dr. Elena Rostova (QA Approver)",
                "justification": "Corroborated by verified calibration bench test CAL-2026-88 with zero contradictory findings."
            })
            assert confirm_res.status_code == 200
            confirmed_rc = confirm_res.json()
            assert confirmed_rc["status"] == "CONFIRMED"
            assert confirmed_rc["is_verified"] is True
            assert confirmed_rc["is_ai_suggested"] is False
            assert "Confirmed by Dr. Elena Rostova" in confirmed_rc["investigator_notes"]

# -------------------------------------------------------------
# Test 9: Full Investigation Relational Retrieval
# -------------------------------------------------------------
@pytest.mark.asyncio
async def test_full_investigation_relational_retrieval():
    transport = ASGITransport(app=app)
    async with get_auth_client(transport) as ac:
        inv_res = await ac.post("/api/v1/investigations/", json={"title": "Relational Retrieval Test"})
        inv_id = inv_res.json()["id"]

        # Add evidence
        await ac.post(f"/api/v1/investigations/{inv_id}/evidences/manual", json={
            "title": "SCADA Trend 01",
            "extracted_text": "Thermal excursion trend curve"
        })

        # Add gap
        await ac.post(f"/api/v1/investigations/{inv_id}/evidence-gaps", json={
            "category": "MAINTENANCE_LOG",
            "question": "Provide preventive maintenance record PM-2025-12",
            "impact_description": "Establishes maintenance history",
            "urgency": "MEDIUM"
        })

        # Retrieve full investigation
        get_res = await ac.get(f"/api/v1/investigations/{inv_id}")
        assert get_res.status_code == 200
        inv_data = get_res.json()

        assert len(inv_data["evidences"]) >= 1
        assert len(inv_data["evidence_gaps"]) >= 1
        assert inv_data["evidences"][0]["title"] == "SCADA Trend 01"
        assert inv_data["evidence_gaps"][0]["category"] == "MAINTENANCE_LOG"

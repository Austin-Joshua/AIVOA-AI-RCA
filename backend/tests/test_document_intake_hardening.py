import pytest
import io
import pypdf
from unittest.mock import patch, MagicMock
from httpx import AsyncClient, ASGITransport
from sqlalchemy.future import select
from datetime import datetime

from app.main import app
from app.core import database
from app.core.security import create_access_token, hash_password
from app.services.document_parser import document_parser
from app.services.groq_service import (
    groq_service,
    GroqRateLimitError,
    GroqServiceError,
    GroqAuthenticationError,
    GroqTimeoutError
)
from app.schemas.copilot import ExtractionStatus, ExtractedField
from app.models.investigation import Investigation
from app.models.deviation import Deviation
from app.models.evidence import Evidence, InvestigationFinding, EvidenceGap
from app.models.audit import User, AuditLog

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

# ==============================================================================
# REMEDIATION A: ELIMINATE FABRICATED FALLBACK DATA
# ==============================================================================

def test_remediation_a_unrelated_text_produces_no_fabricated_data():
    """CRITICAL: Unrelated text (cafeteria menu) must NOT manufacture an incident."""
    menu_text = (
        "Weekly Cafeteria Menu - Employee Dining Hall\n"
        "Monday: Tomato basil soup, grilled chicken salad, iced tea.\n"
        "Tuesday: Vegetable lasagna, garlic bread, fruit cup.\n"
        "Wednesday: Beef stir-fry, steamed rice, green tea.\n"
        "All meals served between 11:30 AM and 1:30 PM."
    )
    result = groq_service._fallback_intake_extraction(menu_text, source_type="TEXT")

    # Must NOT invent batch B2026-API-044, equipment RX-301, or Atorvastatin
    dev = result["deviation"]
    assert dev["batch_number"] == "UNRECORDED"
    assert dev["equipment_id"] is None
    assert dev["product_name"] == "Unspecified Product"
    assert dev["unit_operation"] is None
    assert dev["target_yield_kg"] is None
    assert dev["actual_yield_kg"] is None
    assert dev["immediate_containment"] is None

    # Extracted findings must be empty for non-incident text
    assert len(result["extracted_findings"]) == 0

    # Fields check: all ungrounded fields must have status=MISSING and value=None
    field_dict = {f["field_name"]: f for f in result["extracted_fields"]}
    assert field_dict["batch_number"]["status"] == ExtractionStatus.MISSING.value
    assert field_dict["equipment_id"]["status"] == ExtractionStatus.MISSING.value
    assert field_dict["approved_range"]["value"] is None
    assert field_dict["approved_range"]["status"] == ExtractionStatus.MISSING.value
    assert field_dict["observed_value"]["value"] is None
    assert field_dict["observed_value"]["status"] == ExtractionStatus.MISSING.value
    assert field_dict["deviation_duration"]["value"] is None
    assert field_dict["deviation_duration"]["status"] == ExtractionStatus.MISSING.value

    # Title must not fabricate batch
    assert "B2026-API-044" not in result["investigation_title"]

def test_remediation_a_legitimate_incident_extracts_only_real_values():
    """Fallback extraction extracts matched patterns and leaves unmatched as MISSING."""
    incident_text = (
        "Batch B2026-ROSU-009 was processing in equipment CENT-102. "
        "During Centrifugation, temperature reached 32.5°C against approved range <= 25.0°C. "
        "The excursion lasted 15 minutes. QA hold placed immediately."
    )
    result = groq_service._fallback_intake_extraction(incident_text, source_type="TEXT")
    dev = result["deviation"]

    assert dev["batch_number"] == "B2026-ROSU-009"
    assert dev["equipment_id"] == "CENT-102"
    assert dev["unit_operation"] == "Centrifugation"
    assert "QA hold" in (dev["immediate_containment"] or "")
    # Does NOT invent yield
    assert dev["target_yield_kg"] is None
    assert dev["actual_yield_kg"] is None

# ==============================================================================
# REMEDIATION B: EXPLICIT HUMAN ACCEPTANCE
# ==============================================================================

def test_remediation_b_fields_initialize_unaccepted():
    """HIGH: All extracted fields must initially have is_accepted=False."""
    incident_text = "Batch B2026-API-088 in reactor RX-201 experienced temperature spike to 35.0°C."
    result = groq_service._fallback_intake_extraction(incident_text, source_type="TEXT")
    fields = result["extracted_fields"]
    assert len(fields) == 16
    for f in fields:
        assert f["is_accepted"] is False, f"Field {f['field_name']} initialized as accepted"

@pytest.mark.asyncio
async def test_remediation_b_unaccepted_fields_not_applied_to_investigation():
    """HIGH: Server-side apply must ignore fields where is_accepted=False."""
    user = await get_or_create_user("lead_inv_b", "INVESTIGATOR", "Lead Inv B")
    token = create_access_token({"sub": user.username, "role": user.role, "user_id": user.id})
    headers = {"Authorization": f"Bearer {token}"}

    async with get_session() as session:
        inv = Investigation(
            investigation_number=f"INV-B-{int(datetime.utcnow().timestamp())}",
            title="Initial Title",
            lead_investigator_id=user.id,
            lead_investigator=user.full_name
        )
        session.add(inv)
        await session.commit()
        await session.refresh(inv)
        inv_id = inv.id

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Submit fields where batch_number is unaccepted (is_accepted=False)
        payload = {
            "investigation_id": inv_id,
            "apply_deviation": True,
            "apply_evidence": True,
            "reviewed_fields": [
                {
                    "field_name": "batch_number",
                    "label": "Batch Number",
                    "value": "FORGED-BATCH-999",
                    "status": "SOURCE_FACT",
                    "is_accepted": False,  # Rejected by investigator
                    "user_edited": False
                },
                {
                    "field_name": "equipment_id",
                    "label": "Equipment ID",
                    "value": "RX-555",
                    "status": "SOURCE_FACT",
                    "is_accepted": True,  # Accepted by investigator
                    "source_reference": "RX-555 in plant",
                    "user_edited": False
                }
            ],
            "custom_overrides": {
                "raw_document_preview": "Equipment RX-555 in plant experienced excursion."
            }
        }
        res = await client.post("/api/v1/intake/apply-to-investigation", json=payload, headers=headers)
        assert res.status_code == 200
        data = res.json()

        # Unaccepted batch_number was NOT applied
        dev = data.get("deviation") or {}
        assert dev.get("batch_number") != "FORGED-BATCH-999"
        # Accepted equipment_id WAS applied
        assert dev.get("equipment_id") == "RX-555"

        # Check findings: unaccepted batch_number finding was NOT created
        finding_texts = [f["finding_text"] for f in data.get("findings", [])]
        assert not any("FORGED-BATCH-999" in ft for ft in finding_texts)

# ==============================================================================
# REMEDIATION C & D: HARDENED CITATION VALIDATION & SERVER REVALIDATION
# ==============================================================================

def test_remediation_d_rejects_embedded_quote_in_fabricated_prose():
    """HIGH: Embedding a real quote in a fabricated claim must be rejected."""
    source_text = "Valve demand was 100%, but actual position feedback stayed at 12%."
    finding_text = "Operator intentionally sabotaged batch: 'Valve demand was 100%'"

    val = document_parser.validate_source_citation(finding_text, source_text)
    assert val["is_valid"] is False
    assert val["match_type"] == "EMBEDDED_FABRICATION"
    assert "sabotaged" in val["explanation"].lower() or "intentionally" in val["explanation"].lower()

def test_remediation_d_rejects_numeric_metric_mismatch():
    """HIGH: Numeric parameters not grounded in text must be rejected."""
    source_text = "Temperature rose to 38.4°C during crystallization."
    finding_text = "Temperature rose to 45.0°C during crystallization."

    val = document_parser.validate_source_citation(finding_text, source_text)
    assert val["is_valid"] is False
    assert "Numeric parameter mismatch" in val["explanation"]

def test_remediation_d_token_overlap_alone_does_not_qualify_as_source_fact():
    """HIGH: Token overlap alone cannot be marked as verified citation."""
    source_text = "The reactor cooling jacket valve CV-04 failed to stroke open during the ramp."
    paraphrased = "Reactor cooling jacket valve failed stroke open ramp"

    val = document_parser.validate_source_citation(paraphrased, source_text)
    # Since words are not continuous span in source, is_valid must be False
    assert val["is_valid"] is False
    assert "not a continuous span" in val["explanation"]

def test_remediation_d_page_reference_mismatch_rejected():
    """HIGH: Citation claiming Page 1 when text is on Page 2 must be rejected."""
    pages = [
        {"page_number": 1, "text": "Batch processing began at 08:00 AM under standard SOP."},
        {"page_number": 2, "text": "Cooling valve CV-04 failed to stroke open at 14:15."}
    ]
    source_full = "\n".join(p["text"] for p in pages)
    finding = "Cooling valve CV-04 failed to stroke open"

    val = document_parser.validate_source_citation(finding, source_full, pages_metadata=pages, claimed_page=1)
    assert val["is_valid"] is False
    assert "Page reference mismatch" in val["explanation"]
    assert "Page 2" in val["explanation"]

@pytest.mark.asyncio
async def test_remediation_c_server_demotes_unverified_client_source_fact():
    """HIGH: Backend revalidates citations; ungrounded client claims demoted to AI_INFERENCE."""
    user = await get_or_create_user("lead_inv_c", "INVESTIGATOR", "Lead Inv C")
    token = create_access_token({"sub": user.username, "role": user.role, "user_id": user.id})
    headers = {"Authorization": f"Bearer {token}"}

    async with get_session() as session:
        inv = Investigation(
            investigation_number=f"INV-C-{int(datetime.utcnow().timestamp())}",
            title="Citation Test",
            lead_investigator_id=user.id,
            lead_investigator=user.full_name
        )
        session.add(inv)
        await session.commit()
        await session.refresh(inv)
        inv_id = inv.id

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Client maliciously claims status=SOURCE_FACT for completely fabricated claim
        payload = {
            "investigation_id": inv_id,
            "apply_deviation": True,
            "apply_evidence": True,
            "reviewed_fields": [
                {
                    "field_name": "observed_value",
                    "label": "Observed Value",
                    "value": "99.9°C Boiling Excursion",
                    "source_reference": "Spiked to 99.9°C in reactor",  # Not in source!
                    "status": "SOURCE_FACT",  # Client forged status
                    "is_accepted": True,
                    "user_edited": False
                }
            ],
            "custom_overrides": {
                "raw_document_preview": "Temperature spiked to 38.4°C in reactor RX-301."
            }
        }
        res = await client.post("/api/v1/intake/apply-to-investigation", json=payload, headers=headers)
        assert res.status_code == 200
        data = res.json()

        # Finding must be demoted: citation_verified=False, validation_status=AI_INFERENCE
        findings = data.get("findings", [])
        obs_finding = next((f for f in findings if "Observed Value" in f["finding_text"]), None)
        assert obs_finding is not None
        assert obs_finding["citation_verified"] is False
        assert obs_finding["validation_status"] == "AI_INFERENCE"

# ==============================================================================
# REMEDIATION E: IDEMPOTENCY OF APPLY OPERATION
# ==============================================================================

@pytest.mark.asyncio
async def test_remediation_e_apply_is_strictly_idempotent():
    """MEDIUM: Repeated apply calls must NOT duplicate Evidence, Findings, or Gaps."""
    user = await get_or_create_user("lead_inv_e", "INVESTIGATOR", "Lead Inv E")
    token = create_access_token({"sub": user.username, "role": user.role, "user_id": user.id})
    headers = {"Authorization": f"Bearer {token}"}

    async with get_session() as session:
        inv = Investigation(
            investigation_number=f"INV-E-{int(datetime.utcnow().timestamp())}",
            title="Idempotency Test",
            lead_investigator_id=user.id,
            lead_investigator=user.full_name
        )
        session.add(inv)
        await session.commit()
        await session.refresh(inv)
        inv_id = inv.id

    doc_text = "Batch B2026-API-099 processed in equipment RX-301. Temperature peaked at 38.4°C."
    doc_hash = document_parser.compute_sha256(doc_text.encode())

    payload = {
        "investigation_id": inv_id,
        "apply_deviation": True,
        "apply_evidence": True,
        "reviewed_fields": [
            {
                "field_name": "batch_number",
                "label": "Batch Number",
                "value": "B2026-API-099",
                "source_reference": "Batch B2026-API-099",
                "status": "SOURCE_FACT",
                "is_accepted": True,
                "user_edited": False
            },
            {
                "field_name": "equipment_id",
                "label": "Equipment ID",
                "value": "RX-301",
                "source_reference": "equipment RX-301",
                "status": "SOURCE_FACT",
                "is_accepted": True,
                "user_edited": False
            }
        ],
        "custom_overrides": {
            "raw_document_preview": doc_text,
            "missing_information": [
                {
                    "category": "CALIBRATION_RECORDS",
                    "question": "Was RX-301 calibrated in the last 6 months?",
                    "impact_description": "Rule out sensor drift",
                    "urgency": "HIGH"
                }
            ]
        },
        "evidence_metadata": {
            "filename": "batch_099.txt",
            "file_hash_sha256": doc_hash
        }
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # First Apply
        res1 = await client.post("/api/v1/intake/apply-to-investigation", json=payload, headers=headers)
        assert res1.status_code == 200
        data1 = res1.json()

        ev_count_1 = len(data1.get("evidences", []))
        finding_count_1 = len(data1.get("findings", []))
        gap_count_1 = len(data1.get("evidence_gaps", []))

        assert ev_count_1 == 1
        assert finding_count_1 == 2
        assert gap_count_1 == 1

        # Second Apply (identical payload)
        res2 = await client.post("/api/v1/intake/apply-to-investigation", json=payload, headers=headers)
        assert res2.status_code == 200
        data2 = res2.json()

        ev_count_2 = len(data2.get("evidences", []))
        finding_count_2 = len(data2.get("findings", []))
        gap_count_2 = len(data2.get("evidence_gaps", []))

        # Must NOT create duplicate records!
        assert ev_count_2 == ev_count_1, f"Evidence duplicated: {ev_count_2} vs {ev_count_1}"
        assert finding_count_2 == finding_count_1, f"Findings duplicated: {finding_count_2} vs {finding_count_1}"
        assert gap_count_2 == gap_count_1, f"EvidenceGaps duplicated: {gap_count_2} vs {gap_count_1}"

# ==============================================================================
# REMEDIATION F: GROQ ERROR HANDLING (HTTP 429 & HTTP 503)
# ==============================================================================

@pytest.mark.asyncio
async def test_remediation_f_groq_rate_limit_returns_429():
    """MEDIUM: Groq rate limit errors must return HTTP 429, not generic HTTP 500."""
    user = await get_or_create_user("lead_inv_f", "INVESTIGATOR", "Lead Inv F")
    token = create_access_token({"sub": user.username, "role": user.role, "user_id": user.id})
    headers = {"Authorization": f"Bearer {token}"}

    with patch("app.services.langgraph_workflow.rca_graph.ainvoke", side_effect=GroqRateLimitError("Rate limit reached: 200,000 TPD exceeded")):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            res = await client.post(
                "/api/v1/intake/parse-text",
                json={"content": "Batch B2026-API-001 incident details", "is_email": False},
                headers=headers
            )
            assert res.status_code == 429
            assert "rate limit" in res.json()["detail"].lower()

@pytest.mark.asyncio
async def test_remediation_f_groq_service_unavailable_returns_503():
    """MEDIUM: Groq service outage returns HTTP 503, not generic HTTP 500."""
    user = await get_or_create_user("lead_inv_f2", "INVESTIGATOR", "Lead Inv F2")
    token = create_access_token({"sub": user.username, "role": user.role, "user_id": user.id})
    headers = {"Authorization": f"Bearer {token}"}

    with patch("app.services.langgraph_workflow.rca_graph.ainvoke", side_effect=GroqServiceError("Service Unavailable: 503 backend error")):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            res = await client.post(
                "/api/v1/intake/parse-text",
                json={"content": "Batch B2026-API-001 incident details", "is_email": False},
                headers=headers
            )
            assert res.status_code == 503
            assert "unavailable" in res.json()["detail"].lower()

# ==============================================================================
# REMEDIATION G: CORRECT PAGE ATTRIBUTION
# ==============================================================================

def test_remediation_g_unpaginated_text_has_none_page_number():
    """LOW: Unpaginated text must return page_number=None, never defaulting to 1."""
    text = "Batch B2026-API-050 experienced temperature deviation in reactor RX-101."
    result = groq_service._fallback_intake_extraction(text, source_type="TEXT")
    for f in result["extracted_fields"]:
        assert f["page_number"] is None, f"Field {f['field_name']} defaulted page_number to {f['page_number']}"

# ==============================================================================
# REMEDIATION H: FIELD-LEVEL REVIEWER ATTRIBUTION IN POSTGRESQL
# ==============================================================================

@pytest.mark.asyncio
async def test_remediation_h_reviewer_attribution_persisted():
    """LOW: Reviewer attribution (reviewed_by_id, is_accepted, user_edited, reviewed_at) persisted."""
    user = await get_or_create_user("lead_inv_h", "INVESTIGATOR", "Lead Inv H")
    token = create_access_token({"sub": user.username, "role": user.role, "user_id": user.id})
    headers = {"Authorization": f"Bearer {token}"}

    async with get_session() as session:
        inv = Investigation(
            investigation_number=f"INV-H-{int(datetime.utcnow().timestamp())}",
            title="Reviewer Attribution Test",
            lead_investigator_id=user.id,
            lead_investigator=user.full_name
        )
        session.add(inv)
        await session.commit()
        await session.refresh(inv)
        inv_id = inv.id

    doc_text = "Reactor RX-901 experienced thermal runaway."
    payload = {
        "investigation_id": inv_id,
        "apply_deviation": True,
        "apply_evidence": True,
        "reviewed_fields": [
            {
                "field_name": "equipment_id",
                "label": "Equipment ID",
                "value": "RX-901-MODIFIED",
                "original_value": "RX-901",
                "source_reference": "Reactor RX-901",
                "status": "SOURCE_FACT",
                "is_accepted": True,
                "user_edited": True
            }
        ],
        "custom_overrides": {
            "raw_document_preview": doc_text
        }
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post("/api/v1/intake/apply-to-investigation", json=payload, headers=headers)
        assert res.status_code == 200

    # Query PostgreSQL directly to verify attribution columns
    async with get_session() as session:
        stmt = select(InvestigationFinding).where(
            InvestigationFinding.investigation_id == inv_id,
            InvestigationFinding.finding_text.startswith("Equipment ID:")
        )
        finding_res = await session.execute(stmt)
        finding = finding_res.scalars().first()

        assert finding is not None
        assert finding.reviewed_by_id == user.id
        assert finding.is_accepted is True
        assert finding.user_edited is True
        assert finding.reviewed_at is not None
        assert finding.original_finding_text == "RX-901"


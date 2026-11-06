import pytest
import io
import pypdf
from unittest.mock import patch
from httpx import AsyncClient, ASGITransport
from sqlalchemy.future import select
from fastapi import UploadFile

from app.main import app
from app.core import database
from app.core.security import create_access_token, hash_password
from app.services.document_parser import document_parser
from app.services.storage_service import storage_service
from app.services.groq_service import groq_service, GroqRateLimitError, GroqServiceError
from app.schemas.copilot import ExtractionStatus
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
# SECTION A: PURE UNIT TESTS - DOCUMENT PARSING & VALIDATION
# ==============================================================================

def test_multi_page_pdf_parsing_and_page_preservation():
    """Unit Test: Multi-page PDF parsing preserves page count, text, and SHA-256."""
    writer = pypdf.PdfWriter()
    
    # Page 1
    page1 = writer.add_blank_page(width=300, height=300)
    # Page 2
    page2 = writer.add_blank_page(width=300, height=300)
    # Page 3
    page3 = writer.add_blank_page(width=300, height=300)
    
    stream = io.BytesIO()
    writer.write(stream)
    pdf_bytes = stream.getvalue()

    result = document_parser.parse_pdf_structured(pdf_bytes)
    assert result["page_count"] == 3
    assert len(result["pages"]) == 3
    assert result["pages"][0]["page_number"] == 1
    assert result["pages"][1]["page_number"] == 2
    assert result["pages"][2]["page_number"] == 3
    assert len(result["file_hash_sha256"]) == 64
    assert result["file_size_bytes"] == len(pdf_bytes)

def test_invalid_pdf_rejected():
    """Unit Test: Malformed non-PDF bytes raise parsing error."""
    bad_bytes = b"NOT_A_PDF_DOCUMENT_GARBAGE_BYTES"
    with pytest.raises(ValueError, match="Failed to parse PDF document"):
        document_parser.parse_pdf_structured(bad_bytes)

def test_pasted_text_normalization():
    """Unit Test: Text cleaning strips carriage returns and multiple newlines."""
    raw = "Line 1\r\n\r\n\r\n\r\nLine 2 \r\n\r\nLine 3"
    cleaned = document_parser.clean_text(raw)
    assert cleaned == "Line 1\n\nLine 2 \n\nLine 3"

def test_valid_email_parsing():
    """Unit Test: Valid RFC 5322 email extracts headers and body."""
    raw_email = """Subject: Deviation in Batch B2026-API-044
From: dr.sarah@aivoa-pharma.com
Date: Wed, 04 Nov 2026 14:15:00 +0000
To: quality@aivoa-pharma.com

Temperature excursion occurred during crystallization in reactor RX-301.
"""
    parsed = document_parser.parse_email(raw_email)
    assert parsed["headers"]["subject"] == "Deviation in Batch B2026-API-044"
    assert parsed["headers"]["from"] == "dr.sarah@aivoa-pharma.com"
    assert parsed["headers"]["date"] == "Wed, 04 Nov 2026 14:15:00 +0000"
    assert "Temperature excursion occurred" in parsed["body"]

def test_malformed_email_handling():
    """Unit Test: Malformed email without standard headers parses body gracefully."""
    raw_email = "Just a quick note: valve stuck at 12% stroke. Investigate immediately."
    parsed = document_parser.parse_email(raw_email)
    assert isinstance(parsed["headers"], dict)
    assert parsed["body"] == raw_email

def test_citation_validation_exact_and_normalized_matching():
    """Unit Test: Verbatim citation matches return EXACT match with high confidence."""
    source_text = "At 14:15, the crystallization temperature abruptly rose to 38.4°C and stayed high for 42 minutes."
    
    # Exact match
    res_exact = document_parser.validate_source_citation("abruptly rose to 38.4°C", source_text)
    assert res_exact["is_valid"] is True
    assert res_exact["match_type"] == "EXACT"
    assert res_exact["confidence"] == 1.0

    # Normalized whitespace match
    res_norm = document_parser.validate_source_citation("abruptly   rose   to  38.4°C", source_text)
    assert res_norm["is_valid"] is True
    assert res_norm["match_type"] == "NORMALIZED_SPAN"

def test_citation_validation_fabricated_quote_and_numeric_mismatch():
    """Unit Test: Fabricated quotation and unsupported numbers are rejected."""
    source_text = "Reactor RX-301 temperature rose to 38.4C for 42 minutes."
    
    # Fabricated quotation
    res_fake_quote = document_parser.validate_source_citation(
        'Operator stated "the cooling water line froze completely overnight"',
        source_text
    )
    assert res_fake_quote["is_valid"] is False
    assert "Fabricated quotation detected" in res_fake_quote["explanation"]

    # Numeric mismatch
    res_fake_metric = document_parser.validate_source_citation(
        "Temperature spiked to 99.5C",
        source_text
    )
    assert res_fake_metric["is_valid"] is False
    assert "Numeric parameter mismatch" in res_fake_metric["explanation"]

# ==============================================================================
# SECTION B: STRUCTURED EXTRACTION SCHEMAS & FIELD STATUS CLASSIFICATION
# ==============================================================================

def test_structured_fields_16_required_parameters():
    """Unit Test: _build_structured_fields produces all 16 required pharmaceutical fields."""
    sample_text = """PHARMACEUTICAL MANUFACTURING DEVIATION REPORT
Plant: API Manufacturing Block 4
Incident Number: DEV-2026-084
Date of Occurrence: 04-Nov-2026 14:15 UTC
Product: Atorvastatin Calcium Trihydrate API
Batch Number: B2026-API-044
BPR Reference: BPR-ATV-044-REV2
Unit Operation: Crystallization (Stage 4)
Equipment Tag: Reactor RX-301

DESCRIPTION OF DEVIATION:
During cooling crystallization of batch B2026-API-044, reactor RX-301 experienced a temperature overshoot. Process recipe required cooling from 50.0°C to 20.0°C at 0.5°C/min. At 14:15, the temperature abruptly rose to 38.4°C and remained out of specification (>24.0°C) for 42 minutes.
SCADA logs show cooling control valve CV-04 demand was 100%, but actual valve position feedback stayed at 12%. Mother liquor sample ML-044 showed altered crystal aspect ratio.

IMMEDIATE CONTAINMENT:
Batch B2026-API-044 was immediately placed under physical QA quarantine and flagged in SAP. Mother liquor hold tank isolated. Sampling scheduled for HPLC related substances test."""

    dev_data = {
        "title": "Temperature Excursion in RX-301 Batch B2026-API-044",
        "deviation_number": "DEV-2026-084",
        "occurrence_datetime": "04-Nov-2026 14:15 UTC",
        "batch_number": "B2026-API-044",
        "product_name": "Atorvastatin Calcium Trihydrate API",
        "unit_operation": "Crystallization",
        "equipment_id": "RX-301",
        "description": "Temperature rose to 38.4°C exceeding limits for 42 minutes.",
        "immediate_containment": "Batch quarantined in mother liquor vessel."
    }

    fields, conflicts = groq_service._build_structured_fields(
        document_text=sample_text,
        deviation=dev_data
    )

    # Must contain 16 fields
    field_names = [f["field_name"] for f in fields]
    expected_fields = [
        "deviation_title", "deviation_number", "incident_datetime", "batch_number",
        "product_name", "unit_operation", "equipment_id", "process_parameter",
        "approved_range", "observed_value", "deviation_duration", "description",
        "immediate_containment", "potential_impact", "available_evidence", "conflicting_information"
    ]
    for ef in expected_fields:
        assert ef in field_names, f"Expected field '{ef}' missing from extracted fields"

    # Verify status tags
    batch_f = next(f for f in fields if f["field_name"] == "batch_number")
    assert batch_f["value"] == "B2026-API-044"
    assert batch_f["status"] == ExtractionStatus.SOURCE_FACT.value
    assert batch_f["confidence"] == 1.0

    # Conflicting information detected
    conflict_f = next(f for f in fields if f["field_name"] == "conflicting_information")
    assert conflict_f["status"] == ExtractionStatus.CONFLICTING.value
    assert len(conflicts) > 0
    assert conflicts[0]["field_name"] == "equipment_feedback"

def test_missing_field_assigned_missing_status():
    """Unit Test: When an unrecorded batch is provided, batch_number gets MISSING status."""
    text_no_batch = "Incident occurred in crystallization reactor RX-301 without recorded batch details."
    dev_data = {
        "batch_number": "UNRECORDED",
        "product_name": "Atorvastatin API",
        "unit_operation": "Crystallization",
        "equipment_id": "RX-301",
        "description": "Excursion observed."
    }

    fields, _ = groq_service._build_structured_fields(
        document_text=text_no_batch,
        deviation=dev_data
    )

    batch_f = next(f for f in fields if f["field_name"] == "batch_number")
    assert batch_f["status"] == ExtractionStatus.MISSING.value
    assert batch_f["confidence"] == 0.0

# ==============================================================================
# SECTION C: POSTGRESQL 16 INTEGRATION - INTAKE, REVIEW & PERSISTENCE LIFECYCLE
# ==============================================================================

@pytest.mark.asyncio
async def test_end_to_end_document_intake_review_and_postgresql_persistence():
    """Integration Test: Full intake -> review -> apply -> PostgreSQL persistence cycle."""
    await database.init_db()
    transport = ASGITransport(app=app)
    
    # 1. Authenticate Investigator
    user = await get_or_create_user("lead_investigator", "INVESTIGATOR", "Dr. Sarah Lin (QA Lead)")
    inv_token = create_access_token({"sub": user.username, "role": user.role, "user_id": user.id})
    headers = {"Authorization": f"Bearer {inv_token}"}

    with patch.object(groq_service, "extract_intake_data", side_effect=groq_service._fallback_intake_extraction), \
         patch.object(groq_service, "generate_rca_analysis", side_effect=groq_service._fallback_rca_generation):
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            # 2. Create Investigation dossier
            create_res = await ac.post("/api/v1/investigations/", headers=headers, json={
                "title": "API Crystallization Excursion Investigation",
                "lead_investigator": "Dr. Sarah Lin (QA Lead)"
            })
            assert create_res.status_code == 200, create_res.text
            inv = create_res.json()
            inv_id = inv["id"]

            # 3. Document Intake: Parse Text
            incident_text = """Deviation in Batch B2026-API-044 of Atorvastatin API in RX-301.
Unit Operation: Crystallization.
Temperature peaked at 38.4C exceeding 22.0C limit for 42 minutes.
Valve demand was 100% but feedback stayed at 12%.
Immediate containment: Quarantine batch material."""

            intake_res = await ac.post("/api/v1/intake/parse-text", headers=headers, json={
                "content": incident_text,
                "is_email": False,
                "investigation_id": inv_id
            })
            assert intake_res.status_code == 200, intake_res.text
            extraction = intake_res.json()
            assert "extracted_fields" in extraction
            assert len(extraction["extracted_fields"]) >= 15
            assert extraction["deviation"]["batch_number"] == "B2026-API-044"
            assert extraction["source_metadata"]["file_hash_sha256"] is not None

            # 4. Human Review: Edit a field value and accept/reject
            reviewed_fields = list(extraction["extracted_fields"])
            # Investigator edits deviation description
            desc_field = next(f for f in reviewed_fields if f["field_name"] == "description")
            desc_field["value"] = "Formal Investigation: Temperature overshoot in Crystallization RX-301 confirmed."
            desc_field["user_edited"] = True

            # Investigator accepts fields
            for f in reviewed_fields:
                f["is_accepted"] = True

            # 5. Apply Reviewed Data to Investigation
            apply_res = await ac.post("/api/v1/intake/apply-to-investigation", headers=headers, json={
                "investigation_id": inv_id,
                "apply_deviation": True,
                "apply_evidence": True,
                "reviewed_fields": reviewed_fields,
                "evidence_metadata": extraction["source_metadata"]
            })
            assert apply_res.status_code == 200, apply_res.text
            updated_inv = apply_res.json()

            # 6. Verify PostgreSQL Persistence
            assert updated_inv["deviation"] is not None
            assert updated_inv["deviation"]["batch_number"] == "B2026-API-044"
            assert updated_inv["deviation"]["equipment_id"] == "RX-301"
            assert updated_inv["deviation"]["is_ai_populated"] is True
            assert updated_inv["deviation"]["is_verified"] is False  # Explicit unverified flag

            # Verify Evidence persisted
            assert len(updated_inv["evidences"]) > 0
            intake_ev = updated_inv["evidences"][0]
            assert intake_ev["classification"] == "PRIMARY_SOURCE"
            assert intake_ev["is_verified"] is False
            assert intake_ev["file_hash_sha256"] == extraction["source_metadata"]["file_hash_sha256"]

            # Verify Findings persisted
            assert len(updated_inv["findings"]) > 0
            fact_finding = next((f for f in updated_inv["findings"] if f["citation_verified"] is True), None)
            assert fact_finding is not None

            # 7. Retrieval After Refresh (Simulate browser reload)
            get_res = await ac.get(f"/api/v1/investigations/{inv_id}", headers=headers)
            assert get_res.status_code == 200
            refreshed = get_res.json()
            assert refreshed["id"] == inv_id
            assert refreshed["deviation"]["batch_number"] == "B2026-API-044"
            assert len(refreshed["evidences"]) == len(updated_inv["evidences"])
            assert len(refreshed["findings"]) == len(updated_inv["findings"])

@pytest.mark.asyncio
async def test_authorization_isolation_on_intake_apply():
    """Security Test: Unauthorized user cannot apply intake data to another user's investigation."""
    await database.init_db()
    transport = ASGITransport(app=app)
    
    # Tokens for User 1 (Owner) and User 2 (Attacker)
    user1 = await get_or_create_user("lead_investigator", "INVESTIGATOR", "Dr. Sarah Lin (QA Lead)")
    user2 = await get_or_create_user("other_investigator", "INVESTIGATOR", "Other Investigator")
    user1_token = create_access_token({"sub": user1.username, "role": user1.role, "user_id": user1.id})
    user2_token = create_access_token({"sub": user2.username, "role": user2.role, "user_id": user2.id})
    headers1 = {"Authorization": f"Bearer {user1_token}"}
    headers2 = {"Authorization": f"Bearer {user2_token}"}

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Create investigation owned by User 1
        create_res = await ac.post("/api/v1/investigations/", headers=headers1, json={
            "title": "User 1 Investigation Dossier"
        })
        inv_id = create_res.json()["id"]

        # User 2 attempts to apply extraction to User 1's investigation
        hack_res = await ac.post("/api/v1/intake/apply-to-investigation", headers=headers2, json={
            "investigation_id": inv_id,
            "apply_deviation": True,
            "custom_overrides": {"deviation": {"batch_number": "MALICIOUS-BATCH"}}
        })
        assert hack_res.status_code == 403, "Cross-user intake modification must return 403 Forbidden"

# ==============================================================================
# SECTION D: LIVE GROQ INTEGRATION (OPT-IN LIVE PROVIDER)
# ==============================================================================

@pytest.mark.live_provider
@pytest.mark.asyncio
async def test_live_groq_intake_pipeline_or_quota_blocked():
    """Live Groq Test: Verifies live model inference if quota allows, or reports BLOCKED if 429."""
    incident_text = "Deviation in Batch B2026-API-044 of Atorvastatin API in RX-301. Unit Operation: Crystallization."
    try:
        res = groq_service.extract_intake_data(incident_text, source_type="TEXT")
        assert "extracted_fields" in res
        assert len(res["extracted_fields"]) >= 15
    except (GroqRateLimitError, GroqServiceError) as e:
        err_msg = str(e)
        if "429" in err_msg or "Rate limit" in err_msg or "TPD" in err_msg:
            pytest.skip(f"BLOCKED: Live Groq API daily token quota reached (429/TPD): {err_msg}")
        raise


import pytest
import io
import os
import hashlib
from datetime import datetime, timedelta
from httpx import AsyncClient, ASGITransport
from sqlalchemy.future import select

from app.main import app
from app.core import database
from app.models.investigation import Investigation
from app.models.evidence import Evidence, InvestigationFinding
from app.models.root_cause import RootCause, RootCauseEvidenceLink, ContradictionDisposition
from app.models.audit import User, AuditLog
from app.services.document_parser import document_parser
from app.services.storage_service import storage_service, FileIntegrityError
from app.core.security import create_access_token, hash_password, decode_access_token
from app.services.langgraph_workflow import evidence_analysis_node

def get_session():
    if database.AsyncSessionLocal is None:
        database.get_engine()
    return database.AsyncSessionLocal()

def get_auth_client(transport):
    token = create_access_token({"sub": "lead_investigator", "role": "INVESTIGATOR", "user_id": 1})
    return AsyncClient(transport=transport, base_url="http://test", headers={"Authorization": f"Bearer {token}"})

def get_qa_client(transport):
    token = create_access_token({"sub": "qa_director", "role": "QA_APPROVER", "user_id": 2})
    return AsyncClient(transport=transport, base_url="http://test", headers={"Authorization": f"Bearer {token}"})

# -------------------------------------------------------------
# Test 1 & 2: Original File Persistence & SHA-256 Download Verification
# -------------------------------------------------------------
@pytest.mark.asyncio
async def test_1_and_2_original_file_persistence_and_download():
    transport = ASGITransport(app=app)
    async with get_auth_client(transport) as ac:
        inv_res = await ac.post("/api/v1/investigations/", json={"title": "File Persistence Test Investigation"})
        assert inv_res.status_code == 200
        inv_id = inv_res.json()["id"]

        sample_pdf_bytes = b"%PDF-1.4\n1 0 obj\n<< /Title (Calibration Report) >>\nendobj\ntrailer\n<<>>\n%%EOF"
        expected_hash = hashlib.sha256(sample_pdf_bytes).hexdigest()

        # Upload file via multipart/form-data
        upload_res = await ac.post(
            f"/api/v1/investigations/{inv_id}/evidences/upload",
            files={"file": ("calibration_test_report.pdf", sample_pdf_bytes, "application/pdf")},
            data={"title": "Calibration Certificate RX-301", "evidence_type": "CALIBRATION_CERT"}
        )
        assert upload_res.status_code == 200
        ev_data = upload_res.json()
        ev_id = ev_data["id"]
        assert ev_data["file_hash_sha256"] == expected_hash
        assert ev_data["file_path"] is None  # Sensitive filesystem path is hidden from client
        assert ev_data["download_url"] == f"/api/v1/evidences/{ev_id}/download"

        # Verify file exists on disk
        async with get_session() as session:
            res = await session.execute(select(Evidence).filter(Evidence.id == ev_id))
            ev = res.scalar_one()
            assert ev.file_path is not None
            assert os.path.exists(ev.file_path)

        # Download file and verify SHA-256 check
        dl_res = await ac.get(f"/api/v1/evidences/{ev_id}/download")
        assert dl_res.status_code == 200
        assert dl_res.content == sample_pdf_bytes
        assert hashlib.sha256(dl_res.content).hexdigest() == expected_hash

# -------------------------------------------------------------
# Test 3: Detection of Modified or Missing Stored Files
# -------------------------------------------------------------
@pytest.mark.asyncio
async def test_3_detection_of_tampered_or_missing_files():
    transport = ASGITransport(app=app)
    async with get_auth_client(transport) as ac:
        inv_res = await ac.post("/api/v1/investigations/", json={"title": "Tamper Detection Test"})
        inv_id = inv_res.json()["id"]

        content = b"%PDF-1.4\nOriginal untampered batch telemetry record\n%%EOF"
        upload_res = await ac.post(
            f"/api/v1/investigations/{inv_id}/evidences/upload",
            files={"file": ("batch_telemetry.pdf", content, "application/pdf")},
            data={"title": "Telemetry Record"}
        )
        assert upload_res.status_code == 200
        ev_id = upload_res.json()["id"]

        # Fetch actual file path from DB
        async with get_session() as session:
            ev = (await session.execute(select(Evidence).filter(Evidence.id == ev_id))).scalar_one()
            file_path = ev.file_path

        # Case A: Tamper with on-disk bytes
        with open(file_path, "wb") as f:
            f.write(b"%PDF-1.4\nMALICIOUS TAMPERED MODIFIED BYTES INJECTED\n%%EOF")

        # Download attempt must fail with HTTP 409 Conflict due to SHA-256 mismatch
        tamper_dl = await ac.get(f"/api/v1/evidences/{ev_id}/download")
        assert tamper_dl.status_code == 409
        assert "integrity check failed" in tamper_dl.json()["detail"].lower()

        # Case B: Delete file from disk
        os.remove(file_path)
        missing_dl = await ac.get(f"/api/v1/evidences/{ev_id}/download")
        assert missing_dl.status_code == 404

# -------------------------------------------------------------
# Test 4: Rejection of Extracted Source Text Modification
# -------------------------------------------------------------
@pytest.mark.asyncio
async def test_4_rejection_of_source_text_modification():
    transport = ASGITransport(app=app)
    async with get_auth_client(transport) as ac:
        inv_res = await ac.post("/api/v1/investigations/", json={"title": "Immutability Test"})
        inv_id = inv_res.json()["id"]

        ev_res = await ac.post(f"/api/v1/investigations/{inv_id}/evidences/manual", json={
            "title": "Initial Observation Log",
            "extracted_text": "Temperature recorded at 52C on sensor PT-101."
        })
        ev_id = ev_res.json()["id"]

        # Attempt to modify original extracted_text must be rejected with HTTP 400
        tamper_attempt = await ac.put(f"/api/v1/evidences/{ev_id}", json={
            "extracted_text": "Temperature fraudulently changed to 45C (in spec)."
        })
        assert tamper_attempt.status_code == 400
        assert "immutable" in tamper_attempt.json()["detail"].lower()

        # Legitimate metadata update (investigator notes, title) must succeed
        valid_update = await ac.put(f"/api/v1/evidences/{ev_id}", json={
            "title": "Observation Log (Annotated)",
            "investigator_notes": "Cross-checked with secondary sensor PT-102."
        })
        assert valid_update.status_code == 200
        assert valid_update.json()["title"] == "Observation Log (Annotated)"
        assert valid_update.json()["extracted_text"] == "Temperature recorded at 52C on sensor PT-101."

# -------------------------------------------------------------
# Test 5 & 6: Contradiction Disposition Workflow & Preservation
# -------------------------------------------------------------
@pytest.mark.asyncio
async def test_5_and_6_contradiction_disposition_workflow():
    transport = ASGITransport(app=app)
    async with get_auth_client(transport) as ac:
        inv_res = await ac.post("/api/v1/investigations/", json={"title": "Disposition Workflow Test"})
        inv_id = inv_res.json()["id"]

        # Verified supporting evidence
        ev_supp = await ac.post(f"/api/v1/investigations/{inv_id}/evidences/manual", json={
            "title": "SCADA trend showing valve closed",
            "extracted_text": "Valve command 100%, position 0% for 35 mins"
        })
        supp_id = ev_supp.json()["id"]
        async with get_qa_client(transport) as qa_ac:
            await qa_ac.post(f"/api/v1/evidences/{supp_id}/verify", json={"investigator_name": "Dr. Elena Rostova"})

        # Contradictory evidence
        ev_contra = await ac.post(f"/api/v1/investigations/{inv_id}/evidences/manual", json={
            "title": "Operator log note on manual bypass",
            "extracted_text": "Operator note suggests manual bypass valve was opened."
        })
        contra_id = ev_contra.json()["id"]

        # Create Root Cause
        async with get_session() as session:
            rc = RootCause(
                investigation_id=inv_id,
                cause_statement="Cooling valve mechanically seized",
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
            "evidence_id": supp_id,
            "relationship_type": "SUPPORTING"
        })
        c_link = await ac.post(f"/api/v1/root-causes/{rc_id}/evidence-links", json={
            "evidence_id": contra_id,
            "relationship_type": "CONTRADICTORY",
            "relevance_explanation": "Manual bypass could explain cooling regardless of valve status"
        })
        link_id = c_link.json()["id"]

        # Confirmation must fail while contradiction is active
        async with get_qa_client(transport) as qa_ac:
            conf_fail = await qa_ac.post(f"/api/v1/root-causes/{rc_id}/confirm", json={
                "investigator_name": "Dr. Elena Rostova",
                "justification": "Primary valve failure is clear."
            })
            assert conf_fail.status_code == 400

        # Attempt to delete contradictory link without rationale must be rejected
        del_fail = await ac.delete(f"/api/v1/root-causes/{rc_id}/evidence-links/{link_id}")
        assert del_fail.status_code == 400
        assert "disposition rationale" in del_fail.json()["detail"].lower()

        # Dismiss contradictory link with mandatory scientific rationale
        rationale = "Physical inspection of manual bypass verified lock-out tag was intact; log note was a retrospective speculation."
        del_ok = await ac.delete(
            f"/api/v1/root-causes/{rc_id}/evidence-links/{link_id}?disposition_rationale={rationale}&investigator_name=Dr.%20Sarah%20Lin"
        )
        assert del_ok.status_code == 200

        # Verify disposition history is preserved on the root cause
        inv_check = await ac.get(f"/api/v1/investigations/{inv_id}")
        assert inv_check.status_code == 200
        rc_data = next(r for r in inv_check.json()["root_causes"] if r["id"] == rc_id)
        assert len(rc_data["dispositions"]) == 1
        disp = rc_data["dispositions"][0]
        assert disp["evidence_id"] == contra_id
        assert "Dr. Sarah Lin" in disp["dismissed_by"]
        assert disp["disposition_rationale"] == rationale

        # Now confirmation succeeds when signed by QA!
        async with get_qa_client(transport) as qa_ac:
            conf_ok = await qa_ac.post(f"/api/v1/root-causes/{rc_id}/confirm", json={
                "investigator_name": "Dr. Elena Rostova",
                "justification": "Contradiction resolved by physical lock-out verification. SCADA data fully corroborates valve seizure."
            })
            assert conf_ok.status_code == 200
            assert conf_ok.json()["status"] == "CONFIRMED"

# -------------------------------------------------------------
# Test 7 & 8: Evidence Soft Archival Without Cascade & Exclusion
# -------------------------------------------------------------
@pytest.mark.asyncio
async def test_7_and_8_evidence_soft_archival():
    transport = ASGITransport(app=app)
    async with get_auth_client(transport) as ac:
        inv_res = await ac.post("/api/v1/investigations/", json={"title": "Archival Test"})
        inv_id = inv_res.json()["id"]

        ev_res = await ac.post(f"/api/v1/investigations/{inv_id}/evidences/manual", json={
            "title": "Superseded Sensor Log",
            "extracted_text": "Temporary diagnostic sensor data."
        })
        ev_id = ev_res.json()["id"]

        # Soft archive evidence
        arch_res = await ac.delete(f"/api/v1/evidences/{ev_id}?investigator_name=Dr.%20Sarah%20Lin&archival_reason=Superseded%20by%20official%20SCADA")
        assert arch_res.status_code == 200
        assert arch_res.json()["is_archived"] is True

        # Verify row still exists in DB (not physical deletion)
        async with get_session() as session:
            ev = (await session.execute(select(Evidence).filter(Evidence.id == ev_id))).scalar_one()
            assert ev.is_archived is True
            assert ev.archived_at is not None
            assert "Dr. Sarah Lin" in ev.archived_by

        # Active list by default excludes archived evidence
        active_list = await ac.get(f"/api/v1/investigations/{inv_id}/evidences")
        assert len(active_list.json()) == 0

        # Query with include_archived=true includes it
        full_list = await ac.get(f"/api/v1/investigations/{inv_id}/evidences?include_archived=true")
        assert len(full_list.json()) == 1
        assert full_list.json()[0]["is_archived"] is True

        # Attempt to link archived evidence to root cause must be blocked
        async with get_session() as session:
            rc = RootCause(investigation_id=inv_id, cause_statement="Sample Cause", status="PROPOSED")
            session.add(rc)
            await session.commit()
            await session.refresh(rc)
            rc_id = rc.id

        link_fail = await ac.post(f"/api/v1/root-causes/{rc_id}/evidence-links", json={
            "evidence_id": ev_id,
            "relationship_type": "SUPPORTING"
        })
        assert link_fail.status_code == 400
        assert "archived" in link_fail.json()["detail"].lower()

# -------------------------------------------------------------
# Test 9: Runtime Source Citation Validation in LangGraph
# -------------------------------------------------------------
def test_9_runtime_source_citation_validation_in_langgraph():
    source_text = (
        "Batch B2026-API-044 manufacturing excursion on 12-OCT-2026. "
        "During the crystallization stage in reactor RX-301, the temperature controller malfunctioned, "
        "causing a temperature spike to 64C against the upper SOP limit of 50C."
    )

    state = {
        "raw_document": source_text,
        "parsed_text": source_text,
        "metadata": {"pages": [{"page_number": 1, "text": source_text, "char_count": len(source_text)}]},
        "extracted_data": {
            "extracted_findings": [
                {
                    "finding_text": "temperature spike to 64C against the upper SOP limit of 50C",
                    "page_number": 1
                },
                {
                    "finding_text": "The cooling jacket ruptured causing massive solvent deluge", # Hallucinated/fabricated finding
                    "page_number": 1
                }
            ]
        },
        "trace_log": []
    }

    result = evidence_analysis_node(state)
    analysis = result["evidence_analysis"]

    assert analysis["total_findings"] == 2
    assert analysis["verified_findings_count"] == 1
    assert analysis["unverified_findings_count"] == 1

    # Verified finding must be in traceable facts & supporting
    assert any("64c" in str(f).lower() for f in analysis["traceable_facts"])
    # Hallucinated finding must NOT be in supporting findings
    assert not any("ruptured" in str(f).lower() for f in analysis["supporting_findings"])
    assert any("ruptured" in str(f).lower() for f in analysis["unverified_facts"])

# -------------------------------------------------------------
# Test 10: Fabricated Quotation and Citation Rejection
# -------------------------------------------------------------
def test_10_fabricated_quotation_and_citation_rejection():
    source_document = (
        "Investigation into crystallization delay in RX-301. "
        "Operator observed motor speed dropped from 150 rpm to 45 rpm at 14:22. "
        "Product tested at 98.4% purity."
    )

    # 1. Exact match test
    res_exact = document_parser.validate_source_citation(
        "motor speed dropped from 150 rpm to 45 rpm at 14:22",
        source_document
    )
    assert res_exact["is_valid"] is True
    assert res_exact["match_type"] in ("EXACT", "NORMALIZED_SPAN")

    # 2. Fabricated quotation test (quote not in document)
    res_fake_quote = document_parser.validate_source_citation(
        'Operator stated "the entire batch was abandoned and discarded"',
        source_document
    )
    assert res_fake_quote["is_valid"] is False
    assert "fabricated quotation" in res_fake_quote["explanation"].lower()

    # 3. Numeric mismatch test (wrong numbers)
    res_num_mismatch = document_parser.validate_source_citation(
        "motor speed dropped to 10 rpm at 18:00",
        source_document
    )
    assert res_num_mismatch["is_valid"] is False
    assert "mismatch" in res_num_mismatch["explanation"].lower()

    # 4. Multi-page mismatch test
    pages = [
        {"page_number": 1, "text": "Page 1: Overview and batch intro."},
        {"page_number": 2, "text": "Page 2: Motor speed dropped from 150 rpm to 45 rpm."}
    ]
    res_page_mismatch = document_parser.validate_source_citation(
        finding_or_excerpt="Motor speed dropped from 150 rpm to 45 rpm",
        source_text="Page 1: Overview and batch intro. Page 2: Motor speed dropped from 150 rpm to 45 rpm.",
        pages_metadata=pages,
        claimed_page=1  # Claimed Page 1, but actually on Page 2!
    )
    assert res_page_mismatch["is_valid"] is False
    assert "page reference mismatch" in res_page_mismatch["explanation"].lower()

# -------------------------------------------------------------
# Test 11: Direct Upload Validation (Oversized, Invalid, Traversal)
# -------------------------------------------------------------
@pytest.mark.asyncio
async def test_11_direct_upload_validation_guards():
    transport = ASGITransport(app=app)
    async with get_auth_client(transport) as ac:
        inv_res = await ac.post("/api/v1/investigations/", json={"title": "Upload Security Test"})
        inv_id = inv_res.json()["id"]

        # Case A: Unsupported file extension (.exe)
        exe_res = await ac.post(
            f"/api/v1/investigations/{inv_id}/evidences/upload",
            files={"file": ("malicious_payload.exe", b"MZ\x90\x00\x03\x00\x00\x00", "application/x-msdownload")}
        )
        assert exe_res.status_code == 400
        assert "unsupported file format" in exe_res.json()["detail"].lower()

        # Case B: Malformed PDF (starts without %PDF magic bytes)
        fake_pdf_res = await ac.post(
            f"/api/v1/investigations/{inv_id}/evidences/upload",
            files={"file": ("fake_document.pdf", b"This is plain text pretending to be a PDF file", "application/pdf")}
        )
        assert fake_pdf_res.status_code == 400
        assert "malformed pdf" in fake_pdf_res.json()["detail"].lower()

        # Case C: Path traversal attempt in filename
        clean_content = b"%PDF-1.4\nSafe content\n%%EOF"
        traversal_res = await ac.post(
            f"/api/v1/investigations/{inv_id}/evidences/upload",
            files={"file": ("../../../../etc/passwd.pdf", clean_content, "application/pdf")}
        )
        assert traversal_res.status_code == 200
        stored_ev_id = traversal_res.json()["id"]

        # Verify disk path is cleanly inside the investigation storage directory
        async with get_session() as session:
            ev = (await session.execute(select(Evidence).filter(Evidence.id == stored_ev_id))).scalar_one()
            assert ".." not in ev.file_path
            assert str(inv_id) in ev.file_path

# -------------------------------------------------------------
# Test 12: Human Review Identity and Authentication Token Enforcement
# -------------------------------------------------------------
@pytest.mark.asyncio
async def test_12_authentication_and_identity_binding():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Login with seeded credentials
        login_res = await ac.post("/api/v1/auth/login", json={
            "username": "lead_investigator",
            "password": "AivoaPass2026!"
        })
        assert login_res.status_code == 200
        token_data = login_res.json()
        token = token_data["access_token"]
        assert token_data["username"] == "lead_investigator"
        assert token_data["role"] == "INVESTIGATOR"

        # 2. Verify /auth/me returns authenticated identity
        me_res = await ac.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me_res.status_code == 200
        assert me_res.json()["username"] == "lead_investigator"
        assert "Sarah Lin" in me_res.json()["full_name"]

        # 3. Create investigation and evidence with authenticated token
        inv_res = await ac.post("/api/v1/investigations/", headers={"Authorization": f"Bearer {token}"}, json={"title": "Auth Binding Test"})
        assert inv_res.status_code == 200
        inv_id = inv_res.json()["id"]

        ev_res = await ac.post(
            f"/api/v1/investigations/{inv_id}/evidences/manual",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "title": "Auth Verified SOP Review",
                "extracted_text": "SOP-API-301 adhered to during crystallization."
            }
        )
        assert ev_res.status_code == 200
        ev_id = ev_res.json()["id"]

        # 4. Attempt to verify evidence as uploader: blocked by separation of duties
        self_verify_res = await ac.post(
            f"/api/v1/evidences/{ev_id}/verify",
            headers={"Authorization": f"Bearer {token}"},
            json={"investigator_name": "Ignored Spoofed Name", "verification_notes": "Self verification attempt."}
        )
        assert self_verify_res.status_code == 403
        assert "separation of duties" in self_verify_res.json()["detail"].lower()

        # Login as QA Approver (Dr. Elena Rostova)
        qa_login = await ac.post("/api/v1/auth/login", json={
            "username": "qa_director",
            "password": "AivoaPass2026!"
        })
        assert qa_login.status_code == 200
        qa_token = qa_login.json()["access_token"]

        # Verify evidence with QA Bearer token: identity is bound to authenticated user
        verify_res = await ac.post(
            f"/api/v1/evidences/{ev_id}/verify",
            headers={"Authorization": f"Bearer {qa_token}"},
            json={"investigator_name": "Ignored Spoofed Name", "verification_notes": "Verified under authenticated session."}
        )
        assert verify_res.status_code == 200
        # Verified_by MUST be the authenticated user's name, NOT the spoofed name!
        assert "Elena Rostova" in verify_res.json()["verified_by"]
        assert "Ignored Spoofed Name" not in verify_res.json()["verified_by"]

        # 5. Invalid / Expired token rejected
        bad_token_res = await ac.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid.malformed.token"})
        assert bad_token_res.status_code == 401

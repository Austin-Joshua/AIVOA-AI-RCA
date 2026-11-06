import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from datetime import datetime
from sqlalchemy.future import select

from app.main import app
from app.core.database import init_db, get_engine
from app.core.security import create_access_token
from app.models.audit import User

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
            email=f"{username}@pharmatest.internal",
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
async def test_scenarios_1_to_5_evidence_verification_integrity_and_separation_of_duties():
    """
    Scenarios 1-5:
    1. Manual evidence submitted with is_verified=true is still persisted unverified.
    2. Client-supplied verified_by cannot forge reviewer attribution.
    3. An uploader cannot verify their own evidence (HTTP 403).
    4. A separate authorized reviewer can verify evidence (HTTP 200).
    5. verified_by_user_id is derived exclusively from the JWT identity.
    """
    await init_db()
    transport = ASGITransport(app=app)
    async with get_auth_client(transport) as inv_ac, get_qa_client(transport) as qa_ac:
        # Create an investigation
        inv_res = await inv_ac.post("/api/v1/investigations/", json={
            "title": "Evidence Verification Integrity Investigation",
            "lead_investigator": "Dr. Sarah Lin (Lead)"
        })
        assert inv_res.status_code == 200
        inv_id = inv_res.json()["id"]

        # 1 & 2: Manual evidence submitted with client is_verified=True and forged verified_by
        ev_create_res = await inv_ac.post(f"/api/v1/investigations/{inv_id}/evidences/manual", json={
            "title": "Temperature Calibration Certificate",
            "evidence_type": "CALIBRATION_CERT",
            "classification": "PRIMARY_SOURCE",
            "source": "Physical Binder #3",
            "extracted_text": "Calibration RTD-101 verified within +/- 0.1C",
            "is_verified": True,  # Attacking client attempting pre-verification
            "verified_by": "Forged QA Director Signature",  # Attacking client forging reviewer
        })
        assert ev_create_res.status_code == 200
        ev_data = ev_create_res.json()
        ev_id = ev_data["id"]

        # Server-controlled guard check: verification state must remain False and verified_by None
        assert ev_data["is_verified"] is False, "Evidence must never be created pre-verified"
        assert ev_data["verified_by"] is None, "Client-supplied verified_by must be rejected/ignored"
        assert ev_data["verified_by_user_id"] is None
        assert ev_data["uploaded_by_user_id"] is not None

        # 3. Uploader attempts self-verification -> HTTP 403 Separation of Duties violation
        self_ver_res = await inv_ac.post(f"/api/v1/evidences/{ev_id}/verify", json={
            "investigator_name": "Dr. Sarah Lin",
            "verification_notes": "Attempting self-signoff on my own uploaded evidence."
        })
        assert self_ver_res.status_code == 403
        assert "Separation of duties violation" in self_ver_res.json()["detail"]

        # 4 & 5. Independent QA reviewer verifies evidence -> HTTP 200, verified_by_user_id derived from JWT
        qa_ver_res = await qa_ac.post(f"/api/v1/evidences/{ev_id}/verify", json={
            "investigator_name": "Dr. Elena Rostova",
            "verification_notes": "Independent QA check against primary calibration logs."
        })
        assert qa_ver_res.status_code == 200
        verified_ev = qa_ver_res.json()
        assert verified_ev["is_verified"] is True
        assert "Elena Rostova" in verified_ev["verified_by"]
        assert verified_ev["verified_by_user_id"] is not None
        assert verified_ev["verification_date"] is not None

        # Generic PUT cannot modify verification attribution or status
        tamper_put = await inv_ac.put(f"/api/v1/evidences/{ev_id}", json={
            "is_verified": False,
            "verified_by": "Manipulated Verifier",
            "investigator_notes": "Added legitimate investigator annotation."
        })
        assert tamper_put.status_code == 200
        tamper_data = tamper_put.json()
        assert tamper_data["is_verified"] is True, "Generic PUT must not modify is_verified"
        assert tamper_data["verified_by"] == verified_ev["verified_by"], "Generic PUT must not tamper with verified_by"


@pytest.mark.asyncio
async def test_scenarios_6_and_7_root_cause_confirmation_authorization_matrix():
    """
    Scenarios 6-7:
    6. Investigator cannot confirm a root cause (HTTP 403).
    7. QA approver and admin can confirm when all confirmation barriers pass.
    """
    await init_db()
    u_lead = await create_test_user("inv_lead_67", "INVESTIGATOR", "Dr. Lead Investigator")
    u_other = await create_test_user("inv_other_67", "INVESTIGATOR", "Dr. Other Investigator")
    u_qa = await create_test_user("qa_user_67", "QA_APPROVER", "Dr. QA Approver")
    u_admin = await create_test_user("admin_user_67", "ADMIN", "System Administrator")

    transport = ASGITransport(app=app)
    async with get_auth_client(transport, user_id=u_lead.id, username=u_lead.username) as lead_ac, \
               get_auth_client(transport, user_id=u_other.id, username=u_other.username) as other_inv_ac, \
               get_auth_client(transport, user_id=u_qa.id, username=u_qa.username, role="QA_APPROVER") as qa_ac, \
               get_auth_client(transport, user_id=u_admin.id, username=u_admin.username, role="ADMIN") as admin_ac:

        # Create investigation assigned to investigator_lead
        inv_res = await lead_ac.post("/api/v1/investigations/", json={
            "title": "RCA Confirmation Role Matrix Test",
            "lead_investigator": "Lead Investigator Ten"
        })
        assert inv_res.status_code == 200
        inv_id = inv_res.json()["id"]

        # Create root cause proposal
        rc_res = await lead_ac.post(f"/api/v1/investigations/{inv_id}/root-causes", json={
            "cause_statement": "Substandard mechanical face seal material supplied by alternate vendor.",
            "category": "RAW_MATERIAL",
            "is_primary": True,
            "rationale": "Polymer composition failed tensile testing."
        })
        rc_id = rc_res.json()["id"]

        # Upload supporting evidence
        ev_res = await lead_ac.post(
            f"/api/v1/investigations/{inv_id}/evidences/upload",
            data={"title": "Tensile Analysis Report"},
            files={"file": ("tensile.txt", b"Tensile strength 42 MPa below 60 MPa specification limit.", "text/plain")}
        )
        ev_id = ev_res.json()["id"]

        # QA verifies the evidence
        qa_ver = await qa_ac.post(f"/api/v1/evidences/{ev_id}/verify", json={
            "investigator_name": "Dr. Elena Rostova",
            "verification_notes": "Certificate verified against laboratory tensile tester output."
        })
        assert qa_ver.status_code == 200

        # Link supporting evidence to root cause
        link_res = await lead_ac.post(f"/api/v1/root-causes/{rc_id}/evidence-links", json={
            "evidence_id": ev_id,
            "relationship_type": "SUPPORTING",
            "relevance_explanation": "Tensile test proof."
        })
        assert link_res.status_code == 200

        # Scenario 6A: Assigned lead investigator attempts confirmation -> HTTP 403 Forbidden
        lead_conf_res = await lead_ac.post(f"/api/v1/root-causes/{rc_id}/confirm", json={
            "investigator_name": "Lead Investigator Ten",
            "justification": "Self-confirming my own root cause proposal."
        })
        assert lead_conf_res.status_code == 403
        assert "Forbidden" in lead_conf_res.json()["detail"] or "Separation of duties" in lead_conf_res.json()["detail"]

        # Scenario 6B: Unassigned non-owner investigator attempts confirmation -> HTTP 403 Forbidden
        other_conf_res = await other_inv_ac.post(f"/api/v1/root-causes/{rc_id}/confirm", json={
            "investigator_name": "Other Investigator",
            "justification": "Other investigator attempting confirmation."
        })
        assert other_conf_res.status_code == 403

        # Scenario 6C: Unauthenticated confirmation -> HTTP 401 Unauthorized
        async with AsyncClient(transport=transport, base_url="http://test") as anon_ac:
            anon_conf = await anon_ac.post(f"/api/v1/root-causes/{rc_id}/confirm", json={
                "investigator_name": "Anonymous Attacker",
                "justification": "Unauthenticated confirmation attempt."
            })
            assert anon_conf.status_code == 401

        # Scenario 7A: QA Approver confirms -> HTTP 200 OK
        qa_conf_res = await qa_ac.post(f"/api/v1/root-causes/{rc_id}/confirm", json={
            "investigator_name": "Dr. Elena Rostova",
            "justification": "Verified empirical proof of substandard polymer tensile properties."
        })
        assert qa_conf_res.status_code == 200
        confirmed_rc = qa_conf_res.json()
        assert confirmed_rc["status"] == "CONFIRMED"
        assert confirmed_rc["is_verified"] is True
        assert confirmed_rc["confirmed_by_user_id"] is not None
        assert confirmed_rc["confirmed_at"] is not None

        # Scenario 7B: Admin can confirm on another proposal
        rc_res_2 = await lead_ac.post(f"/api/v1/investigations/{inv_id}/root-causes", json={
            "cause_statement": "Secondary contributing factor: inspection protocol not updated.",
            "category": "PROCEDURE",
            "is_primary": False,
            "rationale": "SOP-API-092 did not require tensile certificate verification."
        })
        rc_id_2 = rc_res_2.json()["id"]

        # Link supporting evidence to proposal 2
        await lead_ac.post(f"/api/v1/root-causes/{rc_id_2}/evidence-links", json={
            "evidence_id": ev_id,
            "relationship_type": "SUPPORTING",
            "relevance_explanation": "Tensile verification gap."
        })

        admin_conf_res = await admin_ac.post(f"/api/v1/root-causes/{rc_id_2}/confirm", json={
            "investigator_name": "System Administrator",
            "justification": "Administrator review of procedure gap supported by evidence."
        })
        assert admin_conf_res.status_code == 200
        assert admin_conf_res.json()["status"] == "CONFIRMED"

        # Create root cause proposal
        rc_res = await lead_ac.post(f"/api/v1/investigations/{inv_id}/root-causes", json={
            "cause_statement": "Substandard mechanical face seal material supplied by alternate vendor.",
            "category": "RAW_MATERIAL",
            "is_primary": True,
            "rationale": "Polymer composition failed tensile testing."
        })
        rc_id = rc_res.json()["id"]

        # Upload supporting evidence
        ev_res = await lead_ac.post(
            f"/api/v1/investigations/{inv_id}/evidences/upload",
            data={"title": "Tensile Analysis Report"},
            files={"file": ("tensile.txt", b"Tensile strength 42 MPa below 60 MPa specification limit.", "text/plain")}
        )
        ev_id = ev_res.json()["id"]

        # QA verifies the evidence
        qa_ver = await qa_ac.post(f"/api/v1/evidences/{ev_id}/verify", json={
            "investigator_name": "Dr. Elena Rostova",
            "verification_notes": "Certificate verified against laboratory tensile tester output."
        })
        assert qa_ver.status_code == 200

        # Link supporting evidence to root cause
        link_res = await lead_ac.post(f"/api/v1/root-causes/{rc_id}/evidence-links", json={
            "evidence_id": ev_id,
            "relationship_type": "SUPPORTING",
            "relevance_explanation": "Tensile test proof."
        })
        assert link_res.status_code == 200

        # Scenario 6A: Assigned lead investigator attempts confirmation -> HTTP 403 Forbidden
        lead_conf_res = await lead_ac.post(f"/api/v1/root-causes/{rc_id}/confirm", json={
            "investigator_name": "Lead Investigator Ten",
            "justification": "Self-confirming my own root cause proposal."
        })
        assert lead_conf_res.status_code == 403
        assert "Forbidden" in lead_conf_res.json()["detail"] or "Separation of duties" in lead_conf_res.json()["detail"]

        # Scenario 6B: Unassigned non-owner investigator attempts confirmation -> HTTP 403 Forbidden
        other_conf_res = await other_inv_ac.post(f"/api/v1/root-causes/{rc_id}/confirm", json={
            "investigator_name": "Other Investigator",
            "justification": "Other investigator attempting confirmation."
        })
        assert other_conf_res.status_code == 403

        # Scenario 6C: Unauthenticated confirmation -> HTTP 401 Unauthorized
        async with AsyncClient(transport=transport, base_url="http://test") as anon_ac:
            anon_conf = await anon_ac.post(f"/api/v1/root-causes/{rc_id}/confirm", json={
                "investigator_name": "Anonymous Attacker",
                "justification": "Unauthenticated confirmation attempt."
            })
            assert anon_conf.status_code == 401

        # Scenario 7A: QA Approver confirms -> HTTP 200 OK
        qa_conf_res = await qa_ac.post(f"/api/v1/root-causes/{rc_id}/confirm", json={
            "investigator_name": "Dr. Elena Rostova",
            "justification": "Verified empirical proof of substandard polymer tensile properties."
        })
        assert qa_conf_res.status_code == 200
        confirmed_rc = qa_conf_res.json()
        assert confirmed_rc["status"] == "CONFIRMED"
        assert confirmed_rc["is_verified"] is True
        assert confirmed_rc["confirmed_by_user_id"] is not None
        assert confirmed_rc["confirmed_at"] is not None

        # Scenario 7B: Admin can confirm on another proposal
        rc_res_2 = await lead_ac.post(f"/api/v1/investigations/{inv_id}/root-causes", json={
            "cause_statement": "Secondary contributing factor: inspection protocol not updated.",
            "category": "PROCEDURE",
            "is_primary": False,
            "rationale": "SOP-API-092 did not require tensile certificate verification."
        })
        rc_id_2 = rc_res_2.json()["id"]

        # Link supporting evidence to proposal 2
        await lead_ac.post(f"/api/v1/root-causes/{rc_id_2}/evidence-links", json={
            "evidence_id": ev_id,
            "relationship_type": "SUPPORTING",
            "relevance_explanation": "Tensile verification gap."
        })

        admin_conf_res = await admin_ac.post(f"/api/v1/root-causes/{rc_id_2}/confirm", json={
            "investigator_name": "System Administrator",
            "justification": "Administrator review of procedure gap supported by evidence."
        })
        assert admin_conf_res.status_code == 200
        assert admin_conf_res.json()["status"] == "CONFIRMED"


@pytest.mark.asyncio
async def test_scenarios_8_to_11_root_cause_generic_update_and_provenance_validation():
    """
    Scenarios 8-11:
    8. Generic root-cause PUT cannot modify is_verified.
    9. Generic root-cause PUT cannot alter provenance (source_type, source_id).
    10. Unsupported source_type is rejected.
    11. Invalid and cross-investigation provenance references are rejected.
    """
    await init_db()
    transport = ASGITransport(app=app)
    async with get_auth_client(transport) as ac:
        # Create Investigation A and Investigation B
        inv_a = (await ac.post("/api/v1/investigations/", json={"title": "Inv A", "lead_investigator": "Dr. Lin"})).json()["id"]
        inv_b = (await ac.post("/api/v1/investigations/", json={"title": "Inv B", "lead_investigator": "Dr. Lin"})).json()["id"]

        # Create Five Whys step in Inv A
        why_a = (await ac.post(f"/api/v1/investigations/{inv_a}/five-whys", json={
            "step_number": 1,
            "question": "Why did pump cavitate?",
            "answer": "Suction head was insufficient.",
        })).json()["id"]

        # Create Fishbone cause in Inv A
        fish_a = (await ac.post(f"/api/v1/investigations/{inv_a}/fishbone", json={
            "category": "MACHINE",
            "cause_description": "Impeller wear ring clearance excessive",
        })).json()["id"]

        # Scenario 10: Unsupported source_type is rejected (e.g. UNKNOWN_TOOL -> HTTP 400 or 422)
        invalid_source_res = await ac.post(f"/api/v1/investigations/{inv_a}/root-causes", json={
            "cause_statement": "Invalid source test",
            "source_type": "UNKNOWN_TOOL",
            "source_id": 999
        })
        assert invalid_source_res.status_code in (400, 422), "Unsupported source_type must be rejected"

        # Scenario 11A: Nonexistent Five Whys source -> HTTP 400
        nonexistent_why_res = await ac.post(f"/api/v1/investigations/{inv_a}/root-causes", json={
            "cause_statement": "Nonexistent Why test",
            "source_type": "FIVE_WHYS",
            "source_id": 999999
        })
        assert nonexistent_why_res.status_code == 400
        assert "does not exist" in nonexistent_why_res.json()["detail"]

        # Scenario 11B: Cross-investigation Five Whys reference (Why A referenced from Inv B) -> HTTP 400
        cross_why_res = await ac.post(f"/api/v1/investigations/{inv_b}/root-causes", json={
            "cause_statement": "Cross Why test",
            "source_type": "FIVE_WHYS",
            "source_id": why_a
        })
        assert cross_why_res.status_code == 400
        assert "Cross-investigation provenance violation" in cross_why_res.json()["detail"]

        # Scenario 11C: Cross-investigation Fishbone reference (Fish A referenced from Inv B) -> HTTP 400
        cross_fish_res = await ac.post(f"/api/v1/investigations/{inv_b}/root-causes", json={
            "cause_statement": "Cross Fishbone test",
            "source_type": "FISHBONE",
            "source_id": fish_a
        })
        assert cross_fish_res.status_code == 400
        assert "Cross-investigation provenance violation" in cross_fish_res.json()["detail"]

        # Valid creation with valid Five Whys provenance in Inv A
        valid_rc_res = await ac.post(f"/api/v1/investigations/{inv_a}/root-causes", json={
            "cause_statement": "Pump cavitation due to inadequate suction head.",
            "source_type": "FIVE_WHYS",
            "source_id": why_a,
            "category": "EQUIPMENT_FAILURE",
            "is_primary": True
        })
        assert valid_rc_res.status_code == 200
        rc_data = valid_rc_res.json()
        rc_id = rc_data["id"]
        assert rc_data["source_type"] == "FIVE_WHYS"
        assert rc_data["source_id"] == why_a
        assert rc_data["is_verified"] is False

        # Scenario 8: Generic PUT cannot modify is_verified
        put_verified_res = await ac.put(f"/api/v1/root-causes/{rc_id}", json={
            "is_verified": True,
            "cause_statement": "Updated statement with attempted verified spoof"
        })
        assert put_verified_res.status_code == 200
        rc_after_put = put_verified_res.json()
        assert rc_after_put["is_verified"] is False, "Generic PUT must not modify is_verified"
        assert rc_after_put["cause_statement"] == "Updated statement with attempted verified spoof"

        # Scenario 9: Generic PUT cannot alter provenance (source_type, source_id)
        put_provenance_res = await ac.put(f"/api/v1/root-causes/{rc_id}", json={
            "source_type": "DIRECT_SYNTHESIS",
            "source_id": 99999
        })
        assert put_provenance_res.status_code == 200
        rc_after_prov = put_provenance_res.json()
        assert rc_after_prov["source_type"] == "FIVE_WHYS", "Generic PUT must not modify source_type"
        assert rc_after_prov["source_id"] == why_a, "Generic PUT must not modify source_id"


@pytest.mark.asyncio
async def test_scenario_12_provenance_deletion_protection():
    """
    Scenario 12: Source deletion cannot silently invalidate provenance (returns HTTP 409 Conflict).
    """
    await init_db()
    transport = ASGITransport(app=app)
    async with get_auth_client(transport) as ac:
        inv = (await ac.post("/api/v1/investigations/", json={"title": "Provenance Guard Inv", "lead_investigator": "Dr. Lin"})).json()["id"]

        # Create Why step and dependent Root Cause
        why_step = (await ac.post(f"/api/v1/investigations/{inv}/five-whys", json={
            "step_number": 1,
            "question": "Why did steam jacket lose pressure?",
            "answer": "Steam bypass valve stuck open.",
        })).json()["id"]

        rc_why = (await ac.post(f"/api/v1/investigations/{inv}/root-causes", json={
            "cause_statement": "Steam bypass valve seat degradation.",
            "source_type": "FIVE_WHYS",
            "source_id": why_step
        })).json()["id"]

        # Attempt deleting Why step while Root Cause depends on it -> HTTP 409 Conflict
        del_why_res = await ac.delete(f"/api/v1/five-whys/{why_step}")
        assert del_why_res.status_code == 409
        assert "depend on it for provenance" in del_why_res.json()["detail"]

        # Create Fishbone cause and dependent Root Cause
        fish_cause = (await ac.post(f"/api/v1/investigations/{inv}/fishbone", json={
            "category": "MACHINE",
            "cause_description": "Compressor oil filter bypass valve jammed open",
        })).json()["id"]

        rc_fish = (await ac.post(f"/api/v1/investigations/{inv}/root-causes", json={
            "cause_statement": "Compressor oil contamination.",
            "source_type": "FISHBONE",
            "source_id": fish_cause
        })).json()["id"]

        # Attempt deleting Fishbone cause while Root Cause depends on it -> HTTP 409 Conflict
        del_fish_res = await ac.delete(f"/api/v1/fishbone/{fish_cause}")
        assert del_fish_res.status_code == 409
        assert "depend on it for provenance" in del_fish_res.json()["detail"]


@pytest.mark.asyncio
async def test_scenarios_13_to_15_fishbone_promotion_locking_concurrency_and_links():
    """
    Scenarios 13-15:
    13. Repeated Fishbone promotion returns HTTP 409.
    14. Concurrent Fishbone promotion cannot create duplicate proposals.
    15. Promoted evidence links remain present after persistence and retrieval.
    """
    await init_db()
    transport = ASGITransport(app=app)
    async with get_auth_client(transport) as ac, get_qa_client(transport) as qa_ac:
        inv = (await ac.post("/api/v1/investigations/", json={"title": "Promotion Concurrency Inv", "lead_investigator": "Dr. Lin"})).json()["id"]

        # Add Fishbone cause
        cause = (await ac.post(f"/api/v1/investigations/{inv}/fishbone", json={
            "category": "METHOD",
            "cause_description": "Solvent wash rate exceeded filter membrane maximum flux limit",
            "status": "HYPOTHESIS",
            "rationale": "Batch record step 14 specified 120 L/min instead of 80 L/min maximum."
        })).json()
        cause_id = cause["id"]

        # Upload and verify supporting evidence
        ev_id = (await ac.post(
            f"/api/v1/investigations/{inv}/evidences/upload",
            data={"title": "Batch Wash Rate Record"},
            files={"file": ("wash_rate.txt", b"Wash step pumped at 120 L/min for 45 minutes.", "text/plain")}
        )).json()["id"]

        await qa_ac.post(f"/api/v1/evidences/{ev_id}/verify", json={
            "investigator_name": "Dr. Elena Rostova",
            "verification_notes": "Cross-verified with SCADA flow transmitter FT-204."
        })

        # Link evidence to fishbone cause
        await ac.post(f"/api/v1/fishbone/{cause_id}/evidence", json={
            "evidence_id": ev_id,
            "relationship_type": "SUPPORTING",
            "relevance_explanation": "SCADA wash telemetry."
        })

        # Mark cause VERIFIED
        await ac.post(f"/api/v1/fishbone/{cause_id}/verify", json={
            "status": "VERIFIED",
            "verification_notes": "Empirically supported by FT-204 logs."
        })

        # Scenario 14: Concurrent promotion attempts using asyncio.gather
        async def do_promote():
            return await ac.post(f"/api/v1/fishbone/{cause_id}/promote", json={
                "is_primary": True,
                "category": "PROCEDURE",
                "investigator_notes": "Promoted from Method evaluation."
            })

        results = await asyncio.gather(do_promote(), do_promote(), do_promote(), return_exceptions=True)
        status_codes = [r.status_code for r in results if not isinstance(r, Exception)]

        # Exactly ONE promotion must succeed with 200, and the rest must be rejected with 409 Conflict
        assert 200 in status_codes, f"One promotion must succeed with 200: {status_codes}"
        assert status_codes.count(200) == 1, f"Expected exactly one 200 OK, got {status_codes}"
        assert status_codes.count(409) == 2, f"Expected exactly two 409 Conflicts, got {status_codes}"

        # Scenario 13: Additional repeated promotion attempt returns HTTP 409
        subsequent_promote = await ac.post(f"/api/v1/fishbone/{cause_id}/promote", json={
            "is_primary": True,
            "category": "PROCEDURE"
        })
        assert subsequent_promote.status_code == 409
        assert "already been promoted" in subsequent_promote.json()["detail"]

        # Scenario 15: Promoted evidence links remain present after persistence and retrieval
        rc_list = (await ac.get(f"/api/v1/investigations/{inv}/root-causes")).json()
        assert len(rc_list) == 1, "There must be exactly one promoted root cause"
        rc_promoted = rc_list[0]
        assert rc_promoted["source_type"] == "FISHBONE"
        assert rc_promoted["source_id"] == cause_id
        assert len(rc_promoted["evidence_links"]) == 1, "Evidence link must be preserved"
        assert rc_promoted["evidence_links"][0]["evidence_id"] == ev_id
        assert rc_promoted["evidence_links"][0]["relationship_type"] == "SUPPORTING"

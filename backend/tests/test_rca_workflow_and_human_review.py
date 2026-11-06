import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core import database
from app.core.database import init_db
from app.core.security import create_access_token

def get_auth_client(transport, user_id=1, username="lead_investigator", role="INVESTIGATOR"):
    token = create_access_token({"sub": username, "role": role, "user_id": user_id})
    return AsyncClient(transport=transport, base_url="http://test", headers={"Authorization": f"Bearer {token}"})

def get_qa_client(transport, user_id=2, username="qa_director"):
    return get_auth_client(transport, user_id=user_id, username=username, role="QA_APPROVER")

@pytest.mark.asyncio
async def test_dynamic_five_whys_depth_beyond_five():
    """Verify 5-Whys causal chaining supports dynamic depth (> 5 levels) without artificial schema constraint."""
    await init_db()
    transport = ASGITransport(app=app)
    async with get_auth_client(transport) as ac:
        inv_res = await ac.post("/api/v1/investigations/", json={
            "title": "Dynamic 5-Whys Depth Investigation",
            "lead_investigator": "Dr. Sarah Lin (QA Lead)"
        })
        assert inv_res.status_code == 200
        inv_id = inv_res.json()["id"]

        # Add steps 1 through 7
        for i in range(1, 8):
            step_res = await ac.post(f"/api/v1/investigations/{inv_id}/five-whys", json={
                "step_number": i,
                "question": f"Why step #{i} occurred?",
                "answer": f"Empirical explanation for causal tier {i}",
                "evidence_reference": f"Logbook entry #{i}"
            })
            assert step_res.status_code == 200, f"Step #{i} failed with: {step_res.text}"
            data = step_res.json()
            assert data["step_number"] == i

        # Query all steps
        list_res = await ac.get(f"/api/v1/investigations/{inv_id}/five-whys")
        assert list_res.status_code == 200
        steps = list_res.json()
        assert len(steps) == 7
        assert steps[5]["step_number"] == 6
        assert steps[6]["step_number"] == 7

@pytest.mark.asyncio
async def test_five_whys_evidence_linking_and_verification_barrier():
    """Verify that a 5-Whys step cannot be marked VERIFIED without at least one verified piece of supporting evidence."""
    await init_db()
    transport = ASGITransport(app=app)
    async with get_auth_client(transport) as ac:
        inv_res = await ac.post("/api/v1/investigations/", json={
            "title": "5-Whys Evidence Barrier Test",
            "lead_investigator": "Dr. Sarah Lin (QA Lead)"
        })
        inv_id = inv_res.json()["id"]

        # Add Why step
        step_res = await ac.post(f"/api/v1/investigations/{inv_id}/five-whys", json={
            "step_number": 1,
            "question": "Why did jacket temperature drop?",
            "answer": "Steam regulator valve stuck at 15% open.",
        })
        step_id = step_res.json()["id"]

        # Barrier 1: Cannot verify without any evidence
        verify_fail = await ac.post(f"/api/v1/five-whys/{step_id}/verify", json={
            "is_verified": True,
            "verification_notes": "Attempting verification without evidence."
        })
        assert verify_fail.status_code == 400
        assert "Verification safety violation" in verify_fail.json()["detail"]

        # Upload evidence
        ev_res = await ac.post(
            f"/api/v1/investigations/{inv_id}/evidences/upload",
            data={"title": "Valve Inspection Report", "evidence_type": "LOGBOOK"},
            files={"file": ("valve_inspection.txt", b"Regulator valve V-102 stuck mechanical inspection.", "text/plain")}
        )
        assert ev_res.status_code == 200
        ev_id = ev_res.json()["id"]

        # Link unverified evidence as SUPPORTING
        link_res = await ac.post(f"/api/v1/five-whys/{step_id}/evidence", json={
            "evidence_id": ev_id,
            "relationship_type": "SUPPORTING",
            "relevance_explanation": "Direct physical inspection of valve V-102."
        })
        assert link_res.status_code == 200
        assert link_res.json()["relationship_type"] == "SUPPORTING"

        # Barrier 2: Cannot verify with unverified evidence
        verify_fail_2 = await ac.post(f"/api/v1/five-whys/{step_id}/verify", json={
            "is_verified": True,
            "verification_notes": "Attempting verification with unverified evidence."
        })
        assert verify_fail_2.status_code == 400
        assert "Verification safety violation" in verify_fail_2.json()["detail"]

        # Barrier 3: Uploader cannot verify their own evidence (Separation of Duties)
        self_verify = await ac.post(f"/api/v1/evidences/{ev_id}/verify", json={
            "investigator_name": "Dr. Sarah Lin",
            "verification_notes": "Attempting self-verification."
        })
        assert self_verify.status_code == 403
        assert "Separation of duties violation" in self_verify.json()["detail"]

        # Independent QA reviewer formally verifies the evidence record
        async with get_qa_client(transport) as qa_ac:
            ev_verify = await qa_ac.post(f"/api/v1/evidences/{ev_id}/verify", json={
                "investigator_name": "Dr. Elena Rostova",
                "verification_notes": "Verified against maintenance sign-off."
            })
            assert ev_verify.status_code == 200
            assert ev_verify.json()["is_verified"] is True
            assert ev_verify.json()["verified_by_user_id"] is not None

        # Now verification succeeds!
        verify_ok = await ac.post(f"/api/v1/five-whys/{step_id}/verify", json={
            "is_verified": True,
            "verification_notes": "Confirmed by physical maintenance teardown report."
        })
        assert verify_ok.status_code == 200
        step_data = verify_ok.json()
        assert step_data["is_verified"] is True
        assert step_data["verified_by_user_id"] is not None
        assert step_data["verified_at"] is not None

        # Link contradictory evidence
        ev_contra = await ac.post(
            f"/api/v1/investigations/{inv_id}/evidences/upload",
            data={"title": "SCADA Valve Position Telemetry", "evidence_type": "SCADA_TREND"},
            files={"file": ("scada_valve.txt", b"Valve position sensor reported 100% open at 04:00.", "text/plain")}
        )
        contra_id = ev_contra.json()["id"]

        contra_link = await ac.post(f"/api/v1/five-whys/{step_id}/evidence", json={
            "evidence_id": contra_id,
            "relationship_type": "CONTRADICTORY",
            "relevance_explanation": "Sensor indicates open while valve was physically closed."
        })
        assert contra_link.status_code == 200
        assert contra_link.json()["relationship_type"] == "CONTRADICTORY"

        # Step reflects both links
        steps_res = await ac.get(f"/api/v1/investigations/{inv_id}/five-whys")
        step_checked = steps_res.json()[0]
        assert len(step_checked["evidence_links"]) == 2

@pytest.mark.asyncio
async def test_fishbone_causes_evaluation_and_promotion_to_root_cause():
    """Verify Fishbone cause creation, evidence-linked verification barrier, and promotion to Root Cause proposal."""
    await init_db()
    transport = ASGITransport(app=app)
    async with get_auth_client(transport) as ac:
        inv_res = await ac.post("/api/v1/investigations/", json={
            "title": "Fishbone Promotion Test",
            "lead_investigator": "Dr. Sarah Lin (QA Lead)"
        })
        inv_id = inv_res.json()["id"]

        # Add Fishbone cause
        cause_res = await ac.post(f"/api/v1/investigations/{inv_id}/fishbone", json={
            "category": "MACHINE",
            "cause_description": "Mechanical seal carbon face scored allowing coolant ingress",
            "status": "HYPOTHESIS",
            "rationale": "Microscopic analysis revealed groove wear on primary seal face."
        })
        assert cause_res.status_code == 200
        cause = cause_res.json()
        assert cause["category"] == "MACHINE"
        assert cause["status"] == "HYPOTHESIS"
        cause_id = cause["id"]

        # Upload and verify supporting evidence
        ev_res = await ac.post(
            f"/api/v1/investigations/{inv_id}/evidences/upload",
            data={"title": "Seal Teardown Report", "evidence_type": "LOGBOOK"},
            files={"file": ("seal_report.txt", b"Seal teardown: 0.3mm radial groove on face A.", "text/plain")}
        )
        ev_id = ev_res.json()["id"]
        async with get_qa_client(transport) as qa_ac:
            await qa_ac.post(f"/api/v1/evidences/{ev_id}/verify", json={
                "investigator_name": "Dr. Elena Rostova",
                "verification_notes": "Metallurgical lab sign-off."
            })

        # Link evidence to fishbone cause
        fb_link = await ac.post(f"/api/v1/fishbone/{cause_id}/evidence", json={
            "evidence_id": ev_id,
            "relationship_type": "SUPPORTING",
            "relevance_explanation": "Radial groove measurements."
        })
        assert fb_link.status_code == 200

        # Mark cause VERIFIED
        cause_verify = await ac.post(f"/api/v1/fishbone/{cause_id}/verify", json={
            "status": "VERIFIED",
            "verification_notes": "Verified by metallurgical report."
        })
        assert cause_verify.status_code == 200
        assert cause_verify.json()["status"] == "VERIFIED"

        # Promote Fishbone cause to Root Cause proposal
        promote_res = await ac.post(f"/api/v1/fishbone/{cause_id}/promote", json={
            "is_primary": True,
            "category": "EQUIPMENT_FAILURE",
            "investigator_notes": "Promoted from Fishbone Machine evaluation."
        })
        assert promote_res.status_code == 200
        rc = promote_res.json()
        assert rc["cause_statement"] == "Mechanical seal carbon face scored allowing coolant ingress"
        assert rc["category"] == "EQUIPMENT_FAILURE"
        assert rc["is_primary"] is True
        assert rc["status"] == "PROPOSED"  # Crucial safety rule: always PROPOSED
        assert rc["source_type"] == "FISHBONE"
        assert rc["source_id"] == cause_id
        # Evidence link copied to root cause
        assert len(rc["evidence_links"]) == 1
        assert rc["evidence_links"][0]["evidence_id"] == ev_id

        # Repeated promotion must return HTTP 409 Conflict
        dup_promote = await ac.post(f"/api/v1/fishbone/{cause_id}/promote", json={
            "is_primary": True,
            "category": "EQUIPMENT_FAILURE",
        })
        assert dup_promote.status_code == 409
        assert "already been promoted" in dup_promote.json()["detail"]

@pytest.mark.asyncio
async def test_cross_investigation_evidence_isolation_boundaries():
    """Verify strict cross-investigation isolation when linking evidence to Whys, Fishbone, or Root Causes."""
    await init_db()
    transport = ASGITransport(app=app)
    async with get_auth_client(transport) as ac:
        # Create Investigation A
        inv_a = (await ac.post("/api/v1/investigations/", json={"title": "Inv A", "lead_investigator": "Dr. Lin"})).json()["id"]
        # Create Investigation B
        inv_b = (await ac.post("/api/v1/investigations/", json={"title": "Inv B", "lead_investigator": "Dr. Lin"})).json()["id"]

        # Upload evidence in Inv A
        ev_a = (await ac.post(
            f"/api/v1/investigations/{inv_a}/evidences/upload",
            data={"title": "Evidence A"},
            files={"file": ("ev_a.txt", b"Batch A sensor trace data.", "text/plain")}
        )).json()["id"]

        # Create 5-Whys step in Inv B
        why_b = (await ac.post(f"/api/v1/investigations/{inv_b}/five-whys", json={
            "step_number": 1, "question": "Why in B?", "answer": "Answer in B"
        })).json()["id"]

        # Create Fishbone cause in Inv B
        fish_b = (await ac.post(f"/api/v1/investigations/{inv_b}/fishbone", json={
            "category": "MACHINE", "cause_description": "Cause in B"
        })).json()["id"]

        # Create Root Cause in Inv B
        rc_b = (await ac.post(f"/api/v1/investigations/{inv_b}/root-causes", json={
            "cause_statement": "Root cause in B", "is_primary": True
        })).json()["id"]

        # Attempt cross-linking Evidence A to Why B -> HTTP 400
        cross_why = await ac.post(f"/api/v1/five-whys/{why_b}/evidence", json={
            "evidence_id": ev_a, "relationship_type": "SUPPORTING"
        })
        assert cross_why.status_code == 400
        assert "Forbidden" in cross_why.json()["detail"]

        # Attempt cross-linking Evidence A to Fishbone B -> HTTP 400
        cross_fish = await ac.post(f"/api/v1/fishbone/{fish_b}/evidence", json={
            "evidence_id": ev_a, "relationship_type": "SUPPORTING"
        })
        assert cross_fish.status_code == 400
        assert "Forbidden" in cross_fish.json()["detail"]

        # Attempt cross-linking Evidence A to Root Cause B -> HTTP 400
        cross_rc = await ac.post(f"/api/v1/root-causes/{rc_b}/evidence-links", json={
            "evidence_id": ev_a, "relationship_type": "SUPPORTING"
        })
        assert cross_rc.status_code == 400
        assert "Forbidden" in cross_rc.json()["detail"]

@pytest.mark.asyncio
async def test_root_cause_confirmation_barrier_and_provenance():
    """Verify that root cause confirmation strictly enforces evidence verification, contradiction disposition, and saves auditor ID."""
    await init_db()
    transport = ASGITransport(app=app)
    async with get_auth_client(transport) as ac:
        inv_res = await ac.post("/api/v1/investigations/", json={
            "title": "Root Cause Confirmation Safety Test",
            "lead_investigator": "Dr. Sarah Lin (QA Lead)"
        })
        inv_id = inv_res.json()["id"]

        # Create root cause proposal
        rc_res = await ac.post(f"/api/v1/investigations/{inv_id}/root-causes", json={
            "cause_statement": "Impeller shaft mechanical fatigue failure.",
            "category": "EQUIPMENT_FAILURE",
            "is_primary": True,
            "rationale": "High cyclic stress caused crack propagation."
        })
        assert rc_res.status_code == 200
        rc = rc_res.json()
        assert rc["status"] == "PROPOSED"
        rc_id = rc["id"]

        # Try to confirm without evidence as QA -> returns HTTP 400
        async with get_qa_client(transport) as qa_ac:
            fail_confirm = await qa_ac.post(f"/api/v1/root-causes/{rc_id}/confirm", json={
                "investigator_name": "Dr. Elena Rostova",
                "justification": "I visually inspected the shaft and confirmed the failure."
            })
            assert fail_confirm.status_code == 400
            assert "Regulatory safety violation" in fail_confirm.json()["detail"]

        # Lead investigator cannot confirm root cause -> returns HTTP 403
        fail_investigator = await ac.post(f"/api/v1/root-causes/{rc_id}/confirm", json={
            "investigator_name": "Dr. Sarah Lin",
            "justification": "Investigator attempting direct confirmation."
        })
        assert fail_investigator.status_code == 403

        # Upload and verify supporting evidence
        ev_supp = (await ac.post(
            f"/api/v1/investigations/{inv_id}/evidences/upload",
            data={"title": "Metallurgical Fatigue Analysis"},
            files={"file": ("fatigue.txt", b"Fracture surface exhibits beach marks indicative of fatigue.", "text/plain")}
        )).json()["id"]

        # Uploader cannot verify their own evidence -> returns HTTP 403
        self_ver = await ac.post(f"/api/v1/evidences/{ev_supp}/verify", json={
            "investigator_name": "Dr. Sarah Lin",
            "verification_notes": "Attempting self-verify"
        })
        assert self_ver.status_code == 403

        # QA Approver verifies supporting evidence
        async with get_qa_client(transport) as qa_ac:
            ver_ok = await qa_ac.post(f"/api/v1/evidences/{ev_supp}/verify", json={
                "investigator_name": "Dr. Elena Rostova",
                "verification_notes": "Metallurgy lab report verified."
            })
            assert ver_ok.status_code == 200

        # Link supporting evidence
        await ac.post(f"/api/v1/root-causes/{rc_id}/evidence-links", json={
            "evidence_id": ev_supp,
            "relationship_type": "SUPPORTING",
            "relevance_explanation": "Fatigue striation micrographs."
        })

        # Link contradictory evidence
        ev_contra = (await ac.post(
            f"/api/v1/investigations/{inv_id}/evidences/upload",
            data={"title": "Vibration Sensor Telemetry"},
            files={"file": ("vibration.txt", b"Vibration telemetry within baseline limits.", "text/plain")}
        )).json()["id"]
        contra_link = (await ac.post(f"/api/v1/root-causes/{rc_id}/evidence-links", json={
            "evidence_id": ev_contra,
            "relationship_type": "CONTRADICTORY",
            "relevance_explanation": "Telemetry did not spike before failure."
        })).json()
        contra_link_id = contra_link["id"]

        # Try to confirm with active contradiction as QA -> returns HTTP 400
        async with get_qa_client(transport) as qa_ac:
            fail_contra = await qa_ac.post(f"/api/v1/root-causes/{rc_id}/confirm", json={
                "investigator_name": "Dr. Elena Rostova",
                "justification": "We have supporting evidence now so we want to confirm."
            })
            assert fail_contra.status_code == 400
            assert "active contradictory evidence link(s)" in fail_contra.json()["detail"]

        # Formally dispose of contradiction with mandatory rationale (>=10 chars)
        disp_res = await ac.post(
            f"/api/v1/root-causes/{rc_id}/evidence-links/{contra_link_id}/dismiss",
            json={"disposition_rationale": "Sensor sampling rate was 1 hour, which aliased high-frequency transient spike prior to catastrophic shearing."}
        )
        assert disp_res.status_code == 200

        # Lead investigator still cannot confirm -> returns HTTP 403
        fail_still_inv = await ac.post(f"/api/v1/root-causes/{rc_id}/confirm", json={
            "investigator_name": "Dr. Sarah Lin",
            "justification": "Trying to confirm now that contradiction is resolved."
        })
        assert fail_still_inv.status_code == 403

        # QA Approver confirms successfully!
        async with get_qa_client(transport) as qa_ac:
            confirm_ok = await qa_ac.post(f"/api/v1/root-causes/{rc_id}/confirm", json={
                "investigator_name": "Dr. Elena Rostova",
                "justification": "Fatigue striations verified by SEM imaging. Sensor aliasing explains telemetry baseline."
            })
            assert confirm_ok.status_code == 200
            rc_final = confirm_ok.json()
            assert rc_final["status"] == "CONFIRMED"
            assert rc_final["is_verified"] is True
            assert rc_final["is_ai_suggested"] is False
            assert "Elena Rostova" in rc_final["confirmed_by"]
            assert rc_final["confirmed_by_user_id"] is not None
            assert rc_final["confirmed_at"] is not None

@pytest.mark.asyncio
async def test_itemized_rca_apply_endpoint():
    """Verify granular /copilot/apply-rca-item endpoint accepts individual items without bulk overwrite."""
    await init_db()
    transport = ASGITransport(app=app)
    async with get_auth_client(transport) as ac:
        inv_res = await ac.post("/api/v1/investigations/", json={
            "title": "Itemized Apply Test",
            "lead_investigator": "Dr. Sarah Lin (QA Lead)"
        })
        inv_id = inv_res.json()["id"]

        # 1. Apply single Why step
        why_item = await ac.post("/api/v1/copilot/apply-rca-item", json={
            "investigation_id": inv_id,
            "item_type": "FIVE_WHYS",
            "item_data": {
                "step_number": 1,
                "question": "Why did filter clog?",
                "answer": "Particulate precipitate accumulated.",
                "evidence_reference": "Differential pressure trend"
            }
        })
        assert why_item.status_code == 200
        assert why_item.json()["item_type"] == "FIVE_WHYS"

        # 2. Apply single Fishbone cause
        fish_item = await ac.post("/api/v1/copilot/apply-rca-item", json={
            "investigation_id": inv_id,
            "item_type": "FISHBONE",
            "item_data": {
                "category": "MATERIAL",
                "cause_description": "Impurity in raw material Lot RM-402",
                "rationale": "High viscosity detected in incoming solvent."
            }
        })
        assert fish_item.status_code == 200
        assert fish_item.json()["item_type"] == "FISHBONE"

        # 3. Apply single Root Cause
        rc_item = await ac.post("/api/v1/copilot/apply-rca-item", json={
            "investigation_id": inv_id,
            "item_type": "ROOT_CAUSE",
            "item_data": {
                "cause_statement": "Vendor formulation change introduced insoluble wax additive.",
                "category": "RAW_MATERIAL",
                "is_primary": True,
                "rationale": "Vendor notification confirmed excipient switch."
            }
        })
        assert rc_item.status_code == 200
        assert rc_item.json()["item_type"] == "ROOT_CAUSE"

        # Verify investigation now contains all three curated items
        inv_check = (await ac.get(f"/api/v1/investigations/{inv_id}")).json()
        assert len(inv_check["five_whys"]) == 1
        assert len(inv_check["fishbone_causes"]) == 1
        assert len(inv_check["root_causes"]) == 1
        assert inv_check["root_causes"][0]["status"] == "PROPOSED"

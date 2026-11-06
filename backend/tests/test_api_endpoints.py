import pytest
import pytest_asyncio
from unittest.mock import patch
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import init_db
from app.core.security import create_access_token
from app.services.groq_service import groq_service

@pytest.mark.asyncio
async def test_api_health():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

@pytest.mark.asyncio
async def test_investigation_lifecycle():
    await init_db()
    transport = ASGITransport(app=app)

    # Tokens for Investigator and QA Director
    inv_token = create_access_token({"sub": "lead_investigator", "role": "INVESTIGATOR", "user_id": 1})
    qa_token = create_access_token({"sub": "qa_director", "role": "QA_APPROVER", "user_id": 2})
    inv_headers = {"Authorization": f"Bearer {inv_token}"}
    qa_headers = {"Authorization": f"Bearer {qa_token}"}

    mock_intake = groq_service._fallback_intake_extraction(
        "Deviation in Batch B2026-API-044 of Atorvastatin in RX-301. Temperature spike to 38.4C during Crystallization.",
        source_type="TEXT"
    )
    mock_intake["deviation"]["product_name"] = "Atorvastatin Calcium API"
    mock_intake["deviation"]["batch_number"] = "B2026-API-044"

    mock_rca = {
        "status": "SUCCESS",
        "five_whys": [
            {"step_number": 1, "question": "Why did temp spike to 38.4C?", "answer": "Valve position feedback diverged by 88%", "is_ai_suggested": True, "is_verified": False},
            {"step_number": 2, "question": "Why did position feedback diverge?", "answer": "Mechanical actuator linkage bound", "is_ai_suggested": True, "is_verified": False}
        ],
        "fishbone_causes": [
            {"category": "MACHINE", "cause_description": "Cooling valve positioner malfunction", "status": "HYPOTHESIS", "is_ai_suggested": True, "is_verified": False}
        ],
        "root_causes": [
            {"cause_statement": "Mechanical binding of cooling valve actuator", "category": "EQUIPMENT_FAILURE", "is_primary": True, "status": "PROPOSED", "is_ai_suggested": True, "is_verified": False}
        ],
        "capa_actions": [
            {"action_type": "CORRECTION", "description": "Isolate and overhaul valve actuator", "is_ai_suggested": True, "is_verified": False, "rationale": "Direct containment", "effectiveness_criteria": "Valve stroke hysteresis test passes"}
        ]
    }

    with patch.object(groq_service, "is_available", return_value=True), \
         patch.object(groq_service, "extract_intake_data", return_value=mock_intake), \
         patch.object(groq_service, "generate_rca_analysis", return_value=mock_rca):
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            # 1. Create Investigation
            create_res = await ac.post("/api/v1/investigations/", headers=inv_headers, json={
                "title": "API Crystallization Excursion Investigation",
                "lead_investigator": "Dr. Sarah Lin (QA Lead)"
            })
            assert create_res.status_code == 200, create_res.text
            inv = create_res.json()
            inv_id = inv["id"]
            assert inv["investigation_number"].startswith("INV-2026-")

            # 2. Intake: Parse incident text
            intake_res = await ac.post("/api/v1/intake/parse-text", headers=inv_headers, json={
                "content": "Deviation in Batch B2026-API-044 of Atorvastatin in RX-301. Temperature spike to 38.4C during Crystallization.",
                "is_email": False
            })
            assert intake_res.status_code == 200, intake_res.text
            extracted = intake_res.json()
            assert "deviation" in extracted

            # 3. Apply extracted data to investigation form
            apply_res = await ac.post("/api/v1/intake/apply-to-investigation", headers=inv_headers, json={
                "investigation_id": inv_id,
                "apply_deviation": True,
                "custom_overrides": {
                    "deviation": extracted["deviation"],
                    "extracted_findings": extracted["extracted_findings"]
                }
            })
            assert apply_res.status_code == 200, apply_res.text
            updated_inv = apply_res.json()
            assert updated_inv["deviation"]["batch_number"] == "B2026-API-044"
            assert updated_inv["deviation"]["is_ai_populated"] is True
            assert updated_inv["deviation"]["is_verified"] is False  # AI suggested, not yet approved

            # 4. Generate RCA & CAPA
            rca_res = await ac.post("/api/v1/copilot/generate-rca", headers=inv_headers, json={
                "investigation_id": inv_id,
                "user_context": "Valve position feedback diverged from demand by 88%."
            })
            assert rca_res.status_code == 200, rca_res.text
            rca_data = rca_res.json()
            assert len(rca_data["five_whys"]) >= 1
            assert len(rca_data["fishbone_causes"]) >= 1

            # 5. Apply RCA & CAPA to investigation
            apply_rca_res = await ac.post("/api/v1/copilot/apply-rca-to-investigation", headers=inv_headers, json={
                "investigation_id": inv_id,
                "rca_data": rca_data
            })
            assert apply_rca_res.status_code == 200, apply_rca_res.text
            inv_with_rca = apply_rca_res.json()
            assert len(inv_with_rca["five_whys"]) >= 1
            assert len(inv_with_rca["fishbone_causes"]) >= 1
            assert len(inv_with_rca["capa_actions"]) >= 1

            # 6. Verify human approval by QA Director
            approve_res = await ac.post(
                f"/api/v1/investigations/{inv_id}/approve",
                headers=qa_headers,
                json={"comments": "All CAPAs reviewed and assigned."}
            )
            assert approve_res.status_code == 200, approve_res.text
            approved_inv = approve_res.json()
            assert approved_inv["is_approved"] is True
            assert approved_inv["status"] in ("APPROVED", "CLOSED")
            assert "Dr. Elena Rostova" in approved_inv["qa_approver"]

            # 7. Audit trail check
            audit_res = await ac.get(f"/api/v1/investigations/{inv_id}/audit-logs", headers=inv_headers)
            assert audit_res.status_code == 200
            audit_logs = audit_res.json()
            assert len(audit_logs) >= 3

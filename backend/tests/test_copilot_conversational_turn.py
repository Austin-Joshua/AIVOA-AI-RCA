import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import init_db
from app.core.security import create_access_token
from app.services.groq_service import groq_service
from app.schemas.copilot import FieldPatchStatus

def test_classify_conversation_turn_router():
    """Verify router classifies user messages accurately across the 4 LangGraph categories."""
    # 1. Attachment forces NEW_SOURCE
    assert groq_service.classify_conversation_turn("hello", has_attachment=True) == "NEW_SOURCE"

    # 2. Email header or long pharma incident text -> NEW_SOURCE
    sample_email = (
        "Subject: Urgent Deviation Notification - Crystallization Reactor CR-104\n"
        "From: ops.supervisor@pharma.corp\n"
        "Batch API-2026-104 experienced temperature excursion during crystallization."
    )
    assert groq_service.classify_conversation_turn(sample_email) == "NEW_SOURCE"

    # 3. Conversational corrections -> CORRECTION
    assert groq_service.classify_conversation_turn("sorry, batch is API-2026-104") == "CORRECTION"
    assert groq_service.classify_conversation_turn("actually the equipment is CR-104") == "CORRECTION"
    assert groq_service.classify_conversation_turn("peak temp was 86C") == "CORRECTION"

    # 4. Analysis requests -> ANALYSIS_REQUEST
    assert groq_service.classify_conversation_turn("Can you run 5 whys analysis?") == "ANALYSIS_REQUEST"
    assert groq_service.classify_conversation_turn("Generate 6M fishbone diagram") == "ANALYSIS_REQUEST"

    # 5. General inquiries -> QUESTION
    assert groq_service.classify_conversation_turn("What does ICH Q9 say about risk scoring?") == "QUESTION"

def test_extract_corrections_patch_regex_fallback():
    """Verify rule-based fallback extracts canonical deviation keys from user statements."""
    patches = groq_service.extract_corrections_patch("sorry, the batch is API-2026-104")
    assert any(p["field_key"] == "batch_number" and p["new_value"] == "API-2026-104" for p in patches)

    eq_patches = groq_service.extract_corrections_patch("actually reactor is CR-104")
    assert any(p["field_key"] == "equipment_id" and p["new_value"] == "CR-104" for p in eq_patches)

@pytest.mark.asyncio
async def test_copilot_converse_flow_and_access_control():
    """Verify POST /copilot/converse handles conversational turns and enforces access control."""
    from unittest.mock import patch
    await init_db()
    transport = ASGITransport(app=app)

    inv_token = create_access_token({"sub": "lead_investigator", "role": "INVESTIGATOR", "user_id": 1})
    other_token = create_access_token({"sub": "other_user", "role": "INVESTIGATOR", "user_id": 999})
    auth_headers = {"Authorization": f"Bearer {inv_token}"}
    other_headers = {"Authorization": f"Bearer {other_token}"}

    mock_intake = {
        "deviation": {
            "batch_number": "API-2026-104",
            "product_name": "Paracetamol API",
            "unit_operation": "Crystallization",
            "equipment_id": "CR-104",
            "severity": "Major",
            "description": "Temperature exceeded 75-80C limit reaching 86C.",
            "immediate_containment": "Quarantine mother liquor tank."
        },
        "extracted_fields": [
            {
                "field_name": "batch_number",
                "label": "Batch Number",
                "value": "API-2026-104",
                "status": "SOURCE_FACT",
                "source_reference": "Batch API-2026-104",
                "confidence": 1.0
            },
            {
                "field_name": "equipment_id",
                "label": "Equipment ID",
                "value": "CR-104",
                "status": "SOURCE_FACT",
                "source_reference": "Crystallizer CR-104",
                "confidence": 1.0
            }
        ],
        "missing_information": [
            {
                "category": "CALIBRATION",
                "question": "Is CV-104 calibration log available?",
                "impact_description": "Verify valve positioner accuracy",
                "urgency": "HIGH"
            }
        ]
    }

    mock_corrections = [
        {"field_key": "batch_number", "new_value": "API-2026-104", "reason": "User conversational correction"}
    ]

    with patch.object(groq_service, "extract_intake_data", return_value=mock_intake), \
         patch.object(groq_service, "extract_corrections_patch", return_value=mock_corrections):
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            # Create an investigation
            create_res = await ac.post(
                "/api/v1/investigations/",
                json={"title": "Paracetamol Excursion Test", "stage": "INTAKE", "status": "IN_INVESTIGATION"},
                headers=auth_headers
            )
            assert create_res.status_code == 200
            inv_id = create_res.json()["id"]

            # 1. Post a new source text
            report_text = (
                "INCIDENT NOTIFICATION: Temperature excursion in Crystallizer CR-104 during Batch API-2026-104. "
                "Product Paracetamol API reached 86C exceeding 75-80C limit for 18 minutes. "
                "Immediate containment: Quarantined batch in mother liquor tank."
            )
            res = await ac.post(
                "/api/v1/copilot/converse",
                json={"investigation_id": inv_id, "message": report_text},
                headers=auth_headers
            )
            assert res.status_code == 200, res.text
            data = res.json()
            assert data["classification"] in ("NEW_SOURCE", "QUESTION")
            assert "reply_text" in data
            assert isinstance(data["field_patches"], list)
            if data["classification"] == "NEW_SOURCE":
                assert data["risk_assessment"] is not None

            # 2. Post a correction
            corr_res = await ac.post(
                "/api/v1/copilot/converse",
                json={
                    "investigation_id": inv_id,
                    "message": "actually the batch is API-2026-104",
                    "current_draft_fields": {"batch_number": "OLD-999"}
                },
                headers=auth_headers
            )
            assert corr_res.status_code == 200
            corr_data = corr_res.json()
            assert corr_data["classification"] == "CORRECTION"
            assert any(p["field_key"] == "batch_number" and "API-2026-104" in p["value"] for p in corr_data["field_patches"])

            # 3. Retrieve conversation history
            history_res = await ac.get(
                f"/api/v1/copilot/investigations/{inv_id}/messages",
                headers=auth_headers
            )
            assert history_res.status_code == 200
            msgs = history_res.json()
            assert len(msgs) >= 4  # 2 user turns + 2 assistant replies

            # 4. Unauthorized user access control test
            unauth_converse = await ac.post(
                "/api/v1/copilot/converse",
                json={"investigation_id": inv_id, "message": "hello"},
                headers=other_headers
            )
            assert unauth_converse.status_code in (401, 403, 404)

            unauth_msgs = await ac.get(
                f"/api/v1/copilot/investigations/{inv_id}/messages",
                headers=other_headers
            )
            assert unauth_msgs.status_code in (401, 403, 404)


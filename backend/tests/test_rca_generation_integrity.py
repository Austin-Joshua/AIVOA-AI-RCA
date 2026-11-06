import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import HTTPException
from pydantic import ValidationError

from app.services.groq_service import (
    GroqService,
    GroqServiceError,
    GroqRateLimitError,
    GroqAuthenticationError,
    GroqTimeoutError,
    GroqConnectionError,
    sanitize_secret,
    groq_service
)
from app.schemas.five_whys import FiveWhysStepCreate, FiveWhysStepUpdate
from app.schemas.fishbone import FishboneCauseCreate, FishboneCauseUpdate
from app.schemas.root_cause import RootCauseCreate
from app.schemas.capa import CapaActionCreate
from app.api.endpoints.copilot import generate_rca_analysis, copilot_chat
from app.api.endpoints.five_whys import add_five_why_step, update_five_why_step, delete_five_why_step
from app.api.endpoints.fishbone import add_fishbone_cause, update_fishbone_cause, delete_fishbone_cause
from app.schemas.copilot import GenerateRcaRequest, CopilotChatRequest
from app.models.audit import User
from app.models.investigation import Investigation
from app.models.deviation import Deviation
from app.models.five_whys import FiveWhysStep
from app.models.fishbone import FishboneCause

SYNTHETIC_CONSTANTS = [
    "38.4",
    "22.0",
    "MW-2026-1049",
    "SOP-MAINT-102",
    "CAL-2026-04",
    "RM-2026-088"
]

@pytest.fixture
def mock_user():
    return User(id=1, email="lead_inv@pharma.com", full_name="Dr. Alex Rivera", role="LEAD_INVESTIGATOR")

@pytest.fixture
def mock_investigation():
    inv = Investigation(id=101, investigation_number="INV-2026-001", title="Batch 044 Crystallization Excursion", stage="TRIAGE", status="OPEN", lead_investigator_id=1)
    inv.deviation = Deviation(
        id=201,
        deviation_number="DEV-2026-084",
        batch_number="B2026-API-044",
        product_name="Atorvastatin Calcium API",
        unit_operation="Crystallization",
        equipment_id="RX-301",
        severity="Major",
        description="Agitator speed dropped below lower limit during crystallization stage.",
        immediate_containment="Quarantined batch B2026-API-044."
    )
    inv.five_whys = []
    inv.fishbone_causes = []
    inv.root_causes = []
    inv.capa_actions = []
    inv.evidences = []
    return inv

# ----------------- TEST 1: Groq 429 returns quota-blocked result, no generated RCA findings -----------------
@pytest.mark.asyncio
async def test_groq_rate_limit_error_429(mock_user, mock_investigation):
    """Test 1: Groq 429 raises HTTP 429 at endpoint and returns QUOTA_BLOCKED with zero findings."""
    db = AsyncMock()
    req = GenerateRcaRequest(investigation_id=101)
    with patch("app.api.endpoints.copilot.verify_investigation_access", return_value=True), \
         patch("app.api.endpoints.copilot.get_investigation_by_id", return_value=mock_investigation), \
         patch("app.api.endpoints.copilot.groq_service.generate_rca_analysis", side_effect=GroqRateLimitError("Rate limit exceeded")):
        with pytest.raises(HTTPException) as exc_info:
            await generate_rca_analysis(req=req, current_user=mock_user, db=db)
        assert exc_info.value.status_code == 429
        assert "rate limit or quota exceeded" in exc_info.value.detail.lower()

    # Direct service call with fallback must return explicit QUOTA_BLOCKED with zero findings
    service = GroqService()
    with patch.object(service, "is_available", return_value=True), \
         patch.object(service, "_call_groq_json", side_effect=GroqRateLimitError("TPD limit exceeded")):
        res = service.generate_rca_analysis({"batch_number": "B001", "description": "Temp spike"}, allow_offline_fallback=True)
        assert res["status"] in ["QUOTA_BLOCKED", "RATE_LIMIT_EXCEEDED"]
        assert res["five_whys"] == []
        assert res["fishbone_causes"] == []
        assert res["root_causes"] == []
        assert res["capa_actions"] == []
        assert "unavailable" in res["investigator_guidance"].lower()

# ----------------- TEST 2: Groq 401 returns authentication error, no generated RCA findings -----------------
@pytest.mark.asyncio
async def test_groq_auth_error_401(mock_user, mock_investigation):
    """Test 2: Groq 401 raises HTTP 401 at endpoint and returns AUTH_ERROR with zero findings."""
    db = AsyncMock()
    req = GenerateRcaRequest(investigation_id=101)
    with patch("app.api.endpoints.copilot.verify_investigation_access", return_value=True), \
         patch("app.api.endpoints.copilot.get_investigation_by_id", return_value=mock_investigation), \
         patch("app.api.endpoints.copilot.groq_service.generate_rca_analysis", side_effect=GroqAuthenticationError("Invalid API key")):
        with pytest.raises(HTTPException) as exc_info:
            await generate_rca_analysis(req=req, current_user=mock_user, db=db)
        assert exc_info.value.status_code == 401
        assert "authentication failed" in exc_info.value.detail.lower()

    service = GroqService()
    with patch.object(service, "is_available", return_value=True), \
         patch.object(service, "_call_groq_json", side_effect=GroqAuthenticationError("Invalid key")):
        res = service.generate_rca_analysis({"batch_number": "B001", "description": "Excursion"}, allow_offline_fallback=True)
        assert res["status"] in ["AUTH_ERROR", "AI_UNAVAILABLE"]
        assert res["five_whys"] == []
        assert res["fishbone_causes"] == []
        assert res["root_causes"] == []

# ----------------- TEST 3: Groq timeout returns unavailable result, no generated RCA findings -----------------
@pytest.mark.asyncio
async def test_groq_timeout_error_408(mock_user, mock_investigation):
    """Test 3: Groq timeout raises HTTP 408 and returns REQUEST_TIMEOUT with zero findings."""
    db = AsyncMock()
    req = GenerateRcaRequest(investigation_id=101)
    with patch("app.api.endpoints.copilot.verify_investigation_access", return_value=True), \
         patch("app.api.endpoints.copilot.get_investigation_by_id", return_value=mock_investigation), \
         patch("app.api.endpoints.copilot.groq_service.generate_rca_analysis", side_effect=GroqTimeoutError("Request timed out")):
        with pytest.raises(HTTPException) as exc_info:
            await generate_rca_analysis(req=req, current_user=mock_user, db=db)
        assert exc_info.value.status_code == 408
        assert "timed out" in exc_info.value.detail.lower()

    service = GroqService()
    with patch.object(service, "is_available", return_value=True), \
         patch.object(service, "_call_groq_json", side_effect=GroqTimeoutError("Timeout")):
        res = service.generate_rca_analysis({"batch_number": "B001", "description": "Excursion"}, allow_offline_fallback=True)
        assert res["status"] in ["REQUEST_TIMEOUT", "AI_UNAVAILABLE"]
        assert res["five_whys"] == []
        assert res["root_causes"] == []

# ----------------- TEST 4: Groq 5xx returns unavailable result, no generated RCA findings -----------------
@pytest.mark.asyncio
async def test_groq_5xx_unavailable(mock_user, mock_investigation):
    """Test 4: Groq 5xx raises HTTP 503 and returns AI_UNAVAILABLE with zero findings."""
    db = AsyncMock()
    req = GenerateRcaRequest(investigation_id=101)
    with patch("app.api.endpoints.copilot.verify_investigation_access", return_value=True), \
         patch("app.api.endpoints.copilot.get_investigation_by_id", return_value=mock_investigation), \
         patch("app.api.endpoints.copilot.groq_service.generate_rca_analysis", side_effect=GroqServiceError("Groq 500 internal server error")):
        with pytest.raises(HTTPException) as exc_info:
            await generate_rca_analysis(req=req, current_user=mock_user, db=db)
        assert exc_info.value.status_code == 503
        assert "service unavailable" in exc_info.value.detail.lower()

    service = GroqService()
    with patch.object(service, "is_available", return_value=True), \
         patch.object(service, "_call_groq_json", side_effect=GroqServiceError("500 internal")):
        res = service.generate_rca_analysis({"batch_number": "B001", "description": "Excursion"}, allow_offline_fallback=True)
        assert res["status"] == "AI_UNAVAILABLE"
        assert res["five_whys"] == []
        assert res["root_causes"] == []

# ----------------- TEST 5: Network failure returns unavailable result, no generated RCA findings -----------------
@pytest.mark.asyncio
async def test_network_connection_failure(mock_user, mock_investigation):
    """Test 5: Network failure raises HTTP 503 and returns AI_UNAVAILABLE with zero findings."""
    db = AsyncMock()
    req = GenerateRcaRequest(investigation_id=101)
    with patch("app.api.endpoints.copilot.verify_investigation_access", return_value=True), \
         patch("app.api.endpoints.copilot.get_investigation_by_id", return_value=mock_investigation), \
         patch("app.api.endpoints.copilot.groq_service.generate_rca_analysis", side_effect=GroqConnectionError("Connection refused by peer")):
        with pytest.raises(HTTPException) as exc_info:
            await generate_rca_analysis(req=req, current_user=mock_user, db=db)
        assert exc_info.value.status_code == 503
        assert "connection failed" in exc_info.value.detail.lower()

    service = GroqService()
    with patch.object(service, "is_available", return_value=True), \
         patch.object(service, "_call_groq_json", side_effect=GroqConnectionError("Failed to connect")):
        res = service.generate_rca_analysis({"batch_number": "B001", "description": "Excursion"}, allow_offline_fallback=True)
        assert res["status"] == "AI_UNAVAILABLE"
        assert res["five_whys"] == []
        assert res["fishbone_causes"] == []
        assert res["root_causes"] == []

# ----------------- TEST 6: Malformed JSON does not trigger synthetic RCA package -----------------
def test_malformed_json_response_handling():
    """Test 6: Malformed JSON from model raises GroqServiceError and produces no synthetic findings."""
    service = GroqService()
    with patch.object(service, "is_available", return_value=True):
        with patch("app.services.groq_service.ChatGroq") as mock_chat:
            mock_llm = MagicMock()
            mock_response = MagicMock()
            mock_response.content = "This is not valid JSON at all {missing braces"
            mock_llm.bind.return_value.invoke.return_value = mock_response
            mock_chat.return_value = mock_llm
            with pytest.raises(GroqServiceError) as exc_info:
                service._call_groq_json("system", "user")
            assert "malformed model response" in str(exc_info.value).lower()

    # When offline fallback is allowed, malformed JSON yields AI_UNAVAILABLE with empty findings
    with patch.object(service, "is_available", return_value=True), \
         patch.object(service, "_call_groq_json", side_effect=GroqServiceError("Malformed model response")):
        res = service.generate_rca_analysis({"batch_number": "B001", "description": "Excursion"}, allow_offline_fallback=True)
        assert res["status"] == "AI_UNAVAILABLE"
        assert res["five_whys"] == []
        assert res["fishbone_causes"] == []
        assert res["root_causes"] == []
        assert res["capa_actions"] == []

# ----------------- TEST 7: Incomplete Groq output does not trigger synthetic padding -----------------
def test_incomplete_groq_output_no_padding():
    """Test 7: Incomplete Groq output preserves returned sections and leaves unsupported sections empty."""
    service = GroqService()
    # Mock LLM returning only 2 whys and only 1 fishbone category (MACHINE)
    mock_payload = {
        "five_whys": [
            {"step_number": 1, "question": "Why did agitator stop?", "answer": "VFD tripped", "evidence_reference": "VFD fault log"},
            {"step_number": 2, "question": "Why did VFD trip?", "answer": "Overcurrent detected", "evidence_reference": "Motor log"}
        ],
        "fishbone_causes": [
            {"category": "MACHINE", "cause_description": "Agitator gearbox friction", "status": "HYPOTHESIS"}
        ],
        "root_causes": [
            {"cause_statement": "Motor gearbox overcurrent trip", "category": "EQUIPMENT_FAILURE", "is_primary": True}
        ],
        "capa_actions": []
    }
    with patch.object(service, "is_available", return_value=True), \
         patch.object(service, "_call_groq_json", return_value=mock_payload):
        res = service.generate_rca_analysis({"batch_number": "B001", "description": "Agitator stop"})
        assert len(res["five_whys"]) == 2, "Fewer than 5 whys must be accepted without forced padding"
        assert len(res["fishbone_causes"]) == 1, "Only 1 fishbone category must be accepted without padding to 6"
        assert res["fishbone_causes"][0]["category"] == "MACHINE"
        assert res["capa_actions"] == [], "Empty CAPAs must remain empty without dummy actions injected"

# ----------------- TEST 8: Unrelated document produces no pharmaceutical deviation -----------------
def test_unrelated_document_produces_no_deviation():
    """Test 8: Unrelated documents produce zero fabricated incidents, 0 Whys, and 0 Fishbones."""
    unrelated_text = (
        "Cafeteria Committee Meeting Minutes: Discussed daily special options for Wednesday lunch menu. "
        "Reviewed catering schedule for upcoming company picnic and coffee machine maintenance."
    )
    dev = {"description": unrelated_text}

    # Direct fallback test
    rca = groq_service._fallback_rca_generation(dev)
    assert rca["five_whys"] == []
    assert rca["fishbone_causes"] == []
    assert rca["root_causes"] == []
    assert rca["capa_actions"] == []
    assert "unavailable" in rca["investigator_guidance"].lower()

    # generate_rca_analysis check
    rca_gen = groq_service.generate_rca_analysis(dev, allow_offline_fallback=True)
    assert rca_gen["status"] == "NO_DEVIATION_DETECTED"
    assert rca_gen["five_whys"] == []
    assert rca_gen["fishbone_causes"] == []
    assert rca_gen["root_causes"] == []
    assert rca_gen["capa_actions"] == []

# ----------------- TEST 9: Valid source does not acquire invented constants -----------------
def test_valid_manufacturing_source_no_invented_facts():
    """Test 9: Valid manufacturing source does not acquire invented batch numbers, equipment, temperatures, or SOPs."""
    incident_text = "Temperature excursion in reactor RX-101 for lot B2026-API-111 during crystallization."
    extracted = groq_service._fallback_intake_extraction(incident_text, "TEXT")

    # Verify extracted real fields
    assert extracted["deviation"]["batch_number"] == "B2026-API-111"
    assert extracted["deviation"]["equipment_id"] == "RX-101"
    assert extracted["deviation"]["unit_operation"] == "Crystallization"

    # Verify none of the synthetic constants or canned fabrications exist
    ext_str = str(extracted)
    for const in SYNTHETIC_CONSTANTS:
        assert const not in ext_str, f"Synthetic constant '{const}' detected in extraction"
    assert "CV-04" not in ext_str, "Fabricated valve CV-04 detected"
    assert "pneumatic actuator restriction" not in ext_str, "Fabricated actuator narrative detected"
    assert "ramp rate" not in ext_str, "Fabricated ramp rate detected"

# ----------------- TEST 10: Manual Five Whys and Fishbone CRUD still work -----------------
@pytest.mark.asyncio
async def test_manual_five_whys_and_fishbone_crud(mock_user):
    """Test 10: Existing manual Five Whys and Fishbone CRUD endpoints operate independently of Groq."""
    db = AsyncMock()
    db.add = MagicMock()

    # 1. Manual Five Whys Add
    step_in = FiveWhysStepCreate(
        step_number=1,
        question="Why did the agitator trip?",
        answer="Operator observed VFD overcurrent fault code F002",
        evidence_reference="Shift logbook page 14",
        is_ai_suggested=False,
        is_verified=True
    )
    with patch("app.api.endpoints.five_whys.verify_investigation_access", return_value=True), \
         patch("app.api.endpoints.five_whys.audit_service.log_action", return_value=None):
        added_step = await add_five_why_step(investigation_id=101, step_in=step_in, current_user=mock_user, db=db)
        assert added_step.step_number == 1
        assert added_step.question == "Why did the agitator trip?"
        assert added_step.is_ai_suggested is False
        assert added_step.is_verified is True

    # 2. Manual Fishbone Add
    cause_in = FishboneCauseCreate(
        category="MACHINE",
        cause_description="VFD cooling fan filter clogged with dust",
        status="HYPOTHESIS",
        rationale="Visual inspection of electrical panel cabinet",
        is_ai_suggested=False,
        is_verified=True
    )
    with patch("app.api.endpoints.fishbone.verify_investigation_access", return_value=True), \
         patch("app.api.endpoints.fishbone.audit_service.log_action", return_value=None):
        added_cause = await add_fishbone_cause(investigation_id=101, cause_in=cause_in, current_user=mock_user, db=db)
        assert added_cause.category == "MACHINE"
        assert added_cause.cause_description == "VFD cooling fan filter clogged with dust"
        assert added_cause.is_ai_suggested is False

# ----------------- TEST 11: Human-confirmation and evidence-verification restrictions -----------------
def test_human_confirmation_and_evidence_restrictions():
    """Test 11: Unverified AI causes cannot be CONFIRMED without human review."""
    # Attempting to construct an unverified AI cause with status=CONFIRMED
    rc_obj = RootCauseCreate(
        cause_statement="Proposed primary root cause",
        category="EQUIPMENT_FAILURE",
        status="CONFIRMED",
        is_ai_suggested=True,
        is_verified=False
    )
    # Pydantic validator must demote it to PROPOSED
    assert rc_obj.status == "PROPOSED", "RootCauseCreate validator must demote unverified CONFIRMED status to PROPOSED"

    # Human-verified cause can be CONFIRMED
    rc_verified = RootCauseCreate(
        cause_statement="Verified primary root cause",
        category="EQUIPMENT_FAILURE",
        status="CONFIRMED",
        is_ai_suggested=False,
        is_verified=True
    )
    assert rc_verified.status == "CONFIRMED"

# ----------------- TEST 12: Chat does not produce synthetic AI answer after provider failure -----------------
def test_chat_no_synthetic_answer_after_provider_failure():
    """Test 12: Copilot chat returns explicit provider-unavailable message on provider failure, no fake advice."""
    service = GroqService()
    state = {
        "deviation": {
            "batch": "B2026-API-999",
            "equipment": "DRY-101",
            "unit_operation": "Vacuum Drying"
        }
    }
    with patch.object(service, "is_available", return_value=True):
        with patch("app.services.groq_service.ChatGroq") as mock_chat:
            mock_llm = MagicMock()
            mock_llm.invoke.side_effect = Exception("API connection refused")
            mock_chat.return_value = mock_llm

            reply = service.chat_copilot([], state, "Explain 5 Whys for this deviation", allow_offline_fallback=True)
            assert "unavailable" in reply.lower(), "Must return explicit provider-unavailable notice"
            for const in SYNTHETIC_CONSTANTS:
                assert const not in reply, f"Synthetic constant '{const}' detected in chat fallback"
            assert "diaphragm" not in reply.lower()
            assert "cooling valve" not in reply.lower()
            assert "sop-" not in reply.lower()

# ----------------- TEST 13: API key and token sanitization in error traces -----------------
def test_api_key_sanitization_in_errors():
    """Test 13: Sanitize secret scrubs gsk_ API keys, Bearer tokens, and Auth headers from errors."""
    raw_error = "Error calling endpoint with Authorization: Bearer gsk_secret_1234567890abcdef and key gsk_test_api_key_xyz"
    sanitized = sanitize_secret(raw_error, secret="gsk_secret_1234567890abcdef")
    assert "gsk_secret_1234567890abcdef" not in sanitized
    assert "gsk_test_api_key_xyz" not in sanitized
    assert "***REDACTED_API_KEY***" in sanitized
    assert "Bearer ***REDACTED" in sanitized

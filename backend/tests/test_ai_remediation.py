import pytest
import pytest_asyncio
import os
import json
from unittest.mock import patch, MagicMock

from app.core.config import settings
from app.services.groq_service import (
    GroqService,
    GroqServiceError,
    GroqAuthenticationError,
    GroqModelNotFoundError,
    GroqRateLimitError,
    GroqTimeoutError,
    groq_service
)
from app.services.langgraph_workflow import rca_graph, create_rca_workflow
from app.schemas.deviation import DeviationCreate
from app.schemas.root_cause import RootCauseCreate
from app.schemas.capa import CapaActionCreate

# ----------------- TEST A: Configuration and Groq Client Initialization -----------------
def test_a_configuration_and_groq_client_initialization():
    """Verify GROQ_API_KEY and GROQ_MODEL loading and client initialization."""
    assert bool(settings.GROQ_API_KEY), "GROQ_API_KEY is not configured in settings"
    assert bool(settings.GROQ_MODEL), "GROQ_MODEL is not configured in settings"
    assert groq_service.is_available() is True, "groq_service client is not available"
    assert groq_service.client is not None
    assert groq_service.model == settings.GROQ_MODEL or bool(groq_service.model)

# ----------------- TEST B: Genuine Groq API Inference -----------------
@pytest.mark.live_provider
@pytest.mark.asyncio
async def test_b_genuine_groq_api_inference():
    """Live integration test: invokes genuine Groq API and validates response."""
    if not groq_service.is_available():
        pytest.fail("BLOCKED: Groq credentials missing or client unavailable. Cannot execute live inference.")

    prompt_text = (
        "Deviation DEV-2026-901 in API facility. Batch: B2026-API-999. "
        "Product: Atorvastatin Calcium API. Unit: Crystallization in RX-301. "
        "Temperature spiked to 64C exceeding SOP limit of 50C due to valve sticking."
    )
    # Invoke genuine live Groq inference
    result = groq_service.extract_intake_data(prompt_text, source_type="TEXT")
    
    assert isinstance(result, dict)
    assert "deviation" in result
    dev = result["deviation"]
    assert dev.get("batch_number") == "B2026-API-999"
    assert "Atorvastatin" in dev.get("product_name", "")
    assert len(result.get("extracted_findings", [])) >= 1
    assert len(result.get("missing_information", [])) >= 1

# ----------------- TEST C: Invalid API Key Handling -----------------
def test_c_invalid_api_key_handling():
    """
    Verify request-scoped Groq authentication handling and key sanitization.
    Scenario 1: Invalid primary key with a valid backup key -> succeeds through backup.
    Scenario 2: Invalid primary key with no usable backup key -> raises GroqAuthenticationError and redacts key.
    """
    service = GroqService()
    fake_primary = "gsk_invalid_primary_test_key_abc123"
    fake_backup = "gsk_valid_backup_test_key_xyz789"

    # Scenario 1: Invalid primary with valid backup key -> failover succeeds
    keys_called = []
    def mock_chatgroq_factory(**kwargs):
        key = kwargs.get("groq_api_key")
        keys_called.append(key)
        mock_instance = MagicMock()
        mock_bound = MagicMock()
        mock_instance.bind.return_value = mock_bound
        if key == fake_primary:
            mock_bound.invoke.side_effect = Exception("Error code: 401 - Invalid API Key")
        elif key == fake_backup:
            mock_resp = MagicMock()
            mock_resp.content = '{"status": "SUCCESS", "message": "failover_verified"}'
            mock_bound.invoke.return_value = mock_resp
        return mock_instance

    with patch("app.core.config.settings.GROQ_API_KEY", fake_primary), \
         patch("app.core.config.settings.GROQ_BACKUP_API_KEY", fake_backup), \
         patch("app.services.groq_service.ChatGroq", side_effect=mock_chatgroq_factory):
        res = service._call_groq_json("System prompt", "User prompt", request_api_key=fake_primary)
        assert res.get("status") == "SUCCESS"
        assert fake_primary in keys_called
        assert fake_backup in keys_called

    # Scenario 2: Invalid primary with no usable backup key -> raises GroqAuthenticationError
    def mock_chatgroq_401(**kwargs):
        mock_instance = MagicMock()
        mock_bound = MagicMock()
        mock_instance.bind.return_value = mock_bound
        mock_bound.invoke.side_effect = Exception("Error code: 401 - Invalid API Key")
        return mock_instance

    with patch("app.core.config.settings.GROQ_API_KEY", fake_primary), \
         patch("app.core.config.settings.GROQ_BACKUP_API_KEY", None), \
         patch("app.services.groq_service.ChatGroq", side_effect=mock_chatgroq_401):
        with pytest.raises(GroqAuthenticationError) as excinfo:
            service._call_groq_json("System prompt", "User prompt", request_api_key=fake_primary)
        # Assert that the invalid key is NEVER exposed in the exception message
        assert fake_primary not in str(excinfo.value)


# ----------------- TEST D: Unsupported Model Handling -----------------
def test_d_unsupported_model_handling():
    """Verify handling of unsupported model name."""
    is_valid = groq_service.validate_model_access("non-existent-model-xyz-123")
    assert is_valid is False

    service = GroqService()
    service.model = "non-existent-model-xyz-123"
    # Should resolve to supported candidate without crashing
    service._resolve_model()
    assert service.model != "non-existent-model-xyz-123"

# ----------------- TEST E: Rate-Limit and Timeout Handling -----------------
def test_e_rate_limit_and_timeout_handling():
    """Verify proper classification of rate limits and timeouts into custom exceptions."""
    service = GroqService()
    
    # Simulate rate limit error
    with patch.object(service, "is_available", return_value=True):
        with patch("app.services.groq_service.ChatGroq") as mock_chat, patch("time.sleep"):
            mock_llm = MagicMock()
            mock_llm.bind.return_value.invoke.side_effect = Exception("Error code: 429 - rate limit exceeded for tokens per minute")
            mock_chat.return_value = mock_llm
            with pytest.raises(GroqRateLimitError):
                service._call_groq_json("sys", "user")

    # Simulate timeout error
    with patch.object(service, "is_available", return_value=True):
        with patch("app.services.groq_service.ChatGroq") as mock_chat:
            mock_llm = MagicMock()
            mock_llm.bind.return_value.invoke.side_effect = Exception("Read timed out. (read timeout=60.0)")
            mock_chat.return_value = mock_llm
            with pytest.raises(GroqTimeoutError):
                service._call_groq_json("sys", "user")

# ----------------- TEST F: Structured Output Validation -----------------
def test_f_structured_output_validation():
    """Verify Pydantic schema validation and safety guard on root causes."""
    # Safety rule: AI suggestions cannot be CONFIRMED
    rc = RootCauseCreate(
        cause_statement="Cooling valve diaphragm failure",
        status="CONFIRMED",  # Attempt unauthorized confirmation
        is_ai_suggested=True,
        is_verified=False
    )
    assert rc.status == "PROPOSED", "AI suggestion must never be automatically CONFIRMED"

    # CAPA action type validation
    capa = CapaActionCreate(
        action_type="CORRECTIVE_ACTION",
        description="Replace diaphragm",
        rationale="Eliminates leak",
        effectiveness_criteria="Zero pressure drop"
    )
    assert capa.action_type == "CORRECTIVE_ACTION"

    with pytest.raises(ValueError):
        CapaActionCreate(
            action_type="INVALID_TYPE_XYZ",
            description="Bad action"
        )

MOCK_DETERMINISTIC_INTAKE = {
    "investigation_title": "Deviation Investigation - Batch B2026-API-044",
    "deviation": {
        "deviation_number": "DEV-2026-044",
        "batch_number": "B2026-API-044",
        "product_name": "Atorvastatin Calcium API",
        "unit_operation": "Crystallization",
        "equipment_id": "RX-301",
        "description": "Temperature spike to 68C in RX-301 crystallization reactor exceeding limits.",
        "severity": "Major",
        "is_ai_populated": True,
        "is_verified": False,
    },
    "extracted_fields": [
        {"field_name": "batch_number", "field_value": "B2026-API-044", "status": "EXTRACTED_UNVERIFIED", "is_accepted": False},
        {"field_name": "product_name", "field_value": "Atorvastatin Calcium API", "status": "EXTRACTED_UNVERIFIED", "is_accepted": False},
    ],
    "extracted_findings": [
        {"finding_text": "Temperature spike to 68C in RX-301", "finding_type": "OBSERVATION", "confidence_score": 0.95, "source_page": 1, "quote_text": "Temp spike to 68C in RX-301"}
    ],
    "missing_information": [],
    "conflicting_information": [],
    "recommended_immediate_actions": ["Isolate crystallization tank RX-301"],
    "ai_confidence_score": 0.95,
}

MOCK_DETERMINISTIC_RCA = {
    "status": "SUCCESS",
    "five_whys": [
        {"step_number": 1, "question": "Why did temp spike?", "answer": "Cooling valve CV-301 failed to open", "is_ai_suggested": True, "is_verified": False},
        {"step_number": 2, "question": "Why did CV-301 fail to open?", "answer": "Pneumatic actuator air supply pressure was lost", "is_ai_suggested": True, "is_verified": False}
    ],
    "fishbone_causes": [
        {"category": "MACHINE", "cause_description": "Cooling valve CV-301 actuator failure", "status": "HYPOTHESIS", "is_ai_suggested": True, "is_verified": False}
    ],
    "root_causes": [
        {"cause_statement": "Mechanical sticking of cooling valve CV-301 due to air supply failure", "category": "EQUIPMENT_FAILURE", "is_primary": True, "status": "PROPOSED", "is_ai_suggested": True, "is_verified": False}
    ],
    "capa_actions": [
        {"action_type": "CORRECTION", "description": "Inspect and replace air supply tubing to CV-301", "is_ai_suggested": True, "is_verified": False, "rationale": "Direct containment", "effectiveness_criteria": "Valve stroking test passes"}
    ]
}

# ----------------- TEST G: LangGraph Node Execution -----------------
@pytest.mark.asyncio
async def test_g_langgraph_node_execution():
    """Verify execution of the 13-node LangGraph StateGraph pipeline."""
    initial_state = {
        "raw_document": "Deviation in Batch B2026-API-044. Product: Atorvastatin Calcium. Unit: Crystallization. Temp spike to 68C in RX-301.",
        "raw_bytes": None,
        "source_type": "TEXT",
        "parsed_text": "",
        "metadata": {},
        "extracted_data": {},
        "validation_errors": [],
        "is_valid": True,
        "missing_evidence": [],
        "has_critical_missing_info": False,
        "evidence_analysis": {},
        "has_conflicting_evidence": False,
        "is_evidence_insufficient": False,
        "investigation_plan": {},
        "selected_methodology": "BOTH",
        "rca_analysis": None,
        "five_whys": [],
        "fishbone_causes": [],
        "root_causes": [],
        "capa_actions": [],
        "output_validated": False,
        "validation_issues": [],
        "human_approved": False,
        "current_step": "START",
        "trace_log": [],
        "allow_offline_fallback": False
    }

    with patch.object(groq_service, "is_available", return_value=True), \
         patch.object(groq_service, "extract_intake_data", return_value=MOCK_DETERMINISTIC_INTAKE), \
         patch.object(groq_service, "generate_rca_analysis", return_value=MOCK_DETERMINISTIC_RCA):
        final_state = await rca_graph.ainvoke(initial_state)
        assert final_state["current_step"] == "READY_FOR_INVESTIGATOR"
        assert final_state["human_approved"] is False
        assert final_state["output_validated"] is True
        assert len(final_state["trace_log"]) >= 10

# ----------------- TEST H: Conditional Routing -----------------
@pytest.mark.asyncio
async def test_h_conditional_routing():
    """Verify conditional routing: methodology selection skips unselected nodes."""
    # Test 5-Whys only methodology selection
    initial_state = {
        "raw_document": "Deviation in Batch B2026-API-044. Product: Atorvastatin. Description: Valve failure in RX-301.",
        "raw_bytes": None,
        "source_type": "TEXT",
        "parsed_text": "",
        "metadata": {},
        "extracted_data": {},
        "validation_errors": [],
        "is_valid": True,
        "missing_evidence": [],
        "has_critical_missing_info": False,
        "evidence_analysis": {},
        "has_conflicting_evidence": False,
        "is_evidence_insufficient": False,
        "investigation_plan": {},
        "selected_methodology": "5_WHYS",  # User only selected 5-Whys
        "rca_analysis": None,
        "five_whys": [],
        "fishbone_causes": [],
        "root_causes": [],
        "capa_actions": [],
        "output_validated": False,
        "validation_issues": [],
        "human_approved": False,
        "current_step": "START",
        "trace_log": [],
        "allow_offline_fallback": False
    }

    with patch.object(groq_service, "is_available", return_value=True), \
         patch.object(groq_service, "extract_intake_data", return_value=MOCK_DETERMINISTIC_INTAKE), \
         patch.object(groq_service, "generate_rca_analysis", return_value=MOCK_DETERMINISTIC_RCA):
        final_state = await rca_graph.ainvoke(initial_state)
        traces = " ".join(final_state["trace_log"])
        assert "8. 5 Whys Analysis Node" in traces
        # Fishbone node should have been bypassed via conditional routing
        assert "9. Fishbone Analysis Node" not in traces
        assert len(final_state["five_whys"]) >= 1

# ----------------- TEST I: Missing Evidence Handling -----------------
@pytest.mark.asyncio
async def test_i_missing_evidence_handling():
    """Verify that narrative with missing critical fields generates follow-up questions."""
    initial_state = {
        "raw_document": "Something went wrong in the plant. Temperature went up. No batch info recorded.",
        "raw_bytes": None,
        "source_type": "TEXT",
        "parsed_text": "",
        "metadata": {},
        "extracted_data": {
            "deviation": {"description": "Temperature went up without batch details"}
        },
        "validation_errors": [],
        "is_valid": True,
        "missing_evidence": [],
        "has_critical_missing_info": False,
        "evidence_analysis": {},
        "has_conflicting_evidence": False,
        "is_evidence_insufficient": False,
        "investigation_plan": {},
        "selected_methodology": "5_WHYS",
        "rca_analysis": None,
        "five_whys": [],
        "fishbone_causes": [],
        "root_causes": [],
        "capa_actions": [],
        "output_validated": False,
        "validation_issues": [],
        "human_approved": False,
        "current_step": "START",
        "trace_log": [],
        "allow_offline_fallback": True
    }
    
    with patch.object(groq_service, "is_available", return_value=True), \
         patch.object(groq_service, "generate_rca_analysis", return_value=MOCK_DETERMINISTIC_RCA):
        final_state = await rca_graph.ainvoke(initial_state)
        assert len(final_state["missing_evidence"]) >= 1
        # Check that critical missing batch question was formulated
        categories = [item.get("category") for item in final_state["missing_evidence"]]
        assert any("BATCH" in c or "RECORD" in c for c in categories)

# ----------------- TEST J: Conflicting Evidence Handling -----------------
@pytest.mark.asyncio
async def test_j_conflicting_evidence_handling():
    """Verify that conflicting evidence forces causes to PROPOSED with conflict alert."""
    conflict_text = (
        "Batch B2026-API-044 deviation. SCADA telemetry recorded sharp temperature overshoot to 72C, "
        "however operator logbook states reactor remained at 48C and contradicts sensor data."
    )
    initial_state = {
        "raw_document": conflict_text,
        "raw_bytes": None,
        "source_type": "TEXT",
        "parsed_text": "",
        "metadata": {},
        "extracted_data": {},
        "validation_errors": [],
        "is_valid": True,
        "missing_evidence": [],
        "has_critical_missing_info": False,
        "evidence_analysis": {},
        "has_conflicting_evidence": False,
        "is_evidence_insufficient": False,
        "investigation_plan": {},
        "selected_methodology": "5_WHYS",
        "rca_analysis": None,
        "five_whys": [],
        "fishbone_causes": [],
        "root_causes": [],
        "capa_actions": [],
        "output_validated": False,
        "validation_issues": [],
        "human_approved": False,
        "current_step": "START",
        "trace_log": [],
        "allow_offline_fallback": True
    }

    mock_payload = {
        "five_whys": [{"step_number": 1, "question": "Why?", "answer": "Temp spike"}],
        "fishbone_causes": [{"category": "MACHINE", "cause_description": "Sensor error", "status": "HYPOTHESIS"}],
        "root_causes": [{"cause_statement": "Suspected temperature sensor error", "category": "MEASUREMENT", "is_primary": True, "status": "CONFIRMED"}],
        "capa_actions": [{"action_type": "CORRECTION", "description": "Verify logbooks"}]
    }
    with patch.object(groq_service, "is_available", return_value=True), \
         patch.object(groq_service, "_call_groq_json", return_value=mock_payload):
        final_state = await rca_graph.ainvoke(initial_state)
        assert final_state["has_conflicting_evidence"] is True
        # Verify all root causes are PROPOSED, none confirmed
        for rc in final_state["root_causes"]:
            assert rc["status"] == "PROPOSED"
            assert rc["is_verified"] is False

# ----------------- TEST K: 5 Whys Analysis -----------------
def test_k_five_whys_analysis():
    """Verify 5 Whys structure, non-fabrication, and verification tagging."""
    dev = {
        "deviation_number": "DEV-2026-084",
        "batch_number": "B2026-API-044",
        "product_name": "Atorvastatin Calcium API",
        "description": "Temperature overshoot due to CV-301 valve failure."
    }
    mock_payload = {
        "five_whys": [
            {
                "step_number": 1,
                "question": "Why did temperature overshoot?",
                "answer": "Cooling valve CV-301 failed to open.",
                "evidence_reference": "SCADA trend for CV-301"
            },
            {
                "step_number": 2,
                "question": "Why did CV-301 fail to open?",
                "answer": "Valve positioner feedback was unresponsive.",
                "evidence_reference": "Positioner telemetry"
            }
        ],
        "fishbone_causes": [
            {"category": "MACHINE", "cause_description": "Mechanical restriction in valve CV-301.", "status": "HYPOTHESIS"}
        ],
        "root_causes": [
            {"cause_statement": "Mechanical sticking of cooling valve CV-301.", "category": "EQUIPMENT_FAILURE", "is_primary": True}
        ],
        "capa_actions": [
            {"action_type": "CORRECTION", "description": "Quarantine affected lot and inspect valve CV-301."}
        ]
    }
    with patch.object(groq_service, "is_available", return_value=True), \
         patch.object(groq_service, "_call_groq_json", return_value=mock_payload):
        rca_data = groq_service.generate_rca_analysis(dev)
        whys = rca_data.get("five_whys", [])
        assert len(whys) >= 1
        for step in whys:
            assert step.get("step_number") >= 1
            assert bool(step.get("question"))
            assert bool(step.get("answer"))
            assert step.get("is_ai_suggested") is True
            assert step.get("is_verified") is False

    # Verify that provider failure returns empty findings
    with patch.object(groq_service, "is_available", return_value=True), \
         patch.object(groq_service, "_call_groq_json", side_effect=GroqServiceError("Provider offline")):
        res_fail = groq_service.generate_rca_analysis(dev, allow_offline_fallback=True)
        assert res_fail["status"] == "AI_UNAVAILABLE"
        assert res_fail["five_whys"] == []

# ----------------- TEST L: Fishbone Analysis -----------------
def test_l_fishbone_analysis():
    """Verify Ishikawa 6Ms categories, non-fabrication, and verification tagging."""
    dev = {
        "deviation_number": "DEV-2026-084",
        "batch_number": "B2026-API-044",
        "product_name": "Atorvastatin Calcium API",
        "description": "Cooling failure in crystallization."
    }
    mock_payload = {
        "five_whys": [
            {"step_number": 1, "question": "Why?", "answer": "Cooling failure"}
        ],
        "fishbone_causes": [
            {"category": "MACHINE", "cause_description": "Cooling coil obstruction", "status": "CONFIRMED"},
            {"category": "METHOD", "cause_description": "Cooling ramp rate not calibrated", "status": "HYPOTHESIS"}
        ],
        "root_causes": [
            {"cause_statement": "Cooling failure", "category": "EQUIPMENT_FAILURE", "is_primary": True}
        ],
        "capa_actions": [
            {"action_type": "CORRECTIVE_ACTION", "description": "Inspect and descale cooling coil."}
        ]
    }
    with patch.object(groq_service, "is_available", return_value=True), \
         patch.object(groq_service, "_call_groq_json", return_value=mock_payload):
        rca_data = groq_service.generate_rca_analysis(dev)
        fishbone = rca_data.get("fishbone_causes", [])
        assert len(fishbone) >= 1
        for fc in fishbone:
            assert bool(fc.get("category"))
            assert bool(fc.get("cause_description"))
            assert fc.get("status") in ("HYPOTHESIS", "RULED_OUT", "PROPOSED")
            assert fc.get("status") != "CONFIRMED"
            assert fc.get("is_ai_suggested") is True
            assert fc.get("is_verified") is False

    # Verify that provider failure returns empty findings
    with patch.object(groq_service, "is_available", return_value=True), \
         patch.object(groq_service, "_call_groq_json", side_effect=GroqServiceError("Provider offline")):
        res_fail = groq_service.generate_rca_analysis(dev, allow_offline_fallback=True)
        assert res_fail["status"] == "AI_UNAVAILABLE"
        assert res_fail["fishbone_causes"] == []

# ----------------- TEST M: CAPA Generation -----------------
def test_m_capa_generation():
    """Verify CAPA recommendations include Correction, Corrective Action, Preventive Action."""
    dev = {
        "deviation_number": "DEV-2026-084",
        "batch_number": "B2026-API-044",
        "product_name": "Atorvastatin Calcium API",
        "description": "Diaphragm rupture on cooling valve CV-301."
    }
    mock_payload = {
        "five_whys": [],
        "fishbone_causes": [],
        "root_causes": [],
        "capa_actions": [
            {
                "action_type": "CORRECTION",
                "description": "Quarantine affected lot and isolate cooling valve.",
                "rationale": "Immediate containment",
                "effectiveness_criteria": "Physical quarantine tag attached"
            },
            {
                "action_type": "CORRECTIVE_ACTION",
                "description": "Replace worn valve components and recalibrate positioner.",
                "rationale": "Direct remediation of failure mode",
                "effectiveness_criteria": "Valve stroking test passes without drift"
            },
            {
                "action_type": "PREVENTIVE_ACTION",
                "description": "Review and update PM inspection intervals for all critical control valves.",
                "rationale": "Systemic horizontal prevention across facility trains",
                "effectiveness_criteria": "Zero repeat excursions in 90 days"
            }
        ]
    }
    with patch.object(groq_service, "is_available", return_value=True), \
         patch.object(groq_service, "_call_groq_json", return_value=mock_payload):
        rca_data = groq_service.generate_rca_analysis(dev)
        capas = rca_data.get("capa_actions", [])
        assert len(capas) >= 1
        for c in capas:
            assert c.get("action_type") in ("CORRECTION", "CORRECTIVE_ACTION", "PREVENTIVE_ACTION")
            assert c.get("is_ai_suggested") is True
            assert c.get("is_verified") is False
            assert bool(c.get("description"))
            assert bool(c.get("rationale"))
            assert bool(c.get("effectiveness_criteria"))

    # Verify that provider failure returns empty findings
    with patch.object(groq_service, "is_available", return_value=True), \
         patch.object(groq_service, "_call_groq_json", side_effect=GroqServiceError("Provider offline")):
        res_fail = groq_service.generate_rca_analysis(dev, allow_offline_fallback=True)
        assert res_fail["status"] == "AI_UNAVAILABLE"
        assert res_fail["capa_actions"] == []

# ----------------- TEST N: AI Failure Handling -----------------
def test_n_ai_failure_handling():
    """Verify that missing API key raises clear GroqServiceError instead of fake data."""
    service = GroqService()
    service.api_key = ""
    service.client = None

    with pytest.raises(GroqServiceError) as excinfo:
        service.extract_intake_data("Some incident text", "TEXT", allow_offline_fallback=False)
    assert "GROQ_API_KEY is not configured" in str(excinfo.value)


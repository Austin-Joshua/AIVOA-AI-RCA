import pytest
import asyncio
from unittest.mock import patch, MagicMock
from app.services.groq_service import (
    groq_service,
    GroqServiceError,
    GroqRateLimitError
)
from app.services.langgraph_workflow import rca_graph

MOCK_EXTRACTED_PAYLOAD = {
    "deviation": {
        "deviation_number": "DEV-2026-044",
        "batch_number": "B2026-API-044",
        "product_name": "Atorvastatin Calcium Trihydrate API",
        "unit_operation": "Crystallization",
        "equipment_id": "RX-301",
        "severity": "Major",
        "description": "Observed temperature of 38.4C exceeding specification of 20-24C."
    },
    "extracted_findings": [
        {
            "finding_text": "Observed temperature of 38.4C exceeding specification of 20-24C",
            "finding_type": "OBSERVATION",
            "confidence_score": 0.95,
            "source_page": 1,
            "quote_text": "Observed temperature of 38.4C exceeding specification of 20-24C."
        }
    ],
    "missing_information": [
        {
            "category": "CALIBRATION",
            "question": "What was calibration status of temperature sensor in RX-301?",
            "impact_description": "Verify measurement accuracy",
            "urgency": "HIGH"
        }
    ]
}

MOCK_RCA_PAYLOAD = {
    "status": "SUCCESS",
    "five_whys": [
        {
            "step_number": 1,
            "question": "Why did temperature exceed specification?",
            "answer": "Cooling valve positioner malfunctioned.",
            "is_ai_suggested": True,
            "is_verified": False
        },
        {
            "step_number": 2,
            "question": "Why did cooling valve positioner malfunction?",
            "answer": "Pneumatic supply pressure dropped below required setpoint.",
            "is_ai_suggested": True,
            "is_verified": False
        }
    ],
    "fishbone_causes": [
        {
            "category": "MACHINE",
            "cause_description": "Cooling valve positioner mechanical restriction",
            "status": "HYPOTHESIS",
            "is_ai_suggested": True,
            "is_verified": False
        }
    ],
    "root_causes": [
        {
            "cause_statement": "Cooling valve positioner malfunction due to pneumatic line pressure drop",
            "category": "EQUIPMENT_FAILURE",
            "is_primary": True,
            "status": "CONFIRMED",  # AI attempts to confirm; must be coerced to PROPOSED
            "is_ai_suggested": True,
            "is_verified": False
        }
    ],
    "capa_actions": [
        {
            "action_type": "CORRECTION",
            "description": "Isolate cooling valve CV-301 and replace faulty positioner diaphragm.",
            "rationale": "Direct remediation of failure mode",
            "effectiveness_criteria": "Positioner stroking test completes with 0% hysteresis.",
            "is_ai_suggested": True,
            "is_verified": False
        }
    ]
}

@pytest.mark.asyncio
async def test_groq_intake_extraction():
    """Verify intake extraction with deterministic mocked LLM response and failure handling."""
    sample_text = (
        "Manufacturing Deviation Report: Batch B2026-API-044 of Atorvastatin Calcium Trihydrate API. "
        "Unit Operation: Crystallization in Reactor RX-301. "
        "Observed temperature of 38.4C exceeding specification of 20-24C. "
        "Cooling valve positioner malfunction suspected. Batch quarantined."
    )

    # 1. Successful inference path
    with patch.object(groq_service, "is_available", return_value=True), \
         patch.object(groq_service, "_call_groq_json", return_value=MOCK_EXTRACTED_PAYLOAD):
        extracted = groq_service.extract_intake_data(sample_text, "TEXT", allow_offline_fallback=True)
        assert "deviation" in extracted
        dev = extracted["deviation"]
        assert "B2026-API-044" in dev["batch_number"]
        assert "RX-301" in dev["equipment_id"]
        assert len(extracted["missing_information"]) > 0

    # 2. Provider failure path with offline fallback enabled
    with patch.object(groq_service, "is_available", return_value=True), \
         patch.object(groq_service, "_call_groq_json", side_effect=GroqServiceError("Provider offline")):
        extracted_fallback = groq_service.extract_intake_data(sample_text, "TEXT", allow_offline_fallback=True)
        assert "deviation" in extracted_fallback
        assert extracted_fallback["deviation"]["batch_number"] == "B2026-API-044"

@pytest.mark.asyncio
async def test_groq_rca_generation():
    """Verify RCA generation with deterministic mocked LLM response and failure handling."""
    dev = {
        "batch_number": "B2026-API-044",
        "product_name": "Atorvastatin Calcium Trihydrate API",
        "unit_operation": "Crystallization",
        "equipment_id": "RX-301",
        "severity": "Major",
        "description": "Temperature excursion during cooling cycle."
    }

    # 1. Successful inference path
    with patch.object(groq_service, "is_available", return_value=True), \
         patch.object(groq_service, "_call_groq_json", return_value=MOCK_RCA_PAYLOAD):
        rca = groq_service.generate_rca_analysis(dev, allow_offline_fallback=True)
        assert rca["status"] == "SUCCESS"
        assert len(rca["five_whys"]) >= 1
        assert len(rca["fishbone_causes"]) >= 1
        assert len(rca["root_causes"]) >= 1
        assert len(rca["capa_actions"]) >= 1
        for rc in rca["root_causes"]:
            assert rc["status"] == "PROPOSED", "AI must never automatically CONFIRM a root cause"
            assert rc["is_verified"] is False
            assert rc["is_ai_suggested"] is True

    # 2. Provider failure path returns empty candidate lists with AI_UNAVAILABLE
    with patch.object(groq_service, "is_available", return_value=True), \
         patch.object(groq_service, "_call_groq_json", side_effect=GroqServiceError("Provider 503")):
        rca_fail = groq_service.generate_rca_analysis(dev, allow_offline_fallback=True)
        assert rca_fail["status"] == "AI_UNAVAILABLE"
        assert rca_fail["five_whys"] == []
        assert rca_fail["fishbone_causes"] == []
        assert rca_fail["root_causes"] == []
        assert rca_fail["capa_actions"] == []

@pytest.mark.asyncio
async def test_langgraph_pipeline():
    """Verify end-to-end 13-node LangGraph pipeline execution with deterministic mock boundaries."""
    initial_state = {
        "raw_document": "Critical deviation reported in Batch B2026-API-044 in RX-301 during Crystallization: Temperature exceeded 22.0°C limit reaching 28.5°C during cooling cycle.",
        "raw_bytes": None,
        "source_type": "TEXT",
        "parsed_text": "",
        "metadata": {},
        "extracted_data": {},
        "validation_errors": [],
        "missing_evidence": [],
        "evidence_analysis": {},
        "investigation_plan": {},
        "selected_methodology": "BOTH",
        "rca_analysis": None,
        "five_whys": [],
        "fishbone_causes": [],
        "root_causes": [],
        "capa_actions": [],
        "output_validated": False,
        "human_approved": False,
        "current_step": "START",
        "trace_log": [],
        "allow_offline_fallback": True
    }

    # 1. Successful pipeline execution
    with patch.object(groq_service, "is_available", return_value=True), \
         patch.object(groq_service, "extract_intake_data", return_value=groq_service._fallback_intake_extraction(initial_state["raw_document"], "TEXT")), \
         patch.object(groq_service, "generate_rca_analysis", return_value=MOCK_RCA_PAYLOAD):
        final_state = await rca_graph.ainvoke(initial_state)
        assert final_state["output_validated"] is True
        assert "READY_FOR_INVESTIGATOR" in final_state["current_step"]
        assert len(final_state["five_whys"]) >= 1
        assert len(final_state["fishbone_causes"]) >= 1
        for w in final_state["five_whys"]:
            assert w["is_ai_suggested"] is True
            assert w["is_verified"] is False
        for fc in final_state["fishbone_causes"]:
            assert fc["is_ai_suggested"] is True
            assert fc["is_verified"] is False
        for rc in final_state["root_causes"]:
            assert rc["status"] == "PROPOSED"
            assert rc["is_verified"] is False

    # 2. Pipeline execution during provider unavailability
    unavailable_rca = {
        "status": "AI_UNAVAILABLE",
        "five_whys": [],
        "fishbone_causes": [],
        "root_causes": [],
        "capa_actions": [],
        "preliminary_notes": "Inference unavailable"
    }
    with patch.object(groq_service, "is_available", return_value=True), \
         patch.object(groq_service, "extract_intake_data", return_value=groq_service._fallback_intake_extraction(initial_state["raw_document"], "TEXT")), \
         patch.object(groq_service, "generate_rca_analysis", return_value=unavailable_rca):
        final_state_fail = await rca_graph.ainvoke(initial_state)
        assert final_state_fail["output_validated"] is True
        assert final_state_fail["five_whys"] == []
        assert final_state_fail["fishbone_causes"] == []

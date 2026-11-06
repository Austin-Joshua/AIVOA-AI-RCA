import pytest
import asyncio
import json
from unittest.mock import patch, MagicMock
from app.core.config import settings
from app.services.groq_service import (
    GroqService,
    GroqServiceError,
    GroqRateLimitError,
    GroqAuthenticationError,
    GroqPermissionError,
    GroqTimeoutError,
    GroqConnectionError,
    classify_rate_limit_error,
    sanitize_secret
)

MOCK_PRIMARY_KEY = "gsk_primary_test_key_111111111111111111111111111111111111"
MOCK_BACKUP_KEY  = "gsk_backup_test_key_222222222222222222222222222222222222"

@pytest.fixture(autouse=True)
def mock_sleep_fast():
    with patch("time.sleep"):
        yield

SAMPLE_DEV = {
    "batch_number": "B2026-API-044",
    "product_name": "Atorvastatin Calcium",
    "unit_operation": "Crystallization",
    "equipment_id": "RX-301",
    "severity": "Major",
    "description": "Temperature exceeded approved range during crystallization."
}

VALID_RCA_JSON = """
{
  "five_whys": [
    {
      "step_number": 1,
      "question": "Why did the temperature spike?",
      "answer": "Cooling fluid flow was reduced.",
      "evidence_reference": "Cooling loop flowmeter log",
      "is_ai_suggested": true,
      "is_verified": false
    }
  ],
  "fishbone_causes": [
    {
      "category": "MACHINE",
      "cause_description": "Pneumatic valve restriction",
      "status": "HYPOTHESIS",
      "rationale": "Actuator position feedback discrepancy",
      "evidence_reference": "SCADA log",
      "is_ai_suggested": true,
      "is_verified": false
    }
  ],
  "root_causes": [
    {
      "cause_statement": "Inadequate pneumatic supply pressure to cooling valve.",
      "category": "EQUIPMENT_FAILURE",
      "is_primary": true,
      "evidence_summary": "SCADA trend log confirmed low line pressure.",
      "status": "PROPOSED",
      "is_ai_suggested": true,
      "is_verified": false
    }
  ],
  "capa_actions": [
    {
      "action_type": "CORRECTION",
      "description": "Quarantine affected crystallization batch.",
      "rationale": "Immediate containment to protect downstream processing.",
      "owner": "Production Supervisor",
      "deadline": "24 Hours",
      "effectiveness_criteria": "Physical quarantine tags affixed.",
      "effectiveness_review_period_days": 7,
      "is_ai_suggested": true,
      "is_verified": false
    }
  ],
  "evidence_gaps": [],
  "investigator_guidance": "Review SCADA trend logs."
}
"""

# ==============================================================================
# TEST 1: Primary 401 -> backup successful inference
# ==============================================================================
def test_primary_401_backup_successful_inference():
    """Rule 1: Invalid/revoked primary credential (401) attempts backup credential and succeeds."""
    keys_used = []

    def mock_chatgroq_factory(**kwargs):
        key = kwargs.get("groq_api_key")
        keys_used.append(key)
        mock_instance = MagicMock()
        mock_bound = MagicMock()
        mock_instance.bind.return_value = mock_bound

        if key == MOCK_PRIMARY_KEY:
            mock_bound.invoke.side_effect = Exception("401 Unauthorized: Invalid API Key")
        elif key == MOCK_BACKUP_KEY:
            mock_resp = MagicMock()
            mock_resp.content = VALID_RCA_JSON
            mock_bound.invoke.return_value = mock_resp
        return mock_instance

    with patch("app.core.config.settings.GROQ_API_KEY", MOCK_PRIMARY_KEY), \
         patch("app.core.config.settings.GROQ_BACKUP_API_KEY", MOCK_BACKUP_KEY), \
         patch("app.services.groq_service.ChatGroq", side_effect=mock_chatgroq_factory):
        
        service = GroqService()
        result = service.generate_rca_analysis(SAMPLE_DEV, allow_offline_fallback=True)

        assert result["status"] == "SUCCESS"
        assert len(result["five_whys"]) == 1
        assert result["five_whys"][0]["answer"] == "Cooling fluid flow was reduced."
        # Verify both primary and backup were invoked in that exact order
        assert MOCK_PRIMARY_KEY in keys_used
        assert MOCK_BACKUP_KEY in keys_used
        assert keys_used.index(MOCK_PRIMARY_KEY) < keys_used.index(MOCK_BACKUP_KEY)


# ==============================================================================
# TEST 2: Primary 401 -> backup 401 -> AI_UNAVAILABLE
# ==============================================================================
def test_primary_401_backup_401_returns_ai_unavailable():
    """Rule 2: When both primary and backup credentials return 401, return AI_UNAVAILABLE with empty findings."""
    keys_used = []

    def mock_chatgroq_factory(**kwargs):
        key = kwargs.get("groq_api_key")
        keys_used.append(key)
        mock_instance = MagicMock()
        mock_bound = MagicMock()
        mock_instance.bind.return_value = mock_bound
        mock_bound.invoke.side_effect = Exception("401 Unauthorized: Invalid API Key")
        return mock_instance

    with patch("app.core.config.settings.GROQ_API_KEY", MOCK_PRIMARY_KEY), \
         patch("app.core.config.settings.GROQ_BACKUP_API_KEY", MOCK_BACKUP_KEY), \
         patch("app.services.groq_service.ChatGroq", side_effect=mock_chatgroq_factory):
        
        service = GroqService()
        result = service.generate_rca_analysis(SAMPLE_DEV, allow_offline_fallback=True)

        assert result["status"] == "AI_UNAVAILABLE"
        assert result["five_whys"] == []
        assert result["fishbone_causes"] == []
        assert result["root_causes"] == []
        assert result["capa_actions"] == []
        assert result["evidence_gaps"] == []
        assert "unavailable" in result["investigator_guidance"].lower()
        # Verify both keys were attempted
        assert MOCK_PRIMARY_KEY in keys_used
        assert MOCK_BACKUP_KEY in keys_used


# ==============================================================================
# TEST 3: Organization-level 429 -> no backup attempt
# ==============================================================================
def test_org_level_429_does_not_attempt_backup():
    """Rule 3: Organization-level TPD/TPM exhaustion must NOT rotate keys, returning QUOTA_BLOCKED."""
    keys_used = []

    def mock_chatgroq_factory(**kwargs):
        key = kwargs.get("groq_api_key")
        keys_used.append(key)
        mock_instance = MagicMock()
        mock_bound = MagicMock()
        mock_instance.bind.return_value = mock_bound
        # Simulate organization-level TPD error from Groq
        mock_bound.invoke.side_effect = Exception("429: Organization tokens per day (TPD) limit exceeded.")
        return mock_instance

    with patch("app.core.config.settings.GROQ_API_KEY", MOCK_PRIMARY_KEY), \
         patch("app.core.config.settings.GROQ_BACKUP_API_KEY", MOCK_BACKUP_KEY), \
         patch("app.services.groq_service.ChatGroq", side_effect=mock_chatgroq_factory):
        
        service = GroqService()
        result = service.generate_rca_analysis(SAMPLE_DEV, allow_offline_fallback=True)

        assert result["status"] == "QUOTA_BLOCKED"
        assert result["five_whys"] == []
        assert result["fishbone_causes"] == []
        # Crucial check: backup key was NEVER attempted
        assert MOCK_PRIMARY_KEY in keys_used
        assert MOCK_BACKUP_KEY not in keys_used


# ==============================================================================
# TEST 4: Project-level 429 -> backup attempt only when separate projects established
# ==============================================================================
def test_project_level_429_backup_only_when_separate_project_configured():
    """Rule 4: Project-level 429 attempts backup ONLY when separate projects are explicitly configured."""
    
    # 4A: Same/unconfigured project -> NO backup attempt
    keys_used_a = []
    def mock_chatgroq_factory_a(**kwargs):
        key = kwargs.get("groq_api_key")
        keys_used_a.append(key)
        mock_instance = MagicMock()
        mock_bound = MagicMock()
        mock_instance.bind.return_value = mock_bound
        mock_bound.invoke.side_effect = Exception("429: Project rate limit exceeded.")
        return mock_instance

    with patch("app.core.config.settings.GROQ_API_KEY", MOCK_PRIMARY_KEY), \
         patch("app.core.config.settings.GROQ_BACKUP_API_KEY", MOCK_BACKUP_KEY), \
         patch("app.core.config.settings.GROQ_PROJECT_ID", None), \
         patch("app.core.config.settings.GROQ_BACKUP_PROJECT_ID", None), \
         patch("app.services.groq_service.ChatGroq", side_effect=mock_chatgroq_factory_a):
        
        service = GroqService()
        result_a = service.generate_rca_analysis(SAMPLE_DEV, allow_offline_fallback=True)
        assert result_a["status"] == "QUOTA_BLOCKED"
        assert MOCK_BACKUP_KEY not in keys_used_a

    # 4B: Separate projects configured -> Backup attempted and succeeds
    keys_used_b = []
    def mock_chatgroq_factory_b(**kwargs):
        key = kwargs.get("groq_api_key")
        keys_used_b.append(key)
        mock_instance = MagicMock()
        mock_bound = MagicMock()
        mock_instance.bind.return_value = mock_bound
        if key == MOCK_PRIMARY_KEY:
            mock_bound.invoke.side_effect = Exception("429: Project rate limit exceeded.")
        elif key == MOCK_BACKUP_KEY:
            mock_resp = MagicMock()
            mock_resp.content = VALID_RCA_JSON
            mock_bound.invoke.return_value = mock_resp
        return mock_instance

    with patch("app.core.config.settings.GROQ_API_KEY", MOCK_PRIMARY_KEY), \
         patch("app.core.config.settings.GROQ_BACKUP_API_KEY", MOCK_BACKUP_KEY), \
         patch("app.core.config.settings.GROQ_PROJECT_ID", "proj_dept_a"), \
         patch("app.core.config.settings.GROQ_BACKUP_PROJECT_ID", "proj_dept_b"), \
         patch("app.services.groq_service.ChatGroq", side_effect=mock_chatgroq_factory_b):
        
        service = GroqService()
        result_b = service.generate_rca_analysis(SAMPLE_DEV, allow_offline_fallback=True)
        assert result_b["status"] == "SUCCESS"
        assert MOCK_PRIMARY_KEY in keys_used_b
        assert MOCK_BACKUP_KEY in keys_used_b


# ==============================================================================
# TEST 5: Unknown 429 classification -> QUOTA_BLOCKED, no rotation
# ==============================================================================
def test_unknown_429_classification_fails_safely_without_rotation():
    """Rule 5: Ambiguous 429 fails safely and returns QUOTA_BLOCKED without rotating keys."""
    keys_used = []

    def mock_chatgroq_factory(**kwargs):
        key = kwargs.get("groq_api_key")
        keys_used.append(key)
        mock_instance = MagicMock()
        mock_bound = MagicMock()
        mock_instance.bind.return_value = mock_bound
        mock_bound.invoke.side_effect = Exception("429: Rate limit reached. Please wait before retrying.")
        return mock_instance

    with patch("app.core.config.settings.GROQ_API_KEY", MOCK_PRIMARY_KEY), \
         patch("app.core.config.settings.GROQ_BACKUP_API_KEY", MOCK_BACKUP_KEY), \
         patch("app.services.groq_service.ChatGroq", side_effect=mock_chatgroq_factory):
        
        service = GroqService()
        result = service.generate_rca_analysis(SAMPLE_DEV, allow_offline_fallback=True)

        assert result["status"] == "QUOTA_BLOCKED"
        assert result["five_whys"] == []
        assert MOCK_BACKUP_KEY not in keys_used


# ==============================================================================
# TEST 6: Backup failure -> structured unavailable result
# ==============================================================================
def test_backup_failure_returns_structured_unavailable_result():
    """Rule 6: If primary fails with 401 and backup fails with 5xx/network, return structured AI_UNAVAILABLE."""
    def mock_chatgroq_factory(**kwargs):
        key = kwargs.get("groq_api_key")
        mock_instance = MagicMock()
        mock_bound = MagicMock()
        mock_instance.bind.return_value = mock_bound
        if key == MOCK_PRIMARY_KEY:
            mock_bound.invoke.side_effect = Exception("401 Unauthorized: Invalid primary key")
        elif key == MOCK_BACKUP_KEY:
            mock_bound.invoke.side_effect = Exception("503 Service Unavailable: upstream server down")
        return mock_instance

    with patch("app.core.config.settings.GROQ_API_KEY", MOCK_PRIMARY_KEY), \
         patch("app.core.config.settings.GROQ_BACKUP_API_KEY", MOCK_BACKUP_KEY), \
         patch("app.services.groq_service.ChatGroq", side_effect=mock_chatgroq_factory):
        
        service = GroqService()
        result = service.generate_rca_analysis(SAMPLE_DEV, allow_offline_fallback=True)

        assert result["status"] == "AI_UNAVAILABLE"
        assert result["five_whys"] == []
        assert result["fishbone_causes"] == []
        assert result["root_causes"] == []
        assert result["capa_actions"] == []


# ==============================================================================
# TEST 7: Concurrent requests cannot exchange credentials
# ==============================================================================
@pytest.mark.asyncio
async def test_concurrent_requests_cannot_exchange_credentials():
    """Rule 7: Request-scoped credential selection ensures concurrent requests cannot mutate each other's credentials."""
    
    execution_log = []

    def mock_chatgroq_factory(**kwargs):
        key = kwargs.get("groq_api_key")
        mock_instance = MagicMock()
        mock_bound = MagicMock()
        mock_instance.bind.return_value = mock_bound

        def _invoke(messages):
            # Inspect user message to know which task this is
            prompt = str(messages)
            if "TASK_A" in prompt:
                execution_log.append(("TASK_A", key))
                if key == MOCK_PRIMARY_KEY:
                    raise Exception("401 Unauthorized: Invalid primary key")
                mock_resp = MagicMock()
                mock_resp.content = '{"five_whys": [], "fishbone_causes": [], "root_causes": [], "capa_actions": [], "status": "SUCCESS"}'
                return mock_resp
            else:
                execution_log.append(("TASK_B", key))
                mock_resp = MagicMock()
                mock_resp.content = '{"five_whys": [], "fishbone_causes": [], "root_causes": [], "capa_actions": [], "status": "SUCCESS"}'
                return mock_resp

        mock_bound.invoke.side_effect = _invoke
        return mock_instance

    service = GroqService()

    async def run_task_a():
        # TASK A: Primary key gets 401, fails over to backup key
        await asyncio.sleep(0.01)
        return service._call_groq_json("System prompt", "User prompt for TASK_A")

    async def run_task_b():
        # TASK B: Runs simultaneously, succeeds on primary key
        await asyncio.sleep(0.01)
        return service._call_groq_json("System prompt", "User prompt for TASK_B")

    with patch("app.core.config.settings.GROQ_API_KEY", MOCK_PRIMARY_KEY), \
         patch("app.core.config.settings.GROQ_BACKUP_API_KEY", MOCK_BACKUP_KEY), \
         patch("app.services.groq_service.ChatGroq", side_effect=mock_chatgroq_factory):
        
        res_a, res_b = await asyncio.gather(run_task_a(), run_task_b())
        
        # Verify Task A attempted primary then backup
        task_a_keys = [k for task, k in execution_log if task == "TASK_A"]
        assert task_a_keys == [MOCK_PRIMARY_KEY, MOCK_BACKUP_KEY]

        # Verify Task B used primary key exclusively and was never contaminated by Task A
        task_b_keys = [k for task, k in execution_log if task == "TASK_B"]
        assert task_b_keys == [MOCK_PRIMARY_KEY]


# ==============================================================================
# TEST 8: No API key appears in logs, exceptions, or responses
# ==============================================================================
def test_no_api_key_appears_in_logs_exceptions_or_responses():
    """Rule 8: Verify API keys and secrets are sanitized from all traces, exceptions, and returned error messages."""
    
    raw_error_text = f"Error: Failed to authenticate with key {MOCK_PRIMARY_KEY} and backup {MOCK_BACKUP_KEY} with Bearer eyJhbGciOiJIUzI1NiJ9.test"
    cleaned = sanitize_secret(raw_error_text)

    assert MOCK_PRIMARY_KEY not in cleaned
    assert MOCK_BACKUP_KEY not in cleaned
    assert "eyJhbGciOiJIUzI1NiJ9" not in cleaned
    assert "***REDACTED_API_KEY***" in cleaned
    assert "Bearer ***REDACTED***" in cleaned

    # Service-level verification:
    def mock_chatgroq_factory(**kwargs):
        raise Exception(f"Failed with key {MOCK_PRIMARY_KEY}")

    with patch("app.core.config.settings.GROQ_API_KEY", MOCK_PRIMARY_KEY), \
         patch("app.services.groq_service.ChatGroq", side_effect=mock_chatgroq_factory):
        service = GroqService()
        result = service.generate_rca_analysis(SAMPLE_DEV, allow_offline_fallback=True)
        assert MOCK_PRIMARY_KEY not in str(result)
        assert MOCK_BACKUP_KEY not in str(result)


# ==============================================================================
# TEST 9: No fallback can generate RCA findings after provider failure
# ==============================================================================
def test_no_fallback_can_generate_rca_findings_after_provider_failure():
    """Rule 9: Across ALL failure modes, no synthetic or dynamic findings may ever be generated."""
    failure_scenarios = [
        ("429 RateLimit Org", Exception("429: Organization TPD limit reached")),
        ("429 RateLimit Unknown", Exception("429: Rate limit exceeded")),
        ("401 Authentication", Exception("401: Invalid API Key")),
        ("403 Forbidden", Exception("403: Forbidden model access")),
        ("408 Timeout", Exception("408: Request timed out")),
        ("503 Service Outage", Exception("503: Service Unavailable")),
        ("Malformed JSON", Exception("Malformed JSON returned by model")),
    ]

    service = GroqService()
    for scenario_name, exc in failure_scenarios:
        with patch("app.core.config.settings.GROQ_API_KEY", MOCK_PRIMARY_KEY), \
             patch("app.core.config.settings.GROQ_BACKUP_API_KEY", None), \
             patch.object(service, "_call_groq_json", side_effect=exc):
            
            result = service.generate_rca_analysis(SAMPLE_DEV, allow_offline_fallback=True)
            
            assert result["five_whys"] == [], f"Failed on {scenario_name}"
            assert result["fishbone_causes"] == [], f"Failed on {scenario_name}"
            assert result["root_causes"] == [], f"Failed on {scenario_name}"
            assert result["capa_actions"] == [], f"Failed on {scenario_name}"
            assert result["evidence_gaps"] == [], f"Failed on {scenario_name}"
            assert result["status"] in ["QUOTA_BLOCKED", "AUTH_ERROR", "REQUEST_TIMEOUT", "AI_UNAVAILABLE"], f"Failed on {scenario_name}"


# ==============================================================================
# TEST 10: Primary credential success (No backup rotation)
# ==============================================================================
def test_primary_credential_success():
    """Primary credential succeeds; backup credential is never touched or invoked."""
    keys_used = []

    def mock_chatgroq_factory(**kwargs):
        key = kwargs.get("groq_api_key")
        keys_used.append(key)
        mock_instance = MagicMock()
        mock_bound = MagicMock()
        mock_instance.bind.return_value = mock_bound
        mock_resp = MagicMock()
        mock_resp.content = VALID_RCA_JSON
        mock_bound.invoke.return_value = mock_resp
        return mock_instance

    with patch("app.core.config.settings.GROQ_API_KEY", MOCK_PRIMARY_KEY), \
         patch("app.core.config.settings.GROQ_BACKUP_API_KEY", MOCK_BACKUP_KEY), \
         patch("app.services.groq_service.ChatGroq", side_effect=mock_chatgroq_factory):
        service = GroqService()
        result = service.generate_rca_analysis(SAMPLE_DEV, allow_offline_fallback=True)

        assert result["status"] == "SUCCESS"
        assert keys_used == [MOCK_PRIMARY_KEY]
        assert MOCK_BACKUP_KEY not in keys_used


# ==============================================================================
# TEST 11: Provider 5xx / Network failure handling
# ==============================================================================
def test_provider_5xx_network_failure():
    """Provider 5xx / connection error triggers bounded failure and returns AI_UNAVAILABLE."""
    keys_used = []

    def mock_chatgroq_factory(**kwargs):
        key = kwargs.get("groq_api_key")
        keys_used.append(key)
        mock_instance = MagicMock()
        mock_bound = MagicMock()
        mock_instance.bind.return_value = mock_bound
        mock_bound.invoke.side_effect = Exception("503 Service Unavailable: Groq inference gateway outage")
        return mock_instance

    with patch("app.core.config.settings.GROQ_API_KEY", MOCK_PRIMARY_KEY), \
         patch("app.core.config.settings.GROQ_BACKUP_API_KEY", MOCK_BACKUP_KEY), \
         patch("time.sleep"), \
         patch("app.services.groq_service.ChatGroq", side_effect=mock_chatgroq_factory):
        service = GroqService()
        result = service.generate_rca_analysis(SAMPLE_DEV, allow_offline_fallback=True)

        assert result["status"] == "AI_UNAVAILABLE"
        assert result["five_whys"] == []
        assert result["fishbone_causes"] == []
        assert result["root_causes"] == []
        assert result["capa_actions"] == []


# ==============================================================================
# TEST 12: AI cannot confirm a root cause (Human investigator restriction)
# ==============================================================================
def test_ai_cannot_confirm_root_cause():
    """Even if AI inference attempts to return CONFIRMED status, it is locked to PROPOSED."""
    payload_with_confirmed = {
        "status": "SUCCESS",
        "five_whys": [{"step_number": 1, "question": "Why?", "answer": "Valve stuck", "is_ai_suggested": True}],
        "fishbone_causes": [{"category": "MACHINE", "cause_description": "Valve stuck", "status": "CONFIRMED"}],
        "root_causes": [
            {
                "cause_statement": "Actuator diaphragm rupture",
                "category": "EQUIPMENT_FAILURE",
                "is_primary": True,
                "status": "CONFIRMED",
                "is_ai_suggested": True,
                "is_verified": True  # Unauthorized claim of verification
            }
        ],
        "capa_actions": [{"action_type": "CORRECTION", "description": "Replace diaphragm"}]
    }

    with patch("app.core.config.settings.GROQ_API_KEY", MOCK_PRIMARY_KEY), \
         patch("app.services.groq_service.ChatGroq") as mock_chat:
        mock_llm = MagicMock()
        mock_bound = MagicMock()
        mock_llm.bind.return_value = mock_bound
        mock_resp = MagicMock()
        mock_resp.content = json.dumps(payload_with_confirmed)
        mock_bound.invoke.return_value = mock_resp
        mock_chat.return_value = mock_llm

        service = GroqService()
        result = service.generate_rca_analysis(SAMPLE_DEV, allow_offline_fallback=True)

        for rc in result["root_causes"]:
            assert rc["status"] == "PROPOSED", "AI must never confirm a root cause"
            assert rc["is_verified"] is False, "AI cannot mark root cause as verified"
            assert rc["is_ai_suggested"] is True

        for fc in result["fishbone_causes"]:
            assert fc["status"] in ("HYPOTHESIS", "PROPOSED", "RULED_OUT")
            assert fc["status"] != "CONFIRMED"



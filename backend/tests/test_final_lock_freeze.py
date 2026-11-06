import pytest
import pytest_asyncio
import asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.future import select
from fastapi import HTTPException

from app.main import app
from app.core.config import settings
from app.core.database import get_db, Base
from app.models.audit import User, AiInteraction
from app.models.investigation import Investigation
from app.services.rate_limiter import ai_rate_limiter, investigation_concurrency_limiter, TokenBucketRateLimiter
from app.services.token_budget import estimate_tokens, truncate_text_to_token_budget, TokenBudgetManager
from app.services.groq_service import groq_service

@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

@pytest_asyncio.fixture(autouse=True)
async def reset_rate_limiters():
    ai_rate_limiter.reset()
    investigation_concurrency_limiter.reset()
    yield
    ai_rate_limiter.reset()
    investigation_concurrency_limiter.reset()

@pytest.mark.asyncio
async def test_auth_config_endpoint(client: AsyncClient):
    """Verify GET /api/v1/auth/config returns public config without leaking secrets."""
    res = await client.get("/api/v1/auth/config")
    assert res.status_code == 200
    data = res.json()
    assert "demo_login_enabled" in data
    assert "environment" in data
    assert "SECRET_KEY" not in str(data)
    assert "GROQ_API_KEY" not in str(data)

@pytest.mark.asyncio
async def test_demo_login_flow_allowed(client: AsyncClient, monkeypatch):
    """Verify POST /api/v1/auth/demo-login succeeds when enabled."""
    monkeypatch.setattr(settings, "ALLOW_DEMO_LOGIN", True)
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")

    # Investigator demo login
    res = await client.post("/api/v1/auth/demo-login", json={"persona": "investigator"})
    assert res.status_code == 200
    inv_data = res.json()
    assert "access_token" in inv_data
    assert inv_data["role"] == "INVESTIGATOR"
    assert inv_data["username"] == "lead_investigator"

    # QA Approver demo login
    res_qa = await client.post("/api/v1/auth/demo-login", json={"persona": "qa"})
    assert res_qa.status_code == 200
    qa_data = res_qa.json()
    assert "access_token" in qa_data
    assert qa_data["role"] == "QA_APPROVER"
    assert qa_data["username"] == "qa_director"

@pytest.mark.asyncio
async def test_demo_login_disabled_in_production(client: AsyncClient, monkeypatch):
    """Verify demo-login returns 403 Forbidden when environment is production or flag is False."""
    # When disabled
    monkeypatch.setattr(settings, "ALLOW_DEMO_LOGIN", False)
    res = await client.post("/api/v1/auth/demo-login", json={"persona": "investigator"})
    assert res.status_code == 403
    assert "disabled" in res.json()["detail"].lower()

    # When in production
    monkeypatch.setattr(settings, "ALLOW_DEMO_LOGIN", True)
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    res_prod = await client.post("/api/v1/auth/demo-login", json={"persona": "investigator"})
    assert res_prod.status_code == 403

@pytest.mark.asyncio
async def test_demo_login_invalid_persona(client: AsyncClient, monkeypatch):
    """Verify demo-login returns 400 for invalid persona names."""
    monkeypatch.setattr(settings, "ALLOW_DEMO_LOGIN", True)
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    res = await client.post("/api/v1/auth/demo-login", json={"persona": "hacker"})
    assert res.status_code == 400
    assert "Expected 'investigator' or 'qa'" in res.json()["detail"]

@pytest.mark.asyncio
async def test_no_qwen_in_candidates_and_model_resolution(monkeypatch):
    """Verify qwen/qwen3.8-27b is eliminated and fallback candidates are valid."""
    # Check candidates list in groq_service
    assert "qwen" not in groq_service.model.lower()
    available_models = ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "llama-3.3-70b-versatile"]
    monkeypatch.setattr(groq_service, "get_available_models", lambda: available_models)
    groq_service.model = "unknown-nonexistent-model"
    groq_service._resolve_model()
    assert groq_service.model in available_models
    assert "qwen" not in groq_service.model.lower()

@pytest.mark.asyncio
async def test_token_budget_character_estimator_and_trimming():
    """Verify token character estimator (chars / 3.5) and oldest history pruning."""
    sample_text = "A" * 350
    assert estimate_tokens(sample_text) == 100

    truncated, was_truncated = truncate_text_to_token_budget("B" * 3500, max_tokens=200)
    assert was_truncated is True
    assert "[... Source context truncated" in truncated

    # Test payload assembly and oldest history trimming
    history = [
        {"role": "user", "content": "Turn 1: " + "X" * 1000},
        {"role": "assistant", "content": "Turn 2: " + "Y" * 1000},
        {"role": "user", "content": "Turn 3: " + "Z" * 1000},
        {"role": "assistant", "content": "Turn 4: " + "W" * 500},
    ]
    payload = TokenBudgetManager.prepare_chat_payload(
        model_name="llama-3.3-70b-versatile",
        system_prompt="System instructions",
        sources_text="Source document excerpt",
        history=history,
        user_message="Current question from investigator"
    )
    assert payload["user_message"] == "Current question from investigator"
    assert len(payload["history"]) <= len(history)
    # Check that newest history is preserved over oldest
    if payload["history"]:
        assert payload["history"][-1]["content"].startswith("Turn 4")

@pytest.mark.asyncio
async def test_per_user_rate_limiter_exceed():
    """Verify token bucket rate limiter throws 429 with Retry-After header."""
    limiter = TokenBucketRateLimiter(per_minute=3, per_hour=10)
    user_id = 999
    await limiter.check_rate_limit(user_id)
    await limiter.check_rate_limit(user_id)
    await limiter.check_rate_limit(user_id)

    with pytest.raises(HTTPException) as exc_info:
        await limiter.check_rate_limit(user_id)

    assert exc_info.value.status_code == 429
    assert "Retry-After" in exc_info.value.headers
    assert int(exc_info.value.headers["Retry-After"]) >= 1

@pytest.mark.asyncio
async def test_investigation_concurrency_lock():
    """Verify concurrency limiter raises 409 when concurrent AI request runs for same investigation."""
    inv_id = 101
    async with investigation_concurrency_limiter.acquire(inv_id):
        # Attempt concurrent acquire
        with pytest.raises(HTTPException) as exc_info:
            async with investigation_concurrency_limiter.acquire(inv_id):
                pass
        assert exc_info.value.status_code == 409
        assert "AI is already working on this investigation" in exc_info.value.detail

    # Once released, acquire succeeds cleanly
    async with investigation_concurrency_limiter.acquire(inv_id):
        pass

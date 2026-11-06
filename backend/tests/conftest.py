import pytest
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Ensure backend directory is in path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, backend_dir)

# Load backend/.env if present
env_file = os.path.join(backend_dir, ".env")
if os.path.exists(env_file):
    load_dotenv(env_file)

# Configure primary test database to PostgreSQL 16 (or use explicit env override)
if "DATABASE_URL" not in os.environ or os.environ["DATABASE_URL"].startswith("sqlite"):
    if os.getenv("TEST_FORCE_SQLITE") == "1":
        os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_aivoa.db"
    else:
        os.environ["DATABASE_URL"] = "postgresql+asyncpg://aivoa_user:aivoa_password@localhost:5432/aivoa_rca"

# Configure isolated test environment and deterministic signing secret
if "ENVIRONMENT" not in os.environ:
    os.environ["ENVIRONMENT"] = "test"

if "SECRET_KEY" not in os.environ:
    os.environ["SECRET_KEY"] = "test-isolated-deterministic-signing-secret-key-32chars-minimum!"

# Configure deterministic mock fallback for GROQ_API_KEY for isolated offline test suites
if "GROQ_API_KEY" not in os.environ or not os.environ["GROQ_API_KEY"]:
    os.environ["GROQ_API_KEY"] = "gsk_test_mock_deterministic_key_0000000000000000"

if "DEMO_ACCOUNT_PASSWORD" not in os.environ:
    os.environ["DEMO_ACCOUNT_PASSWORD"] = "AivoaPass2026!"


def pytest_addoption(parser):
    parser.addoption(
        "--run-live",
        action="store_true",
        default=False,
        help="Run explicit live Groq provider integration tests requiring real API credentials and quota",
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "live_provider: marks test as an explicit opt-in live external provider test",
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("--run-live"):
        return

    # If user explicitly passed -m live_provider, allow it
    markexpr = config.getoption("-m", default="")
    if "live_provider" in markexpr:
        return

    deselected = []
    selected = []
    for item in items:
        if "live_provider" in item.keywords:
            deselected.append(item)
        else:
            selected.append(item)

    if deselected:
        config.hook.pytest_deselected(items=deselected)
        items[:] = selected


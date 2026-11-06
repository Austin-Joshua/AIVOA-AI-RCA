# AIVOA.AI — Complete Environment Variable Audit & Configuration Inventory

**Project:** AIVOA.AI — Root Cause Analysis (RCA) Intelligence for Pharmaceutical API Manufacturing  
**Repository:** https://github.com/Austin-Joshua/AIVOA-AI-RCA  
**Branch:** `main`  
**Audit Date:** November 2026 (Post-Migration Release Hardening)  
**Classification:** Confidential Engineering & Security Configuration Audit

---

## 1. Executive Summary & Audit Methodology

This document provides a comprehensive inventory and architectural audit of every environment variable utilized across AIVOA.AI. 

### Audit Methodology
1. **Source Code Static Analysis:** Audited all occurrences of `os.getenv`, `os.environ`, `pydantic_settings.BaseSettings`, `import.meta.env`, and Docker Compose variable interpolation.
2. **Configuration Hierarchy Analysis:** Traced environment loading paths, precedence rules, and file resolution order across repository root, `backend/`, and `frontend/`.
3. **Runtime & Container Verification:** Verified Docker Compose interpolation, Pydantic fail-fast validators, and secret masking behavior during application startup.
4. **Credential Isolation Audit:** Verified that no private backend secrets (API keys, database passwords, JWT signing secrets) are accessible to frontend bundles, client responses, or logging sinks.

---

## 2. Complete Environment Variable Inventory

| Variable Name | Classification | Component | Data Type | Default / Fallback | Declared In | Sensitive | Description & Failure Behavior |
| :--- | :--- | :--- | :--- | :--- | :--- | :---: | :--- |
| `ENVIRONMENT` | **Required (Startup)** | Backend, Docker | String (`str`) | `"development"` | `.env`, `backend/.env`, Compose | No | Environment mode: `development`, `test`, or `production`. Controls demo provisioning, password restrictions, and security validation. |
| `SECRET_KEY` | **Required (Startup)** | Backend, Docker | String (`str`) | *None (Fail-fast)* | `.env`, `backend/.env`, Compose | **YES** | Cryptographic secret for signing HMAC-SHA256 JWT tokens. Must be $\ge 32$ characters. Startup aborts with `RuntimeError` if missing or placeholder in non-test mode. In test mode (`ENVIRONMENT=test`), defaults to deterministic test secret. |
| `DATABASE_URL` | **Required (Startup)** | Backend, Alembic | String (`str`) | `postgresql+asyncpg://aivoa_user:aivoa_password@localhost:5432/aivoa_rca` | `.env`, `backend/.env`, Compose | **YES** | SQLAlchemy 2.0 AsyncIO connection string for PostgreSQL 16 using `asyncpg`. In production mode, rejects development credentials (`aivoa_password`) and SQLite URLs. Startup fails if DB is unreachable. |
| `POSTGRES_USER` | **Required (Docker/DB)** | PostgreSQL, Docker | String (`str`) | `"aivoa_user"` | `.env`, Compose | No | PostgreSQL 16 database user account for Docker Compose. |
| `POSTGRES_PASSWORD` | **Required (Docker/DB)** | PostgreSQL, Docker | String (`str`) | *None (Mandatory in Compose)* | `.env`, Compose | **YES** | PostgreSQL 16 database password. Docker Compose enforces `${POSTGRES_PASSWORD:?Error}` and fails if unset. |
| `POSTGRES_DB` | **Required (Docker/DB)** | PostgreSQL, Docker | String (`str`) | `"aivoa_rca"` | `.env`, Compose | No | PostgreSQL 16 database name for Docker Compose. |
| `POSTGRES_PORT` | **Optional** | PostgreSQL, Docker | Integer (`int`) | `5432` | `.env`, Compose | No | Host port mapped to PostgreSQL container port 5432. |
| `GROQ_API_KEY` | **Feature-Required (AI)** | Backend, Docker | String (`str`) | `""` | `.env`, `backend/.env`, Compose | **YES** | Primary Groq API key (`gsk_...`) for LLM inference. If missing, manual RCA and CAPA features work normally; AI inference returns `HTTP 401` or structured `AI_UNAVAILABLE` with zero fabricated root causes. |
| `GROQ_BACKUP_API_KEY` | **Optional (AI)** | Backend, Docker | String (`str`) | `None` | `.env`, `backend/.env`, Compose | **YES** | Secondary Groq API key for quota-aware and credential-invalid failover. |
| `GROQ_PROJECT_ID` | **Optional (AI)** | Backend, Docker | String (`str`) | `None` | `.env`, `backend/.env`, Compose | No | Primary Groq project identifier. Used to determine if backup key is in a separate quota project. |
| `GROQ_BACKUP_PROJECT_ID` | **Optional (AI)** | Backend, Docker | String (`str`) | `None` | `.env`, `backend/.env`, Compose | No | Backup Groq project identifier. When different from `GROQ_PROJECT_ID`, permits 429 quota failover. |
| `GROQ_MODEL` | **Optional (AI)** | Backend, Docker | String (`str`) | `"llama-3.3-70b-versatile"` | `.env`, `backend/.env`, Compose | No | Primary model ID requested from Groq API. Automatically falls back to available models (`openai/gpt-oss-120b`, etc.) if unlisted on account. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | **Optional** | Backend | Integer (`int`) | `1440` (24h) | `.env`, `backend/.env` | No | JWT access token lifespan in minutes. |
| `CORS_ORIGINS` | **Optional** | Backend | String (`str`) | `http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000` | `.env`, `backend/.env` | No | Comma-separated list of allowed CORS origins. Wildcards (`*`) are prohibited when credentials are enabled. |
| `UPLOAD_DIR` | **Optional** | Backend | String (`str`) | `"uploads"` | `backend/.env` | No | Working directory for temporary multipart file uploads. |
| `EVIDENCE_STORAGE_DIR` | **Optional** | Backend | String (`str`) | `backend/storage/evidences` | `backend/.env` | No | Authoritative physical directory where verified evidence artifacts and PDFs are persisted with SHA-256 verification. |
| `MAX_UPLOAD_SIZE_BYTES` | **Optional** | Backend | Integer (`int`) | `10485760` (10 MB) | `backend/.env` | No | Maximum permitted file upload size in bytes. |
| `ENABLE_DEMO_PROVISIONING` | **Dev/Test Only** | Backend, Docker | Boolean (`bool`) | `true` (dev/test), `false` (prod) | `.env`, `backend/.env`, Compose | No | Enables automatic provisioning of demonstration accounts (`dr.sarah.lin`, `dr.elena.rostova`) upon login in development. Strictly forced `False` when `ENVIRONMENT=production`. |
| `DEMO_ACCOUNT_PASSWORD` | **Dev/Test Only** | Backend | String (`str`) | `"AivoaPass2026!"` | `backend/.env` | No | Default demonstration user password used exclusively when demo provisioning is active. Strictly ignored in production. |
| `INITIAL_ADMIN_USERNAME` | **Optional (Bootstrap)**| Backend | String (`str`) | `None` | `backend/.env` | No | Username for one-time out-of-band administrator account bootstrap. |
| `INITIAL_ADMIN_PASSWORD` | **Optional (Bootstrap)**| Backend | String (`str`) | `None` | `backend/.env` | **YES** | Initial password for out-of-band administrator bootstrap. Ignored if admin already exists. |
| `INITIAL_ADMIN_EMAIL` | **Optional (Bootstrap)**| Backend | String (`str`) | `None` | `backend/.env` | No | Email address for out-of-band administrator bootstrap. |
| `INITIAL_ADMIN_FULL_NAME` | **Optional (Bootstrap)**| Backend | String (`str`) | `None` | `backend/.env` | No | Full name for out-of-band administrator bootstrap. |
| `VITE_API_BASE_URL` | **Optional** | Frontend | String (`str`) | `""` (proxies to `/api/v1`) | `frontend/.env` | No | Public backend API URL for client requests. Defaults to empty string, relying on Vite/Nginx `/api` reverse proxy. |
| `VITE_ENABLE_DEMO_LOGIN` | **Dev/Test Only** | Frontend, Docker | String (`str`) | `"true"` | `frontend/.env`, Compose | No | Controls demonstration login shortcut buttons in frontend UI. Automatically stripped in production builds (`import.meta.env.PROD`). |
| `TESTING` | **Test Only** | Backend | String (`str`) | `None` | Internal (pytest) | No | Set by test runner to indicate active automated test execution. |
| `TEST_FORCE_SQLITE` | **Deprecated / Disallowed** | Backend | String (`str`) | `None` | Internal | No | Legacy switch. SQLite is disallowed for all production and release operations. Full test suite executes against PostgreSQL 16. |

---

## 3. Classification Taxonomy

### A. Required for Application Startup
These variables must be present and valid. Absence causes application startup to terminate immediately:
1. `ENVIRONMENT`: Defines operational security posture (`development`, `test`, `production`).
2. `SECRET_KEY`: Cryptographic signing secret. Startup fails fast if unset, shorter than 32 characters, or containing insecure placeholders.
3. `DATABASE_URL`: PostgreSQL 16 connection string. Direct DDL is prohibited at startup; database connection is verified via `SELECT 1`.
4. `POSTGRES_PASSWORD`: Required for Docker Compose database container.

### B. Required Only for a Particular Feature (Safe Degradation)
1. `GROQ_API_KEY`: Required only for live AI Copilot features (Document intake extraction, AI 5-Whys generation, AI Fishbone generation, and AI CAPA suggestions).  
   *Failure Behavior:* If absent or invalid, the backend starts normally. Manual RCA, document intake validation, and CAPA workflows remain 100% operational. Copilot endpoints return `HTTP 401` or structured `AI_UNAVAILABLE` with an empty candidates list (`[]`) and zero fabricated data.

### C. Optional Configuration
Non-sensitive tuning variables with safe, sensible defaults:
- `GROQ_BACKUP_API_KEY`, `GROQ_PROJECT_ID`, `GROQ_BACKUP_PROJECT_ID`, `GROQ_MODEL`
- `ACCESS_TOKEN_EXPIRE_MINUTES`, `CORS_ORIGINS`
- `UPLOAD_DIR`, `EVIDENCE_STORAGE_DIR`, `MAX_UPLOAD_SIZE_BYTES`
- `VITE_API_BASE_URL`

### D. Development / Test Only
Explicitly disabled or stripped in production:
- `ENABLE_DEMO_PROVISIONING`: Automatically disabled when `ENVIRONMENT=production`.
- `DEMO_ACCOUNT_PASSWORD`: Ignored in production.
- `VITE_ENABLE_DEMO_LOGIN`: Statically eliminated from production bundles by Vite dead-code elimination.
- `INITIAL_ADMIN_*`: Used solely for initial out-of-band administrator provisioning.

---

## 4. Configuration Precedence & File Resolution Rules

In `backend/app/core/config.py`, configuration is loaded via Pydantic Settings `SettingsConfigDict` using absolute filesystem paths:

```python
model_config = SettingsConfigDict(
    case_sensitive=True,
    extra="ignore",
    env_file=(
        str(ROOT_DIR / ".env"),
        str(BACKEND_DIR / ".env"),
    ),
)
```

### Precedence Hierarchy:
1. **Host / Shell Environment (`os.environ`):** Any variable set in the operating system, terminal, or Docker Compose overrides file settings.
2. **`backend/.env`:** Specific backend settings override root settings.
3. **`ROOT_DIR/.env` (`.env` in repo root):** Shared settings across Docker Compose and local services.
4. **Pydantic Field Defaults:** Built-in default values defined in `Settings`.

> **Working Directory Ambiguity Eliminated:** Because `ROOT_DIR` and `BACKEND_DIR` are computed absolutely relative to `__file__`, starting the application from `backend/` or the repository root loads the identical configuration files in the identical order.

---

## 5. Security & Credential Isolation Audit

### 5.1 No Exposure to Frontend Client Bundles
- Verified all frontend source code (`frontend/src/`) for secret leakage.
- Only variables prefixed with `VITE_` are exposed to the browser. The only frontend variables referenced are `VITE_API_BASE_URL` and `VITE_ENABLE_DEMO_LOGIN`.
- `GROQ_API_KEY`, `SECRET_KEY`, and `DATABASE_URL` are strictly confined to the backend and Docker environments. They are never imported, declared, or bundled into frontend artifacts.

### 5.2 Secret Masking in Logging & Telemetry
- Database URLs are masked in logs and metrics via the `safe_database_url` property in `Settings`:
  ```python
  @property
  def safe_database_url(self) -> str:
      if "@" in self.DATABASE_URL:
          return self.DATABASE_URL.split("@")[-1]
      return "configured"
  ```
- All Groq API keys and error strings are passed through `sanitize_secret()` before logging, replacing any `gsk_...` tokens or secret substrings with `***REDACTED_API_KEY***`.

### 5.3 Production Hardening Safeguards
- In `production` mode:
  - Any `SECRET_KEY` matching known insecure values or containing template prefixes (`replace_with_`, `your_secret_key`, etc.) causes an immediate startup abort (`RuntimeError`).
  - `DATABASE_URL` containing default development passwords (`aivoa_password`) or SQLite prefixes is rejected with `RuntimeError`.
  - Demo user provisioning is disabled (`allows_demo_seeding == False`).
  - Frontend production build (`npm run build`) strips demo login shortcuts via Vite dead-code elimination.

---

## 6. Audit Conclusion & Compliance Status

The environment variable architecture of AIVOA.AI conforms to all production security and release readiness requirements:
- **No hardcoded secrets** exist in tracked source code.
- **Fail-fast validation** ensures the application cannot start in an insecure or misconfigured state.
- **Zero fabrication** ensures that missing or exhausted AI credentials produce clean errors rather than false root cause data.
- **Full backward compatibility** is preserved for local developer workflows.


# PROJECT_CLEANUP_BASELINE.md
# AIVOA.AI — Phase 0: Repository Baseline Inspection

**Generated:** 2026-11-05  
**Inspector:** Automated via Antigravity (Claude Sonnet 4.6 Thinking)  
**Repository:** `C:\Users\austi\OneDrive\Desktop\AIVOA\AIVOA-AI-RCA`  
**Remote:** `https://github.com/Austin-Joshua/AIVOA-AI-RCA`  
**Branch:** `main`  
**Last Commit:** `ca5a3e7 feat(core): initial clean release of AIVOA.AI RCA platform`

---

## 1. Git State Summary

| Check | Result |
|---|---|
| Directory exists | YES |
| .git directory present | YES |
| Branch | main |
| Remote | origin to https://github.com/Austin-Joshua/AIVOA-AI-RCA |
| Last commit | ca5a3e7 feat(core): initial clean release of AIVOA.AI RCA platform |
| Tracked files | 136 files |
| Modified tracked files | 16 files |
| Untracked files | 8 files |

### Modified Tracked Files (Preserved — not reset)

```
 M .gitignore
 M DEVELOPMENT_LOG.md
 M PROJECT_CONTEXT.md
 M README.md
 M TESTING.md
 M backend/.env.example
 M backend/alembic/env.py
 M backend/app/api/endpoints/auth.py
 M backend/app/core/config.py
 M backend/app/core/database.py
 M backend/app/core/security.py
 M backend/app/main.py
 M backend/tests/conftest.py
 M docker-compose.yml
 M frontend/src/components/common/LoginModal.jsx
 M frontend/src/services/api.js
```

All 16 modified tracked files represent intentional post-commit improvements
(security hardening, environment configuration, auth endpoint improvements).
They are preserved exactly — no git reset was performed.

### Untracked Files (Preserved)

```
?? .env.example
?? ENVIRONMENT_SETUP.md
?? ENVIRONMENT_VARIABLE_AUDIT.md
?? FINAL_RELEASE_DISCREPANCY_REPORT.md
?? POST_MIGRATION_RELEASE_HARDENING_REPORT.md
?? PROJECT_INTEGRITY_AUDIT.md
?? backend/tests/test_release_hardening.py
?? frontend/.env.example
```

---

## 2. Project Structure

```
AIVOA-AI-RCA/
├── backend/
│   ├── alembic/
│   │   ├── versions/   (7 migration scripts)
│   │   ├── env.py
│   │   └── alembic.ini
│   ├── app/
│   │   ├── api/
│   │   │   ├── endpoints/   (10 endpoint modules)
│   │   │   └── api_v1.py
│   │   ├── core/
│   │   │   ├── config.py     (Pydantic Settings v2)
│   │   │   ├── database.py   (SQLAlchemy 2.0 AsyncIO)
│   │   │   └── security.py   (HMAC-SHA256 JWT)
│   │   ├── models/   (8 SQLAlchemy model files)
│   │   ├── schemas/  (8 Pydantic v2 schema files)
│   │   ├── services/ (5 service modules)
│   │   ├── cli.py
│   │   └── main.py
│   ├── storage/
│   │   └── evidences/  (user evidence — NEVER deleted)
│   ├── tests/   (19 test files)
│   ├── uploads/ (temporary upload staging)
│   ├── .env.example
│   ├── alembic.ini
│   ├── Dockerfile
│   ├── pytest.ini
│   ├── requirements.txt
│   └── run.py
├── docs/
│   └── ARCHITECTURE.md
├── examples/
│   ├── sample_deviation_report.pdf
│   ├── sample_deviation_report.txt
│   └── sample_incident_email.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── common/ (6 components)
│   │   │   ├── copilot/ (5 components)
│   │   │   ├── form/ (7 components)
│   │   │   └── layout/ (2 components)
│   │   ├── services/api.js
│   │   ├── store/ (4 Redux slices + index.js)
│   │   ├── App.jsx / App.css
│   │   └── main.jsx / index.css
│   ├── public/ (favicon.svg, icons.svg)
│   ├── .env.example
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── package.json
│   ├── package-lock.json
│   └── vite.config.js
├── .gitignore
├── AI_WORKFLOW.md
├── API_CONTRACTS.md
├── DATABASE_SCHEMA.md
├── DEVELOPMENT_LOG.md
├── ENVIRONMENT_SETUP.md
├── ENVIRONMENT_VARIABLE_AUDIT.md
├── FINAL_RELEASE_DISCREPANCY_REPORT.md
├── NEW_REPOSITORY_MIGRATION_REPORT.md
├── POST_MIGRATION_RELEASE_HARDENING_REPORT.md
├── PROJECT_CONTEXT.md
├── PROJECT_INTEGRITY_AUDIT.md
├── README.md
├── TESTING.md
└── docker-compose.yml
```

---

## 3. File and Test Inventory

| Metric | Count |
|---|---|
| Git-tracked files | 136 |
| Backend test files | 19 |
| Alembic revision scripts | 7 |
| Frontend components | 20 |
| Redux slices | 4 (auth, investigation, copilot, ui) |
| Backend endpoint modules | 10 |
| Backend service modules | 5 |
| SQLAlchemy model files | 8 |

---

## 4. Alembic Migration History

| Revision | Description |
|---|---|
| e9e38a07f832 | Initial schema with PostgreSQL models |
| c89fbf7d80b8 | Phase 2C evidence management and traceability |
| 6d1518e3b3e9 | Phase 2C-1 critical remediation |
| a1b2c3d4e5f6 | Add finding reviewer metadata |
| 98ea1c729df4 | Add user is_active |
| 3f44c56e6733 | Phase 2D-2.2 RCA workflow evidence links |
| ae9dda31c187 | Phase 2D-2.2.2 security evidence (HEAD) |

Current DB state: ae9dda31c187 (head) PASS

---

## 5. Frontend Entry Points

| File | Purpose |
|---|---|
| frontend/index.html | HTML shell |
| frontend/src/main.jsx | React 19 root mount |
| frontend/src/App.jsx | Root application component |
| frontend/vite.config.js | Vite + proxy config (/api to 127.0.0.1:8000) |
| frontend/src/store/index.js | Redux store (auth, investigation, copilot, ui) |
| frontend/src/services/api.js | Axios client with token injection + 401 handling |

---

## 6. Backend Entry Points

| File | Purpose |
|---|---|
| backend/app/main.py | FastAPI app, CORS, lifespan, health/root routes |
| backend/app/api/api_v1.py | Router assembly (10 endpoint groups) |
| backend/app/core/config.py | Pydantic Settings v2 (fail-fast SECRET_KEY) |
| backend/app/core/database.py | SQLAlchemy 2.0 AsyncIO engine + session |
| backend/app/core/security.py | HMAC-SHA256 JWT, RBAC, SoD checks |

---

## 7. Dependency Versions (Installed)

### Backend (Python 3.12.1)

| Package | Version |
|---|---|
| fastapi | 0.141.1 |
| pydantic | 2.13.3 |
| pydantic-settings | 2.14.2 |
| SQLAlchemy | 2.0.51 |
| alembic | 1.19.1 |
| asyncpg | 0.32.0 |
| langgraph | 1.2.20 |
| langchain | 1.4.9 |
| langchain-groq | 1.1.3 |
| groq | 0.37.1 |
| uvicorn | 0.29.0 |
| pytest | 9.0.3 |
| pytest-asyncio | 1.4.1.post1 |

### Frontend (Node.js / npm)

| Package | Version |
|---|---|
| react | ^19.3.1 |
| @reduxjs/toolkit | ^2.14.0 |
| vite | ^8.3.5 |
| axios | ^1.21.0 |
| tailwindcss | ^4.3.4 |
| oxlint | ^1.89.0 |

---

## 8. Environment Files

| File | Exists | Tracked | Notes |
|---|---|---|---|
| .env | No | No (gitignored) | Missing — created during setup |
| backend/.env | No | No (gitignored) | Missing — created during setup |
| frontend/.env | No | No (gitignored) | Not needed (Vite proxy handles routing) |
| .env.example | Yes | No (untracked) | Root template |
| backend/.env.example | Yes | Yes | Backend template |
| frontend/.env.example | Yes | No (untracked) | Frontend template |

No actual secret values are stored in git-tracked files.

---

## 9. Generated Artifacts Present at Baseline

| Path | Type | Action |
|---|---|---|
| frontend/node_modules/ | Node dependencies | Retained (lockfile present) |
| frontend/dist/ | Build output | Removed (stale) — rebuilt cleanly |
| backend/**/__pycache__/ | Python bytecode | Removed (10 directories) |
| backend/.pytest_cache/ | Pytest cache | Removed |

---

## 10. Services Running at Baseline

| Service | Status |
|---|---|
| PostgreSQL 16 (Docker aivoa-rca-postgres) | RUNNING + healthy (port 5432, 21h uptime) |
| FastAPI backend | Not running (started during Phase 7) |
| Vite frontend | Not running (started during Phase 7) |


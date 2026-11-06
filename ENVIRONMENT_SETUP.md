# AIVOA.AI — Environment Configuration & Local Setup Guide

**Project:** AIVOA.AI — Root Cause Analysis (RCA) Intelligence for Pharmaceutical API Manufacturing  
**Repository:** https://github.com/Austin-Joshua/AIVOA-AI-RCA  
**Branch:** `main`  
**Target Operating Systems:** Windows 10/11 (PowerShell 5.1 / 7+), Linux / macOS (bash / zsh)  
**Mandatory Stack:** React 19 + Redux Toolkit + Vite | FastAPI + Uvicorn | PostgreSQL 16 | SQLAlchemy 2.0 AsyncIO + asyncpg | Alembic | LangGraph + Groq API

---

## 1. Prerequisites

Before setting up the project, ensure the following runtimes and tools are installed:

| Tool | Minimum Version | Verification Command |
| :--- | :--- | :--- |
| **Python** | 3.12 (64-bit) | `py -3.12 --version` or `python --version` |
| **Node.js** | 18.x LTS or 20.x | `node --version` |
| **npm** | 9.x or 10.x | `npm --version` |
| **Docker Desktop** | Compose v2 | `docker compose version` |
| **Git** | 2.40+ | `git --version` |

---

## 2. Environment Architecture & Precedence

AIVOA.AI uses a layered environment configuration architecture managed by Pydantic Settings (`pydantic-settings` 2.x):

```
+-------------------------------------------------------------------------+
|                  1. System / Shell Environment Variables                |
|                  ($env:VAR in PowerShell / export VAR in Linux)         |
|                          (HIGHEST PRECEDENCE)                           |
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
|                       2. backend/.env (Backend-Specific)                |
|              Overrides base values for backend-focused operations        |
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
|                         3. .env (Repository Root)                       |
|           Supplies shared base variables (Docker Compose & default)     |
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
|                   4. Codebase Defaults (Pydantic Settings)              |
|        Safe non-sensitive defaults (Port numbers, timeouts, paths)      |
|                           (LOWEST PRECEDENCE)                           |
+-------------------------------------------------------------------------+
```

> **Security Rule:** Never commit `.env` or `backend/.env` files into Git. Both are strictly excluded in `.gitignore`. Templates (`.env.example`, `backend/.env.example`, `frontend/.env.example`) provide safe placeholders only.

---

## 3. Step-by-Step Local Setup (PowerShell)

### Step 3.1 — Clone & Open Repository

```powershell
cd C:\Users\austi\OneDrive\Desktop\AIVOA\AIVOA-AI-RCA
```

### Step 3.2 — Configure Root Environment (`.env`)

Copy the template to `.env` in the repository root:

```powershell
Copy-Item .env.example .env
```

Open `.env` in your text editor and set:
1. `POSTGRES_PASSWORD`: Choose a secure password for PostgreSQL (e.g. `DevSecretPass2026!`).
2. `SECRET_KEY`: Generate a cryptographically secure random key (see Step 3.3).
3. `GROQ_API_KEY`: Supply your personal Groq API key (`gsk_...`).

### Step 3.3 — Generate Cryptographic Secret Key

`SECRET_KEY` is mandatory for non-test startup. It must be at least 32 characters in length and cannot use known placeholders.

**Generate using Python (Recommended):**
```powershell
py -3.12 -c "import secrets; print(secrets.token_urlsafe(32))"
```

**Generate using pure PowerShell:**
```powershell
$bytes = New-Object byte[] 32
[System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
[Convert]::ToBase64String($bytes)
```

Paste this string as `SECRET_KEY` in your `.env` (and `backend/.env` if used).

### Step 3.4 — Configure Backend Environment (`backend/.env`)

Copy the backend template:

```powershell
Copy-Item backend\.env.example backend\.env
```

Ensure the database URL matches your PostgreSQL credentials:
```ini
ENVIRONMENT=development
DATABASE_URL=postgresql+asyncpg://aivoa_user:DevSecretPass2026!@localhost:5432/aivoa_rca
SECRET_KEY=your_generated_cryptographically_secure_key_here_32_chars_min
GROQ_API_KEY=gsk_your_primary_groq_key_here
GROQ_BACKUP_API_KEY=
GROQ_MODEL=llama-3.3-70b-versatile
```

---

## 4. Starting the PostgreSQL 16 Database

### Option A: Using Docker Compose for Database Only (Recommended)

Start an isolated PostgreSQL 16 Alpine container:

```powershell
docker compose up -d db
```

Verify the database container is healthy:
```powershell
docker compose ps
```
*Expected status: `aivoa-rca-postgres` running and `healthy` on port `5432`.*

### Option B: Using Existing Native PostgreSQL 16

If running PostgreSQL locally without Docker, ensure the database and user exist:

```sql
CREATE USER aivoa_user WITH PASSWORD 'DevSecretPass2026!';
CREATE DATABASE aivoa_rca OWNER aivoa_user;
GRANT ALL PRIVILEGES ON DATABASE aivoa_rca TO aivoa_user;
```

---

## 5. Applying Database Migrations (Alembic)

> **Important:** Application startup no longer creates database tables silently via `Base.metadata.create_all()`. Schema initialization and updates are exclusively managed by Alembic.

Run the migration command from the `backend/` directory:

```powershell
cd backend
py -3.12 -m alembic upgrade head
```

Verify migration status:
```powershell
py -3.12 -m alembic current
```
*Expected output: `ae9dda31c187 (head)`*

To return to the repository root:
```powershell
cd ..
```

---

## 6. Backend Setup & Startup

### Step 6.1 — Install Backend Dependencies

```powershell
py -3.12 -m pip install -r backend\requirements.txt
```

### Step 6.2 — Start FastAPI Development Server

Run Uvicorn from the `backend/` directory:

```powershell
cd backend
py -3.12 -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Step 6.3 — Verify Backend Health

In a separate PowerShell window:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```
*Expected response:*
```json
{
  "status": "healthy",
  "app": "AIVOA.AI – RCA Intelligence",
  "version": "1.0.0",
  "database": "connected"
}
```

Check the authentication configuration:
```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/auth/config
```
*Expected response in development:*
```json
{
  "environment": "development",
  "demo_login_enabled": true
}
```

---

## 7. Frontend Setup & Startup

### Step 7.1 — Install Frontend Dependencies

```powershell
cd frontend
npm ci
```

### Step 7.2 — Configure Frontend Environment (Optional)

In local development, Vite proxies `/api` requests to `http://127.0.0.1:8000` automatically. You do **not** need a `frontend/.env` file unless you are serving the backend on a different port.

If custom configuration is needed:
```powershell
Copy-Item .env.example .env
```

Available frontend variables:
- `VITE_API_BASE_URL`: Public backend API base URL (defaults to `/api/v1`).
- `VITE_ENABLE_DEMO_LOGIN`: Set to `false` if you wish to hide demonstration account buttons in local development. *(In production builds, demo buttons are automatically eliminated by Vite dead-code elimination regardless of this setting).*

### Step 7.3 — Start Vite Development Server

```powershell
npm run dev
```
*Expected output: Local development server active at `http://localhost:5173/`.*

### Step 7.4 — Build Frontend for Production

To verify the production build:
```powershell
npm run build
```
*Expected output: Clean compilation in `< 1.5s` with zero errors.*

---

## 8. Full Docker Compose Deployment (Alternative)

To run the complete stack (PostgreSQL + FastAPI + React/Nginx) in Docker:

1. Ensure `.env` is configured in the repository root (see Step 3.2).
2. Start all services:
   ```powershell
   docker compose up --build
   ```
3. Once running, apply migrations inside the backend container:
   ```powershell
   docker compose exec backend alembic upgrade head
   ```
4. Access the application:
   - Frontend: `http://localhost:5173`
   - Backend API: `http://localhost:8000/docs`
   - Health: `http://localhost:8000/health`

---

## 9. Running Automated Tests

### 9.1 — Full Deterministic Backend Test Suite (164 Tests)

Executes all unit, integration, workflow, authorization, and migration tests against PostgreSQL 16 without consuming Groq quota:

```powershell
py -3.12 -m pytest backend/tests -m "not live_provider" -v
```
*Expected result: 164 passed, 2 deselected, 0 failed.*

### 9.2 — Release Hardening Security Suite (13 Tests)

Verifies configuration fail-fast checks, database lifecycle guards, and demo login isolation:

```powershell
py -3.12 -m pytest backend/tests/test_release_hardening.py -v
```
*Expected result: 13 passed, 0 failed.*

### 9.3 — PostgreSQL 16 & Migration Verification Suite (3 Tests)

Verifies PostgreSQL 16 connectivity, Alembic schema state, and async entity persistence:

```powershell
py -3.12 -m pytest backend/tests/test_postgres_database.py -v
```
*Expected result: 3 passed, 0 failed.*

### 9.4 — Opt-In Live Groq API Test (Consumes Quota)

To verify genuine live inference with your personal Groq API key:

```powershell
py -3.12 -m pytest backend/tests -m live_provider --run-live -v
```

---

## 10. Missing Credentials & Safe Failure Behavior

| Scenario | System Behavior |
| :--- | :--- |
| **Missing or Default `SECRET_KEY` (Non-test)** | Backend startup aborts immediately (`RuntimeError`) with a clear error message. Never starts with insecure defaults. |
| **Missing `DATABASE_URL`** | Backend connects to default local PostgreSQL; fails at startup if PostgreSQL is unavailable. Direct DDL in production raises `RuntimeError`. |
| **Missing `GROQ_API_KEY`** | Application starts normally. Manual RCA tools, document intake validation, and CAPA workflows remain 100% operational. Copilot AI analysis endpoints return `HTTP 401` or structured `status: "AI_UNAVAILABLE"` with zero hallucinated root causes. |
| **Groq Rate Limit (429)** | AI endpoints return `HTTP 429` with clear retry guidance. Multi-key failover attempts backup key only if separate projects are configured (`GROQ_PROJECT_ID` $\neq$ `GROQ_BACKUP_PROJECT_ID`). |
| **Production Mode (`ENVIRONMENT=production`)** | Demo login buttons, demo accounts, and development database passwords (`aivoa_password`) are strictly rejected and disabled. |

---

## 11. Engineering Prototype Scope & Regulatory Notice

> **Important Regulatory Classification:**  
> AIVOA.AI is an **engineering decision-support prototype** developed to demonstrate AI-augmented root cause analysis for pharmaceutical API manufacturing deviations.
> 
> While the codebase incorporates strict data integrity technical controls (immutable audit logging, attributable electronic sign-offs, separation of duties, and verification barriers), it has **not** undergone formal Computer System Validation (CSV), GAMP 5 life-cycle certification, or formal 21 CFR Part 11 regulatory compliance audits. It is not approved for autonomous batch release decisions or commercial pharmaceutical manufacturing release.


# AIVOA.AI – RCA Intelligence Module
### AI-Assisted Root Cause Analysis (RCA) Decision-Support Prototype for Pharmaceutical API Manufacturing

A specialized engineering decision-support prototype platform designed to assist pharmaceutical quality investigators and QA/QC teams during Root Cause Analysis (RCA) and Corrective & Preventive Action (CAPA) formulation for Active Pharmaceutical Ingredient (API) manufacturing deviations.

> [!IMPORTANT]
> **Engineering Decision-Support Prototype Notice:**  
> AIVOA.AI is engineered strictly as an investigator-controlled decision-support prototype. The platform **does not claim 21 CFR Part 11 compliance, GMP certification, or formal Computer System Validation (CSV)**. While its architecture incorporates technical data governance controls aligned with cGMP principles (FDA 21 CFR Part 211, ICH Q9 Quality Risk Management, ICH Q10 Pharmaceutical Quality System) and electronic record data integrity concepts (audit logs, role-based authorization, checksums, separation of duties), it provides computational recommendations under human oversight. Any production deployment in a regulated environment requires formal computerized system validation, qualification protocols (IQ/OQ/PQ), and organizational standard operating procedures (SOPs).

---

## 1. Technology Architecture

- **Frontend**: React 19, Redux Toolkit 2.x, Tailwind CSS v4, Lucide React, Vite (production builds exclude demonstration shortcuts)
- **Backend**: Python 3.12, FastAPI, Pydantic v2 (fail-fast configuration without hardcoded secret fallbacks)
- **AI Orchestration**: LangGraph (`StateGraph` with 13-node investigation pipeline and conditional routing)
- **LLM Inference**: Groq API (`ChatGroq`) with active model `llama-3.3-70b-versatile`, project-scoped quota failover, and zero-fabrication graceful degradation
- **Database**: PostgreSQL 16 (SQLAlchemy 2.0 AsyncIO with asyncpg; mandatory fail-fast enforcement; authoritative Alembic migration versioning; application startup verifies connectivity without executing DDL or silent migrations)
- **Security & Integrity**: Role-Based Access Control (`INVESTIGATOR`, `QA_APPROVER`, `ADMIN`), NIST PBKDF2-HMAC-SHA256 password hashing, HMAC-SHA256 bearer tokens, fail-fast configuration validation (minimum 32-character high-entropy `SECRET_KEY`), demo account production isolation, and immutable audit trails.

---

## 2. Core Business Workflow

```
Incident Intake (PDF / Email / Text)
       ↓
Automated AI Extraction & Grounded Citation Verification (Human Acceptance Gate)
       ↓
Investigation & Evidence Dossier (SHA-256 Checksums, Verification Separation of Duties)
       ↓
5 Whys Causality Cascade & Ishikawa 6Ms Fishbone Analysis (Evidence-Linked Barriers)
       ↓
Root Cause Proposal Synthesis (Locked to PROPOSED; Provenance Serialization via Row Locks)
       ↓
Human Review, Editing & QA Independent Sign-Off (Role-Enforced; Separation of Duties)
```

---

## 3. Two-Panel Enterprise Interface Pattern

### **LEFT PANEL: Structured RCA Investigation Dossier**
1. **Deviation Identification & Manufacturing Context**:
   - Deviation number, severity classification, unit operation (e.g., Crystallization, Centrifugation, Vacuum Drying), equipment ID (e.g., RX-301), batch number, product name, target vs actual yield (kg).
   - Technical deviation narrative and immediate quarantine/containment actions.
   - Clear visual distinction: **AI Suggested (Pending Verification)** vs **Investigator Verified**.
2. **5 Whys Root Cause Methodology**:
   - Dynamic-depth causality cascade (not restricted to 5 steps) with supporting evidence citations.
   - Verification barrier: Why steps cannot be marked verified without supporting verified evidence.
   - Provenance concurrency guard: Active root cause dependencies block step deletion.
3. **Ishikawa Fishbone Diagram (6Ms Analysis)**:
   - Evaluates **Man**, **Machine**, **Material**, **Method**, **Measurement**, and **Milieu**.
   - Interactive status lifecycle: **Hypothesis**, **Verified**, **Ruled Out**.
   - Concurrency-safe promotion: Promotes verified causes into formal `RootCause` proposals (`status="PROPOSED"`).
4. **Synthesized Root Cause & Contributing Factors**:
   - Primary Root Cause vs Secondary Contributing Factors with provenance tracking (`FIVE_WHYS`, `FISHBONE`, `DIRECT_SYNTHESIS`, `MANUAL`).
   - Confirmation barrier: Requires `QA_APPROVER` or `ADMIN` role, $\ge 1$ verified supporting evidence, zero active contradictions, and lead investigator self-confirmation prevention.
5. **CAPA Program**:
   - **Corrections** (Immediate Containment)
   - **Corrective Actions** (Eliminate Root Cause)
   - **Preventive Actions** (Facility-wide Prevention)
   - Accountable **Owners**, **Deadlines**, and **Effectiveness Verification Criteria**.
6. **Immutable Audit Trail Viewer**:
   - Audit trail viewer recording every insert, update, verification, and sign-off with timestamps and actor attribution.

### **RIGHT PANEL: AI Investigation Copilot**
1. **Document Intake Tab**:
   - PDF upload, pasted text, and RFC 5322 email parsing.
   - Multi-parameter extraction with verbatim continuous citation checking (`SOURCE_FACT`, `AI_INFERENCE`, `MISSING`, `CONFLICTING`).
2. **Evidence Gaps Tab**:
   - Automated detection of missing empirical data (calibration records, raw material CoAs, shift handover logs).
   - Structured investigator clarification questions with explicit resolution tracking.
3. **RCA & CAPA Engine Tab**:
   - Generation of 5-Whys causality, Fishbone hypotheses, and CAPA proposals via Groq API.
   - Non-fabrication guard: AI proposals initialize strictly as `status="PROPOSED"` (`is_verified=False`).
   - Granular itemized review (`apply-rca-item`) prevents bulk overwriting of investigator entries.
4. **Copilot Chat Tab**:
   - Interactive investigation assistant. In offline/quota exhaustion states, provides clear notifications without synthetic hallucinations.
5. **LangGraph Workflow Trace Tab**:
   - Live visual monitor of the compiled 13-node investigation StateGraph.

---

## 4. Getting Started & Local Execution

### Prerequisites
- Python 3.12+
- Node.js 18+ and npm
- Docker (for PostgreSQL 16 container)

---

### 5-Step Local Execution Workflow

Follow these five steps to run the complete stack locally from repository root:

```bash
# Step 1: Start PostgreSQL 16 container
docker compose up -d db

# Step 2: Apply authoritative Alembic migrations
cd backend && python -m alembic upgrade head && cd ..

# Step 3: Start FastAPI backend server (port 8000)
cd backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# Step 4: In a new terminal, install dependencies and start Vite frontend (port 5173)
cd frontend && npm install && npm run dev

# Step 5: Open your web browser and navigate to:
# http://127.0.0.1:5173
```

---

### Environment Variables Specification

Both `.env` files are git-ignored. Template files are provided at `.env.example` and `backend/.env.example`.
All values below are descriptive placeholders. **Never commit real secrets or credentials.**

| Variable | Scope | Description | Default / Example Placeholder | Required |
|---|---|---|---|---|
| `POSTGRES_SERVER` | Backend & Docker | PostgreSQL hostname or container address | `127.0.0.1` | Yes |
| `POSTGRES_PORT` | Backend & Docker | PostgreSQL listening port | `5432` | Yes |
| `POSTGRES_DB` | Backend & Docker | PostgreSQL database catalog name | `aivoa_rca` | Yes |
| `POSTGRES_USER` | Backend & Docker | PostgreSQL database user | `aivoa_user` | Yes |
| `POSTGRES_PASSWORD` | Backend & Docker | Local database password | `<your_secure_db_password>` | Yes |
| `DATABASE_URL` | Backend | SQLAlchemy asyncpg connection URI | `postgresql+asyncpg://aivoa_user:<password>@127.0.0.1:5432/aivoa_rca` | Yes |
| `SECRET_KEY` | Backend | HMAC-SHA256 session token signing key ($\ge 32$ chars) | `<generate_via_secrets_token_urlsafe_32>` | Yes |
| `GROQ_API_KEY` | Backend | Primary Groq API key for LLM inference | `gsk_...` | Optional (offline fallback) |
| `GROQ_PROJECT_ID` | Backend | Primary Groq project ID for quota isolation | `<groq_project_id>` | Optional |
| `GROQ_BACKUP_API_KEY` | Backend | Backup Groq API key for project-isolated failover | `gsk_...` | Optional |
| `GROQ_BACKUP_PROJECT_ID`| Backend | Backup Groq project ID for quota isolation | `<backup_groq_project_id>` | Optional |
| `ENVIRONMENT` | Backend | Runtime profile (`development`, `test`, `production`) | `development` | Yes |
| `ALLOW_DEMO_SEEDING` | Backend | Enable development demo user provisioning | `True` | No |
| `DEMO_ACCOUNT_PASSWORD` | Backend | Development-only initial demo password | `<dev_demo_password>` | No (dev/test only) |
| `VITE_API_URL` | Frontend | Base URL for FastAPI backend proxy | `http://127.0.0.1:8000` | No |

---

### Verification and Database Migration Management
Alembic migrations are the authoritative schema management mechanism. Normal application startup does not execute schema DDL or silent migrations. Apply migrations from a clean database:
```bash
# Verify current migration revision matches head:
python -m alembic -c backend/alembic.ini current
# Expected head: c3d4e5f6a7b8 (add_deviation_number_source)
```

### 3. Setup & Start Backend
```bash
# From repository root:
python -m venv .venv

# Activate virtual environment
# Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt

# Start backend server
python backend/run.py
```
Backend starts on `http://127.0.0.1:8000` (API documentation at `http://127.0.0.1:8000/docs`).

### 4. Setup & Start Frontend
```bash
cd frontend
npm install
npm run dev
```
Frontend development server starts on `http://127.0.0.1:5173`.

### 5. Production Build & Deployment Notes
- **Docker Compose**: Running `docker compose up` validates that required variables (`POSTGRES_PASSWORD`, `SECRET_KEY`) are present, failing immediately with descriptive errors if absent.
- **Production Secrets**: In `ENVIRONMENT=production`, default development passwords (`aivoa_password`), SQLite URLs, and placeholder secrets trigger immediate fail-fast exceptions.
- **Demo Account Isolation**: Demonstration accounts and shortcuts are strictly disabled in production (`import.meta.env.PROD` and backend `allows_demo_seeding = False`). Passwords are never embedded in frontend code.

---

## 5. Running the Automated Test Suite

The test suite validates database persistence, Alembic migrations, document extraction, evidence traceability, role authorization, quota-aware failover, PostgreSQL row-level concurrency locking, configuration fail-fast security, and demo login isolation:

```bash
# Execute deterministic test suite (164 automated tests; live external provider calls deselected):
pytest backend/tests -m "not live_provider" -v
```
*(All 171 automated tests pass against live PostgreSQL 16 with 0 warnings)*

To run opt-in live Groq inference tests (requires active API key with available quota):
```bash
pytest backend/tests -m "live_provider" -v
```

---

## 6. Sample Intake Files

Realistic pharmaceutical deviation test files are located in `examples/`:
- `examples/sample_deviation_report.pdf`: Multi-section formatted PDF deviation report for Atorvastatin batch B2026-API-044.
- `examples/sample_deviation_report.txt`: Plaintext incident report.
- `examples/sample_incident_email.txt`: Email notification format.

---

## 7. Data Integrity & Boundary Controls

- **Zero Synthetic Fabrication**: If the AI model is offline or quota-blocked, the system degrades gracefully (`AI_UNAVAILABLE` / `QUOTA_BLOCKED`) with empty proposal structures. It never generates fabricated fallback scenarios or synthetic equipment tags.
- **Project-Scoped Quota Failover**: Quota failover between primary (`GROQ_API_KEY`) and backup (`GROQ_BACKUP_API_KEY`) keys occurs only when keys are explicitly assigned to separate Groq project IDs (`GROQ_PROJECT_ID != GROQ_BACKUP_PROJECT_ID`). If keys share an organization/project quota, key rotation is avoided to prevent shared rate-limit burnout.
- **Fail-Closed Evidence Verification**: Pre-migration legacy evidence records (`uploaded_by_user_id IS NULL`) cannot be verified by standard investigators; verification strictly requires `QA_APPROVER` or `ADMIN` review. Original uploaders can never self-verify attributable evidence.
- **Provenance Concurrency Safety**: PostgreSQL row-level locks (`with_for_update()`) serialize concurrent root cause creation against Five Whys step or Fishbone cause deletion, eliminating dangling causal provenance.
- **Human In The Loop**: AI-suggested root causes can NEVER transition to `CONFIRMED` automatically. Formal confirmation requires an independent QA review, verified supporting evidence, and resolution of contradictory evidence.

---

## 8. AI Limitations

1. **Probabilistic Decision Support Only**:
   - All extractions, 5-Whys causal chains, Fishbone hypotheses, and CAPA recommendations generated by LLM models via Groq are computational suggestions.
   - They do not constitute certified engineering findings or validated cGMP determinations. A qualified human subject-matter expert (Lead Investigator or QA Specialist) must review and verify every hypothesis against empirical primary records.
2. **Document Boundary & Quota Behavior**:
   - In offline mode or under rate-limiting/quota exhaustion, the system returns structured degradation states (`QUOTA_BLOCKED` / `AI_UNAVAILABLE`). It never invents fallback synthetic incidents, fake equipment tags, or simulated batch records.
3. **No Autonomous Decision Execution**:
   - The AI engine cannot sign off investigations, approve CAPAs, confirm root causes, or close deviations. All lifecycle state transitions require human authorization with role-based checks.

---

## 9. Known Limitations

1. **Prototype Validation Status**:
   - Engineered as an architectural and engineering prototype. It has not undergone formal Computer System Validation (CSV), GAMP 5 life-cycle qualification (IQ/OQ/PQ), or formal 21 CFR Part 11 certification.
2. **Intake Ingestion Formats**:
   - Supports text, RFC 5322 formatted emails, and digital PDFs via PyMuPDF. Scanned handwritten documents or low-resolution image-only scans requiring specialized OCR preprocessing are outside current prototype capabilities.
3. **Single-Tenant Deployment Model**:
   - The current architecture operates as an isolated single-tenant workstation or VPC service. Multi-tenant multi-organization tenant isolation with separate schema catalogs is not implemented in this prototype release.

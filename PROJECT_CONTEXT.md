# MASTER PROJECT CONTEXT – AIVOA.AI RCA INTELLIGENCE

## 1. Project Identity
- **Project Name:** AIVOA.AI – RCA Intelligence
- **Official Title:** AI-Powered Root Cause Analysis (RCA) Module for Pharmaceutical API Manufacturing
- **Domain:** Active Pharmaceutical Ingredient (API) Manufacturing Quality Assurance (GMP / cGMP)
- **Classification:** Engineering Decision-Support Prototype (aligned with technical principles of FDA 21 CFR Part 211, FDA 21 CFR Part 11, ICH Q9, and ICH Q10; does not claim autonomous regulatory certification or validated GMP software without formal SOPs, qualification, and CSV).

---

## 2. Strict Technology Stack
- **Frontend:** React 19, Redux / Redux Toolkit, Tailwind CSS v4, Lucide React
- **Backend:** Python 3.12, FastAPI, Pydantic v2
- **AI Orchestration:** LangGraph (Compiled 13-Node `StateGraph` with conditional routing)
- **LLM Inference:** Groq API (`ChatGroq` via `langchain-groq`, default model `llama-3.3-70b-versatile` with quota-aware project failover)
- **Database Engine:** PostgreSQL 16 (`postgres:16-alpine` containerized)
- **Database Driver & ORM:** `asyncpg` + SQLAlchemy 2.0 AsyncIO
- **Database Migrations:** Alembic (Async migration runner)

---

## 3. Core Business Workflow
1. **Incident Intake:**
   - Ingestion of PDF deviation reports, plain text incident notes, and handover emails.
   - Streaming text extraction via `pypdf` and RFC 5322 MIME email parsing.
   - Automated population of structured investigation and deviation form fields using AI.
2. **Investigation & Methodological RCA:**
   - Correlation of empirical evidence (SCADA telemetry, sensor trend logs, calibration certificates).
   - Dual-methodology execution: Iterative 5-Whys causal cascade and Ishikawa Fishbone (6M: Man, Machine, Material, Method, Measurement, Milieu).
   - Identification of missing evidence gaps and generation of targeted investigator follow-up questions.
   - Classification of primary root causes vs. secondary contributing factors with evidence confidence ratings.
3. **CAPA Generation:**
   - Automated generation of Corrections (containment/quarantine), Corrective Actions (prevent local recurrence), and Preventive Actions (facility-wide horizontal deployment).
   - Assignee ownership, deadline suggestions, and quantitative effectiveness review criteria.
4. **Approval & Persistence:**
   - Investigator review and editing of all AI-suggested fields.
   - Explicit distinction between AI hypotheses (`is_ai_suggested=True`, `is_verified=False`) and human-confirmed findings.
   - Immutable audit logging of all field mutations and QA approvals.
   - Persistence in PostgreSQL 16 with full relational integrity.

---

## 4. Current Implementation Status (Same-Day Task 3 Complete)
- **Prototype Status:** Decision-support engineering prototype for pharmaceutical API manufacturing root cause analysis. Does not claim autonomous regulatory compliance (21 CFR Part 11 / cGMP validation requires organizational SOPs, qualification protocols, and formal validation).
- **Database Engine:** PostgreSQL 16 verified healthy on `localhost:5432`.
- **Database Schema:** Managed via Alembic revision `ae9dda31c187` with full relational integrity, user links, user activation status (`is_active`), field-level human review attribution, dynamic 5 Whys depth, Fishbone cause promotion, and junction models for 5 Whys and Fishbone evidence links.
- **End-to-End RCA Workflow & Demonstration Readiness (Same-Day Task 3):**
  - **8-Stage cGMP Lifecycle Fully Integrated:**
    `Deviation Identification → Document Intake → Evidence Review → Root Cause Analysis → CAPA Creation → QA Approval → Completion → Effectiveness Verification`
  - **Fictional Demonstration Scenario:** Paracetamol API crystallization reactor thermal excursion (`DEV-2026-104`, batch `API-2026-104`, reactor `CR-104`, 86°C excursion for 18 minutes due to solenoid SV-104 galling/binding).
  - **Missing Evidence Explicitly Grounded:** Cooling valve CV-104 calibration record missing; operator shift handover logbook not attached (tracked as unaddressed evidence gaps).
  - **Demonstration Accounts & One-Click Login:**
    - `lead_investigator`: Dr. Sarah Lin (Lead Investigator, role `INVESTIGATOR`)
    - `qa_director`: Dr. Elena Rostova (QA Director, role `QA_APPROVER`)
    - Supported by quick-login buttons on the UI login modal and a `[Load Demo (DEV-2026-104)]` button in Document Intake.
  - **End-to-End Test Suite:** Automated 14-step integration test (`backend/tests/test_e2e_rca_demonstration_workflow.py`) passed against PostgreSQL 16.
  - **Regression & Live Provider Status:** 151 deterministic regression tests passed (0 failed, 2 deselected); live Groq inference test passed. Frontend production build clean in 743ms.
- **CAPA Workflow Integrity & Human Approval (Same-Day Task 2):**
  - **State Machine Lifecycle:** Formal progression: `PROPOSED` -> `APPROVED` -> `IN_PROGRESS` -> `COMPLETED` -> `EFFECTIVENESS_VERIFIED`.
  - **Proposal Integrity:** Manual and AI CAPAs always initialize in `PROPOSED` status with `is_verified=False`. Client attempts to forge verification flags are rejected with `HTTP 400 Bad Request`.
  - **Referential Integrity:** Linking to a root cause strictly validates existence in the same investigation and non-rejected status (`HTTP 400 Bad Request` on cross-investigation or rejected links).
  - **Role-Based QA Approval:** Dedicated endpoint `POST /capas/{id}/approve` strictly requires `QA_APPROVER` or `ADMIN` role. Lead investigators cannot self-approve their own investigation's CAPAs (Separation of Duties).
  - **Implementation & Completion:** Work cannot begin (`IN_PROGRESS`) or complete (`COMPLETED`) without prior QA approval. Completion requires valid implementation notes ($\ge 5$ characters).
  - **Effectiveness Verification:** Dedicated endpoint `POST /capas/{id}/verify-effectiveness` requires `QA_APPROVER` or `ADMIN`, `COMPLETED` status, and defined quantitative effectiveness criteria.
  - **Regulatory Locking & Deletion Protection:** Effectiveness-verified CAPAs are locked against modification and deletion (`HTTP 400 Bad Request`).
  - **Full Transactional Audit Trail:** All mutations generate auditable log records and execute explicit `await db.commit()`.
- **Repository Security & Clean Index (Same-Day Task 1):**
  - Git index purged of 8,074 unwanted local/cached files (`.venv/`, `backend/.env`, deprecated `*.db`, local `storage/evidences/`, and bytecode).
  - Root `.gitignore` configured to prevent re-tracking.
  - Config hardened with fail-fast production secrets validation.
- **Legacy Evidence Fail-Closed Hardening & Provenance Locking (Phase 2D.2.3):**
  - Unattributable legacy evidence records (`uploaded_by_user_id IS NULL`) fail closed: ordinary investigators blocked with 403; only `QA_APPROVER` or `ADMIN` can verify.
  - PostgreSQL row-level locks (`with_for_update()`) eliminate creation-vs-deletion race conditions across 5-Whys and Fishbone provenance.
- **RCA Workflow Implementation & Human Review (Phase 2D.2.2):**
  - **Dynamic 5-Whys Depth & Evidence Linking:** Removed arbitrary depth limit (`le=5`), allowing natural causal depth beyond 5 steps. Created `FiveWhysEvidenceLink` supporting `SUPPORTING` and `CONTRADICTORY` evidence associations with confidence rating. Enforced verification barrier: marking step `VERIFIED` strictly requires $\ge 1$ verified supporting evidence item.
  - **Ishikawa 6Ms & Cause Promotion:** Structured Fishbone across 6Ms (MAN, MACHINE, MATERIAL, METHOD, MEASUREMENT, MILIEU) with status lifecycle (`HYPOTHESIS`, `VERIFIED`, `RULED_OUT`). Created `FishboneEvidenceLink` with verification guard. Implemented `POST /api/v1/fishbone/{id}/promote` transitioning verified causes to formal `RootCause` proposals (`status="PROPOSED"`, copying evidence links and preserving provenance `source_type="FISHBONE"`).
  - **Evidence-Supported Root Cause Confirmation Barrier:** Root causes support `PROPOSED`, `UNDER_REVIEW`, `CONFIRMED`, `REJECTED`. AI can never auto-confirm. Confirmation requires $\ge 1$ verified supporting evidence link, zero unresolved contradictions, and explicit human signature + rationale ($\ge 10$ chars), populating `confirmed_by`, `confirmed_by_user_id`, and `confirmed_at`.
  - **Itemized Human-in-the-Loop RCA Review:** Replaced blind bulk-overwrites with granular endpoint `POST /api/v1/copilot/apply-rca-item` and expandable UI review accordion, allowing investigators to accept, modify, or decline individual proposed Whys, Fishbone causes, Root causes, and CAPAs.
  - **Strict Cross-Investigation Isolation:** Comprehensive barrier preventing linking evidence from Investigation A into Five Whys, Fishbone, or Root Causes of Investigation B (HTTP 400 Bad Request).
- **RCA Generation Integrity & Groq Error Hardening (Phase 2D.2.1):**
  - Elimination of synthetic RCA fallback generation and guidance fabrication.
  - Provider unavailability mapped strictly to structured empty candidate payloads with status `AI_UNAVAILABLE`.
  - Request-scoped Groq credential failover with project-aware and quota-aware error handling.
- **Intake Integrity & Human Review Hardening (Phase 2D.1.1):**
  - Elimination of fallback fabrication: unextracted parameters return `value=None` and `status=MISSING`.
  - Explicit human acceptance: unaccepted fields are ignored by backend.
  - Server-side source revalidation: continuous span matching required for `SOURCE_FACT`.
  - Hardened citation validation: embedded fabrication and numeric mismatch rejection.
  - Strict idempotency on repeated intake apply requests.
  - Field-level reviewer attribution in PostgreSQL.
- **Secure Administrator Provisioning & Demo Account Isolation (Phase 2C.4 Task 1):**
  - Hardcoded default ADMIN credentials and automatic production provisioning eliminated.
  - Demo accounts (`lead_investigator`, `qa_director`) strictly gated to `ENVIRONMENT in ("development", "test")`.
  - First-admin provisioning implemented via dedicated CLI (`python -m app.cli provision-admin`) and startup environment secrets (`INITIAL_ADMIN_USERNAME`, `INITIAL_ADMIN_PASSWORD`).
  - Inactive account login guard (`is_active == False` rejected with HTTP 401 Unauthorized).
- **Secure Ownership Assignment & Segregation of Duties (Phase 2C.4 Task 2):**
  - Administrative ownership assignment (`POST /api/v1/investigations/{id}/assign-owner`) strictly restricted to `ADMIN` role.
  - Segregation of Duties: target account must have role `INVESTIGATOR`.
  - Mandatory reason validation (`min_length=10`) with immutable audit logging.
- **Test Verification:**
  - 6/6 Phase 2D.2.2 RCA workflow & human review tests passing (`test_rca_workflow_and_human_review.py`).
  - 13/13 Phase 2D.2.1 RCA generation integrity tests passing (`test_rca_generation_integrity.py`).
  - 10/10 Phase 2D.2.1.2 Groq failover and quota tests passing (`test_groq_failover_and_quota.py`).
  - 14/14 Phase 2D.1.1 intake integrity & human review hardening tests passing (`test_document_intake_hardening.py`).
  - 12/12 Phase 2D.1 document intake and validation tests passing (`test_document_intake_pipeline.py`).
  - 12/12 Phase 2C.4 admin provisioning and ownership validation tests passing (`test_admin_provisioning_and_ownership.py`).
  - 19/19 Phase 2C.3 security authorization tests passing (`test_security_authorization.py`).
  - 9/9 Phase 2C.1 critical remediation tests passing (`test_remediation_p1_p2_p3.py`).
  - 9/9 Phase 2C evidence traceability tests passing (`test_evidence_traceability.py`).
  - 14/14 Phase 2B AI remediation & LangGraph tests passing (`test_ai_remediation.py`).
  - 3/3 Groq and workflow pipeline tests passing (`test_groq_and_workflow.py`).
  - 2/2 API endpoint lifecycle tests passing (`test_api_endpoints.py`).
  - 3/3 PostgreSQL database tests passing (`test_postgres_database.py`).
  - 3/3 Document parser tests passing (`test_document_parser.py`).
  - Total automated deterministic tests passing: 129 passing tests (0 failures, 0 unexpected skips, 2 live-provider tests deselected).
  - Frontend Vite production build: 0 errors, clean output (819ms).

---

## 5. Phase 2D.2.1.2 Implementation Status — Groq Multi-Key Failover Verification & Quota-Aware Correction (Complete)
- **Groq Project Boundary Discovery:**
  - Runtime verification of `x-ratelimit-remaining-requests` and `x-ratelimit-limit-requests` headers confirmed that `GROQ_API_KEY` and `GROQ_BACKUP_API_KEY` share the exact same quota bucket (1000 requests/day) and belong to the same Groq organization/project by default.
- **Quota-Aware Failover Rules:**
  - **401 Unauthorized / Revoked Credential:** Primary credential failure attempts backup credential in request scope. If backup also fails with 401, returns `status="AI_UNAVAILABLE"`.
  - **Organization-level 429 (TPD / TPM / ITPM / OTPM):** Strictly halts key rotation and returns `status="QUOTA_BLOCKED"` since all keys within the organization share identical daily token ceilings.
  - **Project-level 429:** Backup credential is only attempted if `settings.has_separate_groq_projects` is established (`GROQ_PROJECT_ID` and `GROQ_BACKUP_PROJECT_ID` explicitly set and distinct). Otherwise returns `status="QUOTA_BLOCKED"`.
  - **Unknown / Ambiguous 429:** Fails safely without key rotation and returns `status="QUOTA_BLOCKED"`.
  - **Model Permission Errors (403):** Classified immediately as `GroqPermissionError` without repeated retries.
  - **Provider Outage:** Bounded retries across candidate models without endless key rotation.
- **Concurrency-Safe Request-Scoped Credential Selection:**
  - Completely excised mutable global key switching (`self.active_api_key` mutations during inference).
  - All credential selections are strictly request-scoped within the call stack of `_call_groq_json` and `chat_copilot`, ensuring concurrent requests executed via `asyncio.gather` cannot exchange, overwrite, or corrupt each other's credentials.
- **Automated Test Verification:**
  - `backend/tests/test_groq_failover_and_quota.py`: 9/9 dedicated deterministic tests passing.
  - `backend/tests/test_rca_generation_integrity.py`: 13/13 passing.
  - `backend/tests/test_postgres_database.py`: 3/3 passing.
  - Alembic Head: `a1b2c3d4e5f6` (unchanged).
  - Frontend Build: Clean Vite production build in 1.78s.
  - Live Inference: Verified live single-token inference on both primary key and backup key with 100% success.

---

## 6. Phase 2D.2.1.1 Implementation Status — Final RCA Fallback Removal & Provider-Unavailable Integrity Remediation (Complete)
- **Complete Elimination of Dynamic Fallback Hypotheses:**
  - Removed all dynamic 5-Whys and Fishbone hypothesis generation from `_fallback_rca_generation` and `_fallback_chat_reply`.
  - When AI inference is unavailable, the backend returns strictly empty candidate lists (`five_whys: []`, `fishbone_causes: []`, `root_causes: []`, `capa_actions: []`, `evidence_gaps: []`) with an explicit status (`AI_UNAVAILABLE`, `QUOTA_BLOCKED`, `AUTH_ERROR`, or `REQUEST_TIMEOUT`).
  - Clear investigator guidance is surfaced informing the user that AI inference is offline and manual RCA tools remain available for documentation.
- **Provider-Unavailable Offline Notice in Chat:**
  - Replaced canned troubleshooting SOPs with an explicit offline notice: `"AI Copilot inference is currently unavailable. The AI assistant cannot generate live responses at this time. Please check your AI service connection, or proceed using manual investigation tools in the workspace."`
  - Zero fabricated technical answers, fake SOPs, or invented facts are emitted when Groq is unavailable.
- **Incomplete Output Preservation Without Synthetic Padding:**
  - When Groq returns partial output, preserved sections are returned untouched and omitted sections remain empty (`[]`) without synthetic padding.
- **Excised Hardcoded Extraction Defaults:**
  - Removed hardcoded constants (`CV-04`, `88%`, `pneumatic actuator restriction`, `<= 22.0°C`, `ramp rate 0.5°C/min`, `Altered crystal aspect ratio...`) from `_build_structured_fields`. All fields strictly extract text from the document or resolve to `status=MISSING`.
- **Dual Groq API Key Failover & Quota Optimization:**
  - Supported `GROQ_BACKUP_API_KEY` in environment configuration (`backend/.env` and `app/core/config.py`).
  - Automatic failover in `_call_groq_json` and `chat_copilot` when primary key exhausts quota, daily token limits (TPD), or encounters 429 rate limits.
  - Cached available models list to prevent unnecessary network calls and token consumption.
  - Comprehensive API key redaction in `sanitize_secret` covering primary, backup, Bearer tokens, and any `gsk_...` strings.
- **Deterministic Test Verification:**
  - `backend/tests/test_rca_generation_integrity.py`: 13/13 passing (covering 429, 401, 408, 5xx, connection failure, malformed JSON, incomplete output preservation, unrelated document guard, valid manufacturing non-fabrication, manual CRUD, human confirmation restrictions, chat offline notice, and API key sanitization).
  - `backend/tests/test_ai_remediation.py`: 14/14 passing.
  - `backend/tests/test_groq_and_workflow.py`: 3/3 passing.
  - Alembic Head: `a1b2c3d4e5f6` (unchanged).
  - Frontend Build: Clean Vite production build with zero bundle errors.

---

## 6. Phase 2D.1 Implementation Status — End-to-End Document Intake & AI Extraction (Complete)
- **Multi-Format Document Intake:**
  - PDF Upload (`POST /api/v1/intake/parse-file`): Streaming chunked upload with 10 MB limit enforcement, `%PDF` magic byte validation, page-by-page extraction via `pypdf`, page count and text preservation, SHA-256 fingerprinting, and secure isolated filesystem storage (`storage/evidences/{investigation_id}/`).
  - Pasted Incident Text (`POST /api/v1/intake/parse-text`): Ingests unstructured incident descriptions, normalizes whitespace and non-ASCII characters, and computes SHA-256 hash.
  - Incident Handover Email (`POST /api/v1/intake/parse-text` with `is_email=True`): Parses RFC 5322 MIME headers (`From`, `To`, `Subject`, `Date`), extracts clean body, stores email headers in `source_metadata`, and explicitly tags sender identity as unverified metadata (`sender_verified=False`).
- **16 Pharmaceutical Field Extraction Schema:**
  - Extracts 16 canonical GMP parameters: Deviation Title, Deviation ID, Incident DateTime, Batch Number, Product / API Name, Unit Operation, Equipment ID, Process Parameter, Approved Range, Observed Value, Deviation Duration, Description, Immediate Containment, Potential Impact, Available Evidence, Conflicting Information.
- **Pydantic Structured Outputs & Extraction Status Classification:**
  - Each extracted parameter is typed as `ExtractedField` with an explicit `ExtractionStatus`:
    - `SOURCE_FACT`: Verbatim or normalized match in source document, verified page number, and high confidence ($\ge 0.95$).
    - `AI_INFERENCE`: Inferred or paraphrased parameter with explanatory validation note.
    - `MISSING`: Parameter unrecorded or explicitly not stated in the source text.
    - `CONFLICTING`: Contradictory evidence detected across document sources or telemetry streams (e.g. valve controller 100% demand vs 12% position feedback).
  - Deterministic citation verification via `document_parser.validate_source_citation` prevents hallucinated or fabricated citations.
- **Interactive Human Review Interface (`DocumentIntakeTab.jsx`):**
  - Investigator review cockpit displaying raw document preview with verified SHA-256 fingerprint and page count.
  - 16 editable field cards with status color badges (`SOURCE_FACT` in green, `AI_INFERENCE` in purple, `MISSING` in yellow, `CONFLICTING` in red).
  - Inline editing of values, accept/reject toggles, and verbatim source citation references with page citations.
  - Dedicated alerting cards for conflicting evidence pairs and missing information / evidence gaps.
  - "Apply Reviewed Information to Investigation" action with confirmation.
- **Transactional PostgreSQL Persistence & Audit Integrity (`POST /api/v1/intake/apply-to-investigation`):**
  - Guaranteed atomic persistence (`try/except: db.rollback()`).
  - Maps accepted reviewed fields to `Deviation` with explicit unverified flags (`is_ai_populated=True`, `is_verified=False`).
  - Creates primary `Evidence` record (`classification="PRIMARY_SOURCE"`, `is_verified=False`, SHA-256 hash, extracted text).
  - Persists accepted findings as `InvestigationFinding` rows with `citation_verified` flags and validation statuses (`VERIFIED_SOURCE_FACT`, `CONFLICTING_INFORMATION`, `AI_INFERENCE`).
  - Records unstated parameters as `EvidenceGap` rows for investigator follow-up.
  - Generates immutable `AuditLog` entry documenting investigator user ID and reviewed fields applied.
  - Data retrieval verified across browser refresh/reload.

---

## 7. Phase 2D.2.2 & 2D.2.2.2 Implementation Status — RCA Workflow, Human Review & Security Remediation (Complete)
- **Role-Based Root Cause Authorization & Segregation of Duties:**
  - Formal confirmation (`POST /api/v1/root-causes/{id}/confirm`) is strictly restricted to `QA_APPROVER` or `ADMIN` roles. Standard `INVESTIGATOR` attempts return `403 Forbidden`.
  - Enforced separation of duties: The assigned `lead_investigator` cannot confirm their own root cause proposals even if possessing high-level system permissions.
  - Root cause rejection (`POST /api/v1/root-causes/{id}/reject`) is restricted to the QA review boundary (`QA_APPROVER` or `ADMIN`).
  - All attribution fields (`confirmed_by`, `confirmed_by_user_id`, `confirmed_at`, `rejected_by`, `rejected_by_user_id`, `rejected_at`) are derived strictly from the authenticated server-side session.
- **Evidence Verification Integrity & Provenance Tracking:**
  - Evidence creation (`POST /api/v1/investigations/{id}/evidences/manual` and file upload) strictly initializes `is_verified=False`, `verified_by=None`, and `verified_by_user_id=None`, completely ignoring client-supplied payload values.
  - Enforced separation of duties on verification: Original uploader cannot self-verify their own evidence items (`uploaded_by_user_id == current_user.id` returns `403 Forbidden`).
  - Database schema updated via Alembic migration `ae9dda31c187`: added `uploaded_by_user_id` and `verified_by_user_id` foreign keys to `users.id` with btree indexes.
- **Causal Provenance & Generic Update Lockdown:**
  - Excised `is_verified`, `source_type`, and `source_id` from generic `RootCauseUpdate` schema to prevent unverified promotion or provenance tampering via `PUT /api/v1/root-causes/{id}`.
  - Generic updates cannot transition status to `CONFIRMED` or `REJECTED` (must use dedicated human review endpoints).
  - Enforced strict enum validation on `source_type` (`FIVE_WHYS`, `FISHBONE`, `DIRECT_SYNTHESIS`, `MANUAL`).
  - Cross-investigation source references return `400 Bad Request`.
  - Referential integrity: deletion of Five Whys steps or Fishbone causes referenced by active root causes is guarded and returns `409 Conflict`.
- **Fishbone Promotion Concurrency Safety:**
  - Concurrency-safe promotion via row-level locking (`with_for_update()`).
  - Duplicate promotion prevented: subsequent promotion requests return `409 Conflict`.
  - Eager relationship population and session cache synchronization via `execution_options(populate_existing=True)` guarantees cloned evidence links persist reliably.
- **Deterministic Test Verification:**
  - `backend/tests/test_phase_2d_2_2_2_remediation.py`: 5/5 passing (covering all 15 audit scenarios).
  - `backend/tests/test_rca_workflow_and_human_review.py`: 6/6 passing.
  - `backend/tests/test_postgres_database.py`: 3/3 passing.
  - **Full Backend Pytest Suite:** 134 passed, 0 failed, 2 deselected (69.08s).
  - **Alembic Head:** `ae9dda31c187 (head)`.
  - **Frontend Build:** Vite production build clean in 1.50s.

---

## 8. Phase 2D.2.3 Implementation Status — Legacy Evidence Fail-Closed Hardening & Documentation Reconciliation (Complete)
- **Legacy Evidence Fail-Closed Policy:**
  - Case A (Attributable Evidence): Original uploader cannot self-verify their submission (`uploaded_by_user_id == current_user.id` returns `HTTP 403 Forbidden`). Eligible independent reviewers (`QA_APPROVER`, `ADMIN`, or assigned lead investigator reviewing collaborator evidence) can verify (`HTTP 200 OK`).
  - Case B (Unattributable Legacy Evidence): When `uploaded_by_user_id IS NULL`, the system fails closed: ordinary investigators and assigned lead investigators without elevated review roles receive `HTTP 403 Forbidden`. Only authorized `QA_APPROVER` or `ADMIN` roles may verify legacy records. Reviewer identity is bound strictly from the authenticated server token (`verified_by_user_id`, `verified_by`), and historical uploader identity is never inferred or fabricated.
- **Provenance Concurrency Protection via Native Row-Level Locking:**
  - Enforced `with_for_update()` row-level locks on `FiveWhysStep` and `FishboneCause` during `create_root_cause`, `delete_five_why_step`, and `delete_fishbone_cause`.
  - Serializes concurrent transactions at the PostgreSQL database level: if deletion commits first, root-cause creation receives `HTTP 400 Bad Request`; if creation commits first, source deletion receives `HTTP 409 Conflict`. Dangling provenance references are prevented.
- **Historical Test Accounting Reconciliation:**
  - Reconciled Phase 2D.2.2.2 report module accounting discrepancy: `test_groq_failover_and_quota.py` has 12 tests (not 10). Reconciled baseline total: 136 collected (134 selected/passed, 2 deselected).
- **Audit & Documentation Realignment:**
  - Standardized project timeline on actual system execution timestamp (November 2026).
  - Explicitly defined the system as an engineering decision-support prototype. Software technical safeguards (immutable audit trails, SHA-256 digests, electronic review attribution, separation of duties) support investigator workflows but do not replace organizational SOPs, computerized system validation (CSV / CSA), qualified infrastructure, or formal regulatory assessment.
  - User accounts should be deactivated (`is_active = False`) rather than physically deleted to ensure lifelong attribution continuity.
- **Deterministic Test Verification:**
  - Dedicated suite: `backend/tests/test_phase_2d_2_3_legacy_and_provenance.py` (4/4 passed).
  - **Full Backend Pytest Suite:** **138 passed, 0 failed, 2 deselected** (140 collected, 75.14s).
  - **Alembic Head:** `ae9dda31c187 (head)`.
  - **Frontend Production Build:** Vite build clean in 1.53s.


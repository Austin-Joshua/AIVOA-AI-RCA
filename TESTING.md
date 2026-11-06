# AIVOA.AI RCA Intelligence – Testing Documentation

## 1. Overview
The testing framework uses `pytest` and `pytest-asyncio` with strict async loop configurations. Tests verify end-to-end functionality across database persistence, API endpoints, document extraction, and AI orchestration.

---

## 2. Test Execution Commands

### 2.1 Verify PostgreSQL 16 & Database Infrastructure
Verifies live PostgreSQL 16 connection, Alembic migration state, and relational persistence across all 11 tables:
```bash
pytest backend/tests/test_postgres_database.py -v
```

### 2.2 Run Full Deterministic Backend Test Suite
Executes all database, API lifecycle, document parsing, and AI workflow tests deterministically against PostgreSQL 16 using mocked provider boundaries:
```bash
pytest backend/tests -v
```
*Note:* Live provider integration tests requiring external Groq API tokens are cleanly deselected by default, ensuring runs never fail due to live rate limits or quota exhaustion.

### 2.2.1 Run Explicit Opt-In Live Groq Provider Tests
To execute live end-to-end inference against the external Groq API (requires active `GROQ_API_KEY` and remaining quota):
```bash
pytest backend/tests --run-live -v
# Or run ONLY the live provider integration tests:
pytest backend/tests -m live_provider --run-live -v
```

### 2.3 Run AI Remediation & LangGraph Test Suite (Tests A through N)
Executes all 14 AI remediation verification tests against live Groq API and mocked edge-cases:
```bash
pytest backend/tests/test_ai_remediation.py -v
```

### 2.4 Verify Evidence Management & Traceability (Phase 2C Suite)
Executes all 9 evidence persistence, verification, linking, gap management, and Part 11 confirmation tests:
```bash
pytest backend/tests/test_evidence_traceability.py -v
```

### 2.5 Run Critical Remediation Suite (Phase 2C.1 P1, P2, P3)
Executes all 9 verification tests for file persistence, tamper detection, text immutability, contradiction disposition, soft archival, runtime citation validation, fabricated quote rejection, upload guards, and reviewer authentication:
```bash
pytest backend/tests/test_remediation_p1_p2_p3.py -v
```

### 2.6 Run Security Authorization & Investigation Isolation Suite (Phase 2C.3)
Executes all 19 security, ownership authorization, non-mutating access control, admin reassignment, and CORS allowlist test cases:
```bash
pytest backend/tests/test_security_authorization.py -v
```

### 2.7 Run Document Intake & AI Extraction Pipeline Suite (Phase 2D.1)
Executes all 12 multi-format intake, citation validation, 16-parameter extraction, human review, PostgreSQL persistence, and quota-aware Groq tests:
```bash
pytest backend/tests/test_document_intake_pipeline.py -v
```

### 2.8 Run Intake Integrity & Human Review Hardening Suite (Phase 2D.1.1)
Executes all 14 tests verifying zero fallback fabrication, unaccepted field initialization, server-side citation revalidation, rejection of embedded quote fabrications and numeric mismatches, idempotent apply, Groq 429/503 mapping, unpaginated page attribution, and reviewer attribution columns:
```bash
pytest backend/tests/test_document_intake_hardening.py -v
```

### 2.9 Run Critical Admin Provisioning & Ownership Validation Suite (Phase 2C.4)
Executes all 12 administrator provisioning, CLI bootstrap, demo isolation, inactive account rejection, segregation of duties, and transaction rollback test cases:
```bash
pytest backend/tests/test_admin_provisioning_and_ownership.py -v
```

### 2.10 Run RCA Generation Integrity & Error Hardening Suite (Phase 2D.2.1)
Executes all 13 tests verifying Groq HTTP status mapping (429, 401, 408, 503), API secret sanitization, malformed JSON recovery, zero synthetic constants in fallback/chat, cafeteria minutes non-fabrication regression, safety defaults (`PROPOSED`, `is_ai_suggested=True`, `is_verified=False`), variable 5-Whys depth, incomplete Fishbone coverage, and Pydantic schema validation:
```bash
pytest backend/tests/test_rca_generation_integrity.py -v
```

### 2.11 Run RCA Workflow & Human Review Suite (Phase 2D.2.2)
Executes all 6 tests verifying dynamic 5-Whys depth beyond 5, evidence-linked verification barriers, Fishbone 6M evaluation, cause promotion to Root Cause proposals (`status="PROPOSED"`), strict cross-investigation isolation, human confirmation barriers with attribution, and itemized RCA proposal review (`POST /copilot/apply-rca-item`):
```bash
pytest backend/tests/test_rca_workflow_and_human_review.py -v
```

### 2.12 Run Targeted Security, Evidence Lifecycle & Provenance Remediation Suite (Phase 2D.2.2.2)
Executes all 5 tests verifying the 15 security, authorization, evidence lifecycle, provenance, deletion protection, and concurrency-safe promotion audit scenarios:
```bash
pytest backend/tests/test_phase_2d_2_2_2_remediation.py -v
```

### 2.13 Run Legacy Evidence Fail-Closed & Provenance Concurrency Suite (Phase 2D.2.3)
Executes all 4 tests verifying the 10 legacy evidence fail-closed and attributable role matrix scenarios, server-side session attribution binding, and concurrent row-level locking (`with_for_update()`) on root cause creation vs Five Whys step / Fishbone cause deletion:
```bash
pytest backend/tests/test_phase_2d_2_3_legacy_and_provenance.py -v
```

### 2.14 Run CAPA Workflow Integrity & Human Approval Suite (Same-Day Task 2)
Executes all 12 tests verifying valid CAPA creation in `PROPOSED` status, cross-investigation root cause rejection (400), nonexistent/rejected root cause linking rejection (400), client-forged verification metadata rejection (400), investigator approval denial (403), QA approval success (`status="APPROVED"`, `is_verified=True`), lead investigator self-approval prevention (403), invalid lifecycle state transition rejection (400), completion requirements (non-empty notes), effectiveness verification authorization and prerequisite validation, effectiveness-verified modification/deletion protection (400), and full audit logging with PostgreSQL 16 persistence:
```bash
pytest backend/tests/test_phase_2d_capa_workflow.py -v
```

### 2.15 Run Same-Day Task 3 End-to-End RCA Demonstration Workflow Test
Executes the comprehensive 14-step integration test modeling the full cGMP lifecycle from deviation intake to final QA dossier sign-off on PostgreSQL 16:
```bash
pytest backend/tests/test_e2e_rca_demonstration_workflow.py -v
```

### 2.16 Opt-in SQLite Unit Test Execution (Isolated CI Mode)
To run isolated unit tests without contacting PostgreSQL:
```bash
$env:TEST_FORCE_SQLITE="1"
pytest backend/tests/test_document_parser.py -v
```

### 2.17 Run Post-Migration Release Hardening Suite
Executes all 13 security, database lifecycle, startup non-DDL verification, and demo-login production isolation tests:
```bash
pytest backend/tests/test_release_hardening.py -v
```

---

## 3. Test Suites & Coverage

| Test Module | Primary Scope | Tests | Database Target | AI Target |
| :--- | :--- | :--- | :--- | :--- |
| `test_e2e_rca_demonstration_workflow.py` | Same-Day Task 3: Comprehensive 14-step end-to-end integration test of the full cGMP deviation lifecycle (`DEV-2026-104` Paracetamol crystallization excursion), dual-role segregation of duties (`lead_investigator` vs `qa_director`), intake parsing, review & apply, evidence verification separation barrier (403), evidence gap response, Five Whys & Fishbone causal analysis, root cause promotion (`PROPOSED`), QA root cause confirmation barrier (403), CAPA linkage, QA approval barrier (403), execution completion, effectiveness verification & locking (400), final investigation sign-off barrier (403), and fresh PostgreSQL 16 session reload with complete audit trail verification | 1 | PostgreSQL 16 | Deterministic Mock Boundary |
| `test_phase_2d_capa_workflow.py` | Same-Day Task 2: CAPA lifecycle integrity (`PROPOSED` -> `APPROVED` -> `IN_PROGRESS` -> `COMPLETED` -> `EFFECTIVENESS_VERIFIED`), cross-investigation and rejected root cause rejection, client-forged verification metadata prevention, investigator approval denial (403), QA approval authorization, lead investigator self-approval block (403), invalid lifecycle transition guards, completion rationale requirements, effectiveness verification prerequisites, immutable locked deletion/update protection (400), and audit logging | 12 | PostgreSQL 16 | N/A |
| `test_phase_2d_2_3_legacy_and_provenance.py` | Phase 2D.2.3: Comprehensive verification of legacy evidence fail-closed authorization (`uploaded_by_user_id IS NULL` blocks ordinary/lead investigators with 403, requires `QA_APPROVER` or `ADMIN`), attributable evidence separation of duties (uploader blocked with 403, peer/QA allowed), server-session attribution integrity (client payload ignored), and PostgreSQL row-level locking (`with_for_update()`) concurrency serialization between root cause creation and Five Whys step / Fishbone cause deletion | 4 | PostgreSQL 16 | N/A |
| `test_phase_2d_2_2_2_remediation.py` | Phase 2D.2.2.2: Root cause confirmation/rejection role authorization (`QA_APPROVER`/`ADMIN` required), lead investigator self-confirmation block, evidence creation initialization guards (`is_verified=False`), evidence verification separation of duties (uploader blocked with 403), FK bindings to `users.id` (`uploaded_by_user_id`, `verified_by_user_id`), provenance immutability and `RootCauseUpdate` generic lockdown, cross-investigation source reference rejection (400), Five Whys & Fishbone active root cause deletion conflict protection (409), Fishbone cause promotion concurrency locking (`with_for_update()`) and duplicate promotion prevention (409), eager relationship synchronization | 5 | PostgreSQL 16 | N/A |
| `test_rca_workflow_and_human_review.py` | Phase 2D.2.2: Dynamic 5-Whys depth beyond 5, 5-Whys evidence linking & verification barrier, Fishbone 6Ms evaluation & cause promotion to formal Root Cause proposal (`PROPOSED`, evidence copied), strict cross-investigation isolation boundaries across Whys/Fishbone/Root Causes, Root Cause confirmation barrier ($\ge 1$ verified supporting evidence, zero active contradictions, investigator rationale $\ge 10$ chars, attribution binding), itemized RCA proposal apply endpoint (`/copilot/apply-rca-item`) | 6 | PostgreSQL 16 | Unit Mocks + Schema Engine |
| `test_groq_failover_and_quota.py` | Phase 2D.2.1.2 & 2D.2.1.4: Deterministic verification of multi-key failover and quota-aware logic: primary 401 failover to backup success, both 401 to `AI_UNAVAILABLE`, organization-level 429 non-rotation, project-level 429 separate project gating, unknown 429 safe `QUOTA_BLOCKED`, backup 5xx failure handling, concurrent request credential isolation via request scope, complete API key sanitization, primary credential success non-rotation (Test 10), provider 5xx outage to `AI_UNAVAILABLE` (Test 11), AI cannot confirm root causes guard (Test 12), and 100% non-fabrication guarantee across all provider failure modes | 12 | Unit Mocks | Groq Key Failover & Quota Classifier |
| `test_rca_generation_integrity.py` | Phase 2D.2.1.1: Complete elimination of dynamic fallback hypotheses (`five_whys: []`, `fishbone_causes: []`, `root_causes: []`, `capa_actions: []`, `evidence_gaps: []`), provider-unavailable statuses (`AI_UNAVAILABLE`, `QUOTA_BLOCKED`, `AUTH_ERROR`, `REQUEST_TIMEOUT`), partial Groq response preservation without synthetic padding, chat offline notice without fake SOPs, unrelated content guard (cafeteria minutes produces 0 incidents), extraction non-fabrication (excised constants), manual CRUD integrity, human confirmation restrictions, API key regex sanitization | 13 | PostgreSQL 16 | Unit Mocks + Hardened Offline Handler |
| `test_document_intake_hardening.py` | Phase 2D.1.1: Zero fallback data fabrication for unrelated/missing fields, explicit human acceptance initialization (`is_accepted=False`), server-side citation revalidation & demotion to `AI_INFERENCE`, rejection of embedded quote fabrications (`EMBEDDED_FABRICATION`) & metric mismatches, rejection of token overlap alone for `SOURCE_FACT`, multi-page citation checking, idempotent apply with duplicate prevention, Groq 429/503 error handling, unpaginated `page_number=None` attribution, and reviewer attribution schema & persistence | 14 | PostgreSQL 16 | Unit Mocks + Regression Tests |
| `test_document_intake_pipeline.py` | Phase 2D.1: Multi-page PDF parsing & page preservation, invalid PDF rejection, pasted text normalization, RFC 5322 email parsing, malformed email handling, exact/normalized citation validation, fabricated citation rejection & numeric mismatch, 16-parameter schema, missing/conflicting status tags, PostgreSQL review & persistence cycle, cross-user authorization isolation (403), plus 1 opt-in live Groq test (`@pytest.mark.live_provider`) | 12 (11 auto + 1 live) | PostgreSQL 16 | Unit Mocks + Opt-In Live Groq |
| `test_admin_provisioning_and_ownership.py` | Phase 2C.4: Production login non-seeding (Test 1), deleted admin non-recreation (Test 2), development demo seeding isolation (Test 3), CLI & service admin provisioning (Test 4), non-overwrite of existing passwords (Test 5), missing secrets safe failure (Test 6), non-admin ownership assignment rejection (Test 7), inactive/nonexistent target account rejection (Test 8), QA_APPROVER assignment rejection / segregation of duties (Test 9), reason validation & whitespace rejection (Test 10), valid assignment with audit logging (Test 11), transaction rollback on failure (Test 12) | 12 | PostgreSQL 16 | N/A |
| `test_security_authorization.py` | Phase 2C.3: Mandatory auth rejection (401), invalid/expired token rejection, cross-user investigation isolation (403), cross-user evidence isolation (403), single-owner creation binding, QA approval role enforcement (403 for non-QA), secure evidence download auth, unassigned legacy record non-mutation & QA/Admin read-only access (Test 17), admin owner assignment endpoint & audit logging (Test 18), CORS allowlist and wildcard rejection (Test 19) | 19 | PostgreSQL 16 | N/A |
| `test_remediation_p1_p2_p3.py` | Phase 2C.1 & 2D.2.2.2: File persistence/download, SHA-256 tamper detection (409), extracted text immutability (400), contradiction disposition workflow & rationale, evidence soft archival & retention, LangGraph runtime source citation validation, fabricated citation rejection, upload validation guards (size, magic bytes, path traversal), reviewer authentication & user identity binding with separation of duties | 9 | PostgreSQL 16 | Unit Mocks / LangGraph Engine |
| `test_evidence_traceability.py` | Phase 2C & 2D.2.2.2: Evidence ingestion (SHA-256, classification, size), page-level PDF parsing, gap auto-detection, investigator responses, explicit gap resolution, evidence linking, cross-investigation isolation, contradictory evidence rejection, human confirmation workflow with QA approver role and separation of duties | 9 | PostgreSQL 16 | N/A |
| `test_postgres_database.py` | Connection, PostgreSQL 16 version, Alembic revision (`ae9dda31c187`), 16-table relational persistence, FK constraints | 3 | PostgreSQL 16 (Port 5432) | N/A |
| `test_document_parser.py` | PyPDF text extraction, RFC 5322 MIME email parsing, text normalization | 3 | N/A | N/A |
| `test_groq_and_workflow.py` | Intake extraction, 6M RCA causal analysis, 13-node LangGraph pipeline (deterministic mock boundaries, success & AI_UNAVAILABLE paths) | 3 | N/A | Unit Mocks / LangGraph Engine |
| `test_api_endpoints.py` | FastAPI `/health`, authenticated `/investigations`, `/intake/parse-text`, `/intake/apply-to-investigation`, `/copilot/generate-rca`, `/copilot/apply-rca-to-investigation`, QA approval, audit logs (end-to-end PostgreSQL lifecycle with mocked provider boundary) | 2 | PostgreSQL 16 | Unit Mocks / Structured Engine |
| `test_release_hardening.py` | Release Hardening: Fail-fast configuration security, mandatory explicit `SECRET_KEY` (>= 32 chars, placeholder rejection), test-isolation preservation, non-leaking exception messages, production development credential rejection, database startup non-DDL verification, production `init_db` DDL prohibition, live connection check, demo-login production isolation, and frontend config reporting | 13 | PostgreSQL 16 | N/A |
| `test_ai_remediation.py` | Tests A-N: Groq initialization, request-scoped failover (Test C), invalid model/rate errors, structured validation, 13 LangGraph nodes (Test G), conditional routing (Test H), missing/conflicting evidence, traceability, deduplication, non-fabrication rule, graceful degradation, plus 1 opt-in live test (`@pytest.mark.live_provider`) | 14 (13 auto + 1 live) | PostgreSQL 16 (optional) | Unit Mocks + Opt-In Live Groq |
| **Total Test Suite** | **Comprehensive Full System Verification** | **166 (164 Auto + 2 Live)** | **PostgreSQL 16** | **Mocked Provider + Opt-In Live** |


---

## 4. Failure & Blocked Condition Handling

- **PostgreSQL Container Offline**: If `docker compose up -d db` has not been executed, `test_postgres_database.py` fails immediately with an explicit status message:
  ```
  BLOCKED: PostgreSQL 16 is not reachable on localhost:5432. Start container via 'docker compose up -d db'.
  ```
- **Silent Fallbacks Strictly Prohibited**: Tests never silently switch to SQLite when PostgreSQL is the configured target.


# AIVOA.AI RCA Intelligence – Database Schema Documentation

**Target Database Engine:** PostgreSQL 16 (Containerized via `postgres:16-alpine`)  
**ORM / Data Access:** SQLAlchemy 2.0 (AsyncIO with `asyncpg`)  
**Migration Tool:** Alembic (Async runner)  
**Current Active Revision:** `ae9dda31c187` (`phase_2d_2_2_2_security_evidence_provenance`)  

---

## 1. Architecture & Connection Configuration

- **Host:** `localhost` (or `db` within Docker network)
- **Port:** `5432`
- **Database:** `aivoa_rca`
- **User:** `aivoa_user`
- **Driver:** `postgresql+asyncpg`
- **Connection URL:** `postgresql+asyncpg://aivoa_user:your_secure_db_password_here@localhost:5432/aivoa_rca`
- **Fail-Fast Compliance:** Automatic SQLite fallback has been completely removed from application runtime. If PostgreSQL is offline, FastAPI fails immediately with an actionable instruction to start the database container (`docker compose up -d db`).

---

## 2. Entity Relationship Overview

```mermaid
erDiagram
    users ||--o{ investigations : "lead investigator / QA approver"
    users ||--o{ audit_logs : "performed action"
    users ||--o{ contradiction_dispositions : "dismissed contradiction"
    users ||--o{ five_whys_steps : "verified step"
    users ||--o{ fishbone_causes : "verified cause"
    users ||--o{ root_causes : "confirmed / rejected root cause"
    investigations ||--|| deviations : "has deviation details"
    investigations ||--o{ evidences : "contains supporting evidence"
    investigations ||--o{ evidence_gaps : "tracks missing information"
    investigations ||--o{ investigation_findings : "identifies factual findings"
    investigations ||--o{ five_whys_steps : "contains causal 5 Whys chain"
    investigations ||--o{ fishbone_causes : "maps 6M Ishikawa factors"
    investigations ||--o{ root_causes : "evaluates confirmed causes"
    investigations ||--o{ capa_actions : "establishes corrective actions"
    investigations ||--o{ ai_interactions : "records model traces"
    investigations ||--o{ audit_logs : "records compliance audit trail"
    five_whys_steps ||--o{ five_whys_evidence_links : "corroborated / contradicted by"
    evidences ||--o{ five_whys_evidence_links : "linked to why step"
    fishbone_causes ||--o{ fishbone_evidence_links : "corroborated / contradicted by"
    evidences ||--o{ fishbone_evidence_links : "linked to fishbone cause"
    fishbone_causes ||--o| root_causes : "promoted to"
    root_causes ||--o{ root_cause_evidence_links : "corroborated / contradicted by"
    evidences ||--o{ root_cause_evidence_links : "linked to root cause"
    evidences ||--o{ evidence_gaps : "resolves"
    root_causes ||--o{ capa_actions : "mitigated by"
    root_causes ||--o{ contradiction_dispositions : "has dismissed contradictions"
    evidences ||--o{ contradiction_dispositions : "dismissed as contradiction"
```

---

## 3. Relational Table Specifications

### 3.1 `users`
Stores pharmaceutical quality investigators, QA approvers, and system administrators.
- `id` (INTEGER, Primary Key, autoincrement, indexed)
- `username` (VARCHAR(50), Unique, Not Null, indexed)
- `email` (VARCHAR(100), Unique, Not Null, indexed)
- `full_name` (VARCHAR(100), Not Null)
- `role` (VARCHAR(50), Default: `'INVESTIGATOR'`) — `'INVESTIGATOR'`, `'QA_APPROVER'`, `'ADMIN'`
- `department` (VARCHAR(100), Default: `'Quality Assurance'`)
- `hashed_password` (VARCHAR(255), Nullable) — PBKDF2-HMAC-SHA256 hashed password (100,000 rounds)
- `is_active` (BOOLEAN, Default: `True`, Not Null) — Active status flag; inactive accounts cannot authenticate or be assigned investigation ownership. *Integrity Note:* Physical deletion of users is prohibited in production to prevent dangling foreign key references; user revocation is performed exclusively via soft deactivation (`is_active = False`).
- `created_at` (TIMESTAMP WITHOUT TIME ZONE, Default: UTC now)

### 3.2 `investigations`
Parent container representing an end-to-end Root Cause Analysis investigation.
- `id` (INTEGER, Primary Key, autoincrement, indexed)
- `investigation_number` (VARCHAR(50), Unique, Not Null, indexed) e.g., `INV-2026-001`
- `title` (VARCHAR(255), Not Null)
- `status` (VARCHAR(50), Default: `'IN_INVESTIGATION'`) — `'DRAFT'`, `'IN_INVESTIGATION'`, `'PENDING_QA_REVIEW'`, `'APPROVED'`, `'REJECTED'`
- `stage` (VARCHAR(50), Default: `'INTAKE'`) — `'INTAKE'`, `'INVESTIGATION'`, `'ROOT_CAUSE'`, `'CAPA'`, `'APPROVAL'`
- `lead_investigator` (VARCHAR(100), Default: `'Lead Investigator'`) — Human-readable display name
- `lead_investigator_id` (INTEGER, Nullable, Foreign Key -> `users.id` ON DELETE SET NULL)
- `qa_approver` (VARCHAR(100), Nullable) — Human-readable sign-off name
- `qa_approver_id` (INTEGER, Nullable, Foreign Key -> `users.id` ON DELETE SET NULL)
- `is_approved` (BOOLEAN, Default: `False`)
- `approval_date` (TIMESTAMP WITHOUT TIME ZONE, Nullable)
- `approval_comments` (TEXT, Nullable)
- `created_at` (TIMESTAMP WITHOUT TIME ZONE, Default: UTC now)
- `updated_at` (TIMESTAMP WITHOUT TIME ZONE, Default: UTC now)

### 3.3 `deviations`
Captures batch, equipment, and event parameters for the manufacturing deviation.
- `id` (INTEGER, Primary Key, autoincrement, indexed)
- `investigation_id` (INTEGER, Not Null, Foreign Key -> `investigations.id` ON DELETE CASCADE)
- `deviation_number` (VARCHAR(50), Not Null, indexed) e.g., `DEV-2026-084`
- `deviation_type` (VARCHAR(50), Default: `'MAJOR'`) — `'CRITICAL'`, `'MAJOR'`, `'MINOR'`
- `severity` (VARCHAR(50), Default: `'High'`)
- `batch_number` (VARCHAR(100), Not Null, indexed)
- `product_name` (VARCHAR(200), Not Null)
- `unit_operation` (VARCHAR(100), Nullable) e.g., `Crystallization`, `Centrifugation`
- `equipment_id` (VARCHAR(100), Nullable) e.g., `RX-301`
- `bpr_number` (VARCHAR(100), Nullable)
- `target_yield_kg` (DOUBLE PRECISION / FLOAT, Nullable)
- `actual_yield_kg` (DOUBLE PRECISION / FLOAT, Nullable)
- `occurrence_datetime` (TIMESTAMP WITHOUT TIME ZONE, Nullable)
- `detection_datetime` (TIMESTAMP WITHOUT TIME ZONE, Nullable)
- `description` (TEXT, Not Null)
- `immediate_containment` (TEXT, Nullable)
- `is_ai_populated` (BOOLEAN, Default: `True`)
- `is_verified` (BOOLEAN, Default: `False`)
- `created_at` (TIMESTAMP WITHOUT TIME ZONE, Default: UTC now)
- `updated_at` (TIMESTAMP WITHOUT TIME ZONE, Default: UTC now)

### 3.4 `evidences`
Raw or extracted technical attachments, log files, and SCADA trend references with cryptographic data integrity and source localization.
- `id` (INTEGER, Primary Key, autoincrement, indexed)
- `investigation_id` (INTEGER, Not Null, Foreign Key -> `investigations.id` ON DELETE CASCADE)
- `title` (VARCHAR(200), Not Null)
- `evidence_type` (VARCHAR(50), Nullable) — `'DOCUMENT'`, `'LOGBOOK'`, `'BATCH_RECORD'`, `'SENSOR_LOG'`, `'EMAIL'`, `'PHOTO'`, `'CALIBRATION_CERT'`
- `source` (VARCHAR(255), Nullable)
- `original_filename` (VARCHAR(255), Nullable)
- `file_path` (VARCHAR(500), Nullable)
- `file_size_bytes` (INTEGER, Nullable)
- `file_hash_sha256` (VARCHAR(64), Nullable, indexed) — Cryptographic SHA-256 checksum
- `classification` (VARCHAR(50), Default: `'PRIMARY_SOURCE'`) — `'PRIMARY_SOURCE'`, `'CORROBORATING'`, `'ANALYTICAL_DATA'`, `'HISTORICAL_RECORD'`, `'PHYSICAL_EXHIBIT'`
- `source_location` (VARCHAR(255), Nullable) — e.g., `'Page 3, Section 4.2'`
- `page_number` (INTEGER, Nullable)
- `extracted_text` (TEXT, Nullable)
- `source_metadata` (JSON, Nullable)
- `confidence_score` (DOUBLE PRECISION, Default: `1.0`)
- `is_verified` (BOOLEAN, Default: `False`)
- `verified_by` (VARCHAR(100), Nullable)
- `verified_by_user_id` (INTEGER, Nullable, Foreign Key -> `users.id` ON DELETE SET NULL, indexed) — Authenticated user who verified the evidence
- `verification_date` (TIMESTAMP WITHOUT TIME ZONE, Nullable)
- `uploaded_by_user_id` (INTEGER, Nullable, Foreign Key -> `users.id` ON DELETE SET NULL, indexed) — Authenticated user who uploaded/created the evidence. *Legacy Fail-Closed Note:* While nullable in the schema to support pre-migration records, the application enforces a strict fail-closed authorization policy: legacy records where `uploaded_by_user_id IS NULL` can ONLY be verified by `QA_APPROVER` or `ADMIN` roles; ordinary investigators receive HTTP 403 Forbidden.
- `investigator_notes` (TEXT, Nullable)
- `is_archived` (BOOLEAN, Default: `False`, Not Null) — Soft-archival flag replacing hard deletion
- `archived_at` (TIMESTAMP WITHOUT TIME ZONE, Nullable) — Timestamp when record was archived
- `archived_by` (VARCHAR(100), Nullable) — Investigator/user who archived the record
- `archival_reason` (TEXT, Nullable) — Justification for archival
- `created_at` (TIMESTAMP WITHOUT TIME ZONE, Default: UTC now)
- `updated_at` (TIMESTAMP WITHOUT TIME ZONE, Default: UTC now)

### 3.5 `investigation_findings`
Discrete factual statements derived from evidence.
- `id` (INTEGER, Primary Key, autoincrement, indexed)
- `investigation_id` (INTEGER, Not Null, Foreign Key -> `investigations.id` ON DELETE CASCADE)
- `evidence_id` (INTEGER, Nullable, Foreign Key -> `evidences.id` ON DELETE SET NULL, indexed)
- `reviewed_by_id` (INTEGER, Nullable, Foreign Key -> `users.id` ON DELETE SET NULL, indexed) — Authenticated investigator who reviewed the finding
- `finding_text` (TEXT, Not Null)
- `finding_type` (VARCHAR(50), Default: `'FACTUAL_EVIDENCE'`)
- `evidence_reference` (VARCHAR(255), Nullable)
- `source_location` (VARCHAR(100), Nullable)
- `citation_verified` (BOOLEAN, Default: `False`, Not Null) — Verifies citation exists verbatim/normalized in source documents
- `validation_status` (VARCHAR(50), Nullable) — `'VERIFIED_SOURCE_FACT'`, `'AI_INFERENCE'`, `'CONFLICTING_INFORMATION'`, `'UNVERIFIED'`
- `is_ai_suggested` (BOOLEAN, Default: `True`)
- `is_verified` (BOOLEAN, Default: `False`)
- `is_accepted` (BOOLEAN, Default: `False`, Not Null) — Mandatory human review acceptance flag (never defaults to True)
- `user_edited` (BOOLEAN, Default: `False`, Not Null) — Flags whether the investigator edited the field during review
- `reviewed_at` (TIMESTAMP WITHOUT TIME ZONE, Nullable) — Timestamp when investigator reviewed and accepted the finding
- `original_finding_text` (TEXT, Nullable) — Preserves the raw extracted AI value prior to investigator edits
- `created_at` (TIMESTAMP WITHOUT TIME ZONE, Default: UTC now)

### 3.6 `five_whys_steps`
Sequential causal breakdown steps connecting surface symptoms to systemic failure points (supports dynamic depth beyond 5).
- `id` (INTEGER, Primary Key, autoincrement, indexed)
- `investigation_id` (INTEGER, Not Null, Foreign Key -> `investigations.id` ON DELETE CASCADE)
- `step_number` (INTEGER, Not Null) — Dynamic step ordering (1, 2, 3, 4, 5, 6, ...)
- `question` (VARCHAR(500), Not Null)
- `answer` (TEXT, Not Null)
- `evidence_reference` (VARCHAR(255), Nullable)
- `is_ai_suggested` (BOOLEAN, Default: `True`)
- `is_verified` (BOOLEAN, Default: `False`)
- `verified_by_user_id` (INTEGER, Nullable, Foreign Key -> `users.id` ON DELETE SET NULL)
- `verified_at` (TIMESTAMP WITHOUT TIME ZONE, Nullable)
- `verification_notes` (TEXT, Nullable)
- `created_at` (TIMESTAMP WITHOUT TIME ZONE, Default: UTC now)
- `updated_at` (TIMESTAMP WITHOUT TIME ZONE, Default: UTC now)

### 3.7 `five_whys_evidence_links`
Junction entity connecting empirical evidence records to 5-Whys causal steps.
- `id` (INTEGER, Primary Key, autoincrement, indexed)
- `five_whys_step_id` (INTEGER, Not Null, Foreign Key -> `five_whys_steps.id` ON DELETE CASCADE)
- `evidence_id` (INTEGER, Not Null, Foreign Key -> `evidences.id` ON DELETE CASCADE)
- `relationship_type` (VARCHAR(50), Default: `'SUPPORTING'`) — `'SUPPORTING'`, `'CONTRADICTORY'`
- `relevance_explanation` (TEXT, Nullable)
- `confidence_rating` (VARCHAR(20), Default: `'HIGH'`) — `'HIGH'`, `'MEDIUM'`, `'LOW'`
- `created_at` (TIMESTAMP WITHOUT TIME ZONE, Default: UTC now)
- *Constraint:* Unique on `(five_whys_step_id, evidence_id, relationship_type)`

### 3.8 `fishbone_causes`
Ishikawa 6M category factors (Man, Machine, Material, Method, Measurement, Milieu).
- `id` (INTEGER, Primary Key, autoincrement, indexed)
- `investigation_id` (INTEGER, Not Null, Foreign Key -> `investigations.id` ON DELETE CASCADE)
- `category` (VARCHAR(50), Not Null) — `'MAN'`, `'MACHINE'`, `'MATERIAL'`, `'METHOD'`, `'MEASUREMENT'`, `'MILIEU'`
- `cause_description` (VARCHAR(500), Not Null)
- `status` (VARCHAR(50), Default: `'HYPOTHESIS'`) — `'HYPOTHESIS'`, `'VERIFIED'`, `'RULED_OUT'`
- `rationale` (TEXT, Nullable)
- `evidence_reference` (VARCHAR(255), Nullable)
- `is_ai_suggested` (BOOLEAN, Default: `True`)
- `is_verified` (BOOLEAN, Default: `False`)
- `verified_by_user_id` (INTEGER, Nullable, Foreign Key -> `users.id` ON DELETE SET NULL)
- `verified_at` (TIMESTAMP WITHOUT TIME ZONE, Nullable)
- `verification_notes` (TEXT, Nullable)
- `promoted_to_root_cause_id` (INTEGER, Nullable, Foreign Key -> `root_causes.id` ON DELETE SET NULL)
- `created_at` (TIMESTAMP WITHOUT TIME ZONE, Default: UTC now)
- `updated_at` (TIMESTAMP WITHOUT TIME ZONE, Default: UTC now)

### 3.9 `fishbone_evidence_links`
Junction entity connecting empirical evidence records to Fishbone cause hypotheses.
- `id` (INTEGER, Primary Key, autoincrement, indexed)
- `fishbone_cause_id` (INTEGER, Not Null, Foreign Key -> `fishbone_causes.id` ON DELETE CASCADE)
- `evidence_id` (INTEGER, Not Null, Foreign Key -> `evidences.id` ON DELETE CASCADE)
- `relationship_type` (VARCHAR(50), Default: `'SUPPORTING'`) — `'SUPPORTING'`, `'CONTRADICTORY'`
- `relevance_explanation` (TEXT, Nullable)
- `confidence_rating` (VARCHAR(20), Default: `'HIGH'`) — `'HIGH'`, `'MEDIUM'`, `'LOW'`
- `created_at` (TIMESTAMP WITHOUT TIME ZONE, Default: UTC now)
- *Constraint:* Unique on `(fishbone_cause_id, evidence_id, relationship_type)`

### 3.10 `root_causes`
Evaluated root causes classified by ICH Q9 / GAMP categories with provenance and human confirmation tracking.
- `id` (INTEGER, Primary Key, autoincrement, indexed)
- `investigation_id` (INTEGER, Not Null, Foreign Key -> `investigations.id` ON DELETE CASCADE)
- `cause_statement` (TEXT, Not Null)
- `category` (VARCHAR(100), Nullable) — e.g. `'EQUIPMENT_FAILURE'`, `'PROCEDURE'`, `'RAW_MATERIAL'`, `'HUMAN_ERROR'`, `'SYSTEMIC'`
- `is_primary` (BOOLEAN, Default: `True`)
- `status` (VARCHAR(50), Default: `'PROPOSED'`) — `'PROPOSED'`, `'UNDER_REVIEW'`, `'CONFIRMED'`, `'REJECTED'`
- `rationale` (TEXT, Nullable)
- `evidence_summary` (TEXT, Nullable)
- `is_ai_suggested` (BOOLEAN, Default: `True`)
- `is_verified` (BOOLEAN, Default: `False`)
- `investigator_notes` (TEXT, Nullable)
- `source_type` (VARCHAR(50), Default: `'DIRECT_SYNTHESIS'`) — `'FIVE_WHYS'`, `'FISHBONE'`, `'DIRECT_SYNTHESIS'`, `'MANUAL'`
- `source_id` (INTEGER, Nullable)
- `confirmed_by` (VARCHAR(100), Nullable)
- `confirmed_by_user_id` (INTEGER, Nullable, Foreign Key -> `users.id` ON DELETE SET NULL)
- `confirmed_at` (TIMESTAMP WITHOUT TIME ZONE, Nullable)
- `rejection_reason` (TEXT, Nullable)
- `rejected_by` (VARCHAR(100), Nullable)
- `rejected_by_user_id` (INTEGER, Nullable, Foreign Key -> `users.id` ON DELETE SET NULL)
- `rejected_at` (TIMESTAMP WITHOUT TIME ZONE, Nullable)
- `created_at` (TIMESTAMP WITHOUT TIME ZONE, Default: UTC now)
- `updated_at` (TIMESTAMP WITHOUT TIME ZONE, Default: UTC now)

### 3.11 `root_cause_evidence_links`
Junction entity explicitly connecting empirical evidence records to root cause hypotheses.
- `id` (INTEGER, Primary Key, autoincrement, indexed)
- `root_cause_id` (INTEGER, Not Null, Foreign Key -> `root_causes.id` ON DELETE CASCADE)
- `evidence_id` (INTEGER, Not Null, Foreign Key -> `evidences.id` ON DELETE CASCADE)
- `relationship_type` (VARCHAR(50), Default: `'SUPPORTING'`) — `'SUPPORTING'`, `'CONTRADICTORY'`
- `relevance_explanation` (TEXT, Nullable)
- `confidence_rating` (VARCHAR(20), Default: `'HIGH'`) — `'HIGH'`, `'MEDIUM'`, `'LOW'`
- `created_at` (TIMESTAMP WITHOUT TIME ZONE, Default: UTC now)
- *Constraint:* Unique on `(root_cause_id, evidence_id, relationship_type)`

### 3.12 `evidence_gaps`
Tracks missing empirical documents, batch records, and investigator clarifications.
- `id` (INTEGER, Primary Key, autoincrement, indexed)
- `investigation_id` (INTEGER, Not Null, Foreign Key -> `investigations.id` ON DELETE CASCADE)
- `root_cause_id` (INTEGER, Nullable, Foreign Key -> `root_causes.id` ON DELETE SET NULL)
- `category` (VARCHAR(100), Default: `'MISSING_RECORD'`) — e.g., `'CALIBRATION_RECORDS'`, `'RAW_MATERIAL_COA'`, `'CLEANING_LOG'`
- `question` (TEXT, Not Null)
- `impact_description` (TEXT, Nullable)
- `suggested_record` (VARCHAR(255), Nullable)
- `urgency` (VARCHAR(20), Default: `'HIGH'`) — `'CRITICAL'`, `'HIGH'`, `'MEDIUM'`, `'LOW'`
- `investigator_response` (TEXT, Nullable)
- `response_timestamp` (TIMESTAMP WITHOUT TIME ZONE, Nullable)
- `responded_by` (VARCHAR(100), Nullable)
- `is_resolved` (BOOLEAN, Default: `False`)
- `resolving_evidence_id` (INTEGER, Nullable, Foreign Key -> `evidences.id` ON DELETE SET NULL)
- `created_at` (TIMESTAMP WITHOUT TIME ZONE, Default: UTC now)
- `updated_at` (TIMESTAMP WITHOUT TIME ZONE, Default: UTC now)

### 3.13 `capa_actions`
Action items designed to isolate immediate non-conformity and eliminate recurrence.
- `id` (INTEGER, Primary Key, autoincrement, indexed)
- `investigation_id` (INTEGER, Not Null, Foreign Key -> `investigations.id` ON DELETE CASCADE)
- `root_cause_id` (INTEGER, Nullable, Foreign Key -> `root_causes.id` ON DELETE SET NULL)
- `action_type` (VARCHAR(50), Not Null) — `'CORRECTION'`, `'CORRECTIVE_ACTION'`, `'PREVENTIVE_ACTION'`
- `description` (TEXT, Not Null)
- `rationale` (TEXT, Nullable)
- `owner` (VARCHAR(100), Nullable)
- `deadline` (VARCHAR(50), Nullable)
- `effectiveness_criteria` (TEXT, Nullable)
- `effectiveness_review_period_days` (INTEGER, Default: `30`)
- `status` (VARCHAR(50), Default: `'PROPOSED'`) — Lifecycle states: `'PROPOSED'`, `'APPROVED'`, `'IN_PROGRESS'`, `'COMPLETED'`, `'EFFECTIVENESS_VERIFIED'` (Legacy aliases `'OPEN'` -> `'PROPOSED'`, `'CLOSED'` -> `'COMPLETED'`)
- `is_ai_suggested` (BOOLEAN, Default: `False`)
- `is_verified` (BOOLEAN, Default: `False`) — Server-controlled boolean set to `True` strictly upon formal QA approval (`POST /capas/{id}/approve`)
- `created_at` (TIMESTAMP WITHOUT TIME ZONE, Default: UTC now)
- `updated_at` (TIMESTAMP WITHOUT TIME ZONE, Default: UTC now)

**Lifecycle & Integrity Constraints:**
1. **Initial State:** All new manual or AI-suggested CAPAs are initialized in `PROPOSED` status with `is_verified=False`. Client forgery of verification metadata is rejected with HTTP 400.
2. **Root Cause Referential Guard:** If linked to a `root_cause_id`, the target root cause must exist, belong to the same investigation, and not be marked `REJECTED`. Cross-investigation links are rejected with HTTP 400.
3. **Formal Approval:** Only `QA_APPROVER` or `ADMIN` can formally approve (`POST /capas/{id}/approve`). Assigned lead investigators cannot approve CAPAs for their own investigations (Separation of Duties).
4. **Implementation & Completion:** Work cannot begin (`IN_PROGRESS`) or complete (`COMPLETED`) without prior QA approval. Completion requires valid implementation rationale/notes.
5. **Effectiveness Verification:** Requires `QA_APPROVER` or `ADMIN`, `COMPLETED` status, and defined quantitative effectiveness criteria. Sets `status="EFFECTIVENESS_VERIFIED"`.
6. **Regulatory Locking:** Once in `EFFECTIVENESS_VERIFIED` status, records are immutable against general updates and protected against deletion (HTTP 400).
7. **Audit Logging & Transaction Integrity:** All lifecycle events (`CREATED`, `UPDATED`, `APPROVED`, `COMPLETED`, `EFFECTIVENESS_VERIFIED`, `DELETED`) generate explicit `AuditLog` records and commit transactions.

### 3.14 `ai_interactions`
Audit trail of LLM and LangGraph workflow prompts, token counts, and responses.
- `id` (INTEGER, Primary Key, autoincrement, indexed)
- `investigation_id` (INTEGER, Not Null, Foreign Key -> `investigations.id` ON DELETE CASCADE)
- `interaction_type` (VARCHAR(50), Not Null) — `'INTAKE_EXTRACTION'`, `'FIVE_WHYS'`, `'FISHBONE'`, `'CAPA'`, `'COPILOT_CHAT'`
- `prompt_summary` (TEXT, Nullable)
- `response_data` (TEXT, Nullable)
- `model_name` (VARCHAR(100), Default: `'openai/gpt-oss-120b'`)
- `tokens_used` (INTEGER, Default: `0`)
- `created_at` (TIMESTAMP WITHOUT TIME ZONE, Default: UTC now)

### 3.15 `audit_logs`
Chronological, tamper-evident log of changes made to investigation records.
- `id` (INTEGER, Primary Key, autoincrement, indexed)
- `investigation_id` (INTEGER, Not Null, Foreign Key -> `investigations.id` ON DELETE CASCADE)
- `user_id` (INTEGER, Nullable, Foreign Key -> `users.id` ON DELETE SET NULL)
- `user_name` (VARCHAR(100), Default: `'Investigator'`)
- `action` (VARCHAR(50), Not Null) — `'CREATED'`, `'FIELD_UPDATED'`, `'AI_APPLIED'`, `'VERIFIED'`, `'APPROVED'`, `'REJECTED'`
- `entity_type` (VARCHAR(50), Not Null) — `'DEVIATION'`, `'FIVE_WHYS'`, `'FISHBONE'`, `'ROOT_CAUSE'`, `'CAPA'`, `'INVESTIGATION'`
- `entity_id` (VARCHAR(50), Nullable)
- `change_summary` (TEXT, Not Null)
- `timestamp` (TIMESTAMP WITHOUT TIME ZONE, Default: UTC now)

### 3.16 `contradiction_dispositions`
Regulatory disposition audit trail preserving scientific rationale whenever an investigator dismisses contradictory evidence from a proposed root cause.
- `id` (INTEGER, Primary Key, autoincrement, indexed)
- `root_cause_evidence_link_id` (INTEGER, Foreign Key -> `root_cause_evidence_links.id` ON DELETE CASCADE)
- `root_cause_id` (INTEGER, Not Null, Foreign Key -> `root_causes.id` ON DELETE CASCADE)
- `evidence_id` (INTEGER, Not Null, Foreign Key -> `evidences.id` ON DELETE CASCADE)
- `investigator_id` (INTEGER, Nullable, Foreign Key -> `users.id` ON DELETE SET NULL)
- `investigator_name` (VARCHAR(100), Not Null)
- `scientific_rationale` (TEXT, Not Null) — Mandatory scientific explanation justifying why the evidence is not exclusionary
- `dismissed_at` (TIMESTAMP WITHOUT TIME ZONE, Default: UTC now)

---

## 4. Migration Management via Alembic

### 4.1 Applying Migrations
To upgrade PostgreSQL to the latest migration revision:
```bash
cd backend
alembic upgrade head
```

### 4.2 Checking Current Migration Status
```bash
cd backend
alembic current
```

### 4.3 Migration History
1. `e9e38a07f832` (Initial schema with PostgreSQL models)
2. `c89fbf7d80b8` (Phase 2C — evidence management, soft archival, contradiction dispositions)
3. `6d1518e3b3e9` (Phase 2C.1 — critical remediation, audit user relationships)
4. `98ea1c729df4` (Phase 2C.4 — add User.is_active flag)
5. `a1b2c3d4e5f6` (Phase 2D.1.1 — add reviewer attribution and acceptance tracking on investigation_findings: `reviewed_by_id`, `is_accepted`, `user_edited`, `reviewed_at`, `original_finding_text`)

### 4.4 Generating Future Migrations
When modifying models in `backend/app/models/`:
```bash
cd backend
alembic revision --autogenerate -m "Describe schema change"
alembic upgrade head
```


# AIVOA.AI RCA Intelligence – API Contracts Specification

**Base URL:** `/api/v1`  
**Protocol:** REST (JSON over HTTP)  
**Authentication & Authorization:**
- Mandatory Bearer Token (`Authorization: Bearer <token>`) required on all operational endpoints.
- Unauthenticated requests return `401 Unauthorized`.
- Investigation Isolation: Users can access only investigations and child records they own (`lead_investigator_id == current_user.id`). Unauthorized access returns `403 Forbidden`. Legacy unassigned investigations (`lead_investigator_id IS NULL`) are strictly read-only for `QA_APPROVER` and `ADMIN`, and return `403 Forbidden` to non-admin investigators without mutating ownership.
- Role-Based Access Control: QA approval endpoints strictly require `QA_APPROVER` or `ADMIN` role. Ownership assignment strictly requires `ADMIN`. Unauthorized roles return `403 Forbidden`.
- CORS Policy: Governed by `CORS_ORIGINS` allowlist (`settings.cors_origins`). Wildcard `*` is explicitly disallowed with credentials. Methods restricted to `GET`, `POST`, `PUT`, `DELETE`, `OPTIONS`.

---

## 0. Authentication Endpoints

### 0.1 User Login
- **Route:** `POST /auth/login`
- **Request:**
  ```json
  {
    "username": "lead_investigator",
    "password": "AivoaPass2026!"
  }
  ```
- **Response:** `200 OK`
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer",
    "expires_in": 28800,
    "user_id": 1,
    "username": "lead_investigator",
    "role": "INVESTIGATOR"
  }
  ```
- **Error Responses:**
  - `401 Unauthorized`: Invalid username/password, or account is inactive (`is_active == false`).
- **Production Isolation:** Default administrator provisioning via login is eliminated. Demo accounts are seeded strictly when `ENVIRONMENT in ("development", "test")`. Initial production administrators are provisioned via CLI (`python -m app.cli provision-admin`) or `INITIAL_ADMIN_*` configuration.

### 0.2 Get Current User
- **Route:** `GET /auth/me`
- **Headers:** `Authorization: Bearer <token>`
- **Response:** `200 OK` (Returns user profile: `id`, `username`, `email`, `full_name`, `role`, `department`)

### 0.3 User Lifecycle & Account Deactivation Policy
- **Physical Deletion Blocked:** User accounts cannot be physically deleted from the database in production. Physical deletion is prohibited to preserve relational integrity across foreign keys (`uploaded_by_user_id`, `verified_by_user_id`, `lead_investigator_id`, `qa_approver_id`, and `audit_logs.user_id`).
- **Soft Deactivation:** Inactivation is executed by toggling `is_active = false`. Deactivated users are rejected at authentication (`POST /auth/login` returns `401 Unauthorized`) and cannot be assigned ownership of investigations (`POST /investigations/{id}/assign-owner` returns `400 Bad Request`). Historical records and signatures created by deactivated accounts remain fully attributable.

---

## 1. Investigation Endpoints

### 1.1 List Investigations
- **Route:** `GET /investigations/`
- **Headers:** `Authorization: Bearer <token>`
- **Query Params:** `skip` (default 0), `limit` (default 50), `status` (optional)
- **Behavior:** Returns only investigations owned by `current_user.id` (or all investigations for `ADMIN` / `QA_APPROVER`).
- **Response:** `200 OK`
  ```json
  [
    {
      "id": 1,
      "investigation_number": "INV-2026-001",
      "title": "Deviation in Batch B2026-API-044 Temperature Excursion",
      "status": "IN_INVESTIGATION",
      "stage": "INVESTIGATION",
      "lead_investigator": "Dr. Sarah Lin (Lead Investigator)",
      "lead_investigator_id": 1,
      "qa_approver_id": null,
      "is_approved": false,
      "created_at": "2026-11-04T12:00:00Z",
      "updated_at": "2026-11-04T12:05:00Z",
      "deviation_number": "DEV-2026-084",
      "batch_number": "B2026-API-044",
      "product_name": "Atorvastatin Calcium Trihydrate API",
      "severity": "High"
    }
  ]
  ```

### 1.2 Create Investigation
- **Route:** `POST /investigations/`
- **Headers:** `Authorization: Bearer <token>`
- **Request:**
  ```json
  {
    "title": "Crystallization Thermal Spike Investigation",
    "lead_investigator": "Dr. Sarah Lin"
  }
  ```
- **Behavior:** Automatically sets `lead_investigator_id = current_user.id` from token.
- **Response:** `200 OK` (Full `InvestigationRead` object)

### 1.3 Get Investigation by ID
- **Route:** `GET /investigations/{id}`
- **Headers:** `Authorization: Bearer <token>`
- **Behavior:** Verifies caller ownership via `verify_investigation_access`. Returns `403 Forbidden` if owned by another user.
- **Response:** `200 OK` (Returns investigation with nested `deviation`, `five_whys`, `fishbone_causes`, `root_causes`, `capa_actions`, `evidences`, `findings`)

### 1.4 Approve Investigation
- **Route:** `POST /investigations/{id}/approve`
- **Headers:** `Authorization: Bearer <token>`
- **Security:** Requires `current_user.role in ("QA_APPROVER", "ADMIN")`. Returns `403 Forbidden` for standard investigators.
- **Request Body:**
  ```json
  {
    "approver_name": "Dr. Elena Rostova (QA Director)",
    "comments": "Investigation rigorously reviewed. All corrective actions verified."
  }
  ```
- **Behavior:** Binds `qa_approver_id = current_user.id`. Marks `is_approved=True`, `status="APPROVED"`.
- **Response:** `200 OK`

### 1.5 Assign Investigation Owner (Admin Only)
- **Route:** `POST /investigations/{id}/assign-owner`
- **Headers:** `Authorization: Bearer <token>`
- **Security:** Requires `current_user.role == "ADMIN"`. Returns `403 Forbidden` for non-admin users.
- **Request Body:**
  ```json
  {
    "new_investigator_id": 1,
    "reason": "Official assignment to Lead Investigator"
  }
  ```
- **Validation Rules:**
  - `new_investigator_id`: Target user must exist (`404 Not Found`).
  - Target user must be active (`is_active == true`, `400 Bad Request` if inactive).
  - Target user must have role `'INVESTIGATOR'` (`400 Bad Request` if `'QA_APPROVER'` or other role, preserving segregation of duties).
  - `reason`: Mandatory string, `min_length=10`. Blank or whitespace-only strings rejected with `422 Unprocessable Entity`.
- **Behavior:** Reassigns `lead_investigator_id` to target user ID, updates `lead_investigator` string, and records an immutable audit log entry `OWNERSHIP_ASSIGNED`. Transactions are atomic: any validation failure rolls back all changes with zero partial state persistence.
- **Response:** `200 OK` (Updated `InvestigationRead` object)

---

## 2. Intake Endpoints

### 2.1 Parse Incident File
- **Route:** `POST /intake/parse-file`
- **Form Data:** `file: UploadFile` (.pdf or .txt)
- **Response:** `200 OK`
  ```json
  {
    "investigation_title": "Temperature Excursion in Atorvastatin Crystallization",
    "deviation": {
      "deviation_number": "DEV-2026-089",
      "deviation_type": "CRITICAL",
      "severity": "Critical",
      "batch_number": "B2026-API-044",
      "product_name": "Atorvastatin Calcium Trihydrate API",
      "unit_operation": "Crystallization",
      "equipment_id": "RX-301",
      "description": "Temperature spiked to 68C exceeding SOP limit of 50C due to valve actuator sticking.",
      "immediate_containment": "Quarantine mother liquor and isolate wet cake.",
      "is_ai_populated": true,
      "is_verified": false
    },
    "extracted_findings": [
      "Thermal excursion peaked at 68C for 42 minutes.",
      "Cooling valve CV-301 actuator seized in closed position."
    ],
    "missing_information": [
      {
        "category": "SENSOR_CALIBRATION",
        "question": "Provide recent RTD calibration log CAL-2026-88.",
        "impact_description": "Verifies temperature reading accuracy.",
        "urgency": "HIGH"
      }
    ],
    "recommended_immediate_actions": [
      "Isolate batch material in quarantine zone.",
      "Perform diagnostic stroke test on CV-301 actuator."
    ],
    "ai_confidence_score": 0.95,
    "source_type": "PDF"
  }
  ```

### 2.2 Parse Incident Text
- **Route:** `POST /intake/parse-text`
- **Request:**
  ```json
  {
    "content": "Incident narrative...",
    "is_email": false
  }
  ```
- **Response:** `200 OK` (Same schema as 2.1)

---

## 3. Copilot & RCA Endpoints

### 3.1 Copilot Chat
- **Route:** `POST /copilot/chat`
- **Request:**
  ```json
  {
    "investigation_id": 1,
    "message": "Why did the cooling valve actuator fail?",
    "context_stage": "ROOT_CAUSE"
  }
  ```
- **Response:** `200 OK`
  ```json
  {
    "response": "Based on the documented findings, the primary mechanism was pneumatic diaphragm fatigue...",
    "suggested_actions": ["Generate 5-Whys Analysis", "Draft CAPA Recommendations"],
    "workflow_state": { "batch": "B2026-API-044", "status": "IN_INVESTIGATION" }
  }
  ```

### 3.2 Generate RCA & CAPA
- **Route:** `POST /copilot/generate-rca`
- **Request:**
  ```json
  {
    "investigation_id": 1,
    "user_context": "Disassembly confirmed actuator diaphragm tear."
  }
  ```
- **Response:** `200 OK`
  ```json
  {
    "five_whys": [...],
    "fishbone_causes": [...],
    "root_causes": [...],
    "capa_actions": [...],
    "evidence_gaps": [...],
    "investigator_guidance": "Review 5-Whys causality chain before QA approval."
  }
  ```

---

## 4. Evidence, Methodologies & Root Cause Endpoints

### 4.1 Upload Evidence Document
- **Route:** `POST /investigations/{id}/evidences/upload`
- **Guards:** 10 MB maximum streaming file size, `%PDF` magic byte verification, filename traversal sanitization (`../` stripped).
- **Storage:** Persists raw original file into `backend/storage/evidences/{investigation_id}/{uuid}_{safe_filename}` outside public web root.
- **Form Data:** `file: UploadFile` (binary), `title: string`, `evidence_type: string`, `classification: string`
- **Response:** `200 OK` (`EvidenceRead` object with computed SHA-256 hash, byte size, page count, extracted text, and public `download_url: /api/v1/evidences/{id}/download`). Internal disk path is masked.

### 4.2 Download Evidence File
- **Route:** `GET /evidences/{id}/download`
- **Headers:** `Authorization: Bearer <token>`
- **Security & Authorization:** Enforces Bearer authentication and verifies caller has access to the parent investigation (`verify_investigation_access`). Cross-user download attempts return `403 Forbidden`.
- **Integrity Verification:** Re-reads stored file from disk and recalculates SHA-256 hash against database record.
- **Tampering Detection:** If hash does not match, returns `409 Conflict`, blocks file download, and logs tamper event in audit trail.
- **Response:** `200 OK` (Binary file stream with `Content-Disposition: attachment; filename=...`)

### 4.3 Update Evidence (Immutability Enforcement)
- **Route:** `PUT /evidences/{id}`
- **Immutability Guard:** If request payload attempts to modify `extracted_text`, returns `400 Bad Request` (`Extracted source text is immutable`).
- **Allowed Updates:** `title`, `classification`, `source_location`, `page_number`, `investigator_notes`.
- **Response:** `200 OK` (`EvidenceRead`)

### 4.4 Soft-Archive Evidence
- **Route:** `DELETE /evidences/{id}`
- **Retention Guard:** Does NOT perform physical cascade deletion. Marks `is_archived = True`, records timestamp and user ID. Preserves historical linkage.
- **Listing:** `GET /investigations/{id}/evidences` excludes archived evidence by default (use `?include_archived=true` to view).
- **Safety Restriction:** Archived evidence cannot be linked to root causes or satisfy confirmation prerequisites.
- **Response:** `200 OK` (`{"message": "Evidence record soft-archived successfully", "id": 1}`)

### 4.5 Manual Evidence Entry
- **Route:** `POST /investigations/{id}/evidences/manual`
- **Request:**
  ```json
  {
    "title": "Actuator Disassembly Logbook Entry",
    "evidence_type": "LOGBOOK",
    "classification": "PRIMARY_SOURCE",
    "extracted_text": "Diaphragm torn at circumferential clamp seam.",
    "source_location": "Logbook LB-2026-API-04, p. 14"
  }
  ```
- **Security & Integrity:** Always initializes `is_verified=false`, `verified_by=null`, and `verified_by_user_id=null` regardless of any client values provided in request payload. Automatically populates `uploaded_by_user_id=current_user.id`.
- **Response:** `200 OK` (`EvidenceRead`)

### 4.6 Verify Evidence (Investigator Sign-off)
- **Route:** `POST /evidences/{id}/verify`
- **Security, Separation of Duties & Fail-Closed Legacy Policy:**
  - **Attributable Records (`uploaded_by_user_id IS NOT NULL`):** The authenticated user who created or uploaded the record (`uploaded_by_user_id`) CANNOT self-verify their own evidence. Attempting self-verification returns `403 Forbidden` (`Separation of duties violation: Original evidence uploader cannot verify their own evidence submission. Verification requires independent review.`). Independent peer investigators, QA approvers, or admins can verify.
  - **Legacy Records (`uploaded_by_user_id IS NULL`):** Fails closed. Standard investigators and assigned lead investigators receive `403 Forbidden` (`Forbidden: Unattributable legacy evidence record requires QA_APPROVER or ADMIN authorization to verify.`). Only users with role `QA_APPROVER` or `ADMIN` may verify legacy evidence records. Historical upload attribution is never inferred or fabricated.
  - **Server-Derived Attribution:** Identity is derived strictly from the active server session (`verified_by = current_user.full_name`, `verified_by_user_id = current_user.id`). Any client-supplied name or IDs in the payload are ignored for attribution.
  - Does not require lead investigator ownership, allowing independent QA approvers or peer reviewers to perform verification.
- **Request:**
  ```json
  {
    "investigator_name": "Dr. Elena Rostova (QA Approver)",
    "verification_notes": "Cross-referenced with physical workshop bench inspection."
  }
  ```
- **Response:** `200 OK` (`is_verified=true`, `verified_by`, `verified_by_user_id`, `verification_date`)

### 4.7 Five Whys Endpoints (Dynamic Depth & Verification)
- **List Steps:** `GET /investigations/{id}/five-whys`
- **Create Step:** `POST /investigations/{id}/five-whys`
  ```json
  {
    "step_number": 6,
    "question": "Why did the preventive maintenance schedule fail to detect fatigue?",
    "answer": "PM interval for diaphragm inspection was 24 months, exceeding 12-month manufacturer fatigue cycle."
  }
  ```
- **Update Step:** `PUT /five-whys/{id}`
- **Delete Step:** `DELETE /five-whys/{id}`
  - *Conflict & Concurrency Guard:* Acquires exclusive database row-level lock (`with_for_update()`). Returns `409 Conflict` if the Five Whys step is referenced as the causal source for any active `RootCause` (`source_type="FIVE_WHYS"`, `source_id=step.id`). Serializes safely against concurrent root cause creation.
- **Link Evidence to Step:** `POST /five-whys/{id}/evidence`
  ```json
  {
    "evidence_id": 12,
    "relationship_type": "SUPPORTING",
    "relevance_explanation": "Maintenance logbook confirms 24-month inspection interval."
  }
  ```
- **Unlink Evidence:** `DELETE /five-whys/{id}/evidence/{evidence_id}`
- **Verify Step (Barrier Guard):** `POST /five-whys/{id}/verify`
  ```json
  {
    "is_verified": true,
    "verification_notes": "Confirmed against equipment maintenance qualification document."
  }
  ```
  *(Guard: Returns HTTP 400 if step does not have $\ge 1$ verified supporting evidence link.)*

### 4.8 Ishikawa Fishbone Endpoints (6Ms & Promotion)
- **List Causes:** `GET /investigations/{id}/fishbone`
- **Create Cause:** `POST /investigations/{id}/fishbone`
  ```json
  {
    "category": "MACHINE",
    "cause_description": "Mechanical seal carbon face scored allowing coolant ingress",
    "status": "HYPOTHESIS",
    "rationale": "Microscopic analysis revealed groove wear."
  }
  ```
- **Update Cause:** `PUT /fishbone/{id}`
- **Delete Cause:** `DELETE /fishbone/{id}`
  - *Conflict & Concurrency Guard:* Acquires exclusive database row-level lock (`with_for_update()`). Returns `409 Conflict` if the Fishbone cause is referenced as the causal source for any active `RootCause` (`source_type="FISHBONE"`, `source_id=cause.id`). Serializes safely against concurrent root cause creation.
- **Link Evidence to Cause:** `POST /fishbone/{id}/evidence`
  ```json
  {
    "evidence_id": 14,
    "relationship_type": "SUPPORTING",
    "relevance_explanation": "Metallurgical inspection report confirms 0.3mm radial groove."
  }
  ```
- **Unlink Evidence:** `DELETE /fishbone/{id}/evidence/{evidence_id}`
- **Verify Cause:** `POST /fishbone/{id}/verify`
  ```json
  {
    "status": "VERIFIED",
    "verification_notes": "Confirmed by metallurgical lab analysis."
  }
  ```
  *(Guard: Status `VERIFIED` requires $\ge 1$ verified supporting evidence link.)*
- **Promote Cause to Root Cause Proposal:** `POST /fishbone/{id}/promote`
  - *Concurrency & Idempotency Guard:* Uses row-level database locking (`with_for_update()`). If the cause has already been promoted (`promoted_to_root_cause_id IS NOT NULL`), returns `409 Conflict`.
  ```json
  {
    "is_primary": true,
    "category": "EQUIPMENT_FAILURE",
    "investigator_notes": "Promoted from Fishbone Machine evaluation."
  }
  ```
  *(Behavior: Creates `RootCause` with `status="PROPOSED"`, copies evidence links, sets `source_type="FISHBONE"`, `source_id=id`.)*

### 4.9 Root Cause CRUD & Confirmation Endpoints
- **List Root Causes:** `GET /investigations/{id}/root-causes`
- **Create Root Cause:** `POST /investigations/{id}/root-causes`
  ```json
  {
    "cause_statement": "Preventive maintenance frequency inadequate for high-cycle pneumatic valve diaphragms",
    "category": "PROCEDURE",
    "is_primary": true,
    "source_type": "MANUAL"
  }
  ```
  - *Provenance & Concurrency Validation:* `source_type` must be one of `FIVE_WHYS`, `FISHBONE`, `DIRECT_SYNTHESIS`, `MANUAL`. If `source_type` is `FIVE_WHYS` or `FISHBONE`, `source_id` must reference an existing record belonging to the SAME investigation; otherwise returns `400 Bad Request`. During validation, the referenced source step or cause is locked via `with_for_update()`, eliminating race conditions with concurrent source deletion.

- **Update Root Cause:** `PUT /root-causes/{id}`
  - *Lockdown:* Fields `is_verified`, `source_type`, and `source_id` are removed from the update schema. Generic updates attempting to set status to `CONFIRMED` or `REJECTED` return `400 Bad Request`.
- **Delete Root Cause:** `DELETE /root-causes/{id}`
- **Link Evidence:** `POST /root-causes/{id}/evidence-links`
  ```json
  {
    "evidence_id": 12,
    "relationship_type": "SUPPORTING",
    "relevance_explanation": "Maintenance logbook confirms 24-month inspection interval",
    "confidence_rating": "HIGH"
  }
  ```
  *(Cross-investigation isolation is strictly enforced. Returns 400 if evidence belongs to a different investigation.)*
- **Dismiss Contradiction:** `POST /root-causes/{id}/evidence-links/{link_id}/dismiss`
  ```json
  {
    "disposition_rationale": "High temperature during CIP cycle accounted for telemetry divergence; not applicable to crystallization phase."
  }
  ```
- **Confirm Root Cause (Role-Based Safety Guard):** `POST /root-causes/{id}/confirm`
  - *Authorization & Segregation of Duties:*
    - Requires `current_user.role in ("QA_APPROVER", "ADMIN")`. Returns `403 Forbidden` for standard investigators.
    - Assigned lead investigator cannot confirm their own proposals (`inv.lead_investigator_id == current_user.id` returns `403 Forbidden`).
    - Requires $\ge 1$ verified supporting evidence link and zero active contradictions.
    - Mandatory justification ($\ge 10$ chars).
    - Automatically binds `confirmed_by` and `confirmed_by_user_id` from authenticated session.
  ```json
  {
    "investigator_name": "Dr. Elena Rostova (QA Director)",
    "justification": "Corroborated by verified calibration bench report with zero active contradictory evidence."
  }
  ```
- **Reject Root Cause (Role-Based Review):** `POST /root-causes/{id}/reject`
  - *Authorization:* Requires `current_user.role in ("QA_APPROVER", "ADMIN")`. Returns `403 Forbidden` for standard investigators.
  - Automatically binds `rejected_by`, `rejected_by_user_id`, and `rejected_at` from authenticated session.
  ```json
  {
    "investigator_name": "Dr. Elena Rostova (QA Director)",
    "rationale": "Pneumatic pressure telemetry proved valve was commanded open and operational."
  }
  ```

### 4.10 Itemized RCA Review Endpoint
- **Route:** `POST /copilot/apply-rca-item`
- **Headers:** `Authorization: Bearer <token>`
- **Request:**
  ```json
  {
    "investigation_id": 1,
    "item_type": "FIVE_WHYS",
    "item_data": {
      "step_number": 6,
      "question": "Why did PM fail?",
      "answer": "PM interval 24 mo exceeded 12 mo wear limit."
    }
  }
  ```
- **Allowed `item_type` values:** `FIVE_WHYS`, `FISHBONE`, `ROOT_CAUSE`, `CAPA`, `GAP`.
- **Response:** `200 OK` (`{"ok": true, "item_type": "FIVE_WHYS", "id": 42}`)

---

## 5. Document Intake & AI Extraction Endpoints (Phase 2D.1)

### 5.1 Parse Document File (PDF)
- **Route:** `POST /intake/parse-file`
- **Headers:** `Authorization: Bearer <token>`
- **Content-Type:** `multipart/form-data`
- **Form Parameters:**
  - `file`: PDF binary upload (max 10 MB, `%PDF` magic bytes enforced)
  - `investigation_id`: (optional) Integer ID of parent investigation dossier
- **Response:** `200 OK`
  ```json
  {
    "investigation_title": "Deviation in Batch B2026-API-044 Temperature Excursion",
    "deviation": {
      "batch_number": "B2026-API-044",
      "product_name": "Atorvastatin Calcium Trihydrate API",
      "unit_operation": "Crystallization",
      "equipment_id": "RX-301",
      "description": "Temperature peaked at 38.4C exceeding 22.0C limit for 42 minutes."
    },
    "extracted_fields": [
      {
        "field_name": "batch_number",
        "label": "Batch Number",
        "value": "B2026-API-044",
        "source_reference": "Batch B2026-API-044",
        "page_number": 1,
        "source_location": "Page 1",
        "confidence": 0.99,
        "status": "SOURCE_FACT",
        "is_accepted": false,
        "user_edited": false,
        "original_value": "B2026-API-044",
        "validation_explanation": "Exact continuous substring match verified in source document."
      }
    ],
    "conflicting_information": [
      {
        "field_name": "equipment_feedback",
        "claim_a": "Cooling valve CV-04 controller demand was 100%",
        "source_a": "SCADA Supervisory Loop Demand",
        "claim_b": "Actual valve position feedback stayed at 12%",
        "source_b": "Field Valve Positioner Telemetry",
        "explanation": "Actuator demand and actual valve position diverged by 88%."
      }
    ],
    "raw_document_preview": "Deviation in Batch B2026-API-044...",
    "source_type": "PDF",
    "source_metadata": {
      "filename": "incident_report.pdf",
      "file_hash_sha256": "4a5e3...",
      "file_size_bytes": 1048576,
      "page_count": 3
    },
    "ai_confidence_score": 0.95
  }
  ```

### 5.2 Parse Text or Incident Email
- **Route:** `POST /intake/parse-text`
- **Headers:** `Authorization: Bearer <token>`
- **Request:**
  ```json
  {
    "content": "Deviation in Batch B2026-API-044 of Atorvastatin API in RX-301...",
    "is_email": false,
    "investigation_id": 1
  }
  ```
- **Email Ingestion:** When `is_email=true`, parses RFC 5322 headers (`From`, `To`, `Subject`, `Date`) and returns `source_metadata.sender_verified=false` to reflect unverified sender metadata.
- **Unpaginated Source Attribution:** Unpaginated inputs return `page_number: null` rather than defaulting to page 1.
- **Integrity Fallback:** If inference fails or runs offline, extraction grounds strictly in source text. Non-matching fields return `value: null` and `status: "MISSING"`; fabricated placeholder data is never returned.
- **Response:** `200 OK` (Same schema as `IntakeExtractionResponse`)

### 5.3 Apply Reviewed Extraction to Investigation
- **Route:** `POST /intake/apply-to-investigation`
- **Headers:** `Authorization: Bearer <token>`
- **Request:**
  ```json
  {
    "investigation_id": 1,
    "apply_deviation": true,
    "apply_evidence": true,
    "reviewed_fields": [
      {
        "field_name": "batch_number",
        "label": "Batch Number",
        "value": "B2026-API-044",
        "source_reference": "Batch B2026-API-044",
        "page_number": 1,
        "status": "SOURCE_FACT",
        "is_accepted": true,
        "user_edited": false
      }
    ],
    "custom_overrides": {},
    "evidence_metadata": {
      "filename": "incident_report.pdf",
      "file_hash_sha256": "4a5e3...",
      "file_size_bytes": 1048576
    }
  }
  ```
- **Integrity & Review Validation Guards:**
  1. **Explicit Acceptance Enforcement:** Only fields where `is_accepted == true` and `value` is non-null are applied to `Deviation` or saved as findings.
  2. **Server-Side Source Revalidation:** Client-submitted `status` and `source_reference` are revalidated server-side against source text. Claims lacking verbatim or normalized span matches are demoted to `AI_INFERENCE` (`citation_verified=false`).
  3. **Idempotent Operations:** Repeated apply requests with the same document SHA-256 reuse existing `Evidence`, update existing `InvestigationFinding` rows in-place, and skip duplicate `EvidenceGap` rows without creating duplicates.
  4. **Field-Level Attribution:** Saves `reviewed_by_id = current_user.id`, `is_accepted = true`, `user_edited`, `reviewed_at`, and preserves pre-modification `original_finding_text`.
- **Database Side-Effects:**
  1. Updates or creates `Deviation` with `is_ai_populated=true`, `is_verified=false`.
  2. Persists or reuses primary `Evidence` record with `classification="PRIMARY_SOURCE"`, `is_verified=false`, and SHA-256 digest.
  3. Inserts or updates `InvestigationFinding` rows with server-revalidated `citation_verified` and reviewer attribution.
  4. Inserts missing information as `EvidenceGap` rows (deduplicated by question).
  5. Records `AI_APPLIED` entry in `audit_logs` table.
- **Response:** `200 OK` (`InvestigationRead` model)

---

## 7. CAPA Lifecycle Management Endpoints (Same-Day Task 2)

### 7.1 Propose CAPA Action
- **Route:** `POST /investigations/{investigation_id}/capas`
- **Headers:** `Authorization: Bearer <token>`
- **Description:** Proposes a new CAPA action for an active investigation. Server enforces that new CAPAs always start in `PROPOSED` status with `is_verified=false`. Client attempts to pre-verify or pre-approve are rejected with HTTP 400.
- **Request:**
  ```json
  {
    "action_type": "CORRECTIVE_ACTION",
    "description": "Replace all CV-301 valve diaphragms with reinforced PTFE-composite seals.",
    "rationale": "PTFE composite provides 3x higher thermal cycle durability.",
    "owner": "Maintenance Lead",
    "deadline": "14 Days",
    "effectiveness_criteria": "Zero pressure drops across 10 consecutive commercial batches.",
    "effectiveness_review_period_days": 30,
    "root_cause_id": 12
  }
  ```
- **Validation Rules:**
  - `action_type`: Must be one of `CORRECTION`, `CORRECTIVE_ACTION`, `PREVENTIVE_ACTION`.
  - `root_cause_id`: If provided, must reference an existing root cause belonging to the same investigation. Rejected root causes or cross-investigation root causes return `HTTP 400 Bad Request`.
  - `is_verified`: If set to `true` by client, returns `HTTP 400 Bad Request` (client forgery prevention).
  - `status`: If set to `APPROVED` or `EFFECTIVENESS_VERIFIED` by client, returns `HTTP 400 Bad Request`.
- **Response:** `200 OK` (`CapaActionRead` model, `status="PROPOSED"`, `is_verified=false`).
- **Audit Action:** Logs `CREATED` on entity `CAPA`.

### 7.2 Update CAPA Work Fields
- **Route:** `PUT /capas/{capa_id}`
- **Headers:** `Authorization: Bearer <token>`
- **Description:** Updates permitted work fields of a CAPA action (`description`, `rationale`, `owner`, `deadline`, `effectiveness_criteria`, `effectiveness_review_period_days`, `action_type`, `root_cause_id`).
- **Lifecycle Guards:**
  - `is_verified`: Cannot be modified directly via PUT (returns `HTTP 400 Bad Request`).
  - Cannot transition directly to `APPROVED` or `EFFECTIVENESS_VERIFIED` via PUT (dedicated endpoints required; returns `HTTP 400 Bad Request`).
  - Cannot start work (`IN_PROGRESS`) or complete work (`COMPLETED`) while in `PROPOSED` status without prior formal QA approval (returns `HTTP 400 Bad Request`).
  - Cannot modify an action in `EFFECTIVENESS_VERIFIED` status (records are locked for cGMP compliance; returns `HTTP 400 Bad Request`).
  - Transitioning to `COMPLETED` requires non-empty rationale/notes ($\ge 5$ characters).
- **Response:** `200 OK` (`CapaActionRead` model).
- **Audit Action:** Logs `UPDATED` on entity `CAPA`.

### 7.3 Formal QA Approval
- **Route:** `POST /capas/{capa_id}/approve` (and alias `POST /capas/{capa_id}/verify`)
- **Headers:** `Authorization: Bearer <token>`
- **Description:** Formally approves a proposed CAPA action. Transitions status from `PROPOSED` to `APPROVED` and sets `is_verified=true`.
- **Authorization & Segregation of Duties:**
  - Requires caller role `QA_APPROVER` or `ADMIN`. Standard `INVESTIGATOR` role is denied with `HTTP 403 Forbidden`.
  - The assigned lead investigator for the investigation (`lead_investigator_id == current_user.id`) cannot approve CAPAs for their own investigation, even if possessing QA or Admin privileges (`HTTP 403 Forbidden`).
  - CAPA must be in `PROPOSED` status (`HTTP 400 Bad Request` if already approved or in another state).
- **Request:**
  ```json
  {
    "approval_notes": "Reviewed engineering calculations; approved for plant implementation."
  }
  ```
- **Response:** `200 OK` (`status="APPROVED"`, `is_verified=true`).
- **Audit Action:** Logs `APPROVED` on entity `CAPA`.

### 7.4 Mark Implementation Completed
- **Route:** `POST /capas/{capa_id}/complete`
- **Headers:** `Authorization: Bearer <token>`
- **Description:** Marks an approved or in-progress CAPA as completed. Requires non-empty completion notes documenting execution.
- **Request:**
  ```json
  {
    "completion_notes": "PTFE composite diaphragms installed, torque-verified, and pressure hold tested."
  }
  ```
- **Validation:** Requires CAPA to be in `APPROVED` or `IN_PROGRESS` status (`HTTP 400 Bad Request` otherwise). Requires completion notes $\ge 5$ characters.
- **Response:** `200 OK` (`status="COMPLETED"`).
- **Audit Action:** Logs `COMPLETED` on entity `CAPA`.

### 7.5 Formal QA Effectiveness Verification
- **Route:** `POST /capas/{capa_id}/verify-effectiveness`
- **Headers:** `Authorization: Bearer <token>`
- **Description:** Final regulatory sign-off verifying that the completed CAPA successfully prevented recurrence after the designated review period.
- **Authorization & Guards:**
  - Requires caller role `QA_APPROVER` or `ADMIN` (`HTTP 403 Forbidden` for standard investigators).
  - CAPA must be in `COMPLETED` status (`HTTP 400 Bad Request` if still in progress or uncompleted).
  - CAPA must have defined quantitative `effectiveness_criteria` ($\ge 5$ characters; `HTTP 400 Bad Request` if missing).
- **Request:**
  ```json
  {
    "verification_notes": "60 days elapsed. 18 commercial batches run with zero pressure drop alerts."
  }
  ```
- **Response:** `200 OK` (`status="EFFECTIVENESS_VERIFIED"`).
- **Audit Action:** Logs `EFFECTIVENESS_VERIFIED` on entity `CAPA`.

### 7.6 Delete CAPA Action
- **Route:** `DELETE /capas/{capa_id}`
- **Headers:** `Authorization: Bearer <token>`
- **Description:** Deletes a CAPA action from an investigation. Deletion of effectiveness-verified CAPAs is strictly prohibited (`HTTP 400 Bad Request`) to maintain cGMP audit compliance. Fully recorded in audit trail.
- **Response:** `200 OK` (`{"ok": true, "deleted_id": 12}`).
- **Audit Action:** Logs `DELETED` on entity `CAPA`.

---

## 8. Error Responses

- **`400 Bad Request`**: Validation error (e.g. malformed payload or invalid PDF bytes).
- **`401 Unauthorized`**: Missing or invalid Bearer token.
- **`403 Forbidden`**: Ownership isolation violation (user does not own the investigation).
- **`404 Not Found`**: Investigation ID does not exist in PostgreSQL.
- **`429 Too Many Requests`**: Upstream Groq AI rate limit exceeded (e.g. 200,000 TPD limit reached):
  ```json
  {
    "detail": "AI inference rate limit reached: Rate limit reached: 200,000 TPD exceeded"
  }
  ```
- **`503 Service Unavailable`**: Groq AI inference is unavailable or network connection failed:
  ```json
  {
    "detail": "AI inference service unavailable: Service Unavailable: 503 backend error"
  }
  ```


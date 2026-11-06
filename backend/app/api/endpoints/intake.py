import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import Optional, Dict, Any, List

from app.core.database import get_db
from app.core.security import get_current_user, verify_investigation_access
from app.models.audit import User, AiInteraction
from app.models.investigation import Investigation
from app.models.deviation import Deviation
from app.models.evidence import Evidence, InvestigationFinding, EvidenceGap
from app.schemas.copilot import (
    IntakeExtractionResponse, 
    ApplyExtractionRequest, 
    ExtractedField, 
    ExtractionStatus,
    ConflictingInfoItem,
    MissingInfoItem
)
from app.schemas.deviation import DeviationCreate
from app.schemas.investigation import InvestigationRead
from app.services.langgraph_workflow import rca_graph
from app.services.audit_service import audit_service
from app.services.storage_service import storage_service
from app.services.rate_limiter import ai_rate_limiter, investigation_concurrency_limiter
from app.services.token_budget import estimate_tokens
from app.services.document_parser import document_parser
from app.services.groq_service import (
    groq_service,
    GroqServiceError,
    GroqRateLimitError,
    GroqAuthenticationError,
    GroqTimeoutError,
    GroqModelNotFoundError
)
from app.api.endpoints.investigations import get_investigation_by_id
from app.services.ai_guard import validate_source_text, normalize_text

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/parse-file", response_model=IntakeExtractionResponse)
async def parse_incident_file(
    file: UploadFile = File(...),
    investigation_id: Optional[int] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload a deviation PDF, email or text file.
    Runs the full LangGraph ingestion & extraction pipeline with upload validation and page-level integrity.
    If investigation_id is provided, verifies authorization and persists the original file in isolated storage.
    """
    await ai_rate_limiter.check_rate_limit(current_user.id)
    if investigation_id:
        await verify_investigation_access(investigation_id, current_user, db, require_write=True)

    async with investigation_concurrency_limiter.acquire(investigation_id):
        return await _execute_parse_file(file, investigation_id, current_user, db)

async def _execute_parse_file(file: UploadFile, investigation_id: Optional[int], current_user: User, db: AsyncSession):
    file_bytes, filename, ext = await storage_service.read_and_validate_upload(file)
    source_type = "PDF" if ext == ".pdf" else ("EMAIL" if ext == ".eml" else "TEXT")

    file_hash = document_parser.compute_sha256(file_bytes)
    stored_path = None
    if investigation_id:
        stored_path, _ = storage_service.save_evidence_file(investigation_id, filename, file_bytes)

    # Structured metadata
    meta = {
        "filename": filename,
        "uploaded_by_id": current_user.id,
        "file_size_bytes": len(file_bytes),
        "file_hash_sha256": file_hash,
        "file_path": stored_path,
        "source_type": source_type
    }

    parsed_text = ""
    pages_list = None
    if ext == ".pdf":
        try:
            pdf_data = document_parser.parse_pdf_structured(file_bytes)
            parsed_text = pdf_data["full_text"]
            pages_list = pdf_data["pages"]
            meta["page_count"] = pdf_data["page_count"]
            meta["pages"] = [{"page_number": p["page_number"], "char_count": p["char_count"]} for p in pages_list]
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to parse PDF document: {str(e)}")
    else:
        parsed_text = file_bytes.decode("utf-8", errors="ignore")

    meta["raw_document_preview"] = parsed_text[:5000]

    # Invoke LangGraph workflow with complete 13-node state
    initial_state = {
        "raw_document": parsed_text if ext == ".pdf" else None,
        "raw_bytes": file_bytes if ext == ".pdf" else None,
        "source_type": source_type,
        "parsed_text": parsed_text,
        "metadata": meta,
        "extracted_data": {},
        "validation_errors": [],
        "is_valid": True,
        "missing_evidence": [],
        "has_critical_missing_info": False,
        "evidence_analysis": {},
        "has_conflicting_evidence": False,
        "is_evidence_insufficient": False,
        "investigation_plan": {},
        "selected_methodology": "BOTH",
        "rca_analysis": None,
        "five_whys": [],
        "fishbone_causes": [],
        "root_causes": [],
        "capa_actions": [],
        "output_validated": False,
        "validation_issues": [],
        "human_approved": False,
        "current_step": "START",
        "trace_log": [],
        "allow_offline_fallback": False
    }

    try:
        final_state = await rca_graph.ainvoke(initial_state)
        extracted = final_state.get("extracted_data", {})
        
        return IntakeExtractionResponse(
            investigation_title=extracted.get("investigation_title", f"Deviation Investigation - {filename}"),
            deviation=extracted.get("deviation", {}),
            extracted_fields=extracted.get("extracted_fields", []),
            extracted_findings=extracted.get("extracted_findings", []),
            missing_information=extracted.get("missing_information", []),
            conflicting_information=extracted.get("conflicting_information", []),
            recommended_immediate_actions=extracted.get("recommended_immediate_actions", []),
            raw_document_preview=extracted.get("raw_document_preview") or final_state.get("parsed_text", "")[:5000],
            source_type=source_type,
            source_metadata=meta,
            ai_confidence_score=extracted.get("ai_confidence_score", 0.95)
        )
    except GroqRateLimitError as e:
        logger.warning(f"Groq rate limit in parse_incident_file: {e}")
        raise HTTPException(status_code=429, detail=f"AI inference rate limit reached: {str(e)}")
    except GroqAuthenticationError as e:
        logger.error(f"Groq authentication error in parse_incident_file: {e}")
        raise HTTPException(status_code=503, detail="AI service configuration or authentication failure.")
    except (GroqServiceError, GroqTimeoutError, GroqModelNotFoundError) as e:
        logger.error(f"Groq service error in parse_incident_file: {e}")
        raise HTTPException(status_code=503, detail=f"AI inference service unavailable: {str(e)}")
    except Exception as e:
        err_str = str(e)
        if "429" in err_str or "rate limit" in err_str.lower() or "tpd" in err_str.lower() or "tokens per day" in err_str.lower():
            raise HTTPException(status_code=429, detail=f"AI inference rate limit reached: {err_str}")
        if "503" in err_str or "service unavailable" in err_str.lower() or "connection error" in err_str.lower():
            raise HTTPException(status_code=503, detail=f"AI inference service unavailable: {err_str}")
        raise HTTPException(status_code=500, detail=f"AI Ingestion Pipeline Failed: {err_str}")

@router.post("/parse-text", response_model=IntakeExtractionResponse)
async def parse_incident_text(
    content: str = Body(..., embed=True),
    is_email: bool = Body(False, embed=True),
    investigation_id: Optional[int] = Body(None, embed=True),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Process pasted deviation text or email notification.
    Preserves raw content, parses RFC 5322 headers, computes SHA-256 fingerprint, and runs full extraction.
    """
    await ai_rate_limiter.check_rate_limit(current_user.id)
    if investigation_id:
        await verify_investigation_access(investigation_id, current_user, db, require_write=True)

    async with investigation_concurrency_limiter.acquire(investigation_id):
        return await _execute_parse_text(content, is_email, investigation_id, current_user, db)

async def _execute_parse_text(content: str, is_email: bool, investigation_id: Optional[int], current_user: User, db: AsyncSession):
    if not content or not content.strip():
        raise HTTPException(status_code=400, detail="Incident text content cannot be empty.")

    clean_content, was_truncated = validate_source_text(content, max_chars=30000)

    source_type = "EMAIL" if is_email else "TEXT"
    file_hash = document_parser.compute_sha256(clean_content.encode("utf-8"))
    
    meta = {
        "uploaded_by_id": current_user.id,
        "file_hash_sha256": file_hash,
        "file_size_bytes": len(clean_content.encode("utf-8")),
        "source_type": source_type,
        "raw_document_preview": clean_content[:5000]
    }

    if is_email:
        parsed_email = document_parser.parse_email(clean_content)
        meta["email_headers"] = parsed_email.get("headers", {})
        # Sender identity is treated as unverified metadata
        meta["sender_verified"] = False
    
    initial_state = {
        "raw_document": clean_content,
        "raw_bytes": None,
        "source_type": source_type,
        "parsed_text": "",
        "metadata": meta,
        "extracted_data": {},
        "validation_errors": [],
        "is_valid": True,
        "missing_evidence": [],
        "has_critical_missing_info": False,
        "evidence_analysis": {},
        "has_conflicting_evidence": False,
        "is_evidence_insufficient": False,
        "investigation_plan": {},
        "selected_methodology": "BOTH",
        "rca_analysis": None,
        "five_whys": [],
        "fishbone_causes": [],
        "root_causes": [],
        "capa_actions": [],
        "output_validated": False,
        "validation_issues": [],
        "human_approved": False,
        "current_step": "START",
        "trace_log": [],
        "allow_offline_fallback": False
    }

    try:
        final_state = await rca_graph.ainvoke(initial_state)
        extracted = final_state.get("extracted_data", {})

        return IntakeExtractionResponse(
            investigation_title=extracted.get("investigation_title", "Deviation Investigation"),
            deviation=extracted.get("deviation", {}),
            extracted_fields=extracted.get("extracted_fields", []),
            extracted_findings=extracted.get("extracted_findings", []),
            missing_information=extracted.get("missing_information", []),
            conflicting_information=extracted.get("conflicting_information", []),
            recommended_immediate_actions=extracted.get("recommended_immediate_actions", []),
            raw_document_preview=extracted.get("raw_document_preview") or content[:5000],
            source_type=source_type,
            source_metadata=meta,
            ai_confidence_score=extracted.get("ai_confidence_score", 0.95)
        )
    except GroqRateLimitError as e:
        logger.warning(f"Groq rate limit in parse_incident_file: {e}")
        raise HTTPException(status_code=429, detail=f"AI inference rate limit reached: {str(e)}")
    except GroqAuthenticationError as e:
        logger.error(f"Groq authentication error in parse_incident_file: {e}")
        raise HTTPException(status_code=503, detail="AI service configuration or authentication failure.")
    except (GroqServiceError, GroqTimeoutError, GroqModelNotFoundError) as e:
        logger.error(f"Groq service error in parse_incident_file: {e}")
        raise HTTPException(status_code=503, detail=f"AI inference service unavailable: {str(e)}")
    except Exception as e:
        err_str = str(e)
        if "429" in err_str or "rate limit" in err_str.lower() or "tpd" in err_str.lower() or "tokens per day" in err_str.lower():
            raise HTTPException(status_code=429, detail=f"AI inference rate limit reached: {err_str}")
        if "503" in err_str or "service unavailable" in err_str.lower() or "connection error" in err_str.lower():
            raise HTTPException(status_code=503, detail=f"AI inference service unavailable: {err_str}")
        raise HTTPException(status_code=500, detail=f"AI Ingestion Pipeline Failed: {err_str}")

@router.post("/apply-to-investigation", response_model=InvestigationRead)
async def apply_ai_extraction_to_investigation(
    req: ApplyExtractionRequest = Body(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Applies extracted AI data into the structured investigation record after investigator review.
    Guarantees transactional integrity: rollback on any error.
    Updates Deviation, attaches primary Evidence, records InvestigationFindings, and tracks EvidenceGaps.
    All applied AI suggestions are explicitly marked with is_ai_populated=True, is_verified=False.
    """
    await verify_investigation_access(req.investigation_id, current_user, db, require_write=True)
    inv = await get_investigation_by_id(req.investigation_id, db)
    custom = req.custom_overrides or {}
    dev_data = dict(custom.get("deviation", {}))
    evidence_meta = req.evidence_metadata or custom.get("source_metadata") or {}

    # Extract field map from reviewed_fields if supplied
    field_map: Dict[str, ExtractedField] = {}
    if req.reviewed_fields:
        for f in req.reviewed_fields:
            if f.is_accepted:
                field_map[f.field_name] = f

        # Map reviewed fields into dev_data
        if "batch_number" in field_map and field_map["batch_number"].value:
            dev_data["batch_number"] = field_map["batch_number"].value
        if "product_name" in field_map and field_map["product_name"].value:
            dev_data["product_name"] = field_map["product_name"].value
        if "unit_operation" in field_map and field_map["unit_operation"].value:
            dev_data["unit_operation"] = field_map["unit_operation"].value
        if "equipment_id" in field_map and field_map["equipment_id"].value:
            dev_data["equipment_id"] = field_map["equipment_id"].value
        if "description" in field_map and field_map["description"].value:
            dev_data["description"] = field_map["description"].value
        if "immediate_containment" in field_map and field_map["immediate_containment"].value:
            dev_data["immediate_containment"] = field_map["immediate_containment"].value
        if "deviation_number" in field_map and field_map["deviation_number"].value:
            dev_data["deviation_number"] = field_map["deviation_number"].value

        # Update investigation title if reviewed title was accepted
        if "deviation_title" in field_map and field_map["deviation_title"].value:
            inv.title = field_map["deviation_title"].value

    try:
        # 1. Update or Create Deviation
        if req.apply_deviation and dev_data:
            extracted_num = dev_data.get("deviation_number")
            dev_source = "SOURCE" if extracted_num else "SYSTEM"
            clean_num = extracted_num if extracted_num else f"DEV-2026-{inv.id:04d}"

            if inv.deviation:
                for k, v in dev_data.items():
                    if hasattr(inv.deviation, k) and v is not None:
                        setattr(inv.deviation, k, v)
                if not inv.deviation.deviation_number:
                    inv.deviation.deviation_number = f"DEV-2026-{inv.id:04d}"
                    inv.deviation.deviation_number_source = "SYSTEM"
                elif extracted_num:
                    inv.deviation.deviation_number_source = "SOURCE"
                inv.deviation.is_ai_populated = True
                inv.deviation.is_verified = False
            else:
                new_dev = Deviation(
                    investigation_id=inv.id,
                    deviation_number=clean_num,
                    deviation_number_source=dev_source,
                    deviation_type=dev_data.get("deviation_type", "MAJOR"),
                    severity=dev_data.get("severity", "High"),
                    batch_number=dev_data.get("batch_number", "Unknown"),
                    product_name=dev_data.get("product_name", "Unknown API"),
                    unit_operation=dev_data.get("unit_operation"),
                    equipment_id=dev_data.get("equipment_id"),
                    bpr_number=dev_data.get("bpr_number"),
                    target_yield_kg=dev_data.get("target_yield_kg"),
                    actual_yield_kg=dev_data.get("actual_yield_kg"),
                    description=dev_data.get("description", "Deviation description"),
                    immediate_containment=dev_data.get("immediate_containment"),
                    is_ai_populated=True,
                    is_verified=False
                )
                db.add(new_dev)
                inv.deviation = new_dev

            # Record AI interaction row with active model_name and token tracking
            ai_record = AiInteraction(
                investigation_id=inv.id,
                interaction_type="INTAKE_EXTRACTION",
                prompt_summary=f"Applied intake extraction review for deviation {inv.deviation.deviation_number}",
                response_data=f"Batch: {inv.deviation.batch_number}, Product: {inv.deviation.product_name}, Source: {inv.deviation.deviation_number_source}",
                model_name=groq_service.model,
                tokens_used=estimate_tokens(str(dev_data))
            )
            db.add(ai_record)

            await audit_service.log_action(
                db, inv.id, "AI_APPLIED", "DEVIATION",
                f"AI populated deviation details for Batch {dev_data.get('batch_number')}",
                user_id=current_user.id,
                user_name=current_user.full_name
            )

        # 2. Persist Primary Intake Evidence Record (Idempotent)
        intake_evidence = None
        source_filename = evidence_meta.get("filename") or custom.get("filename") or f"intake_report_{inv.id}.txt"
        raw_preview = (
            custom.get("raw_document_preview")
            or evidence_meta.get("raw_document_preview")
            or evidence_meta.get("extracted_text")
            or dev_data.get("description", "Incident intake record")
        )
        file_hash = evidence_meta.get("file_hash_sha256") or (document_parser.compute_sha256(raw_preview.encode()) if raw_preview else None)

        if req.apply_evidence and file_hash:
            existing_ev_stmt = select(Evidence).where(
                Evidence.investigation_id == inv.id,
                Evidence.file_hash_sha256 == file_hash
            )
            ev_res = await db.execute(existing_ev_stmt)
            intake_evidence = ev_res.scalars().first()

        if req.apply_evidence and not intake_evidence:
            intake_evidence = Evidence(
                investigation_id=inv.id,
                title=f"Intake Incident Record (Batch {dev_data.get('batch_number', 'Initial')})",
                original_filename=source_filename,
                file_path=evidence_meta.get("file_path"),
                file_size_bytes=evidence_meta.get("file_size_bytes"),
                file_hash_sha256=file_hash,
                evidence_type="BATCH_RECORD" if "batch" in str(dev_data).lower() else "DOCUMENT",
                classification="PRIMARY_SOURCE",
                source=source_filename,
                source_location="Incident Intake Document",
                page_number=1,
                extracted_text=raw_preview,
                source_metadata=evidence_meta,
                confidence_score=0.95,
                is_verified=False,
                verified_by=None,
                verified_by_user_id=None,
                uploaded_by_user_id=current_user.id
            )
            db.add(intake_evidence)
            inv.evidences.append(intake_evidence)
            await db.flush()
        elif intake_evidence:
            # Update existing Evidence record rather than creating duplicate
            if raw_preview and not intake_evidence.extracted_text:
                intake_evidence.extracted_text = raw_preview
            if evidence_meta:
                intake_evidence.source_metadata = evidence_meta

        # 3. Apply Findings from Reviewed Fields (Server-side revalidation & idempotency)
        existing_findings_stmt = select(InvestigationFinding).where(
            InvestigationFinding.investigation_id == inv.id
        )
        if intake_evidence:
            existing_findings_stmt = existing_findings_stmt.where(
                InvestigationFinding.evidence_id == intake_evidence.id
            )
        existing_findings_res = await db.execute(existing_findings_stmt)
        existing_findings = list(existing_findings_res.scalars().all())

        if req.reviewed_fields:
            for f in req.reviewed_fields:
                # Remediation B: Explicit acceptance enforcement
                if not f.is_accepted or not f.value:
                    continue
                
                # Remediation C & D: Server-side source citation revalidation (do not trust client)
                citation_verified = False
                val_status = "AI_INFERENCE"
                finding_type = "OBSERVATION"

                if f.status == ExtractionStatus.SOURCE_FACT or f.source_reference:
                    ref_text = f.source_reference or f.value
                    pages_meta = evidence_meta.get("pages_metadata") or custom.get("pages_metadata")
                    reval = document_parser.validate_source_citation(
                        finding_or_excerpt=ref_text,
                        source_text=raw_preview,
                        pages_metadata=pages_meta,
                        claimed_page=f.page_number
                    )
                    if reval.get("is_valid"):
                        citation_verified = True
                        val_status = "VERIFIED_SOURCE_FACT"
                        finding_type = "FACT"
                    else:
                        citation_verified = False
                        val_status = "AI_INFERENCE"
                        finding_type = "OBSERVATION"
                elif f.status == ExtractionStatus.CONFLICTING:
                    finding_type = "INCONSISTENCY"
                    val_status = "CONFLICTING_INFORMATION"
                else:
                    finding_type = "OBSERVATION"
                    val_status = "AI_INFERENCE"

                # Check if a finding for this field already exists (Idempotency)
                target_prefix = f"{f.label}:"
                matched_finding = next(
                    (ef for ef in existing_findings if ef.finding_text.startswith(target_prefix)),
                    None
                )

                if matched_finding:
                    matched_finding.finding_text = f"{f.label}: {f.value}"
                    matched_finding.finding_type = finding_type
                    matched_finding.evidence_reference = f.source_reference[:255] if f.source_reference else None
                    matched_finding.source_location = (f"Page {f.page_number}" if f.page_number else (f.source_location or "Intake"))[:100]
                    matched_finding.citation_verified = citation_verified
                    matched_finding.validation_status = val_status
                    matched_finding.is_accepted = True
                    matched_finding.user_edited = bool(f.user_edited)
                    matched_finding.reviewed_by_id = current_user.id
                    matched_finding.reviewed_at = datetime.utcnow()
                    if f.original_value and not matched_finding.original_finding_text:
                        matched_finding.original_finding_text = f.original_value
                else:
                    new_finding = InvestigationFinding(
                        investigation_id=inv.id,
                        evidence_id=intake_evidence.id if intake_evidence else None,
                        reviewed_by_id=current_user.id,
                        finding_text=f"{f.label}: {f.value}",
                        finding_type=finding_type,
                        evidence_reference=f.source_reference[:255] if f.source_reference else None,
                        source_location=(f"Page {f.page_number}" if f.page_number else (f.source_location or "Intake"))[:100],
                        is_ai_suggested=True,
                        is_verified=False,
                        citation_verified=citation_verified,
                        validation_status=val_status,
                        is_accepted=True,
                        user_edited=bool(f.user_edited),
                        reviewed_at=datetime.utcnow(),
                        original_finding_text=f.original_value or f.value
                    )
                    db.add(new_finding)
                    inv.findings.append(new_finding)
                    existing_findings.append(new_finding)
        else:
            # Fallback legacy findings
            existing_texts = {ef.finding_text.strip() for ef in existing_findings}
            findings = custom.get("extracted_findings", [])
            for f_item in findings:
                f_str = f_item.get("finding_text") if isinstance(f_item, dict) else str(f_item)
                if not f_str or f_str.strip() in existing_texts:
                    continue
                is_cit_ver = bool(f_item.get("citation_verified", False)) if isinstance(f_item, dict) else False
                val_stat = f_item.get("validation_status", "UNVERIFIED") if isinstance(f_item, dict) else "UNVERIFIED"

                finding = InvestigationFinding(
                    investigation_id=inv.id,
                    evidence_id=intake_evidence.id if intake_evidence else None,
                    reviewed_by_id=current_user.id,
                    finding_text=f_str,
                    finding_type="FACT",
                    source_location="Intake Findings",
                    is_ai_suggested=True,
                    is_verified=False,
                    citation_verified=is_cit_ver,
                    validation_status=val_stat,
                    is_accepted=True,
                    user_edited=False,
                    reviewed_at=datetime.utcnow(),
                    original_finding_text=f_str
                )
                db.add(finding)
                inv.findings.append(finding)
                existing_texts.add(f_str.strip())

        # 4. Persist Missing Information as EvidenceGap Records (Idempotent)
        existing_gaps_stmt = select(EvidenceGap).where(EvidenceGap.investigation_id == inv.id)
        existing_gaps_res = await db.execute(existing_gaps_stmt)
        existing_gaps = list(existing_gaps_res.scalars().all())
        existing_gap_questions = {g.question.strip().lower() for g in existing_gaps}

        missing_info = custom.get("missing_information", [])
        for gap_item in missing_info:
            q_text = gap_item.get("question", "").strip()
            if not q_text or q_text.lower() in existing_gap_questions:
                continue
            gap = EvidenceGap(
                investigation_id=inv.id,
                category=gap_item.get("category", "GMP_BATCH_RECORD"),
                question=q_text,
                impact_description=gap_item.get("impact_description", "Required for causal investigation"),
                suggested_record=gap_item.get("suggested_record") or gap_item.get("category"),
                urgency=gap_item.get("urgency", "HIGH"),
                is_resolved=False
            )
            db.add(gap)
            inv.evidence_gaps.append(gap)
            existing_gap_questions.add(q_text.lower())

        await db.flush()
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    return await get_investigation_by_id(req.investigation_id, db)

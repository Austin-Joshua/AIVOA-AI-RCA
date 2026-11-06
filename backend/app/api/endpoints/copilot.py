from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Dict, Any, List, Optional
from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)

from app.core.database import get_db
from app.core.security import get_current_user, verify_investigation_access
from app.models.audit import User, AiInteraction
from app.models.copilot import CopilotMessage
from app.models.evidence import Evidence
from app.schemas.copilot import (
    CopilotChatRequest,
    CopilotChatResponse,
    GenerateRcaRequest,
    RcaAnalysisResult,
    ApplyRcaItemRequest,
    FieldPatch,
    FieldPatchStatus,
    RiskAssessment,
    CopilotConverseRequest,
    CopilotConverseResponse,
    CopilotMessageRead,
    MissingInfoItem,
)
from app.schemas.investigation import InvestigationRead
from app.models.five_whys import FiveWhysStep
from app.models.fishbone import FishboneCause
from app.models.root_cause import RootCause, RootCauseEvidenceLink
from app.models.evidence import EvidenceGap
from app.models.capa import CapaAction
from app.services.groq_service import (
    groq_service,
    GroqServiceError,
    GroqRateLimitError,
    GroqAuthenticationError,
    GroqTimeoutError,
    GroqConnectionError,
    sanitize_secret,
)
from app.services.audit_service import audit_service
from app.services.document_parser import document_parser
from app.api.endpoints.investigations import get_investigation_by_id
from app.services.ai_guard import (
    normalize_text,
    validate_chat_input,
    validate_source_text,
    detect_injection,
    is_strictly_out_of_domain,
    retrieve_context,
    log_guard_blocked_audit,
    check_canary_leak,
    check_system_prompt_leak,
    FIXED_REFUSAL,
)

router = APIRouter()

@router.post("/converse", response_model=CopilotConverseResponse)
async def copilot_converse(
    req: CopilotConverseRequest = Body(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Primary conversational interface for AI RCA Copilot (matching reference video interaction).
    Accepts pasted incident text, uploaded documents, field corrections, or questions.
    Returns categorized field patches, risk assessment, and contextual guidance.
    Draft field patches are never automatically committed to DB; investigator confirms.
    """
    await verify_investigation_access(req.investigation_id, current_user, db, require_write=True)
    inv = await get_investigation_by_id(req.investigation_id, db)

    # 0. Input hygiene, length bounds, and attack validation
    clean_message = normalize_text(req.message)
    if not clean_message:
        raise HTTPException(status_code=422, detail="Message cannot be empty.")

    if len(clean_message) > 100000:
        raise HTTPException(
            status_code=413,
            detail=f"Message payload exceeds 100,000 character limit (received {len(clean_message):,} characters)."
        )

    is_doc_candidate = bool(req.attached_document_id) or (
        len(clean_message) > 2000 and any(kw in clean_message.lower() for kw in ["deviation", "batch", "subject:", "incident", "reactor", "excursion"])
    )
    if not is_doc_candidate and len(clean_message) > 2000:
        raise HTTPException(
            status_code=422,
            detail=f"Chat message exceeds the 2,000 character limit (received {len(clean_message):,} characters). Please condense your inquiry."
        )

    if is_doc_candidate and len(clean_message) > 30000:
        clean_message, _ = validate_source_text(clean_message, max_chars=30000)

    # Attack & prompt injection detection
    inj = detect_injection(clean_message)
    if inj["suspected"]:
        await log_guard_blocked_audit(
            db=db,
            investigation_id=inv.id,
            category=",".join(inj["categories"]),
            user_id=current_user.id,
            user_name=current_user.full_name,
            raw_input=clean_message
        )
        attack_cats = set(inj["categories"])
        if attack_cats.intersection({"PROMPT_EXTRACTION", "JAILBREAK_DAN", "INSTRUCTION_OVERRIDE", "DATA_SMUGGLING", "MULTILINGUAL_INJECTION", "DELIMITER_SPOOFING"}):
            db.add(CopilotMessage(
                investigation_id=inv.id,
                user_id=current_user.id,
                role="user",
                content=clean_message,
                message_type="TEXT"
            ))
            db.add(CopilotMessage(
                investigation_id=inv.id,
                user_id=None,
                role="assistant",
                content=FIXED_REFUSAL,
                message_type="TEXT"
            ))
            await db.commit()
            return CopilotConverseResponse(
                reply_text=FIXED_REFUSAL,
                classification="QUESTION",
                field_patches=[],
                risk_assessment=None,
                missing_fields=[],
                suggested_actions=["Review Investigation Evidence", "Check Evidence Gaps"]
            )

    if is_strictly_out_of_domain(clean_message):
        db.add(CopilotMessage(
            investigation_id=inv.id,
            user_id=current_user.id,
            role="user",
            content=clean_message,
            message_type="TEXT"
        ))
        db.add(CopilotMessage(
            investigation_id=inv.id,
            user_id=None,
            role="assistant",
            content=FIXED_REFUSAL,
            message_type="TEXT"
        ))
        await db.commit()
        return CopilotConverseResponse(
            reply_text=FIXED_REFUSAL,
            classification="QUESTION",
            field_patches=[],
            risk_assessment=None,
            missing_fields=[],
            suggested_actions=["Review Investigation Evidence", "Check Evidence Gaps"]
        )

    # 1. Fetch conversation history for context
    history_res = await db.execute(
        select(CopilotMessage)
        .where(CopilotMessage.investigation_id == inv.id)
        .order_by(CopilotMessage.created_at.asc())
    )
    history_msgs = history_res.scalars().all()

    # 2. Resolve document / source text
    source_text = req.message
    source_type = "TEXT"
    pages_meta = None

    if req.attached_document_id:
        ev_res = await db.execute(
            select(Evidence).where(
                Evidence.id == req.attached_document_id,
                Evidence.investigation_id == inv.id
            )
        )
        ev = ev_res.scalar_one_or_none()
        if ev:
            source_type = ev.evidence_type or "DOCUMENT"
            if ev.extracted_text:
                source_text = ev.extracted_text
                pages_meta = ev.source_metadata.get("pages") if isinstance(ev.source_metadata, dict) else None
            elif ev.file_path:
                try:
                    p = Path(ev.file_path)
                    if p.exists():
                        file_bytes = p.read_bytes()
                        if p.suffix.lower() == ".pdf":
                            pdf_data = document_parser.parse_pdf_structured(file_bytes)
                            source_text = pdf_data["full_text"]
                            pages_meta = pdf_data["pages"]
                            source_type = "PDF"
                        else:
                            source_text = file_bytes.decode("utf-8", errors="ignore")
                except Exception as e:
                    logger.warning(f"Failed to read attached evidence file: {e}")

    # 3. Assemble current state
    current_state = {
        "investigation_number": inv.investigation_number,
        "title": inv.title,
        "stage": inv.stage,
        "status": inv.status,
        "deviation": {
            "batch": inv.deviation.batch_number if inv.deviation else None,
            "product": inv.deviation.product_name if inv.deviation else None,
            "unit_operation": inv.deviation.unit_operation if inv.deviation else None,
            "equipment": inv.deviation.equipment_id if inv.deviation else None,
            "severity": inv.deviation.severity if inv.deviation else None,
        } if inv.deviation else None,
        "five_whys_count": len(inv.five_whys) if inv.five_whys else 0,
        "fishbone_causes_count": len(inv.fishbone_causes) if inv.fishbone_causes else 0,
        "capa_count": len(inv.capa_actions) if inv.capa_actions else 0
    }

    # 4. Classify conversation turn
    classification = groq_service.classify_conversation_turn(
        message=clean_message,
        has_attachment=bool(req.attached_document_id),
        current_state=current_state
    )
    if classification == "OUT_OF_DOMAIN":
        db.add(CopilotMessage(
            investigation_id=inv.id,
            user_id=current_user.id,
            role="user",
            content=clean_message,
            message_type="TEXT"
        ))
        db.add(CopilotMessage(
            investigation_id=inv.id,
            user_id=None,
            role="assistant",
            content=FIXED_REFUSAL,
            message_type="TEXT"
        ))
        await db.commit()
        return CopilotConverseResponse(
            reply_text=FIXED_REFUSAL,
            classification="QUESTION",
            field_patches=[],
            risk_assessment=None,
            missing_fields=[],
            suggested_actions=["Review Investigation Evidence", "Check Evidence Gaps"]
        )

    field_patches: List[FieldPatch] = []
    risk_assessment: Optional[RiskAssessment] = None
    missing_fields: List[MissingInfoItem] = []
    suggested_actions: List[str] = []
    retrieved_sources: List[Dict[str, Any]] = []
    reply_text = ""

    try:
        if classification == "NEW_SOURCE":
            doc_to_analyze = source_text if len(source_text.strip()) > 30 else clean_message

            # Idempotency check: verify if identical source text was already ingested for this dossier
            stmt = select(CopilotMessage).where(
                CopilotMessage.investigation_id == req.investigation_id,
                CopilotMessage.role == "user",
                CopilotMessage.message_type == "NEW_SOURCE"
            )
            past_sources_res = await db.execute(stmt)
            past_sources = past_sources_res.scalars().all()
            already_ingested = any(m.content.strip() == clean_message.strip() for m in past_sources)
            if already_ingested:
                reply_text = (
                    "This incident report has already been ingested for this investigation. "
                    "The structured form draft is populated. You can provide field corrections "
                    "or click 'Commit Form' to save changes."
                )
                suggested_actions = ["Commit Form", "Generate 5 Whys & Fishbone with AI"]
                # Save assistant response
                db.add(CopilotMessage(
                    investigation_id=req.investigation_id,
                    user_id=None,
                    role="assistant",
                    content=reply_text,
                    message_type="TEXT"
                ))
                await db.commit()
                return CopilotConverseResponse(
                    reply_text=reply_text,
                    classification=classification,
                    field_patches=[],
                    risk_assessment=None,
                    missing_fields=[],
                    suggested_actions=suggested_actions
                )

            extraction_data = groq_service.extract_intake_data(
                document_text=doc_to_analyze,
                source_type=source_type,
                pages_metadata=pages_meta
            )

            # Map extracted fields into FieldPatch list
            for field in extraction_data.get("extracted_fields", []):
                fname = field.get("field_name")
                raw_status = field.get("status", "SOURCE_FACT")
                try:
                    patch_status = FieldPatchStatus(raw_status)
                except ValueError:
                    patch_status = FieldPatchStatus.SOURCE_FACT

                field_patches.append(FieldPatch(
                    field_key=fname,
                    label=field.get("label", fname),
                    value=field.get("value"),
                    status=patch_status,
                    source_excerpt=field.get("source_reference"),
                    page_number=field.get("page_number"),
                    reason=field.get("validation_explanation") or "Extracted from incident report"
                ))

            # Assemble risk assessment
            dev_dict = extraction_data.get("deviation", {})
            batch_no = dev_dict.get("batch_number") or "unspecified batch"
            sev_val = dev_dict.get("severity") or "Major"
            containment_action = dev_dict.get("immediate_containment") or "Quarantine impacted batch and initiate cross-functional review."
            risk_text = (
                f"Manufacturing deviation detected for batch {batch_no}. "
                f"Severity evaluated as {sev_val}. Immediate isolation required to protect Critical Quality Attributes."
            )
            risk_assessment = RiskAssessment(
                suggested_severity=sev_val,
                suggested_next_action=containment_action,
                initial_risk_text=risk_text
            )

            # Assemble missing fields
            for m in extraction_data.get("missing_information", []):
                if isinstance(m, dict):
                    missing_fields.append(MissingInfoItem(**m))
                elif isinstance(m, MissingInfoItem):
                    missing_fields.append(m)

            reply_text = (
                f"I've analyzed the incident details and populated the deviation draft fields "
                f"with source citations. Batch {batch_no} is identified with {sev_val} severity. "
                f"Please review the extracted values on the form. You can confirm them or type corrections."
            )
            suggested_actions = ["Review Draft Fields", "Commit Form to Investigation", "Check Evidence Gaps"]

        elif classification == "CORRECTION":
            corrections = groq_service.extract_corrections_patch(
                message=req.message,
                current_fields=req.current_draft_fields
            )
            for c in corrections:
                fkey = c.get("field_key")
                if not fkey:
                    continue
                field_patches.append(FieldPatch(
                    field_key=fkey,
                    label=fkey.replace("_", " ").title(),
                    value=c.get("new_value"),
                    status=FieldPatchStatus.USER_CORRECTION,
                    reason=c.get("reason", "Investigator conversational correction"),
                    user_attributed=current_user.full_name
                ))

            if field_patches:
                summary_items = [f"{p.label} -> '{p.value}'" for p in field_patches]
                reply_text = f"Understood. I have updated the active form draft: {'; '.join(summary_items)}. Marked as 'Edited by you'."
                suggested_actions = ["Save Investigation Changes", "Run Full RCA Engine"]
            else:
                reply_text = f"I noted your correction ('{req.message}'), but couldn't identify the specific deviation field to update. Please specify the field name, e.g. 'batch number is API-2026-104'."
                suggested_actions = ["Save Investigation Changes", "Run Full RCA Engine"]

        elif classification == "ANALYSIS_REQUEST":
            reply_text = (
                "I am ready to conduct root cause analysis. You can trigger the 5-Whys causal chain "
                "or 6M Fishbone decomposition using the actions below, or open the RCA Engine tab."
            )
            suggested_actions = ["Generate 5-Whys Analysis", "Generate 6M Fishbone Analysis", "Draft CAPA Package", "Run Full RCA Engine"]

        else: # QUESTION
            conv_history = [{"role": m.role, "content": m.content} for m in history_msgs[-6:]]
            retrieved_sources = await retrieve_context(db, inv.id, clean_message, budget_tokens=1000)
            reply_text = groq_service.chat_copilot(
                conversation_history=conv_history,
                current_state=current_state,
                user_message=clean_message,
                sources=retrieved_sources
            )
            if check_canary_leak(reply_text) or check_system_prompt_leak(reply_text):
                await log_guard_blocked_audit(
                    db=db,
                    investigation_id=inv.id,
                    category="SYSTEM_PROMPT_LEAK",
                    user_id=current_user.id,
                    user_name=current_user.full_name,
                    raw_input=clean_message
                )
                reply_text = FIXED_REFUSAL
            suggested_actions = ["Run Full RCA Engine", "Check Evidence Gaps", "Draft CAPA Recommendations"]

    except GroqRateLimitError as e:
        logger.warning(f"Copilot converse rate limit: {sanitize_secret(str(e))}")
        raise HTTPException(
            status_code=429,
            detail="AI inference rate limit or quota exceeded. Please wait before retrying."
        )
    except GroqAuthenticationError as e:
        logger.error(f"Copilot converse auth error: {sanitize_secret(str(e))}")
        raise HTTPException(
            status_code=401,
            detail="AI service authentication failed. Please check configured GROQ_API_KEY."
        )
    except GroqTimeoutError as e:
        logger.error(f"Copilot converse timeout: {sanitize_secret(str(e))}")
        raise HTTPException(
            status_code=408,
            detail="AI inference request timed out. Please try again."
        )
    except GroqConnectionError as e:
        logger.error(f"Copilot converse connection error: {sanitize_secret(str(e))}")
        raise HTTPException(
            status_code=503,
            detail="AI inference connection failed. Unable to reach AI inference service."
        )
    except GroqServiceError as e:
        logger.error(f"Copilot converse service error: {sanitize_secret(str(e))}")
        raise HTTPException(
            status_code=503,
            detail=f"AI Copilot Inference Service Unavailable: {sanitize_secret(str(e))}"
        )
    except Exception as e:
        logger.error(f"Copilot converse unexpected error: {sanitize_secret(str(e))}")
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred during Copilot conversation: {sanitize_secret(str(e))}"
        )

    # 5. Persist interaction into copilot_messages table
    user_msg = CopilotMessage(
        investigation_id=inv.id,
        user_id=current_user.id,
        role="user",
        content=req.message,
        message_type="FILE_ATTACHMENT" if req.attached_document_id else "TEXT"
    )
    db.add(user_msg)

    extra_payload = {
        "field_patches": [p.model_dump() for p in field_patches],
        "risk_assessment": risk_assessment.model_dump() if risk_assessment else None,
        "missing_fields": [m.model_dump() for m in missing_fields],
        "classification": classification,
        "suggested_actions": suggested_actions
    }
    asst_msg = CopilotMessage(
        investigation_id=inv.id,
        user_id=None,
        role="assistant",
        content=reply_text,
        message_type=classification,
        extra_data=json.dumps(extra_payload)
    )
    db.add(asst_msg)
    await db.flush()

    # 6. Audit trail
    await audit_service.log_action(
        db, inv.id, "COPILOT_CONVERSE", inv.stage,
        f"Copilot turn ({classification}): '{req.message[:80]}'",
        user_id=current_user.id,
        user_name=current_user.full_name
    )
    await db.commit()

    return CopilotConverseResponse(
        reply_text=reply_text,
        classification=classification,
        field_patches=field_patches,
        risk_assessment=risk_assessment,
        missing_fields=missing_fields,
        suggested_actions=suggested_actions,
        sources=retrieved_sources if classification == "QUESTION" else None,
        workflow_state=current_state
    )

@router.get("/investigations/{investigation_id}/messages", response_model=List[CopilotMessageRead])
async def get_investigation_messages(
    investigation_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve complete audit-logged Copilot conversation history for an investigation."""
    await verify_investigation_access(investigation_id, current_user, db)
    result = await db.execute(
        select(CopilotMessage)
        .where(CopilotMessage.investigation_id == investigation_id)
        .order_by(CopilotMessage.created_at.asc())
    )
    return result.scalars().all()

@router.post("/chat", response_model=CopilotChatResponse)
async def copilot_chat(
    req: CopilotChatRequest = Body(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Interactive conversation with AI Investigation Copilot.
    """
    await verify_investigation_access(req.investigation_id, current_user, db)
    inv = await get_investigation_by_id(req.investigation_id, db)
    
    current_state = {
        "investigation_number": inv.investigation_number,
        "title": inv.title,
        "stage": inv.stage,
        "status": inv.status,
        "deviation": {
            "batch": inv.deviation.batch_number if inv.deviation else None,
            "product": inv.deviation.product_name if inv.deviation else None,
            "unit_operation": inv.deviation.unit_operation if inv.deviation else None,
            "equipment": inv.deviation.equipment_id if inv.deviation else None,
            "severity": inv.deviation.severity if inv.deviation else None,
        } if inv.deviation else None,
        "five_whys_count": len(inv.five_whys),
        "fishbone_causes_count": len(inv.fishbone_causes),
        "capa_count": len(inv.capa_actions)
    }

    clean_message = validate_chat_input(req.message, max_chars=2000)

    # Attack & injection detection
    inj = detect_injection(clean_message)
    if inj["suspected"]:
        await log_guard_blocked_audit(
            db=db,
            investigation_id=inv.id,
            category=",".join(inj["categories"]),
            user_id=current_user.id,
            user_name=current_user.full_name,
            raw_input=clean_message
        )
        if set(inj["categories"]).intersection({"PROMPT_EXTRACTION", "JAILBREAK_DAN", "INSTRUCTION_OVERRIDE", "DATA_SMUGGLING", "MULTILINGUAL_INJECTION", "DELIMITER_SPOOFING"}):
            return CopilotChatResponse(
                response=FIXED_REFUSAL,
                suggested_actions=["Review Investigation Evidence", "Check Evidence Gaps"],
                workflow_state=current_state
            )

    if is_strictly_out_of_domain(clean_message):
        return CopilotChatResponse(
            response=FIXED_REFUSAL,
            suggested_actions=["Review Investigation Evidence", "Check Evidence Gaps"],
            workflow_state=current_state
        )

    retrieved_sources = await retrieve_context(db, inv.id, clean_message, budget_tokens=1000)

    try:
        ai_reply = groq_service.chat_copilot(
            conversation_history=[],
            current_state=current_state,
            user_message=clean_message,
            sources=retrieved_sources
        )
        if check_canary_leak(ai_reply) or check_system_prompt_leak(ai_reply):
            await log_guard_blocked_audit(
                db=db,
                investigation_id=inv.id,
                category="SYSTEM_PROMPT_LEAK",
                user_id=current_user.id,
                user_name=current_user.full_name,
                raw_input=clean_message
            )
            ai_reply = FIXED_REFUSAL
    except GroqRateLimitError as e:
        logger.warning(f"Copilot chat rate limit: {sanitize_secret(str(e))}")
        raise HTTPException(
            status_code=429,
            detail="AI inference rate limit or quota exceeded. Please wait before retrying."
        )
    except GroqAuthenticationError as e:
        logger.error(f"Copilot chat auth error: {sanitize_secret(str(e))}")
        raise HTTPException(
            status_code=401,
            detail="AI service authentication failed. Please check configured GROQ_API_KEY."
        )
    except GroqTimeoutError as e:
        logger.error(f"Copilot chat timeout: {sanitize_secret(str(e))}")
        raise HTTPException(
            status_code=408,
            detail="AI inference request timed out. Please try again."
        )
    except GroqConnectionError as e:
        logger.error(f"Copilot chat connection error: {sanitize_secret(str(e))}")
        raise HTTPException(
            status_code=503,
            detail="AI inference connection failed. Unable to reach AI inference service."
        )
    except GroqServiceError as e:
        logger.error(f"Copilot chat service error: {sanitize_secret(str(e))}")
        raise HTTPException(
            status_code=503,
            detail=f"AI Copilot Inference Service Unavailable: {sanitize_secret(str(e))}"
        )
    except Exception as e:
        logger.error(f"Copilot chat failed: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"An unexpected error occurred during Copilot chat: {sanitize_secret(str(e))}"
        )

    suggested_actions = []
    if "5" in req.message.lower() or "why" in req.message.lower():
        suggested_actions.append("Generate 5-Whys Analysis")
    if "fishbone" in req.message.lower() or "cause" in req.message.lower():
        suggested_actions.append("Generate 6M Fishbone Analysis")
    if "capa" in req.message.lower():
        suggested_actions.append("Draft CAPA Package")
    if not suggested_actions:
        suggested_actions = ["Run Full RCA Engine", "Check Evidence Gaps", "Draft CAPA Recommendations"]

    # Record AI interaction
    ai_record = AiInteraction(
        investigation_id=inv.id,
        interaction_type="COPILOT_CHAT",
        prompt_summary=req.message[:200],
        response_data=ai_reply[:500],
        model_name=groq_service.model
    )
    db.add(ai_record)
    await db.flush()

    return CopilotChatResponse(
        response=ai_reply,
        suggested_actions=suggested_actions,
        sources=retrieved_sources,
        workflow_state=current_state
    )

@router.post("/generate-rca", response_model=RcaAnalysisResult)
async def generate_rca_analysis(
    req: GenerateRcaRequest = Body(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate 5 Whys, Fishbone (6Ms), Root Cause statements, and CAPA actions for an investigation.
    """
    await verify_investigation_access(req.investigation_id, current_user, db, require_write=True)
    inv = await get_investigation_by_id(req.investigation_id, db)
    if not inv.deviation:
        raise HTTPException(
            status_code=400, 
            detail="Cannot run RCA analysis without deviation details. Please complete incident intake first."
        )

    dev_dict = {
        "deviation_number": inv.deviation.deviation_number,
        "batch_number": inv.deviation.batch_number,
        "product_name": inv.deviation.product_name,
        "unit_operation": inv.deviation.unit_operation,
        "equipment_id": inv.deviation.equipment_id,
        "severity": inv.deviation.severity,
        "description": inv.deviation.description,
        "immediate_containment": inv.deviation.immediate_containment
    }

    # Enrich prompt context with verified findings and active evidence dossier items
    context_sections = []
    if req.user_context:
        context_sections.append(f"Investigator Guidance / Context:\n{req.user_context}")

    verified_findings = [f.finding_text for f in (inv.findings or []) if f.is_verified or f.is_accepted]
    if verified_findings:
        context_sections.append("Verified Findings from Intake Dossier:\n" + "\n".join(f"- {f}" for f in verified_findings[:10]))

    active_evidences = [e for e in (inv.evidences or []) if not e.is_archived]
    if active_evidences:
        context_sections.append("Available Evidence Records in Dossier:\n" + "\n".join(f"- [{e.evidence_type}] {e.title} ({e.source_location or 'N/A'})" for e in active_evidences[:10]))

    combined_context = "\n\n".join(context_sections) if context_sections else None

    try:
        rca_data = groq_service.generate_rca_analysis(dev_dict, combined_context)
    except GroqRateLimitError as e:
        logger.warning(f"Groq rate limit: {sanitize_secret(str(e))}")
        raise HTTPException(
            status_code=429,
            detail="AI inference rate limit or quota exceeded. Please wait before retrying."
        )
    except GroqAuthenticationError as e:
        logger.error(f"Groq authentication error: {sanitize_secret(str(e))}")
        raise HTTPException(
            status_code=401,
            detail="AI service authentication failed. Please check configured GROQ_API_KEY."
        )
    except GroqTimeoutError as e:
        logger.error(f"Groq timeout: {sanitize_secret(str(e))}")
        raise HTTPException(
            status_code=408,
            detail="AI inference request timed out. Please try again."
        )
    except GroqConnectionError as e:
        logger.error(f"Groq connection error: {sanitize_secret(str(e))}")
        raise HTTPException(
            status_code=503,
            detail="AI inference connection failed. Unable to reach AI inference service."
        )
    except GroqServiceError as e:
        logger.error(f"Groq service error: {sanitize_secret(str(e))}")
        raise HTTPException(
            status_code=503,
            detail=f"AI RCA Analysis Service Unavailable: {sanitize_secret(str(e))}"
        )
    except Exception as e:
        logger.error(f"RCA generation unexpected error: {sanitize_secret(str(e))}")
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred during RCA generation: {sanitize_secret(str(e))}"
        )

    # Record AI interaction
    ai_record = AiInteraction(
        investigation_id=inv.id,
        interaction_type="RCA_ANALYSIS",
        prompt_summary=f"Generated 5-Whys, Fishbone, Root Cause, and CAPA for {inv.deviation.batch_number}",
        response_data=str(rca_data)[:500],
        model_name=groq_service.model
    )
    db.add(ai_record)
    await db.flush()

    return RcaAnalysisResult(
        status=rca_data.get("status", "SUCCESS"),
        error_message=rca_data.get("error_message"),
        five_whys=rca_data.get("five_whys", []),
        fishbone_causes=rca_data.get("fishbone_causes", []),
        root_causes=rca_data.get("root_causes", []),
        capa_actions=rca_data.get("capa_actions", []),
        evidence_gaps=rca_data.get("evidence_gaps", []),
        investigator_guidance=rca_data.get("investigator_guidance", "Review findings with cross-functional investigation team.")
    )

@router.post("/apply-rca-to-investigation", response_model=InvestigationRead)
async def apply_rca_to_investigation(
    investigation_id: int = Body(..., embed=True),
    rca_data: Dict[str, Any] = Body(..., embed=True),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Commit the AI generated 5 Whys, Fishbone, Root Causes, and CAPAs into the database.
    All are marked as AI-suggested (is_ai_suggested=True, is_verified=False) for investigator review.
    """
    await verify_investigation_access(investigation_id, current_user, db, require_write=True)
    inv = await get_investigation_by_id(investigation_id, db)

    # 1. Five Whys
    for item in rca_data.get("five_whys", []):
        step = FiveWhysStep(
            investigation_id=inv.id,
            step_number=item.get("step_number", 1),
            question=item.get("question", ""),
            answer=item.get("answer", ""),
            evidence_reference=item.get("evidence_reference"),
            is_ai_suggested=True,
            is_verified=False
        )
        db.add(step)
        inv.five_whys.append(step)

    # 2. Fishbone
    for item in rca_data.get("fishbone_causes", []):
        cause = FishboneCause(
            investigation_id=inv.id,
            category=item.get("category", "MACHINE"),
            cause_description=item.get("cause_description", ""),
            status=item.get("status", "HYPOTHESIS"),
            rationale=item.get("rationale"),
            evidence_reference=item.get("evidence_reference"),
            is_ai_suggested=True,
            is_verified=False
        )
        db.add(cause)
        inv.fishbone_causes.append(cause)

    # 3. Root Causes (Classified as PROPOSED; no auto-confirmation or bulk evidence association)
    created_root_causes = []
    for item in rca_data.get("root_causes", []):
        rc = RootCause(
            investigation_id=inv.id,
            cause_statement=item.get("cause_statement", ""),
            category=item.get("category", "EQUIPMENT_FAILURE"),
            is_primary=item.get("is_primary", True),
            status="PROPOSED",
            rationale=item.get("rationale"),
            evidence_summary=item.get("evidence_summary"),
            is_ai_suggested=True,
            is_verified=False,
            source_type="DIRECT_SYNTHESIS"
        )
        db.add(rc)
        inv.root_causes.append(rc)
        created_root_causes.append(rc)
    
    await db.flush()
    primary_rc = created_root_causes[0] if created_root_causes else None

    # Persist any evidence gaps from RCA analysis
    for gap_item in rca_data.get("evidence_gaps", []):
        if isinstance(gap_item, str):
            category = "INVESTIGATION_GAP"
            question = gap_item
            impact = "Required to verify root cause hypothesis"
            suggested = None
            urgency = "HIGH"
        elif isinstance(gap_item, dict):
            category = gap_item.get("category", "INVESTIGATION_GAP")
            question = gap_item.get("question", "")
            impact = gap_item.get("impact_description", "Required to verify root cause hypothesis")
            suggested = gap_item.get("suggested_record")
            urgency = gap_item.get("urgency", "HIGH")
        else:
            continue

        gap = EvidenceGap(
            investigation_id=inv.id,
            root_cause_id=primary_rc.id if primary_rc else None,
            category=category,
            question=question,
            impact_description=impact,
            suggested_record=suggested,
            urgency=urgency,
            is_resolved=False
        )
        db.add(gap)

    # 4. CAPAs
    primary_rc_id = primary_rc.id if primary_rc else None
    for item in rca_data.get("capa_actions", []):
        capa = CapaAction(
            investigation_id=inv.id,
            root_cause_id=primary_rc_id,
            action_type=item.get("action_type", "CORRECTIVE_ACTION"),
            description=item.get("description", ""),
            rationale=item.get("rationale"),
            owner=item.get("owner", "Quality Assurance"),
            deadline=item.get("deadline", "30 Days"),
            effectiveness_criteria=item.get("effectiveness_criteria"),
            effectiveness_review_period_days=item.get("effectiveness_review_period_days", 30),
            status="PROPOSED",
            is_ai_suggested=True,
            is_verified=False
        )
        db.add(capa)
        inv.capa_actions.append(capa)

    # Update investigation stage
    inv.stage = "ROOT_CAUSE"
    await db.flush()

    await audit_service.log_action(
        db, inv.id, "AI_APPLIED", "ROOT_CAUSE",
        "Applied AI generated 5-Whys, Fishbone causes, Root Cause, evidence links, and CAPA proposals",
        user_id=current_user.id,
        user_name=current_user.full_name
    )

    await db.commit()
    return await get_investigation_by_id(investigation_id, db)

@router.post("/apply-rca-item", response_model=Dict[str, Any])
async def apply_rca_item(
    req: ApplyRcaItemRequest = Body(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Accept an individual proposed item (Why step, Fishbone cause, Root cause, CAPA, or Gap) into the investigation.
    Allows granular investigator curation rather than all-or-nothing overwrite.
    """
    await verify_investigation_access(req.investigation_id, current_user, db, require_write=True)
    inv = await get_investigation_by_id(req.investigation_id, db)
    item_type = req.item_type.upper()
    data = req.item_data

    created_id = None
    if item_type == "FIVE_WHYS":
        step = FiveWhysStep(
            investigation_id=inv.id,
            step_number=data.get("step_number", len(inv.five_whys) + 1),
            question=data.get("question", ""),
            answer=data.get("answer", ""),
            evidence_reference=data.get("evidence_reference"),
            is_ai_suggested=True,
            is_verified=False
        )
        db.add(step)
        await db.flush()
        created_id = step.id
        await audit_service.log_action(
            db, inv.id, "ACCEPTED_ITEM", "FIVE_WHYS",
            f"Accepted Why #{step.step_number}: '{step.question}'", entity_id=str(step.id),
            user_id=current_user.id, user_name=current_user.full_name
        )

    elif item_type == "FISHBONE":
        cause = FishboneCause(
            investigation_id=inv.id,
            category=data.get("category", "MACHINE").upper(),
            cause_description=data.get("cause_description", ""),
            status="HYPOTHESIS",
            rationale=data.get("rationale"),
            evidence_reference=data.get("evidence_reference"),
            is_ai_suggested=True,
            is_verified=False
        )
        db.add(cause)
        await db.flush()
        created_id = cause.id
        await audit_service.log_action(
            db, inv.id, "ACCEPTED_ITEM", "FISHBONE",
            f"Accepted Fishbone cause in {cause.category}: '{cause.cause_description}'", entity_id=str(cause.id),
            user_id=current_user.id, user_name=current_user.full_name
        )

    elif item_type == "ROOT_CAUSE":
        rc = RootCause(
            investigation_id=inv.id,
            cause_statement=data.get("cause_statement", ""),
            category=data.get("category", "EQUIPMENT_FAILURE"),
            is_primary=data.get("is_primary", True),
            status="PROPOSED",
            rationale=data.get("rationale"),
            evidence_summary=data.get("evidence_summary"),
            is_ai_suggested=True,
            is_verified=False,
            source_type="DIRECT_SYNTHESIS"
        )
        db.add(rc)
        await db.flush()
        created_id = rc.id
        await audit_service.log_action(
            db, inv.id, "ACCEPTED_ITEM", "ROOT_CAUSE",
            f"Accepted Root Cause proposal #{rc.id}: '{rc.cause_statement}'", entity_id=str(rc.id),
            user_id=current_user.id, user_name=current_user.full_name
        )

    elif item_type == "CAPA":
        capa = CapaAction(
            investigation_id=inv.id,
            action_type=data.get("action_type", "CORRECTIVE_ACTION"),
            description=data.get("description", ""),
            rationale=data.get("rationale"),
            owner=data.get("owner", "Quality Assurance"),
            deadline=data.get("deadline", "30 Days"),
            effectiveness_criteria=data.get("effectiveness_criteria"),
            effectiveness_review_period_days=data.get("effectiveness_review_period_days", 30),
            status="PROPOSED",
            is_ai_suggested=True,
            is_verified=False
        )
        db.add(capa)
        await db.flush()
        created_id = capa.id
        await audit_service.log_action(
            db, inv.id, "ACCEPTED_ITEM", "CAPA",
            f"Accepted CAPA: '{capa.description}'", entity_id=str(capa.id),
            user_id=current_user.id, user_name=current_user.full_name
        )

    elif item_type == "EVIDENCE_GAP":
        gap = EvidenceGap(
            investigation_id=inv.id,
            category=data.get("category", "INVESTIGATION_GAP"),
            question=data.get("question", ""),
            impact_description=data.get("impact_description", "Required to verify root cause hypothesis"),
            suggested_record=data.get("suggested_record"),
            urgency=data.get("urgency", "HIGH")
        )
        db.add(gap)
        await db.flush()
        created_id = gap.id
        await audit_service.log_action(
            db, inv.id, "ACCEPTED_ITEM", "EVIDENCE_GAP",
            f"Accepted Evidence Gap: '{gap.question}'", entity_id=str(gap.id),
            user_id=current_user.id, user_name=current_user.full_name
        )
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported item_type: {item_type}")

    await db.commit()
    return {"ok": True, "item_type": item_type, "created_id": created_id}

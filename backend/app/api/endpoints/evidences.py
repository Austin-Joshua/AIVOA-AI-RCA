import os
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Body, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_user, verify_investigation_access
from app.models.investigation import Investigation
from app.models.evidence import Evidence, InvestigationFinding, EvidenceGap
from app.models.root_cause import RootCause, RootCauseEvidenceLink, ContradictionDisposition
from app.models.five_whys import FiveWhysStep
from app.models.fishbone import FishboneCause
from app.models.audit import User
from app.schemas.evidence import (
    EvidenceCreate,
    EvidenceUpdate,
    EvidenceVerifyRequest,
    EvidenceRead,
    EvidenceGapCreate,
    EvidenceGapResponseRequest,
    EvidenceGapResolveRequest,
    EvidenceGapRead,
)
from app.schemas.root_cause import (
    RootCauseEvidenceLinkCreate,
    RootCauseEvidenceLinkRead,
    RootCauseConfirmRequest,
    RootCauseRejectRequest,
    RootCauseRead,
    RootCauseCreate,
    RootCauseUpdate,
    ContradictionDispositionCreate,
    ContradictionDispositionRead,
)
from app.services.document_parser import document_parser
from app.services.audit_service import audit_service
from app.services.storage_service import storage_service, FileIntegrityError

router = APIRouter()

# ---------------------------------------------------------
# Evidence Endpoints
# ---------------------------------------------------------

@router.post("/investigations/{investigation_id}/evidences/upload", response_model=EvidenceRead)
async def upload_evidence_file(
    investigation_id: int,
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    evidence_type: Optional[str] = Form("DOCUMENT"),
    classification: Optional[str] = Form("PRIMARY_SOURCE"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload and persist an original evidence file with SHA-256 integrity hash,
    isolated disk persistence, structured page-level extraction, and audit trail.
    Requires authenticated user with investigation write access.
    """
    await verify_investigation_access(investigation_id, current_user, db, require_write=True)

    # Read and validate upload (size limits, extension, magic bytes)
    file_bytes, safe_filename, ext = await storage_service.read_and_validate_upload(file)
    file_size = len(file_bytes)
    
    # Save original bytes to isolated investigation storage directory
    file_path, sha256_hash = storage_service.save_evidence_file(investigation_id, safe_filename, file_bytes)
    evidence_title = title or safe_filename

    # Extract text and page structures
    source_location = "Document Body"
    page_num = 1
    source_meta = {}
    extracted_text = ""

    if ext == ".pdf":
        try:
            parsed = document_parser.parse_pdf_structured(file_bytes)
            extracted_text = parsed["full_text"]
            source_meta = {
                "page_count": parsed["page_count"],
                "file_hash_sha256": sha256_hash,
                "metadata": parsed["metadata"],
                "pages_summary": [{"page_number": p["page_number"], "chars": p["char_count"]} for p in parsed["pages"]],
                "pages": parsed["pages"]
            }
            source_location = f"Pages 1-{parsed['page_count']}"
            page_num = 1
        except Exception as e:
            extracted_text = f"[PDF Extraction Error: {str(e)}]"
    else:
        text_content = file_bytes.decode("utf-8", errors="replace")
        if "subject:" in text_content.lower() and "from:" in text_content.lower():
            parsed_email = document_parser.parse_email(text_content)
            extracted_text = parsed_email["body"]
            source_meta = parsed_email["headers"]
            evidence_type = "EMAIL"
            source_location = "Email Body"
        else:
            extracted_text = document_parser.clean_text(text_content)
            source_location = "Text Document"
            source_meta = {"char_count": len(extracted_text)}

    evidence = Evidence(
        investigation_id=investigation_id,
        title=evidence_title,
        original_filename=file.filename or safe_filename,
        file_path=file_path,
        file_size_bytes=file_size,
        file_hash_sha256=sha256_hash,
        evidence_type=evidence_type or "DOCUMENT",
        classification=classification or "PRIMARY_SOURCE",
        source=safe_filename,
        source_location=source_location,
        page_number=page_num,
        extracted_text=extracted_text,
        source_metadata=source_meta,
        confidence_score=1.0,
        is_verified=False,
        verified_by=None,
        verified_by_user_id=None,
        uploaded_by_user_id=current_user.id,
        is_archived=False
    )
    db.add(evidence)
    await db.flush()
    await db.refresh(evidence)

    # Automatically generate finding reference
    finding = InvestigationFinding(
        investigation_id=investigation_id,
        evidence_id=evidence.id,
        finding_text=f"Uploaded source evidence: {safe_filename} ({evidence_type}, {file_size} bytes)",
        finding_type="FACT",
        evidence_reference=f"Evidence #{evidence.id} ({safe_filename})",
        source_location=source_location,
        is_ai_suggested=False,
        is_verified=False,
        citation_verified=True,
        validation_status="VERIFIED_SOURCE_FACT"
    )
    db.add(finding)

    await audit_service.log_action(
        db, investigation_id, "CREATED", "EVIDENCE",
        f"Uploaded evidence '{safe_filename}' (SHA-256: {sha256_hash[:12]}..., Type: {evidence_type})",
        entity_id=str(evidence.id),
        user_name=current_user.full_name,
        user_id=current_user.id
    )
    await db.commit()
    
    # Hide raw internal disk path in client response and attach download URL
    res = EvidenceRead.model_validate(evidence)
    res.file_path = None
    res.download_url = f"/api/v1/evidences/{evidence.id}/download"
    return res

@router.get("/evidences/{evidence_id}/download")
async def download_evidence_file(
    evidence_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Authorized evidence file download endpoint.
    Verifies caller access to the parent investigation before retrieving.
    Recalculates SHA-256 checksum against stored fingerprint before returning.
    Rejects retrieval and logs audit event on integrity mismatch.
    """
    res = await db.execute(select(Evidence).filter(Evidence.id == evidence_id))
    evidence = res.scalar_one_or_none()
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")

    # Strict isolation: caller must be authorized for this investigation
    await verify_investigation_access(evidence.investigation_id, current_user, db)

    if not evidence.file_path:
        raise HTTPException(status_code=404, detail="No stored physical file available for this evidence record.")

    try:
        disk_bytes = storage_service.retrieve_and_verify_file(
            file_path_str=evidence.file_path,
            expected_hash=evidence.file_hash_sha256
        )
    except FileIntegrityError as e:
        await audit_service.log_action(
            db, evidence.investigation_id, "INTEGRITY_FAILED", "EVIDENCE",
            f"SHA-256 integrity verification failed during download for Evidence #{evidence.id}: {str(e)}",
            entity_id=str(evidence.id),
            user_name=current_user.full_name,
            user_id=current_user.id
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Evidence integrity check failed: On-disk SHA-256 hash does not match registered fingerprint."
        )

    ext = os.path.splitext(evidence.original_filename or "")[1].lower()
    media_type = "application/pdf" if ext == ".pdf" else "application/octet-stream"
    filename = evidence.original_filename or f"evidence_{evidence.id}.bin"

    return Response(
        content=disk_bytes,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

@router.post("/investigations/{investigation_id}/evidences/manual", response_model=EvidenceRead)
async def create_manual_evidence(
    investigation_id: int,
    ev_in: EvidenceCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a structured evidence record manually (e.g. interview, inspection)."""
    await verify_investigation_access(investigation_id, current_user, db, require_write=True)

    evidence = Evidence(
        investigation_id=investigation_id,
        title=ev_in.title,
        evidence_type=ev_in.evidence_type,
        classification=ev_in.classification,
        source=ev_in.source or "Manual Entry",
        source_location=ev_in.source_location or "Physical Observation",
        page_number=ev_in.page_number,
        extracted_text=ev_in.extracted_text or "",
        source_metadata=ev_in.source_metadata,
        confidence_score=ev_in.confidence_score,
        is_verified=False,
        verified_by=None,
        verified_by_user_id=None,
        uploaded_by_user_id=current_user.id,
        investigator_notes=ev_in.investigator_notes,
        is_archived=False
    )
    db.add(evidence)
    await db.flush()
    await db.refresh(evidence)

    await audit_service.log_action(
        db, investigation_id, "CREATED", "EVIDENCE",
        f"Manually logged evidence '{evidence.title}' ({evidence.evidence_type})",
        entity_id=str(evidence.id),
        user_name=current_user.full_name,
        user_id=current_user.id
    )
    await db.commit()
    res = EvidenceRead.model_validate(evidence)
    res.file_path = None
    return res

@router.get("/investigations/{investigation_id}/evidences", response_model=List[EvidenceRead])
async def list_investigation_evidences(
    investigation_id: int,
    include_archived: bool = Query(False, description="Whether to include soft-archived evidence records"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all evidence items associated with an investigation (excluding archived by default)."""
    await verify_investigation_access(investigation_id, current_user, db)
    query = select(Evidence).filter(Evidence.investigation_id == investigation_id)
    if not include_archived:
        query = query.filter(Evidence.is_archived == False)
    query = query.order_by(Evidence.created_at.desc())
    res = await db.execute(query)
    items = res.scalars().all()
    
    out = []
    for ev in items:
        r = EvidenceRead.model_validate(ev)
        r.file_path = None
        if ev.file_path:
            r.download_url = f"/api/v1/evidences/{ev.id}/download"
        out.append(r)
    return out

@router.get("/evidences/{evidence_id}", response_model=EvidenceRead)
async def get_evidence(
    evidence_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve detailed evidence information."""
    res = await db.execute(select(Evidence).filter(Evidence.id == evidence_id))
    evidence = res.scalar_one_or_none()
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")
    await verify_investigation_access(evidence.investigation_id, current_user, db)
    r = EvidenceRead.model_validate(evidence)
    r.file_path = None
    if evidence.file_path:
        r.download_url = f"/api/v1/evidences/{evidence.id}/download"
    return r

@router.put("/evidences/{evidence_id}", response_model=EvidenceRead)
async def update_evidence(
    evidence_id: int,
    update_in: EvidenceUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update evidence metadata or investigator notes with audit log.
    STRICT DATA INTEGRITY GUARD:
    Rejects any modification of original extracted source text or source hash.
    """
    res = await db.execute(select(Evidence).filter(Evidence.id == evidence_id))
    evidence = res.scalar_one_or_none()
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")

    await verify_investigation_access(evidence.investigation_id, current_user, db, require_write=True)

    # Protect original extracted source text from tampering
    if update_in.extracted_text is not None and update_in.extracted_text != evidence.extracted_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Data integrity violation: Original extracted source text is immutable under cGMP rules. "
                "Add annotations or corrections in 'investigator_notes' instead of altering source text."
            )
        )

    changes = []
    update_dict = update_in.dict(exclude_unset=True)
    
    # Strictly protect immutable evidence fields against generic tampering
    protected_fields = {
        "extracted_text", "is_verified", "verified_by", "verified_by_user_id",
        "verification_date", "uploaded_by_user_id", "is_archived", "archived_at",
        "archived_by", "archival_reason"
    }
    for field in protected_fields:
        update_dict.pop(field, None)

    for k, v in update_dict.items():
        old_val = getattr(evidence, k)
        if old_val != v:
            setattr(evidence, k, v)
            changes.append(f"{k}: '{old_val}' -> '{v}'")

    evidence.updated_at = datetime.utcnow()
    await db.flush()

    if changes:
        await audit_service.log_action(
            db, evidence.investigation_id, "UPDATED", "EVIDENCE",
            "; ".join(changes), entity_id=str(evidence.id),
            user_id=current_user.id, user_name=current_user.full_name
        )
    await db.commit()
    r = EvidenceRead.model_validate(evidence)
    r.file_path = None
    if evidence.file_path:
        r.download_url = f"/api/v1/evidences/{evidence.id}/download"
    return r

@router.post("/evidences/{evidence_id}/verify", response_model=EvidenceRead)
async def verify_evidence(
    evidence_id: int,
    req: EvidenceVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Human verification of an evidence record with audit logging."""
    res = await db.execute(select(Evidence).filter(Evidence.id == evidence_id))
    evidence = res.scalar_one_or_none()
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")

    await verify_investigation_access(evidence.investigation_id, current_user, db, require_write=False)

    if evidence.is_archived:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot verify an archived evidence record. Unarchive or re-upload evidence first."
        )

    # Authorization & Segregation of Duties:
    if evidence.uploaded_by_user_id is not None:
        # Case A — Attributable evidence: original uploader cannot verify their own submission
        if evidence.uploaded_by_user_id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Separation of duties violation: The original uploader cannot verify their own evidence record. "
                    "Verification requires an independent reviewer."
                )
            )
    else:
        # Case B — Unattributable legacy evidence (uploaded_by_user_id IS NULL):
        # Fail-closed policy: Cannot establish uploader identity, so ordinary investigators
        # and assigned lead investigators without QA/Admin role cannot verify.
        # Only QA_APPROVER or ADMIN may formally verify legacy evidence.
        if current_user.role not in ("QA_APPROVER", "ADMIN"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Forbidden: Unattributable legacy evidence record (missing uploader identity). "
                    "In accordance with cGMP separation-of-duties governance, verification of legacy evidence "
                    "requires explicit QA_APPROVER or ADMIN authorization."
                )
            )

    verified_by_name = current_user.full_name

    evidence.is_verified = True
    evidence.verified_by = verified_by_name
    evidence.verified_by_user_id = current_user.id
    evidence.verification_date = datetime.utcnow()
    if req.verification_notes:
        evidence.investigator_notes = (evidence.investigator_notes or "") + f"\n[Verification Note]: {req.verification_notes}"
    evidence.updated_at = datetime.utcnow()

    auth_tag = f" (User ID #{current_user.id})"
    await audit_service.log_action(
        db, evidence.investigation_id, "VERIFIED", "EVIDENCE",
        f"Evidence '{evidence.title}' verified by {verified_by_name}{auth_tag}. Notes: {req.verification_notes or 'None'}",
        entity_id=str(evidence.id),
        user_id=current_user.id,
        user_name=verified_by_name
    )
    await db.commit()
    r = EvidenceRead.model_validate(evidence)
    r.file_path = None
    if evidence.file_path:
        r.download_url = f"/api/v1/evidences/{evidence.id}/download"
    return r

@router.delete("/evidences/{evidence_id}")
async def delete_evidence(
    evidence_id: int,
    archival_reason: Optional[str] = Query(None, description="Reason for archiving evidence"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Soft-archives an evidence record.
    Preserves historical relational links, citations, and checksums for cGMP auditability.
    """
    res = await db.execute(select(Evidence).filter(Evidence.id == evidence_id))
    evidence = res.scalar_one_or_none()
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")

    await verify_investigation_access(evidence.investigation_id, current_user, db, require_write=True)

    inv_id = evidence.investigation_id
    title = evidence.title
    investigator_name = current_user.full_name

    evidence.is_archived = True
    evidence.archived_at = datetime.utcnow()
    evidence.archived_by = investigator_name
    evidence.archival_reason = archival_reason or "Archived by investigator"
    evidence.updated_at = datetime.utcnow()

    await audit_service.log_action(
        db, inv_id, "ARCHIVED", "EVIDENCE",
        f"Evidence '{title}' (ID #{evidence_id}) soft-archived by {investigator_name}. Reason: {evidence.archival_reason}",
        entity_id=str(evidence_id),
        user_id=current_user.id,
        user_name=investigator_name
    )
    await db.commit()
    return {"deleted": True, "id": evidence_id, "is_archived": True}

# ---------------------------------------------------------
# Evidence Gap Endpoints
# ---------------------------------------------------------

@router.get("/investigations/{investigation_id}/evidence-gaps", response_model=List[EvidenceGapRead])
async def list_investigation_evidence_gaps(
    investigation_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all evidence gaps identified for an investigation."""
    await verify_investigation_access(investigation_id, current_user, db)
    query = select(EvidenceGap).filter(EvidenceGap.investigation_id == investigation_id).order_by(EvidenceGap.created_at.asc())
    res = await db.execute(query)
    return res.scalars().all()

@router.post("/investigations/{investigation_id}/evidence-gaps", response_model=EvidenceGapRead)
async def create_evidence_gap(
    investigation_id: int,
    gap_in: EvidenceGapCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a structured missing evidence gap item."""
    await verify_investigation_access(investigation_id, current_user, db, require_write=True)
    gap = EvidenceGap(
        investigation_id=investigation_id,
        category=gap_in.category,
        question=gap_in.question,
        impact_description=gap_in.impact_description,
        suggested_record=gap_in.suggested_record,
        urgency=gap_in.urgency or "MEDIUM",
        is_resolved=False
    )
    db.add(gap)
    await db.flush()
    await db.refresh(gap)

    await audit_service.log_action(
        db, investigation_id, "CREATED", "EVIDENCE_GAP",
        f"Identified evidence gap ({gap.category}): {gap.question}",
        entity_id=str(gap.id),
        user_id=current_user.id,
        user_name=current_user.full_name
    )
    await db.commit()
    return gap

@router.post("/evidence-gaps/{gap_id}/respond", response_model=EvidenceGapRead)
async def respond_to_evidence_gap(
    gap_id: int,
    req: EvidenceGapResponseRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Investigator submits factual response to a missing information question."""
    res = await db.execute(select(EvidenceGap).filter(EvidenceGap.id == gap_id))
    gap = res.scalar_one_or_none()
    if not gap:
        raise HTTPException(status_code=404, detail="Evidence gap not found")

    await verify_investigation_access(gap.investigation_id, current_user, db, require_write=True)

    responder = current_user.full_name
    response_text = getattr(req, "response", None) or getattr(req, "investigator_response", "")

    gap.investigator_response = response_text
    gap.responded_by = responder
    gap.response_timestamp = datetime.utcnow()
    gap.updated_at = datetime.utcnow()

    await audit_service.log_action(
        db, gap.investigation_id, "GAP_ANSWERED", "EVIDENCE_GAP",
        f"Gap #{gap.id} answered by {responder}: {response_text[:80]}...",
        entity_id=str(gap.id),
        user_id=current_user.id,
        user_name=responder
    )
    await db.commit()
    return gap

@router.post("/evidence-gaps/{gap_id}/resolve", response_model=EvidenceGapRead)
async def resolve_evidence_gap(
    gap_id: int,
    req: EvidenceGapResolveRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark an evidence gap as resolved, linking to the resolving evidence."""
    res = await db.execute(select(EvidenceGap).filter(EvidenceGap.id == gap_id))
    gap = res.scalar_one_or_none()
    if not gap:
        raise HTTPException(status_code=404, detail="Evidence gap not found")

    await verify_investigation_access(gap.investigation_id, current_user, db, require_write=True)

    resolver = current_user.full_name

    # Validate resolving evidence exists and belongs to same investigation if specified
    if req.resolving_evidence_id is not None:
        ev_res = await db.execute(select(Evidence).filter(Evidence.id == req.resolving_evidence_id))
        resolving_ev = ev_res.scalar_one_or_none()
        if not resolving_ev:
            raise HTTPException(status_code=404, detail="Resolving evidence record not found")
        if resolving_ev.investigation_id != gap.investigation_id:
            raise HTTPException(status_code=400, detail="Resolving evidence must belong to the same investigation")
        gap.resolving_evidence_id = req.resolving_evidence_id

    gap.is_resolved = True
    if req.resolution_notes:
        gap.investigator_response = (gap.investigator_response or "") + f"\n[Resolution]: {req.resolution_notes}"
    gap.updated_at = datetime.utcnow()

    await audit_service.log_action(
        db, gap.investigation_id, "GAP_RESOLVED", "EVIDENCE_GAP",
        f"Gap #{gap.id} resolved with Evidence #{req.resolving_evidence_id} by {resolver}",
        entity_id=str(gap.id),
        user_id=current_user.id,
        user_name=resolver
    )
    await db.commit()
    return gap

# ---------------------------------------------------------
# Root Cause Endpoints & Evidence Linking
# ---------------------------------------------------------

@router.get("/investigations/{investigation_id}/root-causes", response_model=List[RootCauseRead])
async def get_investigation_root_causes(
    investigation_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve all root causes for an investigation with evidence links and dispositions."""
    await verify_investigation_access(investigation_id, current_user, db, require_write=False)
    stmt = (
        select(RootCause)
        .options(
            selectinload(RootCause.evidence_links).selectinload(RootCauseEvidenceLink.evidence),
            selectinload(RootCause.dispositions)
        )
        .filter(RootCause.investigation_id == investigation_id)
        .order_by(RootCause.is_primary.desc(), RootCause.id.asc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()

@router.post("/investigations/{investigation_id}/root-causes", response_model=RootCauseRead)
async def create_root_cause(
    investigation_id: int,
    rc_in: RootCauseCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Add a manual or synthesized Root Cause proposal (always starts as PROPOSED)."""
    await verify_investigation_access(investigation_id, current_user, db, require_write=True)

    # Provenance validation
    source_type = (rc_in.source_type or "MANUAL").upper()
    valid_source_types = {"FIVE_WHYS", "FISHBONE", "DIRECT_SYNTHESIS", "MANUAL"}
    if source_type not in valid_source_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid source_type '{source_type}'. Allowed types: {sorted(valid_source_types)}"
        )

    source_id = rc_in.source_id
    if source_type == "FIVE_WHYS":
        if not source_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="source_id is required when source_type is FIVE_WHYS."
            )
        step_res = await db.execute(
            select(FiveWhysStep)
            .filter(FiveWhysStep.id == source_id)
            .with_for_update()
        )
        step_obj = step_res.scalar_one_or_none()
        if not step_obj:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Referenced Five Whys source step #{source_id} does not exist."
            )
        if step_obj.investigation_id != investigation_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cross-investigation provenance violation: Five Whys step #{source_id} does not belong to investigation #{investigation_id}."
            )
    elif source_type == "FISHBONE":
        if not source_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="source_id is required when source_type is FISHBONE."
            )
        cause_res = await db.execute(
            select(FishboneCause)
            .filter(FishboneCause.id == source_id)
            .with_for_update()
        )
        cause_obj = cause_res.scalar_one_or_none()
        if not cause_obj:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Referenced Fishbone source cause #{source_id} does not exist."
            )
        if cause_obj.investigation_id != investigation_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cross-investigation provenance violation: Fishbone cause #{source_id} does not belong to investigation #{investigation_id}."
            )
    elif source_type in ("DIRECT_SYNTHESIS", "MANUAL"):
        source_id = None

    rc = RootCause(
        investigation_id=investigation_id,
        cause_statement=rc_in.cause_statement,
        category=rc_in.category or "EQUIPMENT_FAILURE",
        is_primary=rc_in.is_primary,
        status="PROPOSED",  # Crucial safety rule: always starts as PROPOSED
        rationale=rc_in.rationale,
        evidence_summary=rc_in.evidence_summary,
        is_ai_suggested=False,  # Manual entry
        is_verified=False,
        investigator_notes=rc_in.investigator_notes,
        source_type=source_type,
        source_id=source_id,
    )
    db.add(rc)
    await db.flush()
    await db.refresh(rc)

    await audit_service.log_action(
        db, investigation_id, "CREATED", "ROOT_CAUSE",
        f"Added Root Cause proposal: '{rc.cause_statement}'", entity_id=str(rc.id),
        user_id=current_user.id,
        user_name=current_user.full_name
    )
    await db.commit()

    rc_reload = await db.execute(
        select(RootCause)
        .options(
            selectinload(RootCause.evidence_links).selectinload(RootCauseEvidenceLink.evidence),
            selectinload(RootCause.dispositions)
        )
        .filter(RootCause.id == rc.id)
    )
    return rc_reload.scalar_one()

@router.put("/root-causes/{root_cause_id}", response_model=RootCauseRead)
async def update_root_cause(
    root_cause_id: int,
    rc_update: RootCauseUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update root cause fields (status changes to CONFIRMED must use /confirm)."""
    rc_res = await db.execute(
        select(RootCause)
        .options(
            selectinload(RootCause.evidence_links).selectinload(RootCauseEvidenceLink.evidence),
            selectinload(RootCause.dispositions)
        )
        .filter(RootCause.id == root_cause_id)
    )
    rc = rc_res.scalar_one_or_none()
    if not rc:
        raise HTTPException(status_code=404, detail="Root cause not found")

    await verify_investigation_access(rc.investigation_id, current_user, db, require_write=True)

    update_dict = rc_update.dict(exclude_unset=True)
    forbidden_rc_fields = {
        "is_verified", "source_type", "source_id", "confirmed_by",
        "confirmed_by_user_id", "confirmed_at", "rejected_by",
        "rejected_by_user_id", "rejected_at"
    }
    for field in forbidden_rc_fields:
        update_dict.pop(field, None)

    for k, v in update_dict.items():
        if k == "status" and v in ("CONFIRMED", "REJECTED"):
            # Safety rule: status cannot transition directly to CONFIRMED or REJECTED via PUT
            continue
        setattr(rc, k, v)
    rc.updated_at = datetime.utcnow()

    await audit_service.log_action(
        db, rc.investigation_id, "UPDATED", "ROOT_CAUSE",
        f"Updated Root Cause #{rc.id}", entity_id=str(rc.id),
        user_id=current_user.id,
        user_name=current_user.full_name
    )
    await db.commit()

    rc_reload = await db.execute(
        select(RootCause)
        .options(
            selectinload(RootCause.evidence_links).selectinload(RootCauseEvidenceLink.evidence),
            selectinload(RootCause.dispositions)
        )
        .filter(RootCause.id == root_cause_id)
    )
    return rc_reload.scalar_one()

@router.delete("/root-causes/{root_cause_id}")
async def delete_root_cause(
    root_cause_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a root cause proposal."""
    rc_res = await db.execute(select(RootCause).filter(RootCause.id == root_cause_id))
    rc = rc_res.scalar_one_or_none()
    if not rc:
        raise HTTPException(status_code=404, detail="Root cause not found")

    await verify_investigation_access(rc.investigation_id, current_user, db, require_write=True)

    inv_id = rc.investigation_id
    await db.delete(rc)
    await db.commit()

    await audit_service.log_action(
        db, inv_id, "DELETED", "ROOT_CAUSE",
        f"Deleted Root Cause proposal #{root_cause_id}", entity_id=str(root_cause_id),
        user_id=current_user.id,
        user_name=current_user.full_name
    )
    return {"ok": True}

@router.post("/root-causes/{root_cause_id}/evidence-links", response_model=RootCauseEvidenceLinkRead)
async def link_root_cause_evidence(
    root_cause_id: int,
    link_in: RootCauseEvidenceLinkCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Explicitly link evidence to a root cause as supporting or contradictory."""
    rc_res = await db.execute(select(RootCause).filter(RootCause.id == root_cause_id))
    rc = rc_res.scalar_one_or_none()
    if not rc:
        raise HTTPException(status_code=404, detail="Root cause not found")

    await verify_investigation_access(rc.investigation_id, current_user, db, require_write=True)

    ev_res = await db.execute(select(Evidence).filter(Evidence.id == link_in.evidence_id))
    ev = ev_res.scalar_one_or_none()
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence item not found")

    if ev.is_archived:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot link archived evidence record as active supporting or contradictory evidence."
        )

    # Strict isolation check across investigations
    if rc.investigation_id != ev.investigation_id:
        raise HTTPException(
            status_code=400,
            detail="Forbidden: Cannot link evidence and root cause across different investigations."
        )

    # Check for existing link with same relationship
    existing = await db.execute(
        select(RootCauseEvidenceLink).filter(
            RootCauseEvidenceLink.root_cause_id == root_cause_id,
            RootCauseEvidenceLink.evidence_id == link_in.evidence_id,
            RootCauseEvidenceLink.relationship_type == link_in.relationship_type
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="This evidence relationship is already linked to this root cause.")

    link = RootCauseEvidenceLink(
        root_cause_id=root_cause_id,
        evidence_id=link_in.evidence_id,
        relationship_type=link_in.relationship_type,
        relevance_explanation=link_in.relevance_explanation,
        confidence_rating=link_in.confidence_rating or "HIGH"
    )
    db.add(link)
    await db.flush()
    await db.refresh(link)

    await audit_service.log_action(
        db, rc.investigation_id, "LINKED", "ROOT_CAUSE",
        f"Linked Evidence #{ev.id} ('{ev.title}') to Root Cause #{rc.id} as {link.relationship_type}",
        entity_id=str(rc.id),
        user_id=current_user.id,
        user_name=current_user.full_name
    )
    await db.commit()

    # Reload with evidence nested
    res_link = await db.execute(
        select(RootCauseEvidenceLink)
        .options(selectinload(RootCauseEvidenceLink.evidence))
        .filter(RootCauseEvidenceLink.id == link.id)
    )
    return res_link.scalar_one()

@router.delete("/root-causes/{root_cause_id}/evidence-links/{link_id}")
async def unlink_root_cause_evidence(
    root_cause_id: int,
    link_id: int,
    disposition_rationale: Optional[str] = Query(None, description="Mandatory rationale if dismissing a contradictory link"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Remove relationship link between root cause and evidence.
    MANDATORY DISPOSITION WORKFLOW:
    Contradictory links CANNOT be deleted without a scientific disposition rationale.
    Creates an immutable ContradictionDisposition record before removing active link.
    """
    res = await db.execute(
        select(RootCauseEvidenceLink).filter(
            RootCauseEvidenceLink.id == link_id,
            RootCauseEvidenceLink.root_cause_id == root_cause_id
        )
    )
    link = res.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="Evidence link not found")

    rc_res = await db.execute(select(RootCause).filter(RootCause.id == root_cause_id))
    rc = rc_res.scalar_one_or_none()
    if not rc:
        raise HTTPException(status_code=404, detail="Root cause not found")

    await verify_investigation_access(rc.investigation_id, current_user, db, require_write=True)

    dismissed_by = current_user.full_name
    user_id = current_user.id

    # Enforce disposition rationale for contradictory links
    if link.relationship_type == "CONTRADICTORY":
        if not disposition_rationale or len(disposition_rationale.strip()) < 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Mandatory disposition required: A contradictory evidence link cannot be removed without "
                    "a scientific disposition rationale explaining why the contradiction is resolved or dismissed "
                    "(minimum 10 characters)."
                )
            )

        # Create historical disposition record
        disposition = ContradictionDisposition(
            root_cause_id=root_cause_id,
            evidence_id=link.evidence_id,
            relationship_type="CONTRADICTORY",
            disposition_rationale=disposition_rationale.strip(),
            dismissed_by=dismissed_by,
            dismissed_by_user_id=user_id,
            dismissed_at=datetime.utcnow(),
            original_link_created_at=link.created_at,
            original_relevance_explanation=link.relevance_explanation
        )
        db.add(disposition)

        await audit_service.log_action(
            db, rc.investigation_id, "CONTRADICTION_DISPOSED", "ROOT_CAUSE",
            f"Contradictory Evidence #{link.evidence_id} dismissed for Root Cause #{root_cause_id} by {dismissed_by}. Rationale: {disposition_rationale.strip()}",
            entity_id=str(root_cause_id),
            user_id=current_user.id,
            user_name=dismissed_by
        )

    await db.delete(link)
    if link.relationship_type != "CONTRADICTORY":
        await audit_service.log_action(
            db, rc.investigation_id, "UNLINKED", "ROOT_CAUSE",
            f"Removed Evidence Link #{link_id} from Root Cause #{root_cause_id} by {dismissed_by}",
            entity_id=str(root_cause_id),
            user_id=current_user.id,
            user_name=dismissed_by
        )
    await db.commit()
    return {"deleted": True, "id": link_id}

@router.post("/root-causes/{root_cause_id}/evidence-links/{link_id}/dismiss", response_model=ContradictionDispositionRead)
async def dismiss_contradictory_link(
    root_cause_id: int,
    link_id: int,
    req: ContradictionDispositionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Dedicated endpoint to formally dismiss a contradictory link with required rationale."""
    res = await db.execute(
        select(RootCauseEvidenceLink).filter(
            RootCauseEvidenceLink.id == link_id,
            RootCauseEvidenceLink.root_cause_id == root_cause_id
        )
    )
    link = res.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="Evidence link not found")

    if link.relationship_type != "CONTRADICTORY":
        raise HTTPException(status_code=400, detail="Only contradictory links require a formal dismissal workflow.")

    rc_res = await db.execute(select(RootCause).filter(RootCause.id == root_cause_id))
    rc = rc_res.scalar_one_or_none()
    if not rc:
        raise HTTPException(status_code=404, detail="Root cause not found")

    await verify_investigation_access(rc.investigation_id, current_user, db, require_write=True)

    dismissed_by = current_user.full_name
    user_id = current_user.id

    disposition = ContradictionDisposition(
        root_cause_id=root_cause_id,
        evidence_id=link.evidence_id,
        relationship_type="CONTRADICTORY",
        disposition_rationale=req.disposition_rationale.strip(),
        dismissed_by=dismissed_by,
        dismissed_by_user_id=user_id,
        dismissed_at=datetime.utcnow(),
        original_link_created_at=link.created_at,
        original_relevance_explanation=link.relevance_explanation
    )
    db.add(disposition)
    await db.delete(link)

    await audit_service.log_action(
        db, rc.investigation_id, "CONTRADICTION_DISPOSED", "ROOT_CAUSE",
        f"Contradictory Evidence #{link.evidence_id} dismissed for Root Cause #{root_cause_id} by {dismissed_by}. Rationale: {req.disposition_rationale.strip()}",
        entity_id=str(root_cause_id),
        user_id=current_user.id,
        user_name=dismissed_by
    )
    await db.commit()
    await db.refresh(disposition)
    return disposition

@router.post("/root-causes/{root_cause_id}/confirm", response_model=RootCauseRead)
async def confirm_root_cause(
    root_cause_id: int,
    req: RootCauseConfirmRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Formal human verification confirming a proposed root cause.
    ENFORCES STRICT REGULATORY SAFETY RULES:
    1. Mandatory authentication - spoofed signatures rejected.
    2. Must have at least one verified, non-archived supporting evidence record.
    3. Must not have active contradictory evidence links.
    4. Requires explicit investigator justification.
    5. Binds authenticated investigator ID.
    """
    rc_res = await db.execute(
        select(RootCause)
        .options(
            selectinload(RootCause.evidence_links).selectinload(RootCauseEvidenceLink.evidence),
            selectinload(RootCause.dispositions)
        )
        .filter(RootCause.id == root_cause_id)
    )
    rc = rc_res.scalar_one_or_none()
    if not rc:
        raise HTTPException(status_code=404, detail="Root cause not found")

    inv = await verify_investigation_access(rc.investigation_id, current_user, db)

    # Authorization Check 1: Must be QA_APPROVER or ADMIN
    if current_user.role not in ("QA_APPROVER", "ADMIN"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Formal root cause confirmation requires QA_APPROVER or ADMIN role."
        )

    # Authorization Check 2: Lead investigator cannot confirm their own proposal (Separation of Duties)
    if inv.lead_investigator_id is not None and inv.lead_investigator_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Separation of duties violation: The assigned lead investigator cannot formally confirm their own root cause proposal. Confirmation requires independent QA review."
        )

    # Safety Guard 1: Must have verified, active supporting evidence
    verified_supporting = [
        link for link in rc.evidence_links 
        if link.relationship_type == "SUPPORTING" and link.evidence and link.evidence.is_verified and not link.evidence.is_archived
    ]
    if not verified_supporting:
        raise HTTPException(
            status_code=400,
            detail=(
                "Regulatory safety violation: Cannot confirm root cause without at least one verified, active supporting "
                "evidence record. Please verify linked evidence or unarchive supporting records first."
            )
        )

    # Safety Guard 2: Contradictory evidence must be formally resolved/disposed
    contradictory_links = [
        link for link in rc.evidence_links 
        if link.relationship_type == "CONTRADICTORY"
    ]
    if contradictory_links:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Regulatory safety violation: Found {len(contradictory_links)} active contradictory evidence link(s). "
                "All empirical contradictions must be formally disposed with rationale prior to confirmation."
            )
        )

    confirmed_by_name = current_user.full_name
    auth_tag = f" (User ID #{current_user.id})"

    # Confirm the root cause
    rc.status = "CONFIRMED"
    rc.is_verified = True
    rc.is_ai_suggested = False  # Elevated to human confirmed
    rc.confirmed_by = confirmed_by_name
    rc.confirmed_by_user_id = current_user.id
    rc.confirmed_at = datetime.utcnow()
    rc.investigator_notes = (rc.investigator_notes or "") + f"\n[Confirmed by {confirmed_by_name}{auth_tag}]: {req.justification}"
    rc.updated_at = datetime.utcnow()
    await db.flush()

    await audit_service.log_action(
        db, rc.investigation_id, "CONFIRMED", "ROOT_CAUSE",
        f"Root Cause #{rc.id} CONFIRMED by {confirmed_by_name}{auth_tag}. Justification: {req.justification[:100]}...",
        entity_id=str(rc.id),
        user_id=current_user.id,
        user_name=confirmed_by_name
    )
    await db.commit()

    # Reload full root cause
    rc_reload = await db.execute(
        select(RootCause)
        .options(
            selectinload(RootCause.evidence_links).selectinload(RootCauseEvidenceLink.evidence),
            selectinload(RootCause.dispositions)
        )
        .filter(RootCause.id == root_cause_id)
    )
    return rc_reload.scalar_one()

@router.post("/root-causes/{root_cause_id}/reject", response_model=RootCauseRead)
async def reject_root_cause(
    root_cause_id: int,
    req: RootCauseRejectRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Human action to reject an ungrounded or refuted causal hypothesis."""
    rc_res = await db.execute(
        select(RootCause)
        .options(
            selectinload(RootCause.evidence_links).selectinload(RootCauseEvidenceLink.evidence),
            selectinload(RootCause.dispositions)
        )
        .filter(RootCause.id == root_cause_id)
    )
    rc = rc_res.scalar_one_or_none()
    if not rc:
        raise HTTPException(status_code=404, detail="Root cause not found")

    await verify_investigation_access(rc.investigation_id, current_user, db)

    # Authorization Check: Formal rejection is strictly restricted to QA_APPROVER or ADMIN
    if current_user.role not in ("QA_APPROVER", "ADMIN"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Formal root cause rejection requires QA_APPROVER or ADMIN role."
        )

    rejected_by_name = current_user.full_name
    auth_tag = f" (User ID #{current_user.id})"

    rc.status = "REJECTED"
    rc.is_verified = True
    rc.rejected_by = rejected_by_name
    rc.rejected_by_user_id = current_user.id
    rc.rejected_at = datetime.utcnow()
    rc.rejection_reason = req.rationale
    rc.investigator_notes = (rc.investigator_notes or "") + f"\n[Rejected by {rejected_by_name}{auth_tag}]: {req.rationale}"
    rc.updated_at = datetime.utcnow()
    await db.flush()

    await audit_service.log_action(
        db, rc.investigation_id, "REJECTED", "ROOT_CAUSE",
        f"Root Cause #{rc.id} REJECTED by {rejected_by_name}. Rationale: {req.rationale[:100]}...",
        entity_id=str(rc.id),
        user_id=current_user.id,
        user_name=rejected_by_name
    )
    await db.commit()

    rc_reload = await db.execute(
        select(RootCause)
        .options(
            selectinload(RootCause.evidence_links).selectinload(RootCauseEvidenceLink.evidence),
            selectinload(RootCause.dispositions)
        )
        .filter(RootCause.id == root_cause_id)
    )
    return rc_reload.scalar_one()

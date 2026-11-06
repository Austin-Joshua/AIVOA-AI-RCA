from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import datetime
import inspect

from app.core.database import get_db
from app.core.security import get_current_user, verify_investigation_access
from app.models.audit import User
from app.models.fishbone import FishboneCause, FishboneEvidenceLink
from app.models.evidence import Evidence
from app.models.root_cause import RootCause, RootCauseEvidenceLink
from app.schemas.fishbone import (
    FishboneCauseCreate,
    FishboneCauseUpdate,
    FishboneCauseRead,
    FishboneEvidenceLinkCreate,
    FishboneEvidenceLinkRead,
    FishboneVerifyRequest,
    FishbonePromoteRequest,
)
from app.schemas.root_cause import RootCauseRead
from app.services.audit_service import audit_service

router = APIRouter()

FISHBONE_TO_RC_CATEGORY = {
    "MAN": "HUMAN_ERROR",
    "MACHINE": "EQUIPMENT_FAILURE",
    "METHOD": "PROCEDURE",
    "MATERIAL": "RAW_MATERIAL",
    "MEASUREMENT": "EQUIPMENT_FAILURE",
    "MILIEU": "SYSTEMIC",
}

@router.get("/investigations/{investigation_id}/fishbone", response_model=List[FishboneCauseRead])
async def get_fishbone_causes(
    investigation_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve all Fishbone causes for an investigation with linked evidence."""
    await verify_investigation_access(investigation_id, current_user, db, require_write=False)
    stmt = (
        select(FishboneCause)
        .options(
            selectinload(FishboneCause.evidence_links).selectinload(FishboneEvidenceLink.evidence)
        )
        .filter(FishboneCause.investigation_id == investigation_id)
        .order_by(FishboneCause.category.asc(), FishboneCause.id.asc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()

@router.post("/investigations/{investigation_id}/fishbone", response_model=FishboneCauseRead)
async def add_fishbone_cause(
    investigation_id: int,
    cause_in: FishboneCauseCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Add a categorized Ishikawa Fishbone cause hypothesis."""
    await verify_investigation_access(investigation_id, current_user, db, require_write=True)
    cause = FishboneCause(
        investigation_id=investigation_id,
        category=cause_in.category.upper(),
        cause_description=cause_in.cause_description,
        status=cause_in.status.upper() if cause_in.status else "HYPOTHESIS",
        rationale=cause_in.rationale,
        evidence_reference=cause_in.evidence_reference,
        is_ai_suggested=cause_in.is_ai_suggested,
        is_verified=cause_in.is_verified
    )
    db.add(cause)
    await db.flush()
    await db.refresh(cause)

    await audit_service.log_action(
        db, investigation_id, "CREATED", "FISHBONE",
        f"Added cause to {cause.category}: '{cause.cause_description}'", entity_id=str(cause.id),
        user_id=current_user.id,
        user_name=current_user.full_name
    )
    await db.commit()

    stmt = (
        select(FishboneCause)
        .options(
            selectinload(FishboneCause.evidence_links).selectinload(FishboneEvidenceLink.evidence)
        )
        .filter(FishboneCause.id == cause.id)
    )
    res = await db.execute(stmt)
    if hasattr(res, "scalar_one"):
        fetched = res.scalar_one()
        if inspect.isawaitable(fetched):
            fetched = await fetched
        if fetched and isinstance(fetched, FishboneCause):
            return fetched
    return cause

@router.put("/fishbone/{cause_id}", response_model=FishboneCauseRead)
async def update_fishbone_cause(
    cause_id: int,
    cause_update: FishboneCauseUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a Fishbone cause hypothesis."""
    stmt = (
        select(FishboneCause)
        .options(
            selectinload(FishboneCause.evidence_links).selectinload(FishboneEvidenceLink.evidence)
        )
        .filter(FishboneCause.id == cause_id)
    )
    result = await db.execute(stmt)
    cause = result.scalar_one_or_none()
    if not cause:
        raise HTTPException(status_code=404, detail="Fishbone cause not found")

    await verify_investigation_access(cause.investigation_id, current_user, db, require_write=True)

    for k, v in cause_update.dict(exclude_unset=True).items():
        if k in ("category", "status") and isinstance(v, str):
            v = v.upper()
        setattr(cause, k, v)
    cause.updated_at = datetime.utcnow()

    await audit_service.log_action(
        db, cause.investigation_id, "UPDATED", "FISHBONE",
        f"Updated cause in {cause.category} (status: {cause.status})", entity_id=str(cause.id),
        user_id=current_user.id,
        user_name=current_user.full_name
    )

    await db.flush()
    await db.commit()

    res = await db.execute(stmt)
    if hasattr(res, "scalar_one"):
        fetched = res.scalar_one()
        if inspect.isawaitable(fetched):
            fetched = await fetched
        if fetched and isinstance(fetched, FishboneCause):
            return fetched
    return cause

@router.delete("/fishbone/{cause_id}")
async def delete_fishbone_cause(
    cause_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a Fishbone cause."""
    result = await db.execute(
        select(FishboneCause)
        .filter(FishboneCause.id == cause_id)
        .with_for_update()
    )
    cause = result.scalar_one_or_none()
    if not cause:
        raise HTTPException(status_code=404, detail="Fishbone cause not found")

    inv_id = cause.investigation_id
    await verify_investigation_access(inv_id, current_user, db, require_write=True)

    # Provenance deletion guard: prevent deletion if a Root Cause proposal depends on this cause
    rc_dep = await db.execute(
        select(RootCause).filter(
            RootCause.investigation_id == inv_id,
            RootCause.source_type == "FISHBONE",
            RootCause.source_id == cause_id
        )
    )
    dependent_rcs = rc_dep.scalars().all()
    if dependent_rcs or cause.promoted_to_root_cause_id is not None:
        rc_ids = [str(r.id) for r in dependent_rcs]
        if cause.promoted_to_root_cause_id and str(cause.promoted_to_root_cause_id) not in rc_ids:
            rc_ids.append(str(cause.promoted_to_root_cause_id))
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Cannot delete Fishbone cause #{cause_id} because Root Cause proposal(s) "
                f"#{', #'.join(rc_ids)} depend on it for provenance. Delete or reassign dependent root causes first."
            )
        )

    cat = cause.category
    await db.delete(cause)
    await db.commit()

    await audit_service.log_action(
        db, inv_id, "DELETED", "FISHBONE",
        f"Deleted cause from {cat}", entity_id=str(cause_id),
        user_id=current_user.id,
        user_name=current_user.full_name
    )
    return {"ok": True}

# ---------------------------------------------------------
# Evidence Linking for Fishbone
# ---------------------------------------------------------

@router.post("/fishbone/{cause_id}/evidence", response_model=FishboneEvidenceLinkRead)
async def link_fishbone_evidence(
    cause_id: int,
    link_in: FishboneEvidenceLinkCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Link an evidence item to a Fishbone cause as supporting or contradictory."""
    stmt = select(FishboneCause).filter(FishboneCause.id == cause_id)
    res = await db.execute(stmt)
    cause = res.scalar_one_or_none()
    if not cause:
        raise HTTPException(status_code=404, detail="Fishbone cause not found")

    await verify_investigation_access(cause.investigation_id, current_user, db, require_write=True)

    ev_res = await db.execute(select(Evidence).filter(Evidence.id == link_in.evidence_id))
    ev = ev_res.scalar_one_or_none()
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence item not found")

    if ev.is_archived:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot link archived evidence record to a Fishbone cause."
        )

    # Cross-investigation isolation check
    if cause.investigation_id != ev.investigation_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Forbidden: Cannot link evidence and Fishbone cause across different investigations."
        )

    # Check duplicate
    dup = await db.execute(
        select(FishboneEvidenceLink).filter(
            FishboneEvidenceLink.fishbone_cause_id == cause_id,
            FishboneEvidenceLink.evidence_id == link_in.evidence_id,
            FishboneEvidenceLink.relationship_type == link_in.relationship_type
        )
    )
    if dup.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="This evidence relationship is already linked to this Fishbone cause.")

    link = FishboneEvidenceLink(
        fishbone_cause_id=cause_id,
        evidence_id=link_in.evidence_id,
        relationship_type=link_in.relationship_type,
        relevance_explanation=link_in.relevance_explanation,
        confidence_rating=link_in.confidence_rating or "HIGH"
    )
    db.add(link)
    await db.flush()
    await db.refresh(link)

    await audit_service.log_action(
        db, cause.investigation_id, "LINKED", "FISHBONE",
        f"Linked Evidence #{ev.id} ('{ev.title}') to Fishbone cause in {cause.category} as {link.relationship_type}",
        entity_id=str(cause.id),
        user_id=current_user.id,
        user_name=current_user.full_name
    )
    await db.commit()

    res_link = await db.execute(
        select(FishboneEvidenceLink)
        .options(selectinload(FishboneEvidenceLink.evidence))
        .filter(FishboneEvidenceLink.id == link.id)
    )
    return res_link.scalar_one()

@router.delete("/fishbone/{cause_id}/evidence/{evidence_id}")
async def unlink_fishbone_evidence(
    cause_id: int,
    evidence_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Unlink an evidence item from a Fishbone cause."""
    stmt = select(FishboneCause).filter(FishboneCause.id == cause_id)
    res = await db.execute(stmt)
    cause = res.scalar_one_or_none()
    if not cause:
        raise HTTPException(status_code=404, detail="Fishbone cause not found")

    await verify_investigation_access(cause.investigation_id, current_user, db, require_write=True)

    link_res = await db.execute(
        select(FishboneEvidenceLink).filter(
            FishboneEvidenceLink.fishbone_cause_id == cause_id,
            FishboneEvidenceLink.evidence_id == evidence_id
        )
    )
    link = link_res.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="Evidence link not found")

    await db.delete(link)
    await db.commit()

    await audit_service.log_action(
        db, cause.investigation_id, "UNLINKED", "FISHBONE",
        f"Unlinked Evidence #{evidence_id} from Fishbone cause in {cause.category}",
        entity_id=str(cause.id),
        user_id=current_user.id,
        user_name=current_user.full_name
    )
    return {"ok": True}

@router.post("/fishbone/{cause_id}/verify", response_model=FishboneCauseRead)
async def verify_fishbone_cause(
    cause_id: int,
    req: FishboneVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Formally evaluate and update status of a Fishbone cause (VERIFIED, RULED_OUT, HYPOTHESIS).
    Safety Guard: Marking VERIFIED requires at least one verified piece of supporting evidence.
    """
    stmt = (
        select(FishboneCause)
        .options(
            selectinload(FishboneCause.evidence_links).selectinload(FishboneEvidenceLink.evidence)
        )
        .filter(FishboneCause.id == cause_id)
    )
    res = await db.execute(stmt)
    cause = res.scalar_one_or_none()
    if not cause:
        raise HTTPException(status_code=404, detail="Fishbone cause not found")

    await verify_investigation_access(cause.investigation_id, current_user, db, require_write=True)

    target_status = req.status.upper()
    if target_status == "VERIFIED":
        verified_supporting = [
            link for link in cause.evidence_links
            if link.relationship_type == "SUPPORTING" and link.evidence and link.evidence.is_verified and not link.evidence.is_archived
        ]
        if not verified_supporting:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Verification safety violation: Cannot mark Fishbone cause as VERIFIED without at least "
                    "one verified, active piece of supporting evidence linked to this cause."
                )
            )
        cause.status = "VERIFIED"
        cause.is_verified = True
        cause.verified_by_user_id = current_user.id
        cause.verified_at = datetime.utcnow()
        cause.verification_notes = req.verification_notes
    elif target_status == "RULED_OUT":
        cause.status = "RULED_OUT"
        cause.is_verified = True
        cause.verified_by_user_id = current_user.id
        cause.verified_at = datetime.utcnow()
        cause.verification_notes = req.verification_notes
    else:
        cause.status = "HYPOTHESIS"
        cause.is_verified = False
        cause.verified_by_user_id = None
        cause.verified_at = None
        cause.verification_notes = req.verification_notes

    cause.updated_at = datetime.utcnow()
    await db.flush()
    await db.commit()

    await audit_service.log_action(
        db, cause.investigation_id, cause.status, "FISHBONE",
        f"Cause in {cause.category} set to {cause.status} by {current_user.full_name}",
        entity_id=str(cause.id),
        user_id=current_user.id,
        user_name=current_user.full_name
    )

    re_res = await db.execute(stmt)
    if hasattr(re_res, "scalar_one"):
        fetched = re_res.scalar_one()
        if inspect.isawaitable(fetched):
            fetched = await fetched
        if fetched:
            return fetched
    return cause

@router.post("/fishbone/{cause_id}/promote", response_model=RootCauseRead)
async def promote_fishbone_to_root_cause(
    cause_id: int,
    req: FishbonePromoteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Promote a Fishbone cause hypothesis into a formal Root Cause proposal.
    - Preserves causal provenance (source_type='FISHBONE', source_id=cause_id).
    - Status is always PROPOSED (never auto-confirmed).
    - Copies evidence links from Fishbone to the new Root Cause.
    - Binds promoted_to_root_cause_id on the Fishbone cause.
    """
    stmt = (
        select(FishboneCause)
        .options(
            selectinload(FishboneCause.evidence_links).selectinload(FishboneEvidenceLink.evidence)
        )
        .filter(FishboneCause.id == cause_id)
        .with_for_update()
    )
    res = await db.execute(stmt)
    cause = res.scalar_one_or_none()
    if not cause:
        raise HTTPException(status_code=404, detail="Fishbone cause not found")

    await verify_investigation_access(cause.investigation_id, current_user, db, require_write=True)

    # Concurrency and duplicate promotion guard
    if cause.promoted_to_root_cause_id is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Fishbone cause #{cause_id} has already been promoted to Root Cause #{cause.promoted_to_root_cause_id}. Repeated promotion is not permitted."
        )

    mapped_cat = FISHBONE_TO_RC_CATEGORY.get(cause.category.upper(), "SYSTEMIC")
    target_category = req.category or mapped_cat

    rc = RootCause(
        investigation_id=cause.investigation_id,
        cause_statement=cause.cause_description,
        category=target_category,
        is_primary=req.is_primary,
        status="PROPOSED",  # Crucial safety rule: always PROPOSED
        rationale=cause.rationale,
        evidence_summary=f"Promoted from Fishbone category: {cause.category}",
        is_ai_suggested=False,  # Human promoted action
        is_verified=False,
        investigator_notes=req.investigator_notes or f"Promoted from Fishbone #{cause.id} by {current_user.full_name}",
        source_type="FISHBONE",
        source_id=cause.id,
    )
    db.add(rc)
    await db.flush()

    # Copy evidence links from Fishbone cause to Root Cause explicitly
    fb_links_res = await db.execute(
        select(FishboneEvidenceLink).filter(FishboneEvidenceLink.fishbone_cause_id == cause_id)
    )
    fb_links = fb_links_res.scalars().all()
    for link in fb_links:
        rc_link = RootCauseEvidenceLink(
            root_cause_id=rc.id,
            evidence_id=link.evidence_id,
            relationship_type=link.relationship_type,
            relevance_explanation=link.relevance_explanation or f"Inherited from Fishbone cause in {cause.category}",
            confidence_rating=link.confidence_rating or "HIGH"
        )
        db.add(rc_link)

    cause.promoted_to_root_cause_id = rc.id
    cause.updated_at = datetime.utcnow()
    await db.flush()

    await audit_service.log_action(
        db, cause.investigation_id, "PROMOTED", "FISHBONE",
        f"Promoted Fishbone #{cause.id} ('{cause.cause_description}') to Root Cause #{rc.id} proposal",
        entity_id=str(cause.id),
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
        .execution_options(populate_existing=True)
    )
    return rc_reload.scalar_one()

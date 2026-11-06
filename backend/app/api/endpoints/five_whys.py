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
from app.models.five_whys import FiveWhysStep, FiveWhysEvidenceLink
from app.models.evidence import Evidence
from app.models.root_cause import RootCause
from app.schemas.five_whys import (
    FiveWhysStepCreate,
    FiveWhysStepUpdate,
    FiveWhysStepRead,
    FiveWhysEvidenceLinkCreate,
    FiveWhysEvidenceLinkRead,
    FiveWhysVerifyRequest,
)
from app.services.audit_service import audit_service

router = APIRouter()

@router.get("/investigations/{investigation_id}/five-whys", response_model=List[FiveWhysStepRead])
async def get_five_whys_steps(
    investigation_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve all Five Whys steps for an investigation with linked evidence."""
    await verify_investigation_access(investigation_id, current_user, db, require_write=False)
    stmt = (
        select(FiveWhysStep)
        .options(
            selectinload(FiveWhysStep.evidence_links).selectinload(FiveWhysEvidenceLink.evidence)
        )
        .filter(FiveWhysStep.investigation_id == investigation_id)
        .order_by(FiveWhysStep.step_number.asc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()

@router.post("/investigations/{investigation_id}/five-whys", response_model=FiveWhysStepRead)
async def add_five_why_step(
    investigation_id: int,
    step_in: FiveWhysStepCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Add a Five Whys step with dynamic depth (1, 2, ... N)."""
    await verify_investigation_access(investigation_id, current_user, db, require_write=True)
    step = FiveWhysStep(
        investigation_id=investigation_id,
        step_number=step_in.step_number,
        question=step_in.question,
        answer=step_in.answer,
        evidence_reference=step_in.evidence_reference,
        is_ai_suggested=step_in.is_ai_suggested,
        is_verified=step_in.is_verified
    )
    db.add(step)
    await db.flush()
    await db.refresh(step)

    await audit_service.log_action(
        db, investigation_id, "CREATED", "FIVE_WHYS",
        f"Added Why #{step.step_number}: '{step.question}'", entity_id=str(step.id),
        user_id=current_user.id,
        user_name=current_user.full_name
    )
    await db.commit()

    stmt = (
        select(FiveWhysStep)
        .options(
            selectinload(FiveWhysStep.evidence_links).selectinload(FiveWhysEvidenceLink.evidence)
        )
        .filter(FiveWhysStep.id == step.id)
    )
    res = await db.execute(stmt)
    if hasattr(res, "scalar_one"):
        fetched = res.scalar_one()
        if inspect.isawaitable(fetched):
            fetched = await fetched
        if fetched and isinstance(fetched, FiveWhysStep):
            return fetched
    return step

@router.put("/five-whys/{step_id}", response_model=FiveWhysStepRead)
async def update_five_why_step(
    step_id: int,
    step_update: FiveWhysStepUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a Five Whys step."""
    stmt = (
        select(FiveWhysStep)
        .options(
            selectinload(FiveWhysStep.evidence_links).selectinload(FiveWhysEvidenceLink.evidence)
        )
        .filter(FiveWhysStep.id == step_id)
    )
    result = await db.execute(stmt)
    step = result.scalar_one_or_none()
    if not step:
        raise HTTPException(status_code=404, detail="Five Whys step not found")

    await verify_investigation_access(step.investigation_id, current_user, db, require_write=True)

    for k, v in step_update.dict(exclude_unset=True).items():
        setattr(step, k, v)
    step.updated_at = datetime.utcnow()

    await audit_service.log_action(
        db, step.investigation_id, "UPDATED", "FIVE_WHYS",
        f"Updated Why #{step.step_number}", entity_id=str(step.id),
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
        if fetched and isinstance(fetched, FiveWhysStep):
            return fetched
    return step

@router.delete("/five-whys/{step_id}")
async def delete_five_why_step(
    step_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a Five Whys step."""
    result = await db.execute(
        select(FiveWhysStep)
        .filter(FiveWhysStep.id == step_id)
        .with_for_update()
    )
    step = result.scalar_one_or_none()
    if not step:
        raise HTTPException(status_code=404, detail="Step not found")

    inv_id = step.investigation_id
    await verify_investigation_access(inv_id, current_user, db, require_write=True)

    # Provenance deletion guard: prevent deletion if a Root Cause proposal depends on this step
    rc_dep = await db.execute(
        select(RootCause).filter(
            RootCause.investigation_id == inv_id,
            RootCause.source_type == "FIVE_WHYS",
            RootCause.source_id == step_id
        )
    )
    dependent_rcs = rc_dep.scalars().all()
    if dependent_rcs:
        rc_ids = [str(r.id) for r in dependent_rcs]
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Cannot delete Five Whys step #{step_id} because Root Cause proposal(s) "
                f"#{', #'.join(rc_ids)} depend on it for provenance. Delete or reassign dependent root causes first."
            )
        )

    step_num = step.step_number
    await db.delete(step)
    await db.commit()

    await audit_service.log_action(
        db, inv_id, "DELETED", "FIVE_WHYS",
        f"Deleted Why #{step_num}", entity_id=str(step_id),
        user_id=current_user.id,
        user_name=current_user.full_name
    )
    return {"ok": True}

# ---------------------------------------------------------
# Evidence Linking for Five Whys
# ---------------------------------------------------------

@router.post("/five-whys/{step_id}/evidence", response_model=FiveWhysEvidenceLinkRead)
async def link_five_whys_evidence(
    step_id: int,
    link_in: FiveWhysEvidenceLinkCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Link an evidence item to a 5-Whys step as supporting or contradictory."""
    stmt = select(FiveWhysStep).filter(FiveWhysStep.id == step_id)
    res = await db.execute(stmt)
    step = res.scalar_one_or_none()
    if not step:
        raise HTTPException(status_code=404, detail="Five Whys step not found")

    await verify_investigation_access(step.investigation_id, current_user, db, require_write=True)

    ev_res = await db.execute(select(Evidence).filter(Evidence.id == link_in.evidence_id))
    ev = ev_res.scalar_one_or_none()
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence item not found")

    if ev.is_archived:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot link archived evidence record to a 5-Whys step."
        )

    # Cross-investigation isolation check
    if step.investigation_id != ev.investigation_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Forbidden: Cannot link evidence and 5-Whys step across different investigations."
        )

    # Check for existing duplicate link
    dup = await db.execute(
        select(FiveWhysEvidenceLink).filter(
            FiveWhysEvidenceLink.five_whys_step_id == step_id,
            FiveWhysEvidenceLink.evidence_id == link_in.evidence_id,
            FiveWhysEvidenceLink.relationship_type == link_in.relationship_type
        )
    )
    if dup.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="This evidence relationship is already linked to this 5-Whys step.")

    link = FiveWhysEvidenceLink(
        five_whys_step_id=step_id,
        evidence_id=link_in.evidence_id,
        relationship_type=link_in.relationship_type,
        relevance_explanation=link_in.relevance_explanation,
        confidence_rating=link_in.confidence_rating or "HIGH"
    )
    db.add(link)
    await db.flush()
    await db.refresh(link)

    await audit_service.log_action(
        db, step.investigation_id, "LINKED", "FIVE_WHYS",
        f"Linked Evidence #{ev.id} ('{ev.title}') to Why #{step.step_number} as {link.relationship_type}",
        entity_id=str(step.id),
        user_id=current_user.id,
        user_name=current_user.full_name
    )
    await db.commit()

    res_link = await db.execute(
        select(FiveWhysEvidenceLink)
        .options(selectinload(FiveWhysEvidenceLink.evidence))
        .filter(FiveWhysEvidenceLink.id == link.id)
    )
    return res_link.scalar_one()

@router.delete("/five-whys/{step_id}/evidence/{evidence_id}")
async def unlink_five_whys_evidence(
    step_id: int,
    evidence_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Unlink an evidence item from a 5-Whys step."""
    stmt = select(FiveWhysStep).filter(FiveWhysStep.id == step_id)
    res = await db.execute(stmt)
    step = res.scalar_one_or_none()
    if not step:
        raise HTTPException(status_code=404, detail="Five Whys step not found")

    await verify_investigation_access(step.investigation_id, current_user, db, require_write=True)

    link_res = await db.execute(
        select(FiveWhysEvidenceLink).filter(
            FiveWhysEvidenceLink.five_whys_step_id == step_id,
            FiveWhysEvidenceLink.evidence_id == evidence_id
        )
    )
    link = link_res.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="Evidence link not found")

    await db.delete(link)
    await db.commit()

    await audit_service.log_action(
        db, step.investigation_id, "UNLINKED", "FIVE_WHYS",
        f"Unlinked Evidence #{evidence_id} from Why #{step.step_number}",
        entity_id=str(step.id),
        user_id=current_user.id,
        user_name=current_user.full_name
    )
    return {"ok": True}

@router.post("/five-whys/{step_id}/verify", response_model=FiveWhysStepRead)
async def verify_five_whys_step(
    step_id: int,
    req: FiveWhysVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Formally verify or un-verify a Five Whys causal step.
    Safety Guard: Cannot mark verified without at least one verified piece of supporting evidence.
    """
    stmt = (
        select(FiveWhysStep)
        .options(
            selectinload(FiveWhysStep.evidence_links).selectinload(FiveWhysEvidenceLink.evidence)
        )
        .filter(FiveWhysStep.id == step_id)
    )
    res = await db.execute(stmt)
    step = res.scalar_one_or_none()
    if not step:
        raise HTTPException(status_code=404, detail="Five Whys step not found")

    await verify_investigation_access(step.investigation_id, current_user, db, require_write=True)

    if req.is_verified:
        # Check that step has at least one verified, non-archived supporting evidence link
        verified_supporting = [
            link for link in step.evidence_links
            if link.relationship_type == "SUPPORTING" and link.evidence and link.evidence.is_verified and not link.evidence.is_archived
        ]
        if not verified_supporting:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Verification safety violation: Cannot mark 5-Whys step as verified without at least "
                    "one verified, active piece of supporting evidence linked to this step."
                )
            )
        step.is_verified = True
        step.verified_by_user_id = current_user.id
        step.verified_at = datetime.utcnow()
        step.verification_notes = req.verification_notes
    else:
        step.is_verified = False
        step.verified_by_user_id = None
        step.verified_at = None
        step.verification_notes = req.verification_notes

    step.updated_at = datetime.utcnow()
    await db.flush()
    await db.commit()

    status_str = "VERIFIED" if step.is_verified else "UNVERIFIED"
    await audit_service.log_action(
        db, step.investigation_id, status_str, "FIVE_WHYS",
        f"Why #{step.step_number} marked {status_str} by {current_user.full_name}",
        entity_id=str(step.id),
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
    return step

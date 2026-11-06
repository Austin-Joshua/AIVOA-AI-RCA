from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime
from typing import Optional

from app.core.database import get_db
from app.core.security import get_current_user, verify_investigation_access
from app.models.audit import User
from app.models.capa import CapaAction
from app.models.root_cause import RootCause
from app.schemas.capa import (
    CapaActionCreate,
    CapaActionUpdate,
    CapaActionRead,
    CapaApproveRequest,
    CapaEffectivenessVerifyRequest,
    CapaCompleteRequest,
)
from app.services.audit_service import audit_service

router = APIRouter()


@router.post("/investigations/{investigation_id}/capas", response_model=CapaActionRead)
async def add_capa_action(
    investigation_id: int,
    capa_in: CapaActionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Propose a new CAPA action for an investigation.
    Enforces server-side data integrity:
    1. Caller must have write access to the investigation.
    2. Client cannot forge verification status (is_verified=True or status=APPROVED rejected with 400).
    3. Root cause, if specified, must exist, belong to the same investigation, and not be rejected.
    4. Initial status is always server-set to PROPOSED with is_verified=False.
    """
    await verify_investigation_access(investigation_id, current_user, db, require_write=True)

    # Prevent client from forging verification flags on creation
    if capa_in.is_verified is True:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Client cannot forge verification metadata. New CAPA actions must start unverified.",
        )
    if capa_in.status and capa_in.status.upper() in ("APPROVED", "EFFECTIVENESS_VERIFIED"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Client cannot create CAPA with pre-approved status. New CAPA actions must start in PROPOSED status.",
        )

    # Validate root_cause_id if provided
    if capa_in.root_cause_id is not None:
        rc_res = await db.execute(select(RootCause).filter(RootCause.id == capa_in.root_cause_id))
        rc = rc_res.scalar_one_or_none()
        if not rc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Referenced root cause #{capa_in.root_cause_id} does not exist.",
            )
        if rc.investigation_id != investigation_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cross-investigation error: Referenced root cause belongs to a different investigation.",
            )
        if rc.status == "REJECTED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot link CAPA action to a rejected root cause.",
            )

    capa = CapaAction(
        investigation_id=investigation_id,
        root_cause_id=capa_in.root_cause_id,
        action_type=capa_in.action_type.upper(),
        description=capa_in.description,
        rationale=capa_in.rationale,
        owner=capa_in.owner,
        deadline=capa_in.deadline,
        effectiveness_criteria=capa_in.effectiveness_criteria,
        effectiveness_review_period_days=capa_in.effectiveness_review_period_days,
        status="PROPOSED",
        is_ai_suggested=capa_in.is_ai_suggested,
        is_verified=False,
    )
    db.add(capa)
    await db.flush()
    await db.refresh(capa)

    await audit_service.log_action(
        db,
        investigation_id,
        "CREATED",
        "CAPA",
        f"Proposed {capa.action_type}: '{capa.description[:60]}...'",
        entity_id=str(capa.id),
        user_id=current_user.id,
        user_name=current_user.full_name,
    )
    await db.commit()
    await db.refresh(capa)
    return capa


@router.put("/capas/{capa_id}", response_model=CapaActionRead)
async def update_capa_action(
    capa_id: int,
    capa_update: CapaActionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update permitted work fields of a CAPA action.
    Enforces lifecycle guards:
    1. Verification flag (is_verified) cannot be forged or toggled directly via PUT.
    2. Cannot transition to APPROVED or EFFECTIVENESS_VERIFIED via PUT (dedicated QA endpoints required).
    3. PROPOSED actions cannot start (IN_PROGRESS) or complete without prior QA approval.
    4. Effectiveness-verified CAPAs are locked against general modification.
    5. Completing an action requires explanatory rationale notes.
    """
    result = await db.execute(select(CapaAction).filter(CapaAction.id == capa_id))
    capa = result.scalar_one_or_none()
    if not capa:
        raise HTTPException(status_code=404, detail="CAPA action not found")

    await verify_investigation_access(capa.investigation_id, current_user, db, require_write=True)

    # Guard: Verification flag cannot be modified directly via update
    if capa_update.is_verified is not None and capa_update.is_verified != capa.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification status (is_verified) cannot be modified directly. Formal QA approval is required.",
        )

    # Guard: Locked record
    if capa.status == "EFFECTIVENESS_VERIFIED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify an effectiveness-verified CAPA action. Verified records are locked for cGMP compliance.",
        )

    # Status transition validation
    if capa_update.status is not None:
        new_status = capa_update.status.upper().strip()
        if new_status == "OPEN":
            new_status = "PROPOSED"
        elif new_status == "CLOSED":
            new_status = "COMPLETED"

        valid_statuses = {"PROPOSED", "APPROVED", "IN_PROGRESS", "COMPLETED", "EFFECTIVENESS_VERIFIED"}
        if new_status not in valid_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid CAPA status: {new_status}. Must be one of {valid_statuses}",
            )

        # Prohibit jumping to APPROVED or EFFECTIVENESS_VERIFIED via general update
        if new_status == "APPROVED" and capa.status != "APPROVED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot transition to APPROVED via general update. Formal QA approval endpoint (POST /capas/{id}/approve) is required.",
            )
        if new_status == "EFFECTIVENESS_VERIFIED" and capa.status != "EFFECTIVENESS_VERIFIED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot transition to EFFECTIVENESS_VERIFIED via general update. Dedicated QA effectiveness verification endpoint is required.",
            )

        # Lifecycle state progression rules
        if capa.status == "PROPOSED" and new_status in ("IN_PROGRESS", "COMPLETED"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="CAPA must be formally APPROVED by QA before starting implementation (IN_PROGRESS) or completing.",
            )
        if capa.status in ("IN_PROGRESS", "COMPLETED") and new_status == "PROPOSED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot revert active or completed CAPA to PROPOSED status.",
            )

        # If marking COMPLETED, require rationale / completion notes
        if new_status == "COMPLETED":
            target_rationale = capa_update.rationale if capa_update.rationale is not None else capa.rationale
            if not target_rationale or len(target_rationale.strip()) < 5:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Completion requires valid rationale explaining corrective actions completed (minimum 5 characters).",
                )

        capa.status = new_status

    # Validate root_cause_id if changed
    if capa_update.root_cause_id is not None and capa_update.root_cause_id != capa.root_cause_id:
        rc_res = await db.execute(select(RootCause).filter(RootCause.id == capa_update.root_cause_id))
        rc = rc_res.scalar_one_or_none()
        if not rc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Referenced root cause #{capa_update.root_cause_id} does not exist.",
            )
        if rc.investigation_id != capa.investigation_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cross-investigation error: Referenced root cause belongs to a different investigation.",
            )
        if rc.status == "REJECTED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot link CAPA action to a rejected root cause.",
            )
        capa.root_cause_id = capa_update.root_cause_id

    # Update permitted work fields
    if capa_update.action_type is not None:
        capa.action_type = capa_update.action_type.upper().strip()
    if capa_update.description is not None:
        capa.description = capa_update.description
    if capa_update.rationale is not None:
        capa.rationale = capa_update.rationale
    if capa_update.owner is not None:
        capa.owner = capa_update.owner
    if capa_update.deadline is not None:
        capa.deadline = capa_update.deadline
    if capa_update.effectiveness_criteria is not None:
        capa.effectiveness_criteria = capa_update.effectiveness_criteria
    if capa_update.effectiveness_review_period_days is not None:
        capa.effectiveness_review_period_days = capa_update.effectiveness_review_period_days
    if capa_update.is_ai_suggested is not None:
        capa.is_ai_suggested = capa_update.is_ai_suggested

    capa.updated_at = datetime.utcnow()

    await audit_service.log_action(
        db,
        capa.investigation_id,
        "UPDATED",
        "CAPA",
        f"Updated CAPA action #{capa.id} ({capa.action_type}, Status: {capa.status})",
        entity_id=str(capa.id),
        user_id=current_user.id,
        user_name=current_user.full_name,
    )

    await db.commit()
    await db.refresh(capa)
    return capa


@router.post("/capas/{capa_id}/approve", response_model=CapaActionRead)
async def approve_capa_action(
    capa_id: int,
    req: Optional[CapaApproveRequest] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Formal QA approval of a proposed CAPA action.
    Enforces regulatory safety and separation of duties:
    1. Caller must have role QA_APPROVER or ADMIN (Investigator role denied with 403).
    2. Assigned lead investigator cannot approve CAPAs for their own investigation (denied with 403).
    3. CAPA must be in PROPOSED status (denied with 400).
    4. Sets status to APPROVED and is_verified=True.
    5. Commits transaction and creates auditable log record.
    """
    result = await db.execute(select(CapaAction).filter(CapaAction.id == capa_id))
    capa = result.scalar_one_or_none()
    if not capa:
        raise HTTPException(status_code=404, detail="CAPA action not found")

    inv = await verify_investigation_access(capa.investigation_id, current_user, db, require_write=False)

    # Role check: Only QA_APPROVER or ADMIN may formally approve
    if current_user.role not in ("QA_APPROVER", "ADMIN"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Formal CAPA approval requires QA_APPROVER or ADMIN role.",
        )

    # Separation of duties: Lead investigator cannot approve their own investigation's CAPAs
    if inv.lead_investigator_id is not None and inv.lead_investigator_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Separation of duties violation: The assigned lead investigator cannot formally approve CAPA proposals for their own investigation.",
        )

    if capa.status != "PROPOSED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot approve CAPA with status '{capa.status}'. Only PROPOSED CAPAs can be approved.",
        )

    capa.status = "APPROVED"
    capa.is_verified = True
    if req and req.approval_notes:
        note_text = f"[QA Approval]: {req.approval_notes.strip()}"
        capa.rationale = f"{capa.rationale}\n{note_text}" if capa.rationale else note_text
    capa.updated_at = datetime.utcnow()

    await audit_service.log_action(
        db,
        capa.investigation_id,
        "APPROVED",
        "CAPA",
        f"QA Approver {current_user.full_name} approved CAPA #{capa.id} ({capa.action_type})",
        entity_id=str(capa.id),
        user_id=current_user.id,
        user_name=current_user.full_name,
    )

    await db.commit()
    await db.refresh(capa)
    return capa


@router.post("/capas/{capa_id}/verify", response_model=CapaActionRead)
async def verify_capa_action(
    capa_id: int,
    req: Optional[CapaApproveRequest] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Backward-compatibility alias for CAPA approval.
    Directs to full approve workflow with QA role authorization and separation-of-duties checks.
    """
    return await approve_capa_action(capa_id=capa_id, req=req, current_user=current_user, db=db)


@router.post("/capas/{capa_id}/complete", response_model=CapaActionRead)
async def complete_capa_action(
    capa_id: int,
    req: CapaCompleteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Mark an approved or in-progress CAPA action as COMPLETED.
    Requires completion notes documenting execution.
    """
    result = await db.execute(select(CapaAction).filter(CapaAction.id == capa_id))
    capa = result.scalar_one_or_none()
    if not capa:
        raise HTTPException(status_code=404, detail="CAPA action not found")

    await verify_investigation_access(capa.investigation_id, current_user, db, require_write=True)

    if capa.status not in ("APPROVED", "IN_PROGRESS"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot complete CAPA action with status '{capa.status}'. CAPA must be APPROVED or IN_PROGRESS.",
        )

    if not req.completion_notes or len(req.completion_notes.strip()) < 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Completion requires non-empty completion notes explaining corrective action outcome (min 5 chars).",
        )

    capa.status = "COMPLETED"
    note_text = f"[Completion Note]: {req.completion_notes.strip()}"
    capa.rationale = f"{capa.rationale}\n{note_text}" if capa.rationale else note_text
    capa.updated_at = datetime.utcnow()

    await audit_service.log_action(
        db,
        capa.investigation_id,
        "COMPLETED",
        "CAPA",
        f"Investigator {current_user.full_name} marked CAPA #{capa.id} as COMPLETED",
        entity_id=str(capa.id),
        user_id=current_user.id,
        user_name=current_user.full_name,
    )

    await db.commit()
    await db.refresh(capa)
    return capa


@router.post("/capas/{capa_id}/verify-effectiveness", response_model=CapaActionRead)
async def verify_capa_effectiveness(
    capa_id: int,
    req: Optional[CapaEffectivenessVerifyRequest] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Formal QA verification of CAPA effectiveness after implementation review window.
    1. Caller must have role QA_APPROVER or ADMIN (Investigator role denied with 403).
    2. CAPA must be in COMPLETED status (denied with 400).
    3. CAPA must have defined quantitative effectiveness criteria.
    4. Sets status to EFFECTIVENESS_VERIFIED.
    5. Commits transaction and creates auditable log record.
    """
    result = await db.execute(select(CapaAction).filter(CapaAction.id == capa_id))
    capa = result.scalar_one_or_none()
    if not capa:
        raise HTTPException(status_code=404, detail="CAPA action not found")

    await verify_investigation_access(capa.investigation_id, current_user, db, require_write=False)

    if current_user.role not in ("QA_APPROVER", "ADMIN"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: CAPA effectiveness verification requires QA_APPROVER or ADMIN role.",
        )

    if capa.status != "COMPLETED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot verify effectiveness of CAPA with status '{capa.status}'. CAPA must be in COMPLETED status.",
        )

    if not capa.effectiveness_criteria or len(capa.effectiveness_criteria.strip()) < 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot verify effectiveness: CAPA lacks quantitative effectiveness criteria.",
        )

    capa.status = "EFFECTIVENESS_VERIFIED"
    if req and req.verification_notes:
        note_text = f"[Effectiveness Verification]: {req.verification_notes.strip()}"
        capa.effectiveness_criteria = (
            f"{capa.effectiveness_criteria}\n{note_text}" if capa.effectiveness_criteria else note_text
        )
    capa.updated_at = datetime.utcnow()

    await audit_service.log_action(
        db,
        capa.investigation_id,
        "EFFECTIVENESS_VERIFIED",
        "CAPA",
        f"QA Approver {current_user.full_name} verified effectiveness for CAPA #{capa.id} ({capa.action_type})",
        entity_id=str(capa.id),
        user_id=current_user.id,
        user_name=current_user.full_name,
    )

    await db.commit()
    await db.refresh(capa)
    return capa


@router.delete("/capas/{capa_id}")
async def delete_capa_action(
    capa_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a CAPA action from an investigation.
    Enforces regulatory integrity:
    1. Caller must have write access to the parent investigation.
    2. Cannot delete an effectiveness-verified CAPA action.
    3. Fully logs deletion in audit trail with committing transaction.
    """
    result = await db.execute(select(CapaAction).filter(CapaAction.id == capa_id))
    capa = result.scalar_one_or_none()
    if not capa:
        raise HTTPException(status_code=404, detail="CAPA action not found")

    inv_id = capa.investigation_id
    await verify_investigation_access(inv_id, current_user, db, require_write=True)

    if capa.status == "EFFECTIVENESS_VERIFIED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete an effectiveness-verified CAPA action. Verified records must be retained for regulatory compliance.",
        )

    action_type = capa.action_type
    desc = capa.description[:60]

    await db.delete(capa)

    await audit_service.log_action(
        db,
        inv_id,
        "DELETED",
        "CAPA",
        f"Deleted CAPA action #{capa_id} ({action_type}): '{desc}...' by {current_user.full_name}",
        entity_id=str(capa_id),
        user_id=current_user.id,
        user_name=current_user.full_name,
    )
    await db.commit()
    return {"ok": True, "deleted_id": capa_id}

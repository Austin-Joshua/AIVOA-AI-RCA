from fastapi import APIRouter, Depends, HTTPException, Query, Body, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import or_
from sqlalchemy.orm import selectinload
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel
import uuid

from app.core.database import get_db
from app.core.security import get_current_user, verify_investigation_access
from app.models.investigation import Investigation
from app.models.deviation import Deviation
from app.models.evidence import Evidence
from app.models.five_whys import FiveWhysStep, FiveWhysEvidenceLink
from app.models.fishbone import FishboneCause, FishboneEvidenceLink
from app.models.root_cause import RootCause, RootCauseEvidenceLink
from app.models.audit import User
from app.schemas.investigation import (
    InvestigationCreate,
    InvestigationUpdate,
    InvestigationAssignOwner,
    InvestigationRead,
    InvestigationSummary
)
from app.services.audit_service import audit_service

router = APIRouter()

@router.get("/", response_model=List[InvestigationSummary])
async def list_investigations(
    skip: int = 0,
    limit: int = 50,
    status: Optional[str] = None,
    include_archived: bool = Query(False, description="Whether to include soft-archived investigations"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all investigations accessible to the authenticated user."""
    query = select(Investigation).options(selectinload(Investigation.deviation)).order_by(Investigation.created_at.desc())
    
    # Ownership isolation: Investigators only see investigations they lead; QA/Admin can see all including unassigned
    if current_user.role not in ("ADMIN", "QA_APPROVER"):
        query = query.filter(Investigation.lead_investigator_id == current_user.id)
    
    if status:
        query = query.filter(Investigation.status == status)
    elif not include_archived:
        query = query.filter(Investigation.status != "ARCHIVED")
    
    result = await db.execute(query.offset(skip).limit(limit))
    investigations = result.scalars().all()
    
    summaries = []
    for inv in investigations:
        dev = inv.deviation
        summaries.append(InvestigationSummary(
            id=inv.id,
            investigation_number=inv.investigation_number,
            title=inv.title,
            status=inv.status,
            stage=inv.stage,
            lead_investigator=inv.lead_investigator,
            lead_investigator_id=inv.lead_investigator_id,
            qa_approver_id=inv.qa_approver_id,
            is_approved=inv.is_approved,
            created_at=inv.created_at,
            updated_at=inv.updated_at,
            deviation_number=dev.deviation_number if dev else None,
            batch_number=dev.batch_number if dev else None,
            product_name=dev.product_name if dev else None,
            severity=dev.severity if dev else None
        ))
    return summaries

@router.post("/", response_model=InvestigationRead)
async def create_investigation(
    inv_in: InvestigationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new RCA investigation dossier associated with the authenticated user."""
    inv_number = inv_in.investigation_number or f"INV-2026-{uuid.uuid4().hex[:6].upper()}"
    
    new_inv = Investigation(
        investigation_number=inv_number,
        title=inv_in.title,
        status=inv_in.status,
        stage=inv_in.stage,
        lead_investigator=current_user.full_name,
        lead_investigator_id=current_user.id,
        qa_approver=inv_in.qa_approver
    )
    db.add(new_inv)
    await db.flush()
    await db.refresh(new_inv)
    
    # Audit trail capturing authenticated user identity
    await audit_service.log_action(
        db, new_inv.id, "CREATED", "INVESTIGATION",
        f"Investigation {new_inv.investigation_number} opened: '{new_inv.title}'",
        user_name=current_user.full_name,
        user_id=current_user.id
    )
    
    # Return full investigation
    return await get_investigation_by_id(new_inv.id, db)

@router.post("/seed-demo-scenario", response_model=InvestigationRead)
async def seed_demo_scenario(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Seeds a fully initialized, cGMP-ready Paracetamol API demo investigation
    with deviation telemetry and verified evidence records for seamless presentation.
    """
    inv_number = f"INV-2026-{uuid.uuid4().hex[:6].upper()}"
    new_inv = Investigation(
        investigation_number=inv_number,
        title="Temperature Excursion in Paracetamol API Crystallization (Batch API-2026-104)",
        status="IN_INVESTIGATION",
        stage="INVESTIGATION",
        lead_investigator=current_user.full_name,
        lead_investigator_id=current_user.id
    )
    db.add(new_inv)
    await db.flush()

    dev = Deviation(
        investigation_id=new_inv.id,
        deviation_number="DEV-2026-104",
        deviation_number_source="SOURCE",
        deviation_type="MAJOR",
        severity="High",
        batch_number="API-2026-104",
        product_name="Paracetamol API (Acetaminophen Micronized USP)",
        unit_operation="Crystallization",
        equipment_id="CR-104",
        bpr_number="BPR-PARA-2026-042",
        occurrence_datetime=datetime.utcnow(),
        detection_datetime=datetime.utcnow(),
        description="During the secondary cooling crystallization cycle for Paracetamol API lot API-2026-104 in reactor CR-104, cooling control valve CV-104 failed to open beyond 15% due to a sudden drop in instrument pneumatic air pressure. Reactor temperature spiked to 86.4°C for 18 minutes, exceeding validated range of 75.0-80.0°C.",
        immediate_containment="Batch cooled to 72.0°C via manual bypass cooling. Slurry isolated and quarantined in buffer vessel. Quality Assurance quarantine notices affixed.",
        is_ai_populated=True,
        is_verified=True
    )
    db.add(dev)

    ev1 = Evidence(
        investigation_id=new_inv.id,
        title="SCADA Temperature Excursion Log (Reactor CR-104)",
        original_filename="SCADA_CR104_Temp_Batch_104.pdf",
        evidence_type="SCADA_TREND",
        classification="SYSTEM_TELEMETRY",
        source="DCS-HISTORIAN-TAG-TI104",
        source_location="Historian Archive Batch API-2026-104",
        extracted_text="CR-104 Temperature Historian Trace: 04:12:00 setpoint 78.0°C, actual 78.2°C; 04:14:30 temp 81.5°C (CRITICAL ALARM HIGH); 04:18:00 temp peak 86.4°C; 04:30:00 temp normalized to 78.1°C following emergency manual cooling water bypass engagement.",
        confidence_score=1.0,
        is_verified=True,
        verified_by=current_user.full_name,
        verified_by_user_id=current_user.id,
        verification_date=datetime.utcnow(),
        investigator_notes="Empirical process historian telemetry corroborating the 18-minute thermal excursion above 80.0°C."
    )
    db.add(ev1)

    ev2 = Evidence(
        investigation_id=new_inv.id,
        title="Cooling Control Valve CV-104 Telemetry & Pressure Log",
        original_filename="Maintenance_Valve_Actuator_CV104.pdf",
        evidence_type="LOGBOOK",
        classification="PRIMARY_SOURCE",
        source="PNEUMATIC-SENSOR-PT104",
        source_location="Valve Actuation Diagnostics Channel 2",
        extracted_text="CV-104 Valve Diagnostics: Command signal 100% open delivered at 04:13:10. Actuator position feedback remained mechanically arrested at 14.8%. Upstream instrument air header pressure fell from nominal 6.0 bar to 2.1 bar due to a ruptured O-ring on pneumatic regulator PR-104.",
        confidence_score=1.0,
        is_verified=True,
        verified_by=current_user.full_name,
        verified_by_user_id=current_user.id,
        verification_date=datetime.utcnow(),
        investigator_notes="Direct mechanical evidence establishing that pneumatic pressure loss prevented CV-104 from actuating."
    )
    db.add(ev2)

    await db.flush()

    await audit_service.log_action(
        db, new_inv.id, "CREATED", "INVESTIGATION",
        f"Demo scenario initialized with deviation and verified evidence: '{new_inv.title}'",
        user_name=current_user.full_name,
        user_id=current_user.id
    )

    return await get_investigation_by_id(new_inv.id, db)

@router.get("/{investigation_id}", response_model=InvestigationRead)
async def get_investigation(
    investigation_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get full investigation details with ownership access verification."""
    await verify_investigation_access(investigation_id, current_user, db)
    return await get_investigation_by_id(investigation_id, db)

@router.put("/{investigation_id}", response_model=InvestigationRead)
async def update_investigation(
    investigation_id: int,
    inv_update: InvestigationUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update investigation status, stage, or title with ownership enforcement."""
    inv = await verify_investigation_access(investigation_id, current_user, db, require_write=True)

    changes = []
    if inv_update.title is not None and inv_update.title != inv.title:
        changes.append(f"Title: '{inv.title}' -> '{inv_update.title}'")
        inv.title = inv_update.title
    if inv_update.status is not None and inv_update.status != inv.status:
        changes.append(f"Status: '{inv.status}' -> '{inv_update.status}'")
        inv.status = inv_update.status
    if inv_update.stage is not None and inv_update.stage != inv.stage:
        changes.append(f"Stage: '{inv.stage}' -> '{inv_update.stage}'")
        inv.stage = inv_update.stage
    if inv_update.qa_approver is not None:
        inv.qa_approver = inv_update.qa_approver
    if inv_update.is_approved is not None:
        inv.is_approved = inv_update.is_approved
        if inv.is_approved:
            inv.approval_date = datetime.utcnow()
            changes.append(f"Investigation signed off by {inv.qa_approver or inv.lead_investigator}")
    if inv_update.approval_comments is not None:
        inv.approval_comments = inv_update.approval_comments

    inv.updated_at = datetime.utcnow()
    await db.flush()

    if changes:
        await audit_service.log_action(
            db, investigation_id, "UPDATED", "INVESTIGATION",
            "; ".join(changes),
            user_name=current_user.full_name,
            user_id=current_user.id
        )

    return await get_investigation_by_id(investigation_id, db)

class ArchiveRequest(BaseModel):
    reason: Optional[str] = "Archived by administrator"

class ApprovalPayload(BaseModel):
    comments: Optional[str] = None

@router.post("/{investigation_id}/approve", response_model=InvestigationRead)
async def approve_investigation(
    investigation_id: int,
    comments: Optional[str] = Query(None, description="QA Review Comments"),
    payload: Optional[ApprovalPayload] = Body(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Formal human sign-off on the investigation dossier.
    Requires QA_APPROVER or ADMIN role. Resolves identity directly from authenticated user token.
    Enforces a mandatory closure rationale (minimum 10 characters).
    """
    inv = await verify_investigation_access(investigation_id, current_user, db, require_qa=True)

    final_comments = (comments or "").strip()
    if not final_comments and payload and payload.comments:
        final_comments = payload.comments.strip()

    if not final_comments or len(final_comments) < 10:
        raise HTTPException(
            status_code=400,
            detail="Formal QA approval requires a closure rationale of at least 10 characters."
        )

    inv.is_approved = True
    inv.status = "APPROVED"
    inv.stage = "APPROVAL"
    inv.qa_approver = current_user.full_name
    inv.qa_approver_id = current_user.id
    inv.approval_date = datetime.utcnow()
    inv.approval_comments = final_comments
    inv.updated_at = datetime.utcnow()

    await audit_service.log_action(
        db, investigation_id, "APPROVED", "INVESTIGATION",
        f"Formal QA approval signed by {current_user.full_name} (User ID #{current_user.id}). Comments: {inv.approval_comments}",
        user_name=current_user.full_name,
        user_id=current_user.id
    )

    return await get_investigation_by_id(investigation_id, db)

@router.post("/{investigation_id}/archive", response_model=InvestigationRead)
async def archive_investigation(
    investigation_id: int,
    payload: Optional[ArchiveRequest] = Body(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Soft-archives an investigation dossier.
    Restricted strictly to users with the ADMIN role.
    """
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=403,
            detail="Administrative privilege required to archive investigation dossiers."
        )

    inv = await get_investigation_by_id(investigation_id, db)
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")

    reason = (payload.reason if payload and payload.reason else "Archived by administrator").strip()
    inv.status = "ARCHIVED"
    inv.updated_at = datetime.utcnow()

    await audit_service.log_action(
        db, investigation_id, "ARCHIVED", "INVESTIGATION",
        f"Investigation archived: {inv.investigation_number}. Reason: {reason}",
        user_name=current_user.full_name,
        user_id=current_user.id
    )
    await db.commit()
    await db.refresh(inv)
    return inv

@router.post("/{investigation_id}/assign-owner", response_model=InvestigationRead)
async def assign_investigation_owner(
    investigation_id: int,
    assignment_in: InvestigationAssignOwner,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Administrative ownership assignment endpoint.
    Strictly restricted to users with role='ADMIN'.
    Records an immutable audit event with actor, previous owner, new owner, and rationale.
    """
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Only administrators can assign investigation ownership."
        )

    res = await db.execute(select(Investigation).filter(Investigation.id == investigation_id))
    inv = res.scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")

    target_res = await db.execute(select(User).filter(User.id == assignment_in.new_investigator_id))
    new_owner = target_res.scalar_one_or_none()
    if not new_owner:
        raise HTTPException(status_code=404, detail=f"Target user #{assignment_in.new_investigator_id} not found")

    if hasattr(new_owner, "is_active") and not new_owner.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Target user #{new_owner.id} ('{new_owner.username}') is inactive and cannot be assigned ownership."
        )

    if new_owner.role != "INVESTIGATOR":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Target user #{new_owner.id} has role '{new_owner.role}'. Investigation ownership can only be assigned to accounts with role 'INVESTIGATOR' to maintain segregation of duties between investigation and quality approval."
        )

    try:
        prev_owner_id = inv.lead_investigator_id
        prev_owner_name = inv.lead_investigator or "Unassigned"

        inv.lead_investigator_id = new_owner.id
        inv.lead_investigator = new_owner.full_name
        inv.updated_at = datetime.utcnow()

        await audit_service.log_action(
            db, investigation_id, "OWNERSHIP_ASSIGNED", "INVESTIGATION",
            f"Investigation ownership reassigned from '{prev_owner_name}' (ID #{prev_owner_id}) to '{new_owner.full_name}' (ID #{new_owner.id}) by administrator {current_user.full_name}. Reason: {assignment_in.reason}",
            user_name=current_user.full_name,
            user_id=current_user.id
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    return await get_investigation_by_id(investigation_id, db)

async def get_investigation_by_id(inv_id: int, db: AsyncSession) -> Investigation:
    query = (
        select(Investigation)
        .options(
            selectinload(Investigation.deviation),
            selectinload(Investigation.evidences),
            selectinload(Investigation.evidence_gaps),
            selectinload(Investigation.findings),
            selectinload(Investigation.five_whys).selectinload(FiveWhysStep.evidence_links).selectinload(FiveWhysEvidenceLink.evidence),
            selectinload(Investigation.fishbone_causes).selectinload(FishboneCause.evidence_links).selectinload(FishboneEvidenceLink.evidence),
            selectinload(Investigation.root_causes).selectinload(RootCause.evidence_links).selectinload(RootCauseEvidenceLink.evidence),
            selectinload(Investigation.root_causes).selectinload(RootCause.dispositions),
            selectinload(Investigation.capa_actions),
            selectinload(Investigation.audit_logs),
        )
        .filter(Investigation.id == inv_id)
    )
    result = await db.execute(query)
    inv = result.scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return inv


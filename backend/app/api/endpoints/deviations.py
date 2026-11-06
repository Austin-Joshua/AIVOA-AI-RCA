from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.core.security import get_current_user, verify_investigation_access
from app.models.audit import User
from app.models.deviation import Deviation
from app.schemas.deviation import DeviationUpdate, DeviationRead, DeviationCreate
from app.services.audit_service import audit_service

router = APIRouter()

@router.post("/", response_model=DeviationRead)
async def create_or_upsert_deviation(
    dev_in: DeviationCreate,
    investigation_id: int = Query(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create or upsert deviation details for an investigation dossier."""
    await verify_investigation_access(investigation_id, current_user, db, require_write=True)
    res = await db.execute(select(Deviation).filter(Deviation.investigation_id == investigation_id))
    dev = res.scalar_one_or_none()

    if dev:
        for k, v in dev_in.dict(exclude_unset=True).items():
            setattr(dev, k, v)
        action_msg = f"Updated deviation {dev.deviation_number} for investigation {investigation_id}"
    else:
        dev = Deviation(investigation_id=investigation_id, **dev_in.dict())
        db.add(dev)
        action_msg = f"Created deviation {dev.deviation_number} for investigation {investigation_id}"

    await db.flush()
    await audit_service.log_action(
        db, investigation_id, "UPSERTED", "DEVIATION",
        action_msg, entity_id=str(dev.id),
        user_id=current_user.id,
        user_name=current_user.full_name
    )
    await db.commit()
    await db.refresh(dev)
    return dev

@router.put("/{deviation_id}", response_model=DeviationRead)
async def update_deviation(
    deviation_id: int,
    dev_update: DeviationUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update deviation fields with audit trail."""
    result = await db.execute(select(Deviation).filter(Deviation.id == deviation_id))
    dev = result.scalar_one_or_none()
    if not dev:
        raise HTTPException(status_code=404, detail="Deviation not found")

    await verify_investigation_access(dev.investigation_id, current_user, db, require_write=True)

    update_dict = dev_update.dict(exclude_unset=True)
    changes = []
    for field, new_val in update_dict.items():
        old_val = getattr(dev, field)
        if old_val != new_val:
            setattr(dev, field, new_val)
            changes.append(f"{field}: '{old_val}' -> '{new_val}'")

    if changes:
        await audit_service.log_action(
            db, dev.investigation_id, "UPDATED", "DEVIATION",
            "; ".join(changes), entity_id=str(dev.id),
            user_id=current_user.id,
            user_name=current_user.full_name
        )

    await db.flush()
    await db.refresh(dev)
    return dev

@router.post("/{deviation_id}/verify", response_model=DeviationRead)
async def verify_deviation(
    deviation_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Investigator confirms and signs off on the accuracy of the deviation details."""
    result = await db.execute(select(Deviation).filter(Deviation.id == deviation_id))
    dev = result.scalar_one_or_none()
    if not dev:
        raise HTTPException(status_code=404, detail="Deviation not found")

    await verify_investigation_access(dev.investigation_id, current_user, db, require_write=True)

    dev.is_verified = True
    await audit_service.log_action(
        db, dev.investigation_id, "VERIFIED", "DEVIATION",
        f"Investigator {current_user.full_name} verified deviation information as accurate",
        entity_id=str(dev.id),
        user_id=current_user.id,
        user_name=current_user.full_name
    )

    await db.flush()
    await db.refresh(dev)
    return dev


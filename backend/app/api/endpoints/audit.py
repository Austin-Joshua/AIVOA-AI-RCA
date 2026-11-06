from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

from app.core.database import get_db
from app.core.security import get_current_user, verify_investigation_access
from app.models.audit import AuditLog, User
from app.schemas.investigation import AuditLogRead

router = APIRouter()

@router.get("/investigations/{investigation_id}/audit-logs", response_model=List[AuditLogRead])
async def get_investigation_audit_logs(
    investigation_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve full audit trail for an investigation."""
    await verify_investigation_access(investigation_id, current_user, db)
    result = await db.execute(
        select(AuditLog)
        .filter(AuditLog.investigation_id == investigation_id)
        .order_by(AuditLog.timestamp.desc())
    )
    return result.scalars().all()


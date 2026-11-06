from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit import AuditLog
import logging

logger = logging.getLogger(__name__)

class AuditService:
    @staticmethod
    async def log_action(
        db: AsyncSession,
        investigation_id: int,
        action: str,
        entity_type: str,
        change_summary: str,
        user_name: str = "Lead Investigator",
        entity_id: str = None,
        user_id: int = None
    ) -> AuditLog:
        """Create an audit log record for an investigation change with authenticated user ID."""
        audit_entry = AuditLog(
            investigation_id=investigation_id,
            user_id=user_id,
            user_name=user_name,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id else None,
            change_summary=change_summary
        )
        db.add(audit_entry)
        await db.flush()
        logger.info(f"Audit log recorded: [Inv #{investigation_id}] {action} on {entity_type}: {change_summary}")
        return audit_entry

audit_service = AuditService()


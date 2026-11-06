import logging
from typing import Dict, Any, Optional
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import User
from app.core.security import hash_password

logger = logging.getLogger("aivoa-rca.admin-provisioning")

async def provision_admin_account(
    db: AsyncSession,
    username: Optional[str] = None,
    password: Optional[str] = None,
    email: Optional[str] = None,
    full_name: Optional[str] = None,
    department: str = "IT Quality Compliance"
) -> Dict[str, Any]:
    """
    Provisions an initial administrator account securely.
    - Validates required inputs (username, password min 10 chars).
    - Checks whether user already exists. If user exists, preserves existing credentials
      without overwriting.
    - Creates new ADMIN user with PBKDF2-HMAC-SHA256 hashed password.
    - Never logs or exposes password in outputs or messages.
    """
    clean_username = (username or "").strip()
    clean_password = (password or "").strip()

    if not clean_username or not clean_password:
        return {
            "success": False,
            "error": "Missing required administrator credentials. Provide both a non-empty username and password."
        }

    if len(clean_password) < 10:
        return {
            "success": False,
            "error": "Password does not meet minimum security requirements. Password must be at least 10 characters."
        }

    # Check if user already exists
    res = await db.execute(select(User).where(User.username == clean_username))
    existing = res.scalars().first()
    if existing:
        return {
            "success": False,
            "user_id": existing.id,
            "username": existing.username,
            "already_exists": True,
            "error": f"Administrator account '{clean_username}' already exists. Existing credentials were preserved and not modified."
        }

    admin_email = (email or f"{clean_username}@aivoa.pharma").strip()
    admin_name = (full_name or f"System Administrator ({clean_username})").strip()

    new_admin = User(
        username=clean_username,
        email=admin_email,
        full_name=admin_name,
        hashed_password=hash_password(clean_password),
        role="ADMIN",
        department=department,
        is_active=True
    )
    db.add(new_admin)
    await db.commit()
    await db.refresh(new_admin)

    logger.info(
        "Administrator account '%s' successfully provisioned with role ADMIN (User ID #%d).",
        clean_username,
        new_admin.id
    )
    return {
        "success": True,
        "user_id": new_admin.id,
        "username": new_admin.username,
        "email": new_admin.email,
        "role": new_admin.role,
        "message": f"Administrator account '{clean_username}' successfully provisioned."
    }


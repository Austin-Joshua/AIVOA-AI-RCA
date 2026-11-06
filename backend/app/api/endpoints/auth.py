from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
import logging

logger = logging.getLogger(__name__)
from app.core.config import settings
from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token, get_current_user
from app.models.audit import User

router = APIRouter()

class LoginRequest(BaseModel):
    username: str
    password: str

class DemoLoginRequest(BaseModel):
    persona: str = Field(..., description="'investigator' or 'qa'")

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in_seconds: int
    user_id: int
    username: str
    full_name: str
    role: str
    department: str

class UserProfileResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: str
    role: str
    department: str

async def ensure_default_users(db: AsyncSession):
    """
    Seeds demo QA Lead Investigator and Director accounts for development and testing.
    Strictly restricted to 'development' and 'test' environments.
    Production login requests never seed accounts.
    Refuses to run if DEMO_ACCOUNT_PASSWORD is unset in environment.
    Default ADMIN accounts are NEVER auto-seeded via public login requests in any environment.
    """
    if not settings.allows_demo_seeding or settings.is_production or getattr(settings, "ENVIRONMENT", "").lower() == "production":
        return

    import os
    dev_demo_password = os.getenv("DEMO_ACCOUNT_PASSWORD")
    if not dev_demo_password or not dev_demo_password.strip():
        logger.warning("DEMO_ACCOUNT_PASSWORD not configured. Demo seeding disabled.")
        return

    inv_name = os.getenv("DEMO_INVESTIGATOR_NAME", "Lead Investigator")
    qa_name = os.getenv("DEMO_QA_NAME", "Quality Assurance Director")

    demo_accounts = [
        {
            "username": "lead_investigator",
            "password": dev_demo_password,
            "email": "investigator@aivoa.pharma",
            "full_name": inv_name,
            "role": "INVESTIGATOR",
            "department": "Quality Assurance"
        },
        {
            "username": "qa_director",
            "password": dev_demo_password,
            "email": "director@aivoa.pharma",
            "full_name": qa_name,
            "role": "QA_APPROVER",
            "department": "Executive Quality"
        }
    ]
    for acc in demo_accounts:
        res = await db.execute(select(User).where(User.username == acc["username"]))
        existing = res.scalars().first()
        if not existing:
            new_user = User(
                username=acc["username"],
                email=acc["email"],
                full_name=acc["full_name"],
                hashed_password=hash_password(acc["password"]),
                role=acc["role"],
                department=acc["department"],
                is_active=True
            )
            db.add(new_user)
            await db.commit()

@router.get("/config")
async def get_auth_config():
    """
    Returns public client-facing authentication capabilities.
    Does not expose secrets, credentials, or internal configuration paths.
    """
    return {
        "demo_login_enabled": settings.demo_login_allowed,
        "environment": "production" if settings.is_production else settings.ENVIRONMENT,
    }

@router.post("/demo-login", response_model=TokenResponse)
async def demo_login(req: DemoLoginRequest, db: AsyncSession = Depends(get_db)):
    """
    One-click demo login for recording/demo environments only.
    Works ONLY when ALLOW_DEMO_LOGIN=true and ENVIRONMENT != production.
    Reads password/credentials from server-side environment and logs an audit entry.
    """
    if not settings.demo_login_allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo login is disabled in this environment."
        )

    persona = req.persona.strip().lower()
    if persona not in ("investigator", "qa"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid persona. Expected 'investigator' or 'qa'."
        )

    await ensure_default_users(db)

    username = "lead_investigator" if persona == "investigator" else "qa_director"
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Demo account '{username}' is not provisioned."
        )

    logger.info(
        f"AUDIT_AUTH: Demo login granted for persona='{persona}' username='{user.username}' user_id={user.id}"
    )

    token_data = {
        "sub": user.username,
        "user_id": user.id,
        "role": user.role,
        "full_name": user.full_name
    }
    token = create_access_token(token_data)

    return TokenResponse(
        access_token=token,
        expires_in_seconds=24 * 3600,
        user_id=user.id,
        username=user.username,
        full_name=user.full_name,
        role=user.role,
        department=user.department or "Quality Assurance"
    )

@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticates investigator or QA approver credentials and issues a signed, expiring access token."""
    await ensure_default_users(db)

    result = await db.execute(select(User).where(User.username == req.username))
    user = result.scalars().first()

    if not user or not user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password."
        )

    if not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password."
        )

    if hasattr(user, "is_active") and not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is inactive. Contact system administrator."
        )

    token_data = {
        "sub": user.username,
        "user_id": user.id,
        "role": user.role,
        "full_name": user.full_name
    }
    token = create_access_token(token_data)

    return TokenResponse(
        access_token=token,
        expires_in_seconds=24 * 3600,
        user_id=user.id,
        username=user.username,
        full_name=user.full_name,
        role=user.role,
        department=user.department or "Quality Assurance"
    )

@router.get("/me", response_model=UserProfileResponse)
async def get_my_profile(current_user: User = Depends(get_current_user)):
    """Returns the profile of the currently authenticated investigator/approver."""
    return UserProfileResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        department=current_user.department or "Quality Assurance"
    )


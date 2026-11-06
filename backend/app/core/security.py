import hmac
import hashlib
import secrets
import json
import base64
import time
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import get_db
from app.models.audit import User

security_scheme = HTTPBearer(auto_error=False)

# Password hashing using NIST-recommended PBKDF2-HMAC-SHA256
def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    iterations = 100_000
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${derived.hex()}"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not hashed_password or not plain_password:
        return False
    try:
        parts = hashed_password.split("$")
        if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
            return False
        iterations = int(parts[1])
        salt = bytes.fromhex(parts[2])
        expected_hash = parts[3]
        derived = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(derived.hex(), expected_hash)
    except Exception:
        return False

# Cryptographic token management using base64url + HMAC-SHA256
def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")

def _b64url_decode(s: str) -> bytes:
    padding = 4 - (len(s) % 4)
    if padding and padding < 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s.encode("utf-8"))

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    now = datetime.utcnow()
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode["exp"] = int(expire.timestamp())
    to_encode["iat"] = int(now.timestamp())
    
    header = {"alg": "HS256", "typ": "JWT"}
    header_bytes = json.dumps(header, separators=(",", ":")).encode("utf-8")
    payload_bytes = json.dumps(to_encode, separators=(",", ":")).encode("utf-8")
    
    encoded_header = _b64url_encode(header_bytes)
    encoded_payload = _b64url_encode(payload_bytes)
    
    signing_input = f"{encoded_header}.{encoded_payload}".encode("utf-8")
    signature = hmac.new(settings.SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
    encoded_signature = _b64url_encode(signature)
    
    return f"{encoded_header}.{encoded_payload}.{encoded_signature}"

def decode_access_token(token: str) -> Dict[str, Any]:
    try:
        parts = token.strip().split(".")
        if len(parts) != 3:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Malformed authentication token."
            )
        encoded_header, encoded_payload, encoded_signature = parts
        signing_input = f"{encoded_header}.{encoded_payload}".encode("utf-8")
        expected_sig = hmac.new(settings.SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
        
        # Verify signature
        if not hmac.compare_digest(_b64url_encode(expected_sig), encoded_signature):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token signature."
            )
        
        payload_bytes = _b64url_decode(encoded_payload)
        payload = json.loads(payload_bytes.decode("utf-8"))
        
        # Check expiration
        exp = payload.get("exp")
        if not exp or int(time.time()) > exp:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication token has expired."
            )
        return payload
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials."
        )

async def get_optional_current_user(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """Returns authenticated User if Bearer token is provided, or None if omitted."""
    if not auth or not auth.credentials:
        return None
    
    payload = decode_access_token(auth.credentials)
    username: str = payload.get("sub")
    if not username:
        return None
    
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalars().first()
    return user

async def get_current_user(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Enforces Bearer authentication; raises HTTP 401 if token is missing, invalid or user not found."""
    if not auth or not auth.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please provide a valid Bearer token."
        )
    user = await get_optional_current_user(auth, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user account not found in database."
        )
    return user

async def verify_investigation_access(
    investigation_id: int,
    current_user: User,
    db: AsyncSession,
    require_qa: bool = False,
    require_write: bool = False
):
    """
    Verifies that the investigation exists and that current_user has access.
    - If require_qa is True: requires current_user.role in ("QA_APPROVER", "ADMIN").
    - If require_write is True: ensures the user is the owner (lead_investigator) or an ADMIN.
    - An INVESTIGATOR can only access investigations where lead_investigator_id == current_user.id.
    - Raises HTTP 404 if investigation does not exist.
    - Raises HTTP 403 if unauthorized.
    """
    from app.models.investigation import Investigation

    res = await db.execute(select(Investigation).filter(Investigation.id == investigation_id))
    inv = res.scalar_one_or_none()
    if not inv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Investigation not found"
        )

    if require_qa:
        if current_user.role not in ("QA_APPROVER", "ADMIN"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: Formal QA approval requires QA_APPROVER or ADMIN role."
            )
        return inv

    if inv.lead_investigator_id is not None:
        if inv.lead_investigator_id != current_user.id and current_user.role not in ("ADMIN", "QA_APPROVER"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: You do not have permission to access or modify this investigation."
            )
        if require_write and inv.lead_investigator_id != current_user.id and current_user.role != "ADMIN":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: Only the assigned lead investigator or an administrator can modify this investigation."
            )
    else:
        # Unassigned / legacy investigation: Strictly non-mutating authorization.
        # Ordinary investigators cannot access unassigned records.
        # Quality approvers and Administrators may read unassigned dossiers.
        if current_user.role not in ("ADMIN", "QA_APPROVER"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: This investigation has not been assigned to a lead investigator. Please contact an Administrator for assignment."
            )
        if require_write and current_user.role != "ADMIN":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: Only an administrator can modify an unassigned investigation."
            )

    return inv


"""
Authentication Module
=====================
Handles JWT token creation, password hashing, and user authentication.

Security Features:
- Bcrypt password hashing
- JWT tokens with expiration
- Role-based access control (RBAC)
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, List
import bcrypt
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

import models
import database
from config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES

# Bcrypt hashes passwords in 72-byte blocks: anything longer is silently
# truncated by older implementations and rejected by bcrypt >= 5.
BCRYPT_MAX_BYTES = 72

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


# ============================================
# Password Functions
# ============================================
def _password_bytes(password: str) -> bytes:
    """Encode a password and enforce bcrypt's 72-byte limit explicitly.

    Truncating silently would make two different long passwords equivalent.
    """
    encoded = password.encode("utf-8")
    if len(encoded) > BCRYPT_MAX_BYTES:
        raise ValueError(f"Password must not exceed {BCRYPT_MAX_BYTES} bytes")
    return encoded


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its bcrypt hash.

    Returns False instead of raising on malformed hashes or oversized
    passwords, so a bad row can never turn a login attempt into a 500.
    """
    try:
        return bcrypt.checkpw(
            _password_bytes(plain_password),
            hashed_password.encode("utf-8"),
        )
    except (ValueError, TypeError):
        return False


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(_password_bytes(password), bcrypt.gensalt()).decode("utf-8")


# ============================================
# JWT Token Functions
# ============================================
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()

    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "iat": now})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> dict:
    """Decode and verify a JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ============================================
# Dependency Functions
# ============================================
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(database.get_db),
) -> models.User:
    """
    FastAPI dependency that extracts the current authenticated user from JWT token.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_token(token)
    username: str = payload.get("sub")
    user_id: int = payload.get("user_id")

    if username is None or user_id is None:
        raise credentials_exception

    user = db.query(models.User).filter(models.User.id == user_id).first()

    # A deactivated account must lose access immediately, even if it still
    # holds a valid (non-expired) token.
    if user is None or not user.is_active:
        raise credentials_exception

    return user


def require_role(allowed_roles: List[str]):
    """
    Role-based access control dependency.

    Usage:
        @app.get("/admin-only")
        def admin_endpoint(current_user: User = Depends(require_role(["admin"]))):
            ...
    """
    def role_checker(current_user: models.User = Depends(get_current_user)) -> models.User:
        if current_user.role.value not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {', '.join(allowed_roles)}",
            )
        return current_user

    return role_checker


# ============================================
# Utility Functions
# ============================================
def authenticate_user(db: Session, username: str, password: str) -> Optional[models.User]:
    """Authenticate a user with username and password."""
    from sqlalchemy import or_

    user = db.query(models.User).filter(
        or_(
            models.User.username == username,
            models.User.email == username,
        )
    ).first()

    if not user:
        return None

    if not verify_password(password, user.hashed_password):
        return None

    return user


def create_refresh_token(data: dict) -> str:
    """Create a refresh token with longer expiration (7 days)."""
    expires_delta = timedelta(days=7)
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + expires_delta
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

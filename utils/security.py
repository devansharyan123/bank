"""
security.py — All authentication and authorization logic in one place.

Covers:
  - Password hashing and verification
  - JWT token creation and decoding
  - FastAPI dependencies: get_current_user, require_admin
"""

from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from database import get_db, get_settings
from models.enums import UserRole

settings = get_settings()

# bcrypt is the hashing algorithm — slow by design to resist brute-force attacks
password_hasher = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Tells FastAPI where the token comes from (used in /docs Authorize button)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# ---------------------------------------------------------------------------
# Password utilities
# ---------------------------------------------------------------------------

def hash_password(plain_password: str) -> str:
    """Convert a plain-text password into a secure bcrypt hash."""
    return password_hasher.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check if a plain-text password matches its stored hash."""
    return password_hasher.verify(plain_password, hashed_password)


# ---------------------------------------------------------------------------
# JWT utilities
# ---------------------------------------------------------------------------

def create_access_token(data: dict) -> str:
    """
    Create a JWT token that encodes the user's identity.

    The token expires after the configured number of minutes.
    The user sends this token in every request header to prove who they are.
    """
    payload = data.copy()
    expiry_time = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload["exp"] = expiry_time

    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def decode_access_token(token: str) -> dict | None:
    """
    Decode a JWT token and return its payload.

    Returns None if the token is invalid or has expired.
    """
    try:
        return jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    except JWTError:
        return None


# ---------------------------------------------------------------------------
# FastAPI route dependencies
# ---------------------------------------------------------------------------

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    """
    FastAPI dependency — decode the JWT token and return the logged-in user.

    Use this on any route that requires the user to be logged in.
    """
    # Import here to avoid circular imports (models import database, database does not import models)
    from models.user import User

    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token does not contain user information.",
        )

    user = db.get(User, int(user_id))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer exists.",
        )

    return user


def require_admin(current_user=Depends(get_current_user)):
    """
    FastAPI dependency — same as get_current_user but also checks for admin role.

    Use this on admin-only routes like loan approval or the fraud dashboard.
    """
    if current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )
    return current_user

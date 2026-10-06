"""
FastAPI dependency providers: DB session, current user authentication, and RBAC enforcement.
"""
import uuid
from typing import Callable, Generator
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.config import Settings, get_settings
from backend.app.core.security import decode_access_token
from backend.app.db.session import SessionLocal
from backend.app.models.revoked_token import RevokedToken
from backend.app.models.user import User

security_bearer = HTTPBearer(auto_error=False)


def get_db() -> Generator[Session, None, None]:
    """Provide a transactional DB session; always closes on exit."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_settings_dep() -> Settings:
    """Provide cached settings."""
    return get_settings()


async def get_current_user(
    auth: HTTPAuthorizationCredentials | None = Depends(security_bearer),
    db: Session = Depends(get_db),
) -> User:
    """
    Authenticate the request by validating the Bearer JWT token.
    Enforces token expiration, algorithm, signature, jti denylist, and user active status.
    """
    if auth is None or not auth.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = auth.credentials
    try:
        payload = decode_access_token(token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    jti_str = payload.get("jti")
    user_id_str = payload.get("sub")
    if not jti_str or not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token claims",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        token_jti = uuid.UUID(jti_str)
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed token identifiers",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check revoked tokens denylist
    is_revoked = db.execute(
        select(RevokedToken.jti).where(RevokedToken.jti == token_jti)
    ).scalar_one_or_none()
    if is_revoked is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Fetch user from DB
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is deactivated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Attach current token info to user instance for use in logout
    user._current_jti = token_jti  # type: ignore[attr-defined]
    user._current_exp = payload.get("exp")  # type: ignore[attr-defined]
    return user


def require_role(*allowed_roles: str) -> Callable:
    """Factory for RBAC dependency requiring user to have one of the allowed_roles."""

    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: role '{current_user.role}' lacks permission for this resource",
            )
        return current_user

    return role_checker

"""
Authentication router: login, logout, and current user profile.
"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.deps import get_current_user, get_db
from backend.app.core.rate_limit import limiter
from backend.app.core.security import create_access_token, verify_password
from backend.app.models.revoked_token import RevokedToken
from backend.app.models.user import User
from backend.app.schemas.auth import (
    LoginRequest,
    LogoutResponse,
    TokenResponse,
    UserResponse,
)
from backend.app.services.audit_service import create_audit_log

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(
    request: Request,
    credentials: LoginRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """
    Authenticate user with username and password.
    Enforces Argon2id verification, equalized timing on non-existent users,
    login rate-limiting, and security audit logging.
    """
    client_ip = request.client.host if request.client else "unknown"

    # Query user by username
    user = db.execute(
        select(User).where(User.username == credentials.username)
    ).scalar_one_or_none()

    # Verify password (timing equalized via dummy hash if user is None)
    password_valid = verify_password(
        credentials.password,
        user.password_hash if user else None,
    )

    if not user or not password_valid:
        # Audit log failed attempt without recording password
        create_audit_log(
            db=db,
            action="LOGIN_FAILED",
            entity_type="USER",
            actor_user_id=user.id if user else None,
            entity_id=credentials.username,
            ip=client_ip,
            details={"reason": "Invalid credentials", "attempted_username": credentials.username},
        )
        # Uniform 401 error message regardless of whether username or password was wrong
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        create_audit_log(
            db=db,
            action="LOGIN_BLOCKED",
            entity_type="USER",
            actor_user_id=user.id,
            entity_id=str(user.id),
            ip=client_ip,
            details={"reason": "Account is deactivated"},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is deactivated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Issue access token
    token, jti, expire = create_access_token(
        data={"sub": str(user.id), "username": user.username, "role": user.role}
    )

    # Update last login timestamp
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()

    # Audit log success
    create_audit_log(
        db=db,
        action="LOGIN_SUCCESS",
        entity_type="USER",
        actor_user_id=user.id,
        entity_id=str(user.id),
        ip=client_ip,
    )

    expires_in_seconds = int((expire - datetime.now(timezone.utc)).total_seconds())
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=expires_in_seconds,
    )


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LogoutResponse:
    """
    Log out the current user by placing the JWT jti into the revoked_tokens deny-list.
    """
    client_ip = request.client.host if request.client else "unknown"
    jti = getattr(current_user, "_current_jti", None)
    exp_timestamp = getattr(current_user, "_current_exp", None)

    if jti and exp_timestamp:
        expires_at = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
        revoked_token = RevokedToken(
            jti=jti,
            user_id=current_user.id,
            expires_at=expires_at,
        )
        db.add(revoked_token)
        db.commit()

    create_audit_log(
        db=db,
        action="LOGOUT",
        entity_type="USER",
        actor_user_id=current_user.id,
        entity_id=str(current_user.id),
        ip=client_ip,
    )
    return LogoutResponse(message="Successfully logged out")


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Return the profile of the currently authenticated user."""
    return UserResponse.model_validate(current_user)

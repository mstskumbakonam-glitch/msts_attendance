"""
Security utilities: Argon2id password hashing and JWT token handling.
"""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from backend.app.core.config import get_settings

# Argon2id password hasher instance
_ph = PasswordHasher(
    time_cost=2,
    memory_cost=65536,
    parallelism=1,
    hash_len=32,
)

# Dummy hash computed once at import time to equalize verification timing for non-existent users
_DUMMY_HASH = _ph.hash("dummy_constant_time_precomputed_password_string")


def hash_password(password: str) -> str:
    """Hash a plaintext password using Argon2id."""
    return _ph.hash(password)


def verify_password(plain_password: str, hashed_password: Optional[str]) -> bool:
    """
    Verify a plaintext password against an Argon2id hash.
    If hashed_password is None, verifies against a dummy hash to prevent timing attacks.
    """
    target_hash = hashed_password if hashed_password is not None else _DUMMY_HASH
    try:
        return _ph.verify(target_hash, plain_password)
    except VerifyMismatchError:
        return False
    except Exception:
        return False


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> Tuple[str, uuid.UUID, datetime]:
    """
    Create a signed JWT access token with unique jti, exp, iat claims.
    Returns: (token_str, jti, expires_at)
    """
    settings = get_settings()
    to_encode = data.copy()

    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.jwt_expire_minutes)

    token_jti = uuid.uuid4()
    to_encode.update(
        {
            "jti": str(token_jti),
            "iat": int(now.timestamp()),
            "exp": int(expire.timestamp()),
        }
    )

    encoded_jwt = jwt.encode(
        to_encode,
        settings.token_secret,
        algorithm=settings.algorithm,
    )
    return encoded_jwt, token_jti, expire


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate a JWT access token.
    Enforces algorithm='HS256' and rejects 'none' or mismatched algorithms.
    Raises jwt.PyJWTError on invalid/expired tokens.
    """
    settings = get_settings()
    return jwt.decode(
        token,
        settings.token_secret,
        algorithms=[settings.algorithm],
        options={"require": ["exp", "iat", "jti", "sub"]},
    )

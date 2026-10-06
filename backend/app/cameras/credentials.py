"""
Secure RTSP credential resolution.
"""

import os
import re
from urllib.parse import quote, urlsplit, urlunsplit


_ENV_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def resolve_credentials(credentials_ref: str) -> tuple[str, str]:
    """Read username:password from environment or project .env settings."""
    if not credentials_ref:
        raise ValueError("credentials_ref is required")

    if not _ENV_NAME_RE.fullmatch(credentials_ref):
        raise ValueError("Invalid credentials_ref")

    raw = os.getenv(credentials_ref)

    if not raw:
        from backend.app.core.config import get_settings

        settings = get_settings()
        field_name = credentials_ref.lower()

        if hasattr(settings, field_name):
            raw = getattr(settings, field_name)

    if not raw:
        raise ValueError(
            f"Credentials environment variable '{credentials_ref}' is not set"
        )

    if ":" not in raw:
        raise ValueError(
            f"Credentials environment variable '{credentials_ref}' "
            "must contain username:password"
        )

    username, password = raw.split(":", 1)

    if not username or not password:
        raise ValueError(
            f"Credentials environment variable '{credentials_ref}' is incomplete"
        )

    return username, password


def reject_embedded_credentials(source_url: str) -> None:
    """Reject URLs containing embedded username/password."""
    parsed = urlsplit(source_url)

    if parsed.username is not None or parsed.password is not None:
        raise ValueError("RTSP URL must not contain embedded credentials")


def build_authenticated_url(source_url: str, credentials_ref: str) -> str:
    """Build authenticated RTSP URL in memory."""
    reject_embedded_credentials(source_url)

    parsed = urlsplit(source_url)

    if parsed.scheme.lower() != "rtsp":
        raise ValueError("RTSP source URL must use rtsp://")

    if not parsed.hostname:
        raise ValueError("RTSP source URL must contain a hostname")

    username, password = resolve_credentials(credentials_ref)

    host = parsed.hostname
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"

    netloc = f"{quote(username, safe='')}:{quote(password, safe='')}@{host}"

    if parsed.port is not None:
        netloc += f":{parsed.port}"

    return urlunsplit(
        (
            parsed.scheme,
            netloc,
            parsed.path,
            parsed.query,
            parsed.fragment,
        )
    )


def mask_url(url: str) -> str:
    """Return URL without credentials for safe logging."""
    parsed = urlsplit(url)

    if not parsed.hostname:
        return url

    host = parsed.hostname
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"

    netloc = host

    if parsed.port is not None:
        netloc += f":{parsed.port}"

    return urlunsplit(
        (
            parsed.scheme,
            netloc,
            parsed.path,
            parsed.query,
            parsed.fragment,
        )
    )
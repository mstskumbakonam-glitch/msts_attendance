"""
Audit logging service.
Records immutable security and operational audit trails in PostgreSQL audit_logs table.
"""
import logging
import uuid
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session

from backend.app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)

# Keys that must NEVER be saved in audit log details
BLOCKED_AUDIT_KEYS = frozenset(
    {
        "password",
        "password_hash",
        "token",
        "access_token",
        "authorization",
        "embedding",
        "secret_key",
    }
)


def _sanitize_details(details: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not details:
        return {}
    return {
        k: "[REDACTED]" if k.lower() in BLOCKED_AUDIT_KEYS else v
        for k, v in details.items()
    }


def create_audit_log(
    db: Session,
    action: str,
    entity_type: str,
    actor_user_id: Optional[uuid.UUID] = None,
    entity_id: Optional[str] = None,
    ip: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> AuditLog:
    """Insert an immutable audit log entry into the database."""
    sanitized = _sanitize_details(details)
    log_entry = AuditLog(
        actor_user_id=actor_user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        ip=ip,
        details=sanitized,
    )
    db.add(log_entry)
    try:
        db.commit()
        db.refresh(log_entry)
        return log_entry
    except Exception:
        db.rollback()
        logger.error("Failed to commit audit log entry for action %s", action, exc_info=True)
        raise

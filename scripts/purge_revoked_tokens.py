"""
Helper script to purge expired tokens from the revoked_tokens table.
Can be scheduled as a periodic cron job.
"""
from datetime import datetime, timezone
from sqlalchemy import delete

from backend.app.db.session import SessionLocal
from backend.app.models.revoked_token import RevokedToken


def purge_expired_tokens() -> int:
    """Delete all revoked tokens whose expires_at is in the past."""
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        stmt = delete(RevokedToken).where(RevokedToken.expires_at < now)
        result = db.execute(stmt)
        db.commit()
        count = result.rowcount
        print(f"Purged {count} expired revoked token(s).")
        return count
    finally:
        db.close()


if __name__ == "__main__":
    purge_expired_tokens()

"""
Rate limiting configuration using slowapi.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)


def reset_limiter() -> None:
    """Reset limiter storage for test isolation."""
    if hasattr(limiter, "_storage") and hasattr(limiter._storage, "reset"):
        limiter._storage.reset()
    # For in-memory storage, clear the internal dictionary
    storage = getattr(limiter, "_storage", None)
    if storage is None:
        return
    inner = getattr(storage, "storage", None)
    if isinstance(inner, dict):
        inner.clear()

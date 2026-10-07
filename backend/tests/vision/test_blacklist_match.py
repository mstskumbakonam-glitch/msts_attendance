"""Blacklist identity decision tests."""
import uuid

from backend.app.vision.recognizer import IdentityCandidate, IdentityKind, resolve_identity


def test_blacklist_wins_tie():
    student = IdentityCandidate(IdentityKind.STUDENT, 0.80, student_id=uuid.uuid4())
    blacklist = IdentityCandidate(IdentityKind.BLACKLISTED, 0.80, blacklist_id=uuid.uuid4())
    result = resolve_identity(student, blacklist, threshold=0.45)
    assert result.kind == IdentityKind.BLACKLISTED


def test_higher_similarity_wins():
    student = IdentityCandidate(IdentityKind.STUDENT, 0.91, student_id=uuid.uuid4())
    blacklist = IdentityCandidate(IdentityKind.BLACKLISTED, 0.72, blacklist_id=uuid.uuid4())
    result = resolve_identity(student, blacklist, threshold=0.45)
    assert result.kind == IdentityKind.STUDENT


def test_blacklist_wins_when_higher():
    student = IdentityCandidate(IdentityKind.STUDENT, 0.73, student_id=uuid.uuid4())
    blacklist = IdentityCandidate(IdentityKind.BLACKLISTED, 0.88, blacklist_id=uuid.uuid4())
    result = resolve_identity(student, blacklist, threshold=0.45)
    assert result.kind == IdentityKind.BLACKLISTED


def test_below_threshold_is_unknown():
    blacklist = IdentityCandidate(IdentityKind.BLACKLISTED, 0.30, blacklist_id=uuid.uuid4())
    result = resolve_identity(None, blacklist, threshold=0.45)
    assert result.kind == IdentityKind.UNKNOWN

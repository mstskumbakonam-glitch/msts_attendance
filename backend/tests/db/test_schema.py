"""
Database Schema and Constraint Tests
Tests all business constraints, vector indexes, and partial unique indexes.
"""
from datetime import date, datetime, timezone
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, DBAPIError

from backend.app.models.student import Student
from backend.app.models.blacklist import BlacklistEntry
from backend.app.models.camera import Camera
from backend.app.models.attendance import AttendanceRecord
from backend.app.models.face_embedding import FaceEmbedding
from backend.app.models.security_alert import SecurityAlert
from backend.app.models.system_setting import SystemSetting


def test_student_unique_id(db_session):
    """Insert student; duplicate student_id -> IntegrityError."""
    s1 = Student(
        student_id="STU001",
        name="Alice Smith",
        department="Computer Science",
        year=2,
    )
    db_session.add(s1)
    db_session.flush()

    s2 = Student(
        student_id="STU001",
        name="Alice Duplicate",
        department="Computer Science",
        year=2,
    )
    db_session.add(s2)
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_attendance_unique_per_session(db_session):
    """
    Insert two attendance_records with same (student, date, session) -> IntegrityError;
    different session -> OK.
    """
    cam = Camera(
        name="Main Entrance Cam",
        location="Gate 1",
        source_type="WEBCAM",
    )
    db_session.add(cam)
    student = Student(
        student_id="STU002",
        name="Bob Jones",
        department="Electrical",
        year=3,
    )
    db_session.add(student)
    db_session.flush()

    today = date(2026, 10, 2)
    att1 = AttendanceRecord(
        student_id=student.id,
        camera_id=cam.id,
        attendance_date=today,
        session_label="MORNING",
        similarity=0.92,
    )
    db_session.add(att1)
    db_session.flush()

    # Same student, date, and session -> IntegrityError
    att_dup = AttendanceRecord(
        student_id=student.id,
        camera_id=cam.id,
        attendance_date=today,
        session_label="MORNING",
        similarity=0.95,
    )
    db_session.add(att_dup)
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()

    # Different session -> OK
    # Re-add cam & student since transaction was rolled back
    cam2 = Camera(name="Main Entrance Cam 2", location="Gate 1", source_type="WEBCAM")
    student2 = Student(student_id="STU002B", name="Bob Jones", department="Electrical", year=3)
    db_session.add_all([cam2, student2])
    db_session.flush()

    att_morning = AttendanceRecord(
        student_id=student2.id,
        camera_id=cam2.id,
        attendance_date=today,
        session_label="MORNING",
        similarity=0.92,
    )
    att_afternoon = AttendanceRecord(
        student_id=student2.id,
        camera_id=cam2.id,
        attendance_date=today,
        session_label="AFTERNOON",
        similarity=0.88,
    )
    db_session.add_all([att_morning, att_afternoon])
    db_session.flush()
    assert att_morning.id is not None
    assert att_afternoon.id is not None


def test_face_embeddings_owner_check(db_session):
    """
    face_embeddings with both owners NULL or both set -> CHECK violation.
    Exactly one owner (student_id OR blacklist_entry_id) is allowed.
    """
    student = Student(student_id="STU003", name="Charlie", department="Civil", year=1)
    bl = BlacklistEntry(full_name="Banned Person", reason="Trespassing")
    db_session.add_all([student, bl])
    db_session.flush()

    zero_vector = [0.0] * 512

    # Case 1: Both owners NULL -> CHECK violation
    emb_no_owner = FaceEmbedding(
        student_id=None,
        blacklist_entry_id=None,
        embedding=zero_vector,
    )
    db_session.add(emb_no_owner)
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()

    # Re-add student and bl after rollback
    student = Student(student_id="STU003", name="Charlie", department="Civil", year=1)
    bl = BlacklistEntry(full_name="Banned Person", reason="Trespassing")
    db_session.add_all([student, bl])
    db_session.flush()

    # Case 2: Both owners set -> CHECK violation
    emb_both_owners = FaceEmbedding(
        student_id=student.id,
        blacklist_entry_id=bl.id,
        embedding=zero_vector,
    )
    db_session.add(emb_both_owners)
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()

    # Case 3: Exactly one owner -> OK
    student = Student(student_id="STU003", name="Charlie", department="Civil", year=1)
    db_session.add(student)
    db_session.flush()

    emb_valid = FaceEmbedding(
        student_id=student.id,
        blacklist_entry_id=None,
        embedding=zero_vector,
    )
    db_session.add(emb_valid)
    db_session.flush()
    assert emb_valid.id is not None


def test_vector_nearest_neighbor(db_session):
    """
    Insert 3 embeddings; nearest-neighbour query ORDER BY embedding <=> :q LIMIT 1
    returns the closest vector.
    """
    s1 = Student(student_id="VEC01", name="Target Person", department="CS", year=1)
    s2 = Student(student_id="VEC02", name="Far Person 1", department="CS", year=1)
    s3 = Student(student_id="VEC03", name="Far Person 2", department="CS", year=1)
    db_session.add_all([s1, s2, s3])
    db_session.flush()

    # Create 3 distinct 512-d vectors
    v_target = [1.0] + [0.0] * 511
    v_far1 = [0.0, 1.0] + [0.0] * 510
    v_far2 = [0.0, 0.0, 1.0] + [0.0] * 509

    e1 = FaceEmbedding(student_id=s1.id, embedding=v_target, sample_label="target")
    e2 = FaceEmbedding(student_id=s2.id, embedding=v_far1, sample_label="far1")
    e3 = FaceEmbedding(student_id=s3.id, embedding=v_far2, sample_label="far2")
    db_session.add_all([e1, e2, e3])
    db_session.flush()

    # Query with vector very close to target: [0.99, 0.01, 0, ...]
    query_vec = [0.99, 0.01] + [0.0] * 510

    # Using pgvector cosine distance operator <=>
    stmt = (
        select(FaceEmbedding)
        .order_by(FaceEmbedding.embedding.cosine_distance(query_vec))
        .limit(1)
    )
    closest = db_session.execute(stmt).scalar_one()
    assert closest.student_id == s1.id
    assert closest.sample_label == "target"


def test_security_alerts_partial_unique_dedup(db_session):
    """
    Partial unique alert key: two open (status != 'RESOLVED') alerts with same dedup_key -> IntegrityError;
    after alert is RESOLVED, a new alert with the same dedup_key is allowed.
    """
    cam = Camera(name="Alert Cam", location="Hallway B", source_type="WEBCAM")
    db_session.add(cam)
    db_session.flush()

    now = datetime.now(timezone.utc)
    dedup = "CAM01_UNKNOWN_20261002"

    alert1 = SecurityAlert(
        alert_type="UNKNOWN_PERSON",
        severity="MEDIUM",
        status="NEW",
        camera_id=cam.id,
        dedup_key=dedup,
        first_seen_at=now,
        last_seen_at=now,
    )
    db_session.add(alert1)
    db_session.flush()

    # Attempt second open alert with same dedup_key -> IntegrityError
    alert2 = SecurityAlert(
        alert_type="UNKNOWN_PERSON",
        severity="HIGH",
        status="NEW",
        camera_id=cam.id,
        dedup_key=dedup,
        first_seen_at=now,
        last_seen_at=now,
    )
    db_session.add(alert2)
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()

    # Recreate cam & alert1 and mark alert1 as RESOLVED
    cam = Camera(name="Alert Cam 2", location="Hallway B", source_type="WEBCAM")
    db_session.add(cam)
    db_session.flush()

    alert1 = SecurityAlert(
        alert_type="UNKNOWN_PERSON",
        severity="MEDIUM",
        status="RESOLVED",
        camera_id=cam.id,
        dedup_key=dedup,
        first_seen_at=now,
        last_seen_at=now,
        resolution_note="Resolved by admin",
    )
    db_session.add(alert1)
    db_session.flush()

    # Now a NEW alert with the same dedup_key is allowed because status <> 'RESOLVED' partial index applies!
    alert_new = SecurityAlert(
        alert_type="UNKNOWN_PERSON",
        severity="HIGH",
        status="NEW",
        camera_id=cam.id,
        dedup_key=dedup,
        first_seen_at=now,
        last_seen_at=now,
    )
    db_session.add(alert_new)
    db_session.flush()
    assert alert_new.id is not None


def test_vector_wrong_dimension_rejected(db_session):
    """Vector of wrong dimension (e.g. 128 instead of 512) is rejected by PostgreSQL/pgvector ORM."""
    student = Student(student_id="VEC_DIM", name="Dim Test", department="CS", year=1)
    db_session.add(student)
    db_session.flush()

    # 128 dimensions instead of 512
    wrong_dim_vec = [1.0] * 128
    emb_wrong = FaceEmbedding(
        student_id=student.id,
        embedding=wrong_dim_vec,
    )
    db_session.add(emb_wrong)
    # pgvector raises ValueError -> wrapped in StatementError by SQLAlchemy
    from sqlalchemy.exc import StatementError
    with pytest.raises((IntegrityError, DBAPIError, StatementError)):
        db_session.flush()


def test_all_tables_exist_and_system_setting(db_session):
    """Verify system_settings and overall schema queryability."""
    setting = SystemSetting(
        key="recognition_threshold",
        value={"threshold": 0.45, "model": "buffalo_l"},
    )
    db_session.add(setting)
    db_session.flush()

    fetched = db_session.get(SystemSetting, "recognition_threshold")
    assert fetched is not None
    assert fetched.value["threshold"] == 0.45

"""initial schema

Revision ID: 0001_initial
Revises: 
Create Date: 2026-10-02 18:42:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import pgvector

# revision identifiers, used by Alembic.
revision: str = '0001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Ensure vector extension exists
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # 1. cameras table
    op.create_table(
        'cameras',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('name', sa.String(length=80), nullable=False),
        sa.Column('location', sa.String(length=160), nullable=False),
        sa.Column('source_type', sa.String(length=16), nullable=False),
        sa.Column('source_url', sa.Text(), nullable=True),
        sa.Column('credentials_ref', sa.String(length=64), nullable=True),
        sa.Column('enabled', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('status', sa.String(length=16), server_default=sa.text("'UNKNOWN'"), nullable=False),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("source_type IN ('WEBCAM', 'VIDEO_FILE', 'RTSP')", name='chk_cameras_source_type'),
        sa.CheckConstraint("status IN ('UNKNOWN', 'ONLINE', 'OFFLINE', 'ERROR', 'DISABLED')", name='chk_cameras_status'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )

    # 2. users table
    op.create_table(
        'users',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('username', sa.String(length=64), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('password_hash', sa.Text(), nullable=False),
        sa.Column('role', sa.String(length=16), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("role IN ('ADMIN', 'OPERATOR')", name='chk_users_role'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('username')
    )

    # 3. audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column('occurred_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('actor_user_id', sa.UUID(), nullable=True),
        sa.Column('action', sa.String(length=48), nullable=False),
        sa.Column('entity_type', sa.String(length=32), nullable=False),
        sa.Column('entity_id', sa.String(length=64), nullable=True),
        sa.Column('ip', sa.String(length=45), nullable=True),
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.ForeignKeyConstraint(['actor_user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_audit_actor', 'audit_logs', ['actor_user_id', sa.text('occurred_at DESC')], unique=False)
    op.create_index('idx_audit_occurred', 'audit_logs', [sa.text('occurred_at DESC')], unique=False)

    # 4. blacklist_entries table
    op.create_table(
        'blacklist_entries',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('full_name', sa.String(length=120), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('category', sa.String(length=40), nullable=True),
        sa.Column('severity', sa.String(length=16), server_default=sa.text("'HIGH'"), nullable=False),
        sa.Column('status', sa.String(length=16), server_default=sa.text("'ACTIVE'"), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deactivated_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("severity IN ('HIGH', 'CRITICAL')", name='chk_blacklist_severity'),
        sa.CheckConstraint("status IN ('ACTIVE', 'INACTIVE')", name='chk_blacklist_status'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_blacklist_name', 'blacklist_entries', [sa.text('lower(full_name)')], unique=False)
    op.create_index('idx_blacklist_status', 'blacklist_entries', ['status'], unique=False)

    # 5. revoked_tokens table
    op.create_table(
        'revoked_tokens',
        sa.Column('jti', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('jti')
    )
    op.create_index('idx_revoked_tokens_expires', 'revoked_tokens', ['expires_at'], unique=False)

    # 6. students table
    op.create_table(
        'students',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('student_id', sa.String(length=32), nullable=False),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('department', sa.String(length=80), nullable=False),
        sa.Column('year', sa.SmallInteger(), nullable=False),
        sa.Column('status', sa.String(length=16), server_default=sa.text("'ACTIVE'"), nullable=False),
        sa.Column('consent_given_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('consent_version', sa.String(length=16), nullable=True),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("status IN ('ACTIVE', 'INACTIVE')", name='chk_students_status'),
        sa.CheckConstraint('year BETWEEN 1 AND 8', name='chk_students_year'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('student_id')
    )
    op.create_index('idx_students_dept_year', 'students', ['department', 'year'], unique=False)
    op.create_index('idx_students_name', 'students', [sa.text('lower(name)')], unique=False)
    op.create_index('idx_students_status', 'students', ['status'], unique=False)

    # 7. system_settings table
    op.create_table(
        'system_settings',
        sa.Column('key', sa.String(length=64), nullable=False),
        sa.Column('value', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('updated_by', sa.UUID(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('key')
    )

    # 8. attendance_records table
    op.create_table(
        'attendance_records',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('student_id', sa.UUID(), nullable=False),
        sa.Column('camera_id', sa.UUID(), nullable=False),
        sa.Column('attendance_date', sa.Date(), nullable=False),
        sa.Column('session_label', sa.String(length=32), server_default=sa.text("'DEFAULT'"), nullable=False),
        sa.Column('marked_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('status', sa.String(length=12), server_default=sa.text("'PRESENT'"), nullable=False),
        sa.Column('similarity', sa.Float(), nullable=False),
        sa.Column('method', sa.String(length=8), server_default=sa.text("'AUTO'"), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("method IN ('AUTO', 'MANUAL')", name='chk_attendance_method'),
        sa.CheckConstraint("status IN ('PRESENT', 'LATE')", name='chk_attendance_status'),
        sa.ForeignKeyConstraint(['camera_id'], ['cameras.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['student_id'], ['students.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('student_id', 'attendance_date', 'session_label', name='uq_attendance_student_date_session')
    )
    op.create_index('idx_attendance_camera', 'attendance_records', ['camera_id'], unique=False)
    op.create_index('idx_attendance_date', 'attendance_records', ['attendance_date'], unique=False)
    op.create_index('idx_attendance_student_date', 'attendance_records', ['student_id', sa.text('attendance_date DESC')], unique=False)

    # 9. detection_events table
    op.create_table(
        'detection_events',
        sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('camera_id', sa.UUID(), nullable=False),
        sa.Column('event_type', sa.String(length=12), nullable=False),
        sa.Column('student_id', sa.UUID(), nullable=True),
        sa.Column('blacklist_entry_id', sa.UUID(), nullable=True),
        sa.Column('similarity', sa.Float(), nullable=True),
        sa.Column('bbox', postgresql.ARRAY(sa.SmallInteger()), nullable=True),
        sa.Column('track_id', sa.String(length=40), nullable=True),
        sa.Column('snapshot_path', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("event_type IN ('RECOGNIZED', 'UNKNOWN', 'BLACKLISTED')", name='chk_detection_events_type'),
        sa.ForeignKeyConstraint(['blacklist_entry_id'], ['blacklist_entries.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['camera_id'], ['cameras.id'], ),
        sa.ForeignKeyConstraint(['student_id'], ['students.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_events_camera_occurred', 'detection_events', ['camera_id', sa.text('occurred_at DESC')], unique=False)
    op.create_index('idx_events_occurred', 'detection_events', [sa.text('occurred_at DESC')], unique=False)
    op.create_index('idx_events_student_occurred', 'detection_events', ['student_id', sa.text('occurred_at DESC')], unique=False)
    op.create_index('idx_events_type_occurred', 'detection_events', ['event_type', sa.text('occurred_at DESC')], unique=False)

    # 10. face_embeddings table
    op.create_table(
        'face_embeddings',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('student_id', sa.UUID(), nullable=True),
        sa.Column('blacklist_entry_id', sa.UUID(), nullable=True),
        sa.Column('embedding', pgvector.sqlalchemy.vector.VECTOR(dim=512), nullable=False),
        sa.Column('model_name', sa.String(length=40), server_default=sa.text("'buffalo_l'"), nullable=False),
        sa.Column('model_version', sa.String(length=40), server_default=sa.text("'w600k_r50'"), nullable=False),
        sa.Column('quality_score', sa.Float(), nullable=True),
        sa.Column('sample_label', sa.String(length=24), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('((student_id IS NOT NULL)::int + (blacklist_entry_id IS NOT NULL)::int) = 1', name='chk_face_embeddings_owner'),
        sa.ForeignKeyConstraint(['blacklist_entry_id'], ['blacklist_entries.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['student_id'], ['students.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_face_embeddings_blacklist', 'face_embeddings', ['blacklist_entry_id'], unique=False)
    op.create_index('idx_face_embeddings_hnsw', 'face_embeddings', ['embedding'], unique=False, postgresql_using='hnsw', postgresql_with={'m': 16, 'ef_construction': 64}, postgresql_ops={'embedding': 'vector_cosine_ops'})
    op.create_index('idx_face_embeddings_is_active', 'face_embeddings', ['is_active'], unique=False)
    op.create_index('idx_face_embeddings_student', 'face_embeddings', ['student_id'], unique=False)

    # 11. security_alerts table
    op.create_table(
        'security_alerts',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('alert_type', sa.String(length=24), nullable=False),
        sa.Column('severity', sa.String(length=10), nullable=False),
        sa.Column('status', sa.String(length=14), server_default=sa.text("'NEW'"), nullable=False),
        sa.Column('camera_id', sa.UUID(), nullable=False),
        sa.Column('blacklist_entry_id', sa.UUID(), nullable=True),
        sa.Column('student_id', sa.UUID(), nullable=True),
        sa.Column('dedup_key', sa.String(length=128), nullable=False),
        sa.Column('first_seen_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('occurrence_count', sa.Integer(), server_default=sa.text('1'), nullable=False),
        sa.Column('max_similarity', sa.Float(), nullable=True),
        sa.Column('acknowledged_by', sa.UUID(), nullable=True),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_by', sa.UUID(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolution_note', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("alert_type IN ('UNKNOWN_PERSON', 'BLACKLISTED_PERSON', 'CAMERA_OFFLINE')", name='chk_alerts_type'),
        sa.CheckConstraint("severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')", name='chk_alerts_severity'),
        sa.CheckConstraint("status IN ('NEW', 'ACKNOWLEDGED', 'RESOLVED')", name='chk_alerts_status'),
        sa.ForeignKeyConstraint(['acknowledged_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['blacklist_entry_id'], ['blacklist_entries.id'], ),
        sa.ForeignKeyConstraint(['camera_id'], ['cameras.id'], ),
        sa.ForeignKeyConstraint(['resolved_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['student_id'], ['students.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_alerts_camera_created', 'security_alerts', ['camera_id', sa.text('created_at DESC')], unique=False)
    op.create_index('idx_alerts_status_severity', 'security_alerts', ['status', 'severity', sa.text('last_seen_at DESC')], unique=False)
    op.create_index('idx_alerts_unresolved_dedup', 'security_alerts', ['dedup_key'], unique=True, postgresql_where=sa.text("status <> 'RESOLVED'"))


def downgrade() -> None:
    op.drop_index('idx_alerts_unresolved_dedup', table_name='security_alerts', postgresql_where=sa.text("status <> 'RESOLVED'"))
    op.drop_index('idx_alerts_status_severity', table_name='security_alerts')
    op.drop_index('idx_alerts_camera_created', table_name='security_alerts')
    op.drop_table('security_alerts')

    op.drop_index('idx_face_embeddings_student', table_name='face_embeddings')
    op.drop_index('idx_face_embeddings_is_active', table_name='face_embeddings')
    op.drop_index('idx_face_embeddings_hnsw', table_name='face_embeddings', postgresql_using='hnsw', postgresql_with={'m': 16, 'ef_construction': 64}, postgresql_ops={'embedding': 'vector_cosine_ops'})
    op.drop_index('idx_face_embeddings_blacklist', table_name='face_embeddings')
    op.drop_table('face_embeddings')

    op.drop_index('idx_events_type_occurred', table_name='detection_events')
    op.drop_index('idx_events_student_occurred', table_name='detection_events')
    op.drop_index('idx_events_occurred', table_name='detection_events')
    op.drop_index('idx_events_camera_occurred', table_name='detection_events')
    op.drop_table('detection_events')

    op.drop_index('idx_attendance_student_date', table_name='attendance_records')
    op.drop_index('idx_attendance_date', table_name='attendance_records')
    op.drop_index('idx_attendance_camera', table_name='attendance_records')
    op.drop_table('attendance_records')

    op.drop_table('system_settings')

    op.drop_index('idx_students_status', table_name='students')
    op.drop_index('idx_students_name', table_name='students')
    op.drop_index('idx_students_dept_year', table_name='students')
    op.drop_table('students')

    op.drop_index('idx_revoked_tokens_expires', table_name='revoked_tokens')
    op.drop_table('revoked_tokens')

    op.drop_index('idx_blacklist_status', table_name='blacklist_entries')
    op.drop_index('idx_blacklist_name', table_name='blacklist_entries')
    op.drop_table('blacklist_entries')

    op.drop_index('idx_audit_occurred', table_name='audit_logs')
    op.drop_index('idx_audit_actor', table_name='audit_logs')
    op.drop_table('audit_logs')

    op.drop_table('users')
    op.drop_table('cameras')

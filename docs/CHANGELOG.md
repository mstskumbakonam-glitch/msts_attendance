# CHANGELOG

## [Phase 1] - 2026-10-02
### Added
- Completed Phase 1 Architecture Finalization.
- Created repository architecture blueprints in `docs/architecture/`:
  - `ARCHITECTURE.md`: High-level system context, modular monolith structure, process model, and risk mitigations.
  - `DECISIONS.md`: Formal ADRs (ADR-01 through ADR-15).
  - `DATABASE.md`: PostgreSQL 16 + pgvector schema, table specifications, indices, constraints, and Mermaid ER diagram.
  - `API.md`: Comprehensive REST API catalog (/api/v1) covering health, auth, users, students, face registration, recognition, attendance, cameras, alerts, blacklist, tracking, and reports.
  - `AI_PIPELINE.md`: Shared AI Vision Engine design (InsightFace SCRFD + ArcFace `buffalo_l`), landmark alignment, quality filtering, temporal confirmation, and threshold calibration.
  - `FRONTEND.md`: Streamlit multi-page UI dashboard layout, JWT session state management, API client architecture, and visual bounding box conventions.
  - `DATA_FLOW.md`: End-to-end Mermaid sequence diagrams for frame processing, attendance marking, unknown person detection, blacklist alerts, and movement tracking.
  - `MODULE_BOUNDARIES.md`: Package layout, strict import dependency rules, and boundary enforcement guidelines.
- Updated `README.md` to link all 8 architecture blueprints.

## [Phase 2] - 2026-10-02
### Added
- Python 3.11 virtual environment configuration and CPU dependencies.
- Environment verification script `scripts/check_env.py`.
- Windows setup guide `docs/SETUP_WINDOWS.md`.

## [Phase 3] - 2026-10-02
### Added
- Docker infrastructure setup: PostgreSQL 16 + pgvector container and Redis profile.
- Extension initialization SQL `docker/postgres/init/01-extensions.sql`.

## [Phase 4] - 2026-10-02
### Added
- 11 SQLAlchemy 2.0 models with Mapped typing and constraints.
- Initial Alembic migration `0001_initial.py` with HNSW vector index and partial unique index.
- Comprehensive database schema test suite `backend/tests/db/test_schema.py` (7 tests).

## [Phase 6] - 2026-10-03
### Added
- Argon2id password hashing and constant-time dummy verification for non-existent users in `backend/app/core/security.py`.
- JWT creation and validation with unique `jti`, expiration, algorithm pinning, and denylist checking.
- Rate limiting via slowapi (`5/minute` on `/auth/login`).
- Audit logging for login attempts (success and failure) via `backend/app/services/audit_service.py`.
- Auth endpoints: `POST /api/v1/auth/login`, `POST /api/v1/auth/logout`, and `GET /api/v1/auth/me`.
- RBAC dependencies with `require_role("ADMIN", "OPERATOR")`.
- Automated test suites: `backend/tests/api/test_auth.py` and `backend/tests/api/test_rbac.py`.

## [Phase 7] - 2026-10-03
### Added
- Student Pydantic schemas (`StudentCreate`, `StudentUpdate`, `StudentResponse`, `StudentListResponse`) in `backend/app/schemas/student.py`.
- Student repository `StudentRepository` in `backend/app/db/repositories/student_repo.py`.
- Student business service `StudentService` with audit logging in `backend/app/services/student_service.py`.
- Student REST API endpoints (`POST/GET /api/v1/students`, `GET/PATCH/DELETE /api/v1/students/{id}`) with RBAC enforcement in `backend/app/api/v1/students.py`.
- Streamlit unified dashboard shell (`frontend/app.py`), login gate component (`frontend/components/auth.py`), and API client (`frontend/api_client.py`).
- Frontend login gate test in `frontend/tests/test_login_gate.py`.
- Student management API test suite `backend/tests/api/test_students.py` (7 tests).

## [Phase 8] - 2026-10-03
### Added
- `CameraSource` abstract base class in `backend/app/cameras/source.py`.
- `WebcamSource` with OpenCV VideoCapture and Windows `CAP_DSHOW` support in `backend/app/cameras/webcam.py`.
- `RegistrationSessionManager` managing in-memory sessions with TTL and camera exclusivity in `backend/app/services/registration_session.py`.
- Stream preview endpoints with short-lived tickets in `backend/app/api/v1/stream.py`.
- Face registration session endpoints (`POST/DELETE /students/{id}/face/session`, `POST .../capture`, `GET .../status`, `DELETE .../face`) in `backend/app/api/v1/face.py`.
- Guided webcam enrollment UI in Streamlit `frontend/app.py` with live MJPEG preview, pose prompts, and progress bar.
- Test suites: `backend/tests/cameras/test_webcam_mock.py` (3 tests) and `backend/tests/api/test_face_session.py` (5 tests).


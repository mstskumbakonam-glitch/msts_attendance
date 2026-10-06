# SMART ATTENDANCE AND SECURITY MANAGEMENT SYSTEM
## AI-Based Face Recognition, Automated Attendance and Campus Security Monitoring
### Google Antigravity — MASTER IMPLEMENTATION PLAYBOOK

> **Repository:** `Aradhya6/smart-attendance-security-system` (private) · **Dev machine:** Windows + PowerShell · **Python:** 3.11 (`.python-version`) · **Mode:** CPU-first, laptop-webcam-first
> **This file is an instruction manual for an AI coding agent. It contains no application code.**

---

## 0. HOW TO USE THIS PLAYBOOK

1. Save this file in your repo as `docs/PLAYBOOK.md` (so Antigravity can read it from the workspace). Commit it on a `docs/` branch.
2. Open the repo in Antigravity. Paste the **Global Instructions block (Section 2)** into Antigravity's workspace/global *Rules* (or paste it at the start of every new agent session).
3. Go to **Phase 0**. Copy the block under **"EXACT ANTIGRAVITY PROMPT"** into Antigravity. Let it work.
4. Run the **Commands**, **Tests** and **Manual Verification** yourself. Never trust "it works" without seeing it.
5. Tick the **Acceptance Criteria**. If anything fails, paste the failure back to Antigravity and tell it to fix only that failure.
6. Do the **HUMAN APPROVAL** check, then the **Git Checkpoint**, then move to the next phase.
7. Never skip a phase. Phases **0, 1 and 19 are hard human gates**; every other phase also ends in a stop.

**Phase map (39 phases):**

| Block | Phases | Result |
|---|---|---|
| Foundation | 0–7 | Audit, architecture, environment, Docker DB, schema, API, auth, students |
| Face pipeline | 8–13 | Capture, preprocessing, detection, embeddings, pgvector, recognition |
| **Attendance MVP** | 14–19 | Live webcam recognition → attendance → dashboard → unknown → test → **human gate** |
| Camera sources | 20–22 | Video file, RTSP, camera management |
| Security module | 23–27 | Event layer, blacklist, alerts, security dashboard, tracking |
| Scale & quality | 28–35 | Multi-camera, Redis, reports, performance, security, privacy, tests, E2E |
| Delivery | 36–38 | Full Docker, documentation, final demo |

---

## 1. PROJECT SUMMARY AND NON-NEGOTIABLES

**One application, two modules, one engine.** Attendance and Security are two *consumers* of a single shared AI Vision Engine. They never duplicate detection, embedding, or recognition code.

```
CAMERA → FRAME → FACE DETECTION → PREPROCESS/ALIGN → EMBEDDING → VECTOR SEARCH (pgvector)
      → IDENTITY DECISION ─┬─ KNOWN (normal)  → Attendance + Detection Event (movement)
                           ├─ UNKNOWN         → Detection Event + configurable Security Alert
                           └─ BLACKLISTED     → Detection Event + HIGH/CRITICAL Security Alert
```

**Non-negotiables (apply to every phase):**

- Modular **monolith**. No microservices, Kubernetes, Kafka, or extra databases.
- **CPU first** (`DEVICE=cpu`, `onnxruntime` CPU). GPU is optional and last.
- Recognition model loaded **once** (singleton), never per frame.
- "similarity" is a cosine similarity score, **never called "accuracy"**.
- Unknown ≠ malicious. Label it `UNKNOWN`, alert per configurable policy.
- No fabricated metrics. ≥90 % accuracy and <5 s per student (from the project PPT) are **targets to be measured**, never claimed.
- No biometric images, datasets, CCTV recordings, model weights, secrets or `.env` in Git — ever.
- Laptop webcam MVP must work **before** any CCTV/RTSP work begins.

**Project PPT alignment:** MTCNN/YOLOv8 + FaceNet/ArcFace appear in the PPT as options. This playbook deliberately picks **one** path: **InsightFace (SCRFD detector + ArcFace `w600k_r50` recognizer via the `buffalo_l` pack) + cosine similarity in pgvector**. This is a valid reading of "InsightFace (ArcFace)" in the methodology slide.

---

## 2. ANTIGRAVITY GLOBAL INSTRUCTIONS (copy-paste block)

```text
=== GLOBAL RULES FOR ANTIGRAVITY — SMART ATTENDANCE & SECURITY SYSTEM ===
You are building ONE application (modular monolith) with two modules (Attendance, Security)
sharing ONE AI Vision Engine. Follow docs/PLAYBOOK.md. Work on ONE phase at a time.

PROCESS
 1. Read the current phase completely before touching anything.
 2. Inspect the existing repository first (tree, README, docs/, configs, git log).
 3. Never assume a file does not exist. Search first.
 4. Never duplicate existing functionality; extend it.
 5. Never silently change architecture. If a major decision is needed -> STOP and ask the human.
 6. Never delete unrelated files. Never overwrite teammate work. Never force push.
 7. Keep changes focused on the current phase only. No "while I'm here" refactors.
 8. Make the smallest compatible change when something is ambiguous (inspect code, README,
    docs, config first).
 9. Update documentation whenever behavior/architecture changes.
10. Run tests after implementation. Fix failures before declaring done.
11. STOP at the phase gate and report. Do not start the next phase.

HONESTY
12. Never fabricate test results, recognition accuracy, performance numbers or API responses.
13. Never claim a feature works unless you ran it and can show the command + real output.
14. If you could not run something (no camera, no Docker, no RTSP source), say "NOT VERIFIED"
    and explain why. Do not mark the acceptance criterion as passed.

SECURITY / PRIVACY
15. Never commit: .env, credentials, passwords, API keys, face images, biometric datasets,
    CCTV recordings, model weights (*.onnx, ~/.insightface), caches, virtual environments.
16. Never log or return: passwords, tokens, raw embeddings, raw images, stack traces to clients.
17. All secrets come from environment variables. Provide placeholders only in .env.example.
18. Use parameterised queries / ORM only. Validate all input. Protect against path traversal.

TECH CHOICES (fixed unless the human approves a change)
 Python 3.11 · FastAPI · SQLAlchemy 2.x + Alembic · PostgreSQL 16 + pgvector (HNSW, cosine)
 OpenCV · InsightFace buffalo_l (SCRFD + ArcFace) on onnxruntime CPU · Streamlit dashboard
 Redis only from Phase 29 · Windows PowerShell commands (label Linux/macOS separately).

GIT
 Branch from main per phase (feature/<name>). Commit with a clear message after tests pass.
 Push the feature branch. Never commit to main. Never force push.

REPORT FORMAT AT END OF EVERY PHASE
 - Files created / modified (list)
 - Commands run + real output summary
 - Tests: passed/failed counts (real)
 - Acceptance criteria: each ✅ / ❌ / NOT VERIFIED
 - Known issues / deviations from the playbook
 - Git branch + commit hash
 - "STOPPED AT PHASE GATE — awaiting human approval"
=== END GLOBAL RULES ===
```

---

## 3. ARCHITECTURE DECISIONS (ADR SUMMARY)

Antigravity must record these in `docs/architecture/DECISIONS.md` in Phase 1 and must not change them without human approval.

| # | Decision | Choice | Reason | Revisit when |
|---|---|---|---|---|
| ADR-01 | Style | Modular monolith (`backend/` + `frontend/`) | Simple, demonstrable, college scope | Never for this project |
| ADR-02 | Detector + recognizer | InsightFace `buffalo_l` (SCRFD det + ArcFace R50 512-d) | One library, strong accuracy on CPU, handles alignment | Measured latency too high → try `buffalo_s` |
| ADR-03 | Vector store | PostgreSQL 16 + pgvector, `vector(512)`, HNSW `vector_cosine_ops`, similarity = `1 - (a <=> b)` | One DB for everything | >100k embeddings |
| ADR-04 | Backend | FastAPI + SQLAlchemy 2 + Alembic + Pydantic v2 | Typed, testable, OpenAPI docs | — |
| ADR-05 | Frontend | **Streamlit** multi-page app (sidebar matches required navigation). Live video = MJPEG stream from FastAPI shown via `<img>` | Fastest path to a unified dashboard | If UX needs exceed Streamlit → React (needs approval) |
| ADR-06 | Camera access | **Server-side** OpenCV capture in a worker thread (laptop = server in MVP) | Browser webcam → server adds latency/complexity | — |
| ADR-07 | Auth | Argon2id password hashing, JWT access token (short expiry), `jti` denylist for logout, roles `ADMIN`/`OPERATOR` | Secure, simple | Add refresh tokens only if needed |
| ADR-08 | Attendance dedup | DB `UNIQUE(student_id, attendance_date, session_label)` + `INSERT … ON CONFLICT DO NOTHING` + in-memory cooldown | DB is the source of truth; cooldown reduces DB load | Lectures/periods needed → real sessions table |
| ADR-09 | Movement history | **No separate `movement_history` table.** Derived from `detection_events` by query | Avoids duplicated data; single source | Measured slow → materialized view |
| ADR-10 | Redis | Not before Phase 29. Used only for pub/sub bridge, alert-dedup TTL keys, camera heartbeat, stream tickets | Avoid needless infra | — |
| ADR-11 | Raw images | Not persisted by default (`RETAIN_RAW_IMAGES=false`). Registration frames live in memory with TTL | Data minimization | Human approves snapshots |
| ADR-12 | Identity search scope | One search over active student **and** active blacklist embeddings; top-1 decides owner type | Single pass, no duplicated logic | — |
| ADR-13 | Embedding protection | Disk-level encryption (BitLocker) + DB access control; embeddings never returned by API | App-level encryption breaks vector search | — |
| ADR-14 | Timezone | `APP_TIMEZONE=Asia/Kolkata` default; timestamps stored `timestamptz` (UTC); `attendance_date` computed in app timezone | Correct local "day" | — |
| ADR-15 | Docker & webcam | DB (+Redis) in Docker during development; backend runs on host so it can reach the laptop webcam. Full-Docker mode (Phase 36) uses video file / RTSP, because Docker Desktop on Windows cannot easily expose the webcam | Practical | — |

### 3.1 Repository layout (target — Phase 0/1 must reconcile with what exists)

```text
smart-attendance-security-system/
├─ backend/
│  ├─ app/
│  │  ├─ main.py
│  │  ├─ core/            # config.py, logging.py, security.py, errors.py, deps.py, rate_limit.py
│  │  ├─ db/              # session.py, base.py, repositories/
│  │  ├─ models/          # SQLAlchemy models (one file per table)
│  │  ├─ schemas/         # Pydantic request/response models
│  │  ├─ api/v1/          # routers: auth, students, face, recognition, attendance, cameras,
│  │  │                   #   events, alerts, blacklist, tracking, reports, dashboard, health, stream
│  │  ├─ services/        # attendance_service, alert_service, tracking_service, report_service,
│  │  │                   #   student_service, audit_service, privacy_service
│  │  ├─ vision/          # detector.py, embedder.py, recognizer.py, preprocess.py, pipeline.py,
│  │  │                   #   tracker.py, overlay.py, model_registry.py   <-- SHARED AI ENGINE
│  │  ├─ cameras/         # source.py (abstraction), webcam.py, video_file.py, rtsp.py,
│  │  │                   #   worker.py, manager.py
│  │  └─ events/          # bus.py (in-memory), redis_bus.py (Phase 29), handlers/
│  ├─ alembic/ , alembic.ini
│  └─ tests/              # unit/, integration/, api/, db/, vision/, security/
├─ frontend/              # Streamlit: app.py, api_client.py, pages/, components/
├─ scripts/               # check_env.py, create_admin.py, calibrate_threshold.py, eval_recognition.py,
│                         #   benchmark.py, seed_demo.py, run_video.py
├─ docker/                # postgres init sql, Dockerfiles (Phase 36)
├─ docs/                  # PLAYBOOK.md, architecture/, audit/, testing/, performance/, privacy/ ...
├─ data/                  # GITIGNORED: tmp, videos, snapshots
├─ docker-compose.yml  .env.example  .gitignore  .dockerignore  requirements*.txt  README.md
```

### 3.2 Process model (MVP)

```text
[ Streamlit :8501 ] --HTTP/JWT--> [ FastAPI :8000 ] --SQL--> [ PostgreSQL+pgvector :5432 (Docker) ]
                                     |  ^
                                     |  +-- MJPEG /api/v1/stream/{camera}?ticket=...
                                     v
                        [ CameraWorker thread(s) ]  → [ VisionPipeline (model loaded once) ]
                                     |                      → EventBus → Attendance / Security / Movement handlers
                              Laptop webcam (OpenCV)
```

---

## 4. DATABASE DESIGN

PostgreSQL 16, extension `vector`. UUID primary keys (`gen_random_uuid()`), `timestamptz` everywhere. All schema changes go through **Alembic migrations**.

```mermaid
erDiagram
    users ||--o{ audit_logs : "acts in"
    users ||--o{ revoked_tokens : "owns"
    students ||--o{ face_embeddings : "has"
    blacklist_entries ||--o{ face_embeddings : "has"
    students ||--o{ attendance_records : "attends"
    cameras ||--o{ attendance_records : "captured by"
    cameras ||--o{ detection_events : "captured by"
    students ||--o{ detection_events : "seen as"
    blacklist_entries ||--o{ detection_events : "seen as"
    cameras ||--o{ security_alerts : "raised at"
    blacklist_entries ||--o{ security_alerts : "triggers"
    users ||--o{ security_alerts : "acknowledges/resolves"
    users ||--o{ students : "creates"
    users ||--o{ blacklist_entries : "creates"
    users {
        uuid id PK
        varchar username UK
        text password_hash
        varchar role
        bool is_active
    }
    students {
        uuid id PK
        varchar student_id UK
        varchar name
        varchar department
        smallint year
        varchar status
        timestamptz consent_given_at
    }
    face_embeddings {
        uuid id PK
        uuid student_id FK
        uuid blacklist_entry_id FK
        vector_512 embedding
        bool is_active
    }
    cameras {
        uuid id PK
        varchar name UK
        varchar location
        varchar source_type
        bool enabled
        varchar status
    }
    attendance_records {
        uuid id PK
        uuid student_id FK
        uuid camera_id FK
        date attendance_date
        varchar session_label
        real similarity
    }
    detection_events {
        bigint id PK
        uuid camera_id FK
        uuid student_id FK
        uuid blacklist_entry_id FK
        varchar event_type
        real similarity
        timestamptz occurred_at
    }
    security_alerts {
        uuid id PK
        varchar alert_type
        varchar severity
        varchar status
        varchar dedup_key
        int occurrence_count
    }
    blacklist_entries {
        uuid id PK
        varchar full_name
        varchar severity
        varchar status
    }
    audit_logs {
        bigint id PK
        uuid actor_user_id FK
        varchar action
    }
    revoked_tokens {
        uuid jti PK
        uuid user_id FK
        timestamptz expires_at
    }
```

### 4.1 Table specifications

**`users`** — *Purpose:* admin/operator accounts. *PK:* `id uuid`. *Fields:* `username varchar(64) NOT NULL`, `email varchar(255) NULL`, `password_hash text NOT NULL` (Argon2id), `role varchar(16) NOT NULL CHECK IN ('ADMIN','OPERATOR')`, `is_active bool default true`, `last_login_at timestamptz`, `created_at`, `updated_at`. *Unique:* `username`, `email`. *Indexes:* unique indexes only. *Relationships:* creates students/blacklist, acts in audit_logs. *Retention:* kept while account exists; deactivate instead of delete.

**`revoked_tokens`** — *Purpose:* logout/denylist for JWT. *PK:* `jti uuid`. *Fields:* `user_id uuid FK users(id) ON DELETE CASCADE`, `expires_at timestamptz`, `revoked_at timestamptz`. *Indexes:* `(expires_at)`. *Retention:* purge rows where `expires_at < now()` daily (Redis may replace in Phase 29).

**`students`** — *Purpose:* registered people for attendance. *PK:* `id uuid`. *Fields:* `student_id varchar(32) NOT NULL` (business id e.g. `001`), `name varchar(120) NOT NULL`, `department varchar(80) NOT NULL`, `year smallint NOT NULL CHECK 1..8`, `status varchar(16) NOT NULL default 'ACTIVE' CHECK IN ('ACTIVE','INACTIVE')`, `consent_given_at timestamptz NULL`, `consent_version varchar(16) NULL`, `created_by uuid FK users`, `created_at`, `updated_at`. *Unique:* `student_id`. *Indexes:* `(department, year)`, `(lower(name))`, `(status)`. *Relationships:* 1—N face_embeddings, attendance_records, detection_events. *Retention:* soft-delete (INACTIVE) keeps attendance history; **biometric withdrawal hard-deletes embeddings** (Phase 33).

**`blacklist_entries`** — *Purpose:* people flagged for high-priority alerts. *PK:* `id uuid`. *Fields:* `full_name varchar(120)`, `reason text`, `category varchar(40) NULL`, `severity varchar(16) default 'HIGH' CHECK IN ('HIGH','CRITICAL')`, `status varchar(16) default 'ACTIVE' CHECK IN ('ACTIVE','INACTIVE')`, `notes text NULL`, `created_by uuid FK users`, `created_at`, `updated_at`, `deactivated_at`. *Indexes:* `(status)`, `(lower(full_name))`. *Retention:* review policy periodically; deactivation excludes embeddings from search.

**`face_embeddings`** — *Purpose:* ArcFace vectors for students and blacklist entries. *PK:* `id uuid`. *Fields:* `student_id uuid NULL FK students(id) ON DELETE CASCADE`, `blacklist_entry_id uuid NULL FK blacklist_entries(id) ON DELETE CASCADE`, `embedding vector(512) NOT NULL` (L2-normalised), `model_name varchar(40)`, `model_version varchar(40)`, `quality_score real`, `sample_label varchar(24) NULL` (front/left/right/up/down/lowlight…), `is_active bool default true`, `created_at`. *Constraint:* `CHECK ((student_id IS NOT NULL)::int + (blacklist_entry_id IS NOT NULL)::int = 1)`. *Indexes:* `HNSW (embedding vector_cosine_ops) WITH (m=16, ef_construction=64)`, `(student_id)`, `(blacklist_entry_id)`, `(is_active)`. *Retention:* deleted on withdrawal; re-registration deactivates old rows in the same transaction. **Never returned by any API.**

**`cameras`** — *Purpose:* camera/location registry. *PK:* `id uuid`. *Fields:* `name varchar(80) NOT NULL`, `location varchar(160) NOT NULL`, `source_type varchar(16) CHECK IN ('WEBCAM','VIDEO_FILE','RTSP')`, `source_url text NULL` (index `0` for webcam, file path under `data/videos`, or RTSP URL **without credentials**), `credentials_ref varchar(64) NULL` (NAME of env var holding credentials), `enabled bool`, `status varchar(16) CHECK IN ('UNKNOWN','ONLINE','OFFLINE','ERROR','DISABLED')`, `last_seen_at timestamptz`, `created_at`, `updated_at`. *Unique:* `name`. *Retention:* kept; disabling preferred to deleting.

**`attendance_records`** — *Purpose:* one attendance mark per student per day per session. *PK:* `id uuid`. *Fields:* `student_id uuid NOT NULL FK students ON DELETE RESTRICT`, `camera_id uuid NOT NULL FK cameras ON DELETE RESTRICT`, `attendance_date date NOT NULL`, `session_label varchar(32) NOT NULL default 'DEFAULT'`, `marked_at timestamptz NOT NULL`, `status varchar(12) CHECK IN ('PRESENT','LATE')`, `similarity real`, `method varchar(8) CHECK IN ('AUTO','MANUAL')`, `created_at`. *Unique:* `(student_id, attendance_date, session_label)`. *Indexes:* `(attendance_date)`, `(student_id, attendance_date DESC)`, `(camera_id)`. *Retention:* academic-record policy (institution decides).

**`detection_events`** — *Purpose:* every accepted detection (recognized / unknown / blacklisted) — the **single source for movement tracking**. *PK:* `id bigint GENERATED ALWAYS AS IDENTITY`. *Fields:* `occurred_at timestamptz NOT NULL`, `camera_id uuid NOT NULL FK cameras`, `event_type varchar(12) CHECK IN ('RECOGNIZED','UNKNOWN','BLACKLISTED')`, `student_id uuid NULL FK students ON DELETE SET NULL`, `blacklist_entry_id uuid NULL FK blacklist_entries ON DELETE SET NULL`, `similarity real NULL`, `bbox smallint[4] NULL`, `track_id varchar(40) NULL`, `snapshot_path text NULL` (disabled by default), `created_at`. *Indexes:* `(occurred_at DESC)`, `(student_id, occurred_at DESC)`, `(camera_id, occurred_at DESC)`, `(event_type, occurred_at DESC)`. *Retention:* `DETECTION_RETENTION_DAYS` (default 90) purge job. Consider monthly partitioning only if measured necessary.

**`security_alerts`** — *Purpose:* actionable alerts with lifecycle. *PK:* `id uuid`. *Fields:* `alert_type varchar(24) CHECK IN ('UNKNOWN_PERSON','BLACKLISTED_PERSON','CAMERA_OFFLINE')`, `severity varchar(10) CHECK IN ('LOW','MEDIUM','HIGH','CRITICAL')`, `status varchar(14) CHECK IN ('NEW','ACKNOWLEDGED','RESOLVED') default 'NEW'`, `camera_id uuid FK cameras`, `blacklist_entry_id uuid NULL FK`, `student_id uuid NULL FK`, `dedup_key varchar(128) NOT NULL`, `first_seen_at`, `last_seen_at`, `occurrence_count int default 1`, `max_similarity real NULL`, `acknowledged_by uuid FK users NULL`, `acknowledged_at`, `resolved_by uuid FK users NULL`, `resolved_at`, `resolution_note text NULL`, `metadata jsonb default '{}'`, `created_at`. *Indexes:* `(status, severity, last_seen_at DESC)`, **partial unique** `(dedup_key) WHERE status <> 'RESOLVED'`, `(camera_id, created_at DESC)`. *Retention:* `ALERT_RETENTION_DAYS` (default 180).

**`audit_logs`** — *Purpose:* who did what to sensitive data. *PK:* `id bigint identity`. *Fields:* `occurred_at`, `actor_user_id uuid NULL FK users`, `action varchar(48)` (LOGIN, LOGIN_FAILED, STUDENT_CREATE, FACE_REGISTER, FACE_DELETE, BLACKLIST_ADD, EXPORT_CSV, ALERT_ACK…), `entity_type varchar(32)`, `entity_id varchar(64)`, `ip varchar(45)`, `details jsonb` (**never biometric data**). *Indexes:* `(occurred_at DESC)`, `(actor_user_id, occurred_at DESC)`. *Retention:* ≥1 year recommended (institution decides).

**`system_settings`** — *Purpose:* runtime-editable thresholds (recognition threshold, alert policy). *PK:* `key varchar(64)`. *Fields:* `value jsonb`, `updated_by uuid FK users`, `updated_at`. Env vars provide defaults; DB overrides.

**`movement_history`** — *Not a table (ADR-09).* Implemented as a query/service over `detection_events` that groups consecutive same-camera events within `SIGHTING_GAP_SECONDS` (default 60) into a "sighting". Labelled in the UI as **"recorded sightings"**, never "continuous tracking".

---

## 5. API CATALOG

Base path `/api/v1`. Errors use a uniform body `{"error": {"code": "...", "message": "...", "request_id": "..."}}` — never stack traces. Auth column: `—` public, `A` ADMIN only, `AO` ADMIN or OPERATOR. Every request body is validated by Pydantic; invalid → `422`. Auth missing/invalid → `401`; wrong role → `403`; missing resource → `404`; conflict → `409`; rate limit → `429`. "Tests" are mandatory test names (pytest) for Phase 34 coverage; each phase also lists its own.

### 5.1 Health & Auth

| Method | Path | Auth | Request | Response | Validation / Errors | DB effect | Tests |
|---|---|---|---|---|---|---|---|
| GET | `/health` | — | — | `{status, version}` | — | none | health_ok |
| GET | `/health/db` | — | — | `{db:"ok", pgvector:"ok"}` | 503 if DB down (generic message) | `SELECT 1`, extension check | health_db_ok, health_db_down |
| POST | `/auth/login` | — | `{username,password}` | `{access_token, token_type, expires_in, user}` | 401 generic message; 429 after N tries | updates `last_login_at`; audit LOGIN/LOGIN_FAILED | login_ok, login_bad_pw, login_rate_limit |
| POST | `/auth/logout` | AO | — | `204` | 401 | insert `revoked_tokens` | logout_revokes |
| GET | `/auth/me` | AO | — | user profile | 401 | none | me_ok |
| POST | `/stream/ticket` | AO | `{camera_id}` | `{ticket, expires_in}` (≤60 s, single camera) | 404 camera | none (memory/Redis) | ticket_scope, ticket_expiry |

### 5.2 Users & Settings

| Method | Path | Auth | Request | Response | Validation / Errors | DB effect | Tests |
|---|---|---|---|---|---|---|---|
| GET | `/users` | A | filters | paged users (no hashes) | — | none | users_list_admin_only |
| POST | `/users` | A | `{username,password,role}` | user | password policy ≥12 chars; 409 duplicate | insert + audit | users_create |
| PATCH | `/users/{id}` | A | `{role?,is_active?}` | user | cannot demote/deactivate last admin | update + audit | users_last_admin |
| GET/PUT | `/settings` | A | thresholds, alert policy | settings | ranges (threshold 0.2–0.9) | `system_settings` upsert + audit | settings_validation |

### 5.3 Students & Face Registration

| Method | Path | Auth | Request | Response | Validation / Errors | DB effect | Tests |
|---|---|---|---|---|---|---|---|
| POST | `/students` | A | `{student_id,name,department,year,consent}` | student | id regex `^[A-Za-z0-9_-]{1,32}$`; 409 dup | insert + audit | student_create, student_dup |
| GET | `/students` | AO | `q,department,year,status,page,size` | paged list incl. `face_registered`, `sample_count` | size ≤100 | none | student_search |
| GET | `/students/{id}` | AO | — | student | 404 | none | student_get |
| PATCH | `/students/{id}` | A | partial | student | same rules | update + audit | student_update |
| DELETE | `/students/{id}` | A | — | `204` (soft: INACTIVE) | 404 | status=INACTIVE, embeddings deactivated | student_deactivate |
| POST | `/students/{id}/face/session` | A | `{target_samples?}` | `{session_id, required, expires_in}` | needs consent; 409 if camera busy | in-memory session | face_session_requires_consent |
| POST | `/students/{id}/face/session/{sid}/capture` | A | `{camera_id?}` | `{accepted, reason?, count, required, quality}` | rejects no face / multiple / blur / small | in-memory | capture_rejects_* |
| POST | `/students/{id}/face/session/{sid}/commit` | A | — | `{embeddings_stored, rejected}` | needs ≥ `FACE_MIN_SAMPLES`; consistency check | deactivate old + insert new embeddings (one transaction) + audit | commit_ok, commit_too_few |
| GET | `/students/{id}/face/status` | AO | — | `{registered, sample_count, model}` (no vectors) | — | none | face_status_no_vectors |
| DELETE | `/students/{id}/face` | A | — | `204` | — | hard-delete embeddings + audit | face_delete |

### 5.4 Recognition, Attendance, Dashboard

| Method | Path | Auth | Request | Response | Validation / Errors | DB effect | Tests |
|---|---|---|---|---|---|---|---|
| POST | `/recognition/identify` | A | multipart image (≤5 MB, jpeg/png) | `{faces:[{recognized,kind,student_id,name,similarity,bbox}]}` | magic-byte check; 422 no face | none | identify_known, identify_unknown, identify_bad_image |
| POST | `/recognition/workers/{camera_id}/start` · `/stop` | A | — | worker state | 404/409 | camera status | worker_start_stop |
| GET | `/recognition/workers` | AO | — | states + fps + last_error | — | none | workers_list |
| GET | `/stream/{camera_id}` | ticket | query `ticket` | `multipart/x-mixed-replace` MJPEG | 401 bad ticket | none | stream_requires_ticket |
| GET | `/attendance` | AO | `from,to,student_id,department,year,camera_id,page,size` | paged records | date range ≤ 366 d | none | attendance_filters |
| GET | `/attendance/recent` | AO | `limit≤50` | latest records | — | none | attendance_recent |
| POST | `/attendance/manual` | A | `{student_id,date,session_label,reason}` | record (method=MANUAL) | 409 dup | insert + audit | attendance_manual_audit |
| GET | `/dashboard/summary` | AO | — | totals (students, present today, attendance %, unknown today, active alerts, blacklisted today, active cameras) | — | read-only aggregates | summary_real_values |

### 5.5 Cameras, Events, Alerts, Blacklist, Tracking, Reports

| Method | Path | Auth | Request | Response | Validation / Errors | DB effect | Tests |
|---|---|---|---|---|---|---|---|
| GET/POST | `/cameras` | AO / A | `{name,location,source_type,source_url,credentials_ref,enabled}` | camera (URL credential-masked) | RTSP URL must not contain `user:pass@`; video path must resolve inside `data/videos` | insert + audit | camera_create, camera_rejects_creds_in_url |
| GET/PATCH/DELETE | `/cameras/{id}` | AO/A/A | partial | camera | 404 | update/disable | camera_update |
| POST | `/cameras/{id}/test` | A | — | `{ok, width, height, fps, error?}` | timeout 5 s | status update | camera_test_failure |
| GET | `/events` | AO | `from,to,camera_id,event_type,student_id,page,size` | paged events | — | none | events_filters |
| GET | `/alerts` | AO | `status,severity,type,camera_id,from,to,page,size` | paged alerts | — | none | alerts_filters |
| POST | `/alerts/{id}/acknowledge` | AO | `{note?}` | alert | 409 if already RESOLVED | status NEW→ACKNOWLEDGED + audit | alert_ack |
| POST | `/alerts/{id}/resolve` | AO | `{resolution_note}` | alert | note required | →RESOLVED + audit | alert_resolve |
| GET/POST | `/blacklist` | A | `{full_name,reason,category,severity,notes}` | entry (no biometrics) | — | insert + audit | blacklist_create |
| GET/PATCH | `/blacklist/{id}` | A | partial | entry | — | update + audit | blacklist_update |
| POST | `/blacklist/{id}/deactivate` | A | — | entry | — | status INACTIVE; embeddings inactive | blacklist_deactivate_excludes |
| POST | `/blacklist/{id}/face/session` … `/capture` … `/commit` | A | same as students | same | same | embeddings with `blacklist_entry_id` | blacklist_face_register |
| GET | `/tracking/persons?q=` | AO | name/ID search | matches | q ≥2 chars | none | tracking_search |
| GET | `/tracking/persons/{student_id}/history` | AO | `from,to,camera_id` | sightings timeline | — | none | tracking_history |
| GET | `/tracking/persons/{student_id}/last-seen` | AO | — | `{camera,location,time,similarity}` | 404 never seen | none | tracking_last_seen |
| GET | `/reports/attendance` | A | filters | JSON | — | none | report_attendance |
| GET | `/reports/attendance.csv` | A | filters | CSV stream | row cap; formula-injection safe | audit EXPORT_CSV | csv_export_safe |
| GET | `/reports/security` · `/reports/security.csv` | A | filters | JSON / CSV | same | audit | report_security |
| GET | `/audit-logs` | A | filters | paged | — | none | audit_admin_only |

---

## 6. CONFIGURATION REFERENCE (`.env.example` must contain placeholders only)

| Variable | Default | Meaning |
|---|---|---|
| `APP_ENV` | `development` | environment |
| `APP_TIMEZONE` | `Asia/Kolkata` | local day boundary |
| `DATABASE_URL` | `postgresql+psycopg://sas_user:CHANGE_ME@localhost:5432/sas_db` | DB |
| `POSTGRES_USER/PASSWORD/DB` | `sas_user / CHANGE_ME / sas_db` | docker DB |
| `JWT_SECRET` | `CHANGE_ME_LONG_RANDOM` | signing key (≥32 bytes) |
| `JWT_EXPIRE_MINUTES` | `30` | token expiry |
| `CORS_ORIGINS` | `http://localhost:8501` | allowed origins |
| `DEVICE` | `cpu` | inference device |
| `INSIGHTFACE_MODEL` | `buffalo_l` | model pack |
| `INSIGHTFACE_HOME` | `%USERPROFILE%\.insightface` | weights (never in repo) |
| `DET_SIZE` | `640` | detector input |
| `DET_THRESHOLD` | `0.5` | detector score min |
| `MIN_FACE_PIXELS` | `80` | min face width |
| `RECOGNITION_THRESHOLD` | `0.45` | cosine similarity to accept — **must be calibrated** (Phase 13/18) |
| `FACE_SAMPLES_REQUIRED` | `30` | full spec: 30–50 |
| `FACE_MIN_SAMPLES` | `5` | minimum to commit (MVP quick mode: set `FACE_SAMPLES_REQUIRED=5`) |
| `PROCESS_EVERY_N_FRAMES` | `3` | frame skipping |
| `CONFIRM_FRAMES` | `3` | consecutive matches before accepting |
| `ATTENDANCE_COOLDOWN_SECONDS` | `300` | in-memory per-student guard |
| `ATTENDANCE_SESSION_LABEL` | `DEFAULT` | session label |
| `UNKNOWN_EVENT_COOLDOWN_SECONDS` | `30` | unknown dedup |
| `ALERT_POLICY_UNKNOWN` | `MEDIUM` | `OFF/LOW/MEDIUM/HIGH` |
| `ALERT_POLICY_BLACKLIST` | `CRITICAL` | `HIGH/CRITICAL` |
| `ALERT_DEDUP_WINDOW_SECONDS` | `300` | alert merge window |
| `SIGHTING_GAP_SECONDS` | `60` | movement grouping |
| `RETAIN_RAW_IMAGES` | `false` | raw image policy |
| `UNKNOWN_SNAPSHOT_ENABLED` | `false` | snapshot of unknowns |
| `DETECTION_RETENTION_DAYS` | `90` | purge |
| `ALERT_RETENTION_DAYS` | `180` | purge |
| `REDIS_ENABLED` / `REDIS_URL` | `false` / `redis://localhost:6379/0` | Phase 29 |
| `MAX_ACTIVE_CAMERAS` | `4` | Phase 28 |
| `CAMERA_1_CREDENTIALS` etc. | (unset) | `user:pass` for camera `credentials_ref` |

---

## 7. AI/ML DESIGN

- **Detection:** InsightFace SCRFD (inside `buffalo_l`), `det_size=(640,640)`, returns bbox, 5 landmarks, det_score.
- **Alignment:** InsightFace aligns using the 5 landmarks (`norm_crop`) before the ArcFace model — no manual alignment code.
- **Embedding:** ArcFace `w600k_r50`, 512-d, L2-normalised (`normed_embedding`). Cosine similarity = dot product.
- **Preprocessing:** validation (decode, size, blur via Laplacian variance, brightness, face size). CLAHE/brightness normalisation and flip augmentation are **optional flags, default OFF** — enable only if evaluation shows benefit.
- **Registration:** 30–50 samples (config) across prompted poses/lighting; each sample validated; consistency check (each sample's cosine to the median embedding ≥ 0.5, else rejected); store all accepted embeddings (not just a mean) so different angles are matched.
- **Matching:** top-k nearest by `<=>`; similarity = `1 - distance`; accept if `similarity ≥ threshold`. Identity score per person = max over that person's embeddings. Optional margin check vs. second-best *different* identity.
- **Temporal confirmation:** require `CONFIRM_FRAMES` consecutive matches on the same track before attendance/alerts → reduces false positives from a single bad frame.
- **Threshold calibration:** `scripts/calibrate_threshold.py` computes genuine vs. impostor similarity distributions from a **local, gitignored** dataset and reports FAR/FRR at candidate thresholds. The shipped default is a *starting point*, not a validated value.
- **Result shape:** `{"recognized": true, "kind": "STUDENT|BLACKLISTED|UNKNOWN", "student_id": "001", "name": "...", "similarity": 0.94, "bbox": [x1,y1,x2,y2]}` — no embeddings.
- **Performance:** model loaded once (`ModelRegistry`), frame skipping, bounded frame queues that drop stale frames, resize before detection if needed.

---

## 8. FRONTEND DESIGN (Streamlit, ONE dashboard)

```text
LOGIN
Dashboard                      (7 real KPIs + recent attendance + recent alerts + live tile)
ATTENDANCE   Live Attendance | Students | Attendance Records | Reports
SECURITY     Live Monitoring | Alerts | Blacklist | Detection Events | Movement Tracking
SYSTEM       Cameras | Users | Settings
```

Rules: token kept in `st.session_state` only; every call through `frontend/api_client.py`; pages hide/disable admin-only actions for OPERATOR but the **backend is the authority**; no fabricated numbers — empty states show "No data yet"; live video via `<img src="…/stream/{camera}?ticket=…">`; green box = recognized, red box = unknown, (blacklisted = red with thick border + "BLACKLISTED").

---

## 9. SECURITY DESIGN (summary — enforced in Phases 5, 6, 32)

Argon2id hashing · JWT with `exp`, `jti`, role claim · deny-list logout · login rate-limit · RBAC dependency on every router · strict CORS · security headers · upload size/type limits with magic-byte verification · filenames never trusted (UUIDs, resolved paths must stay inside `data/`) · SQLAlchemy parameter binding only · generic error bodies + request ids · log redaction · CSV formula-injection protection · `pip-audit` + `bandit` + `ruff` in CI-style checks · secrets only via env · stream tickets short-lived and camera-scoped.

## 10. PRIVACY AND BIOMETRIC DESIGN (summary — enforced in Phases 8, 12, 24, 33)

Face data is sensitive personal data. The system must: obtain and record **consent** before enrolling a student (`consent_given_at`, `consent_version`); minimise data (store embeddings, not images; `RETAIN_RAW_IMAGES=false`); never return embeddings via API; restrict biometric operations to ADMIN; write **audit logs** for registration, deletion, blacklist changes, exports; support **withdrawal** (hard-delete embeddings); apply **retention** purges; restrict CSV export to ADMIN and log it; recommend disk encryption (BitLocker) for the DB volume and exports; keep blacklist use proportionate and documented. **Institutional policies and applicable laws (for example India's Digital Personal Data Protection Act, 2023 and any institutional rules) must be reviewed by the institution before any real deployment. This playbook makes no legal claims.**

## 11. TEST STRATEGY (detail in Phases 18, 34, 35)

| Layer | Tool | Scope |
|---|---|---|
| Unit | pytest | thresholds, dedup logic, validators, tracker, CSV sanitiser |
| Database | pytest + test DB (`sas_test`) | migrations up/down, constraints, HNSW query, unique attendance |
| API | pytest + FastAPI `TestClient`/httpx | auth, RBAC matrix, validation, errors |
| Vision | pytest + **local gitignored fixtures** (`tests/fixtures_local/`) | no face, multiple faces, blur, embedding shape/norm, genuine vs impostor; tests **skip with a clear message** if fixtures absent |
| Camera | mocks + video file | camera failure, reconnect, EOF |
| Security | pytest + bandit + pip-audit | authz bypass, JWT tamper, path traversal, SQLi strings, upload abuse |
| Frontend | `streamlit.testing.v1.AppTest` | login gate, navigation, empty states |
| E2E | `scripts/e2e_check.py` + manual checklist | full scenario |

Required scenarios: student registration · face registration · invalid image · no face · multiple faces · embedding generation · embedding storage · recognition · unknown person · attendance · duplicate attendance · camera failure · database failure · authentication · authorization · API validation · security alerts · blacklist · tracking · reports · CSV export.

## 12. PERFORMANCE PLAN (Phase 31)

Measure (p50/p95, N≥200 where applicable): detection latency · embedding latency · pgvector search latency (`EXPLAIN ANALYZE`) · end-to-end frame→decision · attendance processing time (first appearance → DB row) · FPS per camera · CPU % and RAM (`psutil`) · API latency for key endpoints. Record the **machine spec** (CPU, RAM, OS). Compare to PPT targets (≥90 % recognition accuracy, <5 s per student) **only with measured results from the local evaluation set**, stating dataset size and conditions.

## 13. GIT WORKFLOW

```powershell
git checkout main
git pull origin main
git checkout -b feature/<feature-name>
# ... implement, test ...
git status
git diff
git add .
git commit -m "<message>"
git push -u origin feature/<feature-name>
```

Open a Pull Request into `main` after human approval of the phase (or merge locally yourself — never let the agent push to `main`). No force push. Run `git status` before `git add .` and confirm no `.env`, images, videos, `.onnx` files or `data/` content is staged. If `git add .` would stage something sensitive, add it to `.gitignore` first and **never** commit it.

Phase branch names and commit messages are given per phase.

---

# PHASE INDEX

| # | Phase | Branch | Gate |
|---|---|---|---|
| 0 | REPOSITORY AUDIT | `chore/phase-00-repo-audit` | HARD |
| 1 | ARCHITECTURE FINALIZATION | `docs/phase-01-architecture` | HARD |
| 2 | DEVELOPMENT ENVIRONMENT | `chore/phase-02-dev-environment` | Stop + approve |
| 3 | DOCKER INFRASTRUCTURE | `feature/phase-03-docker-infra` | Stop + approve |
| 4 | DATABASE | `feature/phase-04-database` | Stop + approve |
| 5 | BACKEND FOUNDATION | `feature/phase-05-backend-foundation` | Stop + approve |
| 6 | AUTHENTICATION | `feature/phase-06-authentication` | Stop + approve |
| 7 | STUDENT MANAGEMENT + DASHBOARD SHELL | `feature/phase-07-students` | Stop + approve |
| 8 | FACE REGISTRATION (WEBCAM CAPTURE) | `feature/phase-08-face-registration` | Stop + approve |
| 9 | FACE PREPROCESSING & IMAGE VALIDATION | `feature/phase-09-preprocessing` | Stop + approve |
| 10 | FACE DETECTION | `feature/phase-10-face-detection` | Stop + approve |
| 11 | FACE EMBEDDINGS (INSIGHTFACE / ARCFACE) | `feature/phase-11-embeddings` | Stop + approve |
| 12 | VECTOR STORAGE (PGVECTOR) | `feature/phase-12-vector-storage` | Stop + approve |
| 13 | FACE RECOGNITION | `feature/phase-13-recognition` | Stop + approve |
| 14 | LIVE LAPTOP CAMERA RECOGNITION | `feature/phase-14-live-camera` | Stop + approve |
| 15 | ATTENDANCE ENGINE | `feature/phase-15-attendance-engine` | Stop + approve |
| 16 | ATTENDANCE DASHBOARD | `feature/phase-16-attendance-dashboard` | Stop + approve |
| 17 | UNKNOWN PERSON DETECTION | `feature/phase-17-unknown-person` | Stop + approve |
| 18 | FIRST MVP TESTING | `test/phase-18-mvp-testing` | Stop + approve |
| 19 | MVP HUMAN APPROVAL | `(no new branch — tag on main after merge)` | HARD |
| 20 | VIDEO FILE SUPPORT | `feature/phase-20-video-file` | Stop + approve |
| 21 | RTSP / CCTV SUPPORT | `feature/phase-21-rtsp` | Stop + approve |
| 22 | CAMERA MANAGEMENT | `feature/phase-22-camera-management` | Stop + approve |
| 23 | SECURITY EVENTS (EVENT LAYER) | `feature/phase-23-event-layer` | Stop + approve |
| 24 | BLACKLIST MANAGEMENT | `feature/phase-24-blacklist` | Stop + approve |
| 25 | SECURITY ALERTS | `feature/phase-25-security-alerts` | Stop + approve |
| 26 | SECURITY DASHBOARD | `feature/phase-26-security-dashboard` | Stop + approve |
| 27 | PERSON TRACKING (DETECTION-BASED) | `feature/phase-27-person-tracking` | Stop + approve |
| 28 | MULTI-CAMERA SUPPORT | `feature/phase-28-multi-camera` | Stop + approve |
| 29 | REDIS (WHERE JUSTIFIED) | `feature/phase-29-redis` | Stop + approve |
| 30 | REPORTING | `feature/phase-30-reporting` | Stop + approve |
| 31 | PERFORMANCE MEASUREMENT | `perf/phase-31-measurement` | Stop + approve |
| 32 | SECURITY HARDENING | `security/phase-32-hardening` | Stop + approve |
| 33 | PRIVACY HARDENING (BIOMETRICS) | `security/phase-33-privacy` | Stop + approve |
| 34 | TESTING (CONSOLIDATION) | `test/phase-34-test-suite` | Stop + approve |
| 35 | END-TO-END TESTING | `test/phase-35-e2e` | Stop + approve |
| 36 | DOCKER FULL APPLICATION | `feature/phase-36-docker-full` | Stop + approve |
| 37 | DOCUMENTATION | `docs/phase-37-documentation` | Stop + approve |
| 38 | FINAL DEMONSTRATION | `release/phase-38-final-demo` | Stop + approve |

---

# Phase 0 — REPOSITORY AUDIT

> **Branch:** `chore/phase-00-repo-audit` · **Gate:** HARD GATE — read the audit report yourself before Phase 1

## Objective

Inspect the existing repository and produce an audit report (current state, existing code, missing modules, dependency conflicts, architecture, risks). **Do not modify application code.**

## Why This Phase Exists

The repo already has a 'Set up development environment' commit (docs/, .dockerignore, .env.example, .gitignore, .python-version, README.md, TOKEN-OPTIMIZATION.md, docker-compose.yml, requirements*.txt). Every later phase must extend what exists instead of overwriting it.

## Prerequisites

- Repository cloned locally on Windows
- Antigravity open on the repo root
- Global Rules block pasted (Section 2)
- `docs/PLAYBOOK.md` saved in the repo

## Inputs

- The repository as it is today
- Project PPT in docs/

## Expected Outputs

- `docs/audit/PHASE0_AUDIT_REPORT.md`
- A list of risks, conflicts and recommended changes (not applied)

## Architecture

No architecture change. Read-only analysis.

```text
Repo (read) → Audit report (docs/audit) → Human reads → Phase 1
```

## Files To Inspect

- Repository tree (`Get-ChildItem -Recurse -Depth 3`)
- README.md
- docs/ (including the project PPT/PDF and docs/PLAYBOOK.md)
- TOKEN-OPTIMIZATION.md
- docker-compose.yml
- requirements.txt, requirements-dev.txt, requirements-gpu.txt
- .env.example, .gitignore, .dockerignore, .python-version
- `git log --oneline -15` and `git status`
- `docs/` PPT: confirm objectives, timeline
- `.gitignore` (full): does it cover `.env`, `*.onnx`, `data/`, `.insightface/`, `*.jpg/*.png` of faces, `*.mp4`, `*.pt`?
- `requirements*.txt`: conflicting pins (numpy 2.x vs onnxruntime/insightface; opencv-python vs opencv-python-headless; GPU packages in the CPU file)
- `docker-compose.yml`: image tags, ports, volumes, secrets in plain text?
- `.env.example`: any real-looking secrets?
- Does any `backend/`, `app/`, `src/` code already exist?

## Files To Create

- docs/audit/PHASE0_AUDIT_REPORT.md

## Files To Modify

No existing files (other than the Git-ignored and doc updates noted).

## Dependencies

No new dependencies.

## Environment Variables

No new variables.

## Database Changes

None.

## API Changes

None.

## Frontend Changes

None.

## Implementation Sequence

1. Create the branch
2. List the full tree and summarise each top-level file/folder
3. Read README, TOKEN-OPTIMIZATION.md, docs/, compose, requirements, .env.example, .gitignore
4. Compare the repo against this playbook's target layout (Section 3.1) and list what exists / is missing
5. Identify dependency conflicts and risks (see inspect list)
6. Write `docs/audit/PHASE0_AUDIT_REPORT.md` with sections: Current State, Existing Code, Missing Modules, Dependency Conflicts, Architecture Observations, Security/Privacy Risks, Recommended Changes (prioritised), Open Questions
7. Commit only the report
8. Stop

## EXACT ANTIGRAVITY PROMPT

```text
YOU ARE IMPLEMENTING: PHASE 0 — REPOSITORY AUDIT

Follow the GLOBAL RULES (docs/PLAYBOOK.md Section 2). Work ONLY on this phase.


STEP 0 — BRANCH
  git checkout main ; git pull origin main ; git checkout -b chore/phase-00-repo-audit
  (If the branch exists, check it out instead. Never commit to main.)

STEP 1 — INSPECT FIRST (do not modify anything yet)
  - Repository tree (`Get-ChildItem -Recurse -Depth 3`)
  - README.md
  - docs/ (including the project PPT/PDF and docs/PLAYBOOK.md)
  - TOKEN-OPTIMIZATION.md
  - docker-compose.yml
  - requirements.txt, requirements-dev.txt, requirements-gpu.txt
  - .env.example, .gitignore, .dockerignore, .python-version
  - `git log --oneline -15` and `git status`
  - `docs/` PPT: confirm objectives, timeline
  - `.gitignore` (full): does it cover `.env`, `*.onnx`, `data/`, `.insightface/`, `*.jpg/*.png` of faces, `*.mp4`, `*.pt`?
  - `requirements*.txt`: conflicting pins (numpy 2.x vs onnxruntime/insightface; opencv-python vs opencv-python-headless; GPU packages in the CPU file)
  - `docker-compose.yml`: image tags, ports, volumes, secrets in plain text?
  - `.env.example`: any real-looking secrets?
  - Does any `backend/`, `app/`, `src/` code already exist?
  Report briefly what already exists that is relevant to this phase. Never assume a file is missing.

OBJECTIVE
  Inspect the existing repository and produce an audit report (current state, existing code, missing modules, dependency conflicts, architecture, risks). **Do not modify application code.**

STEP 2 — CREATE (only after inspection; skip anything that already exists and extend it instead)
  - docs/audit/PHASE0_AUDIT_REPORT.md

STEP 3 — MODIFY
  - (nothing)

DO NOT MODIFY / DO NOT DO
  - ANY application code, requirements, docker-compose, .gitignore or .env files (report issues only)
  - Installing packages
  - Running docker compose up

DEPENDENCIES: none new  (resolve compatible versions, pin them, verify with `pip check`)
ENVIRONMENT VARIABLES: none new  (placeholders only in .env.example)

STEP 4 — IMPLEMENTATION ORDER
  1. Create the branch
  2. List the full tree and summarise each top-level file/folder
  3. Read README, TOKEN-OPTIMIZATION.md, docs/, compose, requirements, .env.example, .gitignore
  4. Compare the repo against this playbook's target layout (Section 3.1) and list what exists / is missing
  5. Identify dependency conflicts and risks (see inspect list)
  6. Write `docs/audit/PHASE0_AUDIT_REPORT.md` with sections: Current State, Existing Code, Missing Modules, Dependency Conflicts, Architecture Observations, Security/Privacy Risks, Recommended Changes (prioritised), Open Questions
  7. Commit only the report
  8. Stop

STEP 5 — TESTS (write and RUN; paste real output)
  - No code tests. Verify `git diff main --stat` shows ONLY `docs/audit/PHASE0_AUDIT_REPORT.md`
  - Verify the report references real file names/contents (no invented files)

STEP 6 — VERIFICATION (run these and report real results)
  Get-ChildItem -Recurse -Depth 3 | Select-Object FullName
  git log --oneline -15
  git status
  Get-Content .gitignore
  Get-Content requirements.txt, requirements-dev.txt, requirements-gpu.txt
  Get-Content docker-compose.yml
  Get-Content .env.example
  python --version ; git --version ; docker --version ; docker compose version

STEP 7 — ACCEPTANCE CRITERIA (mark each ✅ / ❌ / NOT VERIFIED — never guess)
  [ ] Report created at `docs/audit/PHASE0_AUDIT_REPORT.md`
  [ ] Report covers all 8 sections
  [ ] `git diff main --stat` shows only the report
  [ ] Dependency conflicts and `.gitignore` gaps are explicitly listed
  [ ] No application code was changed

STEP 8 — DOCUMENTATION: update README/docs for anything this phase changed; add a short entry to docs/CHANGELOG.md.

STEP 9 — GIT CHECKPOINT (only if tests pass)
  git status ; git diff   (confirm NO secrets, images, videos, .onnx, data/ content staged)
  git add . ; git commit -m "docs: add phase 0 repository audit report" ; git push -u origin chore/phase-00-repo-audit

STEP 10 — STOP. Print the REPORT FORMAT from the global rules and write: STOPPED AT PHASE 0 GATE — awaiting human approval. Do NOT start Phase 1.
```

## Commands

Windows PowerShell (run from the repo root unless stated):

```powershell
Get-ChildItem -Recurse -Depth 3 | Select-Object FullName
git log --oneline -15
git status
Get-Content .gitignore
Get-Content requirements.txt, requirements-dev.txt, requirements-gpu.txt
Get-Content docker-compose.yml
Get-Content .env.example
python --version ; git --version ; docker --version ; docker compose version
```

## Tests

- No code tests. Verify `git diff main --stat` shows ONLY `docs/audit/PHASE0_AUDIT_REPORT.md`
- Verify the report references real file names/contents (no invented files)

## Manual Verification

1. Open the report; check each claim against the real repo
2. Confirm the 'Recommended Changes' list is sensible and nothing was changed

## Expected Result

A factual audit report exists. Nothing else changed.

## Failure Conditions

- Any file other than the report modified
- Report mentions files that do not exist
- Agent started installing or building

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| Agent starts fixing issues | Remind: Phase 0 is read-only. Revert with `git checkout -- .` and re-run |
| Python/Docker missing | Record in report as a finding; fix in Phase 2 |

## Acceptance Criteria

- [ ] Report created at `docs/audit/PHASE0_AUDIT_REPORT.md`
- [ ] Report covers all 8 sections
- [ ] `git diff main --stat` shows only the report
- [ ] Dependency conflicts and `.gitignore` gaps are explicitly listed
- [ ] No application code was changed

## Git Checkpoint

```powershell
git checkout main
git pull origin main
git checkout -b chore/phase-00-repo-audit   # at the START of the phase

# after tests pass:
git status
git diff
git add .
git commit -m "docs: add phase 0 repository audit report"
git push -u origin chore/phase-00-repo-audit
```

Recommended commit message: `docs: add phase 0 repository audit report`

## HUMAN APPROVAL

Before approving, you should personally:

1. Read the whole report
2. Check `.gitignore` gaps and dependency conflicts are real
3. Decide whether any 'Open Questions' need your answer before Phase 1

## NEXT PHASE

Phase 1 can finalise the architecture on top of a truthful picture of the repo.

---

# Phase 1 — ARCHITECTURE FINALIZATION

> **Branch:** `docs/phase-01-architecture` · **Gate:** HARD GATE — you must approve the architecture documents

## Objective

Turn Sections 3–9 of this playbook into repository architecture documents, reconciled with the Phase 0 audit: module boundaries, database design, API structure, frontend structure, AI pipeline, data flow, and ADRs.

## Why This Phase Exists

Cheap to change on paper, expensive to change in code. This phase locks the blueprint every later phase obeys.

## Prerequisites

- Phase 0 approved

## Inputs

- Phase 0 audit report
- Playbook Sections 3–9

## Expected Outputs

- Architecture documents in `docs/architecture/`
- Decision log with every ADR
- List of any deviations from the playbook (with reasons)

## Architecture

Documentation only. Includes Mermaid diagrams: system context, process model, AI pipeline, data flow (attendance / unknown / blacklist), ER diagram, module dependency rules.

Module dependency rule: `api → services → (db repositories, vision, events)`; `vision` never imports `api` or `db`; `cameras` talks to `vision` and publishes to `events`; `frontend` talks to `api` only.

## Files To Inspect

- Repository tree (`Get-ChildItem -Recurse -Depth 3`)
- README.md
- docs/ (including the project PPT/PDF and docs/PLAYBOOK.md)
- TOKEN-OPTIMIZATION.md
- docker-compose.yml
- requirements.txt, requirements-dev.txt, requirements-gpu.txt
- .env.example, .gitignore, .dockerignore, .python-version
- `git log --oneline -15` and `git status`

## Files To Create

- docs/architecture/ARCHITECTURE.md
- docs/architecture/DECISIONS.md (ADR-01…15 from Section 3)
- docs/architecture/DATABASE.md (tables, constraints, ER Mermaid)
- docs/architecture/API.md (endpoint catalog from Section 5)
- docs/architecture/AI_PIPELINE.md
- docs/architecture/FRONTEND.md
- docs/architecture/DATA_FLOW.md
- docs/architecture/MODULE_BOUNDARIES.md

## Files To Modify

- README.md (link to architecture docs only)

## Dependencies

No new dependencies.

## Environment Variables

No new variables.

## Database Changes

None.

## API Changes

None.

## Frontend Changes

None.

## Implementation Sequence

1. Create branch
2. Read Phase 0 report and playbook Sections 3–9
3. Reconcile target layout with existing files; record every deviation
4. Write each architecture document with Mermaid diagrams
5. Write DECISIONS.md with Context/Decision/Consequences per ADR
6. Add a 'Risks and Mitigations' section (webcam on Docker, Windows insightface build, threshold calibration, privacy)
7. Link from README
8. Commit and stop

## EXACT ANTIGRAVITY PROMPT

```text
YOU ARE IMPLEMENTING: PHASE 1 — ARCHITECTURE FINALIZATION

Follow the GLOBAL RULES (docs/PLAYBOOK.md Section 2). Work ONLY on this phase.


STEP 0 — BRANCH
  git checkout main ; git pull origin main ; git checkout -b docs/phase-01-architecture
  (If the branch exists, check it out instead. Never commit to main.)

STEP 1 — INSPECT FIRST (do not modify anything yet)
  - Repository tree (`Get-ChildItem -Recurse -Depth 3`)
  - README.md
  - docs/ (including the project PPT/PDF and docs/PLAYBOOK.md)
  - TOKEN-OPTIMIZATION.md
  - docker-compose.yml
  - requirements.txt, requirements-dev.txt, requirements-gpu.txt
  - .env.example, .gitignore, .dockerignore, .python-version
  - `git log --oneline -15` and `git status`
  Report briefly what already exists that is relevant to this phase. Never assume a file is missing.

OBJECTIVE
  Turn Sections 3–9 of this playbook into repository architecture documents, reconciled with the Phase 0 audit: module boundaries, database design, API structure, frontend structure, AI pipeline, data flow, and ADRs.

STEP 2 — CREATE (only after inspection; skip anything that already exists and extend it instead)
  - docs/architecture/ARCHITECTURE.md
  - docs/architecture/DECISIONS.md (ADR-01…15 from Section 3)
  - docs/architecture/DATABASE.md (tables, constraints, ER Mermaid)
  - docs/architecture/API.md (endpoint catalog from Section 5)
  - docs/architecture/AI_PIPELINE.md
  - docs/architecture/FRONTEND.md
  - docs/architecture/DATA_FLOW.md
  - docs/architecture/MODULE_BOUNDARIES.md

STEP 3 — MODIFY
  - README.md (link to architecture docs only)

DO NOT MODIFY / DO NOT DO
  - Any code, dependencies, compose or schema files
  - Changing ADR choices — if you disagree, list under 'Proposed Deviations' and STOP

DEPENDENCIES: none new  (resolve compatible versions, pin them, verify with `pip check`)
ENVIRONMENT VARIABLES: none new  (placeholders only in .env.example)

STEP 4 — IMPLEMENTATION ORDER
  1. Create branch
  2. Read Phase 0 report and playbook Sections 3–9
  3. Reconcile target layout with existing files; record every deviation
  4. Write each architecture document with Mermaid diagrams
  5. Write DECISIONS.md with Context/Decision/Consequences per ADR
  6. Add a 'Risks and Mitigations' section (webcam on Docker, Windows insightface build, threshold calibration, privacy)
  7. Link from README
  8. Commit and stop

STEP 5 — TESTS (write and RUN; paste real output)
  - Mermaid blocks are syntactically valid (paste two into a Mermaid preview)
  - Every API row in Section 5 appears in API.md
  - Every table in Section 4 appears in DATABASE.md with PK/FK/unique/index/retention

STEP 6 — VERIFICATION (run these and report real results)
  git diff main --stat
  Get-ChildItem docs\architecture

STEP 7 — ACCEPTANCE CRITERIA (mark each ✅ / ❌ / NOT VERIFIED — never guess)
  [ ] All 8 architecture files exist
  [ ] ADR-01…15 documented
  [ ] ER diagram present and valid
  [ ] Module boundary rules documented
  [ ] Deviations (if any) listed explicitly
  [ ] No code changed

STEP 8 — DOCUMENTATION: update README/docs for anything this phase changed; add a short entry to docs/CHANGELOG.md.

STEP 9 — GIT CHECKPOINT (only if tests pass)
  git status ; git diff   (confirm NO secrets, images, videos, .onnx, data/ content staged)
  git add . ; git commit -m "docs: finalize architecture, ADRs, database and API design" ; git push -u origin docs/phase-01-architecture

STEP 10 — STOP. Print the REPORT FORMAT from the global rules and write: STOPPED AT PHASE 1 GATE — awaiting human approval. Do NOT start Phase 2.
```

## Commands

Windows PowerShell (run from the repo root unless stated):

```powershell
git diff main --stat
Get-ChildItem docs\architecture
```

## Tests

- Mermaid blocks are syntactically valid (paste two into a Mermaid preview)
- Every API row in Section 5 appears in API.md
- Every table in Section 4 appears in DATABASE.md with PK/FK/unique/index/retention

## Manual Verification

1. Read ARCHITECTURE.md end to end
2. Check the attendance and security data-flow diagrams match your mental model
3. Check DATABASE.md against your needs (e.g., add fields you want now)

## Expected Result

A coherent, internally consistent architecture set that you explicitly approve.

## Failure Conditions

- Docs contradict the playbook without a listed deviation
- Any code changed
- Missing tables/endpoints

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| Mermaid does not render | Avoid special characters in node labels; quote labels |
| Agent proposes microservices/Kafka | Reject; cite 'DO NOT OVERENGINEER' |

## Acceptance Criteria

- [ ] All 8 architecture files exist
- [ ] ADR-01…15 documented
- [ ] ER diagram present and valid
- [ ] Module boundary rules documented
- [ ] Deviations (if any) listed explicitly
- [ ] No code changed

## Git Checkpoint

```powershell
git checkout main
git pull origin main
git checkout -b docs/phase-01-architecture   # at the START of the phase

# after tests pass:
git status
git diff
git add .
git commit -m "docs: finalize architecture, ADRs, database and API design"
git push -u origin docs/phase-01-architecture
```

Recommended commit message: `docs: finalize architecture, ADRs, database and API design`

## HUMAN APPROVAL

Before approving, you should personally:

1. Approve or request changes to each ADR
2. Confirm Streamlit vs React decision (default Streamlit)
3. Confirm the recognition threshold will be calibrated, not assumed

## NEXT PHASE

Phase 2 builds the actual development environment.

---

# Phase 2 — DEVELOPMENT ENVIRONMENT

> **Branch:** `chore/phase-02-dev-environment` · **Gate:** STOP — human approval required before the next phase

## Objective

Verify Python 3.11, Git, Docker, Docker Compose and camera access. Create the virtual environment, install CPU dependencies, harden `.gitignore`, and verify every critical import.

## Why This Phase Exists

Most failures in CV projects are environment failures (insightface build, numpy conflicts, camera access). Find them now.

## Prerequisites

- Previous phase approved and merged (or branch checked out from it)

## Inputs

- Approved architecture
- requirements*.txt

## Expected Outputs

- Working `.venv` with all CPU deps
- `scripts/check_env.py` printing a PASS/FAIL table
- Hardened `.gitignore`, clean split of requirements files
- `docs/SETUP_WINDOWS.md`

## Architecture

```text
requirements.txt      (runtime, CPU)
requirements-dev.txt  (pytest, ruff, bandit, pip-audit, httpx...)
requirements-gpu.txt  (OPTIONAL, onnxruntime-gpu — NOT installed in MVP)
```

## Files To Inspect

- Repository tree (`Get-ChildItem -Recurse -Depth 3`)
- README.md
- docs/ (including the project PPT/PDF and docs/PLAYBOOK.md)
- TOKEN-OPTIMIZATION.md
- docker-compose.yml
- requirements.txt, requirements-dev.txt, requirements-gpu.txt
- .env.example, .gitignore, .dockerignore, .python-version
- `git log --oneline -15` and `git status`
- Windows: is Microsoft C++ Build Tools installed? (insightface may compile Cython)

## Files To Create

- scripts/check_env.py
- docs/SETUP_WINDOWS.md

## Files To Modify

- requirements.txt
- requirements-dev.txt
- requirements-gpu.txt (comment only)
- .gitignore
- .env.example
- .dockerignore

## Dependencies

- fastapi, uvicorn[standard], sqlalchemy>=2, alembic, psycopg[binary] (v3), pgvector, pydantic-settings, argon2-cffi, pyjwt, python-multipart, slowapi, httpx
- opencv-python (webcam), numpy (<2 if insightface/onnxruntime require it), onnxruntime (CPU), insightface
- streamlit, pandas, psutil
- dev: pytest, pytest-cov, ruff, bandit, pip-audit

## Environment Variables

- DEVICE=cpu
- INSIGHTFACE_HOME
- APP_TIMEZONE

## Database Changes

None.

## API Changes

None.

## Frontend Changes

None.

## Implementation Sequence

1. Create branch
2. Check versions: Python, Git, Docker, Compose
3. Create venv: `py -3.11 -m venv .venv` and activate
4. Fix/split requirements, install, run `pip check`
5. Harden `.gitignore` and `.env.example`
6. Write `scripts/check_env.py`
7. Run it; on insightface build failure STOP and document
8. Write `docs/SETUP_WINDOWS.md` with exact working steps
9. Commit and stop

## EXACT ANTIGRAVITY PROMPT

```text
YOU ARE IMPLEMENTING: PHASE 2 — DEVELOPMENT ENVIRONMENT

Follow the GLOBAL RULES (docs/PLAYBOOK.md Section 2). Work ONLY on this phase.


STEP 0 — BRANCH
  git checkout main ; git pull origin main ; git checkout -b chore/phase-02-dev-environment
  (If the branch exists, check it out instead. Never commit to main.)

STEP 1 — INSPECT FIRST (do not modify anything yet)
  - Repository tree (`Get-ChildItem -Recurse -Depth 3`)
  - README.md
  - docs/ (including the project PPT/PDF and docs/PLAYBOOK.md)
  - TOKEN-OPTIMIZATION.md
  - docker-compose.yml
  - requirements.txt, requirements-dev.txt, requirements-gpu.txt
  - .env.example, .gitignore, .dockerignore, .python-version
  - `git log --oneline -15` and `git status`
  - Windows: is Microsoft C++ Build Tools installed? (insightface may compile Cython)
  Report briefly what already exists that is relevant to this phase. Never assume a file is missing.

OBJECTIVE
  Verify Python 3.11, Git, Docker, Docker Compose and camera access. Create the virtual environment, install CPU dependencies, harden `.gitignore`, and verify every critical import.

STEP 2 — CREATE (only after inspection; skip anything that already exists and extend it instead)
  - scripts/check_env.py
  - docs/SETUP_WINDOWS.md

STEP 3 — MODIFY
  - requirements.txt
  - requirements-dev.txt
  - requirements-gpu.txt (comment only)
  - .gitignore
  - .env.example
  - .dockerignore

DO NOT MODIFY / DO NOT DO
  - Install onnxruntime-gpu
  - Create application code
  - Commit `.venv`, weights or images

DEPENDENCIES: fastapi, uvicorn[standard], sqlalchemy>=2, alembic, psycopg[binary] (v3), pgvector, pydantic-settings, argon2-cffi, pyjwt, python-multipart, slowapi, httpx; opencv-python (webcam), numpy (<2 if insightface/onnxruntime require it), onnxruntime (CPU), insightface; streamlit, pandas, psutil; dev: pytest, pytest-cov, ruff, bandit, pip-audit  (resolve compatible versions, pin them, verify with `pip check`)
ENVIRONMENT VARIABLES: DEVICE=cpu; INSIGHTFACE_HOME; APP_TIMEZONE  (placeholders only in .env.example)

STEP 4 — IMPLEMENTATION ORDER
  1. Create branch
  2. Check versions: Python, Git, Docker, Compose
  3. Create venv: `py -3.11 -m venv .venv` and activate
  4. Fix/split requirements, install, run `pip check`
  5. Harden `.gitignore` and `.env.example`
  6. Write `scripts/check_env.py`
  7. Run it; on insightface build failure STOP and document
  8. Write `docs/SETUP_WINDOWS.md` with exact working steps
  9. Commit and stop

SPECIFIC REQUIREMENTS
  - `.gitignore` MUST cover: `.env`, `.env.*` (except `.env.example`), `.venv/`, `__pycache__/`, `*.onnx`, `*.pt`, `*.pth`, `.insightface/`, `data/`, `*.jpg *.jpeg *.png *.bmp` under `data/` and `tests/fixtures_local/`, `*.mp4 *.avi *.mkv`, `*.log`, `.pytest_cache/`, `htmlcov/`, `.coverage`
  - `check_env.py` must verify: Python 3.11, imports (cv2, numpy, onnxruntime, insightface, fastapi, sqlalchemy, psycopg, pgvector, streamlit), `onnxruntime.get_available_providers()` contains CPUExecutionProvider, webcam opens (`cv2.VideoCapture(0, cv2.CAP_DSHOW)`) and returns a frame (skip with WARN if user passes `--no-camera`), Docker reachable. It must NOT download model weights yet.

STEP 5 — TESTS (write and RUN; paste real output)
  - `python scripts/check_env.py` exits 0 and prints PASS for every non-camera check
  - `git check-ignore` confirms `.env`, `*.onnx`, `data/`, `.venv` are ignored
  - `pip check` reports no broken requirements
  - Camera check returns a frame OR clear WARN with reason

STEP 6 — VERIFICATION (run these and report real results)
  py -3.11 --version
  py -3.11 -m venv .venv
  .\.venv\Scripts\Activate.ps1
  python -m pip install --upgrade pip
  pip install -r requirements.txt -r requirements-dev.txt
  pip check
  python scripts\check_env.py
  git check-ignore -v .env data\x.jpg model.onnx

STEP 7 — ACCEPTANCE CRITERIA (mark each ✅ / ❌ / NOT VERIFIED — never guess)
  [ ] Python 3.11 venv works
  [ ] All required imports succeed
  [ ] CPUExecutionProvider available
  [ ] Webcam frame captured (or documented)
  [ ] `.gitignore` hardened and verified
  [ ] requirements pinned and `pip check` clean
  [ ] `docs/SETUP_WINDOWS.md` written from real steps

STEP 8 — DOCUMENTATION: update README/docs for anything this phase changed; add a short entry to docs/CHANGELOG.md.

STEP 9 — GIT CHECKPOINT (only if tests pass)
  git status ; git diff   (confirm NO secrets, images, videos, .onnx, data/ content staged)
  git add . ; git commit -m "chore: set up Python 3.11 environment, pinned CPU dependencies and env checker" ; git push -u origin chore/phase-02-dev-environment

STEP 10 — STOP. Print the REPORT FORMAT from the global rules and write: STOPPED AT PHASE 2 GATE — awaiting human approval. Do NOT start Phase 3.
```

## Commands

Windows PowerShell (run from the repo root unless stated):

```powershell
py -3.11 --version
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt -r requirements-dev.txt
pip check
python scripts\check_env.py
git check-ignore -v .env data\x.jpg model.onnx
```

## Tests

- `python scripts/check_env.py` exits 0 and prints PASS for every non-camera check
- `git check-ignore` confirms `.env`, `*.onnx`, `data/`, `.venv` are ignored
- `pip check` reports no broken requirements
- Camera check returns a frame OR clear WARN with reason

## Manual Verification

1. Run check_env and read the table
2. Webcam LED turns on briefly during the camera check
3. Confirm `git status` shows no `.venv`

## Expected Result

Every import works, CPU provider present, camera accessible (or documented problem), `.gitignore` protects biometric/model/secret files.

## Failure Conditions

- insightface fails to install and no documented workaround
- numpy/onnxruntime conflict unresolved
- `.env` or `.onnx` not ignored

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| `error: Microsoft Visual C++ 14.0 or greater is required` during insightface install | Install 'Build Tools for Visual Studio' (C++ workload), reopen PowerShell, retry; or use a prebuilt wheel matching Python 3.11 and document it |
| numpy 2.x incompatibility errors | Pin `numpy<2` (verify) and reinstall onnxruntime/opencv |
| Webcam not opening | Close Zoom/Teams/browser tabs using camera; try index 1; check Windows Settings → Privacy → Camera; use `cv2.CAP_DSHOW` |
| Script execution disabled | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |

## Acceptance Criteria

- [ ] Python 3.11 venv works
- [ ] All required imports succeed
- [ ] CPUExecutionProvider available
- [ ] Webcam frame captured (or documented)
- [ ] `.gitignore` hardened and verified
- [ ] requirements pinned and `pip check` clean
- [ ] `docs/SETUP_WINDOWS.md` written from real steps

## Git Checkpoint

```powershell
git checkout main
git pull origin main
git checkout -b chore/phase-02-dev-environment   # at the START of the phase

# after tests pass:
git status
git diff
git add .
git commit -m "chore: set up Python 3.11 environment, pinned CPU dependencies and env checker"
git push -u origin chore/phase-02-dev-environment
```

Recommended commit message: `chore: set up Python 3.11 environment, pinned CPU dependencies and env checker`

## HUMAN APPROVAL

Before approving, you should personally:

1. Run `python scripts\check_env.py` yourself
2. Verify `git status` is clean of venv/data
3. Confirm webcam works

## NEXT PHASE

Phase 3 brings up PostgreSQL + pgvector in Docker.

---

# Phase 3 — DOCKER INFRASTRUCTURE

> **Branch:** `feature/phase-03-docker-infra` · **Gate:** STOP — human approval required before the next phase

## Objective

Configure PostgreSQL 16 with pgvector (and Redis as an optional, profile-gated service) in `docker-compose.yml`, with healthchecks and persistent volumes.

## Why This Phase Exists

A reproducible database is required before schema work. Redis is defined but **not started by default** (ADR-10).

## Prerequisites

- Previous phase approved and merged (or branch checked out from it)

## Inputs

- Existing docker-compose.yml
- .env.example

## Expected Outputs

- Healthy `db` container with `vector` extension
- Optional `redis` service under profile `redis`
- docker/postgres/init/01-extensions.sql

## Architecture

```text
Host (FastAPI, Streamlit, camera)  --5432-->  [db: pgvector/pgvector:pg16]  (named volume pgdata)
                                       [redis: redis:7-alpine] (profile 'redis', off by default)
```

## Files To Inspect

- Repository tree (`Get-ChildItem -Recurse -Depth 3`)
- README.md
- docs/ (including the project PPT/PDF and docs/PLAYBOOK.md)
- TOKEN-OPTIMIZATION.md
- docker-compose.yml
- requirements.txt, requirements-dev.txt, requirements-gpu.txt
- .env.example, .gitignore, .dockerignore, .python-version
- `git log --oneline -15` and `git status`

## Files To Create

- docker/postgres/init/01-extensions.sql  (CREATE EXTENSION IF NOT EXISTS vector;)

## Files To Modify

- docker-compose.yml
- .env.example
- .dockerignore

## Dependencies

No new dependencies.

## Environment Variables

- POSTGRES_USER
- POSTGRES_PASSWORD
- POSTGRES_DB
- POSTGRES_PORT=5432
- REDIS_PORT=6379

## Database Changes

None.

## API Changes

None.

## Frontend Changes

None.

## Implementation Sequence

1. Create branch
2. Review the existing compose file; keep useful parts
3. Define `db` service, volume, healthcheck, 127.0.0.1 port binding
4. Add init SQL to enable `vector`
5. Define optional `redis` profile
6. Copy `.env.example` → `.env` and set a local password
7. Start db, verify health and extension
8. Document commands in SETUP_WINDOWS.md
9. Commit and stop

## EXACT ANTIGRAVITY PROMPT

```text
YOU ARE IMPLEMENTING: PHASE 3 — DOCKER INFRASTRUCTURE

Follow the GLOBAL RULES (docs/PLAYBOOK.md Section 2). Work ONLY on this phase.


STEP 0 — BRANCH
  git checkout main ; git pull origin main ; git checkout -b feature/phase-03-docker-infra
  (If the branch exists, check it out instead. Never commit to main.)

STEP 1 — INSPECT FIRST (do not modify anything yet)
  - Repository tree (`Get-ChildItem -Recurse -Depth 3`)
  - README.md
  - docs/ (including the project PPT/PDF and docs/PLAYBOOK.md)
  - TOKEN-OPTIMIZATION.md
  - docker-compose.yml
  - requirements.txt, requirements-dev.txt, requirements-gpu.txt
  - .env.example, .gitignore, .dockerignore, .python-version
  - `git log --oneline -15` and `git status`
  Report briefly what already exists that is relevant to this phase. Never assume a file is missing.

OBJECTIVE
  Configure PostgreSQL 16 with pgvector (and Redis as an optional, profile-gated service) in `docker-compose.yml`, with healthchecks and persistent volumes.

STEP 2 — CREATE (only after inspection; skip anything that already exists and extend it instead)
  - docker/postgres/init/01-extensions.sql  (CREATE EXTENSION IF NOT EXISTS vector;)

STEP 3 — MODIFY
  - docker-compose.yml
  - .env.example
  - .dockerignore

DO NOT MODIFY / DO NOT DO
  - Commit real passwords
  - Add backend/frontend containers yet (Phase 36)
  - Publish ports on 0.0.0.0 unnecessarily — bind to `127.0.0.1`

DEPENDENCIES: none new  (resolve compatible versions, pin them, verify with `pip check`)
ENVIRONMENT VARIABLES: POSTGRES_USER; POSTGRES_PASSWORD; POSTGRES_DB; POSTGRES_PORT=5432; REDIS_PORT=6379  (placeholders only in .env.example)

STEP 4 — IMPLEMENTATION ORDER
  1. Create branch
  2. Review the existing compose file; keep useful parts
  3. Define `db` service, volume, healthcheck, 127.0.0.1 port binding
  4. Add init SQL to enable `vector`
  5. Define optional `redis` profile
  6. Copy `.env.example` → `.env` and set a local password
  7. Start db, verify health and extension
  8. Document commands in SETUP_WINDOWS.md
  9. Commit and stop

SPECIFIC REQUIREMENTS
  - Use image `pgvector/pgvector:pg16`
  - Credentials via `${VAR}` from `.env`; compose must fail clearly if missing
  - Healthcheck: `pg_isready -U $POSTGRES_USER -d $POSTGRES_DB`
  - Redis: `profiles: ["redis"]`, `redis:7-alpine`, healthcheck `redis-cli ping`
  - Create your own local `.env` from `.env.example` (do NOT commit it)

STEP 5 — TESTS (write and RUN; paste real output)
  - `docker compose ps` shows db `healthy`
  - `vector` extension listed
  - A cosine-distance query returns a number
  - Data persists after `docker compose down` then `up -d` (create a temp table first, then drop it)
  - `git status` does not show `.env`

STEP 6 — VERIFICATION (run these and report real results)
  Copy-Item .env.example .env   # then edit passwords locally
  docker compose config
  docker compose up -d db
  docker compose ps
  docker compose exec db psql -U $env:POSTGRES_USER -d $env:POSTGRES_DB -c "SELECT extname, extversion FROM pg_extension;"
  docker compose exec db psql -U $env:POSTGRES_USER -d $env:POSTGRES_DB -c "SELECT '[1,2,3]'::vector <=> '[1,2,4]'::vector;"
  # optional
docker compose --profile redis up -d redis ; docker compose exec redis redis-cli ping
  docker compose down

STEP 7 — ACCEPTANCE CRITERIA (mark each ✅ / ❌ / NOT VERIFIED — never guess)
  [ ] db healthy
  [ ] pgvector extension present and queryable
  [ ] Persistence verified
  [ ] Redis gated behind profile
  [ ] No secrets committed

STEP 8 — DOCUMENTATION: update README/docs for anything this phase changed; add a short entry to docs/CHANGELOG.md.

STEP 9 — GIT CHECKPOINT (only if tests pass)
  git status ; git diff   (confirm NO secrets, images, videos, .onnx, data/ content staged)
  git add . ; git commit -m "feat(infra): add PostgreSQL 16 + pgvector and optional Redis via docker compose" ; git push -u origin feature/phase-03-docker-infra

STEP 10 — STOP. Print the REPORT FORMAT from the global rules and write: STOPPED AT PHASE 3 GATE — awaiting human approval. Do NOT start Phase 4.
```

## Commands

Windows PowerShell (run from the repo root unless stated):

```powershell
Copy-Item .env.example .env   # then edit passwords locally
docker compose config
docker compose up -d db
docker compose ps
docker compose exec db psql -U $env:POSTGRES_USER -d $env:POSTGRES_DB -c "SELECT extname, extversion FROM pg_extension;"
docker compose exec db psql -U $env:POSTGRES_USER -d $env:POSTGRES_DB -c "SELECT '[1,2,3]'::vector <=> '[1,2,4]'::vector;"
# optional
docker compose --profile redis up -d redis ; docker compose exec redis redis-cli ping
docker compose down
```

## Tests

- `docker compose ps` shows db `healthy`
- `vector` extension listed
- A cosine-distance query returns a number
- Data persists after `docker compose down` then `up -d` (create a temp table first, then drop it)
- `git status` does not show `.env`

## Manual Verification

1. Run the commands and read outputs
2. Restart the container and confirm persistence

## Expected Result

PostgreSQL 16 with pgvector healthy on 127.0.0.1:5432; Redis available only on request.

## Failure Conditions

- Extension missing
- Container unhealthy
- Password committed
- Redis starts by default

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| Port 5432 already in use | Stop local Postgres service or change `POSTGRES_PORT` |
| `Docker daemon not running` | Start Docker Desktop; wait for engine |
| Init SQL did not run | Init scripts only run on empty volume: `docker compose down -v` (local dev data only) then up |
| Variables empty in compose | Ensure `.env` exists next to docker-compose.yml |

## Acceptance Criteria

- [ ] db healthy
- [ ] pgvector extension present and queryable
- [ ] Persistence verified
- [ ] Redis gated behind profile
- [ ] No secrets committed

## Git Checkpoint

```powershell
git checkout main
git pull origin main
git checkout -b feature/phase-03-docker-infra   # at the START of the phase

# after tests pass:
git status
git diff
git add .
git commit -m "feat(infra): add PostgreSQL 16 + pgvector and optional Redis via docker compose"
git push -u origin feature/phase-03-docker-infra
```

Recommended commit message: `feat(infra): add PostgreSQL 16 + pgvector and optional Redis via docker compose`

## HUMAN APPROVAL

Before approving, you should personally:

1. Run `docker compose ps` and the pgvector query yourself

## NEXT PHASE

Phase 4 creates the schema with Alembic migrations.

---

# Phase 4 — DATABASE

> **Branch:** `feature/phase-04-database` · **Gate:** STOP — human approval required before the next phase

## Objective

Create SQLAlchemy models and Alembic migrations for the full schema in Section 4 (users, revoked_tokens, students, blacklist_entries, face_embeddings, cameras, attendance_records, detection_events, security_alerts, audit_logs, system_settings).

## Why This Phase Exists

All later features read/write these tables. Constraints (unique attendance, embedding owner CHECK, partial unique alert key) enforce business rules at the database level.

## Prerequisites

- Previous phase approved and merged (or branch checked out from it)

## Inputs

- Section 4 / docs/architecture/DATABASE.md
- Running db container

## Expected Outputs

- Models, Alembic config, initial migration, DB session module
- Repository tests proving constraints
- `docs/architecture/DATABASE.md` updated to match reality

## Architecture

```text
backend/app/db/{base.py,session.py}  backend/app/models/*.py  backend/alembic/versions/0001_initial.py
```
Use SQLAlchemy 2.0 typed `Mapped[]` style, `pgvector.sqlalchemy.Vector(512)`.

## Files To Inspect

- Repository tree (`Get-ChildItem -Recurse -Depth 3`)
- README.md
- docs/ (including the project PPT/PDF and docs/PLAYBOOK.md)
- TOKEN-OPTIMIZATION.md
- docker-compose.yml
- requirements.txt, requirements-dev.txt, requirements-gpu.txt
- .env.example, .gitignore, .dockerignore, .python-version
- `git log --oneline -15` and `git status`

## Files To Create

- backend/app/db/base.py
- backend/app/db/session.py
- backend/app/models/*.py (one file per table)
- backend/alembic.ini
- backend/alembic/env.py
- backend/alembic/versions/0001_initial.py
- backend/tests/db/test_schema.py
- backend/tests/conftest.py (test DB fixture using `sas_test`)

## Files To Modify

- requirements.txt (only if something is missing)
- .env.example (DATABASE_URL, TEST_DATABASE_URL)

## Dependencies

- sqlalchemy, alembic, psycopg, pgvector

## Environment Variables

- DATABASE_URL
- TEST_DATABASE_URL

## Database Changes

Initial migration creates ALL tables, constraints, indexes (including `HNSW (embedding vector_cosine_ops)` with `m=16, ef_construction=64`, the partial unique index on `security_alerts(dedup_key) WHERE status <> 'RESOLVED'`, and the embedding owner CHECK). Migration must be reversible (`downgrade`).

## API Changes

None.

## Frontend Changes

None.

## Implementation Sequence

1. Create branch
2. Read DATABASE.md
3. Write session/base modules (engine from `DATABASE_URL`, no hardcoded creds)
4. Write models exactly per Section 4
5. Configure Alembic env to use model metadata and `DATABASE_URL`
6. Autogenerate then HAND-REVIEW migration; add HNSW index, CHECK and partial unique index manually if autogenerate missed them
7. `alembic upgrade head`; test `downgrade base` then upgrade again
8. Write DB tests
9. Update DATABASE.md
10. Commit and stop

## EXACT ANTIGRAVITY PROMPT

```text
YOU ARE IMPLEMENTING: PHASE 4 — DATABASE

Follow the GLOBAL RULES (docs/PLAYBOOK.md Section 2). Work ONLY on this phase.


STEP 0 — BRANCH
  git checkout main ; git pull origin main ; git checkout -b feature/phase-04-database
  (If the branch exists, check it out instead. Never commit to main.)

STEP 1 — INSPECT FIRST (do not modify anything yet)
  - Repository tree (`Get-ChildItem -Recurse -Depth 3`)
  - README.md
  - docs/ (including the project PPT/PDF and docs/PLAYBOOK.md)
  - TOKEN-OPTIMIZATION.md
  - docker-compose.yml
  - requirements.txt, requirements-dev.txt, requirements-gpu.txt
  - .env.example, .gitignore, .dockerignore, .python-version
  - `git log --oneline -15` and `git status`
  Report briefly what already exists that is relevant to this phase. Never assume a file is missing.

OBJECTIVE
  Create SQLAlchemy models and Alembic migrations for the full schema in Section 4 (users, revoked_tokens, students, blacklist_entries, face_embeddings, cameras, attendance_records, detection_events, security_alerts, audit_logs, system_settings).

STEP 2 — CREATE (only after inspection; skip anything that already exists and extend it instead)
  - backend/app/db/base.py
  - backend/app/db/session.py
  - backend/app/models/*.py (one file per table)
  - backend/alembic.ini
  - backend/alembic/env.py
  - backend/alembic/versions/0001_initial.py
  - backend/tests/db/test_schema.py
  - backend/tests/conftest.py (test DB fixture using `sas_test`)

STEP 3 — MODIFY
  - requirements.txt (only if something is missing)
  - .env.example (DATABASE_URL, TEST_DATABASE_URL)

DO NOT MODIFY / DO NOT DO
  - FastAPI code
  - Seed users or fake data
  - Store plaintext secrets

DEPENDENCIES: sqlalchemy, alembic, psycopg, pgvector  (resolve compatible versions, pin them, verify with `pip check`)
ENVIRONMENT VARIABLES: DATABASE_URL; TEST_DATABASE_URL  (placeholders only in .env.example)

STEP 4 — IMPLEMENTATION ORDER
  1. Create branch
  2. Read DATABASE.md
  3. Write session/base modules (engine from `DATABASE_URL`, no hardcoded creds)
  4. Write models exactly per Section 4
  5. Configure Alembic env to use model metadata and `DATABASE_URL`
  6. Autogenerate then HAND-REVIEW migration; add HNSW index, CHECK and partial unique index manually if autogenerate missed them
  7. `alembic upgrade head`; test `downgrade base` then upgrade again
  8. Write DB tests
  9. Update DATABASE.md
  10. Commit and stop

STEP 5 — TESTS (write and RUN; paste real output)
  - Migration up/down/up works
  - Insert student; duplicate `student_id` → IntegrityError
  - Insert two `attendance_records` same (student,date,session) → IntegrityError; different session → OK
  - `face_embeddings` with both owners NULL or both set → CHECK violation
  - Insert 3 embeddings; nearest-neighbour query `ORDER BY embedding <=> :q LIMIT 1` returns the closest
  - Partial unique alert key: two open alerts same key → error; after RESOLVED a new one is allowed
  - Vector of wrong dimension rejected
  - `\d face_embeddings` shows the HNSW index

STEP 6 — VERIFICATION (run these and report real results)
  docker compose up -d db
  cd backend
  alembic revision --autogenerate -m "initial schema"
  alembic upgrade head
  alembic downgrade base ; alembic upgrade head
  cd ..
  docker compose exec db psql -U $env:POSTGRES_USER -d $env:POSTGRES_DB -c "\dt"
  docker compose exec db psql -U $env:POSTGRES_USER -d $env:POSTGRES_DB -c "\d face_embeddings"
  pytest backend/tests/db -v

STEP 7 — ACCEPTANCE CRITERIA (mark each ✅ / ❌ / NOT VERIFIED — never guess)
  [ ] 11 tables exist
  [ ] All constraints and indexes verified with psql
  [ ] up/down/up migration works
  [ ] DB tests pass (real output)
  [ ] DATABASE.md matches actual schema

STEP 8 — DOCUMENTATION: update README/docs for anything this phase changed; add a short entry to docs/CHANGELOG.md.

STEP 9 — GIT CHECKPOINT (only if tests pass)
  git status ; git diff   (confirm NO secrets, images, videos, .onnx, data/ content staged)
  git add . ; git commit -m "feat(db): add SQLAlchemy models and initial Alembic migration with pgvector" ; git push -u origin feature/phase-04-database

STEP 10 — STOP. Print the REPORT FORMAT from the global rules and write: STOPPED AT PHASE 4 GATE — awaiting human approval. Do NOT start Phase 5.
```

## Commands

Windows PowerShell (run from the repo root unless stated):

```powershell
docker compose up -d db
cd backend
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
alembic downgrade base ; alembic upgrade head
cd ..
docker compose exec db psql -U $env:POSTGRES_USER -d $env:POSTGRES_DB -c "\dt"
docker compose exec db psql -U $env:POSTGRES_USER -d $env:POSTGRES_DB -c "\d face_embeddings"
pytest backend/tests/db -v
```

## Tests

- Migration up/down/up works
- Insert student; duplicate `student_id` → IntegrityError
- Insert two `attendance_records` same (student,date,session) → IntegrityError; different session → OK
- `face_embeddings` with both owners NULL or both set → CHECK violation
- Insert 3 embeddings; nearest-neighbour query `ORDER BY embedding <=> :q LIMIT 1` returns the closest
- Partial unique alert key: two open alerts same key → error; after RESOLVED a new one is allowed
- Vector of wrong dimension rejected
- `\d face_embeddings` shows the HNSW index

## Manual Verification

1. Run `\dt` and confirm 11 tables
2. Run `\d` on face_embeddings, attendance_records, security_alerts and read constraints/indexes

## Expected Result

Schema matches Section 4, constraints enforce rules, migrations are reversible.

## Failure Conditions

- Missing HNSW index or CHECK
- Autogenerated migration committed without review
- Tests use the dev DB and destroy data

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| `type "vector" does not exist` | Extension not created in that DB; `CREATE EXTENSION vector;` or recreate volume |
| Alembic cannot import models | Run from `backend/`, set `prepend_sys_path = .` |
| HNSW index missing in autogenerate | Add with `op.execute` raw SQL in migration |
| psycopg connection refused | Check db health, port, and `DATABASE_URL` host `localhost` |

## Acceptance Criteria

- [ ] 11 tables exist
- [ ] All constraints and indexes verified with psql
- [ ] up/down/up migration works
- [ ] DB tests pass (real output)
- [ ] DATABASE.md matches actual schema

## Git Checkpoint

```powershell
git checkout main
git pull origin main
git checkout -b feature/phase-04-database   # at the START of the phase

# after tests pass:
git status
git diff
git add .
git commit -m "feat(db): add SQLAlchemy models and initial Alembic migration with pgvector"
git push -u origin feature/phase-04-database
```

Recommended commit message: `feat(db): add SQLAlchemy models and initial Alembic migration with pgvector`

## HUMAN APPROVAL

Before approving, you should personally:

1. Inspect `\d` output for the three key tables
2. Run pytest db tests yourself

## NEXT PHASE

Phase 5 creates the FastAPI foundation on top of the schema.

---

# Phase 5 — BACKEND FOUNDATION

> **Branch:** `feature/phase-05-backend-foundation` · **Gate:** STOP — human approval required before the next phase

## Objective

Create the FastAPI application skeleton: configuration, DB dependency, structured logging with redaction, uniform error handling, request IDs, CORS, security headers, health endpoints and versioned router structure.

## Why This Phase Exists

Every later router plugs into this. Getting config, errors and logging right once prevents leaks and rework.

## Prerequisites

- Previous phase approved and merged (or branch checked out from it)

## Inputs

- Output of the previous phase
- This playbook

## Expected Outputs

- Running API at http://127.0.0.1:8000 with `/docs`
- `/api/v1/health` and `/api/v1/health/db`
- Uniform error body; no stack traces to clients

## Architecture

```text
main.py → create_app(): middleware(request_id, security headers, CORS) → exception handlers → /api/v1 routers
core/config.py (pydantic-settings) · core/logging.py (redacting) · core/errors.py · db/session.get_db
```

## Files To Inspect

- Repository tree (`Get-ChildItem -Recurse -Depth 3`)
- README.md
- docs/ (including the project PPT/PDF and docs/PLAYBOOK.md)
- TOKEN-OPTIMIZATION.md
- docker-compose.yml
- requirements.txt, requirements-dev.txt, requirements-gpu.txt
- .env.example, .gitignore, .dockerignore, .python-version
- `git log --oneline -15` and `git status`

## Files To Create

- backend/app/main.py
- backend/app/core/{config,logging,errors,deps}.py
- backend/app/api/v1/__init__.py, router.py, health.py
- backend/tests/api/test_health.py, test_errors.py

## Files To Modify

- .env.example (APP_ENV, CORS_ORIGINS, LOG_LEVEL)
- docs/SETUP_WINDOWS.md (run command)

## Dependencies

No new dependencies.

## Environment Variables

- APP_ENV
- CORS_ORIGINS
- LOG_LEVEL
- DATABASE_URL

## Database Changes

None.

## API Changes

`GET /api/v1/health`, `GET /api/v1/health/db`. Error schema `{error:{code,message,request_id}}`.

## Frontend Changes

None.

## Implementation Sequence

1. Create branch
2. Inspect for existing backend code
3. Write config, logging, errors
4. Create app factory + middleware + routers
5. Implement health and DB health (generic message on failure)
6. Write tests (including forcing a 500 and verifying no stack trace is returned)
7. Document run command
8. Commit and stop

## EXACT ANTIGRAVITY PROMPT

```text
YOU ARE IMPLEMENTING: PHASE 5 — BACKEND FOUNDATION

Follow the GLOBAL RULES (docs/PLAYBOOK.md Section 2). Work ONLY on this phase.


STEP 0 — BRANCH
  git checkout main ; git pull origin main ; git checkout -b feature/phase-05-backend-foundation
  (If the branch exists, check it out instead. Never commit to main.)

STEP 1 — INSPECT FIRST (do not modify anything yet)
  - Repository tree (`Get-ChildItem -Recurse -Depth 3`)
  - README.md
  - docs/ (including the project PPT/PDF and docs/PLAYBOOK.md)
  - TOKEN-OPTIMIZATION.md
  - docker-compose.yml
  - requirements.txt, requirements-dev.txt, requirements-gpu.txt
  - .env.example, .gitignore, .dockerignore, .python-version
  - `git log --oneline -15` and `git status`
  Report briefly what already exists that is relevant to this phase. Never assume a file is missing.

OBJECTIVE
  Create the FastAPI application skeleton: configuration, DB dependency, structured logging with redaction, uniform error handling, request IDs, CORS, security headers, health endpoints and versioned router structure.

STEP 2 — CREATE (only after inspection; skip anything that already exists and extend it instead)
  - backend/app/main.py
  - backend/app/core/{config,logging,errors,deps}.py
  - backend/app/api/v1/__init__.py, router.py, health.py
  - backend/tests/api/test_health.py, test_errors.py

STEP 3 — MODIFY
  - .env.example (APP_ENV, CORS_ORIGINS, LOG_LEVEL)
  - docs/SETUP_WINDOWS.md (run command)

DO NOT MODIFY / DO NOT DO
  - Business endpoints
  - Wildcard CORS (`*`) with credentials
  - Logging request bodies

DEPENDENCIES: none new  (resolve compatible versions, pin them, verify with `pip check`)
ENVIRONMENT VARIABLES: APP_ENV; CORS_ORIGINS; LOG_LEVEL; DATABASE_URL  (placeholders only in .env.example)

STEP 4 — IMPLEMENTATION ORDER
  1. Create branch
  2. Inspect for existing backend code
  3. Write config, logging, errors
  4. Create app factory + middleware + routers
  5. Implement health and DB health (generic message on failure)
  6. Write tests (including forcing a 500 and verifying no stack trace is returned)
  7. Document run command
  8. Commit and stop

SPECIFIC REQUIREMENTS
  - Settings loaded once via `lru_cache`; fail fast if `JWT_SECRET` is still `CHANGE_ME` when `APP_ENV != development`
  - Logging filter redacts `password`, `token`, `authorization`, `embedding`
  - Unhandled exceptions → 500 generic body + logged with request_id
  - Add headers: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`

STEP 5 — TESTS (write and RUN; paste real output)
  - health returns 200 with version
  - health/db returns 200 with DB up
  - health/db returns 503 generic body with DB stopped (`docker compose stop db`), then restart
  - A deliberately raised exception returns 500 without traceback and includes `request_id`
  - CORS: allowed origin gets header; other origin does not
  - Security headers present
  - Settings fail-fast test

STEP 6 — VERIFICATION (run these and report real results)
  uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000   # adjust module path to the real layout
  curl.exe http://127.0.0.1:8000/api/v1/health
  curl.exe http://127.0.0.1:8000/api/v1/health/db
  pytest backend/tests/api -v
  ruff check backend

STEP 7 — ACCEPTANCE CRITERIA (mark each ✅ / ❌ / NOT VERIFIED — never guess)
  [ ] /docs reachable
  [ ] Health endpoints verified incl. DB-down case
  [ ] No traceback leak (tested)
  [ ] Logs redact secrets (tested)
  [ ] ruff clean

STEP 8 — DOCUMENTATION: update README/docs for anything this phase changed; add a short entry to docs/CHANGELOG.md.

STEP 9 — GIT CHECKPOINT (only if tests pass)
  git status ; git diff   (confirm NO secrets, images, videos, .onnx, data/ content staged)
  git add . ; git commit -m "feat(api): add FastAPI foundation with config, logging, errors and health endpoints" ; git push -u origin feature/phase-05-backend-foundation

STEP 10 — STOP. Print the REPORT FORMAT from the global rules and write: STOPPED AT PHASE 5 GATE — awaiting human approval. Do NOT start Phase 6.
```

## Commands

Windows PowerShell (run from the repo root unless stated):

```powershell
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000   # adjust module path to the real layout
curl.exe http://127.0.0.1:8000/api/v1/health
curl.exe http://127.0.0.1:8000/api/v1/health/db
pytest backend/tests/api -v
ruff check backend
```

## Tests

- health returns 200 with version
- health/db returns 200 with DB up
- health/db returns 503 generic body with DB stopped (`docker compose stop db`), then restart
- A deliberately raised exception returns 500 without traceback and includes `request_id`
- CORS: allowed origin gets header; other origin does not
- Security headers present
- Settings fail-fast test

## Manual Verification

1. Open http://127.0.0.1:8000/docs
2. Stop the db container and call `/health/db`; restart it

## Expected Result

API runs, health checks reflect real DB state, errors are safe.

## Failure Conditions

- Stack trace in any response
- CORS wildcard
- Secrets in logs

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| `ModuleNotFoundError: app` | Run uvicorn from repo root with `--app-dir backend` or use `backend.app.main:app` consistently |
| CORS error from Streamlit | Add `http://localhost:8501` to `CORS_ORIGINS` |

## Acceptance Criteria

- [ ] /docs reachable
- [ ] Health endpoints verified incl. DB-down case
- [ ] No traceback leak (tested)
- [ ] Logs redact secrets (tested)
- [ ] ruff clean

## Git Checkpoint

```powershell
git checkout main
git pull origin main
git checkout -b feature/phase-05-backend-foundation   # at the START of the phase

# after tests pass:
git status
git diff
git add .
git commit -m "feat(api): add FastAPI foundation with config, logging, errors and health endpoints"
git push -u origin feature/phase-05-backend-foundation
```

Recommended commit message: `feat(api): add FastAPI foundation with config, logging, errors and health endpoints`

## HUMAN APPROVAL

Before approving, you should personally:

1. Call health endpoints with DB up and down
2. Read one log line and confirm no secrets

## NEXT PHASE

Phase 6 adds authentication.

---

# Phase 6 — AUTHENTICATION

> **Branch:** `feature/phase-06-authentication` · **Gate:** STOP — human approval required before the next phase

## Objective

Implement admin/operator authentication: Argon2id hashing, JWT with expiry and `jti`, login, logout (deny-list), `/auth/me`, RBAC dependencies, login rate limiting, audit logging, and an admin-creation script.

## Why This Phase Exists

All biometric and security data must sit behind authentication and authorization.

## Prerequisites

- Previous phase approved and merged (or branch checked out from it)

## Inputs

- Output of the previous phase
- This playbook

## Expected Outputs

- Working login/logout/me
- `require_role()` dependency
- `scripts/create_admin.py`
- Audit log entries for login events

## Architecture

```text
POST /auth/login → verify Argon2id → JWT{sub,role,jti,exp} → Authorization: Bearer
protected route → decode → check exp, jti not in revoked_tokens, user active → role check
```

## Files To Inspect

- Repository tree (`Get-ChildItem -Recurse -Depth 3`)
- README.md
- docs/ (including the project PPT/PDF and docs/PLAYBOOK.md)
- TOKEN-OPTIMIZATION.md
- docker-compose.yml
- requirements.txt, requirements-dev.txt, requirements-gpu.txt
- .env.example, .gitignore, .dockerignore, .python-version
- `git log --oneline -15` and `git status`

## Files To Create

- backend/app/core/security.py
- backend/app/core/rate_limit.py
- backend/app/api/v1/auth.py
- backend/app/schemas/auth.py
- backend/app/services/audit_service.py
- scripts/create_admin.py
- backend/tests/api/test_auth.py, test_rbac.py

## Files To Modify

- backend/app/api/v1/router.py
- backend/app/core/deps.py
- .env.example (JWT_SECRET, JWT_EXPIRE_MINUTES)

## Dependencies

- argon2-cffi, pyjwt, slowapi

## Environment Variables

- JWT_SECRET (≥32 random bytes)
- JWT_EXPIRE_MINUTES=30
- LOGIN_RATE_LIMIT=5/minute

## Database Changes

Uses `users`, `revoked_tokens`, `audit_logs` (no schema change).

## API Changes

`POST /auth/login`, `POST /auth/logout`, `GET /auth/me`. All other future routers use `Depends(require_role(...))`.

## Frontend Changes

None.

## Implementation Sequence

1. Create branch
2. Inspect existing auth code
3. Implement hashing and JWT utilities
4. Implement login with rate limit + audit
5. Implement logout deny-list and `me`
6. Implement `require_role`
7. Write `create_admin.py`
8. Tests
9. Commit and stop

## EXACT ANTIGRAVITY PROMPT

```text
YOU ARE IMPLEMENTING: PHASE 6 — AUTHENTICATION

Follow the GLOBAL RULES (docs/PLAYBOOK.md Section 2). Work ONLY on this phase.


STEP 0 — BRANCH
  git checkout main ; git pull origin main ; git checkout -b feature/phase-06-authentication
  (If the branch exists, check it out instead. Never commit to main.)

STEP 1 — INSPECT FIRST (do not modify anything yet)
  - Repository tree (`Get-ChildItem -Recurse -Depth 3`)
  - README.md
  - docs/ (including the project PPT/PDF and docs/PLAYBOOK.md)
  - TOKEN-OPTIMIZATION.md
  - docker-compose.yml
  - requirements.txt, requirements-dev.txt, requirements-gpu.txt
  - .env.example, .gitignore, .dockerignore, .python-version
  - `git log --oneline -15` and `git status`
  Report briefly what already exists that is relevant to this phase. Never assume a file is missing.

OBJECTIVE
  Implement admin/operator authentication: Argon2id hashing, JWT with expiry and `jti`, login, logout (deny-list), `/auth/me`, RBAC dependencies, login rate limiting, audit logging, and an admin-creation script.

STEP 2 — CREATE (only after inspection; skip anything that already exists and extend it instead)
  - backend/app/core/security.py
  - backend/app/core/rate_limit.py
  - backend/app/api/v1/auth.py
  - backend/app/schemas/auth.py
  - backend/app/services/audit_service.py
  - scripts/create_admin.py
  - backend/tests/api/test_auth.py, test_rbac.py

STEP 3 — MODIFY
  - backend/app/api/v1/router.py
  - backend/app/core/deps.py
  - .env.example (JWT_SECRET, JWT_EXPIRE_MINUTES)

DO NOT MODIFY / DO NOT DO
  - Hardcode default admin credentials
  - Return distinct messages for 'user not found' vs 'wrong password'
  - Store tokens in DB beyond jti denylist

DEPENDENCIES: argon2-cffi, pyjwt, slowapi  (resolve compatible versions, pin them, verify with `pip check`)
ENVIRONMENT VARIABLES: JWT_SECRET (≥32 random bytes); JWT_EXPIRE_MINUTES=30; LOGIN_RATE_LIMIT=5/minute  (placeholders only in .env.example)

STEP 4 — IMPLEMENTATION ORDER
  1. Create branch
  2. Inspect existing auth code
  3. Implement hashing and JWT utilities
  4. Implement login with rate limit + audit
  5. Implement logout deny-list and `me`
  6. Implement `require_role`
  7. Write `create_admin.py`
  8. Tests
  9. Commit and stop

SPECIFIC REQUIREMENTS
  - `create_admin.py` prompts for password via `getpass` (min 12 chars) — never accepts it on the command line
  - Run a dummy hash on unknown username to equalise timing
  - Reject tokens with `alg=none` or wrong algorithm; pin `HS256`
  - Purge expired `revoked_tokens` helper

STEP 5 — TESTS (write and RUN; paste real output)
  - Correct login → token
  - Wrong password and unknown user → identical 401 body
  - 6th login within a minute → 429
  - No token → 401; garbage token → 401; expired token → 401
  - Token with tampered payload or `alg=none` → 401
  - Logout then reuse token → 401
  - OPERATOR calling an ADMIN route → 403
  - Deactivated user's token → 401
  - Password never appears in logs or responses
  - DB contains Argon2 hash, never plaintext

STEP 6 — VERIFICATION (run these and report real results)
  python scripts\create_admin.py --username admin --role ADMIN
  curl.exe -X POST http://127.0.0.1:8000/api/v1/auth/login -H "Content-Type: application/json" -d "{\"username\":\"admin\",\"password\":\"<your-password>\"}"
  curl.exe http://127.0.0.1:8000/api/v1/auth/me -H "Authorization: Bearer <token>"
  pytest backend/tests/api/test_auth.py backend/tests/api/test_rbac.py -v

STEP 7 — ACCEPTANCE CRITERIA (mark each ✅ / ❌ / NOT VERIFIED — never guess)
  [ ] All auth tests pass (real output)
  [ ] RBAC verified for ADMIN and OPERATOR
  [ ] Rate limit works
  [ ] No secrets in repo
  [ ] Audit logs written for login success/failure

STEP 8 — DOCUMENTATION: update README/docs for anything this phase changed; add a short entry to docs/CHANGELOG.md.

STEP 9 — GIT CHECKPOINT (only if tests pass)
  git status ; git diff   (confirm NO secrets, images, videos, .onnx, data/ content staged)
  git add . ; git commit -m "feat(auth): add Argon2id + JWT authentication, RBAC, logout deny-list and audit logging" ; git push -u origin feature/phase-06-authentication

STEP 10 — STOP. Print the REPORT FORMAT from the global rules and write: STOPPED AT PHASE 6 GATE — awaiting human approval. Do NOT start Phase 7.
```

## Commands

Windows PowerShell (run from the repo root unless stated):

```powershell
python scripts\create_admin.py --username admin --role ADMIN
curl.exe -X POST http://127.0.0.1:8000/api/v1/auth/login -H "Content-Type: application/json" -d "{\"username\":\"admin\",\"password\":\"<your-password>\"}"
curl.exe http://127.0.0.1:8000/api/v1/auth/me -H "Authorization: Bearer <token>"
pytest backend/tests/api/test_auth.py backend/tests/api/test_rbac.py -v
```

## Tests

- Correct login → token
- Wrong password and unknown user → identical 401 body
- 6th login within a minute → 429
- No token → 401; garbage token → 401; expired token → 401
- Token with tampered payload or `alg=none` → 401
- Logout then reuse token → 401
- OPERATOR calling an ADMIN route → 403
- Deactivated user's token → 401
- Password never appears in logs or responses
- DB contains Argon2 hash, never plaintext

## Manual Verification

1. Create admin, log in via /docs 'Authorize'
2. Log out and confirm the token stops working
3. Check `audit_logs` rows via psql

## Expected Result

Secure, role-aware authentication with audit trail.

## Failure Conditions

- Plaintext password anywhere
- Any protected route reachable without token
- Default credentials in repo

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| 401 on valid token | Clock skew or wrong `JWT_SECRET` after restart; ensure `.env` loaded |
| argon2 import error | Reinstall `argon2-cffi` |

## Acceptance Criteria

- [ ] All auth tests pass (real output)
- [ ] RBAC verified for ADMIN and OPERATOR
- [ ] Rate limit works
- [ ] No secrets in repo
- [ ] Audit logs written for login success/failure

## Git Checkpoint

```powershell
git checkout main
git pull origin main
git checkout -b feature/phase-06-authentication   # at the START of the phase

# after tests pass:
git status
git diff
git add .
git commit -m "feat(auth): add Argon2id + JWT authentication, RBAC, logout deny-list and audit logging"
git push -u origin feature/phase-06-authentication
```

Recommended commit message: `feat(auth): add Argon2id + JWT authentication, RBAC, logout deny-list and audit logging`

## HUMAN APPROVAL

Before approving, you should personally:

1. Try wrong password 6 times
2. Verify logout invalidates token
3. Grep repo for passwords: `git grep -i password`

## NEXT PHASE

Phase 7 adds student management and the Streamlit dashboard shell.

---

# Phase 7 — STUDENT MANAGEMENT + DASHBOARD SHELL

> **Branch:** `feature/phase-07-students` · **Gate:** STOP — human approval required before the next phase

## Objective

Student CRUD API (soft delete, search, filters, pagination, consent field) and the Streamlit app shell: login page, sidebar navigation exactly as specified, API client, Students page.

## Why This Phase Exists

Face registration needs students to exist; the unified dashboard needs its shell early.

## Prerequisites

- Previous phase approved and merged (or branch checked out from it)

## Inputs

- Output of the previous phase
- This playbook

## Expected Outputs

- Student endpoints with RBAC and audit
- Streamlit app with login + sidebar (Dashboard / ATTENDANCE / SECURITY / SYSTEM groups; unbuilt pages show 'Coming in Phase N')
- Students page: list, search, filters, create, edit, deactivate

## Architecture

```text
Streamlit page → frontend/api_client.py (adds Bearer token, handles 401 → logout) → FastAPI /students → student_service → students table
```

## Files To Inspect

- Repository tree (`Get-ChildItem -Recurse -Depth 3`)
- README.md
- docs/ (including the project PPT/PDF and docs/PLAYBOOK.md)
- TOKEN-OPTIMIZATION.md
- docker-compose.yml
- requirements.txt, requirements-dev.txt, requirements-gpu.txt
- .env.example, .gitignore, .dockerignore, .python-version
- `git log --oneline -15` and `git status`

## Files To Create

- backend/app/api/v1/students.py
- backend/app/schemas/student.py
- backend/app/services/student_service.py
- backend/app/db/repositories/student_repo.py
- frontend/app.py
- frontend/api_client.py
- frontend/pages/*.py (placeholders for later pages)
- frontend/components/auth.py
- backend/tests/api/test_students.py
- frontend/tests/test_login_gate.py

## Files To Modify

- backend/app/api/v1/router.py
- requirements.txt (streamlit)

## Dependencies

No new dependencies.

## Environment Variables

- API_BASE_URL=http://127.0.0.1:8000/api/v1 (frontend)

## Database Changes

None.

## API Changes

`POST/GET /students`, `GET/PATCH/DELETE /students/{id}` per Section 5.3 (face endpoints come later).

## Frontend Changes

Login form; sidebar groups; Students page (table, search box, department/year filters, add/edit form with **consent checkbox**, deactivate button with confirm). Token only in `st.session_state`; auto-logout on 401.

## Implementation Sequence

1. Create branch
2. Inspect any existing frontend
3. Student repo/service/schemas (validate `student_id` regex, year 1–8)
4. Router with RBAC + audit
5. API tests
6. Streamlit shell: login, sidebar, api_client
7. Students page
8. AppTest login-gate test
9. Commit and stop

## EXACT ANTIGRAVITY PROMPT

```text
YOU ARE IMPLEMENTING: PHASE 7 — STUDENT MANAGEMENT + DASHBOARD SHELL

Follow the GLOBAL RULES (docs/PLAYBOOK.md Section 2). Work ONLY on this phase.


STEP 0 — BRANCH
  git checkout main ; git pull origin main ; git checkout -b feature/phase-07-students
  (If the branch exists, check it out instead. Never commit to main.)

STEP 1 — INSPECT FIRST (do not modify anything yet)
  - Repository tree (`Get-ChildItem -Recurse -Depth 3`)
  - README.md
  - docs/ (including the project PPT/PDF and docs/PLAYBOOK.md)
  - TOKEN-OPTIMIZATION.md
  - docker-compose.yml
  - requirements.txt, requirements-dev.txt, requirements-gpu.txt
  - .env.example, .gitignore, .dockerignore, .python-version
  - `git log --oneline -15` and `git status`
  Report briefly what already exists that is relevant to this phase. Never assume a file is missing.

OBJECTIVE
  Student CRUD API (soft delete, search, filters, pagination, consent field) and the Streamlit app shell: login page, sidebar navigation exactly as specified, API client, Students page.

STEP 2 — CREATE (only after inspection; skip anything that already exists and extend it instead)
  - backend/app/api/v1/students.py
  - backend/app/schemas/student.py
  - backend/app/services/student_service.py
  - backend/app/db/repositories/student_repo.py
  - frontend/app.py
  - frontend/api_client.py
  - frontend/pages/*.py (placeholders for later pages)
  - frontend/components/auth.py
  - backend/tests/api/test_students.py
  - frontend/tests/test_login_gate.py

STEP 3 — MODIFY
  - backend/app/api/v1/router.py
  - requirements.txt (streamlit)

DO NOT MODIFY / DO NOT DO
  - Face capture (Phase 8)
  - Hard-deleting students
  - Putting the JWT in URLs or cookies

DEPENDENCIES: none new  (resolve compatible versions, pin them, verify with `pip check`)
ENVIRONMENT VARIABLES: API_BASE_URL=http://127.0.0.1:8000/api/v1 (frontend)  (placeholders only in .env.example)

STEP 4 — IMPLEMENTATION ORDER
  1. Create branch
  2. Inspect any existing frontend
  3. Student repo/service/schemas (validate `student_id` regex, year 1–8)
  4. Router with RBAC + audit
  5. API tests
  6. Streamlit shell: login, sidebar, api_client
  7. Students page
  8. AppTest login-gate test
  9. Commit and stop

STEP 5 — TESTS (write and RUN; paste real output)
  - Create student → 201; duplicate student_id → 409
  - Invalid year/ID → 422
  - OPERATOR cannot create/edit/delete (403) but can list
  - Search by name fragment and by department/year
  - DELETE sets INACTIVE and keeps row
  - Pagination limits (size>100 rejected)
  - Audit rows created
  - Streamlit: unauthenticated visit shows only login form

STEP 6 — VERIFICATION (run these and report real results)
  uvicorn backend.app.main:app --reload --port 8000
  streamlit run frontend\app.py
  pytest backend/tests/api/test_students.py frontend/tests -v

STEP 7 — ACCEPTANCE CRITERIA (mark each ✅ / ❌ / NOT VERIFIED — never guess)
  [ ] Student CRUD tests pass
  [ ] RBAC verified
  [ ] Sidebar structure matches specification
  [ ] Consent field captured
  [ ] Audit logging works

STEP 8 — DOCUMENTATION: update README/docs for anything this phase changed; add a short entry to docs/CHANGELOG.md.

STEP 9 — GIT CHECKPOINT (only if tests pass)
  git status ; git diff   (confirm NO secrets, images, videos, .onnx, data/ content staged)
  git add . ; git commit -m "feat(students): add student CRUD API and Streamlit dashboard shell" ; git push -u origin feature/phase-07-students

STEP 10 — STOP. Print the REPORT FORMAT from the global rules and write: STOPPED AT PHASE 7 GATE — awaiting human approval. Do NOT start Phase 8.
```

## Commands

Windows PowerShell (run from the repo root unless stated):

```powershell
uvicorn backend.app.main:app --reload --port 8000
streamlit run frontend\app.py
pytest backend/tests/api/test_students.py frontend/tests -v
```

## Tests

- Create student → 201; duplicate student_id → 409
- Invalid year/ID → 422
- OPERATOR cannot create/edit/delete (403) but can list
- Search by name fragment and by department/year
- DELETE sets INACTIVE and keeps row
- Pagination limits (size>100 rejected)
- Audit rows created
- Streamlit: unauthenticated visit shows only login form

## Manual Verification

1. Log in through Streamlit
2. Create 3 students (yourself + 2 friends) — use real IDs `001`,`002`,`003`
3. Search, edit, deactivate, re-activate

## Expected Result

Working student management inside the unified dashboard shell.

## Failure Conditions

- Page content visible before login
- Operator can modify students
- Student rows hard-deleted

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| Streamlit cannot reach API | Check `API_BASE_URL`, CORS, API running |
| Session lost on refresh | Expected with `st.session_state`; acceptable — re-login |

## Acceptance Criteria

- [ ] Student CRUD tests pass
- [ ] RBAC verified
- [ ] Sidebar structure matches specification
- [ ] Consent field captured
- [ ] Audit logging works

## Git Checkpoint

```powershell
git checkout main
git pull origin main
git checkout -b feature/phase-07-students   # at the START of the phase

# after tests pass:
git status
git diff
git add .
git commit -m "feat(students): add student CRUD API and Streamlit dashboard shell"
git push -u origin feature/phase-07-students
```

Recommended commit message: `feat(students): add student CRUD API and Streamlit dashboard shell`

## HUMAN APPROVAL

Before approving, you should personally:

1. Use the UI to create your 3 students
2. Try as OPERATOR (create one via create_admin.py --role OPERATOR)

## NEXT PHASE

Phase 8 begins face registration with the laptop webcam.

---

# Phase 8 — FACE REGISTRATION (WEBCAM CAPTURE)

> **Branch:** `feature/phase-08-face-registration` · **Gate:** STOP — human approval required before the next phase

## Objective

Build the registration capture workflow: a laptop-webcam camera abstraction, registration sessions held **in memory with TTL**, MJPEG preview, guided capture of N samples (configurable; 30–50 full spec, 5 quick mode), consent enforcement.

## Why This Phase Exists

Embeddings need good, varied samples. Capture must not persist raw images (ADR-11).

## Prerequisites

- Previous phase approved and merged (or branch checked out from it)

## Inputs

- Output of the previous phase
- This playbook

## Expected Outputs

- `CameraSource` abstraction + `WebcamSource`
- Registration session API (`session` / `capture` stubs wired to validation in Phase 9)
- Streamlit 'Register Face' panel with preview and progress
- Pose/lighting prompts (front, left, right, up, down, glasses-off/on, bright, dim)

## Architecture

```text
CameraSource (abstract: open/read/close/is_open)
   └─ WebcamSource(cv2.VideoCapture(index, CAP_DSHOW))
RegistrationSessionStore (in-memory dict[session_id] → {student_id, frames[], expires_at}) — TTL 10 min, cleared on commit/cancel
Preview: GET /stream/{camera}?ticket= (MJPEG) ← POST /stream/ticket
```

## Files To Inspect

- Repository tree (`Get-ChildItem -Recurse -Depth 3`)
- README.md
- docs/ (including the project PPT/PDF and docs/PLAYBOOK.md)
- TOKEN-OPTIMIZATION.md
- docker-compose.yml
- requirements.txt, requirements-dev.txt, requirements-gpu.txt
- .env.example, .gitignore, .dockerignore, .python-version
- `git log --oneline -15` and `git status`

## Files To Create

- backend/app/cameras/source.py
- backend/app/cameras/webcam.py
- backend/app/services/registration_session.py
- backend/app/api/v1/face.py
- backend/app/api/v1/stream.py
- backend/app/schemas/face.py
- frontend/pages/2_Students.py (register-face panel) or components/face_capture.py
- backend/tests/cameras/test_webcam_mock.py
- backend/tests/api/test_face_session.py

## Files To Modify

- backend/app/api/v1/router.py
- .env.example (FACE_SAMPLES_REQUIRED, FACE_MIN_SAMPLES, WEBCAM_INDEX)

## Dependencies

No new dependencies.

## Environment Variables

- WEBCAM_INDEX=0
- FACE_SAMPLES_REQUIRED=30
- FACE_MIN_SAMPLES=5
- RETAIN_RAW_IMAGES=false
- SESSION_TTL_SECONDS=600

## Database Changes

None.

## API Changes

`POST /stream/ticket`, `GET /stream/{camera_id}`, `POST /students/{id}/face/session`, `POST .../capture`, DELETE session. Capture endpoint in this phase only grabs a frame and stores it in the session; validation arrives in Phase 9.

## Frontend Changes

Student row action 'Register Face' → live preview, pose prompt text, progress bar `n/required`, Cancel button. Block with a message if the student has no consent.

## Implementation Sequence

1. Create branch
2. Inspect for existing camera code
3. Implement `CameraSource` + `WebcamSource` with reconnect-safe open/close
4. Ticket + MJPEG endpoint
5. Session store with TTL cleanup
6. Session/capture endpoints with consent check
7. Streamlit capture panel
8. Tests with mocked camera
9. Manual webcam run
10. Commit and stop

## EXACT ANTIGRAVITY PROMPT

```text
YOU ARE IMPLEMENTING: PHASE 8 — FACE REGISTRATION (WEBCAM CAPTURE)

Follow the GLOBAL RULES (docs/PLAYBOOK.md Section 2). Work ONLY on this phase.


STEP 0 — BRANCH
  git checkout main ; git pull origin main ; git checkout -b feature/phase-08-face-registration
  (If the branch exists, check it out instead. Never commit to main.)

STEP 1 — INSPECT FIRST (do not modify anything yet)
  - Repository tree (`Get-ChildItem -Recurse -Depth 3`)
  - README.md
  - docs/ (including the project PPT/PDF and docs/PLAYBOOK.md)
  - TOKEN-OPTIMIZATION.md
  - docker-compose.yml
  - requirements.txt, requirements-dev.txt, requirements-gpu.txt
  - .env.example, .gitignore, .dockerignore, .python-version
  - `git log --oneline -15` and `git status`
  Report briefly what already exists that is relevant to this phase. Never assume a file is missing.

OBJECTIVE
  Build the registration capture workflow: a laptop-webcam camera abstraction, registration sessions held **in memory with TTL**, MJPEG preview, guided capture of N samples (configurable; 30–50 full spec, 5 quick mode), consent enforcement.

STEP 2 — CREATE (only after inspection; skip anything that already exists and extend it instead)
  - backend/app/cameras/source.py
  - backend/app/cameras/webcam.py
  - backend/app/services/registration_session.py
  - backend/app/api/v1/face.py
  - backend/app/api/v1/stream.py
  - backend/app/schemas/face.py
  - frontend/pages/2_Students.py (register-face panel) or components/face_capture.py
  - backend/tests/cameras/test_webcam_mock.py
  - backend/tests/api/test_face_session.py

STEP 3 — MODIFY
  - backend/app/api/v1/router.py
  - .env.example (FACE_SAMPLES_REQUIRED, FACE_MIN_SAMPLES, WEBCAM_INDEX)

DO NOT MODIFY / DO NOT DO
  - Write frames to disk (unless `RETAIN_RAW_IMAGES=true`, which stays false)
  - Run detection/embedding yet
  - Allow stream access without a ticket

DEPENDENCIES: none new  (resolve compatible versions, pin them, verify with `pip check`)
ENVIRONMENT VARIABLES: WEBCAM_INDEX=0; FACE_SAMPLES_REQUIRED=30; FACE_MIN_SAMPLES=5; RETAIN_RAW_IMAGES=false; SESSION_TTL_SECONDS=600  (placeholders only in .env.example)

STEP 4 — IMPLEMENTATION ORDER
  1. Create branch
  2. Inspect for existing camera code
  3. Implement `CameraSource` + `WebcamSource` with reconnect-safe open/close
  4. Ticket + MJPEG endpoint
  5. Session store with TTL cleanup
  6. Session/capture endpoints with consent check
  7. Streamlit capture panel
  8. Tests with mocked camera
  9. Manual webcam run
  10. Commit and stop

SPECIFIC REQUIREMENTS
  - Release the camera on session end/cancel/exception; never leak `VideoCapture` handles
  - One physical webcam = one owner: return 409 if the live attendance worker holds it
  - Stream ticket: random 32 bytes, 60 s expiry, scoped to one camera and one user
  - Use `cv2.CAP_DSHOW` on Windows; fallback to default backend
  - Mock `cv2.VideoCapture` in tests — CI must not need a camera

STEP 5 — TESTS (write and RUN; paste real output)
  - Session creation without consent → 4xx
  - Ticket expires after 60 s; ticket for camera A cannot open camera B
  - Stream without ticket → 401
  - Session expires and frames are dropped
  - Camera released after cancel (mock `release()` called)
  - No files written under `data/` after a session (assert)
  - Two concurrent sessions for the same camera → 409

STEP 6 — VERIFICATION (run these and report real results)
  pytest backend/tests/cameras backend/tests/api/test_face_session.py -v
  uvicorn backend.app.main:app --port 8000
  streamlit run frontend\app.py

STEP 7 — ACCEPTANCE CRITERIA (mark each ✅ / ❌ / NOT VERIFIED — never guess)
  [ ] Webcam preview works
  [ ] Sessions in memory only with TTL
  [ ] Consent enforced
  [ ] Ticket security tested
  [ ] Camera released properly (verified)

STEP 8 — DOCUMENTATION: update README/docs for anything this phase changed; add a short entry to docs/CHANGELOG.md.

STEP 9 — GIT CHECKPOINT (only if tests pass)
  git status ; git diff   (confirm NO secrets, images, videos, .onnx, data/ content staged)
  git add . ; git commit -m "feat(face): add webcam source, registration sessions and MJPEG preview" ; git push -u origin feature/phase-08-face-registration

STEP 10 — STOP. Print the REPORT FORMAT from the global rules and write: STOPPED AT PHASE 8 GATE — awaiting human approval. Do NOT start Phase 9.
```

## Commands

Windows PowerShell (run from the repo root unless stated):

```powershell
pytest backend/tests/cameras backend/tests/api/test_face_session.py -v
uvicorn backend.app.main:app --port 8000
streamlit run frontend\app.py
```

## Tests

- Session creation without consent → 4xx
- Ticket expires after 60 s; ticket for camera A cannot open camera B
- Stream without ticket → 401
- Session expires and frames are dropped
- Camera released after cancel (mock `release()` called)
- No files written under `data/` after a session (assert)
- Two concurrent sessions for the same camera → 409

## Manual Verification

1. Start registration for student 001 and see yourself in the preview
2. Capture 5 frames (quick mode) following pose prompts
3. Cancel and verify the webcam LED turns off

## Expected Result

Webcam preview and guided capture work; no images are stored on disk.

## Failure Conditions

- Camera stays on after cancel
- Frames saved to disk
- Stream open without ticket

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| Black preview | Camera index/driver; try `WEBCAM_INDEX=1`; close other apps |
| MJPEG not showing in Streamlit | Use `st.markdown('<img src=...>', unsafe_allow_html=True)` only with the ticket URL; allow the API origin |
| Laggy preview | Lower resolution (640x480) and JPEG quality 70 |

## Acceptance Criteria

- [ ] Webcam preview works
- [ ] Sessions in memory only with TTL
- [ ] Consent enforced
- [ ] Ticket security tested
- [ ] Camera released properly (verified)

## Git Checkpoint

```powershell
git checkout main
git pull origin main
git checkout -b feature/phase-08-face-registration   # at the START of the phase

# after tests pass:
git status
git diff
git add .
git commit -m "feat(face): add webcam source, registration sessions and MJPEG preview"
git push -u origin feature/phase-08-face-registration
```

Recommended commit message: `feat(face): add webcam source, registration sessions and MJPEG preview`

## HUMAN APPROVAL

Before approving, you should personally:

1. Run a capture session and confirm `data/` has no images
2. Confirm the webcam light turns off

## NEXT PHASE

Phase 9 validates and preprocesses captured frames.

---

# Phase 9 — FACE PREPROCESSING & IMAGE VALIDATION

> **Branch:** `feature/phase-09-preprocessing` · **Gate:** STOP — human approval required before the next phase

## Objective

Implement image validation and quality preprocessing: decode/format/size checks, blur (Laplacian variance), brightness range, minimum resolution, optional CLAHE/denoise/flip augmentation (default OFF), and uploaded-image security checks (magic bytes, size limit).

## Why This Phase Exists

Bad samples poison recognition. The PPT lists alignment, resizing, brightness normalisation, noise reduction and augmentation; here they are implemented as measured, configurable options — alignment itself is done by InsightFace in Phase 11.

## Prerequisites

- Previous phase approved and merged (or branch checked out from it)

## Inputs

- Output of the previous phase
- This playbook

## Expected Outputs

- `vision/preprocess.py` with pure functions returning `ValidationResult(ok, reason, metrics)`
- Reasons: `INVALID_IMAGE`, `TOO_SMALL`, `TOO_BLURRY`, `TOO_DARK`, `TOO_BRIGHT`
- Safe upload decoder used by `/recognition/identify` later

## Architecture

```text
bytes/ndarray → validate_image() → quality_metrics(blur, brightness) → optional enhance() → ndarray BGR
```
Pure functions, no model, no DB.

## Files To Inspect

- Repository tree (`Get-ChildItem -Recurse -Depth 3`)
- README.md
- docs/ (including the project PPT/PDF and docs/PLAYBOOK.md)
- TOKEN-OPTIMIZATION.md
- docker-compose.yml
- requirements.txt, requirements-dev.txt, requirements-gpu.txt
- .env.example, .gitignore, .dockerignore, .python-version
- `git log --oneline -15` and `git status`

## Files To Create

- backend/app/vision/__init__.py
- backend/app/vision/preprocess.py
- backend/app/vision/image_io.py (safe decode: magic bytes, ≤5 MB, ≤4096 px, decompression-bomb guard)
- backend/tests/vision/test_preprocess.py

## Files To Modify

- backend/app/services/registration_session.py (call validators in capture)
- .env.example

## Dependencies

No new dependencies.

## Environment Variables

- MIN_IMAGE_SIDE=240
- BLUR_MIN_LAPLACIAN=60
- BRIGHTNESS_MIN=40
- BRIGHTNESS_MAX=220
- ENABLE_CLAHE=false
- ENABLE_AUGMENT_FLIP=false
- MAX_UPLOAD_BYTES=5242880

## Database Changes

None.

## API Changes

None.

## Frontend Changes

None.

## Implementation Sequence

1. Create branch
2. Implement `image_io` safe decode
3. Implement metrics and validators
4. Implement optional enhancements behind flags
5. Wire validators into capture (reject with reason)
6. Synthetic-image tests
7. Commit and stop

## EXACT ANTIGRAVITY PROMPT

```text
YOU ARE IMPLEMENTING: PHASE 9 — FACE PREPROCESSING & IMAGE VALIDATION

Follow the GLOBAL RULES (docs/PLAYBOOK.md Section 2). Work ONLY on this phase.


STEP 0 — BRANCH
  git checkout main ; git pull origin main ; git checkout -b feature/phase-09-preprocessing
  (If the branch exists, check it out instead. Never commit to main.)

STEP 1 — INSPECT FIRST (do not modify anything yet)
  - Repository tree (`Get-ChildItem -Recurse -Depth 3`)
  - README.md
  - docs/ (including the project PPT/PDF and docs/PLAYBOOK.md)
  - TOKEN-OPTIMIZATION.md
  - docker-compose.yml
  - requirements.txt, requirements-dev.txt, requirements-gpu.txt
  - .env.example, .gitignore, .dockerignore, .python-version
  - `git log --oneline -15` and `git status`
  Report briefly what already exists that is relevant to this phase. Never assume a file is missing.

OBJECTIVE
  Implement image validation and quality preprocessing: decode/format/size checks, blur (Laplacian variance), brightness range, minimum resolution, optional CLAHE/denoise/flip augmentation (default OFF), and uploaded-image security checks (magic bytes, size limit).

STEP 2 — CREATE (only after inspection; skip anything that already exists and extend it instead)
  - backend/app/vision/__init__.py
  - backend/app/vision/preprocess.py
  - backend/app/vision/image_io.py (safe decode: magic bytes, ≤5 MB, ≤4096 px, decompression-bomb guard)
  - backend/tests/vision/test_preprocess.py

STEP 3 — MODIFY
  - backend/app/services/registration_session.py (call validators in capture)
  - .env.example

DO NOT MODIFY / DO NOT DO
  - Make CLAHE/augmentation default ON
  - Trust the file extension
  - Use PIL/cv2 decode on unchecked giant images

DEPENDENCIES: none new  (resolve compatible versions, pin them, verify with `pip check`)
ENVIRONMENT VARIABLES: MIN_IMAGE_SIDE=240; BLUR_MIN_LAPLACIAN=60; BRIGHTNESS_MIN=40; BRIGHTNESS_MAX=220; ENABLE_CLAHE=false; ENABLE_AUGMENT_FLIP=false; MAX_UPLOAD_BYTES=5242880  (placeholders only in .env.example)

STEP 4 — IMPLEMENTATION ORDER
  1. Create branch
  2. Implement `image_io` safe decode
  3. Implement metrics and validators
  4. Implement optional enhancements behind flags
  5. Wire validators into capture (reject with reason)
  6. Synthetic-image tests
  7. Commit and stop

SPECIFIC REQUIREMENTS
  - Thresholds are starting values; document that they must be tuned with the real webcam (Phase 18)
  - Tests generate synthetic images with numpy/OpenCV (noise, blur, black frame) — no real faces committed

STEP 5 — TESTS (write and RUN; paste real output)
  - Random bytes → INVALID_IMAGE
  - PNG disguised as .jpg handled by magic bytes
  - 50×50 image → TOO_SMALL
  - Gaussian-blurred image → TOO_BLURRY; sharp noise image passes blur
  - Black image → TOO_DARK; white → TOO_BRIGHT
  - Oversized upload rejected
  - Enhancements off by default (assert no pixel change)
  - CLAHE on → output shape unchanged

STEP 6 — VERIFICATION (run these and report real results)
  pytest backend/tests/vision/test_preprocess.py -v
  ruff check backend

STEP 7 — ACCEPTANCE CRITERIA (mark each ✅ / ❌ / NOT VERIFIED — never guess)
  [ ] All validators unit-tested
  [ ] Reasons surfaced to UI
  [ ] Flags default OFF
  [ ] Upload guard tested

STEP 8 — DOCUMENTATION: update README/docs for anything this phase changed; add a short entry to docs/CHANGELOG.md.

STEP 9 — GIT CHECKPOINT (only if tests pass)
  git status ; git diff   (confirm NO secrets, images, videos, .onnx, data/ content staged)
  git add . ; git commit -m "feat(vision): add image validation, quality metrics and optional preprocessing" ; git push -u origin feature/phase-09-preprocessing

STEP 10 — STOP. Print the REPORT FORMAT from the global rules and write: STOPPED AT PHASE 9 GATE — awaiting human approval. Do NOT start Phase 10.
```

## Commands

Windows PowerShell (run from the repo root unless stated):

```powershell
pytest backend/tests/vision/test_preprocess.py -v
ruff check backend
```

## Tests

- Random bytes → INVALID_IMAGE
- PNG disguised as .jpg handled by magic bytes
- 50×50 image → TOO_SMALL
- Gaussian-blurred image → TOO_BLURRY; sharp noise image passes blur
- Black image → TOO_DARK; white → TOO_BRIGHT
- Oversized upload rejected
- Enhancements off by default (assert no pixel change)
- CLAHE on → output shape unchanged

## Manual Verification

1. Run capture in a dark room and while shaking the laptop; see rejection reasons in the UI

## Expected Result

Poor frames are rejected with clear reasons before any model runs.

## Failure Conditions

- Validation depends on extension
- Enhancements enabled by default

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| Everything rejected as blurry | Lower `BLUR_MIN_LAPLACIAN` after observing real values logged at DEBUG |
| Decompression-bomb error | Expected for huge images; keep guard |

## Acceptance Criteria

- [ ] All validators unit-tested
- [ ] Reasons surfaced to UI
- [ ] Flags default OFF
- [ ] Upload guard tested

## Git Checkpoint

```powershell
git checkout main
git pull origin main
git checkout -b feature/phase-09-preprocessing   # at the START of the phase

# after tests pass:
git status
git diff
git add .
git commit -m "feat(vision): add image validation, quality metrics and optional preprocessing"
git push -u origin feature/phase-09-preprocessing
```

Recommended commit message: `feat(vision): add image validation, quality metrics and optional preprocessing`

## HUMAN APPROVAL

Before approving, you should personally:

1. Watch rejection reasons appear when you cover the camera / blur it

## NEXT PHASE

Phase 10 adds face detection (no face / multiple faces).

---

# Phase 10 — FACE DETECTION

> **Branch:** `feature/phase-10-face-detection` · **Gate:** STOP — human approval required before the next phase

## Objective

Load the InsightFace `buffalo_l` detector **once** (singleton `ModelRegistry`, CPU) and implement `detect_faces(frame)` returning bbox, landmarks and score. Integrate 'no face' and 'multiple faces' rejection into registration capture.

## Why This Phase Exists

Detection is the first stage of the shared AI engine for both modules.

## Prerequisites

- Previous phase approved and merged (or branch checked out from it)

## Inputs

- Output of the previous phase
- This playbook

## Expected Outputs

- `vision/model_registry.py`, `vision/detector.py`
- Capture now rejects NO_FACE, MULTIPLE_FACES, FACE_TOO_SMALL
- `scripts/check_models.py` that downloads/loads weights into `INSIGHTFACE_HOME` (outside repo)

## Architecture

```text
ModelRegistry.get() → FaceAnalysis(name=buffalo_l, providers=[CPUExecutionProvider], allowed_modules=['detection'])
detect_faces(frame) → [Face(bbox, kps, det_score)]
```
Thread-safe lazy singleton; `prepare(ctx_id=-1, det_size=(640,640))`.

## Files To Inspect

- Repository tree (`Get-ChildItem -Recurse -Depth 3`)
- README.md
- docs/ (including the project PPT/PDF and docs/PLAYBOOK.md)
- TOKEN-OPTIMIZATION.md
- docker-compose.yml
- requirements.txt, requirements-dev.txt, requirements-gpu.txt
- .env.example, .gitignore, .dockerignore, .python-version
- `git log --oneline -15` and `git status`

## Files To Create

- backend/app/vision/model_registry.py
- backend/app/vision/detector.py
- scripts/check_models.py
- backend/tests/vision/test_detector.py

## Files To Modify

- backend/app/services/registration_session.py
- .env.example

## Dependencies

No new dependencies.

## Environment Variables

- INSIGHTFACE_MODEL=buffalo_l
- INSIGHTFACE_HOME
- DET_SIZE=640
- DET_THRESHOLD=0.5
- MIN_FACE_PIXELS=80
- DEVICE=cpu

## Database Changes

None.

## API Changes

None.

## Frontend Changes

None.

## Implementation Sequence

1. Create branch
2. Implement ModelRegistry singleton with lock
3. Implement detector wrapper and dataclass
4. Add size/score filters
5. Integrate into capture (reasons NO_FACE / MULTIPLE_FACES / FACE_TOO_SMALL)
6. `check_models.py`
7. Tests (singleton identity test: two `get()` calls return the same object; load counter == 1)
8. Measure and log detection latency (DEBUG)
9. Commit and stop

## EXACT ANTIGRAVITY PROMPT

```text
YOU ARE IMPLEMENTING: PHASE 10 — FACE DETECTION

Follow the GLOBAL RULES (docs/PLAYBOOK.md Section 2). Work ONLY on this phase.


STEP 0 — BRANCH
  git checkout main ; git pull origin main ; git checkout -b feature/phase-10-face-detection
  (If the branch exists, check it out instead. Never commit to main.)

STEP 1 — INSPECT FIRST (do not modify anything yet)
  - Repository tree (`Get-ChildItem -Recurse -Depth 3`)
  - README.md
  - docs/ (including the project PPT/PDF and docs/PLAYBOOK.md)
  - TOKEN-OPTIMIZATION.md
  - docker-compose.yml
  - requirements.txt, requirements-dev.txt, requirements-gpu.txt
  - .env.example, .gitignore, .dockerignore, .python-version
  - `git log --oneline -15` and `git status`
  Report briefly what already exists that is relevant to this phase. Never assume a file is missing.

OBJECTIVE
  Load the InsightFace `buffalo_l` detector **once** (singleton `ModelRegistry`, CPU) and implement `detect_faces(frame)` returning bbox, landmarks and score. Integrate 'no face' and 'multiple faces' rejection into registration capture.

STEP 2 — CREATE (only after inspection; skip anything that already exists and extend it instead)
  - backend/app/vision/model_registry.py
  - backend/app/vision/detector.py
  - scripts/check_models.py
  - backend/tests/vision/test_detector.py

STEP 3 — MODIFY
  - backend/app/services/registration_session.py
  - .env.example

DO NOT MODIFY / DO NOT DO
  - Instantiate the model per frame or per request
  - Commit weights
  - Enable the recognition module yet

DEPENDENCIES: none new  (resolve compatible versions, pin them, verify with `pip check`)
ENVIRONMENT VARIABLES: INSIGHTFACE_MODEL=buffalo_l; INSIGHTFACE_HOME; DET_SIZE=640; DET_THRESHOLD=0.5; MIN_FACE_PIXELS=80; DEVICE=cpu  (placeholders only in .env.example)

STEP 4 — IMPLEMENTATION ORDER
  1. Create branch
  2. Implement ModelRegistry singleton with lock
  3. Implement detector wrapper and dataclass
  4. Add size/score filters
  5. Integrate into capture (reasons NO_FACE / MULTIPLE_FACES / FACE_TOO_SMALL)
  6. `check_models.py`
  7. Tests (singleton identity test: two `get()` calls return the same object; load counter == 1)
  8. Measure and log detection latency (DEBUG)
  9. Commit and stop

SPECIFIC REQUIREMENTS
  - First run downloads ~280 MB of weights — warn the user; the download needs internet (outside the sandbox allowlist this may fail: report NOT VERIFIED if blocked)
  - Log load time once
  - Detector tests use a LOCAL fixture from `tests/fixtures_local/` (gitignored) — `pytest.skip` with a clear message if absent; plus tests with synthetic blank images (expect zero faces)

STEP 5 — TESTS (write and RUN; paste real output)
  - Model singleton: loaded exactly once across 100 calls
  - Blank frame → zero faces → NO_FACE
  - Local fixture with one face → 1 detection with bbox inside image
  - Local fixture with two faces → MULTIPLE_FACES
  - Tiny face → FACE_TOO_SMALL
  - `DEVICE=cpu` uses CPUExecutionProvider only

STEP 6 — VERIFICATION (run these and report real results)
  python scripts\check_models.py
  pytest backend/tests/vision/test_detector.py -v -rs
  streamlit run frontend\app.py   # register-face capture now rejects no-face / multi-face

STEP 7 — ACCEPTANCE CRITERIA (mark each ✅ / ❌ / NOT VERIFIED — never guess)
  [ ] Singleton verified by test
  [ ] No/multiple/small face handled
  [ ] Weights outside repo
  [ ] Latency logged
  [ ] Skips documented for missing local fixtures

STEP 8 — DOCUMENTATION: update README/docs for anything this phase changed; add a short entry to docs/CHANGELOG.md.

STEP 9 — GIT CHECKPOINT (only if tests pass)
  git status ; git diff   (confirm NO secrets, images, videos, .onnx, data/ content staged)
  git add . ; git commit -m "feat(vision): add InsightFace face detector with singleton model registry" ; git push -u origin feature/phase-10-face-detection

STEP 10 — STOP. Print the REPORT FORMAT from the global rules and write: STOPPED AT PHASE 10 GATE — awaiting human approval. Do NOT start Phase 11.
```

## Commands

Windows PowerShell (run from the repo root unless stated):

```powershell
python scripts\check_models.py
pytest backend/tests/vision/test_detector.py -v -rs
streamlit run frontend\app.py   # register-face capture now rejects no-face / multi-face
```

## Tests

- Model singleton: loaded exactly once across 100 calls
- Blank frame → zero faces → NO_FACE
- Local fixture with one face → 1 detection with bbox inside image
- Local fixture with two faces → MULTIPLE_FACES
- Tiny face → FACE_TOO_SMALL
- `DEVICE=cpu` uses CPUExecutionProvider only

## Manual Verification

1. Capture with your face: accepted. Cover camera: NO_FACE. Have a friend join: MULTIPLE_FACES. Step far back: FACE_TOO_SMALL

## Expected Result

Reliable single-face validation with the model loaded once.

## Failure Conditions

- Model reloaded per frame
- Weights inside repo
- Multiple faces accepted

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| Weight download blocked/slow | Download manually to `%USERPROFILE%\.insightface\models\buffalo_l` and rerun |
| Very slow detection | Lower `DET_SIZE` to 320–480 and measure |
| `onnxruntime` provider warnings | Safe if CPUExecutionProvider selected |

## Acceptance Criteria

- [ ] Singleton verified by test
- [ ] No/multiple/small face handled
- [ ] Weights outside repo
- [ ] Latency logged
- [ ] Skips documented for missing local fixtures

## Git Checkpoint

```powershell
git checkout main
git pull origin main
git checkout -b feature/phase-10-face-detection   # at the START of the phase

# after tests pass:
git status
git diff
git add .
git commit -m "feat(vision): add InsightFace face detector with singleton model registry"
git push -u origin feature/phase-10-face-detection
```

Recommended commit message: `feat(vision): add InsightFace face detector with singleton model registry`

## HUMAN APPROVAL

Before approving, you should personally:

1. Try the 4 manual cases yourself

## NEXT PHASE

Phase 11 adds ArcFace embeddings.

---

# Phase 11 — FACE EMBEDDINGS (INSIGHTFACE / ARCFACE)

> **Branch:** `feature/phase-11-embeddings` · **Gate:** STOP — human approval required before the next phase

## Objective

Enable the ArcFace recognition module (`w600k_r50`, 512-d) and implement `embed_face(frame, face)` returning an L2-normalised float32 vector. Add registration-time consistency checks.

## Why This Phase Exists

Embeddings are the core biometric representation used by both attendance and security.

## Prerequisites

- Previous phase approved and merged (or branch checked out from it)

## Inputs

- Output of the previous phase
- This playbook

## Expected Outputs

- `vision/embedder.py`
- Embedding dimension/norm guarantees
- Sample consistency check (cosine to median ≥ 0.5)
- `scripts/bench_embedding.py` (measures latency; no claims)

## Architecture

```text
frame → detect (SCRFD) → norm_crop (InsightFace alignment) → ArcFace R50 → normed_embedding (512,) float32
```
`ModelRegistry` now loads detection+recognition modules once.

## Files To Inspect

- Repository tree (`Get-ChildItem -Recurse -Depth 3`)
- README.md
- docs/ (including the project PPT/PDF and docs/PLAYBOOK.md)
- TOKEN-OPTIMIZATION.md
- docker-compose.yml
- requirements.txt, requirements-dev.txt, requirements-gpu.txt
- .env.example, .gitignore, .dockerignore, .python-version
- `git log --oneline -15` and `git status`

## Files To Create

- backend/app/vision/embedder.py
- backend/app/vision/quality.py (consistency check)
- scripts/bench_embedding.py
- backend/tests/vision/test_embedder.py

## Files To Modify

- backend/app/vision/model_registry.py (allowed_modules detection+recognition)
- backend/app/services/registration_session.py (compute embeddings at commit)

## Dependencies

No new dependencies.

## Environment Variables

No new variables.

## Database Changes

None.

## API Changes

None.

## Frontend Changes

None.

## Implementation Sequence

1. Create branch
2. Extend registry to load recognition model once
3. Implement embedder + dataclass `EmbeddingResult(vector, det_score, quality)`
4. Implement consistency check
5. Benchmark script
6. Tests (same-person pair similarity high vs different-person pair — local fixtures; skip if absent)
7. Commit and stop

## EXACT ANTIGRAVITY PROMPT

```text
YOU ARE IMPLEMENTING: PHASE 11 — FACE EMBEDDINGS (INSIGHTFACE / ARCFACE)

Follow the GLOBAL RULES (docs/PLAYBOOK.md Section 2). Work ONLY on this phase.


STEP 0 — BRANCH
  git checkout main ; git pull origin main ; git checkout -b feature/phase-11-embeddings
  (If the branch exists, check it out instead. Never commit to main.)

STEP 1 — INSPECT FIRST (do not modify anything yet)
  - Repository tree (`Get-ChildItem -Recurse -Depth 3`)
  - README.md
  - docs/ (including the project PPT/PDF and docs/PLAYBOOK.md)
  - TOKEN-OPTIMIZATION.md
  - docker-compose.yml
  - requirements.txt, requirements-dev.txt, requirements-gpu.txt
  - .env.example, .gitignore, .dockerignore, .python-version
  - `git log --oneline -15` and `git status`
  Report briefly what already exists that is relevant to this phase. Never assume a file is missing.

OBJECTIVE
  Enable the ArcFace recognition module (`w600k_r50`, 512-d) and implement `embed_face(frame, face)` returning an L2-normalised float32 vector. Add registration-time consistency checks.

STEP 2 — CREATE (only after inspection; skip anything that already exists and extend it instead)
  - backend/app/vision/embedder.py
  - backend/app/vision/quality.py (consistency check)
  - scripts/bench_embedding.py
  - backend/tests/vision/test_embedder.py

STEP 3 — MODIFY
  - backend/app/vision/model_registry.py (allowed_modules detection+recognition)
  - backend/app/services/registration_session.py (compute embeddings at commit)

DO NOT MODIFY / DO NOT DO
  - Store embeddings yet (Phase 12)
  - Log or print embedding values
  - Return embeddings through any API

DEPENDENCIES: none new  (resolve compatible versions, pin them, verify with `pip check`)
ENVIRONMENT VARIABLES: none new  (placeholders only in .env.example)

STEP 4 — IMPLEMENTATION ORDER
  1. Create branch
  2. Extend registry to load recognition model once
  3. Implement embedder + dataclass `EmbeddingResult(vector, det_score, quality)`
  4. Implement consistency check
  5. Benchmark script
  6. Tests (same-person pair similarity high vs different-person pair — local fixtures; skip if absent)
  7. Commit and stop

SPECIFIC REQUIREMENTS
  - Assert `embedding.shape == (512,)`, dtype float32, `abs(norm-1) < 1e-3`
  - Pick the largest face if the caller allows; registration still requires exactly one face
  - Embeddings computed in memory only

STEP 5 — TESTS (write and RUN; paste real output)
  - Shape/dtype/norm assertions on a local fixture
  - Embedding of same image twice is identical (deterministic)
  - Genuine-pair similarity > impostor-pair similarity (local fixtures; skipped otherwise)
  - Consistency check rejects a sample from a different person
  - Model loaded once

STEP 6 — VERIFICATION (run these and report real results)
  python scripts\bench_embedding.py --frames 50
  pytest backend/tests/vision/test_embedder.py -v -rs

STEP 7 — ACCEPTANCE CRITERIA (mark each ✅ / ❌ / NOT VERIFIED — never guess)
  [ ] Embeddings verified (shape/norm)
  [ ] Consistency check tested
  [ ] Benchmark runs and prints real numbers
  [ ] No embedding leakage in logs

STEP 8 — DOCUMENTATION: update README/docs for anything this phase changed; add a short entry to docs/CHANGELOG.md.

STEP 9 — GIT CHECKPOINT (only if tests pass)
  git status ; git diff   (confirm NO secrets, images, videos, .onnx, data/ content staged)
  git add . ; git commit -m "feat(vision): add ArcFace embedding generation with consistency checks" ; git push -u origin feature/phase-11-embeddings

STEP 10 — STOP. Print the REPORT FORMAT from the global rules and write: STOPPED AT PHASE 11 GATE — awaiting human approval. Do NOT start Phase 12.
```

## Commands

Windows PowerShell (run from the repo root unless stated):

```powershell
python scripts\bench_embedding.py --frames 50
pytest backend/tests/vision/test_embedder.py -v -rs
```

## Tests

- Shape/dtype/norm assertions on a local fixture
- Embedding of same image twice is identical (deterministic)
- Genuine-pair similarity > impostor-pair similarity (local fixtures; skipped otherwise)
- Consistency check rejects a sample from a different person
- Model loaded once

## Manual Verification

1. Run the benchmark and note p50/p95 latency for your laptop (record, do not claim)

## Expected Result

Deterministic 512-d normalised embeddings; consistency check works.

## Failure Conditions

- Wrong shape/norm
- Embeddings logged
- Model reloaded

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| Recognition model fails to load | Check `buffalo_l` contains `w600k_r50.onnx` in INSIGHTFACE_HOME |
| Very slow embeddings | Expected on CPU (~tens of ms/face); measure before optimizing |

## Acceptance Criteria

- [ ] Embeddings verified (shape/norm)
- [ ] Consistency check tested
- [ ] Benchmark runs and prints real numbers
- [ ] No embedding leakage in logs

## Git Checkpoint

```powershell
git checkout main
git pull origin main
git checkout -b feature/phase-11-embeddings   # at the START of the phase

# after tests pass:
git status
git diff
git add .
git commit -m "feat(vision): add ArcFace embedding generation with consistency checks"
git push -u origin feature/phase-11-embeddings
```

Recommended commit message: `feat(vision): add ArcFace embedding generation with consistency checks`

## HUMAN APPROVAL

Before approving, you should personally:

1. Run benchmark and note numbers
2. Confirm no vector values in logs: search logs for '0.'-style arrays

## NEXT PHASE

Phase 12 persists embeddings in pgvector.

---

# Phase 12 — VECTOR STORAGE (PGVECTOR)

> **Branch:** `feature/phase-12-vector-storage` · **Gate:** STOP — human approval required before the next phase

## Objective

Persist embeddings in `face_embeddings` and implement the repository for insert, deactivate, delete and nearest-neighbour search; finish the registration commit/status/delete endpoints.

## Why This Phase Exists

Recognition quality and speed depend on correct vector storage and indexing.

## Prerequisites

- Previous phase approved and merged (or branch checked out from it)

## Inputs

- Output of the previous phase
- This playbook

## Expected Outputs

- `face_repo` with `add_embeddings`, `deactivate_for_owner`, `delete_for_owner`, `nearest(query, k)`
- Commit endpoint storing embeddings atomically
- Re-registration (replace old embeddings in one transaction)

## Architecture

```sql
SELECT owner ids, 1 - (embedding <=> :q) AS similarity
FROM face_embeddings WHERE is_active = true
ORDER BY embedding <=> :q LIMIT :k;
```
HNSW index from Phase 4; set `hnsw.ef_search` (default 40) per query/session.

## Files To Inspect

- Repository tree (`Get-ChildItem -Recurse -Depth 3`)
- README.md
- docs/ (including the project PPT/PDF and docs/PLAYBOOK.md)
- TOKEN-OPTIMIZATION.md
- docker-compose.yml
- requirements.txt, requirements-dev.txt, requirements-gpu.txt
- .env.example, .gitignore, .dockerignore, .python-version
- `git log --oneline -15` and `git status`

## Files To Create

- backend/app/db/repositories/face_repo.py
- backend/app/services/face_service.py
- backend/tests/db/test_face_repo.py
- backend/tests/api/test_face_commit.py

## Files To Modify

- backend/app/api/v1/face.py (commit, status, delete)
- backend/app/services/registration_session.py

## Dependencies

No new dependencies.

## Environment Variables

No new variables.

## Database Changes

No schema change. Verify index usage with `EXPLAIN` (sequential scan acceptable at tiny sizes; document).

## API Changes

`POST /students/{id}/face/session/{sid}/commit`, `GET /students/{id}/face/status`, `DELETE /students/{id}/face`. Responses contain counts only — never vectors.

## Frontend Changes

None.

## Implementation Sequence

1. Create branch
2. Write repository with parameterised pgvector queries
3. Service orchestrating session → embeddings → repo
4. Endpoints + schemas (no vector fields)
5. Tests incl. rollback on failure
6. `EXPLAIN` documentation
7. Commit and stop

## EXACT ANTIGRAVITY PROMPT

```text
YOU ARE IMPLEMENTING: PHASE 12 — VECTOR STORAGE (PGVECTOR)

Follow the GLOBAL RULES (docs/PLAYBOOK.md Section 2). Work ONLY on this phase.


STEP 0 — BRANCH
  git checkout main ; git pull origin main ; git checkout -b feature/phase-12-vector-storage
  (If the branch exists, check it out instead. Never commit to main.)

STEP 1 — INSPECT FIRST (do not modify anything yet)
  - Repository tree (`Get-ChildItem -Recurse -Depth 3`)
  - README.md
  - docs/ (including the project PPT/PDF and docs/PLAYBOOK.md)
  - TOKEN-OPTIMIZATION.md
  - docker-compose.yml
  - requirements.txt, requirements-dev.txt, requirements-gpu.txt
  - .env.example, .gitignore, .dockerignore, .python-version
  - `git log --oneline -15` and `git status`
  Report briefly what already exists that is relevant to this phase. Never assume a file is missing.

OBJECTIVE
  Persist embeddings in `face_embeddings` and implement the repository for insert, deactivate, delete and nearest-neighbour search; finish the registration commit/status/delete endpoints.

STEP 2 — CREATE (only after inspection; skip anything that already exists and extend it instead)
  - backend/app/db/repositories/face_repo.py
  - backend/app/services/face_service.py
  - backend/tests/db/test_face_repo.py
  - backend/tests/api/test_face_commit.py

STEP 3 — MODIFY
  - backend/app/api/v1/face.py (commit, status, delete)
  - backend/app/services/registration_session.py

DO NOT MODIFY / DO NOT DO
  - Return embeddings in any response/schema
  - Delete attendance history on re-registration
  - Update embeddings row-by-row outside a transaction

DEPENDENCIES: none new  (resolve compatible versions, pin them, verify with `pip check`)
ENVIRONMENT VARIABLES: none new  (placeholders only in .env.example)

STEP 4 — IMPLEMENTATION ORDER
  1. Create branch
  2. Write repository with parameterised pgvector queries
  3. Service orchestrating session → embeddings → repo
  4. Endpoints + schemas (no vector fields)
  5. Tests incl. rollback on failure
  6. `EXPLAIN` documentation
  7. Commit and stop

SPECIFIC REQUIREMENTS
  - Commit: validate ≥ `FACE_MIN_SAMPLES`; run consistency check; transaction = deactivate old + insert new; audit `FACE_REGISTER` (details: count only)
  - Sessions cleared from memory after commit

STEP 5 — TESTS (write and RUN; paste real output)
  - Insert N embeddings and retrieve nearest = itself with similarity ≈ 1.0
  - Inactive embeddings excluded from search
  - Re-register: old rows inactive, new active, one transaction (inject failure → nothing changes)
  - Too few samples → 4xx and nothing stored
  - Status endpoint has no vector field (schema test)
  - Delete removes rows and writes audit
  - Operator cannot commit/delete (403)

STEP 6 — VERIFICATION (run these and report real results)
  pytest backend/tests/db/test_face_repo.py backend/tests/api/test_face_commit.py -v
  docker compose exec db psql -U $env:POSTGRES_USER -d $env:POSTGRES_DB -c "SELECT student_id, count(*) FROM face_embeddings GROUP BY 1;"

STEP 7 — ACCEPTANCE CRITERIA (mark each ✅ / ❌ / NOT VERIFIED — never guess)
  [ ] Atomic commit verified
  [ ] Search ordering verified
  [ ] Re-registration verified
  [ ] No vectors in responses (tested)
  [ ] Audit entries written

STEP 8 — DOCUMENTATION: update README/docs for anything this phase changed; add a short entry to docs/CHANGELOG.md.

STEP 9 — GIT CHECKPOINT (only if tests pass)
  git status ; git diff   (confirm NO secrets, images, videos, .onnx, data/ content staged)
  git add . ; git commit -m "feat(face): store and search ArcFace embeddings with pgvector" ; git push -u origin feature/phase-12-vector-storage

STEP 10 — STOP. Print the REPORT FORMAT from the global rules and write: STOPPED AT PHASE 12 GATE — awaiting human approval. Do NOT start Phase 13.
```

## Commands

Windows PowerShell (run from the repo root unless stated):

```powershell
pytest backend/tests/db/test_face_repo.py backend/tests/api/test_face_commit.py -v
docker compose exec db psql -U $env:POSTGRES_USER -d $env:POSTGRES_DB -c "SELECT student_id, count(*) FROM face_embeddings GROUP BY 1;"
```

## Tests

- Insert N embeddings and retrieve nearest = itself with similarity ≈ 1.0
- Inactive embeddings excluded from search
- Re-register: old rows inactive, new active, one transaction (inject failure → nothing changes)
- Too few samples → 4xx and nothing stored
- Status endpoint has no vector field (schema test)
- Delete removes rows and writes audit
- Operator cannot commit/delete (403)

## Manual Verification

1. Register yourself (quick mode 5 samples) and check row counts in psql
2. Re-register and confirm old rows are inactive

## Expected Result

Embeddings persisted, searchable, replaceable and deletable; API never leaks vectors.

## Failure Conditions

- Vector present in any API response
- Partial commit on error

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| `operator does not exist: vector <=> numeric[]` | Cast parameter with pgvector adapter / `CAST(:q AS vector)` |
| HNSW not used | Normal for tiny tables; validate with >1k synthetic rows |

## Acceptance Criteria

- [ ] Atomic commit verified
- [ ] Search ordering verified
- [ ] Re-registration verified
- [ ] No vectors in responses (tested)
- [ ] Audit entries written

## Git Checkpoint

```powershell
git checkout main
git pull origin main
git checkout -b feature/phase-12-vector-storage   # at the START of the phase

# after tests pass:
git status
git diff
git add .
git commit -m "feat(face): store and search ArcFace embeddings with pgvector"
git push -u origin feature/phase-12-vector-storage
```

Recommended commit message: `feat(face): store and search ArcFace embeddings with pgvector`

## HUMAN APPROVAL

Before approving, you should personally:

1. Register all 3 people (you + 2 friends) and verify counts per student

## NEXT PHASE

Phase 13 implements recognition decisions.

---

# Phase 13 — FACE RECOGNITION

> **Branch:** `feature/phase-13-recognition` · **Gate:** STOP — human approval required before the next phase

## Objective

Implement the shared `VisionPipeline.process(frame)`: detect → embed → search → threshold → identity decision (`STUDENT` / `BLACKLISTED` / `UNKNOWN`), plus a calibration script and a protected test endpoint.

## Why This Phase Exists

This is the single recognition path both modules will use. Threshold must be evidence-based.

## Prerequisites

- Previous phase approved and merged (or branch checked out from it)

## Inputs

- Output of the previous phase
- This playbook

## Expected Outputs

- `vision/recognizer.py`, `vision/pipeline.py`
- `POST /recognition/identify` (ADMIN)
- `scripts/calibrate_threshold.py`
- Structured result `FaceResult`

## Architecture

```text
VisionPipeline.process(frame) -> list[FaceResult]
FaceResult{ recognized, kind, student_id, name, blacklist_id, similarity, bbox, det_score }
Decision: top1.similarity >= RECOGNITION_THRESHOLD → owner kind; else UNKNOWN
```
Optional margin: if top1 and top2 are *different* identities with gap < `RECOGNITION_MARGIN` (default 0.05) → UNKNOWN (ambiguous).

## Files To Inspect

- Repository tree (`Get-ChildItem -Recurse -Depth 3`)
- README.md
- docs/ (including the project PPT/PDF and docs/PLAYBOOK.md)
- TOKEN-OPTIMIZATION.md
- docker-compose.yml
- requirements.txt, requirements-dev.txt, requirements-gpu.txt
- .env.example, .gitignore, .dockerignore, .python-version
- `git log --oneline -15` and `git status`

## Files To Create

- backend/app/vision/recognizer.py
- backend/app/vision/pipeline.py
- backend/app/api/v1/recognition.py
- backend/app/schemas/recognition.py
- scripts/calibrate_threshold.py
- scripts/eval_recognition.py (skeleton)
- backend/tests/vision/test_recognizer.py
- backend/tests/api/test_identify.py

## Files To Modify

- backend/app/api/v1/router.py
- .env.example (RECOGNITION_THRESHOLD, RECOGNITION_MARGIN)

## Dependencies

No new dependencies.

## Environment Variables

- RECOGNITION_THRESHOLD=0.45 (starting point only)
- RECOGNITION_MARGIN=0.05
- TOP_K=5

## Database Changes

None.

## API Changes

`POST /recognition/identify` multipart image → faces list. Uses safe image decoder; ADMIN only; response contains similarity and bbox, **never embeddings**; label the field `similarity`, not accuracy.

## Frontend Changes

None.

## Implementation Sequence

1. Create branch
2. Write pure decision logic + tests
3. Write recognizer (search) and pipeline
4. Endpoint with safe upload
5. Calibration script
6. Run calibration with your own local photos and record recommended threshold in `docs/testing/THRESHOLD_NOTES.md` (real numbers only)
7. Commit and stop

## EXACT ANTIGRAVITY PROMPT

```text
YOU ARE IMPLEMENTING: PHASE 13 — FACE RECOGNITION

Follow the GLOBAL RULES (docs/PLAYBOOK.md Section 2). Work ONLY on this phase.


STEP 0 — BRANCH
  git checkout main ; git pull origin main ; git checkout -b feature/phase-13-recognition
  (If the branch exists, check it out instead. Never commit to main.)

STEP 1 — INSPECT FIRST (do not modify anything yet)
  - Repository tree (`Get-ChildItem -Recurse -Depth 3`)
  - README.md
  - docs/ (including the project PPT/PDF and docs/PLAYBOOK.md)
  - TOKEN-OPTIMIZATION.md
  - docker-compose.yml
  - requirements.txt, requirements-dev.txt, requirements-gpu.txt
  - .env.example, .gitignore, .dockerignore, .python-version
  - `git log --oneline -15` and `git status`
  Report briefly what already exists that is relevant to this phase. Never assume a file is missing.

OBJECTIVE
  Implement the shared `VisionPipeline.process(frame)`: detect → embed → search → threshold → identity decision (`STUDENT` / `BLACKLISTED` / `UNKNOWN`), plus a calibration script and a protected test endpoint.

STEP 2 — CREATE (only after inspection; skip anything that already exists and extend it instead)
  - backend/app/vision/recognizer.py
  - backend/app/vision/pipeline.py
  - backend/app/api/v1/recognition.py
  - backend/app/schemas/recognition.py
  - scripts/calibrate_threshold.py
  - scripts/eval_recognition.py (skeleton)
  - backend/tests/vision/test_recognizer.py
  - backend/tests/api/test_identify.py

STEP 3 — MODIFY
  - backend/app/api/v1/router.py
  - .env.example (RECOGNITION_THRESHOLD, RECOGNITION_MARGIN)

DO NOT MODIFY / DO NOT DO
  - Call similarity 'accuracy'
  - Hardcode the threshold in code (read from settings/DB)
  - Duplicate recognition logic for security later

DEPENDENCIES: none new  (resolve compatible versions, pin them, verify with `pip check`)
ENVIRONMENT VARIABLES: RECOGNITION_THRESHOLD=0.45 (starting point only); RECOGNITION_MARGIN=0.05; TOP_K=5  (placeholders only in .env.example)

STEP 4 — IMPLEMENTATION ORDER
  1. Create branch
  2. Write pure decision logic + tests
  3. Write recognizer (search) and pipeline
  4. Endpoint with safe upload
  5. Calibration script
  6. Run calibration with your own local photos and record recommended threshold in `docs/testing/THRESHOLD_NOTES.md` (real numbers only)
  7. Commit and stop

SPECIFIC REQUIREMENTS
  - Pure decision function `decide(candidates, threshold, margin)` separated from I/O for unit testing
  - Aggregate to best similarity per identity (max across that identity's embeddings)
  - `calibrate_threshold.py` reads a local folder `data/calibration/<person>/*.jpg` (gitignored), computes genuine/impostor similarity distributions and prints FAR/FRR at thresholds 0.30–0.70; prints dataset size; never writes images anywhere

STEP 5 — TESTS (write and RUN; paste real output)
  - decide(): below threshold → UNKNOWN; at/above → recognized
  - Margin ambiguity → UNKNOWN
  - Identify known registered fixture → correct student_id (local fixture)
  - Identify unregistered fixture → UNKNOWN
  - No face → empty list, not error
  - Corrupt upload → 422; oversized → 413
  - Response schema contains no embedding field
  - Operator → 403

STEP 6 — VERIFICATION (run these and report real results)
  pytest backend/tests/vision/test_recognizer.py backend/tests/api/test_identify.py -v -rs
  python scripts\calibrate_threshold.py --dir data\calibration

STEP 7 — ACCEPTANCE CRITERIA (mark each ✅ / ❌ / NOT VERIFIED — never guess)
  [ ] Decision logic unit-tested
  [ ] Identify endpoint verified with real images
  [ ] Calibration run and numbers documented
  [ ] No embedding leakage
  [ ] Single shared pipeline

STEP 8 — DOCUMENTATION: update README/docs for anything this phase changed; add a short entry to docs/CHANGELOG.md.

STEP 9 — GIT CHECKPOINT (only if tests pass)
  git status ; git diff   (confirm NO secrets, images, videos, .onnx, data/ content staged)
  git add . ; git commit -m "feat(recognition): add shared vision pipeline, threshold decision and calibration script" ; git push -u origin feature/phase-13-recognition

STEP 10 — STOP. Print the REPORT FORMAT from the global rules and write: STOPPED AT PHASE 13 GATE — awaiting human approval. Do NOT start Phase 14.
```

## Commands

Windows PowerShell (run from the repo root unless stated):

```powershell
pytest backend/tests/vision/test_recognizer.py backend/tests/api/test_identify.py -v -rs
python scripts\calibrate_threshold.py --dir data\calibration
```

## Tests

- decide(): below threshold → UNKNOWN; at/above → recognized
- Margin ambiguity → UNKNOWN
- Identify known registered fixture → correct student_id (local fixture)
- Identify unregistered fixture → UNKNOWN
- No face → empty list, not error
- Corrupt upload → 422; oversized → 413
- Response schema contains no embedding field
- Operator → 403

## Manual Verification

1. Upload your photo via /docs → recognized with similarity
2. Upload a stranger photo → UNKNOWN
3. Run calibration and read the FAR/FRR table

## Expected Result

Correct structured identity decisions with an evidence-based threshold.

## Failure Conditions

- Threshold hardcoded
- Embeddings in response
- Separate recognition code paths

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| Everyone UNKNOWN | Threshold too high or embeddings from poor samples; lower threshold per calibration and re-register with better samples |
| Different people matched | Threshold too low; raise it; enable margin |

## Acceptance Criteria

- [ ] Decision logic unit-tested
- [ ] Identify endpoint verified with real images
- [ ] Calibration run and numbers documented
- [ ] No embedding leakage
- [ ] Single shared pipeline

## Git Checkpoint

```powershell
git checkout main
git pull origin main
git checkout -b feature/phase-13-recognition   # at the START of the phase

# after tests pass:
git status
git diff
git add .
git commit -m "feat(recognition): add shared vision pipeline, threshold decision and calibration script"
git push -u origin feature/phase-13-recognition
```

Recommended commit message: `feat(recognition): add shared vision pipeline, threshold decision and calibration script`

## HUMAN APPROVAL

Before approving, you should personally:

1. Review THRESHOLD_NOTES.md numbers and dataset size
2. Test /identify with a stranger photo

## NEXT PHASE

Phase 14 runs the pipeline on the live laptop webcam.

---

# Phase 14 — LIVE LAPTOP CAMERA RECOGNITION

> **Branch:** `feature/phase-14-live-camera` · **Gate:** STOP — human approval required before the next phase

## Objective

Implement `CameraWorker` that continuously reads the laptop webcam, runs the shared pipeline on every Nth frame, stabilises results across frames, draws green/red boxes with name/ID/score, and streams annotated MJPEG. Seed the 'Laptop Webcam' camera row.

## Why This Phase Exists

First visible proof that you and your friends are recognized live.

## Prerequisites

- Previous phase approved and merged (or branch checked out from it)

## Inputs

- Output of the previous phase
- This playbook

## Expected Outputs

- `cameras/worker.py`, `vision/tracker.py`, `vision/overlay.py`
- Worker start/stop/list endpoints
- Seeded camera `Laptop Webcam` (location `Dev Laptop`)
- Streamlit Live Attendance page with video

## Architecture

```text
WebcamSource → [reader thread: latest-frame buffer, drops stale frames]
   → [process thread: every Nth frame → VisionPipeline]
   → SimpleTracker (IoU association, CONFIRM_FRAMES consecutive agreement)
   → overlay (green=recognized, red=UNKNOWN) → MJPEG
   → publish FaceObservation (used by Phase 15/17 handlers)
```
Overlay text: `Name`, `ID: 001`, `similarity 0.78` (label 'score').

## Files To Inspect

- Repository tree (`Get-ChildItem -Recurse -Depth 3`)
- README.md
- docs/ (including the project PPT/PDF and docs/PLAYBOOK.md)
- TOKEN-OPTIMIZATION.md
- docker-compose.yml
- requirements.txt, requirements-dev.txt, requirements-gpu.txt
- .env.example, .gitignore, .dockerignore, .python-version
- `git log --oneline -15` and `git status`

## Files To Create

- backend/app/cameras/worker.py
- backend/app/cameras/manager.py (single-camera for now)
- backend/app/vision/tracker.py
- backend/app/vision/overlay.py
- backend/app/api/v1/recognition.py (workers start/stop/list)
- scripts/seed_camera.py or startup seed in migration data step
- frontend/pages/ Live Attendance page
- backend/tests/vision/test_tracker.py, test_overlay.py, backend/tests/cameras/test_worker_mock.py

## Files To Modify

- backend/app/api/v1/stream.py (serve annotated frames)
- backend/app/main.py (graceful worker shutdown on app stop)

## Dependencies

No new dependencies.

## Environment Variables

- PROCESS_EVERY_N_FRAMES=3
- CONFIRM_FRAMES=3
- STREAM_JPEG_QUALITY=70
- STREAM_MAX_FPS=15

## Database Changes

None.

## API Changes

None.

## Frontend Changes

Live Attendance page: Start/Stop button, MJPEG view, status chips (FPS, faces, camera state). Attendance panel is added in Phase 16.

## Implementation Sequence

1. Create branch
2. Implement tracker + overlay with unit tests
3. Implement reader/process threads and worker lifecycle
4. Seed camera row
5. Worker endpoints + stream annotated frames
6. Streamlit Live Attendance page
7. Manual test with yourself
8. Commit and stop

## EXACT ANTIGRAVITY PROMPT

```text
YOU ARE IMPLEMENTING: PHASE 14 — LIVE LAPTOP CAMERA RECOGNITION

Follow the GLOBAL RULES (docs/PLAYBOOK.md Section 2). Work ONLY on this phase.


STEP 0 — BRANCH
  git checkout main ; git pull origin main ; git checkout -b feature/phase-14-live-camera
  (If the branch exists, check it out instead. Never commit to main.)

STEP 1 — INSPECT FIRST (do not modify anything yet)
  - Repository tree (`Get-ChildItem -Recurse -Depth 3`)
  - README.md
  - docs/ (including the project PPT/PDF and docs/PLAYBOOK.md)
  - TOKEN-OPTIMIZATION.md
  - docker-compose.yml
  - requirements.txt, requirements-dev.txt, requirements-gpu.txt
  - .env.example, .gitignore, .dockerignore, .python-version
  - `git log --oneline -15` and `git status`
  Report briefly what already exists that is relevant to this phase. Never assume a file is missing.

OBJECTIVE
  Implement `CameraWorker` that continuously reads the laptop webcam, runs the shared pipeline on every Nth frame, stabilises results across frames, draws green/red boxes with name/ID/score, and streams annotated MJPEG. Seed the 'Laptop Webcam' camera row.

STEP 2 — CREATE (only after inspection; skip anything that already exists and extend it instead)
  - backend/app/cameras/worker.py
  - backend/app/cameras/manager.py (single-camera for now)
  - backend/app/vision/tracker.py
  - backend/app/vision/overlay.py
  - backend/app/api/v1/recognition.py (workers start/stop/list)
  - scripts/seed_camera.py or startup seed in migration data step
  - frontend/pages/ Live Attendance page
  - backend/tests/vision/test_tracker.py, test_overlay.py, backend/tests/cameras/test_worker_mock.py

STEP 3 — MODIFY
  - backend/app/api/v1/stream.py (serve annotated frames)
  - backend/app/main.py (graceful worker shutdown on app stop)

DO NOT MODIFY / DO NOT DO
  - Mark attendance (Phase 15)
  - Block the API event loop (use threads)
  - Process every frame at full resolution if it stalls

DEPENDENCIES: none new  (resolve compatible versions, pin them, verify with `pip check`)
ENVIRONMENT VARIABLES: PROCESS_EVERY_N_FRAMES=3; CONFIRM_FRAMES=3; STREAM_JPEG_QUALITY=70; STREAM_MAX_FPS=15  (placeholders only in .env.example)

STEP 4 — IMPLEMENTATION ORDER
  1. Create branch
  2. Implement tracker + overlay with unit tests
  3. Implement reader/process threads and worker lifecycle
  4. Seed camera row
  5. Worker endpoints + stream annotated frames
  6. Streamlit Live Attendance page
  7. Manual test with yourself
  8. Commit and stop

SPECIFIC REQUIREMENTS
  - Reader thread keeps only the newest frame (bounded queue size 1)
  - Worker exposes state: STOPPED/STARTING/RUNNING/ERROR, fps, last_error
  - Graceful stop joins threads and releases camera
  - Tracker: IoU ≥ 0.3 association; a track becomes 'confirmed' after `CONFIRM_FRAMES` identical decisions; flicker suppressed; stale track dropped after 1.5 s
  - Display score as 'score', never 'accuracy'

STEP 5 — TESTS (write and RUN; paste real output)
  - Tracker: stable ID for moving box; new ID for disjoint box; drop after timeout
  - Confirmation: 2 matching frames then 1 different → not yet confirmed
  - Overlay: green for recognized, red for UNKNOWN (pixel-colour assertion at box edge)
  - Worker mock: camera read failure sets ERROR and does not crash API
  - Stop releases camera (mock)
  - Start twice → 409

STEP 6 — VERIFICATION (run these and report real results)
  pytest backend/tests/vision backend/tests/cameras -v
  uvicorn backend.app.main:app --port 8000
  streamlit run frontend\app.py

STEP 7 — ACCEPTANCE CRITERIA (mark each ✅ / ❌ / NOT VERIFIED — never guess)
  [ ] Green box with name/ID/score for registered people
  [ ] Red UNKNOWN for unregistered
  [ ] Worker start/stop clean
  [ ] No attendance written yet
  [ ] Tracker/overlay tests pass
  [ ] Measured FPS recorded

STEP 8 — DOCUMENTATION: update README/docs for anything this phase changed; add a short entry to docs/CHANGELOG.md.

STEP 9 — GIT CHECKPOINT (only if tests pass)
  git status ; git diff   (confirm NO secrets, images, videos, .onnx, data/ content staged)
  git add . ; git commit -m "feat(live): add camera worker, tracker, overlay and live MJPEG recognition" ; git push -u origin feature/phase-14-live-camera

STEP 10 — STOP. Print the REPORT FORMAT from the global rules and write: STOPPED AT PHASE 14 GATE — awaiting human approval. Do NOT start Phase 15.
```

## Commands

Windows PowerShell (run from the repo root unless stated):

```powershell
pytest backend/tests/vision backend/tests/cameras -v
uvicorn backend.app.main:app --port 8000
streamlit run frontend\app.py
```

## Tests

- Tracker: stable ID for moving box; new ID for disjoint box; drop after timeout
- Confirmation: 2 matching frames then 1 different → not yet confirmed
- Overlay: green for recognized, red for UNKNOWN (pixel-colour assertion at box edge)
- Worker mock: camera read failure sets ERROR and does not crash API
- Stop releases camera (mock)
- Start twice → 409

## Manual Verification

1. Start worker; stand in front of the camera: green box, name, ID, score
2. Hold up a friend's phone photo or have an unregistered person appear: red UNKNOWN
3. Observe FPS on the status chip

## Expected Result

Live annotated webcam stream with correct colours and stable labels.

## Failure Conditions

- UI freezes
- Box flicker between names every frame
- Camera not released on stop

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| Low FPS (<3) | Raise `PROCESS_EVERY_N_FRAMES`, lower `DET_SIZE`, lower capture resolution |
| Wrong person briefly shown | Raise `CONFIRM_FRAMES`/threshold |
| Stream stalls in browser | Single viewer per stream in MVP; reduce `STREAM_MAX_FPS` |

## Acceptance Criteria

- [ ] Green box with name/ID/score for registered people
- [ ] Red UNKNOWN for unregistered
- [ ] Worker start/stop clean
- [ ] No attendance written yet
- [ ] Tracker/overlay tests pass
- [ ] Measured FPS recorded

## Git Checkpoint

```powershell
git checkout main
git pull origin main
git checkout -b feature/phase-14-live-camera   # at the START of the phase

# after tests pass:
git status
git diff
git add .
git commit -m "feat(live): add camera worker, tracker, overlay and live MJPEG recognition"
git push -u origin feature/phase-14-live-camera
```

Recommended commit message: `feat(live): add camera worker, tracker, overlay and live MJPEG recognition`

## HUMAN APPROVAL

Before approving, you should personally:

1. Recognize yourself and both friends live
2. Record observed FPS and any misidentifications

## NEXT PHASE

Phase 15 turns confirmed recognitions into attendance.

---

# Phase 15 — ATTENDANCE ENGINE

> **Branch:** `feature/phase-15-attendance-engine` · **Gate:** STOP — human approval required before the next phase

## Objective

Implement attendance business logic: confirmed recognition → eligibility checks → deduplication → attendance record. Unknown people never get attendance.

## Why This Phase Exists

Face detected ≠ attendance. Rules and deduplication make records trustworthy.

## Prerequisites

- Previous phase approved and merged (or branch checked out from it)

## Inputs

- Output of the previous phase
- This playbook

## Expected Outputs

- `AttendanceService.handle(observation)`
- Dedup: in-memory cooldown **and** DB unique constraint with `ON CONFLICT DO NOTHING`
- Decision log in `docs/architecture/DECISIONS.md` (ADR-08 confirmed after repo inspection)

## Architecture

```text
confirmed track (kind=STUDENT, similarity>=threshold, CONFIRM_FRAMES met)
  → student ACTIVE? → cooldown cache hit? → INSERT ... ON CONFLICT (student_id, attendance_date, session_label) DO NOTHING
  → result: MARKED | ALREADY_MARKED | SKIPPED(reason)
```
`attendance_date` computed in `APP_TIMEZONE`. Optional `LATE` if `ATTENDANCE_LATE_AFTER` (HH:MM) is set; default unset → always PRESENT.

## Files To Inspect

- Repository tree (`Get-ChildItem -Recurse -Depth 3`)
- README.md
- docs/ (including the project PPT/PDF and docs/PLAYBOOK.md)
- TOKEN-OPTIMIZATION.md
- docker-compose.yml
- requirements.txt, requirements-dev.txt, requirements-gpu.txt
- .env.example, .gitignore, .dockerignore, .python-version
- `git log --oneline -15` and `git status`

## Files To Create

- backend/app/services/attendance_service.py
- backend/app/db/repositories/attendance_repo.py
- backend/app/api/v1/attendance.py
- backend/app/schemas/attendance.py
- backend/tests/unit/test_attendance_rules.py
- backend/tests/db/test_attendance_dedup.py
- backend/tests/api/test_attendance.py

## Files To Modify

- backend/app/cameras/worker.py (call the attendance handler for confirmed observations)
- .env.example

## Dependencies

No new dependencies.

## Environment Variables

- ATTENDANCE_COOLDOWN_SECONDS=300
- ATTENDANCE_SESSION_LABEL=DEFAULT
- ATTENDANCE_LATE_AFTER= (optional)

## Database Changes

No schema change (unique constraint exists from Phase 4).

## API Changes

`GET /attendance`, `GET /attendance/recent`, `POST /attendance/manual` (ADMIN, audited).

## Frontend Changes

None.

## Implementation Sequence

1. Create branch
2. Pure rules function + unit tests
3. Repository with ON CONFLICT
4. Service with cooldown cache
5. Wire into worker
6. API endpoints
7. Concurrency test: 20 parallel attempts → exactly 1 row
8. Manual webcam test
9. Commit and stop

## EXACT ANTIGRAVITY PROMPT

```text
YOU ARE IMPLEMENTING: PHASE 15 — ATTENDANCE ENGINE

Follow the GLOBAL RULES (docs/PLAYBOOK.md Section 2). Work ONLY on this phase.


STEP 0 — BRANCH
  git checkout main ; git pull origin main ; git checkout -b feature/phase-15-attendance-engine
  (If the branch exists, check it out instead. Never commit to main.)

STEP 1 — INSPECT FIRST (do not modify anything yet)
  - Repository tree (`Get-ChildItem -Recurse -Depth 3`)
  - README.md
  - docs/ (including the project PPT/PDF and docs/PLAYBOOK.md)
  - TOKEN-OPTIMIZATION.md
  - docker-compose.yml
  - requirements.txt, requirements-dev.txt, requirements-gpu.txt
  - .env.example, .gitignore, .dockerignore, .python-version
  - `git log --oneline -15` and `git status`
  Report briefly what already exists that is relevant to this phase. Never assume a file is missing.

OBJECTIVE
  Implement attendance business logic: confirmed recognition → eligibility checks → deduplication → attendance record. Unknown people never get attendance.

STEP 2 — CREATE (only after inspection; skip anything that already exists and extend it instead)
  - backend/app/services/attendance_service.py
  - backend/app/db/repositories/attendance_repo.py
  - backend/app/api/v1/attendance.py
  - backend/app/schemas/attendance.py
  - backend/tests/unit/test_attendance_rules.py
  - backend/tests/db/test_attendance_dedup.py
  - backend/tests/api/test_attendance.py

STEP 3 — MODIFY
  - backend/app/cameras/worker.py (call the attendance handler for confirmed observations)
  - .env.example

DO NOT MODIFY / DO NOT DO
  - Create attendance from UNKNOWN or unconfirmed detections
  - Write to DB on every frame
  - Skip the DB unique constraint and rely only on memory

DEPENDENCIES: none new  (resolve compatible versions, pin them, verify with `pip check`)
ENVIRONMENT VARIABLES: ATTENDANCE_COOLDOWN_SECONDS=300; ATTENDANCE_SESSION_LABEL=DEFAULT; ATTENDANCE_LATE_AFTER= (optional)  (placeholders only in .env.example)

STEP 4 — IMPLEMENTATION ORDER
  1. Create branch
  2. Pure rules function + unit tests
  3. Repository with ON CONFLICT
  4. Service with cooldown cache
  5. Wire into worker
  6. API endpoints
  7. Concurrency test: 20 parallel attempts → exactly 1 row
  8. Manual webcam test
  9. Commit and stop

SPECIFIC REQUIREMENTS
  - Worker must never crash if the DB write fails: log, back off, continue
  - Attendance record stores camera_id, similarity, marked_at (UTC)
  - Return `ALREADY_MARKED` silently (no error)

STEP 5 — TESTS (write and RUN; paste real output)
  - Known confirmed → 1 record
  - Same student 100 observations → still 1 record
  - Same student next day → new record (mock clock)
  - Different session label → second record
  - Inactive student → skipped
  - UNKNOWN → no record
  - Unconfirmed (below CONFIRM_FRAMES) → no record
  - Concurrent inserts → exactly one row
  - DB failure → worker keeps running (mock)
  - Manual attendance requires reason and writes audit

STEP 6 — VERIFICATION (run these and report real results)
  pytest backend/tests/unit/test_attendance_rules.py backend/tests/db/test_attendance_dedup.py backend/tests/api/test_attendance.py -v
  docker compose exec db psql -U $env:POSTGRES_USER -d $env:POSTGRES_DB -c "SELECT s.student_id, a.status, a.marked_at, a.similarity FROM attendance_records a JOIN students s ON s.id=a.student_id ORDER BY marked_at DESC LIMIT 10;"

STEP 7 — ACCEPTANCE CRITERIA (mark each ✅ / ❌ / NOT VERIFIED — never guess)
  [ ] Dedup verified at memory and DB level
  [ ] Concurrency test passes
  [ ] Unknown excluded
  [ ] Timezone-correct dates
  [ ] ADR-08 recorded

STEP 8 — DOCUMENTATION: update README/docs for anything this phase changed; add a short entry to docs/CHANGELOG.md.

STEP 9 — GIT CHECKPOINT (only if tests pass)
  git status ; git diff   (confirm NO secrets, images, videos, .onnx, data/ content staged)
  git add . ; git commit -m "feat(attendance): add attendance engine with confirmation, cooldown and DB-level deduplication" ; git push -u origin feature/phase-15-attendance-engine

STEP 10 — STOP. Print the REPORT FORMAT from the global rules and write: STOPPED AT PHASE 15 GATE — awaiting human approval. Do NOT start Phase 16.
```

## Commands

Windows PowerShell (run from the repo root unless stated):

```powershell
pytest backend/tests/unit/test_attendance_rules.py backend/tests/db/test_attendance_dedup.py backend/tests/api/test_attendance.py -v
docker compose exec db psql -U $env:POSTGRES_USER -d $env:POSTGRES_DB -c "SELECT s.student_id, a.status, a.marked_at, a.similarity FROM attendance_records a JOIN students s ON s.id=a.student_id ORDER BY marked_at DESC LIMIT 10;"
```

## Tests

- Known confirmed → 1 record
- Same student 100 observations → still 1 record
- Same student next day → new record (mock clock)
- Different session label → second record
- Inactive student → skipped
- UNKNOWN → no record
- Unconfirmed (below CONFIRM_FRAMES) → no record
- Concurrent inserts → exactly one row
- DB failure → worker keeps running (mock)
- Manual attendance requires reason and writes audit

## Manual Verification

1. Stand in front of the webcam: one record appears; stay 2 minutes: still one
2. Friend 1 enters: second record
3. Unregistered person: no record

## Expected Result

Exactly one attendance record per student per day/session; unknown never counted.

## Failure Conditions

- Multiple records per student/day
- Attendance from UNKNOWN
- Worker crashes on DB error

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| Record not created | Check confirmation frames, threshold, student ACTIVE, worker logs |
| Wrong date near midnight | Verify `APP_TIMEZONE` conversion |

## Acceptance Criteria

- [ ] Dedup verified at memory and DB level
- [ ] Concurrency test passes
- [ ] Unknown excluded
- [ ] Timezone-correct dates
- [ ] ADR-08 recorded

## Git Checkpoint

```powershell
git checkout main
git pull origin main
git checkout -b feature/phase-15-attendance-engine   # at the START of the phase

# after tests pass:
git status
git diff
git add .
git commit -m "feat(attendance): add attendance engine with confirmation, cooldown and DB-level deduplication"
git push -u origin feature/phase-15-attendance-engine
```

Recommended commit message: `feat(attendance): add attendance engine with confirmation, cooldown and DB-level deduplication`

## HUMAN APPROVAL

Before approving, you should personally:

1. Run the 3 manual scenarios and check psql output

## NEXT PHASE

Phase 16 shows attendance in the dashboard.

---

# Phase 16 — ATTENDANCE DASHBOARD

> **Branch:** `feature/phase-16-attendance-dashboard` · **Gate:** STOP — human approval required before the next phase

## Objective

Build the Dashboard overview (real KPIs), Live Attendance panel (recent marks), and Attendance Records page with date/student/department/year filters and pagination.

## Why This Phase Exists

Makes the MVP demonstrable and verifiable by non-developers.

## Prerequisites

- Previous phase approved and merged (or branch checked out from it)

## Inputs

- Output of the previous phase
- This playbook

## Expected Outputs

- `GET /dashboard/summary` real aggregates
- Live Attendance page: video + recent attendance list refreshing every 2 s
- Attendance Records page with filters

## Architecture

```text
Dashboard KPIs: total students, present today, attendance % (definition below), unknown detections today, active alerts, blacklisted detections today, active cameras
```
Attendance % = distinct students present today ÷ ACTIVE students with registered faces (documented definition; security KPIs show real zeros until later phases).

## Files To Inspect

- Repository tree (`Get-ChildItem -Recurse -Depth 3`)
- README.md
- docs/ (including the project PPT/PDF and docs/PLAYBOOK.md)
- TOKEN-OPTIMIZATION.md
- docker-compose.yml
- requirements.txt, requirements-dev.txt, requirements-gpu.txt
- .env.example, .gitignore, .dockerignore, .python-version
- `git log --oneline -15` and `git status`

## Files To Create

- backend/app/api/v1/dashboard.py
- backend/app/services/dashboard_service.py
- frontend/pages/ Dashboard, Live Attendance (panel), Attendance Records
- backend/tests/api/test_dashboard.py

## Files To Modify

- backend/app/api/v1/attendance.py (filters)
- frontend/app.py

## Dependencies

No new dependencies.

## Environment Variables

No new variables.

## Database Changes

None.

## API Changes

`GET /dashboard/summary`; `GET /attendance` filters: from,to,student_id,department,year,camera_id,page,size.

## Frontend Changes

KPI cards (7), 'Recent Attendance' table, filters (date range, student search, department, year), empty states: 'No attendance recorded yet'. Use `st.fragment(run_every=...)` or a timed refresh for the live panel.

## Implementation Sequence

1. Create branch
2. Summary service with SQL aggregates
3. Filter queries with indexes
4. Dashboard + Live panel + Records pages
5. Tests with seeded data
6. Manual check
7. Commit and stop

## EXACT ANTIGRAVITY PROMPT

```text
YOU ARE IMPLEMENTING: PHASE 16 — ATTENDANCE DASHBOARD

Follow the GLOBAL RULES (docs/PLAYBOOK.md Section 2). Work ONLY on this phase.


STEP 0 — BRANCH
  git checkout main ; git pull origin main ; git checkout -b feature/phase-16-attendance-dashboard
  (If the branch exists, check it out instead. Never commit to main.)

STEP 1 — INSPECT FIRST (do not modify anything yet)
  - Repository tree (`Get-ChildItem -Recurse -Depth 3`)
  - README.md
  - docs/ (including the project PPT/PDF and docs/PLAYBOOK.md)
  - TOKEN-OPTIMIZATION.md
  - docker-compose.yml
  - requirements.txt, requirements-dev.txt, requirements-gpu.txt
  - .env.example, .gitignore, .dockerignore, .python-version
  - `git log --oneline -15` and `git status`
  Report briefly what already exists that is relevant to this phase. Never assume a file is missing.

OBJECTIVE
  Build the Dashboard overview (real KPIs), Live Attendance panel (recent marks), and Attendance Records page with date/student/department/year filters and pagination.

STEP 2 — CREATE (only after inspection; skip anything that already exists and extend it instead)
  - backend/app/api/v1/dashboard.py
  - backend/app/services/dashboard_service.py
  - frontend/pages/ Dashboard, Live Attendance (panel), Attendance Records
  - backend/tests/api/test_dashboard.py

STEP 3 — MODIFY
  - backend/app/api/v1/attendance.py (filters)
  - frontend/app.py

DO NOT MODIFY / DO NOT DO
  - Fabricate or hardcode numbers
  - Add charts that cannot be backed by data

DEPENDENCIES: none new  (resolve compatible versions, pin them, verify with `pip check`)
ENVIRONMENT VARIABLES: none new  (placeholders only in .env.example)

STEP 4 — IMPLEMENTATION ORDER
  1. Create branch
  2. Summary service with SQL aggregates
  3. Filter queries with indexes
  4. Dashboard + Live panel + Records pages
  5. Tests with seeded data
  6. Manual check
  7. Commit and stop

STEP 5 — TESTS (write and RUN; paste real output)
  - Summary values equal hand-counted values from seeded data
  - Zero-state returns zeros, not errors/division by zero
  - Each filter narrows results correctly; combined filters work
  - Date range >366 days rejected
  - Pagination correct
  - Auth required

STEP 6 — VERIFICATION (run these and report real results)
  pytest backend/tests/api/test_dashboard.py -v
  streamlit run frontend\app.py

STEP 7 — ACCEPTANCE CRITERIA (mark each ✅ / ❌ / NOT VERIFIED — never guess)
  [ ] KPIs real and tested
  [ ] Filters verified
  [ ] Live panel updates after a new recognition
  [ ] Empty states handled

STEP 8 — DOCUMENTATION: update README/docs for anything this phase changed; add a short entry to docs/CHANGELOG.md.

STEP 9 — GIT CHECKPOINT (only if tests pass)
  git status ; git diff   (confirm NO secrets, images, videos, .onnx, data/ content staged)
  git add . ; git commit -m "feat(dashboard): add real KPIs, live attendance panel and attendance records filters" ; git push -u origin feature/phase-16-attendance-dashboard

STEP 10 — STOP. Print the REPORT FORMAT from the global rules and write: STOPPED AT PHASE 16 GATE — awaiting human approval. Do NOT start Phase 17.
```

## Commands

Windows PowerShell (run from the repo root unless stated):

```powershell
pytest backend/tests/api/test_dashboard.py -v
streamlit run frontend\app.py
```

## Tests

- Summary values equal hand-counted values from seeded data
- Zero-state returns zeros, not errors/division by zero
- Each filter narrows results correctly; combined filters work
- Date range >366 days rejected
- Pagination correct
- Auth required

## Manual Verification

1. Compare KPI numbers with psql counts
2. Filter by department/year/date and verify rows

## Expected Result

All numbers on screen match the database.

## Failure Conditions

- Any hardcoded KPI
- Division by zero crash

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| Panel not refreshing | Use fragment run_every; ensure token handled in refresh |
| Slow table | Add pagination and check indexes |

## Acceptance Criteria

- [ ] KPIs real and tested
- [ ] Filters verified
- [ ] Live panel updates after a new recognition
- [ ] Empty states handled

## Git Checkpoint

```powershell
git checkout main
git pull origin main
git checkout -b feature/phase-16-attendance-dashboard   # at the START of the phase

# after tests pass:
git status
git diff
git add .
git commit -m "feat(dashboard): add real KPIs, live attendance panel and attendance records filters"
git push -u origin feature/phase-16-attendance-dashboard
```

Recommended commit message: `feat(dashboard): add real KPIs, live attendance panel and attendance records filters`

## HUMAN APPROVAL

Before approving, you should personally:

1. Cross-check each KPI against psql

## NEXT PHASE

Phase 17 adds unknown-person handling.

---

# Phase 17 — UNKNOWN PERSON DETECTION

> **Branch:** `feature/phase-17-unknown-person` · **Gate:** STOP — human approval required before the next phase

## Objective

Classify unmatched faces as `UNKNOWN` (red box), write deduplicated `detection_events` for RECOGNIZED and UNKNOWN observations, and never mark attendance for unknown.

## Why This Phase Exists

Foundation for the Security module; also guarantees no false attendance.

## Prerequisites

- Previous phase approved and merged (or branch checked out from it)

## Inputs

- Output of the previous phase
- This playbook

## Expected Outputs

- Detection event writer with per-track cooldown (`UNKNOWN_EVENT_COOLDOWN_SECONDS`)
- Optional snapshot support (default OFF)
- Unknown count visible on Dashboard

## Architecture

```text
confirmed UNKNOWN track → if track not seen/last event older than cooldown → INSERT detection_events(event_type='UNKNOWN', camera_id, similarity=best, bbox, track_id)
confirmed RECOGNIZED track → throttled RECOGNIZED event (every SIGHTING cooldown, e.g. 30 s)
```
Alerts are NOT created here (Phase 25).

## Files To Inspect

- Repository tree (`Get-ChildItem -Recurse -Depth 3`)
- README.md
- docs/ (including the project PPT/PDF and docs/PLAYBOOK.md)
- TOKEN-OPTIMIZATION.md
- docker-compose.yml
- requirements.txt, requirements-dev.txt, requirements-gpu.txt
- .env.example, .gitignore, .dockerignore, .python-version
- `git log --oneline -15` and `git status`

## Files To Create

- backend/app/services/detection_service.py
- backend/app/db/repositories/detection_repo.py
- backend/tests/unit/test_unknown_dedup.py
- backend/tests/db/test_detection_events.py

## Files To Modify

- backend/app/cameras/worker.py
- backend/app/services/dashboard_service.py (unknown today)

## Dependencies

No new dependencies.

## Environment Variables

- UNKNOWN_EVENT_COOLDOWN_SECONDS=30
- RECOGNIZED_EVENT_COOLDOWN_SECONDS=30
- UNKNOWN_SNAPSHOT_ENABLED=false

## Database Changes

None.

## API Changes

None.

## Frontend Changes

None.

## Implementation Sequence

1. Create branch
2. Cooldown logic + unit tests
3. Event repository
4. Wire worker → detection service
5. Dashboard unknown KPI
6. Manual test
7. Commit and stop

## EXACT ANTIGRAVITY PROMPT

```text
YOU ARE IMPLEMENTING: PHASE 17 — UNKNOWN PERSON DETECTION

Follow the GLOBAL RULES (docs/PLAYBOOK.md Section 2). Work ONLY on this phase.


STEP 0 — BRANCH
  git checkout main ; git pull origin main ; git checkout -b feature/phase-17-unknown-person
  (If the branch exists, check it out instead. Never commit to main.)

STEP 1 — INSPECT FIRST (do not modify anything yet)
  - Repository tree (`Get-ChildItem -Recurse -Depth 3`)
  - README.md
  - docs/ (including the project PPT/PDF and docs/PLAYBOOK.md)
  - TOKEN-OPTIMIZATION.md
  - docker-compose.yml
  - requirements.txt, requirements-dev.txt, requirements-gpu.txt
  - .env.example, .gitignore, .dockerignore, .python-version
  - `git log --oneline -15` and `git status`
  Report briefly what already exists that is relevant to this phase. Never assume a file is missing.

OBJECTIVE
  Classify unmatched faces as `UNKNOWN` (red box), write deduplicated `detection_events` for RECOGNIZED and UNKNOWN observations, and never mark attendance for unknown.

STEP 2 — CREATE (only after inspection; skip anything that already exists and extend it instead)
  - backend/app/services/detection_service.py
  - backend/app/db/repositories/detection_repo.py
  - backend/tests/unit/test_unknown_dedup.py
  - backend/tests/db/test_detection_events.py

STEP 3 — MODIFY
  - backend/app/cameras/worker.py
  - backend/app/services/dashboard_service.py (unknown today)

DO NOT MODIFY / DO NOT DO
  - Call unknown persons malicious/intruders in UI or logs
  - Store snapshots by default
  - Create alerts yet

DEPENDENCIES: none new  (resolve compatible versions, pin them, verify with `pip check`)
ENVIRONMENT VARIABLES: UNKNOWN_EVENT_COOLDOWN_SECONDS=30; RECOGNIZED_EVENT_COOLDOWN_SECONDS=30; UNKNOWN_SNAPSHOT_ENABLED=false  (placeholders only in .env.example)

STEP 4 — IMPLEMENTATION ORDER
  1. Create branch
  2. Cooldown logic + unit tests
  3. Event repository
  4. Wire worker → detection service
  5. Dashboard unknown KPI
  6. Manual test
  7. Commit and stop

SPECIFIC REQUIREMENTS
  - UI label exactly `UNKNOWN`
  - If snapshots enabled: save under `data/snapshots/<uuid>.jpg` with path-safe naming, JPEG only, and document retention — default remains disabled

STEP 5 — TESTS (write and RUN; paste real output)
  - Unknown visible 60 s → ≤2 events (cooldown 30 s)
  - New unknown track after leaving → new event
  - Unknown never creates attendance
  - Recognized events throttled
  - Snapshot disabled by default (no files created)
  - Dashboard unknown count matches DB

STEP 6 — VERIFICATION (run these and report real results)
  pytest backend/tests/unit/test_unknown_dedup.py backend/tests/db/test_detection_events.py -v
  docker compose exec db psql -U $env:POSTGRES_USER -d $env:POSTGRES_DB -c "SELECT event_type, count(*) FROM detection_events GROUP BY 1;"

STEP 7 — ACCEPTANCE CRITERIA (mark each ✅ / ❌ / NOT VERIFIED — never guess)
  [ ] Red UNKNOWN verified
  [ ] Deduplicated events verified
  [ ] No attendance for unknown
  [ ] No snapshots by default

STEP 8 — DOCUMENTATION: update README/docs for anything this phase changed; add a short entry to docs/CHANGELOG.md.

STEP 9 — GIT CHECKPOINT (only if tests pass)
  git status ; git diff   (confirm NO secrets, images, videos, .onnx, data/ content staged)
  git add . ; git commit -m "feat(security): classify unknown faces and log deduplicated detection events" ; git push -u origin feature/phase-17-unknown-person

STEP 10 — STOP. Print the REPORT FORMAT from the global rules and write: STOPPED AT PHASE 17 GATE — awaiting human approval. Do NOT start Phase 18.
```

## Commands

Windows PowerShell (run from the repo root unless stated):

```powershell
pytest backend/tests/unit/test_unknown_dedup.py backend/tests/db/test_detection_events.py -v
docker compose exec db psql -U $env:POSTGRES_USER -d $env:POSTGRES_DB -c "SELECT event_type, count(*) FROM detection_events GROUP BY 1;"
```

## Tests

- Unknown visible 60 s → ≤2 events (cooldown 30 s)
- New unknown track after leaving → new event
- Unknown never creates attendance
- Recognized events throttled
- Snapshot disabled by default (no files created)
- Dashboard unknown count matches DB

## Manual Verification

1. Have an unregistered person stand in front for ~1 minute; confirm red UNKNOWN and ≤ a few events

## Expected Result

Unknown people are clearly flagged, logged without spam, and never counted present.

## Failure Conditions

- Hundreds of unknown events per minute
- Attendance for unknown

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| Registered person flagged UNKNOWN | Improve registration samples; recalibrate threshold |
| Too many unknown events | Raise cooldown / CONFIRM_FRAMES |

## Acceptance Criteria

- [ ] Red UNKNOWN verified
- [ ] Deduplicated events verified
- [ ] No attendance for unknown
- [ ] No snapshots by default

## Git Checkpoint

```powershell
git checkout main
git pull origin main
git checkout -b feature/phase-17-unknown-person   # at the START of the phase

# after tests pass:
git status
git diff
git add .
git commit -m "feat(security): classify unknown faces and log deduplicated detection events"
git push -u origin feature/phase-17-unknown-person
```

Recommended commit message: `feat(security): classify unknown faces and log deduplicated detection events`

## HUMAN APPROVAL

Before approving, you should personally:

1. Run the unknown-person scenario and inspect detection_events rows

## NEXT PHASE

Phase 18 runs the formal MVP test campaign.

---

# Phase 18 — FIRST MVP TESTING

> **Branch:** `test/phase-18-mvp-testing` · **Gate:** STOP — human approval required before the next phase

## Objective

Execute a structured MVP test campaign with you and two friends and record **real measured results**: recognition behaviour, false accepts/rejects, FPS, attendance latency.

## Why This Phase Exists

Honest evidence for the ≥90 % accuracy and <5 s targets — or documented gaps.

## Prerequisites

- Previous phase approved and merged (or branch checked out from it)

## Inputs

- Output of the previous phase
- This playbook

## Expected Outputs

- `docs/testing/MVP_TEST_REPORT.md` filled with real observations
- `scripts/eval_recognition.py` implemented (local dataset, no images committed)
- `scripts/measure_attendance_latency.py`
- Tuned config recommendations

## Architecture

```text
Local gitignored dataset: data/eval/<person>/{near,far,dim,bright,left,right,glasses}/*.jpg
eval_recognition → genuine/impostor trials → TAR/FAR/FRR at threshold → report
```

## Files To Inspect

- Repository tree (`Get-ChildItem -Recurse -Depth 3`)
- README.md
- docs/ (including the project PPT/PDF and docs/PLAYBOOK.md)
- TOKEN-OPTIMIZATION.md
- docker-compose.yml
- requirements.txt, requirements-dev.txt, requirements-gpu.txt
- .env.example, .gitignore, .dockerignore, .python-version
- `git log --oneline -15` and `git status`

## Files To Create

- docs/testing/MVP_TEST_REPORT.md (template then real results)
- scripts/eval_recognition.py
- scripts/measure_attendance_latency.py
- docs/testing/MVP_TEST_MATRIX.md

## Files To Modify

- .env.example (tuned defaults, only if justified by results)

## Dependencies

No new dependencies.

## Environment Variables

No new variables.

## Database Changes

None.

## API Changes

None.

## Frontend Changes

None.

## Implementation Sequence

1. Create branch
2. Implement evaluation scripts
3. Create the test matrix + report template
4. Human runs the physical tests (below)
5. Fill the report with real numbers
6. Tune config only with evidence
7. Commit and stop

## EXACT ANTIGRAVITY PROMPT

```text
YOU ARE IMPLEMENTING: PHASE 18 — FIRST MVP TESTING

Follow the GLOBAL RULES (docs/PLAYBOOK.md Section 2). Work ONLY on this phase.


STEP 0 — BRANCH
  git checkout main ; git pull origin main ; git checkout -b test/phase-18-mvp-testing
  (If the branch exists, check it out instead. Never commit to main.)

STEP 1 — INSPECT FIRST (do not modify anything yet)
  - Repository tree (`Get-ChildItem -Recurse -Depth 3`)
  - README.md
  - docs/ (including the project PPT/PDF and docs/PLAYBOOK.md)
  - TOKEN-OPTIMIZATION.md
  - docker-compose.yml
  - requirements.txt, requirements-dev.txt, requirements-gpu.txt
  - .env.example, .gitignore, .dockerignore, .python-version
  - `git log --oneline -15` and `git status`
  Report briefly what already exists that is relevant to this phase. Never assume a file is missing.

OBJECTIVE
  Execute a structured MVP test campaign with you and two friends and record **real measured results**: recognition behaviour, false accepts/rejects, FPS, attendance latency.

STEP 2 — CREATE (only after inspection; skip anything that already exists and extend it instead)
  - docs/testing/MVP_TEST_REPORT.md (template then real results)
  - scripts/eval_recognition.py
  - scripts/measure_attendance_latency.py
  - docs/testing/MVP_TEST_MATRIX.md

STEP 3 — MODIFY
  - .env.example (tuned defaults, only if justified by results)

DO NOT MODIFY / DO NOT DO
  - Invent results
  - Commit evaluation images
  - Change recognition code unless a real bug is found (then fix + test)

DEPENDENCIES: none new  (resolve compatible versions, pin them, verify with `pip check`)
ENVIRONMENT VARIABLES: none new  (placeholders only in .env.example)

STEP 4 — IMPLEMENTATION ORDER
  1. Create branch
  2. Implement evaluation scripts
  3. Create the test matrix + report template
  4. Human runs the physical tests (below)
  5. Fill the report with real numbers
  6. Tune config only with evidence
  7. Commit and stop

SPECIFIC REQUIREMENTS
  - Report must state dataset size (#people, #images per condition), machine spec, threshold used, date
  - Antigravity may build tools and the report template; **the human performs the physical tests** and supplies observations — Antigravity must leave unfilled cells as `TO BE FILLED BY HUMAN`

STEP 5 — TESTS (write and RUN; paste real output)
  - MYSELF: register, recognized live, attendance once
  - FRIEND 1 and FRIEND 2: same
  - MULTIPLE FACES: all 3 in frame → each recognized separately, 3 attendance rows
  - UNKNOWN PERSON: red box, no attendance, ≤ cooldown events
  - NO FACE: empty scene, no crash, no events
  - REPEATED RECOGNITION: stay 5 min, still 1 attendance row
  - LIGHTING CHANGES: bright, dim, backlit — note failures
  - HEAD ROTATION: ±30°, ±45° — note thresholds of failure
  - DIFFERENT DISTANCES: 0.5 m, 1 m, 2 m, 3 m — note max reliable range
  - PHOTO/PHONE SPOOF: hold a photo of a registered person — **record what happens** (the system has no liveness detection; document as a known limitation)

STEP 6 — VERIFICATION (run these and report real results)
  python scripts\eval_recognition.py --dir data\eval --threshold 0.45
  python scripts\measure_attendance_latency.py --runs 10
  pytest -q

STEP 7 — ACCEPTANCE CRITERIA (mark each ✅ / ❌ / NOT VERIFIED — never guess)
  [ ] All 10 test groups executed and recorded
  [ ] Eval script outputs real TAR/FAR with dataset size
  [ ] Attendance latency measured (n=10)
  [ ] Known limitations written (incl. no liveness)
  [ ] No biometric files tracked by Git

STEP 8 — DOCUMENTATION: update README/docs for anything this phase changed; add a short entry to docs/CHANGELOG.md.

STEP 9 — GIT CHECKPOINT (only if tests pass)
  git status ; git diff   (confirm NO secrets, images, videos, .onnx, data/ content staged)
  git add . ; git commit -m "test(mvp): add evaluation scripts and first MVP test report with measured results" ; git push -u origin test/phase-18-mvp-testing

STEP 10 — STOP. Print the REPORT FORMAT from the global rules and write: STOPPED AT PHASE 18 GATE — awaiting human approval. Do NOT start Phase 19.
```

## Commands

Windows PowerShell (run from the repo root unless stated):

```powershell
python scripts\eval_recognition.py --dir data\eval --threshold 0.45
python scripts\measure_attendance_latency.py --runs 10
pytest -q
```

## Tests

- MYSELF: register, recognized live, attendance once
- FRIEND 1 and FRIEND 2: same
- MULTIPLE FACES: all 3 in frame → each recognized separately, 3 attendance rows
- UNKNOWN PERSON: red box, no attendance, ≤ cooldown events
- NO FACE: empty scene, no crash, no events
- REPEATED RECOGNITION: stay 5 min, still 1 attendance row
- LIGHTING CHANGES: bright, dim, backlit — note failures
- HEAD ROTATION: ±30°, ±45° — note thresholds of failure
- DIFFERENT DISTANCES: 0.5 m, 1 m, 2 m, 3 m — note max reliable range
- PHOTO/PHONE SPOOF: hold a photo of a registered person — **record what happens** (the system has no liveness detection; document as a known limitation)

## Manual Verification

1. Perform each test above with the webcam and record outcome (✅/❌), similarity values and notes in the report
2. Time from first appearance to attendance row (10 runs) and compute median/max

## Expected Result

A truthful report. Success is *knowing* the system's real behaviour, including limits (e.g., no liveness detection).

## Failure Conditions

- Fabricated numbers
- Images committed
- Report claims targets achieved without data

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| High false rejects in dim light | Register samples in dim light too; consider ENABLE_CLAHE test via eval (measure!) |
| Friends misidentified | Raise threshold/enable margin; add more registration samples |

## Acceptance Criteria

- [ ] All 10 test groups executed and recorded
- [ ] Eval script outputs real TAR/FAR with dataset size
- [ ] Attendance latency measured (n=10)
- [ ] Known limitations written (incl. no liveness)
- [ ] No biometric files tracked by Git

## Git Checkpoint

```powershell
git checkout main
git pull origin main
git checkout -b test/phase-18-mvp-testing   # at the START of the phase

# after tests pass:
git status
git diff
git add .
git commit -m "test(mvp): add evaluation scripts and first MVP test report with measured results"
git push -u origin test/phase-18-mvp-testing
```

Recommended commit message: `test(mvp): add evaluation scripts and first MVP test report with measured results`

## HUMAN APPROVAL

Before approving, you should personally:

1. Read the report: are the numbers believable and honestly framed?
2. Decide whether recognition quality is acceptable to proceed

## NEXT PHASE

Phase 19 is the MVP human approval gate.

---

# Phase 19 — MVP HUMAN APPROVAL

> **Branch:** `(no new branch — tag on main after merge)` · **Gate:** HARD GATE — DO NOT PROCEED until you confirm the attendance system works

## Objective

Human-only checkpoint. Antigravity prepares a short MVP readiness summary and tags the release after you approve.

## Why This Phase Exists

Everything after this (video, RTSP, security, redis) builds on a trustworthy attendance MVP.

## Prerequisites

- Previous phase approved and merged (or branch checked out from it)

## Inputs

- Phase 18 report
- All earlier phases merged into main

## Expected Outputs

- `docs/MVP_READINESS.md`
- Git tag `mvp-attendance-v0.1` (after your approval)

## Architecture

No code. Review gate.

## Files To Inspect

- Repository tree (`Get-ChildItem -Recurse -Depth 3`)
- README.md
- docs/ (including the project PPT/PDF and docs/PLAYBOOK.md)
- TOKEN-OPTIMIZATION.md
- docker-compose.yml
- requirements.txt, requirements-dev.txt, requirements-gpu.txt
- .env.example, .gitignore, .dockerignore, .python-version
- `git log --oneline -15` and `git status`

## Files To Create

- docs/MVP_READINESS.md

## Files To Modify

No existing files (other than the Git-ignored and doc updates noted).

## Dependencies

No new dependencies.

## Environment Variables

No new variables.

## Database Changes

None.

## API Changes

None.

## Frontend Changes

None.

## Implementation Sequence

1. Summarise what works / what does not / known limitations from real evidence
2. List open defects with severity
3. Wait for human approval
4. After approval only: tag

## EXACT ANTIGRAVITY PROMPT

```text
YOU ARE IMPLEMENTING: PHASE 19 — MVP HUMAN APPROVAL

Follow the GLOBAL RULES (docs/PLAYBOOK.md Section 2). Work ONLY on this phase.


STEP 0 — BRANCH
  git checkout main ; git pull origin main ; git checkout -b (no new branch — tag on main after merge)
  (If the branch exists, check it out instead. Never commit to main.)

STEP 1 — INSPECT FIRST (do not modify anything yet)
  - Repository tree (`Get-ChildItem -Recurse -Depth 3`)
  - README.md
  - docs/ (including the project PPT/PDF and docs/PLAYBOOK.md)
  - TOKEN-OPTIMIZATION.md
  - docker-compose.yml
  - requirements.txt, requirements-dev.txt, requirements-gpu.txt
  - .env.example, .gitignore, .dockerignore, .python-version
  - `git log --oneline -15` and `git status`
  Report briefly what already exists that is relevant to this phase. Never assume a file is missing.

OBJECTIVE
  Human-only checkpoint. Antigravity prepares a short MVP readiness summary and tags the release after you approve.

STEP 2 — CREATE (only after inspection; skip anything that already exists and extend it instead)
  - docs/MVP_READINESS.md

STEP 3 — MODIFY
  - (nothing)

DO NOT MODIFY / DO NOT DO
  - Start Phase 20
  - Add features
  - Tag before the human says 'approved'

DEPENDENCIES: none new  (resolve compatible versions, pin them, verify with `pip check`)
ENVIRONMENT VARIABLES: none new  (placeholders only in .env.example)

STEP 4 — IMPLEMENTATION ORDER
  1. Summarise what works / what does not / known limitations from real evidence
  2. List open defects with severity
  3. Wait for human approval
  4. After approval only: tag

STEP 5 — TESTS (write and RUN; paste real output)
  - Full test suite green on `main`
  - Fresh clone dry-run: follow SETUP_WINDOWS.md from scratch on a clean folder and reach a working login

STEP 6 — VERIFICATION (run these and report real results)
  git checkout main
  git pull origin main
  git tag -a mvp-attendance-v0.1 -m "Attendance MVP approved"
  git push origin mvp-attendance-v0.1
  pytest -q
  docker compose up -d db
  uvicorn backend.app.main:app --port 8000
  streamlit run frontend\app.py

STEP 7 — ACCEPTANCE CRITERIA (mark each ✅ / ❌ / NOT VERIFIED — never guess)
  [ ] Human explicitly approved attendance MVP
  [ ] Full test suite green
  [ ] Fresh-clone setup verified
  [ ] Readiness doc written honestly

STEP 8 — DOCUMENTATION: update README/docs for anything this phase changed; add a short entry to docs/CHANGELOG.md.

STEP 9 — GIT CHECKPOINT (only if tests pass)
  git status ; git diff   (confirm NO secrets, images, videos, .onnx, data/ content staged)
  git add . ; git commit -m "docs: add MVP readiness summary" ; git push -u origin (no new branch — tag on main after merge)

STEP 10 — STOP. Print the REPORT FORMAT from the global rules and write: STOPPED AT PHASE 19 GATE — awaiting human approval. Do NOT start Phase 20.
```

## Commands

Windows PowerShell (run from the repo root unless stated):

```powershell
git checkout main
git pull origin main
git tag -a mvp-attendance-v0.1 -m "Attendance MVP approved"
git push origin mvp-attendance-v0.1
pytest -q
docker compose up -d db
uvicorn backend.app.main:app --port 8000
streamlit run frontend\app.py
```

## Tests

- Full test suite green on `main`
- Fresh clone dry-run: follow SETUP_WINDOWS.md from scratch on a clean folder and reach a working login

## Manual Verification

1. Live demo to yourself: register → recognize → attendance → duplicate prevention → unknown → records page
2. Check the unknown/no-attendance behaviour once more
3. Check privacy: no images on disk, no secrets tracked

## Expected Result

You are satisfied that attendance works on the laptop webcam.

## Failure Conditions

- Recognition unreliable for you/friends
- Duplicate attendance
- Unknown gets attendance
- Fresh clone setup fails

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| Not satisfied with accuracy | Return to Phases 8/13/18: more samples, better lighting, recalibration — do NOT proceed |

## Acceptance Criteria

- [ ] Human explicitly approved attendance MVP
- [ ] Full test suite green
- [ ] Fresh-clone setup verified
- [ ] Readiness doc written honestly

## Git Checkpoint

```powershell
git checkout main
git pull origin main
git checkout -b (no new branch — tag on main after merge)   # at the START of the phase

# after tests pass:
git status
git diff
git add .
git commit -m "docs: add MVP readiness summary"
git push -u origin (no new branch — tag on main after merge)
```

Recommended commit message: `docs: add MVP readiness summary`

## HUMAN APPROVAL

Before approving, you should personally:

1. Type 'MVP APPROVED' to Antigravity only after completing every manual check above

## NEXT PHASE

Phase 20 adds video-file input so you can test without a live person present.

---

# Phase 20 — VIDEO FILE SUPPORT

> **Branch:** `feature/phase-20-video-file` · **Gate:** STOP — human approval required before the next phase

## Objective

Add `VideoFileSource` so the same pipeline can process pre-recorded video, with safe file handling.

## Why This Phase Exists

Reproducible tests and demos without a live camera; stepping stone to CCTV.

## Prerequisites

- Previous phase approved and merged (or branch checked out from it)

## Inputs

- Output of the previous phase
- This playbook

## Expected Outputs

- `cameras/video_file.py`
- Camera of type `VIDEO_FILE`
- CLI `scripts/run_video.py`
- Upload endpoint (ADMIN) into `data/videos/`

## Architecture

```text
CameraSource ← WebcamSource | VideoFileSource(path, loop, realtime_pacing)
Same worker → same pipeline → same handlers
```

## Files To Inspect

- Repository tree (`Get-ChildItem -Recurse -Depth 3`)
- README.md
- docs/ (including the project PPT/PDF and docs/PLAYBOOK.md)
- TOKEN-OPTIMIZATION.md
- docker-compose.yml
- requirements.txt, requirements-dev.txt, requirements-gpu.txt
- .env.example, .gitignore, .dockerignore, .python-version
- `git log --oneline -15` and `git status`

## Files To Create

- backend/app/cameras/video_file.py
- scripts/run_video.py
- backend/tests/cameras/test_video_source.py

## Files To Modify

- backend/app/cameras/manager.py
- backend/app/api/v1/cameras.py (minimal create for video)
- .env.example (VIDEO_DIR=data/videos, MAX_VIDEO_BYTES)

## Dependencies

No new dependencies.

## Environment Variables

- VIDEO_DIR=data/videos
- MAX_VIDEO_BYTES=524288000
- VIDEO_REALTIME=true

## Database Changes

None.

## API Changes

`POST /cameras/video-upload` (ADMIN, multipart, mp4/avi/mkv, size-limited, UUID filename).

## Frontend Changes

None.

## Implementation Sequence

1. Create branch
2. Implement source with pacing + EOF
3. Upload endpoint with validation
4. Camera row creation for video
5. Tests
6. Run on a recorded clip of yourself
7. Commit and stop

## EXACT ANTIGRAVITY PROMPT

```text
YOU ARE IMPLEMENTING: PHASE 20 — VIDEO FILE SUPPORT

Follow the GLOBAL RULES (docs/PLAYBOOK.md Section 2). Work ONLY on this phase.


STEP 0 — BRANCH
  git checkout main ; git pull origin main ; git checkout -b feature/phase-20-video-file
  (If the branch exists, check it out instead. Never commit to main.)

STEP 1 — INSPECT FIRST (do not modify anything yet)
  - Repository tree (`Get-ChildItem -Recurse -Depth 3`)
  - README.md
  - docs/ (including the project PPT/PDF and docs/PLAYBOOK.md)
  - TOKEN-OPTIMIZATION.md
  - docker-compose.yml
  - requirements.txt, requirements-dev.txt, requirements-gpu.txt
  - .env.example, .gitignore, .dockerignore, .python-version
  - `git log --oneline -15` and `git status`
  Report briefly what already exists that is relevant to this phase. Never assume a file is missing.

OBJECTIVE
  Add `VideoFileSource` so the same pipeline can process pre-recorded video, with safe file handling.

STEP 2 — CREATE (only after inspection; skip anything that already exists and extend it instead)
  - backend/app/cameras/video_file.py
  - scripts/run_video.py
  - backend/tests/cameras/test_video_source.py

STEP 3 — MODIFY
  - backend/app/cameras/manager.py
  - backend/app/api/v1/cameras.py (minimal create for video)
  - .env.example (VIDEO_DIR=data/videos, MAX_VIDEO_BYTES)

DO NOT MODIFY / DO NOT DO
  - Commit videos
  - Trust client filenames
  - Allow paths outside `VIDEO_DIR`

DEPENDENCIES: none new  (resolve compatible versions, pin them, verify with `pip check`)
ENVIRONMENT VARIABLES: VIDEO_DIR=data/videos; MAX_VIDEO_BYTES=524288000; VIDEO_REALTIME=true  (placeholders only in .env.example)

STEP 4 — IMPLEMENTATION ORDER
  1. Create branch
  2. Implement source with pacing + EOF
  3. Upload endpoint with validation
  4. Camera row creation for video
  5. Tests
  6. Run on a recorded clip of yourself
  7. Commit and stop

SPECIFIC REQUIREMENTS
  - Resolve and verify the real path stays inside `VIDEO_DIR` (path traversal tests)
  - End-of-file: mark worker STOPPED(EOF) or loop if configured; never crash
  - `VIDEO_REALTIME=true` paces frames by video FPS; false = process as fast as possible (for tests/benchmarks)

STEP 5 — TESTS (write and RUN; paste real output)
  - Valid clip yields frames then EOF
  - Path traversal `..\..\x.mp4` rejected
  - Wrong extension/magic bytes rejected
  - Oversized upload rejected
  - Loop mode restarts
  - Missing file → camera status ERROR, API stays up
  - Recognition+attendance work from video (local clip)

STEP 6 — VERIFICATION (run these and report real results)
  python scripts\run_video.py --file data\videos\test.mp4 --no-realtime
  pytest backend/tests/cameras/test_video_source.py -v

STEP 7 — ACCEPTANCE CRITERIA (mark each ✅ / ❌ / NOT VERIFIED — never guess)
  [ ] Video pipeline works end to end
  [ ] Traversal/upload tests pass
  [ ] EOF handled
  [ ] Videos git-ignored

STEP 8 — DOCUMENTATION: update README/docs for anything this phase changed; add a short entry to docs/CHANGELOG.md.

STEP 9 — GIT CHECKPOINT (only if tests pass)
  git status ; git diff   (confirm NO secrets, images, videos, .onnx, data/ content staged)
  git add . ; git commit -m "feat(cameras): add video file source and safe upload" ; git push -u origin feature/phase-20-video-file

STEP 10 — STOP. Print the REPORT FORMAT from the global rules and write: STOPPED AT PHASE 20 GATE — awaiting human approval. Do NOT start Phase 21.
```

## Commands

Windows PowerShell (run from the repo root unless stated):

```powershell
python scripts\run_video.py --file data\videos\test.mp4 --no-realtime
pytest backend/tests/cameras/test_video_source.py -v
```

## Tests

- Valid clip yields frames then EOF
- Path traversal `..\..\x.mp4` rejected
- Wrong extension/magic bytes rejected
- Oversized upload rejected
- Loop mode restarts
- Missing file → camera status ERROR, API stays up
- Recognition+attendance work from video (local clip)

## Manual Verification

1. Record 20 s clip of yourself, run it, see green box and attendance
2. Upload a text file renamed .mp4 → rejected

## Expected Result

Same recognition and attendance behaviour from a video file.

## Failure Conditions

- Path escapes data/videos
- EOF crashes worker

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| Codec unsupported | Re-encode with ffmpeg to H.264 mp4 |
| Video plays too fast | Enable `VIDEO_REALTIME` |

## Acceptance Criteria

- [ ] Video pipeline works end to end
- [ ] Traversal/upload tests pass
- [ ] EOF handled
- [ ] Videos git-ignored

## Git Checkpoint

```powershell
git checkout main
git pull origin main
git checkout -b feature/phase-20-video-file   # at the START of the phase

# after tests pass:
git status
git diff
git add .
git commit -m "feat(cameras): add video file source and safe upload"
git push -u origin feature/phase-20-video-file
```

Recommended commit message: `feat(cameras): add video file source and safe upload`

## HUMAN APPROVAL

Before approving, you should personally:

1. Run the pipeline on your own clip

## NEXT PHASE

Phase 21 adds RTSP/CCTV.

---

# Phase 21 — RTSP / CCTV SUPPORT

> **Branch:** `feature/phase-21-rtsp` · **Gate:** STOP — human approval required before the next phase

## Objective

Add `RtspSource` with reconnect/backoff, timeouts and credentials supplied via environment variables (never stored in the database or URL).

## Why This Phase Exists

Real CCTV deployment path. Verified against a simulated stream if no real camera is available.

## Prerequisites

- Previous phase approved and merged (or branch checked out from it)

## Inputs

- Output of the previous phase
- This playbook

## Expected Outputs

- `cameras/rtsp.py`
- Credential resolver using `credentials_ref`
- Docs for simulating RTSP (MediaMTX + ffmpeg loop of a local video)

## Architecture

```text
cameras.source_url = rtsp://192.168.1.50:554/stream1   (no user:pass)
cameras.credentials_ref = CAMERA_1_CREDENTIALS         → env CAMERA_1_CREDENTIALS='user:pass'
RtspSource builds the authenticated URL in memory only; masks it in all logs
```
Use TCP transport (`OPENCV_FFMPEG_CAPTURE_OPTIONS=rtsp_transport;tcp`), open/read timeouts, exponential backoff reconnect (1→30 s).

## Files To Inspect

- Repository tree (`Get-ChildItem -Recurse -Depth 3`)
- README.md
- docs/ (including the project PPT/PDF and docs/PLAYBOOK.md)
- TOKEN-OPTIMIZATION.md
- docker-compose.yml
- requirements.txt, requirements-dev.txt, requirements-gpu.txt
- .env.example, .gitignore, .dockerignore, .python-version
- `git log --oneline -15` and `git status`

## Files To Create

- backend/app/cameras/rtsp.py
- backend/app/cameras/credentials.py
- docs/RTSP_SETUP.md
- backend/tests/cameras/test_rtsp_source.py

## Files To Modify

- backend/app/cameras/manager.py
- .env.example (CAMERA_1_CREDENTIALS= placeholder)

## Dependencies

No new dependencies.

## Environment Variables

- CAMERA_1_CREDENTIALS (placeholder)
- RTSP_OPEN_TIMEOUT_MS=5000
- RTSP_RECONNECT_MAX_SECONDS=30

## Database Changes

None.

## API Changes

None.

## Frontend Changes

None.

## Implementation Sequence

1. Create branch
2. Credential resolver + URL masking tests
3. RtspSource with reconnect
4. Mocked-capture tests (open failure, read failure, recovery)
5. Document MediaMTX simulation
6. If possible run simulation and test live
7. Commit and stop

## EXACT ANTIGRAVITY PROMPT

```text
YOU ARE IMPLEMENTING: PHASE 21 — RTSP / CCTV SUPPORT

Follow the GLOBAL RULES (docs/PLAYBOOK.md Section 2). Work ONLY on this phase.


STEP 0 — BRANCH
  git checkout main ; git pull origin main ; git checkout -b feature/phase-21-rtsp
  (If the branch exists, check it out instead. Never commit to main.)

STEP 1 — INSPECT FIRST (do not modify anything yet)
  - Repository tree (`Get-ChildItem -Recurse -Depth 3`)
  - README.md
  - docs/ (including the project PPT/PDF and docs/PLAYBOOK.md)
  - TOKEN-OPTIMIZATION.md
  - docker-compose.yml
  - requirements.txt, requirements-dev.txt, requirements-gpu.txt
  - .env.example, .gitignore, .dockerignore, .python-version
  - `git log --oneline -15` and `git status`
  Report briefly what already exists that is relevant to this phase. Never assume a file is missing.

OBJECTIVE
  Add `RtspSource` with reconnect/backoff, timeouts and credentials supplied via environment variables (never stored in the database or URL).

STEP 2 — CREATE (only after inspection; skip anything that already exists and extend it instead)
  - backend/app/cameras/rtsp.py
  - backend/app/cameras/credentials.py
  - docs/RTSP_SETUP.md
  - backend/tests/cameras/test_rtsp_source.py

STEP 3 — MODIFY
  - backend/app/cameras/manager.py
  - .env.example (CAMERA_1_CREDENTIALS= placeholder)

DO NOT MODIFY / DO NOT DO
  - Commit camera URLs with credentials
  - Log full RTSP URLs
  - Claim RTSP works if only mock-tested

DEPENDENCIES: none new  (resolve compatible versions, pin them, verify with `pip check`)
ENVIRONMENT VARIABLES: CAMERA_1_CREDENTIALS (placeholder); RTSP_OPEN_TIMEOUT_MS=5000; RTSP_RECONNECT_MAX_SECONDS=30  (placeholders only in .env.example)

STEP 4 — IMPLEMENTATION ORDER
  1. Create branch
  2. Credential resolver + URL masking tests
  3. RtspSource with reconnect
  4. Mocked-capture tests (open failure, read failure, recovery)
  5. Document MediaMTX simulation
  6. If possible run simulation and test live
  7. Commit and stop

SPECIFIC REQUIREMENTS
  - Reject URLs containing `@` userinfo at the API level
  - If no real/simulated RTSP source is available, mark acceptance 'RTSP live test: NOT VERIFIED' — mock-based tests only

STEP 5 — TESTS (write and RUN; paste real output)
  - URL with embedded credentials rejected
  - Credentials injected from env and masked in logs (assert no password in captured logs)
  - Open failure → ERROR + retry with backoff
  - Read failure mid-stream → reconnect
  - Missing env var → clear error, no crash
  - Simulated live stream (if available): detection + attendance work

STEP 6 — VERIFICATION (run these and report real results)
  # Optional simulation (Docker + ffmpeg required)
docker run --rm -d --name mediamtx -p 8554:8554 bluenviron/mediamtx
  ffmpeg -re -stream_loop -1 -i data\videos\test.mp4 -c copy -f rtsp rtsp://127.0.0.1:8554/test
  pytest backend/tests/cameras/test_rtsp_source.py -v

STEP 7 — ACCEPTANCE CRITERIA (mark each ✅ / ❌ / NOT VERIFIED — never guess)
  [ ] Credential handling tested
  [ ] Reconnect tested (mock and, if possible, live)
  [ ] Live verification status stated honestly
  [ ] RTSP_SETUP.md written

STEP 8 — DOCUMENTATION: update README/docs for anything this phase changed; add a short entry to docs/CHANGELOG.md.

STEP 9 — GIT CHECKPOINT (only if tests pass)
  git status ; git diff   (confirm NO secrets, images, videos, .onnx, data/ content staged)
  git add . ; git commit -m "feat(cameras): add RTSP source with reconnect and env-based credentials" ; git push -u origin feature/phase-21-rtsp

STEP 10 — STOP. Print the REPORT FORMAT from the global rules and write: STOPPED AT PHASE 21 GATE — awaiting human approval. Do NOT start Phase 22.
```

## Commands

Windows PowerShell (run from the repo root unless stated):

```powershell
# Optional simulation (Docker + ffmpeg required)
docker run --rm -d --name mediamtx -p 8554:8554 bluenviron/mediamtx
ffmpeg -re -stream_loop -1 -i data\videos\test.mp4 -c copy -f rtsp rtsp://127.0.0.1:8554/test
pytest backend/tests/cameras/test_rtsp_source.py -v
```

## Tests

- URL with embedded credentials rejected
- Credentials injected from env and masked in logs (assert no password in captured logs)
- Open failure → ERROR + retry with backoff
- Read failure mid-stream → reconnect
- Missing env var → clear error, no crash
- Simulated live stream (if available): detection + attendance work

## Manual Verification

1. Run MediaMTX + ffmpeg loop and open the stream through the dashboard (if Docker available)

## Expected Result

RTSP source behaves robustly; credentials never leak.

## Failure Conditions

- Credentials in DB/logs/repo
- Worker dies on network drop

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| `Could not open RTSP` | Check URL path/port, firewall, TCP transport option |
| High latency | Lower resolution, set buffer size 1, drop old frames |

## Acceptance Criteria

- [ ] Credential handling tested
- [ ] Reconnect tested (mock and, if possible, live)
- [ ] Live verification status stated honestly
- [ ] RTSP_SETUP.md written

## Git Checkpoint

```powershell
git checkout main
git pull origin main
git checkout -b feature/phase-21-rtsp   # at the START of the phase

# after tests pass:
git status
git diff
git add .
git commit -m "feat(cameras): add RTSP source with reconnect and env-based credentials"
git push -u origin feature/phase-21-rtsp
```

Recommended commit message: `feat(cameras): add RTSP source with reconnect and env-based credentials`

## HUMAN APPROVAL

Before approving, you should personally:

1. Grep repo/logs for any credential strings
2. Note whether live RTSP was verified or only mocked

## NEXT PHASE

Phase 22 adds camera management UI/API.

---

# Phase 22 — CAMERA MANAGEMENT

> **Branch:** `feature/phase-22-camera-management` · **Gate:** STOP — human approval required before the next phase

## Objective

Complete camera CRUD, connection test, status tracking (heartbeat), enable/disable, and the Cameras page.

## Why This Phase Exists

Operators must configure and monitor cameras without editing the database.

## Prerequisites

- Previous phase approved and merged (or branch checked out from it)

## Inputs

- Output of the previous phase
- This playbook

## Expected Outputs

- Full cameras API per Section 5.5
- Status heartbeat (`last_seen_at`, status transitions)
- Cameras page

## Architecture

```text
CameraManager reads cameras table → starts workers for enabled cameras → updates status ONLINE/OFFLINE/ERROR every 10 s
```

## Files To Inspect

- Repository tree (`Get-ChildItem -Recurse -Depth 3`)
- README.md
- docs/ (including the project PPT/PDF and docs/PLAYBOOK.md)
- TOKEN-OPTIMIZATION.md
- docker-compose.yml
- requirements.txt, requirements-dev.txt, requirements-gpu.txt
- .env.example, .gitignore, .dockerignore, .python-version
- `git log --oneline -15` and `git status`

## Files To Create

- backend/app/services/camera_service.py
- backend/app/schemas/camera.py
- frontend/pages/ Cameras page
- backend/tests/api/test_cameras.py

## Files To Modify

- backend/app/api/v1/cameras.py
- backend/app/cameras/manager.py

## Dependencies

No new dependencies.

## Environment Variables

No new variables.

## Database Changes

None.

## API Changes

`GET/POST /cameras`, `GET/PATCH/DELETE /cameras/{id}` (DELETE = disable if referenced), `POST /cameras/{id}/test`. Responses mask credentials.

## Frontend Changes

Table with status badge, location, type; add/edit form with source-type specific fields; Test Connection button; Enable/Disable; Start/Stop worker.

## Implementation Sequence

1. Create branch
2. Service + schemas + validation per source type
3. Endpoints + audit
4. Heartbeat/status updater
5. UI page
6. Tests
7. Commit and stop

## EXACT ANTIGRAVITY PROMPT

```text
YOU ARE IMPLEMENTING: PHASE 22 — CAMERA MANAGEMENT

Follow the GLOBAL RULES (docs/PLAYBOOK.md Section 2). Work ONLY on this phase.


STEP 0 — BRANCH
  git checkout main ; git pull origin main ; git checkout -b feature/phase-22-camera-management
  (If the branch exists, check it out instead. Never commit to main.)

STEP 1 — INSPECT FIRST (do not modify anything yet)
  - Repository tree (`Get-ChildItem -Recurse -Depth 3`)
  - README.md
  - docs/ (including the project PPT/PDF and docs/PLAYBOOK.md)
  - TOKEN-OPTIMIZATION.md
  - docker-compose.yml
  - requirements.txt, requirements-dev.txt, requirements-gpu.txt
  - .env.example, .gitignore, .dockerignore, .python-version
  - `git log --oneline -15` and `git status`
  Report briefly what already exists that is relevant to this phase. Never assume a file is missing.

OBJECTIVE
  Complete camera CRUD, connection test, status tracking (heartbeat), enable/disable, and the Cameras page.

STEP 2 — CREATE (only after inspection; skip anything that already exists and extend it instead)
  - backend/app/services/camera_service.py
  - backend/app/schemas/camera.py
  - frontend/pages/ Cameras page
  - backend/tests/api/test_cameras.py

STEP 3 — MODIFY
  - backend/app/api/v1/cameras.py
  - backend/app/cameras/manager.py

DO NOT MODIFY / DO NOT DO
  - Return source URLs with secrets
  - Hard-delete cameras referenced by records

DEPENDENCIES: none new  (resolve compatible versions, pin them, verify with `pip check`)
ENVIRONMENT VARIABLES: none new  (placeholders only in .env.example)

STEP 4 — IMPLEMENTATION ORDER
  1. Create branch
  2. Service + schemas + validation per source type
  3. Endpoints + audit
  4. Heartbeat/status updater
  5. UI page
  6. Tests
  7. Commit and stop

STEP 5 — TESTS (write and RUN; paste real output)
  - Create webcam/video/RTSP cameras; invalid source rejected
  - Credentials masked in responses
  - Test endpoint: unreachable RTSP → ok=false within 5 s timeout
  - Disable stops worker
  - Delete of referenced camera → disabled, not removed
  - Operator read-only

STEP 6 — VERIFICATION (run these and report real results)
  pytest backend/tests/api/test_cameras.py -v

STEP 7 — ACCEPTANCE CRITERIA (mark each ✅ / ❌ / NOT VERIFIED — never guess)
  [ ] CRUD verified
  [ ] Status transitions verified
  [ ] Credential masking tested
  [ ] RBAC tested

STEP 8 — DOCUMENTATION: update README/docs for anything this phase changed; add a short entry to docs/CHANGELOG.md.

STEP 9 — GIT CHECKPOINT (only if tests pass)
  git status ; git diff   (confirm NO secrets, images, videos, .onnx, data/ content staged)
  git add . ; git commit -m "feat(cameras): add camera management API, status heartbeat and Cameras page" ; git push -u origin feature/phase-22-camera-management

STEP 10 — STOP. Print the REPORT FORMAT from the global rules and write: STOPPED AT PHASE 22 GATE — awaiting human approval. Do NOT start Phase 23.
```

## Commands

Windows PowerShell (run from the repo root unless stated):

```powershell
pytest backend/tests/api/test_cameras.py -v
```

## Tests

- Create webcam/video/RTSP cameras; invalid source rejected
- Credentials masked in responses
- Test endpoint: unreachable RTSP → ok=false within 5 s timeout
- Disable stops worker
- Delete of referenced camera → disabled, not removed
- Operator read-only

## Manual Verification

1. Add a video camera, test it, start it, see status ONLINE; unplug/disable and see OFFLINE/DISABLED

## Expected Result

Cameras are manageable from the UI with accurate status.

## Failure Conditions

- Status stuck ONLINE after failure
- Credentials visible

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| Test hangs | Enforce timeout with a worker thread/future |
| Status flapping | Add hysteresis (3 failed checks) |

## Acceptance Criteria

- [ ] CRUD verified
- [ ] Status transitions verified
- [ ] Credential masking tested
- [ ] RBAC tested

## Git Checkpoint

```powershell
git checkout main
git pull origin main
git checkout -b feature/phase-22-camera-management   # at the START of the phase

# after tests pass:
git status
git diff
git add .
git commit -m "feat(cameras): add camera management API, status heartbeat and Cameras page"
git push -u origin feature/phase-22-camera-management
```

Recommended commit message: `feat(cameras): add camera management API, status heartbeat and Cameras page`

## HUMAN APPROVAL

Before approving, you should personally:

1. Create/test/disable a camera in the UI

## NEXT PHASE

Phase 23 builds the event layer used by the Security module.

---

# Phase 23 — SECURITY EVENTS (EVENT LAYER)

> **Branch:** `feature/phase-23-event-layer` · **Gate:** STOP — human approval required before the next phase

## Objective

Refactor observation handling into an in-process **EventBus** with typed events and handlers (Attendance, Detection/Movement, Security), keeping behaviour identical, and expose `/events` with filters.

## Why This Phase Exists

Cleanly separates the shared engine from its consumers; Redis can later replace the bus transport without touching handlers (ADR-10).

## Prerequisites

- Previous phase approved and merged (or branch checked out from it)

## Inputs

- Output of the previous phase
- This playbook

## Expected Outputs

- `events/bus.py` (interface + in-memory implementation)
- Handlers registered at startup
- `GET /events`
- Detection Events page

## Architecture

```text
Worker → bus.publish(FaceObserved{camera, kind, student_id|blacklist_id, similarity, bbox, track_id, ts})
   ├─ AttendanceHandler   (kind=STUDENT)
   ├─ DetectionHandler    (all kinds → detection_events, throttled)
   └─ SecurityHandler     (UNKNOWN/BLACKLISTED → alert policy in Phase 25)
Bus: non-blocking queue + dispatcher thread; handler exceptions isolated and logged
```

## Files To Inspect

- Repository tree (`Get-ChildItem -Recurse -Depth 3`)
- README.md
- docs/ (including the project PPT/PDF and docs/PLAYBOOK.md)
- TOKEN-OPTIMIZATION.md
- docker-compose.yml
- requirements.txt, requirements-dev.txt, requirements-gpu.txt
- .env.example, .gitignore, .dockerignore, .python-version
- `git log --oneline -15` and `git status`

## Files To Create

- backend/app/events/bus.py
- backend/app/events/types.py
- backend/app/events/handlers/{attendance,detection,security}.py
- backend/app/api/v1/events.py
- frontend/pages/ Detection Events page
- backend/tests/unit/test_event_bus.py

## Files To Modify

- backend/app/cameras/worker.py (publish instead of calling services directly)
- backend/app/main.py (register handlers)

## Dependencies

No new dependencies.

## Environment Variables

No new variables.

## Database Changes

None.

## API Changes

None.

## Frontend Changes

None.

## Implementation Sequence

1. Create branch
2. Write bus and event types with tests
3. Move attendance/detection logic into handlers (no behaviour change)
4. Run all earlier tests (regression)
5. Events API + page
6. Commit and stop

## EXACT ANTIGRAVITY PROMPT

```text
YOU ARE IMPLEMENTING: PHASE 23 — SECURITY EVENTS (EVENT LAYER)

Follow the GLOBAL RULES (docs/PLAYBOOK.md Section 2). Work ONLY on this phase.


STEP 0 — BRANCH
  git checkout main ; git pull origin main ; git checkout -b feature/phase-23-event-layer
  (If the branch exists, check it out instead. Never commit to main.)

STEP 1 — INSPECT FIRST (do not modify anything yet)
  - Repository tree (`Get-ChildItem -Recurse -Depth 3`)
  - README.md
  - docs/ (including the project PPT/PDF and docs/PLAYBOOK.md)
  - TOKEN-OPTIMIZATION.md
  - docker-compose.yml
  - requirements.txt, requirements-dev.txt, requirements-gpu.txt
  - .env.example, .gitignore, .dockerignore, .python-version
  - `git log --oneline -15` and `git status`
  Report briefly what already exists that is relevant to this phase. Never assume a file is missing.

OBJECTIVE
  Refactor observation handling into an in-process **EventBus** with typed events and handlers (Attendance, Detection/Movement, Security), keeping behaviour identical, and expose `/events` with filters.

STEP 2 — CREATE (only after inspection; skip anything that already exists and extend it instead)
  - backend/app/events/bus.py
  - backend/app/events/types.py
  - backend/app/events/handlers/{attendance,detection,security}.py
  - backend/app/api/v1/events.py
  - frontend/pages/ Detection Events page
  - backend/tests/unit/test_event_bus.py

STEP 3 — MODIFY
  - backend/app/cameras/worker.py (publish instead of calling services directly)
  - backend/app/main.py (register handlers)

DO NOT MODIFY / DO NOT DO
  - Change attendance or unknown behaviour
  - Introduce Redis/Kafka

DEPENDENCIES: none new  (resolve compatible versions, pin them, verify with `pip check`)
ENVIRONMENT VARIABLES: none new  (placeholders only in .env.example)

STEP 4 — IMPLEMENTATION ORDER
  1. Create branch
  2. Write bus and event types with tests
  3. Move attendance/detection logic into handlers (no behaviour change)
  4. Run all earlier tests (regression)
  5. Events API + page
  6. Commit and stop

STEP 5 — TESTS (write and RUN; paste real output)
  - Publish → all subscribers receive
  - Failing handler does not stop others
  - Queue overflow policy (drop oldest + counter)
  - Regression: attendance/unknown tests still pass
  - Events API filters (camera, type, student, date)
  - Shutdown drains queue

STEP 6 — VERIFICATION (run these and report real results)
  pytest -q
  pytest backend/tests/unit/test_event_bus.py -v

STEP 7 — ACCEPTANCE CRITERIA (mark each ✅ / ❌ / NOT VERIFIED — never guess)
  [ ] Regression suite green
  [ ] Bus tests pass
  [ ] Events API/page work
  [ ] No new infra added

STEP 8 — DOCUMENTATION: update README/docs for anything this phase changed; add a short entry to docs/CHANGELOG.md.

STEP 9 — GIT CHECKPOINT (only if tests pass)
  git status ; git diff   (confirm NO secrets, images, videos, .onnx, data/ content staged)
  git add . ; git commit -m "refactor(events): add in-process event bus and handler layer; add events API" ; git push -u origin feature/phase-23-event-layer

STEP 10 — STOP. Print the REPORT FORMAT from the global rules and write: STOPPED AT PHASE 23 GATE — awaiting human approval. Do NOT start Phase 24.
```

## Commands

Windows PowerShell (run from the repo root unless stated):

```powershell
pytest -q
pytest backend/tests/unit/test_event_bus.py -v
```

## Tests

- Publish → all subscribers receive
- Failing handler does not stop others
- Queue overflow policy (drop oldest + counter)
- Regression: attendance/unknown tests still pass
- Events API filters (camera, type, student, date)
- Shutdown drains queue

## Manual Verification

1. Repeat Phase 15/17 scenarios; behaviour unchanged
2. View Detection Events page filtering by type

## Expected Result

Same behaviour, cleaner structure, new events API.

## Failure Conditions

- Regression in attendance/unknown
- Handler exception kills worker

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| Events delayed | Check dispatcher thread and queue depth metrics |
| Duplicate handling | Ensure handlers registered once on startup |

## Acceptance Criteria

- [ ] Regression suite green
- [ ] Bus tests pass
- [ ] Events API/page work
- [ ] No new infra added

## Git Checkpoint

```powershell
git checkout main
git pull origin main
git checkout -b feature/phase-23-event-layer   # at the START of the phase

# after tests pass:
git status
git diff
git add .
git commit -m "refactor(events): add in-process event bus and handler layer; add events API"
git push -u origin feature/phase-23-event-layer
```

Recommended commit message: `refactor(events): add in-process event bus and handler layer; add events API`

## HUMAN APPROVAL

Before approving, you should personally:

1. Re-run the attendance and unknown scenarios

## NEXT PHASE

Phase 24 adds blacklist management.

---

# Phase 24 — BLACKLIST MANAGEMENT

> **Branch:** `feature/phase-24-blacklist` · **Gate:** STOP — human approval required before the next phase

## Objective

Implement blacklist entries (add, edit, deactivate, view, search), reuse the registration flow to enroll blacklist faces, and extend recognition so a matching blacklist identity yields `kind=BLACKLISTED`.

## Why This Phase Exists

Higher-priority security identities handled by the same engine (ADR-12).

## Prerequisites

- Previous phase approved and merged (or branch checked out from it)

## Inputs

- Output of the previous phase
- This playbook

## Expected Outputs

- Blacklist CRUD + face enrollment
- Pipeline returns BLACKLISTED
- Red box with thick border + label `BLACKLISTED`
- Blacklist page

## Architecture

```text
face_embeddings.blacklist_entry_id set → same nearest search → owner type decides kind
Deactivate → entry INACTIVE and its embeddings is_active=false (excluded from search)
```
If the same face matches both a student and a blacklist entry, the **higher similarity wins**; tie → BLACKLISTED (safer), and log a data-quality warning.

## Files To Inspect

- Repository tree (`Get-ChildItem -Recurse -Depth 3`)
- README.md
- docs/ (including the project PPT/PDF and docs/PLAYBOOK.md)
- TOKEN-OPTIMIZATION.md
- docker-compose.yml
- requirements.txt, requirements-dev.txt, requirements-gpu.txt
- .env.example, .gitignore, .dockerignore, .python-version
- `git log --oneline -15` and `git status`

## Files To Create

- backend/app/api/v1/blacklist.py
- backend/app/schemas/blacklist.py
- backend/app/services/blacklist_service.py
- frontend/pages/ Blacklist page
- backend/tests/api/test_blacklist.py
- backend/tests/vision/test_blacklist_match.py

## Files To Modify

- backend/app/vision/recognizer.py
- backend/app/vision/overlay.py
- backend/app/api/v1/face.py (owner-generic session endpoints)
- backend/app/events/handlers/security.py

## Dependencies

No new dependencies.

## Environment Variables

No new variables.

## Database Changes

None.

## API Changes

Per Section 5.5. **ADMIN only**. No biometric data in responses. Every change audited.

## Frontend Changes

Search box, status filter, add/edit form (name, reason, category, severity, notes), enroll-face panel, deactivate with confirm. Notice: 'Use only with institutional authorization.'

## Implementation Sequence

1. Create branch
2. Service/API/schemas with audit
3. Generalise face registration to owner types
4. Extend recognizer for BLACKLISTED
5. Overlay + event handler
6. UI page
7. Tests
8. Commit and stop

## EXACT ANTIGRAVITY PROMPT

```text
YOU ARE IMPLEMENTING: PHASE 24 — BLACKLIST MANAGEMENT

Follow the GLOBAL RULES (docs/PLAYBOOK.md Section 2). Work ONLY on this phase.


STEP 0 — BRANCH
  git checkout main ; git pull origin main ; git checkout -b feature/phase-24-blacklist
  (If the branch exists, check it out instead. Never commit to main.)

STEP 1 — INSPECT FIRST (do not modify anything yet)
  - Repository tree (`Get-ChildItem -Recurse -Depth 3`)
  - README.md
  - docs/ (including the project PPT/PDF and docs/PLAYBOOK.md)
  - TOKEN-OPTIMIZATION.md
  - docker-compose.yml
  - requirements.txt, requirements-dev.txt, requirements-gpu.txt
  - .env.example, .gitignore, .dockerignore, .python-version
  - `git log --oneline -15` and `git status`
  Report briefly what already exists that is relevant to this phase. Never assume a file is missing.

OBJECTIVE
  Implement blacklist entries (add, edit, deactivate, view, search), reuse the registration flow to enroll blacklist faces, and extend recognition so a matching blacklist identity yields `kind=BLACKLISTED`.

STEP 2 — CREATE (only after inspection; skip anything that already exists and extend it instead)
  - backend/app/api/v1/blacklist.py
  - backend/app/schemas/blacklist.py
  - backend/app/services/blacklist_service.py
  - frontend/pages/ Blacklist page
  - backend/tests/api/test_blacklist.py
  - backend/tests/vision/test_blacklist_match.py

STEP 3 — MODIFY
  - backend/app/vision/recognizer.py
  - backend/app/vision/overlay.py
  - backend/app/api/v1/face.py (owner-generic session endpoints)
  - backend/app/events/handlers/security.py

DO NOT MODIFY / DO NOT DO
  - Expose face data
  - Let OPERATOR edit the blacklist
  - Treat blacklisted as attendance

DEPENDENCIES: none new  (resolve compatible versions, pin them, verify with `pip check`)
ENVIRONMENT VARIABLES: none new  (placeholders only in .env.example)

STEP 4 — IMPLEMENTATION ORDER
  1. Create branch
  2. Service/API/schemas with audit
  3. Generalise face registration to owner types
  4. Extend recognizer for BLACKLISTED
  5. Overlay + event handler
  6. UI page
  7. Tests
  8. Commit and stop

SPECIFIC REQUIREMENTS
  - For testing, blacklist a **consenting friend** as 'Test Identity' — never a real third party
  - Blacklisted persons never get attendance rows

STEP 5 — TESTS (write and RUN; paste real output)
  - Create/edit/search/deactivate entries
  - Active blacklist face → kind=BLACKLISTED
  - Deactivated → UNKNOWN or STUDENT (no longer BLACKLISTED)
  - Operator → 403
  - No attendance for BLACKLISTED
  - Audit rows present
  - Response has no embedding/biometric fields

STEP 6 — VERIFICATION (run these and report real results)
  pytest backend/tests/api/test_blacklist.py backend/tests/vision/test_blacklist_match.py -v

STEP 7 — ACCEPTANCE CRITERIA (mark each ✅ / ❌ / NOT VERIFIED — never guess)
  [ ] Blacklist CRUD verified
  [ ] Match and deactivation behaviour verified live
  [ ] Audit + RBAC verified
  [ ] No attendance for BLACKLISTED

STEP 8 — DOCUMENTATION: update README/docs for anything this phase changed; add a short entry to docs/CHANGELOG.md.

STEP 9 — GIT CHECKPOINT (only if tests pass)
  git status ; git diff   (confirm NO secrets, images, videos, .onnx, data/ content staged)
  git add . ; git commit -m "feat(security): add blacklist management and blacklisted identity recognition" ; git push -u origin feature/phase-24-blacklist

STEP 10 — STOP. Print the REPORT FORMAT from the global rules and write: STOPPED AT PHASE 24 GATE — awaiting human approval. Do NOT start Phase 25.
```

## Commands

Windows PowerShell (run from the repo root unless stated):

```powershell
pytest backend/tests/api/test_blacklist.py backend/tests/vision/test_blacklist_match.py -v
```

## Tests

- Create/edit/search/deactivate entries
- Active blacklist face → kind=BLACKLISTED
- Deactivated → UNKNOWN or STUDENT (no longer BLACKLISTED)
- Operator → 403
- No attendance for BLACKLISTED
- Audit rows present
- Response has no embedding/biometric fields

## Manual Verification

1. Enroll a friend as 'Test Identity'; live camera shows BLACKLISTED; deactivate and watch the label disappear

## Expected Result

Blacklisted identities are recognized and distinguished from normal students.

## Failure Conditions

- Operator can modify
- Deactivated entry still matches

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| Friend matches as student instead | Remove duplicate enrollment or follow precedence rule; check scores |

## Acceptance Criteria

- [ ] Blacklist CRUD verified
- [ ] Match and deactivation behaviour verified live
- [ ] Audit + RBAC verified
- [ ] No attendance for BLACKLISTED

## Git Checkpoint

```powershell
git checkout main
git pull origin main
git checkout -b feature/phase-24-blacklist   # at the START of the phase

# after tests pass:
git status
git diff
git add .
git commit -m "feat(security): add blacklist management and blacklisted identity recognition"
git push -u origin feature/phase-24-blacklist
```

Recommended commit message: `feat(security): add blacklist management and blacklisted identity recognition`

## HUMAN APPROVAL

Before approving, you should personally:

1. Enroll/deactivate your test identity live

## NEXT PHASE

Phase 25 turns events into alerts.

---

# Phase 25 — SECURITY ALERTS

> **Branch:** `feature/phase-25-security-alerts` · **Gate:** STOP — human approval required before the next phase

## Objective

Implement alert policy, creation with deduplication, severity, and the NEW → ACKNOWLEDGED → RESOLVED lifecycle.

## Why This Phase Exists

Converts security-relevant events into actionable, non-spammy alerts.

## Prerequisites

- Previous phase approved and merged (or branch checked out from it)

## Inputs

- Output of the previous phase
- This playbook

## Expected Outputs

- `AlertService`
- Policy via settings: UNKNOWN → OFF/LOW/MEDIUM/HIGH (default MEDIUM); BLACKLISTED → HIGH/CRITICAL (default CRITICAL)
- Alerts API with acknowledge/resolve
- Alert dedup via partial unique index + upsert

## Architecture

```text
SecurityHandler(event) → policy → dedup_key = type:camera:identity_or_track → 
  open alert with key within ALERT_DEDUP_WINDOW? → UPDATE last_seen_at, occurrence_count+1, max_similarity
  else INSERT (NEW)
```
Example: same unknown visible for 30 s ⇒ **one** alert with occurrence_count>1, not hundreds.

## Files To Inspect

- Repository tree (`Get-ChildItem -Recurse -Depth 3`)
- README.md
- docs/ (including the project PPT/PDF and docs/PLAYBOOK.md)
- TOKEN-OPTIMIZATION.md
- docker-compose.yml
- requirements.txt, requirements-dev.txt, requirements-gpu.txt
- .env.example, .gitignore, .dockerignore, .python-version
- `git log --oneline -15` and `git status`

## Files To Create

- backend/app/services/alert_service.py
- backend/app/db/repositories/alert_repo.py
- backend/app/api/v1/alerts.py
- backend/app/schemas/alert.py
- backend/tests/unit/test_alert_policy.py
- backend/tests/db/test_alert_dedup.py
- backend/tests/api/test_alerts.py

## Files To Modify

- backend/app/events/handlers/security.py
- backend/app/api/v1/settings.py (policy endpoints; ADMIN)
- .env.example

## Dependencies

No new dependencies.

## Environment Variables

- ALERT_POLICY_UNKNOWN=MEDIUM
- ALERT_POLICY_BLACKLIST=CRITICAL
- ALERT_DEDUP_WINDOW_SECONDS=300

## Database Changes

None.

## API Changes

`GET /alerts`, `POST /alerts/{id}/acknowledge`, `POST /alerts/{id}/resolve` (note required), settings GET/PUT.

## Frontend Changes

None.

## Implementation Sequence

1. Create branch
2. Policy pure functions + tests
3. Repo with atomic dedup
4. Handler integration
5. Endpoints with lifecycle rules
6. Tests incl. concurrency
7. Commit and stop

## EXACT ANTIGRAVITY PROMPT

```text
YOU ARE IMPLEMENTING: PHASE 25 — SECURITY ALERTS

Follow the GLOBAL RULES (docs/PLAYBOOK.md Section 2). Work ONLY on this phase.


STEP 0 — BRANCH
  git checkout main ; git pull origin main ; git checkout -b feature/phase-25-security-alerts
  (If the branch exists, check it out instead. Never commit to main.)

STEP 1 — INSPECT FIRST (do not modify anything yet)
  - Repository tree (`Get-ChildItem -Recurse -Depth 3`)
  - README.md
  - docs/ (including the project PPT/PDF and docs/PLAYBOOK.md)
  - TOKEN-OPTIMIZATION.md
  - docker-compose.yml
  - requirements.txt, requirements-dev.txt, requirements-gpu.txt
  - .env.example, .gitignore, .dockerignore, .python-version
  - `git log --oneline -15` and `git status`
  Report briefly what already exists that is relevant to this phase. Never assume a file is missing.

OBJECTIVE
  Implement alert policy, creation with deduplication, severity, and the NEW → ACKNOWLEDGED → RESOLVED lifecycle.

STEP 2 — CREATE (only after inspection; skip anything that already exists and extend it instead)
  - backend/app/services/alert_service.py
  - backend/app/db/repositories/alert_repo.py
  - backend/app/api/v1/alerts.py
  - backend/app/schemas/alert.py
  - backend/tests/unit/test_alert_policy.py
  - backend/tests/db/test_alert_dedup.py
  - backend/tests/api/test_alerts.py

STEP 3 — MODIFY
  - backend/app/events/handlers/security.py
  - backend/app/api/v1/settings.py (policy endpoints; ADMIN)
  - .env.example

DO NOT MODIFY / DO NOT DO
  - Describe unknown as 'intruder'/'malicious' in alert text — use 'Unknown person detected'
  - Create alerts per frame

DEPENDENCIES: none new  (resolve compatible versions, pin them, verify with `pip check`)
ENVIRONMENT VARIABLES: ALERT_POLICY_UNKNOWN=MEDIUM; ALERT_POLICY_BLACKLIST=CRITICAL; ALERT_DEDUP_WINDOW_SECONDS=300  (placeholders only in .env.example)

STEP 4 — IMPLEMENTATION ORDER
  1. Create branch
  2. Policy pure functions + tests
  3. Repo with atomic dedup
  4. Handler integration
  5. Endpoints with lifecycle rules
  6. Tests incl. concurrency
  7. Commit and stop

SPECIFIC REQUIREMENTS
  - Use `INSERT ... ON CONFLICT` on the partial unique index or a locked select for atomic dedup
  - Acknowledge/resolve write who/when and audit entries; invalid transitions → 409

STEP 5 — TESTS (write and RUN; paste real output)
  - Unknown 30 s continuous → exactly 1 open alert
  - Reappears after window or after RESOLVED → new alert
  - Policy OFF → no alert
  - Blacklisted → CRITICAL
  - NEW→ACK→RESOLVED allowed; RESOLVED→ACK → 409
  - Resolve without note → 422
  - Concurrent 20 handler calls → 1 alert
  - Operator can ack/resolve; cannot change policy

STEP 6 — VERIFICATION (run these and report real results)
  pytest backend/tests/unit/test_alert_policy.py backend/tests/db/test_alert_dedup.py backend/tests/api/test_alerts.py -v

STEP 7 — ACCEPTANCE CRITERIA (mark each ✅ / ❌ / NOT VERIFIED — never guess)
  [ ] Dedup verified (incl. concurrency)
  [ ] Lifecycle verified
  [ ] Policy configurable
  [ ] Alert wording neutral

STEP 8 — DOCUMENTATION: update README/docs for anything this phase changed; add a short entry to docs/CHANGELOG.md.

STEP 9 — GIT CHECKPOINT (only if tests pass)
  git status ; git diff   (confirm NO secrets, images, videos, .onnx, data/ content staged)
  git add . ; git commit -m "feat(alerts): add alert policy, deduplication and acknowledge/resolve lifecycle" ; git push -u origin feature/phase-25-security-alerts

STEP 10 — STOP. Print the REPORT FORMAT from the global rules and write: STOPPED AT PHASE 25 GATE — awaiting human approval. Do NOT start Phase 26.
```

## Commands

Windows PowerShell (run from the repo root unless stated):

```powershell
pytest backend/tests/unit/test_alert_policy.py backend/tests/db/test_alert_dedup.py backend/tests/api/test_alerts.py -v
```

## Tests

- Unknown 30 s continuous → exactly 1 open alert
- Reappears after window or after RESOLVED → new alert
- Policy OFF → no alert
- Blacklisted → CRITICAL
- NEW→ACK→RESOLVED allowed; RESOLVED→ACK → 409
- Resolve without note → 422
- Concurrent 20 handler calls → 1 alert
- Operator can ack/resolve; cannot change policy

## Manual Verification

1. Stand as unknown for 1 minute: one alert with count; acknowledge then resolve it; trigger blacklist: CRITICAL alert

## Expected Result

Few, meaningful alerts with auditable lifecycle.

## Failure Conditions

- Alert spam
- Invalid transitions accepted

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| Duplicate alerts | Check dedup_key construction and unique index |
| No alert for unknown | Verify policy not OFF and CONFIRM_FRAMES met |

## Acceptance Criteria

- [ ] Dedup verified (incl. concurrency)
- [ ] Lifecycle verified
- [ ] Policy configurable
- [ ] Alert wording neutral

## Git Checkpoint

```powershell
git checkout main
git pull origin main
git checkout -b feature/phase-25-security-alerts   # at the START of the phase

# after tests pass:
git status
git diff
git add .
git commit -m "feat(alerts): add alert policy, deduplication and acknowledge/resolve lifecycle"
git push -u origin feature/phase-25-security-alerts
```

Recommended commit message: `feat(alerts): add alert policy, deduplication and acknowledge/resolve lifecycle`

## HUMAN APPROVAL

Before approving, you should personally:

1. Trigger unknown + blacklist live and manage the alerts

## NEXT PHASE

Phase 26 builds the security dashboard.

---

# Phase 26 — SECURITY DASHBOARD

> **Branch:** `feature/phase-26-security-dashboard` · **Gate:** STOP — human approval required before the next phase

## Objective

Build Live Monitoring, Security Alerts and extended Dashboard KPIs (unknown detections, active alerts, blacklisted detections, active cameras, recent events).

## Why This Phase Exists

Operators need one place to watch cameras and manage alerts.

## Prerequisites

- Previous phase approved and merged (or branch checked out from it)

## Inputs

- Output of the previous phase
- This playbook

## Expected Outputs

- Live Monitoring page: camera tiles with status + stream
- Alerts page: filters (status, severity, type, camera, date), actions
- Dashboard: recent attendance + recent alerts + live tile

## Architecture

Uses existing APIs; auto-refresh via `st.fragment(run_every=3)`. Colour: CRITICAL red, HIGH orange, MEDIUM yellow, LOW blue. Colour is never the only indicator (text label too).

## Files To Inspect

- Repository tree (`Get-ChildItem -Recurse -Depth 3`)
- README.md
- docs/ (including the project PPT/PDF and docs/PLAYBOOK.md)
- TOKEN-OPTIMIZATION.md
- docker-compose.yml
- requirements.txt, requirements-dev.txt, requirements-gpu.txt
- .env.example, .gitignore, .dockerignore, .python-version
- `git log --oneline -15` and `git status`

## Files To Create

- frontend/pages/ Live Monitoring, Security Alerts
- backend/tests/api/test_dashboard_security.py
- frontend/tests/test_security_pages.py

## Files To Modify

- backend/app/services/dashboard_service.py
- frontend/pages/ Dashboard

## Dependencies

No new dependencies.

## Environment Variables

No new variables.

## Database Changes

None.

## API Changes

None.

## Frontend Changes

Tiles show camera name, location, status badge, worker FPS; at most `MAX_ACTIVE_CAMERAS` streams rendered; alert table with Acknowledge/Resolve buttons and note dialog; filters persist in session.

## Implementation Sequence

1. Create branch
2. Extend summary endpoint (real queries)
3. Live Monitoring page
4. Alerts page
5. Dashboard integration
6. AppTest tests
7. Commit and stop

## EXACT ANTIGRAVITY PROMPT

```text
YOU ARE IMPLEMENTING: PHASE 26 — SECURITY DASHBOARD

Follow the GLOBAL RULES (docs/PLAYBOOK.md Section 2). Work ONLY on this phase.


STEP 0 — BRANCH
  git checkout main ; git pull origin main ; git checkout -b feature/phase-26-security-dashboard
  (If the branch exists, check it out instead. Never commit to main.)

STEP 1 — INSPECT FIRST (do not modify anything yet)
  - Repository tree (`Get-ChildItem -Recurse -Depth 3`)
  - README.md
  - docs/ (including the project PPT/PDF and docs/PLAYBOOK.md)
  - TOKEN-OPTIMIZATION.md
  - docker-compose.yml
  - requirements.txt, requirements-dev.txt, requirements-gpu.txt
  - .env.example, .gitignore, .dockerignore, .python-version
  - `git log --oneline -15` and `git status`
  Report briefly what already exists that is relevant to this phase. Never assume a file is missing.

OBJECTIVE
  Build Live Monitoring, Security Alerts and extended Dashboard KPIs (unknown detections, active alerts, blacklisted detections, active cameras, recent events).

STEP 2 — CREATE (only after inspection; skip anything that already exists and extend it instead)
  - frontend/pages/ Live Monitoring, Security Alerts
  - backend/tests/api/test_dashboard_security.py
  - frontend/tests/test_security_pages.py

STEP 3 — MODIFY
  - backend/app/services/dashboard_service.py
  - frontend/pages/ Dashboard

DO NOT MODIFY / DO NOT DO
  - Fake charts/stats
  - Render more than the configured live streams at once

DEPENDENCIES: none new  (resolve compatible versions, pin them, verify with `pip check`)
ENVIRONMENT VARIABLES: none new  (placeholders only in .env.example)

STEP 4 — IMPLEMENTATION ORDER
  1. Create branch
  2. Extend summary endpoint (real queries)
  3. Live Monitoring page
  4. Alerts page
  5. Dashboard integration
  6. AppTest tests
  7. Commit and stop

STEP 5 — TESTS (write and RUN; paste real output)
  - KPIs equal DB counts (seeded)
  - Filters combine correctly
  - Actions update state and refresh
  - Empty states render
  - Operator sees alerts but not admin-only controls

STEP 6 — VERIFICATION (run these and report real results)
  pytest backend/tests/api/test_dashboard_security.py frontend/tests -v
  streamlit run frontend\app.py

STEP 7 — ACCEPTANCE CRITERIA (mark each ✅ / ❌ / NOT VERIFIED — never guess)
  [ ] KPIs real
  [ ] Alerts workflow works in UI
  [ ] Filters verified
  [ ] Stream limits respected

STEP 8 — DOCUMENTATION: update README/docs for anything this phase changed; add a short entry to docs/CHANGELOG.md.

STEP 9 — GIT CHECKPOINT (only if tests pass)
  git status ; git diff   (confirm NO secrets, images, videos, .onnx, data/ content staged)
  git add . ; git commit -m "feat(ui): add security live monitoring, alerts page and dashboard KPIs" ; git push -u origin feature/phase-26-security-dashboard

STEP 10 — STOP. Print the REPORT FORMAT from the global rules and write: STOPPED AT PHASE 26 GATE — awaiting human approval. Do NOT start Phase 27.
```

## Commands

Windows PowerShell (run from the repo root unless stated):

```powershell
pytest backend/tests/api/test_dashboard_security.py frontend/tests -v
streamlit run frontend\app.py
```

## Tests

- KPIs equal DB counts (seeded)
- Filters combine correctly
- Actions update state and refresh
- Empty states render
- Operator sees alerts but not admin-only controls

## Manual Verification

1. Trigger unknown + blacklist and watch KPIs/alerts update within a few seconds

## Expected Result

A usable security console backed by real data.

## Failure Conditions

- Static/fake numbers
- UI freezes with video

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| Page reruns too often | Use fragments, limit refresh intervals |
| Multiple streams lag | Show one live stream + thumbnails/status for others |

## Acceptance Criteria

- [ ] KPIs real
- [ ] Alerts workflow works in UI
- [ ] Filters verified
- [ ] Stream limits respected

## Git Checkpoint

```powershell
git checkout main
git pull origin main
git checkout -b feature/phase-26-security-dashboard   # at the START of the phase

# after tests pass:
git status
git diff
git add .
git commit -m "feat(ui): add security live monitoring, alerts page and dashboard KPIs"
git push -u origin feature/phase-26-security-dashboard
```

Recommended commit message: `feat(ui): add security live monitoring, alerts page and dashboard KPIs`

## HUMAN APPROVAL

Before approving, you should personally:

1. Run the unknown/blacklist scenario and watch the UI

## NEXT PHASE

Phase 27 adds detection-based person tracking.

---

# Phase 27 — PERSON TRACKING (DETECTION-BASED)

> **Branch:** `feature/phase-27-person-tracking` · **Gate:** STOP — human approval required before the next phase

## Objective

Implement person search, movement history, filters and last-known-location from `detection_events` (ADR-09). Group events into 'sightings'. Be explicit that this is **recorded sightings**, not continuous tracking.

## Why This Phase Exists

Delivers the PPT's person-tracking objective honestly and without data duplication.

## Prerequisites

- Previous phase approved and merged (or branch checked out from it)

## Inputs

- Output of the previous phase
- This playbook

## Expected Outputs

- `TrackingService`
- Tracking endpoints
- Movement Tracking page with timeline

## Architecture

```text
SELECT ... FROM detection_events WHERE student_id=:id AND occurred_at BETWEEN ... ORDER BY occurred_at
Group: consecutive events on same camera with gap <= SIGHTING_GAP_SECONDS → one sighting {camera, location, first_seen, last_seen, max_similarity, n_events}
Last known = most recent RECOGNIZED event
```
Example timeline: `10:10 Camera 01 — Main Gate`, `10:25 Camera 02 — Block A`, `10:47 Camera 04 — Lab`.

## Files To Inspect

- Repository tree (`Get-ChildItem -Recurse -Depth 3`)
- README.md
- docs/ (including the project PPT/PDF and docs/PLAYBOOK.md)
- TOKEN-OPTIMIZATION.md
- docker-compose.yml
- requirements.txt, requirements-dev.txt, requirements-gpu.txt
- .env.example, .gitignore, .dockerignore, .python-version
- `git log --oneline -15` and `git status`

## Files To Create

- backend/app/services/tracking_service.py
- backend/app/api/v1/tracking.py
- backend/app/schemas/tracking.py
- frontend/pages/ Movement Tracking
- backend/tests/unit/test_sighting_grouping.py
- backend/tests/api/test_tracking.py

## Files To Modify

- backend/app/api/v1/router.py

## Dependencies

No new dependencies.

## Environment Variables

No new variables.

## Database Changes

None.

## API Changes

`GET /tracking/persons?q=`, `GET /tracking/persons/{id}/history`, `GET /tracking/persons/{id}/last-seen`.

## Frontend Changes

Search by name/ID → select person → date range + camera filter → timeline table + last-known card with timestamp and 'seen N minutes ago'. Banner: 'Based on recorded recognition events; gaps mean the person was not recognised, not that they disappeared.'

## Implementation Sequence

1. Create branch
2. Pure grouping function + tests
3. Service/queries (indexed)
4. Endpoints
5. UI page
6. Seed multi-camera events in tests
7. Commit and stop

## EXACT ANTIGRAVITY PROMPT

```text
YOU ARE IMPLEMENTING: PHASE 27 — PERSON TRACKING (DETECTION-BASED)

Follow the GLOBAL RULES (docs/PLAYBOOK.md Section 2). Work ONLY on this phase.


STEP 0 — BRANCH
  git checkout main ; git pull origin main ; git checkout -b feature/phase-27-person-tracking
  (If the branch exists, check it out instead. Never commit to main.)

STEP 1 — INSPECT FIRST (do not modify anything yet)
  - Repository tree (`Get-ChildItem -Recurse -Depth 3`)
  - README.md
  - docs/ (including the project PPT/PDF and docs/PLAYBOOK.md)
  - TOKEN-OPTIMIZATION.md
  - docker-compose.yml
  - requirements.txt, requirements-dev.txt, requirements-gpu.txt
  - .env.example, .gitignore, .dockerignore, .python-version
  - `git log --oneline -15` and `git status`
  Report briefly what already exists that is relevant to this phase. Never assume a file is missing.

OBJECTIVE
  Implement person search, movement history, filters and last-known-location from `detection_events` (ADR-09). Group events into 'sightings'. Be explicit that this is **recorded sightings**, not continuous tracking.

STEP 2 — CREATE (only after inspection; skip anything that already exists and extend it instead)
  - backend/app/services/tracking_service.py
  - backend/app/api/v1/tracking.py
  - backend/app/schemas/tracking.py
  - frontend/pages/ Movement Tracking
  - backend/tests/unit/test_sighting_grouping.py
  - backend/tests/api/test_tracking.py

STEP 3 — MODIFY
  - backend/app/api/v1/router.py

DO NOT MODIFY / DO NOT DO
  - Create a movement_history table
  - Claim continuous tracking or real-time position
  - Track unknown persons by identity

DEPENDENCIES: none new  (resolve compatible versions, pin them, verify with `pip check`)
ENVIRONMENT VARIABLES: none new  (placeholders only in .env.example)

STEP 4 — IMPLEMENTATION ORDER
  1. Create branch
  2. Pure grouping function + tests
  3. Service/queries (indexed)
  4. Endpoints
  5. UI page
  6. Seed multi-camera events in tests
  7. Commit and stop

STEP 5 — TESTS (write and RUN; paste real output)
  - Events at 10:10(c1),10:10:20(c1),10:25(c2),10:47(c4) → 3 sightings
  - Gap > threshold splits sightings
  - Date and camera filters
  - Last seen returns most recent; none → 404
  - Search needs ≥2 chars; case-insensitive
  - Inactive student history still visible to ADMIN
  - Audit entry for history access (privacy-sensitive)

STEP 6 — VERIFICATION (run these and report real results)
  pytest backend/tests/unit/test_sighting_grouping.py backend/tests/api/test_tracking.py -v

STEP 7 — ACCEPTANCE CRITERIA (mark each ✅ / ❌ / NOT VERIFIED — never guess)
  [ ] Grouping logic tested
  [ ] Endpoints + page verified
  [ ] UI wording honest
  [ ] No movement table

STEP 8 — DOCUMENTATION: update README/docs for anything this phase changed; add a short entry to docs/CHANGELOG.md.

STEP 9 — GIT CHECKPOINT (only if tests pass)
  git status ; git diff   (confirm NO secrets, images, videos, .onnx, data/ content staged)
  git add . ; git commit -m "feat(tracking): add detection-based person search, movement history and last known location" ; git push -u origin feature/phase-27-person-tracking

STEP 10 — STOP. Print the REPORT FORMAT from the global rules and write: STOPPED AT PHASE 27 GATE — awaiting human approval. Do NOT start Phase 28.
```

## Commands

Windows PowerShell (run from the repo root unless stated):

```powershell
pytest backend/tests/unit/test_sighting_grouping.py backend/tests/api/test_tracking.py -v
```

## Tests

- Events at 10:10(c1),10:10:20(c1),10:25(c2),10:47(c4) → 3 sightings
- Gap > threshold splits sightings
- Date and camera filters
- Last seen returns most recent; none → 404
- Search needs ≥2 chars; case-insensitive
- Inactive student history still visible to ADMIN
- Audit entry for history access (privacy-sensitive)

## Manual Verification

1. Use video-file cameras 'Main Gate' and 'Lab' (two videos) to create two locations; view your movement history

## Expected Result

Searchable, honest movement history and last known location.

## Failure Conditions

- Phrases like 'live tracking' in UI
- Duplicate data table

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| Only one sighting | Increase gap or check events throttle |
| Slow query | Check indexes; EXPLAIN ANALYZE |

## Acceptance Criteria

- [ ] Grouping logic tested
- [ ] Endpoints + page verified
- [ ] UI wording honest
- [ ] No movement table

## Git Checkpoint

```powershell
git checkout main
git pull origin main
git checkout -b feature/phase-27-person-tracking   # at the START of the phase

# after tests pass:
git status
git diff
git add .
git commit -m "feat(tracking): add detection-based person search, movement history and last known location"
git push -u origin feature/phase-27-person-tracking
```

Recommended commit message: `feat(tracking): add detection-based person search, movement history and last known location`

## HUMAN APPROVAL

Before approving, you should personally:

1. Read the UI wording; check timeline vs actual events

## NEXT PHASE

Phase 28 supports multiple simultaneous cameras.

---

# Phase 28 — MULTI-CAMERA SUPPORT

> **Branch:** `feature/phase-28-multi-camera` · **Gate:** STOP — human approval required before the next phase

## Objective

Run multiple camera workers concurrently with one shared model, bounded resources, supervision and per-camera isolation.

## Why This Phase Exists

PPT scalability objective, within CPU limits.

## Prerequisites

- Previous phase approved and merged (or branch checked out from it)

## Inputs

- Output of the previous phase
- This playbook

## Expected Outputs

- `CameraManager` supervising workers (start/stop/restart on failure)
- Shared `InferenceQueue` with a single inference thread (model is not thread-safe by assumption; verify)
- `MAX_ACTIVE_CAMERAS` enforced
- Per-camera FPS/queue metrics

## Architecture

```text
N readers (one per camera) → bounded frame slots → InferenceQueue (round-robin, drop-oldest) → single VisionPipeline → results routed by camera_id → tracker per camera → EventBus
Supervisor restarts crashed workers with backoff
```
Python threads are fine because OpenCV/ONNX release the GIL. Process-per-camera is **not** introduced unless measurements demand it (document).

## Files To Inspect

- Repository tree (`Get-ChildItem -Recurse -Depth 3`)
- README.md
- docs/ (including the project PPT/PDF and docs/PLAYBOOK.md)
- TOKEN-OPTIMIZATION.md
- docker-compose.yml
- requirements.txt, requirements-dev.txt, requirements-gpu.txt
- .env.example, .gitignore, .dockerignore, .python-version
- `git log --oneline -15` and `git status`

## Files To Create

- backend/app/cameras/inference_queue.py
- backend/app/cameras/supervisor.py
- backend/tests/cameras/test_multi_camera.py

## Files To Modify

- backend/app/cameras/manager.py
- backend/app/cameras/worker.py
- .env.example

## Dependencies

No new dependencies.

## Environment Variables

- MAX_ACTIVE_CAMERAS=4
- INFERENCE_QUEUE_SIZE=8

## Database Changes

None.

## API Changes

None.

## Frontend Changes

None.

## Implementation Sequence

1. Create branch
2. Inference queue with fairness + tests
3. Refactor workers to submit frames
4. Supervisor + restart policy
5. Enforce limit
6. Load test with 3 video cameras; record FPS per camera and CPU
7. Commit and stop

## EXACT ANTIGRAVITY PROMPT

```text
YOU ARE IMPLEMENTING: PHASE 28 — MULTI-CAMERA SUPPORT

Follow the GLOBAL RULES (docs/PLAYBOOK.md Section 2). Work ONLY on this phase.


STEP 0 — BRANCH
  git checkout main ; git pull origin main ; git checkout -b feature/phase-28-multi-camera
  (If the branch exists, check it out instead. Never commit to main.)

STEP 1 — INSPECT FIRST (do not modify anything yet)
  - Repository tree (`Get-ChildItem -Recurse -Depth 3`)
  - README.md
  - docs/ (including the project PPT/PDF and docs/PLAYBOOK.md)
  - TOKEN-OPTIMIZATION.md
  - docker-compose.yml
  - requirements.txt, requirements-dev.txt, requirements-gpu.txt
  - .env.example, .gitignore, .dockerignore, .python-version
  - `git log --oneline -15` and `git status`
  Report briefly what already exists that is relevant to this phase. Never assume a file is missing.

OBJECTIVE
  Run multiple camera workers concurrently with one shared model, bounded resources, supervision and per-camera isolation.

STEP 2 — CREATE (only after inspection; skip anything that already exists and extend it instead)
  - backend/app/cameras/inference_queue.py
  - backend/app/cameras/supervisor.py
  - backend/tests/cameras/test_multi_camera.py

STEP 3 — MODIFY
  - backend/app/cameras/manager.py
  - backend/app/cameras/worker.py
  - .env.example

DO NOT MODIFY / DO NOT DO
  - Microservices/processes unless measured necessary
  - Unbounded queues

DEPENDENCIES: none new  (resolve compatible versions, pin them, verify with `pip check`)
ENVIRONMENT VARIABLES: MAX_ACTIVE_CAMERAS=4; INFERENCE_QUEUE_SIZE=8  (placeholders only in .env.example)

STEP 4 — IMPLEMENTATION ORDER
  1. Create branch
  2. Inference queue with fairness + tests
  3. Refactor workers to submit frames
  4. Supervisor + restart policy
  5. Enforce limit
  6. Load test with 3 video cameras; record FPS per camera and CPU
  7. Commit and stop

SPECIFIC REQUIREMENTS
  - Use two or three video-file cameras for tests (plus webcam if free)
  - Fairness: a busy camera must not starve others

STEP 5 — TESTS (write and RUN; paste real output)
  - Camera A crash does not affect B
  - Queue never exceeds bound; stale frames dropped
  - Start >MAX cameras → 409
  - Results routed to the correct camera (events carry right camera_id)
  - Restart after failure with backoff
  - Clean shutdown joins all threads

STEP 6 — VERIFICATION (run these and report real results)
  pytest backend/tests/cameras/test_multi_camera.py -v
  python scripts\bench_multicam.py --cameras 3   # report measured FPS only

STEP 7 — ACCEPTANCE CRITERIA (mark each ✅ / ❌ / NOT VERIFIED — never guess)
  [ ] 3-camera run verified
  [ ] Isolation tested
  [ ] Bounded queues tested
  [ ] Measured FPS recorded (no claims)

STEP 8 — DOCUMENTATION: update README/docs for anything this phase changed; add a short entry to docs/CHANGELOG.md.

STEP 9 — GIT CHECKPOINT (only if tests pass)
  git status ; git diff   (confirm NO secrets, images, videos, .onnx, data/ content staged)
  git add . ; git commit -m "feat(cameras): add multi-camera supervision with shared inference queue" ; git push -u origin feature/phase-28-multi-camera

STEP 10 — STOP. Print the REPORT FORMAT from the global rules and write: STOPPED AT PHASE 28 GATE — awaiting human approval. Do NOT start Phase 29.
```

## Commands

Windows PowerShell (run from the repo root unless stated):

```powershell
pytest backend/tests/cameras/test_multi_camera.py -v
python scripts\bench_multicam.py --cameras 3   # report measured FPS only
```

## Tests

- Camera A crash does not affect B
- Queue never exceeds bound; stale frames dropped
- Start >MAX cameras → 409
- Results routed to the correct camera (events carry right camera_id)
- Restart after failure with backoff
- Clean shutdown joins all threads

## Manual Verification

1. Run 3 video cameras concurrently; view statuses and per-camera FPS

## Expected Result

Several cameras run concurrently with graceful degradation (lower FPS), not crashes.

## Failure Conditions

- Cross-camera mislabeling
- Memory growth over 10 minutes (measure)

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| FPS collapses | Raise frame skip, lower resolution, reduce camera count — measure first |
| Deadlock on stop | Use timeouts on joins and sentinel values |

## Acceptance Criteria

- [ ] 3-camera run verified
- [ ] Isolation tested
- [ ] Bounded queues tested
- [ ] Measured FPS recorded (no claims)

## Git Checkpoint

```powershell
git checkout main
git pull origin main
git checkout -b feature/phase-28-multi-camera   # at the START of the phase

# after tests pass:
git status
git diff
git add .
git commit -m "feat(cameras): add multi-camera supervision with shared inference queue"
git push -u origin feature/phase-28-multi-camera
```

Recommended commit message: `feat(cameras): add multi-camera supervision with shared inference queue`

## HUMAN APPROVAL

Before approving, you should personally:

1. Watch 3 streams; kill one source and verify others continue

## NEXT PHASE

Phase 29 introduces Redis where justified.

---

# Phase 29 — REDIS (WHERE JUSTIFIED)

> **Branch:** `feature/phase-29-redis` · **Gate:** STOP — human approval required before the next phase

## Objective

Introduce Redis behind interfaces, only for: (1) `RedisEventBus` (pub/sub bridge enabling API and workers in separate processes), (2) alert-dedup TTL keys, (3) camera heartbeat/status cache, (4) stream tickets. Everything must still work with `REDIS_ENABLED=false`.

## Why This Phase Exists

Redis earns its place now: multi-process workers, TTL-based dedup and shared ephemeral state. Explain this justification in `docs/architecture/REDIS.md`; if measurements show no benefit for an item, do not implement that item.

## Prerequisites

- Previous phase approved and merged (or branch checked out from it)

## Inputs

- Output of the previous phase
- This playbook

## Expected Outputs

- `events/redis_bus.py` behind the existing bus interface
- TTL dedup helper (`SET key NX EX`)
- Heartbeat cache
- Redis-backed ticket store
- Fallback to in-memory when disabled/unavailable

## Architecture

```text
REDIS_ENABLED=false → in-memory implementations (default)
REDIS_ENABLED=true  → redis://... implementations; if Redis drops → log + fall back (never crash recognition)
```
DB remains the source of truth for attendance and alerts; Redis holds only ephemeral state.

## Files To Inspect

- Repository tree (`Get-ChildItem -Recurse -Depth 3`)
- README.md
- docs/ (including the project PPT/PDF and docs/PLAYBOOK.md)
- TOKEN-OPTIMIZATION.md
- docker-compose.yml
- requirements.txt, requirements-dev.txt, requirements-gpu.txt
- .env.example, .gitignore, .dockerignore, .python-version
- `git log --oneline -15` and `git status`

## Files To Create

- backend/app/events/redis_bus.py
- backend/app/core/cache.py
- docs/architecture/REDIS.md
- backend/tests/unit/test_redis_fallback.py
- backend/tests/integration/test_redis_bus.py

## Files To Modify

- backend/app/events/bus.py (factory)
- backend/app/services/alert_service.py
- backend/app/api/v1/stream.py
- .env.example
- docker-compose.yml (profile redis already present)

## Dependencies

- redis (python client)

## Environment Variables

- REDIS_ENABLED=false
- REDIS_URL=redis://localhost:6379/0

## Database Changes

None.

## API Changes

None.

## Frontend Changes

None.

## Implementation Sequence

1. Create branch
2. Write REDIS.md justification
3. Implement factory + Redis implementations
4. Fallback behaviour
5. Tests with Redis up and down
6. Run full regression twice (REDIS_ENABLED false and true)
7. Commit and stop

## EXACT ANTIGRAVITY PROMPT

```text
YOU ARE IMPLEMENTING: PHASE 29 — REDIS (WHERE JUSTIFIED)

Follow the GLOBAL RULES (docs/PLAYBOOK.md Section 2). Work ONLY on this phase.


STEP 0 — BRANCH
  git checkout main ; git pull origin main ; git checkout -b feature/phase-29-redis
  (If the branch exists, check it out instead. Never commit to main.)

STEP 1 — INSPECT FIRST (do not modify anything yet)
  - Repository tree (`Get-ChildItem -Recurse -Depth 3`)
  - README.md
  - docs/ (including the project PPT/PDF and docs/PLAYBOOK.md)
  - TOKEN-OPTIMIZATION.md
  - docker-compose.yml
  - requirements.txt, requirements-dev.txt, requirements-gpu.txt
  - .env.example, .gitignore, .dockerignore, .python-version
  - `git log --oneline -15` and `git status`
  Report briefly what already exists that is relevant to this phase. Never assume a file is missing.

OBJECTIVE
  Introduce Redis behind interfaces, only for: (1) `RedisEventBus` (pub/sub bridge enabling API and workers in separate processes), (2) alert-dedup TTL keys, (3) camera heartbeat/status cache, (4) stream tickets. Everything must still work with `REDIS_ENABLED=false`.

STEP 2 — CREATE (only after inspection; skip anything that already exists and extend it instead)
  - backend/app/events/redis_bus.py
  - backend/app/core/cache.py
  - docs/architecture/REDIS.md
  - backend/tests/unit/test_redis_fallback.py
  - backend/tests/integration/test_redis_bus.py

STEP 3 — MODIFY
  - backend/app/events/bus.py (factory)
  - backend/app/services/alert_service.py
  - backend/app/api/v1/stream.py
  - .env.example
  - docker-compose.yml (profile redis already present)

DO NOT MODIFY / DO NOT DO
  - Store attendance/alerts only in Redis
  - Require Redis for the app to start
  - Store embeddings in Redis

DEPENDENCIES: redis (python client)  (resolve compatible versions, pin them, verify with `pip check`)
ENVIRONMENT VARIABLES: REDIS_ENABLED=false; REDIS_URL=redis://localhost:6379/0  (placeholders only in .env.example)

STEP 4 — IMPLEMENTATION ORDER
  1. Create branch
  2. Write REDIS.md justification
  3. Implement factory + Redis implementations
  4. Fallback behaviour
  5. Tests with Redis up and down
  6. Run full regression twice (REDIS_ENABLED false and true)
  7. Commit and stop

STEP 5 — TESTS (write and RUN; paste real output)
  - Full suite passes with Redis disabled and enabled
  - Events published via Redis reach handlers in a separate process (integration)
  - Dedup key TTL expiry works
  - Redis stopped mid-run → fallback + warning, no crash
  - Ticket stored in Redis expires

STEP 6 — VERIFICATION (run these and report real results)
  docker compose --profile redis up -d redis
  pytest -q   # REDIS_ENABLED=false
  $env:REDIS_ENABLED='true'; pytest -q
  docker compose stop redis   # then verify app keeps running
  docker compose --profile redis down

STEP 7 — ACCEPTANCE CRITERIA (mark each ✅ / ❌ / NOT VERIFIED — never guess)
  [ ] Both modes pass regression
  [ ] Fallback verified
  [ ] Justification documented
  [ ] No hard dependency

STEP 8 — DOCUMENTATION: update README/docs for anything this phase changed; add a short entry to docs/CHANGELOG.md.

STEP 9 — GIT CHECKPOINT (only if tests pass)
  git status ; git diff   (confirm NO secrets, images, videos, .onnx, data/ content staged)
  git add . ; git commit -m "feat(redis): add optional Redis event bus, TTL dedup and heartbeat cache with in-memory fallback" ; git push -u origin feature/phase-29-redis

STEP 10 — STOP. Print the REPORT FORMAT from the global rules and write: STOPPED AT PHASE 29 GATE — awaiting human approval. Do NOT start Phase 30.
```

## Commands

Windows PowerShell (run from the repo root unless stated):

```powershell
docker compose --profile redis up -d redis
pytest -q   # REDIS_ENABLED=false
$env:REDIS_ENABLED='true'; pytest -q
docker compose stop redis   # then verify app keeps running
docker compose --profile redis down
```

## Tests

- Full suite passes with Redis disabled and enabled
- Events published via Redis reach handlers in a separate process (integration)
- Dedup key TTL expiry works
- Redis stopped mid-run → fallback + warning, no crash
- Ticket stored in Redis expires

## Manual Verification

1. Run recognition with Redis on; stop Redis; confirm the app continues

## Expected Result

Redis adds capability without becoming a hard dependency.

## Failure Conditions

- App cannot start without Redis
- Attendance depends on Redis

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| Connection refused | Start with `--profile redis`; check `REDIS_URL` |
| Duplicate delivery | Make handlers idempotent (DB constraints already protect attendance) |

## Acceptance Criteria

- [ ] Both modes pass regression
- [ ] Fallback verified
- [ ] Justification documented
- [ ] No hard dependency

## Git Checkpoint

```powershell
git checkout main
git pull origin main
git checkout -b feature/phase-29-redis   # at the START of the phase

# after tests pass:
git status
git diff
git add .
git commit -m "feat(redis): add optional Redis event bus, TTL dedup and heartbeat cache with in-memory fallback"
git push -u origin feature/phase-29-redis
```

Recommended commit message: `feat(redis): add optional Redis event bus, TTL dedup and heartbeat cache with in-memory fallback`

## HUMAN APPROVAL

Before approving, you should personally:

1. Run the stop-Redis experiment yourself

## NEXT PHASE

Phase 30 builds reports and CSV export.

---

# Phase 30 — REPORTING

> **Branch:** `feature/phase-30-reporting` · **Gate:** STOP — human approval required before the next phase

## Objective

Attendance and security reports with filters, summaries, and safe CSV export (ADMIN only, audited).

## Why This Phase Exists

PPT dashboard objective: attendance reports, search and export.

## Prerequisites

- Previous phase approved and merged (or branch checked out from it)

## Inputs

- Output of the previous phase
- This playbook

## Expected Outputs

- Report JSON + CSV endpoints
- Reports page (attendance and security tabs)
- Per-student attendance % summary

## Architecture

Attendance columns: date, student_id, name, department, year, status, timestamp, camera, location. Security columns: alert type, severity, person (student/blacklist name or 'UNKNOWN'), camera, location, first/last seen, count, status, acknowledged/resolved by/at.

Attendance % definition (document in UI): `days present ÷ days on which attendance was recorded for anyone in the range`, per student. Streamed CSV with UTF-8 BOM for Excel.

## Files To Inspect

- Repository tree (`Get-ChildItem -Recurse -Depth 3`)
- README.md
- docs/ (including the project PPT/PDF and docs/PLAYBOOK.md)
- TOKEN-OPTIMIZATION.md
- docker-compose.yml
- requirements.txt, requirements-dev.txt, requirements-gpu.txt
- .env.example, .gitignore, .dockerignore, .python-version
- `git log --oneline -15` and `git status`

## Files To Create

- backend/app/services/report_service.py
- backend/app/api/v1/reports.py
- backend/app/core/csv_safe.py
- frontend/pages/ Reports
- backend/tests/unit/test_csv_safe.py
- backend/tests/api/test_reports.py

## Files To Modify

- backend/app/api/v1/router.py

## Dependencies

No new dependencies.

## Environment Variables

- REPORT_MAX_ROWS=50000

## Database Changes

None.

## API Changes

`GET /reports/attendance`, `GET /reports/attendance.csv`, `GET /reports/security`, `GET /reports/security.csv`.

## Frontend Changes

None.

## Implementation Sequence

1. Create branch
2. CSV sanitiser + tests
3. Report queries
4. Endpoints (stream)
5. UI with filters and download button
6. Tests with seeded data
7. Commit and stop

## EXACT ANTIGRAVITY PROMPT

```text
YOU ARE IMPLEMENTING: PHASE 30 — REPORTING

Follow the GLOBAL RULES (docs/PLAYBOOK.md Section 2). Work ONLY on this phase.


STEP 0 — BRANCH
  git checkout main ; git pull origin main ; git checkout -b feature/phase-30-reporting
  (If the branch exists, check it out instead. Never commit to main.)

STEP 1 — INSPECT FIRST (do not modify anything yet)
  - Repository tree (`Get-ChildItem -Recurse -Depth 3`)
  - README.md
  - docs/ (including the project PPT/PDF and docs/PLAYBOOK.md)
  - TOKEN-OPTIMIZATION.md
  - docker-compose.yml
  - requirements.txt, requirements-dev.txt, requirements-gpu.txt
  - .env.example, .gitignore, .dockerignore, .python-version
  - `git log --oneline -15` and `git status`
  Report briefly what already exists that is relevant to this phase. Never assume a file is missing.

OBJECTIVE
  Attendance and security reports with filters, summaries, and safe CSV export (ADMIN only, audited).

STEP 2 — CREATE (only after inspection; skip anything that already exists and extend it instead)
  - backend/app/services/report_service.py
  - backend/app/api/v1/reports.py
  - backend/app/core/csv_safe.py
  - frontend/pages/ Reports
  - backend/tests/unit/test_csv_safe.py
  - backend/tests/api/test_reports.py

STEP 3 — MODIFY
  - backend/app/api/v1/router.py

DO NOT MODIFY / DO NOT DO
  - Allow OPERATOR export
  - Export embeddings or raw biometric data
  - Build the whole CSV in memory for large exports

DEPENDENCIES: none new  (resolve compatible versions, pin them, verify with `pip check`)
ENVIRONMENT VARIABLES: REPORT_MAX_ROWS=50000  (placeholders only in .env.example)

STEP 4 — IMPLEMENTATION ORDER
  1. Create branch
  2. CSV sanitiser + tests
  3. Report queries
  4. Endpoints (stream)
  5. UI with filters and download button
  6. Tests with seeded data
  7. Commit and stop

SPECIFIC REQUIREMENTS
  - CSV formula-injection protection: prefix cells beginning with `=`, `+`, `-`, `@`, tab or CR with `'`
  - Every export writes an audit log: who, filters, row count

STEP 5 — TESTS (write and RUN; paste real output)
  - Row counts equal DB for filters
  - Name `=cmd|' /C calc'!A0` exported safely
  - Row cap enforced with clear error
  - Operator → 403
  - Audit EXPORT_CSV recorded
  - CSV opens in Excel with correct columns
  - Percentages match hand calculation

STEP 6 — VERIFICATION (run these and report real results)
  pytest backend/tests/unit/test_csv_safe.py backend/tests/api/test_reports.py -v

STEP 7 — ACCEPTANCE CRITERIA (mark each ✅ / ❌ / NOT VERIFIED — never guess)
  [ ] Reports match DB
  [ ] CSV safety tested
  [ ] RBAC + audit verified

STEP 8 — DOCUMENTATION: update README/docs for anything this phase changed; add a short entry to docs/CHANGELOG.md.

STEP 9 — GIT CHECKPOINT (only if tests pass)
  git status ; git diff   (confirm NO secrets, images, videos, .onnx, data/ content staged)
  git add . ; git commit -m "feat(reports): add attendance and security reports with safe CSV export" ; git push -u origin feature/phase-30-reporting

STEP 10 — STOP. Print the REPORT FORMAT from the global rules and write: STOPPED AT PHASE 30 GATE — awaiting human approval. Do NOT start Phase 31.
```

## Commands

Windows PowerShell (run from the repo root unless stated):

```powershell
pytest backend/tests/unit/test_csv_safe.py backend/tests/api/test_reports.py -v
```

## Tests

- Row counts equal DB for filters
- Name `=cmd|' /C calc'!A0` exported safely
- Row cap enforced with clear error
- Operator → 403
- Audit EXPORT_CSV recorded
- CSV opens in Excel with correct columns
- Percentages match hand calculation

## Manual Verification

1. Download both CSVs and open in Excel; check columns and a malicious-name test

## Expected Result

Correct, safe, audited reports.

## Failure Conditions

- Formula injection possible
- Export without audit

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| Garbled characters in Excel | Ensure UTF-8 BOM |
| Huge export slow | Stream with server-side cursor |

## Acceptance Criteria

- [ ] Reports match DB
- [ ] CSV safety tested
- [ ] RBAC + audit verified

## Git Checkpoint

```powershell
git checkout main
git pull origin main
git checkout -b feature/phase-30-reporting   # at the START of the phase

# after tests pass:
git status
git diff
git add .
git commit -m "feat(reports): add attendance and security reports with safe CSV export"
git push -u origin feature/phase-30-reporting
```

Recommended commit message: `feat(reports): add attendance and security reports with safe CSV export`

## HUMAN APPROVAL

Before approving, you should personally:

1. Open the CSVs and compare with the UI

## NEXT PHASE

Phase 31 measures performance.

---

# Phase 31 — PERFORMANCE MEASUREMENT

> **Branch:** `perf/phase-31-measurement` · **Gate:** STOP — human approval required before the next phase

## Objective

Measure (not claim) detection, embedding, recognition and attendance latency, FPS, CPU/memory, DB query and API response times; write the performance report.

## Why This Phase Exists

Targets from the PPT (≥90 % accuracy, <5 s per student) must be validated by data.

## Prerequisites

- Previous phase approved and merged (or branch checked out from it)

## Inputs

- Output of the previous phase
- This playbook

## Expected Outputs

- `scripts/benchmark.py`, `scripts/bench_api.py`
- `docs/performance/PERFORMANCE_REPORT.md` with machine spec and raw numbers

## Architecture

Metrics (p50/p95/max, N≥200 where applicable): detection ms, embedding ms, pgvector search ms (`EXPLAIN ANALYZE`, at 1k and 10k synthetic embeddings), end-to-end frame→decision, attendance time (first appearance→row), FPS per camera (1,2,3 cameras), CPU %, RSS memory over 10 min (leak check), API latency for health, login, students list, attendance list, reports.

## Files To Inspect

- Repository tree (`Get-ChildItem -Recurse -Depth 3`)
- README.md
- docs/ (including the project PPT/PDF and docs/PLAYBOOK.md)
- TOKEN-OPTIMIZATION.md
- docker-compose.yml
- requirements.txt, requirements-dev.txt, requirements-gpu.txt
- .env.example, .gitignore, .dockerignore, .python-version
- `git log --oneline -15` and `git status`

## Files To Create

- scripts/benchmark.py
- scripts/bench_api.py
- docs/performance/PERFORMANCE_REPORT.md

## Files To Modify

No existing files (other than the Git-ignored and doc updates noted).

## Dependencies

- psutil

## Environment Variables

No new variables.

## Database Changes

None.

## API Changes

None.

## Frontend Changes

None.

## Implementation Sequence

1. Create branch
2. Write benchmark scripts
3. Run on idle machine (close heavy apps); record machine spec
4. Record results verbatim
5. Compare to targets honestly
6. Propose optimisations (do not apply)
7. Commit and stop

## EXACT ANTIGRAVITY PROMPT

```text
YOU ARE IMPLEMENTING: PHASE 31 — PERFORMANCE MEASUREMENT

Follow the GLOBAL RULES (docs/PLAYBOOK.md Section 2). Work ONLY on this phase.


STEP 0 — BRANCH
  git checkout main ; git pull origin main ; git checkout -b perf/phase-31-measurement
  (If the branch exists, check it out instead. Never commit to main.)

STEP 1 — INSPECT FIRST (do not modify anything yet)
  - Repository tree (`Get-ChildItem -Recurse -Depth 3`)
  - README.md
  - docs/ (including the project PPT/PDF and docs/PLAYBOOK.md)
  - TOKEN-OPTIMIZATION.md
  - docker-compose.yml
  - requirements.txt, requirements-dev.txt, requirements-gpu.txt
  - .env.example, .gitignore, .dockerignore, .python-version
  - `git log --oneline -15` and `git status`
  Report briefly what already exists that is relevant to this phase. Never assume a file is missing.

OBJECTIVE
  Measure (not claim) detection, embedding, recognition and attendance latency, FPS, CPU/memory, DB query and API response times; write the performance report.

STEP 2 — CREATE (only after inspection; skip anything that already exists and extend it instead)
  - scripts/benchmark.py
  - scripts/bench_api.py
  - docs/performance/PERFORMANCE_REPORT.md

STEP 3 — MODIFY
  - (nothing)

DO NOT MODIFY / DO NOT DO
  - Optimise before measuring
  - Report improvements without before/after numbers
  - State accuracy without the Phase 18 evaluation data

DEPENDENCIES: psutil  (resolve compatible versions, pin them, verify with `pip check`)
ENVIRONMENT VARIABLES: none new  (placeholders only in .env.example)

STEP 4 — IMPLEMENTATION ORDER
  1. Create branch
  2. Write benchmark scripts
  3. Run on idle machine (close heavy apps); record machine spec
  4. Record results verbatim
  5. Compare to targets honestly
  6. Propose optimisations (do not apply)
  7. Commit and stop

SPECIFIC REQUIREMENTS
  - If any target is missed, report it as missed and propose measured optimisations (frame skip, `DET_SIZE`, `buffalo_s`, caching embeddings in memory, ONNX threads) — implement only after the human approves

STEP 5 — TESTS (write and RUN; paste real output)
  - Benchmark script runs and writes JSON
  - Report contains machine spec, N, percentiles, date
  - Targets table shows 'MET / NOT MET / NOT MEASURED' with evidence

STEP 6 — VERIFICATION (run these and report real results)
  python scripts\benchmark.py --frames 200 --out docs\performance\raw.json
  python scripts\bench_api.py --requests 200
  docker compose exec db psql -U $env:POSTGRES_USER -d $env:POSTGRES_DB -c "EXPLAIN ANALYZE SELECT id FROM face_embeddings WHERE is_active ORDER BY embedding <=> (SELECT embedding FROM face_embeddings LIMIT 1) LIMIT 5;"

STEP 7 — ACCEPTANCE CRITERIA (mark each ✅ / ❌ / NOT VERIFIED — never guess)
  [ ] All listed metrics measured
  [ ] Raw data saved
  [ ] Targets evaluated honestly
  [ ] Optimisation proposals listed but not applied

STEP 8 — DOCUMENTATION: update README/docs for anything this phase changed; add a short entry to docs/CHANGELOG.md.

STEP 9 — GIT CHECKPOINT (only if tests pass)
  git status ; git diff   (confirm NO secrets, images, videos, .onnx, data/ content staged)
  git add . ; git commit -m "perf: add benchmarks and measured performance report" ; git push -u origin perf/phase-31-measurement

STEP 10 — STOP. Print the REPORT FORMAT from the global rules and write: STOPPED AT PHASE 31 GATE — awaiting human approval. Do NOT start Phase 32.
```

## Commands

Windows PowerShell (run from the repo root unless stated):

```powershell
python scripts\benchmark.py --frames 200 --out docs\performance\raw.json
python scripts\bench_api.py --requests 200
docker compose exec db psql -U $env:POSTGRES_USER -d $env:POSTGRES_DB -c "EXPLAIN ANALYZE SELECT id FROM face_embeddings WHERE is_active ORDER BY embedding <=> (SELECT embedding FROM face_embeddings LIMIT 1) LIMIT 5;"
```

## Tests

- Benchmark script runs and writes JSON
- Report contains machine spec, N, percentiles, date
- Targets table shows 'MET / NOT MET / NOT MEASURED' with evidence

## Manual Verification

1. Read the report: is every number traceable to raw output?

## Expected Result

An honest quantitative picture of system performance.

## Failure Conditions

- Any number without a source
- Targets declared met without data

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| Unstable numbers | Warm-up runs, fixed power plan, close background apps |

## Acceptance Criteria

- [ ] All listed metrics measured
- [ ] Raw data saved
- [ ] Targets evaluated honestly
- [ ] Optimisation proposals listed but not applied

## Git Checkpoint

```powershell
git checkout main
git pull origin main
git checkout -b perf/phase-31-measurement   # at the START of the phase

# after tests pass:
git status
git diff
git add .
git commit -m "perf: add benchmarks and measured performance report"
git push -u origin perf/phase-31-measurement
```

Recommended commit message: `perf: add benchmarks and measured performance report`

## HUMAN APPROVAL

Before approving, you should personally:

1. Verify numbers by re-running one benchmark yourself

## NEXT PHASE

Phase 32 hardens security.

---

# Phase 32 — SECURITY HARDENING

> **Branch:** `security/phase-32-hardening` · **Gate:** STOP — human approval required before the next phase

## Objective

Review and harden application security: authz matrix, input validation, uploads, path traversal, SQL injection, CORS, headers, secrets, errors, logging, rate limits, dependency audit.

## Why This Phase Exists

The system handles biometric and security data.

## Prerequisites

- Previous phase approved and merged (or branch checked out from it)

## Inputs

- Output of the previous phase
- This playbook

## Expected Outputs

- `docs/security/SECURITY_REVIEW.md` (findings, fixes, residual risk)
- Security test suite
- Clean `bandit`, `pip-audit`, `ruff` results (or documented exceptions)

## Architecture

Checklist: endpoint × role matrix tested exhaustively · JWT tamper/replay · brute-force limits · upload fuzzing (zero-byte, huge, polyglot, wrong magic) · traversal on every path param/filename · SQLi payloads in all text filters · CORS strict · security headers · error bodies · log redaction scan · secrets scan (`git log -p` grep, `detect-secrets` optional) · dependency CVEs · Docker non-root (Phase 36) · stream ticket abuse.

## Files To Inspect

- Repository tree (`Get-ChildItem -Recurse -Depth 3`)
- README.md
- docs/ (including the project PPT/PDF and docs/PLAYBOOK.md)
- TOKEN-OPTIMIZATION.md
- docker-compose.yml
- requirements.txt, requirements-dev.txt, requirements-gpu.txt
- .env.example, .gitignore, .dockerignore, .python-version
- `git log --oneline -15` and `git status`

## Files To Create

- docs/security/SECURITY_REVIEW.md
- backend/tests/security/test_authz_matrix.py, test_jwt.py, test_uploads.py, test_traversal.py, test_sqli.py, test_headers.py, test_log_redaction.py

## Files To Modify

- Whatever needs fixing (minimal, listed)
- requirements*.txt (upgrade vulnerable deps if needed)

## Dependencies

- bandit, pip-audit (dev)

## Environment Variables

No new variables.

## Database Changes

None.

## API Changes

None.

## Frontend Changes

None.

## Implementation Sequence

1. Create branch
2. Run bandit/pip-audit/ruff
3. Generate the endpoint × role matrix automatically from the OpenAPI schema and test it
4. Write attack tests
5. Fix findings
6. Write SECURITY_REVIEW.md with residual risks (e.g., no liveness/anti-spoofing, local-network only)
7. Commit and stop

## EXACT ANTIGRAVITY PROMPT

```text
YOU ARE IMPLEMENTING: PHASE 32 — SECURITY HARDENING

Follow the GLOBAL RULES (docs/PLAYBOOK.md Section 2). Work ONLY on this phase.


STEP 0 — BRANCH
  git checkout main ; git pull origin main ; git checkout -b security/phase-32-hardening
  (If the branch exists, check it out instead. Never commit to main.)

STEP 1 — INSPECT FIRST (do not modify anything yet)
  - Repository tree (`Get-ChildItem -Recurse -Depth 3`)
  - README.md
  - docs/ (including the project PPT/PDF and docs/PLAYBOOK.md)
  - TOKEN-OPTIMIZATION.md
  - docker-compose.yml
  - requirements.txt, requirements-dev.txt, requirements-gpu.txt
  - .env.example, .gitignore, .dockerignore, .python-version
  - `git log --oneline -15` and `git status`
  Report briefly what already exists that is relevant to this phase. Never assume a file is missing.

OBJECTIVE
  Review and harden application security: authz matrix, input validation, uploads, path traversal, SQL injection, CORS, headers, secrets, errors, logging, rate limits, dependency audit.

STEP 2 — CREATE (only after inspection; skip anything that already exists and extend it instead)
  - docs/security/SECURITY_REVIEW.md
  - backend/tests/security/test_authz_matrix.py, test_jwt.py, test_uploads.py, test_traversal.py, test_sqli.py, test_headers.py, test_log_redaction.py

STEP 3 — MODIFY
  - Whatever needs fixing (minimal, listed)
  - requirements*.txt (upgrade vulnerable deps if needed)

DO NOT MODIFY / DO NOT DO
  - Disable a check to make it pass
  - Hide findings

DEPENDENCIES: bandit, pip-audit (dev)  (resolve compatible versions, pin them, verify with `pip check`)
ENVIRONMENT VARIABLES: none new  (placeholders only in .env.example)

STEP 4 — IMPLEMENTATION ORDER
  1. Create branch
  2. Run bandit/pip-audit/ruff
  3. Generate the endpoint × role matrix automatically from the OpenAPI schema and test it
  4. Write attack tests
  5. Fix findings
  6. Write SECURITY_REVIEW.md with residual risks (e.g., no liveness/anti-spoofing, local-network only)
  7. Commit and stop

STEP 5 — TESTS (write and RUN; paste real output)
  - Every endpoint without token → 401 (except health/login)
  - Every ADMIN endpoint with OPERATOR token → 403
  - Tampered/none-alg/expired JWT → 401
  - Traversal strings rejected on upload and video paths
  - SQLi strings return normal 4xx/empty, never 500
  - Oversized/polyglot uploads rejected
  - Logs contain no password/token/embedding
  - Headers present

STEP 6 — VERIFICATION (run these and report real results)
  bandit -r backend/app -ll
  pip-audit
  ruff check backend frontend scripts
  pytest backend/tests/security -v
  git grep -nI -E "(password|secret|api[_-]?key)\s*=\s*['\"][^'\"]{6,}" -- . ':!*.md' ':!.env.example'

STEP 7 — ACCEPTANCE CRITERIA (mark each ✅ / ❌ / NOT VERIFIED — never guess)
  [ ] Authz matrix fully tested
  [ ] bandit/pip-audit results clean or justified
  [ ] Attack tests pass
  [ ] Review document complete

STEP 8 — DOCUMENTATION: update README/docs for anything this phase changed; add a short entry to docs/CHANGELOG.md.

STEP 9 — GIT CHECKPOINT (only if tests pass)
  git status ; git diff   (confirm NO secrets, images, videos, .onnx, data/ content staged)
  git add . ; git commit -m "security: harden authz, uploads, headers and dependencies; add security test suite" ; git push -u origin security/phase-32-hardening

STEP 10 — STOP. Print the REPORT FORMAT from the global rules and write: STOPPED AT PHASE 32 GATE — awaiting human approval. Do NOT start Phase 33.
```

## Commands

Windows PowerShell (run from the repo root unless stated):

```powershell
bandit -r backend/app -ll
pip-audit
ruff check backend frontend scripts
pytest backend/tests/security -v
git grep -nI -E "(password|secret|api[_-]?key)\s*=\s*['\"][^'\"]{6,}" -- . ':!*.md' ':!.env.example'
```

## Tests

- Every endpoint without token → 401 (except health/login)
- Every ADMIN endpoint with OPERATOR token → 403
- Tampered/none-alg/expired JWT → 401
- Traversal strings rejected on upload and video paths
- SQLi strings return normal 4xx/empty, never 500
- Oversized/polyglot uploads rejected
- Logs contain no password/token/embedding
- Headers present

## Manual Verification

1. Read SECURITY_REVIEW.md and challenge residual risks

## Expected Result

Documented, tested hardening with honest residual risk list.

## Failure Conditions

- Open endpoint found and unfixed
- High-severity dependency CVE ignored

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| pip-audit flags a transitive CVE | Upgrade/pin or document justified exception with review date |

## Acceptance Criteria

- [ ] Authz matrix fully tested
- [ ] bandit/pip-audit results clean or justified
- [ ] Attack tests pass
- [ ] Review document complete

## Git Checkpoint

```powershell
git checkout main
git pull origin main
git checkout -b security/phase-32-hardening   # at the START of the phase

# after tests pass:
git status
git diff
git add .
git commit -m "security: harden authz, uploads, headers and dependencies; add security test suite"
git push -u origin security/phase-32-hardening
```

Recommended commit message: `security: harden authz, uploads, headers and dependencies; add security test suite`

## HUMAN APPROVAL

Before approving, you should personally:

1. Skim the authz matrix output; confirm no public biometric endpoint

## NEXT PHASE

Phase 33 reviews biometric privacy.

---

# Phase 33 — PRIVACY HARDENING (BIOMETRICS)

> **Branch:** `security/phase-33-privacy` · **Gate:** STOP — human approval required before the next phase

## Objective

Implement and document biometric privacy controls: consent enforcement, data minimisation, retention purge jobs, biometric withdrawal (hard delete), audit-log viewing, export restrictions, and a privacy notice template.

## Why This Phase Exists

Face data is sensitive; the system must support consent, deletion and minimisation. Institutional policies and applicable laws must be reviewed before real deployment — **this is not legal advice**.

## Prerequisites

- Previous phase approved and merged (or branch checked out from it)

## Inputs

- Output of the previous phase
- This playbook

## Expected Outputs

- Consent required before enrollment (API enforced)
- `scripts/purge_retention.py` (+ scheduled task docs)
- `DELETE /students/{id}/biometrics` (withdrawal: embeddings hard-deleted, detection events de-linked or deleted per policy flag)
- `docs/privacy/PRIVACY_NOTICE_TEMPLATE.md`, `DATA_RETENTION.md`, `BIOMETRIC_DATA_INVENTORY.md`
- Audit-log viewer (ADMIN)

## Architecture

Data inventory: embeddings (kept until withdrawal/graduation), raw images (not stored), detection events (90 d), alerts (180 d), attendance (institution policy), audit logs (≥1 y). At-rest: disk encryption (BitLocker) recommended; app-level embedding encryption intentionally not used (breaks vector search — ADR-13). Exports ADMIN-only and audited.

## Files To Inspect

- Repository tree (`Get-ChildItem -Recurse -Depth 3`)
- README.md
- docs/ (including the project PPT/PDF and docs/PLAYBOOK.md)
- TOKEN-OPTIMIZATION.md
- docker-compose.yml
- requirements.txt, requirements-dev.txt, requirements-gpu.txt
- .env.example, .gitignore, .dockerignore, .python-version
- `git log --oneline -15` and `git status`

## Files To Create

- scripts/purge_retention.py
- docs/privacy/*.md
- backend/app/services/privacy_service.py
- backend/tests/security/test_privacy.py

## Files To Modify

- backend/app/api/v1/students.py (withdrawal)
- backend/app/api/v1/face.py
- frontend/pages/ Settings/Users (privacy info; audit viewer)

## Dependencies

No new dependencies.

## Environment Variables

- DETECTION_RETENTION_DAYS=90
- ALERT_RETENTION_DAYS=180
- UNKNOWN_SNAPSHOT_ENABLED=false

## Database Changes

None.

## API Changes

`DELETE /students/{id}/biometrics` (ADMIN, requires confirmation flag), `GET /audit-logs`.

## Frontend Changes

None.

## Implementation Sequence

1. Create branch
2. Privacy service + endpoints
3. Purge script with dry-run mode
4. Docs written from actual system behaviour
5. Tests
6. Commit and stop

## EXACT ANTIGRAVITY PROMPT

```text
YOU ARE IMPLEMENTING: PHASE 33 — PRIVACY HARDENING (BIOMETRICS)

Follow the GLOBAL RULES (docs/PLAYBOOK.md Section 2). Work ONLY on this phase.


STEP 0 — BRANCH
  git checkout main ; git pull origin main ; git checkout -b security/phase-33-privacy
  (If the branch exists, check it out instead. Never commit to main.)

STEP 1 — INSPECT FIRST (do not modify anything yet)
  - Repository tree (`Get-ChildItem -Recurse -Depth 3`)
  - README.md
  - docs/ (including the project PPT/PDF and docs/PLAYBOOK.md)
  - TOKEN-OPTIMIZATION.md
  - docker-compose.yml
  - requirements.txt, requirements-dev.txt, requirements-gpu.txt
  - .env.example, .gitignore, .dockerignore, .python-version
  - `git log --oneline -15` and `git status`
  Report briefly what already exists that is relevant to this phase. Never assume a file is missing.

OBJECTIVE
  Implement and document biometric privacy controls: consent enforcement, data minimisation, retention purge jobs, biometric withdrawal (hard delete), audit-log viewing, export restrictions, and a privacy notice template.

STEP 2 — CREATE (only after inspection; skip anything that already exists and extend it instead)
  - scripts/purge_retention.py
  - docs/privacy/*.md
  - backend/app/services/privacy_service.py
  - backend/tests/security/test_privacy.py

STEP 3 — MODIFY
  - backend/app/api/v1/students.py (withdrawal)
  - backend/app/api/v1/face.py
  - frontend/pages/ Settings/Users (privacy info; audit viewer)

DO NOT MODIFY / DO NOT DO
  - Make legal compliance claims
  - Delete attendance history on withdrawal (policy: keep records, remove biometrics) unless a flag says otherwise

DEPENDENCIES: none new  (resolve compatible versions, pin them, verify with `pip check`)
ENVIRONMENT VARIABLES: DETECTION_RETENTION_DAYS=90; ALERT_RETENTION_DAYS=180; UNKNOWN_SNAPSHOT_ENABLED=false  (placeholders only in .env.example)

STEP 4 — IMPLEMENTATION ORDER
  1. Create branch
  2. Privacy service + endpoints
  3. Purge script with dry-run mode
  4. Docs written from actual system behaviour
  5. Tests
  6. Commit and stop

STEP 5 — TESTS (write and RUN; paste real output)
  - Enrollment without consent → blocked
  - Withdrawal removes all embeddings (count 0) and logs audit
  - After withdrawal the person is UNKNOWN to recognition
  - Purge dry-run lists counts; real run deletes only expired rows
  - No raw image files exist after a registration session
  - Audit log lists registration/deletion/export events
  - Operator cannot access audit logs/withdrawal

STEP 6 — VERIFICATION (run these and report real results)
  python scripts\purge_retention.py --dry-run
  pytest backend/tests/security/test_privacy.py -v

STEP 7 — ACCEPTANCE CRITERIA (mark each ✅ / ❌ / NOT VERIFIED — never guess)
  [ ] Withdrawal verified live
  [ ] Retention purge verified
  [ ] Docs match behaviour
  [ ] Legal-review disclaimer present

STEP 8 — DOCUMENTATION: update README/docs for anything this phase changed; add a short entry to docs/CHANGELOG.md.

STEP 9 — GIT CHECKPOINT (only if tests pass)
  git status ; git diff   (confirm NO secrets, images, videos, .onnx, data/ content staged)
  git add . ; git commit -m "security(privacy): add consent enforcement, biometric withdrawal, retention purge and privacy docs" ; git push -u origin security/phase-33-privacy

STEP 10 — STOP. Print the REPORT FORMAT from the global rules and write: STOPPED AT PHASE 33 GATE — awaiting human approval. Do NOT start Phase 34.
```

## Commands

Windows PowerShell (run from the repo root unless stated):

```powershell
python scripts\purge_retention.py --dry-run
pytest backend/tests/security/test_privacy.py -v
```

## Tests

- Enrollment without consent → blocked
- Withdrawal removes all embeddings (count 0) and logs audit
- After withdrawal the person is UNKNOWN to recognition
- Purge dry-run lists counts; real run deletes only expired rows
- No raw image files exist after a registration session
- Audit log lists registration/deletion/export events
- Operator cannot access audit logs/withdrawal

## Manual Verification

1. Withdraw your own test biometrics; confirm you become UNKNOWN live
2. Review privacy docs for accuracy against real behaviour

## Expected Result

Demonstrable consent, minimisation, retention and deletion.

## Failure Conditions

- Embeddings remain after withdrawal
- Docs claim controls that do not exist

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| Purge deletes too much | Always run `--dry-run` first; add `--older-than` explicit |

## Acceptance Criteria

- [ ] Withdrawal verified live
- [ ] Retention purge verified
- [ ] Docs match behaviour
- [ ] Legal-review disclaimer present

## Git Checkpoint

```powershell
git checkout main
git pull origin main
git checkout -b security/phase-33-privacy   # at the START of the phase

# after tests pass:
git status
git diff
git add .
git commit -m "security(privacy): add consent enforcement, biometric withdrawal, retention purge and privacy docs"
git push -u origin security/phase-33-privacy
```

Recommended commit message: `security(privacy): add consent enforcement, biometric withdrawal, retention purge and privacy docs`

## HUMAN APPROVAL

Before approving, you should personally:

1. Have the institution/guide review the privacy notice template before any real use

## NEXT PHASE

Phase 34 consolidates testing.

---

# Phase 34 — TESTING (CONSOLIDATION)

> **Branch:** `test/phase-34-test-suite` · **Gate:** STOP — human approval required before the next phase

## Objective

Consolidate unit, integration, API, database, computer-vision, security and frontend tests; fill coverage gaps; add a single `pytest` entry point and test documentation.

## Why This Phase Exists

Protects the system from regressions before packaging.

## Prerequisites

- Previous phase approved and merged (or branch checked out from it)

## Inputs

- Output of the previous phase
- This playbook

## Expected Outputs

- Complete suite organised per Section 11
- Coverage report with measured numbers
- `docs/testing/TESTING.md`

## Architecture

Markers: `unit`, `integration`, `db`, `api`, `vision` (needs local fixtures), `security`, `slow`. CV tests skip with a clear reason when `tests/fixtures_local/` is absent.

## Files To Inspect

- Repository tree (`Get-ChildItem -Recurse -Depth 3`)
- README.md
- docs/ (including the project PPT/PDF and docs/PLAYBOOK.md)
- TOKEN-OPTIMIZATION.md
- docker-compose.yml
- requirements.txt, requirements-dev.txt, requirements-gpu.txt
- .env.example, .gitignore, .dockerignore, .python-version
- `git log --oneline -15` and `git status`

## Files To Create

- pytest.ini / pyproject pytest section
- docs/testing/TESTING.md
- Missing tests discovered by coverage

## Files To Modify

- Existing tests for flakiness
- requirements-dev.txt

## Dependencies

- pytest-cov

## Environment Variables

No new variables.

## Database Changes

None.

## API Changes

None.

## Frontend Changes

None.

## Implementation Sequence

1. Create branch
2. Run suite + coverage; list gaps
3. Write missing tests for the required scenarios
4. Fix flaky tests
5. Write TESTING.md with traceability table
6. Commit and stop

## EXACT ANTIGRAVITY PROMPT

```text
YOU ARE IMPLEMENTING: PHASE 34 — TESTING (CONSOLIDATION)

Follow the GLOBAL RULES (docs/PLAYBOOK.md Section 2). Work ONLY on this phase.


STEP 0 — BRANCH
  git checkout main ; git pull origin main ; git checkout -b test/phase-34-test-suite
  (If the branch exists, check it out instead. Never commit to main.)

STEP 1 — INSPECT FIRST (do not modify anything yet)
  - Repository tree (`Get-ChildItem -Recurse -Depth 3`)
  - README.md
  - docs/ (including the project PPT/PDF and docs/PLAYBOOK.md)
  - TOKEN-OPTIMIZATION.md
  - docker-compose.yml
  - requirements.txt, requirements-dev.txt, requirements-gpu.txt
  - .env.example, .gitignore, .dockerignore, .python-version
  - `git log --oneline -15` and `git status`
  Report briefly what already exists that is relevant to this phase. Never assume a file is missing.

OBJECTIVE
  Consolidate unit, integration, API, database, computer-vision, security and frontend tests; fill coverage gaps; add a single `pytest` entry point and test documentation.

STEP 2 — CREATE (only after inspection; skip anything that already exists and extend it instead)
  - pytest.ini / pyproject pytest section
  - docs/testing/TESTING.md
  - Missing tests discovered by coverage

STEP 3 — MODIFY
  - Existing tests for flakiness
  - requirements-dev.txt

DO NOT MODIFY / DO NOT DO
  - Delete failing tests
  - Mark tests xfail to hide bugs
  - Commit fixtures containing faces

DEPENDENCIES: pytest-cov  (resolve compatible versions, pin them, verify with `pip check`)
ENVIRONMENT VARIABLES: none new  (placeholders only in .env.example)

STEP 4 — IMPLEMENTATION ORDER
  1. Create branch
  2. Run suite + coverage; list gaps
  3. Write missing tests for the required scenarios
  4. Fix flaky tests
  5. Write TESTING.md with traceability table
  6. Commit and stop

SPECIFIC REQUIREMENTS
  - Required scenarios (all must have at least one test): student registration, face registration, invalid image, no face, multiple faces, embedding generation, embedding storage, recognition, unknown person, attendance, duplicate attendance, camera failure, database failure, authentication, authorization, API validation, security alerts, blacklist, tracking, reports, CSV export
  - Produce a traceability table: scenario → test file::test name

STEP 5 — TESTS (write and RUN; paste real output)
  - All required scenarios traced to tests
  - Suite is deterministic (run 3 times)
  - Coverage figure recorded as measured (no target claimed unless met)

STEP 6 — VERIFICATION (run these and report real results)
  pytest -q --cov=backend/app --cov-report=term-missing
  pytest -m "not vision and not slow" -q
  pytest -m vision -rs
  pytest frontend/tests -q

STEP 7 — ACCEPTANCE CRITERIA (mark each ✅ / ❌ / NOT VERIFIED — never guess)
  [ ] Traceability table complete
  [ ] Suite green (real output)
  [ ] Coverage measured
  [ ] Skips explained

STEP 8 — DOCUMENTATION: update README/docs for anything this phase changed; add a short entry to docs/CHANGELOG.md.

STEP 9 — GIT CHECKPOINT (only if tests pass)
  git status ; git diff   (confirm NO secrets, images, videos, .onnx, data/ content staged)
  git add . ; git commit -m "test: consolidate unit, integration, API, DB, vision, security and frontend tests" ; git push -u origin test/phase-34-test-suite

STEP 10 — STOP. Print the REPORT FORMAT from the global rules and write: STOPPED AT PHASE 34 GATE — awaiting human approval. Do NOT start Phase 35.
```

## Commands

Windows PowerShell (run from the repo root unless stated):

```powershell
pytest -q --cov=backend/app --cov-report=term-missing
pytest -m "not vision and not slow" -q
pytest -m vision -rs
pytest frontend/tests -q
```

## Tests

- All required scenarios traced to tests
- Suite is deterministic (run 3 times)
- Coverage figure recorded as measured (no target claimed unless met)

## Manual Verification

1. Read the traceability table; spot-check 3 tests

## Expected Result

A trustworthy regression suite.

## Failure Conditions

- Scenario without test
- Flaky tests left in

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| Vision tests all skipped | Populate `tests/fixtures_local/` locally (never commit) |
| DB tests interfere | Use separate `sas_test` DB and transactional fixtures |

## Acceptance Criteria

- [ ] Traceability table complete
- [ ] Suite green (real output)
- [ ] Coverage measured
- [ ] Skips explained

## Git Checkpoint

```powershell
git checkout main
git pull origin main
git checkout -b test/phase-34-test-suite   # at the START of the phase

# after tests pass:
git status
git diff
git add .
git commit -m "test: consolidate unit, integration, API, DB, vision, security and frontend tests"
git push -u origin test/phase-34-test-suite
```

Recommended commit message: `test: consolidate unit, integration, API, DB, vision, security and frontend tests`

## HUMAN APPROVAL

Before approving, you should personally:

1. Run `pytest -q` yourself

## NEXT PHASE

Phase 35 tests the entire system end to end.

---

# Phase 35 — END-TO-END TESTING

> **Branch:** `test/phase-35-e2e` · **Gate:** STOP — human approval required before the next phase

## Objective

Verify the complete flow on a clean setup: both modules, tracking, reports, multi-camera, restart resilience.

## Why This Phase Exists

Catches integration issues unit tests miss.

## Prerequisites

- Previous phase approved and merged (or branch checked out from it)

## Inputs

- Output of the previous phase
- This playbook

## Expected Outputs

- `scripts/e2e_check.py` (API-level scripted scenario using video-file cameras)
- `docs/testing/E2E_REPORT.md` (real results)
- Manual E2E checklist

## Architecture

Scenario: fresh DB → admin → 3 students (real local samples or video) → register → start cameras → recognition → attendance → unknown → alert → blacklist → alert → ack/resolve → tracking → reports/CSV → restart API mid-run (worker recovers) → camera failure → DB restart.

## Files To Inspect

- Repository tree (`Get-ChildItem -Recurse -Depth 3`)
- README.md
- docs/ (including the project PPT/PDF and docs/PLAYBOOK.md)
- TOKEN-OPTIMIZATION.md
- docker-compose.yml
- requirements.txt, requirements-dev.txt, requirements-gpu.txt
- .env.example, .gitignore, .dockerignore, .python-version
- `git log --oneline -15` and `git status`

## Files To Create

- scripts/e2e_check.py
- docs/testing/E2E_REPORT.md
- docs/testing/E2E_CHECKLIST.md

## Files To Modify

No existing files (other than the Git-ignored and doc updates noted).

## Dependencies

No new dependencies.

## Environment Variables

No new variables.

## Database Changes

None.

## API Changes

None.

## Frontend Changes

None.

## Implementation Sequence

1. Create branch
2. Write script + checklist
3. Run from a clean DB (`docker compose down -v` is allowed locally only with human consent)
4. Record outcomes
5. Fix defects (small commits) and re-run
6. Commit and stop

## EXACT ANTIGRAVITY PROMPT

```text
YOU ARE IMPLEMENTING: PHASE 35 — END-TO-END TESTING

Follow the GLOBAL RULES (docs/PLAYBOOK.md Section 2). Work ONLY on this phase.


STEP 0 — BRANCH
  git checkout main ; git pull origin main ; git checkout -b test/phase-35-e2e
  (If the branch exists, check it out instead. Never commit to main.)

STEP 1 — INSPECT FIRST (do not modify anything yet)
  - Repository tree (`Get-ChildItem -Recurse -Depth 3`)
  - README.md
  - docs/ (including the project PPT/PDF and docs/PLAYBOOK.md)
  - TOKEN-OPTIMIZATION.md
  - docker-compose.yml
  - requirements.txt, requirements-dev.txt, requirements-gpu.txt
  - .env.example, .gitignore, .dockerignore, .python-version
  - `git log --oneline -15` and `git status`
  Report briefly what already exists that is relevant to this phase. Never assume a file is missing.

OBJECTIVE
  Verify the complete flow on a clean setup: both modules, tracking, reports, multi-camera, restart resilience.

STEP 2 — CREATE (only after inspection; skip anything that already exists and extend it instead)
  - scripts/e2e_check.py
  - docs/testing/E2E_REPORT.md
  - docs/testing/E2E_CHECKLIST.md

STEP 3 — MODIFY
  - (nothing)

DO NOT MODIFY / DO NOT DO
  - Mock the AI in E2E
  - Mark steps passed without running

DEPENDENCIES: none new  (resolve compatible versions, pin them, verify with `pip check`)
ENVIRONMENT VARIABLES: none new  (placeholders only in .env.example)

STEP 4 — IMPLEMENTATION ORDER
  1. Create branch
  2. Write script + checklist
  3. Run from a clean DB (`docker compose down -v` is allowed locally only with human consent)
  4. Record outcomes
  5. Fix defects (small commits) and re-run
  6. Commit and stop

SPECIFIC REQUIREMENTS
  - Steps needing a physical camera or person are human-run; Antigravity must list them as `HUMAN STEP` and not claim them

STEP 5 — TESTS (write and RUN; paste real output)
  - Every checklist step recorded ✅/❌ with evidence
  - Restart resilience: kill API process mid-run, restart, workers recover
  - DB restart: API reconnects
  - Camera unplug: status OFFLINE, others unaffected

STEP 6 — VERIFICATION (run these and report real results)
  docker compose down -v
  docker compose up -d db
  cd backend ; alembic upgrade head ; cd ..
  python scripts\create_admin.py --username admin --role ADMIN
  python scripts\e2e_check.py
  pytest -q

STEP 7 — ACCEPTANCE CRITERIA (mark each ✅ / ❌ / NOT VERIFIED — never guess)
  [ ] E2E script passes
  [ ] Human steps completed and recorded
  [ ] Resilience verified
  [ ] Defects fixed or logged

STEP 8 — DOCUMENTATION: update README/docs for anything this phase changed; add a short entry to docs/CHANGELOG.md.

STEP 9 — GIT CHECKPOINT (only if tests pass)
  git status ; git diff   (confirm NO secrets, images, videos, .onnx, data/ content staged)
  git add . ; git commit -m "test(e2e): add end-to-end script, checklist and verified report" ; git push -u origin test/phase-35-e2e

STEP 10 — STOP. Print the REPORT FORMAT from the global rules and write: STOPPED AT PHASE 35 GATE — awaiting human approval. Do NOT start Phase 36.
```

## Commands

Windows PowerShell (run from the repo root unless stated):

```powershell
docker compose down -v
docker compose up -d db
cd backend ; alembic upgrade head ; cd ..
python scripts\create_admin.py --username admin --role ADMIN
python scripts\e2e_check.py
pytest -q
```

## Tests

- Every checklist step recorded ✅/❌ with evidence
- Restart resilience: kill API process mid-run, restart, workers recover
- DB restart: API reconnects
- Camera unplug: status OFFLINE, others unaffected

## Manual Verification

1. Perform the HUMAN STEPS in the checklist

## Expected Result

The full product behaves correctly from a clean install.

## Failure Conditions

- Any step skipped or unrecorded
- Unrecoverable failure after restart

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| Stale connections after DB restart | Enable `pool_pre_ping=True` |

## Acceptance Criteria

- [ ] E2E script passes
- [ ] Human steps completed and recorded
- [ ] Resilience verified
- [ ] Defects fixed or logged

## Git Checkpoint

```powershell
git checkout main
git pull origin main
git checkout -b test/phase-35-e2e   # at the START of the phase

# after tests pass:
git status
git diff
git add .
git commit -m "test(e2e): add end-to-end script, checklist and verified report"
git push -u origin test/phase-35-e2e
```

Recommended commit message: `test(e2e): add end-to-end script, checklist and verified report`

## HUMAN APPROVAL

Before approving, you should personally:

1. Execute the human steps yourself

## NEXT PHASE

Phase 36 containerises the full application.

---

# Phase 36 — DOCKER FULL APPLICATION

> **Branch:** `feature/phase-36-docker-full` · **Gate:** STOP — human approval required before the next phase

## Objective

Containerise backend and frontend, add them to compose with Postgres (and Redis optional), healthchecks, non-root users, model-weight volume and migration-on-start.

## Why This Phase Exists

One-command reproducible deployment/demo.

## Prerequisites

- Previous phase approved and merged (or branch checked out from it)

## Inputs

- Output of the previous phase
- This playbook

## Expected Outputs

- `docker/Dockerfile.backend`, `docker/Dockerfile.frontend`
- Compose profile `full`
- `docs/DEPLOYMENT.md`

## Architecture

```text
compose --profile full: db, backend (uvicorn), frontend (streamlit), [redis]
Volumes: pgdata, insightface_models (weights NOT in image/Git), data (videos)
Webcam: NOT available in Docker Desktop on Windows → full-Docker mode uses VIDEO_FILE/RTSP cameras. For webcam demos run backend on host (ADR-15).
```
Backend image: `python:3.11-slim`, `opencv-python-headless`, needed apt libs (`libgl1`, `libglib2.0-0`), non-root user, `HEALTHCHECK`. Entrypoint: wait for DB → `alembic upgrade head` → start.

## Files To Inspect

- Repository tree (`Get-ChildItem -Recurse -Depth 3`)
- README.md
- docs/ (including the project PPT/PDF and docs/PLAYBOOK.md)
- TOKEN-OPTIMIZATION.md
- docker-compose.yml
- requirements.txt, requirements-dev.txt, requirements-gpu.txt
- .env.example, .gitignore, .dockerignore, .python-version
- `git log --oneline -15` and `git status`

## Files To Create

- docker/Dockerfile.backend
- docker/Dockerfile.frontend
- docker/entrypoint.sh
- docs/DEPLOYMENT.md

## Files To Modify

- docker-compose.yml
- .dockerignore (exclude data/, .venv, tests/fixtures_local, .env)
- requirements.txt (headless OpenCV for container if separate file needed: requirements-docker.txt)

## Dependencies

No new dependencies.

## Environment Variables

No new variables.

## Database Changes

None.

## API Changes

None.

## Frontend Changes

None.

## Implementation Sequence

1. Create branch
2. Write Dockerfiles
3. Compose profile + env wiring
4. First-run weights download into the models volume (documented command)
5. Build and run
6. Run E2E using video cameras
7. Document webcam limitation
8. Commit and stop

## EXACT ANTIGRAVITY PROMPT

```text
YOU ARE IMPLEMENTING: PHASE 36 — DOCKER FULL APPLICATION

Follow the GLOBAL RULES (docs/PLAYBOOK.md Section 2). Work ONLY on this phase.


STEP 0 — BRANCH
  git checkout main ; git pull origin main ; git checkout -b feature/phase-36-docker-full
  (If the branch exists, check it out instead. Never commit to main.)

STEP 1 — INSPECT FIRST (do not modify anything yet)
  - Repository tree (`Get-ChildItem -Recurse -Depth 3`)
  - README.md
  - docs/ (including the project PPT/PDF and docs/PLAYBOOK.md)
  - TOKEN-OPTIMIZATION.md
  - docker-compose.yml
  - requirements.txt, requirements-dev.txt, requirements-gpu.txt
  - .env.example, .gitignore, .dockerignore, .python-version
  - `git log --oneline -15` and `git status`
  Report briefly what already exists that is relevant to this phase. Never assume a file is missing.

OBJECTIVE
  Containerise backend and frontend, add them to compose with Postgres (and Redis optional), healthchecks, non-root users, model-weight volume and migration-on-start.

STEP 2 — CREATE (only after inspection; skip anything that already exists and extend it instead)
  - docker/Dockerfile.backend
  - docker/Dockerfile.frontend
  - docker/entrypoint.sh
  - docs/DEPLOYMENT.md

STEP 3 — MODIFY
  - docker-compose.yml
  - .dockerignore (exclude data/, .venv, tests/fixtures_local, .env)
  - requirements.txt (headless OpenCV for container if separate file needed: requirements-docker.txt)

DO NOT MODIFY / DO NOT DO
  - Bake secrets, weights or biometric data into images
  - Run as root
  - Expose DB port publicly in `full` profile

DEPENDENCIES: none new  (resolve compatible versions, pin them, verify with `pip check`)
ENVIRONMENT VARIABLES: none new  (placeholders only in .env.example)

STEP 4 — IMPLEMENTATION ORDER
  1. Create branch
  2. Write Dockerfiles
  3. Compose profile + env wiring
  4. First-run weights download into the models volume (documented command)
  5. Build and run
  6. Run E2E using video cameras
  7. Document webcam limitation
  8. Commit and stop

STEP 5 — TESTS (write and RUN; paste real output)
  - All services healthy
  - Login works through the containerised UI
  - Video-file recognition + attendance works inside the container
  - `docker history` / image contents contain no `.env`, `.onnx`, images
  - Container runs as non-root (`whoami`)
  - Data survives restart

STEP 6 — VERIFICATION (run these and report real results)
  docker compose --profile full build
  docker compose --profile full up -d
  docker compose --profile full ps
  curl.exe http://127.0.0.1:8000/api/v1/health
  docker compose --profile full logs backend --tail 50
  docker compose --profile full down

STEP 7 — ACCEPTANCE CRITERIA (mark each ✅ / ❌ / NOT VERIFIED — never guess)
  [ ] Full stack runs in Docker
  [ ] No secrets/weights in images
  [ ] Non-root verified
  [ ] Webcam limitation documented

STEP 8 — DOCUMENTATION: update README/docs for anything this phase changed; add a short entry to docs/CHANGELOG.md.

STEP 9 — GIT CHECKPOINT (only if tests pass)
  git status ; git diff   (confirm NO secrets, images, videos, .onnx, data/ content staged)
  git add . ; git commit -m "feat(docker): containerise backend and frontend with compose full profile" ; git push -u origin feature/phase-36-docker-full

STEP 10 — STOP. Print the REPORT FORMAT from the global rules and write: STOPPED AT PHASE 36 GATE — awaiting human approval. Do NOT start Phase 37.
```

## Commands

Windows PowerShell (run from the repo root unless stated):

```powershell
docker compose --profile full build
docker compose --profile full up -d
docker compose --profile full ps
curl.exe http://127.0.0.1:8000/api/v1/health
docker compose --profile full logs backend --tail 50
docker compose --profile full down
```

## Tests

- All services healthy
- Login works through the containerised UI
- Video-file recognition + attendance works inside the container
- `docker history` / image contents contain no `.env`, `.onnx`, images
- Container runs as non-root (`whoami`)
- Data survives restart

## Manual Verification

1. Open http://localhost:8501, log in, run a video-file camera

## Expected Result

`docker compose --profile full up` produces a working system (with video/RTSP cameras).

## Failure Conditions

- Weights/secrets baked into image
- Root user
- Migrations not applied

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| `libGL.so.1` missing | Use headless OpenCV or install `libgl1` |
| Slow first start | Model download into volume; wait for logs |
| Camera not found in container | Expected; use video/RTSP or host-run backend |

## Acceptance Criteria

- [ ] Full stack runs in Docker
- [ ] No secrets/weights in images
- [ ] Non-root verified
- [ ] Webcam limitation documented

## Git Checkpoint

```powershell
git checkout main
git pull origin main
git checkout -b feature/phase-36-docker-full   # at the START of the phase

# after tests pass:
git status
git diff
git add .
git commit -m "feat(docker): containerise backend and frontend with compose full profile"
git push -u origin feature/phase-36-docker-full
```

Recommended commit message: `feat(docker): containerise backend and frontend with compose full profile`

## HUMAN APPROVAL

Before approving, you should personally:

1. Bring the stack up from scratch and log in

## NEXT PHASE

Phase 37 finalises documentation.

---

# Phase 37 — DOCUMENTATION

> **Branch:** `docs/phase-37-documentation` · **Gate:** STOP — human approval required before the next phase

## Objective

Produce complete, accurate documentation derived from the real system.

## Why This Phase Exists

The final report/viva requires reproducible setup and clear explanations.

## Prerequisites

- Previous phase approved and merged (or branch checked out from it)

## Inputs

- Output of the previous phase
- This playbook

## Expected Outputs

- README.md (overview, screenshots placeholders, quick start)
- docs/: ARCHITECTURE, API (exported OpenAPI + narrative), DATABASE, SETUP, TESTING, SECURITY, PRIVACY, DEPLOYMENT, TROUBLESHOOTING, USER_GUIDE, PERFORMANCE (linked), LIMITATIONS

## Architecture

Docs must match code. Export OpenAPI JSON to `docs/api/openapi.json`. Include Mermaid diagrams updated to the final system. LIMITATIONS must list: no liveness/anti-spoofing, lighting/angle sensitivity, CPU performance limits, detection-based (not continuous) tracking, institutional/legal review required.

## Files To Inspect

- Repository tree (`Get-ChildItem -Recurse -Depth 3`)
- README.md
- docs/ (including the project PPT/PDF and docs/PLAYBOOK.md)
- TOKEN-OPTIMIZATION.md
- docker-compose.yml
- requirements.txt, requirements-dev.txt, requirements-gpu.txt
- .env.example, .gitignore, .dockerignore, .python-version
- `git log --oneline -15` and `git status`

## Files To Create

- docs/*.md as listed
- docs/api/openapi.json

## Files To Modify

- README.md

## Dependencies

No new dependencies.

## Environment Variables

No new variables.

## Database Changes

None.

## API Changes

None.

## Frontend Changes

None.

## Implementation Sequence

1. Create branch
2. Generate OpenAPI export
3. Write/refresh each doc by reading actual code
4. Verify every command in docs by running it
5. Link check
6. Commit and stop

## EXACT ANTIGRAVITY PROMPT

```text
YOU ARE IMPLEMENTING: PHASE 37 — DOCUMENTATION

Follow the GLOBAL RULES (docs/PLAYBOOK.md Section 2). Work ONLY on this phase.


STEP 0 — BRANCH
  git checkout main ; git pull origin main ; git checkout -b docs/phase-37-documentation
  (If the branch exists, check it out instead. Never commit to main.)

STEP 1 — INSPECT FIRST (do not modify anything yet)
  - Repository tree (`Get-ChildItem -Recurse -Depth 3`)
  - README.md
  - docs/ (including the project PPT/PDF and docs/PLAYBOOK.md)
  - TOKEN-OPTIMIZATION.md
  - docker-compose.yml
  - requirements.txt, requirements-dev.txt, requirements-gpu.txt
  - .env.example, .gitignore, .dockerignore, .python-version
  - `git log --oneline -15` and `git status`
  Report briefly what already exists that is relevant to this phase. Never assume a file is missing.

OBJECTIVE
  Produce complete, accurate documentation derived from the real system.

STEP 2 — CREATE (only after inspection; skip anything that already exists and extend it instead)
  - docs/*.md as listed
  - docs/api/openapi.json

STEP 3 — MODIFY
  - README.md

DO NOT MODIFY / DO NOT DO
  - Document features that do not exist
  - Include screenshots with real students' faces in Git (use your own consented images or blur)

DEPENDENCIES: none new  (resolve compatible versions, pin them, verify with `pip check`)
ENVIRONMENT VARIABLES: none new  (placeholders only in .env.example)

STEP 4 — IMPLEMENTATION ORDER
  1. Create branch
  2. Generate OpenAPI export
  3. Write/refresh each doc by reading actual code
  4. Verify every command in docs by running it
  5. Link check
  6. Commit and stop

STEP 5 — TESTS (write and RUN; paste real output)
  - Every documented command executed successfully
  - No TODO/TBD left
  - Docs list all env vars from Section 6 correctly

STEP 6 — VERIFICATION (run these and report real results)
  python -c "import json; from backend.app.main import app; print(json.dumps(app.openapi()))" > docs\api\openapi.json
  Select-String -Path docs\*.md -Pattern 'TODO|TBD|FIXME'

STEP 7 — ACCEPTANCE CRITERIA (mark each ✅ / ❌ / NOT VERIFIED — never guess)
  [ ] All documents exist
  [ ] Commands verified
  [ ] Limitations honest
  [ ] OpenAPI exported

STEP 8 — DOCUMENTATION: update README/docs for anything this phase changed; add a short entry to docs/CHANGELOG.md.

STEP 9 — GIT CHECKPOINT (only if tests pass)
  git status ; git diff   (confirm NO secrets, images, videos, .onnx, data/ content staged)
  git add . ; git commit -m "docs: complete README, architecture, API, setup, security, privacy and troubleshooting docs" ; git push -u origin docs/phase-37-documentation

STEP 10 — STOP. Print the REPORT FORMAT from the global rules and write: STOPPED AT PHASE 37 GATE — awaiting human approval. Do NOT start Phase 38.
```

## Commands

Windows PowerShell (run from the repo root unless stated):

```powershell
python -c "import json; from backend.app.main import app; print(json.dumps(app.openapi()))" > docs\api\openapi.json
Select-String -Path docs\*.md -Pattern 'TODO|TBD|FIXME'
```

## Tests

- Every documented command executed successfully
- No TODO/TBD left
- Docs list all env vars from Section 6 correctly

## Manual Verification

1. Follow README on a fresh clone to a working login (ask a teammate to try)

## Expected Result

Someone new can set up, run, test and understand the system.

## Failure Conditions

- Docs describe unimplemented features
- Commands that do not work

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| Docs drift | Grep code for env var names and compare with docs |

## Acceptance Criteria

- [ ] All documents exist
- [ ] Commands verified
- [ ] Limitations honest
- [ ] OpenAPI exported

## Git Checkpoint

```powershell
git checkout main
git pull origin main
git checkout -b docs/phase-37-documentation   # at the START of the phase

# after tests pass:
git status
git diff
git add .
git commit -m "docs: complete README, architecture, API, setup, security, privacy and troubleshooting docs"
git push -u origin docs/phase-37-documentation
```

Recommended commit message: `docs: complete README, architecture, API, setup, security, privacy and troubleshooting docs`

## HUMAN APPROVAL

Before approving, you should personally:

1. Fresh-clone dry run by someone else

## NEXT PHASE

Phase 38 prepares the final demonstration.

---

# Phase 38 — FINAL DEMONSTRATION

> **Branch:** `release/phase-38-final-demo` · **Gate:** STOP — human approval required before the next phase

## Objective

Prepare and rehearse the complete demonstration showing BOTH modules in ONE application, with backups for live-demo risks.

## Why This Phase Exists

Final evaluation (project Week 16).

## Prerequisites

- Previous phase approved and merged (or branch checked out from it)

## Inputs

- Output of the previous phase
- This playbook

## Expected Outputs

- `docs/DEMO_SCRIPT.md` (24 steps, timings, expected screens, fallback plan)
- `scripts/seed_demo.py` (non-biometric demo data only: admin/operator, cameras, settings)
- Backup recorded demo videos (local, **not** in Git)
- Final tag `v1.0.0` (after human approval)

## Architecture

Demo order:

**PART 1 — ATTENDANCE:** 1 Login · 2 Register students · 3 Capture face · 4 Start laptop webcam · 5 Recognize myself · 6 Recognize friend · 7 Green boxes · 8 Attendance · 9 Duplicate prevention · 10 Attendance report

**PART 2 — SECURITY:** 11 Unregistered person · 12 UNKNOWN · 13 Security event · 14 Alert · 15 Blacklist a consenting test identity · 16 Blacklisted recognition · 17 High-priority (CRITICAL) alert · 18 Alert management (ack/resolve)

**PART 3 — TRACKING:** 19 Search recognized person · 20 Detection history · 21 Last known location

**PART 4 — CCTV:** 22 Video file · 23 RTSP architecture/config (live only if verified) · 24 Camera management

End with: dashboard KPIs, performance report numbers (measured), limitations and privacy slide.

## Files To Inspect

- Repository tree (`Get-ChildItem -Recurse -Depth 3`)
- README.md
- docs/ (including the project PPT/PDF and docs/PLAYBOOK.md)
- TOKEN-OPTIMIZATION.md
- docker-compose.yml
- requirements.txt, requirements-dev.txt, requirements-gpu.txt
- .env.example, .gitignore, .dockerignore, .python-version
- `git log --oneline -15` and `git status`

## Files To Create

- docs/DEMO_SCRIPT.md
- scripts/seed_demo.py
- docs/DEMO_CHECKLIST.md (pre-flight)

## Files To Modify

- README.md (demo section)

## Dependencies

No new dependencies.

## Environment Variables

No new variables.

## Database Changes

None.

## API Changes

None.

## Frontend Changes

None.

## Implementation Sequence

1. Create branch
2. Write demo script + checklist
3. Seed script (idempotent)
4. Rehearse full demo twice; record timing and any failures in DEMO_SCRIPT.md
5. Fix issues found (small commits)
6. Final regression run
7. After human approval: tag v1.0.0
8. Stop

## EXACT ANTIGRAVITY PROMPT

```text
YOU ARE IMPLEMENTING: PHASE 38 — FINAL DEMONSTRATION

Follow the GLOBAL RULES (docs/PLAYBOOK.md Section 2). Work ONLY on this phase.


STEP 0 — BRANCH
  git checkout main ; git pull origin main ; git checkout -b release/phase-38-final-demo
  (If the branch exists, check it out instead. Never commit to main.)

STEP 1 — INSPECT FIRST (do not modify anything yet)
  - Repository tree (`Get-ChildItem -Recurse -Depth 3`)
  - README.md
  - docs/ (including the project PPT/PDF and docs/PLAYBOOK.md)
  - TOKEN-OPTIMIZATION.md
  - docker-compose.yml
  - requirements.txt, requirements-dev.txt, requirements-gpu.txt
  - .env.example, .gitignore, .dockerignore, .python-version
  - `git log --oneline -15` and `git status`
  Report briefly what already exists that is relevant to this phase. Never assume a file is missing.

OBJECTIVE
  Prepare and rehearse the complete demonstration showing BOTH modules in ONE application, with backups for live-demo risks.

STEP 2 — CREATE (only after inspection; skip anything that already exists and extend it instead)
  - docs/DEMO_SCRIPT.md
  - scripts/seed_demo.py
  - docs/DEMO_CHECKLIST.md (pre-flight)

STEP 3 — MODIFY
  - README.md (demo section)

DO NOT MODIFY / DO NOT DO
  - Show or commit real students' biometric data without consent
  - Claim results not in the reports

DEPENDENCIES: none new  (resolve compatible versions, pin them, verify with `pip check`)
ENVIRONMENT VARIABLES: none new  (placeholders only in .env.example)

STEP 4 — IMPLEMENTATION ORDER
  1. Create branch
  2. Write demo script + checklist
  3. Seed script (idempotent)
  4. Rehearse full demo twice; record timing and any failures in DEMO_SCRIPT.md
  5. Fix issues found (small commits)
  6. Final regression run
  7. After human approval: tag v1.0.0
  8. Stop

SPECIFIC REQUIREMENTS
  - Pre-flight checklist: camera free, DB up, models downloaded, threshold set, friends' registrations done, lighting checked, backup video ready, laptop on charger/performance power plan
  - Fallback plan per step (e.g., webcam fails → run video-file camera)

STEP 5 — TESTS (write and RUN; paste real output)
  - Full rehearsal: all 24 steps ✅ or documented fallback used
  - Final `pytest -q` green
  - Seed script idempotent (run twice)

STEP 6 — VERIFICATION (run these and report real results)
  python scripts\seed_demo.py
  docker compose up -d db
  uvicorn backend.app.main:app --port 8000
  streamlit run frontend\app.py
  pytest -q
  git tag -a v1.0.0 -m "Smart Attendance & Security Management System v1.0.0"   # after approval
  git push origin v1.0.0

STEP 7 — ACCEPTANCE CRITERIA (mark each ✅ / ❌ / NOT VERIFIED — never guess)
  [ ] 24-step demo rehearsed
  [ ] Fallbacks documented
  [ ] All claims traceable to reports
  [ ] Tag v1.0.0 created after approval

STEP 8 — DOCUMENTATION: update README/docs for anything this phase changed; add a short entry to docs/CHANGELOG.md.

STEP 9 — GIT CHECKPOINT (only if tests pass)
  git status ; git diff   (confirm NO secrets, images, videos, .onnx, data/ content staged)
  git add . ; git commit -m "docs(demo): add final demonstration script, seed data and release checklist" ; git push -u origin release/phase-38-final-demo

STEP 10 — STOP. Print the REPORT FORMAT from the global rules and write: STOPPED AT PHASE 38 GATE — awaiting human approval. Do NOT start Phase 39.
```

## Commands

Windows PowerShell (run from the repo root unless stated):

```powershell
python scripts\seed_demo.py
docker compose up -d db
uvicorn backend.app.main:app --port 8000
streamlit run frontend\app.py
pytest -q
git tag -a v1.0.0 -m "Smart Attendance & Security Management System v1.0.0"   # after approval
git push origin v1.0.0
```

## Tests

- Full rehearsal: all 24 steps ✅ or documented fallback used
- Final `pytest -q` green
- Seed script idempotent (run twice)

## Manual Verification

1. Rehearse in front of someone and time it
2. Practise answering: accuracy (cite measured report), limitations, privacy, why InsightFace/pgvector

## Expected Result

A smooth, honest, end-to-end demonstration of one unified application.

## Failure Conditions

- Demo depends on an unverified feature
- Claims exceed measured evidence

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| Webcam busy during demo | Close other apps; fallback to video-file camera |
| Bad lighting | Add a lamp facing the person; recheck threshold |

## Acceptance Criteria

- [ ] 24-step demo rehearsed
- [ ] Fallbacks documented
- [ ] All claims traceable to reports
- [ ] Tag v1.0.0 created after approval

## Git Checkpoint

```powershell
git checkout main
git pull origin main
git checkout -b release/phase-38-final-demo   # at the START of the phase

# after tests pass:
git status
git diff
git add .
git commit -m "docs(demo): add final demonstration script, seed data and release checklist"
git push -u origin release/phase-38-final-demo
```

Recommended commit message: `docs(demo): add final demonstration script, seed data and release checklist`

## HUMAN APPROVAL

Before approving, you should personally:

1. Perform the full demo yourself, cold, from the checklist

## NEXT PHASE

Project complete. Maintain via the Troubleshooting appendix; GPU support (`requirements-gpu.txt`) and a React frontend are optional future work requiring a new ADR.

---

# APPENDIX A — RECOVERY PROMPTS (copy-paste when Antigravity misbehaves)

**Agent changed too much:**
```text
STOP. You modified files outside the current phase. Run `git status` and `git diff --stat`.
List every file changed. Revert (with `git checkout -- <file>`) everything that is not listed under
"Files To Create/Modify" for this phase. Do not delete untracked work without asking me. Then re-run the tests.
```

**Agent claims success without evidence:**
```text
You reported success without command output. Re-run every verification command from this phase.
Paste the real output. Mark each acceptance criterion ✅ / ❌ / NOT VERIFIED. Do not summarise from memory.
```

**Test failure loop:**
```text
Tests failed. Show the failing test names and the full assertion error. Diagnose the root cause before editing.
Fix only the cause. Do not weaken or delete tests. Re-run and paste the output.
```

**New session / context lost:**
```text
Read docs/PLAYBOOK.md Section 2 (Global Rules) and Phase <N>. Inspect the repo and `git log -15` and
`git status` to determine what is already implemented for this phase. Continue from there; do not redo
completed work. Report what you found before changing anything.
```

**Secrets or biometric files staged:**
```text
Run `git status`. If any .env, image, video, .onnx file, or data/ content is staged, run
`git restore --staged <path>`, add the pattern to .gitignore, and show me `git status` again.
If anything sensitive was already committed, STOP and tell me — do not rewrite history yourself.
```

---

# APPENDIX B — GLOBAL TROUBLESHOOTING

| Problem | Where | Fix |
|---|---|---|
| insightface build error on Windows | Phase 2 | Install Visual Studio Build Tools (C++), retry; confirm Python 3.11 |
| Webcam busy / black frames | 8, 14 | Close other camera apps; `cv2.CAP_DSHOW`; try index 1 |
| Everyone recognised as UNKNOWN | 13, 18 | Check threshold vs calibration table; re-register with more varied samples; verify same model for register and recognise |
| Strangers recognised as students | 13, 18 | Raise threshold, enable margin, add more impostor data to calibration |
| Low FPS | 14, 28 | Raise `PROCESS_EVERY_N_FRAMES`, lower `DET_SIZE`/resolution, try `buffalo_s` — measure each change |
| Attendance duplicates | 15 | Verify unique constraint exists; check `session_label` and timezone |
| Alert spam | 25 | Inspect `dedup_key`; confirm partial unique index; raise window |
| Streamlit cannot show video | 8, 14 | Use ticketed MJPEG `<img>`; check CORS and ticket expiry |
| `type "vector" does not exist` | 3, 4 | Extension missing; use `pgvector/pgvector:pg16` image and init SQL |
| Alembic cannot find models | 4 | Run from `backend/`; fix `prepend_sys_path` |
| 401 after restart | 6 | `JWT_SECRET` changed or `.env` not loaded |
| Docker container cannot open webcam | 36 | Expected on Windows; use video/RTSP or run backend on host |
| Port in use (5432/8000/8501) | any | `netstat -ano | findstr :8000` then stop the process or change port |

---

# APPENDIX C — QUALITY CHECKLIST (where each requirement is covered)

| Requirement | Covered in |
|---|---|
| One unified application, two modules | Sections 1, 3, 8 |
| Shared AI vision engine | Section 7, Phases 10–14, 23 |
| Laptop webcam MVP first | Phases 8, 14–19 |
| Registration / preprocessing / detection | Phases 8, 9, 10 |
| InsightFace/ArcFace + pgvector | ADR-02/03, Phases 11–13 |
| Recognition, attendance, dedup | Phases 13, 15 |
| Unknown detection | Phase 17 |
| Blacklist, alerts | Phases 24, 25 |
| Camera management, video, RTSP, multi-camera | Phases 20–22, 28 |
| Person tracking / movement history | ADR-09, Phase 27 |
| Dashboard, reports, CSV | Phases 16, 26, 30 |
| Authentication, security, privacy | Phases 6, 32, 33; Sections 9–10 |
| PostgreSQL, Redis (justified), Docker | Phases 3, 4, 29, 36 |
| Windows, CPU-first | Global Rules, Phase 2, all commands |
| Testing, performance measurement | Phases 18, 31, 34, 35; Sections 11–12 |
| Git workflow, phase gates, human approvals | Sections 0, 13; every phase |
| Final documentation and demo | Phases 37, 38 |

---

# APPENDIX D — KNOWN LIMITATIONS TO STATE HONESTLY

1. **No liveness / anti-spoofing:** a printed photo or phone screen of a registered person may be accepted. Phase 18 must record the observed behaviour. Possible future work, not in this scope.
2. **Accuracy depends on lighting, angle, distance and enrollment quality;** the ≥90 % target is validated only by your Phase 18 dataset.
3. **CPU-only throughput** limits FPS and simultaneous cameras; numbers come from Phase 31.
4. **"Tracking" is detection-based sightings** from camera events, not continuous trajectory tracking.
5. **Similarity scores are not probabilities** and are not "accuracy".
6. **Legal/ethical review required** by the institution before deploying face recognition on real people.

---

# APPENDIX E — GLOSSARY

**Embedding:** 512-number vector representing a face. **Cosine similarity:** angle-based closeness (1 = identical direction). **HNSW:** approximate nearest-neighbour index in pgvector. **SCRFD:** InsightFace face detector. **ArcFace:** recognition model producing embeddings. **FAR/FRR:** false accept / false reject rate. **Sighting:** group of nearby detection events of one person on one camera. **ADR:** architecture decision record. **MJPEG:** stream of JPEG frames viewable via `<img>`.

*End of playbook.*

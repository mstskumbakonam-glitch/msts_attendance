# Architecture Decision Records (ADRs)

This document records the foundational architectural decisions for the **Smart Attendance and Security System**.

---

## Index of Architecture Decisions

| ID | Title | Choice Summary | Status |
|---|---|---|---|
| [ADR-01](#adr-01-architecture-style) | Architecture Style | Modular Monolith (`backend/` + `frontend/`) | Accepted |
| [ADR-02](#adr-02-face-detector--recognizer) | Face Detector & Recognizer | InsightFace `buffalo_l` (SCRFD + ArcFace R50) | Accepted |
| [ADR-03](#adr-03-vector-store) | Vector Store Engine | PostgreSQL 16 + pgvector (`vector(512)`, HNSW cosine) | Accepted |
| [ADR-04](#adr-04-backend-framework) | Backend Framework | FastAPI + SQLAlchemy 2.x + Alembic + Pydantic v2 | Accepted |
| [ADR-05](#adr-05-frontend-framework) | Frontend Framework | Streamlit Multi-Page Application | Accepted |
| [ADR-06](#adr-06-camera-access) | Camera Access Model | Server-side OpenCV capture worker threads | Accepted |
| [ADR-07](#adr-07-authentication--authorization) | Auth & Password Hashing | Argon2id + JWT + `jti` Denylist Deny-on-Logout | Accepted |
| [ADR-08](#adr-08-attendance-deduplication) | Attendance Deduplication | DB Unique Constraint + In-Memory Cooldown Guard | Accepted |
| [ADR-09](#adr-09-movement-history) | Movement History Model | No separate `movement_history` table (query over `detection_events`) | Accepted |
| [ADR-10](#adr-10-redis-usage) | Redis Usage Scope | Deferred to Phase 29 (Optional Pub/Sub bridge & TTL cache) | Accepted |
| [ADR-11](#adr-11-raw-image-retention) | Raw Image Retention | Transient memory processing (`RETAIN_RAW_IMAGES=false`) | Accepted |
| [ADR-12](#adr-12-identity-search-scope) | Identity Search Scope | Unified single pass vector search (Students + Blacklist) | Accepted |
| [ADR-13](#adr-13-embedding-protection) | Embedding Protection | OS-level encryption + DB ACLs; never exposed via API | Accepted |
| [ADR-14](#adr-14-timezone-handling) | Timezone & Date Bounds | `APP_TIMEZONE=Asia/Kolkata`, stored as UTC `timestamptz` | Accepted |
| [ADR-15](#adr-15-docker--webcam-execution) | Docker & Webcam Strategy | Hybrid host backend MVP for webcam; Full Docker for RTSP | Accepted |

---

## ADR Details

### ADR-01: Architecture Style
- **Status:** Accepted
- **Context:** The system needs automated attendance marking and CCTV security monitoring. We must choose between microservices and a monolith.
- **Decision:** Build a **Modular Monolith** with a single `backend/` package and a `frontend/` Streamlit application.
- **Consequences:** Simple deployment, zero distributed IPC overhead, single database transaction boundary.
- **Revisit Conditions:** Never for this project scope.

### ADR-02: Face Detector & Recognizer
- **Status:** Accepted
- **Context:** Face detection and embedding generation require accurate, fast CPU inference models.
- **Decision:** Select **InsightFace `buffalo_l` pack** (SCRFD for detection and landmark alignment + ArcFace `w600k_r50` for 512-d L2-normalized embeddings) on `onnxruntime` CPU.
- **Consequences:** Single robust library handles detection, landmark alignment, and embedding extraction. High accuracy on CPU.
- **Revisit Conditions:** If CPU detection latency exceeds target limits on low-spec hardware, evaluate `buffalo_s`.

### ADR-03: Vector Store
- **Status:** Accepted
- **Context:** High-dimensional vector search (512-d cosine similarity) is required for matching identity face embeddings against registered candidates.
- **Decision:** Use **PostgreSQL 16 with the `pgvector` extension**, utilizing `vector(512)` data type and HNSW index with `vector_cosine_ops`. Cosine similarity is computed as `1 - (a <=> b)`.
- **Consequences:** Eliminates secondary vector database infrastructure (ChromaDB, Qdrant, etc.). Single database handles relational metadata and vector searches.
- **Revisit Conditions:** Re-evaluate if vector dataset exceeds 100,000 active face embeddings.

### ADR-04: Backend Framework
- **Status:** Accepted
- **Context:** Needs a fast, typed, async Python web API framework with automatic OpenAPI documentation and ORM migration support.
- **Decision:** Use **FastAPI**, **SQLAlchemy 2.x** (with async engine support), **Alembic** migrations, and **Pydantic v2**.
- **Consequences:** Type safety, fast serialization, clean repository patterns, automatic OpenAPI docs at `/docs`.
- **Revisit Conditions:** None.

### ADR-05: Frontend Framework
- **Status:** Accepted
- **Context:** An administrative dashboard is required to display attendance summaries, security alerts, live camera streams, and tracking history.
- **Decision:** Use **Streamlit** multi-page dashboard running on port 8501. Live video feeds are served via HTTP MJPEG multipart streams (`/api/v1/stream/{camera}?ticket=...`) rendered in standard HTML `<img>` elements.
- **Consequences:** Rapid UI development in pure Python, built-in layout widgets.
- **Revisit Conditions:** If UI requirement exceeds Streamlit capabilities, consider React (requires human approval).

### ADR-06: Camera Access Model
- **Status:** Accepted
- **Context:** Live video frames must be read continuously from local webcams, video files, or CCTV RTSP endpoints.
- **Decision:** Execute **Server-side OpenCV capture** in dedicated worker threads (`CameraWorker`).
- **Consequences:** Zero browser webcam permissions needed; backend directly interfaces with hardware and stream endpoints.
- **Revisit Conditions:** None.

### ADR-07: Authentication & Authorization
- **Status:** Accepted
- **Context:** System requires secure authentication and role-based access control (ADMIN and OPERATOR).
- **Decision:** Implement **Argon2id password hashing**, short-lived JWT access tokens, and a database-backed token denylist (`revoked_tokens`) for explicit logout invalidate.
- **Consequences:** High security standards, protection against GPU hash cracking, immediate token revocation upon logout.
- **Revisit Conditions:** Add refresh tokens only if session duration requirements change.

### ADR-08: Attendance Deduplication
- **Status:** Accepted
- **Context:** A student walking past a camera will be recognized across dozens of consecutive frames. Duplicate attendance entries must be prevented.
- **Decision:** Enforce database-level uniqueness `UNIQUE(student_id, attendance_date, session_label)` with `INSERT ... ON CONFLICT DO NOTHING`, combined with an in-memory student cooldown guard (`ATTENDANCE_COOLDOWN_SECONDS=300`).
- **Consequences:** Database is the absolute source of truth; memory guard minimizes database write load.
- **Revisit Conditions:** If multiple distinct lecture periods per day are introduced, extend `session_label` to link to a formal sessions schedule table.

### ADR-09: Movement History Model
- **Status:** Accepted
- **Context:** Movement tracking across campus cameras must be recorded without duplicating detection records.
- **Decision:** **Do NOT create a separate `movement_history` table.** Derive movement sightings dynamically by querying `detection_events` and grouping consecutive same-camera sightings within `SIGHTING_GAP_SECONDS=60`.
- **Consequences:** Single source of truth for detection events, zero data redundancy.
- **Revisit Conditions:** If query latency on millions of events degrades, implement a PostgreSQL materialized view.

### ADR-10: Redis Usage Scope
- **Status:** Accepted
- **Context:** Evaluating when Redis caching and pub/sub should be added to the infrastructure.
- **Decision:** **Do NOT enable Redis before Phase 29.** The core system uses in-memory queues and PostgreSQL. Redis is introduced in Phase 29 for multi-worker scaling and alert deduplication TTL keys.
- **Consequences:** Simplified development infrastructure during MVP phases (0–28).
- **Revisit Conditions:** Phase 29 multi-camera scaling.

### ADR-11: Raw Image Retention
- **Status:** Accepted
- **Context:** Biometric images collected during webcam capture or registration contain sensitive personal data.
- **Decision:** Set `RETAIN_RAW_IMAGES=false` by default. Captured frames exist only in memory during vector extraction and are immediately discarded. Registration uploads are processed transiently.
- **Consequences:** Maximum privacy compliance, minimal disk storage requirement.
- **Revisit Conditions:** If human admin explicitly enables unknown snapshots (`UNKNOWN_SNAPSHOT_ENABLED=true`).

### ADR-12: Identity Search Scope
- **Status:** Accepted
- **Context:** Incoming face embeddings must be matched against both active student embeddings and blacklisted individual embeddings.
- **Decision:** Perform a **single unified vector search pass** over all active embeddings (`is_active=true`). The top-1 vector match decides the target entity type (`STUDENT` or `BLACKLISTED`). If distance exceeds threshold, identity is `UNKNOWN`.
- **Consequences:** Single database index query, optimal performance, no duplicate search logic.
- **Revisit Conditions:** None.

### ADR-13: Embedding Protection
- **Status:** Accepted
- **Context:** Face vectors represent sensitive biometric templates and must be safeguarded.
- **Decision:** Rely on disk encryption (BitLocker) and database security ACLs. **Raw embedding vectors are NEVER returned by any REST API endpoint.**
- **Consequences:** Protects biometric templates against API data leaks.
- **Revisit Conditions:** None.

### ADR-14: Timezone & Date Bounds
- **Status:** Accepted
- **Context:** Attendance dates must respect local timezone day boundaries (e.g. midnight in IST vs UTC).
- **Decision:** Application timezone defaults to `APP_TIMEZONE=Asia/Kolkata`. Database timestamps are stored in UTC (`timestamptz`), while `attendance_date` is calculated in the application timezone.
- **Consequences:** Accurate local calendar date handling regardless of backend server region.
- **Revisit Conditions:** Multi-timezone campus deployments.

### ADR-15: Docker & Webcam Strategy
- **Status:** Accepted
- **Context:** Windows Docker Desktop containers cannot access host laptop webcams easily.
- **Decision:** During MVP development (Phases 0–35), run PostgreSQL+pgvector in Docker container, and run FastAPI backend directly on Windows host OS. Full Docker application deployment (Phase 36) uses RTSP / video file sources.
- **Consequences:** Developer friction eliminated; webcam access works natively on Windows.
- **Revisit Conditions:** Phase 36 production release.

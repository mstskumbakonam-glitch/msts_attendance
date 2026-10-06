# PHASE 0 — REPOSITORY AUDIT REPORT

**Date:** 2026-10-02  
**Repository:** `Aradhya6/smart-attendance-security-system`  
**Auditor:** Antigravity AI Agent  
**Branch:** `chore/phase-00-repo-audit`  
**Git Base Commit:** `08017ba` (`chore: initial repository setup`)  

---

## 1. Current State

The repository currently contains the initial configuration, documentation, container configuration, and dependency manifests for the **Smart Attendance and Security System**.

### Environment & System Diagnostics
- **Operating System:** Windows (PowerShell environment)
- **Python Version on PATH:** `Python 3.14.4` (Note: `.python-version` pins `3.11`; `py -0` lists 3.14 and 3.12. Python 3.11 is required for binary wheel compatibility with AI libraries).
- **Git Version:** `2.53.0.windows.1`
- **Docker / Docker Compose:** `docker` CLI not found on system PATH. Docker Desktop needs to be started or added to PATH before Phase 3.

### Existing Root & Document Structure
```text
C:\Projects\smart-attendance-security-system
├─ .dockerignore
├─ .env.example
├─ .gitignore
├─ .python-version
├─ docker-compose.yml
├─ README.md
├─ requirements.txt
├─ requirements-dev.txt
├─ requirements-gpu.txt
├─ TOKEN-OPTIMIZATION.md
└─ docs/
   ├─ PLAYBOOK.md
   └─ Smart-Attendance-and-Security-System.md
```

---

## 2. Existing Code

- **Application Source Code:** No application code (`backend/`, `app/`, `frontend/`, `src/`, `scripts/`, or `docker/`) exists in the repository yet.
- **Configuration & Setup Files:**
  - `.python-version`: Pins Python `3.11`.
  - `.gitignore`: Standard Python, virtualenv, IDE, cache, database, and model weight ignore rules.
  - `.dockerignore`: Excludes `.venv`, `__pycache__`, `data/`, `faces/`, `uploads/`, `recordings/`, `.git`, and markdown files (except `README.md`).
  - `.env.example`: Template for environment variables (FastAPI, Postgres, Redis, Streamlit, AI models).
  - `docker-compose.yml`: Services defined for `db` (Postgres 16 + pgvector), `redis`, `backend`, `dashboard`, and `video_processor`.
  - `requirements.txt`: Core Python dependencies (FastAPI, SQLAlchemy, pgvector, OpenCV, InsightFace, PyTorch, Streamlit, etc.).
  - `requirements-dev.txt`: Development and testing dependencies (pytest, pytest-asyncio, pytest-cov, flake8, black).
  - `requirements-gpu.txt`: GPU acceleration reference instructions.
- **Documentation:**
  - `docs/PLAYBOOK.md`: Google Antigravity Master Implementation Playbook (Source of Truth for workflow and architecture).
  - `docs/Smart-Attendance-and-Security-System.md`: Functional and technical project specification.
  - `README.md`: Overview, prerequisites, and developer guide.
  - `TOKEN-OPTIMIZATION.md`: AI agent instruction manual and token optimization guidelines.

---

## 3. Missing Modules (Target Layout vs Actual)

Comparing the current repository structure against **Section 3.1 (Repository Layout)** in `docs/PLAYBOOK.md`:

| Module / Directory | Target Path in Playbook | Status | Description / Action Required |
|---|---|---|---|
| **Backend Core** | `backend/app/` | ❌ Missing | Needs FastAPI `main.py`, `core/`, `db/`, `models/`, `schemas/`, `api/v1/`, `services/`, `vision/`, `cameras/`, `events/` |
| **Database Migrations** | `backend/alembic/`, `alembic.ini` | ❌ Missing | Alembic migration framework to be initialized in Phase 4 |
| **Backend Tests** | `backend/tests/` | ❌ Missing | Test suite (unit, integration, db, vision, security) |
| **Frontend** | `frontend/` | ❌ Missing | Streamlit multi-page dashboard (`app.py`, `api_client.py`, `pages/`, `components/`) |
| **Scripts** | `scripts/` | ❌ Missing | Utility scripts (`check_env.py`, `calibrate_threshold.py`, `seed_demo.py`, etc.) |
| **Docker Assets** | `docker/` | ❌ Missing | Postgres init SQL scripts and application Dockerfiles |
| **Architecture Docs** | `docs/architecture/` | ❌ Missing | ADR summary file `docs/architecture/DECISIONS.md` (to be created in Phase 1) |
| **Audit Docs** | `docs/audit/` | 🟡 Created | This report `docs/audit/PHASE0_AUDIT_REPORT.md` |
| **Data Directory** | `data/` | ❌ Missing | Git-ignored directory for transient files (`tmp/`, `videos/`, `snapshots/`) |

---

## 4. Dependency Conflicts & Observations

1. **Python Version Compatibility (`3.14.4` vs `3.11`):**
   - System environment has Python 3.14.4 active.
   - Heavy AI packages (`insightface`, `onnxruntime`, `torch`, `scipy`) lack binary wheels for Python 3.14.
   - **Resolution:** Python 3.11 virtual environment must be created and used for development as specified in `.python-version`.
2. **Password Hashing Library:**
   - `requirements.txt` specifies `passlib[bcrypt]`.
   - `docs/PLAYBOOK.md` ADR-07 specifies **Argon2id** password hashing (`argon2-cffi` / `passlib[argon2]`).
   - **Resolution:** Add `argon2-cffi` to `requirements.txt` in Phase 2/5.
3. **Numpy Version Pinning:**
   - `requirements.txt` pins `numpy>=1.26.0,<2.0.0`. This correctly prevents Numpy 2.x breaking `onnxruntime` and `insightface`.
4. **OpenCV Package Choice:**
   - `requirements.txt` includes `opencv-python-headless`.
   - Headless is ideal for server and Docker deployments; for local GUI debugging, `opencv-python` can be substituted if window displays (`cv2.imshow`) are needed.

---

## 5. Architecture Observations

1. **Monolith vs Microservices Alignment in `docker-compose.yml`:**
   - Playbook ADR-01 and ADR-05 specify a **modular monolith** (`backend/` + `frontend/` Streamlit app).
   - The initial `docker-compose.yml` defines 5 separate microservice containers (`db`, `redis`, `backend`, `dashboard`, `video_processor`).
   - Redis is included in initial compose, but Playbook ADR-10 states Redis is NOT to be introduced before Phase 29.
   - **Action:** In Phase 3, simplify `docker-compose.yml` to focus on PostgreSQL+pgvector infrastructure for local development, matching the modular monolith structure.
2. **Database Credentials & Naming:**
   - `.env.example` and `docker-compose.yml` default to `POSTGRES_USER=postgres` and `POSTGRES_DB=smart_attendance`.
   - Playbook Section 6 specifies `POSTGRES_USER=sas_user` and `POSTGRES_DB=sas_db` with `DATABASE_URL=postgresql+psycopg://sas_user:CHANGE_ME@localhost:5432/sas_db`.

---

## 6. Security and Privacy Risks

1. **`.gitignore` Scope Gaps:**
   - `models/*.onnx` and `models/*.pt` are ignored, but `.onnx` or `.pt` files placed outside `models/` (e.g. root or subfolders) are not covered by root wildcards.
   - Video files (`*.mp4`, `*.avi`, `*.mkv`) are ignored under `recordings/` and `data/`, but not globally.
   - Image files containing biometric faces are ignored under `faces/` and `uploads/`, but wildcard image extensions (`*.jpg`, `*.jpeg`, `*.png`) outside static folders are not explicitly listed.
   - **Action:** Expand `.gitignore` rules to globally exclude model weights, video recordings, and transient face images.
2. **Secrets & Environment Variables:**
   - `.env.example` contains placeholders only (`SECRET_KEY=change_this_to_a_secure_random_string_in_production`). No real secrets or credentials are present in the repo.

---

## 7. Recommended Changes (Prioritised)

1. **Environment Setup (Phase 2):** Install Python 3.11 and create a virtual environment (`.venv`) using Python 3.11.
2. **Docker Service Setup (Phase 3):** Install/start Docker Desktop on Windows. Update `docker-compose.yml` to run `pgvector/pgvector:pg16` with user `sas_user` and database `sas_db`.
3. **Architecture Finalization (Phase 1):** Record ADRs in `docs/architecture/DECISIONS.md` confirming modular monolith design, single AI Vision Engine, and CPU-first execution.
4. **Dependency Alignment (Phase 2):** Add `argon2-cffi` to `requirements.txt` for Argon2id hashing.
5. **Git Hygiene (Phase 0/1):** Add explicit global ignores to `.gitignore` for `*.onnx`, `*.pt`, `*.engine`, `*.mp4`, `*.avi`, `*.mov`, `*.jpg`, `*.png` (except UI assets).

---

## 8. Open Questions

1. Should Python 3.11 be installed via standard Windows installer, `pyenv-win`, or Conda on the developer machine?
2. Will Docker Desktop be used for running PostgreSQL+pgvector in Phase 3, or should native PostgreSQL 16 for Windows + pgvector extension be prepared as an alternative if Docker Desktop is unavailable?

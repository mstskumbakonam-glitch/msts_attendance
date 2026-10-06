# Smart Attendance & Security System

> AI-based smart attendance and campus security system using face recognition and CCTV surveillance.

---

## 1. Project Overview

This system integrates live CCTV video surveillance with face recognition to automate student attendance marking, detect unknown individuals, identify blacklisted persons, issue real-time alerts, and track movement history across campus camera locations.

* **Specification (Source of Truth):** [`docs/Smart-Attendance-and-Security-System.md`](docs/Smart-Attendance-and-Security-System.md)
* **Master Playbook:** [`docs/PLAYBOOK.md`](docs/PLAYBOOK.md)
* **Agent Guidelines & Token Efficiency:** [`TOKEN-OPTIMIZATION.md`](TOKEN-OPTIMIZATION.md)

### System Architecture Documentation
* [System Architecture Overview](docs/architecture/ARCHITECTURE.md)
* [Architecture Decision Records (ADRs)](docs/architecture/DECISIONS.md)
* [Database Design & Schema](docs/architecture/DATABASE.md)
* [REST API Catalog](docs/architecture/API.md)
* [AI Vision Engine Pipeline](docs/architecture/AI_PIPELINE.md)
* [Frontend Streamlit Dashboard](docs/architecture/FRONTEND.md)
* [End-to-End Data Flows](docs/architecture/DATA_FLOW.md)
* [Module Boundaries & Rules](docs/architecture/MODULE_BOUNDARIES.md)

---

## 2. Project Structure

Current repository structure:

```
smart-attendance-security-system/
├── docs/
│   └── Smart-Attendance-and-Security-System.md   # Project specification (Source of Truth)
├── .dockerignore                                 # Docker build ignore rules
├── .env.example                                  # Environment variables template
├── .gitignore                                    # Git ignore rules (env, venv, cache, models)
├── .python-version                               # Python version pin (3.11)
├── docker-compose.yml                            # Infrastructure & service orchestration
├── requirements.txt                              # Core dependencies (FastAPI, Streamlit, CV, CPU ML)
├── requirements-dev.txt                          # Dev & test tools (pytest, pytest-asyncio, black, flake8)
├── requirements-gpu.txt                          # Optional GPU/CUDA acceleration reference
├── TOKEN-OPTIMIZATION.md                         # AI agent instruction manual & token efficiency rules
└── README.md                                     # Team setup and workflow guide
```

---

## 3. Prerequisites

Ensure the following tools are installed on your machine:
* **Python 3.11** (or Conda / Miniconda)
* **Docker Desktop** (or Docker Engine + Docker Compose)
* **Git** (and optionally **GitHub Desktop**)

---

## 4. Environment Installation

### Step 1: Clone Repository
```bash
git clone https://github.com/Aradhya6/smart-attendance-security-system.git
cd smart-attendance-security-system
```

### Step 2: Create & Activate Python 3.11 Environment

Using Conda:
```bash
conda create -n smart-attendance python=3.11 -y
conda activate smart-attendance
```

*(Alternative: standard venv via `python -m venv .venv` and activating it)*

### Step 3: Install Dependencies

`requirements.txt` is the single source for all core application dependencies.

```bash
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

---

## 5. Environment Variables

Create your local `.env` file from the provided template:

**Windows:**
```bash
copy .env.example .env
```

**Linux / macOS:**
```bash
cp .env.example .env
```

> [!IMPORTANT]
> * The `.env` file is **local only**.
> * **Never commit `.env`, credentials, API keys, or secrets to GitHub.** It is automatically ignored by `.gitignore`.

---

## 6. Docker Infrastructure

PostgreSQL 16 + pgvector and Redis are provided through Docker containers. **Do NOT install PostgreSQL directly on Windows.** PostgreSQL must use the official pgvector image (`pgvector/pgvector:pg16`) specified in `docker-compose.yml` to support vector embeddings.

### Start Infrastructure Services
```bash
docker compose up -d db redis
```

### Stop Services
```bash
docker compose down
```

### Reset Data & Volumes (if needed)
```bash
docker compose down -v
```

---

## 7. GPU Configuration

> [!NOTE]
> **PENDING — NVIDIA GPU model has not yet been confirmed.**

* **Do not install `requirements-gpu.txt` yet.**
* The environment defaults to **CPU configuration** for development (`DEVICE=cpu`, `ONNX_PROVIDER=CPUExecutionProvider`, `INSIGHTFACE_MODEL_NAME=buffalo_s`), allowing all team members to build and test immediately without dedicated hardware.
* GPU-specific CUDA installation, PyTorch CUDA builds, ONNX Runtime GPU, model size selection (`buffalo_l`), and Docker GPU pass-through will be finalized after the team confirms the NVIDIA GPU model.

---

## 8. Verification

> **Note:** Only perform container and database verifications after the Docker services have successfully started.

### 1. Verify Python & Core Libraries
```bash
python -c "import torch, cv2, fastapi, streamlit, insightface, pgvector, redis; print('All core libraries imported successfully!')"
```

### 2. Verify Docker Containers
```bash
docker compose ps
```
Verify that the `db` and `redis` services are running and healthy.

### 3. Verify PostgreSQL + pgvector
```bash
docker compose exec db psql -U postgres -d smart_attendance -c "CREATE EXTENSION IF NOT EXISTS vector; SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';"
```
Expected output: A table displaying `vector` and its installed version.

### 4. Verify Redis Cache & Pub/Sub
```bash
docker compose exec redis redis-cli ping
```
Expected output: `PONG`.

---

## 9. Git & Team Workflow

### A. Terminal / Git Command Workflow

1. **Check changes:**
   ```bash
   git status
   ```

2. **Review changes:**
   ```bash
   git diff
   ```

3. **Stage changes:**
   ```bash
   git add .
   ```

4. **Commit changes:**
   ```bash
   git commit -m "Describe your changes"
   ```
   *Example:*
   ```bash
   git commit -m "Add face recognition pipeline"
   ```

5. **Push changes:**
   ```bash
   git push
   ```
   *Note: For the first push of a new feature branch:*
   ```bash
   git push -u origin feature/<feature-name>
   ```

---

### B. Before Starting a New Task

```bash
git checkout main
git pull origin main
git checkout -b feature/<feature-name>
```

*Example:*
```bash
git checkout main
git pull origin main
git checkout -b feature/face-recognition
```

---

### C. Pull Request Workflow

1. Review changes with `git status` and `git diff`.
2. Run `git add .`.
3. Commit with a clear message.
4. Push the feature branch.
5. Open the repository on GitHub.
6. Create a Pull Request from the feature branch into `main`.
7. Request review from a teammate.
8. Merge into `main` only after review and verification.

---

### D. GitHub Desktop Workflow

| Git Operation | GitHub Desktop Action |
|---|---|
| `git status` | View the Changes tab |
| `git diff` | Select a changed file to review the diff |
| `git add .` | Select/check the files under Changes |
| `git commit -m "..."` | Enter commit message → Click Commit to <branch> |
| `git push` | Click Push origin |
| First branch push | Click Publish branch |
| `git pull` | Click Fetch origin → Pull origin |
| Create PR | Click Create Pull Request |

---

## 10. Team Git Rules

### DO:
* Pull the latest `main` before starting a new task.
* Work on a dedicated feature branch.
* Keep commits focused, small, and descriptive.
* Review changes with `git status` and `git diff` before committing.
* Push the feature branch to GitHub.
* Use Pull Requests for merging into `main`.
* Keep the team informed when modifying shared schemas or interfaces.

### DO NOT:
* **DO NOT** commit directly to `main`.
* **DO NOT** force push (`git push -f`).
* **DO NOT** commit `.env` or credentials/API keys.
* **DO NOT** commit model weights (`.pt`, `.onnx`).
* **DO NOT** commit CCTV recordings or video clips.
* **DO NOT** commit captured face images or biometric datasets.
* **DO NOT** overwrite another teammate's work.
* **DO NOT** reset or rebase shared branches without team agreement.


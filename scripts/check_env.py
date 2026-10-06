"""
scripts/check_env.py
====================
Smart Attendance & Security System — Phase 2 environment checker.

Prints a PASS / FAIL / WARN table for every prerequisite.
Exits 0 if all mandatory checks PASS, 1 otherwise.

Usage:
  python scripts/check_env.py            # full check including camera
  python scripts/check_env.py --no-camera  # skip camera (CI / headless)
"""

from __future__ import annotations

import argparse
import importlib
import platform
import subprocess
import sys

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MIN_PYTHON = (3, 11)
MAX_PYTHON = (3, 12)  # exclusive upper bound

GREEN = "\033[92m"
RED   = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"

PASS  = f"{GREEN}PASS{RESET}"
FAIL  = f"{RED}FAIL{RESET}"
WARN  = f"{YELLOW}WARN{RESET}"


# ---------------------------------------------------------------------------
# Result accumulator
# ---------------------------------------------------------------------------
results: list[tuple[str, str, str]] = []   # (check, status, detail)


def record(check: str, status: str, detail: str = "") -> None:
    results.append((check, status, detail))
    tag = {"PASS": PASS, "FAIL": FAIL, "WARN": WARN}.get(status, status)
    print(f"  [{tag}] {check}" + (f" — {detail}" if detail else ""))


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def check_python_version() -> None:
    v = sys.version_info
    if v[:2] >= MIN_PYTHON and v[:2] < MAX_PYTHON:
        record("Python version", "PASS", f"{v.major}.{v.minor}.{v.micro}")
    else:
        record(
            "Python version",
            "FAIL",
            f"Got {v.major}.{v.minor}.{v.micro}, need >=3.11,<3.12",
        )


def check_import(module: str, pip_name: str | None = None) -> None:
    try:
        importlib.import_module(module)
        record(f"import {module}", "PASS")
    except ImportError as exc:
        hint = f"pip install {pip_name or module}"
        record(f"import {module}", "FAIL", f"{exc} — {hint}")


def check_onnxruntime_cpu() -> None:
    try:
        import onnxruntime as ort  # noqa: PLC0415
        providers = ort.get_available_providers()
        if "CPUExecutionProvider" in providers:
            record("onnxruntime CPUExecutionProvider", "PASS", str(providers))
        else:
            record(
                "onnxruntime CPUExecutionProvider",
                "FAIL",
                f"Available: {providers}",
            )
    except Exception as exc:  # noqa: BLE001
        record("onnxruntime CPUExecutionProvider", "FAIL", str(exc))


def check_docker() -> None:
    try:
        out = subprocess.run(
            ["docker", "info", "--format", "{{.ServerVersion}}"],
            capture_output=True, text=True, timeout=8,
        )
        if out.returncode == 0:
            record("Docker daemon", "PASS", out.stdout.strip())
        else:
            record("Docker daemon", "WARN", "docker info failed — Docker may not be running")
    except FileNotFoundError:
        record("Docker daemon", "WARN", "docker not found — install Docker Desktop")
    except Exception as exc:  # noqa: BLE001
        record("Docker daemon", "WARN", str(exc))


def check_docker_compose() -> None:
    for cmd in (["docker", "compose", "version"], ["docker-compose", "--version"]):
        try:
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=8)
            if out.returncode == 0:
                record("Docker Compose", "PASS", out.stdout.strip()[:80])
                return
        except FileNotFoundError:
            continue
        except Exception:  # noqa: BLE001
            continue
    record("Docker Compose", "WARN", "docker compose not found")


def check_camera(no_camera: bool) -> None:
    if no_camera:
        record("Webcam", "WARN", "--no-camera flag set; skipped")
        return
    try:
        import cv2  # noqa: PLC0415
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cap.isOpened():
            record("Webcam", "WARN", "cv2.VideoCapture(0) failed to open")
            return
        ret, frame = cap.read()
        cap.release()
        if ret and frame is not None:
            h, w = frame.shape[:2]
            record("Webcam", "PASS", f"{w}×{h} frame captured")
        else:
            record("Webcam", "WARN", "Camera opened but no frame returned")
    except Exception as exc:  # noqa: BLE001
        record("Webcam", "WARN", str(exc))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Smart-Attendance environment checker")
    parser.add_argument(
        "--no-camera",
        action="store_true",
        help="Skip webcam check (useful for headless / CI environments)",
    )
    args = parser.parse_args()

    print("\nSmart Attendance & Security System — Environment Check")
    print(f"Python: {sys.version}")
    print(f"Platform: {platform.platform()}")
    print("-" * 60)

    # 1. Python version
    check_python_version()

    # 2. Critical runtime imports
    import_checks = [
        ("cv2",          "opencv-python"),
        ("numpy",        "numpy"),
        ("onnxruntime",  "onnxruntime"),
        ("insightface",  "insightface"),
        ("fastapi",      "fastapi"),
        ("sqlalchemy",   "sqlalchemy"),
        ("psycopg",      "psycopg[binary]"),
        ("pgvector",     "pgvector"),
        ("streamlit",    "streamlit"),
        ("pydantic",     "pydantic"),
        ("alembic",      "alembic"),
        ("redis",        "redis"),
        ("httpx",        "httpx"),
        ("slowapi",      "slowapi"),
        ("passlib",      "passlib[bcrypt]"),
        ("psutil",       "psutil"),
        ("pandas",       "pandas"),
        ("plotly",       "plotly"),
    ]
    for mod, pip in import_checks:
        check_import(mod, pip)

    # 3. ONNX CPU provider
    check_onnxruntime_cpu()

    # 4. Docker
    check_docker()
    check_docker_compose()

    # 5. Camera (optional skip)
    check_camera(args.no_camera)

    # ---------------------------------------------------------------------------
    # Summary
    # ---------------------------------------------------------------------------
    print("-" * 60)
    total   = len(results)
    passed  = sum(1 for _, s, _ in results if s == "PASS")
    failed  = sum(1 for _, s, _ in results if s == "FAIL")
    warned  = sum(1 for _, s, _ in results if s == "WARN")

    print(f"\nSummary: {passed}/{total} PASS | {warned} WARN | {failed} FAIL\n")

    if failed > 0:
        print(f"{RED}ENVIRONMENT INCOMPLETE — fix FAIL items before proceeding.{RESET}")
        return 1
    if warned > 0:
        print(f"{YELLOW}ENVIRONMENT READY WITH WARNINGS — review WARN items.{RESET}")
        return 0
    print(f"{GREEN}ENVIRONMENT OK — all checks passed.{RESET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

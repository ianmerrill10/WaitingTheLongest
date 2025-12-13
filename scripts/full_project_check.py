#!/usr/bin/env python3
"""
Full Project Check - Run all validation checks in one command.

Usage:
    python scripts/full_project_check.py [--with-docker]

Runs:
    - File inventory generation
    - Scheduled tests (pytest)
    - Import validation for key modules
    - Docker build (optional)
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"


@dataclass
class CheckResult:
    name: str
    ok: bool
    message: str


def _python_exe() -> str:
    venv_python = BACKEND_DIR / ".venv" / "Scripts" / "python.exe"
    if venv_python.exists():
        return str(venv_python)
    venv_python_unix = BACKEND_DIR / ".venv" / "bin" / "python"
    if venv_python_unix.exists():
        return str(venv_python_unix)
    return sys.executable


def run_check(name: str, cmd: list[str], cwd: Path | None = None) -> CheckResult:
    """Run a check command and return result."""
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=300,
        )
        ok = proc.returncode == 0
        message = "passed" if ok else f"failed (exit={proc.returncode})"
        return CheckResult(name=name, ok=ok, message=message)
    except subprocess.TimeoutExpired:
        return CheckResult(name=name, ok=False, message="timeout")
    except Exception as e:
        return CheckResult(name=name, ok=False, message=str(e))


def check_imports() -> CheckResult:
    """Verify key modules import successfully."""
    py = _python_exe()
    imports = [
        "from app.main import app",
        "from ingestors.rescuegroups import RescueGroupsIngestor",
        "from workers.scheduler import IngestionWorker",
        "from tools.video_generator import SocialVideoGenerator",
    ]
    for imp in imports:
        proc = subprocess.run(
            [py, "-c", imp],
            cwd=str(BACKEND_DIR),
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            return CheckResult(name="imports", ok=False, message=f"failed: {imp}")
    return CheckResult(name="imports", ok=True, message="all key modules import OK")


def main() -> int:
    parser = argparse.ArgumentParser(description="Full project check")
    parser.add_argument("--with-docker", action="store_true", help="Include Docker build check")
    args = parser.parse_args()

    py = _python_exe()
    results: list[CheckResult] = []

    print("=" * 60)
    print("FULL PROJECT CHECK")
    print("=" * 60)

    # 1. File inventory
    print("\n[1/5] Generating file inventory...")
    results.append(run_check(
        "inventory",
        [py, "backend/tools/file_inventory.py"],
        cwd=PROJECT_ROOT,
    ))

    # 2. Key imports
    print("[2/5] Checking module imports...")
    results.append(check_imports())

    # 3. Pytest
    print("[3/5] Running tests...")
    results.append(run_check(
        "tests",
        [py, "-m", "pytest", "-q"],
        cwd=BACKEND_DIR,
    ))

    # 4. Launch all agents (cross-platform check)
    print("[4/5] Running agent orchestrator check...")
    results.append(run_check(
        "agents",
        [py, "scripts/launch_all_agents.py", "--report-only"],
        cwd=PROJECT_ROOT,
    ))

    # 5. Docker build (optional)
    if args.with_docker:
        print("[5/5] Building Docker image...")
        results.append(run_check(
            "docker",
            ["docker", "build", "-t", "wtl-check:local", "-f", "backend/Dockerfile", "backend"],
            cwd=PROJECT_ROOT,
        ))
    else:
        print("[5/5] Docker build skipped (use --with-docker to include)")

    # Summary
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    
    all_ok = True
    for r in results:
        icon = "✅" if r.ok else "❌"
        print(f"{icon} {r.name}: {r.message}")
        if not r.ok:
            all_ok = False

    print("=" * 60)
    if all_ok:
        print("✅ ALL CHECKS PASSED")
    else:
        print("❌ SOME CHECKS FAILED")
    print("=" * 60)

    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

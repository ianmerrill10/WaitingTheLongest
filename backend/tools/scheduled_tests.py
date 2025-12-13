from __future__ import annotations

import subprocess
import sys
import os
import shlex
from pathlib import Path
from typing import List

from testing_ledger import append_testing_log_entry, update_file_entry


def _backend_dir() -> Path:
    # backend/tools/scheduled_tests.py -> backend
    return Path(__file__).resolve().parents[1]


def run_pytest(args: List[str]) -> dict:
    cmd = [sys.executable, "-m", "pytest", *args]
    proc = subprocess.run(
        cmd,
        cwd=str(_backend_dir()),
        capture_output=True,
        text=True,
    )

    return {
        "command": " ".join(cmd),
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def main() -> int:
    # Resolve args in priority order:
    # 1) CLI args passed to this module
    # 2) env var SCHEDULED_TESTS_ARGS
    # 3) app.config.settings.SCHEDULED_TESTS_ARGS (if importable)
    # 4) default suite

    if len(sys.argv) > 1:
        args = sys.argv[1:]
    else:
        cfg = os.environ.get("SCHEDULED_TESTS_ARGS")
        if not cfg:
            try:
                from app.config import settings  # type: ignore
                cfg = getattr(settings, "SCHEDULED_TESTS_ARGS", "")
            except Exception:
                cfg = ""

        # Default: run the full backend suite quietly.
        args = shlex.split(cfg) if cfg else ["-q"]

    # Provide safe defaults so this works in clean environments (CI/local)
    os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
    os.environ.setdefault("SECRET_KEY", "scheduled-tests")

    result = run_pytest(args)

    ok = result["returncode"] == 0
    scope = " ".join(args) if args else "(default)"
    title = "Scheduled pytest run"
    append_testing_log_entry(
        title,
        [
            f"Scope: {scope}",
            f"Command: `{result['command']}`",
            f"Result: {'PASS' if ok else 'FAIL'} (exit={result['returncode']})",
            "Stdout/Stderr captured in worker logs (not embedded here by default).",
        ],
    )

    # Record the run against the backend test suite (or a specific file if provided).
    recorded_target = "backend/tests"
    for token in reversed(args):
        if token.endswith(".py") and (token.startswith("tests/") or token.startswith("backend/tests/")):
            recorded_target = "backend/" + token if token.startswith("tests/") else token
            break

    update_file_entry(
        recorded_target,
        status="pass" if ok else "fail",
        test_command=result["command"],
        notes="Scheduled run" if ok else "Scheduled run failed; check logs/artifacts.",
    )

    if not ok:
        # Emit a short failure snippet for CI readability.
        tail = (result.get("stdout") or "")[-2000:]
        if tail.strip():
            print(tail)

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

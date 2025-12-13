from __future__ import annotations

import argparse
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"


@dataclass
class JobResult:
    name: str
    ok: bool
    returncode: int
    stdout: str
    stderr: str


def _python_exe() -> str:
    venv_python = BACKEND_DIR / ".venv" / "Scripts" / "python.exe"
    if venv_python.exists():
        return str(venv_python)
    return sys.executable


def _run(name: str, cmd: list[str], cwd: Path | None = None) -> JobResult:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
    )
    return JobResult(
        name=name,
        ok=proc.returncode == 0,
        returncode=proc.returncode,
        stdout=proc.stdout,
        stderr=proc.stderr,
    )


def job_inventory() -> JobResult:
    py = _python_exe()
    return _run(
        "inventory",
        [py, "backend/tools/file_inventory.py"],
        cwd=PROJECT_ROOT,
    )


def job_scheduled_tests(pytest_args: str | None) -> JobResult:
    py = _python_exe()
    cmd = [py, "backend/tools/scheduled_tests.py"]
    if pytest_args:
        cmd.extend(pytest_args.split())
    return _run("tests", cmd, cwd=PROJECT_ROOT)


def job_docker_build() -> JobResult:
    return _run(
        "docker-build",
        [
            "docker",
            "build",
            "-t",
            "waitingthelongest-backend:local",
            "-f",
            "backend/Dockerfile",
            "backend",
        ],
        cwd=PROJECT_ROOT,
    )


def run_jobs(jobs: Iterable[tuple[str, callable]]) -> int:
    results: list[JobResult] = []

    with ThreadPoolExecutor(max_workers=3) as pool:
        futs = [pool.submit(fn) for _, fn in jobs]
        for fut in as_completed(futs):
            results.append(fut.result())

    results.sort(key=lambda r: r.name)

    print("\n=== Parallel run summary ===")
    exit_code = 0
    for r in results:
        status = "OK" if r.ok else "FAIL"
        print(f"- {r.name}: {status} (exit={r.returncode})")
        if not r.ok:
            exit_code = 1

    # Keep output short; show tails for failures.
    for r in results:
        if not r.ok:
            out_tail = (r.stdout or "")[-1200:]
            err_tail = (r.stderr or "")[-1200:]
            print(f"\n--- {r.name} stdout (tail) ---\n{out_tail}")
            print(f"\n--- {r.name} stderr (tail) ---\n{err_tail}")

    return exit_code


def main() -> int:
    parser = argparse.ArgumentParser(description="Run multiple project checks in parallel")
    parser.add_argument(
        "--with-docker",
        action="store_true",
        help="Also run a local Docker build (slower).",
    )
    parser.add_argument(
        "--pytest-args",
        default=None,
        help="Optional pytest args to pass through to scheduled_tests.py (e.g. '-q tests/test_api.py').",
    )
    args = parser.parse_args()

    jobs: list[tuple[str, callable]] = []
    jobs.append(("inventory", job_inventory))
    jobs.append(("tests", lambda: job_scheduled_tests(args.pytest_args)))
    if args.with_docker:
        jobs.append(("docker-build", job_docker_build))

    return run_jobs(jobs)


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""
===============================================================================
Waiting The Longest™ - Continuous Integration Script
===============================================================================
Purpose: Run all CI checks locally before pushing. Mirrors what GitHub Actions
         will run, helping catch issues before they hit CI.

Usage:
    python scripts/ci.py           # Run all checks
    python scripts/ci.py --quick   # Quick checks only (no Docker)
    python scripts/ci.py --fix     # Auto-fix what we can

Exit codes:
    0 = All checks passed
    1 = Some checks failed

Author: Waiting The Longest™ Development Team
===============================================================================
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple


def get_project_root() -> Path:
    return Path(__file__).parent.parent


def get_backend_dir() -> Path:
    return get_project_root() / "backend"


def get_venv_python() -> str:
    backend_dir = get_backend_dir()
    if sys.platform == "win32":
        return str(backend_dir / ".venv" / "Scripts" / "python.exe")
    return str(backend_dir / ".venv" / "bin" / "python")


def run_check(name: str, cmd: List[str], cwd: Path = None, allow_fail: bool = False) -> Tuple[bool, str]:
    """Run a check and return (success, output)."""
    print(f"\n{'='*60}")
    print(f"🔍 {name}")
    print(f"{'='*60}")
    print(f"   Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True
        )
        
        output = result.stdout + result.stderr
        success = result.returncode == 0
        
        if success:
            print(f"   ✅ PASSED")
        else:
            print(f"   ❌ FAILED (exit code {result.returncode})")
            if output.strip():
                # Show last few lines of output
                lines = output.strip().split('\n')
                for line in lines[-10:]:
                    print(f"      {line}")
        
        return success or allow_fail, output
        
    except FileNotFoundError:
        print(f"   ⚠️  SKIPPED (command not found)")
        return allow_fail, ""
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        return allow_fail, str(e)


def main():
    parser = argparse.ArgumentParser(
        description="Run CI checks locally"
    )
    parser.add_argument(
        "--quick", "-q",
        action="store_true",
        help="Quick mode - skip slow checks"
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Auto-fix issues where possible"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show full output"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🔬 Waiting The Longest™ - CI Checks")
    print("=" * 60)
    
    python = get_venv_python()
    backend = get_backend_dir()
    project = get_project_root()
    
    results = []
    
    # 1. Python syntax check
    results.append(run_check(
        "Python Syntax Check",
        [python, "-m", "py_compile", "app/main.py"],
        cwd=backend
    ))
    
    # 2. Import check
    results.append(run_check(
        "Import Verification",
        [python, "-c", "from app.main import app; print('Imports OK')"],
        cwd=backend
    ))
    
    # 3. Black formatting
    if args.fix:
        results.append(run_check(
            "Black Formatting (fix)",
            [python, "-m", "black", "app/", "tools/", "tests/", "--line-length=100"],
            cwd=backend,
            allow_fail=True
        ))
    else:
        results.append(run_check(
            "Black Formatting (check)",
            [python, "-m", "black", "app/", "tools/", "tests/", "--check", "--line-length=100"],
            cwd=backend,
            allow_fail=True
        ))
    
    # 4. isort import sorting
    if args.fix:
        results.append(run_check(
            "isort Import Sorting (fix)",
            [python, "-m", "isort", "app/", "tools/", "tests/", "--profile=black"],
            cwd=backend,
            allow_fail=True
        ))
    else:
        results.append(run_check(
            "isort Import Sorting (check)",
            [python, "-m", "isort", "app/", "tools/", "tests/", "--check", "--profile=black"],
            cwd=backend,
            allow_fail=True
        ))
    
    # 5. Flake8 linting
    results.append(run_check(
        "Flake8 Linting",
        [python, "-m", "flake8", "app/", "--max-line-length=100", "--extend-ignore=E203,E501,W503"],
        cwd=backend,
        allow_fail=True
    ))
    
    # 6. Pytest
    results.append(run_check(
        "Pytest (all tests)",
        [python, "-m", "pytest", "-q", "--tb=short"],
        cwd=backend
    ))
    
    # 7. API smoke test (quick server start)
    if not args.quick:
        results.append(run_check(
            "API Import Test",
            [python, "-c", """
import sys
sys.path.insert(0, '.')
from app.main import app
from app.database import get_db
from app.models import Animal, Observation, Shelter
print('All models and app loaded successfully')
"""],
            cwd=backend
        ))
    
    # 8. Docker build (skip in quick mode)
    if not args.quick:
        dockerfile = project / "Dockerfile"
        if dockerfile.exists():
            results.append(run_check(
                "Docker Build",
                ["docker", "build", "-t", "wtl-test", "."],
                cwd=project,
                allow_fail=True
            ))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 CI Results Summary")
    print("=" * 60)
    
    passed = sum(1 for success, _ in results if success)
    total = len(results)
    
    print(f"\n   Passed: {passed}/{total}")
    
    if passed == total:
        print("\n   🎉 All checks passed!")
        return 0
    else:
        print(f"\n   ⚠️  {total - passed} check(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())

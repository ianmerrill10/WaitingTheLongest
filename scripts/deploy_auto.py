#!/usr/bin/env python3
"""
===============================================================================
Waiting The Longest™ - Deployment Automation Script
===============================================================================
Purpose: Automate deployment to various environments (local, staging, production).
         Handles pre-flight checks, database migrations, and health verification.

Usage:
    python scripts/deploy.py local        # Deploy locally
    python scripts/deploy.py staging      # Deploy to staging
    python scripts/deploy.py production   # Deploy to production
    python scripts/deploy.py --check      # Run pre-flight checks only

Author: Waiting The Longest™ Development Team
===============================================================================
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional
import urllib.request
import json


def get_project_root() -> Path:
    return Path(__file__).parent.parent


def run_command(cmd: list, cwd: Path = None, check: bool = True) -> tuple:
    """Run a command and return (success, output)."""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd or get_project_root(),
            capture_output=True,
            text=True,
            check=check
        )
        return True, result.stdout + result.stderr
    except subprocess.CalledProcessError as e:
        return False, e.stdout + e.stderr
    except Exception as e:
        return False, str(e)


def print_step(step: str, status: str = ""):
    """Print a deployment step."""
    icons = {
        "start": "🔄",
        "success": "✅",
        "fail": "❌",
        "skip": "⏭️",
        "warn": "⚠️",
    }
    icon = icons.get(status, "▶️")
    print(f"  {icon} {step}")


def check_prerequisites() -> bool:
    """Check that all prerequisites are met."""
    print("\n📋 Pre-flight Checks")
    print("-" * 40)
    
    checks_passed = True
    
    # Check Python version
    print_step("Python version", "start")
    if sys.version_info >= (3, 10):
        print_step(f"Python {sys.version_info.major}.{sys.version_info.minor}", "success")
    else:
        print_step("Python 3.10+ required", "fail")
        checks_passed = False
    
    # Check virtual environment
    print_step("Virtual environment", "start")
    venv_path = get_project_root() / "backend" / ".venv"
    if venv_path.exists():
        print_step("Virtual environment found", "success")
    else:
        print_step("Virtual environment not found", "warn")
    
    # Check Docker
    print_step("Docker availability", "start")
    success, _ = run_command(["docker", "--version"], check=False)
    if success:
        print_step("Docker available", "success")
    else:
        print_step("Docker not available", "warn")
    
    # Check git status
    print_step("Git status", "start")
    success, output = run_command(["git", "status", "--porcelain"], check=False)
    if success and not output.strip():
        print_step("Working directory clean", "success")
    else:
        print_step("Uncommitted changes detected", "warn")
    
    # Run tests
    print_step("Running tests", "start")
    backend_dir = get_project_root() / "backend"
    venv_python = backend_dir / ".venv" / ("Scripts" if sys.platform == "win32" else "bin") / "python"
    
    if venv_python.exists():
        success, output = run_command(
            [str(venv_python), "-m", "pytest", "-q", "--tb=no"],
            cwd=backend_dir,
            check=False
        )
        if success and "passed" in output:
            print_step("All tests passed", "success")
        else:
            print_step("Some tests failed", "fail")
            checks_passed = False
    else:
        print_step("Tests skipped (no venv)", "skip")
    
    return checks_passed


def deploy_local():
    """Deploy locally using Docker Compose."""
    print("\n🏠 Local Deployment")
    print("-" * 40)
    
    # Build and start containers
    print_step("Building containers", "start")
    success, output = run_command(["docker-compose", "build"])
    if not success:
        print_step("Build failed", "fail")
        print(output)
        return False
    print_step("Containers built", "success")
    
    print_step("Starting services", "start")
    success, output = run_command(["docker-compose", "up", "-d"])
    if not success:
        print_step("Failed to start services", "fail")
        print(output)
        return False
    print_step("Services started", "success")
    
    # Wait for health check
    print_step("Waiting for health check", "start")
    time.sleep(5)
    
    if verify_health("http://localhost:8000/health"):
        print_step("Application healthy", "success")
    else:
        print_step("Health check failed", "fail")
        return False
    
    print("\n🎉 Local deployment complete!")
    print("   API: http://localhost:8000/api/docs")
    print("   Frontend: http://localhost:3000")
    
    return True


def deploy_staging():
    """Deploy to staging environment."""
    print("\n🔬 Staging Deployment")
    print("-" * 40)
    
    # Build Docker image
    print_step("Building Docker image", "start")
    success, output = run_command([
        "docker", "build",
        "-t", "waitingthelongest:staging",
        "."
    ])
    if not success:
        print_step("Build failed", "fail")
        return False
    print_step("Image built", "success")
    
    # Tag for registry
    print_step("Tagging for registry", "start")
    registry = "your-registry.com"  # Configure this
    success, _ = run_command([
        "docker", "tag",
        "waitingthelongest:staging",
        f"{registry}/waitingthelongest:staging"
    ])
    print_step("Image tagged", "success")
    
    print("\n📝 Next steps for staging:")
    print("   1. Push image: docker push {registry}/waitingthelongest:staging")
    print("   2. Update AWS App Runner / ECS service")
    print("   3. Verify staging URL")
    
    return True


def deploy_production():
    """Deploy to production environment."""
    print("\n🚀 Production Deployment")
    print("-" * 40)
    
    # Extra confirmation for production
    print("\n⚠️  You are about to deploy to PRODUCTION!")
    confirm = input("   Type 'yes' to confirm: ")
    if confirm.lower() != "yes":
        print("   Deployment cancelled.")
        return False
    
    # Create backup first
    print_step("Creating backup", "start")
    backup_script = get_project_root() / "scripts" / "backup.py"
    if backup_script.exists():
        success, _ = run_command([sys.executable, str(backup_script)])
        if success:
            print_step("Backup created", "success")
        else:
            print_step("Backup failed", "warn")
    
    # Build production image
    print_step("Building production image", "start")
    success, output = run_command([
        "docker", "build",
        "-t", "waitingthelongest:latest",
        "-t", f"waitingthelongest:{get_git_sha()[:8]}",
        "."
    ])
    if not success:
        print_step("Build failed", "fail")
        return False
    print_step("Image built", "success")
    
    print("\n📝 Next steps for production:")
    print("   1. Push image to registry")
    print("   2. Update production service")
    print("   3. Monitor logs and metrics")
    print("   4. Verify health endpoints")
    
    return True


def get_git_sha() -> str:
    """Get current git commit SHA."""
    success, output = run_command(["git", "rev-parse", "HEAD"], check=False)
    return output.strip() if success else "unknown"


def verify_health(url: str, retries: int = 5) -> bool:
    """Verify application health endpoint."""
    for i in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                data = json.loads(response.read().decode())
                if data.get("status") == "healthy" or data.get("database") == "healthy":
                    return True
        except Exception as e:
            if i < retries - 1:
                time.sleep(2)
    return False


def main():
    parser = argparse.ArgumentParser(
        description="Deploy Waiting The Longest to various environments"
    )
    parser.add_argument(
        "environment",
        nargs="?",
        choices=["local", "staging", "production"],
        default="local",
        help="Target environment"
    )
    parser.add_argument(
        "--check", "-c",
        action="store_true",
        help="Run pre-flight checks only"
    )
    parser.add_argument(
        "--skip-checks",
        action="store_true",
        help="Skip pre-flight checks"
    )
    
    args = parser.parse_args()
    
    print("\n" + "=" * 60)
    print("🚀 Waiting The Longest™ - Deployment Automation")
    print("=" * 60)
    
    # Run pre-flight checks
    if not args.skip_checks:
        checks_passed = check_prerequisites()
        
        if args.check:
            print("\n" + ("✅ All checks passed!" if checks_passed else "❌ Some checks failed"))
            sys.exit(0 if checks_passed else 1)
        
        if not checks_passed and args.environment == "production":
            print("\n❌ Cannot deploy to production with failing checks")
            sys.exit(1)
    
    # Deploy to target environment
    deployers = {
        "local": deploy_local,
        "staging": deploy_staging,
        "production": deploy_production,
    }
    
    success = deployers[args.environment]()
    
    print("\n" + "=" * 60)
    if success:
        print(f"✅ Deployment to {args.environment} complete!")
    else:
        print(f"❌ Deployment to {args.environment} failed!")
    print("=" * 60 + "\n")
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

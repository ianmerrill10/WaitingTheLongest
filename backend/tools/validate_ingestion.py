#!/usr/bin/env python3
"""
Ingestion Validation Script - Dry-run and validate ingestion setup.

Usage:
    python backend/tools/validate_ingestion.py [--dry-run]

Checks:
    - RescueGroups API key is configured
    - API is reachable
    - Response parsing works
    - Database connection works
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure backend/ is on path
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def check_api_key() -> tuple[bool, str]:
    """Check if RescueGroups API key is configured."""
    try:
        from app.config import settings
        key = settings.RESCUEGROUPS_API_KEY
        if key and key != "your-rescuegroups-api-key":
            return True, f"API key configured (ends with ...{key[-4:]})"
        return False, "API key not configured or is placeholder"
    except Exception as e:
        return False, f"Error loading config: {e}"


def check_api_reachable() -> tuple[bool, str]:
    """Check if RescueGroups API is reachable."""
    try:
        import requests
        resp = requests.get("https://api.rescuegroups.org", timeout=10)
        return True, f"API reachable (status={resp.status_code})"
    except Exception as e:
        return False, f"API not reachable: {e}"


def check_database() -> tuple[bool, str]:
    """Check database connection."""
    try:
        from app.database import SessionLocal
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        return True, "Database connection OK"
    except Exception as e:
        return False, f"Database error: {e}"


def check_ingestor_import() -> tuple[bool, str]:
    """Check if ingestor module imports."""
    try:
        from ingestors.rescuegroups import RescueGroupsIngestor
        return True, "Ingestor module imports OK"
    except Exception as e:
        return False, f"Import error: {e}"


def dry_run_fetch() -> tuple[bool, str]:
    """Attempt a minimal API fetch (dry run)."""
    try:
        from ingestors.rescuegroups import RescueGroupsIngestor
        ingestor = RescueGroupsIngestor()
        
        if not ingestor.api_key:
            return False, "Cannot dry-run: API key not configured"
        
        # Try fetching just 1 animal
        animals = ingestor.fetch_animals(species="Dog", limit=1)
        if animals:
            return True, f"Dry run OK: fetched {len(animals)} animal(s)"
        return True, "Dry run OK: no animals returned (may be API limit or filter)"
    except Exception as e:
        return False, f"Dry run failed: {e}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate ingestion setup")
    parser.add_argument("--dry-run", action="store_true", help="Attempt a minimal API fetch")
    args = parser.parse_args()

    print("=" * 60)
    print("INGESTION VALIDATION")
    print("=" * 60)

    checks = [
        ("API Key", check_api_key),
        ("Database", check_database),
        ("Ingestor Import", check_ingestor_import),
        ("API Reachable", check_api_reachable),
    ]

    if args.dry_run:
        checks.append(("Dry Run Fetch", dry_run_fetch))

    all_ok = True
    for name, check_fn in checks:
        ok, msg = check_fn()
        icon = "✅" if ok else "❌"
        print(f"{icon} {name}: {msg}")
        if not ok:
            all_ok = False

    print("=" * 60)
    if all_ok:
        print("✅ Ingestion setup is valid")
    else:
        print("⚠️  Some checks failed - review above")
    print("=" * 60)

    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

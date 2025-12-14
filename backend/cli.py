"""
Waiting The Longest™ - Admin CLI Tools
========================================
Command-line tools for administration.
"""

import argparse
import sys
import os
from typing import Optional


def add_demo_data(count: int = 50) -> None:
    """Add demo/test data to the database."""
    print(f"Adding {count} demo animals...")
    
    # Import here to avoid circular imports
    from backend.app.database import SessionLocal
    from backend.tools.seed_data import seed_all
    
    db = SessionLocal()
    try:
        stats = seed_all(db)
        print(f"✓ Added demo data:")
        for key, value in stats.items():
            print(f"  - {key}: {value}")
    finally:
        db.close()


def cleanup_stale_data(days: int = 90) -> None:
    """Remove stale/orphaned data."""
    print(f"Cleaning up data older than {days} days...")
    
    from backend.app.database import SessionLocal
    from backend.app import models
    from datetime import datetime, timedelta
    
    db = SessionLocal()
    try:
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        # Remove old animals not updated
        old_animals = db.query(models.Animal).filter(
            models.Animal.updated_at < cutoff,
            models.Animal.is_adopted == True,
        ).all()
        
        count = len(old_animals)
        for animal in old_animals:
            db.delete(animal)
        
        db.commit()
        print(f"✓ Removed {count} old adopted animals")
    finally:
        db.close()


def run_migrations() -> None:
    """Run database migrations."""
    print("Running database migrations...")
    
    from backend.app.database import SessionLocal, engine
    from backend.tools.migrations import MigrationManager
    
    db = SessionLocal()
    try:
        manager = MigrationManager(engine)
        applied = manager.apply_pending()
        
        if applied:
            print(f"✓ Applied {len(applied)} migrations:")
            for name in applied:
                print(f"  - {name}")
        else:
            print("✓ No pending migrations")
    finally:
        db.close()


def check_health() -> None:
    """Check application health."""
    print("Checking application health...")
    
    from backend.app.health import HealthChecker
    
    checker = HealthChecker()
    result = checker.full_check()
    
    status = result["status"]
    emoji = "✓" if status == "healthy" else "✗"
    
    print(f"{emoji} Overall status: {status}")
    
    for name, check in result.get("checks", {}).items():
        check_emoji = "✓" if check.get("status") == "healthy" else "✗"
        print(f"  {check_emoji} {name}: {check.get('status')}")
        if check.get("error"):
            print(f"      Error: {check['error']}")


def export_data(format: str = "json", output: Optional[str] = None) -> None:
    """Export animal data."""
    print(f"Exporting data as {format}...")
    
    from backend.app.database import SessionLocal
    from backend.app import models, crud
    from backend.tools.export_utils import DataExporter
    
    db = SessionLocal()
    try:
        animals = crud.get_animals(db, limit=10000)
        exporter = DataExporter()
        
        if format == "json":
            data = exporter.export_json(animals)
        elif format == "csv":
            data = exporter.export_csv(animals)
        else:
            print(f"Unknown format: {format}")
            return
        
        if output:
            with open(output, "w") as f:
                f.write(data)
            print(f"✓ Exported to {output}")
        else:
            print(data)
    finally:
        db.close()


def run_ingestor(source: str = "rescuegroups", dry_run: bool = False) -> None:
    """Run a data ingestor."""
    print(f"Running {source} ingestor (dry_run={dry_run})...")
    
    if source == "rescuegroups":
        from backend.ingestors.rescuegroups import RescueGroupsIngestor
        from backend.app.database import SessionLocal
        
        db = SessionLocal()
        try:
            ingestor = RescueGroupsIngestor()
            result = ingestor.run(db, dry_run=dry_run)
            
            print(f"✓ Ingestor completed:")
            print(f"  - Added: {result.get('added', 0)}")
            print(f"  - Updated: {result.get('updated', 0)}")
            print(f"  - Errors: {result.get('errors', 0)}")
        finally:
            db.close()
    else:
        print(f"Unknown ingestor: {source}")


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Waiting The Longest™ Admin CLI",
        prog="wtl-admin",
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Demo data command
    demo_parser = subparsers.add_parser("add-demo", help="Add demo data")
    demo_parser.add_argument(
        "--count", "-c", type=int, default=50,
        help="Number of animals to add",
    )
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser("cleanup", help="Clean up stale data")
    cleanup_parser.add_argument(
        "--days", "-d", type=int, default=90,
        help="Days threshold for stale data",
    )
    
    # Migrations command
    subparsers.add_parser("migrate", help="Run database migrations")
    
    # Health check command
    subparsers.add_parser("health", help="Check application health")
    
    # Export command
    export_parser = subparsers.add_parser("export", help="Export animal data")
    export_parser.add_argument(
        "--format", "-f", choices=["json", "csv"], default="json",
        help="Export format",
    )
    export_parser.add_argument(
        "--output", "-o", type=str,
        help="Output file path",
    )
    
    # Ingest command
    ingest_parser = subparsers.add_parser("ingest", help="Run data ingestor")
    ingest_parser.add_argument(
        "--source", "-s", default="rescuegroups",
        help="Ingestor source",
    )
    ingest_parser.add_argument(
        "--dry-run", action="store_true",
        help="Dry run mode (no database changes)",
    )
    
    args = parser.parse_args()
    
    if args.command == "add-demo":
        add_demo_data(args.count)
    elif args.command == "cleanup":
        cleanup_stale_data(args.days)
    elif args.command == "migrate":
        run_migrations()
    elif args.command == "health":
        check_health()
    elif args.command == "export":
        export_data(args.format, args.output)
    elif args.command == "ingest":
        run_ingestor(args.source, args.dry_run)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

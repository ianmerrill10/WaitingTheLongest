#!/usr/bin/env python3
"""
===============================================================================
Waiting The Longest™ - Database Seeding CLI
===============================================================================
Purpose: Command-line interface for database operations including seeding
         demo data, clearing data, and database migrations.

Usage:
    python scripts/db_seed.py demo      # Seed demo data
    python scripts/db_seed.py clear     # Clear all data
    python scripts/db_seed.py reset     # Clear and re-seed
    python scripts/db_seed.py status    # Show database status
    python scripts/db_seed.py migrate   # Run migrations (if using Alembic)

Author: Waiting The Longest™ Development Team
===============================================================================
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime

# Ensure backend directory is on path
BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def get_db_session():
    """Get a database session."""
    from app.database import SessionLocal
    return SessionLocal()


def seed_demo_data():
    """Seed the database with demo data."""
    print("🌱 Seeding demo data...")
    
    try:
        # Import and run the demo data generator
        from tools.generate_demo_data import generate_demo_data
        generate_demo_data()
        print("✅ Demo data seeded successfully!")
        return True
    except Exception as e:
        print(f"❌ Error seeding demo data: {e}")
        return False


def clear_all_data():
    """Clear all data from the database (preserves schema)."""
    print("🗑️  Clearing all data...")
    
    db = get_db_session()
    try:
        from app.models import Animal, Observation, Shelter, SuccessStory
        
        # Delete in order to respect foreign keys
        deleted_obs = db.query(Observation).delete()
        deleted_stories = db.query(SuccessStory).delete()
        deleted_animals = db.query(Animal).delete()
        deleted_shelters = db.query(Shelter).delete()
        
        db.commit()
        
        print(f"  Deleted {deleted_obs} observations")
        print(f"  Deleted {deleted_stories} success stories")
        print(f"  Deleted {deleted_animals} animals")
        print(f"  Deleted {deleted_shelters} shelters")
        print("✅ All data cleared!")
        return True
    except Exception as e:
        db.rollback()
        print(f"❌ Error clearing data: {e}")
        return False
    finally:
        db.close()


def show_status():
    """Show database status and counts."""
    print("📊 Database Status")
    print("=" * 40)
    
    db = get_db_session()
    try:
        from app.models import Animal, Observation, Shelter, SuccessStory, AnimalStatus
        from sqlalchemy import func
        
        # Counts
        animal_count = db.query(Animal).count()
        available_count = db.query(Animal).filter(Animal.status == AnimalStatus.AVAILABLE).count()
        adopted_count = db.query(Animal).filter(Animal.status == AnimalStatus.ADOPTED).count()
        observation_count = db.query(Observation).count()
        shelter_count = db.query(Shelter).count()
        story_count = db.query(SuccessStory).count()
        
        # Latest data
        latest_obs = db.query(func.max(Observation.last_seen_at)).scalar()
        
        print(f"  Animals:       {animal_count:,}")
        print(f"    Available:   {available_count:,}")
        print(f"    Adopted:     {adopted_count:,}")
        print(f"  Observations:  {observation_count:,}")
        print(f"  Shelters:      {shelter_count:,}")
        print(f"  Success Stories: {story_count:,}")
        print(f"  Latest Update: {latest_obs or 'No data'}")
        print("=" * 40)
        
        return True
    except Exception as e:
        print(f"❌ Error getting status: {e}")
        return False
    finally:
        db.close()


def reset_database():
    """Clear and re-seed the database."""
    print("🔄 Resetting database...")
    if clear_all_data():
        return seed_demo_data()
    return False


def run_migrations():
    """Run database migrations using Alembic."""
    print("🔧 Running migrations...")
    
    try:
        import subprocess
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            cwd=BACKEND_DIR,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print(result.stdout)
            print("✅ Migrations complete!")
            return True
        else:
            print(f"⚠️  Alembic output: {result.stderr}")
            # Try to create tables directly if Alembic isn't set up
            print("Falling back to direct table creation...")
            from app.database import engine, Base
            from app.models import Animal, Observation, Shelter, SuccessStory
            Base.metadata.create_all(bind=engine)
            print("✅ Tables created!")
            return True
    except FileNotFoundError:
        print("⚠️  Alembic not found, creating tables directly...")
        from app.database import engine, Base
        from app.models import Animal, Observation, Shelter, SuccessStory
        Base.metadata.create_all(bind=engine)
        print("✅ Tables created!")
        return True
    except Exception as e:
        print(f"❌ Error running migrations: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Database management CLI for Waiting The Longest",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/db_seed.py demo     # Add demo animals and shelters
  python scripts/db_seed.py status   # Show current database counts
  python scripts/db_seed.py reset    # Clear and re-seed everything
        """
    )
    
    parser.add_argument(
        "command",
        choices=["demo", "clear", "reset", "status", "migrate"],
        help="Command to execute"
    )
    
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Skip confirmation prompts"
    )
    
    args = parser.parse_args()
    
    # Confirmation for destructive operations
    if args.command in ["clear", "reset"] and not args.force:
        response = input(f"⚠️  This will delete data. Continue? [y/N]: ")
        if response.lower() != 'y':
            print("Cancelled.")
            sys.exit(0)
    
    # Execute command
    commands = {
        "demo": seed_demo_data,
        "clear": clear_all_data,
        "reset": reset_database,
        "status": show_status,
        "migrate": run_migrations,
    }
    
    success = commands[args.command]()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

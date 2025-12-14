"""
Waiting The Longest™ - Database Migrations
============================================
Schema migrations and version management.
"""

import os
from datetime import datetime
from dataclasses import dataclass
from typing import Callable
from sqlalchemy import text, inspect
from sqlalchemy.orm import Session


@dataclass
class Migration:
    """A database migration."""
    version: str
    name: str
    up: Callable[[Session], None]
    down: Callable[[Session], None]


# =============================================================================
# Migration Registry
# =============================================================================

migrations: list[Migration] = []


def migration(version: str, name: str):
    """Decorator to register a migration."""
    def decorator(cls):
        m = Migration(
            version=version,
            name=name,
            up=cls.up,
            down=cls.down,
        )
        migrations.append(m)
        return cls
    return decorator


# =============================================================================
# Migrations Table
# =============================================================================

def ensure_migrations_table(db: Session):
    """Create migrations tracking table if it doesn't exist."""
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS _migrations (
            version VARCHAR(50) PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    db.commit()


def get_applied_migrations(db: Session) -> set[str]:
    """Get set of applied migration versions."""
    ensure_migrations_table(db)
    result = db.execute(text("SELECT version FROM _migrations"))
    return {row[0] for row in result.fetchall()}


def mark_applied(db: Session, migration: Migration):
    """Mark a migration as applied."""
    db.execute(
        text("INSERT INTO _migrations (version, name) VALUES (:version, :name)"),
        {"version": migration.version, "name": migration.name},
    )
    db.commit()


def mark_unapplied(db: Session, migration: Migration):
    """Mark a migration as unapplied."""
    db.execute(
        text("DELETE FROM _migrations WHERE version = :version"),
        {"version": migration.version},
    )
    db.commit()


# =============================================================================
# Migration Runner
# =============================================================================

def run_migrations(db: Session, target: str | None = None):
    """
    Run pending migrations.
    
    Args:
        db: Database session
        target: Target version (None = latest)
    """
    applied = get_applied_migrations(db)
    
    for m in sorted(migrations, key=lambda x: x.version):
        if m.version in applied:
            continue
        
        if target and m.version > target:
            break
        
        print(f"Applying migration {m.version}: {m.name}")
        m.up(db)
        mark_applied(db, m)
        print(f"  ✓ Applied")


def rollback_migration(db: Session, steps: int = 1):
    """
    Rollback migrations.
    
    Args:
        db: Database session
        steps: Number of migrations to rollback
    """
    applied = get_applied_migrations(db)
    
    # Get applied migrations in reverse order
    to_rollback = [
        m for m in sorted(migrations, key=lambda x: x.version, reverse=True)
        if m.version in applied
    ][:steps]
    
    for m in to_rollback:
        print(f"Rolling back migration {m.version}: {m.name}")
        m.down(db)
        mark_unapplied(db, m)
        print(f"  ✓ Rolled back")


def migration_status(db: Session) -> list[dict]:
    """Get status of all migrations."""
    applied = get_applied_migrations(db)
    
    return [
        {
            "version": m.version,
            "name": m.name,
            "applied": m.version in applied,
        }
        for m in sorted(migrations, key=lambda x: x.version)
    ]


# =============================================================================
# Actual Migrations
# =============================================================================

@migration("001", "Initial schema")
class Migration001:
    @staticmethod
    def up(db: Session):
        # Check if tables exist
        inspector = inspect(db.get_bind())
        tables = inspector.get_table_names()
        
        if "animals" not in tables:
            db.execute(text("""
                CREATE TABLE animals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(255) NOT NULL,
                    species VARCHAR(50),
                    breed VARCHAR(255),
                    age VARCHAR(50),
                    gender VARCHAR(20),
                    size VARCHAR(20),
                    description TEXT,
                    photo_url TEXT,
                    intake_date DATE,
                    is_adopted BOOLEAN DEFAULT FALSE,
                    shelter_id INTEGER,
                    external_id VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
        
        if "shelters" not in tables:
            db.execute(text("""
                CREATE TABLE shelters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(255) NOT NULL,
                    city VARCHAR(100),
                    state VARCHAR(50),
                    zip_code VARCHAR(20),
                    phone VARCHAR(30),
                    email VARCHAR(255),
                    website VARCHAR(500),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
        
        db.commit()
    
    @staticmethod
    def down(db: Session):
        db.execute(text("DROP TABLE IF EXISTS animals"))
        db.execute(text("DROP TABLE IF EXISTS shelters"))
        db.commit()


@migration("002", "Add newsletter subscribers")
class Migration002:
    @staticmethod
    def up(db: Session):
        inspector = inspect(db.get_bind())
        tables = inspector.get_table_names()
        
        if "newsletter_subscribers" not in tables:
            db.execute(text("""
                CREATE TABLE newsletter_subscribers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    unsubscribed_at TIMESTAMP
                )
            """))
            db.commit()
    
    @staticmethod
    def down(db: Session):
        db.execute(text("DROP TABLE IF EXISTS newsletter_subscribers"))
        db.commit()


@migration("003", "Add animal indexes")
class Migration003:
    @staticmethod
    def up(db: Session):
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_animals_intake_date 
            ON animals (intake_date)
        """))
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_animals_species 
            ON animals (species)
        """))
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_animals_is_adopted 
            ON animals (is_adopted)
        """))
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_animals_shelter_id 
            ON animals (shelter_id)
        """))
        db.commit()
    
    @staticmethod
    def down(db: Session):
        db.execute(text("DROP INDEX IF EXISTS idx_animals_intake_date"))
        db.execute(text("DROP INDEX IF EXISTS idx_animals_species"))
        db.execute(text("DROP INDEX IF EXISTS idx_animals_is_adopted"))
        db.execute(text("DROP INDEX IF EXISTS idx_animals_shelter_id"))
        db.commit()


@migration("004", "Add additional photos column")
class Migration004:
    @staticmethod
    def up(db: Session):
        try:
            db.execute(text("""
                ALTER TABLE animals ADD COLUMN additional_photos TEXT
            """))
            db.commit()
        except Exception:
            # Column might already exist
            db.rollback()
    
    @staticmethod
    def down(db: Session):
        # SQLite doesn't support DROP COLUMN directly
        pass


@migration("005", "Add location to animals")
class Migration005:
    @staticmethod
    def up(db: Session):
        try:
            db.execute(text("""
                ALTER TABLE animals ADD COLUMN location VARCHAR(255)
            """))
            db.commit()
        except Exception:
            db.rollback()
    
    @staticmethod
    def down(db: Session):
        pass


@migration("006", "Add adoption tracking")
class Migration006:
    @staticmethod
    def up(db: Session):
        inspector = inspect(db.get_bind())
        tables = inspector.get_table_names()
        
        if "adoptions" not in tables:
            db.execute(text("""
                CREATE TABLE adoptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    animal_id INTEGER NOT NULL,
                    adopted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    days_waiting INTEGER,
                    FOREIGN KEY (animal_id) REFERENCES animals (id)
                )
            """))
            db.commit()
    
    @staticmethod
    def down(db: Session):
        db.execute(text("DROP TABLE IF EXISTS adoptions"))
        db.commit()


# =============================================================================
# CLI Functions
# =============================================================================

def init_db():
    """Initialize database with all migrations."""
    from backend.app.database import SessionLocal
    db = SessionLocal()
    try:
        run_migrations(db)
        print("Database initialized successfully")
    finally:
        db.close()


def reset_db():
    """Reset database (rollback all migrations)."""
    from backend.app.database import SessionLocal
    db = SessionLocal()
    try:
        # Rollback all
        applied = get_applied_migrations(db)
        rollback_migration(db, steps=len(applied))
        # Re-apply
        run_migrations(db)
        print("Database reset successfully")
    finally:
        db.close()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python migrations.py [init|reset|status|up|down]")
        sys.exit(1)
    
    command = sys.argv[1]
    
    from backend.app.database import SessionLocal
    db = SessionLocal()
    
    try:
        if command == "init":
            run_migrations(db)
        elif command == "reset":
            reset_db()
        elif command == "status":
            status = migration_status(db)
            for m in status:
                mark = "✓" if m["applied"] else "✗"
                print(f"  {mark} {m['version']}: {m['name']}")
        elif command == "up":
            run_migrations(db)
        elif command == "down":
            steps = int(sys.argv[2]) if len(sys.argv) > 2 else 1
            rollback_migration(db, steps)
        else:
            print(f"Unknown command: {command}")
            sys.exit(1)
    finally:
        db.close()

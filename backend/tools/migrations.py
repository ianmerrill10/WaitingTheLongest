"""
Waiting The Longest™ - Database Migration Utilities
====================================================
Utilities for database migrations and schema updates.
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from sqlalchemy import text, inspect
from sqlalchemy.orm import Session
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


@dataclass
class MigrationStep:
    """Represents a single migration step."""
    version: str
    name: str
    sql_up: str
    sql_down: str
    applied_at: Optional[datetime] = None


class MigrationManager:
    """
    Manage database schema migrations.
    
    Simple migration system for small projects.
    For larger projects, consider Alembic.
    """
    
    def __init__(self, engine: Engine):
        self.engine = engine
        self._ensure_migration_table()
    
    def _ensure_migration_table(self) -> None:
        """Create migration tracking table if it doesn't exist."""
        with self.engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS _migrations (
                    version VARCHAR(50) PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()
    
    def get_applied_migrations(self) -> List[str]:
        """Get list of applied migration versions."""
        with self.engine.connect() as conn:
            result = conn.execute(text(
                "SELECT version FROM _migrations ORDER BY version"
            ))
            return [row[0] for row in result.fetchall()]
    
    def apply_migration(self, migration: MigrationStep) -> bool:
        """Apply a single migration."""
        applied = self.get_applied_migrations()
        
        if migration.version in applied:
            logger.info(f"Migration {migration.version} already applied")
            return False
        
        try:
            with self.engine.connect() as conn:
                # Apply migration
                conn.execute(text(migration.sql_up))
                
                # Record migration
                conn.execute(text("""
                    INSERT INTO _migrations (version, name)
                    VALUES (:version, :name)
                """), {"version": migration.version, "name": migration.name})
                
                conn.commit()
            
            logger.info(f"Applied migration: {migration.version} - {migration.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply migration {migration.version}: {e}")
            raise
    
    def rollback_migration(self, migration: MigrationStep) -> bool:
        """Rollback a single migration."""
        applied = self.get_applied_migrations()
        
        if migration.version not in applied:
            logger.info(f"Migration {migration.version} not applied")
            return False
        
        try:
            with self.engine.connect() as conn:
                # Rollback migration
                conn.execute(text(migration.sql_down))
                
                # Remove migration record
                conn.execute(text(
                    "DELETE FROM _migrations WHERE version = :version"
                ), {"version": migration.version})
                
                conn.commit()
            
            logger.info(f"Rolled back migration: {migration.version}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to rollback migration {migration.version}: {e}")
            raise
    
    def apply_pending(self, migrations: List[MigrationStep]) -> int:
        """Apply all pending migrations."""
        applied = self.get_applied_migrations()
        count = 0
        
        for migration in sorted(migrations, key=lambda m: m.version):
            if migration.version not in applied:
                self.apply_migration(migration)
                count += 1
        
        return count


# =============================================================================
# Migration Definitions
# =============================================================================

MIGRATIONS: List[MigrationStep] = [
    MigrationStep(
        version="001",
        name="add_shelter_geocoding",
        sql_up="""
            ALTER TABLE shelters ADD COLUMN IF NOT EXISTS latitude REAL;
            ALTER TABLE shelters ADD COLUMN IF NOT EXISTS longitude REAL;
        """,
        sql_down="""
            ALTER TABLE shelters DROP COLUMN IF EXISTS latitude;
            ALTER TABLE shelters DROP COLUMN IF EXISTS longitude;
        """,
    ),
    MigrationStep(
        version="002",
        name="add_animal_external_id_index",
        sql_up="""
            CREATE INDEX IF NOT EXISTS idx_animals_external_id 
            ON animals(external_id);
        """,
        sql_down="""
            DROP INDEX IF EXISTS idx_animals_external_id;
        """,
    ),
    MigrationStep(
        version="003",
        name="add_intake_date_index",
        sql_up="""
            CREATE INDEX IF NOT EXISTS idx_animals_intake_date 
            ON animals(intake_date);
        """,
        sql_down="""
            DROP INDEX IF EXISTS idx_animals_intake_date;
        """,
    ),
    MigrationStep(
        version="004",
        name="add_species_index",
        sql_up="""
            CREATE INDEX IF NOT EXISTS idx_animals_species 
            ON animals(species);
        """,
        sql_down="""
            DROP INDEX IF EXISTS idx_animals_species;
        """,
    ),
    MigrationStep(
        version="005",
        name="add_shelter_state_index",
        sql_up="""
            CREATE INDEX IF NOT EXISTS idx_shelters_state 
            ON shelters(state);
        """,
        sql_down="""
            DROP INDEX IF EXISTS idx_shelters_state;
        """,
    ),
    MigrationStep(
        version="006",
        name="add_newsletter_created_at",
        sql_up="""
            ALTER TABLE newsletter_subscribers 
            ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
        """,
        sql_down="""
            ALTER TABLE newsletter_subscribers 
            DROP COLUMN IF EXISTS created_at;
        """,
    ),
    MigrationStep(
        version="007",
        name="add_animal_last_updated",
        sql_up="""
            ALTER TABLE animals 
            ADD COLUMN IF NOT EXISTS last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
        """,
        sql_down="""
            ALTER TABLE animals DROP COLUMN IF EXISTS last_updated;
        """,
    ),
]


# =============================================================================
# Database Inspection Utilities
# =============================================================================

def get_table_info(engine: Engine) -> Dict[str, Any]:
    """Get information about all tables in the database."""
    inspector = inspect(engine)
    
    info = {}
    for table_name in inspector.get_table_names():
        columns = inspector.get_columns(table_name)
        indexes = inspector.get_indexes(table_name)
        
        info[table_name] = {
            "columns": [
                {
                    "name": col["name"],
                    "type": str(col["type"]),
                    "nullable": col.get("nullable", True),
                }
                for col in columns
            ],
            "indexes": [
                {
                    "name": idx["name"],
                    "columns": idx["column_names"],
                    "unique": idx.get("unique", False),
                }
                for idx in indexes
            ],
        }
    
    return info


def print_schema(engine: Engine) -> None:
    """Print database schema summary."""
    info = get_table_info(engine)
    
    print("\n" + "=" * 60)
    print("DATABASE SCHEMA")
    print("=" * 60)
    
    for table_name, table_info in sorted(info.items()):
        print(f"\n{table_name}")
        print("-" * len(table_name))
        
        print("  Columns:")
        for col in table_info["columns"]:
            nullable = "" if col["nullable"] else " NOT NULL"
            print(f"    - {col['name']}: {col['type']}{nullable}")
        
        if table_info["indexes"]:
            print("  Indexes:")
            for idx in table_info["indexes"]:
                unique = " (UNIQUE)" if idx["unique"] else ""
                print(f"    - {idx['name']}: {', '.join(idx['columns'])}{unique}")
    
    print("\n" + "=" * 60)


# =============================================================================
# CLI Entry Point
# =============================================================================

def run_migrations(direction: str = "up") -> None:
    """Run migrations from command line."""
    from app.database import engine
    
    manager = MigrationManager(engine)
    
    if direction == "up":
        count = manager.apply_pending(MIGRATIONS)
        print(f"Applied {count} migration(s)")
    elif direction == "status":
        applied = manager.get_applied_migrations()
        print("Applied migrations:")
        for v in applied:
            print(f"  - {v}")
        print(f"\nTotal: {len(applied)} applied, {len(MIGRATIONS) - len(applied)} pending")
    elif direction == "schema":
        print_schema(engine)
    else:
        print(f"Unknown direction: {direction}")


if __name__ == "__main__":
    import sys
    direction = sys.argv[1] if len(sys.argv) > 1 else "status"
    run_migrations(direction)

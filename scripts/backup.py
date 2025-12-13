#!/usr/bin/env python3
"""
===============================================================================
Waiting The Longest™ - Automated Backup Script
===============================================================================
Purpose: Create automated backups of database and critical files.
         Supports local backups and optional S3 upload.

Usage:
    python scripts/backup.py                    # Create local backup
    python scripts/backup.py --upload           # Backup and upload to S3
    python scripts/backup.py --restore latest   # Restore latest backup
    python scripts/backup.py --list             # List available backups

Author: Waiting The Longest™ Development Team
===============================================================================
"""

import argparse
import gzip
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path


# Configuration
BACKUP_DIR = Path(__file__).parent.parent / "backups"
MAX_LOCAL_BACKUPS = 10  # Keep last N backups


def get_timestamp() -> str:
    """Get timestamp string for backup naming."""
    return datetime.utcnow().strftime("%Y%m%d_%H%M%S")


def ensure_backup_dir():
    """Create backup directory if it doesn't exist."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    gitignore = BACKUP_DIR / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text("*\n!.gitignore\n")


def backup_sqlite(db_path: Path, backup_name: str) -> Path:
    """Backup SQLite database."""
    if not db_path.exists():
        print(f"⚠️  Database not found: {db_path}")
        return None
    
    backup_file = BACKUP_DIR / f"{backup_name}.db.gz"
    
    print(f"📦 Backing up SQLite database...")
    with open(db_path, 'rb') as f_in:
        with gzip.open(backup_file, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
    
    size_mb = backup_file.stat().st_size / (1024 * 1024)
    print(f"   ✅ Created: {backup_file.name} ({size_mb:.2f} MB)")
    return backup_file


def backup_postgres(connection_url: str, backup_name: str) -> Path:
    """Backup PostgreSQL database using pg_dump."""
    backup_file = BACKUP_DIR / f"{backup_name}.sql.gz"
    
    print(f"📦 Backing up PostgreSQL database...")
    try:
        # Use pg_dump with gzip compression
        with gzip.open(backup_file, 'wt') as f_out:
            result = subprocess.run(
                ["pg_dump", connection_url, "--no-owner", "--no-acl"],
                capture_output=True,
                text=True,
                check=True
            )
            f_out.write(result.stdout)
        
        size_mb = backup_file.stat().st_size / (1024 * 1024)
        print(f"   ✅ Created: {backup_file.name} ({size_mb:.2f} MB)")
        return backup_file
    except subprocess.CalledProcessError as e:
        print(f"   ❌ pg_dump failed: {e.stderr}")
        return None
    except FileNotFoundError:
        print("   ❌ pg_dump not found. Is PostgreSQL client installed?")
        return None


def backup_files(backup_name: str) -> Path:
    """Backup critical configuration files."""
    project_root = Path(__file__).parent.parent
    files_to_backup = [
        ".env",
        ".env.example",
        "docker-compose.yml",
        "nginx/waitingthelongest.conf",
    ]
    
    backup_file = BACKUP_DIR / f"{backup_name}_files.tar.gz"
    existing_files = [f for f in files_to_backup if (project_root / f).exists()]
    
    if not existing_files:
        print("⚠️  No config files to backup")
        return None
    
    print(f"📦 Backing up {len(existing_files)} config files...")
    
    import tarfile
    with tarfile.open(backup_file, "w:gz") as tar:
        for file_path in existing_files:
            full_path = project_root / file_path
            tar.add(full_path, arcname=file_path)
    
    size_kb = backup_file.stat().st_size / 1024
    print(f"   ✅ Created: {backup_file.name} ({size_kb:.2f} KB)")
    return backup_file


def cleanup_old_backups():
    """Remove old backups, keeping only the most recent."""
    backups = sorted(BACKUP_DIR.glob("backup_*"), key=lambda p: p.stat().st_mtime, reverse=True)
    
    # Group by timestamp prefix
    backup_sets = {}
    for backup in backups:
        # Extract timestamp from filename
        parts = backup.stem.split("_")
        if len(parts) >= 3:
            timestamp = f"{parts[1]}_{parts[2]}"
            if timestamp not in backup_sets:
                backup_sets[timestamp] = []
            backup_sets[timestamp].append(backup)
    
    # Keep only the most recent sets
    timestamps = sorted(backup_sets.keys(), reverse=True)
    for old_timestamp in timestamps[MAX_LOCAL_BACKUPS:]:
        for backup_file in backup_sets[old_timestamp]:
            print(f"🗑️  Removing old backup: {backup_file.name}")
            backup_file.unlink()


def upload_to_s3(files: list, bucket: str = None):
    """Upload backups to S3."""
    bucket = bucket or os.environ.get("BACKUP_S3_BUCKET")
    if not bucket:
        print("⚠️  S3 bucket not configured (set BACKUP_S3_BUCKET)")
        return False
    
    try:
        import boto3
        s3 = boto3.client('s3')
        
        for file_path in files:
            if file_path and file_path.exists():
                key = f"backups/{file_path.name}"
                print(f"☁️  Uploading {file_path.name} to s3://{bucket}/{key}")
                s3.upload_file(str(file_path), bucket, key)
        
        print("   ✅ S3 upload complete")
        return True
    except ImportError:
        print("   ❌ boto3 not installed. Run: pip install boto3")
        return False
    except Exception as e:
        print(f"   ❌ S3 upload failed: {e}")
        return False


def list_backups():
    """List available backups."""
    ensure_backup_dir()
    backups = sorted(BACKUP_DIR.glob("backup_*"), key=lambda p: p.stat().st_mtime, reverse=True)
    
    if not backups:
        print("No backups found.")
        return
    
    print("\n📂 Available Backups:")
    print("-" * 60)
    
    current_date = None
    for backup in backups:
        mtime = datetime.fromtimestamp(backup.stat().st_mtime)
        date_str = mtime.strftime("%Y-%m-%d")
        
        if date_str != current_date:
            current_date = date_str
            print(f"\n{date_str}:")
        
        size = backup.stat().st_size
        if size > 1024 * 1024:
            size_str = f"{size / (1024*1024):.2f} MB"
        else:
            size_str = f"{size / 1024:.2f} KB"
        
        print(f"  {mtime.strftime('%H:%M:%S')}  {backup.name:40} {size_str:>10}")


def restore_backup(backup_name: str):
    """Restore from a backup."""
    ensure_backup_dir()
    
    if backup_name == "latest":
        backups = sorted(BACKUP_DIR.glob("backup_*.db.gz"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not backups:
            print("❌ No database backups found")
            return False
        backup_file = backups[0]
    else:
        backup_file = BACKUP_DIR / backup_name
        if not backup_file.exists():
            backup_file = BACKUP_DIR / f"backup_{backup_name}.db.gz"
    
    if not backup_file.exists():
        print(f"❌ Backup not found: {backup_file}")
        return False
    
    print(f"🔄 Restoring from: {backup_file.name}")
    
    # Restore SQLite
    project_root = Path(__file__).parent.parent
    db_path = project_root / "backend" / "waitingthelongest.db"
    
    # Create backup of current DB first
    if db_path.exists():
        current_backup = db_path.with_suffix(".db.pre-restore")
        shutil.copy2(db_path, current_backup)
        print(f"   Created pre-restore backup: {current_backup.name}")
    
    # Decompress and restore
    with gzip.open(backup_file, 'rb') as f_in:
        with open(db_path, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
    
    print(f"   ✅ Database restored successfully")
    return True


def create_backup(upload: bool = False) -> bool:
    """Create a full backup."""
    ensure_backup_dir()
    
    timestamp = get_timestamp()
    backup_name = f"backup_{timestamp}"
    
    print("\n" + "=" * 60)
    print(f"🔒 Creating Backup: {backup_name}")
    print("=" * 60)
    
    backup_files_created = []
    
    # Determine database type from environment
    db_url = os.environ.get("DATABASE_URL", "sqlite:///./backend/waitingthelongest.db")
    
    if db_url.startswith("sqlite"):
        # SQLite backup
        db_path = Path(__file__).parent.parent / "backend" / "waitingthelongest.db"
        db_backup = backup_sqlite(db_path, backup_name)
        if db_backup:
            backup_files_created.append(db_backup)
    elif db_url.startswith("postgresql"):
        # PostgreSQL backup
        db_backup = backup_postgres(db_url, backup_name)
        if db_backup:
            backup_files_created.append(db_backup)
    
    # Backup config files
    files_backup = backup_files(backup_name)
    if files_backup:
        backup_files_created.append(files_backup)
    
    # Cleanup old backups
    cleanup_old_backups()
    
    # Upload to S3 if requested
    if upload and backup_files_created:
        upload_to_s3(backup_files_created)
    
    print("\n" + "=" * 60)
    print(f"✅ Backup complete: {len(backup_files_created)} files created")
    print("=" * 60)
    
    return len(backup_files_created) > 0


def main():
    parser = argparse.ArgumentParser(
        description="Backup and restore Waiting The Longest database"
    )
    parser.add_argument(
        "--upload", "-u",
        action="store_true",
        help="Upload backups to S3"
    )
    parser.add_argument(
        "--restore", "-r",
        metavar="BACKUP",
        help="Restore from backup (use 'latest' for most recent)"
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List available backups"
    )
    
    args = parser.parse_args()
    
    if args.list:
        list_backups()
    elif args.restore:
        success = restore_backup(args.restore)
        sys.exit(0 if success else 1)
    else:
        success = create_backup(upload=args.upload)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

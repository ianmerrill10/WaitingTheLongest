#!/usr/bin/env python3
"""
Restore Shelters from Backup
============================
Loads shelter data from shelters_backup.json into the database.
This is the fastest way to populate your local database with 6,462 shelters.

Usage:
    cd backend
    python tools/restore_shelters_from_backup.py
"""
import json
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.database import SessionLocal, init_db
from app.models import Shelter

def restore_shelters():
    backup_file = os.path.join(os.path.dirname(__file__), '../data/shelters_backup.json')

    if not os.path.exists(backup_file):
        print(f"ERROR: Backup file not found: {backup_file}")
        return

    print("=" * 60)
    print("RESTORE SHELTERS FROM BACKUP")
    print("=" * 60)
    print(f"Loading from: {backup_file}")

    # Initialize database tables
    print("\nInitializing database...")
    init_db()

    # Load backup data
    with open(backup_file, 'r', encoding='utf-8') as f:
        shelters_data = json.load(f)

    print(f"Found {len(shelters_data)} shelters in backup")

    db = SessionLocal()
    try:
        # Check existing count
        existing = db.query(Shelter).count()
        print(f"Existing shelters in database: {existing}")

        if existing > 0:
            response = input("\nDatabase already has shelters. Clear and reload? (y/n): ")
            if response.lower() != 'y':
                print("Aborted.")
                return
            print("Clearing existing shelters...")
            db.query(Shelter).delete()
            db.commit()

        # Insert shelters
        print("\nInserting shelters...")
        count = 0
        for shelter_dict in shelters_data:
            # Remove 'id' field - let the database assign new IDs
            shelter_dict.pop('id', None)

            shelter = Shelter(
                name=shelter_dict.get('name'),
                source=shelter_dict.get('source'),
                email=shelter_dict.get('email'),
                phone=shelter_dict.get('phone'),
                website=shelter_dict.get('website'),
                address=shelter_dict.get('address'),
                city=shelter_dict.get('city'),
                state=shelter_dict.get('state'),
                zip_code=shelter_dict.get('zip_code'),
                facebook_url=shelter_dict.get('facebook_url'),
                instagram_url=shelter_dict.get('instagram_url'),
                twitter_url=shelter_dict.get('twitter_url'),
                tiktok_url=shelter_dict.get('tiktok_url'),
            )
            db.add(shelter)
            count += 1

            if count % 500 == 0:
                db.commit()
                print(f"  Inserted {count} shelters...")

        db.commit()

        # Verify
        final_count = db.query(Shelter).count()
        print()
        print("=" * 60)
        print(f"SUCCESS! Restored {final_count} shelters to database.")
        print("=" * 60)

        # Show sample
        print("\nSample shelters by state:")
        from sqlalchemy import func
        state_counts = db.query(
            Shelter.state,
            func.count(Shelter.id)
        ).group_by(Shelter.state).order_by(func.count(Shelter.id).desc()).limit(10).all()

        for state, cnt in state_counts:
            print(f"  {state or 'Unknown'}: {cnt} shelters")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    restore_shelters()

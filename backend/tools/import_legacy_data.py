import sys
import os
import csv
from datetime import datetime

# Add the project root to the python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from sqlalchemy import func
from backend.app.database import SessionLocal
from backend.app.models import Shelter

def import_master_list(db):
    file_path = os.path.join(os.path.dirname(__file__), "../data/master_lists/master_addresses.csv")
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    print(f"Importing from {file_path}...")
    count = 0
    added = 0
    skipped = 0
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.DictReader(f)
            for row in reader:
                count += 1
                if count % 1000 == 0:
                    print(f"Processed {count} records...")
                
                name = row.get('name', '').strip()
                state = row.get('state', '').strip()
                city = row.get('city', '').strip()
                
                if not name:
                    continue

                # Check for existing shelter
                existing = db.query(Shelter).filter(
                    Shelter.name == name,
                    Shelter.state == state,
                    Shelter.city == city
                ).first()

                if existing:
                    skipped += 1
                    continue

                shelter = Shelter(
                    name=name,
                    source="master_list_import",
                    external_id=row.get('ein', '').strip(),
                    address=row.get('street', '').strip(),
                    city=city,
                    state=state,
                    zip_code=row.get('zip', '').strip(),
                    last_verified_at=datetime.utcnow()
                )
                db.add(shelter)
                added += 1
                
                # Commit in batches
                if added % 100 == 0:
                    db.commit()
        
        db.commit()
        print(f"Master List Import Complete: {added} added, {skipped} skipped.")

    except Exception as e:
        print(f"Error importing master list: {e}")
        db.rollback()

def import_bf_network(db):
    file_path = os.path.join(os.path.dirname(__file__), "../data/bf_network_orgs.csv")
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    print(f"Importing from {file_path}...")
    count = 0
    added = 0
    skipped = 0
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.DictReader(f)
            for row in reader:
                count += 1
                if count % 1000 == 0:
                    print(f"Processed {count} records...")
                
                name = row.get('name', '').strip()
                state = row.get('state', '').strip()
                city = row.get('city', '').strip()
                
                if not name:
                    continue

                # Check for existing shelter
                existing = db.query(Shelter).filter(
                    Shelter.name == name,
                    Shelter.state == state,
                    Shelter.city == city
                ).first()

                if existing:
                    skipped += 1
                    # Update website if missing
                    if not existing.website and row.get('website'):
                        existing.website = row.get('website')
                        db.add(existing)
                    continue

                shelter = Shelter(
                    name=name,
                    source="bf_network_import",
                    city=city,
                    state=state,
                    website=row.get('website', '').strip(),
                    description=row.get('description', '').strip(),
                    last_verified_at=datetime.utcnow()
                )
                db.add(shelter)
                added += 1
                
                # Commit in batches
                if added % 100 == 0:
                    db.commit()
        
        db.commit()
        print(f"BF Network Import Complete: {added} added, {skipped} skipped.")

    except Exception as e:
        print(f"Error importing BF network: {e}")
        db.rollback()

if __name__ == "__main__":
    print("=== Starting Legacy Data Import ===")
    db = SessionLocal()
    try:
        import_master_list(db)
        import_bf_network(db)
    finally:
        db.close()
    print("=== Import Finished ===")

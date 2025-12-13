import csv
import sys
import os
from datetime import datetime

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.database import SessionLocal
from app.models import Shelter

def clean_str(s):
    if not s:
        return None
    return s.strip()

def ingest_shelters(csv_path):
    db = SessionLocal()
    try:
        if not os.path.exists(csv_path):
            print(f"File not found: {csv_path}")
            return

        print(f"Reading from: {csv_path}")
        # utf-8-sig handles BOM if present (common in Excel CSVs)
        with open(csv_path, 'r', encoding='utf-8-sig') as f: 
            reader = csv.DictReader(f)
            count = 0
            updated = 0
            
            for row in reader:
                external_id = clean_str(row.get('Number'))
                name = clean_str(row.get('Organization_Name'))
                
                if not name:
                    print("Skipping row with no Organization_Name")
                    continue

                # Check if exists
                existing = None
                if external_id:
                    existing = db.query(Shelter).filter(
                        Shelter.external_id == external_id,
                        Shelter.source == "csv_import"
                    ).first()
                
                shelter_data = {
                    "name": name,
                    "source": "csv_import",
                    "external_id": external_id,
                    "email": clean_str(row.get('Email')),
                    "phone": clean_str(row.get('Phone')),
                    "website": clean_str(row.get('Website')),
                    "description": clean_str(row.get('Description')),
                    "address": clean_str(row.get('Address')),
                    "city": clean_str(row.get('City')),
                    "state": clean_str(row.get('State_Code')) or clean_str(row.get('State')),
                    "zip_code": clean_str(row.get('Zip_Code')),
                    "last_verified_at": datetime.utcnow()
                }

                if existing:
                    # Update existing
                    for key, value in shelter_data.items():
                        setattr(existing, key, value)
                    updated += 1
                else:
                    # Create new
                    shelter = Shelter(**shelter_data)
                    db.add(shelter)
                    count += 1
                
                if (count + updated) % 50 == 0:
                    db.commit()
                    print(f"Processed {count + updated} records...")
            
            db.commit()
            print(f"Finished! Created: {count}, Updated: {updated}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    # Default path relative to this script
    # script is in backend/tools/
    # data is in backend/data/
    default_csv = os.path.join(os.path.dirname(__file__), '../data/shelters.csv')
    
    csv_file = default_csv
    if len(sys.argv) > 1:
        csv_file = sys.argv[1]
        
    print(f"Ingesting from {csv_file}...")
    ingest_shelters(csv_file)

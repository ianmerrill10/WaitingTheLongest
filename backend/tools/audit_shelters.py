import sys
import os
import csv

# Add the project root to the python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from sqlalchemy import func
from backend.app.database import SessionLocal, engine
from backend.app.models import Shelter, Animal, SuccessStory

def audit_shelters():
    db = SessionLocal()
    try:
        # Count total shelters
        total_shelters = db.query(func.count(Shelter.id)).scalar()
        print(f"Total Shelters/Rescues in DB: {total_shelters}")

        # Breakdown by Organization Type
        print("\nBreakdown by Organization Type (DB):")
        org_types = db.query(Shelter.org_type, func.count(Shelter.id)).group_by(Shelter.org_type).all()
        for org_type, count in org_types:
            print(f"  - {org_type or 'Unspecified'}: {count}")

        # Breakdown by Source
        print("\nBreakdown by Source (DB):")
        sources = db.query(Shelter.source, func.count(Shelter.id)).group_by(Shelter.source).all()
        for source, count in sources:
            print(f"  - {source or 'Unknown'}: {count}")

    except Exception as e:
        print(f"Error auditing shelters: {e}")
    finally:
        db.close()

def audit_others():
    db = SessionLocal()
    try:
        # Count Animals
        total_animals = db.query(func.count(Animal.id)).scalar()
        print(f"\nTotal Animals in DB: {total_animals}")

        # Count Success Stories
        total_stories = db.query(func.count(SuccessStory.id)).scalar()
        print(f"Total Success Stories in DB: {total_stories}")

    except Exception as e:
        print(f"Error auditing others: {e}")
    finally:
        db.close()

def audit_files():
    print("\n--- File-Based Data Audit ---")
    # Base path is the project root
    base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
    data_files = [
        os.path.join(base_path, "backend", "data", "master_lists", "master_addresses.csv"),
        os.path.join(base_path, "backend", "data", "bf_network_orgs.csv"),
        os.path.join(base_path, "backend", "data", "shelters.csv"),
        os.path.join(base_path, "backend", "data", "maryland_rescues.csv"),
        os.path.join(base_path, "backend", "data", "florida_rescues.csv"),
    ]

    total_file_records = 0
    for file_path in data_files:
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    # Subtract 1 for header
                    count = sum(1 for _ in f) - 1
                    count = max(0, count) # Ensure no negative if empty
                    print(f"File: {os.path.basename(file_path)}: {count} records")
                    total_file_records += count
            except Exception as e:
                print(f"Error reading {os.path.basename(file_path)}: {e}")
        else:
            print(f"File not found: {os.path.basename(file_path)}")
    
    print(f"\nTotal Records in Data Files: {total_file_records}")

if __name__ == "__main__":
    print("=== Waiting The Longest - Project Audit ===\n")
    audit_shelters()
    audit_others()
    audit_files()

"""
Ingest REAL animals from RescueGroups.org API
Run this after adding your API key to .env

Usage: python ingest_real_animals.py [--limit 100] [--species dog|cat|all]
"""
import sys
sys.path.insert(0, '.')

import argparse
from app.database import SessionLocal, engine, Base
from app.config import settings
from ingestors.rescuegroups import RescueGroupsIngestor, run_full_ingestion

# Create tables
Base.metadata.create_all(bind=engine)

def main():
    parser = argparse.ArgumentParser(description='Ingest animals from RescueGroups.org')
    parser.add_argument('--limit', type=int, default=100, help='Max animals to fetch')
    parser.add_argument('--species', choices=['dog', 'cat', 'all'], default='all', help='Species to fetch')
    args = parser.parse_args()

    # Check API key
    if not settings.RESCUEGROUPS_API_KEY:
        print("=" * 60)
        print("ERROR: No RescueGroups API key found!")
        print("=" * 60)
        print()
        print("To get REAL shelter animals, you need a FREE API key:")
        print()
        print("1. Go to: https://rescuegroups.org/services/request-an-api-key/")
        print("2. Fill out the form (it's free for non-commercial use)")
        print("3. Add to backend/.env:")
        print("   RESCUEGROUPS_API_KEY=your_api_key_here")
        print("4. Run this script again")
        print()
        return

    print(f"API Key found! Fetching {args.species} animals (limit: {args.limit})...")
    
    db = SessionLocal()
    try:
        stats = run_full_ingestion(db, species=args.species, limit=args.limit)
        print()
        print("=" * 60)
        print("INGESTION COMPLETE!")
        print("=" * 60)
        print(f"  New animals:     {stats['new']}")
        print(f"  Updated animals: {stats['updated']}")
        print(f"  Errors:          {stats['errors']}")
        print()
        print("Refresh your browser to see the new animals!")
    except Exception as e:
        print(f"Error during ingestion: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()

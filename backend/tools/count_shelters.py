import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.database import SessionLocal
from app.models import Shelter

def count_shelters():
    db = SessionLocal()
    try:
        count = db.query(Shelter).count()
        print(f"Total Shelter Count: {count}")
        
        # Optional: Breakdown by source
        print("\nBreakdown by Source:")
        from sqlalchemy import func
        breakdown = db.query(Shelter.source, func.count(Shelter.source)).group_by(Shelter.source).all()
        for source, cnt in breakdown:
            print(f"  - {source}: {cnt}")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    count_shelters()

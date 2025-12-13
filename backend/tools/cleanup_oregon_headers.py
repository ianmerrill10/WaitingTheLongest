import sys
import os

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models import Shelter

def cleanup_headers():
    db = SessionLocal()
    
    bad_names = [
        "Organization / Center",
        "Name of Rescue (Non-profit)",
        "Sanctuary / Rescue",
        "Name (Shelter/Humane Society)"
    ]
    
    count = 0
    for name in bad_names:
        deleted = db.query(Shelter).filter(Shelter.name == name).delete()
        count += deleted
        
    db.commit()
    db.close()
    print(f"Deleted {count} invalid header records.")

if __name__ == "__main__":
    cleanup_headers()

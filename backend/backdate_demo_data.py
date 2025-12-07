from app.database import SessionLocal
from app.models import Animal
from datetime import datetime, timedelta
import random

def backdate_animals():
    db = SessionLocal()
    try:
        animals = db.query(Animal).all()
        print(f"Found {len(animals)} animals to backdate.")
        
        for animal in animals:
            # Generate a random number of days waiting (between 30 and 800 days)
            days_waiting = random.randint(30, 800)
            
            # Calculate new first_seen_at
            new_date = datetime.utcnow() - timedelta(days=days_waiting)
            
            animal.first_seen_at = new_date
            print(f"Updated {animal.canonical_name}: waiting {days_waiting} days (since {new_date.date()})")
            
        db.commit()
        print("Successfully backdated all animals.")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    backdate_animals()

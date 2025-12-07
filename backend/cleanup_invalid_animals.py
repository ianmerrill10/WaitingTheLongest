import sys
sys.path.insert(0, '.')

from app.database import SessionLocal
from app.models import Animal, Observation

def cleanup_invalid_animals():
    db = SessionLocal()
    try:
        # Keywords that indicate this is NOT a specific animal listing
        invalid_keywords = [
            "foster needed",
            "fosters needed",
            "foster home",
            "adoption event",
            "read first",
            "sponsor me",
            "donation",
            "volunteer",
            "transport needed",
            "fundraiser",
            "happy tail",
            "success story",
            "blog",
            "unlisted",
            "any dog",
            "afraid of commitment",
            "perfect dog",
            "courtesy post",
            "courtesy listing"
        ]
        
        plural_names = ["kittens", "puppies", "cats", "dogs", "litter", "various"]

        # Find animals to delete
        animals_to_delete = []
        
        all_animals = db.query(Animal).all()
        for animal in all_animals:
            name_lower = (animal.canonical_name or "").lower()
            
            is_invalid = False
            if any(keyword in name_lower for keyword in invalid_keywords):
                is_invalid = True
            
            # Check for plural names (handling punctuation)
            clean_name = ''.join(c for c in name_lower if c.isalnum())
            if clean_name in plural_names:
                is_invalid = True
                
            # Check for "permanent foster" or "forever foster"
            if "permanent foster" in name_lower or "forever foster" in name_lower:
                is_invalid = True
            
            if is_invalid:
                animals_to_delete.append(animal.id)
                print(f"Marking for deletion: {animal.canonical_name} (ID: {animal.id})")

        if not animals_to_delete:
            print("No invalid animals found.")
            return

        print(f"Found {len(animals_to_delete)} invalid animals.")
        
        # Delete observations first
        db.query(Observation).filter(Observation.animal_id.in_(animals_to_delete)).delete(synchronize_session=False)
        
        # Delete animals
        db.query(Animal).filter(Animal.id.in_(animals_to_delete)).delete(synchronize_session=False)
        
        db.commit()
        print("Successfully removed invalid animals.")
        
    except Exception as e:
        db.rollback()
        print(f"Error cleaning up animals: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    cleanup_invalid_animals()

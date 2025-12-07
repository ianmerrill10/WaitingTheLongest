import sys
sys.path.insert(0, '.')

from app.database import SessionLocal
from app.models import Animal, Observation

def remove_demo_data():
    db = SessionLocal()
    try:
        # Find observations with source='demo'
        demo_observations = db.query(Observation).filter(Observation.source == 'demo').all()
        
        if not demo_observations:
            print("No demo data found.")
            return

        print(f"Found {len(demo_observations)} demo observations.")
        
        # Get the animal IDs associated with these observations
        animal_ids = {obs.animal_id for obs in demo_observations}
        print(f"Found {len(animal_ids)} demo animals.")

        # Delete observations
        db.query(Observation).filter(Observation.source == 'demo').delete(synchronize_session=False)
        
        # Delete animals
        if animal_ids:
            db.query(Animal).filter(Animal.id.in_(animal_ids)).delete(synchronize_session=False)
        
        db.commit()
        print("Successfully removed demo data.")
        
    except Exception as e:
        db.rollback()
        print(f"Error removing demo data: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    remove_demo_data()

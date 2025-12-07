"""
Add demo data for the Waiting The Longest site demonstration
"""
import sys
sys.path.insert(0, '.')

from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine, Base
from app.models import Animal, Shelter, Observation

# Create all tables
Base.metadata.create_all(bind=engine)

# Demo data
demo_shelters = [
    {"name": "Happy Tails Rescue", "city": "Austin", "state": "TX", "external_id": "shelter_1"},
    {"name": "Second Chance Animal Shelter", "city": "Portland", "state": "OR", "external_id": "shelter_2"},
    {"name": "Forever Friends Humane Society", "city": "Denver", "state": "CO", "external_id": "shelter_3"},
]

demo_animals = [
    {
        "canonical_name": "Max",
        "species": "dog",
        "breed_primary": "Labrador Retriever Mix",
        "age_group": "senior",
        "size": "large",
        "gender": "male",
        "description": "Max is a gentle giant who has been waiting patiently for his forever home. He loves belly rubs and long walks in the park. Despite his age, he still has plenty of energy for playtime!",
        "photo_url": "https://placedog.net/400/300?id=1",
        "days_ago": 245,
        "city": "Austin",
        "state": "TX",
    },
    {
        "canonical_name": "Bella",
        "species": "cat",
        "breed_primary": "Domestic Shorthair",
        "age_group": "adult",
        "size": "medium",
        "gender": "female",
        "description": "Bella is a sweet and shy girl who takes a little time to warm up but becomes incredibly affectionate. She loves sunny windowsills and gentle pets.",
        "photo_url": "https://placekitten.com/400/300",
        "days_ago": 187,
        "city": "Portland",
        "state": "OR",
    },
    {
        "canonical_name": "Duke",
        "species": "dog",
        "breed_primary": "German Shepherd",
        "age_group": "adult",
        "size": "large",
        "gender": "male",
        "description": "Duke is an intelligent and loyal companion. He knows basic commands and is great with older kids. He'd thrive in an active home with a yard.",
        "photo_url": "https://placedog.net/400/300?id=2",
        "days_ago": 156,
        "city": "Denver",
        "state": "CO",
    },
    {
        "canonical_name": "Luna",
        "species": "cat",
        "breed_primary": "Siamese Mix",
        "age_group": "young",
        "size": "small",
        "gender": "female",
        "description": "Luna is a chatty and playful girl who loves interactive toys and will follow you around the house. She's looking for a home where she can be the center of attention.",
        "photo_url": "https://placekitten.com/401/300",
        "days_ago": 134,
        "city": "Austin",
        "state": "TX",
    },
    {
        "canonical_name": "Rocky",
        "species": "dog",
        "breed_primary": "Pit Bull Mix",
        "age_group": "young",
        "size": "medium",
        "gender": "male",
        "description": "Rocky is a bundle of love! He's great with people and loves to cuddle. He'd do best as the only pet so he can have all your attention.",
        "photo_url": "https://placedog.net/400/300?id=3",
        "days_ago": 112,
        "city": "Portland",
        "state": "OR",
    },
    {
        "canonical_name": "Whiskers",
        "species": "cat",
        "breed_primary": "Maine Coon Mix",
        "age_group": "senior",
        "size": "large",
        "gender": "male",
        "description": "Whiskers is a majestic senior cat with a big personality. He's calm, loves lap time, and would be perfect for a quiet household.",
        "photo_url": "https://placekitten.com/402/300",
        "days_ago": 98,
        "city": "Denver",
        "state": "CO",
    },
    {
        "canonical_name": "Daisy",
        "species": "dog",
        "breed_primary": "Beagle",
        "age_group": "young",
        "size": "medium",
        "gender": "female",
        "description": "Daisy is an energetic young pup who loves to explore! She's great on walks and would love a family that enjoys outdoor adventures.",
        "photo_url": "https://placedog.net/400/300?id=4",
        "days_ago": 87,
        "city": "Austin",
        "state": "TX",
    },
    {
        "canonical_name": "Shadow",
        "species": "cat",
        "breed_primary": "Domestic Longhair",
        "age_group": "adult",
        "size": "medium",
        "gender": "male",
        "description": "Shadow is a mysterious and beautiful black cat. He's independent but enjoys attention on his terms. Perfect for someone who appreciates a cat with character!",
        "photo_url": "https://placekitten.com/403/300",
        "days_ago": 76,
        "city": "Portland",
        "state": "OR",
    },
]

def add_demo_data():
    db = SessionLocal()
    try:
        # Check if data already exists
        existing = db.query(Animal).first()
        if existing:
            print("Demo data already exists!")
            return

        # Add shelters
        shelters = {}
        for shelter_data in demo_shelters:
            shelter = Shelter(
                name=shelter_data["name"],
                city=shelter_data["city"],
                state=shelter_data["state"],
                external_id=shelter_data["external_id"],
                source="demo"
            )
            db.add(shelter)
            db.flush()
            shelters[shelter_data["city"]] = shelter

        # Add animals with observations
        for i, animal_data in enumerate(demo_animals):
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            first_seen = now - timedelta(days=animal_data["days_ago"])
            shelter = shelters.get(animal_data["city"])
            
            # Create animal (core model fields only)
            animal = Animal(
                canonical_name=animal_data["canonical_name"],
                species=animal_data["species"],
                breed_primary=animal_data["breed_primary"],
                age_group=animal_data["age_group"],
                size=animal_data["size"],
                gender=animal_data["gender"],
                status="available",
                first_seen_at=first_seen,
                last_seen_at=now,
            )
            db.add(animal)
            db.flush()
            
            # Create observation with additional details
            observation = Observation(
                animal_id=animal.id,
                source="demo",
                external_id=f"demo_{i+1}",
                shelter_id=shelter.id if shelter else None,
                shelter_name=shelter.name if shelter else "Unknown Shelter",
                name=animal_data["canonical_name"],
                breed_primary=animal_data["breed_primary"],
                description=animal_data["description"],
                photo_url=animal_data["photo_url"],
                city=animal_data["city"],
                state=animal_data["state"],
                first_seen_at=first_seen,
                last_seen_at=now,
            )
            db.add(observation)

        db.commit()
        print("Demo data added successfully!")
        print(f"Added {len(demo_shelters)} shelters and {len(demo_animals)} animals")
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    add_demo_data()

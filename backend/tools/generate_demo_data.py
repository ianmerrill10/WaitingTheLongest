import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Ensure the backend/ directory is on sys.path so we can import `app.*`
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.database import SessionLocal
from app.models import Animal, Observation, Shelter, AnimalStatus, Species, SuccessStory

def generate_demo_data():
    db = SessionLocal()
    
    try:
        existing_demo_obs = (
            db.query(Observation)
            .filter(Observation.source == "Demo Data Generator")
            .count()
        )
        if existing_demo_obs > 0:
            existing_animals = db.query(Animal).count()
            existing_shelters = db.query(Shelter).count()
            print(
                "Demo data already present; skipping generation. "
                f"(observations={existing_demo_obs}, animals={existing_animals}, shelters={existing_shelters})"
            )
            print("To reset the demo, delete the local database file (e.g. backend/waitingthelongest.db) and run again.")
            return

        # Get all shelters
        shelters = db.query(Shelter).all()
        if not shelters:
            print("No shelters found. Creating demo shelters...")
            demo_shelters = [
                {"name": "Metro Animal Rescue", "city": "Boston", "state": "MA", "website": "https://example.org/metro-animal-rescue"},
                {"name": "Pine Valley Humane Society", "city": "Austin", "state": "TX", "website": "https://example.org/pine-valley-humane"},
                {"name": "Coastal Pet Shelter", "city": "San Diego", "state": "CA", "website": "https://example.org/coastal-pet-shelter"},
                {"name": "Great Lakes Rescue", "city": "Chicago", "state": "IL", "website": "https://example.org/great-lakes-rescue"},
                {"name": "Blue Ridge Animal Haven", "city": "Asheville", "state": "NC", "website": "https://example.org/blue-ridge-animal-haven"},
            ]
            for s in demo_shelters:
                db.add(
                    Shelter(
                        name=s["name"],
                        source="demo",
                        city=s["city"],
                        state=s["state"],
                        website=s["website"],
                    )
                )
            db.commit()
            shelters = db.query(Shelter).all()

        print(f"Found {len(shelters)} shelters. Generating demo animals...")

        # Demo data lists
        dog_names = ["Max", "Bella", "Charlie", "Luna", "Cooper", "Lucy", "Buddy", "Daisy", "Rocky", "Sadie", "Bear", "Molly", "Duke", "Bailey", "Tucker", "Maggie", "Oliver", "Sophie", "Leo", "Chloe"]
        cat_names = ["Luna", "Oliver", "Bella", "Leo", "Milo", "Lily", "Simba", "Nala", "Charlie", "Zoe", "Max", "Chloe", "Shadow", "Lucy", "Tiger", "Oreo", "Smokey", "Kitty", "Jack", "Jasper"]
        
        dog_breeds = ["Pit Bull Mix", "Labrador Retriever Mix", "German Shepherd Mix", "Chihuahua Mix", "Boxer Mix", "Husky Mix", "Beagle Mix", "Terrier Mix"]
        cat_breeds = ["Domestic Short Hair", "Domestic Medium Hair", "Domestic Long Hair", "Siamese Mix", "Maine Coon Mix"]
        
        colors = ["Black", "White", "Brown", "Tan", "Brindle", "Grey", "Orange", "Calico", "Tortie"]
        
        # Generate 50 animals
        for i in range(50):
            species = random.choice([Species.DOG, Species.CAT])
            if species == Species.DOG:
                name = random.choice(dog_names)
                breed = random.choice(dog_breeds)
            else:
                name = random.choice(cat_names)
                breed = random.choice(cat_breeds)
            
            # Pick a random shelter
            shelter = random.choice(shelters)
            
            # Random wait time (skewed towards longer wait times for "Waiting The Longest")
            days_waiting = random.randint(30, 1000)
            first_seen = datetime.utcnow() - timedelta(days=days_waiting)
            
            # Create Animal
            animal = Animal(
                species=species,
                canonical_name=name,
                first_seen_at=first_seen,
                last_seen_at=datetime.utcnow(),
                status=AnimalStatus.AVAILABLE,
                breed_primary=breed,
                color_primary=random.choice(colors),
                age_group=random.choice(["Adult", "Senior", "Young"]),
                size=random.choice(["Medium", "Large", "Small"]),
                gender=random.choice(["Male", "Female"]),
                transfer_count=random.randint(0, 2)
            )
            db.add(animal)
            db.flush() # Get ID
            
            # Create Observation linked to shelter
            observation = Observation(
                animal_id=animal.id,
                source="Demo Data Generator",
                external_id=f"DEMO-{i}-{random.randint(1000, 9999)}",
                shelter_id=shelter.id,
                shelter_name=shelter.name,
                name=name,
                breed_primary=breed,
                description=f"Meet {name}! A lovely {breed} waiting for a forever home at {shelter.name}.",
                city=shelter.city,
                state=shelter.state,
                first_seen_at=first_seen,
                last_seen_at=datetime.utcnow(),
                photo_url=f"https://placedog.net/400/300?id={random.randint(1, 200)}" if species == Species.DOG else f"https://placekitten.com/400/300?image={random.randint(1, 16)}"
            )
            db.add(observation)
            
            # For 30% of animals, simulate a shelter transfer with a second observation
            if random.random() < 0.3 and len(shelters) > 1:
                # Pick a different shelter for transfer
                transfer_shelter = random.choice([s for s in shelters if s.id != shelter.id])
                transfer_date = first_seen + timedelta(days=random.randint(30, min(60, days_waiting)))
                
                observation2 = Observation(
                    animal_id=animal.id,
                    source="Demo Data Generator",
                    external_id=f"DEMO-{i}-TRANSFER-{random.randint(1000, 9999)}",
                    shelter_id=transfer_shelter.id,
                    shelter_name=transfer_shelter.name,
                    name=name,
                    breed_primary=breed,
                    description=f"{name} has transferred to {transfer_shelter.name} and is looking for their forever home!",
                    city=transfer_shelter.city,
                    state=transfer_shelter.state,
                    first_seen_at=transfer_date,
                    last_seen_at=datetime.utcnow(),
                    photo_url=f"https://placedog.net/400/300?id={random.randint(1, 200)}" if species == Species.DOG else f"https://placekitten.com/400/300?image={random.randint(1, 16)}"
                )
                db.add(observation2)
                animal.transfer_count = 1

        # Generate 5 ADOPTED animals with Success Stories
        print("Generating success stories...")
        for i in range(5):
            species = random.choice([Species.DOG, Species.CAT])
            if species == Species.DOG:
                name = random.choice(dog_names)
                breed = random.choice(dog_breeds)
            else:
                name = random.choice(cat_names)
                breed = random.choice(cat_breeds)
            
            shelter = random.choice(shelters)
            days_waiting = random.randint(100, 800)
            first_seen = datetime.utcnow() - timedelta(days=days_waiting + 30) # Adopted 30 days ago
            last_seen = datetime.utcnow() - timedelta(days=30)
            
            # Create Adopted Animal
            animal = Animal(
                species=species,
                canonical_name=name,
                first_seen_at=first_seen,
                last_seen_at=last_seen,
                status=AnimalStatus.ADOPTED,
                breed_primary=breed,
                color_primary=random.choice(colors),
                age_group=random.choice(["Adult", "Senior"]),
                size=random.choice(["Medium", "Large", "Small"]),
                gender=random.choice(["Male", "Female"]),
                transfer_count=random.randint(0, 2)
            )
            db.add(animal)
            db.flush()

            # Create Success Story
            story = SuccessStory(
                animal_id=animal.id,
                pet_name=name,
                adopter_name=f"The {random.choice(['Smith', 'Johnson', 'Williams', 'Brown', 'Jones'])} Family",
                story_text=f"After waiting {days_waiting} days, {name} finally found the perfect home! We are so happy to have {name} in our lives. Thank you to {shelter.name} for taking such good care of {name}.",
                days_waited=days_waiting,
                photo_urls=[f"https://placedog.net/400/300?id={random.randint(1, 200)}" if species == Species.DOG else f"https://placekitten.com/400/300?image={random.randint(1, 16)}"],
                adoption_date=last_seen,
                is_approved=True,
                is_featured=True if i == 0 else False
            )
            db.add(story)
            
        db.commit()
        print("Successfully generated 50 demo animals and 5 success stories.")
        
    except Exception as e:
        print(f"Error generating data: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    generate_demo_data()

import random
from datetime import datetime, timedelta
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from backend.app.database import SessionLocal
from backend.app.models import Animal, Observation, Shelter, AnimalStatus, Species, SuccessStory

def generate_demo_data():
    db = SessionLocal()
    
    try:
        # Get all shelters
        shelters = db.query(Shelter).all()
        if not shelters:
            print("No shelters found! Please ingest shelters first.")
            return

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

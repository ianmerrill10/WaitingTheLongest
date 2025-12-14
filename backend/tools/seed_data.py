"""
Waiting The Longest™ - Database Seeding
=======================================
Seed database with sample data for development and testing.
"""

import random
from datetime import date, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.models import Animal, Shelter, SuccessStory, NewsletterSubscriber


# =============================================================================
# Sample Data
# =============================================================================

SAMPLE_SHELTERS = [
    {
        "name": "Best Friends Animal Sanctuary",
        "city": "Kanab",
        "state": "UT",
        "address": "5001 Angel Canyon Rd",
        "phone": "435-644-2001",
        "email": "info@bestfriends.org",
        "website": "https://bestfriends.org",
    },
    {
        "name": "ASPCA Adoption Center",
        "city": "New York",
        "state": "NY",
        "address": "424 E 92nd St",
        "phone": "212-876-7700",
        "email": "adopt@aspca.org",
        "website": "https://aspca.org",
    },
    {
        "name": "Austin Pets Alive!",
        "city": "Austin",
        "state": "TX",
        "address": "1156 W Cesar Chavez St",
        "phone": "512-961-6519",
        "email": "info@austinpetsalive.org",
        "website": "https://austinpetsalive.org",
    },
    {
        "name": "San Francisco SPCA",
        "city": "San Francisco",
        "state": "CA",
        "address": "201 Alabama St",
        "phone": "415-522-3500",
        "email": "adopt@sfspca.org",
        "website": "https://sfspca.org",
    },
    {
        "name": "Seattle Humane",
        "city": "Bellevue",
        "state": "WA",
        "address": "13212 SE Eastgate Way",
        "phone": "425-641-0080",
        "email": "info@seattlehumane.org",
        "website": "https://seattlehumane.org",
    },
]

DOG_NAMES = [
    "Max", "Buddy", "Charlie", "Cooper", "Rocky", "Bear", "Duke", "Tucker",
    "Jack", "Oliver", "Bailey", "Bentley", "Milo", "Teddy", "Winston",
    "Luna", "Bella", "Daisy", "Lucy", "Sadie", "Molly", "Bailey", "Maggie",
    "Sophie", "Chloe", "Stella", "Penny", "Zoey", "Coco", "Rosie",
]

CAT_NAMES = [
    "Oliver", "Leo", "Milo", "Charlie", "Max", "Jack", "Simba", "Loki",
    "Oscar", "Jasper", "Buddy", "Tiger", "Smokey", "Shadow", "Felix",
    "Luna", "Bella", "Chloe", "Lucy", "Nala", "Lily", "Kitty", "Callie",
    "Cleo", "Sophie", "Stella", "Willow", "Penny", "Mia", "Gracie",
]

DOG_BREEDS = [
    "Pit Bull Mix", "Labrador Retriever", "German Shepherd", "Chihuahua Mix",
    "Beagle", "Boxer Mix", "Golden Retriever", "Husky Mix", "Border Collie",
    "Australian Shepherd", "Dachshund", "Terrier Mix", "Hound Mix",
    "Shepherd Mix", "Poodle Mix", "Bulldog", "Mastiff Mix", "Great Dane",
]

CAT_BREEDS = [
    "Domestic Shorthair", "Domestic Longhair", "Tabby", "Tuxedo",
    "Orange Tabby", "Siamese Mix", "Maine Coon Mix", "Calico",
    "Black Cat", "Gray Tabby", "White Cat", "Persian Mix",
]

AGES = ["Baby", "Young", "Adult", "Senior"]
GENDERS = ["Male", "Female"]
SIZES = ["Small", "Medium", "Large", "Extra Large"]

DOG_DESCRIPTIONS = [
    "This lovable pup is ready to find their forever home! They enjoy long walks and belly rubs.",
    "A gentle soul who gets along great with other dogs and loves to cuddle on the couch.",
    "Full of energy and always ready for an adventure! Would do best in an active household.",
    "Sweet and affectionate, this dog is looking for someone to shower with love.",
    "Loyal companion who is eager to please. Basic training complete!",
    "A goofy goofball who will keep you laughing. Great with kids of all ages.",
    "Calm and well-mannered, perfect for a quieter home environment.",
    "This pup has a lot of love to give! They're working on their leash manners.",
]

CAT_DESCRIPTIONS = [
    "This sweet kitty is ready to purr their way into your heart!",
    "Independent but affectionate, loves sunny spots and chin scratches.",
    "Playful and curious, this cat will keep you entertained for hours.",
    "A laid-back lap cat who just wants to be your companion.",
    "Gets along with other cats and enjoys watching birds from the window.",
    "Talkative and social, this cat will greet you at the door every day.",
    "Shy at first but warms up quickly with patience and treats.",
    "An expert napper who also enjoys interactive play sessions.",
]


# =============================================================================
# Seeding Functions
# =============================================================================

def seed_shelters(db: Session, clear_existing: bool = False) -> int:
    """Seed shelter data."""
    if clear_existing:
        db.query(Shelter).delete()
        db.commit()
    
    count = 0
    for shelter_data in SAMPLE_SHELTERS:
        # Check if exists
        existing = db.query(Shelter).filter(
            Shelter.name == shelter_data["name"]
        ).first()
        
        if not existing:
            shelter = Shelter(**shelter_data)
            db.add(shelter)
            count += 1
    
    db.commit()
    return count


def seed_animals(
    db: Session,
    count: int = 50,
    clear_existing: bool = False,
) -> int:
    """Seed animal data with realistic wait times."""
    if clear_existing:
        db.query(Animal).delete()
        db.commit()
    
    shelters = db.query(Shelter).all()
    if not shelters:
        seed_shelters(db)
        shelters = db.query(Shelter).all()
    
    animals_added = 0
    today = date.today()
    
    for i in range(count):
        # Mix of dogs and cats
        is_dog = random.random() < 0.6
        
        if is_dog:
            name = random.choice(DOG_NAMES)
            species = "Dog"
            breed = random.choice(DOG_BREEDS)
            description = random.choice(DOG_DESCRIPTIONS)
            names = DOG_NAMES
        else:
            name = random.choice(CAT_NAMES)
            species = "Cat"
            breed = random.choice(CAT_BREEDS)
            description = random.choice(CAT_DESCRIPTIONS)
            names = CAT_NAMES
        
        # Vary wait times - more weight to longer waits for demo
        days_waiting = random.choices(
            [7, 30, 60, 90, 180, 365, 500, 730, 1000],
            weights=[1, 2, 3, 4, 5, 4, 3, 2, 1],
        )[0]
        days_waiting += random.randint(-5, 20)
        intake_date = today - timedelta(days=max(1, days_waiting))
        
        animal = Animal(
            name=f"{name} #{i+1}",
            species=species,
            breed=breed,
            age=random.choice(AGES),
            gender=random.choice(GENDERS),
            size=random.choice(SIZES) if is_dog else None,
            description=description,
            intake_date=intake_date,
            shelter_id=random.choice(shelters).id,
            photo_url=f"https://placedog.net/400/300?id={i}" if is_dog else f"https://placekitten.com/400/300?image={i % 16}",
            external_id=f"SEED-{species[:3].upper()}-{i+1:04d}",
        )
        
        db.add(animal)
        animals_added += 1
    
    db.commit()
    return animals_added


def seed_success_stories(
    db: Session,
    count: int = 10,
    clear_existing: bool = False,
) -> int:
    """Seed success story data."""
    if clear_existing:
        db.query(SuccessStory).delete()
        db.commit()
    
    stories = [
        ("Max found his perfect match!", "After waiting 847 days at the shelter, Max finally found his forever home with the Johnson family. Now he spends his days playing fetch in their big backyard!"),
        ("Luna's journey home", "Luna was shy at first, but with patience and love, she blossomed into the most affectionate cat. Her new mom says she's the best decision she ever made."),
        ("Senior dog finds love", "At 10 years old, Buddy had been waiting for over a year. But the Martinez family saw past his gray muzzle and gave him the retirement he deserved."),
        ("From shelter to celebrity", "Rescued pit bull Rosie is now a certified therapy dog, bringing joy to hospital patients every week!"),
        ("Two cats, one home", "Bonded pair Oliver and Leo found a family willing to adopt them together. They're inseparable!"),
    ]
    
    stories_added = 0
    today = date.today()
    
    for i, (title, story_text) in enumerate(stories[:count]):
        adopted_date = today - timedelta(days=random.randint(30, 365))
        
        story = SuccessStory(
            title=title,
            story=story_text,
            animal_name=title.split()[0],
            adoption_date=adopted_date,
            photo_url=f"https://placedog.net/600/400?id={i + 100}",
        )
        
        db.add(story)
        stories_added += 1
    
    db.commit()
    return stories_added


def seed_all(
    db: Session,
    animals_count: int = 50,
    stories_count: int = 10,
    clear_existing: bool = False,
) -> dict:
    """Seed all sample data."""
    results = {
        "shelters": seed_shelters(db, clear_existing),
        "animals": seed_animals(db, animals_count, clear_existing),
        "success_stories": seed_success_stories(db, stories_count, clear_existing),
    }
    
    return results


# =============================================================================
# CLI Entry Point
# =============================================================================

def main():
    """Run seeding from command line."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Seed database with sample data")
    parser.add_argument("--animals", type=int, default=50, help="Number of animals")
    parser.add_argument("--stories", type=int, default=10, help="Number of stories")
    parser.add_argument("--clear", action="store_true", help="Clear existing data first")
    
    args = parser.parse_args()
    
    from app.database import SessionLocal
    
    db = SessionLocal()
    try:
        results = seed_all(
            db,
            animals_count=args.animals,
            stories_count=args.stories,
            clear_existing=args.clear,
        )
        
        print("Seeding complete!")
        print(f"  Shelters: {results['shelters']}")
        print(f"  Animals: {results['animals']}")
        print(f"  Success Stories: {results['success_stories']}")
        
    finally:
        db.close()


if __name__ == "__main__":
    main()

"""
===============================================================================
Waiting The Longest™ - Seed 100 Dogs Database Script
===============================================================================
Generates 100 hypothetical dogs:
- 2 dogs from each of the 50 US states
- 100 unique dog breeds (no repeats)
- Varying intake dates (from 1 day to 500+ days waiting)
- Realistic shelter names and details
===============================================================================
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timedelta
import random

from app.database import SessionLocal, engine, Base
from app.models import Animal, Observation, Shelter

# =============================================================================
# US States with Cities and Shelter Names
# =============================================================================

US_STATES = [
    ("Alabama", "AL", "Birmingham", "Birmingham Humane Society"),
    ("Alaska", "AK", "Anchorage", "Alaska SPCA"),
    ("Arizona", "AZ", "Phoenix", "Arizona Humane Society"),
    ("Arkansas", "AR", "Little Rock", "Little Rock Animal Village"),
    ("California", "CA", "Los Angeles", "Best Friends LA"),
    ("Colorado", "CO", "Denver", "Denver Dumb Friends League"),
    ("Connecticut", "CT", "Hartford", "Connecticut Humane Society"),
    ("Delaware", "DE", "Wilmington", "Delaware Humane Association"),
    ("Florida", "FL", "Miami", "Miami-Dade Animal Services"),
    ("Georgia", "GA", "Atlanta", "Atlanta Humane Society"),
    ("Hawaii", "HI", "Honolulu", "Hawaiian Humane Society"),
    ("Idaho", "ID", "Boise", "Idaho Humane Society"),
    ("Illinois", "IL", "Chicago", "PAWS Chicago"),
    ("Indiana", "IN", "Indianapolis", "Indianapolis Humane Society"),
    ("Iowa", "IA", "Des Moines", "Animal Rescue League of Iowa"),
    ("Kansas", "KS", "Wichita", "Kansas Humane Society"),
    ("Kentucky", "KY", "Louisville", "Kentucky Humane Society"),
    ("Louisiana", "LA", "New Orleans", "Louisiana SPCA"),
    ("Maine", "ME", "Portland", "Animal Refuge League of Portland"),
    ("Maryland", "MD", "Baltimore", "Baltimore Humane Society"),
    ("Massachusetts", "MA", "Boston", "MSPCA-Angell"),
    ("Michigan", "MI", "Detroit", "Michigan Humane Society"),
    ("Minnesota", "MN", "Minneapolis", "Animal Humane Society MN"),
    ("Mississippi", "MS", "Jackson", "Mississippi Animal Rescue League"),
    ("Missouri", "MO", "Kansas City", "KC Pet Project"),
    ("Montana", "MT", "Billings", "Yellowstone Valley Animal Shelter"),
    ("Nebraska", "NE", "Omaha", "Nebraska Humane Society"),
    ("Nevada", "NV", "Las Vegas", "The Animal Foundation"),
    ("New Hampshire", "NH", "Manchester", "NH SPCA"),
    ("New Jersey", "NJ", "Newark", "Associated Humane Societies"),
    ("New Mexico", "NM", "Albuquerque", "Albuquerque Animal Welfare"),
    ("New York", "NY", "New York City", "ASPCA"),
    ("North Carolina", "NC", "Charlotte", "Humane Society of Charlotte"),
    ("North Dakota", "ND", "Fargo", "CATS Cradle Shelter"),
    ("Ohio", "OH", "Columbus", "Columbus Humane"),
    ("Oklahoma", "OK", "Oklahoma City", "Oklahoma Humane Society"),
    ("Oregon", "OR", "Portland", "Oregon Humane Society"),
    ("Pennsylvania", "PA", "Philadelphia", "PSPCA"),
    ("Rhode Island", "RI", "Providence", "Providence Animal Rescue League"),
    ("South Carolina", "SC", "Charleston", "Charleston Animal Society"),
    ("South Dakota", "SD", "Sioux Falls", "Sioux Falls Area Humane Society"),
    ("Tennessee", "TN", "Nashville", "Nashville Humane Association"),
    ("Texas", "TX", "Houston", "Houston SPCA"),
    ("Utah", "UT", "Salt Lake City", "Best Friends Utah"),
    ("Vermont", "VT", "Burlington", "Humane Society of Chittenden County"),
    ("Virginia", "VA", "Richmond", "Richmond SPCA"),
    ("Washington", "WA", "Seattle", "Seattle Humane"),
    ("West Virginia", "WV", "Charleston", "Kanawha-Charleston Humane"),
    ("Wisconsin", "WI", "Milwaukee", "Wisconsin Humane Society"),
    ("Wyoming", "WY", "Cheyenne", "Cheyenne Animal Shelter"),
]

# =============================================================================
# 100 Unique Dog Breeds
# =============================================================================

DOG_BREEDS = [
    "Labrador Retriever",
    "German Shepherd",
    "Golden Retriever",
    "French Bulldog",
    "Bulldog",
    "Poodle",
    "Beagle",
    "Rottweiler",
    "German Shorthaired Pointer",
    "Dachshund",
    "Pembroke Welsh Corgi",
    "Australian Shepherd",
    "Yorkshire Terrier",
    "Boxer",
    "Cavalier King Charles Spaniel",
    "Doberman Pinscher",
    "Great Dane",
    "Miniature Schnauzer",
    "Siberian Husky",
    "Shih Tzu",
    "Boston Terrier",
    "Bernese Mountain Dog",
    "Pomeranian",
    "Havanese",
    "Shetland Sheepdog",
    "Brittany",
    "English Springer Spaniel",
    "Cocker Spaniel",
    "Miniature American Shepherd",
    "Border Collie",
    "Vizsla",
    "Basset Hound",
    "Mastiff",
    "Belgian Malinois",
    "Chihuahua",
    "Maltese",
    "Weimaraner",
    "Collie",
    "Rhodesian Ridgeback",
    "Shiba Inu",
    "West Highland White Terrier",
    "Bichon Frise",
    "Cane Corso",
    "Newfoundland",
    "Bloodhound",
    "Akita",
    "Portuguese Water Dog",
    "St. Bernard",
    "Papillon",
    "Australian Cattle Dog",
    "Scottish Terrier",
    "Bullmastiff",
    "Samoyed",
    "Soft Coated Wheaten Terrier",
    "Whippet",
    "Dalmatian",
    "Alaskan Malamute",
    "Irish Setter",
    "Chinese Shar-Pei",
    "Airedale Terrier",
    "Wirehaired Pointing Griffon",
    "Bull Terrier",
    "Old English Sheepdog",
    "Great Pyrenees",
    "Chesapeake Bay Retriever",
    "Miniature Pinscher",
    "Italian Greyhound",
    "Cairn Terrier",
    "Irish Wolfhound",
    "Lhasa Apso",
    "Chinese Crested",
    "Basenji",
    "Staffordshire Bull Terrier",
    "Coton de Tulear",
    "English Setter",
    "American Staffordshire Terrier",
    "Standard Schnauzer",
    "Giant Schnauzer",
    "Gordon Setter",
    "Leonberger",
    "Cardigan Welsh Corgi",
    "Toy Fox Terrier",
    "Norwich Terrier",
    "Keeshond",
    "Border Terrier",
    "English Cocker Spaniel",
    "Flat-Coated Retriever",
    "Bouvier des Flandres",
    "Rat Terrier",
    "Belgian Tervuren",
    "Tibetan Terrier",
    "Norwegian Elkhound",
    "Silky Terrier",
    "Spinone Italiano",
    "Welsh Springer Spaniel",
    "Afghan Hound",
    "Japanese Chin",
    "Clumber Spaniel",
    "Boykin Spaniel",
    "Canaan Dog",
]

# =============================================================================
# Dog Names (200 to pick from)
# =============================================================================

DOG_NAMES = [
    "Max", "Bella", "Charlie", "Luna", "Cooper", "Daisy", "Buddy", "Sadie",
    "Rocky", "Molly", "Bear", "Bailey", "Duke", "Maggie", "Tucker", "Sophie",
    "Jack", "Chloe", "Oliver", "Penny", "Leo", "Zoey", "Milo", "Stella",
    "Zeus", "Lily", "Winston", "Lola", "Finn", "Gracie", "Murphy", "Nala",
    "Louie", "Ruby", "Beau", "Rosie", "Bentley", "Ellie", "Teddy", "Mia",
    "Bruno", "Willow", "Henry", "Coco", "Apollo", "Roxy", "Archie", "Pepper",
    "Oscar", "Ginger", "Toby", "Abby", "Riley", "Piper", "Gus", "Honey",
    "Hank", "Scout", "Sam", "Hazel", "Blue", "Annie", "Diesel", "Izzy",
    "Thor", "Lady", "Ace", "Winnie", "Shadow", "Olive", "Tank", "Emma",
    "Rufus", "Princess", "Jax", "Lucy", "Hunter", "Callie", "Boomer", "Josie",
    "Cash", "Phoebe", "Jasper", "Sasha", "Jake", "Dixie", "Buster", "Maddie",
    "Rex", "Harper", "Chewy", "Athena", "Moose", "Angel", "Rocco", "Belle",
    "Bubba", "Gemma", "Lucky", "Layla", "Bandit", "Sydney", "Prince", "Ivy",
    "Chief", "Dakota", "Marley", "Fiona", "Gunner", "Georgia", "Maverick", "Pearl",
    "Zeke", "Millie", "Ranger", "Holly", "Samson", "Lexi", "Bo", "Heidi",
    "Cody", "Maya", "Otis", "Aurora", "Scout", "Shelby", "Duke", "Bonnie",
]

# =============================================================================
# Age Groups and Sizes
# =============================================================================

AGE_GROUPS = ["puppy", "young", "adult", "senior"]
SIZES = ["small", "medium", "large", "xlarge"]
GENDERS = ["male", "female"]

# Breed size mapping (approximate)
BREED_SIZES = {
    "Chihuahua": "small", "Yorkshire Terrier": "small", "Maltese": "small",
    "Pomeranian": "small", "Shih Tzu": "small", "Papillon": "small",
    "Toy Fox Terrier": "small", "Japanese Chin": "small", "Chinese Crested": "small",
    "Miniature Pinscher": "small", "Italian Greyhound": "small", "Silky Terrier": "small",
    
    "French Bulldog": "medium", "Beagle": "medium", "Cocker Spaniel": "medium",
    "Dachshund": "medium", "Pembroke Welsh Corgi": "medium", "Boston Terrier": "medium",
    "Cavalier King Charles Spaniel": "medium", "Shetland Sheepdog": "medium",
    "Miniature Schnauzer": "medium", "Havanese": "medium", "Bichon Frise": "medium",
    "West Highland White Terrier": "medium", "Scottish Terrier": "medium",
    "Basenji": "medium", "Whippet": "medium", "Bull Terrier": "medium",
    "Cairn Terrier": "medium", "Lhasa Apso": "medium", "Border Terrier": "medium",
    "Norwich Terrier": "medium", "Rat Terrier": "medium", "Tibetan Terrier": "medium",
    "Shiba Inu": "medium", "Cardigan Welsh Corgi": "medium", "Coton de Tulear": "medium",
    "Staffordshire Bull Terrier": "medium", "Brittany": "medium",
    
    "Labrador Retriever": "large", "German Shepherd": "large", "Golden Retriever": "large",
    "Poodle": "large", "Rottweiler": "large", "Boxer": "large", "Doberman Pinscher": "large",
    "Siberian Husky": "large", "Australian Shepherd": "large", "Border Collie": "large",
    "Bernese Mountain Dog": "large", "Weimaraner": "large", "Rhodesian Ridgeback": "large",
    "Belgian Malinois": "large", "Collie": "large", "Vizsla": "large",
    "German Shorthaired Pointer": "large", "English Springer Spaniel": "large",
    "Portuguese Water Dog": "large", "Dalmatian": "large", "Irish Setter": "large",
    "Airedale Terrier": "large", "Chesapeake Bay Retriever": "large",
    "Old English Sheepdog": "large", "Australian Cattle Dog": "large",
    "Samoyed": "large", "Alaskan Malamute": "large", "Akita": "large",
    "Chinese Shar-Pei": "large", "Soft Coated Wheaten Terrier": "large",
    "Flat-Coated Retriever": "large", "Gordon Setter": "large", "English Setter": "large",
    "Wirehaired Pointing Griffon": "large", "Belgian Tervuren": "large",
    "Norwegian Elkhound": "large", "Boykin Spaniel": "large", "Keeshond": "large",
    "Welsh Springer Spaniel": "large", "Spinone Italiano": "large",
    "English Cocker Spaniel": "large", "American Staffordshire Terrier": "large",
    "Standard Schnauzer": "large", "Clumber Spaniel": "large", "Canaan Dog": "large",
    
    "Great Dane": "xlarge", "Mastiff": "xlarge", "St. Bernard": "xlarge",
    "Newfoundland": "xlarge", "Irish Wolfhound": "xlarge", "Great Pyrenees": "xlarge",
    "Cane Corso": "xlarge", "Bullmastiff": "xlarge", "Leonberger": "xlarge",
    "Bloodhound": "xlarge", "Giant Schnauzer": "xlarge", "Bouvier des Flandres": "xlarge",
    "Afghan Hound": "xlarge", "Bulldog": "medium",
    "Basset Hound": "medium", "Miniature American Shepherd": "medium",
}

# =============================================================================
# Photo URLs (Unsplash dog images - royalty free)
# =============================================================================

def get_dog_photo_url(breed_index):
    """Generate a placeholder photo URL for dogs"""
    # Using placeholder service with dog images
    photo_ids = [
        "https://images.unsplash.com/photo-1587300003388-59208cc962cb?w=400",
        "https://images.unsplash.com/photo-1517849845537-4d257902454a?w=400",
        "https://images.unsplash.com/photo-1583511655857-d19b40a7a54e?w=400",
        "https://images.unsplash.com/photo-1477884213360-7e9d7dcc1e48?w=400",
        "https://images.unsplash.com/photo-1548199973-03cce0bbc87b?w=400",
        "https://images.unsplash.com/photo-1561037404-61cd46aa615b?w=400",
        "https://images.unsplash.com/photo-1587559045816-8b0a54d1a52d?w=400",
        "https://images.unsplash.com/photo-1544568100-847a948585b9?w=400",
        "https://images.unsplash.com/photo-1592754862816-1a21a4ea2281?w=400",
        "https://images.unsplash.com/photo-1601758123927-4f7f3a4c8f2b?w=400",
        "https://images.unsplash.com/photo-1558788353-f76d92427f16?w=400",
        "https://images.unsplash.com/photo-1552053831-71594a27632d?w=400",
        "https://images.unsplash.com/photo-1534361960057-19889db9621e?w=400",
        "https://images.unsplash.com/photo-1518717758536-85ae29035b6d?w=400",
        "https://images.unsplash.com/photo-1596492784531-6e6eb5ea9993?w=400",
        "https://images.unsplash.com/photo-1586671267731-da2cf3ceeb80?w=400",
        "https://images.unsplash.com/photo-1560807707-8cc77767d783?w=400",
        "https://images.unsplash.com/photo-1537151625747-768eb6cf92b2?w=400",
        "https://images.unsplash.com/photo-1583512603805-3cc6b41f3edb?w=400",
        "https://images.unsplash.com/photo-1588943211346-0908a1fb0b01?w=400",
    ]
    return photo_ids[breed_index % len(photo_ids)]


# =============================================================================
# Description Templates
# =============================================================================

DESCRIPTION_TEMPLATES = [
    "{name} is a wonderful {age} {breed} who has been patiently waiting for a forever home. {pronoun_cap} loves {activity1} and {activity2}. This sweet {gender} would make a perfect addition to any loving family!",
    "Meet {name}, an adorable {age} {breed} looking for {pronoun} forever family! {pronoun_cap} enjoys {activity1} and is known for {pronoun} {trait}. {name} would thrive in a home with {home_type}.",
    "Say hello to {name}! This charming {age} {breed} is ready to find a loving home. {pronoun_cap} is {trait} and loves nothing more than {activity1}. Give {name} the second chance {pronoun} deserves!",
    "{name} is a {trait} {age} {breed} who dreams of finding {pronoun} forever family. {pronoun_cap} enjoys {activity1} and gets along well with {companion}. Don't let this special {gender} wait any longer!",
    "Looking for a loyal companion? {name} is a {age} {breed} with a heart of gold. This {trait} {gender} loves {activity1} and would be perfect for {home_type}. Come meet {name} today!",
]

ACTIVITIES = [
    "going for walks", "playing fetch", "cuddling on the couch", "exploring the backyard",
    "learning new tricks", "meeting new friends", "car rides", "belly rubs",
    "playing with toys", "hiking adventures", "swimming", "sunbathing",
]

TRAITS = [
    "gentle", "playful", "affectionate", "loyal", "curious", "friendly",
    "calm", "energetic", "smart", "sweet", "brave", "loving",
]

COMPANIONS = ["other dogs", "children", "cats", "everyone"]
HOME_TYPES = ["an active family", "a quiet home", "someone who loves outdoor activities", "a family with a yard"]


def generate_description(name, breed, age_group, gender):
    """Generate a unique description for a dog"""
    template = random.choice(DESCRIPTION_TEMPLATES)
    pronoun = "he" if gender == "male" else "she"
    pronoun_cap = pronoun.capitalize()
    
    age_text = {
        "puppy": "young puppy",
        "young": "young adult",
        "adult": "adult",
        "senior": "senior",
    }.get(age_group, "adult")
    
    return template.format(
        name=name,
        breed=breed,
        age=age_text,
        gender=gender,
        pronoun=pronoun,
        pronoun_cap=pronoun_cap,
        activity1=random.choice(ACTIVITIES),
        activity2=random.choice(ACTIVITIES),
        trait=random.choice(TRAITS),
        companion=random.choice(COMPANIONS),
        home_type=random.choice(HOME_TYPES),
    )


# =============================================================================
# Main Seed Function
# =============================================================================

def seed_100_dogs():
    """Seed the database with 100 dogs (2 per state, 100 unique breeds)"""
    
    print("=" * 70)
    print("Waiting The Longest™ - Seeding 100 Dogs")
    print("=" * 70)
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    try:
        # Clear existing data
        print("\n🗑️  Clearing existing data...")
        db.query(Observation).delete()
        db.query(Animal).delete()
        db.query(Shelter).delete()
        db.commit()
        print("   ✓ Database cleared")
        
        # Create shelters (one per state)
        print("\n🏠 Creating shelters...")
        shelters = {}
        for state_name, state_abbr, city, shelter_name in US_STATES:
            shelter = Shelter(
                name=shelter_name,
                city=city,
                state=state_abbr,
                source="seed_script",
                external_id=f"shelter_{state_abbr.lower()}",
            )
            db.add(shelter)
            db.flush()
            shelters[state_abbr] = shelter
        db.commit()
        print(f"   ✓ Created {len(shelters)} shelters")
        
        # Generate 100 dogs
        print("\n🐕 Generating 100 dogs...")
        
        # Shuffle breeds to randomize assignment
        breeds = DOG_BREEDS.copy()
        random.shuffle(breeds)
        
        # Used names tracker
        used_names = set()
        
        today = datetime.utcnow()
        dogs_created = 0
        
        for i, (state_name, state_abbr, city, shelter_name) in enumerate(US_STATES):
            # 2 dogs per state
            for j in range(2):
                breed_index = i * 2 + j
                breed = breeds[breed_index]
                
                # Pick a unique name
                name = random.choice([n for n in DOG_NAMES if n not in used_names])
                used_names.add(name)
                
                # Determine attributes
                gender = random.choice(GENDERS)
                age_group = random.choice(AGE_GROUPS)
                size = BREED_SIZES.get(breed, "medium")
                
                # Generate varying intake dates (1-500 days ago)
                # Weight towards longer waits for dramatic effect
                if breed_index < 10:
                    days_ago = random.randint(300, 500)  # Longest waiters
                elif breed_index < 30:
                    days_ago = random.randint(150, 299)  # Long waiters
                elif breed_index < 60:
                    days_ago = random.randint(60, 149)   # Medium waiters
                else:
                    days_ago = random.randint(1, 59)     # Recent arrivals
                
                first_seen = today - timedelta(days=days_ago)
                
                # Create animal
                animal = Animal(
                    species="dog",
                    canonical_name=name,
                    first_seen_at=first_seen,
                    last_seen_at=today,
                    status="available",
                    breed_primary=breed,
                    age_group=age_group,
                    size=size,
                    gender=gender,
                )
                db.add(animal)
                db.flush()
                
                # Create observation
                observation = Observation(
                    animal_id=animal.id,
                    source="seed_script",
                    external_id=f"dog_{breed_index + 1:03d}",
                    shelter_id=shelters[state_abbr].id,
                    shelter_name=shelter_name,
                    name=name,
                    breed_primary=breed,
                    description=generate_description(name, breed, age_group, gender),
                    photo_url=get_dog_photo_url(breed_index),
                    city=city,
                    state=state_abbr,
                    first_seen_at=first_seen,
                    last_seen_at=today,
                )
                db.add(observation)
                
                dogs_created += 1
                print(f"   {dogs_created:3d}. {name} - {breed} ({city}, {state_abbr}) - {days_ago} days")
        
        db.commit()
        
        print("\n" + "=" * 70)
        print(f"✅ Successfully created {dogs_created} dogs!")
        print(f"   - 2 dogs per state across all 50 US states")
        print(f"   - 100 unique dog breeds")
        print(f"   - Wait times ranging from 1 to 500+ days")
        print("=" * 70)
        
        # Print summary by wait time
        print("\n📊 Summary by Wait Time:")
        print(f"   - 300-500 days (urgent): 10 dogs")
        print(f"   - 150-299 days (long): 20 dogs")
        print(f"   - 60-149 days (medium): 30 dogs")
        print(f"   - 1-59 days (recent): 40 dogs")
        
        return True
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        db.close()


if __name__ == "__main__":
    seed_100_dogs()

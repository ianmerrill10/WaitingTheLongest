"""
===============================================================================
Waiting The Longest™ - Test Fixtures and Factories
===============================================================================
Purpose: Shared test fixtures and data factories for testing.
         Creates realistic test data for all models.

Author: Waiting The Longest™ Development Team
===============================================================================
"""

import random
import string
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from faker import Faker

fake = Faker()


class AnimalFactory:
    """Factory for creating test animal data."""
    
    DOG_BREEDS = [
        "Labrador Retriever", "German Shepherd", "Golden Retriever",
        "French Bulldog", "Bulldog", "Poodle", "Beagle", "Rottweiler",
        "German Shorthaired Pointer", "Dachshund", "Pembroke Welsh Corgi",
        "Australian Shepherd", "Yorkshire Terrier", "Boxer", "Great Dane",
        "Siberian Husky", "Cavalier King Charles Spaniel", "Doberman Pinscher",
        "Shih Tzu", "Boston Terrier", "Havanese", "Bernese Mountain Dog",
        "Pomeranian", "Shetland Sheepdog", "Brittany", "English Springer Spaniel",
        "Pit Bull Terrier", "Mixed Breed"
    ]
    
    CAT_BREEDS = [
        "Domestic Shorthair", "Domestic Longhair", "Maine Coon", "Ragdoll",
        "British Shorthair", "Persian", "Abyssinian", "Bengal", "Siamese",
        "Sphynx", "Scottish Fold", "Russian Blue", "American Shorthair",
        "Birman", "Norwegian Forest Cat", "Devon Rex", "Oriental Shorthair",
        "Burmese", "Exotic Shorthair", "Mixed Breed"
    ]
    
    COLORS = [
        "Black", "White", "Brown", "Tan", "Gold", "Gray", "Orange",
        "Cream", "Red", "Brindle", "Spotted", "Tuxedo", "Calico", "Tabby"
    ]
    
    @classmethod
    def create(
        cls,
        species: Optional[str] = None,
        days_waiting: Optional[int] = None,
        **overrides
    ) -> Dict[str, Any]:
        """
        Create a realistic test animal.
        
        Args:
            species: "dog" or "cat" (random if not specified)
            days_waiting: Days in shelter (random if not specified)
            **overrides: Any fields to override
            
        Returns:
            Animal data dictionary
        """
        species = species or random.choice(["dog", "cat"])
        
        if days_waiting is None:
            # Most animals 30-300 days, some longer
            days_waiting = random.choices(
                [random.randint(1, 30), random.randint(30, 100), 
                 random.randint(100, 300), random.randint(300, 1000)],
                weights=[20, 40, 30, 10]
            )[0]
        
        intake_date = datetime.now(timezone.utc) - timedelta(days=days_waiting)
        
        breeds = cls.DOG_BREEDS if species == "dog" else cls.CAT_BREEDS
        
        age_groups = {
            "dog": ["puppy", "young", "adult", "senior"],
            "cat": ["kitten", "young", "adult", "senior"]
        }
        
        sizes = ["small", "medium", "large", "extra large"] if species == "dog" else ["small", "medium", "large"]
        
        animal = {
            "name": fake.first_name(),
            "canonical_name": None,  # Set below
            "species": species,
            "breed_primary": random.choice(breeds),
            "breed_secondary": random.choice([None, random.choice(breeds)]),
            "age_group": random.choice(age_groups[species]),
            "size": random.choice(sizes),
            "gender": random.choice(["male", "female"]),
            "color_primary": random.choice(cls.COLORS),
            "color_secondary": random.choice([None, random.choice(cls.COLORS)]),
            "intake_date": intake_date.isoformat(),
            "days_waiting": days_waiting,
            "status": "available",
            "spayed_neutered": random.choice([True, False]),
            "vaccinated": random.choice([True, False]),
            "good_with_dogs": random.choice([True, False, None]),
            "good_with_cats": random.choice([True, False, None]),
            "good_with_children": random.choice([True, False, None]),
            "house_trained": random.choice([True, False, None]),
            "special_needs": random.choice([False, False, False, True]),  # 25% chance
            "description": fake.paragraph(nb_sentences=3),
            "photo_url": f"https://placedog.net/400/300?id={random.randint(1, 1000)}" if species == "dog" else f"https://placekitten.com/400/300",
            "city": fake.city(),
            "state": fake.state_abbr(),
            "zip_code": fake.zipcode(),
            "shelter_id": random.randint(1, 50),
            "external_id": f"test-{random.randint(10000, 99999)}",
            "source": "test_factory"
        }
        
        animal["canonical_name"] = animal["name"]
        animal.update(overrides)
        
        return animal
    
    @classmethod
    def create_batch(cls, count: int = 10, **kwargs) -> List[Dict[str, Any]]:
        """Create multiple test animals."""
        return [cls.create(**kwargs) for _ in range(count)]
    
    @classmethod
    def create_long_waiting(cls, min_days: int = 365, **kwargs) -> Dict[str, Any]:
        """Create an animal that has been waiting a long time."""
        days = random.randint(min_days, min_days + 200)
        return cls.create(days_waiting=days, **kwargs)


class ShelterFactory:
    """Factory for creating test shelter data."""
    
    SHELTER_TYPES = ["Municipal", "Private", "Rescue", "Foster Network", "SPCA", "Humane Society"]
    
    @classmethod
    def create(cls, **overrides) -> Dict[str, Any]:
        """Create a realistic test shelter."""
        shelter = {
            "name": f"{fake.city()} {random.choice(cls.SHELTER_TYPES)}",
            "address": fake.street_address(),
            "city": fake.city(),
            "state": fake.state_abbr(),
            "zip_code": fake.zipcode(),
            "phone": fake.phone_number(),
            "email": fake.company_email(),
            "website": fake.url(),
            "latitude": float(fake.latitude()),
            "longitude": float(fake.longitude()),
            "active": True,
            "external_id": f"shelter-{random.randint(1000, 9999)}",
            "source": "test_factory"
        }
        shelter.update(overrides)
        return shelter
    
    @classmethod
    def create_batch(cls, count: int = 5, **kwargs) -> List[Dict[str, Any]]:
        """Create multiple test shelters."""
        return [cls.create(**kwargs) for _ in range(count)]


class SuccessStoryFactory:
    """Factory for creating test success stories."""
    
    @classmethod
    def create(cls, animal: Optional[Dict[str, Any]] = None, **overrides) -> Dict[str, Any]:
        """Create a realistic test success story."""
        if animal is None:
            animal = AnimalFactory.create(status="adopted")
        
        story = {
            "animal_id": animal.get("id", random.randint(1, 1000)),
            "pet_name": animal.get("name", fake.first_name()),
            "adopter_name": fake.first_name(),
            "days_waited": animal.get("days_waiting", random.randint(30, 500)),
            "story_text": fake.paragraph(nb_sentences=5),
            "photo_url": animal.get("photo_url"),
            "adoption_date": (datetime.now(timezone.utc) - timedelta(days=random.randint(1, 30))).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "approved": True,
            "featured": random.choice([True, False])
        }
        story.update(overrides)
        return story
    
    @classmethod
    def create_batch(cls, count: int = 5, **kwargs) -> List[Dict[str, Any]]:
        """Create multiple test success stories."""
        return [cls.create(**kwargs) for _ in range(count)]


class NewsletterSubscriberFactory:
    """Factory for creating test newsletter subscribers."""
    
    @classmethod
    def create(cls, **overrides) -> Dict[str, Any]:
        """Create a test subscriber."""
        subscriber = {
            "email": fake.email(),
            "name": fake.name(),
            "subscribed_at": datetime.now(timezone.utc).isoformat(),
            "verified": random.choice([True, False]),
            "unsubscribed": False,
            "preferences": {
                "weekly_digest": True,
                "success_stories": True,
                "new_arrivals": random.choice([True, False]),
                "shelter_updates": random.choice([True, False])
            }
        }
        subscriber.update(overrides)
        return subscriber


class UserFactory:
    """Factory for creating test users."""
    
    @classmethod
    def create(cls, **overrides) -> Dict[str, Any]:
        """Create a test user."""
        user = {
            "email": fake.email(),
            "username": fake.user_name(),
            "password_hash": "test_hash_" + ''.join(random.choices(string.ascii_lowercase, k=20)),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "is_active": True,
            "is_admin": False,
            "is_shelter_staff": random.choice([True, False]),
            "shelter_id": random.randint(1, 50) if random.random() > 0.7 else None
        }
        user.update(overrides)
        return user


# Utility functions

def generate_test_database_seed() -> Dict[str, List[Dict[str, Any]]]:
    """Generate a complete test database seed."""
    shelters = ShelterFactory.create_batch(20)
    
    # Create animals associated with shelters
    animals = []
    for shelter in shelters:
        count = random.randint(5, 25)
        shelter_animals = AnimalFactory.create_batch(
            count, 
            shelter_id=shelter.get("id", random.randint(1, 20))
        )
        animals.extend(shelter_animals)
    
    # Create some long-waiting animals
    for _ in range(10):
        animals.append(AnimalFactory.create_long_waiting())
    
    # Create success stories from adopted animals
    adopted = random.sample(animals, min(15, len(animals)))
    stories = [
        SuccessStoryFactory.create(animal=a) 
        for a in adopted
    ]
    
    subscribers = [NewsletterSubscriberFactory.create() for _ in range(100)]
    
    return {
        "shelters": shelters,
        "animals": animals,
        "success_stories": stories,
        "newsletter_subscribers": subscribers
    }

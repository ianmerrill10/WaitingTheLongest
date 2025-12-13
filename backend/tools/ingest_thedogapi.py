#!/usr/bin/env python3
"""
===============================================================================
TheDogAPI Data Ingestor
===============================================================================
Fetches comprehensive dog breed data from TheDogAPI.com for the Knowledge
Library and Training sections.

API Documentation: https://thedogapi.com/
Rate Limits: 100 req/60s, 200 burst, 10,000/month

Usage:
    python ingest_thedogapi.py --breeds      # Fetch all breed data
    python ingest_thedogapi.py --images      # Fetch additional images
    python ingest_thedogapi.py --all         # Fetch everything

Author: Waiting The Longest™ Development Team
===============================================================================
"""
import sys
import os
import argparse
import requests
import time
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.config import settings
from app.database import SessionLocal, init_db
from app.models import DogBreed, DogBreedImage, DogFact, DogHealthTip


# TheDogAPI Configuration
BASE_URL = "https://api.thedogapi.com/v1"
API_KEY = settings.THEDOGAPI_KEY

# Rate limiting
REQUEST_DELAY = 0.6  # 60 seconds / 100 requests = 0.6s between requests


def make_request(endpoint: str, params: Dict = None) -> Optional[Dict]:
    """Make a rate-limited request to TheDogAPI."""
    if not API_KEY:
        print("ERROR: THEDOGAPI_KEY not configured!")
        return None

    headers = {
        "x-api-key": API_KEY
    }

    url = f"{BASE_URL}/{endpoint}"

    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        time.sleep(REQUEST_DELAY)  # Rate limiting
        return response.json()
    except requests.RequestException as e:
        print(f"  ERROR: API request failed: {e}")
        return None


def fetch_all_breeds() -> List[Dict]:
    """Fetch all dog breeds from TheDogAPI."""
    print("Fetching all dog breeds...")

    breeds = make_request("breeds")

    if breeds:
        print(f"  Found {len(breeds)} breeds")
        return breeds
    return []


def fetch_breed_images(breed_id: int, limit: int = 10) -> List[Dict]:
    """Fetch additional images for a specific breed."""
    params = {
        "breed_id": breed_id,
        "limit": limit
    }

    images = make_request("images/search", params)
    return images or []


def infer_exercise_needs(temperament: str, bred_for: str, breed_group: str) -> str:
    """Infer exercise needs from temperament and breeding purpose."""
    if not temperament and not bred_for:
        return "Medium"

    text = f"{temperament or ''} {bred_for or ''} {breed_group or ''}".lower()

    high_energy_keywords = [
        "energetic", "active", "athletic", "working", "herding", "hunting",
        "racing", "sledding", "agile", "playful", "spirited", "tireless"
    ]

    low_energy_keywords = [
        "calm", "gentle", "relaxed", "lazy", "quiet", "docile",
        "companion", "lap dog", "toy"
    ]

    high_score = sum(1 for kw in high_energy_keywords if kw in text)
    low_score = sum(1 for kw in low_energy_keywords if kw in text)

    if high_score > low_score + 1:
        return "High"
    elif low_score > high_score + 1:
        return "Low"
    return "Medium"


def infer_grooming_needs(temperament: str, bred_for: str) -> str:
    """Infer grooming needs (basic heuristic)."""
    # This is a simple heuristic - would be better with actual coat data
    return "Medium"  # Default to medium


def infer_good_with_kids(temperament: str) -> Optional[bool]:
    """Infer if breed is good with kids from temperament."""
    if not temperament:
        return None

    text = temperament.lower()

    good_keywords = ["gentle", "friendly", "patient", "good-natured", "loving", "playful"]
    bad_keywords = ["aggressive", "suspicious", "reserved", "aloof", "protective"]

    good_score = sum(1 for kw in good_keywords if kw in text)
    bad_score = sum(1 for kw in bad_keywords if kw in text)

    if good_score > bad_score:
        return True
    elif bad_score > good_score:
        return False
    return None


def infer_apartment_friendly(weight: str, temperament: str) -> Optional[bool]:
    """Infer if breed is apartment friendly."""
    if not weight:
        return None

    # Parse weight (e.g., "55 - 70")
    try:
        parts = weight.replace(" ", "").split("-")
        max_weight = int(parts[-1]) if parts else 50
    except:
        max_weight = 50

    text = (temperament or "").lower()

    # Small dogs or calm large dogs can be apartment friendly
    if max_weight < 25:
        return True
    elif max_weight > 60 and "energetic" in text:
        return False
    elif "calm" in text or "quiet" in text or "gentle" in text:
        return True

    return max_weight < 40


def generate_description(breed: Dict) -> str:
    """Generate a description for the breed."""
    name = breed.get("name", "Unknown")
    temperament = breed.get("temperament", "")
    bred_for = breed.get("bred_for", "")
    life_span = breed.get("life_span", "")
    origin = breed.get("origin", "")
    breed_group = breed.get("breed_group", "")

    parts = [f"The {name}"]

    if breed_group:
        parts.append(f"belongs to the {breed_group} group")

    if origin:
        parts.append(f"and originates from {origin}")

    parts.append(".")

    if temperament:
        parts.append(f"Known for being {temperament.lower()},")

    if bred_for:
        parts.append(f"this breed was originally bred for {bred_for.lower()}.")

    if life_span:
        parts.append(f"The typical life span is {life_span}.")

    return " ".join(parts).replace("  ", " ").replace(" ,", ",").replace(" .", ".")


def generate_training_tips(breed: Dict) -> str:
    """Generate training tips based on temperament."""
    temperament = (breed.get("temperament") or "").lower()
    name = breed.get("name", "this breed")

    tips = [f"Training a {name} can be rewarding with the right approach."]

    if "intelligent" in temperament or "smart" in temperament:
        tips.append("This intelligent breed responds well to mental stimulation and puzzle toys.")

    if "stubborn" in temperament or "independent" in temperament:
        tips.append("Patience and consistency are key, as this breed can be independent-minded.")

    if "eager to please" in temperament or "loyal" in temperament:
        tips.append("Positive reinforcement works exceptionally well with this eager-to-please breed.")

    if "energetic" in temperament or "active" in temperament:
        tips.append("Incorporate plenty of physical exercise alongside training sessions.")

    if "sensitive" in temperament or "gentle" in temperament:
        tips.append("Use gentle, positive methods as this breed is sensitive to harsh corrections.")

    if "protective" in temperament or "alert" in temperament:
        tips.append("Early socialization is important to ensure a well-rounded temperament.")

    tips.append("Start training early and keep sessions short but frequent for best results.")

    return " ".join(tips)


def save_breed_to_db(db, breed_data: Dict) -> Optional[DogBreed]:
    """Save or update a breed in the database."""
    external_id = breed_data.get("id")

    # Check if breed already exists
    existing = db.query(DogBreed).filter(DogBreed.external_id == external_id).first()

    # Extract height/weight
    height = breed_data.get("height", {})
    weight = breed_data.get("weight", {})
    image = breed_data.get("image", {})

    temperament = breed_data.get("temperament")
    bred_for = breed_data.get("bred_for")
    breed_group = breed_data.get("breed_group")

    # Infer additional attributes
    exercise_needs = infer_exercise_needs(temperament, bred_for, breed_group)
    grooming_needs = infer_grooming_needs(temperament, bred_for)
    good_with_kids = infer_good_with_kids(temperament)
    apartment_friendly = infer_apartment_friendly(weight.get("imperial"), temperament)

    # Generate content
    description = generate_description(breed_data)
    training_tips = generate_training_tips(breed_data)

    breed_values = {
        "external_id": external_id,
        "name": breed_data.get("name"),
        "breed_group": breed_group,
        "height_imperial": height.get("imperial"),
        "height_metric": height.get("metric"),
        "weight_imperial": weight.get("imperial"),
        "weight_metric": weight.get("metric"),
        "life_span": breed_data.get("life_span"),
        "temperament": temperament,
        "origin": breed_data.get("origin"),
        "bred_for": bred_for,
        "image_url": image.get("url"),
        "image_id": image.get("id"),
        "reference_url": breed_data.get("reference_image_id"),
        "description": description,
        "training_tips": training_tips,
        "exercise_needs": exercise_needs,
        "grooming_needs": grooming_needs,
        "good_with_kids": good_with_kids,
        "apartment_friendly": apartment_friendly,
        "updated_at": datetime.utcnow()
    }

    if existing:
        for key, value in breed_values.items():
            setattr(existing, key, value)
        return existing
    else:
        new_breed = DogBreed(**breed_values)
        db.add(new_breed)
        return new_breed


def save_image_to_db(db, breed_id: int, image_data: Dict) -> Optional[DogBreedImage]:
    """Save a breed image to the database."""
    image_id = image_data.get("id")

    # Check if image already exists
    existing = db.query(DogBreedImage).filter(DogBreedImage.image_id == image_id).first()
    if existing:
        return existing

    new_image = DogBreedImage(
        breed_id=breed_id,
        image_id=image_id,
        url=image_data.get("url"),
        width=image_data.get("width"),
        height=image_data.get("height")
    )
    db.add(new_image)
    return new_image


def ingest_breeds(db):
    """Ingest all breeds from TheDogAPI."""
    print("\n" + "=" * 60)
    print("INGESTING DOG BREEDS FROM THEDOGAPI")
    print("=" * 60)

    breeds = fetch_all_breeds()

    if not breeds:
        print("No breeds found or API error")
        return 0

    count = 0
    for breed in breeds:
        name = breed.get("name", "Unknown")
        try:
            save_breed_to_db(db, breed)
            count += 1
            print(f"  [{count}/{len(breeds)}] {name}")
        except Exception as e:
            print(f"  ERROR saving {name}: {e}")

    db.commit()
    print(f"\nSaved {count} breeds to database")
    return count


def ingest_images(db, images_per_breed: int = 5):
    """Ingest additional images for each breed."""
    print("\n" + "=" * 60)
    print("INGESTING BREED IMAGES FROM THEDOGAPI")
    print("=" * 60)

    breeds = db.query(DogBreed).all()
    print(f"Found {len(breeds)} breeds in database")

    total_images = 0

    for i, breed in enumerate(breeds):
        print(f"  [{i+1}/{len(breeds)}] Fetching images for {breed.name}...")

        images = fetch_breed_images(breed.external_id, limit=images_per_breed)

        for img in images:
            try:
                save_image_to_db(db, breed.id, img)
                total_images += 1
            except Exception as e:
                print(f"    ERROR saving image: {e}")

        # Commit every 10 breeds
        if (i + 1) % 10 == 0:
            db.commit()

    db.commit()
    print(f"\nSaved {total_images} images to database")
    return total_images


def export_breeds_json(db, output_path: str = "data/dog_breeds.json"):
    """Export all breed data to JSON for frontend use."""
    print("\n" + "=" * 60)
    print("EXPORTING BREEDS TO JSON")
    print("=" * 60)

    breeds = db.query(DogBreed).all()

    export_data = []
    for breed in breeds:
        export_data.append({
            "id": breed.id,
            "external_id": breed.external_id,
            "name": breed.name,
            "breed_group": breed.breed_group,
            "height": {
                "imperial": breed.height_imperial,
                "metric": breed.height_metric
            },
            "weight": {
                "imperial": breed.weight_imperial,
                "metric": breed.weight_metric
            },
            "life_span": breed.life_span,
            "temperament": breed.temperament,
            "origin": breed.origin,
            "bred_for": breed.bred_for,
            "image_url": breed.image_url,
            "description": breed.description,
            "training_tips": breed.training_tips,
            "exercise_needs": breed.exercise_needs,
            "grooming_needs": breed.grooming_needs,
            "good_with_kids": breed.good_with_kids,
            "apartment_friendly": breed.apartment_friendly
        })

    # Ensure directory exists
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)

    print(f"Exported {len(export_data)} breeds to {output_path}")


def fetch_random_facts(limit: int = 100) -> List[Dict]:
    """Fetch random dog facts from TheDogAPI."""
    print(f"Fetching {limit} random dog facts...")

    facts = make_request("facts", {"limit": limit})

    if facts:
        print(f"  Found {len(facts)} facts")
        return facts
    return []


def fetch_breed_facts(breed_id: int, limit: int = 10) -> List[Dict]:
    """Fetch facts for a specific breed."""
    facts = make_request(f"breeds/{breed_id}/facts", {"limit": limit})
    return facts or []


def fetch_health_tips(limit: int = 100, offset: int = 0) -> List[Dict]:
    """Fetch dog health tips from TheDogAPI."""
    print(f"Fetching health tips (limit={limit}, offset={offset})...")

    params = {
        "limit": limit,
        "offset": offset,
        "include_sources": "true"
    }

    tips = make_request("health-tips", params)

    if tips:
        print(f"  Found {len(tips)} health tips")
        return tips
    return []


def save_fact_to_db(db, fact_data: Dict, breed_db_id: int = None) -> Optional[DogFact]:
    """Save a dog fact to the database."""
    external_id = fact_data.get("id")

    # Check if fact already exists
    existing = db.query(DogFact).filter(DogFact.external_id == external_id).first()
    if existing:
        return existing

    new_fact = DogFact(
        external_id=external_id,
        fact=fact_data.get("fact", ""),
        title=fact_data.get("title"),
        breed_id=breed_db_id
    )
    db.add(new_fact)
    return new_fact


def save_health_tip_to_db(db, tip_data: Dict, breed_db_id: int = None) -> Optional[DogHealthTip]:
    """Save a health tip to the database."""
    external_id = tip_data.get("id")

    # Check if tip already exists
    existing = db.query(DogHealthTip).filter(DogHealthTip.external_id == external_id).first()
    if existing:
        return existing

    new_tip = DogHealthTip(
        external_id=external_id,
        category=tip_data.get("category"),
        title=tip_data.get("title", "Health Tip"),
        description=tip_data.get("description", ""),
        breed_id=breed_db_id,
        sources_json=tip_data.get("sources")
    )
    db.add(new_tip)
    return new_tip


def ingest_facts(db, random_limit: int = 100, per_breed_limit: int = 5):
    """Ingest dog facts from TheDogAPI."""
    print("\n" + "=" * 60)
    print("INGESTING DOG FACTS FROM THEDOGAPI")
    print("=" * 60)

    # First, fetch random facts
    random_facts = fetch_random_facts(limit=random_limit)
    random_count = 0

    for fact in random_facts:
        try:
            # Try to match to breed if breed_id is provided
            breed_db_id = None
            if fact.get("breed_id"):
                breed = db.query(DogBreed).filter(DogBreed.external_id == fact["breed_id"]).first()
                if breed:
                    breed_db_id = breed.id

            save_fact_to_db(db, fact, breed_db_id)
            random_count += 1
        except Exception as e:
            print(f"  ERROR saving fact: {e}")

    db.commit()
    print(f"Saved {random_count} random facts")

    # Now fetch breed-specific facts
    breeds = db.query(DogBreed).all()
    breed_fact_count = 0

    print(f"\nFetching facts for {len(breeds)} breeds...")

    for i, breed in enumerate(breeds):
        print(f"  [{i+1}/{len(breeds)}] {breed.name}...")

        breed_facts = fetch_breed_facts(breed.external_id, limit=per_breed_limit)

        for fact in breed_facts:
            try:
                save_fact_to_db(db, fact, breed.id)
                breed_fact_count += 1
            except Exception as e:
                print(f"    ERROR: {e}")

        # Commit every 10 breeds
        if (i + 1) % 10 == 0:
            db.commit()

    db.commit()
    print(f"\nSaved {breed_fact_count} breed-specific facts")
    return random_count + breed_fact_count


def ingest_health_tips(db, max_tips: int = 500):
    """Ingest dog health tips from TheDogAPI."""
    print("\n" + "=" * 60)
    print("INGESTING DOG HEALTH TIPS FROM THEDOGAPI")
    print("=" * 60)

    total_saved = 0
    offset = 0
    batch_size = 50

    while total_saved < max_tips:
        tips = fetch_health_tips(limit=batch_size, offset=offset)

        if not tips:
            break

        for tip in tips:
            try:
                # Try to match to breed if breed_id is provided
                breed_db_id = None
                if tip.get("breed_id"):
                    breed = db.query(DogBreed).filter(DogBreed.external_id == tip["breed_id"]).first()
                    if breed:
                        breed_db_id = breed.id

                save_health_tip_to_db(db, tip, breed_db_id)
                total_saved += 1
            except Exception as e:
                print(f"  ERROR saving tip: {e}")

        db.commit()
        offset += batch_size

        if len(tips) < batch_size:
            break  # No more tips available

    print(f"\nSaved {total_saved} health tips")
    return total_saved


def print_stats(db):
    """Print statistics about the dog breed data."""
    print("\n" + "=" * 60)
    print("DOG KNOWLEDGE DATABASE STATISTICS")
    print("=" * 60)

    breed_count = db.query(DogBreed).count()
    image_count = db.query(DogBreedImage).count()
    fact_count = db.query(DogFact).count()
    tip_count = db.query(DogHealthTip).count()

    print(f"Total breeds: {breed_count}")
    print(f"Total images: {image_count}")
    print(f"Total facts: {fact_count}")
    print(f"Total health tips: {tip_count}")

    # Breed groups
    from sqlalchemy import func
    groups = db.query(
        DogBreed.breed_group, func.count(DogBreed.id)
    ).group_by(DogBreed.breed_group).all()

    print("\nBreed Groups:")
    for group, count in sorted(groups, key=lambda x: x[1], reverse=True):
        print(f"  {group or 'Unknown'}: {count}")

    # Exercise needs distribution
    exercise = db.query(
        DogBreed.exercise_needs, func.count(DogBreed.id)
    ).group_by(DogBreed.exercise_needs).all()

    print("\nExercise Needs:")
    for level, count in exercise:
        print(f"  {level}: {count}")

    # Health tip categories
    if tip_count > 0:
        categories = db.query(
            DogHealthTip.category, func.count(DogHealthTip.id)
        ).group_by(DogHealthTip.category).all()

        print("\nHealth Tip Categories:")
        for cat, count in sorted(categories, key=lambda x: x[1], reverse=True):
            print(f"  {cat or 'General'}: {count}")


def main():
    parser = argparse.ArgumentParser(description="Ingest dog data from TheDogAPI")
    parser.add_argument("--breeds", action="store_true", help="Fetch all breeds")
    parser.add_argument("--images", action="store_true", help="Fetch additional images")
    parser.add_argument("--facts", action="store_true", help="Fetch dog facts")
    parser.add_argument("--health-tips", action="store_true", help="Fetch health tips")
    parser.add_argument("--export", action="store_true", help="Export to JSON")
    parser.add_argument("--stats", action="store_true", help="Show statistics")
    parser.add_argument("--all", action="store_true", help="Do everything")
    parser.add_argument("--images-per-breed", type=int, default=5, help="Number of images per breed")
    parser.add_argument("--max-facts", type=int, default=100, help="Max random facts to fetch")
    parser.add_argument("--max-tips", type=int, default=500, help="Max health tips to fetch")

    args = parser.parse_args()

    if not any([args.breeds, args.images, args.facts, args.health_tips, args.export, args.stats, args.all]):
        args.all = True  # Default to all

    print("=" * 60)
    print("THEDOGAPI DATA INGESTOR")
    print("Waiting The Longest™ - Dog Knowledge Library")
    print("=" * 60)

    if not API_KEY:
        print("\nERROR: THEDOGAPI_KEY not configured in .env")
        print("Please add: THEDOGAPI_KEY=your_api_key_here")
        return

    print(f"\nAPI Key configured: {API_KEY[:10]}...")

    init_db()
    db = SessionLocal()

    try:
        if args.breeds or args.all:
            ingest_breeds(db)

        if args.images or args.all:
            ingest_images(db, images_per_breed=args.images_per_breed)

        if args.facts or args.all:
            ingest_facts(db, random_limit=args.max_facts)

        if args.health_tips or args.all:
            ingest_health_tips(db, max_tips=args.max_tips)

        if args.export or args.all:
            export_breeds_json(db)

        if args.stats or args.all:
            print_stats(db)

        print("\n" + "=" * 60)
        print("INGESTION COMPLETE!")
        print("=" * 60)

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()

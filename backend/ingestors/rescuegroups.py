"""
===============================================================================
Waiting The Longest™ - RescueGroups.org API Ingestor
===============================================================================
Data ingestion from RescueGroups.org API (PRIMARY DATA SOURCE).

NOTE: Petfinder does NOT have a public API! We discovered this during
development and pivoted to RescueGroups.org as our primary data source.

RescueGroups API: https://rescuegroups.org/services/adoptable-pet-data-api/

Author: Waiting The Longest™ Development Team
===============================================================================
"""

import requests
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from dataclasses import dataclass
import json
import hashlib
from PIL import Image
import imagehash
from io import BytesIO

try:
    from app.config import settings
except ImportError:
    from ..app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class IngestedAnimal:
    """Standardized animal data from ingestion"""
    external_id: str
    source: str
    name: str
    species: str
    breed: Optional[str]
    breed_secondary: Optional[str]
    age_group: Optional[str]
    size: Optional[str]
    gender: Optional[str]
    color: Optional[str]
    description: Optional[str]
    photos: List[str]
    shelter_id: Optional[str]
    shelter_name: str
    city: Optional[str]
    state: Optional[str]
    zip_code: Optional[str]
    listing_url: Optional[str]


class RescueGroupsIngestor:
    """
    Ingestor for RescueGroups.org API

    This is our PRIMARY data source after discovering Petfinder
    does not have a public API.

    RescueGroups offers:
    - Free API access
    - Nationwide shelter data
    - Both dogs and cats
    - Regular updates
    """

    BASE_URL = "https://api.rescuegroups.org/http/v2.json"
    SOURCE_NAME = "rescuegroups"

    def __init__(self):
        self.api_key = settings.RESCUEGROUPS_API_KEY
        if not self.api_key:
            logger.warning("RescueGroups API key not configured!")

    def _make_request(self, object_type: str, object_action: str,
                      search: Optional[Dict] = None) -> Dict:
        """Make API request to RescueGroups"""
        payload = {
            "apikey": self.api_key,
            "objectType": object_type,
            "objectAction": object_action,
        }

        if search:
            payload["search"] = search

        try:
            response = requests.post(
                self.BASE_URL,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"RescueGroups API error: {e}")
            return {"status": "error", "data": {}}

    def fetch_animals(
        self,
        species: str = "Dog",
        limit: int = 100,
        location: Optional[str] = None,
        status: str = "Available"
    ) -> List[IngestedAnimal]:
        """
        Fetch animals from RescueGroups API

        Args:
            species: "Dog", "Cat", or "All"
            limit: Maximum number of results
            location: State abbreviation (e.g., "CA", "NY")
            status: "Available", "Adopted", "All"

        Returns:
            List of standardized IngestedAnimal objects
        """
        if not self.api_key:
            logger.error("Cannot fetch: RescueGroups API key not configured")
            return []

        # Build search filters
        filters = []

        if species != "All":
            filters.append({
                "fieldName": "animalSpecies",
                "operation": "equals",
                "criteria": species
            })

        if status != "All":
            filters.append({
                "fieldName": "animalStatus",
                "operation": "equals",
                "criteria": status
            })

        if location:
            filters.append({
                "fieldName": "locationState",
                "operation": "equals",
                "criteria": location
            })

        search = {
            "resultStart": 0,
            "resultLimit": limit,
            "resultSort": "animalID",
            "resultOrder": "asc",
            "calcFoundRows": "Yes",
            "filters": filters,
            "fields": [
                "animalID", "animalName", "animalSpecies", "animalBreed",
                "animalBreedSecondary", "animalGeneralAge", "animalGeneralSizePotential",
                "animalSex", "animalColor", "animalDescription",
                "animalPictures", "animalLocationCity", "animalLocationState",
                "animalLocationPostalcode", "animalOrgID", "animalOrgName",
                "animalStatusID", "animalStatus", "animalAdoptionFee",
                "animalCreatedDate", "animalUpdatedDate"
            ]
        }

        result = self._make_request("animals", "publicSearch", search)

        if result.get("status") == "error":
            logger.error(f"RescueGroups search failed: {result}")
            return []

        animals = []
        data = result.get("data", {})

        for animal_id, animal_data in data.items():
            try:
                animals.append(self._parse_animal(animal_data))
            except Exception as e:
                logger.warning(f"Failed to parse animal {animal_id}: {e}")
                continue

        logger.info(f"Fetched {len(animals)} animals from RescueGroups")
        return animals

    def _parse_animal(self, data: Dict) -> IngestedAnimal:
        """Parse RescueGroups animal data into standardized format"""

        # Extract photos
        photos = []
        if data.get("animalPictures"):
            for pic in data["animalPictures"]:
                if pic.get("large"):
                    photos.append(pic["large"])
                elif pic.get("original"):
                    photos.append(pic["original"])

        # Map age groups
        age_map = {
            "Baby": "puppy",
            "Young": "young",
            "Adult": "adult",
            "Senior": "senior"
        }
        age_group = age_map.get(data.get("animalGeneralAge"), "adult")

        # Map sizes
        size_map = {
            "Small": "small",
            "Medium": "medium",
            "Large": "large",
            "Extra Large": "extra_large"
        }
        size = size_map.get(data.get("animalGeneralSizePotential"), None)

        # Map gender
        gender_map = {
            "Male": "male",
            "Female": "female"
        }
        gender = gender_map.get(data.get("animalSex"), None)

        return IngestedAnimal(
            external_id=str(data.get("animalID", "")),
            source=self.SOURCE_NAME,
            name=data.get("animalName", "Unknown"),
            species=data.get("animalSpecies", "Dog").lower(),
            breed=data.get("animalBreed"),
            breed_secondary=data.get("animalBreedSecondary"),
            age_group=age_group,
            size=size,
            gender=gender,
            color=data.get("animalColor"),
            description=data.get("animalDescription"),
            photos=photos,
            shelter_id=data.get("animalOrgID"),
            shelter_name=data.get("animalOrgName", "Unknown Shelter"),
            city=data.get("animalLocationCity"),
            state=data.get("animalLocationState"),
            zip_code=data.get("animalLocationPostalcode"),
            listing_url=f"https://www.rescuegroups.org/animal/{data.get('animalID')}"
        )

    def compute_photo_hash(self, photo_url: str) -> Optional[str]:
        """
        Compute perceptual hash for deduplication.

        This helps us identify the same animal across different
        shelter listings.
        """
        try:
            response = requests.get(photo_url, timeout=10)
            response.raise_for_status()

            image = Image.open(BytesIO(response.content))
            phash = imagehash.phash(image)

            return str(phash)
        except Exception as e:
            logger.warning(f"Failed to compute photo hash: {e}")
            return None


class AdoptAPetIngestor:
    """
    Secondary ingestor for Adopt-a-Pet API

    This provides additional data coverage beyond RescueGroups.
    """

    BASE_URL = "https://api.adoptapet.com/search/"
    SOURCE_NAME = "adoptapet"

    def __init__(self):
        self.api_key = settings.ADOPTAPET_API_KEY

    # Implementation similar to RescueGroupsIngestor
    # TODO: Implement when API key is obtained
    pass


def run_full_ingestion(db, species: str = "all", limit: int = 100) -> Dict[str, int]:
    """
    Run full ingestion from all configured sources.

    Returns counts of new and updated animals.
    """
    from ..app.crud import find_duplicate_animal, merge_animal_observation
    from ..app.models import Animal, Observation

    stats = {"new": 0, "updated": 0, "errors": 0}

    # RescueGroups ingestion
    rg_ingestor = RescueGroupsIngestor()

    species_list = ["Dog", "Cat"] if species == "all" else [species.capitalize()]

    for sp in species_list:
        animals = rg_ingestor.fetch_animals(species=sp, limit=limit)

        for animal_data in animals:
            try:
                # Check for duplicate
                existing = find_duplicate_animal(
                    db,
                    name=animal_data.name,
                    species=animal_data.species,
                    breed=animal_data.breed
                )

                if existing:
                    # Update existing animal
                    merge_animal_observation(db, existing, {
                        "source": animal_data.source,
                        "external_id": animal_data.external_id,
                        "shelter_name": animal_data.shelter_name,
                        "name": animal_data.name,
                        "description": animal_data.description,
                        "photo_url": animal_data.photos[0] if animal_data.photos else None,
                        "photo_gallery_json": json.dumps(animal_data.photos) if animal_data.photos else None,
                        "city": animal_data.city,
                        "state": animal_data.state,
                        "zip_code": animal_data.zip_code,
                        "listing_url": animal_data.listing_url,
                        "first_seen_at": datetime.now(timezone.utc).replace(tzinfo=None),
                        "last_seen_at": datetime.now(timezone.utc).replace(tzinfo=None)
                    })
                    stats["updated"] += 1
                else:
                    # Create new animal
                    new_animal = Animal(
                        species=animal_data.species,
                        canonical_name=animal_data.name,
                        breed_primary=animal_data.breed,
                        breed_secondary=animal_data.breed_secondary,
                        age_group=animal_data.age_group,
                        size=animal_data.size,
                        gender=animal_data.gender,
                        color_primary=animal_data.color,
                        first_seen_at=datetime.now(timezone.utc).replace(tzinfo=None),
                        last_seen_at=datetime.now(timezone.utc).replace(tzinfo=None),
                        status="available"
                    )
                    db.add(new_animal)
                    db.flush()

                    # Create observation
                    observation = Observation(
                        animal_id=new_animal.id,
                        source=animal_data.source,
                        external_id=animal_data.external_id,
                        shelter_name=animal_data.shelter_name,
                        name=animal_data.name,
                        description=animal_data.description,
                        photo_url=animal_data.photos[0] if animal_data.photos else None,
                        photo_gallery_json=json.dumps(animal_data.photos) if animal_data.photos else None,
                        city=animal_data.city,
                        state=animal_data.state,
                        zip_code=animal_data.zip_code,
                        listing_url=animal_data.listing_url,
                        first_seen_at=datetime.now(timezone.utc).replace(tzinfo=None),
                        last_seen_at=datetime.now(timezone.utc).replace(tzinfo=None)
                    )
                    db.add(observation)
                    stats["new"] += 1

            except Exception as e:
                logger.error(f"Error processing animal: {e}")
                stats["errors"] += 1
                continue

        db.commit()

    logger.info(f"Ingestion complete: {stats}")
    return stats

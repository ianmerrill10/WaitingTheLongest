"""
===============================================================================
Waiting The Longest™ - CRUD Operations & Business Logic
===============================================================================
Database operations and core business logic including:
- Animal listing with "days waiting" sorting (OUR CORE FEATURE!)
- Deduplication using perceptual hashing
- Success story management
- Statistics calculations

Author: Waiting The Longest™ Development Team
===============================================================================
"""

from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import func, desc, asc, or_, and_
from typing import Optional, List, Dict, Any
from datetime import datetime
import json

from .models import Animal, Observation, Shelter, SuccessStory, SocialPromotion
from .schemas import (
    AnimalListItem, AnimalDetailResponse, AnimalListResponse,
    SuccessStoryCreate, ObservationOut
)


# =============================================================================
# Animal CRUD Operations
# =============================================================================

def paginate_animals(
    db: Session,
    species: Optional[str] = None,
    status: str = "available",
    sort_by: str = "days_waiting",
    sort_order: str = "desc",
    page: int = 1,
    page_size: int = 20,
    breed: Optional[str] = None,
    age_group: Optional[str] = None,
    size: Optional[str] = None,
    gender: Optional[str] = None,
    state: Optional[str] = None,
) -> AnimalListResponse:
    """
    Paginate animals with filtering and sorting.

    The default sort is by days_waiting descending - this is the core
    of "Waiting The Longest™"! We want to show animals who have waited
    the longest first.
    """
    # Base query with eager loading to avoid N+1 queries
    query = db.query(Animal).options(
        selectinload(Animal.observations)
    )

    # Apply filters
    if species:
        query = query.filter(Animal.species == species)

    if status:
        query = query.filter(Animal.status == status)

    if breed:
        query = query.filter(
            or_(
                Animal.breed_primary.ilike(f"%{breed}%"),
                Animal.breed_secondary.ilike(f"%{breed}%")
            )
        )

    if age_group:
        query = query.filter(Animal.age_group == age_group)

    if size:
        query = query.filter(Animal.size == size)

    if gender:
        query = query.filter(Animal.gender == gender)

    # Filter by state (from observations)
    if state:
        query = query.join(Animal.observations).filter(
            Observation.state.ilike(f"%{state}%")
        ).distinct()

    # Get total count before pagination
    total = query.count()

    # Apply sorting
    if sort_by == "days_waiting":
        # Sort by first_seen_at (older = longer waiting)
        order_col = Animal.first_seen_at
        # For days_waiting desc, we want oldest first (asc on first_seen_at)
        if sort_order == "desc":
            query = query.order_by(asc(order_col))
        else:
            query = query.order_by(desc(order_col))
    elif sort_by == "name":
        order_col = Animal.canonical_name
        query = query.order_by(
            desc(order_col) if sort_order == "desc" else asc(order_col)
        )
    elif sort_by == "last_seen":
        order_col = Animal.last_seen_at
        query = query.order_by(
            desc(order_col) if sort_order == "desc" else asc(order_col)
        )
    else:
        # Default to days waiting desc
        query = query.order_by(asc(Animal.first_seen_at))

    # Apply pagination
    offset = (page - 1) * page_size
    animals = query.offset(offset).limit(page_size).all()

    # Calculate pagination info
    total_pages = (total + page_size - 1) // page_size

    # Transform to response format
    items = []
    for animal in animals:
        # Get primary photo from first observation
        photo_url = None
        city = None
        state_val = None

        if animal.observations:
            obs = animal.observations[0]
            photo_url = obs.photo_url
            city = obs.city
            state_val = obs.state

        items.append(AnimalListItem(
            id=animal.id,
            species=animal.species,
            canonical_name=animal.canonical_name,
            breed_primary=animal.breed_primary,
            age_group=animal.age_group,
            size=animal.size,
            gender=animal.gender,
            status=animal.status,
            days_waiting=animal.days_waiting,
            first_seen_at=animal.first_seen_at,
            photo_url=photo_url,
            city=city,
            state=state_val
        ))

    return AnimalListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1
    )


def get_animal_detail(db: Session, animal_id: int) -> Optional[AnimalDetailResponse]:
    """
    Get detailed information about a specific animal.

    Includes all observations, photos, and shelter information.
    """
    animal = db.query(Animal).options(
        selectinload(Animal.observations).selectinload(Observation.shelter)
    ).filter(Animal.id == animal_id).first()

    if not animal:
        return None

    # Collect all photos from observations
    all_photos = []
    description = None
    adoption_url = None
    shelter_info = None

    observations_out = []
    for obs in animal.observations:
        # Get photo gallery
        gallery = []
        if obs.photo_gallery_json:
            try:
                gallery = json.loads(obs.photo_gallery_json) if isinstance(
                    obs.photo_gallery_json, str
                ) else obs.photo_gallery_json
            except:
                gallery = []

        if obs.photo_url:
            all_photos.append(obs.photo_url)
        all_photos.extend(gallery)

        # Get description from first observation with one
        if not description and obs.description:
            description = obs.description

        # Get adoption URL
        if not adoption_url and obs.listing_url:
            adoption_url = obs.listing_url

        # Get shelter info
        if not shelter_info and obs.shelter:
            shelter_info = {
                "name": obs.shelter.name,
                "city": obs.shelter.city,
                "state": obs.shelter.state,
                "phone": obs.shelter.phone,
                "email": obs.shelter.email,
                "website": obs.shelter.website
            }

        observations_out.append(ObservationOut(
            id=obs.id,
            source=obs.source,
            shelter_name=obs.shelter_name,
            name=obs.name,
            description=obs.description,
            photo_url=obs.photo_url,
            photo_gallery=gallery,
            city=obs.city,
            state=obs.state,
            listing_url=obs.listing_url,
            first_seen_at=obs.first_seen_at,
            last_seen_at=obs.last_seen_at
        ))

    # Deduplicate photos
    unique_photos = list(dict.fromkeys(all_photos))

    return AnimalDetailResponse(
        id=animal.id,
        species=animal.species,
        canonical_name=animal.canonical_name,
        breed_primary=animal.breed_primary,
        breed_secondary=animal.breed_secondary,
        color_primary=animal.color_primary,
        age_group=animal.age_group,
        size=animal.size,
        gender=animal.gender,
        status=animal.status,
        transfer_count=animal.transfer_count,
        days_waiting=animal.days_waiting,
        first_seen_at=animal.first_seen_at,
        last_seen_at=animal.last_seen_at,
        observations=observations_out,
        photos=unique_photos,
        description=description,
        adoption_url=adoption_url,
        shelter_info=shelter_info
    )


# =============================================================================
# Success Story CRUD
# =============================================================================

def create_success_story(db: Session, story: SuccessStoryCreate) -> SuccessStory:
    """
    Create a new success story submission.

    These stories are gold for our social media content!
    """
    db_story = SuccessStory(
        animal_id=story.animal_id,
        pet_name=story.pet_name,
        adopter_name=story.adopter_name,
        story_text=story.story_text,
        days_waited=story.days_waited,
        adoption_date=story.adoption_date,
        photo_urls=story.photo_urls,
        contact_email=story.contact_email,
        is_approved=False,  # Require moderation
        is_featured=False
    )

    db.add(db_story)
    db.commit()
    db.refresh(db_story)

    return db_story


def get_trending_stories(db: Session, limit: int = 10) -> List[SuccessStory]:
    """
    Get trending/featured success stories.

    Prioritizes:
    1. Featured stories
    2. Recently approved stories
    3. Stories with long wait times (more emotional impact)
    """
    return db.query(SuccessStory).options(
        joinedload(SuccessStory.animal)
    ).filter(
        SuccessStory.is_approved == True
    ).order_by(
        desc(SuccessStory.is_featured),
        desc(SuccessStory.days_waited),
        desc(SuccessStory.submission_date)
    ).limit(limit).all()


# =============================================================================
# Deduplication Logic
# =============================================================================

def find_duplicate_animal(
    db: Session,
    name: str,
    species: str,
    photo_phash: Optional[str] = None,
    breed: Optional[str] = None,
) -> Optional[Animal]:
    """
    Find a potentially duplicate animal using various matching strategies.

    Matching priority:
    1. Perceptual hash match (most reliable for same animal)
    2. Name + species + breed match
    3. Name similarity + species match
    """
    # Try perceptual hash match first (most reliable)
    if photo_phash:
        # Look for exact or near match
        existing = db.query(Animal).filter(
            Animal.photo_phash == photo_phash,
            Animal.species == species
        ).first()

        if existing:
            return existing

    # Try name + species + breed match
    if name and breed:
        existing = db.query(Animal).filter(
            func.lower(Animal.canonical_name) == func.lower(name),
            Animal.species == species,
            func.lower(Animal.breed_primary) == func.lower(breed)
        ).first()

        if existing:
            return existing

    # Try name + species only
    if name:
        existing = db.query(Animal).filter(
            func.lower(Animal.canonical_name) == func.lower(name),
            Animal.species == species
        ).first()

        if existing:
            return existing

    return None


def merge_animal_observation(
    db: Session,
    animal: Animal,
    observation_data: Dict[str, Any]
) -> Observation:
    """
    Add a new observation to an existing animal record.

    Updates the animal's last_seen_at and potentially other fields.
    """
    # Create observation
    observation = Observation(
        animal_id=animal.id,
        **observation_data
    )

    db.add(observation)

    # Update animal's last seen time
    animal.last_seen_at = datetime.utcnow()

    # Update other fields if we have better data
    if not animal.canonical_name and observation_data.get('name'):
        animal.canonical_name = observation_data['name']

    db.commit()
    db.refresh(observation)

    return observation


# =============================================================================
# Statistics
# =============================================================================

def get_platform_stats(db: Session) -> Dict[str, Any]:
    """Get overall platform statistics"""
    total = db.query(func.count(Animal.id)).scalar() or 0
    available = db.query(func.count(Animal.id)).filter(
        Animal.status == "available"
    ).scalar() or 0

    # Average wait time
    avg_wait = db.query(func.avg(
        func.extract('day', func.now() - Animal.first_seen_at)
    )).filter(Animal.status == "available").scalar() or 0

    # Longest waiting
    longest = db.query(Animal).filter(
        Animal.status == "available"
    ).order_by(Animal.first_seen_at.asc()).first()

    longest_days = 0
    if longest and longest.first_seen_at:
        longest_days = (datetime.utcnow() - longest.first_seen_at).days

    success_count = db.query(func.count(SuccessStory.id)).filter(
        SuccessStory.is_approved == True
    ).scalar() or 0

    return {
        "total_animals": total,
        "available_animals": available,
        "average_wait_days": round(float(avg_wait), 1),
        "longest_wait_days": longest_days,
        "success_stories": success_count
    }

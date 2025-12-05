"""
===============================================================================
Waiting The Longest™ - CRUD Operations & Business Logic
===============================================================================
Purpose: Core business logic and database operations. Implements the 
         "days waiting" sorting which is central to our mission.

Author: Waiting The Longest™ Development Team
Last Updated: 2025-01-15
Dependencies: sqlalchemy
Related Files: main.py, models.py, schemas.py

IMPORTANT: Any changes to this file MUST be documented in OWNERS_MANUAL.md

Key Operations:
- Animal listing with "days waiting" sorting (OUR CORE FEATURE!)
- Deduplication using perceptual hashing
- Success story management
- Statistics calculations
===============================================================================
"""

from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import func, desc, asc, or_, and_
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import json

from .models import Animal, Observation, Shelter, SuccessStory, SocialPromotion, ContactSubmission
from .schemas import (
    AnimalListItem, AnimalDetailResponse, AnimalListResponse,
    SuccessStoryCreate, ObservationOut, ShelterListItem, ShelterDetailResponse,
    ShelterListResponse, ContactSubmissionCreate
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

    This is THE CORE FEATURE of Waiting The Longest™! The default sort is by 
    days_waiting descending, showing animals who have waited the longest first.
    
    Args:
        db: Database session for queries
        species: Filter by species ("dog", "cat", or None for all)
        status: Filter by status (default "available")
        sort_by: Field to sort by (default "days_waiting")
        sort_order: Sort direction ("asc" or "desc", default "desc")
        page: Page number (1-indexed)
        page_size: Number of items per page (max 100)
        breed: Partial match filter for breed
        age_group: Filter by age ("puppy", "young", "adult", "senior")
        size: Filter by size ("small", "medium", "large")
        gender: Filter by gender ("male", "female")
        state: Filter by state (e.g., "CA", "TX")
        
    Returns:
        AnimalListResponse with paginated items and metadata
        
    Example:
        >>> result = paginate_animals(db, species="dog", page=1, page_size=20)
        >>> print(f"Found {result.total} dogs")
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

    Retrieves complete animal information including all observations from
    different sources, photo galleries, descriptions, and shelter contact info.
    
    Args:
        db: Database session for queries
        animal_id: The unique identifier of the animal
        
    Returns:
        AnimalDetailResponse with complete animal data, or None if not found
        
    Example:
        >>> animal = get_animal_detail(db, animal_id=123)
        >>> if animal:
        ...     print(f"{animal.canonical_name} has waited {animal.days_waiting} days")
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
            except (json.JSONDecodeError, TypeError):
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

    These stories are gold for our social media content! Stories with high
    days_waited values create emotional impact and drive engagement.
    
    Args:
        db: Database session
        story: SuccessStoryCreate schema with story details
        
    Returns:
        The created SuccessStory object
        
    Note:
        Stories are created with is_approved=False and require moderation
        before they appear on the site.
        
    Example:
        >>> story = SuccessStoryCreate(pet_name="Max", story_text="...", days_waited=365)
        >>> created = create_success_story(db, story)
        >>> print(f"Story {created.id} created, pending approval")
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
    Get trending/featured success stories for display and social content.

    Stories are prioritized to maximize emotional impact and engagement:
    1. Featured stories (manually curated for quality)
    2. Stories with longest wait times (emotional impact)
    3. Most recently approved stories (freshness)
    
    Args:
        db: Database session
        limit: Maximum number of stories to return (default 10)
        
    Returns:
        List of approved SuccessStory objects with animal data loaded
        
    Example:
        >>> stories = get_trending_stories(db, limit=5)
        >>> for story in stories:
        ...     print(f"{story.pet_name} waited {story.days_waited} days")
    """
    return db.query(SuccessStory).options(
        joinedload(SuccessStory.animal)
    ).filter(
        SuccessStory.is_approved.is_(True)
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

    This is critical for preventing the same animal from appearing multiple
    times in our database. An animal might be listed at different shelters
    or re-listed after being returned.
    
    Matching priority (most to least reliable):
    1. Perceptual hash match - Same photo = same animal
    2. Name + species + breed match - Exact match on all fields
    3. Name + species match - Fallback for missing breed info
    
    Args:
        db: Database session
        name: Animal's name to match
        species: Species ("dog", "cat", etc.)
        photo_phash: Perceptual hash of primary photo (optional)
        breed: Primary breed for matching (optional)
        
    Returns:
        Existing Animal object if duplicate found, None otherwise
        
    Example:
        >>> existing = find_duplicate_animal(db, "Max", "dog", breed="Labrador")
        >>> if existing:
        ...     print(f"Found duplicate: Animal ID {existing.id}")
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
    animal.last_seen_at = datetime.now(timezone.utc).replace(tzinfo=None)

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

    # Average wait time (Current)
    avg_wait = db.query(func.avg(
        func.extract('day', func.now() - Animal.first_seen_at)
    )).filter(Animal.status == "available").scalar() or 0
    
    # Mock Historical Average (e.g., 1.5 years = ~547 days)
    # In a real app, this would come from a history table
    historical_avg_wait = 547.0 
    
    # Calculate reduction
    wait_time_reduction = max(0, historical_avg_wait - (float(avg_wait) if avg_wait else 0))

    # Longest waiting
    longest = db.query(Animal).filter(
        Animal.status == "available"
    ).order_by(Animal.first_seen_at.asc()).first()

    longest_days = 0
    if longest and longest.first_seen_at:
        longest_days = (datetime.utcnow() - longest.first_seen_at).days

    # Total Rescued (Adopted status + Approved Success Stories)
    # We'll count animals with status 'adopted'
    adopted_count = db.query(func.count(Animal.id)).filter(
        Animal.status == "adopted"
    ).scalar() or 0
    
    # Plus any success stories that might not be linked to an 'adopted' animal record (legacy data)
    success_count = db.query(func.count(SuccessStory.id)).filter(
        SuccessStory.is_approved.is_(True)
    ).scalar() or 0
    
    # Use the larger of the two or sum if distinct (simplifying to max for now)
    total_rescued = max(adopted_count, success_count)

    return {
        "total_animals": total,
        "available_animals": available,
        "average_wait_days": round(float(avg_wait), 1),
        "historical_avg_wait_days": round(historical_avg_wait, 1),
        "wait_time_reduction_days": round(wait_time_reduction, 1),
        "longest_wait_days": longest_days,
        "success_stories": success_count,
        "total_rescued": total_rescued
    }


# =============================================================================
# Contact Submission CRUD
# =============================================================================

def create_contact_submission(
    db: Session,
    submission: ContactSubmissionCreate,
    ip_hash: Optional[str] = None,
    user_agent: Optional[str] = None
) -> ContactSubmission:
    """
    Create a new contact form submission.
    
    Args:
        db: Database session
        submission: ContactSubmissionCreate schema with form data
        ip_hash: Hashed IP address for spam prevention
        user_agent: User agent string for analytics
        
    Returns:
        The created ContactSubmission object
        
    Example:
        >>> submission = ContactSubmissionCreate(name="John", email="john@example.com", ...)
        >>> created = create_contact_submission(db, submission)
        >>> print(f"Submission {created.id} received")
    """
    db_submission = ContactSubmission(
        name=submission.name,
        email=submission.email,
        subject=submission.subject,
        message=submission.message,
        ip_hash=ip_hash,
        user_agent=user_agent,
        is_read=False,
        is_responded=False
    )
    
    db.add(db_submission)
    db.commit()
    db.refresh(db_submission)
    
    return db_submission


# =============================================================================
# Shelter CRUD
# =============================================================================

def get_shelters(
    db: Session,
    page: int = 1,
    page_size: int = 20,
    state: Optional[str] = None,
    search: Optional[str] = None
) -> ShelterListResponse:
    """
    Get paginated list of shelters with animal counts.
    
    Args:
        db: Database session
        page: Page number (1-indexed)
        page_size: Number of items per page
        state: Optional filter by state
        search: Optional search term (name, city, or state)
        
    Returns:
        ShelterListResponse with paginated shelter data
        
    Example:
        >>> result = get_shelters(db, page=1, page_size=20)
        >>> print(f"Found {result.total} shelters")
    """
    query = db.query(Shelter)
    
    if state:
        query = query.filter(Shelter.state.ilike(f"%{state}%"))
        
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Shelter.name.ilike(search_term),
                Shelter.city.ilike(search_term),
                Shelter.state.ilike(search_term)
            )
        )
    
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * page_size
    shelters = query.order_by(Shelter.name).offset(offset).limit(page_size).all()
    
    # Calculate pagination info
    total_pages = (total + page_size - 1) // page_size
    
    # Transform to response format with animal counts
    items = []
    for shelter in shelters:
        # Count animals at this shelter
        animal_count = db.query(func.count(Observation.id)).filter(
            Observation.shelter_id == shelter.id
        ).scalar() or 0
        
        items.append(ShelterListItem(
            id=shelter.id,
            name=shelter.name,
            city=shelter.city,
            state=shelter.state,
            email=shelter.email,
            phone=shelter.phone,
            website=shelter.website,
            animal_count=animal_count
        ))
    
    return ShelterListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


def get_shelter_detail(db: Session, shelter_id: int) -> Optional[ShelterDetailResponse]:
    """
    Get detailed information about a specific shelter including its animals.
    
    Args:
        db: Database session
        shelter_id: The unique identifier of the shelter
        
    Returns:
        ShelterDetailResponse with complete shelter data, or None if not found
        
    Example:
        >>> shelter = get_shelter_detail(db, shelter_id=1)
        >>> if shelter:
        ...     print(f"{shelter.name} has {len(shelter.animals)} animals")
    """
    shelter = db.query(Shelter).filter(Shelter.id == shelter_id).first()
    
    if not shelter:
        return None
    
    # Get animals at this shelter
    observations = db.query(Observation).options(
        joinedload(Observation.animal)
    ).filter(
        Observation.shelter_id == shelter_id
    ).all()
    
    # Get unique animals from observations
    seen_animal_ids = set()
    animals = []
    
    for obs in observations:
        if obs.animal and obs.animal.id not in seen_animal_ids:
            seen_animal_ids.add(obs.animal.id)
            animal = obs.animal
            
            animals.append(AnimalListItem(
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
                photo_url=obs.photo_url,
                city=obs.city,
                state=obs.state
            ))
    
    return ShelterDetailResponse(
        id=shelter.id,
        name=shelter.name,
        source=shelter.source,
        email=shelter.email,
        phone=shelter.phone,
        website=shelter.website,
        address=shelter.address,
        city=shelter.city,
        state=shelter.state,
        zip_code=shelter.zip_code,
        latitude=shelter.latitude,
        longitude=shelter.longitude,
        total_animals=len(animals),
        animals=animals
    )

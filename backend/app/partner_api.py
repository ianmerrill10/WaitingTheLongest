"""
===============================================================================
Waiting The Longest™ - Shelter Partner API
===============================================================================
Purpose: API endpoints for shelter partners to submit animal intake data.
         Enables real-time animal listing updates from partner shelters.

Endpoints:
  - POST /api/partner/register - Register as a partner shelter
  - GET /api/partner/status - Check registration status
  - POST /api/partner/animals - Submit animal intake data
  - PUT /api/partner/animals/{id} - Update animal status
  - DELETE /api/partner/animals/{id} - Mark animal as adopted/removed
  - GET /api/partner/animals - List your submitted animals
  - POST /api/partner/webhook - Configure webhook for updates

Authentication:
  - API Key authentication via X-API-Key header
  - Partner shelters receive unique API key upon registration

Mission: Help shelter animals who have waited the longest find forever homes.
===============================================================================
"""

from fastapi import APIRouter, Depends, HTTPException, Header, Query, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, HttpUrl, Field
from typing import Optional, List
from datetime import datetime, timezone
from enum import Enum
import secrets
import hashlib
import logging

from .database import get_db
from .models import Animal, Shelter, Observation

logger = logging.getLogger(__name__)

# Create partner router
partner_router = APIRouter(prefix="/api/partner", tags=["Partner API"])


# ==================== Schemas ====================

class PartnerRegistrationRequest(BaseModel):
    """Request to register as a partner shelter."""
    shelter_name: str = Field(..., min_length=3, max_length=200)
    contact_email: EmailStr
    contact_name: str = Field(..., min_length=2, max_length=100)
    contact_phone: Optional[str] = None
    website: Optional[HttpUrl] = None
    address: Optional[str] = None
    city: str
    state: str = Field(..., min_length=2, max_length=2)
    zip_code: Optional[str] = None
    ein: Optional[str] = Field(None, description="Federal EIN for verification")


class PartnerRegistrationResponse(BaseModel):
    """Response with API credentials."""
    success: bool
    message: str
    partner_id: int
    api_key: str  # Only shown once!
    rate_limit: str = "100 requests/hour"


class AnimalIntakeRequest(BaseModel):
    """Request to add a new animal to the platform."""
    name: str = Field(..., min_length=1, max_length=100)
    species: str = Field(..., description="dog, cat, rabbit, etc.")
    breed: Optional[str] = None
    age: Optional[str] = None
    gender: Optional[str] = None
    size: Optional[str] = None
    color: Optional[str] = None
    description: Optional[str] = None
    photo_url: Optional[HttpUrl] = None
    intake_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    special_needs: Optional[str] = None
    good_with_kids: Optional[bool] = None
    good_with_dogs: Optional[bool] = None
    good_with_cats: Optional[bool] = None
    external_id: Optional[str] = Field(None, description="Your internal animal ID")


class AnimalUpdateRequest(BaseModel):
    """Request to update animal information."""
    name: Optional[str] = None
    description: Optional[str] = None
    photo_url: Optional[HttpUrl] = None
    status: Optional[str] = Field(None, description="available, pending, adopted")
    special_needs: Optional[str] = None


class AnimalResponse(BaseModel):
    """Animal data response."""
    id: int
    name: str
    species: str
    breed: Optional[str]
    age: Optional[str]
    status: str
    days_waiting: int
    photo_url: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class WebhookConfigRequest(BaseModel):
    """Configure webhook for updates."""
    webhook_url: HttpUrl
    events: List[str] = ["inquiry", "featured", "stats"]
    secret: Optional[str] = None  # For signature verification


# ==================== API Key Validation ====================

def generate_api_key() -> str:
    """Generate a secure API key for partners."""
    return f"wtl_{secrets.token_urlsafe(32)}"


def hash_api_key(api_key: str) -> str:
    """Hash API key for storage."""
    return hashlib.sha256(api_key.encode()).hexdigest()


async def validate_api_key(
    x_api_key: str = Header(..., description="Partner API key"),
    db: Session = Depends(get_db)
) -> Shelter:
    """Validate API key and return partner shelter."""
    if not x_api_key or not x_api_key.startswith("wtl_"):
        raise HTTPException(status_code=401, detail="Invalid API key format")

    key_hash = hash_api_key(x_api_key)

    # Find shelter with this API key hash
    # Note: In production, add api_key_hash column to Shelter model
    shelter = db.query(Shelter).filter(
        Shelter.external_id == f"partner_key:{key_hash[:16]}"
    ).first()

    if not shelter:
        raise HTTPException(status_code=401, detail="Invalid or expired API key")

    return shelter


# ==================== Endpoints ====================

@partner_router.post("/register", response_model=PartnerRegistrationResponse)
async def register_partner(
    request: PartnerRegistrationRequest,
    db: Session = Depends(get_db)
):
    """
    Register as a partner shelter.

    After registration, you'll receive an API key that grants access
    to submit and manage animal listings.

    **IMPORTANT**: Save your API key securely. It will only be shown once!
    """
    # Check if shelter already exists
    existing = db.query(Shelter).filter(
        Shelter.name == request.shelter_name,
        Shelter.state == request.state.upper()
    ).first()

    if existing and existing.external_id and existing.external_id.startswith("partner_key:"):
        raise HTTPException(
            status_code=400,
            detail="This shelter is already registered. Contact support for API key recovery."
        )

    # Generate API key
    api_key = generate_api_key()
    key_hash = hash_api_key(api_key)

    if existing:
        # Update existing shelter to partner status
        existing.email = request.contact_email
        existing.phone = request.contact_phone
        existing.website = str(request.website) if request.website else None
        existing.external_id = f"partner_key:{key_hash[:16]}"
        existing.updated_at = datetime.now(timezone.utc)
        partner = existing
    else:
        # Create new shelter
        partner = Shelter(
            name=request.shelter_name,
            email=request.contact_email,
            phone=request.contact_phone,
            website=str(request.website) if request.website else None,
            address=request.address,
            city=request.city,
            state=request.state.upper(),
            zip_code=request.zip_code,
            source="partner_api",
            external_id=f"partner_key:{key_hash[:16]}",
            org_type="partner"
        )
        db.add(partner)

    db.commit()
    db.refresh(partner)

    logger.info(f"New partner registered: {partner.name} (ID: {partner.id})")

    return PartnerRegistrationResponse(
        success=True,
        message=f"Welcome to Waiting The Longest! Save your API key securely.",
        partner_id=partner.id,
        api_key=api_key
    )


@partner_router.get("/status")
async def get_partner_status(
    shelter: Shelter = Depends(validate_api_key),
    db: Session = Depends(get_db)
):
    """Get your partner account status and stats."""
    animal_count = db.query(Animal).filter(
        Animal.shelter_id == shelter.id,
        Animal.status == "available"
    ).count()

    total_animals = db.query(Animal).filter(
        Animal.shelter_id == shelter.id
    ).count()

    return {
        "partner_id": shelter.id,
        "shelter_name": shelter.name,
        "status": "active",
        "available_animals": animal_count,
        "total_animals": total_animals,
        "registered_at": shelter.created_at,
        "rate_limit": "100 requests/hour"
    }


@partner_router.post("/animals", response_model=AnimalResponse)
async def submit_animal(
    animal: AnimalIntakeRequest,
    shelter: Shelter = Depends(validate_api_key),
    db: Session = Depends(get_db)
):
    """
    Submit a new animal to the platform.

    The animal will appear on WaitingTheLongest.com and be ranked by
    how long they've been waiting for adoption.
    """
    # Check for duplicate
    if animal.external_id:
        existing = db.query(Animal).filter(
            Animal.shelter_id == shelter.id,
            Animal.external_id == animal.external_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Animal with external_id '{animal.external_id}' already exists"
            )

    # Create animal
    new_animal = Animal(
        name=animal.name,
        species=animal.species.lower(),
        breed=animal.breed,
        age=animal.age,
        gender=animal.gender,
        size=animal.size,
        color=animal.color,
        description=animal.description,
        photo_url=str(animal.photo_url) if animal.photo_url else None,
        status="available",
        shelter_id=shelter.id,
        intake_date=animal.intake_date,
        external_id=animal.external_id,
        source="partner_api"
    )

    db.add(new_animal)
    db.commit()
    db.refresh(new_animal)

    # Create initial observation
    observation = Observation(
        animal_id=new_animal.id,
        observation_date=datetime.now(timezone.utc),
        source="partner_api",
        notes=f"Initial intake via Partner API from {shelter.name}"
    )
    db.add(observation)
    db.commit()

    logger.info(f"New animal submitted via Partner API: {new_animal.name} from {shelter.name}")

    # Calculate days waiting
    if new_animal.intake_date:
        days_waiting = (datetime.now(timezone.utc) - new_animal.intake_date.replace(tzinfo=timezone.utc)).days
    else:
        days_waiting = 0

    return AnimalResponse(
        id=new_animal.id,
        name=new_animal.name,
        species=new_animal.species,
        breed=new_animal.breed,
        age=new_animal.age,
        status=new_animal.status,
        days_waiting=days_waiting,
        photo_url=new_animal.photo_url,
        created_at=new_animal.created_at
    )


@partner_router.get("/animals", response_model=List[AnimalResponse])
async def list_partner_animals(
    status: Optional[str] = Query(None, description="Filter by status"),
    species: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    shelter: Shelter = Depends(validate_api_key),
    db: Session = Depends(get_db)
):
    """List animals submitted by your shelter."""
    query = db.query(Animal).filter(Animal.shelter_id == shelter.id)

    if status:
        query = query.filter(Animal.status == status)
    if species:
        query = query.filter(Animal.species == species.lower())

    animals = query.order_by(Animal.intake_date.asc()).offset(offset).limit(limit).all()

    results = []
    now = datetime.now(timezone.utc)

    for animal in animals:
        if animal.intake_date:
            intake = animal.intake_date.replace(tzinfo=timezone.utc) if animal.intake_date.tzinfo is None else animal.intake_date
            days_waiting = (now - intake).days
        else:
            days_waiting = 0

        results.append(AnimalResponse(
            id=animal.id,
            name=animal.name,
            species=animal.species,
            breed=animal.breed,
            age=animal.age,
            status=animal.status,
            days_waiting=days_waiting,
            photo_url=animal.photo_url,
            created_at=animal.created_at
        ))

    return results


@partner_router.put("/animals/{animal_id}")
async def update_animal(
    animal_id: int,
    update: AnimalUpdateRequest,
    shelter: Shelter = Depends(validate_api_key),
    db: Session = Depends(get_db)
):
    """Update animal information or status."""
    animal = db.query(Animal).filter(
        Animal.id == animal_id,
        Animal.shelter_id == shelter.id
    ).first()

    if not animal:
        raise HTTPException(status_code=404, detail="Animal not found or not owned by your shelter")

    # Update fields
    if update.name:
        animal.name = update.name
    if update.description:
        animal.description = update.description
    if update.photo_url:
        animal.photo_url = str(update.photo_url)
    if update.status:
        old_status = animal.status
        animal.status = update.status

        # Log status change
        if old_status != update.status:
            observation = Observation(
                animal_id=animal.id,
                observation_date=datetime.now(timezone.utc),
                source="partner_api",
                notes=f"Status changed from {old_status} to {update.status}"
            )
            db.add(observation)
    if update.special_needs is not None:
        animal.special_needs = update.special_needs

    animal.updated_at = datetime.now(timezone.utc)
    db.commit()

    return {"success": True, "message": f"Animal {animal_id} updated"}


@partner_router.delete("/animals/{animal_id}")
async def remove_animal(
    animal_id: int,
    reason: str = Query(..., description="Reason: adopted, transferred, deceased, other"),
    shelter: Shelter = Depends(validate_api_key),
    db: Session = Depends(get_db)
):
    """Mark animal as no longer available (adopted, transferred, etc.)."""
    animal = db.query(Animal).filter(
        Animal.id == animal_id,
        Animal.shelter_id == shelter.id
    ).first()

    if not animal:
        raise HTTPException(status_code=404, detail="Animal not found or not owned by your shelter")

    # Don't actually delete - mark as adopted/removed
    animal.status = reason if reason in ["adopted", "transferred", "deceased"] else "removed"
    animal.updated_at = datetime.now(timezone.utc)

    # Log the outcome
    observation = Observation(
        animal_id=animal.id,
        observation_date=datetime.now(timezone.utc),
        source="partner_api",
        notes=f"Animal marked as {animal.status} via Partner API"
    )
    db.add(observation)
    db.commit()

    if reason == "adopted":
        logger.info(f"Animal adopted via Partner API: {animal.name} from {shelter.name}")

    return {
        "success": True,
        "message": f"Animal {animal_id} marked as {animal.status}",
        "animal_name": animal.name
    }


@partner_router.post("/webhook")
async def configure_webhook(
    config: WebhookConfigRequest,
    shelter: Shelter = Depends(validate_api_key),
    db: Session = Depends(get_db)
):
    """
    Configure a webhook to receive notifications.

    Events:
    - inquiry: When someone inquires about your animal
    - featured: When your animal is featured
    - stats: Weekly statistics about your listings
    """
    # Store webhook config (would need a webhook table in production)
    # For now, store in description field as JSON
    import json

    webhook_config = {
        "url": str(config.webhook_url),
        "events": config.events,
        "secret": config.secret or secrets.token_urlsafe(16),
        "created_at": datetime.now(timezone.utc).isoformat()
    }

    # Update shelter with webhook config
    shelter.description = json.dumps({"webhook": webhook_config})
    db.commit()

    return {
        "success": True,
        "message": "Webhook configured successfully",
        "webhook_url": str(config.webhook_url),
        "events": config.events,
        "webhook_secret": webhook_config["secret"]
    }


# ==================== Bulk Operations ====================

@partner_router.post("/animals/bulk")
async def bulk_submit_animals(
    animals: List[AnimalIntakeRequest],
    shelter: Shelter = Depends(validate_api_key),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db)
):
    """
    Submit multiple animals at once (max 100 per request).

    For initial shelter onboarding or regular sync.
    """
    if len(animals) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 animals per bulk request")

    created = []
    errors = []

    for idx, animal_data in enumerate(animals):
        try:
            # Check for duplicate
            if animal_data.external_id:
                existing = db.query(Animal).filter(
                    Animal.shelter_id == shelter.id,
                    Animal.external_id == animal_data.external_id
                ).first()
                if existing:
                    errors.append({
                        "index": idx,
                        "external_id": animal_data.external_id,
                        "error": "Already exists"
                    })
                    continue

            new_animal = Animal(
                name=animal_data.name,
                species=animal_data.species.lower(),
                breed=animal_data.breed,
                age=animal_data.age,
                gender=animal_data.gender,
                size=animal_data.size,
                color=animal_data.color,
                description=animal_data.description,
                photo_url=str(animal_data.photo_url) if animal_data.photo_url else None,
                status="available",
                shelter_id=shelter.id,
                intake_date=animal_data.intake_date,
                external_id=animal_data.external_id,
                source="partner_api"
            )
            db.add(new_animal)
            created.append(animal_data.name)

        except Exception as e:
            errors.append({
                "index": idx,
                "name": animal_data.name,
                "error": str(e)
            })

    db.commit()

    logger.info(f"Bulk import: {len(created)} animals from {shelter.name}")

    return {
        "success": True,
        "created_count": len(created),
        "error_count": len(errors),
        "created": created[:10],  # Show first 10
        "errors": errors
    }


# ==================== API Documentation ====================

@partner_router.get("/docs")
async def partner_api_docs():
    """Get Partner API documentation."""
    return {
        "name": "Waiting The Longest Partner API",
        "version": "1.0.0",
        "description": "API for shelter partners to manage animal listings",
        "base_url": "https://waitingthelongest.com/api/partner",
        "authentication": {
            "type": "API Key",
            "header": "X-API-Key",
            "format": "wtl_xxxxxxxxxxxxx"
        },
        "endpoints": {
            "POST /register": "Register as a partner (get API key)",
            "GET /status": "Check account status",
            "POST /animals": "Submit new animal",
            "GET /animals": "List your animals",
            "PUT /animals/{id}": "Update animal",
            "DELETE /animals/{id}": "Mark as adopted/removed",
            "POST /animals/bulk": "Bulk submit (up to 100)",
            "POST /webhook": "Configure webhooks"
        },
        "rate_limits": {
            "default": "100 requests/hour",
            "bulk": "10 requests/hour"
        },
        "support": "partners@waitingthelongest.com"
    }

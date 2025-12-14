"""
===============================================================================
Waiting The Longest™ - Main FastAPI Application
===============================================================================
Purpose: FastAPI application entry point. Defines all HTTP endpoints, 
         middleware configuration, and application lifecycle management.

Author: Waiting The Longest™ Development Team
Last Updated: 2025-01-15
Dependencies: fastapi, slowapi, sqlalchemy, pydantic
Related Files: config.py, database.py, models.py, schemas.py, crud.py

IMPORTANT: Any changes to this file MUST be documented in OWNERS_MANUAL.md

Mission: Help shelter animals who have waited the longest find forever homes.
Tagline: "Because Every Day Matters"
===============================================================================
"""

from fastapi import FastAPI, Depends, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, List
from datetime import datetime, timezone
from contextlib import asynccontextmanager
import logging
import hashlib
import uuid

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from .config import settings
from .database import get_db, engine, Base
from .models import Animal, Observation, Shelter, SuccessStory, EmailSubscriber
from .schemas import (
    AnimalListResponse, AnimalDetailResponse,
    SuccessStoryCreate, SuccessStoryResponse,
    HealthResponse,
    EmailSubscriberCreate, EmailSubscriberResponse,
    EmailPreferencesUpdate, PriceAlertCreate, PriceAlertResponse,
    NewsletterSubscribeResponse, UnsubscribeResponse
)
from .crud import (
    paginate_animals, get_animal_detail,
    create_success_story, get_trending_stories
)
from .email_marketing import EmailMarketingService

from pathlib import Path
from fastapi.responses import FileResponse

# Import monetization modules
from backend.monetization.amazon_associates import AmazonAssociates, track_affiliate_click

# Configure rate limiter
limiter = Limiter(key_func=get_remote_address)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Lifespan context manager (replaces deprecated on_event)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Waiting The Longest API starting up...")
    logger.info("Mission: Help shelter animals who have waited the longest find forever homes")
    # Skip DB initialization during tests (tests handle their own DB setup)
    import os
    if not os.environ.get("TESTING"):
        try:
            Base.metadata.create_all(bind=engine)
        except Exception as e:
            logger.warning(f"Database initialization skipped: {e}")
    yield
    # Shutdown
    logger.info("Waiting The Longest API shutting down...")


# Initialize FastAPI app
app = FastAPI(
    title="Waiting The Longest™ API",
    description="API for the pet adoption platform highlighting animals who have waited the longest",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan
)


# =============================================================================
# Middleware
# =============================================================================

class RequestIDMiddleware(BaseHTTPMiddleware):
    """Add unique request ID to each request for tracing"""
    
    async def dispatch(self, request: Request, call_next):
        # Use provided X-Request-ID or generate new one
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
        request.state.request_id = request_id
        
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add request ID middleware (applied first = runs last, so ID is available early)
app.add_middleware(RequestIDMiddleware)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Health & Info Endpoints
# =============================================================================

@app.get("/", response_model=dict)
async def root():
    """Root endpoint with API information"""
    return {
        "name": "Waiting The Longest™ API",
        "tagline": "Because Every Day Matters",
        "version": "1.0.0",
        "status": "running",
        "documentation": "/api/docs"
    }


@app.get("/health", response_model=HealthResponse)
async def health_check(db: Session = Depends(get_db)):
    """Health check endpoint for monitoring"""
    try:
        # Test database connection
        db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "database": db_status,
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }


# =============================================================================
# Animal Listing Endpoints
# =============================================================================

@app.get("/api/animals", response_model=AnimalListResponse)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute;{settings.RATE_LIMIT_PER_HOUR}/hour")
async def list_animals(
    request: Request,
    species: Optional[str] = Query(None, description="Filter by species (dog/cat)"),
    status: Optional[str] = Query("available", description="Filter by status"),
    breed: Optional[str] = Query(None, description="Filter by breed (partial match)"),
    age_group: Optional[str] = Query(None, description="Filter by age (puppy/young/adult/senior)"),
    size: Optional[str] = Query(None, description="Filter by size (small/medium/large)"),
    gender: Optional[str] = Query(None, description="Filter by gender (male/female)"),
    state: Optional[str] = Query(None, description="Filter by state (e.g., CA, TX)"),
    sort_by: Optional[str] = Query("days_waiting", description="Sort field"),
    sort_order: Optional[str] = Query("desc", description="Sort order (asc/desc)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
):
    """
    List animals with pagination and filtering.

    Default sort is by days_waiting descending (longest waiting first).
    This is the core feature of Waiting The Longest™!
    """
    result = paginate_animals(
        db=db,
        species=species,
        status=status,
        breed=breed,
        age_group=age_group,
        size=size,
        gender=gender,
        state=state,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size
    )

    return result


@app.get("/api/animals/{animal_id}", response_model=AnimalDetailResponse)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute;{settings.RATE_LIMIT_PER_HOUR}/hour")
async def get_animal(
    request: Request,
    animal_id: int,
    db: Session = Depends(get_db)
):
    """Get detailed information about a specific animal"""
    animal = get_animal_detail(db, animal_id)

    if not animal:
        raise HTTPException(status_code=404, detail="Animal not found")

    return animal


@app.get("/api/longest-waiting")
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute;{settings.RATE_LIMIT_PER_HOUR}/hour")
async def longest_waiting_animals(
    request: Request,
    species: Optional[str] = None,
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """
    Get the animals who have waited the longest.
    This is the heart of our mission!
    """
    result = paginate_animals(
        db=db,
        species=species,
        status="available",
        sort_by="days_waiting",
        sort_order="desc",
        page=1,
        page_size=limit
    )

    return {
        "message": "These animals have been waiting the longest for their forever homes",
        "animals": result.items,
        "mission": "Because Every Day Matters"
    }


# =============================================================================
# Success Stories Endpoints
# =============================================================================

@app.post("/api/success-stories", response_model=SuccessStoryResponse)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute;{settings.RATE_LIMIT_PER_HOUR}/hour")
async def submit_success_story(
    request: Request,
    story: SuccessStoryCreate,
    db: Session = Depends(get_db)
):
    """
    Submit a success story for an adopted animal.

    These stories are crucial for our TikTok content and
    inspiring potential adopters!
    """
    try:
        created_story = create_success_story(db, story)
        return {
            "success": True,
            "message": "Thank you for sharing! Your story will help other pets find homes.",
            "story_id": created_story.id
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/success-stories")
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute;{settings.RATE_LIMIT_PER_HOUR}/hour")
async def get_success_stories(
    request: Request,
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """Get recent success stories for display and social content"""
    stories = get_trending_stories(db, limit)

    return {
        "stories": [
            {
                "id": s.id,
                "pet_name": s.animal.canonical_name if s.animal else "Unknown",
                "days_waited": s.days_waited,
                "story_preview": s.story_text[:200] if s.story_text else "",
                "photos": s.photo_urls or [],
                "adoption_date": s.adoption_date.isoformat() if s.adoption_date else None
            }
            for s in stories
        ],
        "message": "Every adoption is a victory!"
    }


# =============================================================================
# Statistics Endpoints
# =============================================================================

@app.get("/api/stats")
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute;{settings.RATE_LIMIT_PER_HOUR}/hour")
async def get_statistics(request: Request, db: Session = Depends(get_db)):
    """Get platform statistics"""
    from sqlalchemy import func

    total_animals = db.query(func.count(Animal.id)).scalar() or 0
    available_animals = db.query(func.count(Animal.id)).filter(
        Animal.status == "available"
    ).scalar() or 0

    # Average waiting time
    avg_wait = db.query(func.avg(
        func.extract('day', func.now() - Animal.first_seen_at)
    )).filter(Animal.status == "available").scalar() or 0

    # Longest waiting
    longest = db.query(Animal).filter(
        Animal.status == "available"
    ).order_by(Animal.first_seen_at.asc()).first()

    longest_wait_days = 0
    if longest and longest.first_seen_at:
        longest_wait_days = (datetime.utcnow() - longest.first_seen_at).days

    # Success stories count
    success_count = db.query(func.count(SuccessStory.id)).scalar() or 0

    # Get most recent observation timestamp for "data freshness"
    latest_observation = db.query(func.max(Observation.last_seen_at)).scalar()
    data_updated_at = latest_observation.isoformat() if latest_observation else None

    return {
        "total_animals": total_animals,
        "available_animals": available_animals,
        "average_wait_days": round(float(avg_wait), 1),
        "longest_wait_days": longest_wait_days,
        "success_stories": success_count,
        "mission": "Because Every Day Matters",
        "updated_at": datetime.utcnow().isoformat(),
        "data_updated_at": data_updated_at
    }


# =============================================================================
# Affiliate & Products Endpoints
# =============================================================================

@app.post("/api/affiliate/click")
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute;{settings.RATE_LIMIT_PER_HOUR}/hour")
async def track_affiliate_click_endpoint(
    request: Request,
    product_id: str = Query(..., description="Product ID being clicked"),
    source_page: Optional[str] = Query(None, description="Page where click originated"),
    animal_id: Optional[int] = Query(None, description="Associated animal ID"),
    db: Session = Depends(get_db)
):
    """
    Track affiliate link clicks for analytics and revenue attribution.
    
    IP addresses are hashed for privacy.
    """
    # Get client IP and hash it for privacy
    client_ip = get_remote_address(request)
    
    try:
        click_id = track_affiliate_click(
            db=db,
            product_id=product_id,
            program="amazon",
            source_page=source_page,
            animal_id=animal_id,
            ip_address=client_ip
        )
        
        return {
            "success": True,
            "click_id": click_id,
            "message": "Click tracked successfully"
        }
    except Exception as e:
        logger.error(f"Failed to track affiliate click: {e}")
        raise HTTPException(status_code=500, detail="Failed to track click")


@app.get("/api/products/recommendations")
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute;{settings.RATE_LIMIT_PER_HOUR}/hour")
async def get_product_recommendations(
    request: Request,
    pet_type: str = Query(..., description="Pet type (dog/cat)"),
    pet_age: Optional[str] = Query(None, description="Pet age group (puppy/adult/senior)"),
    pet_size: Optional[str] = Query(None, description="Pet size (small/medium/large)"),
    limit: int = Query(5, ge=1, le=20, description="Maximum number of recommendations")
):
    """
    Get personalized product recommendations with affiliate links.
    
    Returns curated products for new pet adopters to help them
    get supplies for their new family member.
    
    Disclosure: As an Amazon Associate, Waiting The Longest earns from qualifying purchases.
    """
    # Validate pet_type
    if pet_type not in ["dog", "cat", "both"]:
        raise HTTPException(
            status_code=400,
            detail="pet_type must be 'dog', 'cat', or 'both'"
        )
    
    # Validate pet_age if provided
    if pet_age and pet_age not in ["puppy", "adult", "senior"]:
        raise HTTPException(
            status_code=400,
            detail="pet_age must be 'puppy', 'adult', or 'senior'"
        )
    
    # Validate pet_size if provided
    if pet_size and pet_size not in ["small", "medium", "large"]:
        raise HTTPException(
            status_code=400,
            detail="pet_size must be 'small', 'medium', or 'large'"
        )
    
    recommendations = AmazonAssociates.get_recommendations(
        pet_type=pet_type,
        pet_age=pet_age,
        pet_size=pet_size,
        limit=limit
    )
    
    return {
        "products": recommendations,
        "count": len(recommendations),
        "pet_type": pet_type,
        "disclosure": "As an Amazon Associate, Waiting The Longest earns from qualifying purchases."
    }


# =============================================================================
# Email Marketing Endpoints
# =============================================================================

@app.post("/api/newsletter/subscribe", response_model=NewsletterSubscribeResponse)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute;{settings.RATE_LIMIT_PER_HOUR}/hour")
async def subscribe_to_newsletter(
    request: Request,
    subscriber: EmailSubscriberCreate,
    db: Session = Depends(get_db)
):
    """
    Subscribe to the Waiting The Longest™ newsletter.
    
    Subscribers receive:
    - Weekly "Longest Waiting" newsletter (Sundays at 10 AM)
    - Adoption success stories
    - Pet care tips with affiliate product recommendations
    - Special offers and updates
    
    CAN-SPAM and GDPR compliant. Unsubscribe anytime.
    """
    try:
        created_subscriber = EmailMarketingService.subscribe(db, subscriber)
        
        return {
            "success": True,
            "message": "Welcome to the pack! Check your email to confirm your subscription.",
            "subscriber_id": created_subscriber.id,
            "requires_verification": not created_subscriber.is_verified
        }
    except Exception as e:
        logger.error(f"Newsletter subscription failed: {e}")
        raise HTTPException(status_code=400, detail="Subscription failed. Please try again.")


@app.post("/api/newsletter/unsubscribe", response_model=UnsubscribeResponse)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute;{settings.RATE_LIMIT_PER_HOUR}/hour")
async def unsubscribe_from_newsletter(
    request: Request,
    email: str = Query(..., description="Email address to unsubscribe"),
    token: Optional[str] = Query(None, description="Unsubscribe token for verification"),
    db: Session = Depends(get_db)
):
    """
    Unsubscribe from marketing emails.
    
    We honor unsubscribe requests immediately (CAN-SPAM requires within 10 days).
    You can resubscribe at any time.
    """
    success = EmailMarketingService.unsubscribe(db, email, token)
    
    if success:
        return {
            "success": True,
            "message": "You have been unsubscribed. We'll miss you! 🐾"
        }
    else:
        return {
            "success": False,
            "message": "Email not found or already unsubscribed."
        }


@app.get("/api/newsletter/verify")
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute;{settings.RATE_LIMIT_PER_HOUR}/hour")
async def verify_email(
    request: Request,
    email: str = Query(..., description="Email address to verify"),
    token: str = Query(..., description="Verification token"),
    db: Session = Depends(get_db)
):
    """Verify subscriber email address"""
    success = EmailMarketingService.verify_email(db, email, token)
    
    if success:
        return {
            "success": True,
            "message": "Email verified! You're all set to receive our updates."
        }
    else:
        raise HTTPException(status_code=400, detail="Invalid or expired verification link.")


@app.put("/api/newsletter/preferences/{subscriber_id}", response_model=EmailSubscriberResponse)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute;{settings.RATE_LIMIT_PER_HOUR}/hour")
async def update_email_preferences(
    request: Request,
    subscriber_id: int,
    preferences: EmailPreferencesUpdate,
    db: Session = Depends(get_db)
):
    """
    Update email preferences.
    
    Control what types of emails you receive:
    - Newsletter: Weekly longest waiting pets digest
    - Product updates: New features and improvements
    - Adoption alerts: Animals matching your preferences
    - Affiliate emails: Product recommendations and deals
    """
    subscriber = EmailMarketingService.update_preferences(db, subscriber_id, preferences)
    
    if not subscriber:
        raise HTTPException(status_code=404, detail="Subscriber not found")
    
    return subscriber


@app.post("/api/alerts", response_model=PriceAlertResponse)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute;{settings.RATE_LIMIT_PER_HOUR}/hour")
async def create_price_alert(
    request: Request,
    alert: PriceAlertCreate,
    email: str = Query(..., description="Subscriber email address"),
    db: Session = Depends(get_db)
):
    """
    Create a price or availability alert.
    
    Alert types:
    - price_drop: Get notified when a product drops to your target price
    - animal_available: Get notified when a specific animal becomes available
    - new_arrival: Get notified about new arrivals matching your preferences
    
    Alerts expire after 90 days.
    """
    subscriber = EmailMarketingService.get_subscriber_by_email(db, email)
    
    if not subscriber:
        raise HTTPException(
            status_code=404, 
            detail="Please subscribe to newsletter first to set alerts."
        )
    
    if not subscriber.is_active:
        raise HTTPException(
            status_code=400,
            detail="Your subscription is inactive. Please resubscribe to set alerts."
        )
    
    created_alert = EmailMarketingService.create_price_alert(db, subscriber.id, alert)
    return created_alert


@app.get("/api/alerts", response_model=List[PriceAlertResponse])
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute;{settings.RATE_LIMIT_PER_HOUR}/hour")
async def get_price_alerts(
    request: Request,
    email: str = Query(..., description="Subscriber email address"),
    db: Session = Depends(get_db)
):
    """Get all active alerts for a subscriber"""
    subscriber = EmailMarketingService.get_subscriber_by_email(db, email)
    
    if not subscriber:
        raise HTTPException(status_code=404, detail="Subscriber not found")
    
    alerts = EmailMarketingService.get_active_alerts(db, subscriber.id)
    return alerts


@app.delete("/api/alerts/{alert_id}")
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute;{settings.RATE_LIMIT_PER_HOUR}/hour")
async def delete_price_alert(
    request: Request,
    alert_id: int,
    email: str = Query(..., description="Subscriber email address"),
    db: Session = Depends(get_db)
):
    """Deactivate a price alert"""
    subscriber = EmailMarketingService.get_subscriber_by_email(db, email)
    
    if not subscriber:
        raise HTTPException(status_code=404, detail="Subscriber not found")
    
    success = EmailMarketingService.deactivate_alert(db, alert_id, subscriber.id)
    
    if success:
        return {"success": True, "message": "Alert deactivated"}
    else:
        raise HTTPException(status_code=404, detail="Alert not found")


@app.post("/api/favorites/{animal_id}/remind")
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute;{settings.RATE_LIMIT_PER_HOUR}/hour")
async def start_still_waiting_reminder(
    request: Request,
    animal_id: int,
    email: str = Query(..., description="Subscriber email address"),
    db: Session = Depends(get_db)
):
    """
    Start "still waiting" reminder sequence for a favorited animal.
    
    Sends reminder emails at 3, 7, and 14 days if the animal is still available.
    Perfect for keeping track of animals you're interested in!
    """
    subscriber = EmailMarketingService.get_subscriber_by_email(db, email)
    
    if not subscriber:
        raise HTTPException(
            status_code=404,
            detail="Please subscribe to newsletter first to receive reminders."
        )
    
    if not subscriber.adoption_alerts_enabled:
        raise HTTPException(
            status_code=400,
            detail="Please enable adoption alerts in your preferences."
        )
    
    sequence = EmailMarketingService.start_still_waiting_reminder(db, subscriber.id, animal_id)
    
    if sequence:
        return {
            "success": True,
            "message": "We'll remind you about this pet! Check your inbox.",
            "sequence_id": sequence.id
        }
    else:
        raise HTTPException(status_code=404, detail="Animal not found")


@app.get("/api/email/stats")
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute;{settings.RATE_LIMIT_PER_HOUR}/hour")
async def get_email_stats(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Get email marketing statistics.
    
    Returns subscriber counts, open rates, click rates, and comparison to targets.
    """
    stats = EmailMarketingService.get_email_stats(db)
    return stats


@app.post("/api/email/track/open/{email_id}")
async def track_email_open(
    email_id: int,
    db: Session = Depends(get_db)
):
    """Track email open event (typically called from email tracking pixel)"""
    EmailMarketingService.track_email_open(db, email_id)
    # Return 1x1 transparent pixel
    return JSONResponse(
        content={},
        headers={"Content-Type": "image/gif"}
    )


@app.post("/api/email/track/click/{email_id}")
async def track_email_click(
    email_id: int,
    redirect_url: str = Query(..., description="URL to redirect to"),
    db: Session = Depends(get_db)
):
    """Track email click event and redirect"""
    EmailMarketingService.track_email_click(db, email_id)
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=redirect_url)


# =============================================================================
# Error Handlers
# =============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "Something went wrong. Please try again later."
        }
    )


# =============================================================================
# New API Endpoints: Shelters, Breeds, Filters
# =============================================================================

@app.get("/api/shelters")
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute;{settings.RATE_LIMIT_PER_HOUR}/hour")
async def list_shelters(
    request: Request,
    state: Optional[str] = Query(None, description="Filter by state abbreviation"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    List all shelters and rescue organizations.
    
    Returns shelter names, locations, and contact information.
    """
    from sqlalchemy import func
    
    query = db.query(Shelter)
    
    if state:
        query = query.filter(Shelter.state.ilike(f"%{state}%"))
    
    total = query.count()
    offset = (page - 1) * page_size
    shelters = query.order_by(Shelter.name).offset(offset).limit(page_size).all()
    
    return {
        "items": [
            {
                "id": s.id,
                "name": s.name,
                "city": s.city,
                "state": s.state,
                "email": s.email,
                "phone": s.phone,
                "website": s.website,
                "total_animals": s.total_animals
            }
            for s in shelters
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }


@app.get("/api/shelters/{shelter_id}")
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute;{settings.RATE_LIMIT_PER_HOUR}/hour")
async def get_shelter(
    request: Request,
    shelter_id: int,
    db: Session = Depends(get_db)
):
    """Get detailed information about a specific shelter"""
    shelter = db.query(Shelter).filter(Shelter.id == shelter_id).first()
    
    if not shelter:
        raise HTTPException(status_code=404, detail="Shelter not found")
    
    # Get animal count for this shelter
    from sqlalchemy import func
    animal_count = db.query(func.count(Observation.id)).filter(
        Observation.shelter_id == shelter_id
    ).scalar() or 0
    
    return {
        "id": shelter.id,
        "name": shelter.name,
        "address": shelter.address,
        "city": shelter.city,
        "state": shelter.state,
        "zip_code": shelter.zip_code,
        "email": shelter.email,
        "phone": shelter.phone,
        "website": shelter.website,
        "latitude": shelter.latitude,
        "longitude": shelter.longitude,
        "total_animals": animal_count,
        "created_at": shelter.created_at.isoformat() if shelter.created_at else None
    }


@app.get("/api/breeds")
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute;{settings.RATE_LIMIT_PER_HOUR}/hour")
async def list_breeds(
    request: Request,
    species: Optional[str] = Query(None, description="Filter by species (dog/cat)"),
    db: Session = Depends(get_db)
):
    """
    Get list of unique breeds in the database.
    
    Useful for populating filter dropdowns.
    """
    from sqlalchemy import distinct
    
    query = db.query(distinct(Animal.breed_primary)).filter(
        Animal.breed_primary.isnot(None),
        Animal.breed_primary != ""
    )
    
    if species:
        query = query.filter(Animal.species == species)
    
    breeds = [row[0] for row in query.order_by(Animal.breed_primary).all()]
    
    return {
        "breeds": breeds,
        "count": len(breeds),
        "species": species
    }


@app.get("/api/filters")
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute;{settings.RATE_LIMIT_PER_HOUR}/hour")
async def get_filter_options(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Get all available filter options.
    
    Returns counts for each filter value to help users understand data distribution.
    """
    from sqlalchemy import func, distinct
    
    # Species counts
    species_counts = db.query(
        Animal.species,
        func.count(Animal.id)
    ).filter(Animal.status == "available").group_by(Animal.species).all()
    
    # Age group counts
    age_counts = db.query(
        Animal.age_group,
        func.count(Animal.id)
    ).filter(
        Animal.status == "available",
        Animal.age_group.isnot(None)
    ).group_by(Animal.age_group).all()
    
    # Size counts
    size_counts = db.query(
        Animal.size,
        func.count(Animal.id)
    ).filter(
        Animal.status == "available",
        Animal.size.isnot(None)
    ).group_by(Animal.size).all()
    
    # Gender counts
    gender_counts = db.query(
        Animal.gender,
        func.count(Animal.id)
    ).filter(
        Animal.status == "available",
        Animal.gender.isnot(None)
    ).group_by(Animal.gender).all()
    
    # State counts (from observations)
    state_counts = db.query(
        Observation.state,
        func.count(distinct(Observation.animal_id))
    ).join(Animal).filter(
        Animal.status == "available",
        Observation.state.isnot(None)
    ).group_by(Observation.state).all()
    
    return {
        "species": [{"value": s, "count": c} for s, c in species_counts if s],
        "age_groups": [{"value": a, "count": c} for a, c in age_counts if a],
        "sizes": [{"value": s, "count": c} for s, c in size_counts if s],
        "genders": [{"value": g, "count": c} for g, c in gender_counts if g],
        "states": [{"value": s, "count": c} for s, c in state_counts if s]
    }


@app.get("/api/animals/{animal_id}/similar")
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute;{settings.RATE_LIMIT_PER_HOUR}/hour")
async def get_similar_animals(
    request: Request,
    animal_id: int,
    limit: int = Query(6, ge=1, le=20),
    db: Session = Depends(get_db)
):
    """
    Get animals similar to the specified animal.
    
    Similarity is based on species, breed, size, and age.
    """
    # Get the target animal
    animal = db.query(Animal).filter(Animal.id == animal_id).first()
    if not animal:
        raise HTTPException(status_code=404, detail="Animal not found")
    
    # Find similar animals
    query = db.query(Animal).filter(
        Animal.id != animal_id,
        Animal.status == "available",
        Animal.species == animal.species
    )
    
    # Prefer same breed
    if animal.breed_primary:
        similar = query.filter(
            Animal.breed_primary == animal.breed_primary
        ).limit(limit).all()
        
        if len(similar) < limit:
            # Add more by size/age
            more = query.filter(
                Animal.id.notin_([a.id for a in similar]),
                (Animal.size == animal.size) | (Animal.age_group == animal.age_group)
            ).limit(limit - len(similar)).all()
            similar.extend(more)
    else:
        similar = query.filter(
            (Animal.size == animal.size) | (Animal.age_group == animal.age_group)
        ).limit(limit).all()
    
    # Format response
    from .schemas import AnimalListItem
    items = []
    for a in similar:
        photo_url = None
        city = None
        state = None
        if a.observations:
            obs = a.observations[0]
            photo_url = obs.photo_url
            city = obs.city
            state = obs.state
        
        items.append({
            "id": a.id,
            "species": a.species,
            "canonical_name": a.canonical_name,
            "breed_primary": a.breed_primary,
            "age_group": a.age_group,
            "size": a.size,
            "gender": a.gender,
            "status": a.status,
            "days_waiting": a.days_waiting,
            "first_seen_at": a.first_seen_at.isoformat() if a.first_seen_at else None,
            "photo_url": photo_url,
            "city": city,
            "state": state
        })
    
    return {
        "similar_to": animal.canonical_name or f"Animal #{animal_id}",
        "items": items,
        "count": len(items)
    }


# =============================================================================
# Local Demo UI (served from backend)
# =============================================================================

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"

if FRONTEND_DIR.exists():
    @app.get("/demo", include_in_schema=False)
    async def demo_ui():
        return FileResponse(FRONTEND_DIR / "index.html", media_type="text/html")

    @app.get("/styles.css", include_in_schema=False)
    async def demo_styles():
        return FileResponse(FRONTEND_DIR / "styles.css", media_type="text/css")

    @app.get("/app.js", include_in_schema=False)
    async def demo_app_js():
        return FileResponse(FRONTEND_DIR / "app.js", media_type="application/javascript")
else:
    logger.warning(f"Frontend directory not found at {FRONTEND_DIR}; /demo will be unavailable")


# =============================================================================
# Startup/Shutdown Events (Now handled by lifespan context manager above)
# =============================================================================

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

from fastapi import FastAPI, Depends, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, List
from datetime import datetime, timezone
from contextlib import asynccontextmanager
import logging
import hashlib
import json
import re
from copy import deepcopy

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from .config import settings
from .database import get_db, engine, Base
from .models import Animal, Observation, Shelter, SuccessStory, ContactSubmission, Article
from .schemas import (
    AnimalListResponse, AnimalDetailResponse,
    SuccessStoryCreate, SuccessStoryResponse,
    HealthResponse, ReadinessResponse,
    ContactSubmissionCreate, ContactSubmissionResponse,
    ShelterListResponse, ShelterDetailResponse, ShelterListItem,
    ProductListResponse, ProductListItem
)
from .schemas_article import ArticleResponse, ArticleListResponse, ArticleCreate
from .crud import (
    paginate_animals, get_animal_detail,
    create_success_story, get_trending_stories,
    create_contact_submission, get_shelters, get_shelter_detail
)
from .data.rescue_directory import RESCUE_DIRECTORY

# Import monetization modules
from backend.monetization.amazon_associates import AmazonAssociates, track_affiliate_click

# Configure rate limiter
limiter = Limiter(key_func=get_remote_address)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


RESCUE_CACHE_CONTROL = "public, max-age=900, stale-while-revalidate=300"
APP_BOOT_TIME = datetime.now(timezone.utc)


def _generate_etag(payload: dict) -> str:
    """Generate a stable ETag for JSON-serializable payloads."""
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _slugify(value: Optional[str]) -> str:
    """Convert free-form filter input into a predictable slug."""
    if not value:
        return ""
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


STATE_ALIASES = {
    "massachusetts": "massachusetts",
    "ma": "massachusetts",
    "commonwealth_of_massachusetts": "massachusetts"
}


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

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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

@app.get("/api", response_model=dict)
async def api_root():
    """API root endpoint with API information"""
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


@app.get("/healthz", include_in_schema=False)
async def lightweight_health_check():
    """Fast health probe used by load balancers."""
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }


@app.get("/readyz", response_model=ReadinessResponse)
async def readiness_check(db: Session = Depends(get_db)):
    """Readiness probe that verifies dependencies before routing traffic."""
    checks = {}
    try:
        db.execute(text("SELECT 1"))
        db_status = "healthy"
        checks["database"] = "reachable"
    except Exception as exc:
        db_status = f"unhealthy: {exc}"
        checks["database"] = db_status

    try:
        animal_count = db.execute(text("SELECT COUNT(*) FROM animals"))
        count_value = animal_count.scalar() if animal_count else 0
        checks["animals_index"] = f"{count_value} records reachable"
    except Exception as exc:
        checks["animals_index"] = f"error: {exc}"

    uptime_seconds = (datetime.now(timezone.utc) - APP_BOOT_TIME).total_seconds()

    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "database": db_status,
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "uptime_seconds": uptime_seconds,
        "rescue_directory_version": RESCUE_DIRECTORY["metadata"].get("version", "unknown"),
        "checks": checks
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

    return {
        "total_animals": total_animals,
        "available_animals": available_animals,
        "average_wait_days": round(float(avg_wait), 1),
        "longest_wait_days": longest_wait_days,
        "success_stories": success_count,
        "mission": "Because Every Day Matters",
        "updated_at": datetime.utcnow().isoformat()
    }


# =============================================================================
# Resource Directory Endpoints
# =============================================================================

@app.get("/api/resources/rescues")
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute;{settings.RATE_LIMIT_PER_HOUR}/hour")
async def get_rescue_resources(
    request: Request,
    state: Optional[str] = Query(None, description="Filter to a single state's directory (e.g., 'MA' or 'Massachusetts')"),
    network_region: Optional[str] = Query(None, description="Filter national transport partners by region slug (e.g., 'southern_source')"),
    breed: Optional[str] = Query(None, description="Filter AKC breed network entries by breed name"),
    include_counts: bool = Query(True, description="Include summary counts for quick UI badges")
):
    """Serve curated rescue directory data for shelters page widgets."""
    directory = deepcopy(RESCUE_DIRECTORY)
    applied_filters = {}

    if state:
        state_slug = STATE_ALIASES.get(_slugify(state), _slugify(state))
        states_payload = directory.get("states", {})
        matched_entries = states_payload.get(state_slug, [])
        directory["states"] = {state_slug: matched_entries} if matched_entries else {}
        applied_filters["state"] = state_slug

    if network_region:
        region_slug = _slugify(network_region)
        national_payload = directory.get("national", {})
        matched_regions = national_payload.get(region_slug, [])
        directory["national"] = {region_slug: matched_regions} if matched_regions else {}
        applied_filters["network_region"] = region_slug

    if breed:
        breed_lower = breed.lower()
        directory["akc_network"] = [
            entry for entry in directory.get("akc_network", [])
            if breed_lower in entry.get("breed", "").lower()
        ]
        applied_filters["breed"] = breed

    directory["applied_filters"] = applied_filters

    if include_counts:
        directory["counts"] = {
            "state_groups": len(directory.get("states", {})),
            "state_entries": sum(len(entries) for entries in directory.get("states", {}).values()),
            "network_regions": len(directory.get("national", {})),
            "network_entries": sum(len(entries) for entries in directory.get("national", {}).values()),
            "akc_entries": len(directory.get("akc_network", []))
        }

    etag_value = _generate_etag(directory)
    client_tag = request.headers.get("if-none-match")

    headers = {
        "ETag": etag_value,
        "Cache-Control": RESCUE_CACHE_CONTROL,
        "Vary": "Accept-Encoding, If-None-Match",
    }

    if client_tag == etag_value:
        return Response(status_code=304, headers=headers)

    response = JSONResponse(directory)
    for header, value in headers.items():
        response.headers[header] = value
    return response


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
# Contact Form Endpoints
# =============================================================================

@app.post("/api/contact", response_model=ContactSubmissionResponse)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute;{settings.RATE_LIMIT_PER_HOUR}/hour")
async def submit_contact_form(
    request: Request,
    submission: ContactSubmissionCreate,
    db: Session = Depends(get_db)
):
    """
    Submit a contact form message.
    
    Accepts contact form submissions from users including inquiries,
    feedback, partnership requests, or general questions about
    Waiting The Longest™.
    
    Rate limited to prevent spam.
    """
    try:
        # Get client IP and hash it for privacy/spam prevention
        client_ip = get_remote_address(request)
        ip_hash = hashlib.sha256(client_ip.encode()).hexdigest() if client_ip else None
        
        # Get user agent for analytics
        user_agent = request.headers.get("user-agent", None)
        
        # Log the submission for monitoring
        logger.info(f"Contact form submission from {submission.email}: {submission.subject}")
        
        # Create the submission
        created = create_contact_submission(
            db=db,
            submission=submission,
            ip_hash=ip_hash,
            user_agent=user_agent
        )
        
        return {
            "success": True,
            "message": "Thank you for contacting us! We'll get back to you soon.",
            "submission_id": created.id
        }
    except Exception as e:
        logger.error(f"Failed to process contact form: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit contact form")


# =============================================================================
# Shelter Endpoints
# =============================================================================

@app.get("/api/shelters", response_model=ShelterListResponse)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute;{settings.RATE_LIMIT_PER_HOUR}/hour")
async def list_shelters(
    request: Request,
    state: Optional[str] = Query(None, description="Filter by state (e.g., CA, TX)"),
    search: Optional[str] = Query(None, description="Search by name, city, or state"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
):
    """
    List all shelters with animal counts.
    
    Returns paginated shelter information including the number of
    animals currently at each shelter. Can be filtered by state.
    """
    result = get_shelters(
        db=db,
        page=page,
        page_size=page_size,
        state=state,
        search=search
    )
    
    return result


@app.get("/api/shelters/{shelter_id}", response_model=ShelterDetailResponse)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute;{settings.RATE_LIMIT_PER_HOUR}/hour")
async def get_shelter(
    request: Request,
    shelter_id: int,
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific shelter.
    
    Returns complete shelter information including contact details,
    location, and a list of animals currently at this shelter.
    """
    shelter = get_shelter_detail(db, shelter_id)
    
    if not shelter:
        raise HTTPException(status_code=404, detail="Shelter not found")
    
    return shelter


# =============================================================================
# Products Endpoint
# =============================================================================

@app.get("/api/products", response_model=ProductListResponse)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute;{settings.RATE_LIMIT_PER_HOUR}/hour")
async def get_products(
    request: Request,
    pet_type: Optional[str] = Query(None, description="Filter by pet type (dog/cat/both)"),
    category: Optional[str] = Query(None, description="Filter by category (food/toys/beds/etc.)"),
    pet_age: Optional[str] = Query(None, description="Filter by pet age (puppy/adult/senior)"),
    pet_size: Optional[str] = Query(None, description="Filter by pet size (small/medium/large)"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of products")
):
    """
    Get affiliate product recommendations.
    
    Returns curated pet product recommendations with Amazon affiliate links.
    Products can be filtered by pet type, category, age, and size.
    
    Disclosure: As an Amazon Associate, Waiting The Longest earns from 
    qualifying purchases.
    """
    # Validate pet_type if provided
    if pet_type and pet_type not in ["dog", "cat", "both"]:
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
    
    # Get recommendations from Amazon Associates module
    recommendations = AmazonAssociates.get_recommendations(
        pet_type=pet_type or "both",
        pet_age=pet_age,
        pet_size=pet_size,
        category=category,
        limit=limit
    )
    
    # Transform to response format
    # Note: get_recommendations returns {name, category, description, price_range, affiliate_url, asin}
    products = [
        ProductListItem(
            product_id=p.get("asin", ""),
            name=p["name"],
            category=p["category"],
            pet_type=pet_type or "both",
            price_range=p["price_range"],
            affiliate_url=p["affiliate_url"],
            description=p.get("description"),
            image_url=p.get("image_url")
        )
        for p in recommendations
    ]
    
    return ProductListResponse(
        products=products,
        count=len(products),
        pet_type=pet_type,
        category=category,
        disclosure="As an Amazon Associate, Waiting The Longest earns from qualifying purchases."
    )


# =============================================================================
# Knowledge Library Endpoints
# =============================================================================

@app.get("/api/test_articles")
def test_articles_endpoint():
    return {"message": "Articles endpoint is reachable"}

@app.get("/api/articles", response_model=ArticleListResponse)
def list_articles(
    category: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List articles from the Knowledge Library."""
    logger.info(f"Fetching articles. Category: {category}, Limit: {limit}")
    query = db.query(Article).filter(Article.is_published == True)
    if category:
        query = query.filter(Article.category == category)
    
    articles = query.order_by(Article.created_at.desc()).limit(limit).all()
    logger.info(f"Found {len(articles)} articles")
    return {"items": articles, "total": len(articles)}

@app.get("/api/articles/{slug}", response_model=ArticleResponse)
def get_article(slug: str, db: Session = Depends(get_db)):
    """Get a single article by slug."""
    article = db.query(Article).filter(Article.slug == slug).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    # Increment views
    article.views += 1
    db.commit()
    db.refresh(article)
    
    return article

@app.post("/api/articles", response_model=ArticleResponse)
def create_article(article: ArticleCreate, db: Session = Depends(get_db)):
    """Create a new article (Internal/Agent use)."""
    db_article = Article(**article.dict())
    db.add(db_article)
    try:
        db.commit()
        db.refresh(db_article)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    return db_article


# =============================================================================
# Static Files - Serve Frontend
# =============================================================================

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
from pathlib import Path

# Get the path to frontend directory
# Resolve from backend/app/main.py to root/frontend
BASE_DIR = Path(__file__).resolve().parent.parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

logger.info(f"Frontend directory resolved to: {FRONTEND_DIR}")
logger.info(f"Frontend directory exists: {FRONTEND_DIR.exists()}")

# Serve static files (CSS, JS, images)
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    # Serve HTML pages
    @app.get("/{page}.html")
    async def serve_html(page: str):
        file_path = FRONTEND_DIR / f"{page}.html"
        if file_path.exists():
            return FileResponse(file_path, media_type="text/html")
        # Return 404 page if exists
        not_found = FRONTEND_DIR / "404.html"
        if not_found.exists():
            return FileResponse(not_found, media_type="text/html", status_code=404)
        raise HTTPException(status_code=404, detail="Page not found")

    @app.get("/styles.css")
    async def serve_css():
        return FileResponse(FRONTEND_DIR / "styles.css", media_type="text/css")

    @app.get("/app.js")
    async def serve_js():
        return FileResponse(FRONTEND_DIR / "app.js", media_type="application/javascript")

    # Serve index.html at root and /home
    @app.get("/")
    async def serve_root():
        return FileResponse(FRONTEND_DIR / "index.html", media_type="text/html")

    @app.get("/home")
    async def serve_home():
        return FileResponse(FRONTEND_DIR / "index.html", media_type="text/html")
else:
    logger.error(f"CRITICAL: Frontend directory not found at {FRONTEND_DIR}")
    
    @app.get("/")
    async def serve_root_error():
        return JSONResponse(
            status_code=404, 
            content={"detail": f"Frontend not found. Expected at: {FRONTEND_DIR}"}
        )


# =============================================================================
# Startup/Shutdown Events (Now handled by lifespan context manager above)
# =============================================================================

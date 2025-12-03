"""
===============================================================================
Waiting The Longest™ - Main FastAPI Application
===============================================================================
Mission: Help shelter animals who have waited the longest find forever homes.
Tagline: "Because Every Day Matters"

Author: Waiting The Longest™ Development Team
===============================================================================
"""

from fastapi import FastAPI, Depends, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, List
from datetime import datetime, timezone
from contextlib import asynccontextmanager
import logging

from .config import settings
from .database import get_db, engine, Base
from .models import Animal, Observation, Shelter, SuccessStory
from .schemas import (
    AnimalListResponse, AnimalDetailResponse,
    SuccessStoryCreate, SuccessStoryResponse,
    HealthResponse
)
from .crud import (
    paginate_animals, get_animal_detail,
    create_success_story, get_trending_stories
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Lifespan context manager (replaces deprecated on_event)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Waiting The Longest API starting up...")
    logger.info("Mission: Help shelter animals who have waited the longest find forever homes")
    Base.metadata.create_all(bind=engine)
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
async def list_animals(
    request: Request,
    species: Optional[str] = Query(None, description="Filter by species (dog/cat)"),
    status: Optional[str] = Query("available", description="Filter by status"),
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
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size
    )

    return result


@app.get("/api/animals/{animal_id}", response_model=AnimalDetailResponse)
async def get_animal(
    animal_id: int,
    db: Session = Depends(get_db)
):
    """Get detailed information about a specific animal"""
    animal = get_animal_detail(db, animal_id)

    if not animal:
        raise HTTPException(status_code=404, detail="Animal not found")

    return animal


@app.get("/api/longest-waiting")
async def longest_waiting_animals(
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
async def submit_success_story(
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
async def get_success_stories(
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
async def get_statistics(db: Session = Depends(get_db)):
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
# Startup/Shutdown Events (Now handled by lifespan context manager above)
# =============================================================================

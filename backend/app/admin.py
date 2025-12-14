"""
Waiting The Longest™ - Admin API Endpoints
============================================
Administrative endpoints for data management.
"""

from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.database import get_db
from backend.app import models, schemas


router = APIRouter(prefix="/admin", tags=["admin"])


# =============================================================================
# Request/Response Models
# =============================================================================

class AdminStats(BaseModel):
    """Admin dashboard statistics."""
    total_animals: int
    total_shelters: int
    animals_adopted_this_month: int
    animals_added_this_month: int
    average_wait_days: float
    longest_waiting_days: int
    animals_by_species: dict[str, int]
    animals_by_status: dict[str, int]


class IngestRequest(BaseModel):
    """Request to trigger data ingestion."""
    source: str  # rescuegroups, petfinder, etc.
    shelter_id: Optional[int] = None
    full_sync: bool = False


class IngestStatus(BaseModel):
    """Status of an ingestion job."""
    job_id: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    animals_processed: int = 0
    errors: list[str] = []


class BulkUpdateRequest(BaseModel):
    """Bulk update request."""
    animal_ids: list[int]
    updates: dict


class ExportRequest(BaseModel):
    """Data export request."""
    format: str = "csv"  # csv, json, xlsx
    filters: dict = {}
    include_adopted: bool = False


class NotificationRequest(BaseModel):
    """Send notification to subscribers."""
    subject: str
    message: str
    animal_ids: Optional[list[int]] = None  # If specified, about these animals


# =============================================================================
# Dashboard Stats
# =============================================================================

@router.get("/stats", response_model=AdminStats)
def get_admin_stats(db: Session = Depends(get_db)):
    """
    Get admin dashboard statistics.
    """
    now = datetime.utcnow()
    month_ago = now - timedelta(days=30)
    
    # Total counts
    total_animals = db.query(models.Animal).filter(
        models.Animal.is_adopted == False
    ).count()
    
    total_shelters = db.query(models.Shelter).count()
    
    # This month stats
    adopted_this_month = db.query(models.Animal).filter(
        models.Animal.is_adopted == True,
        models.Animal.updated_at >= month_ago,
    ).count()
    
    added_this_month = db.query(models.Animal).filter(
        models.Animal.created_at >= month_ago,
    ).count()
    
    # Wait time stats
    wait_stats = db.query(
        func.avg(func.julianday('now') - func.julianday(models.Animal.intake_date)).label('avg'),
        func.max(func.julianday('now') - func.julianday(models.Animal.intake_date)).label('max'),
    ).filter(
        models.Animal.is_adopted == False,
        models.Animal.intake_date.isnot(None),
    ).first()
    
    avg_wait = round(wait_stats.avg or 0, 1)
    max_wait = int(wait_stats.max or 0)
    
    # By species
    species_counts = db.query(
        models.Animal.species,
        func.count(models.Animal.id),
    ).filter(
        models.Animal.is_adopted == False,
    ).group_by(models.Animal.species).all()
    
    animals_by_species = {s or "Unknown": c for s, c in species_counts}
    
    # By status
    animals_by_status = {
        "available": db.query(models.Animal).filter(
            models.Animal.is_adopted == False
        ).count(),
        "adopted": db.query(models.Animal).filter(
            models.Animal.is_adopted == True
        ).count(),
    }
    
    return AdminStats(
        total_animals=total_animals,
        total_shelters=total_shelters,
        animals_adopted_this_month=adopted_this_month,
        animals_added_this_month=added_this_month,
        average_wait_days=avg_wait,
        longest_waiting_days=max_wait,
        animals_by_species=animals_by_species,
        animals_by_status=animals_by_status,
    )


# =============================================================================
# Data Ingestion
# =============================================================================

@router.post("/ingest", response_model=IngestStatus)
async def trigger_ingestion(
    request: IngestRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Trigger data ingestion from a source.
    """
    import uuid
    
    job_id = str(uuid.uuid4())
    
    # Queue background job
    background_tasks.add_task(
        run_ingestion,
        job_id=job_id,
        source=request.source,
        shelter_id=request.shelter_id,
        full_sync=request.full_sync,
    )
    
    return IngestStatus(
        job_id=job_id,
        status="queued",
        started_at=datetime.utcnow(),
    )


async def run_ingestion(
    job_id: str,
    source: str,
    shelter_id: int | None,
    full_sync: bool,
):
    """Background task to run ingestion."""
    # Implementation would use the ingestors module
    pass


@router.get("/ingest/{job_id}", response_model=IngestStatus)
def get_ingestion_status(job_id: str):
    """
    Get status of an ingestion job.
    """
    # Would query job status from storage
    return IngestStatus(
        job_id=job_id,
        status="completed",
        started_at=datetime.utcnow() - timedelta(minutes=5),
        completed_at=datetime.utcnow(),
        animals_processed=150,
    )


# =============================================================================
# Bulk Operations
# =============================================================================

@router.post("/animals/bulk-update")
def bulk_update_animals(
    request: BulkUpdateRequest,
    db: Session = Depends(get_db),
):
    """
    Update multiple animals at once.
    """
    if not request.animal_ids:
        raise HTTPException(400, "No animal IDs provided")
    
    # Only allow certain fields to be bulk updated
    allowed_fields = {"is_adopted", "shelter_id", "status"}
    updates = {k: v for k, v in request.updates.items() if k in allowed_fields}
    
    if not updates:
        raise HTTPException(400, "No valid fields to update")
    
    updated = db.query(models.Animal).filter(
        models.Animal.id.in_(request.animal_ids)
    ).update(updates, synchronize_session=False)
    
    db.commit()
    
    return {"updated": updated, "ids": request.animal_ids}


@router.delete("/animals/bulk-delete")
def bulk_delete_animals(
    animal_ids: list[int] = Query(...),
    db: Session = Depends(get_db),
):
    """
    Delete multiple animals.
    """
    deleted = db.query(models.Animal).filter(
        models.Animal.id.in_(animal_ids)
    ).delete(synchronize_session=False)
    
    db.commit()
    
    return {"deleted": deleted}


# =============================================================================
# Data Export
# =============================================================================

@router.post("/export")
async def export_data(
    request: ExportRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Export data in specified format.
    """
    import uuid
    
    export_id = str(uuid.uuid4())
    
    background_tasks.add_task(
        generate_export,
        export_id=export_id,
        format=request.format,
        filters=request.filters,
        include_adopted=request.include_adopted,
    )
    
    return {
        "export_id": export_id,
        "status": "processing",
        "download_url": f"/admin/export/{export_id}/download",
    }


async def generate_export(
    export_id: str,
    format: str,
    filters: dict,
    include_adopted: bool,
):
    """Generate export file in background."""
    pass


@router.get("/export/{export_id}/download")
def download_export(export_id: str):
    """
    Download an export file.
    """
    # Would return file response
    raise HTTPException(404, "Export not found")


# =============================================================================
# Shelter Management
# =============================================================================

@router.get("/shelters")
def list_shelters(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """
    List all shelters with admin details.
    """
    shelters = db.query(models.Shelter).offset(skip).limit(limit).all()
    
    result = []
    for shelter in shelters:
        animal_count = db.query(models.Animal).filter(
            models.Animal.shelter_id == shelter.id,
            models.Animal.is_adopted == False,
        ).count()
        
        result.append({
            "id": shelter.id,
            "name": shelter.name,
            "location": f"{shelter.city}, {shelter.state}" if shelter.city else "",
            "animal_count": animal_count,
            "created_at": shelter.created_at if hasattr(shelter, 'created_at') else None,
        })
    
    return result


@router.post("/shelters/{shelter_id}/sync")
async def sync_shelter(
    shelter_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Trigger sync for a specific shelter.
    """
    shelter = db.query(models.Shelter).filter(models.Shelter.id == shelter_id).first()
    if not shelter:
        raise HTTPException(404, "Shelter not found")
    
    background_tasks.add_task(run_ingestion, str(shelter_id), "rescuegroups", shelter_id, True)
    
    return {"status": "sync_queued", "shelter_id": shelter_id}


# =============================================================================
# Notifications
# =============================================================================

@router.post("/notifications/send")
async def send_notification(
    request: NotificationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Send notification to newsletter subscribers.
    """
    # Get subscribers
    subscribers = db.query(models.NewsletterSubscriber).filter(
        models.NewsletterSubscriber.is_active == True
    ).all()
    
    background_tasks.add_task(
        send_bulk_emails,
        subject=request.subject,
        message=request.message,
        recipients=[s.email for s in subscribers],
    )
    
    return {
        "status": "queued",
        "recipient_count": len(subscribers),
    }


async def send_bulk_emails(subject: str, message: str, recipients: list[str]):
    """Send emails in background."""
    pass


# =============================================================================
# System Health
# =============================================================================

@router.get("/health/detailed")
def detailed_health_check(db: Session = Depends(get_db)):
    """
    Get detailed system health information.
    """
    health = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {},
    }
    
    # Database
    try:
        db.execute("SELECT 1")
        health["components"]["database"] = {"status": "healthy"}
    except Exception as e:
        health["components"]["database"] = {"status": "unhealthy", "error": str(e)}
        health["status"] = "degraded"
    
    # Data freshness
    latest_animal = db.query(models.Animal).order_by(
        models.Animal.created_at.desc()
    ).first()
    
    if latest_animal:
        age_hours = (datetime.utcnow() - latest_animal.created_at).total_seconds() / 3600
        health["components"]["data_freshness"] = {
            "status": "healthy" if age_hours < 24 else "stale",
            "last_animal_added": latest_animal.created_at.isoformat(),
            "hours_since_update": round(age_hours, 1),
        }
    
    return health


@router.post("/cache/clear")
def clear_cache():
    """
    Clear all caches.
    """
    # Would clear Redis/memory cache
    return {"status": "cleared"}


@router.get("/logs")
def get_recent_logs(
    level: str = "INFO",
    limit: int = 100,
):
    """
    Get recent application logs.
    """
    # Would read from log storage
    return {"logs": [], "count": 0}

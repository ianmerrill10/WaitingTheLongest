"""
Waiting The Longest™ - Analytics Module
========================================
Track and analyze user engagement, animal views, and adoption metrics.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from collections import defaultdict
import json
import hashlib

from sqlalchemy.orm import Session
from sqlalchemy import func, text


@dataclass
class AnalyticsEvent:
    """Represents a single analytics event."""
    event_type: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    animal_id: Optional[int] = None
    shelter_id: Optional[int] = None
    user_session: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return {
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat(),
            "animal_id": self.animal_id,
            "shelter_id": self.shelter_id,
            "user_session": self.user_session,
            "metadata": self.metadata,
        }


class AnalyticsTracker:
    """
    Track analytics events for the application.
    
    Supports:
    - Page views
    - Animal detail views
    - Favorite actions
    - Share actions
    - Affiliate link clicks
    - Search queries
    """
    
    def __init__(self, db: Session):
        self.db = db
        self._buffer: List[AnalyticsEvent] = []
        self._buffer_size = 100  # Flush after N events
    
    def track(
        self,
        event_type: str,
        animal_id: Optional[int] = None,
        shelter_id: Optional[int] = None,
        user_session: Optional[str] = None,
        **metadata
    ) -> None:
        """Track an analytics event."""
        event = AnalyticsEvent(
            event_type=event_type,
            animal_id=animal_id,
            shelter_id=shelter_id,
            user_session=user_session,
            metadata=metadata,
        )
        self._buffer.append(event)
        
        if len(self._buffer) >= self._buffer_size:
            self.flush()
    
    def track_page_view(self, page: str, user_session: str) -> None:
        """Track a page view."""
        self.track("page_view", user_session=user_session, page=page)
    
    def track_animal_view(self, animal_id: int, user_session: str) -> None:
        """Track when a user views an animal's details."""
        self.track("animal_view", animal_id=animal_id, user_session=user_session)
    
    def track_favorite(self, animal_id: int, user_session: str, action: str = "add") -> None:
        """Track when a user favorites/unfavorites an animal."""
        self.track("favorite", animal_id=animal_id, user_session=user_session, action=action)
    
    def track_share(self, animal_id: int, platform: str, user_session: str) -> None:
        """Track when a user shares an animal."""
        self.track("share", animal_id=animal_id, user_session=user_session, platform=platform)
    
    def track_affiliate_click(self, animal_id: int, provider: str, product_id: str) -> None:
        """Track affiliate link clicks."""
        self.track("affiliate_click", animal_id=animal_id, provider=provider, product_id=product_id)
    
    def track_search(self, query: str, filters: Dict[str, Any], result_count: int) -> None:
        """Track search queries."""
        self.track("search", query=query, filters=filters, result_count=result_count)
    
    def track_adoption_inquiry(self, animal_id: int, shelter_id: int, user_session: str) -> None:
        """Track when a user clicks to adopt."""
        self.track(
            "adoption_inquiry",
            animal_id=animal_id,
            shelter_id=shelter_id,
            user_session=user_session
        )
    
    def flush(self) -> int:
        """Flush buffered events to storage."""
        if not self._buffer:
            return 0
        
        count = len(self._buffer)
        # In production, this would write to a database table or external service
        # For now, we'll just clear the buffer
        self._buffer.clear()
        return count


class AnalyticsReporter:
    """
    Generate analytics reports from tracked data.
    
    Provides insights into:
    - Most viewed animals
    - Popular shelters
    - Engagement trends
    - Adoption funnel metrics
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_dashboard_stats(self) -> Dict[str, Any]:
        """Get high-level dashboard statistics."""
        from app.models import Animal, Shelter, SuccessStory
        
        # Total counts
        total_animals = self.db.query(func.count(Animal.id)).scalar() or 0
        total_shelters = self.db.query(func.count(Shelter.id)).scalar() or 0
        total_success_stories = self.db.query(func.count(SuccessStory.id)).scalar() or 0
        
        # Species breakdown
        species_counts = (
            self.db.query(Animal.species, func.count(Animal.id))
            .group_by(Animal.species)
            .all()
        )
        
        # Long-term residents (waiting > 365 days)
        one_year_ago = datetime.utcnow() - timedelta(days=365)
        long_term_count = (
            self.db.query(func.count(Animal.id))
            .filter(Animal.intake_date <= one_year_ago)
            .scalar() or 0
        )
        
        return {
            "total_animals": total_animals,
            "total_shelters": total_shelters,
            "total_success_stories": total_success_stories,
            "long_term_residents": long_term_count,
            "species_breakdown": {species: count for species, count in species_counts},
            "generated_at": datetime.utcnow().isoformat(),
        }
    
    def get_longest_waiting(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get the animals waiting the longest."""
        from app.models import Animal
        
        animals = (
            self.db.query(Animal)
            .order_by(Animal.intake_date.asc())
            .limit(limit)
            .all()
        )
        
        result = []
        for animal in animals:
            days_waiting = (datetime.utcnow().date() - animal.intake_date).days
            result.append({
                "id": animal.id,
                "name": animal.name,
                "species": animal.species,
                "breed": animal.breed,
                "days_waiting": days_waiting,
                "intake_date": animal.intake_date.isoformat(),
            })
        
        return result
    
    def get_intake_trends(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get animal intake trends over time."""
        from app.models import Animal
        
        start_date = datetime.utcnow().date() - timedelta(days=days)
        
        # Query intakes by date
        intakes = (
            self.db.query(
                func.date(Animal.intake_date),
                func.count(Animal.id)
            )
            .filter(Animal.intake_date >= start_date)
            .group_by(func.date(Animal.intake_date))
            .order_by(func.date(Animal.intake_date))
            .all()
        )
        
        return [
            {"date": date.isoformat() if hasattr(date, 'isoformat') else str(date), "count": count}
            for date, count in intakes
        ]
    
    def get_shelter_stats(self) -> List[Dict[str, Any]]:
        """Get statistics per shelter."""
        from app.models import Animal, Shelter
        
        shelters = self.db.query(Shelter).all()
        
        result = []
        for shelter in shelters:
            animal_count = (
                self.db.query(func.count(Animal.id))
                .filter(Animal.shelter_id == shelter.id)
                .scalar() or 0
            )
            
            avg_wait = (
                self.db.query(func.avg(
                    func.julianday('now') - func.julianday(Animal.intake_date)
                ))
                .filter(Animal.shelter_id == shelter.id)
                .scalar() or 0
            )
            
            result.append({
                "shelter_id": shelter.id,
                "name": shelter.name,
                "city": shelter.city,
                "state": shelter.state,
                "animal_count": animal_count,
                "average_wait_days": round(float(avg_wait), 1),
            })
        
        return sorted(result, key=lambda x: x["animal_count"], reverse=True)
    
    def get_breed_popularity(self, species: str = "dog", limit: int = 20) -> List[Dict[str, Any]]:
        """Get most common breeds by species."""
        from app.models import Animal
        
        breeds = (
            self.db.query(Animal.breed, func.count(Animal.id))
            .filter(Animal.species.ilike(species))
            .group_by(Animal.breed)
            .order_by(func.count(Animal.id).desc())
            .limit(limit)
            .all()
        )
        
        return [
            {"breed": breed, "count": count}
            for breed, count in breeds
        ]
    
    def generate_weekly_report(self) -> Dict[str, Any]:
        """Generate a comprehensive weekly report."""
        return {
            "report_type": "weekly",
            "generated_at": datetime.utcnow().isoformat(),
            "dashboard": self.get_dashboard_stats(),
            "longest_waiting": self.get_longest_waiting(limit=10),
            "intake_trends": self.get_intake_trends(days=7),
            "shelter_stats": self.get_shelter_stats()[:10],
            "dog_breeds": self.get_breed_popularity("dog", 10),
            "cat_breeds": self.get_breed_popularity("cat", 10),
        }


def generate_session_id(ip: str, user_agent: str) -> str:
    """Generate a consistent session ID from request info (privacy-friendly)."""
    # Hash to anonymize
    data = f"{ip}:{user_agent}:{datetime.utcnow().date()}"
    return hashlib.sha256(data.encode()).hexdigest()[:16]

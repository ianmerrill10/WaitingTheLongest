"""
Waiting The Longest™ - Analytics
=================================
Analytics and statistics collection.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any
from collections import defaultdict
from enum import Enum
import json


# =============================================================================
# Analytics Events
# =============================================================================

class AnalyticsEvent(str, Enum):
    """Types of analytics events."""
    PAGE_VIEW = "page_view"
    ANIMAL_VIEW = "animal_view"
    ANIMAL_SHARE = "animal_share"
    SEARCH = "search"
    FILTER_APPLIED = "filter_applied"
    NEWSLETTER_SIGNUP = "newsletter_signup"
    CONTACT_SHELTER = "contact_shelter"
    ADOPTION_INQUIRY = "adoption_inquiry"
    FAVORITE_ADDED = "favorite_added"
    FAVORITE_REMOVED = "favorite_removed"
    DONATION_STARTED = "donation_started"
    DONATION_COMPLETED = "donation_completed"


@dataclass
class AnalyticsData:
    """Single analytics data point."""
    
    event: AnalyticsEvent
    timestamp: datetime = field(default_factory=datetime.utcnow)
    session_id: str | None = None
    user_id: str | None = None
    data: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "event": self.event.value,
            "timestamp": self.timestamp.isoformat(),
            "session_id": self.session_id,
            "user_id": self.user_id,
            "data": self.data,
        }


# =============================================================================
# Analytics Collector
# =============================================================================

class AnalyticsCollector:
    """
    Collects and stores analytics data.
    """
    
    def __init__(self, max_buffer_size: int = 1000):
        self.buffer: list[AnalyticsData] = []
        self.max_buffer_size = max_buffer_size
        self._listeners: list[callable] = []
    
    def track(
        self,
        event: AnalyticsEvent,
        data: dict[str, Any] | None = None,
        session_id: str | None = None,
        user_id: str | None = None,
    ):
        """Track an analytics event."""
        analytics_data = AnalyticsData(
            event=event,
            data=data or {},
            session_id=session_id,
            user_id=user_id,
        )
        
        self.buffer.append(analytics_data)
        
        # Notify listeners
        for listener in self._listeners:
            try:
                listener(analytics_data)
            except Exception:
                pass
        
        # Flush if buffer is full
        if len(self.buffer) >= self.max_buffer_size:
            self.flush()
    
    def add_listener(self, callback: callable):
        """Add event listener."""
        self._listeners.append(callback)
    
    def flush(self):
        """Flush buffer to storage."""
        if not self.buffer:
            return
        
        # In production, this would write to database/analytics service
        events = self.buffer.copy()
        self.buffer.clear()
        
        # Process events (placeholder)
        self._process_events(events)
    
    def _process_events(self, events: list[AnalyticsData]):
        """Process flushed events."""
        # This would store to database or send to analytics service
        pass


# =============================================================================
# Statistics Calculator
# =============================================================================

@dataclass
class AnimalStatistics:
    """Calculated animal statistics."""
    
    total_animals: int = 0
    total_dogs: int = 0
    total_cats: int = 0
    total_other: int = 0
    
    average_days_waiting: float = 0.0
    longest_waiting_days: int = 0
    
    adoptions_today: int = 0
    adoptions_this_week: int = 0
    adoptions_this_month: int = 0
    
    new_intakes_today: int = 0
    new_intakes_this_week: int = 0
    
    by_state: dict[str, int] = field(default_factory=dict)
    by_age: dict[str, int] = field(default_factory=dict)
    by_breed: dict[str, int] = field(default_factory=dict)
    
    calculated_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "total_animals": self.total_animals,
            "by_species": {
                "dogs": self.total_dogs,
                "cats": self.total_cats,
                "other": self.total_other,
            },
            "waiting": {
                "average_days": round(self.average_days_waiting, 1),
                "longest_days": self.longest_waiting_days,
            },
            "adoptions": {
                "today": self.adoptions_today,
                "this_week": self.adoptions_this_week,
                "this_month": self.adoptions_this_month,
            },
            "new_intakes": {
                "today": self.new_intakes_today,
                "this_week": self.new_intakes_this_week,
            },
            "by_state": self.by_state,
            "by_age": self.by_age,
            "calculated_at": self.calculated_at.isoformat(),
        }


class StatisticsCalculator:
    """
    Calculate various statistics from animal data.
    """
    
    def __init__(self, db_session=None):
        self.db = db_session
        self._cache: dict[str, Any] = {}
        self._cache_ttl = 300  # 5 minutes
    
    def calculate_all(self) -> AnimalStatistics:
        """Calculate all statistics."""
        stats = AnimalStatistics()
        
        if not self.db:
            return stats
        
        from backend.app import models
        from sqlalchemy import func
        
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=today_start.weekday())
        month_start = today_start.replace(day=1)
        
        # Total animals (not adopted)
        stats.total_animals = (
            self.db.query(func.count(models.Animal.id))
            .filter(models.Animal.is_adopted == False)
            .scalar()
        ) or 0
        
        # By species
        stats.total_dogs = (
            self.db.query(func.count(models.Animal.id))
            .filter(
                models.Animal.is_adopted == False,
                models.Animal.species.ilike("dog"),
            )
            .scalar()
        ) or 0
        
        stats.total_cats = (
            self.db.query(func.count(models.Animal.id))
            .filter(
                models.Animal.is_adopted == False,
                models.Animal.species.ilike("cat"),
            )
            .scalar()
        ) or 0
        
        stats.total_other = stats.total_animals - stats.total_dogs - stats.total_cats
        
        # Average days waiting
        avg_result = (
            self.db.query(
                func.avg(
                    func.julianday('now') - func.julianday(models.Animal.intake_date)
                )
            )
            .filter(models.Animal.is_adopted == False)
            .scalar()
        )
        stats.average_days_waiting = float(avg_result) if avg_result else 0.0
        
        # Longest waiting
        oldest = (
            self.db.query(models.Animal)
            .filter(models.Animal.is_adopted == False)
            .order_by(models.Animal.intake_date)
            .first()
        )
        if oldest and oldest.intake_date:
            stats.longest_waiting_days = (now.date() - oldest.intake_date.date()).days
        
        # Adoptions
        stats.adoptions_today = (
            self.db.query(func.count(models.Animal.id))
            .filter(
                models.Animal.is_adopted == True,
                models.Animal.updated_at >= today_start,
            )
            .scalar()
        ) or 0
        
        stats.adoptions_this_week = (
            self.db.query(func.count(models.Animal.id))
            .filter(
                models.Animal.is_adopted == True,
                models.Animal.updated_at >= week_start,
            )
            .scalar()
        ) or 0
        
        stats.adoptions_this_month = (
            self.db.query(func.count(models.Animal.id))
            .filter(
                models.Animal.is_adopted == True,
                models.Animal.updated_at >= month_start,
            )
            .scalar()
        ) or 0
        
        # New intakes
        stats.new_intakes_today = (
            self.db.query(func.count(models.Animal.id))
            .filter(models.Animal.intake_date >= today_start)
            .scalar()
        ) or 0
        
        stats.new_intakes_this_week = (
            self.db.query(func.count(models.Animal.id))
            .filter(models.Animal.intake_date >= week_start)
            .scalar()
        ) or 0
        
        # By state (through shelter)
        state_counts = (
            self.db.query(
                models.Shelter.state,
                func.count(models.Animal.id),
            )
            .join(models.Shelter)
            .filter(models.Animal.is_adopted == False)
            .group_by(models.Shelter.state)
            .all()
        )
        stats.by_state = {state: count for state, count in state_counts if state}
        
        # By age
        age_counts = (
            self.db.query(
                models.Animal.age,
                func.count(models.Animal.id),
            )
            .filter(models.Animal.is_adopted == False)
            .group_by(models.Animal.age)
            .all()
        )
        stats.by_age = {age: count for age, count in age_counts if age}
        
        return stats


# =============================================================================
# Dashboard Metrics
# =============================================================================

@dataclass
class DashboardMetrics:
    """Metrics for admin dashboard."""
    
    # Current state
    active_animals: int = 0
    active_shelters: int = 0
    newsletter_subscribers: int = 0
    
    # Trends
    animals_change_7d: int = 0
    adoptions_change_7d: int = 0
    
    # Performance
    avg_response_time_ms: float = 0.0
    error_rate: float = 0.0
    uptime_percent: float = 100.0
    
    # Engagement
    page_views_today: int = 0
    unique_visitors_today: int = 0
    searches_today: int = 0
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "state": {
                "active_animals": self.active_animals,
                "active_shelters": self.active_shelters,
                "newsletter_subscribers": self.newsletter_subscribers,
            },
            "trends": {
                "animals_change_7d": self.animals_change_7d,
                "adoptions_change_7d": self.adoptions_change_7d,
            },
            "performance": {
                "avg_response_time_ms": round(self.avg_response_time_ms, 2),
                "error_rate": round(self.error_rate * 100, 2),
                "uptime_percent": round(self.uptime_percent, 2),
            },
            "engagement": {
                "page_views_today": self.page_views_today,
                "unique_visitors_today": self.unique_visitors_today,
                "searches_today": self.searches_today,
            },
        }


# =============================================================================
# Trend Analysis
# =============================================================================

class TrendAnalyzer:
    """
    Analyze trends in animal data.
    """
    
    def __init__(self, db_session=None):
        self.db = db_session
    
    def get_waiting_time_trend(
        self,
        days: int = 30,
    ) -> list[dict[str, Any]]:
        """Get trend of average waiting time over time."""
        # This would calculate daily averages
        return []
    
    def get_species_distribution_trend(
        self,
        days: int = 30,
    ) -> dict[str, list[int]]:
        """Get trend of species distribution over time."""
        return {}
    
    def get_adoption_rate_trend(
        self,
        days: int = 30,
    ) -> list[dict[str, Any]]:
        """Get adoption rate trend."""
        return []
    
    def get_intake_trend(
        self,
        days: int = 30,
    ) -> list[dict[str, Any]]:
        """Get intake trend."""
        return []


# =============================================================================
# Global Analytics Instance
# =============================================================================

_analytics: AnalyticsCollector | None = None


def get_analytics() -> AnalyticsCollector:
    """Get the global analytics instance."""
    global _analytics
    if _analytics is None:
        _analytics = AnalyticsCollector()
    return _analytics


# =============================================================================
# Convenience Functions
# =============================================================================

def track_page_view(
    page: str,
    session_id: str | None = None,
    referrer: str | None = None,
):
    """Track a page view."""
    get_analytics().track(
        AnalyticsEvent.PAGE_VIEW,
        data={"page": page, "referrer": referrer},
        session_id=session_id,
    )


def track_animal_view(
    animal_id: int,
    session_id: str | None = None,
):
    """Track an animal profile view."""
    get_analytics().track(
        AnalyticsEvent.ANIMAL_VIEW,
        data={"animal_id": animal_id},
        session_id=session_id,
    )


def track_search(
    query: str,
    results_count: int,
    filters: dict | None = None,
    session_id: str | None = None,
):
    """Track a search."""
    get_analytics().track(
        AnalyticsEvent.SEARCH,
        data={
            "query": query,
            "results_count": results_count,
            "filters": filters or {},
        },
        session_id=session_id,
    )


def track_newsletter_signup(
    email_domain: str,  # Only domain, not full email
    source: str | None = None,
):
    """Track newsletter signup."""
    get_analytics().track(
        AnalyticsEvent.NEWSLETTER_SIGNUP,
        data={"email_domain": email_domain, "source": source},
    )

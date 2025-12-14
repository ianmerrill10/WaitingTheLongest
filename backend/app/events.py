"""
Waiting The Longest™ - Event Tracking
======================================
Track and emit application events for analytics.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict


logger = logging.getLogger(__name__)


class EventType(Enum):
    """Types of trackable events."""
    # Page views
    PAGE_VIEW = "page_view"
    
    # Animal interactions
    ANIMAL_VIEW = "animal_view"
    ANIMAL_SHARE = "animal_share"
    ANIMAL_FAVORITE = "animal_favorite"
    ANIMAL_UNFAVORITE = "animal_unfavorite"
    ANIMAL_CONTACT = "animal_contact"
    
    # Search interactions
    SEARCH = "search"
    FILTER_APPLIED = "filter_applied"
    
    # Newsletter
    NEWSLETTER_SUBSCRIBE = "newsletter_subscribe"
    NEWSLETTER_UNSUBSCRIBE = "newsletter_unsubscribe"
    
    # Affiliate
    AFFILIATE_CLICK = "affiliate_click"
    AFFILIATE_CONVERSION = "affiliate_conversion"
    
    # Shelter interactions
    SHELTER_VIEW = "shelter_view"
    SHELTER_CONTACT = "shelter_contact"
    
    # User actions
    DARK_MODE_TOGGLE = "dark_mode_toggle"
    
    # System events
    ADOPTION = "adoption"
    INGEST_COMPLETE = "ingest_complete"
    ERROR = "error"


@dataclass
class Event:
    """A tracked event."""
    type: EventType
    timestamp: datetime = field(default_factory=datetime.utcnow)
    data: Dict[str, Any] = field(default_factory=dict)
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return {
            "type": self.type.value,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
            "user_id": self.user_id,
            "session_id": self.session_id,
        }


class EventEmitter:
    """
    Event emitter for application-wide event tracking.
    
    Supports:
    - In-memory event buffer
    - Event listeners/handlers
    - Batched processing
    """
    
    def __init__(self, buffer_size: int = 1000):
        self.buffer_size = buffer_size
        self.events: List[Event] = []
        self.listeners: Dict[EventType, List[callable]] = defaultdict(list)
        self.global_listeners: List[callable] = []
    
    def emit(self, event: Event) -> None:
        """Emit an event."""
        # Add to buffer
        self.events.append(event)
        
        # Trim buffer if too large
        if len(self.events) > self.buffer_size:
            self.events = self.events[-self.buffer_size:]
        
        # Notify listeners
        for listener in self.listeners.get(event.type, []):
            try:
                listener(event)
            except Exception as e:
                logger.error(f"Event listener error: {e}")
        
        # Notify global listeners
        for listener in self.global_listeners:
            try:
                listener(event)
            except Exception as e:
                logger.error(f"Global event listener error: {e}")
    
    def on(self, event_type: EventType, listener: callable) -> None:
        """Register a listener for a specific event type."""
        self.listeners[event_type].append(listener)
    
    def on_all(self, listener: callable) -> None:
        """Register a listener for all events."""
        self.global_listeners.append(listener)
    
    def get_events(
        self,
        event_type: Optional[EventType] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Event]:
        """Get recent events, optionally filtered."""
        events = self.events
        
        if event_type:
            events = [e for e in events if e.type == event_type]
        
        if since:
            events = [e for e in events if e.timestamp >= since]
        
        return events[-limit:]
    
    def get_stats(self) -> Dict[str, int]:
        """Get event count statistics."""
        stats = defaultdict(int)
        for event in self.events:
            stats[event.type.value] += 1
        return dict(stats)
    
    def flush(self) -> List[Event]:
        """Flush and return all events."""
        events = self.events
        self.events = []
        return events


# =============================================================================
# Global Event Emitter
# =============================================================================

_event_emitter: Optional[EventEmitter] = None


def get_event_emitter() -> EventEmitter:
    """Get the global event emitter."""
    global _event_emitter
    
    if _event_emitter is None:
        _event_emitter = EventEmitter()
    
    return _event_emitter


# =============================================================================
# Convenience Functions
# =============================================================================

def track_page_view(
    path: str,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> None:
    """Track a page view."""
    event = Event(
        type=EventType.PAGE_VIEW,
        data={"path": path},
        user_id=user_id,
        session_id=session_id,
    )
    get_event_emitter().emit(event)


def track_animal_view(
    animal_id: int,
    animal_name: str,
    user_id: Optional[str] = None,
) -> None:
    """Track an animal profile view."""
    event = Event(
        type=EventType.ANIMAL_VIEW,
        data={"animal_id": animal_id, "animal_name": animal_name},
        user_id=user_id,
    )
    get_event_emitter().emit(event)


def track_animal_share(
    animal_id: int,
    platform: str,
    user_id: Optional[str] = None,
) -> None:
    """Track an animal being shared."""
    event = Event(
        type=EventType.ANIMAL_SHARE,
        data={"animal_id": animal_id, "platform": platform},
        user_id=user_id,
    )
    get_event_emitter().emit(event)


def track_search(
    query: str,
    filters: Dict[str, Any],
    result_count: int,
    user_id: Optional[str] = None,
) -> None:
    """Track a search."""
    event = Event(
        type=EventType.SEARCH,
        data={"query": query, "filters": filters, "result_count": result_count},
        user_id=user_id,
    )
    get_event_emitter().emit(event)


def track_newsletter_subscribe(email: str) -> None:
    """Track a newsletter subscription."""
    event = Event(
        type=EventType.NEWSLETTER_SUBSCRIBE,
        data={"email_domain": email.split("@")[-1] if "@" in email else "unknown"},
    )
    get_event_emitter().emit(event)


def track_affiliate_click(
    affiliate: str,
    product_type: str,
    animal_id: Optional[int] = None,
) -> None:
    """Track an affiliate link click."""
    event = Event(
        type=EventType.AFFILIATE_CLICK,
        data={
            "affiliate": affiliate,
            "product_type": product_type,
            "animal_id": animal_id,
        },
    )
    get_event_emitter().emit(event)


def track_adoption(
    animal_id: int,
    animal_name: str,
    days_waiting: int,
    shelter_id: int,
) -> None:
    """Track an adoption."""
    event = Event(
        type=EventType.ADOPTION,
        data={
            "animal_id": animal_id,
            "animal_name": animal_name,
            "days_waiting": days_waiting,
            "shelter_id": shelter_id,
        },
    )
    get_event_emitter().emit(event)


def track_error(
    error_type: str,
    message: str,
    context: Optional[Dict[str, Any]] = None,
) -> None:
    """Track an error."""
    event = Event(
        type=EventType.ERROR,
        data={
            "error_type": error_type,
            "message": message,
            "context": context or {},
        },
    )
    get_event_emitter().emit(event)

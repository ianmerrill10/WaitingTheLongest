"""
Waiting The Longest™ - Notifications System
=============================================
User notifications and alerts.
"""

from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
import json


# =============================================================================
# Notification Types
# =============================================================================

class NotificationType(str, Enum):
    """Types of notifications."""
    ANIMAL_MATCH = "animal_match"       # New animal matching preferences
    ADOPTION_ALERT = "adoption_alert"   # Favorite animal adopted
    MILESTONE = "milestone"             # Animal milestone (100 days, etc.)
    SHELTER_UPDATE = "shelter_update"   # Shelter news
    SYSTEM = "system"                   # System announcements
    NEWSLETTER = "newsletter"           # Newsletter published


class NotificationPriority(str, Enum):
    """Notification priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NotificationChannel(str, Enum):
    """Delivery channels for notifications."""
    IN_APP = "in_app"
    EMAIL = "email"
    PUSH = "push"
    SMS = "sms"


# =============================================================================
# Notification Data Structures
# =============================================================================

@dataclass
class Notification:
    """A single notification."""
    
    id: str
    user_id: str
    type: NotificationType
    title: str
    message: str
    priority: NotificationPriority = NotificationPriority.NORMAL
    data: dict = field(default_factory=dict)
    read: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    read_at: datetime | None = None
    expires_at: datetime | None = None
    
    def mark_read(self):
        """Mark notification as read."""
        self.read = True
        self.read_at = datetime.utcnow()
    
    def is_expired(self) -> bool:
        """Check if notification has expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "type": self.type.value,
            "title": self.title,
            "message": self.message,
            "priority": self.priority.value,
            "data": self.data,
            "read": self.read,
            "created_at": self.created_at.isoformat(),
            "read_at": self.read_at.isoformat() if self.read_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Notification":
        return cls(
            id=data["id"],
            user_id=data["user_id"],
            type=NotificationType(data["type"]),
            title=data["title"],
            message=data["message"],
            priority=NotificationPriority(data.get("priority", "normal")),
            data=data.get("data", {}),
            read=data.get("read", False),
            created_at=datetime.fromisoformat(data["created_at"]) if isinstance(data["created_at"], str) else data["created_at"],
            read_at=datetime.fromisoformat(data["read_at"]) if data.get("read_at") else None,
            expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
        )


@dataclass
class NotificationPreferences:
    """User's notification preferences."""
    
    user_id: str
    email_enabled: bool = True
    push_enabled: bool = False
    sms_enabled: bool = False
    
    # Frequency settings
    digest_enabled: bool = True
    digest_frequency: str = "daily"  # daily, weekly
    
    # Type preferences
    enabled_types: list[NotificationType] = field(default_factory=lambda: list(NotificationType))
    
    # Quiet hours
    quiet_hours_enabled: bool = False
    quiet_start: int = 22  # 10 PM
    quiet_end: int = 8     # 8 AM
    
    def is_type_enabled(self, notification_type: NotificationType) -> bool:
        """Check if a notification type is enabled."""
        return notification_type in self.enabled_types
    
    def is_channel_enabled(self, channel: NotificationChannel) -> bool:
        """Check if a notification channel is enabled."""
        if channel == NotificationChannel.EMAIL:
            return self.email_enabled
        elif channel == NotificationChannel.PUSH:
            return self.push_enabled
        elif channel == NotificationChannel.SMS:
            return self.sms_enabled
        elif channel == NotificationChannel.IN_APP:
            return True  # Always enabled
        return False
    
    def is_quiet_hours(self) -> bool:
        """Check if it's currently quiet hours."""
        if not self.quiet_hours_enabled:
            return False
        
        current_hour = datetime.utcnow().hour
        if self.quiet_start < self.quiet_end:
            return self.quiet_start <= current_hour < self.quiet_end
        else:
            # Spans midnight
            return current_hour >= self.quiet_start or current_hour < self.quiet_end
    
    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "email_enabled": self.email_enabled,
            "push_enabled": self.push_enabled,
            "sms_enabled": self.sms_enabled,
            "digest_enabled": self.digest_enabled,
            "digest_frequency": self.digest_frequency,
            "enabled_types": [t.value for t in self.enabled_types],
            "quiet_hours_enabled": self.quiet_hours_enabled,
            "quiet_start": self.quiet_start,
            "quiet_end": self.quiet_end,
        }


# =============================================================================
# Notification Service
# =============================================================================

class NotificationService:
    """
    Service for managing and delivering notifications.
    """
    
    def __init__(
        self,
        storage: Any = None,
        email_service: Any = None,
        push_service: Any = None,
    ):
        self.storage = storage or InMemoryNotificationStorage()
        self.email_service = email_service
        self.push_service = push_service
        self._handlers: dict[NotificationType, list] = {}
    
    def on(self, notification_type: NotificationType, handler):
        """Register a handler for a notification type."""
        if notification_type not in self._handlers:
            self._handlers[notification_type] = []
        self._handlers[notification_type].append(handler)
    
    async def send(
        self,
        user_id: str,
        notification_type: NotificationType,
        title: str,
        message: str,
        data: dict | None = None,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        channels: list[NotificationChannel] | None = None,
    ) -> Notification:
        """
        Send a notification to a user.
        
        Args:
            user_id: Target user ID
            notification_type: Type of notification
            title: Notification title
            message: Notification message
            data: Additional data payload
            priority: Notification priority
            channels: Specific channels to use (overrides preferences)
        """
        import uuid
        
        # Create notification
        notification = Notification(
            id=str(uuid.uuid4()),
            user_id=user_id,
            type=notification_type,
            title=title,
            message=message,
            priority=priority,
            data=data or {},
        )
        
        # Store notification
        await self.storage.save(notification)
        
        # Get user preferences
        preferences = await self.storage.get_preferences(user_id)
        
        # Check if type is enabled
        if not preferences.is_type_enabled(notification_type):
            return notification
        
        # Check quiet hours for non-urgent notifications
        if priority != NotificationPriority.URGENT and preferences.is_quiet_hours():
            # Queue for later delivery
            return notification
        
        # Determine channels
        if channels is None:
            channels = [NotificationChannel.IN_APP]
            if preferences.email_enabled:
                channels.append(NotificationChannel.EMAIL)
            if preferences.push_enabled:
                channels.append(NotificationChannel.PUSH)
        
        # Deliver to channels
        for channel in channels:
            if preferences.is_channel_enabled(channel):
                await self._deliver(notification, channel)
        
        # Call handlers
        if notification_type in self._handlers:
            for handler in self._handlers[notification_type]:
                try:
                    await handler(notification)
                except Exception as e:
                    # Log error but don't fail
                    pass
        
        return notification
    
    async def _deliver(
        self,
        notification: Notification,
        channel: NotificationChannel,
    ):
        """Deliver notification to a specific channel."""
        if channel == NotificationChannel.EMAIL:
            if self.email_service:
                await self.email_service.send_notification(notification)
        
        elif channel == NotificationChannel.PUSH:
            if self.push_service:
                await self.push_service.send(
                    user_id=notification.user_id,
                    title=notification.title,
                    body=notification.message,
                    data=notification.data,
                )
        
        # IN_APP is handled by storage
    
    async def get_notifications(
        self,
        user_id: str,
        unread_only: bool = False,
        limit: int = 50,
    ) -> list[Notification]:
        """Get notifications for a user."""
        return await self.storage.get_user_notifications(
            user_id,
            unread_only=unread_only,
            limit=limit,
        )
    
    async def mark_read(self, notification_id: str) -> bool:
        """Mark a notification as read."""
        notification = await self.storage.get(notification_id)
        if notification:
            notification.mark_read()
            await self.storage.save(notification)
            return True
        return False
    
    async def mark_all_read(self, user_id: str) -> int:
        """Mark all user notifications as read."""
        notifications = await self.get_notifications(user_id, unread_only=True)
        for notification in notifications:
            notification.mark_read()
            await self.storage.save(notification)
        return len(notifications)
    
    async def get_unread_count(self, user_id: str) -> int:
        """Get count of unread notifications."""
        return await self.storage.get_unread_count(user_id)


# =============================================================================
# Notification Storage
# =============================================================================

class InMemoryNotificationStorage:
    """In-memory storage for development/testing."""
    
    def __init__(self):
        self._notifications: dict[str, Notification] = {}
        self._preferences: dict[str, NotificationPreferences] = {}
    
    async def save(self, notification: Notification):
        self._notifications[notification.id] = notification
    
    async def get(self, notification_id: str) -> Notification | None:
        return self._notifications.get(notification_id)
    
    async def get_user_notifications(
        self,
        user_id: str,
        unread_only: bool = False,
        limit: int = 50,
    ) -> list[Notification]:
        notifications = [
            n for n in self._notifications.values()
            if n.user_id == user_id and not n.is_expired()
        ]
        
        if unread_only:
            notifications = [n for n in notifications if not n.read]
        
        # Sort by created_at desc
        notifications.sort(key=lambda n: n.created_at, reverse=True)
        
        return notifications[:limit]
    
    async def get_unread_count(self, user_id: str) -> int:
        return len([
            n for n in self._notifications.values()
            if n.user_id == user_id and not n.read and not n.is_expired()
        ])
    
    async def get_preferences(self, user_id: str) -> NotificationPreferences:
        if user_id not in self._preferences:
            self._preferences[user_id] = NotificationPreferences(user_id=user_id)
        return self._preferences[user_id]
    
    async def save_preferences(self, preferences: NotificationPreferences):
        self._preferences[preferences.user_id] = preferences


# =============================================================================
# Notification Templates
# =============================================================================

def create_animal_match_notification(
    user_id: str,
    animal_name: str,
    animal_id: int,
    species: str,
) -> dict:
    """Create an animal match notification."""
    return {
        "user_id": user_id,
        "notification_type": NotificationType.ANIMAL_MATCH,
        "title": f"New {species.title()} Match!",
        "message": f"{animal_name} matches your preferences and is waiting for adoption.",
        "data": {"animal_id": animal_id, "animal_name": animal_name},
        "priority": NotificationPriority.NORMAL,
    }


def create_milestone_notification(
    user_id: str,
    animal_name: str,
    animal_id: int,
    days_waiting: int,
) -> dict:
    """Create a milestone notification."""
    return {
        "user_id": user_id,
        "notification_type": NotificationType.MILESTONE,
        "title": f"{animal_name} Milestone",
        "message": f"{animal_name} has been waiting {days_waiting} days. Please help spread the word!",
        "data": {"animal_id": animal_id, "days_waiting": days_waiting},
        "priority": NotificationPriority.HIGH,
    }


def create_adoption_alert(
    user_id: str,
    animal_name: str,
    animal_id: int,
) -> dict:
    """Create an adoption alert for a favorited animal."""
    return {
        "user_id": user_id,
        "notification_type": NotificationType.ADOPTION_ALERT,
        "title": f"🎉 {animal_name} Got Adopted!",
        "message": f"Great news! {animal_name} has found their forever home!",
        "data": {"animal_id": animal_id, "animal_name": animal_name},
        "priority": NotificationPriority.HIGH,
    }


# =============================================================================
# Global Instance
# =============================================================================

_notification_service: NotificationService | None = None


def get_notification_service() -> NotificationService:
    """Get the global notification service."""
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService()
    return _notification_service

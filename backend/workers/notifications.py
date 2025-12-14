"""
Waiting The Longest™ - Notification Service
============================================
Send notifications via email, SMS, and push.
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class NotificationType(Enum):
    """Types of notifications."""
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    WEBHOOK = "webhook"


class NotificationPriority(Enum):
    """Priority levels for notifications."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class Notification:
    """Represents a notification to be sent."""
    type: NotificationType
    recipient: str
    subject: str
    body: str
    priority: NotificationPriority = NotificationPriority.NORMAL
    metadata: Dict[str, Any] = field(default_factory=dict)
    template_id: Optional[str] = None
    template_data: Dict[str, Any] = field(default_factory=dict)
    scheduled_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class NotificationResult:
    """Result of sending a notification."""
    success: bool
    notification_id: Optional[str] = None
    error: Optional[str] = None
    sent_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class NotificationChannel(ABC):
    """Base class for notification channels."""
    
    @abstractmethod
    async def send(self, notification: Notification) -> NotificationResult:
        """Send a notification through this channel."""
        pass
    
    @abstractmethod
    def validate_recipient(self, recipient: str) -> bool:
        """Validate the recipient format for this channel."""
        pass


class EmailChannel(NotificationChannel):
    """Email notification channel."""
    
    def __init__(
        self,
        smtp_host: Optional[str] = None,
        smtp_port: int = 587,
        smtp_user: Optional[str] = None,
        smtp_password: Optional[str] = None,
        from_email: str = "noreply@waitingthelongest.com",
        from_name: str = "Waiting The Longest",
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.from_email = from_email
        self.from_name = from_name
        self._configured = bool(smtp_host and smtp_user)
    
    def validate_recipient(self, recipient: str) -> bool:
        """Validate email address format."""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, recipient))
    
    async def send(self, notification: Notification) -> NotificationResult:
        """Send an email notification."""
        if not self._configured:
            logger.warning("Email channel not configured, skipping send")
            return NotificationResult(
                success=False,
                error="Email channel not configured",
            )
        
        if not self.validate_recipient(notification.recipient):
            return NotificationResult(
                success=False,
                error=f"Invalid email address: {notification.recipient}",
            )
        
        try:
            # In production, use aiosmtplib or similar
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            msg = MIMEMultipart("alternative")
            msg["Subject"] = notification.subject
            msg["From"] = f"{self.from_name} <{self.from_email}>"
            msg["To"] = notification.recipient
            
            # Add plain text version
            text_part = MIMEText(notification.body, "plain")
            msg.attach(text_part)
            
            # Add HTML version if body contains HTML
            if "<html" in notification.body.lower() or "<p>" in notification.body:
                html_part = MIMEText(notification.body, "html")
                msg.attach(html_part)
            
            # Send (blocking - in production use async)
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"Email sent to {notification.recipient}")
            return NotificationResult(
                success=True,
                sent_at=datetime.utcnow(),
            )
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return NotificationResult(
                success=False,
                error=str(e),
            )


class WebhookChannel(NotificationChannel):
    """Webhook notification channel for integrations."""
    
    def validate_recipient(self, recipient: str) -> bool:
        """Validate webhook URL."""
        from urllib.parse import urlparse
        try:
            result = urlparse(recipient)
            return all([result.scheme in ("http", "https"), result.netloc])
        except Exception:
            return False
    
    async def send(self, notification: Notification) -> NotificationResult:
        """Send a webhook notification."""
        if not self.validate_recipient(notification.recipient):
            return NotificationResult(
                success=False,
                error=f"Invalid webhook URL: {notification.recipient}",
            )
        
        try:
            import httpx
            
            payload = {
                "subject": notification.subject,
                "body": notification.body,
                "priority": notification.priority.value,
                "timestamp": notification.created_at.isoformat(),
                **notification.metadata,
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    notification.recipient,
                    json=payload,
                    timeout=10.0,
                )
                response.raise_for_status()
            
            return NotificationResult(
                success=True,
                sent_at=datetime.utcnow(),
                metadata={"status_code": response.status_code},
            )
            
        except Exception as e:
            logger.error(f"Failed to send webhook: {e}")
            return NotificationResult(
                success=False,
                error=str(e),
            )


class NotificationService:
    """
    Main notification service.
    
    Handles sending notifications through various channels
    and managing notification preferences.
    """
    
    def __init__(self):
        self.channels: Dict[NotificationType, NotificationChannel] = {}
        self._queue: List[Notification] = []
    
    def register_channel(
        self,
        channel_type: NotificationType,
        channel: NotificationChannel,
    ) -> None:
        """Register a notification channel."""
        self.channels[channel_type] = channel
        logger.info(f"Registered notification channel: {channel_type.value}")
    
    async def send(self, notification: Notification) -> NotificationResult:
        """Send a notification."""
        channel = self.channels.get(notification.type)
        
        if not channel:
            return NotificationResult(
                success=False,
                error=f"No channel registered for type: {notification.type.value}",
            )
        
        return await channel.send(notification)
    
    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        **kwargs,
    ) -> NotificationResult:
        """Convenience method for sending emails."""
        notification = Notification(
            type=NotificationType.EMAIL,
            recipient=to,
            subject=subject,
            body=body,
            priority=priority,
            metadata=kwargs,
        )
        return await self.send(notification)
    
    async def send_adoption_notification(
        self,
        adopter_email: str,
        animal_name: str,
        shelter_name: str,
    ) -> NotificationResult:
        """Send notification when someone expresses adoption interest."""
        subject = f"Thank you for your interest in adopting {animal_name}!"
        body = f"""
        <html>
        <body>
            <h2>Thank you for considering {animal_name}!</h2>
            <p>We're thrilled that you're interested in giving {animal_name} a forever home.</p>
            <p>The team at <strong>{shelter_name}</strong> will be in touch with you soon 
            to discuss the next steps in the adoption process.</p>
            <p>In the meantime, here are some tips to prepare:</p>
            <ul>
                <li>Gather any required documentation (ID, proof of residence, etc.)</li>
                <li>Prepare your home for a new pet</li>
                <li>Research the breed's needs and characteristics</li>
            </ul>
            <p>Thank you for choosing to adopt! 💜</p>
            <p>- The Waiting The Longest Team</p>
        </body>
        </html>
        """
        
        return await self.send_email(
            to=adopter_email,
            subject=subject,
            body=body,
            animal_name=animal_name,
            shelter_name=shelter_name,
        )
    
    async def send_newsletter_welcome(
        self,
        subscriber_email: str,
        name: Optional[str] = None,
    ) -> NotificationResult:
        """Send welcome email to new newsletter subscribers."""
        greeting = f"Hi {name}," if name else "Hello,"
        
        subject = "Welcome to Waiting The Longest! 🐾"
        body = f"""
        <html>
        <body>
            <h2>Welcome to Waiting The Longest!</h2>
            <p>{greeting}</p>
            <p>Thank you for subscribing to our newsletter! You'll now receive 
            updates about long-term shelter animals waiting for their forever homes.</p>
            <p>What to expect:</p>
            <ul>
                <li>Featured animals who have been waiting the longest</li>
                <li>Heartwarming adoption success stories</li>
                <li>Tips for pet care and adoption</li>
                <li>Updates from partner shelters</li>
            </ul>
            <p>Together, we can help every shelter animal find their perfect match! 💜</p>
            <p>- The Waiting The Longest Team</p>
        </body>
        </html>
        """
        
        return await self.send_email(
            to=subscriber_email,
            subject=subject,
            body=body,
        )


# ============================================================================
# Default Setup
# ============================================================================

def create_notification_service(
    smtp_host: Optional[str] = None,
    smtp_port: int = 587,
    smtp_user: Optional[str] = None,
    smtp_password: Optional[str] = None,
) -> NotificationService:
    """Create and configure notification service."""
    service = NotificationService()
    
    # Register email channel
    email_channel = EmailChannel(
        smtp_host=smtp_host,
        smtp_port=smtp_port,
        smtp_user=smtp_user,
        smtp_password=smtp_password,
    )
    service.register_channel(NotificationType.EMAIL, email_channel)
    
    # Register webhook channel
    webhook_channel = WebhookChannel()
    service.register_channel(NotificationType.WEBHOOK, webhook_channel)
    
    return service

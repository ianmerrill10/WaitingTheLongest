"""
===============================================================================
Waiting The Longest™ - Email Marketing Service
===============================================================================
Purpose: Email marketing automation service with sequence management, scheduling,
         and subscriber handling. Supports SendGrid, Mailgun, and Amazon SES.

Author: Waiting The Longest™ Development Team
Last Updated: 2025-01-15
Dependencies: sqlalchemy, pydantic

IMPORTANT: Any changes to this file MUST be documented in OWNERS_MANUAL.md

Email Sequences:
1. Welcome (5 emails over 14 days)
2. Abandoned cart (3 emails over 7 hours)
3. Weekly newsletter (Sundays at 10:00 AM)
4. Still waiting reminders (3, 7, 14 days)
5. Adoption follow-up sequence

"Because Every Day Matters" - Every email should inspire action!
===============================================================================
"""

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone
import secrets
import hashlib
import logging

from .models import (
    EmailSubscriber, EmailSequence, ScheduledEmail, PriceAlert, Animal
)
from .schemas import (
    EmailSubscriberCreate, EmailSubscriberUpdate, EmailPreferencesUpdate,
    PriceAlertCreate
)
from .config import settings

logger = logging.getLogger(__name__)


# =============================================================================
# Email Sequence Definitions
# =============================================================================

EMAIL_SEQUENCES = {
    "welcome": {
        "total_steps": 5,
        "spacing_days": [0, 1, 3, 7, 14],
        "emails": [
            {"type": "welcome_1", "subject": "Welcome to Waiting The Longest™! 🐾"},
            {"type": "welcome_2", "subject": "Take our style quiz - find your perfect match!"},
            {"type": "welcome_3", "subject": "Meet our top picks just for you"},
            {"type": "welcome_4", "subject": "Share the love - refer a friend!"},
            {"type": "welcome_5", "subject": "Unlock exclusive features with Pro"},
        ]
    },
    "abandoned_cart": {
        "total_steps": 3,
        "spacing_hours": [1, 3, 7],
        "emails": [
            {"type": "cart_reminder", "subject": "Did you forget something? 🐕"},
            {"type": "cart_price_drop", "subject": "Great news! Price dropped on your items"},
            {"type": "cart_last_chance", "subject": "Last chance - special discount inside!"},
        ]
    },
    "still_waiting": {
        "total_steps": 3,
        "spacing_days": [3, 7, 14],
        "emails": [
            {"type": "still_waiting_1", "subject": "{animal_name} is still waiting... 💔"},
            {"type": "still_waiting_2", "subject": "{animal_name} has been waiting {days} days"},
            {"type": "still_waiting_3", "subject": "Update on {animal_name} - still looking for a home"},
        ]
    },
    "adoption_followup": {
        "total_steps": 4,
        "spacing_days": [0, 7, 30, 90],
        "emails": [
            {"type": "adoption_congrats", "subject": "Congratulations on your new family member! 🎉"},
            {"type": "adoption_checkin_1", "subject": "How's your first week going?"},
            {"type": "adoption_checkin_2", "subject": "One month check-in - tips for your pet"},
            {"type": "adoption_story", "subject": "We'd love to hear your story!"},
        ]
    }
}


# =============================================================================
# Email Marketing Service
# =============================================================================

class EmailMarketingService:
    """
    Comprehensive email marketing service.

    Handles subscriber management, email sequences, scheduling, and tracking.
    Designed for CAN-SPAM and GDPR compliance.
    """

    @staticmethod
    def generate_verification_token() -> str:
        """Generate a secure verification token"""
        return secrets.token_urlsafe(32)

    @staticmethod
    def generate_unsubscribe_token(email: str) -> str:
        """Generate unsubscribe token from email"""
        secret = settings.SECRET_KEY
        return hashlib.sha256(f"{email}{secret}".encode()).hexdigest()[:32]

    # =========================================================================
    # Subscriber Management
    # =========================================================================

    @classmethod
    def subscribe(
        cls,
        db: Session,
        subscriber_data: EmailSubscriberCreate
    ) -> EmailSubscriber:
        """
        Subscribe a new email address.

        Creates subscriber record and starts welcome sequence.
        """
        # Check if already subscribed
        existing = db.query(EmailSubscriber).filter(
            EmailSubscriber.email == subscriber_data.email.lower()
        ).first()

        if existing:
            if existing.is_active:
                return existing
            # Reactivate if previously unsubscribed
            existing.is_active = True
            existing.unsubscribe_date = None
            existing.consent_given = True
            existing.consent_date = datetime.now(timezone.utc).replace(tzinfo=None)
            db.commit()
            db.refresh(existing)
            return existing

        # Create new subscriber
        subscriber = EmailSubscriber(
            email=subscriber_data.email.lower(),
            first_name=subscriber_data.first_name,
            last_name=subscriber_data.last_name,
            preferred_species=subscriber_data.preferred_species,
            preferred_location=subscriber_data.preferred_location,
            preferred_age_group=subscriber_data.preferred_age_group,
            newsletter_enabled=subscriber_data.newsletter_enabled,
            product_updates_enabled=subscriber_data.product_updates_enabled,
            adoption_alerts_enabled=subscriber_data.adoption_alerts_enabled,
            affiliate_emails_enabled=subscriber_data.affiliate_emails_enabled,
            consent_given=True,
            consent_date=datetime.now(timezone.utc).replace(tzinfo=None),
            consent_source=subscriber_data.consent_source or "website",
            verification_token=cls.generate_verification_token(),
            is_verified=False,
            is_active=True,
        )

        db.add(subscriber)
        db.commit()
        db.refresh(subscriber)

        # Start welcome sequence
        cls.start_sequence(db, subscriber.id, "welcome")

        return subscriber

    @classmethod
    def unsubscribe(
        cls,
        db: Session,
        email: str,
        token: Optional[str] = None
    ) -> bool:
        """
        Unsubscribe an email address.

        CAN-SPAM requires honoring unsubscribes within 10 days.
        We honor them immediately.
        """
        subscriber = db.query(EmailSubscriber).filter(
            EmailSubscriber.email == email.lower()
        ).first()

        if not subscriber:
            return False

        # Verify token if provided
        if token and token != cls.generate_unsubscribe_token(email):
            return False

        subscriber.is_active = False
        subscriber.unsubscribe_date = datetime.now(timezone.utc).replace(tzinfo=None)

        # Cancel any active sequences
        db.query(EmailSequence).filter(
            EmailSequence.subscriber_id == subscriber.id,
            EmailSequence.status == "active"
        ).update({"status": "cancelled"})

        # Cancel pending emails
        db.query(ScheduledEmail).filter(
            ScheduledEmail.subscriber_id == subscriber.id,
            ScheduledEmail.status == "pending"
        ).update({"status": "cancelled"})

        db.commit()
        return True

    @classmethod
    def verify_email(
        cls,
        db: Session,
        email: str,
        token: str
    ) -> bool:
        """Verify subscriber email address"""
        subscriber = db.query(EmailSubscriber).filter(
            EmailSubscriber.email == email.lower(),
            EmailSubscriber.verification_token == token
        ).first()

        if not subscriber:
            return False

        subscriber.is_verified = True
        subscriber.verification_token = None
        db.commit()
        return True

    @classmethod
    def update_preferences(
        cls,
        db: Session,
        subscriber_id: int,
        preferences: EmailPreferencesUpdate
    ) -> Optional[EmailSubscriber]:
        """Update subscriber email preferences"""
        subscriber = db.query(EmailSubscriber).filter(
            EmailSubscriber.id == subscriber_id
        ).first()

        if not subscriber:
            return None

        if preferences.newsletter_enabled is not None:
            subscriber.newsletter_enabled = preferences.newsletter_enabled
        if preferences.product_updates_enabled is not None:
            subscriber.product_updates_enabled = preferences.product_updates_enabled
        if preferences.adoption_alerts_enabled is not None:
            subscriber.adoption_alerts_enabled = preferences.adoption_alerts_enabled
        if preferences.affiliate_emails_enabled is not None:
            subscriber.affiliate_emails_enabled = preferences.affiliate_emails_enabled

        subscriber.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.commit()
        db.refresh(subscriber)
        return subscriber

    @classmethod
    def get_subscriber_by_email(
        cls,
        db: Session,
        email: str
    ) -> Optional[EmailSubscriber]:
        """Get subscriber by email address"""
        return db.query(EmailSubscriber).filter(
            EmailSubscriber.email == email.lower()
        ).first()

    # =========================================================================
    # Email Sequence Management
    # =========================================================================

    @classmethod
    def start_sequence(
        cls,
        db: Session,
        subscriber_id: int,
        sequence_type: str,
        context_data: Optional[Dict[str, Any]] = None
    ) -> Optional[EmailSequence]:
        """
        Start an email sequence for a subscriber.

        Creates the sequence record and schedules the first email.
        """
        if sequence_type not in EMAIL_SEQUENCES:
            logger.warning(f"Unknown sequence type: {sequence_type}")
            return None

        sequence_config = EMAIL_SEQUENCES[sequence_type]

        # Check if already in this sequence
        existing = db.query(EmailSequence).filter(
            EmailSequence.subscriber_id == subscriber_id,
            EmailSequence.sequence_type == sequence_type,
            EmailSequence.status == "active"
        ).first()

        if existing:
            return existing

        # Create sequence
        sequence = EmailSequence(
            subscriber_id=subscriber_id,
            sequence_type=sequence_type,
            current_step=0,
            total_steps=sequence_config["total_steps"],
            status="active",
            context_data=context_data,
            started_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )

        db.add(sequence)
        db.commit()
        db.refresh(sequence)

        # Schedule first email
        cls.schedule_next_sequence_email(db, sequence)

        return sequence

    @classmethod
    def schedule_next_sequence_email(
        cls,
        db: Session,
        sequence: EmailSequence
    ) -> Optional[ScheduledEmail]:
        """Schedule the next email in a sequence"""
        if sequence.current_step >= sequence.total_steps:
            sequence.status = "completed"
            sequence.is_completed = True
            sequence.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
            db.commit()
            return None

        sequence_config = EMAIL_SEQUENCES.get(sequence.sequence_type)
        if not sequence_config:
            return None

        email_config = sequence_config["emails"][sequence.current_step]

        # Calculate send time
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        if "spacing_days" in sequence_config:
            delay = timedelta(days=sequence_config["spacing_days"][sequence.current_step])
        else:
            delay = timedelta(hours=sequence_config["spacing_hours"][sequence.current_step])

        scheduled_at = now + delay

        # Get subscriber
        subscriber = db.query(EmailSubscriber).filter(
            EmailSubscriber.id == sequence.subscriber_id
        ).first()

        if not subscriber:
            return None

        # Personalize subject
        subject = email_config["subject"]
        if sequence.context_data:
            for key, value in sequence.context_data.items():
                subject = subject.replace(f"{{{key}}}", str(value))

        # Create scheduled email
        scheduled = ScheduledEmail(
            subscriber_id=sequence.subscriber_id,
            sequence_id=sequence.id,
            email_type=email_config["type"],
            subject=subject,
            template_name=email_config["type"],
            template_data=sequence.context_data,
            scheduled_at=scheduled_at,
            status="pending",
        )

        db.add(scheduled)

        # Update sequence
        sequence.next_email_at = scheduled_at

        db.commit()
        db.refresh(scheduled)

        return scheduled

    @classmethod
    def advance_sequence(
        cls,
        db: Session,
        sequence_id: int
    ) -> bool:
        """Advance sequence to next step after email is sent"""
        sequence = db.query(EmailSequence).filter(
            EmailSequence.id == sequence_id
        ).first()

        if not sequence or sequence.status != "active":
            return False

        sequence.current_step += 1
        sequence.last_email_sent_at = datetime.now(timezone.utc).replace(tzinfo=None)

        if sequence.current_step >= sequence.total_steps:
            sequence.status = "completed"
            sequence.is_completed = True
            sequence.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        else:
            # Schedule next email
            cls.schedule_next_sequence_email(db, sequence)

        db.commit()
        return True

    # =========================================================================
    # Price Alerts
    # =========================================================================

    @classmethod
    def create_price_alert(
        cls,
        db: Session,
        subscriber_id: int,
        alert_data: PriceAlertCreate
    ) -> PriceAlert:
        """Create a price or availability alert"""
        alert = PriceAlert(
            subscriber_id=subscriber_id,
            alert_type=alert_data.alert_type,
            target_type=alert_data.target_type,
            target_id=alert_data.target_id,
            target_name=alert_data.target_name,
            target_price=alert_data.target_price,
            is_active=True,
            expires_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=90),
        )

        db.add(alert)
        db.commit()
        db.refresh(alert)
        return alert

    @classmethod
    def get_active_alerts(
        cls,
        db: Session,
        subscriber_id: int
    ) -> List[PriceAlert]:
        """Get all active alerts for a subscriber"""
        return db.query(PriceAlert).filter(
            PriceAlert.subscriber_id == subscriber_id,
            PriceAlert.is_active == True
        ).all()

    @classmethod
    def deactivate_alert(
        cls,
        db: Session,
        alert_id: int,
        subscriber_id: int
    ) -> bool:
        """Deactivate a price alert"""
        alert = db.query(PriceAlert).filter(
            PriceAlert.id == alert_id,
            PriceAlert.subscriber_id == subscriber_id
        ).first()

        if not alert:
            return False

        alert.is_active = False
        db.commit()
        return True

    @classmethod
    def check_price_alerts(
        cls,
        db: Session,
        product_id: str,
        current_price: float
    ) -> List[PriceAlert]:
        """Check if any alerts should be triggered for a product price drop"""
        triggered = []
        alerts = db.query(PriceAlert).filter(
            PriceAlert.target_type == "product",
            PriceAlert.target_id == product_id,
            PriceAlert.is_active == True,
            PriceAlert.is_triggered == False
        ).all()

        for alert in alerts:
            if alert.target_price and current_price <= alert.target_price:
                alert.is_triggered = True
                alert.triggered_at = datetime.now(timezone.utc).replace(tzinfo=None)
                alert.current_price = current_price
                triggered.append(alert)

        if triggered:
            db.commit()

        return triggered

    # =========================================================================
    # Newsletter & Scheduled Email Management
    # =========================================================================

    @classmethod
    def get_pending_emails(
        cls,
        db: Session,
        limit: int = 100
    ) -> List[ScheduledEmail]:
        """Get emails ready to be sent"""
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        return db.query(ScheduledEmail).filter(
            ScheduledEmail.status == "pending",
            ScheduledEmail.scheduled_at <= now
        ).order_by(
            ScheduledEmail.scheduled_at.asc()
        ).limit(limit).all()

    @classmethod
    def mark_email_sent(
        cls,
        db: Session,
        email_id: int,
        external_id: Optional[str] = None
    ) -> bool:
        """Mark an email as sent"""
        email = db.query(ScheduledEmail).filter(
            ScheduledEmail.id == email_id
        ).first()

        if not email:
            return False

        email.status = "sent"
        email.sent_at = datetime.now(timezone.utc).replace(tzinfo=None)
        email.external_id = external_id

        # Update subscriber stats
        subscriber = email.subscriber
        if subscriber:
            subscriber.last_email_sent_at = email.sent_at
            subscriber.total_emails_sent += 1

        # Advance sequence if part of one
        if email.sequence_id:
            cls.advance_sequence(db, email.sequence_id)

        db.commit()
        return True

    @classmethod
    def mark_email_failed(
        cls,
        db: Session,
        email_id: int,
        error_message: str
    ) -> bool:
        """Mark an email as failed"""
        email = db.query(ScheduledEmail).filter(
            ScheduledEmail.id == email_id
        ).first()

        if not email:
            return False

        email.retry_count += 1
        email.error_message = error_message

        if email.retry_count >= email.max_retries:
            email.status = "failed"
        else:
            # Reschedule for retry
            email.scheduled_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(
                minutes=5 * (2 ** email.retry_count)  # Exponential backoff
            )

        db.commit()
        return True

    @classmethod
    def track_email_open(
        cls,
        db: Session,
        email_id: int
    ) -> bool:
        """Track email open event"""
        email = db.query(ScheduledEmail).filter(
            ScheduledEmail.id == email_id
        ).first()

        if not email:
            return False

        if not email.opened_at:  # Only count first open
            email.opened_at = datetime.now(timezone.utc).replace(tzinfo=None)

            # Update subscriber stats
            subscriber = email.subscriber
            if subscriber:
                subscriber.last_email_opened_at = email.opened_at
                subscriber.total_emails_opened += 1

            db.commit()
        return True

    @classmethod
    def track_email_click(
        cls,
        db: Session,
        email_id: int
    ) -> bool:
        """Track email click event"""
        email = db.query(ScheduledEmail).filter(
            ScheduledEmail.id == email_id
        ).first()

        if not email:
            return False

        if not email.clicked_at:  # Only count first click
            email.clicked_at = datetime.now(timezone.utc).replace(tzinfo=None)

            # Update subscriber stats
            subscriber = email.subscriber
            if subscriber:
                subscriber.last_email_clicked_at = email.clicked_at
                subscriber.total_emails_clicked += 1

            db.commit()
        return True

    # =========================================================================
    # Newsletter Scheduling
    # =========================================================================

    @classmethod
    def schedule_weekly_newsletter(
        cls,
        db: Session
    ) -> int:
        """Schedule weekly newsletter for all active subscribers"""
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        # Calculate next Sunday at 10:00 AM
        days_until_sunday = (6 - now.weekday()) % 7
        if days_until_sunday == 0 and now.hour >= 10:
            days_until_sunday = 7

        next_sunday = now.replace(hour=10, minute=0, second=0, microsecond=0)
        next_sunday += timedelta(days=days_until_sunday)

        # Get all active subscribers who want newsletters
        subscribers = db.query(EmailSubscriber).filter(
            EmailSubscriber.is_active == True,
            EmailSubscriber.newsletter_enabled == True
        ).all()

        count = 0
        for subscriber in subscribers:
            # Check if already scheduled
            existing = db.query(ScheduledEmail).filter(
                ScheduledEmail.subscriber_id == subscriber.id,
                ScheduledEmail.email_type == "weekly_newsletter",
                ScheduledEmail.scheduled_at == next_sunday,
                ScheduledEmail.status == "pending"
            ).first()

            if not existing:
                email = ScheduledEmail(
                    subscriber_id=subscriber.id,
                    email_type="weekly_newsletter",
                    subject="🐾 This Week's Longest Waiting Pets",
                    template_name="weekly_newsletter",
                    scheduled_at=next_sunday,
                    status="pending",
                )
                db.add(email)
                count += 1

        db.commit()
        return count

    # =========================================================================
    # Still Waiting Reminders
    # =========================================================================

    @classmethod
    def start_still_waiting_reminder(
        cls,
        db: Session,
        subscriber_id: int,
        animal_id: int
    ) -> Optional[EmailSequence]:
        """Start still waiting reminder sequence for a favorited animal"""
        animal = db.query(Animal).filter(Animal.id == animal_id).first()

        if not animal:
            return None

        context_data = {
            "animal_id": animal_id,
            "animal_name": animal.canonical_name or "This pet",
            "days": animal.days_waiting,
        }

        return cls.start_sequence(
            db,
            subscriber_id,
            "still_waiting",
            context_data=context_data
        )

    # =========================================================================
    # Statistics
    # =========================================================================

    @classmethod
    def get_email_stats(cls, db: Session) -> Dict[str, Any]:
        """Get email marketing statistics"""
        total_subscribers = db.query(func.count(EmailSubscriber.id)).scalar() or 0
        active_subscribers = db.query(func.count(EmailSubscriber.id)).filter(
            EmailSubscriber.is_active == True
        ).scalar() or 0

        total_emails_sent = db.query(func.count(ScheduledEmail.id)).filter(
            ScheduledEmail.status == "sent"
        ).scalar() or 0

        emails_opened = db.query(func.count(ScheduledEmail.id)).filter(
            ScheduledEmail.status == "sent",
            ScheduledEmail.opened_at.isnot(None)
        ).scalar() or 0

        emails_clicked = db.query(func.count(ScheduledEmail.id)).filter(
            ScheduledEmail.status == "sent",
            ScheduledEmail.clicked_at.isnot(None)
        ).scalar() or 0

        open_rate = (emails_opened / total_emails_sent * 100) if total_emails_sent > 0 else 0
        click_rate = (emails_clicked / total_emails_sent * 100) if total_emails_sent > 0 else 0

        return {
            "total_subscribers": total_subscribers,
            "active_subscribers": active_subscribers,
            "total_emails_sent": total_emails_sent,
            "emails_opened": emails_opened,
            "emails_clicked": emails_clicked,
            "open_rate": round(open_rate, 2),
            "click_rate": round(click_rate, 2),
            "target_open_rate": 25.0,
            "target_click_rate": 5.0,
        }

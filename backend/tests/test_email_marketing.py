"""
===============================================================================
Waiting The Longest™ - Email Marketing Tests
===============================================================================
Comprehensive tests for email marketing functionality including:
- Subscriber management
- Email sequences
- Price alerts
- Newsletter scheduling
- Email tracking

===============================================================================
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

from app.models import (
    EmailSubscriber, EmailSequence, ScheduledEmail, PriceAlert, Animal
)
from app.email_marketing import EmailMarketingService, EMAIL_SEQUENCES
from app.schemas import (
    EmailSubscriberCreate, EmailPreferencesUpdate, PriceAlertCreate
)


class TestEmailSubscriberModel:
    """Test EmailSubscriber model"""

    def test_create_subscriber_minimal(self, db_session):
        """Test creating a subscriber with minimal fields"""
        subscriber = EmailSubscriber(
            email="test@example.com"
        )
        db_session.add(subscriber)
        db_session.commit()

        assert subscriber.id is not None
        assert subscriber.email == "test@example.com"
        assert subscriber.is_active == True
        assert subscriber.is_verified == False
        assert subscriber.newsletter_enabled == True

    def test_create_subscriber_full(self, db_session):
        """Test creating a subscriber with all fields"""
        subscriber = EmailSubscriber(
            email="full@example.com",
            first_name="John",
            last_name="Doe",
            preferred_species="dog",
            preferred_location="TX",
            preferred_age_group="adult",
            newsletter_enabled=True,
            product_updates_enabled=True,
            adoption_alerts_enabled=True,
            affiliate_emails_enabled=False,
            consent_given=True,
            consent_date=datetime.now(timezone.utc).replace(tzinfo=None),
            consent_source="website"
        )
        db_session.add(subscriber)
        db_session.commit()

        assert subscriber.id is not None
        assert subscriber.first_name == "John"
        assert subscriber.preferred_species == "dog"
        assert subscriber.affiliate_emails_enabled == False

    def test_subscriber_unique_email(self, db_session):
        """Test that email must be unique"""
        subscriber1 = EmailSubscriber(email="duplicate@example.com")
        db_session.add(subscriber1)
        db_session.commit()

        subscriber2 = EmailSubscriber(email="duplicate@example.com")
        db_session.add(subscriber2)

        with pytest.raises(Exception):  # IntegrityError
            db_session.commit()


class TestEmailSequenceModel:
    """Test EmailSequence model"""

    def test_create_sequence(self, db_session):
        """Test creating an email sequence"""
        subscriber = EmailSubscriber(email="seq@example.com")
        db_session.add(subscriber)
        db_session.commit()

        sequence = EmailSequence(
            subscriber_id=subscriber.id,
            sequence_type="welcome",
            current_step=0,
            total_steps=5,
            status="active"
        )
        db_session.add(sequence)
        db_session.commit()

        assert sequence.id is not None
        assert sequence.sequence_type == "welcome"
        assert sequence.is_completed == False

    def test_sequence_subscriber_relationship(self, db_session):
        """Test sequence-subscriber relationship"""
        subscriber = EmailSubscriber(email="rel@example.com")
        db_session.add(subscriber)
        db_session.commit()

        sequence = EmailSequence(
            subscriber_id=subscriber.id,
            sequence_type="welcome",
            total_steps=5
        )
        db_session.add(sequence)
        db_session.commit()

        assert sequence.subscriber.email == "rel@example.com"
        assert len(subscriber.email_sequences) == 1


class TestScheduledEmailModel:
    """Test ScheduledEmail model"""

    def test_create_scheduled_email(self, db_session):
        """Test creating a scheduled email"""
        subscriber = EmailSubscriber(email="sched@example.com")
        db_session.add(subscriber)
        db_session.commit()

        email = ScheduledEmail(
            subscriber_id=subscriber.id,
            email_type="welcome_1",
            subject="Welcome!",
            scheduled_at=datetime.now(timezone.utc).replace(tzinfo=None),
            status="pending"
        )
        db_session.add(email)
        db_session.commit()

        assert email.id is not None
        assert email.status == "pending"
        assert email.retry_count == 0


class TestPriceAlertModel:
    """Test PriceAlert model"""

    def test_create_price_alert(self, db_session):
        """Test creating a price alert"""
        subscriber = EmailSubscriber(email="alert@example.com")
        db_session.add(subscriber)
        db_session.commit()

        alert = PriceAlert(
            subscriber_id=subscriber.id,
            alert_type="price_drop",
            target_type="product",
            target_id="B001234567",
            target_name="Dog Food",
            target_price=25.99
        )
        db_session.add(alert)
        db_session.commit()

        assert alert.id is not None
        assert alert.is_active == True
        assert alert.is_triggered == False


class TestEmailMarketingService:
    """Test EmailMarketingService methods"""

    def test_subscribe_new_user(self, db_session):
        """Test subscribing a new user"""
        subscriber_data = EmailSubscriberCreate(
            email="new@example.com",
            first_name="New",
            last_name="User"
        )

        subscriber = EmailMarketingService.subscribe(db_session, subscriber_data)

        assert subscriber.id is not None
        assert subscriber.email == "new@example.com"
        assert subscriber.is_active == True
        assert subscriber.consent_given == True

        # Should have started welcome sequence
        sequences = db_session.query(EmailSequence).filter(
            EmailSequence.subscriber_id == subscriber.id
        ).all()
        assert len(sequences) == 1
        assert sequences[0].sequence_type == "welcome"

    def test_subscribe_existing_user(self, db_session):
        """Test subscribing returns existing active user"""
        # Create first subscription
        subscriber_data = EmailSubscriberCreate(email="existing@example.com")
        subscriber1 = EmailMarketingService.subscribe(db_session, subscriber_data)

        # Try to subscribe again
        subscriber2 = EmailMarketingService.subscribe(db_session, subscriber_data)

        assert subscriber1.id == subscriber2.id

    def test_subscribe_reactivate_unsubscribed(self, db_session):
        """Test reactivating an unsubscribed user"""
        subscriber_data = EmailSubscriberCreate(email="reactivate@example.com")
        subscriber = EmailMarketingService.subscribe(db_session, subscriber_data)

        # Unsubscribe
        EmailMarketingService.unsubscribe(db_session, subscriber.email)
        db_session.refresh(subscriber)
        assert subscriber.is_active == False

        # Resubscribe
        reactivated = EmailMarketingService.subscribe(db_session, subscriber_data)
        assert reactivated.is_active == True
        assert reactivated.id == subscriber.id

    def test_unsubscribe(self, db_session):
        """Test unsubscribing a user"""
        subscriber_data = EmailSubscriberCreate(email="unsub@example.com")
        subscriber = EmailMarketingService.subscribe(db_session, subscriber_data)

        result = EmailMarketingService.unsubscribe(db_session, subscriber.email)

        assert result == True
        db_session.refresh(subscriber)
        assert subscriber.is_active == False
        assert subscriber.unsubscribe_date is not None

    def test_unsubscribe_cancels_sequences(self, db_session):
        """Test that unsubscribing cancels active sequences"""
        subscriber_data = EmailSubscriberCreate(email="cancel@example.com")
        subscriber = EmailMarketingService.subscribe(db_session, subscriber_data)

        EmailMarketingService.unsubscribe(db_session, subscriber.email)

        sequences = db_session.query(EmailSequence).filter(
            EmailSequence.subscriber_id == subscriber.id
        ).all()
        for seq in sequences:
            assert seq.status == "cancelled"

    def test_verify_email(self, db_session):
        """Test email verification"""
        subscriber_data = EmailSubscriberCreate(email="verify@example.com")
        subscriber = EmailMarketingService.subscribe(db_session, subscriber_data)
        token = subscriber.verification_token

        result = EmailMarketingService.verify_email(db_session, subscriber.email, token)

        assert result == True
        db_session.refresh(subscriber)
        assert subscriber.is_verified == True
        assert subscriber.verification_token is None

    def test_verify_email_invalid_token(self, db_session):
        """Test verification with invalid token fails"""
        subscriber_data = EmailSubscriberCreate(email="badtoken@example.com")
        subscriber = EmailMarketingService.subscribe(db_session, subscriber_data)

        result = EmailMarketingService.verify_email(db_session, subscriber.email, "wrong-token")

        assert result == False

    def test_update_preferences(self, db_session):
        """Test updating email preferences"""
        subscriber_data = EmailSubscriberCreate(email="prefs@example.com")
        subscriber = EmailMarketingService.subscribe(db_session, subscriber_data)

        preferences = EmailPreferencesUpdate(
            newsletter_enabled=False,
            affiliate_emails_enabled=False
        )
        updated = EmailMarketingService.update_preferences(db_session, subscriber.id, preferences)

        assert updated.newsletter_enabled == False
        assert updated.affiliate_emails_enabled == False
        assert updated.product_updates_enabled == True  # Unchanged

    def test_start_sequence(self, db_session):
        """Test starting an email sequence"""
        subscriber = EmailSubscriber(email="seq-test@example.com", is_active=True)
        db_session.add(subscriber)
        db_session.commit()

        sequence = EmailMarketingService.start_sequence(
            db_session, subscriber.id, "welcome"
        )

        assert sequence is not None
        assert sequence.sequence_type == "welcome"
        assert sequence.total_steps == 5
        assert sequence.current_step == 0

        # Should have scheduled first email
        emails = db_session.query(ScheduledEmail).filter(
            ScheduledEmail.sequence_id == sequence.id
        ).all()
        assert len(emails) == 1
        assert emails[0].email_type == "welcome_1"

    def test_start_sequence_prevents_duplicate(self, db_session):
        """Test that duplicate active sequences are prevented"""
        subscriber = EmailSubscriber(email="dup-seq@example.com", is_active=True)
        db_session.add(subscriber)
        db_session.commit()

        seq1 = EmailMarketingService.start_sequence(db_session, subscriber.id, "welcome")
        seq2 = EmailMarketingService.start_sequence(db_session, subscriber.id, "welcome")

        assert seq1.id == seq2.id

    def test_advance_sequence(self, db_session):
        """Test advancing through a sequence"""
        subscriber = EmailSubscriber(email="adv@example.com", is_active=True)
        db_session.add(subscriber)
        db_session.commit()

        sequence = EmailMarketingService.start_sequence(
            db_session, subscriber.id, "welcome"
        )

        EmailMarketingService.advance_sequence(db_session, sequence.id)

        db_session.refresh(sequence)
        assert sequence.current_step == 1
        assert sequence.last_email_sent_at is not None

    def test_create_price_alert(self, db_session):
        """Test creating a price alert"""
        subscriber = EmailSubscriber(email="price@example.com", is_active=True)
        db_session.add(subscriber)
        db_session.commit()

        alert_data = PriceAlertCreate(
            alert_type="price_drop",
            target_type="product",
            target_id="B001234567",
            target_name="Dog Toy",
            target_price=15.99
        )

        alert = EmailMarketingService.create_price_alert(
            db_session, subscriber.id, alert_data
        )

        assert alert.id is not None
        assert alert.target_price == 15.99
        assert alert.is_active == True
        assert alert.expires_at is not None

    def test_check_price_alerts_triggers(self, db_session):
        """Test that price alerts trigger correctly"""
        subscriber = EmailSubscriber(email="trigger@example.com", is_active=True)
        db_session.add(subscriber)
        db_session.commit()

        # Create alert for price drop to $20
        alert = PriceAlert(
            subscriber_id=subscriber.id,
            alert_type="price_drop",
            target_type="product",
            target_id="PROD123",
            target_price=20.00,
            is_active=True
        )
        db_session.add(alert)
        db_session.commit()

        # Check with price above threshold - should not trigger
        triggered = EmailMarketingService.check_price_alerts(db_session, "PROD123", 25.00)
        assert len(triggered) == 0

        # Check with price at or below threshold - should trigger
        triggered = EmailMarketingService.check_price_alerts(db_session, "PROD123", 19.99)
        assert len(triggered) == 1
        assert triggered[0].is_triggered == True

    def test_get_pending_emails(self, db_session):
        """Test getting pending emails"""
        subscriber = EmailSubscriber(email="pending@example.com", is_active=True)
        db_session.add(subscriber)
        db_session.commit()

        # Create past-due email
        past_email = ScheduledEmail(
            subscriber_id=subscriber.id,
            email_type="test",
            subject="Past Due",
            scheduled_at=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1),
            status="pending"
        )
        db_session.add(past_email)

        # Create future email
        future_email = ScheduledEmail(
            subscriber_id=subscriber.id,
            email_type="test",
            subject="Future",
            scheduled_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=1),
            status="pending"
        )
        db_session.add(future_email)
        db_session.commit()

        pending = EmailMarketingService.get_pending_emails(db_session)

        assert len(pending) == 1
        assert pending[0].subject == "Past Due"

    def test_mark_email_sent(self, db_session):
        """Test marking email as sent"""
        subscriber = EmailSubscriber(email="sent@example.com", is_active=True)
        db_session.add(subscriber)
        db_session.commit()

        email = ScheduledEmail(
            subscriber_id=subscriber.id,
            email_type="test",
            subject="Test",
            scheduled_at=datetime.now(timezone.utc).replace(tzinfo=None),
            status="pending"
        )
        db_session.add(email)
        db_session.commit()

        EmailMarketingService.mark_email_sent(db_session, email.id, "ext-123")

        db_session.refresh(email)
        assert email.status == "sent"
        assert email.external_id == "ext-123"
        assert email.sent_at is not None

        db_session.refresh(subscriber)
        assert subscriber.total_emails_sent == 1

    def test_mark_email_failed_with_retry(self, db_session):
        """Test marking email as failed with retry"""
        subscriber = EmailSubscriber(email="fail@example.com", is_active=True)
        db_session.add(subscriber)
        db_session.commit()

        email = ScheduledEmail(
            subscriber_id=subscriber.id,
            email_type="test",
            subject="Test",
            scheduled_at=datetime.now(timezone.utc).replace(tzinfo=None),
            status="pending",
            max_retries=3
        )
        db_session.add(email)
        db_session.commit()

        original_scheduled = email.scheduled_at

        EmailMarketingService.mark_email_failed(db_session, email.id, "Connection error")

        db_session.refresh(email)
        assert email.retry_count == 1
        assert email.status == "pending"  # Still pending for retry
        assert email.scheduled_at > original_scheduled  # Rescheduled

    def test_mark_email_failed_max_retries(self, db_session):
        """Test marking email as failed after max retries"""
        subscriber = EmailSubscriber(email="maxfail@example.com", is_active=True)
        db_session.add(subscriber)
        db_session.commit()

        email = ScheduledEmail(
            subscriber_id=subscriber.id,
            email_type="test",
            subject="Test",
            scheduled_at=datetime.now(timezone.utc).replace(tzinfo=None),
            status="pending",
            retry_count=2,  # Already tried twice
            max_retries=3
        )
        db_session.add(email)
        db_session.commit()

        EmailMarketingService.mark_email_failed(db_session, email.id, "Connection error")

        db_session.refresh(email)
        assert email.retry_count == 3
        assert email.status == "failed"

    def test_track_email_open(self, db_session):
        """Test tracking email open"""
        subscriber = EmailSubscriber(email="open@example.com", is_active=True)
        db_session.add(subscriber)
        db_session.commit()

        email = ScheduledEmail(
            subscriber_id=subscriber.id,
            email_type="test",
            subject="Test",
            scheduled_at=datetime.now(timezone.utc).replace(tzinfo=None),
            status="sent"
        )
        db_session.add(email)
        db_session.commit()

        EmailMarketingService.track_email_open(db_session, email.id)

        db_session.refresh(email)
        assert email.opened_at is not None

        db_session.refresh(subscriber)
        assert subscriber.total_emails_opened == 1

    def test_track_email_click(self, db_session):
        """Test tracking email click"""
        subscriber = EmailSubscriber(email="click@example.com", is_active=True)
        db_session.add(subscriber)
        db_session.commit()

        email = ScheduledEmail(
            subscriber_id=subscriber.id,
            email_type="test",
            subject="Test",
            scheduled_at=datetime.now(timezone.utc).replace(tzinfo=None),
            status="sent"
        )
        db_session.add(email)
        db_session.commit()

        EmailMarketingService.track_email_click(db_session, email.id)

        db_session.refresh(email)
        assert email.clicked_at is not None

        db_session.refresh(subscriber)
        assert subscriber.total_emails_clicked == 1

    def test_get_email_stats(self, db_session):
        """Test getting email statistics"""
        # Create some test data
        subscriber = EmailSubscriber(email="stats@example.com", is_active=True)
        db_session.add(subscriber)
        db_session.commit()

        for i in range(10):
            email = ScheduledEmail(
                subscriber_id=subscriber.id,
                email_type="test",
                subject=f"Test {i}",
                scheduled_at=datetime.now(timezone.utc).replace(tzinfo=None),
                status="sent"
            )
            if i < 3:  # 30% opened
                email.opened_at = datetime.now(timezone.utc).replace(tzinfo=None)
            if i < 1:  # 10% clicked
                email.clicked_at = datetime.now(timezone.utc).replace(tzinfo=None)
            db_session.add(email)

        db_session.commit()

        stats = EmailMarketingService.get_email_stats(db_session)

        assert stats["total_subscribers"] == 1
        assert stats["active_subscribers"] == 1
        assert stats["total_emails_sent"] == 10
        assert stats["emails_opened"] == 3
        assert stats["emails_clicked"] == 1
        assert stats["open_rate"] == 30.0
        assert stats["click_rate"] == 10.0


class TestEmailMarketingAPI:
    """Test email marketing API endpoints"""

    def test_subscribe_endpoint(self, client):
        """Test newsletter subscription endpoint"""
        response = client.post(
            "/api/newsletter/subscribe",
            json={
                "email": "api-test@example.com",
                "first_name": "API",
                "last_name": "Test"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "subscriber_id" in data

    def test_subscribe_invalid_email(self, client):
        """Test subscription with invalid email"""
        response = client.post(
            "/api/newsletter/subscribe",
            json={
                "email": "not-an-email"
            }
        )
        assert response.status_code == 422

    def test_unsubscribe_endpoint(self, client, db_session):
        """Test unsubscribe endpoint"""
        # First subscribe
        subscriber = EmailSubscriber(email="unsub-api@example.com", is_active=True)
        db_session.add(subscriber)
        db_session.commit()

        response = client.post(
            "/api/newsletter/unsubscribe",
            params={"email": "unsub-api@example.com"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True

    def test_unsubscribe_nonexistent(self, client):
        """Test unsubscribe for non-existent email"""
        response = client.post(
            "/api/newsletter/unsubscribe",
            params={"email": "nonexistent@example.com"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == False

    def test_update_preferences_endpoint(self, client, db_session):
        """Test update preferences endpoint"""
        subscriber = EmailSubscriber(email="prefs-api@example.com", is_active=True)
        db_session.add(subscriber)
        db_session.commit()

        response = client.put(
            f"/api/newsletter/preferences/{subscriber.id}",
            json={
                "newsletter_enabled": False,
                "affiliate_emails_enabled": False
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["newsletter_enabled"] == False

    def test_create_alert_endpoint(self, client, db_session):
        """Test create price alert endpoint"""
        subscriber = EmailSubscriber(email="alert-api@example.com", is_active=True)
        db_session.add(subscriber)
        db_session.commit()

        response = client.post(
            "/api/alerts",
            params={"email": "alert-api@example.com"},
            json={
                "alert_type": "price_drop",
                "target_type": "product",
                "target_id": "B001234567",
                "target_name": "Dog Toy",
                "target_price": 19.99
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["target_id"] == "B001234567"

    def test_create_alert_requires_subscription(self, client):
        """Test that alerts require subscription"""
        response = client.post(
            "/api/alerts",
            params={"email": "notsub@example.com"},
            json={
                "alert_type": "price_drop",
                "target_type": "product",
                "target_id": "B001234567"
            }
        )
        assert response.status_code == 404

    def test_get_alerts_endpoint(self, client, db_session):
        """Test get alerts endpoint"""
        subscriber = EmailSubscriber(email="get-alert@example.com", is_active=True)
        db_session.add(subscriber)
        db_session.commit()

        alert = PriceAlert(
            subscriber_id=subscriber.id,
            alert_type="price_drop",
            target_type="product",
            target_id="TEST123",
            is_active=True
        )
        db_session.add(alert)
        db_session.commit()

        response = client.get(
            "/api/alerts",
            params={"email": "get-alert@example.com"}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    def test_delete_alert_endpoint(self, client, db_session):
        """Test delete alert endpoint"""
        subscriber = EmailSubscriber(email="del-alert@example.com", is_active=True)
        db_session.add(subscriber)
        db_session.commit()

        alert = PriceAlert(
            subscriber_id=subscriber.id,
            alert_type="price_drop",
            target_type="product",
            target_id="DEL123",
            is_active=True
        )
        db_session.add(alert)
        db_session.commit()

        response = client.delete(
            f"/api/alerts/{alert.id}",
            params={"email": "del-alert@example.com"}
        )
        assert response.status_code == 200

        db_session.refresh(alert)
        assert alert.is_active == False

    def test_still_waiting_reminder_endpoint(self, client, db_session, sample_animal):
        """Test still waiting reminder endpoint"""
        subscriber = EmailSubscriber(
            email="remind@example.com",
            is_active=True,
            adoption_alerts_enabled=True
        )
        db_session.add(subscriber)
        db_session.commit()

        response = client.post(
            f"/api/favorites/{sample_animal.id}/remind",
            params={"email": "remind@example.com"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "sequence_id" in data

    def test_still_waiting_requires_adoption_alerts(self, client, db_session, sample_animal):
        """Test that still waiting requires adoption alerts enabled"""
        subscriber = EmailSubscriber(
            email="noalerts@example.com",
            is_active=True,
            adoption_alerts_enabled=False
        )
        db_session.add(subscriber)
        db_session.commit()

        response = client.post(
            f"/api/favorites/{sample_animal.id}/remind",
            params={"email": "noalerts@example.com"}
        )
        assert response.status_code == 400

    def test_email_stats_endpoint(self, client):
        """Test email stats endpoint"""
        response = client.get("/api/email/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_subscribers" in data
        assert "open_rate" in data
        assert "click_rate" in data
        assert "target_open_rate" in data


class TestEmailSequenceDefinitions:
    """Test email sequence configuration"""

    def test_welcome_sequence_exists(self):
        """Test welcome sequence is properly defined"""
        assert "welcome" in EMAIL_SEQUENCES
        welcome = EMAIL_SEQUENCES["welcome"]
        assert welcome["total_steps"] == 5
        assert len(welcome["spacing_days"]) == 5
        assert len(welcome["emails"]) == 5

    def test_abandoned_cart_sequence_exists(self):
        """Test abandoned cart sequence is properly defined"""
        assert "abandoned_cart" in EMAIL_SEQUENCES
        cart = EMAIL_SEQUENCES["abandoned_cart"]
        assert cart["total_steps"] == 3
        assert "spacing_hours" in cart

    def test_still_waiting_sequence_exists(self):
        """Test still waiting sequence is properly defined"""
        assert "still_waiting" in EMAIL_SEQUENCES
        waiting = EMAIL_SEQUENCES["still_waiting"]
        assert waiting["total_steps"] == 3

    def test_adoption_followup_sequence_exists(self):
        """Test adoption followup sequence is properly defined"""
        assert "adoption_followup" in EMAIL_SEQUENCES
        followup = EMAIL_SEQUENCES["adoption_followup"]
        assert followup["total_steps"] == 4

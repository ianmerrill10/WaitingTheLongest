"""
===============================================================================
Waiting The Longest™ - Shelter CRM Models
===============================================================================
Purpose: Database models for the Shelter Customer Relationship Management system.
         Tracks outreach, onboarding stages, contact history, and partnerships.

Tables:
  - shelter_outreach: Track outreach attempts and responses
  - shelter_onboarding: Track onboarding stage progression
  - email_templates: Email templates for bulk outreach
  - mail_templates: Physical mail templates
  - contact_history: Log of all contacts with shelters

Onboarding Stages:
  1. discovered - Found in IRS/other sources
  2. contacted_email - Initial email sent
  3. contacted_mail - Physical mail sent
  4. responded - Shelter responded
  5. interested - Shelter expressed interest
  6. onboarding - In active onboarding
  7. api_setup - Setting up API integration
  8. active_partner - Fully onboarded partner
  9. declined - Shelter declined
  10. unresponsive - No response after multiple attempts

Mission: Help shelter animals who have waited the longest find forever homes.
===============================================================================
"""

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey,
    Boolean, Enum as SQLEnum, Float, JSON
)
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum

from .database import Base


class OutreachStatus(enum.Enum):
    """Status of outreach to a shelter."""
    NOT_CONTACTED = "not_contacted"
    EMAIL_QUEUED = "email_queued"
    EMAIL_SENT = "email_sent"
    EMAIL_OPENED = "email_opened"
    EMAIL_CLICKED = "email_clicked"
    EMAIL_BOUNCED = "email_bounced"
    MAIL_QUEUED = "mail_queued"
    MAIL_SENT = "mail_sent"
    RESPONDED = "responded"
    NO_RESPONSE = "no_response"


class OnboardingStage(enum.Enum):
    """Onboarding stage for a shelter partner."""
    DISCOVERED = "discovered"
    CONTACTED_EMAIL = "contacted_email"
    CONTACTED_MAIL = "contacted_mail"
    FOLLOW_UP_1 = "follow_up_1"
    FOLLOW_UP_2 = "follow_up_2"
    FOLLOW_UP_3 = "follow_up_3"
    RESPONDED = "responded"
    INTERESTED = "interested"
    ONBOARDING = "onboarding"
    API_SETUP = "api_setup"
    ACTIVE_PARTNER = "active_partner"
    DECLINED = "declined"
    UNRESPONSIVE = "unresponsive"


class ContactMethod(enum.Enum):
    """Method of contact."""
    EMAIL = "email"
    PHONE = "phone"
    MAIL = "mail"
    SOCIAL_MEDIA = "social_media"
    IN_PERSON = "in_person"
    API = "api"


class ShelterOutreach(Base):
    """Track outreach to shelters."""
    __tablename__ = "shelter_outreach"

    id = Column(Integer, primary_key=True, index=True)
    shelter_id = Column(Integer, ForeignKey("shelters.id"), nullable=False, index=True)

    # Current status
    outreach_status = Column(String(50), default="not_contacted")
    onboarding_stage = Column(String(50), default="discovered")

    # Contact info quality
    has_email = Column(Boolean, default=False)
    has_phone = Column(Boolean, default=False)
    has_address = Column(Boolean, default=False)
    has_website = Column(Boolean, default=False)

    # Outreach tracking
    emails_sent = Column(Integer, default=0)
    emails_opened = Column(Integer, default=0)
    emails_clicked = Column(Integer, default=0)
    mail_sent = Column(Integer, default=0)
    phone_calls = Column(Integer, default=0)

    # Response tracking
    first_contact_date = Column(DateTime)
    last_contact_date = Column(DateTime)
    first_response_date = Column(DateTime)
    last_response_date = Column(DateTime)

    # Priority/scoring
    priority_score = Column(Float, default=0.0)  # Higher = more important
    engagement_score = Column(Float, default=0.0)  # Based on opens/clicks

    # Notes
    notes = Column(Text)

    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                       onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    shelter = relationship("Shelter", backref="outreach")


class ContactHistory(Base):
    """Log of all contacts with shelters."""
    __tablename__ = "contact_history"

    id = Column(Integer, primary_key=True, index=True)
    shelter_id = Column(Integer, ForeignKey("shelters.id"), nullable=False, index=True)
    outreach_id = Column(Integer, ForeignKey("shelter_outreach.id"))

    # Contact details
    contact_method = Column(String(50), nullable=False)  # email, phone, mail, etc.
    contact_type = Column(String(100))  # initial, follow_up_1, etc.
    template_used = Column(String(100))

    # For emails
    subject = Column(String(500))
    message_preview = Column(Text)

    # Tracking
    sent_at = Column(DateTime)
    opened_at = Column(DateTime)
    clicked_at = Column(DateTime)
    bounced = Column(Boolean, default=False)
    bounce_reason = Column(String(500))

    # Response
    responded = Column(Boolean, default=False)
    response_received_at = Column(DateTime)
    response_content = Column(Text)
    response_sentiment = Column(String(50))  # positive, negative, neutral

    # Metadata
    sent_by = Column(String(100))  # user or agent that sent it
    metadata = Column(JSON)

    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class EmailTemplate(Base):
    """Email templates for bulk outreach."""
    __tablename__ = "email_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, unique=True)
    category = Column(String(100))  # initial, follow_up, partnership, etc.

    # Template content
    subject_template = Column(String(500), nullable=False)
    body_html = Column(Text, nullable=False)
    body_text = Column(Text)  # Plain text version

    # Variables available
    variables = Column(JSON)  # List of variables like {{shelter_name}}, {{state}}

    # Tracking
    times_used = Column(Integer, default=0)
    open_rate = Column(Float, default=0.0)
    click_rate = Column(Float, default=0.0)
    response_rate = Column(Float, default=0.0)

    # Status
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                       onupdate=lambda: datetime.now(timezone.utc))


class MailTemplate(Base):
    """Physical mail templates."""
    __tablename__ = "mail_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, unique=True)
    category = Column(String(100))

    # Template content
    letter_content = Column(Text, nullable=False)
    envelope_format = Column(String(100))  # standard, large, postcard

    # Variables
    variables = Column(JSON)

    # Tracking
    times_used = Column(Integer, default=0)
    response_rate = Column(Float, default=0.0)

    # Status
    is_active = Column(Boolean, default=True)

    # Estimated cost per piece
    estimated_cost = Column(Float, default=0.50)

    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class BulkOutreachCampaign(Base):
    """Track bulk outreach campaigns."""
    __tablename__ = "bulk_outreach_campaigns"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)

    # Campaign type
    campaign_type = Column(String(50))  # email, mail, mixed
    template_id = Column(Integer)  # Reference to email or mail template

    # Targeting
    target_states = Column(JSON)  # List of state codes, or null for all
    target_stages = Column(JSON)  # List of onboarding stages to target
    exclude_stages = Column(JSON)  # Stages to exclude

    # Progress
    total_targets = Column(Integer, default=0)
    sent_count = Column(Integer, default=0)
    opened_count = Column(Integer, default=0)
    clicked_count = Column(Integer, default=0)
    responded_count = Column(Integer, default=0)

    # Status
    status = Column(String(50), default="draft")  # draft, scheduled, running, completed, cancelled
    scheduled_at = Column(DateTime)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)

    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

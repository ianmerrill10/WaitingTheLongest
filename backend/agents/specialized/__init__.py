#!/usr/bin/env python3
"""
===============================================================================
Specialized Agents Package
===============================================================================
Contains all specialized AI agents for the Waiting The Longest system.

Agent Categories:
- Social Media: TikTok, Instagram, Facebook, Marketing
- Data Processing: Librarian, Data Quality, Image Processing, Translation
- Operations: Debugging, Accounting, Scheduler, Backup, Compliance
- Marketing: SEO, Email Campaign, Content Writer, Video Generator
- Monitoring: Alert Monitor, API Monitor, Analytics, Sentiment, Competitor Watch
- Support: Donation Tracker, Volunteer Coordinator, Adoption Matcher, Chat Support

All agents implement the CooperativeMixin for inter-agent communication.
===============================================================================
"""

from agents.specialized.marketing_agent import MarketingAgent
from agents.specialized.tiktok_agent import TikTokAgent
from agents.specialized.instagram_agent import InstagramAgent
from agents.specialized.facebook_agent import FacebookAgent
from agents.specialized.librarian_agent import LibrarianAgent
from agents.specialized.debugging_agent import DebuggingAgent
from agents.specialized.accounting_agent import AccountingAgent
from agents.specialized.intake_agent import IntakeSpecialistAgent
from agents.specialized.data_quality_agent import DataQualityAgent
from agents.specialized.seo_agent import SEOAgent
from agents.specialized.email_agent import EmailCampaignAgent
from agents.specialized.analytics_agent import AnalyticsAgent
from agents.specialized.content_writer_agent import ContentWriterAgent
from agents.specialized.image_agent import ImageProcessingAgent
from agents.specialized.scheduler_agent import SchedulerAgent
from agents.specialized.alert_agent import AlertMonitorAgent
from agents.specialized.donation_agent import DonationTrackerAgent
from agents.specialized.volunteer_agent import VolunteerCoordinatorAgent
from agents.specialized.matcher_agent import AdoptionMatcherAgent
from agents.specialized.translation_agent import TranslationAgent
from agents.specialized.video_agent import VideoGeneratorAgent
from agents.specialized.notification_agent import NotificationAgent
from agents.specialized.compliance_agent import ComplianceAgent
from agents.specialized.backup_agent import BackupAgent
from agents.specialized.api_monitor_agent import APIMonitorAgent
from agents.specialized.report_agent import ReportGeneratorAgent
from agents.specialized.chat_agent import ChatSupportAgent
from agents.specialized.sentiment_agent import SentimentAnalysisAgent
from agents.specialized.competitor_agent import CompetitorWatchAgent

__all__ = [
    'MarketingAgent',
    'TikTokAgent',
    'InstagramAgent',
    'FacebookAgent',
    'LibrarianAgent',
    'DebuggingAgent',
    'AccountingAgent',
    'IntakeSpecialistAgent',
    'DataQualityAgent',
    'SEOAgent',
    'EmailCampaignAgent',
    'AnalyticsAgent',
    'ContentWriterAgent',
    'ImageProcessingAgent',
    'SchedulerAgent',
    'AlertMonitorAgent',
    'DonationTrackerAgent',
    'VolunteerCoordinatorAgent',
    'AdoptionMatcherAgent',
    'TranslationAgent',
    'VideoGeneratorAgent',
    'NotificationAgent',
    'ComplianceAgent',
    'BackupAgent',
    'APIMonitorAgent',
    'ReportGeneratorAgent',
    'ChatSupportAgent',
    'SentimentAnalysisAgent',
    'CompetitorWatchAgent',
]

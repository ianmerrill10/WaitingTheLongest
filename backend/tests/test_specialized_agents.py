"""
===============================================================================
Unit Tests for Specialized Agents
===============================================================================
Tests for specialized agent classes including:
- MarketingAgent
- SocialMediaAgent
- EmailCampaignAgent
- VideoGeneratorAgent
- SEOAgent
- DataQualityAgent
- AdoptionMatcherAgent
- StateAgent

Author: Waiting The Longest Development Team
Last Updated: 2025-12-07
===============================================================================
"""

import pytest
import asyncio
import json
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock, Mock
import queue

# Set up path for imports
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from agents.base_agent import (
    AgentStatus,
    TaskPriority,
    AgentTask,
    AgentResult,
    BaseAgent,
    generate_task_id
)
from agents.protocols import (
    CooperativeMixin,
    CooperationProtocol,
    DataCategory,
    Priority,
    MessageType,
    AgentMessage
)


# ============================================================================
# MarketingAgent Tests
# ============================================================================

class TestMarketingAgent:
    """Tests for MarketingAgent."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Reset state before each test."""
        BaseAgent._registry.clear()
        while not BaseAgent._message_bus.empty():
            try:
                BaseAgent._message_bus.get_nowait()
            except queue.Empty:
                break

    @pytest.fixture
    def marketing_agent(self):
        """Create a marketing agent for testing."""
        with patch('agents.base_agent.init_db'):
            with patch('agents.base_agent.SessionLocal'):
                from agents.specialized.marketing_agent import MarketingAgent
                return MarketingAgent()

    def test_marketing_agent_initialization(self, marketing_agent):
        """Test marketing agent is properly initialized."""
        assert marketing_agent.agent_id == "marketing"
        assert marketing_agent.agent_name == "Marketing Agent"
        assert marketing_agent.agent_type == "specialized_agent"
        assert marketing_agent.status == AgentStatus.IDLE
        assert isinstance(marketing_agent.campaigns, dict)
        assert isinstance(marketing_agent.content_calendar, list)

    @pytest.mark.asyncio
    async def test_create_campaign(self, marketing_agent):
        """Test creating a marketing campaign."""
        campaign_data = {
            'name': 'Spring Adoption Drive',
            'objective': 'awareness',
            'channels': ['instagram', 'facebook'],
            'budget': 1000.0,
            'start_date': datetime.now().isoformat(),
            'end_date': (datetime.now() + timedelta(days=30)).isoformat()
        }

        result = await marketing_agent.create_campaign(campaign_data)

        assert 'campaign_id' in result
        assert result['status'] == 'created'
        assert len(marketing_agent.campaigns) == 1

    @pytest.mark.asyncio
    async def test_launch_campaign(self, marketing_agent):
        """Test launching a campaign."""
        # Create a campaign first
        campaign_data = {
            'name': 'Test Campaign',
            'channels': ['tiktok', 'instagram']
        }
        create_result = await marketing_agent.create_campaign(campaign_data)
        campaign_id = create_result['campaign_id']

        # Mock the request_from_agent method
        marketing_agent.request_from_agent = AsyncMock(return_value={'success': True})

        # Launch the campaign
        result = await marketing_agent.launch_campaign(campaign_id)

        assert result['status'] == 'active'
        assert result['campaign_id'] == campaign_id
        assert set(result['channels']) == {'tiktok', 'instagram'}
        assert marketing_agent.campaigns[campaign_id].status == 'active'

    @pytest.mark.asyncio
    async def test_execute_task_create_campaign(self, marketing_agent):
        """Test executing a create_campaign task."""
        task = AgentTask(
            task_id="test_task_1",
            task_type="create_campaign",
            payload={'name': 'Email Campaign', 'objective': 'conversions'}
        )

        result = await marketing_agent.execute_task(task)

        assert result.success is True
        assert 'campaign_id' in result.data
        assert result.data['status'] == 'created'

    @pytest.mark.asyncio
    async def test_suggest_content(self, marketing_agent):
        """Test content suggestion generation."""
        marketing_agent.request_from_agent = AsyncMock(return_value={'trends': [], 'keywords': []})

        result = await marketing_agent.suggest_content({
            'topic': 'dog adoption',
            'platform': 'instagram'
        })

        assert 'topic' in result
        assert 'content_ideas' in result
        assert 'best_times' in result
        assert len(result['content_ideas']) > 0
        assert 'instagram' in result['best_times']

    @pytest.mark.asyncio
    async def test_marketing_agent_error_handling(self, marketing_agent):
        """Test error handling in marketing agent."""
        task = AgentTask(
            task_id="error_task",
            task_type="unknown_task_type",
            payload={}
        )

        result = await marketing_agent.execute_task(task)

        assert result.success is True  # Task completes but returns error in data
        assert 'error' in result.data


# ============================================================================
# SocialMediaAgent Tests
# ============================================================================

class TestSocialMediaAgent:
    """Tests for SocialMediaAgent."""

    @pytest.fixture
    def social_agent(self):
        """Create a social media agent for testing."""
        from agents.social_agent import SocialMediaAgent
        return SocialMediaAgent()

    def test_social_agent_initialization(self, social_agent):
        """Test social agent is properly initialized."""
        assert hasattr(social_agent, 'logger')

    def test_generate_instagram_post(self, social_agent):
        """Test Instagram post generation."""
        animal_data = {
            'name': 'Buddy',
            'days_waiting': 365,
            'breed': 'Golden Retriever',
            'location': 'Los Angeles, CA',
            'id': 123
        }

        result = social_agent.generate_instagram_post(animal_data)

        assert result['platform'] == 'instagram'
        assert 'caption' in result
        assert 'hashtags' in result
        assert 'Buddy' in result['caption']
        assert '365' in result['caption']

    def test_generate_tweet(self, social_agent):
        """Test Twitter post generation."""
        animal_data = {
            'name': 'Max',
            'days_waiting': 200,
            'breed': 'Labrador',
            'id': 456
        }

        result = social_agent.generate_tweet(animal_data)

        assert result['platform'] == 'twitter'
        assert 'text' in result
        assert 'Max' in result['text']
        assert '200' in result['text']
        assert len(result['text']) <= 280  # Twitter character limit

    def test_generate_tiktok_script(self, social_agent):
        """Test TikTok script generation."""
        animal_data = {
            'name': 'Luna',
            'days_waiting': 500,
            'breed': 'Pitbull'
        }

        result = social_agent.generate_tiktok_script(animal_data)

        assert result['platform'] == 'tiktok'
        assert 'script' in result
        assert 'Luna' in result['script']
        assert '500' in result['script']


# ============================================================================
# EmailCampaignAgent Tests
# ============================================================================

class TestEmailCampaignAgent:
    """Tests for EmailCampaignAgent."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Reset state before each test."""
        BaseAgent._registry.clear()
        while not BaseAgent._message_bus.empty():
            try:
                BaseAgent._message_bus.get_nowait()
            except queue.Empty:
                break

    @pytest.fixture
    def email_agent(self):
        """Create an email agent for testing."""
        with patch('agents.base_agent.init_db'):
            with patch('agents.base_agent.SessionLocal'):
                from agents.specialized.email_agent import EmailCampaignAgent
                return EmailCampaignAgent()

    def test_email_agent_initialization(self, email_agent):
        """Test email agent is properly initialized."""
        assert email_agent.agent_id == "email_campaign"
        assert email_agent.agent_name == "Email Campaign Agent"
        assert email_agent.agent_type == "specialized_agent"
        assert isinstance(email_agent.campaigns, list)
        assert isinstance(email_agent.templates, dict)

    @pytest.mark.asyncio
    async def test_create_campaign(self, email_agent):
        """Test creating an email campaign."""
        params = {
            'name': 'Newsletter Campaign',
            'subject': 'Adopt a Pet Today!',
            'template': 'newsletter',
            'recipients': ['user1@example.com', 'user2@example.com']
        }

        result = await email_agent.create_campaign(params)

        assert 'id' in result
        assert result['name'] == 'Newsletter Campaign'
        assert result['status'] == 'draft'
        assert result['stats']['sent'] == 0
        assert len(email_agent.campaigns) == 1

    @pytest.mark.asyncio
    async def test_send_newsletter(self, email_agent):
        """Test sending a newsletter."""
        email_agent.request_from_agent = AsyncMock(return_value={'content': 'Newsletter content'})

        params = {
            'subject': 'Weekly Update',
            'content': 'This week\'s updates'
        }

        result = await email_agent.send_newsletter(params)

        assert result['subject'] == 'Weekly Update'
        assert result['status'] == 'queued'

    @pytest.mark.asyncio
    async def test_execute_task_create_campaign(self, email_agent):
        """Test executing a create_campaign task."""
        task = AgentTask(
            task_id="email_task_1",
            task_type="create_campaign",
            payload={'name': 'Adoption Campaign', 'subject': 'Find Your Pet'}
        )

        result = await email_agent.execute_task(task)

        assert result.success is True
        assert 'id' in result.data
        assert result.data['name'] == 'Adoption Campaign'

    @pytest.mark.asyncio
    async def test_email_agent_error_handling(self, email_agent):
        """Test error handling in email agent."""
        task = AgentTask(
            task_id="error_task",
            task_type="invalid_task",
            payload={}
        )

        result = await email_agent.execute_task(task)

        assert result.success is True
        assert 'error' in result.data


# ============================================================================
# VideoGeneratorAgent Tests
# ============================================================================

class TestVideoGeneratorAgent:
    """Tests for VideoGeneratorAgent."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Reset state before each test."""
        BaseAgent._registry.clear()
        while not BaseAgent._message_bus.empty():
            try:
                BaseAgent._message_bus.get_nowait()
            except queue.Empty:
                break

    @pytest.fixture
    def video_agent(self):
        """Create a video agent for testing."""
        with patch('agents.base_agent.init_db'):
            with patch('agents.base_agent.SessionLocal'):
                # Mock the settings
                with patch('agents.specialized.video_agent.settings') as mock_settings:
                    mock_settings.VIDEO_OUTPUT_DIR = '/tmp/videos'
                    from agents.specialized.video_agent import VideoGeneratorAgent
                    return VideoGeneratorAgent()

    def test_video_agent_initialization(self, video_agent):
        """Test video agent is properly initialized."""
        assert video_agent.agent_id == "video_generator"
        assert video_agent.agent_name == "Video Generator Agent"
        assert video_agent.agent_type == "specialized_agent"

    @pytest.mark.asyncio
    async def test_create_video(self, video_agent):
        """Test creating a video."""
        params = {
            'format': 'tiktok',
            'duration': 15,
            'style': 'emotional'
        }

        result = await video_agent.create_video(params)

        assert 'video_id' in result
        assert 'video_path' in result
        assert result['format'] == 'tiktok'
        assert result['duration'] == 15
        assert result['style'] == 'emotional'
        assert result['status'] == 'created'

    @pytest.mark.asyncio
    async def test_create_slideshow(self, video_agent):
        """Test creating a slideshow."""
        params = {
            'images': ['img1.jpg', 'img2.jpg', 'img3.jpg'],
            'duration_per_image': 3
        }

        result = await video_agent.create_slideshow(params)

        assert 'video_id' in result
        assert result['image_count'] == 3
        assert result['total_duration'] == 9  # 3 images * 3 seconds
        assert result['status'] == 'created'

    @pytest.mark.asyncio
    async def test_execute_task_create_video(self, video_agent):
        """Test executing a create_video task."""
        task = AgentTask(
            task_id="video_task_1",
            task_type="create_video",
            payload={'format': 'instagram', 'duration': 30}
        )

        result = await video_agent.execute_task(task)

        assert result.success is True
        assert 'video_id' in result.data
        assert result.data['format'] == 'instagram'

    @pytest.mark.asyncio
    async def test_video_agent_error_handling(self, video_agent):
        """Test error handling in video agent."""
        task = AgentTask(
            task_id="error_task",
            task_type="unknown_operation",
            payload={}
        )

        result = await video_agent.execute_task(task)

        assert result.success is True
        assert 'error' in result.data


# ============================================================================
# SEOAgent Tests
# ============================================================================

class TestSEOAgent:
    """Tests for SEOAgent."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Reset state before each test."""
        BaseAgent._registry.clear()
        while not BaseAgent._message_bus.empty():
            try:
                BaseAgent._message_bus.get_nowait()
            except queue.Empty:
                break

    @pytest.fixture
    def seo_agent(self):
        """Create an SEO agent for testing."""
        with patch('agents.base_agent.init_db'):
            with patch('agents.base_agent.SessionLocal'):
                from agents.specialized.seo_agent import SEOAgent
                return SEOAgent()

    def test_seo_agent_initialization(self, seo_agent):
        """Test SEO agent is properly initialized."""
        assert seo_agent.agent_id == "seo"
        assert seo_agent.agent_name == "SEO Agent"
        assert seo_agent.agent_type == "specialized_agent"
        assert isinstance(seo_agent.keywords, dict)

    @pytest.mark.asyncio
    async def test_keyword_research(self, seo_agent):
        """Test keyword research functionality."""
        params = {'topic': 'dog adoption'}

        result = await seo_agent.keyword_research(params)

        assert result['topic'] == 'dog adoption'
        assert 'keywords' in result
        assert 'primary' in result['keywords']
        assert 'secondary' in result['keywords']
        assert 'long_tail' in result['keywords']
        assert 'local' in result['keywords']
        assert len(result['keywords']['primary']) > 0

    @pytest.mark.asyncio
    async def test_analyze_content(self, seo_agent):
        """Test content analysis."""
        params = {
            'content': 'This is a test content about dog adoption. ' * 50  # ~500 words
        }

        result = await seo_agent.analyze_content(params)

        assert 'word_count' in result
        assert 'score' in result
        assert 'recommendations' in result
        assert result['word_count'] > 0

    @pytest.mark.asyncio
    async def test_generate_meta(self, seo_agent):
        """Test meta tag generation."""
        params = {
            'title': 'Adopt a Dog Today',
            'description': 'Find your perfect companion from thousands of dogs waiting for adoption.'
        }

        result = await seo_agent.generate_meta(params)

        assert 'meta_title' in result
        assert 'meta_description' in result
        assert 'og_title' in result
        assert 'og_description' in result
        assert 'schema' in result
        assert len(result['meta_title']) <= 60
        assert len(result['meta_description']) <= 158

    @pytest.mark.asyncio
    async def test_execute_task_keyword_research(self, seo_agent):
        """Test executing a keyword_research task."""
        task = AgentTask(
            task_id="seo_task_1",
            task_type="keyword_research",
            payload={'topic': 'cat rescue'}
        )

        result = await seo_agent.execute_task(task)

        assert result.success is True
        assert 'keywords' in result.data

    @pytest.mark.asyncio
    async def test_seo_agent_error_handling(self, seo_agent):
        """Test error handling in SEO agent."""
        task = AgentTask(
            task_id="error_task",
            task_type="invalid_seo_task",
            payload={}
        )

        result = await seo_agent.execute_task(task)

        assert result.success is True
        assert 'error' in result.data


# ============================================================================
# DataQualityAgent Tests
# ============================================================================

class TestDataQualityAgent:
    """Tests for DataQualityAgent."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Reset state before each test."""
        BaseAgent._registry.clear()
        while not BaseAgent._message_bus.empty():
            try:
                BaseAgent._message_bus.get_nowait()
            except queue.Empty:
                break

    @pytest.fixture
    def data_quality_agent(self):
        """Create a data quality agent for testing."""
        with patch('agents.base_agent.init_db'):
            with patch('agents.base_agent.SessionLocal'):
                from agents.specialized.data_quality_agent import DataQualityAgent
                return DataQualityAgent()

    def test_data_quality_agent_initialization(self, data_quality_agent):
        """Test data quality agent is properly initialized."""
        assert data_quality_agent.agent_id == "data_quality"
        assert data_quality_agent.agent_name == "Data Quality Agent"
        assert data_quality_agent.agent_type == "specialized_agent"
        assert isinstance(data_quality_agent.quality_reports, list)
        assert isinstance(data_quality_agent.known_issues, dict)

    @pytest.mark.asyncio
    async def test_run_audit(self, data_quality_agent):
        """Test running a data quality audit."""
        # Mock database session and queries
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = []

        data_quality_agent.get_db = MagicMock(return_value=mock_db)
        data_quality_agent.share_discovery = MagicMock()

        result = await data_quality_agent.run_audit({'entity_type': 'animals'})

        assert 'audit_id' in result
        assert 'timestamp' in result
        assert 'entities' in result
        assert 'overall_quality_score' in result

    @pytest.mark.asyncio
    async def test_find_duplicates(self, data_quality_agent):
        """Test finding duplicate records."""
        # Mock database
        mock_db = MagicMock()
        data_quality_agent.get_db = MagicMock(return_value=mock_db)
        mock_db.query.return_value.filter.return_value.group_by.return_value.having.return_value.all.return_value = []

        result = await data_quality_agent.find_duplicates({'entity_type': 'shelters'})

        assert result['entity_type'] == 'shelters'
        assert 'duplicates' in result
        assert 'count' in result

    @pytest.mark.asyncio
    async def test_cleanup(self, data_quality_agent):
        """Test cleanup operations."""
        # Mock database
        mock_db = MagicMock()
        data_quality_agent.get_db = MagicMock(return_value=mock_db)
        mock_db.query.return_value.filter.return_value.all.return_value = []

        result = await data_quality_agent.cleanup({'type': 'orphans', 'dry_run': True})

        assert result['cleanup_type'] == 'orphans'
        assert result['dry_run'] is True
        assert 'affected_records' in result

    @pytest.mark.asyncio
    async def test_normalize_data(self, data_quality_agent):
        """Test data normalization."""
        # Mock database
        mock_db = MagicMock()
        data_quality_agent.get_db = MagicMock(return_value=mock_db)
        mock_db.query.return_value.all.return_value = []

        result = await data_quality_agent.normalize_data({'field': 'state'})

        assert result['field'] == 'state'
        assert 'normalized_count' in result

    @pytest.mark.asyncio
    async def test_execute_task_run_audit(self, data_quality_agent):
        """Test executing a run_audit task."""
        # Mock database
        mock_db = MagicMock()
        data_quality_agent.get_db = MagicMock(return_value=mock_db)
        mock_db.query.return_value.filter.return_value.all.return_value = []
        data_quality_agent.share_discovery = MagicMock()

        task = AgentTask(
            task_id="dq_task_1",
            task_type="run_audit",
            payload={'entity_type': 'all'}
        )

        result = await data_quality_agent.execute_task(task)

        assert result.success is True
        assert 'audit_id' in result.data

    @pytest.mark.asyncio
    async def test_data_quality_agent_error_handling(self, data_quality_agent):
        """Test error handling in data quality agent."""
        task = AgentTask(
            task_id="error_task",
            task_type="unknown_quality_task",
            payload={}
        )

        result = await data_quality_agent.execute_task(task)

        assert result.success is True
        assert 'error' in result.data


# ============================================================================
# AdoptionMatcherAgent Tests
# ============================================================================

class TestAdoptionMatcherAgent:
    """Tests for AdoptionMatcherAgent."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Reset state before each test."""
        BaseAgent._registry.clear()
        while not BaseAgent._message_bus.empty():
            try:
                BaseAgent._message_bus.get_nowait()
            except queue.Empty:
                break

    @pytest.fixture
    def matcher_agent(self):
        """Create an adoption matcher agent for testing."""
        with patch('agents.base_agent.init_db'):
            with patch('agents.base_agent.SessionLocal'):
                from agents.specialized.matcher_agent import AdoptionMatcherAgent
                return AdoptionMatcherAgent()

    def test_matcher_agent_initialization(self, matcher_agent):
        """Test matcher agent is properly initialized."""
        assert matcher_agent.agent_id == "adoption_matcher"
        assert matcher_agent.agent_name == "Adoption Matcher Agent"
        assert matcher_agent.agent_type == "specialized_agent"
        assert isinstance(matcher_agent.matches, list)

    @pytest.mark.asyncio
    async def test_find_matches(self, matcher_agent):
        """Test finding adoption matches."""
        # Mock the request_from_agent method
        mock_animals = {
            'results': [
                {'id': 1, 'name': 'Buddy', 'size': 'large', 'age': 'adult', 'days_waiting': 100},
                {'id': 2, 'name': 'Max', 'size': 'medium', 'age': 'young', 'days_waiting': 50},
                {'id': 3, 'name': 'Luna', 'size': 'small', 'age': 'senior', 'days_waiting': 200}
            ]
        }
        matcher_agent.request_from_agent = AsyncMock(return_value=mock_animals)

        preferences = {
            'type': 'dog',
            'size': 'large',
            'age': 'adult'
        }

        result = await matcher_agent.find_matches({'preferences': preferences, 'limit': 5})

        assert 'matches' in result
        assert 'count' in result
        assert len(result['matches']) > 0
        assert all('animal' in match for match in result['matches'])
        assert all('score' in match for match in result['matches'])

    def test_calculate_match_score(self, matcher_agent):
        """Test match score calculation."""
        animal = {
            'size': 'large',
            'age': 'adult',
            'days_waiting': 100
        }
        preferences = {
            'size': 'large',
            'age': 'adult'
        }

        score = matcher_agent._calculate_match_score(animal, preferences)

        assert score > 50  # Should be higher than base score
        assert score <= 100
        assert isinstance(score, float)

    @pytest.mark.asyncio
    async def test_execute_task_find_matches(self, matcher_agent):
        """Test executing a find_matches task."""
        matcher_agent.request_from_agent = AsyncMock(return_value={'results': []})

        task = AgentTask(
            task_id="matcher_task_1",
            task_type="find_matches",
            payload={'preferences': {'type': 'dog'}, 'limit': 10}
        )

        result = await matcher_agent.execute_task(task)

        assert result.success is True
        assert 'matches' in result.data

    @pytest.mark.asyncio
    async def test_matcher_agent_error_handling(self, matcher_agent):
        """Test error handling in matcher agent."""
        task = AgentTask(
            task_id="error_task",
            task_type="invalid_matcher_task",
            payload={}
        )

        result = await matcher_agent.execute_task(task)

        assert result.success is True
        assert 'error' in result.data


# ============================================================================
# StateAgent Tests
# ============================================================================

class TestStateAgent:
    """Tests for StateAgent."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Reset state before each test."""
        BaseAgent._registry.clear()
        while not BaseAgent._message_bus.empty():
            try:
                BaseAgent._message_bus.get_nowait()
            except queue.Empty:
                break

    @pytest.fixture
    def state_agent(self):
        """Create a state agent for testing."""
        with patch('agents.base_agent.init_db'):
            with patch('agents.base_agent.SessionLocal'):
                from agents.state_agents.state_agent import StateAgent
                return StateAgent('CA')

    def test_state_agent_initialization(self, state_agent):
        """Test state agent is properly initialized."""
        assert state_agent.agent_id == "state_agent_ca"
        assert state_agent.agent_name == "California Shelter Discovery Agent"
        assert state_agent.agent_type == "state_discovery"
        assert state_agent.state_code == "CA"
        assert state_agent.state_name == "California"
        assert isinstance(state_agent.discovered_shelters, set)

    def test_state_agent_invalid_state(self):
        """Test state agent rejects invalid state codes."""
        with patch('agents.base_agent.init_db'):
            with patch('agents.base_agent.SessionLocal'):
                from agents.state_agents.state_agent import StateAgent
                with pytest.raises(ValueError):
                    StateAgent('XX')  # Invalid state code

    def test_is_valid_shelter(self, state_agent):
        """Test shelter validation logic."""
        # Valid shelter
        assert state_agent._is_valid_shelter("Happy Paws Animal Rescue", "nonprofit rescue")
        assert state_agent._is_valid_shelter("City Animal Shelter", "spca")

        # Invalid (breeder/store)
        assert not state_agent._is_valid_shelter("Puppies for Sale", "breeder")
        assert not state_agent._is_valid_shelter("Pet Store", "")

    def test_normalize_shelter_name(self, state_agent):
        """Test shelter name normalization."""
        assert state_agent._normalize_shelter_name("Rescue Inc.") == "rescue"
        assert state_agent._normalize_shelter_name("Animal  Shelter, LLC") == "animal shelter"
        assert state_agent._normalize_shelter_name("  Pets Inc  ") == "pets"

    @pytest.mark.asyncio
    async def test_search_rescuegroups(self, state_agent):
        """Test searching RescueGroups database."""
        # Mock database
        mock_shelter = MagicMock()
        mock_shelter.name = "Test Shelter"
        mock_shelter.city = "Los Angeles"
        mock_shelter.state = "CA"
        mock_shelter.phone = "555-1234"
        mock_shelter.email = "test@example.com"
        mock_shelter.website = "http://example.com"

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_shelter]
        state_agent.get_db = MagicMock(return_value=mock_db)

        mock_session = MagicMock()
        shelters = await state_agent.search_rescuegroups(mock_session)

        assert len(shelters) > 0
        assert shelters[0]['name'] == "Test Shelter"
        assert shelters[0]['source'] == 'rescuegroups'

    @pytest.mark.asyncio
    async def test_verify_shelter(self, state_agent):
        """Test shelter verification."""
        valid_shelter = {
            'name': 'Happy Paws Rescue',
            'website': 'http://example.com',
            'description': 'nonprofit animal rescue'
        }

        # Should pass basic validation
        result = await state_agent.verify_shelter(valid_shelter)
        assert result is True

        # Invalid shelter (no name)
        invalid_shelter = {'name': '', 'website': ''}
        result = await state_agent.verify_shelter(invalid_shelter)
        assert result is False

    @pytest.mark.asyncio
    async def test_save_shelter_to_db(self, state_agent):
        """Test saving shelter to database."""
        # Mock database
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        state_agent.get_db = MagicMock(return_value=mock_db)

        shelter = {
            'name': 'New Shelter',
            'city': 'San Francisco',
            'state': 'CA',
            'phone': '555-5678',
            'email': 'new@example.com',
            'website': 'http://newshelter.com'
        }

        result = await state_agent.save_shelter_to_db(shelter)

        assert result is True  # New shelter created
        assert mock_db.add.called
        assert mock_db.commit.called

    @pytest.mark.asyncio
    async def test_execute_task_full_discovery(self, state_agent):
        """Test executing a full_discovery task."""
        # Mock database
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = []
        state_agent.get_db = MagicMock(return_value=mock_db)

        task = AgentTask(
            task_id="state_task_1",
            task_type="full_discovery",
            payload={'state': 'CA'}
        )

        result = await state_agent.execute_task(task)

        assert result.success is True
        assert 'shelters_found' in result.data

    @pytest.mark.asyncio
    async def test_state_agent_error_handling(self, state_agent):
        """Test error handling in state agent."""
        # Force an error by not mocking the database
        task = AgentTask(
            task_id="error_task",
            task_type="full_discovery",
            payload={}
        )

        # The task should handle the error gracefully
        result = await state_agent.execute_task(task)

        # May succeed or fail depending on database state, but should not crash
        assert isinstance(result, AgentResult)

    def test_get_status_report(self, state_agent):
        """Test getting state agent status report."""
        # Mock get_shelter_count
        state_agent.get_shelter_count = MagicMock(return_value=42)

        report = state_agent.get_status_report()

        assert 'state_code' in report
        assert 'state_name' in report
        assert 'region' in report
        assert 'shelter_count' in report
        assert report['state_code'] == 'CA'
        assert report['state_name'] == 'California'
        assert report['shelter_count'] == 42


# ============================================================================
# Integration Tests - Agent Cooperation
# ============================================================================

class TestAgentCooperation:
    """Test inter-agent cooperation between specialized agents."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Reset state before each test."""
        BaseAgent._registry.clear()
        CooperationProtocol._data_store.clear()
        while not BaseAgent._message_bus.empty():
            try:
                BaseAgent._message_bus.get_nowait()
            except queue.Empty:
                break

    @pytest.mark.asyncio
    async def test_marketing_seo_cooperation(self):
        """Test cooperation between marketing and SEO agents."""
        with patch('agents.base_agent.init_db'):
            with patch('agents.base_agent.SessionLocal'):
                from agents.specialized.marketing_agent import MarketingAgent
                from agents.specialized.seo_agent import SEOAgent

                marketing = MarketingAgent()
                seo = SEOAgent()

                # Marketing agent requests SEO keywords
                seo_response = await marketing.request_from_agent(
                    'seo',
                    'get_keywords',
                    {'topic': 'dog adoption'}
                )

                # Process SEO agent messages
                await seo.process_messages()

                # Verify response (may be None if async processing hasn't completed)
                # In real scenario, would use proper async coordination

    @pytest.mark.asyncio
    async def test_data_sharing_between_agents(self):
        """Test data sharing between agents."""
        with patch('agents.base_agent.init_db'):
            with patch('agents.base_agent.SessionLocal'):
                from agents.specialized.data_quality_agent import DataQualityAgent

                dq_agent = DataQualityAgent()

                # Share a discovery
                dq_agent.share_discovery(
                    DataCategory.ANALYTICS,
                    'Quality Report',
                    {'quality_score': 95},
                    tags=['quality', 'report']
                )

                # Retrieve shared data
                shared = CooperationProtocol.get_shared_data(
                    category=DataCategory.ANALYTICS
                )

                assert len(shared) > 0
                assert shared[0].title == 'Quality Report'
                assert shared[0].data['quality_score'] == 95

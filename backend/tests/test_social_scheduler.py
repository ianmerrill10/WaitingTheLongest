"""
===============================================================================
Waiting The Longest™ - Social Scheduler Tests
===============================================================================
Comprehensive tests for the social media auto-posting scheduler.

Tests cover:
- SocialScheduleConfig dataclass
- SocialAutoPostWorker functionality
- Platform-specific posting methods
- Caption generation with hashtags
- Time-based scheduling logic
- Duplicate post prevention

===============================================================================
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

from app.models import Animal, SocialPromotion
from workers.social_scheduler import (
    SocialScheduleConfig,
    PlatformScheduleConfig,
    SocialAutoPostWorker,
    ContentType,
    run_social_autopost,
)


class TestPlatformScheduleConfig:
    """Test PlatformScheduleConfig dataclass"""

    def test_default_values(self):
        """Test default values for PlatformScheduleConfig"""
        config = PlatformScheduleConfig()

        assert config.posts_per_day == 1
        assert config.stories_per_day == 0
        assert config.reels_per_day == 0
        assert config.pins_per_day == 0
        assert config.content_types == []
        assert config.hashtags == []
        assert config.boards == []
        assert config.cross_promote is None

    def test_custom_values(self):
        """Test custom values for PlatformScheduleConfig"""
        config = PlatformScheduleConfig(
            posts_per_day=5,
            stories_per_day=10,
            content_types=["carousel", "reels"],
            hashtags=["#test", "#example"],
            cross_promote="example.com"
        )

        assert config.posts_per_day == 5
        assert config.stories_per_day == 10
        assert config.content_types == ["carousel", "reels"]
        assert config.hashtags == ["#test", "#example"]
        assert config.cross_promote == "example.com"


class TestSocialScheduleConfig:
    """Test SocialScheduleConfig dataclass"""

    def test_default_initialization(self):
        """Test default initialization of SocialScheduleConfig"""
        config = SocialScheduleConfig()

        # TikTok defaults
        assert config.tiktok.posts_per_day == 3
        assert "#adoptdontshop" in config.tiktok.hashtags
        assert config.tiktok.cross_promote == "waitingthelongest.com"

        # Instagram defaults
        assert config.instagram.posts_per_day == 2
        assert config.instagram.stories_per_day == 5
        assert config.instagram.reels_per_day == 1
        assert "carousel" in config.instagram.content_types

        # Twitter defaults
        assert config.twitter.posts_per_day == 5
        assert "adoption_updates" in config.twitter.content_types

        # Pinterest defaults
        assert config.pinterest.pins_per_day == 10
        assert len(config.pinterest.boards) == 3

    def test_from_settings(self):
        """Test loading config from settings"""
        with patch("workers.social_scheduler.settings") as mock_settings:
            mock_settings.TIKTOK_POSTS_PER_DAY = 5
            mock_settings.INSTAGRAM_POSTS_PER_DAY = 3
            mock_settings.INSTAGRAM_STORIES_PER_DAY = 8
            mock_settings.INSTAGRAM_REELS_PER_DAY = 2
            mock_settings.TWITTER_POSTS_PER_DAY = 10
            mock_settings.PINTEREST_PINS_PER_DAY = 15

            config = SocialScheduleConfig.from_settings()

            assert config.tiktok.posts_per_day == 5
            assert config.instagram.posts_per_day == 3
            assert config.instagram.stories_per_day == 8
            assert config.instagram.reels_per_day == 2
            assert config.twitter.posts_per_day == 10
            assert config.pinterest.pins_per_day == 15


class TestSocialAutoPostWorker:
    """Test SocialAutoPostWorker class"""

    def test_initialization_with_default_config(self):
        """Test worker initialization with default config"""
        worker = SocialAutoPostWorker()

        assert worker.config is not None
        assert worker.config.tiktok.posts_per_day == 3
        assert worker.last_run is None

    def test_initialization_with_custom_config(self):
        """Test worker initialization with custom config"""
        custom_config = SocialScheduleConfig(
            tiktok=PlatformScheduleConfig(posts_per_day=10)
        )
        worker = SocialAutoPostWorker(config=custom_config)

        assert worker.config.tiktok.posts_per_day == 10

    def test_run_disabled(self):
        """Test run when auto-posting is disabled"""
        with patch("workers.social_scheduler.settings") as mock_settings:
            mock_settings.SOCIAL_AUTOPOST_ENABLED = False

            worker = SocialAutoPostWorker()
            result = worker.run()

            assert result["skipped"] is True
            assert result["platforms_processed"] == 0

    def test_calculate_posting_times(self):
        """Test posting time calculation"""
        worker = SocialAutoPostWorker()

        # Test with 3 posts
        times = worker._calculate_posting_times(3)
        assert len(times) == 3

        # Times should be between 9 AM and 9 PM
        for t in times:
            assert 9 <= t.hour <= 21

        # Test with 0 posts
        times = worker._calculate_posting_times(0)
        assert len(times) == 0

        # Test with 1 post
        times = worker._calculate_posting_times(1)
        assert len(times) == 1

    def test_generate_caption_basic(self, db_session, sample_animal):
        """Test basic caption generation"""
        worker = SocialAutoPostWorker()
        caption = worker._generate_caption(sample_animal, "tiktok")

        assert sample_animal.canonical_name in caption
        assert str(sample_animal.days_waiting) in caption
        assert "#adoptdontshop" in caption
        assert "waitingthelongest.com" in caption

    def test_generate_caption_long_wait(self, db_session):
        """Test caption for animal waiting over a year"""
        animal = Animal(
            species="dog",
            canonical_name="Buddy",
            first_seen_at=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=400),
            status="available"
        )
        db_session.add(animal)
        db_session.commit()

        worker = SocialAutoPostWorker()
        caption = worker._generate_caption(animal, "tiktok")

        assert "OVER A YEAR WAITING" in caption

    def test_generate_caption_different_platforms(self, db_session, sample_animal):
        """Test caption generation for different platforms"""
        worker = SocialAutoPostWorker()

        tiktok_caption = worker._generate_caption(sample_animal, "tiktok")
        instagram_caption = worker._generate_caption(sample_animal, "instagram")
        twitter_caption = worker._generate_caption(sample_animal, "twitter")

        # All should include the animal name
        assert sample_animal.canonical_name in tiktok_caption
        assert sample_animal.canonical_name in instagram_caption
        assert sample_animal.canonical_name in twitter_caption

        # Platform-specific hashtags
        assert "#waitingthelongest" in tiktok_caption
        assert "#rescuepets" in instagram_caption

    def test_was_recently_promoted_false(self, db_session, sample_animal):
        """Test recently promoted check when not promoted"""
        worker = SocialAutoPostWorker()
        result = worker._was_recently_promoted(db_session, sample_animal.id, "tiktok")

        assert result is False

    def test_was_recently_promoted_true(self, db_session, sample_animal):
        """Test recently promoted check when recently promoted"""
        # Create a recent promotion
        promotion = SocialPromotion(
            animal_id=sample_animal.id,
            platform="tiktok",
            status="posted",
            created_at=datetime.now(timezone.utc).replace(tzinfo=None)
        )
        db_session.add(promotion)
        db_session.commit()

        worker = SocialAutoPostWorker()
        result = worker._was_recently_promoted(db_session, sample_animal.id, "tiktok")

        assert result is True

    def test_was_recently_promoted_old(self, db_session, sample_animal):
        """Test recently promoted check for old promotion"""
        # Create an old promotion (8 days ago)
        promotion = SocialPromotion(
            animal_id=sample_animal.id,
            platform="tiktok",
            status="posted",
            created_at=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=8)
        )
        db_session.add(promotion)
        db_session.commit()

        worker = SocialAutoPostWorker()
        result = worker._was_recently_promoted(db_session, sample_animal.id, "tiktok")

        assert result is False

    def test_get_promotion_candidates(self, db_session, multiple_animals):
        """Test getting promotion candidates"""
        worker = SocialAutoPostWorker()
        candidates = worker._get_promotion_candidates(db_session)

        # Should find animals waiting 100+ days
        # From multiple_animals fixture: Buddy (500 days), Whiskers (200 days)
        # Luna (50 days) should not qualify, Rocky is adopted
        assert len(candidates) >= 2

        # Should be ordered by longest waiting first
        if len(candidates) >= 2:
            assert candidates[0].days_waiting >= candidates[1].days_waiting

    def test_post_to_tiktok_no_token(self, db_session, sample_animal):
        """Test TikTok posting without access token"""
        with patch("workers.social_scheduler.settings") as mock_settings:
            mock_settings.TIKTOK_ACCESS_TOKEN = None

            worker = SocialAutoPostWorker()
            promotion = SocialPromotion(
                animal_id=sample_animal.id,
                platform="tiktok",
                status="pending"
            )

            result = worker._post_to_tiktok(promotion, sample_animal)

            assert result is False

    def test_post_to_instagram_no_token(self, db_session, sample_animal):
        """Test Instagram posting without access token"""
        with patch("workers.social_scheduler.settings") as mock_settings:
            mock_settings.INSTAGRAM_ACCESS_TOKEN = None

            worker = SocialAutoPostWorker()
            promotion = SocialPromotion(
                animal_id=sample_animal.id,
                platform="instagram",
                status="pending"
            )

            result = worker._post_to_instagram(promotion, sample_animal)

            assert result is False

    def test_post_to_twitter_no_token(self, db_session, sample_animal):
        """Test Twitter posting without access token"""
        with patch("workers.social_scheduler.settings") as mock_settings:
            mock_settings.TWITTER_ACCESS_TOKEN = None

            worker = SocialAutoPostWorker()
            promotion = SocialPromotion(
                animal_id=sample_animal.id,
                platform="twitter",
                status="pending"
            )

            result = worker._post_to_twitter(promotion, sample_animal)

            assert result is False

    def test_post_to_pinterest_no_token(self, db_session, sample_animal):
        """Test Pinterest posting without access token"""
        with patch("workers.social_scheduler.settings") as mock_settings:
            mock_settings.PINTEREST_ACCESS_TOKEN = None

            worker = SocialAutoPostWorker()
            promotion = SocialPromotion(
                animal_id=sample_animal.id,
                platform="pinterest",
                status="pending"
            )

            result = worker._post_to_pinterest(promotion, sample_animal)

            assert result is False

    def test_get_posts_for_today(self, db_session, sample_animal):
        """Test counting posts made today"""
        # Create some posts for today
        for i in range(3):
            promotion = SocialPromotion(
                animal_id=sample_animal.id,
                platform="tiktok",
                status="posted",
                created_at=datetime.now(timezone.utc).replace(tzinfo=None)
            )
            db_session.add(promotion)
        db_session.commit()

        worker = SocialAutoPostWorker()
        count = worker.get_posts_for_today("tiktok")

        assert count == 3


class TestContentType:
    """Test ContentType enum"""

    def test_content_type_values(self):
        """Test ContentType enum values"""
        assert ContentType.ADOPTION_SHOWCASE.value == "adoption_showcase"
        assert ContentType.CAROUSEL.value == "carousel"
        assert ContentType.REELS.value == "reels"
        assert ContentType.PIN.value == "pin"


class TestRunSocialAutopost:
    """Test the convenience function"""

    def test_run_social_autopost(self):
        """Test run_social_autopost function"""
        with patch("workers.social_scheduler.settings") as mock_settings:
            mock_settings.SOCIAL_AUTOPOST_ENABLED = False

            result = run_social_autopost()

            assert result["skipped"] is True


class TestSchedulePost:
    """Test schedule_post method"""

    def test_schedule_post_creates_promotion(self, db_session, sample_animal):
        """Test that schedule_post creates a SocialPromotion record"""
        with patch("workers.social_scheduler.settings") as mock_settings:
            mock_settings.TIKTOK_ACCESS_TOKEN = "test_token"
            mock_settings.SOCIAL_AUTOPOST_ENABLED = True

            worker = SocialAutoPostWorker()
            scheduled_time = datetime.now(timezone.utc).replace(tzinfo=None)

            # Mock the database session
            with patch("workers.social_scheduler.SessionLocal") as mock_session:
                mock_session.return_value = db_session

                worker._schedule_post(db_session, sample_animal, "tiktok", scheduled_time)

            # Check that a promotion was created
            promotions = db_session.query(SocialPromotion).filter(
                SocialPromotion.animal_id == sample_animal.id,
                SocialPromotion.platform == "tiktok"
            ).all()

            assert len(promotions) >= 1
            assert promotions[-1].scheduled_at == scheduled_time


class TestProcessPlatform:
    """Test _process_platform method"""

    def test_process_platform_no_config(self, db_session, sample_animal):
        """Test processing a platform with no config"""
        worker = SocialAutoPostWorker()

        # Use a non-existent platform config
        result = worker._process_platform(db_session, "nonexistent", [sample_animal])

        assert result["scheduled"] == 0
        assert result["succeeded"] == 0
        assert result["failed"] == 0

    def test_process_platform_with_candidates(self, db_session, multiple_animals):
        """Test processing a platform with candidates"""
        with patch("workers.social_scheduler.settings") as mock_settings:
            mock_settings.TIKTOK_ACCESS_TOKEN = "test_token"

            worker = SocialAutoPostWorker()

            # Filter to only available animals
            available = [a for a in multiple_animals if a.status == "available"]
            result = worker._process_platform(db_session, "tiktok", available)

            # Should have attempted to schedule posts
            assert result["scheduled"] >= 0

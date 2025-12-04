"""
===============================================================================
Waiting The Longest™ - Social Media Auto-Posting Scheduler
===============================================================================
Purpose: Automated social media posting system that schedules and posts
         content across multiple platforms (TikTok, Instagram, Twitter,
         Pinterest) based on configurable schedules.

Author: Waiting The Longest™ Development Team
Last Updated: 2025-01-15
Dependencies: logging, datetime, dataclasses
Related Files: scheduler.py, video_generator.py, config.py, models.py

IMPORTANT: Any changes to this file MUST be documented in OWNERS_MANUAL.md

Features:
- Multi-platform posting (TikTok, Instagram, Twitter, Pinterest)
- Configurable posting schedules per platform
- Platform-specific caption and hashtag generation
- Time-based scheduling to spread posts throughout the day
- Duplicate post prevention via SocialPromotion tracking

Run manually:
    python -m backend.workers.social_scheduler

Or integrate with scheduler.py for automated runs.
===============================================================================
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from enum import Enum

try:
    from app.database import SessionLocal
    from app.models import Animal, SocialPromotion
    from app.config import settings
except ImportError:
    from ..app.database import SessionLocal
    from ..app.models import Animal, SocialPromotion
    from ..app.config import settings

logger = logging.getLogger(__name__)


class ContentType(str, Enum):
    """Types of content that can be posted for pet adoption"""
    ADOPTION_SHOWCASE = "adoption_showcase"
    SUCCESS_STORY = "success_story"
    PET_PROFILE = "pet_profile"
    TRENDING_SOUNDS = "trending_sounds"
    CAROUSEL = "carousel"
    REELS = "reels"
    STORIES = "stories"
    ADOPTION_UPDATES = "adoption_updates"
    NEW_ARRIVALS = "new_arrivals"
    ENGAGEMENT_THREADS = "engagement_threads"
    PIN = "pin"


@dataclass
class PlatformScheduleConfig:
    """Configuration for a single platform's posting schedule"""
    posts_per_day: int = 1
    stories_per_day: int = 0
    reels_per_day: int = 0
    pins_per_day: int = 0
    content_types: List[str] = field(default_factory=list)
    hashtags: List[str] = field(default_factory=list)
    boards: List[str] = field(default_factory=list)
    cross_promote: Optional[str] = None


@dataclass
class SocialScheduleConfig:
    """
    Complete social media posting schedule configuration.

    Holds configurations for all supported platforms including:
    - Posts per day
    - Content types
    - Platform-specific hashtags
    - Cross-promotion URLs
    """
    tiktok: PlatformScheduleConfig = field(default_factory=lambda: PlatformScheduleConfig(
        posts_per_day=3,
        content_types=["adoption_showcase", "success_story", "pet_profile", "trending_sounds"],
        hashtags=["#adoptdontshop", "#rescuedog", "#rescuecat", "#shelterdog", "#waitingthelongest"],
        cross_promote="waitingthelongest.com"
    ))
    instagram: PlatformScheduleConfig = field(default_factory=lambda: PlatformScheduleConfig(
        posts_per_day=2,
        stories_per_day=5,
        reels_per_day=1,
        content_types=["carousel", "reels", "stories"],
        hashtags=["#adoptdontshop", "#rescuedog", "#sheltercat", "#rescuepets"]
    ))
    twitter: PlatformScheduleConfig = field(default_factory=lambda: PlatformScheduleConfig(
        posts_per_day=5,
        content_types=["adoption_updates", "new_arrivals", "engagement_threads"],
        hashtags=["#adoptdontshop", "#rescuepets"]
    ))
    pinterest: PlatformScheduleConfig = field(default_factory=lambda: PlatformScheduleConfig(
        pins_per_day=10,
        boards=["Adopt Don't Shop", "Long Wait Pets", "Success Stories"],
        hashtags=["#adoptdontshop", "#rescuedog", "#rescuecat"]
    ))

    @classmethod
    def from_settings(cls) -> "SocialScheduleConfig":
        """Create a SocialScheduleConfig from application settings"""
        return cls(
            tiktok=PlatformScheduleConfig(
                posts_per_day=settings.TIKTOK_POSTS_PER_DAY,
                content_types=["adoption_showcase", "success_story", "pet_profile", "trending_sounds"],
                hashtags=["#adoptdontshop", "#rescuedog", "#rescuecat", "#shelterdog", "#waitingthelongest"],
                cross_promote="waitingthelongest.com"
            ),
            instagram=PlatformScheduleConfig(
                posts_per_day=settings.INSTAGRAM_POSTS_PER_DAY,
                stories_per_day=settings.INSTAGRAM_STORIES_PER_DAY,
                reels_per_day=settings.INSTAGRAM_REELS_PER_DAY,
                content_types=["carousel", "reels", "stories"],
                hashtags=["#adoptdontshop", "#rescuedog", "#sheltercat", "#rescuepets"]
            ),
            twitter=PlatformScheduleConfig(
                posts_per_day=settings.TWITTER_POSTS_PER_DAY,
                content_types=["adoption_updates", "new_arrivals", "engagement_threads"],
                hashtags=["#adoptdontshop", "#rescuepets"]
            ),
            pinterest=PlatformScheduleConfig(
                pins_per_day=settings.PINTEREST_PINS_PER_DAY,
                boards=["Adopt Don't Shop", "Long Wait Pets", "Success Stories"],
                hashtags=["#adoptdontshop", "#rescuedog", "#rescuecat"]
            )
        )


class SocialAutoPostWorker:
    """
    Worker for automated social media posting across multiple platforms.

    Handles scheduling and posting content to TikTok, Instagram, Twitter,
    and Pinterest based on configured schedules. Tracks posted content
    to avoid duplicates and spreads posts throughout the day.
    """

    PROMOTION_COOLDOWN_DAYS = 7  # Days between promotions for same animal on same platform
    MIN_DAYS_WAITING = 100  # Minimum days waiting to be promoted

    def __init__(self, config: Optional[SocialScheduleConfig] = None):
        """
        Initialize the SocialAutoPostWorker.

        Args:
            config: Optional SocialScheduleConfig. If not provided,
                   loads from application settings.
        """
        self.config = config or SocialScheduleConfig.from_settings()
        self.last_run: Optional[datetime] = None

    def run(self) -> Dict[str, Any]:
        """
        Execute the social auto-posting workflow.

        Processes all platforms and posts content according to their schedules.

        Returns:
            Dictionary with statistics about the posting run:
            - platforms_processed: Number of platforms attempted
            - posts_scheduled: Total posts scheduled
            - posts_succeeded: Successful posts
            - posts_failed: Failed posts
            - errors: List of error messages
        """
        if not settings.SOCIAL_AUTOPOST_ENABLED:
            logger.info("Social auto-posting is disabled. Skipping.")
            return {
                "platforms_processed": 0,
                "posts_scheduled": 0,
                "posts_succeeded": 0,
                "posts_failed": 0,
                "errors": [],
                "skipped": True
            }

        logger.info("Starting social auto-posting workflow...")

        stats = {
            "platforms_processed": 0,
            "posts_scheduled": 0,
            "posts_succeeded": 0,
            "posts_failed": 0,
            "errors": []
        }

        db = SessionLocal()
        try:
            # Get candidates for promotion (animals waiting 100+ days)
            candidates = self._get_promotion_candidates(db)
            logger.info(f"Found {len(candidates)} promotion candidates")

            if not candidates:
                logger.info("No promotion candidates available")
                return stats

            # Process each platform
            for platform in ["tiktok", "instagram", "twitter", "pinterest"]:
                try:
                    platform_stats = self._process_platform(db, platform, candidates)
                    stats["platforms_processed"] += 1
                    stats["posts_scheduled"] += platform_stats.get("scheduled", 0)
                    stats["posts_succeeded"] += platform_stats.get("succeeded", 0)
                    stats["posts_failed"] += platform_stats.get("failed", 0)
                except Exception as e:
                    logger.error(f"Error processing platform {platform}: {e}")
                    stats["errors"].append(f"{platform}: {str(e)}")

            self.last_run = datetime.now(timezone.utc).replace(tzinfo=None)
            logger.info(f"Social auto-posting complete: {stats}")

        except Exception as e:
            logger.error(f"Social auto-posting failed: {e}")
            stats["errors"].append(str(e))

        finally:
            db.close()

        return stats

    def _get_promotion_candidates(self, db) -> List[Animal]:
        """
        Get animals that are candidates for promotion.

        Finds animals that:
        - Are available for adoption
        - Have been waiting at least MIN_DAYS_WAITING days
        - Ordered by longest waiting first

        Args:
            db: Database session

        Returns:
            List of Animal objects eligible for promotion
        """
        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(
            days=self.MIN_DAYS_WAITING
        )

        candidates = db.query(Animal).filter(
            Animal.status == "available",
            Animal.first_seen_at <= cutoff
        ).order_by(
            Animal.first_seen_at.asc()  # Longest waiting first
        ).limit(50).all()

        return candidates

    def _process_platform(
        self,
        db,
        platform: str,
        candidates: List[Animal]
    ) -> Dict[str, int]:
        """
        Process posting for a specific platform.

        Args:
            db: Database session
            platform: Platform name (tiktok, instagram, twitter, pinterest)
            candidates: List of Animal objects to potentially promote

        Returns:
            Dictionary with scheduled, succeeded, and failed counts
        """
        platform_config = getattr(self.config, platform, None)
        if not platform_config:
            logger.warning(f"No configuration for platform: {platform}")
            return {"scheduled": 0, "succeeded": 0, "failed": 0}

        # Determine how many posts to make
        posts_to_make = platform_config.posts_per_day
        if platform == "pinterest":
            posts_to_make = platform_config.pins_per_day

        stats = {"scheduled": 0, "succeeded": 0, "failed": 0}

        # Calculate optimal posting times for today
        posting_times = self._calculate_posting_times(posts_to_make)

        for i, scheduled_time in enumerate(posting_times):
            if i >= len(candidates):
                break

            animal = candidates[i]

            # Check if already promoted recently on this platform
            if self._was_recently_promoted(db, animal.id, platform):
                continue

            try:
                # Schedule the post
                success = self._schedule_post(db, animal, platform, scheduled_time)
                stats["scheduled"] += 1

                if success:
                    stats["succeeded"] += 1
                else:
                    stats["failed"] += 1

            except Exception as e:
                logger.error(f"Failed to schedule post for animal {animal.id} on {platform}: {e}")
                stats["failed"] += 1

        return stats

    def _was_recently_promoted(self, db, animal_id: int, platform: str) -> bool:
        """
        Check if an animal was recently promoted on a platform.

        Args:
            db: Database session
            animal_id: ID of the animal
            platform: Platform name

        Returns:
            True if promoted within PROMOTION_COOLDOWN_DAYS, False otherwise
        """
        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(
            days=self.PROMOTION_COOLDOWN_DAYS
        )

        recent = db.query(SocialPromotion).filter(
            SocialPromotion.animal_id == animal_id,
            SocialPromotion.platform == platform,
            SocialPromotion.created_at > cutoff
        ).first()

        return recent is not None

    def _calculate_posting_times(self, num_posts: int) -> List[datetime]:
        """
        Calculate optimal posting times spread throughout the day.

        Spreads posts evenly between 9 AM and 9 PM local time.

        Args:
            num_posts: Number of posts to schedule

        Returns:
            List of datetime objects for scheduled posting times
        """
        if num_posts <= 0:
            return []

        today = datetime.now(timezone.utc).replace(tzinfo=None)
        start_hour = 9  # 9 AM
        end_hour = 21  # 9 PM
        hours_range = end_hour - start_hour

        posting_times = []
        interval = hours_range / max(num_posts, 1)

        for i in range(num_posts):
            post_hour = start_hour + (i * interval)
            post_time = today.replace(
                hour=int(post_hour),
                minute=int((post_hour % 1) * 60),
                second=0,
                microsecond=0
            )
            posting_times.append(post_time)

        return posting_times

    def _schedule_post(
        self,
        db,
        animal: Animal,
        platform: str,
        scheduled_time: datetime
    ) -> bool:
        """
        Schedule a post for an animal on a platform.

        Creates a SocialPromotion record and attempts to post via
        platform-specific methods.

        Args:
            db: Database session
            animal: Animal to promote
            platform: Target platform
            scheduled_time: Scheduled posting time

        Returns:
            True if successfully scheduled/posted, False otherwise
        """
        # Generate caption with hashtags
        caption = self._generate_caption(animal, platform)

        # Create promotion record
        promotion = SocialPromotion(
            animal_id=animal.id,
            platform=platform,
            status="pending",
            caption=caption,
            scheduled_at=scheduled_time,
            created_at=datetime.now(timezone.utc).replace(tzinfo=None)
        )
        db.add(promotion)
        db.commit()

        # Attempt to post via platform API
        try:
            success = False
            if platform == "tiktok":
                success = self._post_to_tiktok(promotion, animal)
            elif platform == "instagram":
                success = self._post_to_instagram(promotion, animal)
            elif platform == "twitter":
                success = self._post_to_twitter(promotion, animal)
            elif platform == "pinterest":
                success = self._post_to_pinterest(promotion, animal)

            if success:
                promotion.status = "posted"
                promotion.posted_at = datetime.now(timezone.utc).replace(tzinfo=None)
            else:
                promotion.status = "failed"

            db.commit()
            return success

        except Exception as e:
            logger.error(f"Failed to post to {platform}: {e}")
            promotion.status = "failed"
            db.commit()
            return False

    def _generate_caption(self, animal: Animal, platform: str) -> str:
        """
        Generate a caption with platform-appropriate hashtags.

        Creates an emotional hook caption highlighting the animal's
        wait time and adds platform-specific hashtags.

        Args:
            animal: Animal to generate caption for
            platform: Target platform

        Returns:
            Generated caption string
        """
        name = animal.canonical_name or "This sweet pet"
        days = animal.days_waiting
        breed = animal.breed_primary or animal.species

        # Emotional hook
        hooks = [
            f"After {days} days, {name} is still waiting for a forever home... 💔",
            f"🐾 {days} DAYS WAITING 🐾\n{name} needs YOU!",
            f"Will you be the one to end {name}'s {days}-day wait? ❤️",
            f"Meet {name} - a {breed} waiting {days} days for love 🏠",
        ]

        # Select hook based on days waiting
        if days >= 365:
            caption = f"🚨 OVER A YEAR WAITING 🚨\n{name} has been waiting {days} days. Can you help?"
        elif days >= 200:
            caption = hooks[0]
        elif days >= 100:
            caption = hooks[1]
        else:
            caption = hooks[3]

        # Add platform-specific hashtags
        platform_config = getattr(self.config, platform, None)
        if platform_config and platform_config.hashtags:
            hashtags = " ".join(platform_config.hashtags[:5])  # Limit hashtags
            caption = f"{caption}\n\n{hashtags}"

        # Add cross-promotion if configured
        if platform_config and platform_config.cross_promote:
            caption = f"{caption}\n\n🔗 {platform_config.cross_promote}"

        return caption

    def _post_to_tiktok(self, promotion: SocialPromotion, animal: Animal) -> bool:
        """
        Post content to TikTok.

        Uses TikTok Content Posting API to upload video and caption.
        Returns False when API is not configured to prevent false positive metrics.

        Args:
            promotion: SocialPromotion record
            animal: Animal being promoted

        Returns:
            True if posted successfully, False otherwise
        """
        if not settings.TIKTOK_ACCESS_TOKEN:
            logger.warning("TikTok access token not configured. Skipping TikTok post.")
            return False

        try:
            # Generate video if not already created
            if not promotion.video_path:
                try:
                    from tools.video_generator import generate_animal_video
                except ImportError:
                    from ..tools.video_generator import generate_animal_video

                db = SessionLocal()
                try:
                    video_path = generate_animal_video(db, animal.id)
                finally:
                    db.close()

                if video_path:
                    promotion.video_path = video_path
                else:
                    logger.warning(f"Failed to generate video for animal {animal.id}")
                    return False

            # TODO: Implement actual TikTok API integration when ready
            # TikTok Content Posting API requires app approval
            # For now, mark as pending until API integration is complete
            logger.info(f"TikTok post prepared for animal {animal.id}: {promotion.caption[:50]}...")
            logger.warning("TikTok API integration not yet implemented - post marked as pending")
            return False

        except Exception as e:
            logger.error(f"TikTok posting failed: {e}")
            return False

    def _post_to_instagram(self, promotion: SocialPromotion, animal: Animal) -> bool:
        """
        Post content to Instagram.

        Uses Instagram Graph API for feed posts/reels.
        Returns False when API is not configured to prevent false positive metrics.

        Args:
            promotion: SocialPromotion record
            animal: Animal being promoted

        Returns:
            True if posted successfully, False otherwise
        """
        if not settings.INSTAGRAM_ACCESS_TOKEN:
            logger.warning("Instagram access token not configured. Skipping Instagram post.")
            return False

        try:
            # TODO: Implement actual Instagram Graph API integration when ready
            # Requires Facebook Business account and app approval
            logger.info(f"Instagram post prepared for animal {animal.id}: {promotion.caption[:50]}...")
            logger.warning("Instagram API integration not yet implemented - post marked as pending")
            return False

        except Exception as e:
            logger.error(f"Instagram posting failed: {e}")
            return False

    def _post_to_twitter(self, promotion: SocialPromotion, animal: Animal) -> bool:
        """
        Post content to Twitter/X.

        Uses Twitter API v2 for posting tweets.
        Returns False when API is not configured to prevent false positive metrics.

        Args:
            promotion: SocialPromotion record
            animal: Animal being promoted

        Returns:
            True if posted successfully, False otherwise
        """
        if not settings.TWITTER_ACCESS_TOKEN:
            logger.warning("Twitter access token not configured. Skipping Twitter post.")
            return False

        try:
            # TODO: Implement actual Twitter API v2 integration when ready
            # Requires Twitter Developer account with elevated access
            logger.info(f"Twitter post prepared for animal {animal.id}: {promotion.caption[:50]}...")
            logger.warning("Twitter API integration not yet implemented - post marked as pending")
            return False

        except Exception as e:
            logger.error(f"Twitter posting failed: {e}")
            return False

    def _post_to_pinterest(self, promotion: SocialPromotion, animal: Animal) -> bool:
        """
        Post content to Pinterest.

        Creates a pin on configured boards.
        Returns False when API is not configured to prevent false positive metrics.

        Args:
            promotion: SocialPromotion record
            animal: Animal being promoted

        Returns:
            True if posted successfully, False otherwise
        """
        if not settings.PINTEREST_ACCESS_TOKEN:
            logger.warning("Pinterest access token not configured. Skipping Pinterest post.")
            return False

        try:
            # TODO: Implement actual Pinterest API integration when ready
            # Requires Pinterest Business account and app approval
            logger.info(f"Pinterest pin prepared for animal {animal.id}: {promotion.caption[:50]}...")
            logger.warning("Pinterest API integration not yet implemented - post marked as pending")
            return False

        except Exception as e:
            logger.error(f"Pinterest posting failed: {e}")
            return False

    def get_posts_for_today(self, platform: str) -> int:
        """
        Get the number of posts already made today for a platform.

        Args:
            platform: Platform name

        Returns:
            Count of posts made today
        """
        db = SessionLocal()
        try:
            today_start = datetime.now(timezone.utc).replace(
                tzinfo=None, hour=0, minute=0, second=0, microsecond=0
            )

            count = db.query(SocialPromotion).filter(
                SocialPromotion.platform == platform,
                SocialPromotion.created_at >= today_start,
                SocialPromotion.status == "posted"
            ).count()

            return count
        finally:
            db.close()


def run_social_autopost():
    """
    Convenience function to run the social auto-posting worker.

    Creates a worker instance and executes the posting workflow.
    """
    worker = SocialAutoPostWorker()
    return worker.run()


if __name__ == "__main__":
    # Configure logging for standalone execution
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    run_social_autopost()

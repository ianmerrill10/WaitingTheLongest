"""
===============================================================================
Waiting The Longest™ - Background Workers
===============================================================================
Background task workers for scheduled operations:
- Data ingestion from shelter APIs
- Social media content generation
- Status updates and cleanup

Run manually:
    python -m app.workers.scheduler

Or configure as cron job:
    0 */6 * * * cd /opt/waitingthelongest/backend && venv/bin/python -m app.workers.scheduler

Author: Waiting The Longest™ Development Team
===============================================================================
"""

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

try:
    from app.database import SessionLocal
    from app.models import Animal, SocialPromotion
    from app.config import settings
except ImportError:
    from ..app.database import SessionLocal
    from ..app.models import Animal, SocialPromotion
    from ..app.config import settings

logger = logging.getLogger(__name__)


class IngestionWorker:
    """
    Worker for ingesting data from shelter APIs.

    Runs periodically to fetch new animals and update existing ones.
    """

    def __init__(self):
        self.last_run: Optional[datetime] = None
        self.interval_hours = settings.INGEST_INTERVAL_HOURS

    def should_run(self) -> bool:
        """Check if enough time has passed since last run"""
        if self.last_run is None:
            return True

        elapsed = datetime.now(timezone.utc).replace(tzinfo=None) - self.last_run
        return elapsed >= timedelta(hours=self.interval_hours)

    def run(self) -> dict:
        """
        Run the ingestion process.

        Returns:
            Statistics about the ingestion run
        """
        logger.info("Starting data ingestion...")

        db = SessionLocal()
        stats = {"new": 0, "updated": 0, "errors": 0, "duration_seconds": 0}

        try:
            start_time = time.time()

            # Import here to avoid circular imports
            from ..ingestors.rescuegroups import run_full_ingestion

            # Run ingestion
            result = run_full_ingestion(
                db,
                species="all",
                limit=settings.INGEST_PAGE_LIMIT
            )

            stats.update(result)
            stats["duration_seconds"] = round(time.time() - start_time, 2)

            self.last_run = datetime.now(timezone.utc).replace(tzinfo=None)

            logger.info(f"Ingestion complete: {stats}")

        except Exception as e:
            logger.error(f"Ingestion failed: {e}")
            stats["errors"] += 1

        finally:
            db.close()

        return stats


class StatusUpdateWorker:
    """
    Worker for updating animal statuses.

    Checks for animals that haven't been seen recently and
    marks them as potentially adopted/transferred.
    """

    STALE_DAYS = 14  # Days without sighting before marking stale

    def run(self) -> dict:
        """
        Update statuses for stale animals.

        Returns:
            Statistics about updates made
        """
        logger.info("Running status updates...")

        db = SessionLocal()
        stats = {"checked": 0, "updated": 0}

        try:
            cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=self.STALE_DAYS)

            # Find stale animals
            stale_animals = db.query(Animal).filter(
                Animal.status == "available",
                Animal.last_seen_at < cutoff
            ).all()

            stats["checked"] = len(stale_animals)

            for animal in stale_animals:
                # Mark as unknown (might be adopted, transferred, etc.)
                animal.status = "unknown"
                stats["updated"] += 1

            db.commit()

            logger.info(f"Status updates complete: {stats}")

        except Exception as e:
            logger.error(f"Status update failed: {e}")
            db.rollback()

        finally:
            db.close()

        return stats


class SocialContentWorker:
    """
    Worker for generating social media content.

    Creates videos for animals who have been waiting the longest
    and haven't been promoted recently.
    """

    PROMOTION_COOLDOWN_DAYS = 7  # Days between promotions for same animal
    MAX_VIDEOS_PER_RUN = 5

    def run(self) -> dict:
        """
        Generate social media content for longest-waiting animals.

        Returns:
            Statistics about content generated
        """
        logger.info("Generating social content...")

        db = SessionLocal()
        stats = {"candidates": 0, "generated": 0, "errors": 0}

        try:
            # Find longest-waiting animals not recently promoted
            cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=self.PROMOTION_COOLDOWN_DAYS)

            # Get animals that haven't been promoted recently
            from sqlalchemy import func, and_, or_

            recently_promoted_ids = db.query(SocialPromotion.animal_id).filter(
                SocialPromotion.created_at > cutoff
            ).distinct().subquery()

            candidates = db.query(Animal).filter(
                Animal.status == "available",
                ~Animal.id.in_(recently_promoted_ids)
            ).order_by(
                Animal.first_seen_at.asc()  # Longest waiting first
            ).limit(self.MAX_VIDEOS_PER_RUN).all()

            stats["candidates"] = len(candidates)

            for animal in candidates:
                try:
                    # Generate video
                    from ..tools.video_generator import generate_animal_video

                    video_path = generate_animal_video(db, animal.id)

                    if video_path:
                        # Record the promotion
                        promo = SocialPromotion(
                            animal_id=animal.id,
                            platform="tiktok",
                            status="pending",
                            video_path=video_path
                        )
                        db.add(promo)
                        db.commit()

                        stats["generated"] += 1
                        logger.info(f"Generated video for animal {animal.id}")

                except Exception as e:
                    logger.warning(f"Failed to generate video for {animal.id}: {e}")
                    stats["errors"] += 1

            logger.info(f"Social content generation complete: {stats}")

        except Exception as e:
            logger.error(f"Social content generation failed: {e}")

        finally:
            db.close()

        return stats


class CleanupWorker:
    """
    Worker for cleaning up old data and files.
    """

    VIDEO_RETENTION_DAYS = 30

    def run(self) -> dict:
        """
        Clean up old videos and temporary files.

        Returns:
            Statistics about cleanup
        """
        logger.info("Running cleanup...")

        import os
        from pathlib import Path

        stats = {"files_deleted": 0, "space_freed_mb": 0}

        try:
            video_dir = Path(settings.VIDEO_OUTPUT_DIR)
            cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=self.VIDEO_RETENTION_DAYS)

            if video_dir.exists():
                for video_file in video_dir.glob("*.mp4"):
                    file_mtime = datetime.fromtimestamp(video_file.stat().st_mtime)

                    if file_mtime < cutoff:
                        size_mb = video_file.stat().st_size / (1024 * 1024)
                        video_file.unlink()

                        stats["files_deleted"] += 1
                        stats["space_freed_mb"] += size_mb

            stats["space_freed_mb"] = round(stats["space_freed_mb"], 2)

            logger.info(f"Cleanup complete: {stats}")

        except Exception as e:
            logger.error(f"Cleanup failed: {e}")

        return stats


def run_all_workers():
    """
    Run all workers in sequence.

    Typically called from cron or systemd timer.
    """
    logger.info("=" * 60)
    logger.info("Starting Waiting The Longest Worker Run")
    logger.info(f"Time: {datetime.now(timezone.utc).isoformat()}")
    logger.info("=" * 60)

    results = {}

    # Run ingestion
    if settings.INGEST_ENABLED:
        ingestion = IngestionWorker()
        results["ingestion"] = ingestion.run()

    # Run status updates
    status = StatusUpdateWorker()
    results["status_updates"] = status.run()

    # Run social content generation
    social = SocialContentWorker()
    results["social_content"] = social.run()

    # Run cleanup
    cleanup = CleanupWorker()
    results["cleanup"] = cleanup.run()

    logger.info("=" * 60)
    logger.info("Worker run complete")
    logger.info(f"Results: {results}")
    logger.info("=" * 60)

    return results


if __name__ == "__main__":
    # Configure logging for standalone execution
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    run_all_workers()

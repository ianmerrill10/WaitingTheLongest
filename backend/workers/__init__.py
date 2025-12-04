"""
Waiting The Longest™ - Background Workers
=========================================
Scheduled tasks for data ingestion, social content, and maintenance.
"""

# Lazy import to avoid circular dependencies
__all__ = [
    "run_all_workers",
    "IngestionWorker",
    "SocialContentWorker",
    "StatusUpdateWorker",
    "CleanupWorker",
    "SocialAutoPostWorker",
    "SocialScheduleConfig",
    "run_social_autopost",
]


def __getattr__(name):
    if name in ["run_all_workers", "IngestionWorker", "SocialContentWorker", "StatusUpdateWorker", "CleanupWorker"]:
        from .scheduler import run_all_workers, IngestionWorker, SocialContentWorker, StatusUpdateWorker, CleanupWorker
        return locals()[name]
    if name in ["SocialAutoPostWorker", "SocialScheduleConfig", "run_social_autopost"]:
        from .social_scheduler import SocialAutoPostWorker, SocialScheduleConfig, run_social_autopost
        return locals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

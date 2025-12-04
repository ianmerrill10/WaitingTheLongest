"""
Waiting The Longest™ - Background Workers
=========================================
Scheduled tasks for data ingestion, social content, email processing, and maintenance.
"""

# Lazy import to avoid circular dependencies
__all__ = ["run_all_workers", "IngestionWorker", "SocialContentWorker", "StatusUpdateWorker", "CleanupWorker", "EmailWorker"]


def __getattr__(name):
    if name in __all__:
        from .scheduler import run_all_workers, IngestionWorker, SocialContentWorker, StatusUpdateWorker, CleanupWorker, EmailWorker
        return locals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

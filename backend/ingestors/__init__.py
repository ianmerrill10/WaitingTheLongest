"""
Waiting The Longest™ - Data Ingestors
=====================================
Modules for ingesting data from shelter APIs.

Primary: RescueGroups.org
Secondary: Adopt-a-Pet
"""

# Lazy import to avoid circular dependencies
__all__ = ["RescueGroupsIngestor", "run_full_ingestion", "IngestedAnimal"]


def __getattr__(name):
    if name in __all__:
        from .rescuegroups import RescueGroupsIngestor, run_full_ingestion, IngestedAnimal
        return locals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

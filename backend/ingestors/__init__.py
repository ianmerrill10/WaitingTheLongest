"""
Waiting The Longest™ - Data Ingestors
=====================================
Modules for ingesting data from shelter APIs.

Primary: RescueGroups.org
Secondary: Adopt-a-Pet
"""

from .rescuegroups import RescueGroupsIngestor, run_full_ingestion

__all__ = ["RescueGroupsIngestor", "run_full_ingestion"]

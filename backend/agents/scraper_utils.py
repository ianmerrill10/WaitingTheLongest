#!/usr/bin/env python3
"""
===============================================================================
Waiting The Longest™ - Scraper Utilities Module
===============================================================================
Purpose: Placeholder module for scraping logic to be implemented in future PRs.

Author: Waiting The Longest™ Development Team
Dependencies: requests, beautifulsoup4 (for future implementation)
Related Files: agent.py, data_manager.py

This module provides:
- Placeholder function for county-level entity search
- Entity type definitions
- Validation utilities

IMPORTANT: Any changes to this file MUST be documented in OWNERS_MANUAL.md

NOTE: The actual scraping implementation is deferred to a future PR.
      This module currently returns placeholder/mock data.
===============================================================================
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

# Entity type constants
ENTITY_TYPE_GOVERNMENT = "government"
ENTITY_TYPE_PRIVATE = "private"
ENTITY_TYPE_INDIVIDUAL = "individual"

# Valid entity types
VALID_ENTITY_TYPES = {
    ENTITY_TYPE_GOVERNMENT,
    ENTITY_TYPE_PRIVATE,
    ENTITY_TYPE_INDIVIDUAL,
}

# Animal types commonly handled by rescues
COMMON_ANIMAL_TYPES = [
    "dogs",
    "cats",
    "rabbits",
    "birds",
    "horses",
    "small_animals",
    "reptiles",
    "farm_animals",
    "wildlife",
]


def search_entities_in_county(
    state: str, county: str, timeout: int = 30
) -> List[Dict[str, Any]]:
    """
    Search for animal rescue entities in a specific county.

    This is a PLACEHOLDER function. The actual scraping logic will be
    implemented in a future PR. Currently returns an empty list.

    Args:
        state: Two-letter state abbreviation (e.g., "TX")
        county: County name (e.g., "Travis County")
        timeout: Request timeout in seconds (for future use)

    Returns:
        List of entity dictionaries with the following fields:
        - name: Organization name
        - address: Street address
        - city: City name
        - state: State abbreviation
        - zip_code: ZIP/postal code
        - phone: Contact phone
        - email: Contact email
        - website: Website URL
        - social_facebook: Facebook URL
        - social_instagram: Instagram URL
        - social_twitter: Twitter URL
        - description: Organization description
        - animal_types: Comma-separated animal types
        - entity_type: government/private/individual
        - county: County name
        - collected_at: ISO timestamp

    Example:
        >>> entities = search_entities_in_county("TX", "Travis County")
        >>> for entity in entities:
        ...     print(entity['name'])
    """
    # PLACEHOLDER: Actual scraping logic to be implemented
    # This function should:
    # 1. Search various sources for animal rescues in the county
    # 2. Filter out for-profit breeders and pet stores
    # 3. Validate and normalize the data
    # 4. Return a list of entity dictionaries

    # Return empty list - no mock data in production
    return []


def validate_entity(entity: Dict[str, Any]) -> bool:
    """
    Validate that an entity has required fields and valid data.

    Args:
        entity: Entity dictionary to validate

    Returns:
        True if entity is valid, False otherwise
    """
    # Required: name must be present and non-empty
    name = entity.get("name", "").strip()
    if not name:
        return False

    # Required: state must be a valid 2-letter abbreviation
    state = entity.get("state", "").strip().upper()
    if len(state) != 2:
        return False

    # Optional validation: entity_type if present must be valid
    entity_type = entity.get("entity_type", "").strip().lower()
    if entity_type and entity_type not in VALID_ENTITY_TYPES:
        return False

    return True


def normalize_entity(entity: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize entity data to consistent format.

    Args:
        entity: Raw entity dictionary

    Returns:
        Normalized entity dictionary
    """
    normalized = {
        "name": entity.get("name", "").strip(),
        "address": entity.get("address", "").strip(),
        "city": entity.get("city", "").strip(),
        "state": entity.get("state", "").strip().upper(),
        "zip_code": entity.get("zip_code", "").strip(),
        "phone": entity.get("phone", "").strip(),
        "email": entity.get("email", "").strip().lower(),
        "website": entity.get("website", "").strip(),
        "social_facebook": entity.get("social_facebook", "").strip(),
        "social_instagram": entity.get("social_instagram", "").strip(),
        "social_twitter": entity.get("social_twitter", "").strip(),
        "description": entity.get("description", "").strip(),
        "animal_types": entity.get("animal_types", "").strip(),
        "entity_type": entity.get("entity_type", "").strip().lower(),
        "county": entity.get("county", "").strip(),
        "collected_at": entity.get("collected_at", datetime.utcnow().isoformat()),
    }

    # Default entity_type to private if not specified
    if not normalized["entity_type"]:
        normalized["entity_type"] = ENTITY_TYPE_PRIVATE

    return normalized


def is_excluded_entity(name: str, description: str = "") -> bool:
    """
    Check if an entity should be excluded (breeders, pet stores, etc.).

    Args:
        name: Entity name
        description: Entity description

    Returns:
        True if entity should be excluded
    """
    # Keywords that indicate for-profit breeding or pet sales
    excluded_keywords = [
        "breeder",
        "breeding",
        "puppy mill",
        "puppymill",
        "pet store",
        "pet shop",
        "petstore",
        "petshop",
        "for sale",
        "puppies for sale",
        "kittens for sale",
        "akc registered",
        "ckc registered",
        "purebred puppies",
        "designer dogs",
    ]

    combined_text = f"{name} {description}".lower()

    for keyword in excluded_keywords:
        if keyword in combined_text:
            return True

    return False


def filter_entities(entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Filter out invalid and excluded entities.

    Args:
        entities: List of raw entity dictionaries

    Returns:
        List of valid, non-excluded entities
    """
    filtered = []
    for entity in entities:
        # Skip invalid entities
        if not validate_entity(entity):
            continue

        # Skip excluded entities (breeders, pet stores)
        name = entity.get("name", "")
        description = entity.get("description", "")
        if is_excluded_entity(name, description):
            continue

        # Normalize and add to list
        filtered.append(normalize_entity(entity))

    return filtered

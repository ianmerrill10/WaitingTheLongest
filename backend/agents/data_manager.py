#!/usr/bin/env python3
"""
===============================================================================
Waiting The Longest™ - Data Manager Module
===============================================================================
Purpose: Handles state/county data retrieval and CSV I/O for rescue entities.

Author: Waiting The Longest™ Development Team
Dependencies: csv, json
Related Files: agent.py, scraper_utils.py

This module provides:
- Complete list of all 50 US states
- County listings for each state
- CSV reading/writing for entity data
- Progress tracking via completed counties

IMPORTANT: Any changes to this file MUST be documented in OWNERS_MANUAL.md
===============================================================================
"""

import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

# Directory paths
MODULE_DIR = Path(__file__).parent
OUTPUT_DIR = MODULE_DIR / "output"

# Default output file
DEFAULT_OUTPUT_FILE = OUTPUT_DIR / "rescue_entities.csv"

# CSV columns for entity data
CSV_COLUMNS = [
    "name",
    "address",
    "city",
    "state",
    "zip_code",
    "phone",
    "email",
    "website",
    "social_facebook",
    "social_instagram",
    "social_twitter",
    "description",
    "animal_types",
    "entity_type",
    "county",
    "collected_at",
]

# All 50 US states with abbreviations
US_STATES: Dict[str, str] = {
    "AL": "Alabama",
    "AK": "Alaska",
    "AZ": "Arizona",
    "AR": "Arkansas",
    "CA": "California",
    "CO": "Colorado",
    "CT": "Connecticut",
    "DE": "Delaware",
    "FL": "Florida",
    "GA": "Georgia",
    "HI": "Hawaii",
    "ID": "Idaho",
    "IL": "Illinois",
    "IN": "Indiana",
    "IA": "Iowa",
    "KS": "Kansas",
    "KY": "Kentucky",
    "LA": "Louisiana",
    "ME": "Maine",
    "MD": "Maryland",
    "MA": "Massachusetts",
    "MI": "Michigan",
    "MN": "Minnesota",
    "MS": "Mississippi",
    "MO": "Missouri",
    "MT": "Montana",
    "NE": "Nebraska",
    "NV": "Nevada",
    "NH": "New Hampshire",
    "NJ": "New Jersey",
    "NM": "New Mexico",
    "NY": "New York",
    "NC": "North Carolina",
    "ND": "North Dakota",
    "OH": "Ohio",
    "OK": "Oklahoma",
    "OR": "Oregon",
    "PA": "Pennsylvania",
    "RI": "Rhode Island",
    "SC": "South Carolina",
    "SD": "South Dakota",
    "TN": "Tennessee",
    "TX": "Texas",
    "UT": "Utah",
    "VT": "Vermont",
    "VA": "Virginia",
    "WA": "Washington",
    "WV": "West Virginia",
    "WI": "Wisconsin",
    "WY": "Wyoming",
}

# County data file path
COUNTY_DATA_FILE = MODULE_DIR / "us_counties.json"


def get_all_states() -> List[str]:
    """
    Get a list of all 50 US state abbreviations.

    Returns:
        List of state abbreviations (e.g., ['AL', 'AK', 'AZ', ...])
    """
    return list(US_STATES.keys())


def get_state_name(state_abbr: str) -> Optional[str]:
    """
    Get the full name of a state from its abbreviation.

    Args:
        state_abbr: Two-letter state abbreviation

    Returns:
        Full state name or None if not found
    """
    return US_STATES.get(state_abbr.upper())


def get_counties_for_state(state_abbr: str) -> List[str]:
    """
    Get all counties for a specific state.

    Reads from the embedded county data file. If the file doesn't exist,
    returns a placeholder list for the state.

    Args:
        state_abbr: Two-letter state abbreviation

    Returns:
        List of county names for the state
    """
    state_abbr = state_abbr.upper()
    if state_abbr not in US_STATES:
        return []

    # Try to load county data from file
    if COUNTY_DATA_FILE.exists():
        try:
            with open(COUNTY_DATA_FILE, "r") as f:
                county_data = json.load(f)
                return county_data.get(state_abbr, [])
        except (json.JSONDecodeError, IOError):
            pass

    # Return placeholder if no data available
    return [f"{US_STATES[state_abbr]} County (Placeholder)"]


def ensure_output_directory() -> None:
    """Ensure the output directory exists."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def initialize_csv(output_file: Path = DEFAULT_OUTPUT_FILE) -> None:
    """
    Initialize the CSV file with headers if it doesn't exist.

    Args:
        output_file: Path to the output CSV file
    """
    ensure_output_directory()
    if not output_file.exists():
        with open(output_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
            writer.writeheader()


def write_entities_to_csv(
    entities: List[Dict[str, Any]], output_file: Path = DEFAULT_OUTPUT_FILE
) -> int:
    """
    Append entities to the CSV file.

    Args:
        entities: List of entity dictionaries to write
        output_file: Path to the output CSV file

    Returns:
        Number of entities written
    """
    if not entities:
        return 0

    ensure_output_directory()
    initialize_csv(output_file)

    with open(output_file, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        for entity in entities:
            # Ensure only valid columns are written
            row = {col: entity.get(col, "") for col in CSV_COLUMNS}
            writer.writerow(row)

    return len(entities)


def read_existing_entities(
    output_file: Path = DEFAULT_OUTPUT_FILE,
) -> List[Dict[str, Any]]:
    """
    Read all existing entities from the CSV file.

    Args:
        output_file: Path to the CSV file

    Returns:
        List of entity dictionaries
    """
    if not output_file.exists():
        return []

    entities = []
    with open(output_file, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            entities.append(dict(row))

    return entities


def get_completed_counties(
    output_file: Path = DEFAULT_OUTPUT_FILE,
) -> Set[tuple]:
    """
    Get set of (state, county) tuples that have already been processed.

    This enables resumability - we can skip counties that are already done.

    Args:
        output_file: Path to the CSV file

    Returns:
        Set of (state_abbr, county_name) tuples
    """
    entities = read_existing_entities(output_file)
    completed = set()
    for entity in entities:
        state = entity.get("state", "").strip()
        county = entity.get("county", "").strip()
        if state and county:
            completed.add((state, county))
    return completed


def get_progress_stats(
    output_file: Path = DEFAULT_OUTPUT_FILE,
) -> Dict[str, Any]:
    """
    Get statistics about collection progress.

    Args:
        output_file: Path to the CSV file

    Returns:
        Dictionary with progress statistics
    """
    entities = read_existing_entities(output_file)
    completed_counties = get_completed_counties(output_file)

    # Count unique states with at least one county done
    states_with_progress = set(state for state, _ in completed_counties)

    return {
        "total_entities": len(entities),
        "completed_counties": len(completed_counties),
        "states_with_progress": len(states_with_progress),
        "total_states": len(US_STATES),
    }


def is_county_completed(
    state_abbr: str, county: str, output_file: Path = DEFAULT_OUTPUT_FILE
) -> bool:
    """
    Check if a specific county has already been processed.

    Args:
        state_abbr: Two-letter state abbreviation
        county: County name
        output_file: Path to the CSV file

    Returns:
        True if county is already completed
    """
    completed = get_completed_counties(output_file)
    return (state_abbr.upper(), county) in completed

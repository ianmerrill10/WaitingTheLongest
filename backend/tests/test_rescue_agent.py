"""
===============================================================================
Waiting The Longest™ - Rescue Entity Scraper Agent Tests
===============================================================================
Tests for the rescue entity scraper agent framework.

This module tests:
- Data manager functionality (state/county data, CSV I/O)
- Scraper utilities (validation, filtering)
- Agent execution and progress tracking

===============================================================================
"""

import csv
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# Add agents directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "agents"))

from data_manager import (
    CSV_COLUMNS,
    US_STATES,
    get_all_states,
    get_completed_counties,
    get_counties_for_state,
    get_progress_stats,
    get_state_name,
    initialize_csv,
    is_county_completed,
    read_existing_entities,
    write_entities_to_csv,
)
from scraper_utils import (
    ENTITY_TYPE_GOVERNMENT,
    ENTITY_TYPE_INDIVIDUAL,
    ENTITY_TYPE_PRIVATE,
    VALID_ENTITY_TYPES,
    filter_entities,
    is_excluded_entity,
    normalize_entity,
    search_entities_in_county,
    validate_entity,
)


class TestDataManagerStates:
    """Tests for state data functions."""

    def test_get_all_states_returns_50(self):
        """Test that get_all_states returns all 50 states."""
        states = get_all_states()
        assert len(states) == 50

    def test_get_all_states_returns_list(self):
        """Test that get_all_states returns a list."""
        states = get_all_states()
        assert isinstance(states, list)

    def test_get_all_states_abbreviations_format(self):
        """Test that all state abbreviations are 2 uppercase letters."""
        states = get_all_states()
        for state in states:
            assert len(state) == 2
            assert state.isupper()

    def test_get_state_name_valid(self):
        """Test getting state name for valid abbreviation."""
        assert get_state_name("TX") == "Texas"
        assert get_state_name("CA") == "California"
        assert get_state_name("NY") == "New York"

    def test_get_state_name_lowercase(self):
        """Test getting state name with lowercase input."""
        assert get_state_name("tx") == "Texas"

    def test_get_state_name_invalid(self):
        """Test getting state name for invalid abbreviation."""
        assert get_state_name("XX") is None
        assert get_state_name("ZZ") is None


class TestDataManagerCounties:
    """Tests for county data functions."""

    def test_get_counties_invalid_state_returns_empty(self):
        """Test that invalid state returns empty list."""
        counties = get_counties_for_state("XX")
        assert counties == []

    def test_get_counties_returns_list(self):
        """Test that get_counties_for_state returns a list."""
        counties = get_counties_for_state("TX")
        assert isinstance(counties, list)

    def test_get_counties_normalizes_state(self):
        """Test that state abbreviation is normalized to uppercase."""
        counties_upper = get_counties_for_state("TX")
        counties_lower = get_counties_for_state("tx")
        assert counties_upper == counties_lower

    def test_get_counties_with_data_file(self):
        """Test loading counties from data file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            county_file = Path(tmpdir) / "us_counties.json"
            county_file.write_text(
                json.dumps({"TX": ["Travis County", "Harris County"]})
            )

            with patch("data_manager.COUNTY_DATA_FILE", county_file):
                counties = get_counties_for_state("TX")

            assert "Travis County" in counties
            assert "Harris County" in counties


class TestDataManagerCSV:
    """Tests for CSV I/O functions."""

    def test_initialize_csv_creates_file(self):
        """Test that initialize_csv creates file with headers."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "test.csv"

            with patch("data_manager.OUTPUT_DIR", Path(tmpdir)):
                initialize_csv(output_file)

            assert output_file.exists()

            with open(output_file, "r") as f:
                reader = csv.reader(f)
                headers = next(reader)
                assert headers == CSV_COLUMNS

    def test_initialize_csv_does_not_overwrite(self):
        """Test that initialize_csv doesn't overwrite existing file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "test.csv"

            # Write some initial content
            output_file.write_text("existing,content\n")

            with patch("data_manager.OUTPUT_DIR", Path(tmpdir)):
                initialize_csv(output_file)

            content = output_file.read_text()
            assert content == "existing,content\n"

    def test_write_entities_to_csv(self):
        """Test writing entities to CSV file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "test.csv"

            entities = [
                {"name": "Test Shelter", "state": "TX", "county": "Travis County"},
                {"name": "Another Rescue", "state": "CA", "county": "Los Angeles County"},
            ]

            with patch("data_manager.OUTPUT_DIR", Path(tmpdir)):
                written = write_entities_to_csv(entities, output_file)

            assert written == 2
            assert output_file.exists()

    def test_write_entities_empty_list(self):
        """Test that writing empty list returns 0."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "test.csv"

            with patch("data_manager.OUTPUT_DIR", Path(tmpdir)):
                written = write_entities_to_csv([], output_file)

            assert written == 0

    def test_read_existing_entities(self):
        """Test reading entities from CSV file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "test.csv"

            # Create file with some data
            entities = [
                {"name": "Test Shelter", "state": "TX", "county": "Travis County"},
            ]

            with patch("data_manager.OUTPUT_DIR", Path(tmpdir)):
                write_entities_to_csv(entities, output_file)
                read_entities = read_existing_entities(output_file)

            assert len(read_entities) == 1
            assert read_entities[0]["name"] == "Test Shelter"

    def test_read_existing_entities_nonexistent_file(self):
        """Test reading from non-existent file returns empty list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "nonexistent.csv"
            entities = read_existing_entities(output_file)
            assert entities == []


class TestDataManagerProgress:
    """Tests for progress tracking functions."""

    def test_get_completed_counties(self):
        """Test getting completed counties from CSV."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "test.csv"

            entities = [
                {"name": "Shelter 1", "state": "TX", "county": "Travis County"},
                {"name": "Shelter 2", "state": "TX", "county": "Harris County"},
                {"name": "Shelter 3", "state": "CA", "county": "Los Angeles County"},
            ]

            with patch("data_manager.OUTPUT_DIR", Path(tmpdir)):
                write_entities_to_csv(entities, output_file)
                completed = get_completed_counties(output_file)

            assert ("TX", "Travis County") in completed
            assert ("TX", "Harris County") in completed
            assert ("CA", "Los Angeles County") in completed
            assert len(completed) == 3

    def test_is_county_completed(self):
        """Test checking if specific county is completed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "test.csv"

            entities = [{"name": "Shelter", "state": "TX", "county": "Travis County"}]

            with patch("data_manager.OUTPUT_DIR", Path(tmpdir)):
                write_entities_to_csv(entities, output_file)

                assert is_county_completed("TX", "Travis County", output_file)
                assert not is_county_completed("TX", "Harris County", output_file)

    def test_get_progress_stats(self):
        """Test getting progress statistics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "test.csv"

            entities = [
                {"name": "Shelter 1", "state": "TX", "county": "Travis County"},
                {"name": "Shelter 2", "state": "TX", "county": "Harris County"},
                {"name": "Shelter 3", "state": "CA", "county": "Los Angeles County"},
            ]

            with patch("data_manager.OUTPUT_DIR", Path(tmpdir)):
                write_entities_to_csv(entities, output_file)
                stats = get_progress_stats(output_file)

            assert stats["total_entities"] == 3
            assert stats["completed_counties"] == 3
            assert stats["states_with_progress"] == 2
            assert stats["total_states"] == 50


class TestScraperUtilsValidation:
    """Tests for entity validation functions."""

    def test_validate_entity_valid(self):
        """Test validation of valid entity."""
        entity = {"name": "Test Shelter", "state": "TX"}
        assert validate_entity(entity) is True

    def test_validate_entity_missing_name(self):
        """Test validation fails without name."""
        entity = {"state": "TX"}
        assert validate_entity(entity) is False

    def test_validate_entity_empty_name(self):
        """Test validation fails with empty name."""
        entity = {"name": "   ", "state": "TX"}
        assert validate_entity(entity) is False

    def test_validate_entity_invalid_state(self):
        """Test validation fails with invalid state format."""
        entity = {"name": "Test", "state": "Texas"}  # Not 2 letters
        assert validate_entity(entity) is False

    def test_validate_entity_invalid_entity_type(self):
        """Test validation fails with invalid entity type."""
        entity = {"name": "Test", "state": "TX", "entity_type": "invalid"}
        assert validate_entity(entity) is False

    def test_validate_entity_valid_entity_type(self):
        """Test validation passes with valid entity type."""
        entity = {"name": "Test", "state": "TX", "entity_type": "government"}
        assert validate_entity(entity) is True


class TestScraperUtilsNormalization:
    """Tests for entity normalization functions."""

    def test_normalize_entity_basic(self):
        """Test basic entity normalization."""
        entity = {"name": "  Test Shelter  ", "state": "tx", "city": "Austin"}
        normalized = normalize_entity(entity)

        assert normalized["name"] == "Test Shelter"
        assert normalized["state"] == "TX"
        assert normalized["city"] == "Austin"

    def test_normalize_entity_email_lowercase(self):
        """Test email is lowercased."""
        entity = {"name": "Test", "state": "TX", "email": "Test@Example.COM"}
        normalized = normalize_entity(entity)
        assert normalized["email"] == "test@example.com"

    def test_normalize_entity_default_entity_type(self):
        """Test default entity type is private."""
        entity = {"name": "Test", "state": "TX"}
        normalized = normalize_entity(entity)
        assert normalized["entity_type"] == ENTITY_TYPE_PRIVATE

    def test_normalize_entity_preserves_entity_type(self):
        """Test existing entity type is preserved."""
        entity = {"name": "Test", "state": "TX", "entity_type": "Government"}
        normalized = normalize_entity(entity)
        assert normalized["entity_type"] == "government"


class TestScraperUtilsFiltering:
    """Tests for entity filtering functions."""

    def test_is_excluded_entity_breeder(self):
        """Test that breeders are excluded."""
        assert is_excluded_entity("Golden Retriever Breeder") is True
        assert is_excluded_entity("Test", "We are a breeding facility") is True

    def test_is_excluded_entity_pet_store(self):
        """Test that pet stores are excluded."""
        assert is_excluded_entity("Local Pet Store") is True
        assert is_excluded_entity("Pet Shop Downtown") is True

    def test_is_excluded_entity_puppy_mill(self):
        """Test that puppy mills are excluded."""
        assert is_excluded_entity("", "puppymill operation") is True

    def test_is_excluded_entity_rescue_not_excluded(self):
        """Test that legitimate rescues are not excluded."""
        assert is_excluded_entity("Happy Tails Animal Rescue") is False
        assert is_excluded_entity("County Humane Society") is False

    def test_filter_entities_removes_invalid(self):
        """Test that invalid entities are filtered out."""
        entities = [
            {"name": "Valid Shelter", "state": "TX"},
            {"state": "TX"},  # Missing name
            {"name": "", "state": "TX"},  # Empty name
        ]
        filtered = filter_entities(entities)
        assert len(filtered) == 1
        assert filtered[0]["name"] == "Valid Shelter"

    def test_filter_entities_removes_excluded(self):
        """Test that excluded entities are filtered out."""
        entities = [
            {"name": "Happy Tails Rescue", "state": "TX"},
            {"name": "Local Pet Store", "state": "TX"},
            {"name": "Golden Breeder", "state": "TX"},
        ]
        filtered = filter_entities(entities)
        assert len(filtered) == 1
        assert filtered[0]["name"] == "Happy Tails Rescue"

    def test_filter_entities_normalizes(self):
        """Test that filtered entities are normalized."""
        entities = [{"name": "  Test Shelter  ", "state": "tx"}]
        filtered = filter_entities(entities)
        assert filtered[0]["name"] == "Test Shelter"
        assert filtered[0]["state"] == "TX"


class TestScraperUtilsPlaceholder:
    """Tests for placeholder scraping function."""

    def test_search_entities_returns_list(self):
        """Test that search returns a list."""
        result = search_entities_in_county("TX", "Travis County")
        assert isinstance(result, list)

    def test_search_entities_returns_empty(self):
        """Test that placeholder returns empty list."""
        result = search_entities_in_county("TX", "Travis County")
        assert result == []


class TestConstants:
    """Tests for module constants."""

    def test_us_states_count(self):
        """Test that US_STATES has 50 states."""
        assert len(US_STATES) == 50

    def test_valid_entity_types(self):
        """Test that all expected entity types are defined."""
        assert ENTITY_TYPE_GOVERNMENT in VALID_ENTITY_TYPES
        assert ENTITY_TYPE_PRIVATE in VALID_ENTITY_TYPES
        assert ENTITY_TYPE_INDIVIDUAL in VALID_ENTITY_TYPES

    def test_csv_columns_required(self):
        """Test that required CSV columns are present."""
        required = ["name", "state", "county", "entity_type"]
        for col in required:
            assert col in CSV_COLUMNS

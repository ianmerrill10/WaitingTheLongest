"""
===============================================================================
Waiting The Longest™ - Shelter Collector Tests
===============================================================================
Tests for the shelter data collection and processing tool.

This module tests:
- Shelter data validation
- State data processing
- Progress tracking
- File operations
- Database upsert logic

===============================================================================
"""

import json
import os
import pytest
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.shelter_collector import (
    ShelterCollector,
    ShelterData,
    CollectionResult,
    ValidationError,
    US_STATES,
    VALID_ORG_TYPES,
    SOURCE_NAME
)


class TestShelterDataValidation:
    """Tests for shelter data validation"""
    
    def test_validate_valid_shelter(self):
        """Test validation of a complete valid shelter"""
        collector = ShelterCollector(db=None)
        data = {
            "name": "Austin Pets Alive!",
            "type": "rescue",
            "email": "info@austinpetsalive.org",
            "phone": "(512) 961-6519",
            "website": "https://www.austinpetsalive.org",
            "address": "1156 West Cesar Chavez Street",
            "city": "Austin",
            "state": "TX",
            "zip_code": "78703",
            "description": "A nonprofit rescue organization"
        }
        
        result = collector.validate_shelter(data)
        
        assert result.name == "Austin Pets Alive!"
        assert result.email == "info@austinpetsalive.org"
        assert result.phone == "(512) 961-6519"
        assert result.state == "TX"
        assert result.source == SOURCE_NAME
    
    def test_validate_minimal_shelter(self):
        """Test validation of a shelter with only required fields"""
        collector = ShelterCollector(db=None)
        data = {"name": "Test Shelter"}
        
        result = collector.validate_shelter(data)
        
        assert result.name == "Test Shelter"
        assert result.email is None
        assert result.phone is None
    
    def test_validate_missing_name_raises_error(self):
        """Test that missing name raises ValidationError"""
        collector = ShelterCollector(db=None)
        data = {"email": "test@test.com"}
        
        with pytest.raises(ValidationError, match="Shelter name is required"):
            collector.validate_shelter(data)
    
    def test_validate_empty_name_raises_error(self):
        """Test that empty name raises ValidationError"""
        collector = ShelterCollector(db=None)
        data = {"name": "   "}
        
        with pytest.raises(ValidationError, match="Shelter name is required"):
            collector.validate_shelter(data)
    
    def test_validate_name_too_long_raises_error(self):
        """Test that name exceeding 200 characters raises ValidationError"""
        collector = ShelterCollector(db=None)
        data = {"name": "A" * 201}
        
        with pytest.raises(ValidationError, match="exceeds 200 characters"):
            collector.validate_shelter(data)
    
    def test_validate_invalid_state_raises_error(self):
        """Test that invalid state abbreviation raises ValidationError"""
        collector = ShelterCollector(db=None)
        data = {"name": "Test Shelter", "state": "XX"}
        
        with pytest.raises(ValidationError, match="Invalid state abbreviation"):
            collector.validate_shelter(data)
    
    def test_validate_state_normalization(self):
        """Test that state is normalized to uppercase"""
        collector = ShelterCollector(db=None)
        data = {"name": "Test Shelter", "state": "tx"}
        
        result = collector.validate_shelter(data)
        
        assert result.state == "TX"
    
    def test_validate_coordinates(self):
        """Test coordinate validation"""
        collector = ShelterCollector(db=None)
        data = {
            "name": "Test Shelter",
            "latitude": 30.2672,
            "longitude": -97.7431
        }
        
        result = collector.validate_shelter(data)
        
        assert result.latitude == 30.2672
        assert result.longitude == -97.7431
    
    def test_validate_invalid_coordinates_ignored(self):
        """Test that invalid coordinates are set to None"""
        collector = ShelterCollector(db=None)
        data = {
            "name": "Test Shelter",
            "latitude": 999,  # Invalid
            "longitude": "invalid"  # Invalid
        }
        
        result = collector.validate_shelter(data)
        
        assert result.latitude is None
        assert result.longitude is None
    
    def test_validate_org_type_normalization(self):
        """Test organization type normalization"""
        collector = ShelterCollector(db=None)
        data = {"name": "Test Shelter", "type": "Humane Society"}
        
        result = collector.validate_shelter(data)
        
        assert result.org_type == "humane_society"
    
    def test_validate_unknown_org_type_defaults_to_nonprofit(self):
        """Test that unknown org type defaults to nonprofit"""
        collector = ShelterCollector(db=None)
        data = {"name": "Test Shelter", "type": "unknown_type"}
        
        result = collector.validate_shelter(data)
        
        assert result.org_type == "nonprofit"
    
    def test_validate_truncates_long_fields(self):
        """Test that long fields are truncated appropriately"""
        collector = ShelterCollector(db=None)
        data = {
            "name": "Test Shelter",
            "city": "A" * 150,  # Over 100 chars
            "address": "B" * 400,  # Over 300 chars
            "description": "C" * 1500  # Over 1000 chars
        }
        
        result = collector.validate_shelter(data)
        
        assert len(result.city) == 100
        assert len(result.address) == 300
        assert len(result.description) == 1000


class TestStateProcessing:
    """Tests for state data processing"""
    
    def test_process_valid_state_data(self):
        """Test processing valid state data"""
        collector = ShelterCollector(db=None)
        state_data = {
            "state": "TX",
            "state_full": "Texas",
            "shelters": [
                {"name": "Shelter 1", "city": "Austin"},
                {"name": "Shelter 2", "city": "Dallas"}
            ]
        }
        
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('tools.shelter_collector.SHELTERS_DIR', Path(tmpdir)):
                with patch('tools.shelter_collector.TRACKER_FILE', Path(tmpdir) / 'tracker.json'):
                    # Create initial tracker
                    tracker_path = Path(tmpdir) / 'tracker.json'
                    tracker_path.write_text(json.dumps({
                        "metadata": {},
                        "states": {"TX": {"name": "Texas", "status": "pending"}}
                    }))
                    
                    result = collector.process_state_data(
                        state_data, 
                        save_to_file=True, 
                        insert_to_db=False
                    )
        
        assert result.success is True
        assert result.state == "TX"
        assert result.total_processed == 2
    
    def test_process_invalid_state_returns_error(self):
        """Test that invalid state returns error result"""
        collector = ShelterCollector(db=None)
        state_data = {
            "state": "XX",
            "shelters": [{"name": "Test"}]
        }
        
        result = collector.process_state_data(state_data, save_to_file=False, insert_to_db=False)
        
        assert result.success is False
        assert "Invalid state" in result.message
    
    def test_process_empty_shelters_returns_error(self):
        """Test that empty shelters list returns error result"""
        collector = ShelterCollector(db=None)
        state_data = {
            "state": "TX",
            "shelters": []
        }
        
        result = collector.process_state_data(state_data, save_to_file=False, insert_to_db=False)
        
        assert result.success is False
        assert "No shelters provided" in result.message
    
    def test_process_tracks_validation_errors(self):
        """Test that validation errors are tracked"""
        collector = ShelterCollector(db=None)
        state_data = {
            "state": "TX",
            "shelters": [
                {"name": "Valid Shelter"},
                {"email": "invalid@no-name.com"},  # Missing name
                {"name": "Another Valid"}
            ]
        }
        
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('tools.shelter_collector.SHELTERS_DIR', Path(tmpdir)):
                with patch('tools.shelter_collector.TRACKER_FILE', Path(tmpdir) / 'tracker.json'):
                    tracker_path = Path(tmpdir) / 'tracker.json'
                    tracker_path.write_text(json.dumps({
                        "metadata": {},
                        "states": {"TX": {"name": "Texas", "status": "pending"}}
                    }))
                    
                    result = collector.process_state_data(
                        state_data, 
                        save_to_file=True, 
                        insert_to_db=False
                    )
        
        assert result.skipped == 1
        assert len(result.errors) == 1
        assert "Shelter name is required" in result.errors[0]


class TestProgressTracking:
    """Tests for collection progress tracking"""
    
    def test_get_next_state(self):
        """Test getting next state to collect"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker_path = Path(tmpdir) / 'tracker.json'
            tracker_path.write_text(json.dumps({
                "metadata": {},
                "states": {
                    "AL": {"name": "Alabama", "status": "completed"},
                    "AK": {"name": "Alaska", "status": "pending"},
                    "AZ": {"name": "Arizona", "status": "pending"}
                }
            }))
            
            with patch('tools.shelter_collector.TRACKER_FILE', tracker_path):
                collector = ShelterCollector(db=None)
                next_state = collector.get_next_state()
        
        assert next_state == "AK"
    
    def test_get_next_state_all_completed(self):
        """Test getting next state when all are completed"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker_path = Path(tmpdir) / 'tracker.json'
            tracker_path.write_text(json.dumps({
                "metadata": {},
                "states": {
                    "AL": {"name": "Alabama", "status": "completed"},
                    "AK": {"name": "Alaska", "status": "completed"}
                }
            }))
            
            with patch('tools.shelter_collector.TRACKER_FILE', tracker_path):
                collector = ShelterCollector(db=None)
                next_state = collector.get_next_state()
        
        assert next_state is None
    
    def test_get_progress(self):
        """Test getting progress summary"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker_path = Path(tmpdir) / 'tracker.json'
            tracker_path.write_text(json.dumps({
                "metadata": {},
                "states": {
                    "AL": {"name": "Alabama", "status": "completed", "shelter_count": 10},
                    "AK": {"name": "Alaska", "status": "completed", "shelter_count": 5},
                    "AZ": {"name": "Arizona", "status": "pending", "shelter_count": 0},
                    "AR": {"name": "Arkansas", "status": "in_progress", "shelter_count": 0}
                }
            }))
            
            with patch('tools.shelter_collector.TRACKER_FILE', tracker_path):
                collector = ShelterCollector(db=None)
                progress = collector.get_progress()
        
        assert progress['total_states'] == 4
        assert progress['completed_count'] == 2
        assert progress['pending_count'] == 1
        assert progress['in_progress_count'] == 1
        assert progress['total_shelters_collected'] == 15
        assert progress['progress_percentage'] == 50.0


class TestFileOperations:
    """Tests for file operations"""
    
    def test_load_state_shelters(self):
        """Test loading shelters from file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            shelters_dir = Path(tmpdir)
            tx_file = shelters_dir / "TX_shelters.json"
            tx_file.write_text(json.dumps({
                "state": "TX",
                "shelters": [{"name": "Test Shelter"}]
            }))
            
            with patch('tools.shelter_collector.SHELTERS_DIR', shelters_dir):
                collector = ShelterCollector(db=None)
                data = collector.load_state_shelters("TX")
        
        assert data is not None
        assert data['state'] == "TX"
        assert len(data['shelters']) == 1
    
    def test_load_state_shelters_not_found(self):
        """Test loading shelters from non-existent file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('tools.shelter_collector.SHELTERS_DIR', Path(tmpdir)):
                collector = ShelterCollector(db=None)
                data = collector.load_state_shelters("XX")
        
        assert data is None
    
    def test_save_state_shelters(self):
        """Test saving shelters to file"""
        collector = ShelterCollector(db=None)
        state_data = {
            "state": "TX",
            "state_full": "Texas",
            "shelters": [{"name": "Test Shelter"}]
        }
        
        with tempfile.TemporaryDirectory() as tmpdir:
            shelters_dir = Path(tmpdir)
            with patch('tools.shelter_collector.SHELTERS_DIR', shelters_dir):
                with patch('tools.shelter_collector.TRACKER_FILE', Path(tmpdir) / 'tracker.json'):
                    tracker_path = Path(tmpdir) / 'tracker.json'
                    tracker_path.write_text(json.dumps({
                        "metadata": {},
                        "states": {"TX": {"name": "Texas", "status": "pending"}}
                    }))
                    
                    collector.process_state_data(
                        state_data, 
                        save_to_file=True, 
                        insert_to_db=False
                    )
            
            saved_file = shelters_dir / "TX_shelters.json"
            assert saved_file.exists()
            
            saved_data = json.loads(saved_file.read_text())
            assert saved_data['state'] == "TX"


class TestDatabaseOperations:
    """Tests for database operations"""
    
    def test_upsert_new_shelter(self, db_session, sample_shelter):
        """Test inserting a new shelter"""
        from app.models import Shelter
        
        collector = ShelterCollector(db=db_session)
        
        shelter_data = ShelterData(
            name="New Test Shelter",
            source=SOURCE_NAME,
            email="new@shelter.org",
            phone="555-1234",
            state="CA",
            city="Los Angeles"
        )
        
        is_new, action = collector.upsert_shelter(shelter_data)
        db_session.commit()
        
        assert is_new is True
        assert action == "inserted"
        
        # Verify in database
        shelter = db_session.query(Shelter).filter(
            Shelter.name == "New Test Shelter"
        ).first()
        assert shelter is not None
        assert shelter.source == SOURCE_NAME
    
    def test_upsert_existing_shelter(self, db_session, sample_shelter):
        """Test updating an existing shelter"""
        collector = ShelterCollector(db=db_session)
        
        # Use the same name and state as sample_shelter
        shelter_data = ShelterData(
            name=sample_shelter.name,
            source=SOURCE_NAME,
            email="updated@shelter.org",
            phone="555-9999",
            state=sample_shelter.state,
            city=sample_shelter.city
        )
        
        is_new, action = collector.upsert_shelter(shelter_data)
        db_session.commit()
        db_session.refresh(sample_shelter)
        
        assert is_new is False
        assert action == "updated"
        assert sample_shelter.email == "updated@shelter.org"
        assert sample_shelter.phone == "555-9999"
    
    def test_upsert_without_db_skips(self):
        """Test that upsert without database connection skips"""
        collector = ShelterCollector(db=None)
        
        shelter_data = ShelterData(
            name="Test Shelter",
            source=SOURCE_NAME,
            state="TX"
        )
        
        is_new, action = collector.upsert_shelter(shelter_data)
        
        assert is_new is False
        assert action == "skipped"


class TestConstants:
    """Tests for module constants"""
    
    def test_all_50_states_present(self):
        """Test that all 50 US states are defined"""
        assert len(US_STATES) == 50
    
    def test_state_abbreviations_format(self):
        """Test that all state abbreviations are 2 uppercase letters"""
        for abbr in US_STATES.keys():
            assert len(abbr) == 2
            assert abbr.isupper()
    
    def test_valid_org_types(self):
        """Test that expected organization types are defined"""
        expected_types = {
            "shelter", "rescue", "humane_society", "spca", 
            "aspca", "sanctuary", "foster_network", "nonprofit"
        }
        assert expected_types.issubset(VALID_ORG_TYPES)
    
    def test_source_name(self):
        """Test that source name is correctly defined"""
        assert SOURCE_NAME == "copilot_agent_collection"

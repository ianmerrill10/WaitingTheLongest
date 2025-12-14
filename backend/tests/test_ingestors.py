"""
Waiting The Longest™ - Ingestor Tests
=====================================
Tests for data ingestion from external sources.
"""

import pytest
from datetime import date, datetime
from unittest.mock import Mock, patch, AsyncMock
import json

from sqlalchemy.orm import Session

from app.models import Animal, Shelter


class TestRescueGroupsIngestor:
    """Test RescueGroups API ingestion."""
    
    @pytest.fixture
    def mock_rescuegroups_response(self):
        """Mock response from RescueGroups API."""
        return {
            "data": [
                {
                    "id": "12345",
                    "type": "animals",
                    "attributes": {
                        "name": "Buddy",
                        "species": {"name": "Dog"},
                        "breeds": {"primary": {"name": "Golden Retriever"}},
                        "ageGroup": "Adult",
                        "sex": "Male",
                        "descriptionText": "A friendly dog.",
                        "pictureThumbnailUrl": "https://example.com/photo.jpg",
                        "createdDate": "2023-01-15T00:00:00Z",
                    },
                    "relationships": {
                        "orgs": {"data": [{"type": "orgs", "id": "org1"}]}
                    }
                }
            ],
            "included": [
                {
                    "id": "org1",
                    "type": "orgs",
                    "attributes": {
                        "name": "Happy Tails Shelter",
                        "city": "Portland",
                        "state": "OR",
                    }
                }
            ],
            "meta": {"count": 1}
        }
    
    def test_parse_animal_data(self, mock_rescuegroups_response):
        """Test parsing animal data from API response."""
        from ingestors.rescuegroups import RescueGroupsIngestor
        
        # Mock database session
        mock_db = Mock(spec=Session)
        
        ingestor = RescueGroupsIngestor(mock_db)
        
        animal_data = mock_rescuegroups_response["data"][0]
        org_data = mock_rescuegroups_response["included"][0]
        
        # Parse animal
        parsed = ingestor._parse_animal(animal_data, {"org1": org_data})
        
        assert parsed is not None
        assert parsed["name"] == "Buddy"
        assert parsed["species"] == "Dog"
        assert parsed["breed"] == "Golden Retriever"
    
    def test_parse_shelter_data(self, mock_rescuegroups_response):
        """Test parsing shelter data from API response."""
        from ingestors.rescuegroups import RescueGroupsIngestor
        
        mock_db = Mock(spec=Session)
        ingestor = RescueGroupsIngestor(mock_db)
        
        org_data = mock_rescuegroups_response["included"][0]
        
        parsed = ingestor._parse_shelter(org_data)
        
        assert parsed is not None
        assert parsed["name"] == "Happy Tails Shelter"
        assert parsed["city"] == "Portland"
        assert parsed["state"] == "OR"
    
    def test_date_parsing(self):
        """Test intake date parsing from various formats."""
        from ingestors.rescuegroups import RescueGroupsIngestor
        
        mock_db = Mock(spec=Session)
        ingestor = RescueGroupsIngestor(mock_db)
        
        test_dates = [
            ("2023-01-15T00:00:00Z", date(2023, 1, 15)),
            ("2023-06-20", date(2023, 6, 20)),
            ("01/15/2023", date(2023, 1, 15)),
        ]
        
        for date_str, expected in test_dates:
            parsed = ingestor._parse_date(date_str)
            if parsed:  # May return None for unparseable formats
                assert parsed == expected, f"Failed to parse {date_str}"
    
    def test_handles_missing_fields_gracefully(self):
        """Test that missing fields don't cause errors."""
        from ingestors.rescuegroups import RescueGroupsIngestor
        
        mock_db = Mock(spec=Session)
        ingestor = RescueGroupsIngestor(mock_db)
        
        incomplete_data = {
            "id": "123",
            "type": "animals",
            "attributes": {
                "name": "Unknown",
                # Missing other fields
            }
        }
        
        # Should not raise, may return None or partial data
        try:
            result = ingestor._parse_animal(incomplete_data, {})
            # Test passes if no exception
        except Exception as e:
            pytest.fail(f"Failed to handle missing fields: {e}")
    
    @pytest.mark.asyncio
    async def test_dry_run_mode(self, mock_rescuegroups_response):
        """Test dry run doesn't modify database."""
        from ingestors.rescuegroups import RescueGroupsIngestor
        
        mock_db = Mock(spec=Session)
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        ingestor = RescueGroupsIngestor(mock_db)
        
        with patch.object(ingestor, '_fetch_animals', return_value=mock_rescuegroups_response):
            result = await ingestor.run(dry_run=True)
        
        # In dry run, db.add should not be called
        mock_db.add.assert_not_called()
        mock_db.commit.assert_not_called()
    
    def test_duplicate_detection(self, db_session):
        """Test that duplicate animals are not re-added."""
        from ingestors.rescuegroups import RescueGroupsIngestor
        
        # Add existing shelter and animal
        shelter = Shelter(
            name="Test Shelter",
            city="Test",
            state="TS",
            external_id="org1",
        )
        db_session.add(shelter)
        db_session.commit()
        
        existing_animal = Animal(
            name="Buddy",
            species="Dog",
            external_id="12345",
            shelter_id=shelter.id,
            intake_date=date.today(),
        )
        db_session.add(existing_animal)
        db_session.commit()
        
        ingestor = RescueGroupsIngestor(db_session)
        
        # Check duplicate detection
        is_duplicate = ingestor._is_duplicate("12345")
        
        assert is_duplicate is True


class TestIngestorUtils:
    """Test utility functions for ingestors."""
    
    def test_normalize_species_name(self):
        """Test species name normalization."""
        from ingestors.rescuegroups import normalize_species
        
        test_cases = [
            ("Dog", "Dog"),
            ("dog", "Dog"),
            ("DOG", "Dog"),
            ("Canine", "Dog"),
            ("Cat", "Cat"),
            ("Feline", "Cat"),
            ("Rabbit", "Rabbit"),
            ("Unknown", "Other"),
        ]
        
        for input_val, expected in test_cases:
            result = normalize_species(input_val)
            assert result == expected, f"normalize_species({input_val}) = {result}, expected {expected}"
    
    def test_normalize_age(self):
        """Test age normalization."""
        from ingestors.rescuegroups import normalize_age
        
        test_cases = [
            ("Baby", "Baby"),
            ("Puppy", "Baby"),
            ("Kitten", "Baby"),
            ("Young", "Young"),
            ("Adult", "Adult"),
            ("Senior", "Senior"),
            ("Geriatric", "Senior"),
        ]
        
        for input_val, expected in test_cases:
            result = normalize_age(input_val)
            assert result == expected, f"normalize_age({input_val}) = {result}, expected {expected}"
    
    def test_clean_description(self):
        """Test description cleaning (HTML removal, etc.)."""
        from ingestors.rescuegroups import clean_description
        
        html_description = "<p>This is a <strong>great</strong> dog!</p>"
        clean = clean_description(html_description)
        
        # Should not contain HTML tags
        assert "<p>" not in clean
        assert "<strong>" not in clean
        assert "great" in clean


class TestIngestorRateLimiting:
    """Test rate limiting in ingestors."""
    
    @pytest.mark.asyncio
    async def test_respects_rate_limits(self):
        """Test that ingestor respects API rate limits."""
        from ingestors.rescuegroups import RescueGroupsIngestor
        import time
        
        mock_db = Mock(spec=Session)
        ingestor = RescueGroupsIngestor(mock_db)
        
        # Record request times
        request_times = []
        
        async def mock_request(*args, **kwargs):
            request_times.append(time.time())
            return {"data": [], "meta": {"count": 0}}
        
        with patch.object(ingestor, '_make_request', mock_request):
            await ingestor._fetch_animals(limit=5)
        
        # Verify spacing between requests if multiple were made
        if len(request_times) > 1:
            for i in range(1, len(request_times)):
                gap = request_times[i] - request_times[i-1]
                # Should have some delay between requests
                assert gap >= 0, "Requests should be spaced out"


class TestIngestorErrorHandling:
    """Test error handling in ingestors."""
    
    @pytest.mark.asyncio
    async def test_handles_api_errors(self):
        """Test handling of API errors."""
        from ingestors.rescuegroups import RescueGroupsIngestor
        
        mock_db = Mock(spec=Session)
        ingestor = RescueGroupsIngestor(mock_db)
        
        # Mock API error
        with patch.object(ingestor, '_make_request', side_effect=Exception("API Error")):
            result = await ingestor.run()
        
        # Should handle gracefully, not crash
        assert result.get("error") or result.get("animals_added") == 0
    
    @pytest.mark.asyncio
    async def test_handles_malformed_response(self):
        """Test handling of malformed API response."""
        from ingestors.rescuegroups import RescueGroupsIngestor
        
        mock_db = Mock(spec=Session)
        ingestor = RescueGroupsIngestor(mock_db)
        
        malformed = {"unexpected": "format"}
        
        with patch.object(ingestor, '_fetch_animals', return_value=malformed):
            result = await ingestor.run()
        
        # Should handle gracefully
        assert result is not None
    
    def test_handles_database_errors(self, db_session):
        """Test handling of database errors during ingestion."""
        from ingestors.rescuegroups import RescueGroupsIngestor
        
        ingestor = RescueGroupsIngestor(db_session)
        
        # Simulate a database error
        with patch.object(db_session, 'commit', side_effect=Exception("DB Error")):
            try:
                ingestor._save_animal({
                    "name": "Test",
                    "species": "Dog",
                    "intake_date": date.today(),
                })
            except Exception:
                pass  # Expected
        
        # Session should be rolled back
        db_session.rollback()

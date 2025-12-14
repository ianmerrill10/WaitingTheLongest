"""
===============================================================================
Waiting The Longest™ - Data Validation Tests
===============================================================================
Purpose: Test data validation utilities
===============================================================================
"""

import pytest
from backend.tools.data_validator import DataValidator


class TestDataValidator:
    """Tests for DataValidator class."""
    
    def test_validate_animal_with_valid_data(self):
        """Test validation with complete valid data."""
        data = {
            "name": "Buddy",
            "species": "dog",
            "age_group": "adult",
            "size": "medium",
            "gender": "male",
            "status": "available",
            "breed_primary": "Labrador Retriever",
            "city": "Austin",
            "state": "TX",
            "zip_code": "78701",
            "photo_url": "https://example.com/photo.jpg",
            "description": "A friendly dog looking for a home.",
        }
        
        is_valid, errors, sanitized = DataValidator.validate_animal(data)
        
        assert is_valid is True
        assert len(errors) == 0
        assert sanitized["name"] == "Buddy"
        assert sanitized["species"] == "dog"
        assert sanitized["state"] == "TX"
    
    def test_validate_animal_missing_name(self):
        """Test validation with missing name."""
        data = {
            "species": "dog",
        }
        
        is_valid, errors, sanitized = DataValidator.validate_animal(data)
        
        assert is_valid is False
        assert "Missing required field: name" in errors
    
    def test_validate_animal_invalid_species(self):
        """Test validation with invalid species."""
        data = {
            "name": "Test",
            "species": "elephant",
        }
        
        is_valid, errors, sanitized = DataValidator.validate_animal(data)
        
        assert is_valid is False
        assert any("Invalid species" in e for e in errors)
    
    def test_normalize_species(self):
        """Test species normalization."""
        assert DataValidator.normalize_species("dog") == "dog"
        assert DataValidator.normalize_species("DOG") == "dog"
        assert DataValidator.normalize_species("dogs") == "dog"
        assert DataValidator.normalize_species("canine") == "dog"
        assert DataValidator.normalize_species("puppy") == "dog"
        assert DataValidator.normalize_species("cat") == "cat"
        assert DataValidator.normalize_species("cats") == "cat"
        assert DataValidator.normalize_species("feline") == "cat"
        assert DataValidator.normalize_species("kitten") == "cat"
        assert DataValidator.normalize_species("rabbit") == "other"
        assert DataValidator.normalize_species("") == "other"
    
    def test_normalize_age_group(self):
        """Test age group normalization."""
        assert DataValidator.normalize_age_group("puppy") == "puppy"
        assert DataValidator.normalize_age_group("puppies") == "puppy"
        assert DataValidator.normalize_age_group("baby") == "puppy"
        assert DataValidator.normalize_age_group("kitten") == "kitten"
        assert DataValidator.normalize_age_group("young") == "young"
        assert DataValidator.normalize_age_group("adolescent") == "young"
        assert DataValidator.normalize_age_group("adult") == "adult"
        assert DataValidator.normalize_age_group("mature") == "adult"
        assert DataValidator.normalize_age_group("senior") == "senior"
        assert DataValidator.normalize_age_group("elderly") == "senior"
        assert DataValidator.normalize_age_group("unknown") is None
    
    def test_normalize_size(self):
        """Test size normalization."""
        assert DataValidator.normalize_size("small") == "small"
        assert DataValidator.normalize_size("tiny") == "small"
        assert DataValidator.normalize_size("mini") == "small"
        assert DataValidator.normalize_size("medium") == "medium"
        assert DataValidator.normalize_size("med") == "medium"
        assert DataValidator.normalize_size("large") == "large"
        assert DataValidator.normalize_size("big") == "large"
        assert DataValidator.normalize_size("extra large") == "extra large"
        assert DataValidator.normalize_size("xl") == "extra large"
        assert DataValidator.normalize_size("giant") == "extra large"
        assert DataValidator.normalize_size("") is None
    
    def test_normalize_gender(self):
        """Test gender normalization."""
        assert DataValidator.normalize_gender("male") == "male"
        assert DataValidator.normalize_gender("m") == "male"
        assert DataValidator.normalize_gender("boy") == "male"
        assert DataValidator.normalize_gender("female") == "female"
        assert DataValidator.normalize_gender("f") == "female"
        assert DataValidator.normalize_gender("girl") == "female"
        assert DataValidator.normalize_gender("other") == "unknown"
        assert DataValidator.normalize_gender("") is None
    
    def test_normalize_state(self):
        """Test state normalization."""
        assert DataValidator.normalize_state("TX") == "TX"
        assert DataValidator.normalize_state("tx") == "TX"
        assert DataValidator.normalize_state("Texas") == "TX"
        assert DataValidator.normalize_state("TEXAS") == "TX"
        assert DataValidator.normalize_state("California") == "CA"
        assert DataValidator.normalize_state("New York") == "NY"
        assert DataValidator.normalize_state("District of Columbia") == "DC"
        assert DataValidator.normalize_state("Invalid") is None
        assert DataValidator.normalize_state("") is None
    
    def test_validate_zip_code(self):
        """Test ZIP code validation."""
        assert DataValidator.validate_zip_code("78701") == "78701"
        assert DataValidator.validate_zip_code("78701-1234") == "78701-1234"
        assert DataValidator.validate_zip_code("787011234") == "78701-1234"
        assert DataValidator.validate_zip_code("abc") is None
        assert DataValidator.validate_zip_code("1234") is None
        assert DataValidator.validate_zip_code("") is None
    
    def test_validate_url(self):
        """Test URL validation."""
        assert DataValidator.validate_url("https://example.com/photo.jpg") == "https://example.com/photo.jpg"
        assert DataValidator.validate_url("http://example.com/photo.jpg") == "http://example.com/photo.jpg"
        assert DataValidator.validate_url("ftp://example.com") is None
        assert DataValidator.validate_url("invalid-url") is None
        assert DataValidator.validate_url("data:image/png;base64,abc") is None
        assert DataValidator.validate_url("") is None
    
    def test_sanitize_name(self):
        """Test name sanitization."""
        assert DataValidator.sanitize_name("Buddy") == "Buddy"
        assert DataValidator.sanitize_name("  Buddy  ") == "Buddy"
        assert DataValidator.sanitize_name("Buddy    Jr.") == "Buddy Jr."
        assert DataValidator.sanitize_name("") == "Unknown"
        assert DataValidator.sanitize_name(None) == "Unknown"
        # Should handle special characters
        assert DataValidator.sanitize_name("Buddy's Pet!") == "Buddy's Pet"
    
    def test_sanitize_description(self):
        """Test description sanitization."""
        assert DataValidator.sanitize_description("A friendly dog.") == "A friendly dog."
        assert DataValidator.sanitize_description("<p>HTML content</p>") == "HTML content"
        assert DataValidator.sanitize_description("<script>alert('xss')</script>") == "alert('xss')"
        assert DataValidator.sanitize_description("  Extra   spaces  ") == "Extra spaces"
        assert DataValidator.sanitize_description("") is None

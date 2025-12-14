"""
===============================================================================
Waiting The Longest™ - Data Validation Utilities
===============================================================================
Purpose: Validate and sanitize animal data before database insertion.
         Ensures data quality and consistency across all sources.

Author: Waiting The Longest™ Development Team
===============================================================================
"""

import re
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class DataValidator:
    """Validate and sanitize animal data before database insertion."""
    
    # Valid values for categorical fields
    VALID_SPECIES = {"dog", "cat", "other"}
    VALID_AGE_GROUPS = {"puppy", "kitten", "young", "adult", "senior"}
    VALID_SIZES = {"small", "medium", "large", "extra large"}
    VALID_GENDERS = {"male", "female", "unknown"}
    VALID_STATUSES = {"available", "adopted", "pending", "transferred", "deceased", "unknown"}
    
    # US State abbreviations
    US_STATES = {
        "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
        "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
        "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
        "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
        "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
        "DC", "PR", "VI", "GU", "AS", "MP"
    }
    
    @classmethod
    def validate_animal(cls, data: Dict[str, Any]) -> Tuple[bool, List[str], Dict[str, Any]]:
        """
        Validate and sanitize animal data.
        
        Args:
            data: Raw animal data dictionary
            
        Returns:
            Tuple of (is_valid, errors, sanitized_data)
        """
        errors = []
        sanitized = {}
        
        # Required fields
        if not data.get("name"):
            errors.append("Missing required field: name")
        else:
            sanitized["name"] = cls.sanitize_name(data["name"])
        
        # Species
        species = cls.normalize_species(data.get("species", ""))
        if species not in cls.VALID_SPECIES:
            errors.append(f"Invalid species: {data.get('species')}")
        else:
            sanitized["species"] = species
        
        # Age group
        age_group = cls.normalize_age_group(data.get("age_group", ""))
        if age_group and age_group not in cls.VALID_AGE_GROUPS:
            logger.warning(f"Unknown age group: {data.get('age_group')}")
        sanitized["age_group"] = age_group if age_group in cls.VALID_AGE_GROUPS else None
        
        # Size
        size = cls.normalize_size(data.get("size", ""))
        if size and size not in cls.VALID_SIZES:
            logger.warning(f"Unknown size: {data.get('size')}")
        sanitized["size"] = size if size in cls.VALID_SIZES else None
        
        # Gender
        gender = cls.normalize_gender(data.get("gender", ""))
        sanitized["gender"] = gender if gender in cls.VALID_GENDERS else None
        
        # Status
        status = data.get("status", "available").lower().strip()
        sanitized["status"] = status if status in cls.VALID_STATUSES else "available"
        
        # Breed
        sanitized["breed_primary"] = cls.sanitize_breed(data.get("breed_primary", ""))
        sanitized["breed_secondary"] = cls.sanitize_breed(data.get("breed_secondary", ""))
        
        # Location
        sanitized["city"] = cls.sanitize_city(data.get("city", ""))
        sanitized["state"] = cls.normalize_state(data.get("state", ""))
        sanitized["zip_code"] = cls.validate_zip_code(data.get("zip_code", ""))
        
        # Photos
        sanitized["photo_url"] = cls.validate_url(data.get("photo_url", ""))
        sanitized["photos"] = [
            url for url in (data.get("photos") or [])
            if cls.validate_url(url)
        ]
        
        # Description
        sanitized["description"] = cls.sanitize_description(data.get("description", ""))
        
        # External IDs
        sanitized["external_id"] = str(data.get("external_id", "")).strip()[:100]
        sanitized["source"] = str(data.get("source", "")).strip().lower()[:50]
        
        is_valid = len(errors) == 0
        return is_valid, errors, sanitized
    
    @classmethod
    def sanitize_name(cls, name: str) -> str:
        """Sanitize animal name."""
        if not name:
            return "Unknown"
        # Remove excessive whitespace
        name = " ".join(name.split())
        # Remove special characters except basic punctuation
        name = re.sub(r'[^\w\s\'-]', '', name)
        # Limit length
        return name[:200].strip() or "Unknown"
    
    @classmethod
    def normalize_species(cls, species: str) -> str:
        """Normalize species to standard values."""
        if not species:
            return "other"
        species = species.lower().strip()
        if species in {"dog", "dogs", "canine", "puppy", "puppies"}:
            return "dog"
        if species in {"cat", "cats", "feline", "kitten", "kittens"}:
            return "cat"
        return "other"
    
    @classmethod
    def normalize_age_group(cls, age: str) -> Optional[str]:
        """Normalize age group."""
        if not age:
            return None
        age = age.lower().strip()
        
        if age in {"puppy", "puppies", "baby", "babies"}:
            return "puppy"
        if age in {"kitten", "kittens"}:
            return "kitten"
        if age in {"young", "juvenile", "adolescent", "teen", "teenager"}:
            return "young"
        if age in {"adult", "mature", "grown"}:
            return "adult"
        if age in {"senior", "old", "elderly", "geriatric"}:
            return "senior"
        return None
    
    @classmethod
    def normalize_size(cls, size: str) -> Optional[str]:
        """Normalize size."""
        if not size:
            return None
        size = size.lower().strip()
        
        if size in {"small", "tiny", "mini", "miniature", "toy", "xs", "petite"}:
            return "small"
        if size in {"medium", "med", "mid", "average", "m"}:
            return "medium"
        if size in {"large", "big", "lg", "l"}:
            return "large"
        if size in {"extra large", "xl", "xlarge", "giant", "huge", "xxl"}:
            return "extra large"
        return None
    
    @classmethod
    def normalize_gender(cls, gender: str) -> Optional[str]:
        """Normalize gender."""
        if not gender:
            return None
        gender = gender.lower().strip()
        
        if gender in {"male", "m", "boy", "he", "him"}:
            return "male"
        if gender in {"female", "f", "girl", "she", "her"}:
            return "female"
        return "unknown"
    
    @classmethod
    def normalize_state(cls, state: str) -> Optional[str]:
        """Normalize US state to 2-letter abbreviation."""
        if not state:
            return None
        state = state.upper().strip()
        
        # Already a valid abbreviation
        if state in cls.US_STATES:
            return state
        
        # Common full names to abbreviations
        state_names = {
            "ALABAMA": "AL", "ALASKA": "AK", "ARIZONA": "AZ", "ARKANSAS": "AR",
            "CALIFORNIA": "CA", "COLORADO": "CO", "CONNECTICUT": "CT", "DELAWARE": "DE",
            "FLORIDA": "FL", "GEORGIA": "GA", "HAWAII": "HI", "IDAHO": "ID",
            "ILLINOIS": "IL", "INDIANA": "IN", "IOWA": "IA", "KANSAS": "KS",
            "KENTUCKY": "KY", "LOUISIANA": "LA", "MAINE": "ME", "MARYLAND": "MD",
            "MASSACHUSETTS": "MA", "MICHIGAN": "MI", "MINNESOTA": "MN", "MISSISSIPPI": "MS",
            "MISSOURI": "MO", "MONTANA": "MT", "NEBRASKA": "NE", "NEVADA": "NV",
            "NEW HAMPSHIRE": "NH", "NEW JERSEY": "NJ", "NEW MEXICO": "NM", "NEW YORK": "NY",
            "NORTH CAROLINA": "NC", "NORTH DAKOTA": "ND", "OHIO": "OH", "OKLAHOMA": "OK",
            "OREGON": "OR", "PENNSYLVANIA": "PA", "RHODE ISLAND": "RI", "SOUTH CAROLINA": "SC",
            "SOUTH DAKOTA": "SD", "TENNESSEE": "TN", "TEXAS": "TX", "UTAH": "UT",
            "VERMONT": "VT", "VIRGINIA": "VA", "WASHINGTON": "WA", "WEST VIRGINIA": "WV",
            "WISCONSIN": "WI", "WYOMING": "WY", "DISTRICT OF COLUMBIA": "DC", "PUERTO RICO": "PR"
        }
        
        return state_names.get(state)
    
    @classmethod
    def sanitize_breed(cls, breed: str) -> Optional[str]:
        """Sanitize breed name."""
        if not breed:
            return None
        breed = " ".join(breed.split())
        breed = re.sub(r'[^\w\s\'-/]', '', breed)
        return breed[:100].strip() or None
    
    @classmethod
    def sanitize_city(cls, city: str) -> Optional[str]:
        """Sanitize city name."""
        if not city:
            return None
        city = " ".join(city.split())
        city = re.sub(r'[^\w\s\'-.]', '', city)
        return city[:100].strip() or None
    
    @classmethod
    def validate_zip_code(cls, zip_code: str) -> Optional[str]:
        """Validate and format ZIP code."""
        if not zip_code:
            return None
        # Remove non-digits
        digits = re.sub(r'\D', '', str(zip_code))
        # 5 or 9 digit ZIP
        if len(digits) == 5:
            return digits
        if len(digits) == 9:
            return f"{digits[:5]}-{digits[5:]}"
        return None
    
    @classmethod
    def validate_url(cls, url: str) -> Optional[str]:
        """Validate URL."""
        if not url:
            return None
        url = url.strip()
        # Basic URL validation
        if not re.match(r'^https?://', url, re.IGNORECASE):
            return None
        # Block data URIs in photo URLs
        if url.startswith('data:'):
            return None
        return url[:2000]  # Limit length
    
    @classmethod
    def sanitize_description(cls, description: str) -> Optional[str]:
        """Sanitize description text."""
        if not description:
            return None
        # Remove HTML tags
        description = re.sub(r'<[^>]+>', '', description)
        # Normalize whitespace
        description = " ".join(description.split())
        # Limit length
        return description[:5000].strip() or None

"""
Waiting The Longest™ - Data Validation
========================================
Input validation utilities for API endpoints.
"""

import re
from typing import Optional, List, Any, Tuple
from dataclasses import dataclass


@dataclass
class ValidationError:
    """A validation error."""
    field: str
    message: str
    value: Any = None


class Validator:
    """
    Collection of validation functions.
    
    All methods return (is_valid, error_message) tuples.
    """
    
    # Common regex patterns
    EMAIL_PATTERN = re.compile(
        r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    )
    
    URL_PATTERN = re.compile(
        r"^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(/.*)?$"
    )
    
    PHONE_PATTERN = re.compile(
        r"^[\d\s\-\+\(\)]{7,20}$"
    )
    
    STATE_CODES = {
        "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
        "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
        "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
        "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
        "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
        "DC", "PR", "VI",
    }
    
    SPECIES = {"dog", "cat", "bird", "rabbit", "guinea pig", "hamster", "fish", "reptile", "other"}
    
    GENDERS = {"male", "female", "unknown"}
    
    AGE_CATEGORIES = {"baby", "young", "adult", "senior"}
    
    @classmethod
    def validate_email(cls, email: str) -> Tuple[bool, Optional[str]]:
        """Validate an email address."""
        if not email:
            return False, "Email is required"
        
        if len(email) > 254:
            return False, "Email is too long"
        
        if not cls.EMAIL_PATTERN.match(email):
            return False, "Invalid email format"
        
        return True, None
    
    @classmethod
    def validate_url(cls, url: str, required: bool = False) -> Tuple[bool, Optional[str]]:
        """Validate a URL."""
        if not url:
            if required:
                return False, "URL is required"
            return True, None
        
        if len(url) > 2048:
            return False, "URL is too long"
        
        if not cls.URL_PATTERN.match(url):
            return False, "Invalid URL format"
        
        return True, None
    
    @classmethod
    def validate_phone(cls, phone: str, required: bool = False) -> Tuple[bool, Optional[str]]:
        """Validate a phone number."""
        if not phone:
            if required:
                return False, "Phone number is required"
            return True, None
        
        if not cls.PHONE_PATTERN.match(phone):
            return False, "Invalid phone number format"
        
        return True, None
    
    @classmethod
    def validate_state(cls, state: str, required: bool = False) -> Tuple[bool, Optional[str]]:
        """Validate a US state code."""
        if not state:
            if required:
                return False, "State is required"
            return True, None
        
        if state.upper() not in cls.STATE_CODES:
            return False, f"Invalid state code: {state}"
        
        return True, None
    
    @classmethod
    def validate_species(cls, species: str, required: bool = False) -> Tuple[bool, Optional[str]]:
        """Validate animal species."""
        if not species:
            if required:
                return False, "Species is required"
            return True, None
        
        if species.lower() not in cls.SPECIES:
            return False, f"Invalid species: {species}"
        
        return True, None
    
    @classmethod
    def validate_gender(cls, gender: str, required: bool = False) -> Tuple[bool, Optional[str]]:
        """Validate animal gender."""
        if not gender:
            if required:
                return False, "Gender is required"
            return True, None
        
        if gender.lower() not in cls.GENDERS:
            return False, f"Invalid gender: {gender}"
        
        return True, None
    
    @classmethod
    def validate_age_category(cls, age: str, required: bool = False) -> Tuple[bool, Optional[str]]:
        """Validate age category."""
        if not age:
            if required:
                return False, "Age is required"
            return True, None
        
        if age.lower() not in cls.AGE_CATEGORIES:
            return False, f"Invalid age category: {age}"
        
        return True, None
    
    @classmethod
    def validate_string(
        cls,
        value: str,
        field_name: str,
        min_length: int = 0,
        max_length: int = 1000,
        required: bool = False,
    ) -> Tuple[bool, Optional[str]]:
        """Validate a string field."""
        if not value:
            if required:
                return False, f"{field_name} is required"
            return True, None
        
        if len(value) < min_length:
            return False, f"{field_name} must be at least {min_length} characters"
        
        if len(value) > max_length:
            return False, f"{field_name} must be at most {max_length} characters"
        
        return True, None
    
    @classmethod
    def validate_integer(
        cls,
        value: Any,
        field_name: str,
        min_value: Optional[int] = None,
        max_value: Optional[int] = None,
        required: bool = False,
    ) -> Tuple[bool, Optional[str]]:
        """Validate an integer field."""
        if value is None:
            if required:
                return False, f"{field_name} is required"
            return True, None
        
        try:
            int_value = int(value)
        except (ValueError, TypeError):
            return False, f"{field_name} must be a valid integer"
        
        if min_value is not None and int_value < min_value:
            return False, f"{field_name} must be at least {min_value}"
        
        if max_value is not None and int_value > max_value:
            return False, f"{field_name} must be at most {max_value}"
        
        return True, None
    
    @classmethod
    def sanitize_html(cls, text: str) -> str:
        """Remove HTML tags from text."""
        if not text:
            return text
        
        # Simple HTML tag removal
        clean = re.sub(r"<[^>]+>", "", text)
        # Remove any remaining script content
        clean = re.sub(r"<script.*?</script>", "", clean, flags=re.DOTALL | re.IGNORECASE)
        return clean.strip()
    
    @classmethod
    def sanitize_sql(cls, text: str) -> str:
        """Escape potential SQL injection characters."""
        if not text:
            return text
        
        # This is a backup - parameterized queries should always be used
        dangerous = ["'", '"', ";", "--", "/*", "*/", "xp_", "sp_"]
        result = text
        for char in dangerous:
            result = result.replace(char, "")
        return result


class RequestValidator:
    """
    Validate request data with multiple fields.
    
    Usage:
        validator = RequestValidator()
        validator.validate_email("email", request_data.get("email"))
        validator.validate_string("name", request_data.get("name"), min_length=2)
        
        if not validator.is_valid:
            raise ValidationException(validator.errors)
    """
    
    def __init__(self):
        self.errors: List[ValidationError] = []
    
    @property
    def is_valid(self) -> bool:
        """Check if all validations passed."""
        return len(self.errors) == 0
    
    def add_error(self, field: str, message: str, value: Any = None) -> None:
        """Add a validation error."""
        self.errors.append(ValidationError(field, message, value))
    
    def validate_email(self, field: str, value: str, required: bool = True) -> None:
        """Validate email field."""
        valid, message = Validator.validate_email(value) if value else (not required, "Required" if required else None)
        if not valid:
            self.add_error(field, message or "Invalid email", value)
    
    def validate_url(self, field: str, value: str, required: bool = False) -> None:
        """Validate URL field."""
        valid, message = Validator.validate_url(value, required)
        if not valid:
            self.add_error(field, message or "Invalid URL", value)
    
    def validate_string(
        self,
        field: str,
        value: str,
        min_length: int = 0,
        max_length: int = 1000,
        required: bool = False,
    ) -> None:
        """Validate string field."""
        valid, message = Validator.validate_string(value, field, min_length, max_length, required)
        if not valid:
            self.add_error(field, message or "Invalid value", value)
    
    def validate_integer(
        self,
        field: str,
        value: Any,
        min_value: Optional[int] = None,
        max_value: Optional[int] = None,
        required: bool = False,
    ) -> None:
        """Validate integer field."""
        valid, message = Validator.validate_integer(value, field, min_value, max_value, required)
        if not valid:
            self.add_error(field, message or "Invalid integer", value)
    
    def validate_state(self, field: str, value: str, required: bool = False) -> None:
        """Validate state code field."""
        valid, message = Validator.validate_state(value, required)
        if not valid:
            self.add_error(field, message or "Invalid state", value)
    
    def validate_species(self, field: str, value: str, required: bool = False) -> None:
        """Validate species field."""
        valid, message = Validator.validate_species(value, required)
        if not valid:
            self.add_error(field, message or "Invalid species", value)
    
    def get_error_dict(self) -> dict:
        """Get errors as a dictionary."""
        return {
            "errors": [
                {"field": e.field, "message": e.message}
                for e in self.errors
            ]
        }

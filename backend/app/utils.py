"""
Waiting The Longest™ - Utility Functions
==========================================
Common utilities used throughout the application.
"""

import re
import unicodedata
from datetime import datetime, timedelta, date
from typing import Any, TypeVar, Sequence
from functools import wraps
import hashlib
import secrets
import time


T = TypeVar("T")


# =============================================================================
# Date/Time Utilities
# =============================================================================

def calculate_days_waiting(intake_date: datetime | date | None) -> int:
    """Calculate days an animal has been waiting for adoption."""
    if intake_date is None:
        return 0
    
    if isinstance(intake_date, datetime):
        intake_date = intake_date.date()
    
    today = datetime.utcnow().date()
    delta = today - intake_date
    return max(0, delta.days)


def format_days_waiting(days: int) -> str:
    """Format days waiting in a human-friendly way."""
    if days == 0:
        return "Just arrived"
    elif days == 1:
        return "1 day"
    elif days < 7:
        return f"{days} days"
    elif days < 14:
        return "1 week"
    elif days < 30:
        weeks = days // 7
        return f"{weeks} weeks"
    elif days < 60:
        return "1 month"
    elif days < 365:
        months = days // 30
        return f"{months} months"
    else:
        years = days // 365
        if years == 1:
            return "1 year"
        return f"{years} years"


def parse_date_flexible(date_string: str) -> date | None:
    """Parse various date formats."""
    formats = [
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%d/%m/%Y",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S.%fZ",
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(date_string.strip(), fmt)
            return dt.date()
        except ValueError:
            continue
    
    return None


def is_within_timeframe(dt: datetime, hours: int = 24) -> bool:
    """Check if a datetime is within the given hours from now."""
    now = datetime.utcnow()
    threshold = now - timedelta(hours=hours)
    return dt >= threshold


# =============================================================================
# String Utilities
# =============================================================================

def slugify(text: str) -> str:
    """Convert text to URL-friendly slug."""
    # Normalize unicode
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    
    # Convert to lowercase
    text = text.lower()
    
    # Replace spaces with hyphens
    text = re.sub(r"\s+", "-", text)
    
    # Remove non-alphanumeric characters
    text = re.sub(r"[^a-z0-9-]", "", text)
    
    # Remove multiple hyphens
    text = re.sub(r"-+", "-", text)
    
    # Strip leading/trailing hyphens
    return text.strip("-")


def truncate(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate text to maximum length."""
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)].rstrip() + suffix


def normalize_whitespace(text: str) -> str:
    """Normalize whitespace in text."""
    return " ".join(text.split())


def capitalize_words(text: str) -> str:
    """Capitalize first letter of each word."""
    return " ".join(word.capitalize() for word in text.split())


def mask_email(email: str) -> str:
    """Mask email address for privacy."""
    if "@" not in email:
        return email
    
    local, domain = email.rsplit("@", 1)
    
    if len(local) <= 2:
        masked_local = local[0] + "*"
    else:
        masked_local = local[0] + "*" * (len(local) - 2) + local[-1]
    
    return f"{masked_local}@{domain}"


# =============================================================================
# Collection Utilities
# =============================================================================

def chunk_list(items: Sequence[T], chunk_size: int) -> list[list[T]]:
    """Split a list into chunks of specified size."""
    return [list(items[i:i + chunk_size]) for i in range(0, len(items), chunk_size)]


def flatten(nested: list[list[T]]) -> list[T]:
    """Flatten a nested list."""
    return [item for sublist in nested for item in sublist]


def unique_by_key(items: Sequence[dict], key: str) -> list[dict]:
    """Get unique items by a specific key."""
    seen = set()
    result = []
    for item in items:
        value = item.get(key)
        if value not in seen:
            seen.add(value)
            result.append(item)
    return result


def group_by_key(items: Sequence[dict], key: str) -> dict[Any, list[dict]]:
    """Group items by a specific key."""
    groups: dict[Any, list[dict]] = {}
    for item in items:
        value = item.get(key)
        if value not in groups:
            groups[value] = []
        groups[value].append(item)
    return groups


# =============================================================================
# Hash/Token Utilities
# =============================================================================

def generate_token(length: int = 32) -> str:
    """Generate a secure random token."""
    return secrets.token_urlsafe(length)


def hash_string(text: str) -> str:
    """Create SHA-256 hash of a string."""
    return hashlib.sha256(text.encode()).hexdigest()


def short_hash(text: str, length: int = 8) -> str:
    """Create a short hash for identification."""
    return hash_string(text)[:length]


# =============================================================================
# Validation Utilities
# =============================================================================

def is_valid_email(email: str) -> bool:
    """Check if email is valid."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def is_valid_url(url: str) -> bool:
    """Check if URL is valid."""
    pattern = r'^https?://[^\s/$.?#].[^\s]*$'
    return bool(re.match(pattern, url))


def is_valid_phone(phone: str) -> bool:
    """Check if phone number is valid (basic check)."""
    digits = re.sub(r'\D', '', phone)
    return 10 <= len(digits) <= 15


# =============================================================================
# Timing Utilities
# =============================================================================

def timing_decorator(func):
    """Decorator to measure function execution time."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        end = time.perf_counter()
        print(f"{func.__name__} took {end - start:.4f} seconds")
        return result
    return wrapper


async def async_timing_decorator(func):
    """Decorator to measure async function execution time."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = await func(*args, **kwargs)
        end = time.perf_counter()
        print(f"{func.__name__} took {end - start:.4f} seconds")
        return result
    return wrapper


class Timer:
    """Context manager for timing code blocks."""
    
    def __init__(self, name: str = ""):
        self.name = name
        self.start = 0.0
        self.end = 0.0
    
    def __enter__(self):
        self.start = time.perf_counter()
        return self
    
    def __exit__(self, *args):
        self.end = time.perf_counter()
    
    @property
    def elapsed(self) -> float:
        return self.end - self.start


# =============================================================================
# Animal-Specific Utilities
# =============================================================================

def normalize_species(species: str) -> str:
    """Normalize species name."""
    species = species.lower().strip()
    
    mappings = {
        "dogs": "dog",
        "cats": "cat",
        "rabbit": "rabbit",
        "rabbits": "rabbit",
        "birds": "bird",
        "small animals": "small animal",
        "small & furry": "small animal",
        "horse": "horse",
        "horses": "horse",
        "reptile": "reptile",
        "reptiles": "reptile",
        "barnyard": "barnyard",
        "scales, fins & other": "other",
    }
    
    return mappings.get(species, species)


def normalize_age(age: str) -> str:
    """Normalize age category."""
    age = age.lower().strip()
    
    mappings = {
        "baby": "baby",
        "kitten": "baby",
        "puppy": "baby",
        "young": "young",
        "junior": "young",
        "adult": "adult",
        "senior": "senior",
        "old": "senior",
        "geriatric": "senior",
    }
    
    return mappings.get(age, age)


def normalize_gender(gender: str) -> str:
    """Normalize gender."""
    gender = gender.lower().strip()
    
    mappings = {
        "male": "male",
        "m": "male",
        "female": "female",
        "f": "female",
        "unknown": "unknown",
        "": "unknown",
    }
    
    return mappings.get(gender, gender)


def extract_primary_breed(breed: str) -> str:
    """Extract primary breed from mixed breed description."""
    if not breed:
        return "Unknown"
    
    # Handle common patterns
    breed = breed.strip()
    
    # Remove "Mix" suffix
    if breed.lower().endswith(" mix"):
        breed = breed[:-4].strip()
    
    # Take first breed if separated by /
    if "/" in breed:
        breed = breed.split("/")[0].strip()
    
    return breed or "Unknown"


# =============================================================================
# Safe Operations
# =============================================================================

def safe_int(value: Any, default: int = 0) -> int:
    """Safely convert value to integer."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert value to float."""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_get(data: dict, *keys, default: Any = None) -> Any:
    """Safely get nested dictionary value."""
    for key in keys:
        if isinstance(data, dict):
            data = data.get(key)
        else:
            return default
        if data is None:
            return default
    return data

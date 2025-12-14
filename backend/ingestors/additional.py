"""
Waiting The Longest™ - Additional Ingestors
=============================================
Support for multiple data sources.
"""

import logging
import httpx
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from sqlalchemy.orm import Session


logger = logging.getLogger(__name__)


@dataclass
class IngestResult:
    """Result of an ingestion run."""
    source: str
    added: int = 0
    updated: int = 0
    errors: int = 0
    skipped: int = 0
    duration_seconds: float = 0.0
    error_messages: List[str] = None
    
    def __post_init__(self):
        if self.error_messages is None:
            self.error_messages = []
    
    @property
    def total_processed(self) -> int:
        return self.added + self.updated + self.skipped


class BaseIngestor(ABC):
    """Base class for all data ingestors."""
    
    SOURCE_NAME: str = "base"
    
    def __init__(self):
        self.client = httpx.Client(timeout=30.0)
    
    @abstractmethod
    def fetch_animals(self) -> List[Dict[str, Any]]:
        """Fetch raw animal data from the source."""
        pass
    
    @abstractmethod
    def transform_animal(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform raw data to our standard format."""
        pass
    
    def run(self, db: Session, dry_run: bool = False) -> IngestResult:
        """Run the ingestion process."""
        start_time = datetime.utcnow()
        result = IngestResult(source=self.SOURCE_NAME)
        
        try:
            raw_animals = self.fetch_animals()
            logger.info(f"Fetched {len(raw_animals)} animals from {self.SOURCE_NAME}")
            
            for raw in raw_animals:
                try:
                    animal_data = self.transform_animal(raw)
                    
                    if dry_run:
                        result.added += 1
                        continue
                    
                    # TODO: Actually save to database
                    result.added += 1
                    
                except Exception as e:
                    result.errors += 1
                    result.error_messages.append(str(e))
                    logger.error(f"Error processing animal: {e}")
        
        except Exception as e:
            result.errors += 1
            result.error_messages.append(f"Fetch error: {e}")
            logger.error(f"Error fetching from {self.SOURCE_NAME}: {e}")
        
        result.duration_seconds = (datetime.utcnow() - start_time).total_seconds()
        return result
    
    def close(self):
        """Clean up resources."""
        self.client.close()


class PetfinderIngestor(BaseIngestor):
    """
    Ingestor for Petfinder API.
    
    Note: Requires Petfinder API key.
    Documentation: https://www.petfinder.com/developers/
    """
    
    SOURCE_NAME = "petfinder"
    BASE_URL = "https://api.petfinder.com/v2"
    
    def __init__(self, api_key: str, secret: str):
        super().__init__()
        self.api_key = api_key
        self.secret = secret
        self._token: Optional[str] = None
        self._token_expires: Optional[datetime] = None
    
    def _authenticate(self) -> str:
        """Get OAuth token."""
        if self._token and self._token_expires and datetime.utcnow() < self._token_expires:
            return self._token
        
        response = self.client.post(
            f"{self.BASE_URL}/oauth2/token",
            data={
                "grant_type": "client_credentials",
                "client_id": self.api_key,
                "client_secret": self.secret,
            },
        )
        response.raise_for_status()
        data = response.json()
        
        self._token = data["access_token"]
        # Token expires in 1 hour, refresh a bit early
        from datetime import timedelta
        self._token_expires = datetime.utcnow() + timedelta(seconds=data["expires_in"] - 300)
        
        return self._token
    
    def fetch_animals(self, location: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Fetch animals from Petfinder API."""
        token = self._authenticate()
        
        params = {"limit": min(limit, 100), "sort": "recent"}
        if location:
            params["location"] = location
        
        response = self.client.get(
            f"{self.BASE_URL}/animals",
            headers={"Authorization": f"Bearer {token}"},
            params=params,
        )
        response.raise_for_status()
        
        return response.json().get("animals", [])
    
    def transform_animal(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """Transform Petfinder data to our format."""
        photos = raw.get("photos", [])
        primary_photo = photos[0]["medium"] if photos else None
        
        return {
            "external_id": f"petfinder_{raw['id']}",
            "name": raw.get("name", "Unknown"),
            "species": raw.get("type", "").lower(),
            "breed": raw.get("breeds", {}).get("primary", "Mixed"),
            "age": raw.get("age", "").lower(),
            "gender": raw.get("gender", "").lower(),
            "description": raw.get("description", ""),
            "photo_url": primary_photo,
            "external_url": raw.get("url"),
            "shelter_external_id": raw.get("organization_id"),
        }


class AdoptAPetIngestor(BaseIngestor):
    """
    Ingestor for Adopt-a-Pet API.
    
    Note: Requires partner API access.
    """
    
    SOURCE_NAME = "adoptapet"
    BASE_URL = "https://api.adoptapet.com"
    
    def __init__(self, api_key: str):
        super().__init__()
        self.api_key = api_key
    
    def fetch_animals(self) -> List[Dict[str, Any]]:
        """Fetch animals from Adopt-a-Pet."""
        # This is a placeholder - actual API may differ
        response = self.client.get(
            f"{self.BASE_URL}/search",
            headers={"X-API-Key": self.api_key},
            params={"limit": 100},
        )
        response.raise_for_status()
        return response.json().get("pets", [])
    
    def transform_animal(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """Transform Adopt-a-Pet data to our format."""
        return {
            "external_id": f"adoptapet_{raw.get('id')}",
            "name": raw.get("name", "Unknown"),
            "species": raw.get("species", "").lower(),
            "breed": raw.get("breed", "Mixed"),
            "age": raw.get("age_category", "").lower(),
            "gender": raw.get("sex", "").lower(),
            "description": raw.get("description", ""),
            "photo_url": raw.get("photo_url"),
            "external_url": raw.get("profile_url"),
        }


class ShelterManagerIngestor(BaseIngestor):
    """
    Generic ingestor for shelter management system exports.
    
    Supports CSV/JSON file imports from various shelter software.
    """
    
    SOURCE_NAME = "shelter_manager"
    
    def __init__(self, file_path: str, file_format: str = "csv"):
        super().__init__()
        self.file_path = file_path
        self.file_format = file_format
    
    def fetch_animals(self) -> List[Dict[str, Any]]:
        """Load animals from file."""
        import json
        import csv
        
        if self.file_format == "json":
            with open(self.file_path, "r") as f:
                return json.load(f)
        elif self.file_format == "csv":
            with open(self.file_path, "r", newline="") as f:
                reader = csv.DictReader(f)
                return list(reader)
        else:
            raise ValueError(f"Unsupported file format: {self.file_format}")
    
    def transform_animal(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """Transform shelter manager data."""
        # Try to handle various common field names
        return {
            "external_id": raw.get("id") or raw.get("animal_id") or raw.get("ID"),
            "name": raw.get("name") or raw.get("animal_name") or raw.get("Name") or "Unknown",
            "species": (raw.get("species") or raw.get("type") or raw.get("Species") or "").lower(),
            "breed": raw.get("breed") or raw.get("Breed") or "Mixed",
            "age": (raw.get("age") or raw.get("Age") or "").lower(),
            "gender": (raw.get("gender") or raw.get("sex") or raw.get("Gender") or "").lower(),
            "description": raw.get("description") or raw.get("bio") or raw.get("Description") or "",
            "photo_url": raw.get("photo") or raw.get("photo_url") or raw.get("image"),
            "intake_date": raw.get("intake_date") or raw.get("arrival_date"),
        }


class IngestorRegistry:
    """
    Registry of available ingestors.
    
    Usage:
        registry = IngestorRegistry()
        ingestor = registry.get("rescuegroups")
        result = ingestor.run(db)
    """
    
    def __init__(self):
        self._ingestors: Dict[str, type] = {}
        self._register_defaults()
    
    def _register_defaults(self):
        """Register built-in ingestors."""
        self.register("petfinder", PetfinderIngestor)
        self.register("adoptapet", AdoptAPetIngestor)
        self.register("shelter_manager", ShelterManagerIngestor)
    
    def register(self, name: str, ingestor_class: type) -> None:
        """Register an ingestor class."""
        self._ingestors[name] = ingestor_class
    
    def get(self, name: str, **kwargs) -> BaseIngestor:
        """Get an ingestor instance."""
        if name not in self._ingestors:
            raise ValueError(f"Unknown ingestor: {name}")
        
        return self._ingestors[name](**kwargs)
    
    def list_available(self) -> List[str]:
        """List available ingestor names."""
        return list(self._ingestors.keys())


# Global registry instance
ingestor_registry = IngestorRegistry()

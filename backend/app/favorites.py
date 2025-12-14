"""
Waiting The Longest™ - Favorites System
=========================================
User favorites/bookmarks functionality.
"""

import json
import hashlib
from datetime import datetime
from dataclasses import dataclass, field
from typing import Any


# =============================================================================
# Favorites Data Structures
# =============================================================================

@dataclass
class FavoriteAnimal:
    """A favorited animal record."""
    
    animal_id: int
    added_at: datetime = field(default_factory=datetime.utcnow)
    notes: str = ""
    
    def to_dict(self) -> dict:
        return {
            "animal_id": self.animal_id,
            "added_at": self.added_at.isoformat(),
            "notes": self.notes,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "FavoriteAnimal":
        return cls(
            animal_id=data["animal_id"],
            added_at=datetime.fromisoformat(data["added_at"]) if isinstance(data["added_at"], str) else data["added_at"],
            notes=data.get("notes", ""),
        )


@dataclass
class UserFavorites:
    """Collection of user's favorites."""
    
    user_id: str
    animals: list[FavoriteAnimal] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def add(self, animal_id: int, notes: str = "") -> FavoriteAnimal:
        """Add an animal to favorites."""
        # Check if already exists
        existing = self.get(animal_id)
        if existing:
            return existing
        
        favorite = FavoriteAnimal(animal_id=animal_id, notes=notes)
        self.animals.append(favorite)
        self.updated_at = datetime.utcnow()
        return favorite
    
    def remove(self, animal_id: int) -> bool:
        """Remove an animal from favorites."""
        for i, fav in enumerate(self.animals):
            if fav.animal_id == animal_id:
                del self.animals[i]
                self.updated_at = datetime.utcnow()
                return True
        return False
    
    def get(self, animal_id: int) -> FavoriteAnimal | None:
        """Get a favorite by animal ID."""
        for fav in self.animals:
            if fav.animal_id == animal_id:
                return fav
        return None
    
    def has(self, animal_id: int) -> bool:
        """Check if animal is favorited."""
        return self.get(animal_id) is not None
    
    def count(self) -> int:
        """Get number of favorites."""
        return len(self.animals)
    
    def get_animal_ids(self) -> list[int]:
        """Get list of favorited animal IDs."""
        return [fav.animal_id for fav in self.animals]
    
    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "animals": [a.to_dict() for a in self.animals],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "UserFavorites":
        return cls(
            user_id=data["user_id"],
            animals=[FavoriteAnimal.from_dict(a) for a in data.get("animals", [])],
            created_at=datetime.fromisoformat(data["created_at"]) if isinstance(data["created_at"], str) else data["created_at"],
            updated_at=datetime.fromisoformat(data["updated_at"]) if isinstance(data["updated_at"], str) else data["updated_at"],
        )


# =============================================================================
# Favorites Storage
# =============================================================================

class FavoritesStorage:
    """
    Abstract base for favorites storage.
    """
    
    async def get(self, user_id: str) -> UserFavorites | None:
        raise NotImplementedError
    
    async def save(self, favorites: UserFavorites) -> None:
        raise NotImplementedError
    
    async def delete(self, user_id: str) -> bool:
        raise NotImplementedError


class InMemoryFavoritesStorage(FavoritesStorage):
    """
    In-memory favorites storage (for development/testing).
    """
    
    def __init__(self):
        self._store: dict[str, UserFavorites] = {}
    
    async def get(self, user_id: str) -> UserFavorites | None:
        return self._store.get(user_id)
    
    async def save(self, favorites: UserFavorites) -> None:
        self._store[favorites.user_id] = favorites
    
    async def delete(self, user_id: str) -> bool:
        if user_id in self._store:
            del self._store[user_id]
            return True
        return False


class RedisFavoritesStorage(FavoritesStorage):
    """
    Redis-based favorites storage.
    """
    
    def __init__(self, redis_client: Any, prefix: str = "favorites:"):
        self.redis = redis_client
        self.prefix = prefix
    
    def _key(self, user_id: str) -> str:
        return f"{self.prefix}{user_id}"
    
    async def get(self, user_id: str) -> UserFavorites | None:
        data = await self.redis.get(self._key(user_id))
        if data:
            return UserFavorites.from_dict(json.loads(data))
        return None
    
    async def save(self, favorites: UserFavorites) -> None:
        key = self._key(favorites.user_id)
        data = json.dumps(favorites.to_dict())
        await self.redis.set(key, data)
    
    async def delete(self, user_id: str) -> bool:
        result = await self.redis.delete(self._key(user_id))
        return result > 0


class DatabaseFavoritesStorage(FavoritesStorage):
    """
    Database-based favorites storage using SQLAlchemy.
    """
    
    def __init__(self, db_session: Any):
        self.db = db_session
    
    async def get(self, user_id: str) -> UserFavorites | None:
        # Would query the favorites table
        # Placeholder implementation
        return None
    
    async def save(self, favorites: UserFavorites) -> None:
        # Would upsert favorites to database
        pass
    
    async def delete(self, user_id: str) -> bool:
        # Would delete from database
        return False


# =============================================================================
# Favorites Manager
# =============================================================================

class FavoritesManager:
    """
    Manages user favorites with pluggable storage.
    """
    
    def __init__(self, storage: FavoritesStorage | None = None):
        self.storage = storage or InMemoryFavoritesStorage()
    
    async def get_favorites(self, user_id: str) -> UserFavorites:
        """Get or create favorites for a user."""
        favorites = await self.storage.get(user_id)
        if favorites is None:
            favorites = UserFavorites(user_id=user_id)
        return favorites
    
    async def add_favorite(
        self,
        user_id: str,
        animal_id: int,
        notes: str = "",
    ) -> FavoriteAnimal:
        """Add an animal to user's favorites."""
        favorites = await self.get_favorites(user_id)
        favorite = favorites.add(animal_id, notes)
        await self.storage.save(favorites)
        return favorite
    
    async def remove_favorite(
        self,
        user_id: str,
        animal_id: int,
    ) -> bool:
        """Remove an animal from user's favorites."""
        favorites = await self.get_favorites(user_id)
        removed = favorites.remove(animal_id)
        if removed:
            await self.storage.save(favorites)
        return removed
    
    async def is_favorited(
        self,
        user_id: str,
        animal_id: int,
    ) -> bool:
        """Check if an animal is in user's favorites."""
        favorites = await self.get_favorites(user_id)
        return favorites.has(animal_id)
    
    async def get_favorite_animals(
        self,
        user_id: str,
        db_session: Any = None,
    ) -> list[dict]:
        """
        Get full animal data for all favorites.
        
        Args:
            user_id: User identifier
            db_session: Database session for fetching animal data
        
        Returns:
            List of animal dictionaries with favorite metadata
        """
        favorites = await self.get_favorites(user_id)
        animal_ids = favorites.get_animal_ids()
        
        if not animal_ids or db_session is None:
            return []
        
        # Fetch animal data from database
        from backend.app import models
        
        animals = (
            db_session.query(models.Animal)
            .filter(models.Animal.id.in_(animal_ids))
            .all()
        )
        
        # Add favorite metadata
        result = []
        for animal in animals:
            fav = favorites.get(animal.id)
            animal_dict = {
                "id": animal.id,
                "name": animal.name,
                "species": animal.species,
                "breed": animal.breed,
                # ... other fields
                "favorited_at": fav.added_at.isoformat() if fav else None,
                "favorite_notes": fav.notes if fav else None,
            }
            result.append(animal_dict)
        
        return result
    
    async def clear_favorites(self, user_id: str) -> bool:
        """Clear all favorites for a user."""
        return await self.storage.delete(user_id)


# =============================================================================
# Anonymous User ID Generation
# =============================================================================

def generate_anonymous_user_id(
    session_id: str | None = None,
    fingerprint: str | None = None,
) -> str:
    """
    Generate a consistent anonymous user ID.
    
    For anonymous users, we use a combination of session ID
    and browser fingerprint to create a stable identifier.
    """
    data = f"{session_id or ''}-{fingerprint or ''}"
    return f"anon_{hashlib.sha256(data.encode()).hexdigest()[:16]}"


# =============================================================================
# Global Instance
# =============================================================================

_favorites_manager: FavoritesManager | None = None


def get_favorites_manager() -> FavoritesManager:
    """Get the global favorites manager."""
    global _favorites_manager
    if _favorites_manager is None:
        _favorites_manager = FavoritesManager()
    return _favorites_manager


def set_favorites_storage(storage: FavoritesStorage):
    """Set the favorites storage backend."""
    global _favorites_manager
    _favorites_manager = FavoritesManager(storage)

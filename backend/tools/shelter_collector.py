#!/usr/bin/env python3
"""
===============================================================================
Waiting The Longest™ - Shelter Collector Tool
===============================================================================
Purpose: Process and store shelter data collected by the Copilot agent.
         Validates shelter data, performs upsert operations, and maintains
         collection progress tracking.

Author: Waiting The Longest™ Development Team
Last Updated: 2025-12-04
Dependencies: sqlalchemy, json
Related Files: models.py, state_collection_tracker.json

IMPORTANT: Any changes to this file MUST be documented in OWNERS_MANUAL.md

Usage:
    from tools.shelter_collector import ShelterCollector

    collector = ShelterCollector(db_session)
    result = collector.process_state_data(state_data)

CLI Usage:
    python shelter_collector.py --state TX --file TX_shelters.json
    python shelter_collector.py --show-progress
    python shelter_collector.py --next-state
===============================================================================
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from app.models import Shelter
    from app.database import SessionLocal, engine
    from sqlalchemy.orm import Session
except ImportError:
    # Allow module to be imported for testing without database
    Shelter = None
    SessionLocal = None
    engine = None
    Session = None

logger = logging.getLogger(__name__)

# Constants
SOURCE_NAME = "copilot_agent_collection"
DATA_DIR = Path(__file__).parent.parent / "data"
TRACKER_FILE = DATA_DIR / "state_collection_tracker.json"
SHELTERS_DIR = DATA_DIR / "collected_shelters"

# Valid organization types
VALID_ORG_TYPES = {
    "shelter", "rescue", "humane_society", "spca", "aspca",
    "animal_control", "nonprofit", "sanctuary", "foster_network"
}

# All 50 US states with abbreviations
US_STATES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
    "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
    "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming"
}


@dataclass
class ShelterData:
    """Validated shelter data structure"""
    name: str
    source: str = SOURCE_NAME
    external_id: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    org_type: Optional[str] = None
    description: Optional[str] = None


@dataclass
class CollectionResult:
    """Result of a collection operation"""
    success: bool
    state: str
    total_processed: int = 0
    inserted: int = 0
    updated: int = 0
    skipped: int = 0
    errors: List[str] = field(default_factory=list)
    message: str = ""


class ValidationError(Exception):
    """Raised when shelter data validation fails"""
    pass


class ShelterCollector:
    """
    Processes shelter data from the Copilot agent collection.

    This class handles:
    - Validation of shelter data against the Shelter model
    - Upsert operations (insert or update based on name + state)
    - Progress tracking for 50-state collection
    - File-based storage for review before database insertion

    Attributes:
        db: SQLAlchemy database session

    Example:
        >>> collector = ShelterCollector(db_session)
        >>> state_data = {
        ...     "state": "TX",
        ...     "state_full": "Texas",
        ...     "shelters": [{"name": "Austin Pets Alive!", ...}]
        ... }
        >>> result = collector.process_state_data(state_data)
        >>> print(f"Processed {result.total_processed} shelters")
    """

    def __init__(self, db: Optional[Session] = None):
        """
        Initialize the shelter collector.

        Args:
            db: SQLAlchemy database session. If None, only file operations
                are available (no database upserts).
        """
        self.db = db
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Ensure required directories exist"""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        SHELTERS_DIR.mkdir(parents=True, exist_ok=True)

    def validate_shelter(self, data: Dict[str, Any]) -> ShelterData:
        """
        Validate shelter data against required schema.

        Args:
            data: Raw shelter data dictionary

        Returns:
            Validated ShelterData instance

        Raises:
            ValidationError: If validation fails
        """
        # Required field: name
        name = data.get("name", "").strip()
        if not name:
            raise ValidationError("Shelter name is required")
        if len(name) > 200:
            raise ValidationError(
                f"Shelter name exceeds 200 characters: {name[:50]}..."
            )

        # Validate state if provided
        state = data.get("state", "").strip().upper() if data.get("state") else None
        if state and state not in US_STATES:
            raise ValidationError(f"Invalid state abbreviation: {state}")

        # Validate email format if provided
        email = data.get("email", "").strip() if data.get("email") else None
        if email and len(email) > 200:
            raise ValidationError("Email exceeds 200 characters")

        # Validate phone format if provided
        phone = data.get("phone", "").strip() if data.get("phone") else None
        if phone and len(phone) > 50:
            raise ValidationError("Phone exceeds 50 characters")

        # Validate other string fields
        city = data.get("city", "").strip() if data.get("city") else None
        if city and len(city) > 100:
            city = city[:100]

        address = data.get("address", "").strip() if data.get("address") else None
        if address and len(address) > 300:
            address = address[:300]

        zip_code = data.get("zip_code", "").strip() if data.get("zip_code") else None
        if zip_code and len(zip_code) > 20:
            zip_code = zip_code[:20]

        # Validate coordinates if provided
        latitude = data.get("latitude")
        longitude = data.get("longitude")
        if latitude is not None:
            try:
                latitude = float(latitude)
                if not -90 <= latitude <= 90:
                    latitude = None
            except (ValueError, TypeError):
                latitude = None
        if longitude is not None:
            try:
                longitude = float(longitude)
                if not -180 <= longitude <= 180:
                    longitude = None
            except (ValueError, TypeError):
                longitude = None

        # Normalize organization type
        org_type = None
        if data.get("type"):
            # Normalize: lowercase, replace spaces/hyphens with underscores, collapse multiple
            org_type = data.get("type", "").strip().lower()
            org_type = org_type.replace("-", "_").replace(" ", "_")
            # Collapse multiple underscores
            while "__" in org_type:
                org_type = org_type.replace("__", "_")
            org_type = org_type.strip("_")
        if org_type and org_type not in VALID_ORG_TYPES:
            org_type = "nonprofit"  # Default to nonprofit if unknown

        description = None
        if data.get("description"):
            description = data.get("description", "").strip()[:1000]

        return ShelterData(
            name=name,
            source=SOURCE_NAME,
            external_id=data.get("external_id"),
            email=email,
            phone=phone,
            website=data.get("website", "").strip() if data.get("website") else None,
            address=address,
            city=city,
            state=state,
            zip_code=zip_code,
            latitude=latitude,
            longitude=longitude,
            org_type=org_type,
            description=description
        )

    def upsert_shelter(self, shelter_data: ShelterData) -> Tuple[bool, str]:
        """
        Insert or update a shelter record in the database.

        Uses name + state as the unique identifier for upsert logic.

        Args:
            shelter_data: Validated ShelterData instance

        Returns:
            Tuple of (is_new, action_taken) where action_taken is
            "inserted", "updated", or "skipped"
        """
        if not self.db or Shelter is None:
            return (False, "skipped")

        # Look for existing shelter by name and state
        existing = self.db.query(Shelter).filter(
            Shelter.name == shelter_data.name,
            Shelter.state == shelter_data.state
        ).first()

        if existing:
            # Update existing record
            if shelter_data.email:
                existing.email = shelter_data.email
            if shelter_data.phone:
                existing.phone = shelter_data.phone
            if shelter_data.website:
                existing.website = shelter_data.website
            if shelter_data.address:
                existing.address = shelter_data.address
            if shelter_data.city:
                existing.city = shelter_data.city
            if shelter_data.zip_code:
                existing.zip_code = shelter_data.zip_code
            if shelter_data.latitude is not None:
                existing.latitude = shelter_data.latitude
            if shelter_data.longitude is not None:
                existing.longitude = shelter_data.longitude
            existing.updated_at = datetime.utcnow()
            return (False, "updated")
        else:
            # Insert new record
            new_shelter = Shelter(
                name=shelter_data.name,
                source=shelter_data.source,
                external_id=shelter_data.external_id,
                email=shelter_data.email,
                phone=shelter_data.phone,
                website=shelter_data.website,
                address=shelter_data.address,
                city=shelter_data.city,
                state=shelter_data.state,
                zip_code=shelter_data.zip_code,
                latitude=shelter_data.latitude,
                longitude=shelter_data.longitude,
                total_animals=0
            )
            self.db.add(new_shelter)
            return (True, "inserted")

    def process_state_data(self, state_data: Dict[str, Any],
                           save_to_file: bool = True,
                           insert_to_db: bool = True) -> CollectionResult:
        """
        Process shelter data for a state.

        Args:
            state_data: Dictionary containing state info and shelters list
            save_to_file: Whether to save data to JSON file
            insert_to_db: Whether to insert/update database records

        Returns:
            CollectionResult with processing statistics
        """
        state = state_data.get("state", "").upper()
        if state not in US_STATES:
            return CollectionResult(
                success=False,
                state=state,
                message=f"Invalid state: {state}"
            )

        shelters = state_data.get("shelters", [])
        if not shelters:
            return CollectionResult(
                success=False,
                state=state,
                message=f"No shelters provided for {state}"
            )

        result = CollectionResult(success=True, state=state)
        validated_shelters = []

        # Validate all shelters
        for i, shelter in enumerate(shelters):
            try:
                validated = self.validate_shelter(shelter)
                validated.state = state  # Ensure state is set
                validated_shelters.append(validated)
            except ValidationError as e:
                result.errors.append(f"Shelter {i + 1}: {str(e)}")
                result.skipped += 1

        result.total_processed = len(shelters)

        # Save to file if requested
        if save_to_file and validated_shelters:
            file_data = {
                "state": state,
                "state_full": US_STATES[state],
                "collection_date": datetime.utcnow().isoformat(),
                "total_count": len(validated_shelters),
                "shelters": [
                    {
                        "name": s.name,
                        "type": s.org_type,
                        "email": s.email,
                        "phone": s.phone,
                        "website": s.website,
                        "address": s.address,
                        "city": s.city,
                        "state": s.state,
                        "zip_code": s.zip_code,
                        "latitude": s.latitude,
                        "longitude": s.longitude,
                        "description": s.description
                    }
                    for s in validated_shelters
                ]
            }
            file_path = SHELTERS_DIR / f"{state}_shelters.json"
            with open(file_path, 'w') as f:
                json.dump(file_data, f, indent=2)
            logger.info(f"Saved {len(validated_shelters)} shelters to {file_path}")

        # Insert to database if requested
        if insert_to_db and validated_shelters and self.db:
            for shelter_data in validated_shelters:
                try:
                    is_new, action = self.upsert_shelter(shelter_data)
                    if action == "inserted":
                        result.inserted += 1
                    elif action == "updated":
                        result.updated += 1
                    else:
                        result.skipped += 1
                except Exception as e:
                    result.errors.append(
                        f"DB error for {shelter_data.name}: {str(e)}"
                    )
                    result.skipped += 1

            try:
                self.db.commit()
            except Exception as e:
                self.db.rollback()
                result.success = False
                result.errors.append(f"Commit failed: {str(e)}")

        # Update tracker
        self._update_tracker(state, len(validated_shelters))

        result.message = (
            f"Processed {result.total_processed} shelters for {US_STATES[state]}: "
            f"{result.inserted} inserted, {result.updated} updated, "
            f"{result.skipped} skipped"
        )

        return result

    def _update_tracker(self, state: str, shelter_count: int) -> None:
        """Update the state collection tracker"""
        try:
            tracker = self.load_tracker()

            if state in tracker.get("states", {}):
                tracker["states"][state]["status"] = "completed"
                tracker["states"][state]["last_collection"] = (
                    datetime.utcnow().isoformat()
                )
                tracker["states"][state]["shelter_count"] = shelter_count

                # Update metadata
                completed = sum(
                    1 for s in tracker["states"].values()
                    if s.get("status") == "completed"
                )
                total_shelters = sum(
                    s.get("shelter_count", 0) for s in tracker["states"].values()
                )
                tracker["metadata"]["completed_count"] = completed
                tracker["metadata"]["total_shelters_collected"] = total_shelters
                tracker["metadata"]["last_updated"] = datetime.utcnow().isoformat()

                self.save_tracker(tracker)
        except Exception as e:
            logger.warning(f"Failed to update tracker: {e}")

    @staticmethod
    def load_tracker() -> Dict[str, Any]:
        """Load the state collection tracker"""
        if TRACKER_FILE.exists():
            with open(TRACKER_FILE, 'r') as f:
                return json.load(f)
        return {"metadata": {}, "states": {}}

    @staticmethod
    def save_tracker(tracker: Dict[str, Any]) -> None:
        """Save the state collection tracker"""
        with open(TRACKER_FILE, 'w') as f:
            json.dump(tracker, f, indent=2)

    def get_next_state(self) -> Optional[str]:
        """
        Get the next state to collect.

        Returns:
            State abbreviation or None if all states are completed
        """
        tracker = self.load_tracker()
        for abbr, data in tracker.get("states", {}).items():
            if data.get("status") == "pending":
                return abbr
        return None

    def get_progress(self) -> Dict[str, Any]:
        """
        Get collection progress summary.

        Returns:
            Dictionary with progress statistics
        """
        tracker = self.load_tracker()
        states = tracker.get("states", {})

        completed = [
            abbr for abbr, data in states.items()
            if data.get("status") == "completed"
        ]
        pending = [
            abbr for abbr, data in states.items()
            if data.get("status") == "pending"
        ]
        in_progress = [
            abbr for abbr, data in states.items()
            if data.get("status") == "in_progress"
        ]

        total_shelters = sum(s.get("shelter_count", 0) for s in states.values())

        pct = round(len(completed) / len(states) * 100, 1) if states else 0

        return {
            "total_states": len(states),
            "completed_count": len(completed),
            "pending_count": len(pending),
            "in_progress_count": len(in_progress),
            "total_shelters_collected": total_shelters,
            "completed_states": completed,
            "pending_states": pending,
            "in_progress_states": in_progress,
            "progress_percentage": pct
        }

    def load_state_shelters(self, state: str) -> Optional[Dict[str, Any]]:
        """
        Load collected shelters for a state from file.

        Args:
            state: State abbreviation (e.g., "TX")

        Returns:
            Dictionary with shelter data or None if file doesn't exist
        """
        state = state.upper()
        file_path = SHELTERS_DIR / f"{state}_shelters.json"
        if file_path.exists():
            with open(file_path, 'r') as f:
                return json.load(f)
        return None

    def insert_from_file(self, state: str) -> CollectionResult:
        """
        Insert shelters from a saved state file into the database.

        Args:
            state: State abbreviation

        Returns:
            CollectionResult with insertion statistics
        """
        data = self.load_state_shelters(state)
        if not data:
            return CollectionResult(
                success=False,
                state=state,
                message=f"No saved data found for {state}"
            )

        return self.process_state_data(data, save_to_file=False, insert_to_db=True)


def main():
    """CLI entry point for the shelter collector"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Waiting The Longest™ - Shelter Data Collector"
    )
    parser.add_argument(
        "--state",
        type=str,
        help="State abbreviation to process (e.g., TX, CA)"
    )
    parser.add_argument(
        "--file",
        type=str,
        help="JSON file with shelter data to process"
    )
    parser.add_argument(
        "--show-progress",
        action="store_true",
        help="Show collection progress"
    )
    parser.add_argument(
        "--next-state",
        action="store_true",
        help="Show next state to collect"
    )
    parser.add_argument(
        "--insert",
        action="store_true",
        help="Insert shelters from saved file into database"
    )
    parser.add_argument(
        "--no-db",
        action="store_true",
        help="Skip database operations (file only)"
    )

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    # Create collector (with or without database)
    db = None
    if not args.no_db and SessionLocal is not None:
        try:
            db = SessionLocal()
        except Exception as e:
            logger.warning(f"Could not connect to database: {e}")

    collector = ShelterCollector(db)

    try:
        if args.show_progress:
            progress = collector.get_progress()
            print("\n" + "=" * 60)
            print("Waiting The Longest™ - Shelter Collection Progress")
            print("=" * 60)
            print(f"\nTotal States: {progress['total_states']}")
            print(
                f"Completed: {progress['completed_count']} "
                f"({progress['progress_percentage']}%)"
            )
            print(f"Pending: {progress['pending_count']}")
            print(f"In Progress: {progress['in_progress_count']}")
            print(f"Total Shelters Collected: {progress['total_shelters_collected']}")

            if progress['completed_states']:
                print(
                    f"\nCompleted States: "
                    f"{', '.join(sorted(progress['completed_states']))}"
                )
            print()

        elif args.next_state:
            next_state = collector.get_next_state()
            if next_state:
                print(
                    f"Next state to collect: {next_state} ({US_STATES[next_state]})"
                )
            else:
                print("All states have been collected!")

        elif args.insert and args.state:
            result = collector.insert_from_file(args.state.upper())
            print(f"\n{result.message}")
            if result.errors:
                print(f"Errors: {len(result.errors)}")
                for error in result.errors[:5]:
                    print(f"  - {error}")

        elif args.file:
            with open(args.file, 'r') as f:
                data = json.load(f)
            result = collector.process_state_data(
                data,
                save_to_file=True,
                insert_to_db=not args.no_db
            )
            print(f"\n{result.message}")
            if result.errors:
                print(f"Errors: {len(result.errors)}")
                for error in result.errors[:5]:
                    print(f"  - {error}")
        else:
            parser.print_help()
    finally:
        if db:
            db.close()


if __name__ == "__main__":
    main()

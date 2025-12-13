#!/usr/bin/env python3
"""
===============================================================================
ProPublica Nonprofit Explorer Ingest Tool
===============================================================================
Ingests animal shelter and rescue nonprofits from ProPublica's FREE API.

This API sources data directly from IRS Form 990 filings - the same source
as CauseIQ's 28,259 animal shelters, but completely free!

NTEE Codes for animal organizations:
- D20: Animal Protection and Welfare
- D30: Wildlife Preservation, Protection
- D60: Animal Services N.E.C.

API Documentation: https://projects.propublica.org/nonprofits/api
===============================================================================
"""

import os
import sys
import time
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, field

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import aiohttp
from tqdm import tqdm

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ProPublica API Configuration
PROPUBLICA_BASE_URL = "https://projects.propublica.org/nonprofits/api/v2"
RESULTS_PER_PAGE = 25


@dataclass
class NonprofitOrg:
    """Nonprofit organization data structure."""
    ein: str
    name: str
    city: Optional[str] = None
    state: Optional[str] = None
    ntee_code: Optional[str] = None
    subsection_code: Optional[str] = None
    has_filings: bool = False
    revenue: Optional[int] = None
    assets: Optional[int] = None
    formatted_ein: Optional[str] = None


# Animal-related search terms for comprehensive coverage
ANIMAL_SEARCH_TERMS = [
    "animal shelter",
    "animal rescue",
    "humane society",
    "spca",
    "aspca",
    "dog rescue",
    "cat rescue",
    "pet rescue",
    "animal welfare",
    "animal protection",
    "wildlife rescue",
    "pet adoption",
    "dog shelter",
    "cat shelter",
    "animal league",
    "animal sanctuary",
    "animal hospital",  # Many are nonprofits
    "no kill shelter",
    "animal control",
    "veterinary",
    "animal foundation",
    "pet foundation",
    "breed rescue",
    "equine rescue",
    "horse rescue",
    "bird rescue",
    "rabbit rescue",
    "exotic animal",
    "feral cat",
    "stray animal",
    "animal assistance",
    "pet assistance",
]


async def search_nonprofits(session: aiohttp.ClientSession, query: str, page: int = 0) -> Dict:
    """
    Search ProPublica's Nonprofit Explorer API.

    Args:
        session: aiohttp client session
        query: Search query
        page: Page number (0-indexed)

    Returns:
        API response as dict
    """
    url = f"{PROPUBLICA_BASE_URL}/search.json"
    params = {
        "q": query,
        "page": page
    }

    try:
        async with session.get(url, params=params, timeout=30) as response:
            if response.status == 200:
                return await response.json()
            else:
                logger.warning(f"API returned {response.status} for query: {query}")
                return {}
    except Exception as e:
        logger.error(f"Error searching for '{query}': {e}")
        return {}


async def get_org_details(session: aiohttp.ClientSession, ein: str) -> Dict:
    """
    Get detailed information about a specific nonprofit.

    Args:
        session: aiohttp client session
        ein: Employer Identification Number

    Returns:
        Org details dict
    """
    url = f"{PROPUBLICA_BASE_URL}/organizations/{ein}.json"

    try:
        async with session.get(url, timeout=30) as response:
            if response.status == 200:
                return await response.json()
            return {}
    except Exception as e:
        logger.error(f"Error getting details for EIN {ein}: {e}")
        return {}


async def ingest_all_animal_nonprofits(max_per_term: int = 1000) -> List[NonprofitOrg]:
    """
    Ingest all animal-related nonprofits from ProPublica.

    Args:
        max_per_term: Maximum results per search term

    Returns:
        List of NonprofitOrg objects
    """
    all_orgs = {}  # Use dict keyed by EIN to dedupe

    async with aiohttp.ClientSession() as session:
        for term in tqdm(ANIMAL_SEARCH_TERMS, desc="Searching terms"):
            page = 0
            term_count = 0

            while term_count < max_per_term:
                data = await search_nonprofits(session, term, page)

                if not data or "organizations" not in data:
                    break

                orgs = data.get("organizations", [])
                if not orgs:
                    break

                for org in orgs:
                    ein = org.get("ein")
                    if not ein or ein in all_orgs:
                        continue

                    nonprofit = NonprofitOrg(
                        ein=str(ein),
                        name=org.get("name", ""),
                        city=org.get("city"),
                        state=org.get("state"),
                        ntee_code=org.get("ntee_code"),
                        subsection_code=org.get("subsection_code"),
                        has_filings=org.get("have_filings", False),
                        formatted_ein=org.get("ein_formatted")
                    )
                    all_orgs[ein] = nonprofit
                    term_count += 1

                # Check if more pages
                total_pages = data.get("total_pages", 1)
                if page >= total_pages - 1:
                    break

                page += 1

                # Rate limiting - be nice to ProPublica
                await asyncio.sleep(0.2)

            logger.info(f"Found {term_count} orgs for '{term}' (Total unique: {len(all_orgs)})")

    return list(all_orgs.values())


async def ingest_by_state(state: str, max_results: int = 5000) -> List[NonprofitOrg]:
    """
    Ingest animal nonprofits for a specific state.

    Args:
        state: 2-letter state code
        max_results: Maximum results to return

    Returns:
        List of NonprofitOrg objects for that state
    """
    state_orgs = {}

    async with aiohttp.ClientSession() as session:
        for term in ANIMAL_SEARCH_TERMS[:10]:  # Use top 10 terms
            query = f"{term} {state}"
            page = 0

            while len(state_orgs) < max_results:
                data = await search_nonprofits(session, query, page)

                if not data or "organizations" not in data:
                    break

                orgs = data.get("organizations", [])
                if not orgs:
                    break

                for org in orgs:
                    # Filter to match state
                    org_state = org.get("state", "")
                    if org_state != state:
                        continue

                    ein = org.get("ein")
                    if not ein or ein in state_orgs:
                        continue

                    nonprofit = NonprofitOrg(
                        ein=str(ein),
                        name=org.get("name", ""),
                        city=org.get("city"),
                        state=org.get("state"),
                        ntee_code=org.get("ntee_code"),
                        subsection_code=org.get("subsection_code"),
                        has_filings=org.get("have_filings", False),
                        formatted_ein=org.get("ein_formatted")
                    )
                    state_orgs[ein] = nonprofit

                # Check if more pages
                total_pages = data.get("total_pages", 1)
                if page >= total_pages - 1:
                    break

                page += 1
                await asyncio.sleep(0.2)

    logger.info(f"Found {len(state_orgs)} animal orgs in {state}")
    return list(state_orgs.values())


async def save_to_database(orgs: List[NonprofitOrg]) -> int:
    """
    Save nonprofits to database as shelters.

    Args:
        orgs: List of NonprofitOrg objects

    Returns:
        Number of new records saved
    """
    try:
        from app.database import SessionLocal
        from app.models import Shelter

        db = SessionLocal()
        saved_count = 0

        for org in tqdm(orgs, desc="Saving to DB"):
            # Check if already exists by name and state
            existing = db.query(Shelter).filter(
                Shelter.name == org.name,
                Shelter.state == org.state
            ).first()

            if existing:
                # Update EIN if we have it
                if org.ein and not existing.external_id:
                    existing.external_id = f"ein:{org.ein}"
                    existing.updated_at = datetime.utcnow()
            else:
                # Create new shelter
                shelter = Shelter(
                    name=org.name,
                    city=org.city,
                    state=org.state,
                    source="propublica_990",
                    external_id=f"ein:{org.ein}" if org.ein else None,
                    org_type="nonprofit"
                )
                db.add(shelter)
                saved_count += 1

                # Commit in batches
                if saved_count % 100 == 0:
                    db.commit()

        db.commit()
        db.close()

        logger.info(f"Saved {saved_count} new organizations to database")
        return saved_count

    except Exception as e:
        logger.error(f"Database error: {e}")
        return 0


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Ingest animal nonprofits from ProPublica')
    parser.add_argument('--state', '-s', type=str, help='Specific state to ingest (e.g., MA)')
    parser.add_argument('--all', action='store_true', help='Ingest all states')
    parser.add_argument('--db', action='store_true', help='Save to database')
    parser.add_argument('--max', type=int, default=1000, help='Max results per search term')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    print("=" * 60)
    print("ProPublica Nonprofit Explorer - Animal Org Ingester")
    print("=" * 60)
    print("Source: IRS Form 990 filings (same source as CauseIQ)")
    print()

    if args.state:
        state = args.state.upper()
        print(f"Ingesting animal nonprofits for: {state}")
        orgs = await ingest_by_state(state, args.max)
    else:
        print("Ingesting ALL animal nonprofits nationwide...")
        orgs = await ingest_all_animal_nonprofits(args.max)

    print(f"\n{'=' * 60}")
    print(f"Total organizations found: {len(orgs)}")

    # Show sample
    if orgs:
        print("\nSample organizations:")
        for org in orgs[:10]:
            print(f"  - {org.name}")
            if org.city and org.state:
                print(f"    Location: {org.city}, {org.state}")
            if org.ein:
                print(f"    EIN: {org.ein}")

    # State distribution
    state_counts = {}
    for org in orgs:
        if org.state:
            state_counts[org.state] = state_counts.get(org.state, 0) + 1

    if state_counts:
        print("\nTop 10 states by count:")
        for state, count in sorted(state_counts.items(), key=lambda x: -x[1])[:10]:
            print(f"  {state}: {count}")

    if args.db:
        print("\nSaving to database...")
        saved = await save_to_database(orgs)
        print(f"Saved {saved} new organizations")

    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(main())

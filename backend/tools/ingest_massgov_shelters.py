#!/usr/bin/env python3
"""
===============================================================================
Mass.gov Licensed Shelter Scraper
===============================================================================
Scrapes the official Massachusetts state directory of licensed animal shelters
and rescue organizations.

Source: https://www.mass.gov/lists/list-of-licensed-animal-shelters-and-rescue-organizations

This provides additional coverage beyond RescueGroups and Best Friends Network.
===============================================================================
"""

import os
import sys
import re
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import aiohttp
from bs4 import BeautifulSoup

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class MAShelter:
    """Massachusetts shelter data structure."""
    name: str
    city: Optional[str] = None
    state: str = "MA"
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    license_type: Optional[str] = None


async def scrape_massgov_directory() -> List[MAShelter]:
    """
    Scrape the Mass.gov licensed animal shelters directory.

    Returns:
        List of MAShelter objects.
    """
    url = "https://www.mass.gov/lists/list-of-licensed-animal-shelters-and-rescue-organizations"
    shelters = []

    logger.info(f"Fetching Mass.gov directory: {url}")

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=30) as response:
                if response.status != 200:
                    logger.error(f"Failed to fetch page: HTTP {response.status}")
                    return shelters

                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')

                # Mass.gov typically lists organizations in structured HTML
                # Look for list items, tables, or content blocks

                # Try finding main content area
                main_content = soup.find('main') or soup.find('article') or soup.find('div', class_='main-content')

                if not main_content:
                    main_content = soup

                # Look for organization listings
                # Mass.gov often uses accordion or list structures
                org_sections = main_content.find_all(['section', 'div', 'article'], class_=lambda x: x and ('org' in str(x).lower() or 'shelter' in str(x).lower() or 'rescue' in str(x).lower()))

                # Also look for list items that might contain shelter info
                list_items = main_content.find_all('li')

                logger.info(f"Found {len(list_items)} list items to parse")

                # Parse each list item for organization info
                for item in list_items:
                    text = item.get_text(strip=True)

                    # Skip navigation/menu items
                    if len(text) < 10 or len(text) > 500:
                        continue

                    # Look for patterns that indicate shelter entries
                    # Usually: Name, City/Address, Contact info
                    if any(keyword in text.lower() for keyword in ['rescue', 'shelter', 'animal', 'humane', 'spca', 'aspca', 'league']):
                        shelter = parse_shelter_entry(text, item)
                        if shelter:
                            shelters.append(shelter)

                # Also try to find links to individual org pages
                links = main_content.find_all('a', href=True)
                for link in links:
                    href = link.get('href', '')
                    text = link.get_text(strip=True)

                    # Check if this looks like an organization link
                    if any(kw in text.lower() for kw in ['rescue', 'shelter', 'humane', 'animal']):
                        if text not in [s.name for s in shelters]:
                            shelter = MAShelter(
                                name=text,
                                website=href if href.startswith('http') else None
                            )
                            shelters.append(shelter)

                logger.info(f"Parsed {len(shelters)} shelters from Mass.gov")

        except asyncio.TimeoutError:
            logger.error("Request timed out")
        except Exception as e:
            logger.error(f"Error scraping Mass.gov: {e}")

    return shelters


def parse_shelter_entry(text: str, element) -> Optional[MAShelter]:
    """
    Parse a shelter entry from text content.

    Args:
        text: Text content of the entry
        element: BeautifulSoup element for additional parsing

    Returns:
        MAShelter object or None
    """
    # Try to extract structured data
    lines = [l.strip() for l in text.split('\n') if l.strip()]

    if not lines:
        return None

    name = lines[0] if lines else text[:100]

    # Look for city patterns (often after name)
    city = None
    for line in lines[1:4]:
        # Massachusetts cities pattern
        if re.search(r'[A-Z][a-z]+,?\s*MA', line):
            match = re.search(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?),?\s*MA', line)
            if match:
                city = match.group(1)
                break

    # Look for phone numbers
    phone = None
    phone_match = re.search(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', text)
    if phone_match:
        phone = phone_match.group()

    # Look for email
    email = None
    email_match = re.search(r'[\w.+-]+@[\w-]+\.[\w.-]+', text)
    if email_match:
        email = email_match.group()

    # Look for website in element
    website = None
    link = element.find('a', href=True)
    if link:
        href = link.get('href', '')
        if href.startswith('http'):
            website = href

    return MAShelter(
        name=name,
        city=city,
        phone=phone,
        email=email,
        website=website
    )


async def scrape_additional_ma_sources() -> List[MAShelter]:
    """
    Scrape additional Massachusetts shelter sources.

    Returns:
        Combined list of shelters from multiple sources.
    """
    all_shelters = []

    # Source 1: Mass.gov official directory
    massgov_shelters = await scrape_massgov_directory()
    all_shelters.extend(massgov_shelters)

    # Source 2: MDAR (MA Dept of Agricultural Resources) might have listings
    # TODO: Add MDAR scraper if available

    # Source 3: Local MSPCA chapters
    mspca_locations = [
        MAShelter(name="MSPCA-Angell Boston", city="Boston", phone="617-522-7400", website="https://www.mspca.org"),
        MAShelter(name="MSPCA at Nevins Farm", city="Methuen", phone="978-687-7453", website="https://www.mspca.org/nevins-farm"),
        MAShelter(name="MSPCA Cape Cod", city="Centerville", phone="508-775-0940", website="https://www.mspca.org/cape-cod"),
        MAShelter(name="MSPCA Springfield", city="Springfield", phone="413-736-2992", website="https://www.mspca.org/springfield"),
    ]

    # Add MSPCA locations if not already present
    existing_names = {s.name.lower() for s in all_shelters}
    for mspca in mspca_locations:
        if mspca.name.lower() not in existing_names:
            all_shelters.append(mspca)

    logger.info(f"Total MA shelters found: {len(all_shelters)}")

    return all_shelters


async def save_to_database(shelters: List[MAShelter]) -> int:
    """
    Save scraped shelters to the database.

    Args:
        shelters: List of MAShelter objects

    Returns:
        Number of shelters saved/updated
    """
    try:
        from app.database import SessionLocal
        from app.models import Shelter

        db = SessionLocal()
        saved_count = 0

        for shelter in shelters:
            # Check if already exists
            existing = db.query(Shelter).filter(
                Shelter.name == shelter.name,
                Shelter.state == 'MA'
            ).first()

            if existing:
                # Update if we have new data
                if shelter.phone and not existing.phone:
                    existing.phone = shelter.phone
                if shelter.email and not existing.email:
                    existing.email = shelter.email
                if shelter.website and not existing.website:
                    existing.website = shelter.website
                if shelter.city and not existing.city:
                    existing.city = shelter.city
                existing.updated_at = datetime.utcnow()
            else:
                # Create new
                new_shelter = Shelter(
                    name=shelter.name,
                    city=shelter.city,
                    state='MA',
                    address=shelter.address,
                    phone=shelter.phone,
                    email=shelter.email,
                    website=shelter.website,
                    source='massgov_directory',
                    org_type=shelter.license_type or 'shelter'
                )
                db.add(new_shelter)
                saved_count += 1

        db.commit()
        db.close()

        logger.info(f"Saved {saved_count} new shelters to database")
        return saved_count

    except Exception as e:
        logger.error(f"Database error: {e}")
        return 0


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Scrape Mass.gov licensed shelter directory')
    parser.add_argument('--db', action='store_true', help='Save results to database')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    print("=" * 60)
    print("Mass.gov Licensed Shelter Scraper")
    print("=" * 60)

    shelters = await scrape_additional_ma_sources()

    print(f"\nFound {len(shelters)} Massachusetts shelters/rescues")

    if shelters:
        print("\nSample entries:")
        for shelter in shelters[:10]:
            print(f"  - {shelter.name}")
            if shelter.city:
                print(f"    City: {shelter.city}")
            if shelter.phone:
                print(f"    Phone: {shelter.phone}")
            if shelter.website:
                print(f"    Web: {shelter.website}")

    if args.db:
        print("\nSaving to database...")
        saved = await save_to_database(shelters)
        print(f"Saved {saved} new entries")

    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(main())

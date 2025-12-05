#!/usr/bin/env python3
"""
Rescue Entity Scraper Agent v2
==============================
Scrapes shelter/rescue data from multiple directory sources organized by state.
Uses established shelter directories instead of search engines.

NO breeders or pet stores - only legitimate rescues, shelters, and sanctuaries.
"""

import json
import os
import sys
import re
import time
import random
import argparse
from datetime import datetime
from urllib.parse import urlparse, quote_plus, urljoin

import requests
from bs4 import BeautifulSoup

# Add parent directory for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from app.database import SessionLocal, init_db
from app.models import Shelter

# Initialize database
init_db()

# Constants
COUNTIES_FILE = os.path.join(os.path.dirname(__file__), 'us_counties.json')
PROGRESS_FILE = os.path.join(os.path.dirname(__file__), 'scraper_progress.json')
RESULTS_FILE = os.path.join(os.path.dirname(__file__), 'discovered_shelters.json')

# Request headers
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}

# State abbreviation to full name mapping
STATE_NAMES = {
    'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas',
    'CA': 'California', 'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware',
    'FL': 'Florida', 'GA': 'Georgia', 'HI': 'Hawaii', 'ID': 'Idaho',
    'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa', 'KS': 'Kansas',
    'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland',
    'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi',
    'MO': 'Missouri', 'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada',
    'NH': 'New Hampshire', 'NJ': 'New Jersey', 'NM': 'New Mexico', 'NY': 'New York',
    'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio', 'OK': 'Oklahoma',
    'OR': 'Oregon', 'PA': 'Pennsylvania', 'RI': 'Rhode Island', 'SC': 'South Carolina',
    'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah',
    'VT': 'Vermont', 'VA': 'Virginia', 'WA': 'Washington', 'WV': 'West Virginia',
    'WI': 'Wisconsin', 'WY': 'Wyoming', 'DC': 'Washington DC'
}

# Terms that indicate NOT a shelter
EXCLUDE_TERMS = [
    'breeder', 'breeding', 'puppies for sale', 'kittens for sale',
    'pet store', 'pet shop', 'petco', 'petsmart',
    'puppy mill', 'dog for sale', 'cat for sale',
    'stud service', 'akc registered', 'ckc registered'
]


def load_progress():
    """Load progress from file to resume scraping."""
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'completed_states': [], 'discovered_count': 0, 'last_updated': None}


def save_progress(progress):
    """Save progress to file."""
    progress['last_updated'] = datetime.now().isoformat()
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(progress, f, indent=2)


def load_discovered():
    """Load discovered shelters from file."""
    if os.path.exists(RESULTS_FILE):
        with open(RESULTS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'shelters': [], 'last_updated': None}


def save_discovered(discovered):
    """Save discovered shelters to file."""
    discovered['last_updated'] = datetime.now().isoformat()
    with open(RESULTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(discovered, f, indent=2)


def is_excluded_org(name, description=''):
    """Check if organization name/description indicates a breeder or pet store."""
    text = f"{name} {description}".lower()
    return any(term in text for term in EXCLUDE_TERMS)


def normalize_url(url):
    """Normalize URL for deduplication."""
    if not url:
        return None
    url = url.lower().strip()
    url = url.rstrip('/')
    url = re.sub(r'^(https?://)www\.', r'\1', url)
    return url


# NOTE: Petfinder does NOT have a public API. DO NOT add Petfinder integration.
# See NO_PETFINDER_API.md in the project root for details.


def scrape_shelterlist(state_code):
    """
    Scrape shelters from shelterlist.com by state.
    """
    shelters = []
    state_name = STATE_NAMES.get(state_code, state_code).lower().replace(' ', '-')

    url = f"https://www.shelterlist.com/{state_name}/"

    try:
        print(f"    Checking ShelterList for {state_code}...")
        response = requests.get(url, headers=HEADERS, timeout=15)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')

            # Find shelter entries
            for entry in soup.select('.shelter-entry, .listing, article'):
                try:
                    name_elem = entry.select_one('h2, h3, .title, .name')

                    if name_elem:
                        name = name_elem.get_text(strip=True)

                        if is_excluded_org(name):
                            continue

                        org = {
                            'name': name,
                            'state': state_code,
                            'source': 'shelterlist'
                        }

                        # Try to get address/city
                        address_elem = entry.select_one('.address, .location')
                        if address_elem:
                            org['address'] = address_elem.get_text(strip=True)

                        # Try to get phone
                        phone_elem = entry.select_one('.phone, [href^="tel:"]')
                        if phone_elem:
                            phone = phone_elem.get_text(strip=True)
                            if not phone and phone_elem.get('href'):
                                phone = phone_elem.get('href').replace('tel:', '')
                            org['phone'] = phone

                        # Try to get website
                        website_elem = entry.select_one('a[href*="http"]:not([href*="shelterlist"])')
                        if website_elem:
                            org['website'] = website_elem.get('href')

                        shelters.append(org)
                except Exception:
                    continue

    except Exception as e:
        print(f"    ShelterList error: {e}")

    return shelters


def scrape_humanesociety_directory(state_code):
    """
    Scrape from HSUS directory pages.
    """
    shelters = []

    try:
        print(f"    Checking Humane Society directory for {state_code}...")
        # HSUS has a different URL structure
        url = f"https://www.humanesociety.org/resources/find-local-animal-shelter?state={state_code}"
        response = requests.get(url, headers=HEADERS, timeout=15)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')

            for listing in soup.select('.shelter-listing, .organization'):
                try:
                    name_elem = listing.select_one('h3, .org-name')
                    if name_elem:
                        name = name_elem.get_text(strip=True)
                        if not is_excluded_org(name):
                            shelters.append({
                                'name': name,
                                'state': state_code,
                                'source': 'hsus_directory'
                            })
                except Exception:
                    continue

    except Exception as e:
        print(f"    HSUS error: {e}")

    return shelters


def scrape_adoptapet_directory(state_code):
    """
    Scrape shelters from Adopt-a-Pet.com by state.
    """
    shelters = []
    state_name = STATE_NAMES.get(state_code, state_code).lower().replace(' ', '-')

    # Adopt-a-Pet uses a search API
    url = f"https://www.adoptapet.com/shelter-search/{state_name}"

    try:
        print(f"    Checking Adopt-a-Pet for {state_code}...")
        response = requests.get(url, headers=HEADERS, timeout=15)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')

            for shelter_div in soup.select('.shelter-card, .shelter-result, [data-shelter-id]'):
                try:
                    name_elem = shelter_div.select_one('.shelter-name, h3, h4')
                    if name_elem:
                        name = name_elem.get_text(strip=True)

                        if is_excluded_org(name):
                            continue

                        org = {
                            'name': name,
                            'state': state_code,
                            'source': 'adoptapet_directory'
                        }

                        location_elem = shelter_div.select_one('.location, .city-state')
                        if location_elem:
                            location = location_elem.get_text(strip=True)
                            if ',' in location:
                                org['city'] = location.split(',')[0].strip()

                        link_elem = shelter_div.select_one('a[href*="/shelter/"]')
                        if link_elem:
                            org['listing_url'] = urljoin('https://www.adoptapet.com', link_elem.get('href', ''))

                        shelters.append(org)
                except Exception:
                    continue

    except Exception as e:
        print(f"    Adopt-a-Pet error: {e}")

    return shelters


def scrape_rescuegroups_api(state_code):
    """
    Try to get data from RescueGroups public API.
    """
    shelters = []

    try:
        print(f"    Checking RescueGroups for {state_code}...")
        # RescueGroups has a public search page
        url = f"https://toolkit.rescuegroups.org/of/v1.1/search/shelters?state={state_code}"

        response = requests.get(url, headers={
            **HEADERS,
            'Accept': 'application/json'
        }, timeout=15)

        if response.status_code == 200:
            try:
                data = response.json()
                if 'data' in data:
                    for org in data['data'][:50]:  # Limit per request
                        if is_excluded_org(org.get('name', '')):
                            continue
                        shelters.append({
                            'name': org.get('name'),
                            'city': org.get('city'),
                            'state': state_code,
                            'website': org.get('website'),
                            'phone': org.get('phone'),
                            'email': org.get('email'),
                            'source': 'rescuegroups_api'
                        })
            except json.JSONDecodeError:
                pass

    except Exception as e:
        print(f"    RescueGroups error: {e}")

    return shelters


def scrape_animalfoundation_directory(state_code):
    """
    Scrape from state animal foundation directories.
    """
    shelters = []
    state_name = STATE_NAMES.get(state_code, state_code).lower()

    # Try state-specific directories
    urls_to_try = [
        f"https://www.{state_name}animalshelter.org/shelters/",
        f"https://www.{state_name}humanesociety.org/",
        f"https://{state_name}spca.org/",
    ]

    for url in urls_to_try:
        try:
            response = requests.get(url, headers=HEADERS, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')

                # Look for shelter links/listings
                for link in soup.select('a[href*="shelter"], a[href*="rescue"], a[href*="animal"]'):
                    name = link.get_text(strip=True)
                    if name and len(name) > 3 and not is_excluded_org(name):
                        shelters.append({
                            'name': name,
                            'state': state_code,
                            'website': urljoin(url, link.get('href', '')),
                            'source': 'state_directory'
                        })
        except Exception:
            continue

    return shelters


def scrape_state(state_code, db):
    """
    Scrape all sources for a single state.
    Returns list of discovered organizations.
    """
    all_shelters = []
    seen_names = set()

    # Get existing shelters for this state
    existing = db.query(Shelter.name, Shelter.website).filter(
        Shelter.state == state_code
    ).all()
    existing_names = {r[0].lower().strip()[:50] for r in existing if r[0]}
    existing_urls = {normalize_url(r[1]) for r in existing if r[1]}

    # Try multiple sources
    # NOTE: Petfinder does NOT have an API - do not add it here
    sources = [
        ('ShelterList', scrape_shelterlist),
        ('AdoptAPet', scrape_adoptapet_directory),
        ('RescueGroups', scrape_rescuegroups_api),
    ]

    for source_name, scrape_func in sources:
        try:
            results = scrape_func(state_code)
            print(f"      {source_name}: {len(results)} found")

            for org in results:
                name_key = org['name'].lower().strip()[:50] if org.get('name') else ''
                url_key = normalize_url(org.get('website'))

                # Skip duplicates
                if name_key in seen_names or name_key in existing_names:
                    continue
                if url_key and url_key in existing_urls:
                    continue

                seen_names.add(name_key)
                all_shelters.append(org)

            # Rate limiting between sources
            time.sleep(random.uniform(1.0, 2.0))

        except Exception as e:
            print(f"      {source_name} error: {e}")
            continue

    return all_shelters


def add_to_database(org, db):
    """Add a discovered organization to the database if not duplicate."""
    # Create new shelter record
    shelter = Shelter(
        name=org.get('name', 'Unknown')[:200],
        website=org.get('website'),
        city=org.get('city'),
        state=org.get('state'),
        phone=org.get('phone'),
        email=org.get('email'),
        address=org.get('address'),
        description=org.get('snippet') or org.get('listing_url'),
        source=org.get('source', 'directory_scraper'),
        org_type='rescue'
    )

    try:
        db.add(shelter)
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        return False


def run_scraper(states=None, limit=None, save_to_db=True):
    """
    Run the state-by-state directory scraper.
    """
    print("=" * 60)
    print("RESCUE ENTITY SCRAPER AGENT v2")
    print("=" * 60)

    # Load progress
    progress = load_progress()
    discovered_data = load_discovered()

    # Determine states to scrape
    if states:
        states_to_scrape = [s.upper() for s in states]
    else:
        states_to_scrape = [s for s in STATE_NAMES.keys() if s not in progress['completed_states']]

    # Apply limit
    if limit:
        states_to_scrape = states_to_scrape[:limit]

    total_states = len(states_to_scrape)
    print(f"States to scrape: {total_states}")
    print(f"Save to DB: {save_to_db}")
    print("=" * 60)

    if total_states == 0:
        print("All states already scraped!")
        return

    # Create database session
    db = SessionLocal()

    new_count = 0
    processed = 0

    try:
        for state_code in states_to_scrape:
            state_name = STATE_NAMES.get(state_code, state_code)
            processed += 1

            print(f"\n[{processed}/{total_states}] {state_name} ({state_code})")
            print("-" * 40)

            # Scrape this state
            orgs = scrape_state(state_code, db)

            if orgs:
                print(f"  Total new: {len(orgs)} organizations")

                for org in orgs:
                    # Save to discovered list
                    discovered_data['shelters'].append(org)

                    # Save to database
                    if save_to_db:
                        if add_to_database(org, db):
                            new_count += 1
                            print(f"    + {org['name'][:50]}")
            else:
                print(f"  No new organizations found")

            # Mark state as complete
            if state_code not in progress['completed_states']:
                progress['completed_states'].append(state_code)
            progress['discovered_count'] = len(discovered_data['shelters'])

            # Save progress
            save_progress(progress)
            save_discovered(discovered_data)

            # Rate limiting between states
            time.sleep(random.uniform(2.0, 4.0))

    except KeyboardInterrupt:
        print("\n\nInterrupted! Saving progress...")
    finally:
        save_progress(progress)
        save_discovered(discovered_data)
        db.close()

    print("\n" + "=" * 60)
    print("SCRAPER COMPLETE")
    print("=" * 60)
    print(f"States processed: {processed}")
    print(f"New organizations added to DB: {new_count}")
    print(f"Total discovered: {len(discovered_data['shelters'])}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description='Rescue Entity Scraper Agent v2')
    parser.add_argument('--states', nargs='+', help='State codes to scrape (e.g., NJ NY PA)')
    parser.add_argument('--limit', type=int, help='Max states to scrape')
    parser.add_argument('--no-db', action='store_true', help='Skip database saves')
    parser.add_argument('--reset', action='store_true', help='Reset progress and start fresh')
    parser.add_argument('--status', action='store_true', help='Show current progress')
    parser.add_argument('--all', action='store_true', help='Scrape all states')

    args = parser.parse_args()

    if args.status:
        progress = load_progress()
        completed = len(progress['completed_states'])
        total = len(STATE_NAMES)
        print(f"Progress: {completed}/{total} states ({100*completed/total:.1f}%)")
        print(f"Completed: {', '.join(progress['completed_states'])}")
        print(f"Discovered: {progress.get('discovered_count', 0)} organizations")
        print(f"Last updated: {progress.get('last_updated', 'Never')}")
        return

    if args.reset:
        if os.path.exists(PROGRESS_FILE):
            os.remove(PROGRESS_FILE)
            print("Progress reset!")
        if os.path.exists(RESULTS_FILE):
            os.remove(RESULTS_FILE)
            print("Results reset!")
        return

    run_scraper(
        states=args.states,
        limit=args.limit if not args.all else None,
        save_to_db=not args.no_db
    )


if __name__ == '__main__':
    main()

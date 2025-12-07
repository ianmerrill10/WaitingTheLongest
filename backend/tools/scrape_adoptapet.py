#!/usr/bin/env python3
"""
===============================================================================
Adopt-a-Pet Shelter Directory Scraper
===============================================================================
Scrapes shelter/rescue listings from Adopt-a-Pet's public directory.
Adopt-a-Pet is one of the largest pet adoption websites with ~17,000+ shelters.

This scraper:
  - Goes through all 50 US states + DC
  - Extracts shelter names, locations, and profile URLs
  - Visits individual shelter pages for contact details
  - Saves to JSON/CSV with resume support
  - Can ingest directly to database

Usage:
    python scrape_adoptapet.py              # Interactive mode
    python scrape_adoptapet.py --all        # Scrape all states
    python scrape_adoptapet.py --all --db   # Scrape and save to database
    python scrape_adoptapet.py --state TX   # Scrape just Texas

===============================================================================
"""
import csv
import json
import os
import re
import sys
import time
import argparse
from datetime import datetime
from typing import Dict, List, Any, Optional, Set, Tuple
from urllib.parse import urljoin, quote

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# ==========================
# CONFIG
# ==========================

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
os.makedirs(DATA_DIR, exist_ok=True)

OUTPUT_JSON = os.path.join(DATA_DIR, "adoptapet_shelters.json")
OUTPUT_CSV = os.path.join(DATA_DIR, "adoptapet_shelters.csv")
PROGRESS_JSON = os.path.join(DATA_DIR, "adoptapet_progress.json")

BASE_URL = "https://www.adoptapet.com"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

REQUEST_TIMEOUT = 20
DELAY_BETWEEN_REQUESTS = 1.0

# US States with their Adopt-a-Pet URL slugs
US_STATES = {
    'AL': 'alabama', 'AK': 'alaska', 'AZ': 'arizona', 'AR': 'arkansas',
    'CA': 'california', 'CO': 'colorado', 'CT': 'connecticut', 'DE': 'delaware',
    'DC': 'district-of-columbia', 'FL': 'florida', 'GA': 'georgia', 'HI': 'hawaii',
    'ID': 'idaho', 'IL': 'illinois', 'IN': 'indiana', 'IA': 'iowa',
    'KS': 'kansas', 'KY': 'kentucky', 'LA': 'louisiana', 'ME': 'maine',
    'MD': 'maryland', 'MA': 'massachusetts', 'MI': 'michigan', 'MN': 'minnesota',
    'MS': 'mississippi', 'MO': 'missouri', 'MT': 'montana', 'NE': 'nebraska',
    'NV': 'nevada', 'NH': 'new-hampshire', 'NJ': 'new-jersey', 'NM': 'new-mexico',
    'NY': 'new-york', 'NC': 'north-carolina', 'ND': 'north-dakota', 'OH': 'ohio',
    'OK': 'oklahoma', 'OR': 'oregon', 'PA': 'pennsylvania', 'RI': 'rhode-island',
    'SC': 'south-carolina', 'SD': 'south-dakota', 'TN': 'tennessee', 'TX': 'texas',
    'UT': 'utah', 'VT': 'vermont', 'VA': 'virginia', 'WA': 'washington',
    'WV': 'west-virginia', 'WI': 'wisconsin', 'WY': 'wyoming'
}


# ==========================
# UTILITIES
# ==========================

def load_shelters() -> List[Dict]:
    if os.path.exists(OUTPUT_JSON):
        with open(OUTPUT_JSON, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def save_shelters(shelters: List[Dict]):
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(shelters, f, indent=2, ensure_ascii=False)


def save_csv(shelters: List[Dict]):
    if not shelters:
        return

    fieldnames = [
        'name', 'city', 'state', 'address', 'phone', 'email', 'website',
        'profile_url', 'description', 'facebook_url', 'instagram_url',
        'scraped_at', 'source'
    ]

    with open(OUTPUT_CSV, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        for s in shelters:
            writer.writerow(s)


def load_progress() -> Dict:
    if os.path.exists(PROGRESS_JSON):
        with open(PROGRESS_JSON, 'r') as f:
            return json.load(f)
    return {'completed_states': [], 'last_run': None}


def save_progress(progress: Dict):
    progress['last_run'] = datetime.utcnow().isoformat()
    with open(PROGRESS_JSON, 'w') as f:
        json.dump(progress, f, indent=2)


def shelter_key(shelter: Dict) -> str:
    return f"{shelter.get('name', '').lower().strip()}|{shelter.get('city', '').lower().strip()}|{shelter.get('state', '').upper()}"


# ==========================
# SCRAPING
# ==========================

def fetch_page(url: str, retries: int = 3) -> Optional[BeautifulSoup]:
    """Fetch a page with retry logic."""
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            if resp.status_code == 200:
                return BeautifulSoup(resp.text, 'html.parser')
            elif resp.status_code == 429:
                wait = 10 * (attempt + 1)
                print(f"    Rate limited, waiting {wait}s...")
                time.sleep(wait)
            elif resp.status_code == 404:
                return None
            else:
                print(f"    HTTP {resp.status_code} for {url}")
        except requests.RequestException as e:
            print(f"    Request error: {e}")
            if attempt < retries - 1:
                time.sleep(2)
    return None


def scrape_state_shelters(state_code: str, state_slug: str) -> List[Dict]:
    """Scrape all shelters for a given state."""
    shelters = []

    # Adopt-a-Pet shelter listing URL pattern
    # https://www.adoptapet.com/shelter-search/{state-slug}
    listing_url = f"{BASE_URL}/shelter-search/{state_slug}"

    print(f"  Fetching: {listing_url}")
    soup = fetch_page(listing_url)

    if not soup:
        print(f"    Could not fetch state listing for {state_code}")
        return shelters

    # Look for shelter links in the page
    # Pattern: /adoption_rescue/{shelter-id}.html or /shelter/{id}
    shelter_links = set()

    for a in soup.find_all('a', href=True):
        href = a['href']
        # Match shelter profile URLs
        if '/adoption_rescue/' in href or '/shelter/' in href:
            full_url = urljoin(BASE_URL, href)
            shelter_links.add(full_url)

    print(f"    Found {len(shelter_links)} shelter links")

    # Also try to find shelter cards/divs with data
    for card in soup.find_all(['div', 'article'], class_=lambda c: c and ('shelter' in str(c).lower() or 'rescue' in str(c).lower())):
        name_elem = card.find(['h2', 'h3', 'h4', 'a'])
        if name_elem:
            name = name_elem.get_text(strip=True)
            link = card.find('a', href=True)
            profile_url = urljoin(BASE_URL, link['href']) if link else ''

            # Try to get location
            location_elem = card.find(class_=lambda c: c and 'location' in str(c).lower())
            city = ''
            if location_elem:
                city = location_elem.get_text(strip=True)

            if name and len(name) > 2:
                shelters.append({
                    'name': name,
                    'city': city,
                    'state': state_code,
                    'profile_url': profile_url,
                    'source': 'adoptapet',
                    'scraped_at': datetime.utcnow().isoformat()
                })

    # Visit individual shelter pages for more details
    for url in list(shelter_links)[:50]:  # Limit per state to avoid overwhelming
        time.sleep(DELAY_BETWEEN_REQUESTS)
        shelter_data = scrape_shelter_page(url, state_code)
        if shelter_data:
            shelters.append(shelter_data)

    return shelters


def scrape_shelter_page(url: str, state_code: str) -> Optional[Dict]:
    """Scrape details from an individual shelter page."""
    soup = fetch_page(url)
    if not soup:
        return None

    shelter = {
        'name': '',
        'city': '',
        'state': state_code,
        'address': '',
        'phone': '',
        'email': '',
        'website': '',
        'profile_url': url,
        'description': '',
        'facebook_url': '',
        'instagram_url': '',
        'source': 'adoptapet',
        'scraped_at': datetime.utcnow().isoformat()
    }

    # Try to find name
    name_elem = soup.find('h1')
    if name_elem:
        shelter['name'] = name_elem.get_text(strip=True)

    # Look for contact info section
    for elem in soup.find_all(['div', 'section', 'aside']):
        text = elem.get_text(' ', strip=True).lower()

        # Phone
        if not shelter['phone']:
            phone_match = re.search(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', elem.get_text())
            if phone_match:
                shelter['phone'] = phone_match.group(0)

        # Email
        if not shelter['email']:
            for a in elem.find_all('a', href=True):
                if a['href'].startswith('mailto:'):
                    shelter['email'] = a['href'].replace('mailto:', '').split('?')[0]
                    break

    # Look for address
    addr_elem = soup.find(class_=lambda c: c and 'address' in str(c).lower())
    if addr_elem:
        shelter['address'] = addr_elem.get_text(' ', strip=True)

    # Extract city from address if possible
    if shelter['address'] and not shelter['city']:
        # Try to find city, state pattern
        city_match = re.search(r'([A-Za-z\s]+),\s*[A-Z]{2}', shelter['address'])
        if city_match:
            shelter['city'] = city_match.group(1).strip()

    # Social links
    for a in soup.find_all('a', href=True):
        href = a['href'].lower()
        if 'facebook.com' in href and not shelter['facebook_url']:
            shelter['facebook_url'] = a['href']
        elif 'instagram.com' in href and not shelter['instagram_url']:
            shelter['instagram_url'] = a['href']
        elif not any(x in href for x in ['adoptapet', 'facebook', 'instagram', 'twitter', 'mailto:', 'tel:']):
            # Might be org website
            if href.startswith('http') and not shelter['website']:
                shelter['website'] = a['href']

    # Description/About
    about_elem = soup.find(class_=lambda c: c and ('about' in str(c).lower() or 'description' in str(c).lower() or 'bio' in str(c).lower()))
    if about_elem:
        shelter['description'] = about_elem.get_text(' ', strip=True)[:500]

    # Only return if we got a name
    if shelter['name']:
        return shelter
    return None


def scrape_all_states(existing: List[Dict], progress: Dict) -> Tuple[List[Dict], Dict, int]:
    """Scrape all US states."""
    seen_keys = {shelter_key(s) for s in existing}
    total_added = 0

    completed = set(progress.get('completed_states', []))

    for state_code, state_slug in US_STATES.items():
        if state_code in completed:
            print(f"[{state_code}] Already completed, skipping...")
            continue

        print(f"\n[{state_code}] Scraping {state_slug}...")

        state_shelters = scrape_state_shelters(state_code, state_slug)
        added = 0

        for shelter in state_shelters:
            key = shelter_key(shelter)
            if key not in seen_keys:
                existing.append(shelter)
                seen_keys.add(key)
                added += 1

        total_added += added
        print(f"    Added {added} new shelters from {state_code}")

        # Mark state as completed
        completed.add(state_code)
        progress['completed_states'] = list(completed)

        # Save checkpoint
        save_shelters(existing)
        save_progress(progress)

        time.sleep(2)  # Delay between states

    return existing, progress, total_added


# ==========================
# DATABASE INGESTION
# ==========================

def ingest_to_database(shelters: List[Dict]) -> Tuple[int, int]:
    """Ingest scraped shelters to database."""
    try:
        from app.database import SessionLocal, init_db
        from app.models import Shelter
    except ImportError as e:
        print(f"ERROR: Could not import database modules: {e}")
        return 0, 0

    print("\n=== INGESTING TO DATABASE ===")

    init_db()
    db = SessionLocal()

    created = 0
    updated = 0

    try:
        for s in shelters:
            name = s.get('name', '').strip()
            state = s.get('state', '').strip()

            if not name:
                continue

            existing = db.query(Shelter).filter(
                Shelter.name == name,
                Shelter.state == state
            ).first()

            if existing:
                # Update with new data
                if s.get('phone') and not existing.phone:
                    existing.phone = s['phone']
                if s.get('email') and not existing.email:
                    existing.email = s['email']
                if s.get('website') and not existing.website:
                    existing.website = s['website']
                if s.get('address') and not existing.address:
                    existing.address = s['address']
                if s.get('city') and not existing.city:
                    existing.city = s['city']
                if s.get('facebook_url') and not existing.facebook_url:
                    existing.facebook_url = s['facebook_url']
                if s.get('instagram_url') and not existing.instagram_url:
                    existing.instagram_url = s['instagram_url']
                existing.last_verified_at = datetime.utcnow()
                updated += 1
            else:
                new_shelter = Shelter(
                    name=name,
                    city=s.get('city', ''),
                    state=state,
                    address=s.get('address', ''),
                    phone=s.get('phone', ''),
                    email=s.get('email', ''),
                    website=s.get('website', ''),
                    description=s.get('description', ''),
                    facebook_url=s.get('facebook_url', ''),
                    instagram_url=s.get('instagram_url', ''),
                    source='adoptapet',
                    org_type='rescue',
                    last_verified_at=datetime.utcnow()
                )
                db.add(new_shelter)
                created += 1

            if (created + updated) % 100 == 0:
                db.commit()

        db.commit()
        print(f"  Created: {created}")
        print(f"  Updated: {updated}")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

    return created, updated


# ==========================
# CLI
# ==========================

def interactive_mode():
    """Interactive menu."""
    print("\n=== Adopt-a-Pet Shelter Scraper ===")
    print(f"Output: {OUTPUT_JSON}")

    shelters = load_shelters()
    progress = load_progress()

    completed = len(progress.get('completed_states', []))
    print(f"\nLoaded {len(shelters)} shelters")
    print(f"States completed: {completed}/{len(US_STATES)}")

    while True:
        print("\n" + "=" * 50)
        print("Options:")
        print("  [S] Scrape a specific state")
        print("  [A] Scrape ALL remaining states")
        print("  [D] Ingest to database")
        print("  [R] Reset progress (start over)")
        print("  [I] Show stats")
        print("  [Q] Quit")

        choice = input("Enter choice: ").strip().lower()

        if choice == 'q':
            break

        elif choice == 'i':
            print(f"\n  Total shelters: {len(shelters)}")
            print(f"  States completed: {len(progress.get('completed_states', []))}/{len(US_STATES)}")
            remaining = set(US_STATES.keys()) - set(progress.get('completed_states', []))
            print(f"  Remaining states: {', '.join(sorted(remaining))}")

        elif choice == 'r':
            confirm = input("  Are you sure? (y/n): ").strip().lower()
            if confirm == 'y':
                progress = {'completed_states': [], 'last_run': None}
                save_progress(progress)
                print("  Progress reset!")

        elif choice == 's':
            state = input("  Enter state code (e.g., TX): ").strip().upper()
            if state in US_STATES:
                seen = {shelter_key(s) for s in shelters}
                state_shelters = scrape_state_shelters(state, US_STATES[state])
                added = 0
                for s in state_shelters:
                    key = shelter_key(s)
                    if key not in seen:
                        shelters.append(s)
                        seen.add(key)
                        added += 1
                save_shelters(shelters)
                save_csv(shelters)
                print(f"  Added {added} new shelters from {state}")
            else:
                print(f"  Invalid state code: {state}")

        elif choice == 'a':
            shelters, progress, added = scrape_all_states(shelters, progress)
            save_shelters(shelters)
            save_csv(shelters)
            save_progress(progress)
            print(f"\n  Scrape complete! Added {added} shelters")

        elif choice == 'd':
            ingest_to_database(shelters)

        else:
            print("  Unknown choice.")

    save_shelters(shelters)
    save_csv(shelters)
    print("\nDone!")


def main():
    parser = argparse.ArgumentParser(description="Scrape Adopt-a-Pet shelter directory")
    parser.add_argument('--all', action='store_true', help="Scrape all states")
    parser.add_argument('--db', action='store_true', help="Ingest to database")
    parser.add_argument('--state', type=str, help="Scrape specific state (e.g., TX)")

    args = parser.parse_args()

    if args.all or args.state:
        shelters = load_shelters()
        progress = load_progress()

        if args.state:
            state = args.state.upper()
            if state in US_STATES:
                print(f"Scraping {state}...")
                seen = {shelter_key(s) for s in shelters}
                state_shelters = scrape_state_shelters(state, US_STATES[state])
                added = 0
                for s in state_shelters:
                    key = shelter_key(s)
                    if key not in seen:
                        shelters.append(s)
                        seen.add(key)
                        added += 1
                print(f"Added {added} shelters from {state}")
            else:
                print(f"Invalid state: {state}")
                return
        else:
            shelters, progress, added = scrape_all_states(shelters, progress)
            print(f"\nTotal added: {added}")

        save_shelters(shelters)
        save_csv(shelters)
        save_progress(progress)

        if args.db:
            ingest_to_database(shelters)
    else:
        interactive_mode()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted.")
        sys.exit(0)

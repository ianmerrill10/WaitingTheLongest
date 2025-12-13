#!/usr/bin/env python3
"""
===============================================================================
Best Friends Network - Contact Detail Enricher (Phase 2)
===============================================================================
Visits individual org profile pages to extract:
- Phone numbers
- Email addresses
- Website URLs
- Social media links (Facebook, Instagram, Twitter)

Run this AFTER scrape_bestfriends.py to add contact details.

Usage:
    python enrich_bestfriends.py              # Interactive
    python enrich_bestfriends.py --all        # Enrich all missing
    python enrich_bestfriends.py --all --db   # Enrich and update database

===============================================================================
"""
import json
import os
import re
import sys
import time
import argparse
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# ==========================
# CONFIG
# ==========================

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
INPUT_JSON = os.path.join(DATA_DIR, "bf_network_orgs.json")
OUTPUT_JSON = os.path.join(DATA_DIR, "bf_network_enriched.json")
PROGRESS_JSON = os.path.join(DATA_DIR, "bf_enrich_progress.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; WaitingTheLongestCollector/1.0; +https://waitingthelongest.com)"
}

BATCH_SIZE = 20


# ==========================
# CONTACT EXTRACTION
# ==========================

def extract_phone(text: str) -> Optional[str]:
    """Extract US phone number from text"""
    patterns = [
        r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
        r'\d{3}[-.\s]\d{3}[-.\s]\d{4}',
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0)
    return None


def extract_email(text: str) -> Optional[str]:
    """Extract email address from text"""
    match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
    return match.group(0) if match else None


def extract_website(soup: BeautifulSoup, exclude_domains: List[str] = None) -> Optional[str]:
    """Extract organization website (not social media)"""
    exclude_domains = exclude_domains or ['facebook.com', 'instagram.com', 'twitter.com', 'tiktok.com', 'bestfriends.org']

    for a in soup.find_all('a', href=True):
        href = a['href'].lower()
        text = a.get_text(strip=True).lower()

        # Look for website links
        if any(kw in text for kw in ['website', 'visit us', 'our site', 'home page']):
            if not any(domain in href for domain in exclude_domains):
                return a['href']

        # Look for external links that aren't social media
        if href.startswith('http') and not any(domain in href for domain in exclude_domains):
            if 'bestfriends.org' not in href:
                return a['href']

    return None


def extract_social_links(soup: BeautifulSoup) -> Dict[str, Optional[str]]:
    """Extract social media links"""
    socials = {
        'facebook_url': None,
        'instagram_url': None,
        'twitter_url': None,
        'tiktok_url': None,
    }

    for a in soup.find_all('a', href=True):
        href = a['href'].lower()

        if 'facebook.com' in href:
            socials['facebook_url'] = a['href']
        elif 'instagram.com' in href:
            socials['instagram_url'] = a['href']
        elif 'twitter.com' in href or 'x.com' in href:
            socials['twitter_url'] = a['href']
        elif 'tiktok.com' in href:
            socials['tiktok_url'] = a['href']

    return socials


def extract_address(soup: BeautifulSoup) -> Optional[str]:
    """Try to extract street address"""
    # Look for address-like patterns
    text = soup.get_text()

    # Pattern: number + street name + city, state zip
    address_pattern = r'\d+\s+[\w\s]+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Boulevard|Blvd|Way|Court|Ct)[\.,]?\s*[\w\s]+,\s*[A-Z]{2}\s*\d{5}'
    match = re.search(address_pattern, text, re.IGNORECASE)

    if match:
        return match.group(0).strip()

    return None


def scrape_profile_page(url: str, retries: int = 2) -> Dict:
    """Scrape contact details from an org's profile page"""
    result = {
        'phone': None,
        'email': None,
        'website': None,
        'address': None,
        'facebook_url': None,
        'instagram_url': None,
        'twitter_url': None,
        'tiktok_url': None,
        'scraped': False,
        'error': None,
    }

    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20)
            if resp.status_code != 200:
                result['error'] = f"HTTP {resp.status_code}"
                continue

            soup = BeautifulSoup(resp.text, 'html.parser')
            text = soup.get_text()

            result['phone'] = extract_phone(text)
            result['email'] = extract_email(text)
            result['website'] = extract_website(soup)
            result['address'] = extract_address(soup)

            socials = extract_social_links(soup)
            result.update(socials)

            result['scraped'] = True
            result['error'] = None

            return result

        except requests.RequestException as e:
            result['error'] = str(e)
            if attempt < retries - 1:
                time.sleep(2)

    return result


# ==========================
# PROGRESS TRACKING
# ==========================

def load_progress() -> Dict:
    if os.path.exists(PROGRESS_JSON):
        with open(PROGRESS_JSON, 'r') as f:
            return json.load(f)
    return {'enriched_urls': [], 'last_index': 0}


def save_progress(progress: Dict):
    with open(PROGRESS_JSON, 'w') as f:
        json.dump(progress, f, indent=2)


def load_orgs() -> List[Dict]:
    if not os.path.exists(INPUT_JSON):
        print(f"ERROR: {INPUT_JSON} not found. Run scrape_bestfriends.py first.")
        return []
    with open(INPUT_JSON, 'r') as f:
        return json.load(f)


def save_enriched(orgs: List[Dict]):
    with open(OUTPUT_JSON, 'w') as f:
        json.dump(orgs, f, indent=2, ensure_ascii=False)
    print(f"  Saved to {OUTPUT_JSON}")


# ==========================
# ENRICHMENT LOGIC
# ==========================

def enrich_batch(orgs: List[Dict], progress: Dict, batch_size: int = BATCH_SIZE) -> Tuple[List[Dict], Dict, int]:
    """Enrich a batch of orgs with contact details"""
    enriched_urls = set(progress.get('enriched_urls', []))
    enriched_count = 0

    for org in orgs:
        if enriched_count >= batch_size:
            break

        url = org.get('profile_url', '')
        if not url or url in enriched_urls:
            continue

        print(f"  Enriching: {org.get('name', 'Unknown')}...")

        details = scrape_profile_page(url)

        # Merge details into org
        if details['phone'] and not org.get('phone'):
            org['phone'] = details['phone']
        if details['email'] and not org.get('email'):
            org['email'] = details['email']
        if details['website'] and not org.get('website'):
            org['website'] = details['website']
        if details['address'] and not org.get('address'):
            org['address'] = details['address']

        for social_key in ['facebook_url', 'instagram_url', 'twitter_url', 'tiktok_url']:
            if details[social_key] and not org.get(social_key):
                org[social_key] = details[social_key]

        org['enriched_at'] = datetime.utcnow().isoformat()
        enriched_urls.add(url)
        enriched_count += 1

        time.sleep(1)  # Be polite

    progress['enriched_urls'] = list(enriched_urls)

    return orgs, progress, enriched_count


def enrich_all(orgs: List[Dict], progress: Dict) -> Tuple[List[Dict], Dict, int]:
    """Enrich all un-enriched orgs"""
    total_enriched = 0
    batch_num = 0

    while True:
        batch_num += 1
        print(f"\n--- Batch {batch_num} ---")

        orgs, progress, enriched = enrich_batch(orgs, progress)
        total_enriched += enriched

        if enriched == 0:
            print("  No more orgs to enrich.")
            break

        # Save checkpoint
        save_enriched(orgs)
        save_progress(progress)
        print(f"  Checkpoint: {len(progress['enriched_urls'])} orgs enriched")

    return orgs, progress, total_enriched


# ==========================
# DATABASE UPDATE
# ==========================

def update_database(orgs: List[Dict]) -> Tuple[int, int]:
    """Update database shelters with enriched contact info"""
    try:
        from app.database import SessionLocal, init_db
        from app.models import Shelter
    except ImportError as e:
        print(f"ERROR: Could not import database modules: {e}")
        return 0, 0

    print("\n=== UPDATING DATABASE ===")

    init_db()
    db = SessionLocal()

    updated = 0
    not_found = 0

    try:
        for org in orgs:
            if not org.get('enriched_at'):
                continue

            # Find matching shelter
            shelter = db.query(Shelter).filter(
                Shelter.name == org['name'],
                Shelter.state == org['state']
            ).first()

            if not shelter:
                not_found += 1
                continue

            # Update contact fields
            changed = False

            if org.get('phone') and not shelter.phone:
                shelter.phone = org['phone']
                changed = True
            if org.get('email') and not shelter.email:
                shelter.email = org['email']
                changed = True
            if org.get('website') and not shelter.website:
                shelter.website = org['website']
                changed = True
            if org.get('address') and not shelter.address:
                shelter.address = org['address']
                changed = True
            if org.get('facebook_url') and not shelter.facebook_url:
                shelter.facebook_url = org['facebook_url']
                changed = True
            if org.get('instagram_url') and not shelter.instagram_url:
                shelter.instagram_url = org['instagram_url']
                changed = True
            if org.get('twitter_url') and not shelter.twitter_url:
                shelter.twitter_url = org['twitter_url']
                changed = True
            if org.get('tiktok_url') and not shelter.tiktok_url:
                shelter.tiktok_url = org['tiktok_url']
                changed = True

            if changed:
                shelter.last_verified_at = datetime.utcnow()
                updated += 1

        db.commit()
        print(f"  Updated: {updated}")
        print(f"  Not found in DB: {not_found}")

    except Exception as e:
        print(f"ERROR: {e}")
        db.rollback()
    finally:
        db.close()

    return updated, not_found


# ==========================
# CLI
# ==========================

def interactive_mode():
    """Interactive menu"""
    print("\n=== Best Friends Network - Contact Enricher ===")
    print(f"Input: {INPUT_JSON}")
    print(f"Output: {OUTPUT_JSON}")

    orgs = load_orgs()
    if not orgs:
        return

    progress = load_progress()
    enriched_count = len(progress.get('enriched_urls', []))

    print(f"\nLoaded {len(orgs)} orgs")
    print(f"Already enriched: {enriched_count}")
    print(f"Remaining: {len(orgs) - enriched_count}")

    while True:
        print("\n" + "=" * 50)
        print("Options:")
        print("  [N] Next batch (enrich 20 orgs)")
        print("  [A] Enrich ALL remaining")
        print("  [D] Update database with enriched data")
        print("  [S] Show stats")
        print("  [Q] Quit")

        choice = input("Enter choice: ").strip().lower()

        if choice == 'q':
            break

        elif choice == 's':
            with_phone = sum(1 for o in orgs if o.get('phone'))
            with_email = sum(1 for o in orgs if o.get('email'))
            with_website = sum(1 for o in orgs if o.get('website'))

            print(f"\n  Total orgs: {len(orgs)}")
            print(f"  Enriched: {len(progress.get('enriched_urls', []))}")
            print(f"  With phone: {with_phone}")
            print(f"  With email: {with_email}")
            print(f"  With website: {with_website}")

        elif choice == 'n':
            orgs, progress, enriched = enrich_batch(orgs, progress)
            save_enriched(orgs)
            save_progress(progress)
            print(f"\n  Batch complete! Enriched: {enriched}")

        elif choice == 'a':
            orgs, progress, enriched = enrich_all(orgs, progress)
            save_enriched(orgs)
            save_progress(progress)
            print(f"\n  All done! Total enriched: {enriched}")

        elif choice == 'd':
            update_database(orgs)

        else:
            print("  Unknown choice.")

    save_enriched(orgs)
    save_progress(progress)
    print("\nDone!")


def main():
    parser = argparse.ArgumentParser(description="Enrich Best Friends orgs with contact details")
    parser.add_argument('--all', action='store_true', help="Enrich all orgs")
    parser.add_argument('--db', action='store_true', help="Update database")

    args = parser.parse_args()

    if args.all:
        orgs = load_orgs()
        if not orgs:
            return

        progress = load_progress()
        orgs, progress, enriched = enrich_all(orgs, progress)
        save_enriched(orgs)
        save_progress(progress)

        print(f"\nComplete! Enriched: {enriched}")

        if args.db:
            update_database(orgs)
    else:
        interactive_mode()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted.")
        sys.exit(0)

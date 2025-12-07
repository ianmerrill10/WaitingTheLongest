#!/usr/bin/env python3
"""
===============================================================================
Best Friends Network - Website Deep Enricher (Phase 3)
===============================================================================
Visits each org's OWN website to extract contact info directly from their site.

This builds on top of:
  - Phase 1: scrape_bestfriends.py -> bf_network_orgs.json
  - Phase 2: enrich_bestfriends.py -> bf_network_enriched.json

Output:
  - bf_network_website_enriched.json
  - bf_network_website_enriched.csv

Fields extracted from org websites:
  - site_email, site_phone, site_address
  - site_facebook_url, site_instagram_url, site_twitter_url, etc.

Usage:
    python enrich_websites.py              # Interactive (50 sites at a time)
    python enrich_websites.py --all        # Process all remaining sites
    python enrich_websites.py --all --db   # Process all and update database
    python enrich_websites.py --batch 100  # Process 100 sites then stop

===============================================================================
"""
import csv
import json
import os
import re
import sys
import time
import argparse
from typing import Dict, Any, List, Optional, Set
from urllib.parse import urlparse, urljoin
from datetime import datetime

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# ==========================
# CONFIG
# ==========================

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
os.makedirs(DATA_DIR, exist_ok=True)

# Input from Phase 2 (or Phase 1 if Phase 2 wasn't run)
ENRICHED_INPUT = os.path.join(DATA_DIR, "bf_network_enriched.json")
BASE_INPUT = os.path.join(DATA_DIR, "bf_network_orgs.json")

# Output
SITE_ENRICHED_JSON = os.path.join(DATA_DIR, "bf_network_website_enriched.json")
SITE_ENRICHED_CSV = os.path.join(DATA_DIR, "bf_network_website_enriched.csv")
PROGRESS_JSON = os.path.join(DATA_DIR, "bf_website_progress.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

REQUEST_TIMEOUT = 20
DELAY_BETWEEN_REQUESTS = 1.5
DEFAULT_BATCH_SIZE = 50

# Social media domain mappings
SOCIAL_DOMAINS = {
    "facebook.com": "site_facebook_url",
    "fb.com": "site_facebook_url",
    "instagram.com": "site_instagram_url",
    "twitter.com": "site_twitter_url",
    "x.com": "site_twitter_url",
    "youtube.com": "site_youtube_url",
    "youtu.be": "site_youtube_url",
    "tiktok.com": "site_tiktok_url",
    "linkedin.com": "site_linkedin_url",
    "pinterest.com": "site_pinterest_url",
}

# Domains to skip (not actual org websites)
SKIP_DOMAINS = {
    "bestfriends.org",
    "petfinder.com",
    "adoptapet.com",
    "facebook.com",
    "instagram.com",
    "twitter.com",
    "google.com",
    "yelp.com",
}


# ==========================
# UTILITIES
# ==========================

def load_input_orgs() -> List[Dict[str, Any]]:
    """Load orgs from Phase 2 output, falling back to Phase 1 if needed."""
    if os.path.exists(ENRICHED_INPUT):
        print(f"Loading from Phase 2 output: {ENRICHED_INPUT}")
        with open(ENRICHED_INPUT, 'r', encoding='utf-8') as f:
            return json.load(f)
    elif os.path.exists(BASE_INPUT):
        print(f"Phase 2 not found, loading from Phase 1: {BASE_INPUT}")
        with open(BASE_INPUT, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        print("ERROR: No input file found. Run scrape_bestfriends.py first.")
        return []


def load_site_enriched() -> List[Dict[str, Any]]:
    """Load existing website-enriched data."""
    if os.path.exists(SITE_ENRICHED_JSON):
        with open(SITE_ENRICHED_JSON, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def save_site_enriched_json(data: List[Dict[str, Any]]):
    with open(SITE_ENRICHED_JSON, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def save_site_enriched_csv(data: List[Dict[str, Any]]):
    """Save to CSV with sensible column ordering."""
    if not data:
        return

    # Collect all keys
    all_keys = set()
    for item in data:
        all_keys.update(item.keys())

    # Preferred column order
    preferred = [
        "name", "city", "state", "description",
        "profile_url", "website_url",
        # Phase 2 fields
        "phone", "email", "address",
        "facebook_url", "instagram_url", "twitter_url",
        # Phase 3 fields (from org's own site)
        "site_phone", "site_email", "site_address",
        "site_facebook_url", "site_instagram_url", "site_twitter_url",
        "site_youtube_url", "site_tiktok_url", "site_linkedin_url", "site_pinterest_url",
        # Status fields
        "enriched", "site_enriched", "site_enrich_error",
        "scraped_at", "enriched_at", "site_enriched_at",
    ]

    fieldnames = [k for k in preferred if k in all_keys]
    fieldnames.extend(sorted(k for k in all_keys if k not in fieldnames))

    with open(SITE_ENRICHED_CSV, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in data:
            writer.writerow({k: row.get(k, '') for k in fieldnames})

    print(f"  Saved CSV to {SITE_ENRICHED_CSV}")


def load_progress() -> Dict:
    if os.path.exists(PROGRESS_JSON):
        with open(PROGRESS_JSON, 'r') as f:
            return json.load(f)
    return {'processed_urls': [], 'last_run': None}


def save_progress(progress: Dict):
    progress['last_run'] = datetime.utcnow().isoformat()
    with open(PROGRESS_JSON, 'w') as f:
        json.dump(progress, f, indent=2)


def org_key(org: Dict[str, Any]) -> str:
    """Unique key for deduplication."""
    return f"{org.get('name', '').strip().lower()}|{org.get('city', '').strip().lower()}|{org.get('state', '').strip().upper()}"


def normalize_url(url: str, base: str) -> str:
    """Normalize relative URLs to absolute."""
    url = (url or '').strip()
    if not url:
        return ''
    if url.startswith('//'):
        parsed = urlparse(base)
        return f"{parsed.scheme}:{url}"
    if url.startswith('/'):
        return urljoin(base, url)
    if not url.startswith('http'):
        return f"https://{url}"
    return url


def is_valid_website(url: str) -> bool:
    """Check if URL is a valid org website to scrape."""
    if not url:
        return False
    try:
        parsed = urlparse(url.lower())
        host = parsed.netloc
        return not any(skip in host for skip in SKIP_DOMAINS)
    except:
        return False


# ==========================
# SCRAPING HELPERS
# ==========================

def extract_emails(soup: BeautifulSoup, text: str) -> List[str]:
    """Extract all email addresses from page."""
    emails = set()

    # From mailto links
    for a in soup.find_all('a', href=True):
        href = a['href'].lower()
        if href.startswith('mailto:'):
            email = href.split(':', 1)[1].split('?')[0].strip()
            if '@' in email:
                emails.add(email)

    # From text using regex
    email_re = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
    for match in email_re.findall(text):
        # Filter out common false positives
        if not any(x in match.lower() for x in ['example.com', 'domain.com', 'email.com', '.png', '.jpg']):
            emails.add(match.lower())

    return list(emails)


def extract_phones(soup: BeautifulSoup, text: str) -> List[str]:
    """Extract phone numbers from page."""
    phones = set()

    # From tel: links
    for a in soup.find_all('a', href=True):
        href = a['href']
        if href.lower().startswith('tel:'):
            phone = href.split(':', 1)[1].strip()
            phones.add(phone)

    # From text using regex (US format)
    phone_patterns = [
        r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
        r'\+1[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
        r'\d{3}[-.\s]\d{3}[-.\s]\d{4}',
    ]
    for pattern in phone_patterns:
        for match in re.findall(pattern, text):
            # Clean up
            cleaned = re.sub(r'[^\d]', '', match)
            if len(cleaned) >= 10:
                phones.add(match)

    return list(phones)


def extract_address(soup: BeautifulSoup, text: str) -> Optional[str]:
    """Try to extract physical address."""
    candidates = []

    # From <address> tags
    for tag in soup.find_all('address'):
        txt = tag.get_text(' ', strip=True)
        if txt and len(txt) > 10:
            candidates.append(txt)

    # From elements with "address" in class/id
    for tag in soup.find_all(True, class_=lambda c: c and 'address' in str(c).lower()):
        txt = tag.get_text(' ', strip=True)
        if txt and len(txt) > 10:
            candidates.append(txt)

    for tag in soup.find_all(True, id=lambda i: i and 'address' in str(i).lower()):
        txt = tag.get_text(' ', strip=True)
        if txt and len(txt) > 10:
            candidates.append(txt)

    # From text matching address patterns
    if not candidates:
        # Pattern: number + street + city, state zip
        addr_re = re.compile(
            r'\d{1,5}\s+[\w\s\.\-]+'
            r'(?:Street|St|Avenue|Ave|Boulevard|Blvd|Road|Rd|Drive|Dr|Lane|Ln|Court|Ct|Way|Circle|Cir|Highway|Hwy)'
            r'[\.,]?\s*[\w\s]+,\s*[A-Z]{2}\s*\d{5}',
            re.IGNORECASE
        )
        matches = addr_re.findall(text)
        candidates.extend(matches)

    # Deduplicate and return first
    seen = set()
    unique = []
    for c in candidates:
        c_clean = ' '.join(c.split())
        if c_clean not in seen and len(c_clean) > 15:
            seen.add(c_clean)
            unique.append(c_clean)

    return unique[0] if unique else None


def extract_social_links(soup: BeautifulSoup, base_url: str) -> Dict[str, str]:
    """Extract social media links."""
    socials = {
        'site_facebook_url': '',
        'site_instagram_url': '',
        'site_twitter_url': '',
        'site_youtube_url': '',
        'site_tiktok_url': '',
        'site_linkedin_url': '',
        'site_pinterest_url': '',
    }

    for a in soup.find_all('a', href=True):
        href = a['href'].strip()
        if not href:
            continue

        full_url = normalize_url(href, base_url)

        try:
            host = urlparse(full_url).netloc.lower()
        except:
            continue

        for domain, field in SOCIAL_DOMAINS.items():
            if domain in host and not socials.get(field):
                socials[field] = full_url
                break

    return socials


def scrape_website(url: str, retries: int = 2) -> Dict[str, Any]:
    """Scrape contact info from an org's website."""
    result = {
        'site_phone': '',
        'site_email': '',
        'site_address': '',
        'site_facebook_url': '',
        'site_instagram_url': '',
        'site_twitter_url': '',
        'site_youtube_url': '',
        'site_tiktok_url': '',
        'site_linkedin_url': '',
        'site_pinterest_url': '',
        'site_enriched': False,
        'site_enrich_error': '',
        'site_enriched_at': '',
    }

    if not is_valid_website(url):
        result['site_enrich_error'] = 'invalid_or_skipped_domain'
        return result

    for attempt in range(retries):
        try:
            resp = requests.get(
                url,
                headers=HEADERS,
                timeout=REQUEST_TIMEOUT,
                allow_redirects=True
            )

            if resp.status_code != 200:
                result['site_enrich_error'] = f'http_{resp.status_code}'
                if attempt < retries - 1:
                    time.sleep(2)
                    continue
                return result

            soup = BeautifulSoup(resp.text, 'html.parser')
            text = soup.get_text(' ', strip=True)

            # Extract all the things
            emails = extract_emails(soup, text)
            phones = extract_phones(soup, text)
            address = extract_address(soup, text)
            socials = extract_social_links(soup, url)

            # Take first/best result
            result['site_email'] = emails[0] if emails else ''
            result['site_phone'] = phones[0] if phones else ''
            result['site_address'] = address or ''
            result.update(socials)
            result['site_enriched'] = True
            result['site_enrich_error'] = ''
            result['site_enriched_at'] = datetime.utcnow().isoformat()

            return result

        except requests.Timeout:
            result['site_enrich_error'] = 'timeout'
        except requests.ConnectionError as e:
            result['site_enrich_error'] = f'connection_error: {str(e)[:50]}'
        except Exception as e:
            result['site_enrich_error'] = f'error: {str(e)[:50]}'

        if attempt < retries - 1:
            time.sleep(2)

    return result


# ==========================
# BATCH PROCESSING
# ==========================

def process_batch(
    orgs: List[Dict],
    index: Dict[str, Dict],
    progress: Dict,
    batch_size: int = DEFAULT_BATCH_SIZE,
    verbose: bool = True
) -> int:
    """Process a batch of orgs, enriching from their websites."""
    processed_urls = set(progress.get('processed_urls', []))
    processed = 0

    for org in orgs:
        if processed >= batch_size:
            break

        key = org_key(org)

        # Skip if already successfully site-enriched
        existing = index.get(key)
        if existing and existing.get('site_enriched'):
            continue

        # Get website URL (from Phase 2 or profile_url as fallback)
        website_url = org.get('website_url') or org.get('website') or ''

        if not website_url:
            # Try to use the Best Friends profile URL to find a website
            if verbose:
                print(f"  Skipping {org.get('name', 'Unknown')} - no website URL")
            index[key] = {**org, 'site_enriched': False, 'site_enrich_error': 'no_website_url'}
            continue

        if website_url in processed_urls:
            continue

        if verbose:
            print(f"  [{processed + 1}/{batch_size}] {org.get('name', 'Unknown')} -> {website_url[:50]}...")

        # Scrape the website
        site_data = scrape_website(website_url)

        # Merge with existing org data
        enriched = {**org, **site_data}
        index[key] = enriched
        processed_urls.add(website_url)
        processed += 1

        time.sleep(DELAY_BETWEEN_REQUESTS)

    progress['processed_urls'] = list(processed_urls)
    return processed


def process_all(orgs: List[Dict], index: Dict[str, Dict], progress: Dict) -> int:
    """Process all remaining orgs."""
    total_processed = 0
    batch_num = 0

    while True:
        batch_num += 1
        print(f"\n--- Batch {batch_num} ---")

        processed = process_batch(orgs, index, progress, batch_size=50, verbose=True)
        total_processed += processed

        # Save checkpoint
        save_site_enriched_json(list(index.values()))
        save_progress(progress)
        print(f"  Checkpoint: {len(index)} total orgs saved")

        if processed == 0:
            print("  No more orgs to process!")
            break

    return total_processed


# ==========================
# DATABASE UPDATE
# ==========================

def update_database(orgs: List[Dict]) -> tuple:
    """Update database with website-scraped contact info."""
    try:
        from app.database import SessionLocal, init_db
        from app.models import Shelter
    except ImportError as e:
        print(f"ERROR: Could not import database modules: {e}")
        return 0, 0

    print("\n=== UPDATING DATABASE WITH WEBSITE DATA ===")

    init_db()
    db = SessionLocal()

    updated = 0
    not_found = 0

    try:
        for org in orgs:
            if not org.get('site_enriched'):
                continue

            # Find matching shelter
            shelter = db.query(Shelter).filter(
                Shelter.name == org.get('name'),
                Shelter.state == org.get('state')
            ).first()

            if not shelter:
                not_found += 1
                continue

            changed = False

            # Update with site_ fields if better than existing
            if org.get('site_phone') and not shelter.phone:
                shelter.phone = org['site_phone']
                changed = True
            if org.get('site_email') and not shelter.email:
                shelter.email = org['site_email']
                changed = True
            if org.get('site_address') and not shelter.address:
                shelter.address = org['site_address']
                changed = True

            # Social media
            for field in ['facebook_url', 'instagram_url', 'twitter_url', 'tiktok_url']:
                site_field = f'site_{field}'
                if org.get(site_field) and not getattr(shelter, field, None):
                    setattr(shelter, field, org[site_field])
                    changed = True

            if changed:
                shelter.last_verified_at = datetime.utcnow()
                updated += 1

        db.commit()
        print(f"  Updated: {updated}")
        print(f"  Not found in DB: {not_found}")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

    return updated, not_found


# ==========================
# CLI
# ==========================

def interactive_mode():
    """Interactive menu-driven mode."""
    print("\n=== Best Friends Network - Website Enricher (Phase 3) ===")
    print(f"Output: {SITE_ENRICHED_JSON}")

    orgs = load_input_orgs()
    if not orgs:
        return

    existing = load_site_enriched()
    progress = load_progress()

    # Build index
    index = {org_key(o): o for o in existing}

    # Merge base orgs into index (keeping enriched data)
    for org in orgs:
        key = org_key(org)
        if key not in index:
            index[key] = org

    site_enriched_count = sum(1 for o in index.values() if o.get('site_enriched'))
    print(f"\nTotal orgs: {len(orgs)}")
    print(f"Already site-enriched: {site_enriched_count}")
    print(f"Remaining: {len(orgs) - site_enriched_count}")

    while True:
        print("\n" + "=" * 50)
        print("Options:")
        print("  [N] Next batch (process 50 websites)")
        print("  [A] Process ALL remaining websites")
        print("  [D] Update database with enriched data")
        print("  [S] Show stats")
        print("  [Q] Quit")

        choice = input("Enter choice: ").strip().lower()

        if choice == 'q':
            break

        elif choice == 's':
            total = len(index)
            with_site_email = sum(1 for o in index.values() if o.get('site_email'))
            with_site_phone = sum(1 for o in index.values() if o.get('site_phone'))
            with_site_address = sum(1 for o in index.values() if o.get('site_address'))
            enriched = sum(1 for o in index.values() if o.get('site_enriched'))

            print(f"\n  Total orgs: {total}")
            print(f"  Site-enriched: {enriched}")
            print(f"  With site_email: {with_site_email}")
            print(f"  With site_phone: {with_site_phone}")
            print(f"  With site_address: {with_site_address}")

        elif choice == 'n':
            processed = process_batch(orgs, index, progress, verbose=True)
            save_site_enriched_json(list(index.values()))
            save_site_enriched_csv(list(index.values()))
            save_progress(progress)
            print(f"\n  Batch complete! Processed: {processed} websites")

        elif choice == 'a':
            total = process_all(orgs, index, progress)
            save_site_enriched_json(list(index.values()))
            save_site_enriched_csv(list(index.values()))
            save_progress(progress)
            print(f"\n  All done! Total processed: {total}")

        elif choice == 'd':
            update_database(list(index.values()))

        else:
            print("  Unknown choice.")

    # Final save
    save_site_enriched_json(list(index.values()))
    save_site_enriched_csv(list(index.values()))
    save_progress(progress)
    print("\nDone!")


def main():
    parser = argparse.ArgumentParser(description="Enrich orgs from their own websites (Phase 3)")
    parser.add_argument('--all', action='store_true', help="Process all remaining websites")
    parser.add_argument('--db', action='store_true', help="Update database after processing")
    parser.add_argument('--batch', type=int, default=0, help="Process N websites then stop")

    args = parser.parse_args()

    if args.all or args.batch > 0:
        # Non-interactive mode
        orgs = load_input_orgs()
        if not orgs:
            return

        existing = load_site_enriched()
        progress = load_progress()

        index = {org_key(o): o for o in existing}
        for org in orgs:
            key = org_key(org)
            if key not in index:
                index[key] = org

        print(f"Loaded {len(orgs)} orgs, {len(existing)} already processed")

        if args.all:
            total = process_all(orgs, index, progress)
        else:
            total = 0
            remaining = args.batch
            while remaining > 0:
                batch = min(remaining, 50)
                processed = process_batch(orgs, index, progress, batch_size=batch, verbose=True)
                total += processed
                remaining -= processed
                if processed == 0:
                    break

                save_site_enriched_json(list(index.values()))
                save_progress(progress)

        save_site_enriched_json(list(index.values()))
        save_site_enriched_csv(list(index.values()))
        save_progress(progress)

        print(f"\nComplete! Processed {total} websites")

        if args.db:
            update_database(list(index.values()))
    else:
        interactive_mode()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted.")
        sys.exit(0)

#!/usr/bin/env python3
"""
===============================================================================
AI Web Enrichment Agent - Deep Contact Info Extraction
===============================================================================
Visits organization websites, crawls internal pages, and extracts:
  - Phone numbers
  - Email addresses
  - Physical addresses
  - Social media URLs
  - Extended descriptions

Features:
  - Multi-threaded for rapid iteration
  - Intelligent page prioritization (Contact, About pages first)
  - Robust extraction with multiple fallback patterns
  - Rate limiting to respect websites
  - Checkpoint saving for resume capability

Usage:
    python -m agents.web_enrichment_agent --batch 100 --workers 5
    python -m agents.web_enrichment_agent --all

===============================================================================
"""
import sys
import os
import re
import time
import json
import argparse
from datetime import datetime, timezone
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass, asdict, field
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin, urlparse
import hashlib

import requests
from bs4 import BeautifulSoup

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# ==========================
# CONFIG
# ==========================

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

# Pages to prioritize when crawling
PRIORITY_PAGES = [
    '/contact', '/contact-us', '/contactus', '/contact.html',
    '/about', '/about-us', '/aboutus', '/about.html',
    '/info', '/information',
    '/adopt', '/adoption', '/adoptions',
    '/location', '/locations', '/find-us',
    '/hours', '/visit', '/visit-us',
]

# Default timeouts
REQUEST_TIMEOUT = 15
MAX_PAGES_PER_SITE = 5  # Limit internal page crawling

# Data directory
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
os.makedirs(DATA_DIR, exist_ok=True)

CHECKPOINT_FILE = os.path.join(DATA_DIR, 'enrichment_checkpoint.json')
RESULTS_FILE = os.path.join(DATA_DIR, 'enrichment_results.json')


# ==========================
# EXTRACTION PATTERNS
# ==========================

PHONE_PATTERNS = [
    r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',  # (555) 555-5555
    r'\d{3}[-.\s]\d{3}[-.\s]\d{4}',           # 555-555-5555
    r'1[-.\s]?\d{3}[-.\s]?\d{3}[-.\s]?\d{4}', # 1-555-555-5555
]

EMAIL_PATTERN = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'

ADDRESS_PATTERNS = [
    r'\d+\s+[\w\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Way|Court|Ct|Circle|Cir|Highway|Hwy|Parkway|Pkwy)\.?(?:\s+(?:Suite|Ste|Unit|Apt|#)\s*\d+)?',
]

ZIP_PATTERN = r'\b\d{5}(?:-\d{4})?\b'

SOCIAL_PATTERNS = {
    'facebook': r'(?:facebook\.com|fb\.com)/[\w.-]+',
    'instagram': r'instagram\.com/[\w.-]+',
    'twitter': r'(?:twitter\.com|x\.com)/[\w.-]+',
    'tiktok': r'tiktok\.com/@?[\w.-]+',
    'youtube': r'youtube\.com/(?:c/|channel/|user/)?[\w.-]+',
}


# ==========================
# ENRICHMENT RESULT
# ==========================

@dataclass
class EnrichmentResult:
    """Results from enriching a shelter's website."""
    shelter_id: int
    website: str
    success: bool = False
    error: Optional[str] = None

    # Extracted data
    phone: str = ""
    email: str = ""
    address: str = ""
    zip_code: str = ""
    description: str = ""

    # Social media
    facebook_url: str = ""
    instagram_url: str = ""
    twitter_url: str = ""
    tiktok_url: str = ""
    youtube_url: str = ""

    # Metadata
    pages_crawled: int = 0
    enriched_at: str = ""

    def __post_init__(self):
        if not self.enriched_at:
            self.enriched_at = datetime.now(timezone.utc).isoformat()


# ==========================
# EXTRACTION HELPERS
# ==========================

def extract_phone(text: str) -> str:
    """Extract phone number from text."""
    # First look for explicit phone labels
    labeled_patterns = [
        r'(?:Phone|Tel|Call|Contact|Office|Fax)[:\s]*\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
        r'(?:Phone|Tel|Call)[:\s]*1?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
    ]
    for pattern in labeled_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            # Extract just the number
            num_match = re.search(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', match.group(0))
            if num_match:
                return normalize_phone(num_match.group(0))

    # Fall back to any phone number
    for pattern in PHONE_PATTERNS:
        match = re.search(pattern, text)
        if match:
            return normalize_phone(match.group(0))
    return ""


def normalize_phone(phone: str) -> str:
    """Normalize phone to consistent format."""
    digits = re.sub(r'\D', '', phone)
    if len(digits) == 11 and digits[0] == '1':
        digits = digits[1:]
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    return phone


def extract_email(text: str) -> str:
    """Extract email from text."""
    match = re.search(EMAIL_PATTERN, text, re.IGNORECASE)
    if match:
        email = match.group(0).lower()
        # Filter out common false positives
        if not any(x in email for x in ['example.com', 'domain.com', 'email.com', '.png', '.jpg', '.gif']):
            return email
    return ""


def extract_address(text: str) -> Tuple[str, str]:
    """Extract street address and zip code from text."""
    address = ""
    zip_code = ""

    for pattern in ADDRESS_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            address = match.group(0).strip()
            break

    zip_match = re.search(ZIP_PATTERN, text)
    if zip_match:
        zip_code = zip_match.group(0)

    return address, zip_code


def extract_social_urls(soup: BeautifulSoup) -> Dict[str, str]:
    """Extract social media URLs from page."""
    social = {
        'facebook_url': '',
        'instagram_url': '',
        'twitter_url': '',
        'tiktok_url': '',
        'youtube_url': '',
    }

    for link in soup.find_all('a', href=True):
        href = link.get('href', '').lower()

        if 'facebook.com' in href and not social['facebook_url']:
            social['facebook_url'] = link.get('href', '')
        elif 'instagram.com' in href and not social['instagram_url']:
            social['instagram_url'] = link.get('href', '')
        elif ('twitter.com' in href or 'x.com' in href) and not social['twitter_url']:
            social['twitter_url'] = link.get('href', '')
        elif 'tiktok.com' in href and not social['tiktok_url']:
            social['tiktok_url'] = link.get('href', '')
        elif 'youtube.com' in href and not social['youtube_url']:
            social['youtube_url'] = link.get('href', '')

    return social


def extract_description(soup: BeautifulSoup, page_text: str) -> str:
    """Extract organization description."""
    # Try meta description first
    meta = soup.find('meta', {'name': 'description'})
    if meta and meta.get('content'):
        return meta.get('content', '')[:500]

    # Try og:description
    og_desc = soup.find('meta', {'property': 'og:description'})
    if og_desc and og_desc.get('content'):
        return og_desc.get('content', '')[:500]

    # Try first substantial paragraph
    for p in soup.find_all('p'):
        text = p.get_text(strip=True)
        if len(text) > 100 and len(text) < 1000:
            return text[:500]

    return ""


# ==========================
# WEB CRAWLER
# ==========================

def fetch_page(url: str) -> Optional[BeautifulSoup]:
    """Fetch and parse a webpage."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT, allow_redirects=True)
        if resp.status_code == 200:
            return BeautifulSoup(resp.text, 'html.parser')
    except Exception:
        pass
    return None


def find_internal_links(soup: BeautifulSoup, base_url: str) -> List[str]:
    """Find internal links that might have contact info."""
    links = []
    base_domain = urlparse(base_url).netloc

    for link in soup.find_all('a', href=True):
        href = link.get('href', '')

        # Skip empty, anchors, javascript
        if not href or href.startswith('#') or href.startswith('javascript:'):
            continue

        # Build absolute URL
        if href.startswith('/'):
            full_url = urljoin(base_url, href)
        elif href.startswith('http'):
            full_url = href
        else:
            full_url = urljoin(base_url, href)

        # Check if same domain
        link_domain = urlparse(full_url).netloc
        if link_domain != base_domain:
            continue

        # Prioritize contact/about pages
        path = urlparse(full_url).path.lower()
        for priority in PRIORITY_PAGES:
            if priority in path:
                links.insert(0, full_url)
                break
        else:
            links.append(full_url)

    # Dedupe while preserving order
    seen = set()
    unique_links = []
    for link in links:
        normalized = urlparse(link)._replace(fragment='').geturl()
        if normalized not in seen:
            seen.add(normalized)
            unique_links.append(link)

    return unique_links[:MAX_PAGES_PER_SITE]


def enrich_from_website(shelter_id: int, website: str) -> EnrichmentResult:
    """
    Main enrichment function - crawl a website and extract contact info.
    """
    result = EnrichmentResult(shelter_id=shelter_id, website=website)

    if not website:
        result.error = "No website URL"
        return result

    # Normalize URL
    if not website.startswith('http'):
        website = 'https://' + website

    try:
        # Fetch homepage
        soup = fetch_page(website)
        if not soup:
            result.error = "Could not fetch homepage"
            return result

        result.pages_crawled = 1
        page_text = soup.get_text(' ', strip=True)

        # Extract from homepage
        result.phone = extract_phone(page_text)
        result.email = extract_email(page_text)
        result.address, result.zip_code = extract_address(page_text)
        result.description = extract_description(soup, page_text)

        # Extract social media
        social = extract_social_urls(soup)
        result.facebook_url = social['facebook_url']
        result.instagram_url = social['instagram_url']
        result.twitter_url = social['twitter_url']
        result.tiktok_url = social['tiktok_url']

        # Check mailto/tel links on homepage
        if not result.email:
            mailto = soup.find('a', href=re.compile(r'^mailto:', re.I))
            if mailto:
                email = mailto.get('href', '').replace('mailto:', '').split('?')[0]
                if '@' in email:
                    result.email = email.lower()

        if not result.phone:
            tel = soup.find('a', href=re.compile(r'^tel:', re.I))
            if tel:
                phone = re.sub(r'\D', '', tel.get('href', '').replace('tel:', ''))
                if len(phone) >= 10:
                    result.phone = normalize_phone(phone)

        # If missing key info, crawl internal pages
        if not result.phone or not result.email:
            internal_links = find_internal_links(soup, website)

            for link in internal_links:
                if result.phone and result.email:
                    break

                time.sleep(0.3)  # Polite delay
                page_soup = fetch_page(link)
                if not page_soup:
                    continue

                result.pages_crawled += 1
                page_text = page_soup.get_text(' ', strip=True)

                if not result.phone:
                    result.phone = extract_phone(page_text)
                    if not result.phone:
                        tel = page_soup.find('a', href=re.compile(r'^tel:', re.I))
                        if tel:
                            phone = re.sub(r'\D', '', tel.get('href', '').replace('tel:', ''))
                            if len(phone) >= 10:
                                result.phone = normalize_phone(phone)

                if not result.email:
                    result.email = extract_email(page_text)
                    if not result.email:
                        mailto = page_soup.find('a', href=re.compile(r'^mailto:', re.I))
                        if mailto:
                            email = mailto.get('href', '').replace('mailto:', '').split('?')[0]
                            if '@' in email:
                                result.email = email.lower()

                if not result.address:
                    result.address, zip_code = extract_address(page_text)
                    if zip_code and not result.zip_code:
                        result.zip_code = zip_code

                # Check for more social links
                if not result.facebook_url or not result.instagram_url:
                    social = extract_social_urls(page_soup)
                    if not result.facebook_url:
                        result.facebook_url = social['facebook_url']
                    if not result.instagram_url:
                        result.instagram_url = social['instagram_url']

        result.success = True

    except Exception as e:
        result.error = str(e)[:200]

    return result


# ==========================
# BATCH PROCESSING
# ==========================

def get_shelters_needing_enrichment(limit: int = 100) -> List[Dict]:
    """Get shelters that have websites but missing contact info."""
    try:
        from app.database import SessionLocal, init_db
        from app.models import Shelter
    except ImportError as e:
        print(f"ERROR: Could not import database: {e}")
        return []

    init_db()
    db = SessionLocal()

    try:
        # Get shelters with websites but missing phone OR email
        shelters = db.query(Shelter).filter(
            Shelter.website.isnot(None),
            Shelter.website != '',
            (Shelter.phone.is_(None) | (Shelter.phone == '')) |
            (Shelter.email.is_(None) | (Shelter.email == ''))
        ).limit(limit).all()

        return [{
            'id': s.id,
            'name': s.name,
            'website': s.website,
            'phone': s.phone,
            'email': s.email,
        } for s in shelters]
    finally:
        db.close()


def update_shelter_with_result(result: EnrichmentResult) -> bool:
    """Update database with enrichment results."""
    try:
        from app.database import SessionLocal
        from app.models import Shelter
    except ImportError:
        return False

    if not result.success:
        return False

    db = SessionLocal()
    try:
        shelter = db.query(Shelter).filter(Shelter.id == result.shelter_id).first()
        if not shelter:
            return False

        # Only update fields that were missing
        updated = False

        if result.phone and not shelter.phone:
            shelter.phone = result.phone
            updated = True
        if result.email and not shelter.email:
            shelter.email = result.email
            updated = True
        if result.address and not shelter.address:
            shelter.address = result.address
            updated = True
        if result.zip_code and not shelter.zip_code:
            shelter.zip_code = result.zip_code
            updated = True
        if result.description and not shelter.description:
            shelter.description = result.description
            updated = True
        if result.facebook_url and not shelter.facebook_url:
            shelter.facebook_url = result.facebook_url
            updated = True
        if result.instagram_url and not shelter.instagram_url:
            shelter.instagram_url = result.instagram_url
            updated = True
        if result.twitter_url and not shelter.twitter_url:
            shelter.twitter_url = result.twitter_url
            updated = True
        if result.tiktok_url and not shelter.tiktok_url:
            shelter.tiktok_url = result.tiktok_url
            updated = True

        if updated:
            shelter.last_verified_at = datetime.now(timezone.utc)
            db.commit()

        return updated
    except Exception as e:
        db.rollback()
        return False
    finally:
        db.close()


def run_enrichment_batch(batch_size: int = 100, workers: int = 5, db_update: bool = True):
    """Run enrichment on a batch of shelters."""
    print("\n" + "=" * 60)
    print("AI WEB ENRICHMENT AGENT")
    print("=" * 60)
    print(f"Batch size: {batch_size}")
    print(f"Workers: {workers}")
    print(f"Database update: {db_update}")
    print("=" * 60 + "\n")

    # Get shelters needing enrichment
    shelters = get_shelters_needing_enrichment(batch_size)
    print(f"Found {len(shelters)} shelters needing enrichment\n")

    if not shelters:
        print("No shelters need enrichment!")
        return

    results = []
    success_count = 0
    phone_found = 0
    email_found = 0

    start_time = time.time()

    # Process with thread pool
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(enrich_from_website, s['id'], s['website']): s
            for s in shelters
        }

        for i, future in enumerate(as_completed(futures)):
            shelter = futures[future]
            try:
                result = future.result()
                results.append(asdict(result))

                if result.success:
                    success_count += 1
                    if result.phone:
                        phone_found += 1
                    if result.email:
                        email_found += 1

                    # Update database
                    if db_update:
                        update_shelter_with_result(result)

                # Progress update
                if (i + 1) % 10 == 0 or i == len(shelters) - 1:
                    elapsed = time.time() - start_time
                    rate = (i + 1) / elapsed
                    print(f"  Processed {i + 1}/{len(shelters)} | "
                          f"Success: {success_count} | "
                          f"Phone: {phone_found} | Email: {email_found} | "
                          f"Rate: {rate:.1f}/sec")

            except Exception as e:
                print(f"  Error processing {shelter['name']}: {e}")

    # Save results
    with open(RESULTS_FILE, 'w') as f:
        json.dump(results, f, indent=2)

    # Final stats
    elapsed = time.time() - start_time
    print("\n" + "=" * 60)
    print("ENRICHMENT COMPLETE")
    print("=" * 60)
    print(f"Total processed: {len(shelters)}")
    print(f"Successful: {success_count} ({success_count*100//max(len(shelters),1)}%)")
    print(f"Phone found: {phone_found} ({phone_found*100//max(len(shelters),1)}%)")
    print(f"Email found: {email_found} ({email_found*100//max(len(shelters),1)}%)")
    print(f"Time: {elapsed:.1f} seconds")
    print(f"Rate: {len(shelters)/elapsed:.1f} shelters/sec")
    print(f"\nResults saved to: {RESULTS_FILE}")


def run_all_enrichment(workers: int = 10, iterations: int = 100):
    """Run enrichment on ALL shelters that need it, in iterations."""
    print("\n" + "=" * 60)
    print("AI WEB ENRICHMENT AGENT - FULL RUN")
    print("=" * 60)
    print(f"Workers: {workers}")
    print(f"Max iterations: {iterations}")
    print("=" * 60 + "\n")

    total_processed = 0
    total_phone = 0
    total_email = 0

    for iteration in range(iterations):
        # Get next batch
        shelters = get_shelters_needing_enrichment(100)

        if not shelters:
            print(f"\nNo more shelters need enrichment!")
            break

        print(f"\n--- Iteration {iteration + 1} ({len(shelters)} shelters) ---")

        success_count = 0
        phone_found = 0
        email_found = 0

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(enrich_from_website, s['id'], s['website']): s
                for s in shelters
            }

            for future in as_completed(futures):
                try:
                    result = future.result()

                    if result.success:
                        success_count += 1
                        if result.phone:
                            phone_found += 1
                        if result.email:
                            email_found += 1

                        update_shelter_with_result(result)
                except Exception:
                    pass

        total_processed += len(shelters)
        total_phone += phone_found
        total_email += email_found

        print(f"  Processed: {len(shelters)} | Phone: {phone_found} | Email: {email_found}")

    print("\n" + "=" * 60)
    print("FULL ENRICHMENT COMPLETE")
    print("=" * 60)
    print(f"Total processed: {total_processed}")
    print(f"Total phone found: {total_phone}")
    print(f"Total email found: {total_email}")


# ==========================
# CLI
# ==========================

def main():
    parser = argparse.ArgumentParser(description="AI Web Enrichment Agent")
    parser.add_argument('--batch', type=int, default=100, help='Batch size')
    parser.add_argument('--workers', type=int, default=5, help='Number of workers')
    parser.add_argument('--all', action='store_true', help='Run on all shelters needing enrichment')
    parser.add_argument('--no-db', action='store_true', help='Don\'t update database')
    parser.add_argument('--test', type=str, help='Test single URL')

    args = parser.parse_args()

    if args.test:
        print(f"Testing URL: {args.test}")
        result = enrich_from_website(0, args.test)
        print(f"\nResult:")
        for key, value in asdict(result).items():
            if value:
                print(f"  {key}: {value}")
        return

    if args.all:
        run_all_enrichment(workers=args.workers)
    else:
        run_enrichment_batch(
            batch_size=args.batch,
            workers=args.workers,
            db_update=not args.no_db
        )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
        sys.exit(0)

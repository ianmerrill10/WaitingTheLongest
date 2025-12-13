#!/usr/bin/env python3
"""
===============================================================================
Best Friends Animal Society Network Scraper - FULL CONTACT INFO VERSION
===============================================================================
Scrapes ALL ~5,800+ rescue/shelter partners from Best Friends' public directory
AND visits each profile page to extract complete contact information.

Extracts:
    - Name, City, State
    - Phone number
    - Email address
    - Website URL
    - Facebook, Instagram, Twitter URLs
    - Full address

Usage:
    python scrape_bestfriends.py --all --db

===============================================================================
"""
import csv
import json
import os
import re
import sys
import time
import argparse
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any, Tuple, Set, Optional
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup, NavigableString, Tag

# Add backend to path for database imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# ==========================
# CONFIG
# ==========================

BATCH_SIZE = 50
PROFILE_DELAY = 0.5  # Delay between profile page fetches

# Data directory
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
os.makedirs(DATA_DIR, exist_ok=True)

DATA_JSON = os.path.join(DATA_DIR, "bf_network_orgs.json")
DATA_CSV = os.path.join(DATA_DIR, "bf_network_orgs.csv")
META_JSON = os.path.join(DATA_DIR, "bf_network_meta.json")

BASE_URL = "https://bestfriends.org/partners"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


# ==========================
# MODEL - NOW WITH FULL CONTACT INFO
# ==========================

@dataclass
class OrgRecord:
    name: str
    city: str
    state: str
    description: str
    profile_url: str
    # Contact info (extracted from profile page)
    phone: str = ""
    email: str = ""
    website: str = ""
    address: str = ""
    zip_code: str = ""
    # Social media
    facebook_url: str = ""
    instagram_url: str = ""
    twitter_url: str = ""
    # Metadata
    scraped_at: str = ""
    profile_scraped: bool = False

    def __post_init__(self):
        if not self.scraped_at:
            self.scraped_at = datetime.now(timezone.utc).isoformat()

    @property
    def key(self) -> str:
        """Unique key for deduplication"""
        return f"{self.name.strip().lower()}|{self.city.strip().lower()}|{self.state.strip().upper()}"


# ==========================
# STORAGE HELPERS
# ==========================

def load_existing() -> List[OrgRecord]:
    if not os.path.exists(DATA_JSON):
        return []
    with open(DATA_JSON, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return [OrgRecord(**item) for item in raw]


def save_json(orgs: List[OrgRecord]) -> None:
    with open(DATA_JSON, "w", encoding="utf-8") as f:
        json.dump([asdict(o) for o in orgs], f, ensure_ascii=False, indent=2)
    print(f"  Saved {len(orgs)} orgs to {DATA_JSON}")


def save_csv(orgs: List[OrgRecord]) -> None:
    fieldnames = [
        "name", "city", "state", "address", "zip_code",
        "phone", "email", "website",
        "facebook_url", "instagram_url", "twitter_url",
        "description", "profile_url", "scraped_at"
    ]
    with open(DATA_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for o in orgs:
            row = asdict(o)
            # Only include the fieldnames we want
            writer.writerow({k: row.get(k, "") for k in fieldnames})
    print(f"  Saved {len(orgs)} orgs to {DATA_CSV}")


def load_meta() -> Dict[str, Any]:
    if not os.path.exists(META_JSON):
        return {"next_page": 1, "exhausted": False, "last_run": None}
    with open(META_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


def save_meta(meta: Dict[str, Any]) -> None:
    meta["last_run"] = datetime.now(timezone.utc).isoformat()
    with open(META_JSON, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


# ==========================
# PROFILE PAGE SCRAPING - GET FULL CONTACT INFO
# ==========================

def extract_phone(text: str) -> str:
    """Extract phone number from text."""
    # Look for phone patterns
    patterns = [
        r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',  # (555) 555-5555 or 555-555-5555
        r'\d{3}[-.\s]\d{3}[-.\s]\d{4}',  # 555-555-5555
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0)
    return ""


def extract_email(text: str) -> str:
    """Extract email from text."""
    pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    match = re.search(pattern, text)
    if match:
        return match.group(0).lower()
    return ""


def clean_url(url: str) -> str:
    """Clean and normalize a URL."""
    if not url:
        return ""
    url = url.strip()
    if url.startswith("//"):
        url = "https:" + url
    if not url.startswith("http"):
        url = "https://" + url
    return url


def fetch_profile_details(profile_url: str) -> Dict[str, str]:
    """
    Fetch an org's profile page and extract all contact details.
    """
    details = {
        "phone": "",
        "email": "",
        "website": "",
        "address": "",
        "zip_code": "",
        "facebook_url": "",
        "instagram_url": "",
        "twitter_url": "",
        "description": "",
    }

    if not profile_url or "bestfriends.org" not in profile_url:
        return details

    try:
        resp = requests.get(profile_url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return details

        soup = BeautifulSoup(resp.text, "html.parser")
        page_text = soup.get_text(" ", strip=True)

        # === PHONE ===
        # Look for phone in common locations
        phone_patterns = [
            r'Phone[:\s]*\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
            r'Tel[:\s]*\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
            r'Call[:\s]*\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
        ]
        for pattern in phone_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                details["phone"] = extract_phone(match.group(0))
                break

        # If not found, look for tel: links
        if not details["phone"]:
            tel_link = soup.find("a", href=re.compile(r"^tel:", re.IGNORECASE))
            if tel_link:
                href = tel_link.get("href", "")
                phone = re.sub(r"[^\d]", "", href.replace("tel:", ""))
                if len(phone) >= 10:
                    details["phone"] = phone[:3] + "-" + phone[3:6] + "-" + phone[6:10]

        # === EMAIL ===
        # Look for mailto links first
        mailto_link = soup.find("a", href=re.compile(r"^mailto:", re.IGNORECASE))
        if mailto_link:
            href = mailto_link.get("href", "")
            email = href.replace("mailto:", "").split("?")[0].strip().lower()
            if "@" in email:
                details["email"] = email

        # If not found, search page text
        if not details["email"]:
            details["email"] = extract_email(page_text)

        # === WEBSITE ===
        # Look for "Visit Website" or similar links
        website_keywords = ["visit website", "our website", "website:", "web:"]
        for link in soup.find_all("a", href=True):
            link_text = link.get_text(strip=True).lower()
            href = link.get("href", "")

            # Skip internal Best Friends links
            if "bestfriends.org" in href:
                continue

            # Check if this looks like a website link
            if any(kw in link_text for kw in website_keywords):
                details["website"] = clean_url(href)
                break

            # Also check for http links that aren't social media
            if href.startswith("http") and not any(s in href for s in ["facebook", "instagram", "twitter", "tiktok", "youtube"]):
                if "bestfriends.org" not in href:
                    details["website"] = clean_url(href)

        # === SOCIAL MEDIA ===
        for link in soup.find_all("a", href=True):
            href = link.get("href", "").lower()
            if "facebook.com" in href and not details["facebook_url"]:
                details["facebook_url"] = clean_url(link.get("href", ""))
            elif "instagram.com" in href and not details["instagram_url"]:
                details["instagram_url"] = clean_url(link.get("href", ""))
            elif "twitter.com" in href or "x.com" in href and not details["twitter_url"]:
                details["twitter_url"] = clean_url(link.get("href", ""))

        # === ADDRESS ===
        # Look for address patterns
        address_pattern = r'\d+\s+[\w\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Way|Court|Ct)\.?(?:\s+#?\d+)?'
        match = re.search(address_pattern, page_text, re.IGNORECASE)
        if match:
            details["address"] = match.group(0).strip()

        # === ZIP CODE ===
        zip_pattern = r'\b\d{5}(?:-\d{4})?\b'
        match = re.search(zip_pattern, page_text)
        if match:
            details["zip_code"] = match.group(0)

        # === DESCRIPTION ===
        # Look for meta description or first paragraph
        meta_desc = soup.find("meta", {"name": "description"})
        if meta_desc and meta_desc.get("content"):
            details["description"] = meta_desc.get("content", "")[:500]

    except requests.RequestException as e:
        pass  # Silently fail on individual profile errors
    except Exception as e:
        pass

    return details


# ==========================
# DIRECTORY SCRAPING
# ==========================

def fetch_page(page: int, retries: int = 3) -> BeautifulSoup:
    """Fetch one page of Best Friends partners."""
    params = {
        "np_prox[source_configuration][origin_address]": "",
        "np_prox[value]": "50",
        "page": page,
        "title": "",
    }

    for attempt in range(retries):
        try:
            resp = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=30)
            if resp.status_code == 200:
                return BeautifulSoup(resp.text, "html.parser")
            elif resp.status_code == 429:
                wait_time = 10 * (attempt + 1)
                print(f"    Rate limited, waiting {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise RuntimeError(f"HTTP {resp.status_code}")
        except requests.RequestException as e:
            if attempt < retries - 1:
                time.sleep(2)
            else:
                raise RuntimeError(f"Failed after {retries} attempts: {e}")

    raise RuntimeError(f"Failed to fetch page {page}")


def is_city_state_line(text: str) -> bool:
    """Check if text looks like 'City, ST' format"""
    if not text:
        return False
    text = text.strip()
    return bool(re.search(r".+,\s*[A-Z]{2}\b", text))


def extract_orgs_from_page(soup: BeautifulSoup) -> List[Dict]:
    """Parse a directory page and return basic org info."""
    orgs = []
    main = soup.find("main") or soup

    for city_node in main.find_all(string=is_city_state_line):
        city_state_text = city_node.strip()
        parts = [p.strip() for p in city_state_text.split(",")]
        if len(parts) < 2:
            continue

        city = parts[0]
        state = parts[1][:2]

        link = city_node.find_previous("a")
        if not link:
            continue

        name = link.get_text(strip=True)
        if not name or len(name) < 2:
            continue

        href = link.get("href") or ""
        if href.startswith("/"):
            profile_url = f"https://bestfriends.org{href}"
        else:
            profile_url = href

        # Get basic description
        description_parts = []
        node = city_node
        while True:
            node = node.next_sibling
            if node is None:
                break
            if isinstance(node, NavigableString):
                txt = node.strip()
                if txt:
                    description_parts.append(txt)
                continue
            if isinstance(node, Tag):
                if node.name == "a":
                    break
                txt = node.get_text(" ", strip=True)
                if txt:
                    description_parts.append(txt)

        description = " ".join(description_parts).strip()

        # Filter out navigation text
        bad_prefixes = ("Previous page", "First page", "Current page", "Last page", "Find a network partner", "Search by City", "Next page")
        for prefix in bad_prefixes:
            if description.lower().startswith(prefix.lower()):
                description = ""
                break

        orgs.append({
            "name": name,
            "city": city,
            "state": state,
            "description": description,
            "profile_url": profile_url,
        })

    return orgs


# ==========================
# MAIN SCRAPE WITH FULL CONTACT INFO
# ==========================

def scrape_all_with_details() -> Tuple[List[OrgRecord], int]:
    """
    Scrape all orgs AND fetch full contact details from each profile page.
    """
    print("\n" + "=" * 60)
    print("BEST FRIENDS NETWORK SCRAPER - FULL CONTACT INFO")
    print("=" * 60)
    print("This will:")
    print("  1. Scrape all ~4,600 orgs from the directory")
    print("  2. Visit EACH org's profile page for contact details")
    print("  3. Extract: phone, email, website, social media, address")
    print("\nEstimated time: 30-45 minutes")
    print("=" * 60 + "\n")

    all_orgs: List[OrgRecord] = []
    seen_keys: Set[str] = set()

    page = 1
    empty_streak = 0
    total_profiles_fetched = 0

    while empty_streak < 3 and page <= 400:
        try:
            soup = fetch_page(page)
        except RuntimeError as e:
            print(f"  ERROR on page {page}: {e}")
            break

        page_orgs = extract_orgs_from_page(soup)

        if not page_orgs:
            empty_streak += 1
            page += 1
            time.sleep(0.5)
            continue

        empty_streak = 0
        new_count = 0

        for org_data in page_orgs:
            key = f"{org_data['name'].strip().lower()}|{org_data['city'].strip().lower()}|{org_data['state'].strip().upper()}"
            if key in seen_keys:
                continue
            seen_keys.add(key)

            # Fetch full profile details
            profile_details = fetch_profile_details(org_data["profile_url"])
            total_profiles_fetched += 1

            # Create full record
            org = OrgRecord(
                name=org_data["name"],
                city=org_data["city"],
                state=org_data["state"],
                description=profile_details.get("description") or org_data["description"],
                profile_url=org_data["profile_url"],
                phone=profile_details.get("phone", ""),
                email=profile_details.get("email", ""),
                website=profile_details.get("website", ""),
                address=profile_details.get("address", ""),
                zip_code=profile_details.get("zip_code", ""),
                facebook_url=profile_details.get("facebook_url", ""),
                instagram_url=profile_details.get("instagram_url", ""),
                twitter_url=profile_details.get("twitter_url", ""),
                profile_scraped=True,
            )

            all_orgs.append(org)
            new_count += 1

            # Brief delay between profile fetches
            time.sleep(PROFILE_DELAY)

        print(f"  Page {page}: {len(page_orgs)} listings, {new_count} new orgs (Total: {len(all_orgs)})")

        # Save checkpoint every 10 pages
        if page % 10 == 0:
            save_json(all_orgs)

            # Show contact info stats
            has_phone = sum(1 for o in all_orgs if o.phone)
            has_email = sum(1 for o in all_orgs if o.email)
            has_website = sum(1 for o in all_orgs if o.website)
            print(f"    Checkpoint: {len(all_orgs)} orgs | Phone: {has_phone} | Email: {has_email} | Website: {has_website}")

        page += 1
        time.sleep(0.8)

    print(f"\n  Scraping complete!")
    print(f"  Total orgs: {len(all_orgs)}")
    print(f"  Profile pages fetched: {total_profiles_fetched}")

    # Final contact stats
    has_phone = sum(1 for o in all_orgs if o.phone)
    has_email = sum(1 for o in all_orgs if o.email)
    has_website = sum(1 for o in all_orgs if o.website)
    has_facebook = sum(1 for o in all_orgs if o.facebook_url)
    has_instagram = sum(1 for o in all_orgs if o.instagram_url)

    print(f"\n  Contact Info Extracted:")
    print(f"    Phone:     {has_phone} ({has_phone*100//max(len(all_orgs),1)}%)")
    print(f"    Email:     {has_email} ({has_email*100//max(len(all_orgs),1)}%)")
    print(f"    Website:   {has_website} ({has_website*100//max(len(all_orgs),1)}%)")
    print(f"    Facebook:  {has_facebook} ({has_facebook*100//max(len(all_orgs),1)}%)")
    print(f"    Instagram: {has_instagram} ({has_instagram*100//max(len(all_orgs),1)}%)")

    return all_orgs, len(all_orgs)


# ==========================
# DATABASE INGESTION
# ==========================

def ingest_to_database(orgs: List[OrgRecord]) -> Tuple[int, int]:
    """Ingest scraped orgs into the Shelter database."""
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
        for i, org in enumerate(orgs):
            existing = db.query(Shelter).filter(
                Shelter.name == org.name,
                Shelter.state == org.state
            ).first()

            if existing:
                # Update with new contact info
                if org.phone and not existing.phone:
                    existing.phone = org.phone
                if org.email and not existing.email:
                    existing.email = org.email
                if org.website and not existing.website:
                    existing.website = org.website
                if org.address and not existing.address:
                    existing.address = org.address
                if org.zip_code and not existing.zip_code:
                    existing.zip_code = org.zip_code
                if org.facebook_url and not existing.facebook_url:
                    existing.facebook_url = org.facebook_url
                if org.instagram_url and not existing.instagram_url:
                    existing.instagram_url = org.instagram_url
                if org.twitter_url and not existing.twitter_url:
                    existing.twitter_url = org.twitter_url
                if org.description and not existing.description:
                    existing.description = org.description
                existing.last_verified_at = datetime.now(timezone.utc)
                updated += 1
            else:
                shelter = Shelter(
                    name=org.name,
                    city=org.city,
                    state=org.state,
                    address=org.address,
                    zip_code=org.zip_code,
                    phone=org.phone,
                    email=org.email,
                    website=org.website or org.profile_url,
                    description=org.description or "[Best Friends Network Partner]",
                    facebook_url=org.facebook_url,
                    instagram_url=org.instagram_url,
                    twitter_url=org.twitter_url,
                    source="bestfriends_network",
                    org_type="rescue",
                    last_verified_at=datetime.now(timezone.utc)
                )
                db.add(shelter)
                created += 1

            if (i + 1) % 100 == 0:
                db.commit()
                print(f"  Processed {i + 1}/{len(orgs)} orgs...")

        db.commit()
        print(f"\n  Database ingestion complete!")
        print(f"  Created: {created}")
        print(f"  Updated: {updated}")

    except Exception as e:
        print(f"ERROR during database ingestion: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

    return created, updated


# ==========================
# CLI
# ==========================

def main():
    parser = argparse.ArgumentParser(
        description="Scrape Best Friends Network with FULL contact info"
    )
    parser.add_argument("--all", action="store_true", help="Scrape all orgs with full details")
    parser.add_argument("--db", action="store_true", help="Ingest to database")
    parser.add_argument("--fresh", action="store_true", help="Start fresh (ignore existing data)")

    args = parser.parse_args()

    if args.fresh:
        # Clear existing data files
        for f in [DATA_JSON, DATA_CSV, META_JSON]:
            if os.path.exists(f):
                os.remove(f)
        print("Cleared existing data files.")

    if args.all:
        orgs, count = scrape_all_with_details()

        save_json(orgs)
        save_csv(orgs)

        print(f"\nComplete! Total orgs with contact info: {count}")

        if args.db:
            ingest_to_database(orgs)
    else:
        print("Usage: python scrape_bestfriends.py --all --db")
        print("  --all    Scrape all orgs with full contact details")
        print("  --db     Also save to database")
        print("  --fresh  Clear existing data and start fresh")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
        sys.exit(0)

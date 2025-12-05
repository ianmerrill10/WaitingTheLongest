#!/usr/bin/env python3
"""
===============================================================================
Best Friends Network - FAST Directory Scraper
===============================================================================
Quickly scrapes ALL ~4,600 rescue/shelter partners from Best Friends' directory.
Does NOT visit individual profile pages - just collects directory listings.

Use the AI Web Enrichment Agent afterward to get full contact info.

Speed: ~5 minutes for all 4,600+ orgs (vs 45+ minutes for full profile scraping)

Usage:
    python scrape_bestfriends_fast.py --all --db

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
from typing import List, Dict, Any, Tuple, Set
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup, NavigableString, Tag

# Add backend to path for database imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# ==========================
# CONFIG
# ==========================

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
os.makedirs(DATA_DIR, exist_ok=True)

DATA_JSON = os.path.join(DATA_DIR, "bf_network_orgs.json")
DATA_CSV = os.path.join(DATA_DIR, "bf_network_orgs.csv")

BASE_URL = "https://bestfriends.org/partners"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


# ==========================
# MODEL
# ==========================

@dataclass
class OrgRecord:
    name: str
    city: str
    state: str
    description: str
    profile_url: str
    website: str = ""
    scraped_at: str = ""

    def __post_init__(self):
        if not self.scraped_at:
            self.scraped_at = datetime.now(timezone.utc).isoformat()

    @property
    def key(self) -> str:
        return f"{self.name.strip().lower()}|{self.city.strip().lower()}|{self.state.strip().upper()}"


# ==========================
# STORAGE
# ==========================

def save_json(orgs: List[OrgRecord]) -> None:
    with open(DATA_JSON, "w", encoding="utf-8") as f:
        json.dump([asdict(o) for o in orgs], f, ensure_ascii=False, indent=2)


def save_csv(orgs: List[OrgRecord]) -> None:
    fieldnames = ["name", "city", "state", "website", "profile_url", "description", "scraped_at"]
    with open(DATA_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for o in orgs:
            row = asdict(o)
            writer.writerow({k: row.get(k, "") for k in fieldnames})


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
                wait_time = 5 * (attempt + 1)
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
    """Parse a directory page and return org info."""
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

        # Get description from surrounding text
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


def scrape_all_fast() -> Tuple[List[OrgRecord], int]:
    """
    FAST scrape - just directory listings, no profile page visits.
    """
    print("\n" + "=" * 60)
    print("BEST FRIENDS NETWORK - FAST DIRECTORY SCRAPER")
    print("=" * 60)
    print("Scraping directory listings only (no profile page visits)")
    print("Use the AI Web Enrichment Agent to get full contact info")
    print("=" * 60 + "\n")

    all_orgs: List[OrgRecord] = []
    seen_keys: Set[str] = set()

    page = 1
    empty_streak = 0

    start_time = time.time()

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
            time.sleep(0.3)
            continue

        empty_streak = 0
        new_count = 0

        for org_data in page_orgs:
            key = f"{org_data['name'].strip().lower()}|{org_data['city'].strip().lower()}|{org_data['state'].strip().upper()}"
            if key in seen_keys:
                continue
            seen_keys.add(key)

            # Profile URL acts as website for now
            org = OrgRecord(
                name=org_data["name"],
                city=org_data["city"],
                state=org_data["state"],
                description=org_data["description"],
                profile_url=org_data["profile_url"],
                website=org_data["profile_url"],  # Will be updated by enrichment
            )

            all_orgs.append(org)
            new_count += 1

        print(f"  Page {page}: {len(page_orgs)} listings, {new_count} new (Total: {len(all_orgs)})")

        # Save checkpoint every 20 pages
        if page % 20 == 0:
            save_json(all_orgs)
            elapsed = time.time() - start_time
            rate = len(all_orgs) / elapsed
            print(f"    Checkpoint: {len(all_orgs)} orgs | Rate: {rate:.1f}/sec")

        page += 1
        time.sleep(0.3)  # Polite delay

    elapsed = time.time() - start_time
    print(f"\n  Scraping complete!")
    print(f"  Total orgs: {len(all_orgs)}")
    print(f"  Time: {elapsed:.1f} seconds")
    print(f"  Rate: {len(all_orgs)/elapsed:.1f} orgs/sec")

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
                # Update profile URL if missing
                if not existing.website or 'bestfriends.org' not in existing.website:
                    if not existing.website:
                        existing.website = org.profile_url
                existing.last_verified_at = datetime.now(timezone.utc)
                updated += 1
            else:
                shelter = Shelter(
                    name=org.name,
                    city=org.city,
                    state=org.state,
                    website=org.profile_url,
                    description=org.description or "[Best Friends Network Partner]",
                    source="bestfriends_network",
                    org_type="rescue",
                    last_verified_at=datetime.now(timezone.utc)
                )
                db.add(shelter)
                created += 1

            if (i + 1) % 500 == 0:
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
    parser = argparse.ArgumentParser(description="Fast Best Friends Network scraper")
    parser.add_argument("--all", action="store_true", help="Scrape all orgs (directory only)")
    parser.add_argument("--db", action="store_true", help="Ingest to database")

    args = parser.parse_args()

    if args.all:
        orgs, count = scrape_all_fast()

        save_json(orgs)
        save_csv(orgs)

        print(f"\n  Data saved to:")
        print(f"    - {DATA_JSON}")
        print(f"    - {DATA_CSV}")

        if args.db:
            ingest_to_database(orgs)

        print("\n  Next step: Run AI Web Enrichment Agent")
        print("    python -m agents.web_enrichment_agent --all")
    else:
        print("Usage: python scrape_bestfriends_fast.py --all --db")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
        sys.exit(0)

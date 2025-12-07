#!/usr/bin/env python3
"""
===============================================================================
RescueGroups.org Organization Ingestor
===============================================================================
Pulls ALL shelter/rescue organizations from RescueGroups API.
This gives us real contact data including email, phone, and website.

Usage:
    python ingest_rescuegroups_orgs.py         # Pull all orgs
    python ingest_rescuegroups_orgs.py --db    # Pull and save to database

===============================================================================
"""
import requests
import json
import os
import sys
import time
import argparse
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Config
API_KEY = 'Hu7Ew255'
BASE_URL = 'https://api.rescuegroups.org/http/v2.json'
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
os.makedirs(DATA_DIR, exist_ok=True)
OUTPUT_JSON = os.path.join(DATA_DIR, 'rescuegroups_orgs.json')

# Fields to request
ORG_FIELDS = [
    'orgID', 'orgName', 'orgCity', 'orgState', 'orgPostalcode',
    'orgEmail', 'orgPhone', 'orgFax', 'orgWebsiteUrl',
    'orgAddress', 'orgAbout', 'orgFacebookUrl',
    'orgType', 'orgCountry'
]


def fetch_orgs(start: int = 0, limit: int = 1000) -> dict:
    """Fetch organizations from RescueGroups API."""
    payload = {
        'apikey': API_KEY,
        'objectType': 'orgs',
        'objectAction': 'publicSearch',
        'search': {
            'resultStart': start,
            'resultLimit': limit,
            'resultSort': 'orgID',
            'resultOrder': 'asc',
            'calcFoundRows': 'Yes',
            'filters': [
                {
                    'fieldName': 'orgCountry',
                    'operation': 'equals',
                    'criteria': 'United States'
                }
            ],
            'fields': ORG_FIELDS
        }
    }

    resp = requests.post(BASE_URL, json=payload, timeout=60)
    if resp.status_code == 200:
        return resp.json()
    else:
        print(f"  Error: HTTP {resp.status_code}")
        return {}


def fetch_all_orgs() -> list:
    """Fetch ALL organizations from RescueGroups."""
    print("\n" + "=" * 60)
    print("RESCUEGROUPS ORGANIZATION INGESTOR")
    print("=" * 60)

    all_orgs = []
    start = 0
    batch_size = 1000
    total_found = None

    while True:
        print(f"  Fetching orgs {start} to {start + batch_size}...")

        data = fetch_orgs(start, batch_size)

        if not data or 'data' not in data:
            print("  No data returned, stopping.")
            break

        orgs = data.get('data', {})
        found_rows = int(data.get('foundRows', 0))

        if total_found is None:
            total_found = found_rows
            print(f"  Total orgs available: {total_found}")

        if not orgs:
            break

        # Process orgs
        for org_id, org in orgs.items():
            all_orgs.append({
                'external_id': org.get('orgID', ''),
                'name': org.get('orgName', ''),
                'city': org.get('orgCity', ''),
                'state': org.get('orgState', ''),
                'zip_code': org.get('orgPostalcode', ''),
                'email': org.get('orgEmail', ''),
                'phone': org.get('orgPhone', ''),
                'website': org.get('orgWebsiteUrl', ''),
                'address': org.get('orgAddress', ''),
                'description': org.get('orgAbout', '')[:500] if org.get('orgAbout') else '',
                'facebook_url': org.get('orgFacebookUrl', ''),
                'org_type': org.get('orgType', ''),
                'source': 'rescuegroups',
                'scraped_at': datetime.now(timezone.utc).isoformat()
            })

        print(f"    Got {len(orgs)} orgs (Total: {len(all_orgs)})")

        start += batch_size

        if start >= total_found:
            break

        time.sleep(2)  # Be polite to API - 2 seconds between batches

    print(f"\n  Total organizations fetched: {len(all_orgs)}")
    return all_orgs


def save_json(orgs: list):
    """Save organizations to JSON."""
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(orgs, f, indent=2, ensure_ascii=False)
    print(f"  Saved to: {OUTPUT_JSON}")


def ingest_to_database(orgs: list):
    """Ingest organizations to database."""
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
        for org in orgs:
            name = org.get('name', '').strip()
            state = org.get('state', '').strip()

            if not name:
                continue

            # Check if exists
            existing = db.query(Shelter).filter(
                Shelter.name == name,
                Shelter.state == state
            ).first()

            if existing:
                # Update with new data (only fill empty fields)
                if org.get('email') and not existing.email:
                    existing.email = org['email']
                if org.get('phone') and not existing.phone:
                    existing.phone = org['phone']
                if org.get('website') and not existing.website:
                    existing.website = org['website']
                if org.get('address') and not existing.address:
                    existing.address = org['address']
                if org.get('city') and not existing.city:
                    existing.city = org['city']
                if org.get('zip_code') and not existing.zip_code:
                    existing.zip_code = org['zip_code']
                if org.get('facebook_url') and not existing.facebook_url:
                    existing.facebook_url = org['facebook_url']
                if org.get('description') and not existing.description:
                    existing.description = org['description']
                if org.get('external_id') and not existing.external_id:
                    existing.external_id = org['external_id']
                existing.last_verified_at = datetime.now(timezone.utc)
                updated += 1
            else:
                # Create new
                new_shelter = Shelter(
                    name=name,
                    city=org.get('city', ''),
                    state=state,
                    zip_code=org.get('zip_code', ''),
                    address=org.get('address', ''),
                    email=org.get('email', ''),
                    phone=org.get('phone', ''),
                    website=org.get('website', ''),
                    description=org.get('description', ''),
                    facebook_url=org.get('facebook_url', ''),
                    external_id=org.get('external_id', ''),
                    source='rescuegroups',
                    org_type=org.get('org_type', 'rescue'),
                    last_verified_at=datetime.now(timezone.utc)
                )
                db.add(new_shelter)
                created += 1

            if (created + updated) % 500 == 0:
                db.commit()
                print(f"    Processed {created + updated}...")

        db.commit()
        print(f"\n  Created: {created}")
        print(f"  Updated: {updated}")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

    return created, updated


def main():
    parser = argparse.ArgumentParser(description="Ingest RescueGroups organizations")
    parser.add_argument('--db', action='store_true', help="Save to database")
    args = parser.parse_args()

    orgs = fetch_all_orgs()

    if orgs:
        save_json(orgs)

        if args.db:
            ingest_to_database(orgs)

    print("\nDone!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted.")
        sys.exit(0)

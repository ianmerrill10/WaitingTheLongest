#!/usr/bin/env python3
"""
===============================================================================
IRS Exempt Organizations Business Master File Ingester
===============================================================================
Downloads the official IRS EO BMF data containing ALL registered nonprofits.
This is the SAME source CauseIQ uses for their 28,259 animal shelters!

CSV Downloads (updated monthly):
- https://www.irs.gov/pub/irs-soi/eo1.csv (Region 1: Northeast)
- https://www.irs.gov/pub/irs-soi/eo2.csv (Region 2: Mid-Atlantic/Great Lakes)
- https://www.irs.gov/pub/irs-soi/eo3.csv (Region 3: Gulf/Pacific)
- https://www.irs.gov/pub/irs-soi/eo4.csv (Region 4: International/Other)

NTEE Codes for Animal Organizations:
- D01-D99: Animal-Related organizations
- D20: Animal Protection and Welfare (main target)
- D30: Wildlife Preservation
- D40: Veterinary Services
- D50: Zoos and Aquariums
- D60: Animal Services N.E.C.

Output:
- Database of all animal shelters/rescues
- Master email list for outreach
- Master phone list
- Master address list
- Master socials list
===============================================================================
"""

import os
import sys
import csv
import io
import re
import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import requests
from tqdm import tqdm

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# IRS EO BMF CSV URLs
IRS_EO_BMF_URLS = {
    "region1": "https://www.irs.gov/pub/irs-soi/eo1.csv",  # Northeast
    "region2": "https://www.irs.gov/pub/irs-soi/eo2.csv",  # Mid-Atlantic/Great Lakes
    "region3": "https://www.irs.gov/pub/irs-soi/eo3.csv",  # Gulf/Pacific
    "region4": "https://www.irs.gov/pub/irs-soi/eo4.csv",  # International/Other
}

# Region state mappings
REGION_STATES = {
    "region1": ["CT", "ME", "MA", "NH", "NJ", "NY", "RI", "VT"],
    "region2": ["DE", "DC", "IL", "IN", "IA", "KY", "MD", "MI", "MN", "NE",
                "NC", "ND", "OH", "PA", "SC", "SD", "VA", "WV", "WI"],
    "region3": ["AL", "AK", "AR", "AZ", "CA", "CO", "FL", "GA", "HI", "ID",
                "KS", "LA", "MS", "MO", "MT", "NV", "NM", "OK", "OR", "TX",
                "TN", "UT", "WA", "WY"],
    "region4": ["International", "Other"],
}

# Animal-related NTEE codes (D category)
ANIMAL_NTEE_CODES = [
    "D", "D01", "D02", "D03", "D05", "D11", "D12",
    "D20", "D21", "D22", "D23", "D24", "D25", "D26", "D27", "D28", "D29",
    "D30", "D31", "D32", "D33", "D34",
    "D40", "D41", "D42", "D43", "D44", "D45", "D46", "D47", "D48", "D49",
    "D50", "D51", "D52", "D53", "D54", "D55", "D56", "D57", "D58", "D59",
    "D60", "D61", "D62", "D63", "D64", "D65", "D66", "D67", "D68", "D69",
    "D70", "D71", "D72", "D73", "D74", "D75", "D76", "D77", "D78", "D79",
    "D80", "D81", "D82", "D83", "D84", "D85", "D86", "D87", "D88", "D89",
    "D90", "D91", "D92", "D93", "D94", "D95", "D96", "D97", "D98", "D99",
]


@dataclass
class AnimalOrg:
    """Animal organization data from IRS EO BMF."""
    ein: str
    name: str
    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    ntee_code: Optional[str] = None
    subsection: Optional[str] = None
    classification: Optional[str] = None
    ruling_date: Optional[str] = None
    deductibility: Optional[str] = None
    foundation_type: Optional[str] = None
    activity: Optional[str] = None
    organization_type: Optional[str] = None
    status: Optional[str] = None
    income_amount: Optional[int] = None
    revenue_amount: Optional[int] = None
    asset_amount: Optional[int] = None
    # Enriched data (from web scraping later)
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    facebook_url: Optional[str] = None
    instagram_url: Optional[str] = None
    twitter_url: Optional[str] = None


def download_csv(url: str, region: str) -> str:
    """
    Download a CSV file from IRS.

    Args:
        url: URL to download
        region: Region identifier

    Returns:
        CSV content as string
    """
    logger.info(f"Downloading {region} from {url}...")

    try:
        response = requests.get(url, timeout=120, stream=True)
        response.raise_for_status()

        # Get total size for progress bar
        total_size = int(response.headers.get('content-length', 0))

        content = []
        with tqdm(total=total_size, unit='B', unit_scale=True, desc=f"Downloading {region}") as pbar:
            for chunk in response.iter_content(chunk_size=8192):
                content.append(chunk)
                pbar.update(len(chunk))

        return b''.join(content).decode('utf-8', errors='ignore')

    except Exception as e:
        logger.error(f"Error downloading {region}: {e}")
        return ""


def parse_irs_csv(content: str) -> List[AnimalOrg]:
    """
    Parse IRS EO BMF CSV and extract animal organizations.

    Args:
        content: CSV content as string

    Returns:
        List of AnimalOrg objects
    """
    orgs = []

    try:
        reader = csv.DictReader(io.StringIO(content))

        for row in reader:
            ntee = row.get('NTEE_CD', '') or ''

            # Check if this is an animal-related org (D category)
            if not ntee.upper().startswith('D'):
                continue

            org = AnimalOrg(
                ein=row.get('EIN', ''),
                name=row.get('NAME', ''),
                street=row.get('STREET', ''),
                city=row.get('CITY', ''),
                state=row.get('STATE', ''),
                zip_code=row.get('ZIP', ''),
                ntee_code=ntee,
                subsection=row.get('SUBSECTION', ''),
                classification=row.get('CLASSIFICATION', ''),
                ruling_date=row.get('RULING', ''),
                deductibility=row.get('DEDUCTIBILITY', ''),
                foundation_type=row.get('FOUNDATION', ''),
                activity=row.get('ACTIVITY', ''),
                organization_type=row.get('ORGANIZATION', ''),
                status=row.get('STATUS', ''),
                income_amount=int(row.get('INCOME_AMT', 0) or 0),
                revenue_amount=int(row.get('REVENUE_AMT', 0) or 0),
                asset_amount=int(row.get('ASSET_AMT', 0) or 0),
            )
            orgs.append(org)

    except Exception as e:
        logger.error(f"Error parsing CSV: {e}")

    return orgs


def download_all_regions() -> List[AnimalOrg]:
    """
    Download and parse all IRS EO BMF regions.

    Returns:
        Combined list of all animal organizations
    """
    all_orgs = []

    for region, url in IRS_EO_BMF_URLS.items():
        content = download_csv(url, region)
        if content:
            orgs = parse_irs_csv(content)
            all_orgs.extend(orgs)
            logger.info(f"{region}: Found {len(orgs)} animal organizations")

    logger.info(f"Total animal organizations found: {len(all_orgs)}")
    return all_orgs


def save_to_database(orgs: List[AnimalOrg]) -> int:
    """
    Save organizations to database.

    Args:
        orgs: List of AnimalOrg objects

    Returns:
        Number of new records saved
    """
    try:
        from app.database import SessionLocal
        from app.models import Shelter

        db = SessionLocal()
        saved_count = 0
        updated_count = 0

        for org in tqdm(orgs, desc="Saving to database"):
            # Check if exists by EIN
            existing = db.query(Shelter).filter(
                Shelter.external_id == f"ein:{org.ein}"
            ).first()

            if existing:
                # Update with any new data
                if org.street and not existing.address:
                    existing.address = org.street
                if org.city and not existing.city:
                    existing.city = org.city
                existing.updated_at = datetime.utcnow()
                updated_count += 1
            else:
                # Check by name and state
                existing = db.query(Shelter).filter(
                    Shelter.name == org.name,
                    Shelter.state == org.state
                ).first()

                if existing:
                    existing.external_id = f"ein:{org.ein}"
                    existing.updated_at = datetime.utcnow()
                    updated_count += 1
                else:
                    # Create new
                    shelter = Shelter(
                        name=org.name,
                        city=org.city,
                        state=org.state,
                        address=org.street,
                        zip_code=org.zip_code,
                        source="irs_eo_bmf",
                        external_id=f"ein:{org.ein}",
                        org_type=get_org_type(org.ntee_code)
                    )
                    db.add(shelter)
                    saved_count += 1

            # Commit in batches
            if (saved_count + updated_count) % 500 == 0:
                db.commit()

        db.commit()
        db.close()

        logger.info(f"Saved {saved_count} new, updated {updated_count} existing")
        return saved_count

    except Exception as e:
        logger.error(f"Database error: {e}")
        return 0


def get_org_type(ntee_code: str) -> str:
    """Map NTEE code to organization type."""
    if not ntee_code:
        return "nonprofit"

    code = ntee_code.upper()
    if code.startswith("D2"):
        return "shelter"
    elif code.startswith("D3"):
        return "wildlife"
    elif code.startswith("D4"):
        return "veterinary"
    elif code.startswith("D5"):
        return "zoo"
    elif code.startswith("D6"):
        return "rescue"
    else:
        return "animal_org"


def export_master_lists(orgs: List[AnimalOrg], output_dir: str) -> Dict[str, int]:
    """
    Export master contact lists for outreach.

    Args:
        orgs: List of AnimalOrg objects
        output_dir: Directory to save files

    Returns:
        Dict with counts per list type
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Master address list
    addresses = []
    for org in orgs:
        if org.street and org.city and org.state:
            addresses.append({
                "name": org.name,
                "ein": org.ein,
                "street": org.street,
                "city": org.city,
                "state": org.state,
                "zip": org.zip_code,
            })

    with open(os.path.join(output_dir, "master_addresses.json"), "w") as f:
        json.dump(addresses, f, indent=2)

    # Export as CSV too
    with open(os.path.join(output_dir, "master_addresses.csv"), "w", newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["name", "ein", "street", "city", "state", "zip"])
        writer.writeheader()
        writer.writerows(addresses)

    # State-by-state breakdown
    by_state = {}
    for org in orgs:
        state = org.state or "Unknown"
        if state not in by_state:
            by_state[state] = []
        by_state[state].append(asdict(org))

    with open(os.path.join(output_dir, "orgs_by_state.json"), "w") as f:
        json.dump({
            "total_orgs": len(orgs),
            "state_counts": {k: len(v) for k, v in sorted(by_state.items())},
            "by_state": by_state
        }, f, indent=2)

    # Summary stats
    stats = {
        "total_organizations": len(orgs),
        "with_addresses": len(addresses),
        "states_covered": len(by_state),
        "by_state_count": {k: len(v) for k, v in sorted(by_state.items(), key=lambda x: -len(x[1]))},
        "top_states": dict(sorted(by_state.items(), key=lambda x: -len(x[1]))[:10]),
        "generated_at": datetime.utcnow().isoformat(),
    }

    with open(os.path.join(output_dir, "summary_stats.json"), "w") as f:
        json.dump(stats, f, indent=2)

    logger.info(f"Exported {len(addresses)} addresses to {output_dir}")
    logger.info(f"States covered: {len(by_state)}")

    return {
        "addresses": len(addresses),
        "states": len(by_state),
        "total_orgs": len(orgs),
    }


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Ingest IRS EO BMF animal organizations')
    parser.add_argument('--download', action='store_true', help='Download fresh IRS data')
    parser.add_argument('--db', action='store_true', help='Save to database')
    parser.add_argument('--export', type=str, help='Export master lists to directory')
    parser.add_argument('--region', type=str, choices=['1', '2', '3', '4', 'all'], default='all',
                        help='Region to download (1-4 or all)')
    parser.add_argument('--state', type=str, help='Filter by specific state (e.g., MA)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    print("=" * 70)
    print("IRS Exempt Organizations Business Master File - Animal Org Ingester")
    print("=" * 70)
    print("Source: https://www.irs.gov/charities-non-profits/exempt-organizations-business-master-file-extract-eo-bmf")
    print("Same data source as CauseIQ's 28,259 animal shelters!")
    print()

    if args.download or not os.path.exists("data/irs_animal_orgs.json"):
        print("Downloading IRS EO BMF data...")
        print("This may take a few minutes (files are ~100MB each)")
        print()

        if args.region == 'all':
            orgs = download_all_regions()
        else:
            region_key = f"region{args.region}"
            url = IRS_EO_BMF_URLS.get(region_key)
            if url:
                content = download_csv(url, region_key)
                orgs = parse_irs_csv(content) if content else []
            else:
                orgs = []

        # Cache the data
        Path("data").mkdir(exist_ok=True)
        with open("data/irs_animal_orgs.json", "w") as f:
            json.dump([asdict(o) for o in orgs], f)

        print(f"\nCached {len(orgs)} animal organizations to data/irs_animal_orgs.json")

    else:
        print("Loading cached data...")
        with open("data/irs_animal_orgs.json", "r") as f:
            data = json.load(f)
            orgs = [AnimalOrg(**d) for d in data]
        print(f"Loaded {len(orgs)} organizations from cache")

    # Filter by state if specified
    if args.state:
        state = args.state.upper()
        orgs = [o for o in orgs if o.state == state]
        print(f"Filtered to {len(orgs)} organizations in {state}")

    # Display summary
    print(f"\n{'=' * 70}")
    print(f"TOTAL ANIMAL ORGANIZATIONS: {len(orgs):,}")
    print(f"{'=' * 70}")

    # State breakdown
    state_counts = {}
    for org in orgs:
        state = org.state or "Unknown"
        state_counts[state] = state_counts.get(state, 0) + 1

    print("\nTop 15 states by animal org count:")
    for i, (state, count) in enumerate(sorted(state_counts.items(), key=lambda x: -x[1])[:15], 1):
        print(f"  {i:2}. {state}: {count:,}")

    # Sample orgs
    print("\nSample organizations:")
    for org in orgs[:10]:
        print(f"  - {org.name}")
        if org.city and org.state:
            print(f"    {org.city}, {org.state} {org.zip_code or ''}")
        print(f"    EIN: {org.ein} | NTEE: {org.ntee_code}")

    if args.export:
        print(f"\nExporting master lists to {args.export}...")
        counts = export_master_lists(orgs, args.export)
        print(f"Exported {counts['addresses']:,} addresses")
        print(f"Covering {counts['states']} states")

    if args.db:
        print("\nSaving to database...")
        saved = save_to_database(orgs)
        print(f"Saved {saved:,} new organizations")

    print("\nDone!")
    print(f"\nNext steps:")
    print("  1. Run web enrichment agent to find emails/phones/websites")
    print("  2. Use Email Campaign Agent to prepare outreach")
    print("  3. Launch partnership invitations to shelters")


if __name__ == "__main__":
    main()

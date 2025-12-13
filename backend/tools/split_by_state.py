#!/usr/bin/env python3
"""
===============================================================================
Split Enriched Orgs by State
===============================================================================
Creates individual CSV files for each state from the final enriched dataset.

Output: backend/data/by_state/
  - shelters_AL.csv
  - shelters_AK.csv
  - shelters_AZ.csv
  - ... etc for all 50 states + DC

Usage:
    python split_by_state.py

===============================================================================
"""
import csv
import json
import os
import sys
from collections import defaultdict
from typing import Dict, List, Any

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
OUTPUT_DIR = os.path.join(DATA_DIR, 'by_state')

# Input files in order of preference (most enriched first)
INPUT_FILES = [
    os.path.join(DATA_DIR, "bf_network_website_enriched.json"),
    os.path.join(DATA_DIR, "bf_network_enriched.json"),
    os.path.join(DATA_DIR, "bf_network_orgs.json"),
]

# All US state codes
US_STATES = [
    'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'DC', 'FL',
    'GA', 'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME',
    'MD', 'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH',
    'NJ', 'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI',
    'SC', 'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI',
    'WY'
]


def load_orgs() -> List[Dict[str, Any]]:
    """Load from the most enriched available file."""
    for path in INPUT_FILES:
        if os.path.exists(path):
            print(f"Loading from: {path}")
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
    print("ERROR: No input file found. Run the scraper first.")
    return []


def get_best_value(org: Dict, *fields) -> str:
    """Get the first non-empty value from multiple possible fields."""
    for field in fields:
        val = org.get(field, '')
        if val and str(val).strip():
            return str(val).strip()
    return ''


def flatten_org(org: Dict) -> Dict:
    """Flatten org to a consistent format, preferring site_ fields."""
    return {
        'name': org.get('name', ''),
        'city': org.get('city', ''),
        'state': org.get('state', ''),
        'description': org.get('description', ''),
        'profile_url': org.get('profile_url', ''),
        'website': get_best_value(org, 'website_url', 'website', 'site_website_url'),
        'email': get_best_value(org, 'site_email', 'email'),
        'phone': get_best_value(org, 'site_phone', 'phone'),
        'address': get_best_value(org, 'site_address', 'address'),
        'facebook': get_best_value(org, 'site_facebook_url', 'facebook_url'),
        'instagram': get_best_value(org, 'site_instagram_url', 'instagram_url'),
        'twitter': get_best_value(org, 'site_twitter_url', 'twitter_url'),
        'youtube': get_best_value(org, 'site_youtube_url', 'youtube_url'),
        'tiktok': get_best_value(org, 'site_tiktok_url', 'tiktok_url'),
        'linkedin': get_best_value(org, 'site_linkedin_url', 'linkedin_url'),
    }


def main():
    print("=== Splitting Orgs by State ===")

    orgs = load_orgs()
    if not orgs:
        return

    print(f"Loaded {len(orgs)} orgs")

    # Group by state
    by_state: Dict[str, List[Dict]] = defaultdict(list)

    for org in orgs:
        state = org.get('state', '').strip().upper()
        if state and len(state) == 2:
            by_state[state].append(flatten_org(org))

    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Write per-state CSVs
    fieldnames = [
        'name', 'city', 'state', 'description', 'profile_url', 'website',
        'email', 'phone', 'address',
        'facebook', 'instagram', 'twitter', 'youtube', 'tiktok', 'linkedin'
    ]

    total_written = 0
    states_with_data = 0

    for state in sorted(US_STATES):
        state_orgs = by_state.get(state, [])

        if not state_orgs:
            continue

        states_with_data += 1
        output_path = os.path.join(OUTPUT_DIR, f"shelters_{state}.csv")

        with open(output_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for org in sorted(state_orgs, key=lambda x: x.get('name', '')):
                writer.writerow(org)

        total_written += len(state_orgs)
        print(f"  {state}: {len(state_orgs)} orgs -> {output_path}")

    # Write summary
    print(f"\n=== Summary ===")
    print(f"Total orgs written: {total_written}")
    print(f"States with data: {states_with_data}")
    print(f"Output directory: {OUTPUT_DIR}")

    # Also write a combined "all states" CSV
    all_path = os.path.join(OUTPUT_DIR, "shelters_ALL.csv")
    all_orgs = []
    for state in US_STATES:
        all_orgs.extend(by_state.get(state, []))

    with open(all_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for org in sorted(all_orgs, key=lambda x: (x.get('state', ''), x.get('name', ''))):
            writer.writerow(org)

    print(f"\n  ALL: {len(all_orgs)} orgs -> {all_path}")

    # Print top states by count
    print(f"\n=== Top 10 States by Org Count ===")
    state_counts = [(state, len(by_state[state])) for state in by_state if by_state[state]]
    state_counts.sort(key=lambda x: -x[1])

    for state, count in state_counts[:10]:
        print(f"  {state}: {count}")


if __name__ == "__main__":
    main()

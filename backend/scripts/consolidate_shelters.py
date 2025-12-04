#!/usr/bin/env python3
"""
Consolidate all pet shelters from 50 state JSON files into a master database.
"""

import json
import os
from datetime import datetime
from pathlib import Path

def main():
    # Paths
    collected_shelters_dir = Path(__file__).parent.parent / "data" / "collected_shelters"
    output_dir = Path(__file__).parent.parent / "data"

    # Collect all shelters
    all_shelters = []
    state_summary = {}
    organization_types = {}

    # Process each state file
    state_files = sorted(collected_shelters_dir.glob("*_shelters.json"))

    print(f"Found {len(state_files)} state files to process\n")
    print("=" * 60)
    print("SHELTER COUNT BY STATE")
    print("=" * 60)

    for state_file in state_files:
        with open(state_file, 'r') as f:
            data = json.load(f)

        state_code = data.get('state', 'Unknown')
        state_name = data.get('state_full', 'Unknown')
        shelters = data.get('shelters', [])
        count = len(shelters)

        # Add state info to each shelter and add to master list
        for shelter in shelters:
            shelter['source_state'] = state_code
            shelter['source_state_full'] = state_name
            all_shelters.append(shelter)

            # Track organization types
            org_type = shelter.get('type', 'unknown')
            organization_types[org_type] = organization_types.get(org_type, 0) + 1

        state_summary[state_code] = {
            'name': state_name,
            'count': count
        }

        print(f"{state_name:25} ({state_code}): {count:4} shelters")

    # Sort by count descending
    sorted_states = sorted(state_summary.items(), key=lambda x: x[1]['count'], reverse=True)

    print("\n" + "=" * 60)
    print("SUMMARY STATISTICS")
    print("=" * 60)
    print(f"\nTotal States Processed: {len(state_summary)}")
    print(f"Total Shelters/Agencies: {len(all_shelters)}")

    print("\n--- Top 10 States by Shelter Count ---")
    for i, (code, info) in enumerate(sorted_states[:10], 1):
        print(f"{i:2}. {info['name']:25} ({code}): {info['count']:4}")

    print("\n--- Bottom 5 States by Shelter Count ---")
    for code, info in sorted_states[-5:]:
        print(f"    {info['name']:25} ({code}): {info['count']:4}")

    print("\n--- Organization Types ---")
    sorted_types = sorted(organization_types.items(), key=lambda x: x[1], reverse=True)
    for org_type, count in sorted_types:
        print(f"    {org_type:30}: {count:4}")

    # Create master database
    master_database = {
        "metadata": {
            "title": "US Animal Shelters Master Database",
            "description": "Consolidated database of all pet shelters, rescue organizations, humane societies, and animal agencies across all 50 US states",
            "created_at": datetime.now().isoformat(),
            "total_organizations": len(all_shelters),
            "total_states": len(state_summary),
            "organization_type_breakdown": organization_types,
            "state_breakdown": {code: info['count'] for code, info in state_summary.items()}
        },
        "organizations": all_shelters
    }

    # Write master database
    master_file = output_dir / "master_shelter_database.json"
    with open(master_file, 'w') as f:
        json.dump(master_database, f, indent=2)

    print(f"\n" + "=" * 60)
    print("OUTPUT FILES")
    print("=" * 60)
    print(f"Master database written to: {master_file}")
    print(f"File size: {master_file.stat().st_size / 1024:.1f} KB")

    # Return totals for verification
    return len(all_shelters), len(state_summary)


if __name__ == "__main__":
    total_shelters, total_states = main()
    print(f"\n{'='*60}")
    print(f"GRAND TOTAL: {total_shelters} shelters/agencies across {total_states} states")
    print("=" * 60)

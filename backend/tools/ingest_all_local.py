#!/usr/bin/env python3
"""
===============================================================================
Master Ingestor - Run All Local Data File Ingestors
===============================================================================
Ingests all existing data files into the Shelter database:
  - NJ Shelters (~140 orgs)
  - RI Shelters
  - National Registry Report (~200+ orgs from MA, NY, PA, TX, FL, VA, OH, CA)
  - AKC Rescue Network (~450+ breed-specific rescues)

Usage:
    python ingest_all_local.py

===============================================================================
"""
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def run_all_ingestors():
    print("=" * 60)
    print("MASTER INGESTOR - Local Data Files")
    print("=" * 60)
    print(f"Started: {datetime.now().isoformat()}")
    print()

    results = {}

    # 1. NJ Shelters
    print("-" * 60)
    print("1. Ingesting NJ Shelters...")
    print("-" * 60)
    try:
        from tools.ingest_nj_shelters import ingest_nj_shelters
        nj_file = os.path.join(os.path.dirname(__file__), '../data/nj_shelters.txt')
        if os.path.exists(nj_file):
            ingest_nj_shelters(nj_file)
            results['NJ Shelters'] = 'SUCCESS'
        else:
            print(f"  File not found: {nj_file}")
            results['NJ Shelters'] = 'FILE NOT FOUND'
    except Exception as e:
        print(f"  ERROR: {e}")
        results['NJ Shelters'] = f'ERROR: {e}'

    # 2. RI Shelters
    print()
    print("-" * 60)
    print("2. Ingesting RI Shelters...")
    print("-" * 60)
    try:
        from tools.ingest_ri_shelters import ingest_ri_shelters
        ri_file = os.path.join(os.path.dirname(__file__), '../data/ri_animal_welfare_report.txt')
        if os.path.exists(ri_file):
            ingest_ri_shelters(ri_file)
            results['RI Shelters'] = 'SUCCESS'
        else:
            print(f"  File not found: {ri_file}")
            results['RI Shelters'] = 'FILE NOT FOUND'
    except Exception as e:
        print(f"  ERROR: {e}")
        results['RI Shelters'] = f'ERROR: {e}'

    # 3. National Registry Report
    print()
    print("-" * 60)
    print("3. Ingesting National Registry Report...")
    print("-" * 60)
    try:
        from tools.ingest_registry_report import ingest_report
        report_file = os.path.join(os.path.dirname(__file__), '../data/national_registry_report.txt')
        if os.path.exists(report_file):
            ingest_report(report_file)
            results['National Registry'] = 'SUCCESS'
        else:
            print(f"  File not found: {report_file}")
            results['National Registry'] = 'FILE NOT FOUND'
    except Exception as e:
        print(f"  ERROR: {e}")
        results['National Registry'] = f'ERROR: {e}'

    # 4. AKC Rescue Network
    print()
    print("-" * 60)
    print("4. Ingesting AKC Rescue Network...")
    print("-" * 60)
    try:
        from tools.ingest_akc_network import parse_akc_file, ingest_data
        akc_file = os.path.join(os.path.dirname(__file__), '../data/akc_rescue_network.txt')
        if os.path.exists(akc_file):
            data = parse_akc_file(akc_file)
            print(f"  Parsed {len(data)} records")
            ingest_data(data)
            results['AKC Network'] = 'SUCCESS'
        else:
            print(f"  File not found: {akc_file}")
            results['AKC Network'] = 'FILE NOT FOUND'
    except Exception as e:
        print(f"  ERROR: {e}")
        results['AKC Network'] = f'ERROR: {e}'

    # Summary
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for source, status in results.items():
        status_icon = "✓" if status == 'SUCCESS' else "✗"
        print(f"  {status_icon} {source}: {status}")

    print()
    print(f"Completed: {datetime.now().isoformat()}")
    print("=" * 60)

    # Show total count
    try:
        from app.database import SessionLocal
        from app.models import Shelter
        db = SessionLocal()
        total = db.query(Shelter).count()
        db.close()
        print(f"\nTotal shelters in database: {total}")
    except Exception as e:
        print(f"\nCouldn't get total count: {e}")


if __name__ == "__main__":
    run_all_ingestors()

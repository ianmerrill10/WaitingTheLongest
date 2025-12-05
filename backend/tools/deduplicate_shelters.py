#!/usr/bin/env python3
"""
===============================================================================
Shelter Deduplication Utility
===============================================================================
Finds and merges duplicate shelter records in the database.

Duplicates are identified by:
  - Similar names (fuzzy matching)
  - Same city + state
  - Same phone number
  - Same email address

Usage:
    python deduplicate_shelters.py          # Show duplicates (dry run)
    python deduplicate_shelters.py --merge  # Actually merge duplicates

===============================================================================
"""
import sys
import os
import re
import argparse
from datetime import datetime
from collections import defaultdict
from typing import List, Dict, Tuple, Set

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def normalize_name(name: str) -> str:
    """Normalize organization name for comparison."""
    if not name:
        return ''

    name = name.lower().strip()

    # Remove common suffixes/prefixes
    removals = [
        r'\binc\.?\b', r'\bllc\.?\b', r'\bcorp\.?\b',
        r'\brescue\b', r'\bshelter\b', r'\bhumane\s+society\b',
        r'\bspca\b', r'\banimal\b', r'\bpet\b', r'\bdog\b', r'\bcat\b',
        r'\bof\b', r'\bthe\b', r'\band\b', r'\b&\b',
    ]

    for pattern in removals:
        name = re.sub(pattern, '', name, flags=re.IGNORECASE)

    # Remove punctuation and extra spaces
    name = re.sub(r'[^\w\s]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()

    return name


def normalize_phone(phone: str) -> str:
    """Normalize phone number to just digits."""
    if not phone:
        return ''
    return re.sub(r'\D', '', phone)


def similarity_score(s1: str, s2: str) -> float:
    """Calculate simple similarity between two strings (0-1)."""
    if not s1 or not s2:
        return 0.0

    s1 = s1.lower()
    s2 = s2.lower()

    if s1 == s2:
        return 1.0

    # Check if one contains the other
    if s1 in s2 or s2 in s1:
        return 0.9

    # Count matching words
    words1 = set(s1.split())
    words2 = set(s2.split())

    if not words1 or not words2:
        return 0.0

    common = words1 & words2
    total = words1 | words2

    return len(common) / len(total)


def find_duplicates(shelters: List[Dict]) -> List[Tuple[Dict, Dict, str]]:
    """Find potential duplicate pairs."""
    duplicates = []

    # Index by various keys
    by_phone = defaultdict(list)
    by_email = defaultdict(list)
    by_name_state = defaultdict(list)

    for s in shelters:
        # By phone
        phone = normalize_phone(s.get('phone', ''))
        if len(phone) >= 10:
            by_phone[phone].append(s)

        # By email
        email = (s.get('email') or '').lower().strip()
        if email:
            by_email[email].append(s)

        # By normalized name + state
        norm_name = normalize_name(s.get('name', ''))
        state = (s.get('state') or '').upper()
        if norm_name and state:
            by_name_state[(norm_name, state)].append(s)

    # Find duplicates by phone
    for phone, group in by_phone.items():
        if len(group) > 1:
            for i, s1 in enumerate(group):
                for s2 in group[i+1:]:
                    if s1['id'] != s2['id']:
                        duplicates.append((s1, s2, f'same_phone:{phone}'))

    # Find duplicates by email
    for email, group in by_email.items():
        if len(group) > 1:
            for i, s1 in enumerate(group):
                for s2 in group[i+1:]:
                    if s1['id'] != s2['id']:
                        duplicates.append((s1, s2, f'same_email:{email}'))

    # Find duplicates by name + state
    for (name, state), group in by_name_state.items():
        if len(group) > 1:
            for i, s1 in enumerate(group):
                for s2 in group[i+1:]:
                    if s1['id'] != s2['id']:
                        duplicates.append((s1, s2, f'same_name_state:{name}|{state}'))

    # Dedupe the duplicate pairs
    seen = set()
    unique_duplicates = []
    for s1, s2, reason in duplicates:
        pair_key = tuple(sorted([s1['id'], s2['id']]))
        if pair_key not in seen:
            seen.add(pair_key)
            unique_duplicates.append((s1, s2, reason))

    return unique_duplicates


def merge_shelters(primary: Dict, secondary: Dict) -> Dict:
    """Merge two shelter records, keeping the best data from each."""
    merged = dict(primary)

    # Fields to merge (take secondary if primary is empty)
    fields = [
        'phone', 'email', 'website', 'address', 'city',
        'description', 'facebook_url', 'instagram_url', 'twitter_url', 'tiktok_url'
    ]

    for field in fields:
        if not merged.get(field) and secondary.get(field):
            merged[field] = secondary[field]

    # Prefer longer description
    if secondary.get('description') and len(secondary.get('description', '')) > len(merged.get('description', '')):
        merged['description'] = secondary['description']

    return merged


def run_deduplication(dry_run: bool = True):
    """Main deduplication routine."""
    try:
        from app.database import SessionLocal, init_db
        from app.models import Shelter
    except ImportError as e:
        print(f"ERROR: Could not import database modules: {e}")
        return

    print("=" * 60)
    print("SHELTER DEDUPLICATION")
    print("=" * 60)
    print(f"Mode: {'DRY RUN' if dry_run else 'MERGE'}")
    print()

    init_db()
    db = SessionLocal()

    try:
        # Load all shelters
        shelters = db.query(Shelter).all()
        print(f"Total shelters in database: {len(shelters)}")

        # Convert to dicts for easier handling
        shelter_dicts = []
        for s in shelters:
            shelter_dicts.append({
                'id': s.id,
                'name': s.name,
                'city': s.city,
                'state': s.state,
                'phone': s.phone,
                'email': s.email,
                'website': s.website,
                'address': s.address,
                'description': s.description,
                'source': s.source,
                'facebook_url': s.facebook_url,
                'instagram_url': s.instagram_url,
                'twitter_url': s.twitter_url,
                'tiktok_url': s.tiktok_url,
            })

        # Find duplicates
        duplicates = find_duplicates(shelter_dicts)
        print(f"Found {len(duplicates)} potential duplicate pairs")
        print()

        if not duplicates:
            print("No duplicates found!")
            return

        # Process duplicates
        merged_count = 0
        deleted_ids = set()

        for i, (s1, s2, reason) in enumerate(duplicates[:50]):  # Limit to first 50
            if s1['id'] in deleted_ids or s2['id'] in deleted_ids:
                continue

            print(f"Duplicate #{i+1} ({reason}):")
            print(f"  [A] ID {s1['id']}: {s1['name']} ({s1['city']}, {s1['state']}) - {s1['source']}")
            print(f"      Phone: {s1['phone']} | Email: {s1['email']}")
            print(f"  [B] ID {s2['id']}: {s2['name']} ({s2['city']}, {s2['state']}) - {s2['source']}")
            print(f"      Phone: {s2['phone']} | Email: {s2['email']}")

            if not dry_run:
                # Keep the one with more data, merge from the other
                score1 = sum(1 for v in s1.values() if v)
                score2 = sum(1 for v in s2.values() if v)

                if score1 >= score2:
                    primary_id, secondary_id = s1['id'], s2['id']
                    merged = merge_shelters(s1, s2)
                else:
                    primary_id, secondary_id = s2['id'], s1['id']
                    merged = merge_shelters(s2, s1)

                # Update primary record
                primary = db.query(Shelter).filter(Shelter.id == primary_id).first()
                if primary:
                    for field in ['phone', 'email', 'website', 'address', 'city', 'description',
                                 'facebook_url', 'instagram_url', 'twitter_url', 'tiktok_url']:
                        if merged.get(field):
                            setattr(primary, field, merged[field])
                    primary.last_verified_at = datetime.utcnow()

                # Delete secondary
                db.query(Shelter).filter(Shelter.id == secondary_id).delete()
                deleted_ids.add(secondary_id)
                merged_count += 1

                print(f"  -> Merged into ID {primary_id}, deleted ID {secondary_id}")

            print()

        if not dry_run:
            db.commit()
            print(f"\nMerged {merged_count} duplicate pairs")

            # Final count
            final_count = db.query(Shelter).count()
            print(f"Final shelter count: {final_count}")
        else:
            print("\n[DRY RUN] No changes made. Run with --merge to apply changes.")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Deduplicate shelter records")
    parser.add_argument('--merge', action='store_true', help="Actually merge duplicates (default: dry run)")

    args = parser.parse_args()

    run_deduplication(dry_run=not args.merge)


if __name__ == "__main__":
    main()

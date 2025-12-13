"""Validate the curated rescue directory payload."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Dict, List

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
	sys.path.insert(0, str(BACKEND_ROOT))

from app.data.rescue_directory import RESCUE_DIRECTORY

REQUIRED_STATE_FIELDS = {"name", "location", "website"}
REQUIRED_NATIONAL_FIELDS = {"name", "region", "website"}
REQUIRED_AKC_FIELDS = {"breed", "contacts"}


@dataclass
class ValidationResult:
	"""Structured validation result."""

	issues: List[str]
	stats: Dict[str, int]

	def as_dict(self) -> Dict[str, object]:
		return {"issues": self.issues, "stats": self.stats}


def _validate_required_fields(entry: Dict[str, object], required: set[str], context: str) -> List[str]:
	issues: List[str] = []
	for field in required:
		if not entry.get(field):
			issues.append(f"{context}: missing required field '{field}'")

	website = entry.get("website")
	if website and not str(website).startswith(("http://", "https://")):
		issues.append(f"{context}: website must start with http:// or https://")

	email = entry.get("email")
	if email and "@" not in str(email):
		issues.append(f"{context}: invalid email '{email}'")

	return issues


def validate_rescue_directory(directory: Dict[str, object]) -> ValidationResult:
	"""Validate the rescue directory structure and payload integrity."""

	issues: List[str] = []

	metadata = directory.get("metadata", {})
	if not metadata.get("version"):
		issues.append("metadata: missing version")
	if not metadata.get("generated_at"):
		issues.append("metadata: missing generated_at timestamp")
	if not metadata.get("sources"):
		issues.append("metadata: missing sources list")

	states = directory.get("states", {})
	for state_slug, entries in states.items():
		for entry in entries:
			issues.extend(
				_validate_required_fields(
					entry,
					REQUIRED_STATE_FIELDS,
					f"states.{state_slug}.{entry.get('name', 'unknown')}"
				)
			)

	national = directory.get("national", {})
	for region_slug, entries in national.items():
		for entry in entries:
			issues.extend(
				_validate_required_fields(
					entry,
					REQUIRED_NATIONAL_FIELDS,
					f"national.{region_slug}.{entry.get('name', 'unknown')}"
				)
			)

	akc_entries = directory.get("akc_network", [])
	for entry in akc_entries:
		issues.extend(
			_validate_required_fields(
				entry,
				REQUIRED_AKC_FIELDS,
				f"akc_network.{entry.get('breed', 'unknown')}"
			)
		)
		contacts = entry.get("contacts") or []
		if not isinstance(contacts, list) or not contacts:
			issues.append(
				f"akc_network.{entry.get('breed', 'unknown')}: contacts must be a non-empty list"
			)

	stats = {
		"state_groups": len(states),
		"state_entries": sum(len(entries) for entries in states.values()),
		"network_regions": len(national),
		"network_entries": sum(len(entries) for entries in national.values()),
		"akc_entries": len(akc_entries),
	}

	return ValidationResult(issues=issues, stats=stats)


def _build_cli() -> argparse.ArgumentParser:
	parser = argparse.ArgumentParser(description="Validate the curated rescue directory dataset")
	parser.add_argument(
		"--dump-json",
		action="store_true",
		help="Print the validation report as JSON for machine consumption."
	)
	parser.add_argument(
		"--fail-on-warn",
		action="store_true",
		help="Exit with status 1 if any validation issues are detected."
	)
	return parser


def main(argv: List[str] | None = None) -> int:
	parser = _build_cli()
	args = parser.parse_args(argv)

	result = validate_rescue_directory(RESCUE_DIRECTORY)

	if args.dump_json:
		print(json.dumps(result.as_dict(), indent=2))
	else:
		print("Rescue Directory Validation Report")
		print("==================================")
		print(f"State groups: {result.stats['state_groups']}")
		print(f"State entries: {result.stats['state_entries']}")
		print(f"Network regions: {result.stats['network_regions']}")
		print(f"Network entries: {result.stats['network_entries']}")
		print(f"AKC entries: {result.stats['akc_entries']}")
		if result.issues:
			print("\nIssues detected:")
			for issue in result.issues:
				print(f" - {issue}")
		else:
			print("\nNo structural issues detected ✅")

	if args.fail_on_warn and result.issues:
		return 1

	return 0


if __name__ == "__main__":
	raise SystemExit(main())

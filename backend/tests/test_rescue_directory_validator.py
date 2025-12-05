"""Tests for the rescue directory validator utility."""

from tools.rescue_directory_validator import validate_rescue_directory


def build_sample_directory():
    return {
        "metadata": {
            "version": "test",
            "generated_at": "2025-12-04T00:00:00Z",
            "sources": ["unit-test"],
        },
        "states": {
            "massachusetts": [
                {
                    "name": "Test Rescue",
                    "location": "Boston, MA",
                    "website": "https://example.org",
                }
            ]
        },
        "national": {
            "northeast_destination": [
                {
                    "name": "North Hub",
                    "region": "Boston",
                    "website": "https://hub.example.org",
                }
            ]
        },
        "akc_network": [
            {
                "breed": "Test Breed",
                "contacts": [
                    {"organization": "Breed Friends", "email": "hello@example.org"}
                ],
            }
        ],
    }


def test_validator_accepts_well_formed_directory():
    directory = build_sample_directory()
    result = validate_rescue_directory(directory)
    assert result.issues == []
    assert result.stats["state_groups"] == 1
    assert result.stats["akc_entries"] == 1


def test_validator_flags_missing_required_fields():
    directory = build_sample_directory()
    directory["states"]["massachusetts"][0]["website"] = "example.org"
    directory["akc_network"][0]["contacts"] = []

    result = validate_rescue_directory(directory)
    assert len(result.issues) >= 2
    assert any("website" in issue for issue in result.issues)
    assert any("contacts" in issue for issue in result.issues)

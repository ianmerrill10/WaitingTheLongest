from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def repo_root() -> Path:
    # backend/tools/testing_ledger.py -> backend/tools -> backend -> repo
    return Path(__file__).resolve().parents[2]


def ledger_json_path() -> Path:
    return repo_root() / "logs" / "FILES_TESTED.json"


def ledger_md_path() -> Path:
    return repo_root() / "logs" / "FILES_TESTED.md"


def testing_log_path() -> Path:
    return repo_root() / "logs" / "TESTING_LOG.md"


def load_ledger() -> dict[str, Any]:
    path = ledger_json_path()
    if not path.exists():
        return {"schema_version": 1, "updated_at": _utc_now_iso(), "files": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def save_ledger(ledger: dict[str, Any]) -> None:
    ledger["updated_at"] = _utc_now_iso()
    path = ledger_json_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def update_file_entry(
    file_path: str,
    *,
    status: str,
    test_command: str,
    notes: str,
    tested_at: Optional[str] = None,
) -> None:
    ledger = load_ledger()
    ledger.setdefault("files", {})
    ledger["files"][file_path] = {
        "last_tested_at": tested_at or _utc_now_iso(),
        "status": status,
        "test_command": test_command,
        "notes": notes,
    }
    save_ledger(ledger)
    render_ledger_markdown()


def render_ledger_markdown() -> None:
    ledger = load_ledger()
    rows = []
    for file_path, meta in sorted(ledger.get("files", {}).items()):
        rows.append(
            (
                file_path,
                meta.get("last_tested_at", ""),
                meta.get("status", ""),
                meta.get("notes", ""),
            )
        )

    md_lines = [
        "# Files Tested Ledger",
        "",
        "Source of truth: `logs/FILES_TESTED.json`",
        "",
        "This file is a human-readable view of what’s been tested recently.",
        "",
        "| File | Last Tested (UTC) | Status | Notes |",
        "|------|-------------------|--------|-------|",
    ]

    for file_path, last_tested_at, status, notes in rows:
        safe_notes = (notes or "").replace("\n", " ").strip()
        md_lines.append(f"| {file_path} | {last_tested_at} | {status} | {safe_notes} |")

    path = ledger_md_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")


def append_testing_log_entry(title: str, bullets: Iterable[str]) -> None:
    path = testing_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    if not path.exists():
        lines.extend(
            [
                "# Testing Log",
                "",
                "This log tracks what has been tested, what passed, what failed, and what was fixed.",
                "",
                "## Entries",
                "",
            ]
        )

    timestamp = _utc_now_iso()
    lines.append(f"\n### {timestamp} — {title}\n")
    for bullet in bullets:
        bullet = bullet.strip()
        if bullet:
            lines.append(f"- {bullet}")

    with path.open("a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

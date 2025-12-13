from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class InventoryItem:
    path: str
    size_bytes: int
    mtime_utc: str


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _project_root() -> Path:
    # backend/tools/file_inventory.py -> project root
    return Path(__file__).resolve().parents[2]


def _logs_dir(root: Path) -> Path:
    d = root / "logs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _should_skip_dir(dir_path: Path, root: Path) -> bool:
    rel = dir_path.relative_to(root).as_posix()

    # Keep this conservative: skip things that are huge/noisy or not meaningful
    # for a source inventory.
    skip_prefixes = {
        ".git",
        ".venv",
        "backend/.venv",
        "backend/__pycache__",
        "backend/.pytest_cache",
        "backend/.mypy_cache",
        "node_modules",
        "aws_exports",
    }

    parts = rel.split("/")
    if parts and parts[0] in {".git", ".venv", "node_modules"}:
        return True

    # Prefix match for nested known dirs
    for p in skip_prefixes:
        if rel == p or rel.startswith(p + "/"):
            return True

    return False


def _iter_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        try:
            if path.is_dir():
                if _should_skip_dir(path, root):
                    # Prevent descending further by skipping contents implicitly
                    continue
                continue

            rel = path.relative_to(root).as_posix()
            if rel.startswith(".git/"):
                continue
            if "__pycache__/" in rel:
                continue
            if rel.endswith(".pyc"):
                continue
            yield path
        except (OSError, ValueError):
            # Best-effort inventory.
            continue


def main() -> int:
    root = _project_root()
    items: list[InventoryItem] = []
    total_bytes = 0

    for f in _iter_files(root):
        try:
            st = f.stat()
            rel = f.relative_to(root).as_posix()
            mtime = datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat().replace("+00:00", "Z")
            items.append(InventoryItem(path=rel, size_bytes=int(st.st_size), mtime_utc=mtime))
            total_bytes += int(st.st_size)
        except OSError:
            continue

    items.sort(key=lambda x: x.path)

    payload = {
        "generated_at_utc": _utc_now_iso(),
        "root": str(root),
        "file_count": len(items),
        "total_bytes": total_bytes,
        "files": [item.__dict__ for item in items],
    }

    logs_dir = _logs_dir(root)
    json_path = logs_dir / "FILES_INVENTORY.json"
    md_path = logs_dir / "FILES_INVENTORY.md"

    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    md_lines: list[str] = []
    md_lines.append("# Project File Inventory")
    md_lines.append("")
    md_lines.append(f"Generated: `{payload['generated_at_utc']}`")
    md_lines.append(f"Files: `{payload['file_count']}`")
    md_lines.append(f"Total bytes: `{payload['total_bytes']}`")
    md_lines.append("")
    md_lines.append("Source of truth: `logs/FILES_INVENTORY.json`")
    md_lines.append("")
    md_lines.append("| Path | Size (bytes) | Modified (UTC) |")
    md_lines.append("|------|-------------:|----------------|")
    for item in items:
        md_lines.append(f"| {item.path} | {item.size_bytes} | {item.mtime_utc} |")

    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")
    print(f"Files: {len(items)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

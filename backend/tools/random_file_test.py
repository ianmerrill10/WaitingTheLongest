from __future__ import annotations

import argparse
import json
import os
import random
import sys
from pathlib import Path
from typing import Iterable, List, Tuple

from tools.testing_ledger import append_testing_log_entry, update_file_entry, repo_root


DEFAULT_EXTS = {
    ".py",
    ".js",
    ".html",
    ".css",
    ".md",
    ".json",
    ".yml",
    ".yaml",
}


def _iter_candidate_files(root: Path, exts: set[str]) -> Iterable[Path]:
    # NOTE: Keep this fast. Avoid Path.rglob() which stats *every* entry and can
    # take a long time on large datasets.

    skip_dir_names = {
        ".git",
        ".venv",
        "venv",
        "__pycache__",
        "node_modules",
        "dist",
        "build",
        "logs",
    }

    # Skip large/generated dataset trees (still allow targeted JSON checks via
    # explicit runs if desired).
    skip_prefixes = [
        ("backend", "data"),
        ("backend", "agents", "state"),
        ("aws", "build"),
    ]

    root_str = str(root)
    for dirpath, dirnames, filenames in os.walk(root_str, topdown=True):
        rel = Path(dirpath).relative_to(root)
        rel_parts = rel.parts

        # Prune by directory name.
        dirnames[:] = [d for d in dirnames if d not in skip_dir_names]

        # Prune by prefix.
        if any(rel_parts[: len(prefix)] == prefix for prefix in skip_prefixes):
            dirnames[:] = []
            continue

        for filename in filenames:
            path = Path(dirpath) / filename
            if path.suffix.lower() not in exts:
                continue
            yield path


def _reservoir_sample(paths: Iterable[Path], *, k: int, rng: random.Random) -> List[Path]:
    """Sample up to k items without materializing the whole iterable."""
    sample: List[Path] = []
    seen = 0
    for item in paths:
        seen += 1
        if len(sample) < k:
            sample.append(item)
            continue
        j = rng.randrange(seen)
        if j < k:
            sample[j] = item
    return sample


def _relative(path: Path) -> str:
    return str(path.relative_to(repo_root())).replace("\\", "/")


def _check_python_syntax(py_file: Path) -> Tuple[bool, str]:
    import py_compile

    try:
        py_compile.compile(str(py_file), doraise=True)
        return True, "py_compile ok"
    except Exception as exc:
        return False, f"py_compile failed: {exc}"


def _check_json(json_file: Path) -> Tuple[bool, str]:
    try:
        json.loads(json_file.read_text(encoding="utf-8"))
        return True, "json parse ok"
    except Exception as exc:
        return False, f"json parse failed: {exc}"


def _check_text_file(text_file: Path) -> Tuple[bool, str]:
    try:
        content = text_file.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            content = text_file.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            return False, f"read failed: {exc}"

    if not content.strip():
        return False, "file is empty/whitespace"
    return True, "basic read ok"


def main() -> int:
    parser = argparse.ArgumentParser(description="Random per-file sanity checks")
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()

    rng = random.Random(args.seed)

    root = repo_root()
    picked = _reservoir_sample(_iter_candidate_files(root, DEFAULT_EXTS), k=args.count, rng=rng)
    if not picked:
        append_testing_log_entry(
            "Random file checks",
            ["No candidate files found"],
        )
        return 1

    passes = 0
    failures = 0

    for file_path in picked:
        rel = _relative(file_path)
        ok = True
        note = ""

        if file_path.suffix.lower() == ".py":
            ok, note = _check_python_syntax(file_path)
        elif file_path.suffix.lower() == ".json":
            ok, note = _check_json(file_path)
        else:
            ok, note = _check_text_file(file_path)

        update_file_entry(
            rel,
            status="pass" if ok else "fail",
            test_command="random_file_test",
            notes=note,
        )

        if ok:
            passes += 1
        else:
            failures += 1

    append_testing_log_entry(
        "Random file checks",
        [
            f"Count: {len(picked)}",
            f"Pass: {passes}",
            f"Fail: {failures}",
            "See logs/FILES_TESTED.md for per-file status.",
        ],
    )

    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""
===============================================================================
Waiting The Longest™ - Release Automation Script
===============================================================================
Purpose: Automate version bumping, changelog generation, and release tagging.

Usage:
    python scripts/release.py patch     # 1.0.0 -> 1.0.1
    python scripts/release.py minor     # 1.0.0 -> 1.1.0
    python scripts/release.py major     # 1.0.0 -> 2.0.0
    python scripts/release.py --dry-run minor  # Preview without changes

Author: Waiting The Longest™ Development Team
===============================================================================
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def get_project_root() -> Path:
    return Path(__file__).parent.parent


def run_git(args: list, check: bool = True) -> str:
    """Run a git command and return output."""
    result = subprocess.run(
        ["git"] + args,
        cwd=get_project_root(),
        capture_output=True,
        text=True,
        check=check
    )
    return result.stdout.strip()


def get_current_version() -> str:
    """Get current version from main.py or package files."""
    main_py = get_project_root() / "backend" / "app" / "main.py"
    
    if main_py.exists():
        content = main_py.read_text()
        match = re.search(r'version="(\d+\.\d+\.\d+)"', content)
        if match:
            return match.group(1)
    
    # Fallback: check git tags
    try:
        tag = run_git(["describe", "--tags", "--abbrev=0"], check=False)
        if tag.startswith("v"):
            return tag[1:]
    except:
        pass
    
    return "1.0.0"


def bump_version(current: str, bump_type: str) -> str:
    """Bump version string based on type."""
    parts = list(map(int, current.split(".")))
    
    if bump_type == "major":
        parts[0] += 1
        parts[1] = 0
        parts[2] = 0
    elif bump_type == "minor":
        parts[1] += 1
        parts[2] = 0
    elif bump_type == "patch":
        parts[2] += 1
    
    return ".".join(map(str, parts))


def update_version_in_files(old_version: str, new_version: str, dry_run: bool = False):
    """Update version in all relevant files."""
    project_root = get_project_root()
    
    files_to_update = [
        ("backend/app/main.py", r'version="[\d\.]+"', f'version="{new_version}"'),
    ]
    
    for file_path, pattern, replacement in files_to_update:
        full_path = project_root / file_path
        if not full_path.exists():
            continue
        
        content = full_path.read_text()
        new_content = re.sub(pattern, replacement, content)
        
        if content != new_content:
            print(f"  📝 {file_path}: {old_version} -> {new_version}")
            if not dry_run:
                full_path.write_text(new_content)


def get_commits_since_tag(tag: str) -> list:
    """Get commit messages since the last tag."""
    try:
        output = run_git(["log", f"{tag}..HEAD", "--oneline", "--no-merges"])
        return output.split("\n") if output else []
    except:
        return []


def generate_changelog_entry(version: str, commits: list) -> str:
    """Generate a changelog entry for the new version."""
    date = datetime.now().strftime("%Y-%m-%d")
    
    # Categorize commits
    features = []
    fixes = []
    other = []
    
    for commit in commits:
        if not commit.strip():
            continue
        # Remove commit hash
        message = " ".join(commit.split()[1:])
        
        if any(kw in message.lower() for kw in ["feat", "add", "new"]):
            features.append(message)
        elif any(kw in message.lower() for kw in ["fix", "bug", "patch"]):
            fixes.append(message)
        else:
            other.append(message)
    
    lines = [f"\n## [{version}] - {date}\n"]
    
    if features:
        lines.append("\n### Added\n")
        for f in features:
            lines.append(f"- {f}\n")
    
    if fixes:
        lines.append("\n### Fixed\n")
        for f in fixes:
            lines.append(f"- {f}\n")
    
    if other:
        lines.append("\n### Changed\n")
        for f in other[:5]:  # Limit to 5 items
            lines.append(f"- {f}\n")
    
    return "".join(lines)


def update_changelog(entry: str, dry_run: bool = False):
    """Add entry to CHANGELOG.md."""
    changelog_path = get_project_root() / "CHANGELOG.md"
    
    if not changelog_path.exists():
        # Create new changelog
        content = f"""# Changelog

All notable changes to Waiting The Longest™ will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
{entry}"""
    else:
        content = changelog_path.read_text()
        # Insert after the header
        insert_pos = content.find("\n## ")
        if insert_pos == -1:
            content += entry
        else:
            content = content[:insert_pos] + entry + content[insert_pos:]
    
    print(f"  📝 CHANGELOG.md updated")
    if not dry_run:
        changelog_path.write_text(content)


def create_git_tag(version: str, dry_run: bool = False):
    """Create and push a git tag."""
    tag = f"v{version}"
    
    if dry_run:
        print(f"  🏷️  Would create tag: {tag}")
        return
    
    # Commit version changes
    run_git(["add", "-A"])
    run_git(["commit", "-m", f"chore: release {version}"])
    
    # Create tag
    run_git(["tag", "-a", tag, "-m", f"Release {version}"])
    
    print(f"  🏷️  Created tag: {tag}")
    print(f"  📤 To push: git push origin main --tags")


def main():
    parser = argparse.ArgumentParser(
        description="Release automation for Waiting The Longest"
    )
    parser.add_argument(
        "bump_type",
        choices=["major", "minor", "patch"],
        help="Type of version bump"
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Preview changes without making them"
    )
    parser.add_argument(
        "--no-tag",
        action="store_true",
        help="Skip git tag creation"
    )
    
    args = parser.parse_args()
    
    print("\n" + "=" * 60)
    print("🚀 Waiting The Longest™ - Release Automation")
    print("=" * 60)
    
    if args.dry_run:
        print("⚠️  DRY RUN - No changes will be made\n")
    
    # Get versions
    current_version = get_current_version()
    new_version = bump_version(current_version, args.bump_type)
    
    print(f"\n📦 Version: {current_version} -> {new_version} ({args.bump_type})\n")
    
    # Update version in files
    print("Updating version in files:")
    update_version_in_files(current_version, new_version, args.dry_run)
    
    # Get commits for changelog
    try:
        last_tag = run_git(["describe", "--tags", "--abbrev=0"], check=False)
    except:
        last_tag = ""
    
    if last_tag:
        commits = get_commits_since_tag(last_tag)
        print(f"\nFound {len(commits)} commits since {last_tag}")
    else:
        commits = []
    
    # Update changelog
    print("\nUpdating changelog:")
    entry = generate_changelog_entry(new_version, commits)
    update_changelog(entry, args.dry_run)
    
    # Create git tag
    if not args.no_tag:
        print("\nCreating git tag:")
        create_git_tag(new_version, args.dry_run)
    
    print("\n" + "=" * 60)
    print(f"✅ Release {new_version} {'would be' if args.dry_run else ''} complete!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()

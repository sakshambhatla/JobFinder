#!/usr/bin/env python3
"""Bump the project version across all canonical locations.

Usage:
    python scripts/bump_version.py --major   # 3.0.0 → 4.0.0
    python scripts/bump_version.py --minor   # 3.0.0 → 3.1.0
    python scripts/bump_version.py --patch   # 3.0.0 → 3.0.1
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent

# Each entry: (file_path, regex_pattern, replacement_template)
# The pattern must capture the version string in group 1.
VERSION_LOCATIONS: list[tuple[Path, str, str]] = [
    (
        ROOT / "pyproject.toml",
        r'^(version\s*=\s*")[^"]+(")',
        r'\g<1>{version}\g<2>',
    ),
    (
        ROOT / "jobfinder" / "__init__.py",
        r'^(__version__\s*=\s*")[^"]+(")',
        r'\g<1>{version}\g<2>',
    ),
    (
        ROOT / "jobfinder" / "api" / "main.py",
        r'(app\s*=\s*FastAPI\([^)]*version\s*=\s*")[^"]+(")',
        r'\g<1>{version}\g<2>',
    ),
    (
        ROOT / "jobfinder" / "utils" / "http.py",
        r'("User-Agent":\s*"JobFinder/)[\d.]+',
        r'\g<1>{version}',
    ),
]


def read_current_version() -> str:
    pyproject = ROOT / "pyproject.toml"
    text = pyproject.read_text()
    m = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if not m:
        sys.exit("ERROR: Could not find version in pyproject.toml")
    return m.group(1)


def bump(version: str, part: str) -> str:
    parts = version.split(".")
    if len(parts) != 3:
        sys.exit(f"ERROR: Unexpected version format: {version!r} (expected X.Y.Z)")
    major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
    if part == "major":
        return f"{major + 1}.0.0"
    elif part == "minor":
        return f"{major}.{minor + 1}.0"
    else:  # patch
        return f"{major}.{minor}.{patch + 1}"


def apply_version(new_version: str) -> None:
    for path, pattern, replacement in VERSION_LOCATIONS:
        if not path.exists():
            print(f"  SKIP (not found): {path.relative_to(ROOT)}")
            continue
        text = path.read_text()
        new_text, count = re.subn(
            pattern,
            replacement.format(version=new_version),
            text,
            flags=re.MULTILINE,
        )
        if count == 0:
            print(f"  WARN (no match):  {path.relative_to(ROOT)}")
        else:
            path.write_text(new_text)
            print(f"  updated:          {path.relative_to(ROOT)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Bump the project version.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--major", action="store_true")
    group.add_argument("--minor", action="store_true")
    group.add_argument("--patch", action="store_true")
    args = parser.parse_args()

    part = "major" if args.major else "minor" if args.minor else "patch"
    old = read_current_version()
    new = bump(old, part)

    print(f"Bumping {part}: {old} → {new}")
    apply_version(new)
    print(f"\nDone. Commit with: git commit -am 'chore: bump version to v{new}'")


if __name__ == "__main__":
    main()

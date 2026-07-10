#!/usr/bin/env python3
"""Normalize domain-list-community data files.

Operations:
1. Remove selected files.
2. Rename geolocation files.
3. Merge category-ads-all into category-ads.
4. Remove include directives from category-companies.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List, Set


REMOVE_FILES: List[str] = [
    "category-ai-chat-!cn",
    "cn",
    "google-gemini",
    "private",
    "speedtest",
    "tld-opennic",
    "connectivity-check",
    "category-media-ru-blocked",
]

RENAME_MAP: Dict[str, str] = {
    "category-ir": "geolocation-ir",
    "category-ru": "geolocation-ru",
    "category-tm": "geolocation-tm",
    # This is not a region code
    "category-pt": "category-private-tracker",
    "category-cas": "category-certificate-authority",
    "category-outsource-cn": "category-talnet-marketplace-cn",
    "category-number-verification-cn": "category-kyc-cn",
    "category-betting-ru": "category-gambling-ru",
    "category-medicine-ru": "category-hospital-ru",
}

ADS_SOURCE = "category-ads-all"
ADS_TARGET = "category-ads"
MERGE_EXCLUDE_MARKERS = ("@ads", "include:category-ads")
COMPANIES_FILE = "category-companies"


def remove_files(data_dir: Path) -> Dict[str, int]:
    """Remove files listed in REMOVE_FILES from data_dir."""
    removed = 0
    skipped = 0

    for name in REMOVE_FILES:
        file_path = data_dir / name
        if file_path.exists():
            if file_path.is_file():
                file_path.unlink()
                removed += 1
                print(f"removed: {file_path}")
            else:
                skipped += 1
                print(f"skipped (not a file): {file_path}")
        else:
            skipped += 1
            print(f"skipped (missing): {file_path}")

    return {"removed": removed, "skipped": skipped}


def rename_files(data_dir: Path) -> Dict[str, int]:
    """Rename files defined in RENAME_MAP under data_dir."""
    renamed = 0
    skipped = 0

    for src_name, dst_name in RENAME_MAP.items():
        src = data_dir / src_name
        dst = data_dir / dst_name

        if not src.exists():
            skipped += 1
            print(f"skipped rename (missing source): {src}")
            continue

        if not src.is_file():
            skipped += 1
            print(f"skipped rename (source is not a file): {src}")
            continue

        if dst.exists():
            skipped += 1
            print(f"skipped rename (target exists): {dst}")
            continue

        src.rename(dst)
        renamed += 1
        print(f"renamed: {src} -> {dst}")

    return {"renamed": renamed, "skipped": skipped}


def _read_non_empty_lines(path: Path) -> List[str]:
    """Read file and return non-empty lines without trailing newlines."""
    lines: List[str] = []
    with path.open("r", encoding="utf-8") as file_obj:
        for line in file_obj:
            line = line.strip()
            if line:
                lines.append(line)
    return lines


def merge_ads_files(data_dir: Path) -> Dict[str, int]:
    """Merge category-ads-all into category-ads, excluding undesired lines."""
    source = data_dir / ADS_SOURCE
    target = data_dir / ADS_TARGET

    if not source.exists():
        print(f"skipped merge (missing source): {source}")
        return {"added": 0, "skipped": 1, "removed_source": 0}

    if not source.is_file():
        print(f"skipped merge (source is not a file): {source}")
        return {"added": 0, "skipped": 1, "removed_source": 0}

    source_lines = _read_non_empty_lines(source)

    if target.exists():
        if not target.is_file():
            print(f"skipped merge (target is not a file): {target}")
            return {"added": 0, "skipped": 1, "removed_source": 0}
        target_lines = _read_non_empty_lines(target)
    else:
        target_lines = []

    filtered_target_lines = [
        line
        for line in target_lines
        if not any(marker in line for marker in MERGE_EXCLUDE_MARKERS)
    ]
    filtered_source_lines = [
        line
        for line in source_lines
        if not any(marker in line for marker in MERGE_EXCLUDE_MARKERS)
    ]
    removed_tagged_lines = (
        len(target_lines)
        - len(filtered_target_lines)
        + len(source_lines)
        - len(filtered_source_lines)
    )

    seen: Set[str] = set(filtered_target_lines)
    appended: List[str] = []
    for line in filtered_source_lines:
        if line not in seen:
            seen.add(line)
            appended.append(line)

    merged_lines = filtered_target_lines + appended
    with target.open("w", encoding="utf-8") as file_obj:
        if merged_lines:
            file_obj.write("\n".join(merged_lines) + "\n")

    source.unlink()
    print(
        f"merged: {source} -> {target} "
        f"(added {len(appended)} unique lines, removed {removed_tagged_lines} filtered lines)"
    )

    return {
        "added": len(appended),
        "skipped": 0,
        "removed_source": 1,
        "filtered_ads_tag": removed_tagged_lines,
    }


def remove_companies_includes(data_dir: Path) -> Dict[str, int]:
    """Remove all include directives from the category-companies file."""
    companies_path = data_dir / COMPANIES_FILE

    if not companies_path.exists():
        print(f"skipped companies include cleanup (missing file): {companies_path}")
        return {"removed": 0, "skipped": 1}

    if not companies_path.is_file():
        print(
            "skipped companies include cleanup "
            f"(path is not a file): {companies_path}"
        )
        return {"removed": 0, "skipped": 1}

    removed = 0
    kept_lines: List[str] = []

    with companies_path.open("r", encoding="utf-8") as file_obj:
        for line in file_obj:
            if line.lstrip().startswith("include:"):
                removed += 1
                continue
            kept_lines.append(line)

    with companies_path.open("w", encoding="utf-8") as file_obj:
        file_obj.writelines(kept_lines)

    print(f"removed includes from {companies_path}: {removed}")
    return {"removed": removed, "skipped": 0}


def normalize(data_dir: Path) -> Dict[str, Dict[str, int]]:
    """Run all normalization operations."""
    result = {
        "remove": remove_files(data_dir),
        "rename": rename_files(data_dir),
        "merge": merge_ads_files(data_dir),
        "companies": remove_companies_includes(data_dir),
    }

    print("\nsummary:")
    print(
        "remove: "
        f"removed={result['remove']['removed']} "
        f"skipped={result['remove']['skipped']}"
    )
    print(
        "rename: "
        f"renamed={result['rename']['renamed']} "
        f"skipped={result['rename']['skipped']}"
    )
    print(
        "merge: "
        f"added={result['merge']['added']} "
        f"removed_source={result['merge']['removed_source']} "
        f"skipped={result['merge']['skipped']}"
    )
    print(
        "companies: "
        f"removed={result['companies']['removed']} "
        f"skipped={result['companies']['skipped']}"
    )

    return result


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    default_data_dir = Path(__file__).resolve().parents[1] / "data"

    parser = argparse.ArgumentParser(
        description="Normalize domain-list-community data files."
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=default_data_dir,
        help="Path to the data directory (default: %(default)s)",
    )

    return parser.parse_args()


def main() -> int:
    """Program entrypoint."""
    args = parse_args()
    data_dir = args.data_dir.resolve()

    if not data_dir.exists() or not data_dir.is_dir():
        print(f"error: data directory does not exist or is not a directory: {data_dir}")
        return 1

    normalize(data_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

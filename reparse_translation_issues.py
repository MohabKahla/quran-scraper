#!/usr/bin/env python3
"""
Reparse problematic verses listed in an issues file by regenerating their split
entries from the original numbered translation text.

Usage:
    python reparse_translation_issues.py --issues ksu-translations-formatted/zh-jian/issues.txt
"""

import argparse
import re
from collections import defaultdict
from pathlib import Path

from fix_formatted_translations import (
    ensure_entry,
    load_formatted_entries,
    load_translation_source,
    split_translation_text,
)
from translation_check_utils import read_arabic_structure

REPO_ROOT = Path(__file__).resolve().parent
FORMATTED_ROOT = REPO_ROOT / "ksu-translations-formatted"

KEY_RE = re.compile(r"\d{3}_\d{2}")
HEADER_RE = re.compile(r"^\[(?P<slug>[^\]]+)\]\s+(?P<filename>.+)$")


def parse_issues_file(path: Path):
    issues = defaultdict(lambda: defaultdict(set))
    current_slug = None
    current_filename = None

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue

        header_match = HEADER_RE.match(line)
        if header_match:
            current_slug = header_match.group("slug")
            current_filename = header_match.group("filename")
            continue

        if current_slug and current_filename:
            for key in KEY_RE.findall(line):
                verse = int(key.split("_")[0])
                issues[(current_slug, current_filename)][verse].add(key)

    return issues


def rebuild_file(slug: str, filename: str, verses: set[int]):
    formatted_path = FORMATTED_ROOT / slug / filename
    if not formatted_path.exists():
        raise FileNotFoundError(f"Formatted file not found: {formatted_path}")

    chapter = int(Path(filename).stem)
    arabic_structure, _ = read_arabic_structure(chapter)
    entries = load_formatted_entries(formatted_path)
    source_verses = load_translation_source(slug, chapter)

    updated = 0
    unresolved = []

    for verse in sorted(verses):
        expected_parts = arabic_structure.get(verse)
        if not expected_parts:
            unresolved.append((verse, "no_arabic_structure"))
            continue

        verse_text = source_verses.get(verse, "").strip()
        if not verse_text:
            unresolved.append((verse, "missing_source_text"))
            continue

        parts_needed = len(expected_parts)
        split_parts = split_translation_text(verse_text, parts_needed)

        if len(split_parts) != parts_needed:
            unresolved.append((verse, f"split_mismatch:{len(split_parts)}/{parts_needed}"))
            continue

        for index, part in enumerate(expected_parts):
            key = f"{verse:03d}_{part:02d}"
            ensure_entry(entries, key)
            entries[key] = split_parts[index].strip()
        updated += 1

    if updated:
        lines = []
        if "000_00" in entries:
            lines.append(f"000_00\t{entries['000_00'].strip()}")

        for verse in sorted(arabic_structure.keys()):
            if verse == 0:
                continue
            for part in arabic_structure[verse]:
                key = f"{verse:03d}_{part:02d}"
                ensure_entry(entries, key)
                lines.append(f"{key}\t{entries.get(key, '').strip()}")

        formatted_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return updated, unresolved


def main():
    parser = argparse.ArgumentParser(description="Reparse verses listed in an issues file.")
    parser.add_argument("--issues", required=True, type=Path, help="Path to the issues.txt file.")
    args = parser.parse_args()

    issues_map = parse_issues_file(args.issues)

    total_updated = 0
    all_unresolved = []

    for (slug, filename), verse_map in sorted(issues_map.items()):
        verses = set(verse_map.keys())
        updated, unresolved = rebuild_file(slug, filename, verses)
        total_updated += updated
        if unresolved:
            all_unresolved.append(((slug, filename), unresolved))
        print(f"{slug}/{filename}: updated {updated} verse(s) ({len(verses)} requested)")

    print("\nDone.")
    print(f"Files processed: {len(issues_map)}")
    print(f"Verses updated:  {total_updated}")

    if all_unresolved:
        print("\nUnresolved items:")
        for (slug, filename), items in all_unresolved:
            pending = ", ".join(f"{verse}:{reason}" for verse, reason in items)
            print(f"  {slug}/{filename}: {pending}")


if __name__ == "__main__":
    main()

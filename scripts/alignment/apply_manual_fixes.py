#!/usr/bin/env python3
"""
Apply targeted manual fixes for remaining translation issues.

This script handles:
1. Skipped char-level fixes from fix_char_changes.py
2. Verse number leak removals (e.g., "88" inserted in verse)
3. Simple text replacements that don't need AI

Run iteratively until validation shows only punctuation/spacing mismatches.
"""

import re
import sys
from pathlib import Path
from collections import defaultdict

FORMATTED_DIR = Path("data/ksu-translations-formatted")


def replace_in_verse(file_path: Path, verse_num: int, old_text: str, new_text: str):
    """Replace text in a specific verse across all its parts."""
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    modified = False
    for i, line in enumerate(lines):
        if re.match(rf'^{verse_num:03d}_\d+\t', line):
            key, text = line.rstrip('\n').split('\t', 1)
            if old_text in text:
                text = text.replace(old_text, new_text, 1)
                lines[i] = f"{key}\t{text}\n"
                modified = True
                print(f"  Fixed {file_path.name}:{verse_num} — replaced '{old_text[:40]}'")

    if modified:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        return True
    return False


def fix_verse_number_leaks():
    """Remove verse numbers that leaked into verse text."""
    fixes = [
        ("it-piccardo", "012.txt", 88, " 88", ""),  # Extra verse number in text
    ]

    print("\n=== Fixing Verse Number Leaks ===")
    for lang, file, verse, old, new in fixes:
        file_path = FORMATTED_DIR / lang / file
        if file_path.exists():
            replace_in_verse(file_path, verse, old, new)


def fix_inserted_phrases():
    """Remove extra phrases that were inserted."""
    fixes = [
        # Bosnian - extra phrases at end of verse
        ("bs-korkut", "002.txt", 101, " kao da ne znaju.", ""),
        ("bs-korkut", "003.txt", 49, "te ", ""),
        ("bs-korkut", "004.txt", 12, " te", ""),

        # Spanish - extra spaces/words
        ("es-navio", "002.txt", 228, "p ", ""),
        ("es-navio", "002.txt", 253, "e qu", ""),
        ("es-navio", "040.txt", 56, "un ", ""),
        ("es-navio", "058.txt", 4, " es. ", "es."),

        # Indonesian - extra space
        ("id-indonesian", "057.txt", 27, " d", ". D"),

        # Thai - extra space in word
        ("th-thai", "002.txt", 246, " ขากล่าว", " ขากล่า"),
    ]

    print("\n=== Fixing Inserted Phrases ===")
    for lang, file, verse, old, new in fixes:
        file_path = FORMATTED_DIR / lang / file
        if file_path.exists():
            replace_in_verse(file_path, verse, old, new)


def fix_capitalization():
    """Fix capitalization after sentence boundaries."""
    # These are formatting improvements, but listed for completeness
    # Many of these (sq-nahi 'd' -> 'D') are actually corrections
    pass


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Apply manual fixes")
    parser.add_argument("--all", action="store_true", help="Run all fix categories")
    parser.add_argument("--verse-leaks", action="store_true")
    parser.add_argument("--insertions", action="store_true")
    args = parser.parse_args()

    if args.all or args.verse_leaks:
        fix_verse_number_leaks()

    if args.all or args.insertions:
        fix_inserted_phrases()

    print("\n✅ Done. Run validation to check progress:")
    print("   python3 scripts/validation/compare_formatted_vs_original.py")

    return 0


if __name__ == "__main__":
    sys.exit(main())

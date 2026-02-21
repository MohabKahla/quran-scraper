#!/usr/bin/env python3
"""
Compare formatted translations with original source files to ensure content integrity.

This script validates that the alignment/reformatting process preserved the actual
verse text by comparing:
- Original: data/old-translations/ksu-translations/{lang}/{chapter}.txt
- Formatted: data/ksu-translations-formatted/{lang}/{chapter}.txt

Key differences in format:
- Original: "1. verse text", "2. verse text", etc.
- Formatted: "001_00\tverse text", "026_00\tfirst part", "026_01\tsecond part", etc.

The script:
1. Extracts verse text from both formats
2. Combines split verses in formatted files (026_00 + 026_01 + ...)
3. Normalizes whitespace for comparison
4. Reports any content mismatches
"""

import re
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict
import difflib
import sys


def read_original_verses(file_path: Path) -> Dict[int, str]:
    """
    Read verses from original format: "1. verse text"

    Returns:
        Dict mapping verse number to verse text
    """
    verses = {}

    if not file_path.exists():
        return verses

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Pattern: verse number, period, space, then text until next verse or end
    # Example: "1. verse text\n2. next verse"
    pattern = r'^(\d+)\.\s+(.+?)(?=^\d+\.\s+|\Z)'

    for match in re.finditer(pattern, content, re.MULTILINE | re.DOTALL):
        verse_num = int(match.group(1))
        verse_text = match.group(2).strip()
        # Normalize whitespace: replace multiple spaces/newlines with single space
        verse_text = ' '.join(verse_text.split())
        verses[verse_num] = verse_text

    return verses


def read_formatted_verses(file_path: Path) -> Dict[int, str]:
    """
    Read verses from formatted format: "026_00\tverse part"

    Combines split verses (026_00, 026_01, 026_02, ...) into single verse.

    Returns:
        Dict mapping verse number to complete verse text
    """
    verse_parts = defaultdict(list)

    if not file_path.exists():
        return {}

    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            # Skip surah name lines or other metadata
            if '\t' not in line:
                continue

            # Parse format: "026_01\tverse text"
            parts = line.split('\t', 1)
            if len(parts) != 2:
                continue

            verse_key, verse_text = parts

            # Extract verse number from format "026_01"
            match = re.match(r'(\d+)_(\d+)', verse_key)
            if not match:
                continue

            verse_num = int(match.group(1))
            split_num = int(match.group(2))

            # Store with split number to maintain order
            verse_parts[verse_num].append((split_num, verse_text.strip()))

    # Combine all parts of each verse
    verses = {}
    for verse_num, parts in verse_parts.items():
        # Sort by split number to ensure correct order
        parts.sort(key=lambda x: x[0])
        # Combine with spaces
        combined_text = ' '.join(text for _, text in parts)
        # Normalize whitespace
        combined_text = ' '.join(combined_text.split())
        verses[verse_num] = combined_text

    return verses


def normalize_text(text: str) -> str:
    """
    Normalize text for comparison:
    - Strip leading/trailing whitespace
    - Collapse multiple spaces to single space
    - Remove zero-width characters
    """
    # Remove zero-width spaces and other invisible characters
    text = re.sub(r'[\u200b\u200c\u200d\ufeff]', '', text)
    # Normalize whitespace
    text = ' '.join(text.split())
    return text


def compare_verses(
    original: Dict[int, str],
    formatted: Dict[int, str],
    chapter: str,
    language: str
) -> List[Dict]:
    """
    Compare original and formatted verses.

    Returns:
        List of mismatch reports
    """
    mismatches = []

    all_verse_nums = set(original.keys()) | set(formatted.keys())

    for verse_num in sorted(all_verse_nums):
        orig_text = original.get(verse_num, "")
        fmt_text = formatted.get(verse_num, "")

        # Normalize both texts
        orig_normalized = normalize_text(orig_text)
        fmt_normalized = normalize_text(fmt_text)

        if orig_normalized != fmt_normalized:
            # Calculate similarity ratio
            similarity = difflib.SequenceMatcher(
                None, orig_normalized, fmt_normalized
            ).ratio()

            mismatch = {
                'chapter': chapter,
                'language': language,
                'verse': verse_num,
                'original_text': orig_text,
                'formatted_text': fmt_text,
                'similarity': similarity,
                'missing_in_formatted': verse_num in original and verse_num not in formatted,
                'missing_in_original': verse_num not in original and verse_num in formatted,
            }
            mismatches.append(mismatch)

    return mismatches


def validate_translation(
    language: str,
    old_translations_dir: Path,
    formatted_dir: Path,
    verbose: bool = False
) -> Tuple[int, int, List[Dict]]:
    """
    Validate all chapters for a given translation.

    Returns:
        (total_chapters, total_verses, all_mismatches)
    """
    old_lang_dir = old_translations_dir / language
    fmt_lang_dir = formatted_dir / language

    if not old_lang_dir.exists():
        print(f"⚠️  Original translation not found: {old_lang_dir}")
        return 0, 0, []

    if not fmt_lang_dir.exists():
        print(f"⚠️  Formatted translation not found: {fmt_lang_dir}")
        return 0, 0, []

    all_mismatches = []
    total_chapters = 0
    total_verses = 0

    # Process chapters 001 to 114
    for chapter_num in range(1, 115):
        chapter_str = f"{chapter_num:03d}"

        old_file = old_lang_dir / f"{chapter_str}.txt"
        fmt_file = fmt_lang_dir / f"{chapter_str}.txt"

        if not old_file.exists() or not fmt_file.exists():
            if verbose:
                print(f"  Skipping {chapter_str}: file not found")
            continue

        # Read verses from both files
        original_verses = read_original_verses(old_file)
        formatted_verses = read_formatted_verses(fmt_file)

        if not original_verses and not formatted_verses:
            continue

        total_chapters += 1
        total_verses += max(len(original_verses), len(formatted_verses))

        # Compare verses
        mismatches = compare_verses(
            original_verses,
            formatted_verses,
            chapter_str,
            language
        )

        if mismatches:
            all_mismatches.extend(mismatches)
            if verbose:
                print(f"  ❌ Chapter {chapter_str}: {len(mismatches)} mismatches")
        elif verbose:
            print(f"  ✓ Chapter {chapter_str}: {len(original_verses)} verses OK")

    return total_chapters, total_verses, all_mismatches


def print_mismatch_report(mismatch: Dict, show_diff: bool = True):
    """Print detailed mismatch report."""
    print(f"\n{'='*80}")
    print(f"❌ MISMATCH: {mismatch['language']} - Chapter {mismatch['chapter']} - Verse {mismatch['verse']}")
    print(f"Similarity: {mismatch['similarity']:.1%}")
    print(f"{'='*80}")

    if mismatch['missing_in_formatted']:
        print("⚠️  VERSE MISSING IN FORMATTED VERSION")
    elif mismatch['missing_in_original']:
        print("⚠️  VERSE MISSING IN ORIGINAL VERSION")

    print(f"\nOriginal ({len(mismatch['original_text'])} chars):")
    print(f"  {mismatch['original_text'][:200]}{'...' if len(mismatch['original_text']) > 200 else ''}")

    print(f"\nFormatted ({len(mismatch['formatted_text'])} chars):")
    print(f"  {mismatch['formatted_text'][:200]}{'...' if len(mismatch['formatted_text']) > 200 else ''}")

    if show_diff and mismatch['similarity'] > 0.5:
        # Show character-level diff for similar texts
        print("\nCharacter diff:")
        orig = mismatch['original_text']
        fmt = mismatch['formatted_text']

        # Find first difference
        for i, (c1, c2) in enumerate(zip(orig, fmt)):
            if c1 != c2:
                start = max(0, i - 30)
                end = min(len(orig), i + 30)
                print(f"  Position {i}:")
                print(f"    Orig: ...{orig[start:end]}...")
                print(f"    Fmt:  ...{fmt[start:end]}...")
                break


def main():
    import argparse
    import json

    parser = argparse.ArgumentParser(
        description="Compare formatted translations with original source files"
    )
    parser.add_argument(
        "--language",
        help="Specific language to check (e.g., bn-bengali, es-navio). If not specified, checks all."
    )
    parser.add_argument(
        "--chapter",
        help="Specific chapter to check (001-114). If not specified, checks all."
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed progress for each chapter"
    )
    parser.add_argument(
        "--show-diff",
        action="store_true",
        help="Show detailed character-level diff for mismatches"
    )
    parser.add_argument(
        "--show-all",
        action="store_true",
        help="Show ALL mismatches in detail (not just first 5 per language)"
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        help="Save detailed mismatch report to JSON file for automated processing"
    )
    parser.add_argument(
        "--old-dir",
        type=Path,
        default=Path("data/old-translations/ksu-translations"),
        help="Directory containing original translations"
    )
    parser.add_argument(
        "--formatted-dir",
        type=Path,
        default=Path("data/ksu-translations-formatted"),
        help="Directory containing formatted translations"
    )

    args = parser.parse_args()

    print("="*80)
    print("TRANSLATION CONTENT INTEGRITY VALIDATION")
    print("="*80)
    print(f"\nComparing:")
    print(f"  Original:  {args.old_dir}")
    print(f"  Formatted: {args.formatted_dir}")
    print()

    # Determine which languages to check
    if args.language:
        languages = [args.language]
    else:
        # Get all languages from formatted directory
        languages = [
            d.name for d in args.formatted_dir.iterdir()
            if d.is_dir() and not d.name.startswith('.')
        ]
        languages.sort()

    # Track overall statistics
    total_languages_checked = 0
    total_languages_with_issues = 0
    all_mismatches = []

    for language in languages:
        print(f"\n{'─'*80}")
        print(f"📖 Checking: {language}")
        print(f"{'─'*80}")

        if args.chapter:
            # Check specific chapter only
            chapter_str = args.chapter
            old_file = args.old_dir / language / f"{chapter_str}.txt"
            fmt_file = args.formatted_dir / language / f"{chapter_str}.txt"

            if not old_file.exists() or not fmt_file.exists():
                print(f"⚠️  Chapter {chapter_str} not found for {language}")
                continue

            original_verses = read_original_verses(old_file)
            formatted_verses = read_formatted_verses(fmt_file)

            mismatches = compare_verses(
                original_verses,
                formatted_verses,
                chapter_str,
                language
            )

            if mismatches:
                all_mismatches.extend(mismatches)
                total_languages_with_issues += 1

            total_languages_checked += 1
        else:
            # Check all chapters
            chapters, verses, mismatches = validate_translation(
                language,
                args.old_dir,
                args.formatted_dir,
                verbose=args.verbose
            )

            if chapters > 0:
                total_languages_checked += 1

                if mismatches:
                    all_mismatches.extend(mismatches)
                    total_languages_with_issues += 1
                    print(f"\n❌ {len(mismatches)} mismatches found in {chapters} chapters ({verses} verses)")
                else:
                    print(f"\n✅ All {verses} verses in {chapters} chapters match perfectly!")

    # Print summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Languages checked: {total_languages_checked}")
    print(f"Languages with issues: {total_languages_with_issues}")
    print(f"Languages perfect: {total_languages_checked - total_languages_with_issues}")
    print(f"Total mismatches: {len(all_mismatches)}")

    if all_mismatches:
        print(f"\n{'='*80}")
        print(f"DETAILED MISMATCH REPORT ({len(all_mismatches)} issues)")
        print(f"{'='*80}")

        # Group by language
        by_language = defaultdict(list)
        for m in all_mismatches:
            by_language[m['language']].append(m)

        for language in sorted(by_language.keys()):
            mismatches = by_language[language]
            print(f"\n{language}: {len(mismatches)} mismatches")

            # Show all or just first 5 depending on flag
            show_count = len(mismatches) if args.show_all else min(5, len(mismatches))

            for mismatch in mismatches[:show_count]:
                print_mismatch_report(mismatch, show_diff=args.show_diff)

            if len(mismatches) > show_count:
                print(f"\n... and {len(mismatches) - show_count} more mismatches for {language}")
                if not args.show_all:
                    print("    (Use --show-all to see all mismatches)")

        # Save JSON report if requested
        if args.json_output:
            json_report = {
                'summary': {
                    'languages_checked': total_languages_checked,
                    'languages_with_issues': total_languages_with_issues,
                    'languages_perfect': total_languages_checked - total_languages_with_issues,
                    'total_mismatches': len(all_mismatches)
                },
                'mismatches': all_mismatches
            }

            with open(args.json_output, 'w', encoding='utf-8') as f:
                json.dump(json_report, f, ensure_ascii=False, indent=2)

            print(f"\n📄 Detailed JSON report saved to: {args.json_output}")

        print("\n" + "="*80)
        return 1  # Exit with error code
    else:
        print("\n✅ All translations match perfectly! Content integrity validated.")

        # Save empty JSON report if requested
        if args.json_output:
            json_report = {
                'summary': {
                    'languages_checked': total_languages_checked,
                    'languages_with_issues': 0,
                    'languages_perfect': total_languages_checked,
                    'total_mismatches': 0
                },
                'mismatches': []
            }

            with open(args.json_output, 'w', encoding='utf-8') as f:
                json.dump(json_report, f, ensure_ascii=False, indent=2)

            print(f"📄 JSON report saved to: {args.json_output}")

        return 0


if __name__ == "__main__":
    sys.exit(main())

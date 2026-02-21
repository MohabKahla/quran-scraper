#!/usr/bin/env python3
"""
Restore missing content from original translations to formatted versions.

This script fixes truncation issues where formatted translations lost content
during the AI alignment/reformatting process. It:
1. Compares original vs formatted verses (combining split parts)
2. Detects missing content
3. Appends missing content to the last split part
4. Preserves existing verse split structure

Usage:
    # Test on single language
    python3 restore_missing_content.py --language bn-bengali --dry-run

    # Fix single language
    python3 restore_missing_content.py --language bn-bengali

    # Fix all languages
    python3 restore_missing_content.py --all

    # Skip minor punctuation differences
    python3 restore_missing_content.py --language es-navio --min-similarity 0.99
"""

import re
import shutil
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict
import difflib
import sys
from datetime import datetime


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
    pattern = r'^(\d+)\.\s+(.+?)(?=^\d+\.\s+|\Z)'

    for match in re.finditer(pattern, content, re.MULTILINE | re.DOTALL):
        verse_num = int(match.group(1))
        verse_text = match.group(2).strip()
        # Normalize whitespace: replace multiple spaces/newlines with single space
        verse_text = ' '.join(verse_text.split())
        verses[verse_num] = verse_text

    return verses


def read_formatted_verses(file_path: Path) -> Dict[int, List[Tuple[int, str]]]:
    """
    Read verses from formatted format: "026_00\\tverse part"

    Returns:
        Dict mapping verse number to list of (split_num, text) tuples
    """
    verse_parts = defaultdict(list)

    if not file_path.exists():
        return {}

    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or '\t' not in line:
                continue

            # Parse format: "026_01\\tverse text"
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

            verse_parts[verse_num].append((split_num, verse_text.strip()))

    return verse_parts


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


def find_missing_content(original: str, formatted: str) -> Tuple[str, float]:
    """
    Find content missing from formatted version.

    Returns:
        (missing_content, similarity_ratio)
    """
    orig_normalized = normalize_text(original)
    fmt_normalized = normalize_text(formatted)

    # Calculate similarity
    similarity = difflib.SequenceMatcher(None, orig_normalized, fmt_normalized).ratio()

    # If identical or very similar, no missing content
    if similarity >= 0.999:
        return "", similarity

    # Find missing content by checking if formatted is substring of original
    if fmt_normalized in orig_normalized:
        # Formatted is a prefix/substring - find what's missing
        missing = orig_normalized.replace(fmt_normalized, '', 1).strip()
        return missing, similarity

    # For more complex cases, use difflib to find differences
    matcher = difflib.SequenceMatcher(None, fmt_normalized, orig_normalized)

    # Try to extract missing parts
    missing_parts = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'delete':
            # Content in formatted that's not in original (shouldn't happen)
            continue
        elif tag == 'insert':
            # Content in original that's missing from formatted
            missing_parts.append(orig_normalized[j1:j2])

    missing = ' '.join(missing_parts).strip()
    return missing, similarity


def restore_chapter(
    language: str,
    chapter: str,
    old_dir: Path,
    formatted_dir: Path,
    min_similarity: float = 0.0,
    dry_run: bool = False
) -> Dict:
    """
    Restore missing content for a single chapter.

    Returns:
        Dict with restoration stats
    """
    old_file = old_dir / language / f"{chapter}.txt"
    fmt_file = formatted_dir / language / f"{chapter}.txt"

    if not old_file.exists() or not fmt_file.exists():
        return {'skipped': True, 'reason': 'file_not_found'}

    # Read verses
    original_verses = read_original_verses(old_file)
    formatted_verse_parts = read_formatted_verses(fmt_file)

    if not original_verses or not formatted_verse_parts:
        return {'skipped': True, 'reason': 'no_verses'}

    restorations = []

    for verse_num in sorted(set(original_verses.keys()) | set(formatted_verse_parts.keys())):
        if verse_num not in original_verses:
            continue  # Extra verse in formatted, skip

        if verse_num not in formatted_verse_parts:
            # Verse missing entirely in formatted
            restorations.append({
                'verse': verse_num,
                'type': 'missing_verse',
                'original': original_verses[verse_num][:100],
                'action': 'NEEDS_MANUAL_FIX'
            })
            continue

        # Combine formatted parts
        parts = sorted(formatted_verse_parts[verse_num], key=lambda x: x[0])
        combined_formatted = ' '.join(text for _, text in parts)

        # Find missing content
        missing, similarity = find_missing_content(
            original_verses[verse_num],
            combined_formatted
        )

        # Skip if similarity is above threshold (minor differences)
        if similarity >= min_similarity and not missing:
            continue

        if missing:
            restorations.append({
                'verse': verse_num,
                'type': 'truncated',
                'similarity': similarity,
                'missing_content': missing,
                'last_split': parts[-1][0],  # Last split number
                'original_length': len(original_verses[verse_num]),
                'formatted_length': len(combined_formatted),
                'missing_length': len(missing)
            })

    # Apply restorations if not dry run
    if restorations and not dry_run:
        # Backup original file
        backup_dir = Path('backups') / datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = backup_dir / language / f"{chapter}.txt"
        backup_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(fmt_file, backup_file)

        # Read all lines from formatted file
        with open(fmt_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Apply restorations
        for restoration in restorations:
            if restoration['type'] != 'truncated':
                continue

            verse_num = restoration['verse']
            missing = restoration['missing_content']
            last_split = restoration['last_split']

            # Find the line with the last split
            verse_key = f"{verse_num:03d}_{last_split:02d}"

            for i, line in enumerate(lines):
                if line.startswith(verse_key + '\t'):
                    # Append missing content to this line
                    current_text = line.strip().split('\t', 1)[1]
                    # Add space before appending if needed
                    if not current_text.endswith('.') and not current_text.endswith('؟'):
                        lines[i] = f"{verse_key}\t{current_text} {missing}\n"
                    else:
                        lines[i] = f"{verse_key}\t{current_text} {missing}\n"
                    break

        # Write updated file
        with open(fmt_file, 'w', encoding='utf-8') as f:
            f.writelines(lines)

    return {
        'skipped': False,
        'restorations': restorations,
        'count': len(restorations)
    }


def restore_language(
    language: str,
    old_dir: Path,
    formatted_dir: Path,
    min_similarity: float = 0.0,
    dry_run: bool = False,
    verbose: bool = False
) -> Tuple[int, int, List[Dict]]:
    """
    Restore all chapters for a language.

    Returns:
        (chapters_processed, total_restorations, all_restorations)
    """
    old_lang_dir = old_dir / language
    fmt_lang_dir = formatted_dir / language

    if not old_lang_dir.exists():
        print(f"⚠️  Original translation not found: {old_lang_dir}")
        return 0, 0, []

    if not fmt_lang_dir.exists():
        print(f"⚠️  Formatted translation not found: {fmt_lang_dir}")
        return 0, 0, []

    all_restorations = []
    chapters_processed = 0
    total_restorations = 0

    # Process chapters 001 to 114
    for chapter_num in range(1, 115):
        chapter_str = f"{chapter_num:03d}"

        result = restore_chapter(
            language, chapter_str, old_dir, formatted_dir,
            min_similarity=min_similarity, dry_run=dry_run
        )

        if result['skipped']:
            if verbose:
                print(f"  Skipping {chapter_str}: {result.get('reason', 'unknown')}")
            continue

        chapters_processed += 1

        if result['count'] > 0:
            total_restorations += result['count']
            all_restorations.extend([
                {**r, 'chapter': chapter_str, 'language': language}
                for r in result['restorations']
            ])

            if verbose:
                print(f"  ✓ Chapter {chapter_str}: {result['count']} restorations")
        elif verbose:
            print(f"  ✓ Chapter {chapter_str}: OK")

    return chapters_processed, total_restorations, all_restorations


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Restore missing content from original to formatted translations"
    )
    parser.add_argument(
        "--language",
        help="Specific language to restore (e.g., bn-bengali, es-navio)"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Restore all languages"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be restored without making changes"
    )
    parser.add_argument(
        "--min-similarity",
        type=float,
        default=0.0,
        help="Skip restorations with similarity >= this threshold (0.0-1.0). Use 0.99 to skip punctuation-only differences"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed progress"
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

    if not args.language and not args.all:
        parser.error("Must specify either --language or --all")

    print("=" * 80)
    print("TRANSLATION CONTENT RESTORATION")
    print("=" * 80)
    print(f"\nMode: {'DRY RUN' if args.dry_run else 'LIVE RESTORATION'}")
    print(f"Original:  {args.old_dir}")
    print(f"Formatted: {args.formatted_dir}")
    print(f"Min similarity threshold: {args.min_similarity:.2%}")
    print()

    # Determine languages to process
    if args.language:
        languages = [args.language]
    else:
        languages = [
            d.name for d in args.formatted_dir.iterdir()
            if d.is_dir() and not d.name.startswith('.')
        ]
        languages.sort()

    # Process languages
    total_chapters = 0
    total_restorations = 0
    all_restorations = []

    for i, language in enumerate(languages, 1):
        print(f"\n{'─' * 80}")
        print(f"[{i}/{len(languages)}] 📖 Processing: {language}")
        print(f"{'─' * 80}")

        chapters, restorations, restoration_list = restore_language(
            language,
            args.old_dir,
            args.formatted_dir,
            min_similarity=args.min_similarity,
            dry_run=args.dry_run,
            verbose=args.verbose
        )

        total_chapters += chapters
        total_restorations += restorations
        all_restorations.extend(restoration_list)

        if restorations > 0:
            print(f"\n{'DRY RUN: Would restore' if args.dry_run else 'Restored'} {restorations} verses in {chapters} chapters")
        else:
            print(f"\n✅ All verses OK in {chapters} chapters")

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Languages processed: {len(languages)}")
    print(f"Chapters processed: {total_chapters}")
    print(f"Total restorations: {total_restorations}")

    if all_restorations:
        print(f"\n{'─' * 80}")
        print("RESTORATION DETAILS")
        print(f"{'─' * 80}")

        # Group by language
        by_language = defaultdict(list)
        for r in all_restorations:
            by_language[r['language']].append(r)

        for language in sorted(by_language.keys()):
            restorations = by_language[language]
            print(f"\n{language}: {len(restorations)} restorations")

            # Show first 5 examples
            for r in restorations[:5]:
                if r['type'] == 'truncated':
                    print(f"  Chapter {r['chapter']}, Verse {r['verse']:03d}:")
                    print(f"    Similarity: {r['similarity']:.1%}")
                    print(f"    Missing ({r['missing_length']} chars): {r['missing_content'][:80]}...")
                elif r['type'] == 'missing_verse':
                    print(f"  Chapter {r['chapter']}, Verse {r['verse']:03d}: {r['action']}")

            if len(restorations) > 5:
                print(f"  ... and {len(restorations) - 5} more")

        # Save detailed report
        if not args.dry_run:
            logs_dir = Path('logs')
            logs_dir.mkdir(exist_ok=True)
            report_file = logs_dir / f'restoration_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'

            with open(report_file, 'w', encoding='utf-8') as f:
                f.write("RESTORATION REPORT\n")
                f.write("=" * 80 + "\n\n")

                for r in all_restorations:
                    f.write(f"\n{r['language']} - Chapter {r['chapter']} - Verse {r['verse']:03d}\n")
                    f.write(f"  Type: {r['type']}\n")
                    if r['type'] == 'truncated':
                        f.write(f"  Similarity: {r['similarity']:.1%}\n")
                        f.write(f"  Missing content: {r['missing_content']}\n")
                    f.write("\n")

            print(f"\n📄 Detailed report saved to: {report_file}")

    if args.dry_run:
        print("\n⚠️  DRY RUN MODE - No changes were made")
        print("Remove --dry-run to apply restorations")
    else:
        print("\n✅ Restoration complete!")
        print("\nNext steps:")
        print("  1. Run validation: python3 scripts/validation/compare_formatted_vs_original.py --language <lang>")
        print("  2. Review backup files in: backups/")
        print("  3. Commit changes if satisfied")

    return 0 if total_restorations == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Fix word-break issues in formatted translations.

Handles cases where words are incorrectly split with spaces:
- "Ange li" → "Angeli"
- "vess azioni" → "vessazioni"
- "Giov anni" → "Giovanni"

These typically appear as 99%+ similarity mismatches caused by AI alignment issues.

Usage:
    python3 fix_word_breaks.py --language it-piccardo --dry-run
    python3 fix_word_breaks.py --language it-piccardo
    python3 fix_word_breaks.py --all
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
    """Read verses from original format."""
    verses = {}
    if not file_path.exists():
        return verses

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    pattern = r'^(\d+)\.\s+(.+?)(?=^\d+\.\s+|\Z)'
    for match in re.finditer(pattern, content, re.MULTILINE | re.DOTALL):
        verse_num = int(match.group(1))
        verse_text = match.group(2).strip()
        verse_text = ' '.join(verse_text.split())
        verses[verse_num] = verse_text

    return verses


def read_formatted_file(file_path: Path) -> List[str]:
    """Read formatted file preserving all lines."""
    if not file_path.exists():
        return []

    with open(file_path, 'r', encoding='utf-8') as f:
        return f.readlines()


def find_word_breaks(original: str, formatted: str) -> List[Tuple[str, str]]:
    """
    Find word-break differences between original and formatted.

    Returns list of (broken_word, correct_word) tuples.
    """
    # Simple approach: find sequences in formatted that have extra spaces
    # compared to original

    fixes = []

    # Split into words
    orig_words = original.split()
    fmt_words = formatted.split()

    # Use difflib to find differences
    matcher = difflib.SequenceMatcher(None, orig_words, fmt_words)

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'replace':
            # Check if it's a word-break issue
            orig_segment = ' '.join(orig_words[i1:i2])
            fmt_segment = ' '.join(fmt_words[j1:j2])

            # If formatted has extra spaces (more words for same content)
            if j2 - j1 > i2 - i1:
                # Remove spaces from formatted segment
                orig_no_space = orig_segment.replace(' ', '')
                fmt_no_space = fmt_segment.replace(' ', '')

                # If they match without spaces, it's a word-break
                if orig_no_space == fmt_no_space:
                    fixes.append((fmt_segment, orig_segment))

    return fixes


def fix_chapter(
    language: str,
    chapter: str,
    old_dir: Path,
    formatted_dir: Path,
    min_similarity: float = 0.99,
    dry_run: bool = False
) -> Dict:
    """Fix word breaks in a single chapter."""

    old_file = old_dir / language / f"{chapter}.txt"
    fmt_file = formatted_dir / language / f"{chapter}.txt"

    if not old_file.exists() or not fmt_file.exists():
        return {'skipped': True, 'reason': 'file_not_found'}

    original_verses = read_original_verses(old_file)
    lines = read_formatted_file(fmt_file)

    if not original_verses or not lines:
        return {'skipped': True, 'reason': 'no_content'}

    fixes = []
    modified_lines = 0

    for i, line in enumerate(lines):
        if not line.strip() or '\t' not in line:
            continue

        parts = line.split('\t', 1)
        if len(parts) != 2:
            continue

        verse_key, verse_text = parts

        # Extract verse number
        match = re.match(r'(\d+)_\d+', verse_key)
        if not match:
            continue

        verse_num = int(match.group(1))

        if verse_num not in original_verses:
            continue

        # Check similarity
        orig = ' '.join(original_verses[verse_num].split())
        fmt = ' '.join(verse_text.split())

        similarity = difflib.SequenceMatcher(None, orig, fmt).ratio()

        if similarity >= min_similarity and similarity < 1.0:
            # Find word breaks
            word_fixes = find_word_breaks(orig, fmt)

            if word_fixes:
                # Apply fixes
                new_text = verse_text
                for broken, correct in word_fixes:
                    new_text = new_text.replace(broken, correct)

                if new_text != verse_text:
                    fixes.append({
                        'chapter': chapter,
                        'verse': verse_num,
                        'line': i,
                        'similarity': similarity,
                        'original': verse_text[:80],
                        'fixed': new_text[:80],
                        'num_fixes': len(word_fixes)
                    })

                    if not dry_run:
                        lines[i] = f"{verse_key}\t{new_text}\n"
                        modified_lines += 1

    # Write back if changes made
    if modified_lines > 0 and not dry_run:
        # Backup
        backup_dir = Path('backups') / datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = backup_dir / language / f"{chapter}.txt"
        backup_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(fmt_file, backup_file)

        # Write
        with open(fmt_file, 'w', encoding='utf-8') as f:
            f.writelines(lines)

    return {
        'skipped': False,
        'fixes': fixes,
        'count': len(fixes),
        'modified_lines': modified_lines
    }


def fix_language(
    language: str,
    old_dir: Path,
    formatted_dir: Path,
    min_similarity: float = 0.99,
    dry_run: bool = False,
    verbose: bool = False
) -> Tuple[int, int, List[Dict]]:
    """Fix word breaks for all chapters in a language."""

    all_fixes = []
    chapters_processed = 0
    total_fixes = 0

    for chapter_num in range(1, 115):
        chapter_str = f"{chapter_num:03d}"

        result = fix_chapter(
            language, chapter_str, old_dir, formatted_dir,
            min_similarity=min_similarity, dry_run=dry_run
        )

        if result['skipped']:
            continue

        chapters_processed += 1

        if result['count'] > 0:
            total_fixes += result['count']
            all_fixes.extend([{**f, 'language': language} for f in result['fixes']])

            if verbose:
                print(f"  ✓ Chapter {chapter_str}: {result['count']} word-break fixes")

    return chapters_processed, total_fixes, all_fixes


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Fix word-break issues in translations")
    parser.add_argument("--language", help="Language to fix")
    parser.add_argument("--all", action="store_true", help="Fix all languages")
    parser.add_argument("--dry-run", action="store_true", help="Preview without changes")
    parser.add_argument("--min-similarity", type=float, default=0.99,
                       help="Minimum similarity to consider (default: 0.99)")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--old-dir", type=Path,
                       default=Path("data/old-translations/ksu-translations"))
    parser.add_argument("--formatted-dir", type=Path,
                       default=Path("data/ksu-translations-formatted"))

    args = parser.parse_args()

    if not args.language and not args.all:
        parser.error("Must specify either --language or --all")

    print("=" * 80)
    print("WORD-BREAK FIXER")
    print("=" * 80)
    print(f"\nMode: {'DRY RUN' if args.dry_run else 'LIVE FIX'}")
    print(f"Min similarity: {args.min_similarity:.1%}")
    print()

    if args.language:
        languages = [args.language]
    else:
        languages = [
            d.name for d in args.formatted_dir.iterdir()
            if d.is_dir() and not d.name.startswith('.')
        ]
        languages.sort()

    total_fixes = 0
    all_fixes = []

    for i, language in enumerate(languages, 1):
        print(f"\n{'─' * 80}")
        print(f"[{i}/{len(languages)}] 📖 Processing: {language}")
        print(f"{'─' * 80}")

        chapters, fixes, fix_list = fix_language(
            language, args.old_dir, args.formatted_dir,
            min_similarity=args.min_similarity,
            dry_run=args.dry_run,
            verbose=args.verbose
        )

        total_fixes += fixes
        all_fixes.extend(fix_list)

        if fixes > 0:
            print(f"\n{'Would fix' if args.dry_run else 'Fixed'} {fixes} word-breaks in {chapters} chapters")
        else:
            print(f"\n✅ No word-break issues found")

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Languages: {len(languages)}")
    print(f"Total word-break fixes: {total_fixes}")

    if all_fixes and args.verbose:
        print(f"\n{'─' * 80}")
        print("SAMPLE FIXES")
        print(f"{'─' * 80}")

        by_language = defaultdict(list)
        for fix in all_fixes:
            by_language[fix['language']].append(fix)

        for language in sorted(by_language.keys())[:3]:  # Show first 3 languages
            fixes = by_language[language]
            print(f"\n{language}: {len(fixes)} fixes")
            for fix in fixes[:3]:  # Show first 3 fixes
                print(f"  Chapter {fix['chapter']}, Verse {fix['verse']:03d}")
                print(f"    Similarity: {fix['similarity']:.1%}")
                print(f"    Fixes: {fix['num_fixes']} word-breaks")

    if args.dry_run:
        print("\n⚠️  DRY RUN - No changes made. Remove --dry-run to apply fixes.")
    else:
        print("\n✅ Word-break fixes complete!")

    return 0


if __name__ == "__main__":
    sys.exit(main())

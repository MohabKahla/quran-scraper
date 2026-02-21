#!/usr/bin/env python3
"""
Enhanced restoration script that handles:
1. Simple truncation - append missing content
2. Reordered/corrupted verses - replace with original
3. Junk character removal

Usage:
    python3 restore_missing_content_v2.py --language it-piccardo --dry-run
    python3 restore_missing_content_v2.py --language it-piccardo
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
    """Read verses from original format: "1. verse text" """
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


def read_formatted_verses(file_path: Path) -> Dict[int, List[Tuple[int, str]]]:
    """Read verses from formatted format, preserving line positions"""
    verse_parts = defaultdict(list)

    if not file_path.exists():
        return {}

    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            original_line = line
            line = line.strip()
            if not line or '\t' not in line:
                continue

            parts = line.split('\t', 1)
            if len(parts) != 2:
                continue

            verse_key, verse_text = parts
            match = re.match(r'(\d+)_(\d+)', verse_key)
            if not match:
                continue

            verse_num = int(match.group(1))
            split_num = int(match.group(2))

            verse_parts[verse_num].append((split_num, verse_text.strip(), line_num))

    return verse_parts


def normalize_text(text: str) -> str:
    """Normalize text for comparison"""
    text = re.sub(r'[\u200b\u200c\u200d\ufeff]', '', text)
    text = ' '.join(text.split())
    return text


def clean_junk(text: str) -> str:
    """Remove common junk patterns from corrupted text"""
    # Remove patterns like ". ." or ". . "
    text = re.sub(r'\s*\.\s+\.\s*', ' ', text)
    # Remove multiple spaces
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def analyze_corruption(original: str, formatted: str) -> Dict:
    """
    Analyze type and severity of corruption.

    Returns dict with:
        - type: 'ok', 'truncated', 'reordered', 'severely_corrupted'
        - similarity: float
        - has_junk: bool
        - missing_content: str
    """
    orig_norm = normalize_text(original)
    fmt_norm = normalize_text(formatted)

    similarity = difflib.SequenceMatcher(None, orig_norm, fmt_norm).ratio()

    # Check for junk patterns
    has_junk = bool(re.search(r'\.\s+\.', formatted))

    # Clean junk for better analysis
    fmt_cleaned = clean_junk(fmt_norm)

    if similarity >= 0.999:
        return {
            'type': 'ok',
            'similarity': similarity,
            'has_junk': False,
            'missing_content': ''
        }

    # Check if just truncated (formatted is prefix/substring of original)
    if fmt_cleaned in orig_norm and not has_junk:
        missing = orig_norm.replace(fmt_cleaned, '', 1).strip()
        return {
            'type': 'truncated',
            'similarity': similarity,
            'has_junk': False,
            'missing_content': missing
        }

    # Check if reordered (same words, different order)
    orig_words = set(orig_norm.split())
    fmt_words = set(fmt_cleaned.split())
    word_overlap = len(orig_words & fmt_words) / len(orig_words) if orig_words else 0

    if word_overlap > 0.8 and similarity < 0.95:
        return {
            'type': 'reordered',
            'similarity': similarity,
            'has_junk': has_junk,
            'missing_content': orig_norm  # Need to replace entirely
        }

    # Severely corrupted
    return {
        'type': 'severely_corrupted',
        'similarity': similarity,
        'has_junk': has_junk,
        'missing_content': orig_norm  # Need to replace entirely
    }


def split_text_intelligently(text: str, num_splits: int) -> List[str]:
    """
    Split text into num_splits parts, trying to break at sentence boundaries.
    """
    if num_splits <= 1:
        return [text]

    # Try to split at sentence boundaries (. ! ? followed by space and capital)
    sentences = re.split(r'([.!?]\s+)', text)

    # Recombine sentences with their punctuation
    full_sentences = []
    for i in range(0, len(sentences), 2):
        if i + 1 < len(sentences):
            full_sentences.append(sentences[i] + sentences[i + 1].strip())
        else:
            # Last sentence (no trailing punctuation separator)
            full_sentences.append(sentences[i])

    if len(full_sentences) >= num_splits:
        # Distribute sentences evenly across splits
        sentences_per_split = len(full_sentences) / num_splits
        splits = []
        current_split = []
        current_count = 0

        for sent in full_sentences:
            current_split.append(sent)
            current_count += 1
            if current_count >= sentences_per_split and len(splits) < num_splits - 1:
                splits.append(' '.join(current_split))
                current_split = []
                current_count = 0

        if current_split:
            splits.append(' '.join(current_split))

        return splits
    else:
        # Not enough sentences, just split by character count
        chars_per_split = len(text) // num_splits
        splits = []
        for i in range(num_splits):
            start = i * chars_per_split
            end = start + chars_per_split if i < num_splits - 1 else len(text)
            splits.append(text[start:end].strip())

        return splits


def restore_chapter(
    language: str,
    chapter: str,
    old_dir: Path,
    formatted_dir: Path,
    min_similarity: float = 0.0,
    dry_run: bool = False
) -> Dict:
    """Restore missing/corrupted content for a single chapter."""

    old_file = old_dir / language / f"{chapter}.txt"
    fmt_file = formatted_dir / language / f"{chapter}.txt"

    if not old_file.exists() or not fmt_file.exists():
        return {'skipped': True, 'reason': 'file_not_found'}

    original_verses = read_original_verses(old_file)
    formatted_verse_parts = read_formatted_verses(fmt_file)

    if not original_verses or not formatted_verse_parts:
        return {'skipped': True, 'reason': 'no_verses'}

    restorations = []

    for verse_num in sorted(set(original_verses.keys()) | set(formatted_verse_parts.keys())):
        if verse_num not in original_verses:
            continue

        if verse_num not in formatted_verse_parts:
            restorations.append({
                'verse': verse_num,
                'corruption_type': 'missing_verse',
                'action': 'NEEDS_MANUAL_FIX',
                'original': original_verses[verse_num][:100]
            })
            continue

        # Combine formatted parts
        parts = sorted(formatted_verse_parts[verse_num], key=lambda x: x[0])
        combined_formatted = ' '.join(text for _, text, _ in parts)

        # Analyze corruption
        analysis = analyze_corruption(
            original_verses[verse_num],
            combined_formatted
        )

        if analysis['similarity'] >= min_similarity and analysis['type'] == 'ok':
            continue

        restorations.append({
            'verse': verse_num,
            'corruption_type': analysis['type'],
            'similarity': analysis['similarity'],
            'has_junk': analysis['has_junk'],
            'num_splits': len(parts),
            'original_text': original_verses[verse_num],
            'formatted_text': combined_formatted,
            'first_line_num': parts[0][2] if parts else None
        })

    # Apply restorations if not dry run
    if restorations and not dry_run:
        # Backup original file
        backup_dir = Path('backups') / datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = backup_dir / language / f"{chapter}.txt"
        backup_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(fmt_file, backup_file)

        # Read all lines
        with open(fmt_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Apply restorations
        for restoration in restorations:
            if restoration['corruption_type'] == 'missing_verse':
                continue

            verse_num = restoration['verse']
            original_text = restoration['original_text']
            corruption_type = restoration['corruption_type']

            if corruption_type == 'truncated':
                # Simple append to last split
                verse_key = f"{verse_num:03d}"
                formatted_text = restoration['formatted_text']  # Use from restoration dict

                # Find and update last split
                for i in range(len(lines) - 1, -1, -1):
                    if lines[i].startswith(verse_key + '_'):
                        parts = lines[i].strip().split('\t', 1)
                        if len(parts) == 2:
                            current_text = parts[1]
                            # Append missing content
                            missing = original_text.replace(formatted_text, '', 1).strip()
                            if missing:
                                lines[i] = f"{parts[0]}\t{current_text} {missing}\n"
                        break

            elif corruption_type in ['reordered', 'severely_corrupted']:
                # Replace all splits with corrected version
                verse_key = f"{verse_num:03d}"
                num_splits = restoration['num_splits']

                # Split original intelligently
                new_splits = split_text_intelligently(original_text, num_splits)

                # Find all lines for this verse
                verse_line_indices = []
                for i, line in enumerate(lines):
                    if line.startswith(verse_key + '_'):
                        verse_line_indices.append(i)

                # Replace lines with new splits, mark extras for deletion
                lines_to_delete = []
                for idx, line_i in enumerate(verse_line_indices):
                    if idx < len(new_splits):
                        lines[line_i] = f"{verse_key}_{idx:02d}\t{new_splits[idx]}\n"
                    else:
                        # Extra line - mark for deletion
                        lines_to_delete.append(line_i)

                # Delete extra lines (in reverse order to preserve indices)
                for line_i in sorted(lines_to_delete, reverse=True):
                    del lines[line_i]

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
    """Restore all chapters for a language."""

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
                types = defaultdict(int)
                for r in result['restorations']:
                    types[r.get('corruption_type', 'unknown')] += 1
                type_str = ', '.join(f"{k}:{v}" for k, v in types.items())
                print(f"  ✓ Chapter {chapter_str}: {result['count']} restorations ({type_str})")
        elif verbose:
            print(f"  ✓ Chapter {chapter_str}: OK")

    return chapters_processed, total_restorations, all_restorations


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Enhanced restoration with corruption handling")
    parser.add_argument("--language", help="Language to restore")
    parser.add_argument("--all", action="store_true", help="Restore all languages")
    parser.add_argument("--dry-run", action="store_true", help="Preview without changes")
    parser.add_argument("--min-similarity", type=float, default=0.0)
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--old-dir", type=Path, default=Path("data/old-translations/ksu-translations"))
    parser.add_argument("--formatted-dir", type=Path, default=Path("data/ksu-translations-formatted"))

    args = parser.parse_args()

    if not args.language and not args.all:
        parser.error("Must specify either --language or --all")

    print("=" * 80)
    print("ENHANCED TRANSLATION RESTORATION (v2)")
    print("=" * 80)
    print(f"\nMode: {'DRY RUN' if args.dry_run else 'LIVE RESTORATION'}")
    print(f"Handles: truncation, reordering, junk removal")
    print()

    if args.language:
        languages = [args.language]
    else:
        languages = [d.name for d in args.formatted_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]
        languages.sort()

    total_restorations = 0
    all_restorations = []

    for i, language in enumerate(languages, 1):
        print(f"\n{'─' * 80}")
        print(f"[{i}/{len(languages)}] 📖 Processing: {language}")
        print(f"{'─' * 80}")

        chapters, restorations, restoration_list = restore_language(
            language, args.old_dir, args.formatted_dir,
            min_similarity=args.min_similarity, dry_run=args.dry_run, verbose=args.verbose
        )

        total_restorations += restorations
        all_restorations.extend(restoration_list)

        if restorations > 0:
            # Count by type
            by_type = defaultdict(int)
            for r in restoration_list:
                by_type[r.get('corruption_type', 'unknown')] += 1

            type_summary = ', '.join(f"{k}:{v}" for k, v in by_type.items())
            print(f"\n{'Would restore' if args.dry_run else 'Restored'} {restorations} verses ({type_summary})")
        else:
            print(f"\n✅ All verses OK")

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Languages: {len(languages)}")
    print(f"Total restorations: {total_restorations}")

    if all_restorations:
        by_type = defaultdict(int)
        for r in all_restorations:
            by_type[r.get('corruption_type', 'unknown')] += 1

        print("\nBy corruption type:")
        for ctype, count in sorted(by_type.items()):
            print(f"  {ctype}: {count}")

    if args.dry_run:
        print("\n⚠️  DRY RUN - No changes made. Remove --dry-run to apply fixes.")

    return 0


if __name__ == "__main__":
    sys.exit(main())

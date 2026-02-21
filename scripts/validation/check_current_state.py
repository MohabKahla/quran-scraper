#!/usr/bin/env python3
"""
Check current state of translations without making any changes.
Shows which verses would fail validation if processed.
"""

import argparse
from pathlib import Path
from collections import Counter
import re

def normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    text = re.sub(r'[^\w\s]', ' ', text.lower())
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def get_word_set(text: str) -> Counter:
    """Get word frequency counter from text."""
    normalized = normalize_text(text)
    return Counter(normalized.split())

def load_verse_file(file_path: Path) -> dict:
    """Load verses from a file."""
    verses = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('سُورَةُ'):
                    parts = line.split('\t', 1)
                    if len(parts) == 2:
                        verse_id, text = parts
                        verses[verse_id] = text
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
    return verses

def check_translation(translation_lang: str, arabic_dir: str = "data/chs-ar-final",
                     translations_dir: str = "data/ksu-translations-formatted",
                     verbose: bool = False):
    """Check current state of a translation."""

    arabic_path = Path(arabic_dir)
    translation_path = Path(translations_dir) / translation_lang

    if not translation_path.exists():
        print(f"❌ Translation not found: {translation_path}")
        return

    print(f"\n{'='*60}")
    print(f"Checking: {translation_lang}")
    print(f"{'='*60}\n")

    total_verses_with_splits = 0
    potential_issues = []
    checked_verses = set()

    # Check each chapter
    for chapter_file in sorted(translation_path.glob("*.txt")):
        if not chapter_file.stem.isdigit():
            continue

        chapter_num = int(chapter_file.stem)
        arabic_file = arabic_path / f"{chapter_num:03d}"

        if not arabic_file.exists():
            continue

        arabic_verses = load_verse_file(arabic_file)
        translation_verses = load_verse_file(chapter_file)

        # Find verses with splits
        verse_groups = {}
        for verse_id in arabic_verses.keys():
            match = re.match(r'(\d+)_(\d+)', verse_id)
            if match:
                verse_num = int(match.group(1))
                split_num = int(match.group(2))

                if verse_num not in verse_groups:
                    verse_groups[verse_num] = []
                verse_groups[verse_num].append((verse_id, split_num))

        # Check each verse group
        for verse_num, ids in verse_groups.items():
            # Only check verses with splits (has _01 or higher)
            has_splits = any(split_num > 0 for _, split_num in ids)
            if not has_splits:
                continue

            verse_key = f"{chapter_num:03d}_{verse_num:03d}"
            if verse_key in checked_verses:
                continue

            checked_verses.add(verse_key)
            total_verses_with_splits += 1

            # Get all Arabic and translation IDs for this verse
            arabic_ids = set(vid for vid, _ in ids)
            trans_ids = set(vid for vid in translation_verses.keys()
                          if vid.split('_')[0] == f"{verse_num:03d}")

            # Check 1: ID mismatch
            if arabic_ids != trans_ids:
                missing = arabic_ids - trans_ids
                extra = trans_ids - arabic_ids
                issue = {
                    'verse': verse_key,
                    'chapter': chapter_num,
                    'type': 'ID_MISMATCH',
                    'details': f"Missing IDs: {missing}, Extra IDs: {extra}" if missing or extra else ""
                }
                potential_issues.append(issue)
                continue

            # Check 2: Repetition (only significant repetitions)
            trans_texts = [translation_verses.get(vid, "") for vid, _ in sorted(ids, key=lambda x: x[1])]
            for i, text1 in enumerate(trans_texts):
                for j, text2 in enumerate(trans_texts[i+1:], start=i+1):
                    sentences1 = set([s.strip() for s in re.split(r'[.!?]', text1) if s.strip()])
                    sentences2 = set([s.strip() for s in re.split(r'[.!?]', text2) if s.strip()])
                    overlap = sentences1 & sentences2

                    # Filter out trivial repetitions
                    significant_overlap = []
                    for phrase in overlap:
                        # Skip if too short (punctuation, single words)
                        if len(phrase) < 3:
                            continue
                        # Skip if only punctuation/numbers
                        if re.match(r'^[\W\d]+$', phrase):
                            continue
                        # Skip very common short words
                        if phrase.lower() in ['the', 'and', 'a', 'an', 'or', 'but', 'in', 'on', 'at', 'to', 'for']:
                            continue
                        # Count words - need at least 3 words for it to be significant
                        word_count = len(phrase.split())
                        if word_count < 3:
                            continue

                        significant_overlap.append(phrase)

                    if significant_overlap:
                        issue = {
                            'verse': verse_key,
                            'chapter': chapter_num,
                            'type': 'REPETITION',
                            'details': f"Repeated phrases: {significant_overlap[:2]}"  # Show first 2
                        }
                        potential_issues.append(issue)
                        break

    # Print summary
    print(f"Total verses with splits: {total_verses_with_splits}")
    print(f"Potential issues found: {len(potential_issues)}\n")

    if potential_issues:
        print("Issues found:\n")
        for i, issue in enumerate(potential_issues, 1):
            print(f"{i}. {issue['verse']} (Chapter {issue['chapter']})")
            print(f"   Type: {issue['type']}")
            if issue['details']:
                print(f"   Details: {issue['details']}")

            # Show full verse text in verbose mode
            if verbose:
                chapter = issue['chapter']
                verse_num = int(issue['verse'].split('_')[1])
                chapter_file = translation_path / f"{chapter:03d}.txt"
                trans_verses = load_verse_file(chapter_file)

                print(f"   Verse text:")
                for vid in sorted(trans_verses.keys()):
                    if vid.startswith(f"{verse_num:03d}_"):
                        text_preview = trans_verses[vid][:100] + "..." if len(trans_verses[vid]) > 100 else trans_verses[vid]
                        print(f"      {vid}: {text_preview}")

            print()
    else:
        print("✅ No obvious issues detected!")
        print("   All verses with splits have matching IDs and no repetition.")

    return len(potential_issues)

def main():
    parser = argparse.ArgumentParser(description="Check current state of translations")
    parser.add_argument("--translation", required=True, help="Translation to check (e.g., es-navio)")
    parser.add_argument("--arabic-dir", default="data/chs-ar-final")
    parser.add_argument("--translations-dir", default="data/ksu-translations-formatted")
    parser.add_argument("-v", "--verbose", action="store_true", help="Show detailed verse text for issues")

    args = parser.parse_args()

    issues_count = check_translation(
        translation_lang=args.translation,
        arabic_dir=args.arabic_dir,
        translations_dir=args.translations_dir,
        verbose=args.verbose
    )

    print(f"\n{'='*60}")
    print("RECOMMENDATION:")
    print(f"{'='*60}")

    if issues_count == 0:
        print("✅ Translation looks good!")
        print("   No need to re-run alignment script.")
    else:
        print(f"⚠️  Found {issues_count} potential issues.")
        print("   Consider re-running with failures log:")
        print(f"\n   python3 fix_verse_alignments_with_retry.py \\")
        print(f"     --provider gemini \\")
        print(f"     --translation {args.translation}")
        print(f"\n   Failures will be logged to: logs/failures-{args.translation}.json")

if __name__ == "__main__":
    main()

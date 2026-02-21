#!/usr/bin/env python3
"""
Simple test for verse alignment detection without external dependencies.
"""

import os
import re
from pathlib import Path
from typing import Dict, List

def load_verse_file(file_path: Path) -> Dict[str, str]:
    """Load verses from a file into a dictionary."""
    verses = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('سُورَةُ'):  # Skip surah headers
                    # Split on tab
                    parts = line.split('\t', 1)
                    if len(parts) == 2:
                        verse_id, text = parts
                        verses[verse_id] = text
    except Exception as e:
        print(f"Error loading file {file_path}: {e}")
    return verses

def find_misaligned_verses(arabic_dir: str, translations_dir: str, translation_lang: str) -> List[Dict]:
    """Find all verses with yy>0 that might be misaligned."""
    misaligned = []
    translation_path = Path(translations_dir) / translation_lang

    if not translation_path.exists():
        print(f"Translation directory not found: {translation_path}")
        return misaligned

    print(f"Checking translation: {translation_path}")

    # Process each chapter
    for chapter_file in sorted(translation_path.glob("*.txt")):
        if not chapter_file.stem.isdigit():
            continue  # Skip non-numeric files like surah names
        chapter_num = int(chapter_file.stem)
        arabic_file = Path(arabic_dir) / f"{chapter_num:03d}"

        if not arabic_file.exists():
            print(f"Arabic reference not found: {arabic_file}")
            continue

        # Load Arabic reference
        arabic_verses = load_verse_file(arabic_file)
        translation_verses = load_verse_file(chapter_file)

        # Find verses with splits (yy>0)
        chapter_misaligned = 0
        for verse_id, trans_text in translation_verses.items():
            match = re.match(r'(\d+)_(\d+)', verse_id)
            if match:
                verse_num, split_num = int(match.group(1)), int(match.group(2))

                if split_num > 0:  # This is a split verse
                    arabic_text = arabic_verses.get(verse_id, "")
                    if arabic_text:
                        misaligned.append({
                            'verse_id': verse_id,
                            'chapter': chapter_num,
                            'verse_num': verse_num,
                            'split_num': split_num,
                            'arabic_text': arabic_text,
                            'translation_text': trans_text
                        })
                        chapter_misaligned += 1

        if chapter_misaligned > 0:
            print(f"  Chapter {chapter_num:03d}: {chapter_misaligned} split verses")

    return misaligned

def analyze_split_patterns(misaligned: List[Dict]):
    """Analyze the patterns in split verses."""
    print(f"\n=== Split Pattern Analysis ===")

    # Group by chapter
    by_chapter = {}
    for verse in misaligned:
        chapter = verse['chapter']
        if chapter not in by_chapter:
            by_chapter[chapter] = []
        by_chapter[chapter].append(verse)

    print(f"Split verses found in {len(by_chapter)} chapters")

    # Show examples from first few chapters
    for chapter in sorted(by_chapter.keys())[:3]:
        verses = by_chapter[chapter]
        print(f"\nChapter {chapter:03d} examples:")

        for verse in verses[:3]:  # Show first 3 from each chapter
            print(f"  {verse['verse_id']}")
            print(f"    AR: {verse['arabic_text'][:60]}...")
            print(f"    TR: {verse['translation_text'][:60]}...")

def main():
    print("=== Simple Verse Alignment Test ===\n")

    arabic_dir = "data/chs-ar-final"
    translations_dir = "data/ksu-translations-formatted"

    # Test with Spanish translation
    translation_lang = "es-navio"

    if not Path(arabic_dir).exists():
        print(f"Arabic directory not found: {arabic_dir}")
        return

    if not Path(translations_dir).exists():
        print(f"Translations directory not found: {translations_dir}")
        return

    print(f"Testing misalignment detection for {translation_lang}...")
    misaligned_verses = find_misaligned_verses(arabic_dir, translations_dir, translation_lang)

    if misaligned_verses:
        print(f"\nFound {len(misaligned_verses)} misaligned verses in total")
        analyze_split_patterns(misaligned_verses)
    else:
        print("No misaligned verses found!")

    print(f"\n=== Summary ===")
    print(f"Total verses needing alignment: {len(misaligned_verses)}")
    print(f"These verses have split markers (yy>0) and need semantic alignment with Arabic reference.")

    print(f"\nTo fix alignments:")
    print(f"1. Install dependencies: pip install -r requirements_alignment.txt")
    print(f"2. Get API key (OpenAI or Gemini)")
    print(f"3. Run: python3 fix_verse_alignments.py --provider openai --api-key YOUR_KEY --translation {translation_lang}")

if __name__ == "__main__":
    main()
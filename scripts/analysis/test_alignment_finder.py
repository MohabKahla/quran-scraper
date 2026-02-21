#!/usr/bin/env python3
"""
Test script to check the verse alignment finder without calling LLMs.
"""

import sys
from pathlib import Path
from fix_verse_alignments import VerseAlignmentFixer

def test_misalignment_detection():
    """Test finding misaligned verses in a translation."""

    # Create a dummy fixer (no API calls needed for detection)
    fixer = VerseAlignmentFixer(
        arabic_dir="data/chs-ar-final",
        translations_dir="data/ksu-translations-formatted",
        provider="openai",
        api_key="dummy"
    )

    # Test with Spanish translation
    translation_lang = "es-navio"

    print(f"Testing misalignment detection for {translation_lang}...")
    misaligned_verses = fixer.find_misaligned_verses(translation_lang)

    if misaligned_verses:
        print(f"Found {len(misaligned_verses)} misaligned verses:")

        # Show first few examples
        for i, verse in enumerate(misaligned_verses[:5]):
            print(f"\n{i+1}. Chapter {verse.chapter:03d}, Verse {verse.verse_num:03d}_{verse.split_num:02d}")
            print(f"   Arabic: {verse.arabic_text[:80]}...")
            print(f"   Translation: {verse.translation_text[:80]}...")

        if len(misaligned_verses) > 5:
            print(f"\n... and {len(misaligned_verses) - 5} more verses")
    else:
        print("No misaligned verses found!")

    return len(misaligned_verses)

def test_file_loading():
    """Test basic file loading functionality."""

    fixer = VerseAlignmentFixer(
        arabic_dir="data/chs-ar-final",
        translations_dir="data/ksu-translations-formatted",
        provider="openai",
        api_key="dummy"
    )

    # Test loading Arabic reference
    arabic_file = Path("chs-ar-final/002")
    if arabic_file.exists():
        arabic_verses = fixer._load_verse_file(arabic_file)
        print(f"Loaded {len(arabic_verses)} Arabic verses from chapter 2")

        # Count splits
        split_count = sum(1 for v_id in arabic_verses.keys() if v_id.endswith("_01") or v_id.endswith("_02"))
        print(f"Found {split_count} split verses in Arabic chapter 2")

    # Test loading translation
    trans_file = Path("data/ksu-translations-formatted/es-navio/002.txt")
    if trans_file.exists():
        trans_verses = fixer._load_verse_file(trans_file)
        print(f"Loaded {len(trans_verses)} translation verses from chapter 2")

        # Count splits
        split_count = sum(1 for v_id in trans_verses.keys() if v_id.endswith("_01") or v_id.endswith("_02"))
        print(f"Found {split_count} split verses in translation chapter 2")

if __name__ == "__main__":
    print("=== Verse Alignment Test ===\n")

    print("1. Testing file loading...")
    test_file_loading()

    print("\n2. Testing misalignment detection...")
    count = test_misalignment_detection()

    print(f"\nTest completed. Found {count} verses that need alignment fixing.")
    print("\nTo fix alignments, use:")
    print("python3 fix_verse_alignments.py --provider openai --api-key YOUR_KEY --translation es-navio")
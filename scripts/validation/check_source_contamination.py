#!/usr/bin/env python3
"""Check if Arabic text contamination exists in source files (not just AI alignment failures)."""

import json
import re
from pathlib import Path
from collections import defaultdict

def has_significant_arabic(text, threshold=10):
    """Check if text has significant Arabic character content."""
    # Arabic Unicode range
    arabic_chars = sum(1 for c in text if '\u0600' <= c <= '\u06FF')
    return arabic_chars >= threshold

def check_verse_for_contamination(verse_text, expected_script):
    """
    Check if a verse has unexpected Arabic contamination.
    Returns (is_contaminated, arabic_char_count, total_chars)
    """
    arabic_count = sum(1 for c in verse_text if '\u0600' <= c <= '\u06FF')
    total_chars = len(verse_text)

    # If it's not an Arabic translation, it shouldn't have significant Arabic
    if expected_script != 'arabic' and arabic_count > 10:
        return True, arabic_count, total_chars

    return False, arabic_count, total_chars

def get_translation_script(translation_code):
    """Determine expected script for a translation."""
    # Map translation codes to expected scripts
    script_map = {
        'bn-bengali': 'bengali',
        'bs-korkut': 'bosnian',
        'de-bo': 'german',
        'es-navio': 'spanish',
        'ha-gumi': 'hausa',
        'id-indonesian': 'indonesian',
        'it-piccardo': 'italian',
        'ku-asan': 'kurdish',  # Kurdish can use Arabic script, but mixed is suspicious
        'ml-abdulhameed': 'malayalam',
        'ms-basmeih': 'malay',
        'nl-siregar': 'dutch',
        'pr-tagi': 'persian',  # Persian uses Arabic script but should be distinguishable
        'pt-elhayek': 'portuguese',
        'ru-ku': 'russian',
    }
    return script_map.get(translation_code, 'unknown')

def analyze_source_files():
    """Analyze source translation files for Arabic contamination."""

    ksu_dir = Path('data/ksu-translations-formatted')
    logs_dir = Path('logs')

    # Load failure logs to cross-reference
    contamination_from_logs = defaultdict(set)

    for log_file in logs_dir.glob('failures-*.json'):
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            translation = data['translation']
            for failure in data['failures']:
                # Check if this failure involves Arabic contamination
                orig_splits = failure.get('original_translation_splits', {})
                for split_id, text in orig_splits.items():
                    if has_significant_arabic(text):
                        verse_key = failure['verse_key']
                        contamination_from_logs[translation].add(verse_key)
        except Exception as e:
            print(f"Error reading {log_file}: {e}")

    # Now check actual source files
    print("=" * 80)
    print("SOURCE FILE CONTAMINATION ANALYSIS")
    print("=" * 80)
    print("\nChecking translation source files for Arabic text contamination...\n")

    total_contaminated_verses = 0
    contamination_report = {}

    for translation_dir in sorted(ksu_dir.iterdir()):
        if not translation_dir.is_dir():
            continue

        translation_code = translation_dir.name
        expected_script = get_translation_script(translation_code)

        contaminated_verses = []

        # Check each chapter file
        for chapter_file in sorted(translation_dir.glob('*.txt')):
            # Skip surah name files
            if 'surah' in chapter_file.name.lower() or 'names' in chapter_file.name.lower():
                continue

            try:
                chapter_num = chapter_file.stem

                with open(chapter_file, 'r', encoding='utf-8') as f:
                    for line_num, line in enumerate(f, 1):
                        line = line.strip()
                        if not line:
                            continue

                        # Parse verse: format is "verse_id\ttext"
                        parts = line.split('\t', 1)
                        if len(parts) != 2:
                            continue

                        verse_id, verse_text = parts

                        # Check for contamination
                        is_contaminated, arabic_count, total_count = check_verse_for_contamination(
                            verse_text, expected_script
                        )

                        if is_contaminated:
                            # Extract verse number from verse_id (e.g., "002_00" -> 2)
                            match = re.match(r'(\d+)_(\d+)', verse_id)
                            if match:
                                verse_num = int(match.group(1))
                                verse_key = f"{chapter_num}_{verse_num:03d}"

                                contaminated_verses.append({
                                    'chapter': chapter_num,
                                    'verse_id': verse_id,
                                    'verse_key': verse_key,
                                    'line_num': line_num,
                                    'arabic_count': arabic_count,
                                    'total_count': total_count,
                                    'percentage': (arabic_count / total_count * 100) if total_count > 0 else 0,
                                    'text_preview': verse_text[:100]
                                })

            except Exception as e:
                print(f"Error reading {chapter_file}: {e}")

        if contaminated_verses:
            contamination_report[translation_code] = contaminated_verses
            total_contaminated_verses += len(contaminated_verses)

            print(f"\n{translation_code}: {len(contaminated_verses)} contaminated verses")
            print(f"  Expected script: {expected_script}")

            # Show first few examples
            for verse in contaminated_verses[:3]:
                print(f"  • {verse['verse_key']} (file: {verse['chapter']}.txt, line {verse['line_num']})")
                print(f"    Arabic: {verse['arabic_count']}/{verse['total_count']} chars ({verse['percentage']:.1f}%)")
                print(f"    Preview: {verse['text_preview'][:80]}...")

            if len(contaminated_verses) > 3:
                print(f"  ... and {len(contaminated_verses) - 3} more")

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"\nTotal translations with contamination: {len(contamination_report)}")
    print(f"Total contaminated verses: {total_contaminated_verses}\n")

    # Compare with failure logs
    print("Contamination breakdown:")
    print(f"{'Translation':<25} {'Source File':>15} {'Failure Log':>15} {'Match':>10}")
    print("-" * 80)

    all_translations = set(contamination_report.keys()) | set(contamination_from_logs.keys())
    for translation in sorted(all_translations):
        source_count = len(contamination_report.get(translation, []))
        log_count = len(contamination_from_logs.get(translation, set()))
        match = "✓" if source_count > 0 and log_count > 0 else ""

        print(f"{translation:<25} {source_count:>15} {log_count:>15} {match:>10}")

    print("\n" + "=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    print("\n1. RE-SCRAPE REQUIRED: Translations with source file contamination")
    print("   These have bad data in the original scraped files and need to be re-scraped:")

    for translation, verses in sorted(contamination_report.items()):
        print(f"   • {translation}: {len(verses)} verses")

    print("\n2. Files that need manual fixing:")
    print("   Run this to see specific files that need attention:\n")

    for translation, verses in sorted(contamination_report.items()):
        affected_chapters = sorted(set(v['chapter'] for v in verses))
        print(f"   {translation}:")
        for chapter in affected_chapters:
            chapter_verses = [v for v in verses if v['chapter'] == chapter]
            print(f"     • data/ksu-translations-formatted/{translation}/{chapter}.txt ({len(chapter_verses)} verses)")

    print("\n" + "=" * 80)

    return contamination_report

if __name__ == '__main__':
    results = analyze_source_files()

#!/usr/bin/env python3
"""Check for ACTUAL Arabic text contamination - excluding languages that legitimately use Arabic script."""

import json
import re
from pathlib import Path
from collections import defaultdict

def get_translation_script(translation_code):
    """Determine expected script for a translation."""
    # Languages that LEGITIMATELY use Arabic script
    arabic_script_languages = {
        'ku-asan',      # Kurdish (Sorani) - uses Arabic script
        'pr-tagi',      # Persian/Farsi - uses Arabic script
        'ur-gl',        # Urdu - uses Arabic script (Nastaliq)
        # Add any others that use Arabic script
    }

    # Map translation codes to expected scripts for NON-Arabic script languages
    latin_script = {
        'bs-korkut',      # Bosnian
        'de-bo',          # German
        'es-navio',       # Spanish
        'ha-gumi',        # Hausa
        'id-indonesian',  # Indonesian
        'it-piccardo',    # Italian
        'ms-basmeih',     # Malay
        'nl-siregar',     # Dutch
        'pt-elhayek',     # Portuguese
        'sq-nahi',        # Albanian
        'sv-bernstrom',   # Swedish
    }

    other_scripts = {
        'bn-bengali': 'bengali',
        'ml-abdulhameed': 'malayalam',
        'ru-ku': 'cyrillic',
        'ta-tamil': 'tamil',
        'th-thai': 'thai',
    }

    if translation_code in arabic_script_languages:
        return 'arabic_script_legitimate'
    elif translation_code in latin_script:
        return 'latin'
    else:
        return other_scripts.get(translation_code, 'unknown')

def has_significant_arabic(text, threshold=10):
    """Check if text has significant Arabic character content."""
    arabic_chars = sum(1 for c in text if '\u0600' <= c <= '\u06FF')
    return arabic_chars >= threshold

def analyze_real_contamination():
    """Analyze only ACTUAL contamination (excluding legitimate Arabic-script languages)."""

    ksu_dir = Path('data/ksu-translations-formatted')
    logs_dir = Path('logs')

    print("=" * 80)
    print("REAL CONTAMINATION ANALYSIS")
    print("=" * 80)
    print("\nExcluding: Persian (pr-tagi), Kurdish (ku-asan), Urdu (ur-gl)")
    print("These languages legitimately use Arabic script.\n")

    total_contaminated = 0
    contamination_by_translation = {}

    for translation_dir in sorted(ksu_dir.iterdir()):
        if not translation_dir.is_dir():
            continue

        translation_code = translation_dir.name
        expected_script = get_translation_script(translation_code)

        # Skip languages that legitimately use Arabic script
        if expected_script == 'arabic_script_legitimate':
            continue

        contaminated_verses = []

        for chapter_file in sorted(translation_dir.glob('*.txt')):
            if 'surah' in chapter_file.name.lower() or 'names' in chapter_file.name.lower():
                continue

            try:
                chapter_num = chapter_file.stem

                with open(chapter_file, 'r', encoding='utf-8') as f:
                    for line_num, line in enumerate(f, 1):
                        line = line.strip()
                        if not line:
                            continue

                        parts = line.split('\t', 1)
                        if len(parts) != 2:
                            continue

                        verse_id, verse_text = parts

                        # Check for Arabic contamination
                        if has_significant_arabic(verse_text):
                            arabic_count = sum(1 for c in verse_text if '\u0600' <= c <= '\u06FF')
                            total_count = len(verse_text)

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
                                    'percentage': (arabic_count / total_count * 100),
                                    'text_preview': verse_text[:100]
                                })

            except Exception as e:
                print(f"Error reading {chapter_file}: {e}")

        if contaminated_verses:
            contamination_by_translation[translation_code] = contaminated_verses
            total_contaminated += len(contaminated_verses)

            print(f"\n{translation_code}: {len(contaminated_verses)} contaminated verses")
            print(f"  Expected script: {expected_script}")

            for verse in contaminated_verses[:5]:
                print(f"  • {verse['verse_key']} (Ch {verse['chapter']}, line {verse['line_num']})")
                print(f"    Arabic: {verse['arabic_count']}/{verse['total_count']} chars ({verse['percentage']:.1f}%)")
                print(f"    Preview: {verse['text_preview'][:80]}...")

            if len(contaminated_verses) > 5:
                print(f"  ... and {len(contaminated_verses) - 5} more")

    print("\n" + "=" * 80)
    print("SUMMARY OF REAL CONTAMINATION")
    print("=" * 80)
    print(f"\nTotal translations with contamination: {len(contamination_by_translation)}")
    print(f"Total contaminated verses: {total_contaminated}\n")

    if contamination_by_translation:
        print("Translations that need fixing:")
        for translation, verses in sorted(contamination_by_translation.items(), key=lambda x: len(x[1]), reverse=True):
            print(f"  • {translation}: {len(verses)} verses")

        print("\n" + "=" * 80)
        print("ACTION REQUIRED")
        print("=" * 80)
        print("\nThese translations have Arabic text where they shouldn't.")
        print("They need to be:")
        print("  1. Re-scraped with correct translation IDs, OR")
        print("  2. Manually corrected in the source files\n")

        for translation, verses in sorted(contamination_by_translation.items()):
            affected_chapters = sorted(set(v['chapter'] for v in verses))
            print(f"\n{translation}: {len(affected_chapters)} chapters affected")
            for chapter in affected_chapters[:10]:
                chapter_verses = [v for v in verses if v['chapter'] == chapter]
                print(f"  data/ksu-translations-formatted/{translation}/{chapter}.txt ({len(chapter_verses)} verses)")
            if len(affected_chapters) > 10:
                print(f"  ... and {len(affected_chapters) - 10} more chapters")
    else:
        print("\n✓ No contamination found in non-Arabic-script translations!")

    print("\n" + "=" * 80)

    return contamination_by_translation

if __name__ == '__main__':
    results = analyze_real_contamination()

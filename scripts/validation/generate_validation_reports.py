#!/usr/bin/env python3
"""
Generate comprehensive validation reports for all translations.

Creates a nested directory structure under logs/ with detailed reports:
- logs/validation-reports/TIMESTAMP/
  - summary.txt (overall statistics)
  - by-language/
    - bn-bengali.txt (detailed per-language report)
    - it-piccardo.txt
    - ...
  - by-severity/
    - critical.txt (<80% similarity)
    - moderate.txt (80-95% similarity)
    - minor.txt (95-99% similarity)
    - trivial.txt (>99% similarity)
  - validation-data.json (machine-readable data)

Usage:
    python3 generate_validation_reports.py
    python3 generate_validation_reports.py --languages bn-bengali it-piccardo
    python3 generate_validation_reports.py --verbose
"""

import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Tuple


def run_validation(language: str, old_dir: Path, formatted_dir: Path) -> Dict:
    """
    Run validation for a single language using compare_formatted_vs_original.py

    Returns validation data for the language.
    """
    print(f"  Validating {language}...", end='', flush=True)

    # Run validation with JSON output
    json_output = Path(f'logs/temp_validation_{language}.json')

    try:
        result = subprocess.run(
            [
                'python3',
                'scripts/validation/compare_formatted_vs_original.py',
                '--language', language,
                '--old-dir', str(old_dir),
                '--formatted-dir', str(formatted_dir),
                '--json-output', str(json_output)
            ],
            capture_output=True,
            text=True,
            timeout=300
        )

        # Read JSON output
        if json_output.exists():
            with open(json_output, 'r', encoding='utf-8') as f:
                data = json.load(f)
            json_output.unlink()  # Clean up temp file
            print(" ✓")
            return data
        else:
            print(" ⚠️  (no output)")
            return {'summary': {}, 'mismatches': []}

    except subprocess.TimeoutExpired:
        print(" ⚠️  (timeout)")
        return {'summary': {}, 'mismatches': []}
    except Exception as e:
        print(f" ⚠️  ({str(e)})")
        return {'summary': {}, 'mismatches': []}


def categorize_by_severity(mismatches: List[Dict]) -> Dict[str, List[Dict]]:
    """Categorize mismatches by severity based on similarity."""
    categories = {
        'critical': [],    # <80%
        'moderate': [],    # 80-95%
        'minor': [],       # 95-99%
        'trivial': []      # >99%
    }

    for mismatch in mismatches:
        similarity = mismatch.get('similarity', 0)

        if similarity < 0.80:
            categories['critical'].append(mismatch)
        elif similarity < 0.95:
            categories['moderate'].append(mismatch)
        elif similarity < 0.99:
            categories['minor'].append(mismatch)
        else:
            categories['trivial'].append(mismatch)

    return categories


def write_summary_report(report_dir: Path, all_data: Dict[str, Dict], languages: List[str]):
    """Write overall summary report."""
    summary_file = report_dir / 'summary.txt'

    total_languages = len(languages)
    languages_with_issues = sum(1 for lang in languages if all_data[lang]['summary'].get('total_mismatches', 0) > 0)
    total_mismatches = sum(data['summary'].get('total_mismatches', 0) for data in all_data.values())

    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("QURAN TRANSLATION VALIDATION REPORT\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Report location: {report_dir}\n\n")

        f.write("=" * 80 + "\n")
        f.write("OVERALL SUMMARY\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Total languages validated: {total_languages}\n")
        f.write(f"Languages with issues: {languages_with_issues}\n")
        f.write(f"Languages perfect: {total_languages - languages_with_issues}\n")
        f.write(f"Total mismatches across all languages: {total_mismatches}\n\n")

        f.write("=" * 80 + "\n")
        f.write("BY LANGUAGE\n")
        f.write("=" * 80 + "\n\n")

        # Sort by mismatch count
        sorted_langs = sorted(
            languages,
            key=lambda l: all_data[l]['summary'].get('total_mismatches', 0),
            reverse=True
        )

        for lang in sorted_langs:
            data = all_data[lang]
            mismatches = data['summary'].get('total_mismatches', 0)

            if mismatches == 0:
                f.write(f"✅ {lang:30s} - Perfect\n")
            else:
                # Categorize
                by_severity = categorize_by_severity(data.get('mismatches', []))
                f.write(f"❌ {lang:30s} - {mismatches:4d} issues ")
                f.write(f"(critical:{len(by_severity['critical'])} ")
                f.write(f"moderate:{len(by_severity['moderate'])} ")
                f.write(f"minor:{len(by_severity['minor'])} ")
                f.write(f"trivial:{len(by_severity['trivial'])})\n")

        f.write("\n" + "=" * 80 + "\n")
        f.write("RECOMMENDED ACTIONS\n")
        f.write("=" * 80 + "\n\n")
        f.write("1. Review critical issues (see by-severity/critical.txt)\n")
        f.write("2. Run restoration script:\n")
        f.write("   python3 scripts/alignment/restore_missing_content_v2.py --all\n\n")
        f.write("3. Run word-break fixer for minor issues:\n")
        f.write("   python3 scripts/alignment/fix_word_breaks.py --all\n\n")
        f.write("4. Re-validate:\n")
        f.write("   python3 scripts/validation/generate_validation_reports.py\n\n")


def write_language_report(report_dir: Path, language: str, data: Dict):
    """Write detailed report for a single language."""
    lang_dir = report_dir / 'by-language'
    lang_dir.mkdir(exist_ok=True)

    lang_file = lang_dir / f"{language}.txt"

    mismatches = data.get('mismatches', [])
    summary = data.get('summary', {})

    with open(lang_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write(f"VALIDATION REPORT: {language}\n")
        f.write("=" * 80 + "\n\n")

        total = summary.get('total_mismatches', 0)

        if total == 0:
            f.write("✅ All verses match perfectly!\n")
            return

        f.write(f"Total mismatches: {total}\n\n")

        # Categorize by severity
        by_severity = categorize_by_severity(mismatches)

        f.write("By severity:\n")
        f.write(f"  Critical (<80%):  {len(by_severity['critical'])}\n")
        f.write(f"  Moderate (80-95%): {len(by_severity['moderate'])}\n")
        f.write(f"  Minor (95-99%):   {len(by_severity['minor'])}\n")
        f.write(f"  Trivial (>99%):   {len(by_severity['trivial'])}\n\n")

        # Group by chapter
        by_chapter = defaultdict(list)
        for m in mismatches:
            by_chapter[m['chapter']].append(m)

        f.write("=" * 80 + "\n")
        f.write("ISSUES BY CHAPTER\n")
        f.write("=" * 80 + "\n\n")

        for chapter in sorted(by_chapter.keys()):
            chapter_mismatches = by_chapter[chapter]
            f.write(f"\nChapter {chapter}: {len(chapter_mismatches)} issues\n")
            f.write("-" * 80 + "\n")

            for m in chapter_mismatches[:10]:  # Show first 10 per chapter
                f.write(f"\nVerse {m['verse']:03d} - Similarity: {m['similarity']:.1%}\n")

                if m.get('missing_in_formatted'):
                    f.write("  ⚠️  VERSE MISSING IN FORMATTED VERSION\n")
                elif m.get('missing_in_original'):
                    f.write("  ⚠️  VERSE MISSING IN ORIGINAL VERSION\n")

                f.write(f"  Original ({len(m['original_text'])} chars):\n")
                f.write(f"    {m['original_text'][:100]}...\n")
                f.write(f"  Formatted ({len(m['formatted_text'])} chars):\n")
                f.write(f"    {m['formatted_text'][:100]}...\n")

            if len(chapter_mismatches) > 10:
                f.write(f"\n  ... and {len(chapter_mismatches) - 10} more issues in this chapter\n")


def write_severity_reports(report_dir: Path, all_data: Dict[str, Dict]):
    """Write reports grouped by severity."""
    severity_dir = report_dir / 'by-severity'
    severity_dir.mkdir(exist_ok=True)

    # Collect all mismatches across languages
    all_mismatches = []
    for language, data in all_data.items():
        for m in data.get('mismatches', []):
            m['language'] = language
            all_mismatches.append(m)

    # Categorize
    by_severity = categorize_by_severity(all_mismatches)

    # Write each severity level
    for severity, mismatches in by_severity.items():
        if not mismatches:
            continue

        severity_file = severity_dir / f"{severity}.txt"

        with open(severity_file, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write(f"{severity.upper()} ISSUES\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Total: {len(mismatches)} issues\n\n")

            # Group by language
            by_lang = defaultdict(list)
            for m in mismatches:
                by_lang[m['language']].append(m)

            for language in sorted(by_lang.keys()):
                lang_mismatches = by_lang[language]
                f.write(f"\n{language}: {len(lang_mismatches)} issues\n")
                f.write("-" * 80 + "\n")

                for m in lang_mismatches[:5]:  # Show first 5 per language
                    f.write(f"\nChapter {m['chapter']}, Verse {m['verse']:03d} ")
                    f.write(f"- Similarity: {m['similarity']:.1%}\n")
                    f.write(f"  Original: {m['original_text'][:80]}...\n")
                    f.write(f"  Formatted: {m['formatted_text'][:80]}...\n")

                if len(lang_mismatches) > 5:
                    f.write(f"\n  ... and {len(lang_mismatches) - 5} more\n")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Generate validation reports")
    parser.add_argument(
        "--languages",
        nargs='+',
        help="Specific languages to validate (default: all)"
    )
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument(
        "--old-dir",
        type=Path,
        default=Path("data/old-translations/ksu-translations")
    )
    parser.add_argument(
        "--formatted-dir",
        type=Path,
        default=Path("data/ksu-translations-formatted")
    )

    args = parser.parse_args()

    print("=" * 80)
    print("VALIDATION REPORT GENERATOR")
    print("=" * 80)
    print()

    # Determine languages
    if args.languages:
        languages = args.languages
    else:
        languages = [
            d.name for d in args.formatted_dir.iterdir()
            if d.is_dir() and not d.name.startswith('.')
        ]
        languages.sort()

    print(f"Languages to validate: {len(languages)}\n")

    # Create report directory
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_dir = Path('logs') / 'validation-reports' / timestamp
    report_dir.mkdir(parents=True, exist_ok=True)

    print(f"Report directory: {report_dir}\n")
    print("=" * 80)
    print("RUNNING VALIDATIONS")
    print("=" * 80)

    # Run validation for each language
    all_data = {}
    for language in languages:
        data = run_validation(language, args.old_dir, args.formatted_dir)
        all_data[language] = data

    print("\n" + "=" * 80)
    print("GENERATING REPORTS")
    print("=" * 80)
    print()

    # Write summary report
    print("  Writing summary report...")
    write_summary_report(report_dir, all_data, languages)

    # Write per-language reports
    print("  Writing per-language reports...")
    for language, data in all_data.items():
        write_language_report(report_dir, language, data)

    # Write severity reports
    print("  Writing severity reports...")
    write_severity_reports(report_dir, all_data)

    # Write JSON data
    print("  Writing machine-readable data...")
    json_file = report_dir / 'validation-data.json'
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 80)
    print("REPORT GENERATION COMPLETE")
    print("=" * 80)
    print(f"\nReports saved to: {report_dir}")
    print("\nAvailable reports:")
    print(f"  - summary.txt (overall statistics)")
    print(f"  - by-language/*.txt (detailed per-language)")
    print(f"  - by-severity/*.txt (grouped by issue severity)")
    print(f"  - validation-data.json (machine-readable data)")
    print()

    # Print quick stats
    total_mismatches = sum(data['summary'].get('total_mismatches', 0) for data in all_data.values())
    languages_with_issues = sum(1 for data in all_data.values() if data['summary'].get('total_mismatches', 0) > 0)

    print("Quick summary:")
    print(f"  Languages validated: {len(languages)}")
    print(f"  Languages with issues: {languages_with_issues}")
    print(f"  Total mismatches: {total_mismatches}")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())

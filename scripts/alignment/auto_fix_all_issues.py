#!/usr/bin/env python3
"""
Automated fix for all translation issues:
1. Remove Arabic contamination from source files
2. Re-run AI alignment for problematic translations
3. Validate all fixes
"""

import re
import shutil
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import subprocess
import sys

class TeeLogger:
    """Logger that outputs to both file and console."""
    def __init__(self, log_file):
        self.log_file = log_file
        self.terminal = sys.stdout

    def write(self, message):
        self.terminal.write(message)
        self.log_file.write(message)
        self.log_file.flush()

    def flush(self):
        self.terminal.flush()
        self.log_file.flush()

def setup_logging():
    """Setup logging to both file and console."""
    logs_dir = Path('logs')
    logs_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file_path = logs_dir / f'auto_fix_run_{timestamp}.log'

    # Create log file
    log_file = open(log_file_path, 'w', encoding='utf-8')

    # Redirect stdout to both console and file
    tee = TeeLogger(log_file)
    sys.stdout = tee

    print(f"Logging to: {log_file_path}")
    print("=" * 80)

    return log_file_path, log_file

def has_significant_arabic(text, threshold=10):
    """Check if text has significant Arabic character content."""
    arabic_chars = sum(1 for c in text if '\u0600' <= c <= '\u06FF')
    return arabic_chars >= threshold

def get_translation_script(translation_code):
    """Determine if translation should NOT have Arabic script."""
    # Languages that legitimately use Arabic script (skip these)
    arabic_script_languages = {'ku-asan', 'pr-tagi', 'ur-gl'}

    if translation_code in arabic_script_languages:
        return 'arabic_script_legitimate'
    return 'other'

def remove_arabic_contamination():
    """Remove Arabic text contamination from source files."""

    print("\n" + "=" * 80)
    print("STEP 1: REMOVING ARABIC CONTAMINATION FROM SOURCE FILES")
    print("=" * 80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    ksu_dir = Path('data/ksu-translations-formatted')
    backup_dir = Path('backups') / datetime.now().strftime('%Y%m%d_%H%M%S')

    # Create backup
    print(f"\nCreating backup at: {backup_dir}")
    backup_dir.mkdir(parents=True, exist_ok=True)

    fixes_made = defaultdict(list)
    total_removed = 0

    for translation_dir in sorted(ksu_dir.iterdir()):
        if not translation_dir.is_dir():
            continue

        translation_code = translation_dir.name
        expected_script = get_translation_script(translation_code)

        # Skip languages that legitimately use Arabic script
        if expected_script == 'arabic_script_legitimate':
            continue

        for chapter_file in sorted(translation_dir.glob('*.txt')):
            if 'surah' in chapter_file.name.lower() or 'names' in chapter_file.name.lower():
                continue

            # Backup original file
            backup_file = backup_dir / translation_code / chapter_file.name
            backup_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(chapter_file, backup_file)

            # Read and process file
            lines_to_keep = []
            removed_lines = []

            with open(chapter_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    original_line = line
                    line = line.strip()

                    if not line:
                        lines_to_keep.append(original_line)
                        continue

                    parts = line.split('\t', 1)
                    if len(parts) != 2:
                        lines_to_keep.append(original_line)
                        continue

                    verse_id, verse_text = parts

                    # Check for Arabic contamination
                    if has_significant_arabic(verse_text):
                        arabic_count = sum(1 for c in verse_text if '\u0600' <= c <= '\u06FF')
                        total_count = len(verse_text)
                        percentage = (arabic_count / total_count * 100) if total_count > 0 else 0

                        # If mostly Arabic (>50%), remove this line
                        if percentage > 50:
                            removed_lines.append({
                                'line_num': line_num,
                                'verse_id': verse_id,
                                'text': verse_text[:100]
                            })
                            total_removed += 1
                            # Skip this line (don't add to lines_to_keep)
                            continue
                        else:
                            # Try to clean partial contamination
                            # Remove Arabic text but keep rest
                            cleaned = re.sub(r'[\u0600-\u06FF\s]+', ' ', verse_text)
                            cleaned = re.sub(r'\s+', ' ', cleaned).strip()

                            if cleaned and len(cleaned) > 10:
                                lines_to_keep.append(f"{verse_id}\t{cleaned}\n")
                                removed_lines.append({
                                    'line_num': line_num,
                                    'verse_id': verse_id,
                                    'text': f"CLEANED: {verse_text[:80]}...",
                                    'cleaned_to': cleaned[:80]
                                })
                            else:
                                # Cleaning removed everything, skip line
                                removed_lines.append({
                                    'line_num': line_num,
                                    'verse_id': verse_id,
                                    'text': verse_text[:100]
                                })
                                total_removed += 1
                                continue
                    else:
                        lines_to_keep.append(original_line)

            # Write cleaned file if changes were made
            if removed_lines:
                with open(chapter_file, 'w', encoding='utf-8') as f:
                    f.writelines(lines_to_keep)

                fixes_made[translation_code].extend([
                    f"  {chapter_file.name} - Line {r['line_num']}: {r['verse_id']}"
                    for r in removed_lines
                ])

    # Report
    print(f"\n{'=' * 80}")
    print(f"STEP 1 COMPLETE - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'=' * 80}")
    print(f"Removed/cleaned: {total_removed} contaminated verses")
    print(f"Translations affected: {len(fixes_made)}")

    if fixes_made:
        print("\nDetailed fixes by translation:")
        for translation, lines in sorted(fixes_made.items()):
            print(f"\n{translation}: {len(lines)} verses fixed")
            for line in lines[:10]:
                print(line)
            if len(lines) > 10:
                print(f"  ... and {len(lines) - 10} more")

    print(f"\nBackup location: {backup_dir}")

    return fixes_made

def fix_alignment_issues():
    """Re-run alignment for translations with high failure counts."""

    print("\n" + "=" * 80)
    print("STEP 2: FIXING AI ALIGNMENT ISSUES")
    print("=" * 80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Check if we have OPENAI_API_KEY
    import os
    api_key = os.environ.get('OPENAI_API_KEY')

    if not api_key:
        print("\n⚠️  OPENAI_API_KEY not found in environment")
        print("Skipping AI alignment fixes")
        print("\nTo fix alignment issues, set OPENAI_API_KEY and run:")
        print("  export OPENAI_API_KEY='your-key-here'")
        print("  python3 auto_fix_all_issues.py --alignment-only")
        return

    # High-priority translations (>50 failures)
    high_priority = [
        'pt-elhayek',  # 281 failures
        'nl-siregar',  # 74 failures
        'ml-abdulhameed',  # 73 failures
        'es-navio',  # 66 failures
        'de-bo',  # 52 failures
        'ms-basmeih',  # 51 failures
    ]

    print(f"\nFixing {len(high_priority)} translations with >50 alignment failures\n")

    successes = []
    failures = []

    for i, translation in enumerate(high_priority, 1):
        print(f"\n[{i}/{len(high_priority)}] Processing {translation}...")
        print(f"Time: {datetime.now().strftime('%H:%M:%S')}")

        try:
            result = subprocess.run([
                'python3', 'fix_verse_alignments_with_retry.py',
                '--provider', 'openai',
                '--api-key', api_key,
                '--translation', translation,
                '--max-retries', '3',
                '--failures-log', f'logs/failures-{translation}-FIXED.json'
            ], capture_output=True, text=True, timeout=1800)

            if result.returncode == 0:
                print(f"✓ {translation} completed successfully")
                successes.append(translation)
                # Show last few lines of output
                if result.stdout:
                    lines = result.stdout.strip().split('\n')
                    print("  Last output:")
                    for line in lines[-3:]:
                        print(f"    {line}")
            else:
                print(f"⚠️  {translation} had errors:")
                failures.append(translation)
                if result.stderr:
                    print("  Error output:")
                    for line in result.stderr[:500].split('\n'):
                        print(f"    {line}")

        except subprocess.TimeoutExpired:
            print(f"⚠️  {translation} timed out (>1 hour)")
            failures.append(f"{translation} (timeout)")
        except FileNotFoundError:
            print(f"⚠️  fix_verse_alignments_with_retry.py not found")
            print("Skipping remaining alignment fixes")
            return
        except Exception as e:
            print(f"⚠️  {translation} failed: {e}")
            failures.append(f"{translation} ({str(e)})")

    # Summary
    print(f"\n{'=' * 80}")
    print(f"STEP 2 COMPLETE - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'=' * 80}")
    print(f"Successful: {len(successes)}/{len(high_priority)}")
    if successes:
        print("  ✓ " + ", ".join(successes))
    if failures:
        print(f"Failed: {len(failures)}/{len(high_priority)}")
        print("  ✗ " + ", ".join(failures))

def validate_fixes():
    """Validate all fixes."""

    print("\n" + "=" * 80)
    print("STEP 3: VALIDATING FIXES")
    print("=" * 80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    print("\nRunning contamination check...")
    try:
        result = subprocess.run(
            ['python3', 'check_real_contamination.py'],
            capture_output=True,
            text=True,
            timeout=300
        )

        # Extract summary
        output = result.stdout
        if 'Total contaminated verses:' in output:
            for line in output.split('\n'):
                if 'Total contaminated verses:' in line:
                    print(f"\n{line}")
                    break
        else:
            print(output[-500:])  # Last 500 chars

    except Exception as e:
        print(f"⚠️  Validation check failed: {e}")

    print("\nRunning alignment failure analysis...")
    try:
        result = subprocess.run(
            ['python3', 'analyze_failures.py'],
            capture_output=True,
            text=True,
            timeout=300
        )

        output = result.stdout
        if 'Total failures across all translations:' in output:
            for line in output.split('\n'):
                if 'Total failures' in line or 'Translation' in line:
                    print(line)

    except Exception as e:
        print(f"⚠️  Failure analysis failed: {e}")

    print(f"\n{'=' * 80}")
    print(f"STEP 3 COMPLETE - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'=' * 80}")

def generate_report(fixes_made):
    """Generate final fix report."""

    print("\n" + "=" * 80)
    print("FINAL REPORT")
    print("=" * 80)

    report_file = Path('logs') / f'auto_fix_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
    report_file.parent.mkdir(exist_ok=True)

    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(f"Automated Fix Report\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write("=" * 80 + "\n\n")

        f.write("SOURCE FILE FIXES:\n")
        f.write("-" * 80 + "\n")
        if fixes_made:
            for translation, lines in sorted(fixes_made.items()):
                f.write(f"\n{translation}: {len(lines)} verses cleaned\n")
                for line in lines:
                    f.write(f"{line}\n")
        else:
            f.write("No source file contamination found\n")

        f.write("\n" + "=" * 80 + "\n")
        f.write("\nFor alignment fixes, check:\n")
        f.write("  logs/failures-*-FIXED.json\n")

    print(f"\nDetailed report saved to: {report_file}")
    print("\nFix complete! Next steps:")
    print("  1. Review logs/auto_fix_report_*.txt")
    print("  2. Check logs/failures-*-FIXED.json for alignment improvements")
    print("  3. Run: git diff to see all changes")
    print("  4. Commit fixes if satisfied")

def main():
    """Main execution."""

    import argparse
    parser = argparse.ArgumentParser(description='Automatically fix all translation issues')
    parser.add_argument('--alignment-only', action='store_true',
                       help='Only fix alignment issues, skip contamination cleanup')
    parser.add_argument('--no-alignment', action='store_true',
                       help='Only fix contamination, skip alignment fixes')
    parser.add_argument('--no-validate', action='store_true',
                       help='Skip validation step')

    args = parser.parse_args()

    # Setup logging
    log_file_path, log_file = setup_logging()

    print("=" * 80)
    print("AUTOMATED FIX FOR ALL TRANSLATION ISSUES")
    print("=" * 80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Mode: {'Alignment only' if args.alignment_only else 'Contamination only' if args.no_alignment else 'Full fix'}")
    print("=" * 80)

    start_time = datetime.now()
    fixes_made = {}

    if not args.alignment_only:
        fixes_made = remove_arabic_contamination()
    else:
        print("\nSkipping contamination cleanup (--alignment-only)")

    if not args.no_alignment:
        fix_alignment_issues()
    else:
        print("\nSkipping alignment fixes (--no-alignment)")

    if not args.no_validate:
        validate_fixes()
    else:
        print("\nSkipping validation (--no-validate)")

    generate_report(fixes_made)

    end_time = datetime.now()
    duration = end_time - start_time

    print("\n" + "=" * 80)
    print("ALL FIXES COMPLETE")
    print("=" * 80)
    print(f"Started:  {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Finished: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Duration: {duration}")
    print(f"\nFull log saved to: {log_file_path}")
    print("=" * 80)

    # Close log file and restore stdout
    log_file.close()
    sys.stdout = sys.__stdout__

if __name__ == '__main__':
    main()

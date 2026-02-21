#!/usr/bin/env python3
"""Analyze all failure logs and provide a comprehensive report."""

import json
from pathlib import Path
from collections import Counter, defaultdict

def analyze_failures():
    logs_dir = Path('logs')

    total_failures = 0
    failures_by_translation = {}
    error_categories = Counter()
    critical_issues = []

    # Categories for error types
    def categorize_error(error_msg):
        error_lower = error_msg.lower()
        if 'arabic' in error_lower or any(c in error_msg for c in ['ا', 'ل', 'م', 'ن', 'و', 'ي', 'ه', 'ق']):
            return 'arabic_contamination'
        elif 'added' in error_lower and 'removed' in error_lower:
            return 'words_changed'
        elif 'added' in error_lower:
            return 'words_added'
        elif 'removed' in error_lower:
            return 'words_removed'
        elif 'repeated' in error_lower:
            return 'repetition'
        else:
            return 'other'

    # Analyze each failure log
    for log_file in sorted(logs_dir.glob('failures-*.json')):
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            translation = data['translation']
            count = data['total_failures']
            total_failures += count
            failures_by_translation[translation] = count

            # Analyze error types
            for failure in data['failures']:
                error_type = categorize_error(failure['error'])
                error_categories[error_type] += 1

                # Flag critical issues (Arabic text contamination)
                if error_type == 'arabic_contamination':
                    # Check if translation text contains significant Arabic
                    combined = failure.get('combined_translation', '')
                    orig_splits = failure.get('original_translation_splits', {})

                    # Check if any split contains mostly Arabic text
                    for split_id, text in orig_splits.items():
                        arabic_chars = sum(1 for c in text if '\u0600' <= c <= '\u06FF')
                        if arabic_chars > 10:  # Significant Arabic presence
                            critical_issues.append({
                                'translation': translation,
                                'verse_key': failure['verse_key'],
                                'chapter': failure['chapter'],
                                'verse_number': failure['verse_number'],
                                'split_id': split_id,
                                'text_preview': text[:100],
                                'arabic_char_count': arabic_chars
                            })

        except Exception as e:
            print(f"Error reading {log_file}: {e}")

    # Print comprehensive report
    print("=" * 80)
    print("FAILURE ANALYSIS REPORT")
    print("=" * 80)
    print(f"\nTotal failures across all translations: {total_failures}")
    print(f"Number of translations with failures: {len(failures_by_translation)}")
    print(f"\n{'Translation':<25} {'Failures':>10} {'% of Total':>12}")
    print("-" * 80)

    for translation, count in sorted(failures_by_translation.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / total_failures * 100) if total_failures > 0 else 0
        print(f"{translation:<25} {count:>10} {percentage:>11.1f}%")

    print("\n" + "=" * 80)
    print("ERROR CATEGORIES")
    print("=" * 80)
    print(f"\n{'Category':<30} {'Count':>10} {'% of Total':>12}")
    print("-" * 80)

    for category, count in error_categories.most_common():
        percentage = (count / total_failures * 100) if total_failures > 0 else 0
        print(f"{category:<30} {count:>10} {percentage:>11.1f}%")

    if critical_issues:
        print("\n" + "=" * 80)
        print(f"⚠️  CRITICAL ISSUES: ARABIC TEXT CONTAMINATION ({len(critical_issues)} instances)")
        print("=" * 80)
        print("\nThese verses have Arabic text where translation should be:\n")

        by_translation = defaultdict(list)
        for issue in critical_issues:
            by_translation[issue['translation']].append(issue)

        for translation, issues in sorted(by_translation.items()):
            print(f"\n{translation} ({len(issues)} verses):")
            for issue in sorted(issues, key=lambda x: (x['chapter'], x['verse_number']))[:5]:
                print(f"  • {issue['verse_key']} (Ch {issue['chapter']}:{issue['verse_number']})")
                print(f"    Split: {issue['split_id']}, Arabic chars: {issue['arabic_char_count']}")
                print(f"    Preview: {issue['text_preview'][:80]}...")

            if len(issues) > 5:
                print(f"  ... and {len(issues) - 5} more verses")

    print("\n" + "=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    print("\n1. CRITICAL: Fix Arabic text contamination issues first")
    print("   - These are data quality problems, not alignment issues")
    print("   - Affected translations need to be re-scraped or manually corrected")

    print("\n2. HIGH PRIORITY: Address translations with >50 failures")
    high_failure_count = [t for t, c in failures_by_translation.items() if c > 50]
    if high_failure_count:
        print(f"   - Translations: {', '.join(high_failure_count)}")
        print("   - Consider re-running alignment with different AI model/parameters")

    print("\n3. MEDIUM PRIORITY: Review 'words_added/removed' errors")
    print("   - These indicate LLM made changes to original text during alignment")
    print("   - May need manual correction or re-alignment with stricter prompts")

    print("\n4. LOW PRIORITY: Review other categories")
    print("   - Repetition and other errors are less common")
    print("   - Can be addressed on case-by-case basis")

    print("\n" + "=" * 80)

    return {
        'total_failures': total_failures,
        'failures_by_translation': failures_by_translation,
        'error_categories': dict(error_categories),
        'critical_issues': critical_issues
    }

if __name__ == '__main__':
    results = analyze_failures()

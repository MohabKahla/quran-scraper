#!/usr/bin/env python3
"""
Check all translations for potential issues.
Quick way to see what needs attention.
"""

import sys
from pathlib import Path
from check_current_state import check_translation

def main():
    translations_dir = Path("data/ksu-translations-formatted")

    if not translations_dir.exists():
        print(f"❌ Directory not found: {translations_dir}")
        return

    # Get all translations
    translations = [d.name for d in translations_dir.iterdir()
                   if d.is_dir() and not d.name.startswith('.')]
    translations.sort()

    print(f"Found {len(translations)} translations to check\n")

    results = {}

    for i, trans in enumerate(translations, 1):
        print(f"\n[{i}/{len(translations)}] Checking {trans}...")
        print("─" * 60)

        try:
            issues_count = check_translation(trans)
            results[trans] = issues_count
        except Exception as e:
            print(f"❌ Error: {e}")
            results[trans] = -1

    # Summary
    print("\n" + "="*60)
    print("OVERALL SUMMARY")
    print("="*60 + "\n")

    clean = []
    issues = []
    errors = []

    for trans, count in sorted(results.items()):
        if count == -1:
            errors.append(trans)
        elif count == 0:
            clean.append(trans)
        else:
            issues.append((trans, count))

    print(f"✅ Clean (no issues): {len(clean)}")
    for trans in clean:
        print(f"   - {trans}")

    print(f"\n⚠️  With issues: {len(issues)}")
    for trans, count in sorted(issues, key=lambda x: x[1], reverse=True):
        print(f"   - {trans}: {count} issues")

    if errors:
        print(f"\n❌ Errors: {len(errors)}")
        for trans in errors:
            print(f"   - {trans}")

    print("\n" + "="*60)
    print("NEXT STEPS")
    print("="*60)

    if issues:
        print("\nRe-run alignment for translations with issues:")
        print("\nexport GEMINI_API_KEY='your-key'\n")
        for trans, count in sorted(issues, key=lambda x: x[1], reverse=True)[:5]:
            print(f"# {trans} ({count} issues)")
            print(f"python3 fix_verse_alignments_with_retry.py \\")
            print(f"  --provider gemini --translation {trans}\n")
    else:
        print("\n✅ All translations look good!")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Validate formatted translation files against the Arabic reference structure.

For every translation in ksu-translations-formatted/<slug> and each chapter file
inside it, this script checks that every verse part key present in the Arabic
reference file exists in the translation file and that it has non-empty text.

Usage:
    python validate_formatted_translations.py [--fix]

Add --fix to attempt automatic remediation of missing/empty/extra entries.
"""

import argparse

from translation_check_utils import scan_formatted_translations


def print_summary(summary):
    print("\nValidation finished.")
    print(f"Checked files: {summary['total_files']}")
    if summary["files_with_issues"]:
        print(f"Issues found in: {summary['files_with_issues']} file(s).")
        print(f"  Missing keys: {summary['missing_keys']}")
        print(f"  Empty text:   {summary['empty_text']}")
        print(f"  Extra keys:   {summary['extra_keys']}")
    else:
        print("No issues detected.")


def main():
    parser = argparse.ArgumentParser(
        description="Validate formatted translation files against Arabic reference data."
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Attempt to automatically fix detected issues.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress per-file issue details (summary only).",
    )
    args = parser.parse_args()

    issues, summary = scan_formatted_translations(verbose=not args.quiet)
    print_summary(summary)

    if args.fix:
        if not issues:
            print("\nNo issues detected; nothing to fix.")
            return

        from fix_formatted_translations import fix_issues

        print("\nAttempting to fix issues...\n")
        fix_report = fix_issues(issues, verbose=not args.quiet)

        total_auto = (
            fix_report["missing_fixed"]
            + fix_report["empty_filled"]
            + fix_report["extra_removed"]
        )

        print("Fix summary:")
        print(f"  Files processed:     {fix_report['files_processed']}")
        print(f"  Entries auto-fixed:  {total_auto}")
        print(f"    - Missing filled:  {fix_report['missing_fixed']}")
        print(f"    - Empty filled:    {fix_report['empty_filled']}")
        print(f"    - Extra removed:   {fix_report['extra_removed']}")
        print(f"  Remaining issues:    {fix_report['unresolved_count']}")

        if fix_report["unresolved"]:
            print("  Unresolved entries remain in:")
            for path, keys in fix_report["unresolved"]:
                print(f"    {path}: {', '.join(sorted(keys))}")
        else:
            print("  All detected issues were fixed automatically.")

        print("\nRe-running validation...\n")
        issues, summary = scan_formatted_translations(verbose=not args.quiet)
        print_summary(summary)


if __name__ == "__main__":
    main()

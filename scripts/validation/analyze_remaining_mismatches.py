#!/usr/bin/env python3
"""
Final analysis and categorization of remaining translation mismatches.

Distinguishes between:
1. Space insertions after punctuation (formatting improvements - leave as-is)
2. Split-boundary word breaks (needs check_translation_splits.py)
3. Truncations (missing content - needs restore)
4. Real content issues (needs manual/AI fix)
"""

import json
import re
import sys
from pathlib import Path
from collections import defaultdict

FORMATTED_DIR = Path("data/ksu-translations-formatted")
ORIGINAL_DIR = Path("data/old-translations/ksu-translations")

def normalize(t: str) -> str:
    return re.sub(r"\s+", " ", t).strip()

def main():
    with open("logs/mismatches-current-fresh.json") as f:
        data = json.load(f)

    categories = {
        "space_punct_improvements": [],  # Space after punctuation, capitalisation fixes
        "split_boundaries": [],          # Mid-word splits (th-thai type)
        "truncations": [],               # Content missing from formatted
        "real_content_issues": [],       # Different wording, contamination, etc.
    }

    for m in data["mismatches"]:
        lang = m["language"]
        chapter = m["chapter"]
        verse = m["verse"]
        orig = normalize(m["original_text"])
        fmt = normalize(m["formatted_text"])
        sim = m["similarity"]

        # Check for space/punctuation improvements
        if sim > 0.985:
            orig_nopunct = re.sub(r'[^\w\s]', '', orig)
            fmt_nopunct = re.sub(r'[^\w\s]', '', fmt)
            if orig_nopunct == fmt_nopunct:
                categories["space_punct_improvements"].append(m)
                continue

        # Check for split-boundary (high sim, not just space/punct, many issues per language)
        if sim > 0.95 and len(orig) < len(fmt) * 1.05:
            # Check if it's just space insertion
            if fmt.replace(' ', '') == orig.replace(' ', ''):
                categories["space_punct_improvements"].append(m)
                continue

        # Check for truncation
        if len(orig) > len(fmt) * 1.1 and orig.startswith(fmt[:min(40, len(fmt)//2)]):
            categories["truncations"].append(m)
            continue

        # Real content issue
        categories["real_content_issues"].append(m)

    # Print summary
    print("=" * 80)
    print("REMAINING MISMATCH ANALYSIS")
    print("=" * 80)
    print()

    total = len(data["mismatches"])
    accounted = sum(len(v) for v in categories.values())

    print(f"Total mismatches: {total}")
    print()

    for cat, entries in sorted(categories.items(), key=lambda x: -len(x[1])):
        by_lang = defaultdict(list)
        for e in entries:
            by_lang[e["language"]].append(e)

        print(f"{cat}: {len(entries)}")
        for lang, lang_entries in sorted(by_lang.items(), key=lambda x: -len(x[1])):
            print(f"  {lang}: {len(lang_entries)}")

    print()
    print(f"Accounted for: {accounted}/{total}")
    print(f"Unaccounted: {total - accounted}")
    print()

    # Detail for real_content_issues
    print("=" * 80)
    print("REAL CONTENT ISSUES REQUIRING ATTENTION")
    print("=" * 80)
    print()

    by_lang = defaultdict(list)
    for e in categories["real_content_issues"]:
        by_lang[e["language"]].append(e)

    for lang, entries in sorted(by_lang.items(), key=lambda x: -len(x[1])):
        print(f"{lang}: {len(entries)} entries")
        for e in entries[:5]:  # Show first 5
            print(f"  ch{e['chapter']:>3} v{e['verse']:>3}  sim={e['similarity']:.2f}")
            print(f"    ORIG: {e['original_text'][:80]}")
            print(f"    FMT:  {e['formatted_text'][:80]}")
        if len(entries) > 5:
            print(f"  ... and {len(entries) - 5} more")
        print()

    # Generate commands for actionable items
    print()
    print("=" * 80)
    print("SUGGESTED ACTIONS")
    print("=" * 80)
    print()

    if categories["real_content_issues"]:
        print("1. Real content issues: Manual review required")
        print("   See docs/remaining-work/ for detailed breakdown")
        print()

    if categories["truncations"]:
        print("2. Truncations: Run restore_missing_content.py again")
        langs = set(e["language"] for e in categories["truncations"])
        print(f"   python3 scripts/alignment/restore_missing_content.py {' '.join(langs)}")
        print()

    print("3. Space/punctuation improvements: Leave as-is (intentional)")
    print()

    return 0

if __name__ == "__main__":
    sys.exit(main())

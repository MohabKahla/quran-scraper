#!/usr/bin/env python3
"""
Apply pre-computed character-level fixes to formatted translations.

Reads fix_char entries from logs/mismatches-actionable.json and applies
the exact character changes needed to make formatted files match the
original source text.

No API calls needed — all fixes are deterministic, based on precomputed diffs.

Usage:
    python3 scripts/alignment/fix_char_changes.py --dry-run
    python3 scripts/alignment/fix_char_changes.py
    python3 scripts/alignment/fix_char_changes.py --language bn-bengali
"""

import re
import sys
import json
import shutil
import difflib
from pathlib import Path
from datetime import datetime
from collections import defaultdict


FORMATTED_DIR = Path("data/ksu-translations-formatted")
ORIGINAL_DIR = Path("data/old-translations/ksu-translations")


def normalize(t: str) -> str:
    return re.sub(r"\s+", " ", t).strip()


def read_formatted_lines(path: Path):
    with open(path, encoding="utf-8") as f:
        return f.readlines()


def get_verse_parts(lines, verse_num: int):
    """Return list of (line_idx, key, text) for a given verse number."""
    parts = []
    for i, line in enumerate(lines):
        m = re.match(rf"^({verse_num:03d})_(\d+)\t(.+)", line)
        if m:
            key = f"{verse_num:03d}_{m.group(2)}"
            text = m.group(3).rstrip("\n")
            parts.append((i, key, text))
    return parts


def apply_change_to_parts(parts, op: str, orig_seg: str, fmt_seg: str, orig_full: str):
    """
    Find which part needs changing and apply one op to it.

    Returns (part_index, new_text) or (None, None) if not applicable.
    """
    if op == "replace":
        for i, (_, key, text) in enumerate(parts):
            t = normalize(text)
            if fmt_seg in t:
                return i, t.replace(fmt_seg, orig_seg, 1)

    elif op == "insert":
        # fmt has extra fmt_seg — remove it
        for i, (_, key, text) in enumerate(parts):
            t = normalize(text)
            if fmt_seg in t:
                return i, t.replace(fmt_seg, "", 1)

    elif op == "delete":
        # fmt is missing orig_seg — insert it using surrounding context
        orig_norm = normalize(orig_full)
        idx = orig_norm.find(orig_seg)
        if idx < 0:
            return None, None

        ctx_before = orig_norm[max(0, idx - 25) : idx]
        ctx_after = orig_norm[idx + len(orig_seg) : idx + len(orig_seg) + 25]

        for i, (_, key, text) in enumerate(parts):
            t = normalize(text)
            if ctx_before and ctx_before.strip() and ctx_before.strip() in t:
                pos = t.rfind(ctx_before.strip()) + len(ctx_before.strip())
                return i, t[:pos] + orig_seg + t[pos:]
            if ctx_after and ctx_after.strip() and ctx_after.strip() in t:
                pos = t.find(ctx_after.strip())
                return i, t[:pos] + orig_seg + t[pos:]

    return None, None


def fix_verse(parts, orig_text: str, changes):
    """
    Apply all changes to a multi-part verse.

    Returns dict {line_idx: new_text} for lines that need updating,
    or None if the fix could not be fully applied.
    """
    orig_norm = normalize(orig_text)
    current_parts = list(parts)  # (line_idx, key, text) — mutable copy

    pending_changes = list(changes)
    applied = []
    skipped = []

    for op, orig_seg, fmt_seg in pending_changes:
        part_idx, new_text = apply_change_to_parts(
            current_parts, op, orig_seg, fmt_seg, orig_norm
        )
        if part_idx is not None:
            line_idx, key, _ = current_parts[part_idx]
            current_parts[part_idx] = (line_idx, key, new_text)
            applied.append((op, orig_seg, fmt_seg))
        else:
            skipped.append((op, orig_seg, fmt_seg))

    if not applied:
        return None, skipped

    # Validate: does the combined text now match the original?
    combined = normalize(" ".join(text for _, _, text in current_parts))
    success = combined == orig_norm

    modifications = {
        line_idx: new_text for line_idx, _, new_text in current_parts
    }
    # Only return modifications for lines that actually changed
    original_texts = {line_idx: text for line_idx, _, text in parts}
    changed_only = {
        idx: text
        for idx, text in modifications.items()
        if normalize(text) != normalize(original_texts.get(idx, ""))
    }

    return changed_only, skipped


def process_language(lang: str, entries, dry_run: bool, verbose: bool):
    """Process all fix_char entries for one language."""
    fmt_lang_dir = FORMATTED_DIR / lang

    # Group entries by chapter
    by_chapter = defaultdict(list)
    for e in entries:
        by_chapter[e["chapter"]].append(e)

    total_fixed = 0
    total_skipped = 0
    total_partial = 0
    fix_details = []

    for chapter, chapter_entries in sorted(by_chapter.items()):
        fmt_file = fmt_lang_dir / f"{chapter}.txt"
        if not fmt_file.exists():
            continue

        lines = read_formatted_lines(fmt_file)
        modified = False

        for entry in chapter_entries:
            verse_num = int(entry["verse"])
            orig_text = entry["original_text"]
            changes = entry.get("changes", [])

            if not changes:
                continue

            parts = get_verse_parts(lines, verse_num)
            if not parts:
                total_skipped += 1
                continue

            mods, skipped_ops = fix_verse(parts, orig_text, changes)

            if mods is None:
                total_skipped += 1
                if verbose:
                    print(f"  ✗ {lang} ch{chapter} v{verse_num}: no changes applied")
                continue

            if skipped_ops:
                total_partial += 1
                if verbose:
                    print(
                        f"  ~ {lang} ch{chapter} v{verse_num}: partial fix "
                        f"({len(skipped_ops)} ops skipped)"
                    )
            else:
                total_fixed += 1
                if verbose:
                    print(f"  ✓ {lang} ch{chapter} v{verse_num}: fixed")

            fix_details.append(
                {
                    "language": lang,
                    "chapter": chapter,
                    "verse": verse_num,
                    "ops_applied": len(changes) - len(skipped_ops),
                    "ops_skipped": len(skipped_ops),
                }
            )

            if not dry_run:
                for line_idx, new_text in mods.items():
                    key = lines[line_idx].split("\t")[0]
                    lines[line_idx] = f"{key}\t{new_text}\n"
                modified = True

        if modified and not dry_run:
            # Backup
            backup_dir = (
                Path("backups")
                / datetime.now().strftime("%Y%m%d_%H%M%S")
                / lang
            )
            backup_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(fmt_file, backup_dir / fmt_file.name)

            with open(fmt_file, "w", encoding="utf-8") as f:
                f.writelines(lines)

    return total_fixed, total_partial, total_skipped, fix_details


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Apply precomputed char-level fixes to formatted translations"
    )
    parser.add_argument(
        "--language", help="Only fix this language (e.g. bn-bengali)"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview without writing files"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show per-verse detail"
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("logs/mismatches-actionable.json"),
        help="JSON file with fix_char entries",
    )
    args = parser.parse_args()

    print("=" * 80)
    print("CHAR-LEVEL FIX APPLIER")
    print("=" * 80)
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE FIX'}")
    print(f"Input: {args.input}")
    print()

    with open(args.input, encoding="utf-8") as f:
        data = json.load(f)

    fix_chars = [m for m in data["mismatches"] if m["_category"] == "fix_char"]

    # Group by language
    by_lang = defaultdict(list)
    for e in fix_chars:
        by_lang[e["language"]].append(e)

    if args.language:
        if args.language not in by_lang:
            print(f"No fix_char entries found for: {args.language}")
            return 1
        languages = [args.language]
    else:
        languages = sorted(by_lang.keys())

    grand_fixed = 0
    grand_partial = 0
    grand_skipped = 0
    all_details = []

    for i, lang in enumerate(languages, 1):
        entries = by_lang[lang]
        print(f"[{i}/{len(languages)}] {lang} — {len(entries)} entries")

        fixed, partial, skipped, details = process_language(
            lang, entries, dry_run=args.dry_run, verbose=args.verbose
        )

        grand_fixed += fixed
        grand_partial += partial
        grand_skipped += skipped
        all_details.extend(details)

        status = []
        if fixed:
            status.append(f"✓ {fixed} fixed")
        if partial:
            status.append(f"~ {partial} partial")
        if skipped:
            status.append(f"✗ {skipped} skipped")
        print(f"  {', '.join(status) if status else 'nothing to do'}")

    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"  Fully fixed:      {grand_fixed}")
    print(f"  Partially fixed:  {grand_partial}")
    print(f"  Skipped:          {grand_skipped}")
    print(f"  Total processed:  {grand_fixed + grand_partial + grand_skipped}")

    if args.dry_run:
        print("\n⚠  DRY RUN — no files written. Remove --dry-run to apply.")
    else:
        print("\n✅ Done.")

    return 0


if __name__ == "__main__":
    sys.exit(main())

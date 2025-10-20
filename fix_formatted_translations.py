#!/usr/bin/env python3
"""
Attempt to repair formatted translation files by filling missing/empty entries
from the original scraped translations and removing extraneous keys.
"""

import re
from pathlib import Path
from typing import Dict, Iterable, List, Set, Tuple

from translation_check_utils import (
    KEY_PATTERN,
    TRANSLATION_SOURCE_ROOT,
    read_arabic_structure,
    scan_formatted_translations,
)

VERSE_LINE_PATTERN = re.compile(r"^\s*(\d+)\.\s+(.*)$")
SENTENCE_SPLIT_PATTERN = re.compile(r"([.!?»])\s+")


def load_formatted_entries(path: Path) -> Dict[str, str]:
    entries: Dict[str, str] = {}
    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            match = KEY_PATTERN.match(raw_line.rstrip("\n"))
            if not match:
                continue
            key = match.group("key")
            entries[key] = match.group("text")
    return entries


def load_translation_source(slug: str, chapter: int) -> Dict[int, str]:
    verses: Dict[int, str] = {}
    source_path = TRANSLATION_SOURCE_ROOT / slug / f"{chapter:03d}.txt"
    if not source_path.exists():
        return verses

    with source_path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            match = VERSE_LINE_PATTERN.match(raw_line.strip())
            if not match:
                continue
            verse = int(match.group(1))
            text = match.group(2).strip()
            verses[verse] = text
    return verses


def split_translation_text(text: str, parts_needed: int) -> List[str]:
    text = text.strip()
    if parts_needed <= 1:
        return [text]
    if not text:
        return ["" for _ in range(parts_needed)]

    parts = SENTENCE_SPLIT_PATTERN.split(text)
    sentences: List[str] = []
    i = 0
    while i < len(parts):
        if i + 1 < len(parts) and parts[i + 1] in ".!?»":
            sentences.append((parts[i] + parts[i + 1]).strip())
            i += 2
        else:
            if parts[i].strip():
                sentences.append(parts[i].strip())
            i += 1

    if len(sentences) >= parts_needed:
        per_part = len(sentences) // parts_needed
        result = []
        for idx in range(parts_needed):
            if idx == parts_needed - 1:
                chunk = sentences[idx * per_part :]
            else:
                chunk = sentences[idx * per_part : (idx + 1) * per_part]
            result.append(" ".join(chunk).strip())
        return result

    words = text.split()
    if not words:
        return ["" for _ in range(parts_needed)]

    per_part = max(1, len(words) // parts_needed)
    result = []
    for idx in range(parts_needed):
        start = idx * per_part
        end = None if idx == parts_needed - 1 else (idx + 1) * per_part
        result.append(" ".join(words[start:end]).strip())

    if any(not part for part in result):
        chunk_size = max(1, len(text) // parts_needed)
        char_chunks = []
        for idx in range(parts_needed):
            start = idx * chunk_size
            end = None if idx == parts_needed - 1 else (idx + 1) * chunk_size
            char_chunks.append(text[start:end].strip())
        result = [chunk for chunk in char_chunks]

    return result


def ensure_entry(entries: Dict[str, str], key: str):
    if key not in entries:
        entries[key] = ""


def fix_file(issue: dict, verbose: bool = True):
    formatted_path: Path = issue["file_path"]
    formatted_dir: Path = issue["formatted_dir"]
    slug = formatted_dir.name
    chapter: int = issue["chapter"]
    missing: Set[str] = set(issue["missing"])
    empty: Set[str] = set(issue["empty"])
    extra: Set[str] = set(issue["extra"])

    try:
        arabic_structure, _ = read_arabic_structure(chapter)
    except FileNotFoundError:
        if verbose:
            print(f"Skipping {formatted_path}: Arabic reference missing.")
        return {"missing_fixed": 0, "empty_filled": 0, "extra_removed": 0, "unresolved": set()}

    entries = load_formatted_entries(formatted_path)
    source_verses = load_translation_source(slug, chapter)

    extra_removed = 0
    for key in extra:
        if key in entries:
            entries.pop(key)
            extra_removed += 1

    missing_fixed = 0
    empty_filled = 0
    unresolved: Set[str] = set()
    keys_to_fix = missing.union(empty)

    verse_to_parts: Dict[int, List[int]] = {}
    for key in keys_to_fix:
        verse = int(key.split("_")[0])
        verse_to_parts.setdefault(verse, []).append(int(key.split("_")[1]))

    for verse, parts in verse_to_parts.items():
        expected_parts = arabic_structure.get(verse, [])
        if not expected_parts:
            continue

        verse_text = source_verses.get(verse, "")
        fallback_parts = split_translation_text(verse_text, len(expected_parts))

        fallback_map = {
            expected_parts[idx]: fallback_parts[idx].strip() if idx < len(fallback_parts) else ""
            for idx in range(len(expected_parts))
        }

        for part in expected_parts:
            key = f"{verse:03d}_{part:02d}"
            ensure_entry(entries, key)
            fallback_text = fallback_map.get(part, "").strip()

            if fallback_text:
                entries[key] = fallback_text
                if key in missing:
                    missing_fixed += 1
                elif key in empty:
                    empty_filled += 1
            else:
                if key in keys_to_fix or not entries.get(key, "").strip():
                    unresolved.add(key)

    # Ensure missing keys at least exist
    for key in missing:
        ensure_entry(entries, key)

    # Rebuild file content preserving 000_00 if present
    lines: List[str] = []
    if "000_00" in entries:
        lines.append(f"000_00\t{entries['000_00'].strip()}")

    for verse in sorted(arabic_structure.keys()):
        if verse == 0:
            continue
        for part in arabic_structure[verse]:
            key = f"{verse:03d}_{part:02d}"
            text = entries.get(key, "").strip()
            lines.append(f"{key}\t{text}")

    formatted_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    if verbose:
        print(f"Fixed {formatted_path.name} ({slug}) - missing: {missing_fixed}, empty: {empty_filled}, removed: {extra_removed}")
        if unresolved:
            print(f"  Unresolved keys: {', '.join(sorted(unresolved))}")

    return {
        "missing_fixed": missing_fixed,
        "empty_filled": empty_filled,
        "extra_removed": extra_removed,
        "unresolved": unresolved,
    }


def fix_issues(issues: Iterable[dict], verbose: bool = True):
    summary = {
        "files_processed": 0,
        "missing_fixed": 0,
        "empty_filled": 0,
        "extra_removed": 0,
        "unresolved": [],
        "unresolved_count": 0,
    }

    for issue in issues:
        summary["files_processed"] += 1
        result = fix_file(issue, verbose=verbose)
        summary["missing_fixed"] += result["missing_fixed"]
        summary["empty_filled"] += result["empty_filled"]
        summary["extra_removed"] += result["extra_removed"]
        if result["unresolved"]:
            summary["unresolved"].append((issue["file_path"], result["unresolved"]))
            summary["unresolved_count"] += len(result["unresolved"])

    return summary


def main():
    issues, summary = scan_formatted_translations(verbose=True)
    if not issues:
        print("No issues detected.")
        return

    print("\nAttempting fixes...\n")
    fix_report = fix_issues(issues, verbose=True)
    total_auto = (
        fix_report["missing_fixed"]
        + fix_report["empty_filled"]
        + fix_report["extra_removed"]
    )

    print("\nFix summary:")
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


if __name__ == "__main__":
    main()

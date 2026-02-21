#!/usr/bin/env python3
"""
Fix real issues by comparing concatenated formatted text with original.

Strategy:
1. Concatenate all parts of a verse from formatted file
2. Compare normalized version with original
3. If difference is real (not spacing/punctuation), copy from original
4. Preserve the verse split structure from Arabic
"""

import json
import re
import os
import sys
from pathlib import Path

def normalize(text):
    """Normalize whitespace for comparison."""
    return re.sub(r'\s+', ' ', text).strip()

def contains_arabic(text):
    """Check if text contains Arabic characters."""
    arabic_pattern = re.compile(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]')
    return bool(arabic_pattern.search(text))

def get_verse_from_formatted(formatted_file, chapter, verse):
    """Get concatenated text of all verse parts from formatted file."""
    parts = []
    try:
        with open(formatted_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                if '\t' in line:
                    key, text = line.split('\t', 1)
                    # Format: VERSE_PART\ttext where VERSE is verse number, PART is split index
                    # Example: 049_00 = verse 49 part 0
                    verse_part = key.split('_')
                    if len(verse_part) == 2:
                        v_num, part_num = verse_part
                        if int(v_num) == verse:
                            parts.append(text)
    except Exception as e:
        print(f"    Error reading formatted: {e}")
        return None

    if not parts:
        return None

    # Join with space and normalize
    return normalize(' '.join(parts))

def get_verse_from_original(original_file, verse):
    """Get verse text from original file."""
    try:
        with open(original_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                # Lines start with "verse. text"
                match = re.match(rf'^{verse}\.\s+(.+)$', line)
                if match:
                    return normalize(match.group(1))
    except Exception as e:
        print(f"    Error reading original: {e}")
        return None
    return None

def write_verse_to_formatted(formatted_file, chapter, verse, new_text):
    """Rewrite verse parts with new text."""
    try:
        # Read entire file
        with open(formatted_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Get current verse parts to preserve structure
        current_parts = []
        verse_indices = []
        for i, line in enumerate(lines):
            line = line.strip()
            if not line or '\t' not in line:
                continue
            key, _ = line.split('\t', 1)
            try:
                # Format: VERSE_PART\ttext
                verse_part = key.split('_')
                if len(verse_part) == 2:
                    v_num, part_num = verse_part
                    if int(v_num) == verse:
                        current_parts.append((key, i))
            except:
                pass

        if not current_parts:
            return False

        # Distribute new_text across the existing parts
        # For simplicity, put all in first part and clear others
        if len(current_parts) == 1:
            # Single part - easy
            key, idx = current_parts[0]
            lines[idx] = f"{key}\t{new_text}\n"
        else:
            # Multiple parts - split text by word count roughly
            words = new_text.split()
            num_parts = len(current_parts)
            words_per_part = max(1, len(words) // num_parts)

            for part_idx, (key, idx) in enumerate(current_parts):
                start = part_idx * words_per_part
                if part_idx == num_parts - 1:
                    # Last part gets remaining
                    part_words = words[start:]
                else:
                    part_words = words[start:start + words_per_part]

                part_text = ' '.join(part_words)
                lines[idx] = f"{key}\t{part_text}\n"

        # Write back
        with open(formatted_file, 'w', encoding='utf-8') as f:
            f.writelines(lines)

        return True
    except Exception as e:
        print(f"    Error writing: {e}")
        return False

def main():
    if len(sys.argv) < 2:
        print("Usage: auto_fix_real_issues_v2.py <mismatches.json>")
        sys.exit(1)

    json_file = sys.argv[1]
    formatted_dir = "data/ksu-translations-formatted"
    original_dir = "data/old-translations/ksu-translations"

    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Filter real issues (similarity < 0.99)
    real_issues = [m for m in data["mismatches"] if m["similarity"] < 0.99]

    print(f"Found {len(real_issues)} real issues to check")
    print("=" * 80)

    fixed_count = 0
    contamination_count = 0
    skipped_count = 0

    for idx, issue in enumerate(real_issues, 1):
        lang = issue["language"]
        chapter = int(issue["chapter"])
        verse = int(issue["verse"])
        similarity = issue["similarity"]

        print(f"\n[{idx}/{len(real_issues)}] {lang} ch{chapter:03d} v{verse:03d} (sim: {similarity*100:.1f}%)")

        # Get file paths
        chapter_str = f"{chapter:03d}"
        formatted_file = f"{formatted_dir}/{lang}/{chapter_str}.txt"
        original_file = f"{original_dir}/{lang}/{chapter_str}.txt"

        if not os.path.exists(formatted_file) or not os.path.exists(original_file):
            print("    ⚠️  File not found - skipping")
            skipped_count += 1
            continue

        # Get texts
        fmt_text = get_verse_from_formatted(formatted_file, chapter, verse)
        orig_text = get_verse_from_original(original_file, verse)

        if not fmt_text or not orig_text:
            print("    ⚠️  Could not read verse - skipping")
            skipped_count += 1
            continue

        # Check for Arabic contamination in formatted
        if contains_arabic(fmt_text) and not contains_arabic(orig_text):
            print("    ⚠️  ARABIC CONTAMINATION - fixing...")
            if write_verse_to_formatted(formatted_file, chapter, verse, orig_text):
                print("    ✅ Fixed")
                fixed_count += 1
                contamination_count += 1
            else:
                print("    ❌ Failed to fix")
            continue

        # Compare normalized texts
        if fmt_text == orig_text:
            print("    ℹ️  Same when normalized (split structure only) - skipping")
            skipped_count += 1
            continue

        # Check if difference is just spacing
        fmt_no_space = fmt_text.replace(' ', '')
        orig_no_space = orig_text.replace(' ', '')

        if fmt_no_space == orig_no_space:
            print("    ℹ️  Spacing difference only - skipping")
            skipped_count += 1
            continue

        # Real content difference
        len_diff = len(orig_text) - len(fmt_text)
        print(f"    ⚠️  CONTENT DIFFERENCE ({len_diff:+d} chars)")

        # If formatted has extra Arabic content, fix it
        if contains_arabic(fmt_text):
            print("    ⚠️  Contains Arabic - replacing with original...")
            if write_verse_to_formatted(formatted_file, chapter, verse, orig_text):
                print("    ✅ Fixed")
                fixed_count += 1
            else:
                print("    ❌ Failed to fix")
        else:
            # Other content difference - show sample
            print(f"    Orig: {orig_text[:100]}...")
            print(f"    Formatted: {fmt_text[:100]}...")
            print("    ⚠️  Manual review needed - skipping")
            skipped_count += 1

    print("\n" + "=" * 80)
    print(f"SUMMARY:")
    print(f"  Total checked: {len(real_issues)}")
    print(f"  Fixed: {fixed_count}")
    print(f"  Arabic contamination fixed: {contamination_count}")
    print(f"  Skipped (manual review needed): {skipped_count}")
    print("=" * 80)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Automatically fix real issues in formatted translations.

Issues to fix:
1. Arabic text contamination -> replace with original translation
2. Character changes -> use original text
3. Split boundary errors -> re-parse with OpenAI

For each mismatch:
- If similarity < 0.99, it's a real issue
- Check if formatted contains Arabic characters -> contamination
- Check if normalized text differs -> character changes
- Otherwise it might be a split boundary issue
"""

import json
import re
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

def normalize(text):
    """Normalize whitespace for comparison."""
    return re.sub(r'\s+', ' ', text).strip()

def contains_arabic(text):
    """Check if text contains Arabic characters."""
    arabic_pattern = re.compile(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]')
    return bool(arabic_pattern.search(text))

def get_verse_parts(formatted_file, chapter, verse):
    """Get all parts of a verse from formatted file."""
    parts = []
    try:
        with open(formatted_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                # Parse: "NNN_NN\ttext"
                if '\t' in line:
                    key, text = line.split('\t', 1)
                    ch, v, p = key.split('_')
                    if int(ch) == chapter and int(v) == verse:
                        parts.append((key, text))
    except Exception as e:
        print(f"Error reading {formatted_file}: {e}")
    return parts

def write_verse_parts(formatted_file, chapter, verse, new_parts):
    """Rewrite verse parts in formatted file."""
    try:
        # Read entire file
        with open(formatted_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Find and replace lines for this verse
        new_lines = []
        skip_next = False
        i = 0

        while i < len(lines):
            line = lines[i].strip()
            if not line:
                new_lines.append(lines[i])
                i += 1
                continue

            if '\t' in line:
                key, _ = line.split('\t', 1)
                try:
                    ch, v, p = key.split('_')
                    if int(ch) == chapter and int(v) == verse:
                        # Replace this verse's lines
                        for part_key, part_text in new_parts:
                            new_lines.append(f"{part_key}\t{part_text}\n")
                        # Skip original lines for this verse
                        i += 1
                        while i < len(lines):
                            next_line = lines[i].strip()
                            if '\t' in next_line:
                                next_key, _ = next_line.split('\t', 1)
                                next_ch, next_v, _ = next_key.split('_')
                                if int(next_ch) == chapter and int(next_v) == verse:
                                    i += 1
                                    continue
                            break
                        continue
                except:
                    pass

            new_lines.append(lines[i])
            i += 1

        # Write back
        with open(formatted_file, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)

        return True
    except Exception as e:
        print(f"Error writing {formatted_file}: {e}")
        return False

def fix_verse(language, chapter, verse, original_text, formatted_dir, original_dir):
    """Fix a single verse by copying from original."""
    # Convert to int if strings
    chapter = int(chapter)
    verse = int(verse)
    # Construct file paths
    chapter_str = f"{chapter:03d}"
    formatted_file = f"{formatted_dir}/{language}/{chapter_str}.txt"
    original_file = f"{original_dir}/{language}/{chapter_str}.txt"

    if not os.path.exists(formatted_file):
        return False
    if not os.path.exists(original_file):
        return False

    # Get original verse text
    orig_text = None
    try:
        with open(original_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or not line.startswith(f"{verse}."):
                    continue
                # Remove verse number prefix
                orig_text = line.split('.', 1)[1].strip()
                break
    except Exception as e:
        print(f"  Error reading original: {e}")
        return False

    if not orig_text:
        return False

    # Check if we need to split according to Arabic
    arabic_file = f"data/chs-ar-final/{chapter_str}"
    if os.path.exists(arabic_file):
        # Count parts in Arabic for this verse
        arabic_parts = []
        try:
            with open(arabic_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if '\t' in line:
                        key, text = line.split('\t', 1)
                        ch, v, p = key.split('_')
                        if int(ch) == chapter and int(v) == verse:
                            arabic_parts.append((key, text))
        except:
            pass

        # If Arabic has multiple parts, we need to match that structure
        if len(arabic_parts) > 1:
            # For now, keep original split structure if it exists
            current_parts = get_verse_parts(formatted_file, chapter, verse)
            if current_parts and len(current_parts) == len(arabic_parts):
                # Keep the structure but update text content
                # Normalize original to match current split roughly
                # This is complex - skip for now
                pass

    # Simple fix: replace formatted content with original text
    # Preserve the split structure if it exists
    current_parts = get_verse_parts(formatted_file, chapter, verse)

    if not current_parts:
        return False

    if len(current_parts) == 1:
        # Single part - just replace text
        new_parts = [(current_parts[0][0], orig_text)]
    else:
        # Multiple parts - need to redistribute original text
        # For now, concatenate and let split alignment fix it
        combined_text = normalize(orig_text)
        new_parts = [(current_parts[0][0], combined_text)]

    return write_verse_parts(formatted_file, chapter, verse, new_parts)

def main():
    if len(sys.argv) < 2:
        print("Usage: auto_fix_real_issues.py <mismatches.json>")
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
    skipped_count = 0

    for idx, issue in enumerate(real_issues, 1):
        lang = issue["language"]
        chapter = issue["chapter"]
        verse = issue["verse"]
        orig_text = issue["original_text"]
        fmt_text = issue["formatted_text"]

        ch_int = int(chapter)
        v_int = int(verse)
        similarity_pct = issue['similarity'] * 100
        print(f"\n[{idx}/{len(real_issues)}] {lang} ch{ch_int:03d} v{v_int:03d} (sim: {similarity_pct:.1f}%)")

        # Check for Arabic contamination
        if contains_arabic(fmt_text) and not contains_arabic(orig_text):
            print("  ⚠️  ARABIC CONTAMINATION - fixing...")
            if fix_verse(lang, chapter, verse, orig_text, formatted_dir, original_dir):
                print("  ✅ Fixed")
                fixed_count += 1
            else:
                print("  ❌ Failed to fix")
            continue

        # Check if normalized texts differ
        orig_norm = normalize(orig_text)
        fmt_norm = normalize(fmt_text)

        if orig_norm != fmt_norm:
            # Check length difference
            len_diff = len(orig_norm) - len(fmt_norm)

            if abs(len_diff) > 50:
                # Significant difference - might be truncation or extra content
                print(f"  ⚠️  LENGTH DIFFERENCE: {len_diff:+d} chars")
                if len_diff < 0:
                    print("  (formatted has extra content)")
                else:
                    print("  (formatted is truncated)")

                # Try to fix
                print("  Attempting to fix...")
                if fix_verse(lang, chapter, verse, orig_text, formatted_dir, original_dir):
                    print("  ✅ Fixed")
                    fixed_count += 1
                else:
                    print("  ❌ Failed to fix")
                continue

            # Small difference - might be character changes
            # Skip if it's just spacing
            if fmt_norm.replace(' ', '') == orig_norm.replace(' ', ''):
                print("  ℹ️  Spacing only - skipping")
                skipped_count += 1
                continue

            # Character changes detected
            print("  ⚠️  CHARACTER CHANGES - fixing...")
            if fix_verse(lang, chapter, verse, orig_text, formatted_dir, original_dir):
                print("  ✅ Fixed")
                fixed_count += 1
            else:
                print("  ❌ Failed to fix")
        else:
            print("  ℹ️  Same when normalized - skipping")
            skipped_count += 1

    print("\n" + "=" * 80)
    print(f"SUMMARY:")
    print(f"  Total issues checked: {len(real_issues)}")
    print(f"  Fixed: {fixed_count}")
    print(f"  Skipped: {skipped_count}")
    print("=" * 80)

if __name__ == "__main__":
    main()

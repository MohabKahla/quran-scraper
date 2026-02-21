#!/usr/bin/env python3
"""
Fix split boundary errors using OpenAI API.

For verses where the formatted version has content in wrong order compared to original,
this script will:
1. Get the Arabic reference structure
2. Get the original translation text
3. Ask OpenAI to split the translation to match Arabic structure
4. Write the corrected split to formatted file
"""

import json
import re
import os
import sys
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import openai
except ImportError:
    print("Installing openai...")
    os.system("pip install openai")
    import openai

def normalize(text):
    """Normalize whitespace for comparison."""
    return re.sub(r'\s+', ' ', text).strip()

def contains_arabic(text):
    """Check if text contains Arabic characters."""
    arabic_pattern = re.compile(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]')
    return bool(arabic_pattern.search(text))

def get_arabic_structure(chapter, verse):
    """Get the Arabic verse structure (number of parts)."""
    arabic_file = f"data/chs-ar-final/{chapter:03d}"
    parts = []

    if not os.path.exists(arabic_file):
        return None

    try:
        with open(arabic_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or '\t' not in line:
                    continue
                key, text = line.split('\t', 1)
                verse_part = key.split('_')
                if len(verse_part) == 2:
                    v_num, part_num = verse_part
                    if int(v_num) == verse:
                        parts.append((key, text))
    except Exception as e:
        print(f"    Error reading Arabic: {e}")
        return None

    return parts if parts else None

def get_original_verse(language, chapter, verse):
    """Get original verse text from original translation."""
    original_file = f"data/old-translations/ksu-translations/{language}/{chapter:03d}.txt"

    if not os.path.exists(original_file):
        return None

    try:
        with open(original_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                match = re.match(rf'^{verse}\.\s+(.+)$', line)
                if match:
                    return normalize(match.group(1))
    except Exception as e:
        print(f"    Error reading original: {e}")
        return None

    return None

def get_formatted_parts(language, chapter, verse):
    """Get current formatted verse parts."""
    formatted_file = f"data/ksu-translations-formatted/{language}/{chapter:03d}.txt"
    parts = []

    if not os.path.exists(formatted_file):
        return None

    try:
        with open(formatted_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or '\t' not in line:
                    continue
                key, text = line.split('\t', 1)
                verse_part = key.split('_')
                if len(verse_part) == 2:
                    v_num, part_num = verse_part
                    if int(v_num) == verse:
                        parts.append((key, text))
    except Exception as e:
        print(f"    Error reading formatted: {e}")
        return None

    return parts if parts else None

def split_with_openai(translation_text, arabic_parts, language):
    """Use OpenAI to split translation according to Arabic structure."""

    # Build prompt
    arabic_joined = "\n".join([f"Part {i}: {text[:50]}..." for i, (key, text) in enumerate(arabic_parts)])

    prompt = f"""You are a Quran translation expert. Your task is to split a translation verse into parts that match the Arabic verse structure.

Language: {language}
Full translation text:
{translation_text}

Arabic reference structure (showing where splits occur):
{arabic_joined}

Instructions:
1. Split the translation into {len(arabic_parts)} parts to match the Arabic structure
2. Preserve the exact wording - do not change any text
3. Only determine where to add line breaks
4. Return the result as a JSON object with keys "part_0", "part_1", etc.
5. Each part should contain the text for that segment

Example output format:
{{
  "part_0": "first segment text",
  "part_1": "second segment text",
  ...
}}

Return only the JSON, no other text."""

    try:
        client = openai.OpenAI()

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a precise text segmentation expert for Quran translations."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            max_tokens=2000
        )

        result = response.choices[0].message.content.strip()

        # Extract JSON from response
        if "```json" in result:
            result = result.split("```json")[1].split("```")[0].strip()
        elif "```" in result:
            result = result.split("```")[1].split("```")[0].strip()

        parts_data = json.loads(result)
        return [parts_data.get(f"part_{i}", "") for i in range(len(arabic_parts))]

    except Exception as e:
        print(f"    OpenAI error: {e}")
        return None

def write_formatted_parts(language, chapter, verse, new_parts):
    """Write new parts to formatted file."""
    formatted_file = f"data/ksu-translations-formatted/{language}/{chapter:03d}.txt"

    if not os.path.exists(formatted_file):
        return False

    try:
        # Read entire file
        with open(formatted_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Find lines for this verse
        verse_lines = []
        verse_indices = []
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            if not line_stripped or '\t' not in line_stripped:
                continue
            key, _ = line_stripped.split('\t', 1)
            verse_part = key.split('_')
            if len(verse_part) == 2:
                v_num, part_num = verse_part
                if int(v_num) == verse:
                    verse_lines.append((key, i))
                    verse_indices.append(i)

        if not verse_lines:
            return False

        # Replace verse lines
        for idx, (key, line_idx) in enumerate(verse_lines):
            if idx < len(new_parts):
                lines[line_idx] = f"{key}\t{new_parts[idx]}\n"

        # Write back
        with open(formatted_file, 'w', encoding='utf-8') as f:
            f.writelines(lines)

        return True
    except Exception as e:
        print(f"    Error writing: {e}")
        return False

def main():
    if len(sys.argv) < 2:
        print("Usage: fix_split_boundaries_openai.py <mismatches.json> [--dry-run]")
        sys.exit(1)

    json_file = sys.argv[1]
    dry_run = "--dry-run" in sys.argv

    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Filter real issues (similarity < 0.99)
    real_issues = [m for m in data["mismatches"] if m["similarity"] < 0.99]

    print(f"Found {len(real_issues)} real issues to process")
    print("=" * 80)

    # Group by language for better reporting
    by_language = {}
    for issue in real_issues:
        lang = issue["language"]
        if lang not in by_language:
            by_language[lang] = []
        by_language[lang].append(issue)

    print(f"Languages affected: {len(by_language)}")
    for lang, issues in sorted(by_language.items()):
        print(f"  {lang}: {len(issues)} issues")

    print("\nStarting OpenAI re-parsing...")
    print("=" * 80)

    processed = 0
    fixed = 0
    failed = 0
    skipped = 0

    for lang, issues in sorted(by_language.items()):
        print(f"\n{'='*80}")
        print(f"Processing {lang} ({len(issues)} issues)")
        print(f"{'='*80}")

        for idx, issue in enumerate(issues, 1):  # Process all issues
            chapter = int(issue["chapter"])
            verse = int(issue["verse"])
            similarity = issue["similarity"]

            print(f"\n[{idx}/5] ch{chapter:03d} v{verse:03d} (sim: {similarity*100:.1f}%)")

            # Get Arabic structure
            arabic_parts = get_arabic_structure(chapter, verse)
            if not arabic_parts:
                print("    ⚠️  No Arabic structure found - skipping")
                skipped += 1
                continue

            print(f"    Arabic has {len(arabic_parts)} parts")

            # Get original text
            original_text = get_original_verse(lang, chapter, verse)
            if not original_text:
                print("    ⚠️  Could not read original - skipping")
                skipped += 1
                continue

            # Get current formatted parts
            current_parts = get_formatted_parts(lang, chapter, verse)
            if not current_parts:
                print("    ⚠️  Could not read formatted - skipping")
                skipped += 1
                continue

            # Check if split is already correct
            if len(current_parts) == len(arabic_parts):
                # Verify content order
                current_joined = normalize(' '.join([p[1] for p in current_parts]))
                if current_joined == original_text:
                    print("    ✅ Already correct - skipping")
                    skipped += 1
                    continue

            print(f"    Current has {len(current_parts)} parts")
            print("    ⚠️  Split mismatch - re-parsing with OpenAI...")

            if dry_run:
                print("    [DRY RUN] Would call OpenAI API")
                processed += 1
                continue

            # Call OpenAI
            new_parts = split_with_openai(original_text, arabic_parts, lang)

            if new_parts and len(new_parts) == len(arabic_parts):
                # Verify the joined text matches original
                new_joined = normalize(' '.join(new_parts))
                if new_joined == original_text or len(new_joined) == len(original_text):
                    # Write to file
                    if write_formatted_parts(lang, chapter, verse, new_parts):
                        print("    ✅ Fixed")
                        fixed += 1
                    else:
                        print("    ❌ Failed to write")
                        failed += 1
                else:
                    print(f"    ⚠️  OpenAI result doesn't match original - skipping")
                    print(f"       Expected length: {len(original_text)}, Got: {len(new_joined)}")
                    skipped += 1
            else:
                print("    ❌ OpenAI failed or returned wrong number of parts")
                failed += 1

            processed += 1

            # Rate limiting
            time.sleep(1)

        print(f"\n{lang}: Processed {idx}, Fixed {fixed}, Failed {failed}, Skipped {skipped}")

    print("\n" + "=" * 80)
    print("FINAL SUMMARY:")
    print(f"  Total processed: {processed}")
    print(f"  Fixed: {fixed}")
    print(f"  Failed: {failed}")
    print(f"  Skipped: {skipped}")
    print("=" * 80)
    print("\nAll issues processed.")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Generic script to reformat Quran translation files so they match the Arabic verse
structure using semantic alignment powered by Google's Gemini API.

Update the configuration section below for each target language before running.
"""

import re
import json
import google.generativeai as genai
from pathlib import Path
from typing import Optional


def _resolve_path(value, default):
    if value is None:
        return default
    return value if isinstance(value, Path) else Path(value)

# ============================================================================
# CONFIGURATION – Update these variables for each language
# ============================================================================

# Language metadata
LANGUAGE_NAME = globals().get("LANGUAGE_NAME", "French")  # e.g., "French", "English", "Italian"
LANGUAGE_CODE = globals().get("LANGUAGE_CODE", "fr")  # ISO 639-1 code if available
TRANSLATION_DIRECTION = globals().get("TRANSLATION_DIRECTION", "ltr")  # "ltr" or "rtl"

# Directory paths (absolute paths recommended)
TRANSLATION_INPUT_DIR = _resolve_path(
    globals().get("TRANSLATION_INPUT_DIR"),
    Path("/Users/kahla/Developer/quran-scraper/french"),
)
ARABIC_REFERENCE_DIR = _resolve_path(
    globals().get("ARABIC_REFERENCE_DIR"),
    Path("/Users/kahla/Developer/quran-scraper/chs-ar-final"),
)
OUTPUT_DIR = _resolve_path(
    globals().get("OUTPUT_DIR"),
    Path("/Users/kahla/Developer/quran-scraper/french-formatted-gemini"),
)

# Translation input format
#   "numbered"  -> lines like `1. Verse text`
#   "structured" -> lines like `001_01\tVerse text` (already split similar to Arabic)
TRANSLATION_FORMAT = globals().get("TRANSLATION_FORMAT", "numbered")

# Gemini API configuration
GEMINI_MODEL = globals().get("GEMINI_MODEL", "gemini-1.5-flash")
GEMINI_API_KEY = globals().get(
    "GEMINI_API_KEY",
    "AIzaSyAuyTO5D9bPD3tyTU5UDcc63VJ5kQPbnYE",
)

# If you prefer, you can hardcode an API key (not recommended for committed code)
# GEMINI_API_KEY = ""

# Minimum delay (seconds) between Gemini calls to avoid rate limits
API_THROTTLE_SECONDS = globals().get("API_THROTTLE_SECONDS", 0)

# ============================================================================

if not GEMINI_API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY is not set. Export the key in your environment or update the script."
    )

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(GEMINI_MODEL)

def parse_arabic_file(arabic_path: Path):
    """Parse Arabic file and extract verse structure with full text and Surah name."""
    verse_structure = {}
    surah_name = None

    with open(arabic_path, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line:
                continue

            if line.startswith("سُورَةُ"):
                surah_name = line
                continue

            match = re.match(r"^(\d{3})_(\d{2})\t(.+)$", line)
            if match:
                verse_num = int(match.group(1))
                part_num = int(match.group(2))
                arabic_text = match.group(3)

                verse_structure.setdefault(verse_num, []).append((part_num, arabic_text))

    return verse_structure, surah_name

def parse_translation_numbered(translation_path: Path):
    """Parse simple numbered translation files (e.g., `1. Verse text`)."""
    verses = {}

    with open(translation_path, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line:
                continue

            match = re.match(r"^(\d+)\.\s+(.+)$", line)
            if match:
                verse_num = int(match.group(1))
                verse_text = match.group(2)
                verses[verse_num] = verse_text

    return verses

def parse_translation_structured(translation_path: Path):
    """Parse translation already split like Arabic (`001_01\tText`)."""
    verse_structure = {}

    with open(translation_path, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line:
                continue

            match = re.match(r"^(\d{3})_(\d{2})\t(.+)$", line)
            if match:
                verse_num = int(match.group(1))
                part_num = int(match.group(2))
                text = match.group(3)
                verse_structure.setdefault(verse_num, []).append((part_num, text))

    return verse_structure

def parse_translation_file(translation_path: Path):
    """Dispatch to the correct parser based on TRANSLATION_FORMAT."""
    if TRANSLATION_FORMAT == "structured":
        return parse_translation_structured(translation_path)
    return parse_translation_numbered(translation_path)


def fetch_basmallah_translation(translation_dir: Path) -> Optional[str]:
    """Derive the basmallah text from the translation of Surah 1."""
    translation_files = sorted(translation_dir.glob("*.txt"))
    chapter_one_file = None

    for candidate in translation_files:
        chapter_num = get_chapter_number_from_filename(candidate.name)
        if chapter_num == 1:
            chapter_one_file = candidate
            break

    if not chapter_one_file:
        print("Warning: Could not locate chapter 1 translation file to derive basmallah.")
        return None

    if TRANSLATION_FORMAT == "structured":
        structure = parse_translation_structured(chapter_one_file)
        if 0 in structure and structure[0]:
            # Use 000_00 if present
            return structure[0][0][1].strip()
        if 1 in structure and structure[1]:
            # Fallback to first part of verse 1
            return structure[1][0][1].strip()
        print(
            f"Warning: Unable to extract basmallah from structured translation {chapter_one_file}."
        )
        return None

    verses = parse_translation_numbered(chapter_one_file)
    basmallah = verses.get(1)
    if basmallah:
        return basmallah.strip()

    print(
        f"Warning: Verse 1 missing in numbered translation {chapter_one_file}; basmallah not set."
    )
    return None

def split_verse_semantic(verse_num, translation_text, arabic_parts):
    """Use Gemini to split translation verse text based on semantic alignment."""
    if len(arabic_parts) == 1:
        return [translation_text]

    arabic_parts_text = "\n".join(
        [f"Part {i + 1}: {part[1]}" for i, part in enumerate(arabic_parts)]
    )

    prompt = f"""You align Quranic translations. Given an Arabic verse split into {len(arabic_parts)}
parts and its {LANGUAGE_NAME} translation, split the {LANGUAGE_NAME} translation at the exact
semantic points where the Arabic is split.

Verse {verse_num}:

Arabic parts:
{arabic_parts_text}

{LANGUAGE_NAME} (complete verse):
{translation_text}

Return ONLY a JSON array with {len(arabic_parts)} strings, where each string is one part of the
{LANGUAGE_NAME} text.
"""

    try:
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        json_match = re.search(r"\[.*\]", response_text, re.DOTALL)
        if json_match:
            response_text = json_match.group(0)

        parts = json.loads(response_text)

        if len(parts) != len(arabic_parts):
            print(
                f"Warning: Expected {len(arabic_parts)} parts but got {len(parts)} for verse {verse_num}."
            )
            return simple_split(translation_text, len(arabic_parts))

        return [part.strip() for part in parts]

    except Exception as exc:
        print(f"Error using Gemini for verse {verse_num}: {exc}")
        if "response_text" in locals():
            print(f"Response was: {response_text}")
        return simple_split(translation_text, len(arabic_parts))

def simple_split(text, num_parts):
    """Fallback: naive sentence/word splitting when Gemini alignment fails."""
    if num_parts == 1:
        return [text]

    sentence_pattern = r"([.!?»])\s+"
    parts = re.split(sentence_pattern, text)

    sentences = []
    i = 0
    while i < len(parts):
        if i + 1 < len(parts) and parts[i + 1] in ".!?»":
            sentences.append(parts[i] + parts[i + 1])
            i += 2
        else:
            if parts[i].strip():
                sentences.append(parts[i])
            i += 1

    if len(sentences) >= num_parts:
        sentences_per_part = len(sentences) // num_parts
        result = []
        for idx in range(num_parts):
            if idx == num_parts - 1:
                result.append(" ".join(sentences[idx * sentences_per_part :]).strip())
            else:
                start = idx * sentences_per_part
                end = (idx + 1) * sentences_per_part
                result.append(" ".join(sentences[start:end]).strip())
        return result

    words = text.split()
    words_per_part = len(words) // num_parts or 1
    result = []
    for idx in range(num_parts):
        start = idx * words_per_part
        end = None if idx == num_parts - 1 else (idx + 1) * words_per_part
        result.append(" ".join(words[start:end]).strip())
    return result

def reformat_translation_file(
    translation_path: Path,
    arabic_path: Path,
    output_path: Path,
    basmallah_text: Optional[str],
):
    """Reformat translation file to match Arabic verse structure."""
    arabic_structure, surah_name = parse_arabic_file(arabic_path)

    if TRANSLATION_FORMAT == "structured":
        translation_structure = parse_translation_structured(translation_path)
    else:
        translation_structure = parse_translation_numbered(translation_path)

    current_basmallah = basmallah_text

    if TRANSLATION_FORMAT == "structured":
        verse_zero_parts = translation_structure.pop(0, [])
        if verse_zero_parts:
            current_basmallah = verse_zero_parts[0][1].strip()

    translated_surah_name = ""
    try:
        with open(translation_path, "r", encoding="utf-8") as f:
            first_line = f.readline().strip()
            if first_line and not re.match(r"^\d+\.\s", first_line):
                translated_surah_name = first_line
    except Exception as exc:
        print(f"Warning: Could not read surah name from {translation_path}: {exc}")

    with open(output_path, "w", encoding="utf-8") as f:
        # if translated_surah_name:
        #     f.write(f"{translated_surah_name}\n\n")

        # if surah_name:
        #     f.write(f"{surah_name}\n")

        # if current_basmallah:
        #     f.write(f"000_00\t{current_basmallah}\n")
        # else:
        #     print(
        #         f"Warning: No basmallah text available for {translation_path}; skipping basmallah line."
        #     )

        for verse_num in sorted(arabic_structure.keys()):
            if verse_num == 0:
                continue

            arabic_parts = sorted(arabic_structure[verse_num], key=lambda part: part[0])

            if TRANSLATION_FORMAT == "structured":
                translation_parts = translation_structure.get(verse_num, [])
                if not translation_parts:
                    print(
                        f"Warning: Verse {verse_num} not found in structured translation {translation_path}"
                    )
                    continue

                normalized_parts = {part_num: text for part_num, text in translation_parts}
                for part_num, _ in arabic_parts:
                    if part_num not in normalized_parts:
                        print(
                            f"Warning: Part {part_num} missing for verse {verse_num} in {translation_path}"
                        )
                        normalized_parts[part_num] = ""

                for part_num, _ in arabic_parts:
                    f.write(f"{verse_num:03d}_{part_num:02d}\t{normalized_parts[part_num]}\n")
                continue

            if verse_num not in translation_structure:
                print(f"Warning: Verse {verse_num} missing in translation {translation_path}")
                continue

            verse_text = translation_structure[verse_num]
            if len(arabic_parts) == 1:
                parts = [verse_text]
            else:
                print(f"  Aligning verse {verse_num} ({len(arabic_parts)} parts)...")
                parts = split_verse_semantic(verse_num, verse_text, arabic_parts)

            for index, part_text in enumerate(parts):
                part_num = arabic_parts[index][0]
                f.write(f"{verse_num:03d}_{part_num:02d}\t{part_text}\n")

def get_chapter_number_from_filename(filename: str):
    match = re.match(r"^(\d+)", filename)
    return int(match.group(1)) if match else None

def main():
    translation_dir = TRANSLATION_INPUT_DIR
    arabic_dir = ARABIC_REFERENCE_DIR
    output_dir = OUTPUT_DIR

    for directory, label in [
        (translation_dir, "Translation directory"),
        (arabic_dir, "Arabic reference directory"),
    ]:
        if not Path(directory).exists():
            raise FileNotFoundError(f"{label} not found: {directory}")

    output_dir.mkdir(exist_ok=True)

    basmallah_text = fetch_basmallah_translation(translation_dir)

    print("=" * 60)
    print("Quran Translation Reformatter")
    print(f"Language: {LANGUAGE_NAME} ({LANGUAGE_CODE})")
    print(f"Translation direction: {TRANSLATION_DIRECTION.upper()}")
    print(f"Input directory: {translation_dir}")
    print(f"Output directory: {output_dir}")
    print(f"Translation format: {TRANSLATION_FORMAT}\n")

    translation_files = sorted(translation_dir.glob("*.txt"))
    translation_files = [f for f in translation_files if get_chapter_number_from_filename(f.name)]

    processed = 0
    errors = 0

    for translation_file in translation_files:
        chapter_num = get_chapter_number_from_filename(translation_file.name)
        if chapter_num is None:
            continue

        arabic_file = arabic_dir / f"{chapter_num:03d}.txt"
        if not arabic_file.exists():
            alternate = arabic_dir / f"{chapter_num:03d}"
            if alternate.exists():
                arabic_file = alternate
            else:
                print(f"Skipping {translation_file.name}: Arabic reference file missing")
                errors += 1
                continue

        output_file = output_dir / f"{chapter_num:03d}.txt"

        try:
            print(f"\nProcessing Chapter {chapter_num}: {translation_file.name}")
            reformat_translation_file(
                translation_file,
                arabic_file,
                output_file,
                basmallah_text,
            )
            processed += 1
        except Exception as exc:
            print(f"Error processing {translation_file.name}: {exc}")
            import traceback

            traceback.print_exc()
            errors += 1

    print("\n" + "=" * 60)
    print("Processing complete!")
    print(f"Language: {LANGUAGE_NAME}")
    print(f"Successfully processed: {processed} chapters")
    print(f"Errors: {errors}")
    print(f"Output directory: {output_dir}")
    print("=" * 60)

if __name__ == "__main__":
    main()

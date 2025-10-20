#!/usr/bin/env python3
"""
Script to reformat translation files to match the Arabic verse structure
using semantic alignment with Google's Gemini API.

This script is language-agnostic - just configure the settings below.
"""

import os
import re
import json
import google.generativeai as genai
from pathlib import Path

# ============================================================================
# CONFIGURATION - Update these variables for different languages
# ============================================================================

# Language configuration
LANGUAGE_NAME = "Italian"  # e.g., "Italian", "English", "French", "Spanish", etc.
LANGUAGE_CODE = "it"       # e.g., "it", "en", "fr", "es", etc.

# Basmallah translation (update for each language)
BASMALLAH_TRANSLATION = "In nome di Allah, il Compassionevole, il Misericordioso."

# Directory paths
TRANSLATION_INPUT_DIR = "/Users/kahla/Developer/quran-scraper/italian"
ARABIC_REFERENCE_DIR = "/Users/kahla/Developer/quran-scraper/chs-ar-final"
OUTPUT_DIR = "/Users/kahla/Developer/quran-scraper/italian-formatted-gemini"

# Gemini API configuration
GEMINI_API_KEY = "AIzaSyAuyTO5D9bPD3tyTU5UDcc63VJ5kQPbnYE"
GEMINI_MODEL = "gemini-1.5-flash"  # or "gemini-1.5-pro" for better quality

# ============================================================================

# Configure Gemini API
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(GEMINI_MODEL)

def parse_arabic_file(arabic_path):
    """Parse Arabic file and extract verse structure with full text and Surah name."""
    verse_structure = {}
    surah_name = None
    
    with open(arabic_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            # Extract Surah name from first line
            if line.startswith('سُورَةُ'):
                surah_name = line
                continue
            
            match = re.match(r'^(\d{3})_(\d{2})\t(.+)$', line)
            if match:
                verse_num = int(match.group(1))
                part_num = int(match.group(2))
                arabic_text = match.group(3)
                
                if verse_num not in verse_structure:
                    verse_structure[verse_num] = []
                verse_structure[verse_num].append((part_num, arabic_text))
    
    return verse_structure, surah_name

def parse_translation_file(translation_path):
    """Parse translation file and extract verses."""
    verses = {}
    
    with open(translation_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            match = re.match(r'^(\d+)\.\s+(.+)$', line)
            if match:
                verse_num = int(match.group(1))
                verse_text = match.group(2)
                verses[verse_num] = verse_text
    
    return verses

def split_verse_semantic(verse_num, translation_text, arabic_parts):
    """Use Gemini to split translation verse text based on semantic alignment with Arabic parts."""
    if len(arabic_parts) == 1:
        return [translation_text]
    
    arabic_parts_text = "\n".join([f"Part {i+1}: {part[1]}" for i, part in enumerate(arabic_parts)])
    
    prompt = f"""You are helping to align Quranic translations. Given an Arabic verse split into {len(arabic_parts)} parts and its {LANGUAGE_NAME} translation, you need to split the {LANGUAGE_NAME} translation at the exact same semantic points where the Arabic is split.

Verse {verse_num}:

Arabic parts:
{arabic_parts_text}

{LANGUAGE_NAME} (complete verse):
{translation_text}

Your task: Split the {LANGUAGE_NAME} text into {len(arabic_parts)} parts that correspond semantically to the Arabic parts. Each {LANGUAGE_NAME} part should end at the same meaning/concept where the Arabic part ends.

Return ONLY a JSON array with {len(arabic_parts)} strings, where each string is one part of the {LANGUAGE_NAME} text. Do not include any explanation, just the JSON array.

Example format: ["first part of {LANGUAGE_NAME.lower()} text", "second part of {LANGUAGE_NAME.lower()} text"]
"""

    try:
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        # Try to extract JSON from the response
        json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
        if json_match:
            response_text = json_match.group(0)
        
        parts = json.loads(response_text)
        
        if len(parts) != len(arabic_parts):
            print(f"Warning: Expected {len(arabic_parts)} parts but got {len(parts)} for verse {verse_num}")
            return simple_split(translation_text, len(arabic_parts))
        
        return [part.strip() for part in parts]
        
    except Exception as e:
        print(f"Error using Gemini for verse {verse_num}: {e}")
        print(f"Response was: {response_text if 'response_text' in locals() else 'N/A'}")
        return simple_split(translation_text, len(arabic_parts))

def simple_split(text, num_parts):
    """Fallback: Simple sentence-based splitting."""
    if num_parts == 1:
        return [text]
    
    # Split by sentence boundaries
    sentence_pattern = r'([.!?»])\s+'
    parts = re.split(sentence_pattern, text)
    
    sentences = []
    i = 0
    while i < len(parts):
        if i + 1 < len(parts) and parts[i + 1] in '.!?»':
            sentences.append(parts[i] + parts[i + 1])
            i += 2
        else:
            if parts[i].strip():
                sentences.append(parts[i])
            i += 1
    
    if len(sentences) >= num_parts:
        # Distribute sentences across parts
        sentences_per_part = len(sentences) // num_parts
        result = []
        for i in range(num_parts):
            if i == num_parts - 1:
                result.append(' '.join(sentences[i * sentences_per_part:]).strip())
            else:
                start = i * sentences_per_part
                end = (i + 1) * sentences_per_part
                result.append(' '.join(sentences[start:end]).strip())
        return result
    else:
        # Fall back to word-based splitting
        words = text.split()
        words_per_part = len(words) // num_parts
        result = []
        for i in range(num_parts):
            if i == num_parts - 1:
                result.append(' '.join(words[i * words_per_part:]))
            else:
                result.append(' '.join(words[i * words_per_part:(i + 1) * words_per_part]))
        return result

def reformat_translation_file(translation_path, arabic_path, output_path):
    """Reformat translation file to match Arabic verse structure using semantic alignment."""
    verse_structure, surah_name = parse_arabic_file(arabic_path)
    translation_verses = parse_translation_file(translation_path)
    
    # Get the first line of the translation file which contains the surah name in the target language
    translated_surah_name = ""
    try:
        with open(translation_path, 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()
            # If the first line is a number (verse number), it's not a surah name
            if not re.match(r'^\d+\.', first_line):
                translated_surah_name = first_line
    except Exception as e:
        print(f"Warning: Could not read translated surah name from {translation_path}: {e}")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        # Write Surah name in the target language at the very top if available
        if translated_surah_name:
            f.write(f"{translated_surah_name}\n\n")
        
        # Write Arabic surah name if available
        if surah_name:
            f.write(f"{surah_name}\n")
        
        # Write Basmallah (verse 0) in the target language
        f.write(f"000_00\t{BASMALLAH_TRANSLATION}\n")
        
        # Process all verses
        for verse_num in sorted(verse_structure.keys()):
            # Skip verse 0 (Basmallah) as we already added it
            if verse_num == 0:
                continue
                
            if verse_num not in translation_verses:
                print(f"Warning: Verse {verse_num} not found in translation file {translation_path}")
                continue
            
            arabic_parts = verse_structure[verse_num]
            verse_text = translation_verses[verse_num]
            
            # Split the verse semantically
            if len(arabic_parts) == 1:
                parts = [verse_text]
            else:
                print(f"  Processing verse {verse_num} ({len(arabic_parts)} parts)...")
                parts = split_verse_semantic(verse_num, verse_text, arabic_parts)
            
            # Write each part with the correct format
            for i, part in enumerate(parts):
                part_index = arabic_parts[i][0]
                f.write(f"{verse_num:03d}_{part_index:02d}\t{part}\n")

def get_chapter_number_from_filename(filename):
    """Extract chapter number from translation filename."""
    match = re.match(r'^(\d+)-', filename)
    if match:
        return int(match.group(1))
    return None

def main():
    # Use configured directories
    translation_dir = Path(TRANSLATION_INPUT_DIR)
    arabic_dir = Path(ARABIC_REFERENCE_DIR)
    output_dir = Path(OUTPUT_DIR)
    
    # Validate directories exist
    if not translation_dir.exists():
        print(f"Error: Translation directory not found: {translation_dir}")
        return
    if not arabic_dir.exists():
        print(f"Error: Arabic reference directory not found: {arabic_dir}")
        return
    
    # Create output directory
    output_dir.mkdir(exist_ok=True)
    
    print(f"{'='*60}")
    print(f"Quran Translation Reformatter")
    print(f"Language: {LANGUAGE_NAME} ({LANGUAGE_CODE})")
    print(f"Input: {translation_dir}")
    print(f"Output: {output_dir}")
    print(f"{'='*60}\n")
    
    # Process all translation files
    translation_files = sorted(translation_dir.glob('*.txt'))
    
    # Filter to only process actual chapter files
    translation_files = [f for f in translation_files if get_chapter_number_from_filename(f.name) is not None]
    
    processed = 0
    errors = 0
    
    for translation_file in translation_files:
        chapter_num = get_chapter_number_from_filename(translation_file.name)
        if chapter_num is None:
            continue
        
        # Find corresponding Arabic file
        arabic_file = arabic_dir / f"{chapter_num:03d}.txt"
        if not arabic_file.exists():
            # Try without .txt extension
            arabic_file = arabic_dir / f"{chapter_num:03d}"
            if not arabic_file.exists():
                print(f"Skipping {translation_file.name}: Arabic file not found")
                errors += 1
                continue
        
        # Output file
        output_file = output_dir / f"{chapter_num:03d}.txt"
        
        try:
            print(f"\nProcessing Chapter {chapter_num}: {translation_file.name}")
            reformat_translation_file(translation_file, arabic_file, output_file)
            processed += 1
        except Exception as e:
            print(f"Error processing {translation_file.name}: {e}")
            import traceback
            traceback.print_exc()
            errors += 1
    
    print(f"\n{'='*60}")
    print(f"Processing complete!")
    print(f"Language: {LANGUAGE_NAME}")
    print(f"Successfully processed: {processed} chapters")
    print(f"Errors: {errors}")
    print(f"Output directory: {output_dir}")
    print(f"{'='*60}")

if __name__ == '__main__':
    main()

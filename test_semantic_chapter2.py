#!/usr/bin/env python3
"""
Test script to process just Chapter 2 with semantic alignment.
"""

import os
import re
import json
from pathlib import Path
from anthropic import Anthropic

# Initialize Anthropic client
client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))


def parse_arabic_file(arabic_path):
    """Parse Arabic file and extract verse structure with full text."""
    verse_structure = {}
    
    with open(arabic_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('سُورَةُ'):
                continue
            
            match = re.match(r'^(\d{3})_(\d{2})\t(.+)$', line)
            if match:
                verse_num = int(match.group(1))
                part_num = int(match.group(2))
                arabic_text = match.group(3)
                
                if verse_num not in verse_structure:
                    verse_structure[verse_num] = []
                verse_structure[verse_num].append((part_num, arabic_text))
    
    return verse_structure


def parse_italian_file(italian_path):
    """Parse Italian file and extract verses."""
    verses = {}
    
    with open(italian_path, 'r', encoding='utf-8') as f:
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


def split_italian_verse_semantic(verse_num, italian_text, arabic_parts):
    """Use AI to split Italian verse text based on semantic alignment with Arabic parts."""
    if len(arabic_parts) == 1:
        return [italian_text]
    
    arabic_parts_text = "\n".join([f"Part {i+1}: {part[1]}" for i, part in enumerate(arabic_parts)])
    
    prompt = f"""You are helping to align Quranic translations. Given an Arabic verse split into {len(arabic_parts)} parts and its Italian translation, you need to split the Italian translation at the exact same semantic points where the Arabic is split.

Verse {verse_num}:

Arabic parts:
{arabic_parts_text}

Italian (complete verse):
{italian_text}

Your task: Split the Italian text into {len(arabic_parts)} parts that correspond semantically to the Arabic parts. Each Italian part should end at the same meaning/concept where the Arabic part ends.

Return ONLY a JSON array with {len(arabic_parts)} strings, where each string is one part of the Italian text. Do not include any explanation, just the JSON array.

Example format: ["first part of italian text", "second part of italian text"]
"""

    try:
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1024,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        response_text = message.content[0].text.strip()
        
        # Extract JSON from response
        json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
        if json_match:
            response_text = json_match.group(0)
        
        parts = json.loads(response_text)
        
        if len(parts) != len(arabic_parts):
            print(f"Warning: Expected {len(arabic_parts)} parts but got {len(parts)} for verse {verse_num}")
            return None
        
        return [part.strip() for part in parts]
        
    except Exception as e:
        print(f"Error using AI for verse {verse_num}: {e}")
        if 'response_text' in locals():
            print(f"Response was: {response_text}")
        return None


def main():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY environment variable not set")
        print("Please set it with: export ANTHROPIC_API_KEY='your-api-key'")
        return
    
    italian_file = Path('/Users/kahla/Developer/quran-scraper/italian/002-Al-Baqara.txt')
    arabic_file = Path('/Users/kahla/Developer/quran-scraper/chs-ar-final/002.txt')
    output_file = Path('/Users/kahla/Developer/quran-scraper/002-test-semantic.txt')
    
    print("Loading files...")
    verse_structure = parse_arabic_file(arabic_file)
    italian_verses = parse_italian_file(italian_file)
    
    print(f"Processing Chapter 2...")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        for verse_num in sorted(verse_structure.keys()):
            if verse_num == 0 or verse_num not in italian_verses:
                continue
            
            arabic_parts = verse_structure[verse_num]
            verse_text = italian_verses[verse_num]
            
            if len(arabic_parts) == 1:
                parts = [verse_text]
            else:
                print(f"  Verse {verse_num} ({len(arabic_parts)} parts)...")
                parts = split_italian_verse_semantic(verse_num, verse_text, arabic_parts)
                if parts is None:
                    print(f"  Skipping verse {verse_num} due to error")
                    continue
            
            for i, part in enumerate(parts):
                part_index = arabic_parts[i][0]
                f.write(f"{verse_num:03d}_{part_index:02d}\t{part}\n")
    
    print(f"\nDone! Output written to: {output_file}")
    print("\nFirst few split verses:")
    os.system(f"grep -E '^(019|020|022|025|026)_' {output_file}")


if __name__ == '__main__':
    main()

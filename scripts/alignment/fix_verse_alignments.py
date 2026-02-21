#!/usr/bin/env python3
"""
Script to fix verse split misalignments between translations and Arabic reference.
Finds verses with yy>0 splits, batches them, and uses LLMs to semantically align splits.
"""

import os
import re
import json
import argparse
import asyncio
import aiohttp
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import time

# API imports
import openai
import google.generativeai as genai

@dataclass
class VerseData:
    verse_id: str  # e.g., "019_01"
    arabic_text: str
    translation_text: str
    chapter: int
    verse_num: int
    split_num: int

@dataclass
class BatchResult:
    original_verses: List[VerseData]
    corrected_splits: List[Dict[str, str]]  # [{"019_00": "text1", "019_01": "text2"}, ...]

class LLMClient:
    def __init__(self, provider: str, api_key: str):
        self.provider = provider.lower()
        self.api_key = api_key

        if self.provider == "openai":
            self.client = openai.AsyncOpenAI(api_key=api_key)
        elif self.provider == "gemini":
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-2.0-flash-exp')

    async def process_batch(self, batch: List[VerseData]) -> List[Dict[str, str]]:
        """Process a batch of misaligned verses and return corrected splits."""

        # Group by verse number to handle complete verse splits
        verse_groups = {}
        for verse in batch:
            key = f"{verse.chapter:03d}_{verse.verse_num:03d}"
            if key not in verse_groups:
                verse_groups[key] = []
            verse_groups[key].append(verse)

        prompt = self._build_prompt(verse_groups)

        if self.provider == "openai":
            return await self._call_openai(prompt, verse_groups)
        elif self.provider == "gemini":
            return await self._call_gemini(prompt, verse_groups)

    def _build_prompt(self, verse_groups: Dict[str, List[VerseData]]) -> str:
        prompt = """You are a Quranic translation alignment expert. Your task is to semantically split translation verses to match the Arabic reference splits exactly.

RULES:
1. Split the translation at the SAME semantic point where Arabic splits
2. Do NOT change, add, or remove any words from the translation
3. Only redistribute existing words between splits
4. Maintain the exact same meaning and word order
5. Each split should be a complete semantic unit

INPUT FORMAT: For each verse, you'll see the Arabic reference splits and the misaligned translation.

OUTPUT FORMAT: Return ONLY a JSON object with corrected splits:
```json
{
  "chapter_verse": {
    "xxx_00": "first split text",
    "xxx_01": "second split text"
  }
}
```

EXAMPLES:
Arabic: "019_00": "أَوۡ كَصَيِّبٖ مِّنَ ٱلسَّمَآءِ فِيهِ ظُلُمَٰتٞ وَرَعۡدٞ وَبَرۡقٞ يَجۡعَلُونَ أَصَٰبِعَهُمۡ فِيٓ ءَاذَانِهِم مِّنَ ٱلصَّوَٰعِقِ حَذَرَ ٱلۡمَوۡتِۚ"
Arabic: "019_01": "وَٱللَّهُ مُحِيطُۢ بِٱلۡكَٰفِرِينَ"
Translation: "019_01": "El estampido del rayo al caer, les hace taparse los oídos por temor a la muerte.Pero Allah tiene rodeados a los incrédulos."

Correct Output:
```json
{
  "002_019": {
    "019_00": "El estampido del rayo al caer, les hace taparse los oídos por temor a la muerte.",
    "019_01": "Pero Allah tiene rodeados a los incrédulos."
  }
}
```

NOW PROCESS THESE VERSES:

"""

        for verse_key, verses in verse_groups.items():
            chapter = verses[0].chapter
            verse_num = verses[0].verse_num

            prompt += f"\nVERSE {chapter:03d}_{verse_num:03d}:\n"
            prompt += "Arabic reference splits:\n"

            # Add all Arabic splits for this verse
            for verse in sorted(verses, key=lambda x: x.split_num):
                prompt += f'  "{verse.verse_id}": "{verse.arabic_text}"\n'

            prompt += "Translation to split:\n"
            # Combine all translation parts (they may be incorrectly split)
            combined_translation = " ".join([v.translation_text.strip() for v in sorted(verses, key=lambda x: x.split_num)])
            prompt += f'  Combined: "{combined_translation}"\n'

        prompt += "\nReturn the corrected JSON splits:"
        return prompt

    async def _call_openai(self, prompt: str, verse_groups: Dict[str, List[VerseData]]) -> List[Dict[str, str]]:
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a precise Quranic translation alignment expert."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=2000
            )

            result_text = response.choices[0].message.content.strip()
            # Extract JSON from response
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', result_text, re.DOTALL)
            if json_match:
                result_text = json_match.group(1)

            return json.loads(result_text)
        except Exception as e:
            print(f"OpenAI API error: {e}")
            return {}

    async def _call_gemini(self, prompt: str, verse_groups: Dict[str, List[VerseData]]) -> List[Dict[str, str]]:
        try:
            response = await self.model.generate_content_async(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1,
                    max_output_tokens=2000
                )
            )

            result_text = response.text.strip()
            # Extract JSON from response
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', result_text, re.DOTALL)
            if json_match:
                result_text = json_match.group(1)

            return json.loads(result_text)
        except Exception as e:
            print(f"Gemini API error: {e}")
            return {}

class VerseAlignmentFixer:
    def __init__(self, arabic_dir: str, translations_dir: str, provider: str, api_key: str):
        self.arabic_dir = Path(arabic_dir)
        self.translations_dir = Path(translations_dir)
        self.llm_client = LLMClient(provider, api_key)

    def find_misaligned_verses(self, translation_lang: str) -> List[VerseData]:
        """Find all verses with yy>0 that might be misaligned."""
        misaligned = []
        translation_path = self.translations_dir / translation_lang

        if not translation_path.exists():
            print(f"Translation directory not found: {translation_path}")
            return misaligned

        # Process each chapter
        for chapter_file in sorted(translation_path.glob("*.txt")):
            if not chapter_file.stem.isdigit():
                continue  # Skip non-numeric files like surah names
            chapter_num = int(chapter_file.stem)
            arabic_file = self.arabic_dir / f"{chapter_num:03d}"

            if not arabic_file.exists():
                print(f"Arabic reference not found: {arabic_file}")
                continue

            # Load Arabic reference
            arabic_verses = self._load_verse_file(arabic_file)
            translation_verses = self._load_verse_file(chapter_file)

            # Find verses with splits (yy>0)
            for verse_id, trans_text in translation_verses.items():
                match = re.match(r'(\d+)_(\d+)', verse_id)
                if match:
                    verse_num, split_num = int(match.group(1)), int(match.group(2))

                    if split_num > 0:  # This is a split verse
                        arabic_text = arabic_verses.get(verse_id, "")
                        if arabic_text:
                            misaligned.append(VerseData(
                                verse_id=verse_id,
                                arabic_text=arabic_text,
                                translation_text=trans_text,
                                chapter=chapter_num,
                                verse_num=verse_num,
                                split_num=split_num
                            ))

        return misaligned

    def _load_verse_file(self, file_path: Path) -> Dict[str, str]:
        """Load verses from a file into a dictionary."""
        verses = {}
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('سُورَةُ'):  # Skip surah headers
                        # Split on tab
                        parts = line.split('\t', 1)
                        if len(parts) == 2:
                            verse_id, text = parts
                            verses[verse_id] = text
        except Exception as e:
            print(f"Error loading file {file_path}: {e}")

        return verses

    def create_batches(self, verses: List[VerseData], batch_size: int = 5) -> List[List[VerseData]]:
        """Create batches of verses for LLM processing."""
        batches = []
        for i in range(0, len(verses), batch_size):
            batches.append(verses[i:i + batch_size])
        return batches

    async def process_translation(self, translation_lang: str, batch_size: int = 5, delay: float = 1.0):
        """Process all misaligned verses in a translation."""
        print(f"Finding misaligned verses in {translation_lang}...")
        misaligned_verses = self.find_misaligned_verses(translation_lang)

        if not misaligned_verses:
            print(f"No misaligned verses found in {translation_lang}")
            return

        print(f"Found {len(misaligned_verses)} misaligned verses")

        # Create batches
        batches = self.create_batches(misaligned_verses, batch_size)

        # Process batches
        corrected_verses = {}
        for i, batch in enumerate(batches):
            print(f"Processing batch {i+1}/{len(batches)}...")

            try:
                result = await self.llm_client.process_batch(batch)
                corrected_verses.update(result)

                # Delay between batches to avoid rate limiting
                if i < len(batches) - 1:
                    await asyncio.sleep(delay)

            except Exception as e:
                print(f"Error processing batch {i+1}: {e}")

        # Apply corrections
        await self._apply_corrections(translation_lang, corrected_verses)

    async def _apply_corrections(self, translation_lang: str, corrections: Dict[str, Dict[str, str]]):
        """Apply the corrected splits to the translation files."""
        translation_path = self.translations_dir / translation_lang

        # Group corrections by chapter
        chapter_corrections = {}
        for verse_key, splits in corrections.items():
            chapter = int(verse_key.split('_')[0])
            if chapter not in chapter_corrections:
                chapter_corrections[chapter] = {}
            chapter_corrections[chapter].update(splits)

        # Apply corrections to each chapter file
        for chapter_num, chapter_splits in chapter_corrections.items():
            chapter_file = translation_path / f"{chapter_num:03d}.txt"

            if chapter_file.exists():
                # Load current verses
                verses = self._load_verse_file(chapter_file)

                # Apply corrections
                for verse_id, corrected_text in chapter_splits.items():
                    if verse_id in verses:
                        verses[verse_id] = corrected_text
                        print(f"Corrected {verse_id}: {corrected_text[:50]}...")

                # Write back to file
                self._write_verse_file(chapter_file, verses)

        print(f"Applied {len(corrections)} corrections to {translation_lang}")

    def _write_verse_file(self, file_path: Path, verses: Dict[str, str]):
        """Write verses back to a file."""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                for verse_id in sorted(verses.keys()):
                    f.write(f"{verse_id}\t{verses[verse_id]}\n")
        except Exception as e:
            print(f"Error writing file {file_path}: {e}")

async def process_all_translations(fixer: VerseAlignmentFixer, batch_size: int, delay: float):
    """Process all available translations."""
    translations_dir = Path(fixer.translations_dir)

    # Get all translation directories
    translation_dirs = [d.name for d in translations_dir.iterdir()
                       if d.is_dir() and not d.name.startswith('.')]
    translation_dirs.sort()

    print(f"Found {len(translation_dirs)} translations to process:")
    for i, trans in enumerate(translation_dirs, 1):
        print(f"  {i:2d}. {trans}")

    confirm = input(f"\nProcess all {len(translation_dirs)} translations? (y/N): ").strip().lower()
    if confirm != 'y':
        print("Cancelled.")
        return

    # Process each translation
    for i, translation_lang in enumerate(translation_dirs, 1):
        print(f"\n{'='*60}")
        print(f"Processing {i}/{len(translation_dirs)}: {translation_lang}")
        print(f"{'='*60}")

        try:
            await fixer.process_translation(
                translation_lang=translation_lang,
                batch_size=batch_size,
                delay=delay
            )
            print(f"✅ {translation_lang}: Completed")
        except Exception as e:
            print(f"❌ {translation_lang}: Error - {e}")

    print(f"\n🎉 Finished processing all translations!")

async def main():
    parser = argparse.ArgumentParser(description="Fix verse split alignment issues")
    parser.add_argument("--provider", choices=["openai", "gemini"], required=True,
                        help="LLM provider (openai or gemini)")
    parser.add_argument("--api-key", required=True, help="API key for the chosen provider")
    parser.add_argument("--translation", help="Translation language code (e.g., es-navio). If not specified, processes all translations.")
    parser.add_argument("--batch-size", type=int, default=5, help="Batch size for LLM requests")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay between batches in seconds")
    parser.add_argument("--arabic-dir", default="data/chs-ar-final", help="Arabic reference directory")
    parser.add_argument("--translations-dir", default="data/ksu-translations-formatted", help="Translations directory")

    args = parser.parse_args()

    # Validate API key
    if args.provider == "openai" and not args.api_key.startswith("sk-"):
        print("Warning: OpenAI API key should start with 'sk-'")

    fixer = VerseAlignmentFixer(
        arabic_dir=args.arabic_dir,
        translations_dir=args.translations_dir,
        provider=args.provider,
        api_key=args.api_key
    )

    if args.translation:
        # Process single translation
        await fixer.process_translation(
            translation_lang=args.translation,
            batch_size=args.batch_size,
            delay=args.delay
        )
    else:
        # Process all translations
        await process_all_translations(fixer, args.batch_size, args.delay)

if __name__ == "__main__":
    asyncio.run(main())
#!/usr/bin/env python3
"""
Improved script to fix verse split misalignments between translations and Arabic reference.
Includes comprehensive validation and better prompt engineering.
"""

import os
import re
import json
import argparse
import asyncio
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass
from collections import Counter

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
class ValidationResult:
    is_valid: bool
    errors: List[str]
    warnings: List[str]

class LLMClient:
    def __init__(self, provider: str, api_key: str):
        self.provider = provider.lower()
        self.api_key = api_key

        if self.provider == "openai":
            self.client = openai.AsyncOpenAI(api_key=api_key)
        elif self.provider == "gemini":
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-2.0-flash-exp')

    async def process_batch(self, batch: List[VerseData]) -> Dict[str, Dict[str, str]]:
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
        """Build an improved, concise prompt for semantic alignment."""

        prompt = """You are a Quranic translation alignment specialist. Your ONLY task: redistribute existing translation words to match Arabic verse splits.

CRITICAL RULES:
1. NEVER add, remove, or modify ANY words in the translation
2. ONLY redistribute existing words between splits at the SAME semantic boundary as Arabic
3. The split IDs (xxx_00, xxx_01, etc.) must EXACTLY match Arabic reference
4. Combine ALL translation text parts, then split at the same point as Arabic
5. Each split must contain complete semantic units (full clauses/sentences)

INPUT: Arabic reference splits + Misaligned translation text
OUTPUT: JSON with corrected splits using EXACT original words

Example:
Arabic Reference:
  "019_00": "أَوۡ كَصَيِّبٖ... حَذَرَ ٱلۡمَوۡتِۚ" (storm, thunder... fear of death)
  "019_01": "وَٱللَّهُ مُحِيطُۢ بِٱلۡكَٰفِرِينَ" (And Allah encompasses...)

Current Translation (WRONG):
  "019_00": "Or like a storm with darkness, thunder."
  "019_01": "They put fingers in ears fearing death. Allah encompasses disbelievers."

Corrected Output (RIGHT):
```json
{
  "002_019": {
    "019_00": "Or like a storm with darkness, thunder. They put fingers in ears fearing death.",
    "019_01": "Allah encompasses disbelievers."
  }
}
```

PROCESS THESE VERSES:
"""

        for verse_key, verses in verse_groups.items():
            chapter = verses[0].chapter
            verse_num = verses[0].verse_num

            prompt += f"\n{'='*60}\n"
            prompt += f"VERSE {chapter:03d}_{verse_num:03d}:\n"
            prompt += f"{'='*60}\n"

            # Arabic reference splits
            prompt += "Arabic Reference (split points to match):\n"
            for verse in sorted(verses, key=lambda x: x.split_num):
                arabic_preview = verse.arabic_text[:60] + "..." if len(verse.arabic_text) > 60 else verse.arabic_text
                prompt += f'  "{verse.verse_id}": "{arabic_preview}"\n'

            # Combined translation text
            prompt += "\nCurrent Translation (all parts combined):\n"
            combined_translation = " ".join([v.translation_text.strip() for v in sorted(verses, key=lambda x: x.split_num)])
            prompt += f'  "{combined_translation}"\n'

            prompt += f"\nRequired: Split into {len(verses)} parts with IDs: "
            prompt += ", ".join([f'"{v.verse_id}"' for v in sorted(verses, key=lambda x: x.split_num)])
            prompt += "\n"

        prompt += f"\n{'='*60}\n"
        prompt += "Return ONLY the JSON object with corrected splits:\n"
        prompt += "```json\n{\n  \"chapter_verse\": {\"xxx_yy\": \"text\", ...}\n}\n```"

        return prompt

    async def _call_openai(self, prompt: str, verse_groups: Dict[str, List[VerseData]]) -> Dict[str, Dict[str, str]]:
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a precise Quranic translation alignment expert. You ONLY redistribute existing words, NEVER add or remove content."},
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

    async def _call_gemini(self, prompt: str, verse_groups: Dict[str, List[VerseData]]) -> Dict[str, Dict[str, str]]:
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

class VerseValidator:
    """Validates verse alignment corrections."""

    @staticmethod
    def normalize_text(text: str) -> str:
        """Normalize text for comparison (lowercase, remove extra spaces/punctuation)."""
        # Remove punctuation and normalize spaces
        text = re.sub(r'[^\w\s]', ' ', text.lower())
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    @staticmethod
    def get_word_set(text: str) -> Counter:
        """Get word frequency counter from text."""
        normalized = VerseValidator.normalize_text(text)
        return Counter(normalized.split())

    @staticmethod
    def validate_no_content_change(original_texts: List[str], corrected_texts: List[str]) -> ValidationResult:
        """Validate that no words were added or removed, only redistributed."""
        errors = []
        warnings = []

        # Combine all original and corrected texts
        original_combined = " ".join(original_texts)
        corrected_combined = " ".join(corrected_texts)

        # Get word counts
        original_words = VerseValidator.get_word_set(original_combined)
        corrected_words = VerseValidator.get_word_set(corrected_combined)

        # Check for added words
        added = corrected_words - original_words
        if added:
            errors.append(f"Words added: {list(added.elements())}")

        # Check for removed words
        removed = original_words - corrected_words
        if removed:
            errors.append(f"Words removed: {list(removed.elements())}")

        # Check total word count
        if sum(original_words.values()) != sum(corrected_words.values()):
            warnings.append(f"Word count changed: {sum(original_words.values())} → {sum(corrected_words.values())}")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    @staticmethod
    def validate_no_repetition(splits: List[str]) -> ValidationResult:
        """Validate that no text is repeated across splits."""
        errors = []
        warnings = []

        # Check each pair of splits for significant overlap
        for i, split1 in enumerate(splits):
            for j, split2 in enumerate(splits[i+1:], start=i+1):
                # Get sentences/phrases
                sentences1 = set([s.strip() for s in re.split(r'[.!?]', split1) if s.strip()])
                sentences2 = set([s.strip() for s in re.split(r'[.!?]', split2) if s.strip()])

                # Check for exact sentence repetition
                overlap = sentences1 & sentences2
                if overlap:
                    errors.append(f"Repeated text between splits {i} and {j}: {overlap}")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    @staticmethod
    def validate_split_ids(arabic_ids: Set[str], translation_ids: Set[str], verse_key: str) -> ValidationResult:
        """Validate that translation has exact same split IDs as Arabic."""
        errors = []
        warnings = []

        missing_in_translation = arabic_ids - translation_ids
        if missing_in_translation:
            errors.append(f"Translation missing Arabic IDs: {sorted(missing_in_translation)}")

        extra_in_translation = translation_ids - arabic_ids
        if extra_in_translation:
            errors.append(f"Translation has extra IDs not in Arabic: {sorted(extra_in_translation)}")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

class VerseAlignmentFixer:
    def __init__(self, arabic_dir: str, translations_dir: str, provider: str, api_key: str):
        self.arabic_dir = Path(arabic_dir)
        self.translations_dir = Path(translations_dir)
        self.llm_client = LLMClient(provider, api_key)
        self.validator = VerseValidator()

    def find_misaligned_verses(self, translation_lang: str) -> List[VerseData]:
        """Find all verses with splits that need alignment checking."""
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

            # Load both files
            arabic_verses = self._load_verse_file(arabic_file)
            translation_verses = self._load_verse_file(chapter_file)

            # Find all verses with splits (group by verse number)
            verse_splits = {}
            for verse_id in arabic_verses.keys():
                match = re.match(r'(\d+)_(\d+)', verse_id)
                if match:
                    verse_num, split_num = int(match.group(1)), int(match.group(2))
                    if verse_num not in verse_splits:
                        verse_splits[verse_num] = set()
                    verse_splits[verse_num].add(verse_id)

            # Check verses that have splits in Arabic (split_num > 0)
            for verse_num, arabic_ids in verse_splits.items():
                # Get all split IDs for this verse in Arabic
                split_ids = [vid for vid in arabic_ids if int(vid.split('_')[1]) > 0]

                if split_ids:  # This verse has splits in Arabic
                    # Collect all data for this verse
                    for verse_id in sorted(arabic_ids):
                        arabic_text = arabic_verses.get(verse_id, "")
                        trans_text = translation_verses.get(verse_id, "")

                        match = re.match(r'(\d+)_(\d+)', verse_id)
                        verse_num_parsed, split_num = int(match.group(1)), int(match.group(2))

                        if arabic_text and trans_text:
                            misaligned.append(VerseData(
                                verse_id=verse_id,
                                arabic_text=arabic_text,
                                translation_text=trans_text,
                                chapter=chapter_num,
                                verse_num=verse_num_parsed,
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
        """Create batches of complete verses for LLM processing."""
        # Group by verse first
        verse_groups = {}
        for verse in verses:
            key = f"{verse.chapter:03d}_{verse.verse_num:03d}"
            if key not in verse_groups:
                verse_groups[key] = []
            verse_groups[key].append(verse)

        # Create batches of complete verses
        batches = []
        current_batch = []
        current_count = 0

        for verse_key, verse_data in verse_groups.items():
            if current_count >= batch_size and current_batch:
                batches.append(current_batch)
                current_batch = []
                current_count = 0

            current_batch.extend(verse_data)
            current_count += 1

        if current_batch:
            batches.append(current_batch)

        return batches

    async def process_translation(self, translation_lang: str, batch_size: int = 5, delay: float = 1.0):
        """Process all misaligned verses in a translation with validation."""
        print(f"Finding verses with splits in {translation_lang}...")
        misaligned_verses = self.find_misaligned_verses(translation_lang)

        if not misaligned_verses:
            print(f"No verses with splits found in {translation_lang}")
            return

        print(f"Found {len(misaligned_verses)} verse parts with splits")

        # Create batches
        batches = self.create_batches(misaligned_verses, batch_size)
        print(f"Processing {len(batches)} batches...")

        # Process batches
        all_corrections = {}
        validation_failures = []

        for i, batch in enumerate(batches):
            print(f"\nBatch {i+1}/{len(batches)}...")

            try:
                result = await self.llm_client.process_batch(batch)

                # Validate each corrected verse
                for verse_key, corrected_splits in result.items():
                    # Get original texts for this verse
                    original_texts = [v.translation_text for v in batch if f"{v.chapter:03d}_{v.verse_num:03d}" == verse_key]
                    corrected_texts = list(corrected_splits.values())

                    # Validate no content change
                    content_validation = self.validator.validate_no_content_change(original_texts, corrected_texts)
                    if not content_validation.is_valid:
                        print(f"  ❌ {verse_key}: Content validation failed:")
                        for error in content_validation.errors:
                            print(f"     - {error}")
                        validation_failures.append((verse_key, "content_change", content_validation.errors))
                        continue

                    # Validate no repetition
                    repetition_validation = self.validator.validate_no_repetition(corrected_texts)
                    if not repetition_validation.is_valid:
                        print(f"  ⚠️  {verse_key}: Repetition detected:")
                        for error in repetition_validation.errors:
                            print(f"     - {error}")

                    # Validation passed
                    all_corrections[verse_key] = corrected_splits
                    print(f"  ✅ {verse_key}: Validated and corrected")

                # Delay between batches
                if i < len(batches) - 1:
                    await asyncio.sleep(delay)

            except Exception as e:
                print(f"  ❌ Error processing batch {i+1}: {e}")

        # Report validation failures
        if validation_failures:
            print(f"\n⚠️  {len(validation_failures)} verses failed validation and were NOT corrected")

        # Apply corrections
        if all_corrections:
            await self._apply_corrections(translation_lang, all_corrections)
        else:
            print(f"\nNo corrections to apply for {translation_lang}")

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
                        print(f"  Updated {verse_id}")

                # Write back to file
                self._write_verse_file(chapter_file, verses)

        print(f"\n✅ Applied {len(corrections)} corrections to {translation_lang}")

    def _write_verse_file(self, file_path: Path, verses: Dict[str, str]):
        """Write verses back to a file."""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                for verse_id in sorted(verses.keys()):
                    f.write(f"{verse_id}\t{verses[verse_id]}\n")
        except Exception as e:
            print(f"Error writing file {file_path}: {e}")

async def main():
    parser = argparse.ArgumentParser(description="Fix verse split alignment issues with validation")
    parser.add_argument("--provider", choices=["openai", "gemini"], required=True,
                        help="LLM provider (openai or gemini)")
    parser.add_argument("--api-key", type=str, help="API key (or set OPENAI_API_KEY/GEMINI_API_KEY env var)")
    parser.add_argument("--translation", required=True, help="Translation language code (e.g., es-navio)")
    parser.add_argument("--batch-size", type=int, default=3, help="Batch size for LLM requests")
    parser.add_argument("--delay", type=float, default=1.5, help="Delay between batches in seconds")
    parser.add_argument("--arabic-dir", default="data/chs-ar-final", help="Arabic reference directory")
    parser.add_argument("--translations-dir", default="data/ksu-translations-formatted", help="Translations directory")

    args = parser.parse_args()

    # Get API key from argument or environment variable
    api_key = args.api_key
    if not api_key:
        if args.provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                print("❌ Error: OpenAI API key not found.")
                print("   Provide via --api-key or set OPENAI_API_KEY environment variable")
                return
        elif args.provider == "gemini":
            api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
            if not api_key:
                print("❌ Error: Gemini API key not found.")
                print("   Provide via --api-key or set GEMINI_API_KEY/GOOGLE_API_KEY environment variable")
                return

    print(f"Using {args.provider.upper()} API")

    fixer = VerseAlignmentFixer(
        arabic_dir=args.arabic_dir,
        translations_dir=args.translations_dir,
        provider=args.provider,
        api_key=api_key
    )

    await fixer.process_translation(
        translation_lang=args.translation,
        batch_size=args.batch_size,
        delay=args.delay
    )

if __name__ == "__main__":
    asyncio.run(main())

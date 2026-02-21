#!/usr/bin/env python3
"""
Verse alignment fixer with retry logic for validation failures.
When LLM response fails validation, retries with enhanced prompt.
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
    verse_id: str
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

    async def process_batch(self, batch: List[VerseData], retry_mode: bool = False,
                          previous_error: Optional[str] = None) -> Dict[str, Dict[str, str]]:
        """Process a batch with optional retry enhancement."""
        verse_groups = {}
        for verse in batch:
            key = f"{verse.chapter:03d}_{verse.verse_num:03d}"
            if key not in verse_groups:
                verse_groups[key] = []
            verse_groups[key].append(verse)

        prompt = self._build_prompt(verse_groups, retry_mode, previous_error)

        if self.provider == "openai":
            return await self._call_openai(prompt, verse_groups)
        elif self.provider == "gemini":
            return await self._call_gemini(prompt, verse_groups)

    def _build_prompt(self, verse_groups: Dict[str, List[VerseData]],
                     retry_mode: bool = False, previous_error: Optional[str] = None) -> str:
        """Build prompt with enhanced instructions on retry."""

        retry_warning = ""
        if retry_mode and previous_error:
            retry_warning = f"""
⚠️ RETRY ATTEMPT - Previous attempt failed validation!
Error: {previous_error}

CRITICAL: You MUST follow these rules EXACTLY:
- Count every word in the original translation
- Use EXACTLY the same words in your output
- Only change word ORDER between splits
- Do NOT paraphrase, translate, or modify ANY words
- Verify word counts match before responding

"""

        prompt = f"""{retry_warning}You are a Quranic translation alignment specialist. Your ONLY task: redistribute existing translation words to match Arabic verse splits.

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
{{
  "002_019": {{
    "019_00": "Or like a storm with darkness, thunder. They put fingers in ears fearing death.",
    "019_01": "Allah encompasses disbelievers."
  }}
}}
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
        """Normalize text for comparison."""
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
        """Validate that no words were added or removed."""
        errors = []
        warnings = []

        original_combined = " ".join(original_texts)
        corrected_combined = " ".join(corrected_texts)

        original_words = VerseValidator.get_word_set(original_combined)
        corrected_words = VerseValidator.get_word_set(corrected_combined)

        added = corrected_words - original_words
        if added:
            errors.append(f"Words added: {list(added.elements())}")

        removed = original_words - corrected_words
        if removed:
            errors.append(f"Words removed: {list(removed.elements())}")

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

        for i, split1 in enumerate(splits):
            for j, split2 in enumerate(splits[i+1:], start=i+1):
                sentences1 = set([s.strip() for s in re.split(r'[.!?]', split1) if s.strip()])
                sentences2 = set([s.strip() for s in re.split(r'[.!?]', split2) if s.strip()])

                overlap = sentences1 & sentences2
                if overlap:
                    errors.append(f"Repeated text between splits {i} and {j}: {overlap}")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

class VerseAlignmentFixer:
    def __init__(self, arabic_dir: str, translations_dir: str, provider: str, api_key: str, max_retries: int = 2):
        self.arabic_dir = Path(arabic_dir)
        self.translations_dir = Path(translations_dir)
        self.llm_client = LLMClient(provider, api_key)
        self.validator = VerseValidator()
        self.max_retries = max_retries

    def find_misaligned_verses(self, translation_lang: str) -> List[VerseData]:
        """Find all verses with splits that need alignment checking."""
        misaligned = []
        translation_path = self.translations_dir / translation_lang

        if not translation_path.exists():
            print(f"Translation directory not found: {translation_path}")
            return misaligned

        for chapter_file in sorted(translation_path.glob("*.txt")):
            if not chapter_file.stem.isdigit():
                continue

            chapter_num = int(chapter_file.stem)
            arabic_file = self.arabic_dir / f"{chapter_num:03d}"

            if not arabic_file.exists():
                continue

            arabic_verses = self._load_verse_file(arabic_file)
            translation_verses = self._load_verse_file(chapter_file)

            verse_splits = {}
            for verse_id in arabic_verses.keys():
                match = re.match(r'(\d+)_(\d+)', verse_id)
                if match:
                    verse_num, split_num = int(match.group(1)), int(match.group(2))
                    if verse_num not in verse_splits:
                        verse_splits[verse_num] = set()
                    verse_splits[verse_num].add(verse_id)

            for verse_num, arabic_ids in verse_splits.items():
                split_ids = [vid for vid in arabic_ids if int(vid.split('_')[1]) > 0]

                if split_ids:
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
                    if line and not line.startswith('سُورَةُ'):
                        parts = line.split('\t', 1)
                        if len(parts) == 2:
                            verse_id, text = parts
                            verses[verse_id] = text
        except Exception as e:
            print(f"Error loading file {file_path}: {e}")

        return verses

    def create_batches(self, verses: List[VerseData], batch_size: int = 5) -> List[List[VerseData]]:
        """Create batches of complete verses for LLM processing."""
        verse_groups = {}
        for verse in verses:
            key = f"{verse.chapter:03d}_{verse.verse_num:03d}"
            if key not in verse_groups:
                verse_groups[key] = []
            verse_groups[key].append(verse)

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

    async def process_translation(self, translation_lang: str, batch_size: int = 5,
                                 delay: float = 1.0, failures_log: Optional[str] = None):
        """Process all misaligned verses with retry logic."""
        print(f"Finding verses with splits in {translation_lang}...")
        misaligned_verses = self.find_misaligned_verses(translation_lang)

        if not misaligned_verses:
            print(f"No verses with splits found in {translation_lang}")
            return

        print(f"Found {len(misaligned_verses)} verse parts with splits")

        batches = self.create_batches(misaligned_verses, batch_size)
        print(f"Processing {len(batches)} batches with max {self.max_retries} retries per failure...\n")

        all_corrections = {}
        validation_failures = []
        retry_stats = {"total_retries": 0, "successful_retries": 0}

        for i, batch in enumerate(batches):
            print(f"Batch {i+1}/{len(batches)}...")

            try:
                # Initial attempt
                result = await self._process_batch_with_retry(
                    batch, retry_stats, validation_failures, all_corrections
                )

                await asyncio.sleep(delay)

            except Exception as e:
                print(f"  ❌ Error processing batch {i+1}: {e}")

        # Report results
        print(f"\n{'='*60}")
        print(f"VALIDATION RESULTS:")
        print(f"  Successful corrections: {len(all_corrections)}")
        print(f"  Failed validations: {len(validation_failures)}")
        print(f"  Total retry attempts: {retry_stats['total_retries']}")
        print(f"  Successful retries: {retry_stats['successful_retries']}")
        print(f"{'='*60}\n")

        # Write failures log if requested
        if validation_failures and failures_log:
            self._write_failures_log(translation_lang, validation_failures,
                                    misaligned_verses, failures_log)

        if all_corrections:
            await self._apply_corrections(translation_lang, all_corrections)
        else:
            print(f"No corrections to apply for {translation_lang}")

    async def _process_batch_with_retry(self, batch: List[VerseData],
                                       retry_stats: Dict, validation_failures: List,
                                       all_corrections: Dict) -> None:
        """Process a batch with retry logic for failed validations."""

        result = await self.llm_client.process_batch(batch, retry_mode=False)

        for verse_key, corrected_splits in result.items():
            original_texts = [v.translation_text for v in batch
                            if f"{v.chapter:03d}_{v.verse_num:03d}" == verse_key]
            corrected_texts = list(corrected_splits.values())

            # Try validation
            success, errors = self._validate_correction(
                verse_key, original_texts, corrected_texts
            )

            if success:
                all_corrections[verse_key] = corrected_splits
                print(f"  ✅ {verse_key}: Validated and corrected")
            else:
                # Retry logic
                retry_success = await self._retry_with_enhanced_prompt(
                    verse_key, batch, errors, retry_stats, all_corrections
                )

                if not retry_success:
                    validation_failures.append((verse_key, errors))
                    print(f"  ❌ {verse_key}: Failed after {self.max_retries} retries")

    def _validate_correction(self, verse_key: str, original_texts: List[str],
                           corrected_texts: List[str]) -> Tuple[bool, str]:
        """Validate correction and return success status with error details."""

        # Validate no content change
        content_validation = self.validator.validate_no_content_change(
            original_texts, corrected_texts
        )

        if not content_validation.is_valid:
            error_msg = "; ".join(content_validation.errors)
            return False, error_msg

        # Validate no repetition
        repetition_validation = self.validator.validate_no_repetition(corrected_texts)
        if not repetition_validation.is_valid:
            print(f"  ⚠️  {verse_key}: Repetition warning (non-blocking)")

        return True, ""

    async def _retry_with_enhanced_prompt(self, verse_key: str, batch: List[VerseData],
                                         previous_error: str, retry_stats: Dict,
                                         all_corrections: Dict) -> bool:
        """Retry failed verse with enhanced prompt."""

        # Get only the failed verse data
        verse_batch = [v for v in batch if f"{v.chapter:03d}_{v.verse_num:03d}" == verse_key]

        for attempt in range(1, self.max_retries + 1):
            retry_stats["total_retries"] += 1
            print(f"  🔄 {verse_key}: Retry {attempt}/{self.max_retries}...")

            # Call with retry mode and previous error
            result = await self.llm_client.process_batch(
                verse_batch,
                retry_mode=True,
                previous_error=previous_error
            )

            if verse_key in result:
                original_texts = [v.translation_text for v in verse_batch]
                corrected_texts = list(result[verse_key].values())

                success, errors = self._validate_correction(
                    verse_key, original_texts, corrected_texts
                )

                if success:
                    all_corrections[verse_key] = result[verse_key]
                    retry_stats["successful_retries"] += 1
                    print(f"  ✅ {verse_key}: Retry successful!")
                    return True
                else:
                    previous_error = errors
                    print(f"     Still failing: {errors}")

            await asyncio.sleep(0.5)  # Brief delay between retries

        return False

    async def _apply_corrections(self, translation_lang: str, corrections: Dict[str, Dict[str, str]]):
        """Apply the corrected splits to the translation files."""
        translation_path = self.translations_dir / translation_lang

        chapter_corrections = {}
        for verse_key, splits in corrections.items():
            chapter = int(verse_key.split('_')[0])
            if chapter not in chapter_corrections:
                chapter_corrections[chapter] = {}
            chapter_corrections[chapter].update(splits)

        for chapter_num, chapter_splits in chapter_corrections.items():
            chapter_file = translation_path / f"{chapter_num:03d}.txt"

            if chapter_file.exists():
                verses = self._load_verse_file(chapter_file)

                for verse_id, corrected_text in chapter_splits.items():
                    if verse_id in verses:
                        verses[verse_id] = corrected_text

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

    def _write_failures_log(self, translation_lang: str, validation_failures: List,
                           all_verses: List[VerseData], log_path: str):
        """Write failed validations to a JSON log file for manual review."""
        from datetime import datetime

        # Create detailed failure records
        failure_records = []

        for verse_key, errors in validation_failures:
            # Find the original verse data
            verse_parts = [v for v in all_verses
                         if f"{v.chapter:03d}_{v.verse_num:03d}" == verse_key]

            if verse_parts:
                # Get all splits for this verse
                verse_splits = {}
                arabic_splits = {}
                for v in sorted(verse_parts, key=lambda x: x.split_num):
                    verse_splits[v.verse_id] = v.translation_text
                    arabic_splits[v.verse_id] = v.arabic_text

                failure_record = {
                    "verse_key": verse_key,
                    "chapter": verse_parts[0].chapter,
                    "verse_number": verse_parts[0].verse_num,
                    "error": errors,
                    "original_translation_splits": verse_splits,
                    "arabic_reference_splits": arabic_splits,
                    "combined_translation": " ".join([v.translation_text
                                                     for v in sorted(verse_parts, key=lambda x: x.split_num)]),
                    "timestamp": datetime.now().isoformat()
                }
                failure_records.append(failure_record)

        # Write to JSON file
        output_data = {
            "translation": translation_lang,
            "total_failures": len(failure_records),
            "generated_at": datetime.now().isoformat(),
            "failures": failure_records
        }

        try:
            log_file = Path(log_path)
            log_file.parent.mkdir(parents=True, exist_ok=True)

            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)

            print(f"\n📝 Failures log written to: {log_path}")
            print(f"   Total failed verses: {len(failure_records)}")

        except Exception as e:
            print(f"Error writing failures log: {e}")

async def main():
    parser = argparse.ArgumentParser(description="Fix verse split alignment with retry logic")
    parser.add_argument("--provider", choices=["openai", "gemini"], required=True)
    parser.add_argument("--api-key", type=str, help="API key (or set OPENAI_API_KEY/GEMINI_API_KEY env var)")
    parser.add_argument("--translation", required=True)
    parser.add_argument("--batch-size", type=int, default=3)
    parser.add_argument("--delay", type=float, default=1.5)
    parser.add_argument("--max-retries", type=int, default=2, help="Max retry attempts for failed validations")
    parser.add_argument("--failures-log", type=str,
                        help="Path to write failures log JSON file (default: logs/failures-{translation}.json). Use --no-failures-log to disable.")
    parser.add_argument("--no-failures-log", action="store_true",
                        help="Disable failures logging")
    parser.add_argument("--arabic-dir", default="data/chs-ar-final")
    parser.add_argument("--translations-dir", default="data/ksu-translations-formatted")

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
    if args.api_key:
        print(f"API key source: command line argument")
    else:
        print(f"API key source: environment variable")

    # Set default failures log path if not disabled
    failures_log = args.failures_log
    if not args.no_failures_log and not failures_log:
        failures_log = f"logs/failures-{args.translation}.json"
        print(f"Failures will be logged to: {failures_log}")
    elif args.no_failures_log:
        failures_log = None
        print("Failures logging disabled")
    else:
        print(f"Failures will be logged to: {failures_log}")

    fixer = VerseAlignmentFixer(
        arabic_dir=args.arabic_dir,
        translations_dir=args.translations_dir,
        provider=args.provider,
        api_key=api_key,
        max_retries=args.max_retries
    )

    await fixer.process_translation(
        translation_lang=args.translation,
        batch_size=args.batch_size,
        delay=args.delay,
        failures_log=failures_log
    )

if __name__ == "__main__":
    asyncio.run(main())

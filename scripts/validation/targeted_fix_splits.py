#!/usr/bin/env python3
"""Targeted fix for known broken verses only.

This script only processes verses that are known to have issues, instead of
re-validating all multi-part verses. This is MUCH faster (323 verses vs 20,000+).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

import socket
import urllib.error
import urllib.parse
import urllib.request

# Set global socket timeout
socket.setdefaulttimeout(120)

LINE_ID_PATTERN = re.compile(r"^(\d{3})_(\d{2})\s")
WORD_CHAR_PATTERN = re.compile(r"\w", re.UNICODE)

SYSTEM_PROMPT = (
    "You verify whether multi-part Quran verse translations are split at the "
    "same semantic boundaries as the Arabic reference. You will receive batches "
    "of tasks—each task lists the reference segments, the current translation "
    "segments, the full translation text, and the number of chunks required. "
    "For every task:\n"
    "  • Keep the translation wording, punctuation, and diacritics exactly as "
    "provided; only move the split boundaries (trim surrounding whitespace if "
    "needed).\n"
    "  • Return JSON with a `verses` array.  Every entry must include "
    "`verse` (three-digit string such as \"019\"), `segments` (strings in "
    "order), and optionally `notes`.\n"
    "  • Produce exactly the requested number of contiguous segments.\n"
    "Do not emit prose outside the JSON response."
)

DEFAULT_BATCH_CHARS = 6000  # Larger batch for targeted fixes
BATCH_OVERHEAD_CHARS = 500

VerseEntries = List[tuple[int, str]]
SurahData = Dict[str, VerseEntries]


@dataclass
class VerseUpdate:
    indexes: List[int]
    segments: List[str]


@dataclass
class VerseTask:
    language: str
    file_path: Path
    surah_id: str
    verse: str
    reason: str
    reference_entries: VerseEntries
    translation_entries: VerseEntries
    effective_entries: VerseEntries
    reference_indexes: List[int]
    translation_indexes: List[int]
    effective_indexes: List[int]
    original_segments: List[str]
    translation_text: str
    payload: dict

    @property
    def file_label(self) -> str:
        return f"{self.language}/{self.file_path.name}"


class LLMClientError(RuntimeError):
    """Raised when an LLM request fails or returns malformed output."""


class BaseLLMClient:
    def __init__(self, model: str):
        self.model = model

    def resegment(self, task_payload: dict) -> dict:
        raise NotImplementedError


class OpenAIClient(BaseLLMClient):
    api_url = "https://api.openai.com/v1/chat/completions"

    def __init__(self, api_key: str, model: str):
        super().__init__(model)
        self.api_key = api_key

    def resegment(self, task_payload: dict) -> dict:
        body = {
            "model": self.model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(task_payload, ensure_ascii=False)},
            ],
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        response = _post_json(self.api_url, body, headers)
        try:
            content = response["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise LLMClientError(f"Unexpected OpenAI response: {response}") from exc
        return _parse_llm_json(content)


def _post_json(url: str, payload: dict, headers: dict) -> dict:
    """Make POST request with JSON payload, using requests if available."""
    if HAS_REQUESTS:
        try:
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=(30, 120)  # (connect timeout, read timeout)
            )
            response.raise_for_status()
            return response.json()
        except requests.Timeout as exc:
            raise LLMClientError(f"Request timed out calling {url}: {exc}") from exc
        except requests.RequestException as exc:
            raise LLMClientError(f"Failed to reach {url}: {exc}") from exc
    else:
        # Fallback to urllib
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise LLMClientError(f"HTTP {exc.code} calling {url}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise LLMClientError(f"Failed to reach {url}: {exc}") from exc
        except (TimeoutError, OSError) as exc:
            raise LLMClientError(f"Request timed out calling {url}: {exc}") from exc
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise LLMClientError(f"Non-JSON response from {url}: {raw}") from exc


def _parse_llm_json(text: str) -> dict:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`").strip()
    if stripped.startswith("json"):
        stripped = stripped[4:].strip()
    try:
        return json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise LLMClientError(f"LLM did not return valid JSON: {stripped}") from exc


def is_meaningful_segment(text: str) -> bool:
    """Return True if the segment contains actual content (not just punctuation/whitespace)."""
    has_word_char = bool(WORD_CHAR_PATTERN.search(text))
    has_substantial_content = len(text.strip()) > 2
    return has_word_char and has_substantial_content


def parse_surah_entries(text: str) -> SurahData:
    """Parse a surah file into a dict mapping verse IDs to their segment entries."""
    surah: SurahData = {}
    current_verse: str | None = None
    entries: VerseEntries = []

    for line in text.split('\n'):
        line = line.rstrip('\n')
        if not line:
            continue

        match = LINE_ID_PATTERN.match(line)
        if match:
            verse_id, segment_id = match.groups()
            segment_int = int(segment_id)

            if verse_id != current_verse:
                if current_verse and entries:
                    surah[current_verse] = list(entries)
                current_verse = verse_id
                entries = []

            text_content = line[match.end():].lstrip()
            entries.append((segment_int, text_content))
        elif current_verse and entries:
            entries[-1] = (entries[-1][0], entries[-1][1] + '\n' + line)

    if current_verse and entries:
        surah[current_verse] = entries

    return surah


def combine_segments(entries: VerseEntries) -> str:
    """Combine segment entries back into a single text string."""
    return '\n'.join(text for _, text in entries)


def load_reference(reference_dir: Path) -> SurahData:
    """Load the Arabic reference data."""
    reference: SurahData = {}
    # Files are named like "001", "002" without .txt extension
    for surah_file in sorted(reference_dir.glob("*")):
        if not surah_file.is_file():
            continue
        surah_id = surah_file.name
        try:
            text = surah_file.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            # Try with error handling
            text = surah_file.read_text(encoding="utf-8", errors="ignore")
        reference[surah_id] = parse_surah_entries(text)
    return reference


def load_broken_verses(issues_file: Path) -> Dict[str, List[str]]:
    """Load the list of broken verses from JSON file."""
    with open(issues_file, 'r') as f:
        return json.load(f)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Targeted fix for known broken verse splits"
    )
    parser.add_argument(
        "--provider",
        choices=["openai"],
        default="openai",
        help="LLM provider to use (default: openai)"
    )
    parser.add_argument(
        "--model",
        default="gpt-4o-mini",
        help="Model name for the provider (default: gpt-4o-mini)"
    )
    parser.add_argument(
        "--reference-dir",
        type=Path,
        default=Path("data/chs-ar-final"),
        help="Path to Arabic reference directory"
    )
    parser.add_argument(
        "--translations-dir",
        type=Path,
        default=Path("data/ksu-translations-formatted"),
        help="Path to translations directory"
    )
    parser.add_argument(
        "--issues-file",
        type=Path,
        default=Path("/tmp/broken_verses.json"),
        help="Path to broken verses JSON file"
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Maximum retry attempts per verse (default: 3)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate without writing changes"
    )

    args = parser.parse_args()

    # Validate inputs
    if not args.reference_dir.is_dir():
        print(f"Reference directory not found: {args.reference_dir}", file=sys.stderr)
        return 2
    if not args.translations_dir.is_dir():
        print(f"Translations directory not found: {args.translations_dir}", file=sys.stderr)
        return 2
    if not args.issues_file.exists():
        print(f"Issues file not found: {args.issues_file}", file=sys.stderr)
        return 2

    # Load reference and broken verses
    print("Loading Arabic reference...", file=sys.stderr)
    reference = load_reference(args.reference_dir)
    if not reference:
        print("Arabic reference directory is empty.", file=sys.stderr)
        return 2

    print("Loading broken verses list...", file=sys.stderr)
    broken_verses = load_broken_verses(args.issues_file)

    # Filter out empty languages
    broken_verses = {k: v for k, v in broken_verses.items() if v}
    total_verses = sum(len(v) for v in broken_verses.values())
    print(f"Found {len(broken_verses)} languages with {total_verses} broken verses", file=sys.stderr)

    # Initialize LLM client
    if args.provider == "openai":
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            print("OPENAI_API_KEY environment variable not set", file=sys.stderr)
            return 2
        client = OpenAIClient(api_key, args.model)
    else:
        print(f"Provider {args.provider} not implemented", file=sys.stderr)
        return 2

    # Process each language
    verses_checked = 0
    verses_adjusted = 0
    files_touched: set[str] = set()
    log_entries: List[dict] = []

    for lang_idx, (language, verse_list) in enumerate(sorted(broken_verses.items()), 1):
        print(f"\n[{lang_idx}/{len(broken_verses)}] Processing {language} ({len(verse_list)} verses)...", file=sys.stderr)

        # Group verses by chapter
        chapters: Dict[str, List[str]] = {}
        for verse_ref in verse_list:
            chapter, verse = verse_ref.split('/')
            if chapter not in chapters:
                chapters[chapter] = []
            chapters[chapter].append(verse)

        # Process each chapter
        lang_dir = args.translations_dir / language
        if not lang_dir.is_dir():
            print(f"  Warning: {language} directory not found", file=sys.stderr)
            continue

        for chapter, verses in sorted(chapters.items()):
            chapter_file = lang_dir / f"{chapter}.txt"
            if not chapter_file.exists():
                print(f"  Warning: {chapter_file} not found", file=sys.stderr)
                continue

            # Load the chapter
            translation_text = chapter_file.read_text(encoding="utf-8")
            translation_surah = parse_surah_entries(translation_text)
            reference_surah = reference.get(chapter, {})
            file_updates: Dict[str, VerseUpdate] = {}
            pending_tasks: List[VerseTask] = []
            batch_chars = 0

            for verse in verses:
                if verse not in translation_surah:
                    print(f"  Warning: {chapter}:{verse} not in translation file", file=sys.stderr)
                    continue
                if verse not in reference_surah:
                    print(f"  Warning: {chapter}:{verse} not in reference", file=sys.stderr)
                    continue

                reference_entries = reference_surah[verse]
                translation_entries = translation_surah[verse]

                if len(reference_entries) <= 1:
                    print(f"  Skipping {chapter}:{verse} (not multi-part in reference)", file=sys.stderr)
                    continue

                meaningful_entries = [
                    (idx, text) for idx, text in translation_entries if is_meaningful_segment(text)
                ]
                effective_entries = meaningful_entries or translation_entries

                translation_text_for_verse = combine_segments(effective_entries)
                if not translation_text_for_verse:
                    print(f"  Warning: {chapter}:{verse} has no translation text", file=sys.stderr)
                    continue

                expected_segments = len(reference_entries)
                translation_count = len(effective_entries)
                reference_indexes = [idx for idx, _ in reference_entries]
                effective_indexes = [idx for idx, _ in effective_entries]
                translation_indexes = [idx for idx, _ in translation_entries]
                original_segments = [text for _, text in translation_entries]

                if translation_count != expected_segments:
                    reason = f"Translation has {translation_count} segments but {expected_segments} required"
                elif effective_indexes != reference_indexes:
                    reason = f"Translation uses indexes {effective_indexes} but expected {reference_indexes}"
                else:
                    reason = "Verify translation boundaries match Arabic reference"

                payload = {
                    "reference": [{"id": f"{verse}_{idx}", "text": text} for idx, text in reference_entries],
                    "current": [{"id": f"{verse}_{idx}", "text": text} for idx, text in effective_entries],
                    "full_text": translation_text_for_verse,
                    "segments_needed": expected_segments,
                    "file": f"{language}/{chapter}",
                    "verse": verse,
                }

                task = VerseTask(
                    language=language,
                    file_path=chapter_file,
                    surah_id=chapter,
                    verse=verse,
                    reason=reason,
                    reference_entries=reference_entries,
                    translation_entries=translation_entries,
                    effective_entries=effective_entries,
                    reference_indexes=reference_indexes,
                    translation_indexes=translation_indexes,
                    effective_indexes=effective_indexes,
                    original_segments=original_segments,
                    translation_text=translation_text_for_verse,
                    payload=payload,
                )

                payload_size = len(json.dumps(payload))
                if batch_chars + payload_size > DEFAULT_BATCH_CHARS and pending_tasks:
                    # Process current batch
                    _process_batch(client, pending_tasks, file_updates, args.max_retries, args.dry_run)
                    pending_tasks = [task]
                    batch_chars = payload_size
                else:
                    pending_tasks.append(task)
                    batch_chars += payload_size

            # Process remaining tasks
            if pending_tasks:
                _process_batch(client, pending_tasks, file_updates, args.max_retries, args.dry_run)

            # Apply updates if not dry run
            if file_updates and not args.dry_run:
                _apply_updates(chapter_file, translation_surah, file_updates, files_touched, verses_adjusted)

    # Write log
    if log_entries and not args.dry_run:
        timestamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        log_file = Path(f"logs/split_adjustments_{timestamp}.jsonl")
        log_file.parent.mkdir(exist_ok=True)
        with open(log_file, 'w') as f:
            for entry in log_entries:
                f.write(json.dumps(entry) + '\n')
        print(f"\nLog written to {log_file}", file=sys.stderr)

    print(f"\nValidated {verses_checked} verse(s). Applied {verses_adjusted} adjustment(s) across {len(files_touched)} file(s).", file=sys.stderr)

    return 0


def _process_batch(
    client: BaseLLMClient,
    tasks: List[VerseTask],
    file_updates: Dict[str, VerseUpdate],
    max_retries: int,
    dry_run: bool
):
    """Process a batch of tasks with the LLM."""
    if not tasks:
        return

    # Combine all tasks into one API call
    combined_payload = {"tasks": [task.payload for task in tasks]}

    for attempt in range(max_retries):
        try:
            result = client.resegment(combined_payload)
            break
        except LLMClientError as exc:
            if attempt < max_retries - 1:
                print(f"    Retrying ({attempt + 1}/{max_retries})...", file=sys.stderr)
                continue
            print(f"    ERROR: {exc}", file=sys.stderr)
            # Mark all tasks as failed
            for task in tasks:
                print(f"    [ERROR] LLM failed for {task.file_label} verse {task.verse}: {exc}", file=sys.stderr)
            return

    # Process results
    verses_result = result.get("verses", [])
    if len(verses_result) != len(tasks):
        print(f"    ERROR: Expected {len(tasks)} results but got {len(verses_result)}", file=sys.stderr)
        return

    for task, verse_result in zip(tasks, verses_result):
        verse_id = verse_result.get("verse")
        segments = verse_result.get("segments", [])

        if not segments:
            print(f"    [ERROR] No segments returned for {task.file_label} verse {task.verse}", file=sys.stderr)
            continue

        file_updates[task.verse] = VerseUpdate(
            indexes=task.translation_indexes,
            segments=segments
        )
        print(f"    [UPDATED] {task.file_label} verse {task.verse}: {task.reason}", file=sys.stderr)


def _apply_updates(
    file_path: Path,
    surah_data: SurahData,
    updates: Dict[str, VerseUpdate],
    files_touched: set[str],
    verses_adjusted: int
):
    """Apply updates to a surah file."""
    for verse, update in updates.items():
        if verse not in surah_data:
            continue

        # Rebuild verse entries with new segments
        new_entries = []
        for i, segment_text in enumerate(update.segments):
            new_entries.append((update.indexes[i] if i < len(update.indexes) else i, segment_text))

        surah_data[verse] = new_entries
        verses_adjusted += 1

    # Write back to file
    lines = []
    for verse_id in sorted(surah_data.keys(), key=lambda x: int(x)):
        entries = surah_data[verse_id]
        for segment_id, text in entries:
            lines.append(f"{verse_id}_{segment_id:02d}\t{text}")

    file_path.write_text('\n'.join(lines), encoding="utf-8")
    files_touched.add(str(file_path))


if __name__ == "__main__":
    sys.exit(main())

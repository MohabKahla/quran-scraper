#!/usr/bin/env python3
"""Validate and correct split verses across formatted translations.

Translations under ``ksu-translations-formatted`` and the Arabic reference in
``chs-ar-final`` share the ``XXX_YY <tab> text`` format, where ``XXX`` identifies
the verse and ``YY`` marks sub-segments (``00`` for the first chunk, ``01`` and
above for additional pieces).  This script ensures every multi-part verse in the
translations is split at the same semantic boundary as the Arabic reference.

Instead of issuing one LLM request per verse, the script collects every verse in
a file that needs verification and batches consecutive verses until a serialized
character budget (default: 3,000 characters) is reached.  If adding a verse
would exceed the limit, the current batch is dispatched and the verse starts the
next batch—verses are never broken apart mid-request.  Each applied change is
logged for traceability.
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
from typing import Dict, List, Sequence
import socket
import urllib.error
import urllib.parse
import urllib.request

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

# Set global socket timeout to prevent hanging on API calls
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

DEFAULT_MAX_BATCH_CHARS = 3000
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
    translation_entries: VerseEntries  # raw entries as stored in the file
    effective_entries: VerseEntries  # filtered entries with meaningful text
    reference_indexes: List[int]
    translation_indexes: List[int]  # raw indexes (may include empty segments)
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


class GeminiClient(BaseLLMClient):
    api_root = "https://generativelanguage.googleapis.com/v1beta"

    def __init__(self, api_key: str, model: str):
        super().__init__(model)
        self.api_key = api_key

    def resegment(self, task_payload: dict) -> dict:
        url = (
            f"{self.api_root}/models/{self.model}:generateContent"
            f"?key={urllib.parse.quote(self.api_key)}"
        )
        prompt = f"{SYSTEM_PROMPT}\n\nTASK DATA:\n{json.dumps(task_payload, ensure_ascii=False)}"
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0},
        }
        response = _post_json(url, body, {"Content-Type": "application/json"})
        try:
            candidates = response["candidates"]
            content_parts = candidates[0]["content"]["parts"]
            content = "".join(part.get("text", "") for part in content_parts)
        except (KeyError, IndexError) as exc:
            raise LLMClientError(f"Unexpected Gemini response: {response}") from exc
        if not content:
            raise LLMClientError(f"Gemini returned empty content: {response}")
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
        stripped = stripped.strip("`")
        stripped = re.sub(r"^json\s*", "", stripped, flags=re.IGNORECASE)
    try:
        return json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise LLMClientError(f"Unable to parse model output as JSON: {text}") from exc


def parse_surah_entries(text: str) -> SurahData:
    """Parse a surah file into an ordered mapping of verse -> segments."""
    entries: Dict[str, VerseEntries] = {}
    for line in text.splitlines():
        match = LINE_ID_PATTERN.match(line)
        if not match:
            continue
        verse = match.group(1)
        split_idx = int(match.group(2))
        segment_text = line[match.end():].strip()
        entries.setdefault(verse, []).append((split_idx, segment_text))
    for verse_entries in entries.values():
        verse_entries.sort(key=lambda pair: pair[0])
    return entries


def is_meaningful_segment(text: str) -> bool:
    """Return True if the segment contains at least one alphanumeric character."""
    return bool(WORD_CHAR_PATTERN.search(text))


def load_reference(reference_dir: Path) -> Dict[str, SurahData]:
    reference: Dict[str, SurahData] = {}
    for file_path in sorted(reference_dir.iterdir()):
        if not file_path.is_file() or not file_path.name.isdigit():
            continue
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        reference[file_path.name] = parse_surah_entries(content)
    return reference


def combine_segments(entries: VerseEntries) -> str:
    """Join translation segments so the LLM can analyze the full verse text."""
    parts = [segment.strip() for _, segment in entries if segment.strip()]
    return " ".join(parts).strip()


def rewrite_translation_file(path: Path, updates: Dict[str, VerseUpdate]) -> None:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    new_lines: List[str] = []
    processed: set[str] = set()
    i = 0
    while i < len(lines):
        line = lines[i]
        match = LINE_ID_PATTERN.match(line)
        if not match:
            new_lines.append(line)
            i += 1
            continue
        verse = match.group(1)
        if verse in updates and verse not in processed:
            update = updates[verse]
            for idx, segment in zip(update.indexes, update.segments):
                new_lines.append(f"{verse}_{idx:02d}\t{segment}")
            processed.add(verse)
            i += 1
            while i < len(lines):
                next_match = LINE_ID_PATTERN.match(lines[i])
                if not next_match or next_match.group(1) != verse:
                    break
                i += 1
            continue
        new_lines.append(line)
        i += 1

    missing_updates = set(updates) - processed
    for verse in missing_updates:
        update = updates[verse]
        for idx, segment in zip(update.indexes, update.segments):
            new_lines.append(f"{verse}_{idx:02d}\t{segment}")

    path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def build_task_payload(
    language: str,
    surah_id: str,
    verse: str,
    reason: str,
    reference_entries: VerseEntries,
    effective_entries: VerseEntries,
    raw_entries: VerseEntries,
    translation_text: str,
) -> dict:
    return {
        "language": language,
        "surah": surah_id,
        "verse": verse,
        "reason": reason,
        "expected_segments": len(reference_entries),
        "reference_segments": [
            {"index": idx, "text": text} for idx, text in reference_entries
        ],
        "current_segments": [
            {"index": idx, "text": text} for idx, text in effective_entries
        ],
        "raw_segments": [
            {"index": idx, "text": text} for idx, text in raw_entries
        ],
        "translation_text": translation_text,
    }


def build_batch_payload(language: str, surah_id: str, tasks: List[VerseTask]) -> dict:
    return {
        "language": language,
        "surah": surah_id,
        "tasks": [task.payload for task in tasks],
    }


def estimate_chars(payload: dict) -> int:
    """Character estimate based on JSON serialization."""
    serialized = json.dumps(payload, ensure_ascii=False)
    return len(serialized)


def ensure_api_key(value: str | None, env_key: str, provider: str) -> str:
    key = value or os.getenv(env_key)
    if not key:
        raise ValueError(
            f"{provider} API key missing. Provide via argument or set ${env_key}."
        )
    return key


def build_client(args: argparse.Namespace) -> BaseLLMClient:
    if args.provider == "openai":
        api_key = ensure_api_key(args.openai_api_key, "OPENAI_API_KEY", "OpenAI")
        return OpenAIClient(api_key, args.openai_model)
    api_key = ensure_api_key(args.gemini_api_key, "GEMINI_API_KEY", "Gemini")
    return GeminiClient(api_key, args.gemini_model)


def write_log(log_dir: Path, entries: Sequence[dict]) -> Path:
    log_dir.mkdir(parents=True, exist_ok=True)
    log_name = f"split_adjustments_{dt.datetime.utcnow():%Y%m%d-%H%M%S}.jsonl"
    log_path = log_dir / log_name
    with log_path.open("w", encoding="utf-8") as handle:
        for entry in entries:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return log_path


def process_batch(
    tasks: List[VerseTask],
    client: BaseLLMClient | None,
    args: argparse.Namespace,
    file_updates: Dict[str, VerseUpdate],
    log_entries: List[dict],
    files_touched: set[str],
    dry_run: bool,
) -> tuple[BaseLLMClient | None, int, int, List[VerseTask]]:
    if not tasks:
        return client, 0, 0, []
    if client is None:
        client = build_client(args)

    payload = build_batch_payload(tasks[0].language, tasks[0].surah_id, tasks)
    try:
        response = client.resegment(payload)
    except LLMClientError as exc:
        verses = ", ".join(task.verse for task in tasks)
        print(
            f"[ERROR] LLM failed for {tasks[0].file_label} verses {verses}: {exc}",
            file=sys.stderr,
        )
        return client, 0, 0, tasks

    verse_items = response.get("verses")
    if not isinstance(verse_items, list):
        print(
            f"[WARN] Invalid LLM batch response for {tasks[0].file_label}: {response}",
            file=sys.stderr,
        )
        return client, 0, 0, tasks

    response_map: Dict[str, dict] = {}
    for entry in verse_items:
        verse_value = entry.get("verse")
        if verse_value is None:
            continue
        verse_str = str(verse_value).strip()
        verse_key = verse_str.zfill(3) if verse_str.isdigit() else verse_str
        response_map[verse_key] = entry

    verses_checked = 0
    verses_adjusted = 0
    retry_tasks: List[VerseTask] = []
    for task in tasks:
        result = response_map.get(task.verse)
        if not result:
            print(
                f"[RETRY] LLM response missing verse {task.verse} "
                f"for {task.file_label}; will retry separately.",
                file=sys.stderr,
            )
            retry_tasks.append(task)
            continue

        segments = result.get("segments", [])
        if not isinstance(segments, list):
            print(
                f"[RETRY] Verse {task.verse} returned invalid segments; will retry.",
                file=sys.stderr,
            )
            retry_tasks.append(task)
            continue

        segments = [str(item).strip() for item in segments]
        expected_len = len(task.reference_entries)
        if len(segments) != expected_len:
            print(
                f"[RETRY] Verse {task.verse} expected {expected_len} segments "
                f"but model returned {len(segments)}; retrying.",
                file=sys.stderr,
            )
            retry_tasks.append(task)
            continue

        verses_checked += 1

        translation_count = len(task.effective_entries)
        should_update = (
            translation_count != expected_len
            or task.effective_indexes != task.reference_indexes
            or [text for _, text in task.effective_entries] != segments
        )
        if not should_update:
            continue

        file_updates[task.verse] = VerseUpdate(task.reference_indexes, segments)
        verses_adjusted += 1
        files_touched.add(task.file_label)
        note = result.get("notes")

        log_entries.append(
            {
                "timestamp": dt.datetime.utcnow().isoformat() + "Z",
                "provider": args.provider,
                "model": client.model,
                "language": task.language,
                "file": task.file_label,
                "surah": task.surah_id,
                "verse": task.verse,
                "reason": task.reason,
                "reference_indexes": task.reference_indexes,
                "reference_segments": [text for _, text in task.reference_entries],
                "original_indexes": task.translation_indexes,
                "original_segments": task.original_segments,
                "updated_segments": segments,
                "notes": note,
            }
        )

        label = "PLAN" if dry_run else "UPDATED"
        print(f"[{label}] {task.file_label} verse {task.verse}: {task.reason}")

    return client, verses_checked, verses_adjusted, retry_tasks


def retry_failed_tasks(
    tasks: List[VerseTask],
    client: BaseLLMClient | None,
    args: argparse.Namespace,
    file_updates: Dict[str, VerseUpdate],
    log_entries: List[dict],
    files_touched: set[str],
    dry_run: bool,
    max_retries: int,
) -> tuple[BaseLLMClient | None, int, int]:
    total_checked = 0
    total_adjusted = 0
    attempt = 0
    pending = tasks

    while pending and attempt < max_retries:
        attempt += 1
        next_round: List[VerseTask] = []
        for task in pending:
            client, checked, adjusted, retry = process_batch(
                [task],
                client,
                args,
                file_updates,
                log_entries,
                files_touched,
                dry_run,
            )
            total_checked += checked
            total_adjusted += adjusted
            next_round.extend(retry)
        pending = next_round

    for task in pending:
        print(
            f"[ERROR] Unable to obtain valid segments for {task.file_label} "
            f"verse {task.verse} after {max_retries} retry attempt(s).",
            file=sys.stderr,
        )

    return client, total_checked, total_adjusted


def execute_tasks_with_retries(
    tasks: List[VerseTask],
    client: BaseLLMClient | None,
    args: argparse.Namespace,
    file_updates: Dict[str, VerseUpdate],
    log_entries: List[dict],
    files_touched: set[str],
    dry_run: bool,
) -> tuple[BaseLLMClient | None, int, int]:
    client, checked, adjusted, retry_tasks = process_batch(
        tasks, client, args, file_updates, log_entries, files_touched, dry_run
    )
    total_checked = checked
    total_adjusted = adjusted
    if retry_tasks:
        client, retry_checked, retry_adjusted = retry_failed_tasks(
            retry_tasks,
            client,
            args,
            file_updates,
            log_entries,
            files_touched,
            dry_run,
            max_retries=args.max_retries,
        )
        total_checked += retry_checked
        total_adjusted += retry_adjusted
    return client, total_checked, total_adjusted


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate translation verse splits against the Arabic reference and "
            "use OpenAI or Gemini to fix any mismatches."
        )
    )
    parser.add_argument(
        "--translations-dir",
        default=Path("data/ksu-translations-formatted"),
        type=Path,
        help="Directory containing translation folders.",
    )
    parser.add_argument(
        "--reference-dir",
        default=Path("data/chs-ar-final"),
        type=Path,
        help="Directory containing Arabic surah files.",
    )
    parser.add_argument(
        "--provider",
        choices=("openai", "gemini"),
        default="openai",
        help="LLM provider to use when resplitting verses.",
    )
    parser.add_argument(
        "--openai-model",
        default="gpt-4o-mini",
        help="OpenAI model used when --provider=openai.",
    )
    parser.add_argument(
        "--gemini-model",
        default="gemini-2.0-flash",
        help="Gemini model used when --provider=gemini.",
    )
    parser.add_argument(
        "--openai-api-key",
        help="Explicit OpenAI API key (otherwise the script uses $OPENAI_API_KEY).",
    )
    parser.add_argument(
        "--gemini-api-key",
        help="Explicit Gemini API key (otherwise the script uses $GEMINI_API_KEY).",
    )
    parser.add_argument(
        "--languages",
        nargs="*",
        help="Optional list of translation folder names to process.",
    )
    parser.add_argument(
        "--surahs",
        nargs="*",
        help="Optional list of surah numbers (e.g. 002 114) to process.",
    )
    parser.add_argument(
        "--max-batch-chars",
        type=int,
        default=DEFAULT_MAX_BATCH_CHARS,
        help=(
            "Serialized character budget for each LLM request (default: "
            f"{DEFAULT_MAX_BATCH_CHARS}). Verses are batched without splitting "
            "individual verses across requests."
        ),
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=2,
        help="Maximum number of per-verse retry attempts when the LLM response is invalid.",
    )
    parser.add_argument(
        "--log-dir",
        type=Path,
        default=Path("logs"),
        help="Directory where change logs are written.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show planned changes without editing files or writing logs.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.max_batch_chars <= 0:
        print("--max-batch-chars must be positive.", file=sys.stderr)
        return 2
    if args.max_retries < 0:
        print("--max-retries must be zero or positive.", file=sys.stderr)
        return 2
    if not args.reference_dir.is_dir():
        print(f"Reference directory not found: {args.reference_dir}", file=sys.stderr)
        return 2
    if not args.translations_dir.is_dir():
        print(f"Translations directory not found: {args.translations_dir}", file=sys.stderr)
        return 2

    reference = load_reference(args.reference_dir)
    if not reference:
        print("Arabic reference directory is empty.", file=sys.stderr)
        return 2

    allowed_languages = set(args.languages or [])
    allowed_surahs = {s.zfill(3) for s in (args.surahs or [])}

    verses_checked = 0
    verses_adjusted = 0
    files_touched: set[str] = set()
    log_entries: List[dict] = []
    client: BaseLLMClient | None = None

    translation_dirs = sorted(p for p in args.translations_dir.iterdir() if p.is_dir())
    for lang_dir in translation_dirs:
        if allowed_languages and lang_dir.name not in allowed_languages:
            continue
        translation_files = sorted(lang_dir.glob("*.txt"))
        for translation_file in translation_files:
            surah_id = translation_file.stem
            if allowed_surahs and surah_id not in allowed_surahs:
                continue
            reference_surah = reference.get(surah_id)
            if not reference_surah:
                continue

            translation_text = translation_file.read_text(encoding="utf-8")
            translation_surah = parse_surah_entries(translation_text)
            file_updates: Dict[str, VerseUpdate] = {}
            pending_tasks: List[VerseTask] = []
            batch_chars = 0

            for verse, reference_entries in reference_surah.items():
                if len(reference_entries) <= 1:
                    continue

                translation_entries: VerseEntries = translation_surah.get(verse, [])
                if not translation_entries:
                    print(
                        f"[WARN] {lang_dir.name}/{translation_file.name} verse {verse} "
                        "is missing from the translation file.",
                        file=sys.stderr,
                    )
                    continue

                meaningful_entries = [
                    (idx, text) for idx, text in translation_entries if is_meaningful_segment(text)
                ]
                effective_entries = meaningful_entries or translation_entries

                translation_text_for_verse = combine_segments(effective_entries)
                if not translation_text_for_verse:
                    print(
                        f"[WARN] {lang_dir.name}/{translation_file.name} verse {verse} "
                        "has no translation text to validate.",
                        file=sys.stderr,
                    )
                    continue

                expected_segments = len(reference_entries)
                translation_count = len(effective_entries)
                reference_indexes = [idx for idx, _ in reference_entries]
                effective_indexes = [idx for idx, _ in effective_entries]
                translation_indexes = [idx for idx, _ in translation_entries]
                original_segments = [text for _, text in translation_entries]

                if translation_count != expected_segments:
                    reason = (
                        f"Translation currently has {translation_count} segment(s) but "
                        f"{expected_segments} are required."
                    )
                elif effective_indexes != reference_indexes:
                    reason = (
                        f"Translation uses indexes {effective_indexes} but expected "
                        f"{reference_indexes}."
                    )
                else:
                    reason = (
                        "Verify that the translation boundaries match the Arabic "
                        "reference and adjust if they do not."
                    )

                task_payload = build_task_payload(
                    lang_dir.name,
                    surah_id,
                    verse,
                    reason,
                    reference_entries,
                    effective_entries,
                    translation_entries,
                    translation_text_for_verse,
                )
                char_cost = estimate_chars(task_payload)
                task = VerseTask(
                    language=lang_dir.name,
                    file_path=translation_file,
                    surah_id=surah_id,
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
                    payload=task_payload,
                )

                if pending_tasks:
                    prospective_chars = batch_chars + char_cost
                else:
                    prospective_chars = BATCH_OVERHEAD_CHARS + char_cost

                if pending_tasks and prospective_chars > args.max_batch_chars:
                    client, checked, adjusted = execute_tasks_with_retries(
                        pending_tasks,
                        client,
                        args,
                        file_updates,
                        log_entries,
                        files_touched,
                        args.dry_run,
                    )
                    verses_checked += checked
                    verses_adjusted += adjusted
                    pending_tasks = []
                    batch_chars = 0

                if not pending_tasks:
                    batch_chars = BATCH_OVERHEAD_CHARS
                pending_tasks.append(task)
                batch_chars += char_cost

                if batch_chars > args.max_batch_chars:
                    client, checked, adjusted = execute_tasks_with_retries(
                        pending_tasks,
                        client,
                        args,
                        file_updates,
                        log_entries,
                        files_touched,
                        args.dry_run,
                    )
                    verses_checked += checked
                    verses_adjusted += adjusted
                    pending_tasks = []
                    batch_chars = 0

            if pending_tasks:
                client, checked, adjusted = execute_tasks_with_retries(
                    pending_tasks,
                    client,
                    args,
                    file_updates,
                    log_entries,
                    files_touched,
                    args.dry_run,
                )
                verses_checked += checked
                verses_adjusted += adjusted
                pending_tasks = []
                batch_chars = 0

            if file_updates and not args.dry_run:
                rewrite_translation_file(translation_file, file_updates)

    if verses_adjusted and not args.dry_run:
        log_path = write_log(args.log_dir, log_entries)
        print(
            f"\nValidated {verses_checked} multi-part verse(s). "
            f"Applied {verses_adjusted} adjustment(s) across {len(files_touched)} file(s). "
            f"Log written to {log_path}."
        )
        return 0

    if verses_adjusted and args.dry_run:
        print(
            f"\nDry run complete: validated {verses_checked} multi-part verse(s). "
            f"{verses_adjusted} adjustment(s) would be applied."
        )
        return 0

    if verses_checked:
        print(
            f"Validated {verses_checked} multi-part verse(s); no boundary tweaks were needed."
        )
    else:
        print("No multi-part verses were processed (check filters or warnings above).")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Fetch translation identifiers for each language folder in ksu-translations-formatted.

This script queries the Quran.com translations API and returns, for every language
code detected in the local `ksu-translations-formatted` directory, the list of
translation IDs that belong to that language.
"""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Tuple
from urllib.error import URLError
from urllib.request import Request, urlopen

# Remote API configuration
API_URL = "https://quran.com/api/proxy/content/api/qdc/resources/translations?language=en"
API_HEADERS = {
    # Matching headers from the observed browser request keeps the endpoint happy.
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
    ),
    "Referer": "https://quran.com/",
    "DNT": "1",
}

# Mapping from folder prefixes (language codes) to the language names returned by the API.
# Only the languages present in ksu-translations-formatted are listed here.
CODE_TO_LANGUAGE = {
    "bn": "bengali",
    "bs": "bosnian",
    "de": "german",
    "es": "spanish",
    "ha": "hausa",
    "id": "indonesian",
    "it": "italian",
    "ku": "kurdish",
    "ml": "malayalam",
    "ms": "malay",
    "nl": "dutch",
    "pr": "persian",
    "pt": "portuguese",
    "ru": "russian",
    "sq": "albanian",
    "sv": "swedish",
    "sw": "swahili",
    "ta": "tamil",
    "th": "thai",
    "tr": "turkish",
    "ur": "urdu",
    "uz": "uzbek",
    "zh": "chinese",
}

REPO_ROOT = Path(__file__).resolve().parent
TRANSLATIONS_ROOT = REPO_ROOT / "data/ksu-translations-formatted"


def discover_language_codes(root: Path) -> List[Tuple[str, str]]:
    """Return (folder_name, language_code) pairs for every language directory."""
    if not root.exists():
        raise FileNotFoundError(f"Directory not found: {root}")

    entries: List[Tuple[str, str]] = []
    for entry in sorted(root.iterdir()):
        if not entry.is_dir():
            continue
        code = entry.name.split("-", 1)[0].lower()
        entries.append((entry.name, code))
    return entries


def fetch_translations() -> List[Dict]:
    """Retrieve the full translations payload from the API."""
    request = Request(API_URL, headers=API_HEADERS)
    with urlopen(request) as response:  # nosec: URL comes from trusted constant above
        payload = json.load(response)
    translations = payload.get("translations", [])
    if not isinstance(translations, list):
        raise ValueError("Unexpected payload structure: 'translations' is not a list")
    return translations


def build_language_index(translations: Iterable[Dict]) -> Tuple[Dict[str, List[int]], Dict[str, str]]:
    """Index translations by language name (case-insensitive).

    Returns:
        ids_by_language: mapping of lowercase language names to the list of translation IDs.
        display_name_map: mapping of lowercase language names to their display form.
    """
    ids_by_language: Dict[str, List[int]] = defaultdict(list)
    display_name_map: Dict[str, str] = {}
    for translation in translations:
        language_name = (translation.get("language_name") or "").strip()
        if not language_name:
            continue
        language_key = language_name.lower()
        ids_by_language[language_key].append(translation["id"])
        display_name_map.setdefault(language_key, language_name)
    return ids_by_language, display_name_map


def main() -> int:
    try:
        folder_entries = discover_language_codes(TRANSLATIONS_ROOT)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    try:
        translations = fetch_translations()
    except URLError as exc:  # pragma: no cover - network failure safeguard
        print(f"Failed to fetch translations: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    ids_by_language, display_name_map = build_language_index(translations)

    results = []
    for folder_name, code in folder_entries:
        language_key = CODE_TO_LANGUAGE.get(code)
        if language_key is None:
            # Fallback: try to infer the language from the folder suffix (best-effort).
            language_key = re.sub(r"[^a-z]", " ", folder_name.split("-", 1)[-1]).strip()
            language_key = language_key.lower()

        language_key_lower = language_key.lower()
        ids = sorted(set(ids_by_language.get(language_key_lower, [])))
        language_display = display_name_map.get(language_key_lower, language_key)

        results.append(
            {
                "language_name": language_display,
                "ids": ids,
            }
        )

    print(json.dumps(results, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

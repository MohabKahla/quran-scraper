import re
from pathlib import Path
from typing import Dict, Iterable, List, Set, Tuple

REPO_ROOT = Path(__file__).resolve().parent
ARABIC_DIR = REPO_ROOT / "chs-ar-final"
FORMATTED_ROOT = REPO_ROOT / "ksu-translations-formatted"
TRANSLATION_SOURCE_ROOT = REPO_ROOT / "ksu-translations"

KEY_PATTERN = re.compile(r"^(?P<key>\d{3}_\d{2})\t(?P<text>.*)$")


def read_arabic_structure(chapter: int) -> Tuple[Dict[int, List[int]], Set[str]]:
    """
    Return the verse-part structure for a chapter and the set of keys (excluding 000_00).
    """
    candidates = [
        ARABIC_DIR / f"{chapter:03d}.txt",
        ARABIC_DIR / f"{chapter:03d}",
    ]

    structure: Dict[int, List[int]] = {}
    keys: Set[str] = set()

    for path in candidates:
        if not path.exists():
            continue

        with path.open("r", encoding="utf-8") as handle:
            for raw_line in handle:
                match = KEY_PATTERN.match(raw_line.strip())
                if not match:
                    continue

                key = match.group("key")
                if key == "000_00":
                    continue

                verse = int(key.split("_")[0])
                part = int(key.split("_")[1])

                keys.add(key)
                structure.setdefault(verse, []).append(part)

        if structure:
            for parts in structure.values():
                parts.sort()
            return structure, keys

    raise FileNotFoundError(f"Arabic reference for chapter {chapter:03d} not found.")


def analyze_translation_file(path: Path, arabic_keys: Iterable[str]) -> Tuple[Set[str], Set[str], Set[str]]:
    """
    Compare a formatted translation file with the expected Arabic keys.
    Returns sets of missing keys, empty keys, and extra keys.
    """
    expected_keys = set(arabic_keys)
    found_keys: Set[str] = set()
    empty_keys: Set[str] = set()

    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            match = KEY_PATTERN.match(raw_line.rstrip("\n"))
            if not match:
                continue

            key = match.group("key")
            if key == "000_00":
                continue

            text = match.group("text").strip()
            found_keys.add(key)
            if text == "":
                empty_keys.add(key)

    missing_keys = expected_keys - found_keys
    extra_keys = found_keys - expected_keys
    return missing_keys, empty_keys, extra_keys


def scan_formatted_translations(verbose: bool = True):
    """
    Scan formatted translation files and collect issues.
    Returns a tuple (issues, summary) where `issues` is a list of dicts containing
    information about each problematic file, and `summary` is a dict with counts.
    """
    issues = []
    summary = {
        "total_files": 0,
        "files_with_issues": 0,
        "missing_keys": 0,
        "empty_text": 0,
        "extra_keys": 0,
    }

    if not FORMATTED_ROOT.exists():
        raise FileNotFoundError(f"Formatted translations directory not found: {FORMATTED_ROOT}")

    for translation_dir in sorted(FORMATTED_ROOT.iterdir()):
        if not translation_dir.is_dir():
            continue

        translation_label = translation_dir.name
        for translation_file in sorted(translation_dir.glob("*.txt")):
            summary["total_files"] += 1

            try:
                chapter = int(translation_file.stem)
            except ValueError:
                continue

            try:
                structure, arabic_keys = read_arabic_structure(chapter)
            except FileNotFoundError as exc:
                if verbose:
                    print(f"[{translation_label}] {translation_file.name}: {exc}")
                continue

            missing, empty, extra = analyze_translation_file(translation_file, arabic_keys)

            if missing or empty or extra:
                summary["files_with_issues"] += 1
                summary["missing_keys"] += len(missing)
                summary["empty_text"] += len(empty)
                summary["extra_keys"] += len(extra)

                issues.append({
                    "translation": translation_label,
                    "formatted_dir": translation_dir,
                    "file_path": translation_file,
                    "chapter": chapter,
                    "missing": set(missing),
                    "empty": set(empty),
                    "extra": set(extra),
                })

                if verbose:
                    print(f"[{translation_label}] {translation_file.name}")
                    if missing:
                        print(f"  - Missing keys ({len(missing)}): {', '.join(sorted(missing))}")
                    if empty:
                        print(f"  - Empty text ({len(empty)}): {', '.join(sorted(empty))}")
                    if extra:
                        print(f"  - Extra keys ({len(extra)}): {', '.join(sorted(extra))}")

    return issues, summary

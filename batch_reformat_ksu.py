#!/usr/bin/env python3
"""
Batch runner that reuses reformat_translation_generic.py for multiple KSU translations.

Usage:
  python batch_reformat_ksu.py                 # process all configured translations
  python batch_reformat_ksu.py es_navio it_piccardo
  python batch_reformat_ksu.py --list          # show available ids
"""

import argparse
import runpy
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
SCRIPT_PATH = REPO_ROOT / "reformat_translation_generic.py"
ARABIC_REFERENCE_DIR = REPO_ROOT / "chs-ar-final"
TRANSLATION_INPUT_ROOT = REPO_ROOT / "ksu-translations"
OUTPUT_ROOT = REPO_ROOT / "ksu-translations-formatted"

TRANSLATIONS = [
  {"id": "es_navio", "name": "Spanish", "code": "es", "direction": "ltr"},
  {"id": "de_bo", "name": "German", "code": "de", "direction": "ltr"},
  {"id": "it_piccardo", "name": "Italian", "code": "it", "direction": "ltr"},
  {"id": "pt_elhayek", "name": "Portuguese", "code": "pt", "direction": "ltr"},
  {"id": "nl_siregar", "name": "Dutch", "code": "nl", "direction": "ltr"},
  {"id": "bs_korkut", "name": "Bosnian", "code": "bs", "direction": "ltr"},
  {"id": "sq_nahi", "name": "Albanian", "code": "sq", "direction": "ltr"},
  {"id": "sv_bernstrom", "name": "Swedish", "code": "sv", "direction": "ltr"},
  {"id": "tr_diyanet", "name": "Turkish", "code": "tr", "direction": "ltr"},
  {"id": "ru_ku", "name": "Russian", "code": "ru", "direction": "ltr"},
  {"id": "id_indonesian", "name": "Indonesian", "code": "id", "direction": "ltr"},
  {"id": "ms_basmeih", "name": "Malay", "code": "ms", "direction": "ltr"},
  {"id": "ku_asan", "name": "Kurdish", "code": "ku", "direction": "rtl"},
  {"id": "pr_tagi", "name": "Persian", "code": "fa", "direction": "rtl"},
  {"id": "ur_gl", "name": "Urdu", "code": "ur", "direction": "rtl"},
  {"id": "ml_abdulhameed", "name": "Malayalam", "code": "ml", "direction": "ltr"},
  {"id": "bn_bengali", "name": "Bengali", "code": "bn", "direction": "ltr"},
  {"id": "ta_tamil", "name": "Tamil", "code": "ta", "direction": "ltr"},
  {"id": "th_thai", "name": "Thai", "code": "th", "direction": "ltr"},
  {"id": "ha_gumi", "name": "Hausa", "code": "ha", "direction": "ltr"},
  {"id": "sw_barwani", "name": "Swahili", "code": "sw", "direction": "ltr"},
  {"id": "uz_sodik", "name": "Uzbek", "code": "uz", "direction": "ltr"},
  {"id": "zh_jian", "name": "Chinese", "code": "zh", "direction": "ltr"},
]

TRANSLATION_MAP = {item["id"]: item for item in TRANSLATIONS}


def slugify_translation_id(translation_id: str) -> str:
    return translation_id.replace("_", "-")


def list_translations():
    print("Configured translations:")
    for item in TRANSLATIONS:
        print(f"  {item['id'].ljust(15)} {item['name']} ({item['code']})")


def run_translation(item: dict):
    slug = slugify_translation_id(item["id"])
    input_dir = TRANSLATION_INPUT_ROOT / slug
    output_dir = OUTPUT_ROOT / slug

    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory missing: {input_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 80)
    print(f"Reformatting {item['name']} ({item['id']})")
    print("=" * 80)

    overrides = {
        "LANGUAGE_NAME": item["name"],
        "LANGUAGE_CODE": item["code"],
        "TRANSLATION_DIRECTION": item["direction"],
        "TRANSLATION_INPUT_DIR": input_dir,
        "ARABIC_REFERENCE_DIR": ARABIC_REFERENCE_DIR,
        "OUTPUT_DIR": output_dir,
        "TRANSLATION_FORMAT": "numbered",
    }

    runpy.run_path(str(SCRIPT_PATH), init_globals=overrides, run_name="__main__")


def main():
    parser = argparse.ArgumentParser(description="Batch reformatter for KSU translations.")
    parser.add_argument("translation_ids", nargs="*", help="Subset of translation ids to process.")
    parser.add_argument("--list", action="store_true", help="List available translations and exit.")

    args = parser.parse_args()

    if args.list:
        list_translations()
        return

    if args.translation_ids:
        selected = []
        for translation_id in args.translation_ids:
            if translation_id not in TRANSLATION_MAP:
                raise SystemExit(f"Unknown translation id: {translation_id}")
            selected.append(TRANSLATION_MAP[translation_id])
    else:
        selected = TRANSLATIONS

    OUTPUT_ROOT.mkdir(exist_ok=True)

    for item in selected:
        try:
            run_translation(item)
        except Exception as exc:
            print(f"\nFailed to process {item['id']}: {exc}")


if __name__ == "__main__":
    main()

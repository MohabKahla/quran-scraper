#!/usr/bin/env python3
"""
Script to fix verse alignments for all available translations.
Processes them one by one with progress tracking.
"""

import os
import asyncio
import argparse
from pathlib import Path
from fix_verse_alignments import VerseAlignmentFixer

async def process_all_translations(provider: str, api_key: str, batch_size: int = 5, delay: float = 1.0):
    """Process all available translations."""

    translations_dir = Path("data/ksu-translations-formatted")

    if not translations_dir.exists():
        print("Translations directory not found!")
        return

    # Get all available translation directories
    translation_dirs = [d.name for d in translations_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]
    translation_dirs.sort()

    print(f"Found {len(translation_dirs)} translations to process:")
    for i, trans in enumerate(translation_dirs, 1):
        print(f"  {i:2d}. {trans}")

    print(f"\nUsing: {provider.upper()}, batch_size={batch_size}, delay={delay}s")
    confirm = input("\nProceed with all translations? (y/N): ").strip().lower()

    if confirm != 'y':
        print("Cancelled.")
        return

    # Create the fixer
    fixer = VerseAlignmentFixer(
        arabic_dir="data/chs-ar-final",
        translations_dir="data/ksu-translations-formatted",
        provider=provider,
        api_key=api_key
    )

    # Process each translation
    results = {}
    for i, translation_lang in enumerate(translation_dirs, 1):
        print(f"\n{'='*60}")
        print(f"Processing {i}/{len(translation_dirs)}: {translation_lang}")
        print(f"{'='*60}")

        try:
            # First, count misaligned verses
            misaligned = fixer.find_misaligned_verses(translation_lang)
            verse_count = len(misaligned)

            if verse_count == 0:
                print(f"✅ {translation_lang}: No misaligned verses found")
                results[translation_lang] = {"status": "no_issues", "verses": 0}
                continue

            print(f"Found {verse_count} misaligned verses")
            estimated_calls = (verse_count + batch_size - 1) // batch_size
            estimated_time = estimated_calls * delay / 60  # minutes

            print(f"Estimated: {estimated_calls} API calls, ~{estimated_time:.1f} minutes")

            # Process the translation
            await fixer.process_translation(
                translation_lang=translation_lang,
                batch_size=batch_size,
                delay=delay
            )

            results[translation_lang] = {"status": "processed", "verses": verse_count}
            print(f"✅ {translation_lang}: Completed ({verse_count} verses)")

        except Exception as e:
            print(f"❌ {translation_lang}: Error - {e}")
            results[translation_lang] = {"status": "error", "error": str(e)}

    # Final summary
    print(f"\n{'='*60}")
    print("FINAL SUMMARY")
    print(f"{'='*60}")

    total_processed = 0
    total_errors = 0
    no_issues = 0

    for trans, result in results.items():
        status = result["status"]
        if status == "processed":
            verses = result["verses"]
            print(f"✅ {trans}: {verses} verses fixed")
            total_processed += verses
        elif status == "error":
            print(f"❌ {trans}: ERROR - {result['error']}")
            total_errors += 1
        elif status == "no_issues":
            print(f"⚪ {trans}: No issues found")
            no_issues += 1

    print(f"\nResults:")
    print(f"  Translations with fixes applied: {len([r for r in results.values() if r['status'] == 'processed'])}")
    print(f"  Translations with no issues: {no_issues}")
    print(f"  Translations with errors: {total_errors}")
    print(f"  Total verses fixed: {total_processed}")

async def main():
    parser = argparse.ArgumentParser(description="Fix verse alignments for all translations")
    parser.add_argument("--provider", choices=["openai", "gemini"], required=True)
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--batch-size", type=int, default=5, help="Batch size for LLM requests")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay between batches")
    parser.add_argument("--translations", nargs="*", help="Specific translations to process (default: all)")

    args = parser.parse_args()

    if args.translations:
        # Process only specified translations
        print(f"Processing specified translations: {args.translations}")

        fixer = VerseAlignmentFixer(
            arabic_dir="data/chs-ar-final",
            translations_dir="data/ksu-translations-formatted",
            provider=args.provider,
            api_key=args.api_key
        )

        for translation in args.translations:
            print(f"\nProcessing: {translation}")
            await fixer.process_translation(
                translation_lang=translation,
                batch_size=args.batch_size,
                delay=args.delay
            )
    else:
        # Process all translations
        await process_all_translations(
            provider=args.provider,
            api_key=args.api_key,
            batch_size=args.batch_size,
            delay=args.delay
        )

if __name__ == "__main__":
    asyncio.run(main())
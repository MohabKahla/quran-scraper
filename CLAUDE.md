# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Commands

### Running the scrapers
```bash
# Main Quran.com API scraper (Italian translation by default)
node scripts/scrapers/scrape_quran_all.mjs

# KSU translations scraper (multiple languages)
node scripts/scrapers/scrape_ksu_translations.mjs --list  # List available translations
node scripts/scrapers/scrape_ksu_translations.mjs es_navio de_bo  # Scrape specific translations
node scripts/scrapers/scrape_ksu_translations.mjs  # Scrape all translations

# Fetch translated surah names
node scripts/scrapers/fetch_surah_translated_names.mjs

# Fetch available translation IDs
python3 scripts/scrapers/fetch_translation_ids.py
```

### Docker usage
```bash
# Build and run with Docker Compose
docker-compose -f docker/docker-compose.yml up --build

# Run in detached mode
docker-compose -f docker/docker-compose.yml up -d --build
```

### Python scripts
```bash
# Generic translation reformatting using AI
python3 scripts/alignment/reformat_translation_generic.py

# Check translation quality and splits
python3 scripts/validation/check_translation_splits.py
```

## Architecture Overview

### Core Components

**JavaScript Scrapers (scripts/scrapers/):**
- `scrape_quran_all.mjs` - Main scraper for Quran.com API, fetches verses with translations and applies extensive text cleaning
- `scrape_ksu_translations.mjs` - Multi-language scraper for King Saud University translations API
- `fetch_surah_translated_names.mjs` - Fetches localized chapter names using Quran.com's Next.js data endpoint
- `fetch_translation_ids.py` - Utility to map language codes to available translation IDs from Quran.com API

**Python Processing Scripts (scripts/alignment/):**
- `reformat_translation_generic.py` - AI-powered semantic alignment tool using Google Gemini API to match translation verse structure with Arabic reference
- `fix_verse_alignments.py` - Fixes verse alignment issues between translation and Arabic reference
- `auto_fix_all_issues.py` - Automated detection and fixing of alignment issues

**Validation Scripts (scripts/validation/):**
- `check_translation_splits.py` - Quality assurance tool to validate translation formatting and verse counts
- `check_all_translations.py` - Batch validation of all translations
- `check_source_contamination.py` - Detects contamination from source files

**Configuration (config/):**
- `translations.json` - Complete database of available translations with metadata (153 translations total)
- `chapter_names.txt` - Reference list of Arabic chapter names
- `.env.example` - Environment variables template
- Translation format constants in each script (translation IDs, API endpoints, output directories)

### Data Flow Architecture

1. **Source APIs:**
   - Quran.com API (`api.quran.com/api/v4/verses/by_chapter/`) - Primary source with rate limiting (1 second delay)
   - KSU API (`quran.ksu.edu.sa/interface.php`) - Alternative source for bulk translations (1.5 second delay)

2. **Processing Pipeline:**
   - Raw API data → Text cleaning (remove HTML, footnotes, normalize punctuation) → Verse formatting → File output
   - Optional AI-powered semantic alignment for format mismatches using Gemini API

3. **Output Structure:**
   - Individual files: `001.txt` to `114.txt` (numbered verses per chapter)
   - Combined files: `quran-{language}.txt` (full translation)
   - Directory structure: Language-based folders in `data/ksu-translations-formatted/`
   - Arabic reference text in `data/chs-ar-final/`

### Key Data Structures

- **Verse Counts:** Hardcoded array of 114 chapter verse counts for validation
- **Translation Mapping:** Language codes to API identifiers and metadata
- **Output Formats:** Numbered verses (`1. Verse text`) with chapter headers

### Docker Configuration

- Node.js 18 Alpine base image
- Volume mounting for persistent output (`./out:/app/out`)
- Production environment with automatic dependency installation
- Default command runs main Italian scraper

### Rate Limiting & Error Handling

- Mandatory delays between API requests (1-1.5 seconds)
- Comprehensive error handling with detailed logging
- Retry logic and graceful failure handling for individual chapters
- Request headers optimized to avoid blocking (User-Agent, Referer, etc.)

## Development Notes

- No formal test suite - validation through output file checking and manual QA
- Heavy use of text cleaning regex patterns for translation formatting
- AI integration requires `GOOGLE_API_KEY` environment variable for Gemini access (see `config/.env.example`)
- Translation IDs are API-specific and may change; use fetch scripts to update
- Build ID in `fetch_surah_translated_names.mjs` is hardcoded and may need updates for Quran.com changes
- For comprehensive repository navigation, see `INDEX.md` in the root directory
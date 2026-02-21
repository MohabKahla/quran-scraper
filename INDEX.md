# Quran Scraper - Repository Index

> Complete guide to all scripts, tools, and data in this repository

## Quick Navigation

- [Scripts](#scripts) - All executable scripts organized by purpose
- [Data](#data) - Translation data and backups
- [Configuration](#configuration) - Config files and references
- [Documentation](#documentation) - Guides and documentation
- [Docker](#docker) - Containerization setup

---

## Scripts

All scripts are organized under the `scripts/` directory by their primary function.

### Scrapers (`scripts/scrapers/`)

Scripts for fetching Quran translations from various APIs.

| Script | Language | Purpose |
|--------|----------|---------|
| `scrape_quran_all.mjs` | Node.js | Main scraper for Quran.com API (Italian translation by default) |
| `scrape_ksu_translations.mjs` | Node.js | Multi-language scraper for King Saud University translations API |
| `fetch_surah_translated_names.mjs` | Node.js | Fetches localized chapter names using Quran.com's Next.js data endpoint |
| `fetch_translation_ids.py` | Python | Maps language codes to available translation IDs from Quran.com API |

**Usage Examples:**
```bash
# Scrape main translation (Italian)
node scripts/scrapers/scrape_quran_all.mjs

# List available KSU translations
node scripts/scrapers/scrape_ksu_translations.mjs --list

# Scrape specific translations
node scripts/scrapers/scrape_ksu_translations.mjs es_navio de_bo

# Fetch surah names
node scripts/scrapers/fetch_surah_translated_names.mjs

# Get translation IDs
python3 scripts/scrapers/fetch_translation_ids.py
```

### Alignment & Fixing (`scripts/alignment/`)

AI-powered tools for fixing verse alignment issues in translations.

| Script | Purpose | AI Model |
|--------|---------|----------|
| `reformat_translation_generic.py` | Generic translation reformatting using AI | Google Gemini |
| `fix_verse_alignments.py` | Original verse alignment fixer | Google Gemini |
| `fix_verse_alignments_improved.py` | Enhanced version with better logic | Google Gemini |
| `fix_verse_alignments_with_retry.py` | Version with retry mechanism for API failures | Google Gemini |
| `fix_all_translations.py` | Batch processing for all translations | Google Gemini |
| `auto_fix_all_issues.py` | Automated detection and fixing of all issues | Google Gemini |
| `quick_fix_contamination.py` | Quick fix for contamination issues | - |

**Requirements:**
- `GOOGLE_API_KEY` environment variable
- `config/chapter_names.txt` for reference

**Usage Examples:**
```bash
# Reformat a specific translation
python3 scripts/alignment/reformat_translation_generic.py

# Fix alignment issues with retry
python3 scripts/alignment/fix_verse_alignments_with_retry.py

# Auto-fix all issues
python3 scripts/alignment/auto_fix_all_issues.py
```

### Validation (`scripts/validation/`)

Quality assurance tools for checking translation formatting and integrity.

| Script | Purpose |
|--------|---------|
| `check_translation_splits.py` | Validates translation formatting and verse counts |
| `check_all_translations.py` | Checks all translations for issues |
| `check_current_state.py` | Analyzes current state of translations |
| `check_source_contamination.py` | Detects contamination from source files |
| `check_real_contamination.py` | Deep contamination analysis |
| `compare_formatted_vs_original.py` | **[NEW]** Validates content integrity between formatted and original translations |

**Usage Examples:**
```bash
# Check translation splits
python3 scripts/validation/check_translation_splits.py

# Check all translations
python3 scripts/validation/check_all_translations.py

# Check for contamination
python3 scripts/validation/check_source_contamination.py

# Compare formatted vs original content (NEW!)
python3 scripts/validation/compare_formatted_vs_original.py  # All languages
python3 scripts/validation/compare_formatted_vs_original.py --language bn-bengali  # Specific language
python3 scripts/validation/compare_formatted_vs_original.py --language bn-bengali --chapter 002 --verbose  # Specific chapter
python3 scripts/validation/compare_formatted_vs_original.py --show-diff  # Show character-level diffs
```

**Content Integrity Validation:**

The `compare_formatted_vs_original.py` script ensures the alignment/reformatting process preserved all verse content by comparing:
- **Original source**: `data/old-translations/ksu-translations/{lang}/{chapter}.txt`
- **Formatted output**: `data/ksu-translations-formatted/{lang}/{chapter}.txt`

Key validation features:
- Combines split verses (e.g., `026_00` + `026_01` + `026_02`)
- Normalizes whitespace for fair comparison
- Reports missing content, text differences, and similarity scores
- Generates detailed mismatch reports with character-level diffs

### Analysis (`scripts/analysis/`)

Tools for analyzing failures and testing alignment algorithms.

| Script | Purpose |
|--------|---------|
| `analyze_failures.py` | Analyzes failure logs and generates reports |
| `simple_alignment_test.py` | Simple test for alignment logic |
| `test_alignment_finder.py` | Tests the alignment finding algorithm |

**Usage Examples:**
```bash
# Analyze failures
python3 scripts/analysis/analyze_failures.py

# Test alignment
python3 scripts/analysis/test_alignment_finder.py
```

### Automation (`scripts/automation/`)

Shell scripts for batch processing and automation.

| Script | Purpose |
|--------|---------|
| `process_all_translations.sh` | Process all translations in batch |
| `run_all_translations.sh` | Run all translation scrapers |
| `example_fix_alignments.sh` | Example workflow for fixing alignments |
| `fix_small_translations_only.sh` | Fix only small translation sets |
| `test_alignment.sh` | Test alignment on sample data |

**Usage Examples:**
```bash
# Process all translations
bash scripts/automation/process_all_translations.sh

# Run all scrapers
bash scripts/automation/run_all_translations.sh
```

---

## Data

All data is stored under the `data/` directory.

### Directory Structure

```
data/
├── chs-ar-final/              # Arabic reference text (114 chapters)
│   └── 001-114                # Chapter files (numbered)
├── ksu-translations-formatted/ # Formatted KSU translations (23 languages)
│   ├── bn-bengali/
│   ├── bs-korkut/
│   ├── de-bo/
│   ├── es-navio/
│   ├── ha-gumi/
│   ├── id-indonesian/
│   ├── it-piccardo/
│   ├── ku-asan/
│   ├── ml-abdulhameed/
│   ├── ms-basmeih/
│   ├── nl-siregar/
│   ├── pr-tagi/
│   ├── pt-elhayek/
│   ├── ru-ku/
│   ├── sq-nahi/
│   ├── sv-bernstrom/
│   ├── sw-barwani/
│   ├── ta-tamil/
│   ├── th-thai/
│   ├── tr-diyanet/
│   ├── ur-gl/
│   ├── uz-sodik/
│   └── zh-jian/
├── backups/                   # Timestamped backups
│   └── YYYYMMDD_HHMMSS/
└── old-translations/          # Legacy/archived translations
    ├── foreign-translations/
    ├── french-formatted-gemini-old/
    ├── french-old/
    ├── italian-formatted/
    ├── italian-formatted-gemini-old/
    ├── italian-old/
    └── ksu-translations/
```

### File Formats

**Arabic Reference (`data/chs-ar-final/`):**
- Files: `001` to `114` (no extension)
- Format: Plain Arabic text, one verse per line

**Translations (`data/ksu-translations-formatted/`):**
- Files: `001.txt` to `114.txt` per language directory
- Format: Numbered verses (`1. Verse text`)
- Additional: Some directories contain `{language}-surah-names.txt`

---

## Configuration

Configuration files and reference data are stored in `config/`.

| File | Purpose |
|------|---------|
| `translations.json` | Complete database of 153 available translations with metadata (IDs, languages, authors) |
| `chapter_names.txt` | Reference list of Arabic chapter names (114 surahs) |
| `requirements_alignment.txt` | Python dependencies for alignment scripts |
| `.env.example` | Example environment variables (GOOGLE_API_KEY) |

**Key Configuration:**
- Translation IDs are mapped in `translations.json`
- API endpoints are hardcoded in scraper scripts
- Rate limiting: 1-1.5 second delays between API requests

---

## Documentation

All documentation is in the `docs/` directory.

| Document | Purpose |
|----------|---------|
| `AUTO_FIX_GUIDE.md` | Guide for using automatic fixing tools |
| `FAILURES-LOG-GUIDE.md` | How to read and interpret failure logs |
| `FAILURE-ANALYSIS-SUMMARY.md` | Summary of common failure patterns |
| `VALIDATOR-README.md` | Guide for validation tools |
| `RETRY-COMPARISON.md` | Comparison of retry strategies |
| `QUICK-START.md` | Quick start guide for new users |
| `CHANGELOG.md` | Project changelog |

**Main Documentation (Root):**
- `README.md` - Project overview and main documentation
- `CLAUDE.md` - Instructions for Claude Code AI assistant

---

## Docker

Docker configuration is in the `docker/` directory.

| File | Purpose |
|------|---------|
| `Dockerfile` | Node.js 18 Alpine base image with dependencies |
| `docker-compose.yml` | Service configuration with volume mounting |
| `.dockerignore` | Excludes from Docker build |

**Usage:**
```bash
# Build and run
docker-compose -f docker/docker-compose.yml up --build

# Run in detached mode
docker-compose -f docker/docker-compose.yml up -d --build
```

**Configuration:**
- Volume mounting: `./out:/app/out`
- Default command: Runs main Italian scraper
- Environment: Production mode

---

## Other Directories

| Directory | Purpose |
|-----------|---------|
| `logs/` | Generated log files from scripts (timestamped) |
| `old-scripts/` | Deprecated/legacy scripts (not actively used) |
| `node_modules/` | NPM dependencies (auto-generated) |

---

## Development Workflow

### 1. Scraping New Translations
```bash
# List available translations
node scripts/scrapers/scrape_ksu_translations.mjs --list

# Scrape specific translation
node scripts/scrapers/scrape_ksu_translations.mjs es_navio

# Validate output
python3 scripts/validation/check_translation_splits.py
```

### 2. Fixing Alignment Issues
```bash
# Check for issues
python3 scripts/validation/check_all_translations.py

# Auto-fix issues
python3 scripts/alignment/auto_fix_all_issues.py

# Analyze failures (if any)
python3 scripts/analysis/analyze_failures.py
```

### 3. Quality Assurance
```bash
# Check current state
python3 scripts/validation/check_current_state.py

# Check for contamination
python3 scripts/validation/check_source_contamination.py

# Validate splits
python3 scripts/validation/check_translation_splits.py
```

---

## API Sources

### Quran.com API
- **Endpoint:** `https://api.quran.com/api/v4/verses/by_chapter/`
- **Rate Limit:** 1 second delay between requests
- **Usage:** Main source for `scrape_quran_all.mjs`

### King Saud University API
- **Endpoint:** `http://quran.ksu.edu.sa/interface.php`
- **Rate Limit:** 1.5 second delay between requests
- **Usage:** Source for `scrape_ksu_translations.mjs`

---

## Environment Variables

Required for AI-powered alignment tools:

```bash
# .env file (copy from config/.env.example)
GOOGLE_API_KEY=your_gemini_api_key_here
```

---

## Notes

- No formal test suite - validation through output file checking
- Heavy use of regex patterns for text cleaning
- AI integration requires Google Gemini API access
- Translation IDs may change; use fetch scripts to update
- Build ID in `fetch_surah_translated_names.mjs` may need updates

---

## Support

For issues or questions:
1. Check relevant documentation in `docs/`
2. Review `README.md` and `CLAUDE.md`
3. Examine logs in `logs/` directory
4. Use validation scripts to diagnose issues

---

**Last Updated:** 2026-01-03

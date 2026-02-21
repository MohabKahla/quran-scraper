# Failure Analysis Summary

**Generated:** 2025-12-09
**Analysis of:** 14 translations with logged failures + 16 translations with source contamination

---

## Executive Summary

### Critical Findings

1. **973 total failures** logged across 14 translations
2. **22,703 contaminated verses** found in source files across 16 translations
3. **Major data quality issue:** Arabic text appearing instead of translations

### Issue Breakdown

| Category | Count | Percentage |
|----------|-------|------------|
| Words changed (added + removed) | 365 | 37.5% |
| Arabic contamination | 250 | 25.7% |
| Words added only | 228 | 23.4% |
| Words removed only | 130 | 13.4% |

---

## Detailed Analysis

### 1. Source File Contamination (CRITICAL)

These translations have **Arabic text in the source files** where translations should be:

#### Severe Contamination (>1000 verses)
- **ur-gl (Urdu):** 7,499 verses (~100% of Quran)
- **ku-asan (Kurdish):** 7,542 verses (~100% of Quran)
- **pr-tagi (Persian):** 7,524 verses (~100% of Quran)

**Root Cause:** These files use Arabic script, but contain actual Arabic text instead of translations. Despite Persian, Kurdish, and Urdu using Arabic script, the content should be in those languages, not Arabic.

#### Moderate Contamination (10-100 verses)
- **ta-tamil (Tamil):** 58 verses
- **bn-bengali (Bengali):** 26 verses
- **ms-basmeih (Malay):** 13 verses
- **ml-abdulhameed (Malayalam):** 12 verses
- **bs-korkut (Bosnian):** 11 verses

#### Light Contamination (1-10 verses)
- **sv-bernstrom (Swedish):** 3 verses
- **th-thai (Thai):** 3 verses
- **it-piccardo (Italian):** 3 verses
- **nl-siregar (Dutch):** 3 verses
- **sq-nahi (Albanian):** 2 verses
- **id-indonesian (Indonesian):** 2 verses
- **es-navio (Spanish):** 1 verse
- **ha-gumi (Hausa):** 1 verse

### 2. AI Alignment Failures (from failure logs)

Translations with the most AI-induced errors during alignment:

| Translation | Failures | Primary Issue |
|-------------|----------|---------------|
| pt-elhayek (Portuguese) | 281 | Words changed/added |
| pr-tagi (Persian) | 96 | Arabic contamination + words changed |
| nl-siregar (Dutch) | 74 | Words changed |
| ml-abdulhameed (Malayalam) | 73 | Words changed |
| ku-asan (Kurdish) | 68 | Words changed |
| es-navio (Spanish) | 66 | Words changed |
| de-bo (German) | 52 | Words changed |
| ms-basmeih (Malay) | 51 | Words changed |

---

## Action Plan

### Phase 1: Fix Source Data (CRITICAL - DO FIRST)

**Priority 1: Complete Re-scraping Required**

These translations are completely unusable and need full re-scraping:

1. **ur-gl (Urdu)** - 7,499 contaminated verses
2. **ku-asan (Kurdish)** - 7,542 contaminated verses
3. **pr-tagi (Persian)** - 7,524 contaminated verses

**Action:** Re-scrape from source API with correct translation IDs

**Priority 2: Partial Re-scraping or Manual Fix**

Translations with <100 contaminated verses - can be manually fixed or selectively re-scraped:

- ta-tamil (58 verses)
- bn-bengali (26 verses)
- ms-basmeih (13 verses)
- ml-abdulhameed (12 verses)
- bs-korkut (11 verses)
- And 8 others with <10 verses each

**Action:** Option A: Manual correction using the detailed report in `logs/source_contamination_report.txt`
**Action:** Option B: Re-scrape specific chapters

### Phase 2: Fix AI Alignment Issues

After source data is fixed, address AI alignment failures:

**Priority 1: High Failure Count (>50 failures)**

1. pt-elhayek (Portuguese) - 281 failures
2. pr-tagi (Persian) - 96 failures (AFTER fixing source contamination)
3. nl-siregar (Dutch) - 74 failures
4. ml-abdulhameed (Malayalam) - 73 failures
5. ku-asan (Kurdish) - 68 failures (AFTER fixing source contamination)
6. es-navio (Spanish) - 66 failures
7. de-bo (German) - 52 failures
8. ms-basmeih (Malay) - 51 failures

**Action:** Re-run alignment with stricter prompts or different AI model

**Priority 2: Medium Failure Count (20-50 failures)**

- bs-korkut (Bosnian) - 44 failures
- it-piccardo (Italian) - 43 failures
- ha-gumi (Hausa) - 41 failures
- id-indonesian (Indonesian) - 38 failures
- ru-ku (Russian) - 24 failures
- bn-bengali (Bengali) - 22 failures (AFTER fixing source contamination)

**Action:** Manual review and correction using failure logs

---

## Commands to Execute

### 1. Check Which Translations Need Re-scraping

```bash
# View full contamination report
cat logs/source_contamination_report.txt

# See specific files that need attention
python3 check_source_contamination.py
```

### 2. Re-scrape Contaminated Translations

```bash
# First, identify correct translation IDs
python3 fetch_translation_ids.py

# Re-scrape specific translations
node scrape_ksu_translations.mjs ur_gl ku_asan pr_tagi
```

### 3. After Source Files Are Fixed, Re-run Alignment

```bash
# For translations with >50 failures
python3 fix_verse_alignments_with_retry.py \
  --provider gemini \
  --api-key $GEMINI_API_KEY \
  --translation pt-elhayek \
  --max-retries 3 \
  --failures-log "logs/failures-pt-elhayek-RETRY.json"
```

### 4. Validate Results

```bash
# After fixes, verify improvements
python3 check_translation_splits.py
python3 analyze_failures.py
```

---

## Key Files Generated

1. **analyze_failures.py** - Analyzes failure logs, categorizes errors
2. **check_source_contamination.py** - Checks source files for Arabic contamination
3. **logs/source_contamination_report.txt** - Detailed contamination report with file/line numbers
4. **logs/failures-{translation}.json** - Individual failure logs per translation

---

## Recommendations by Translation

### Translations Ready for Use (Low/No Issues)

None currently meet this criteria. All have either source contamination or significant alignment failures.

### Translations Needing Minor Fixes (<25 failures, no contamination)

- ru-ku (Russian) - 24 failures
- id-indonesian (Indonesian) - 38 failures (2 contaminated verses)

### Translations Needing Major Rework

All others require either:
- Complete re-scraping (Urdu, Kurdish, Persian)
- Partial re-scraping (Tamil, Bengali, Malay, Malayalam, Bosnian, etc.)
- Re-alignment with stricter parameters (Portuguese, Dutch, German, Spanish, etc.)

---

## Next Steps

1. **Immediate:** Identify correct translation IDs for ur-gl, ku-asan, pr-tagi
2. **Day 1:** Re-scrape the 3 completely contaminated translations
3. **Day 2-3:** Fix or re-scrape partially contaminated translations
4. **Day 4-5:** Re-run alignment on high-failure-count translations
5. **Day 6:** Validate all fixes and generate final quality report

---

**Note:** The contamination issue appears to be from the original scraping, not from the AI alignment process. This suggests the scraper may have used incorrect translation IDs or the API returned Arabic text instead of translations.

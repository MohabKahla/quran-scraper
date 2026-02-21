# Translation Restoration & Validation Guide

This guide explains how to restore corrupted/truncated translations and validate their integrity.

## Problem Overview

During AI alignment/reformatting, translations suffered from:
1. **Truncation** - Missing content at verse endings
2. **Reordering** - Sentences shuffled incorrectly
3. **Corruption** - Junk characters added (e.g., `. .`)
4. **Word-breaks** - Words incorrectly split (e.g., "Ange li" instead of "Angeli")

**Impact:** 22 out of 23 languages had issues (13,803 total mismatches)

---

## Quick Start

### Step 1: Initial Validation (Check Current State)

```bash
# Check all languages
python3 scripts/validation/generate_validation_reports.py

# Check specific language
python3 scripts/validation/compare_formatted_vs_original.py --language it-piccardo
```

**Output:** Detailed reports in `logs/validation-reports/TIMESTAMP/`

### Step 2: Restore Content

```bash
# Test on one language first (dry-run)
python3 scripts/alignment/restore_missing_content_v2.py --language it-piccardo --dry-run

# Fix that language
python3 scripts/alignment/restore_missing_content_v2.py --language it-piccardo

# Fix all languages
python3 scripts/alignment/restore_missing_content_v2.py --all
```

**Note:** Run 2-3 times for iterative improvement (some issues need multiple passes)

### Step 3: Fix Word-Breaks

```bash
# Fix minor word-break issues (99%+ similarity)
python3 scripts/alignment/fix_word_breaks.py --all

# Or test on specific language first
python3 scripts/alignment/fix_word_breaks.py --language it-piccardo --dry-run
```

### Step 4: Final Validation

```bash
# Generate comprehensive reports
python3 scripts/validation/generate_validation_reports.py
```

---

## Detailed Workflow

### Phase 1: Assessment

#### Generate Initial Reports

```bash
python3 scripts/validation/generate_validation_reports.py
```

**What it does:**
- Validates all translations against original source
- Creates nested directory structure: `logs/validation-reports/TIMESTAMP/`
  - `summary.txt` - Overall statistics
  - `by-language/*.txt` - Detailed per-language reports
  - `by-severity/*.txt` - Grouped by issue severity (critical/moderate/minor/trivial)
  - `validation-data.json` - Machine-readable data

**Read the reports:**
```bash
# Quick overview
cat logs/validation-reports/*/summary.txt

# Check specific language
cat logs/validation-reports/*/by-language/it-piccardo.txt

# Check critical issues across all languages
cat logs/validation-reports/*/by-severity/critical.txt
```

---

### Phase 2: Restoration

#### Understanding the Restoration Script

The `restore_missing_content_v2.py` script handles three types of corruption:

1. **Truncated** - Simple missing content at end → appends it
2. **Reordered** - Sentences in wrong order → reorders them
3. **Severely Corrupted** - Major issues/junk → replaces with original

#### Test on One Language

```bash
# Dry-run to see what would be fixed
python3 scripts/alignment/restore_missing_content_v2.py \
  --language it-piccardo \
  --dry-run \
  --verbose

# Review the output, then run for real
python3 scripts/alignment/restore_missing_content_v2.py --language it-piccardo
```

#### Run on All Languages

```bash
# First pass
python3 scripts/alignment/restore_missing_content_v2.py --all

# Check progress
python3 scripts/validation/compare_formatted_vs_original.py --language it-piccardo

# Second pass (iterative improvement)
python3 scripts/alignment/restore_missing_content_v2.py --all

# Optional third pass
python3 scripts/alignment/restore_missing_content_v2.py --all
```

**Why multiple passes?**
Some verses have nested issues. Each pass fixes what it can, making the next pass more effective.

#### Advanced Options

```bash
# Skip minor differences (useful after restoration)
python3 scripts/alignment/restore_missing_content_v2.py \
  --language it-piccardo \
  --min-similarity 0.99

# Verbose output to see each chapter
python3 scripts/alignment/restore_missing_content_v2.py \
  --language bn-bengali \
  --verbose
```

---

### Phase 3: Fine-Tuning (Word-Breaks)

After restoration, fix remaining minor issues (word-break problems).

```bash
# Test on one language
python3 scripts/alignment/fix_word_breaks.py \
  --language it-piccardo \
  --dry-run \
  --verbose

# Fix all languages
python3 scripts/alignment/fix_word_breaks.py --all
```

**What it fixes:**
- "Ange li" → "Angeli"
- "vess azioni" → "vessazioni"
- "Giov anni" → "Giovanni"

These are typically 99%+ similarity issues from AI alignment.

#### Options

```bash
# Only fix issues above 99% similarity (very safe)
python3 scripts/alignment/fix_word_breaks.py --all --min-similarity 0.99

# More aggressive (>95% similarity)
python3 scripts/alignment/fix_word_breaks.py --all --min-similarity 0.95
```

---

### Phase 4: Final Validation

```bash
# Generate fresh reports
python3 scripts/validation/generate_validation_reports.py

# Check improvement
cat logs/validation-reports/*/summary.txt
```

---

## Scripts Reference

### Validation Scripts

| Script | Purpose | Output |
|--------|---------|--------|
| `compare_formatted_vs_original.py` | Single/multi-language validation | Terminal output + optional JSON |
| `generate_validation_reports.py` | Comprehensive report generation | Nested directory with multiple reports |

#### compare_formatted_vs_original.py

```bash
# Basic usage
python3 scripts/validation/compare_formatted_vs_original.py --language it-piccardo

# Show detailed diffs
python3 scripts/validation/compare_formatted_vs_original.py \
  --language it-piccardo \
  --show-diff

# Show all issues (not just first 5)
python3 scripts/validation/compare_formatted_vs_original.py \
  --language it-piccardo \
  --show-all

# Save to JSON for processing
python3 scripts/validation/compare_formatted_vs_original.py \
  --language it-piccardo \
  --json-output logs/it-piccardo-validation.json
```

#### generate_validation_reports.py

```bash
# All languages
python3 scripts/validation/generate_validation_reports.py

# Specific languages
python3 scripts/validation/generate_validation_reports.py \
  --languages it-piccardo bn-bengali es-navio

# Verbose output
python3 scripts/validation/generate_validation_reports.py --verbose
```

---

### Restoration Scripts

| Script | Purpose | Best For |
|--------|---------|----------|
| `restore_missing_content_v2.py` | Main restoration (truncation/reordering/corruption) | Major content issues |
| `fix_word_breaks.py` | Fix minor word-break issues | 99%+ similarity issues |

#### restore_missing_content_v2.py

```bash
# Single language
python3 scripts/alignment/restore_missing_content_v2.py --language it-piccardo

# All languages
python3 scripts/alignment/restore_missing_content_v2.py --all

# Dry-run (preview)
python3 scripts/alignment/restore_missing_content_v2.py --language it-piccardo --dry-run

# Verbose (see each chapter)
python3 scripts/alignment/restore_missing_content_v2.py --language it-piccardo --verbose

# Skip minor differences
python3 scripts/alignment/restore_missing_content_v2.py --language it-piccardo --min-similarity 0.99
```

#### fix_word_breaks.py

```bash
# All languages
python3 scripts/alignment/fix_word_breaks.py --all

# Single language
python3 scripts/alignment/fix_word_breaks.py --language it-piccardo

# Dry-run
python3 scripts/alignment/fix_word_breaks.py --language it-piccardo --dry-run

# Verbose
python3 scripts/alignment/fix_word_breaks.py --all --verbose
```

---

## Common Workflows

### Workflow 1: Full Restoration (Recommended)

```bash
# 1. Initial assessment
python3 scripts/validation/generate_validation_reports.py
cat logs/validation-reports/*/summary.txt

# 2. Restore content (run 2-3 times)
python3 scripts/alignment/restore_missing_content_v2.py --all
python3 scripts/alignment/restore_missing_content_v2.py --all

# 3. Fix word-breaks
python3 scripts/alignment/fix_word_breaks.py --all

# 4. Final validation
python3 scripts/validation/generate_validation_reports.py
cat logs/validation-reports/*/summary.txt
```

### Workflow 2: Test on Single Language

```bash
# 1. Check current state
python3 scripts/validation/compare_formatted_vs_original.py --language it-piccardo

# 2. Test restoration (dry-run)
python3 scripts/alignment/restore_missing_content_v2.py --language it-piccardo --dry-run

# 3. Apply restoration
python3 scripts/alignment/restore_missing_content_v2.py --language it-piccardo

# 4. Fix word-breaks
python3 scripts/alignment/fix_word_breaks.py --language it-piccardo

# 5. Validate
python3 scripts/validation/compare_formatted_vs_original.py --language it-piccardo
```

### Workflow 3: Cautious Approach

```bash
# 1. Validate
python3 scripts/validation/generate_validation_reports.py

# 2. Review critical issues only
cat logs/validation-reports/*/by-severity/critical.txt

# 3. Fix only languages with critical issues
python3 scripts/alignment/restore_missing_content_v2.py --language zh-jian
python3 scripts/alignment/restore_missing_content_v2.py --language es-navio
python3 scripts/alignment/restore_missing_content_v2.py --language pt-elhayek

# 4. Validate those languages
python3 scripts/validation/compare_formatted_vs_original.py --language zh-jian
python3 scripts/validation/compare_formatted_vs_original.py --language es-navio
python3 scripts/validation/compare_formatted_vs_original.py --language pt-elhayek
```

---

## Understanding the Reports

### summary.txt

```
OVERALL SUMMARY
Languages validated: 23
Languages with issues: 22
Languages perfect: 1
Total mismatches: 13803

BY LANGUAGE
✅ uz-sodik                        - Perfect
❌ zh-jian                         - 1000 issues (critical:50 moderate:200 minor:600 trivial:150)
❌ es-navio                        -  880 issues (critical:30 moderate:150 minor:500 trivial:200)
...
```

### by-language/it-piccardo.txt

```
VALIDATION REPORT: it-piccardo
Total mismatches: 524

By severity:
  Critical (<80%):  20
  Moderate (80-95%): 150
  Minor (95-99%):   300
  Trivial (>99%):   54

ISSUES BY CHAPTER

Chapter 002: 77 issues
Verse 019 - Similarity: 88.2%
  Original (204 chars):
    আর তাদের উদাহরণ সেসব লোকের মত...
  Formatted (161 chars):
    আর তাদের উদাহরণ সেসব লোকের মত...
```

### by-severity/critical.txt

Shows all critical issues (<80% similarity) across all languages - these need immediate attention.

---

## Troubleshooting

### Issue: "Restorations don't seem to help"

**Solution:** Run multiple iterations
```bash
# Run 2-3 times
python3 scripts/alignment/restore_missing_content_v2.py --all
python3 scripts/alignment/restore_missing_content_v2.py --all
python3 scripts/alignment/restore_missing_content_v2.py --all
```

### Issue: "Some verses are getting worse"

**Cause:** Original formatted files were already corrupted in backups

**Solution:** Restore from git if available, or use `--min-similarity` to skip those verses
```bash
# Only fix issues with <95% similarity
python3 scripts/alignment/restore_missing_content_v2.py --all --min-similarity 0.95
```

### Issue: "Word-break fixer is too aggressive"

**Solution:** Use higher similarity threshold
```bash
# Only fix 99%+ similarity (safest)
python3 scripts/alignment/fix_word_breaks.py --all --min-similarity 0.99
```

### Issue: "Want to undo changes"

**Solution:** Check the backups directory
```bash
# Backups are timestamped
ls -la backups/

# Restore from specific backup
cp -r backups/20260110_145416/it-piccardo/* data/ksu-translations-formatted/it-piccardo/
```

---

## Success Metrics

### it-piccardo Example

- **Before:** 524 mismatches
- **After 1st restoration:** 206 mismatches (61% improvement)
- **After 2nd restoration:** 76 mismatches (85% improvement)
- **After 3rd restoration:** 34 mismatches (93.5% improvement)
- **After word-break fix:** Estimated <10 mismatches (98%+ improvement)

### Expected Results

For most languages:
- **After restoration:** 80-95% of issues fixed
- **After word-breaks:** 95-99% of issues fixed
- **Remaining issues:** Mostly minor (>99% similarity)

---

## File Locations

### Input (Source Data)
- `data/old-translations/ksu-translations/{language}/{chapter}.txt` - Original translations
- `data/ksu-translations-formatted/{language}/{chapter}.txt` - Formatted (potentially corrupted)

### Output (Reports)
- `logs/validation-reports/TIMESTAMP/` - Validation reports
- `logs/restoration_report_TIMESTAMP.txt` - Restoration logs (if generated)

### Backups
- `backups/TIMESTAMP/{language}/{chapter}.txt` - Automatic backups before changes

### Scripts
- `scripts/validation/` - Validation scripts
- `scripts/alignment/` - Restoration scripts

---

## Best Practices

1. **Always dry-run first** - Use `--dry-run` to preview changes
2. **Test on one language** - Validate approach before running on all
3. **Multiple iterations** - Run restoration 2-3 times for best results
4. **Keep backups** - Backups are automatic, but check `backups/` regularly
5. **Validate frequently** - Run validation after each major change
6. **Review reports** - Check `by-severity/critical.txt` for serious issues

---

## Quick Reference

### Most Common Commands

```bash
# Full workflow (recommended)
python3 scripts/validation/generate_validation_reports.py
python3 scripts/alignment/restore_missing_content_v2.py --all
python3 scripts/alignment/restore_missing_content_v2.py --all  # Second pass
python3 scripts/alignment/fix_word_breaks.py --all
python3 scripts/validation/generate_validation_reports.py

# Test single language
python3 scripts/validation/compare_formatted_vs_original.py --language it-piccardo
python3 scripts/alignment/restore_missing_content_v2.py --language it-piccardo --dry-run
python3 scripts/alignment/restore_missing_content_v2.py --language it-piccardo
python3 scripts/alignment/fix_word_breaks.py --language it-piccardo

# Check results
cat logs/validation-reports/*/summary.txt
```

---

## Support

For issues or questions:
1. Check the validation reports in `logs/validation-reports/`
2. Review backup files in `backups/`
3. Try single-language workflow to isolate issues
4. Check git history for original clean versions

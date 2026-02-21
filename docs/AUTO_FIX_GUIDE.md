# Automated Fix Guide

## One Command to Fix Everything

```bash
# Set your API key first
export OPENAI_API_KEY='your-openai-key-here'

# Run the automated fix (everything)
python3 auto_fix_all_issues.py
```

## What It Does

### Step 1: Remove Arabic Contamination (Automatic)
- Scans all translation files (except Persian, Kurdish, Urdu)
- Identifies verses with Arabic text contamination
- Removes contaminated verses or cleans partial contamination
- Creates backup before making changes

### Step 2: Fix AI Alignment Issues (Requires API Key)
- Re-runs alignment for 6 translations with >50 failures:
  - pt-elhayek (281 failures)
  - nl-siregar (74 failures)
  - ml-abdulhameed (73 failures)
  - es-navio (66 failures)
  - de-bo (52 failures)
  - ms-basmeih (51 failures)

### Step 3: Validate All Fixes
- Runs contamination check
- Analyzes remaining failures
- Generates report

## Options

### Fix Only Contamination (No API Key Needed)
```bash
python3 auto_fix_all_issues.py --no-alignment
```

### Fix Only Alignment Issues
```bash
export OPENAI_API_KEY='your-openai-key'
python3 auto_fix_all_issues.py --alignment-only
```

### Skip Validation
```bash
python3 auto_fix_all_issues.py --no-validate
```

## Output & Logging

### Comprehensive Logging
Everything is logged to **both console and file** in real-time:
- **Log file:** `logs/auto_fix_run_YYYYMMDD_HHMMSS.log`
- Includes timestamps for each step
- Shows progress for each translation (1/6, 2/6, etc.)
- Captures success/failure for each operation
- Total duration at the end

### Files Created
- `logs/auto_fix_run_*.log` - **Complete run log** with all output
- `backups/YYYYMMDD_HHMMSS/` - Backup of original files
- `logs/auto_fix_report_*.txt` - Detailed fix report summary
- `logs/failures-*-FIXED.json` - Updated failure logs per translation

### What Gets Fixed

**Contamination (138 verses):**
- ✓ ta-tamil: 58 verses
- ✓ bn-bengali: 26 verses
- ✓ ms-basmeih: 13 verses
- ✓ ml-abdulhameed: 12 verses
- ✓ bs-korkut: 11 verses
- ✓ And 8 others with <5 verses each

**Alignment (973 failures):**
- ⟳ pt-elhayek: 281 failures → re-aligned
- ⟳ nl-siregar: 74 failures → re-aligned
- ⟳ ml-abdulhameed: 73 failures → re-aligned
- ⟳ es-navio: 66 failures → re-aligned
- ⟳ de-bo: 52 failures → re-aligned
- ⟳ ms-basmeih: 51 failures → re-aligned

## After Running

1. **Review Log and Changes:**
   ```bash
   # View the complete run log
   cat logs/auto_fix_run_*.log

   # Check the summary report
   cat logs/auto_fix_report_*.txt

   # See what was modified in files
   git diff ksu-translations-formatted/
   ```

2. **Validate Results:**
   ```bash
   # Check remaining contamination
   python3 check_real_contamination.py

   # Check remaining failures
   python3 analyze_failures.py
   ```

3. **Restore if Needed:**
   ```bash
   # If something went wrong, restore from backup
   cp -r backups/YYYYMMDD_HHMMSS/ksu-translations-formatted .
   ```

4. **Commit if Satisfied:**
   ```bash
   git add ksu-translations-formatted/
   git commit -m "Auto-fix: Remove contamination and re-align translations"
   ```

## Estimated Runtime

- **Contamination cleanup:** ~1-2 minutes
- **Alignment fixes:** ~30-60 minutes (depends on API speed)
- **Validation:** ~1-2 minutes

**Total:** ~35-65 minutes for full run

## Troubleshooting

### "OPENAI_API_KEY not found"
```bash
# Set your API key
export OPENAI_API_KEY='your-openai-key-here'

# Or run without alignment fixes
python3 auto_fix_all_issues.py --no-alignment
```

### Script timeout
If alignment takes too long for some translations, the script will continue with the next one. Check logs for which ones completed.

### No changes made
If contamination check shows 0 verses, no cleanup is needed. The script will skip to alignment fixes.

## What NOT to Worry About

- **Persian (pr-tagi)** - Uses Arabic script legitimately ✓
- **Kurdish (ku-asan)** - Uses Arabic script legitimately ✓
- **Urdu (ur-gl)** - Uses Arabic script legitimately ✓

These are automatically skipped during contamination cleanup.

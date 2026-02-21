# Failures Log Guide

## Overview

The `--failures-log` parameter outputs all validation failures to a JSON file for manual review and correction.

## Usage

### Basic Usage
```bash
python3 fix_verse_alignments_with_retry.py \
  --provider openai \
  --api-key sk-xxx \
  --translation es-navio \
  --failures-log "logs/failures-es-navio.json"
```

### Output Directory Structure
```
logs/
├── failures-es-navio.json
├── failures-bn-bengali.json
├── failures-de-bo.json
└── ...
```

## JSON Output Format

```json
{
  "translation": "es-navio",
  "total_failures": 3,
  "generated_at": "2025-12-07T14:23:45.123456",
  "failures": [
    {
      "verse_key": "002_019",
      "chapter": 2,
      "verse_number": 19,
      "error": "Words added: ['additional', 'text']",
      "original_translation_splits": {
        "019_00": "Or like a storm with darkness and thunder.",
        "019_01": "They put fingers in ears. Allah encompasses disbelievers."
      },
      "arabic_reference_splits": {
        "019_00": "أَوۡ كَصَيِّبٖ مِّنَ ٱلسَّمَآءِ...",
        "019_01": "وَٱللَّهُ مُحِيطُۢ بِٱلۡكَٰفِرِينَ"
      },
      "combined_translation": "Or like a storm with darkness and thunder. They put fingers in ears. Allah encompasses disbelievers.",
      "timestamp": "2025-12-07T14:23:30.123456"
    }
  ]
}
```

## Field Descriptions

| Field | Description |
|-------|-------------|
| `translation` | Language code (e.g., "es-navio") |
| `total_failures` | Count of verses that failed validation |
| `generated_at` | Timestamp when log was created |
| `failures[]` | Array of failed verse records |
| `verse_key` | Unique identifier (chapter_verse) |
| `chapter` | Chapter number |
| `verse_number` | Verse number within chapter |
| `error` | Validation error message |
| `original_translation_splits` | Current (incorrect) splits |
| `arabic_reference_splits` | Reference splits to match |
| `combined_translation` | All parts combined (for manual splitting) |
| `timestamp` | When this failure occurred |

## Processing Failures Log

### Python Script to Review Failures
```python
import json

# Load failures log
with open('logs/failures-es-navio.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"Translation: {data['translation']}")
print(f"Total failures: {data['total_failures']}\n")

# Review each failure
for i, failure in enumerate(data['failures'], 1):
    print(f"\n{i}. Verse {failure['verse_key']} (Chapter {failure['chapter']})")
    print(f"   Error: {failure['error']}")
    print(f"\n   Combined text:")
    print(f"   {failure['combined_translation']}")
    print(f"\n   Current splits:")
    for verse_id, text in failure['original_translation_splits'].items():
        print(f"   {verse_id}: {text}")
    print(f"\n   Arabic reference:")
    for verse_id, text in failure['arabic_reference_splits'].items():
        arabic_preview = text[:80] + "..." if len(text) > 80 else text
        print(f"   {verse_id}: {arabic_preview}")
```

### Manual Correction Workflow

1. **Review the failure:**
   ```bash
   cat logs/failures-es-navio.json | jq '.failures[0]'
   ```

2. **Identify the issue:**
   - Check `error` field for what went wrong
   - Compare `original_translation_splits` with `arabic_reference_splits`
   - Look at `combined_translation` to see all text

3. **Manually correct in translation file:**
   ```bash
   # Edit the specific chapter file
   nano ksu-translations-formatted/es-navio/002.txt

   # Find verse 019_00 and 019_01
   # Redistribute text to match Arabic split point
   ```

4. **Verify correction:**
   ```bash
   # Re-run validator on that specific verse
   python3 test_alignment_finder.py
   ```

## Common Failure Patterns

### Pattern 1: Words Added
**Error:** `Words added: ['however', 'also']`

**Cause:** LLM paraphrased or added connector words

**Fix:** Remove added words, use only original text

### Pattern 2: Words Removed
**Error:** `Words removed: ['the', 'and']`

**Cause:** LLM dropped small words during redistribution

**Fix:** Ensure all original words are preserved

### Pattern 3: Repetition
**Error:** `Repeated text between splits 0 and 1: {'Allah'}`

**Cause:** LLM duplicated phrase in both splits

**Fix:** Remove duplicate, ensure each word appears only once

## Batch Processing with Logs

### Process All Translations and Collect Failures
```bash
#!/bin/bash
# Script to process all translations and collect failures

TRANSLATIONS=("es-navio" "bn-bengali" "de-bo" "id-indonesian")

for TRANS in "${TRANSLATIONS[@]}"; do
    echo "Processing $TRANS..."

    python3 fix_verse_alignments_with_retry.py \
        --provider gemini \
        --api-key $GEMINI_API_KEY \
        --translation $TRANS \
        --max-retries 2 \
        --failures-log "logs/failures-${TRANS}.json"

    echo "✓ $TRANS completed"
    echo ""
done

# Summarize all failures
echo "=== FAILURE SUMMARY ==="
for TRANS in "${TRANSLATIONS[@]}"; do
    if [ -f "logs/failures-${TRANS}.json" ]; then
        FAILURES=$(cat "logs/failures-${TRANS}.json" | jq '.total_failures')
        echo "$TRANS: $FAILURES failures"
    fi
done
```

## Analyzing Failures

### Count Failures by Error Type
```python
import json
from collections import Counter
from pathlib import Path

# Collect all failure logs
failure_counts = {}
error_types = Counter()

for log_file in Path('logs').glob('failures-*.json'):
    with open(log_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    translation = data['translation']
    failure_counts[translation] = data['total_failures']

    # Categorize errors
    for failure in data['failures']:
        error = failure['error']
        if 'added' in error.lower():
            error_types['words_added'] += 1
        elif 'removed' in error.lower():
            error_types['words_removed'] += 1
        elif 'repeated' in error.lower():
            error_types['repetition'] += 1
        else:
            error_types['other'] += 1

print("Failures by Translation:")
for trans, count in sorted(failure_counts.items()):
    print(f"  {trans}: {count}")

print("\nFailures by Error Type:")
for error_type, count in error_types.most_common():
    print(f"  {error_type}: {count}")
```

### Output Example:
```
Failures by Translation:
  bn-bengali: 8
  de-bo: 3
  es-navio: 5
  id-indonesian: 2

Failures by Error Type:
  words_added: 12
  words_removed: 4
  repetition: 2
```

## Export Failures for Manual Review

### Generate CSV for Spreadsheet Review
```python
import json
import csv
from pathlib import Path

# Load failures
with open('logs/failures-es-navio.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Export to CSV
with open('logs/failures-es-navio.csv', 'w', newline='', encoding='utf-8') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(['Verse', 'Chapter', 'Error', 'Combined Text', 'Current Splits'])

    for failure in data['failures']:
        verse = failure['verse_key']
        chapter = failure['chapter']
        error = failure['error']
        combined = failure['combined_translation']

        # Format splits
        splits = ' | '.join([f"{k}: {v}" for k, v in failure['original_translation_splits'].items()])

        writer.writerow([verse, chapter, error, combined, splits])

print("CSV exported to logs/failures-es-navio.csv")
```

## Integration with CI/CD

### GitHub Actions Example
```yaml
name: Validate Translations

on: [push, pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'

      - name: Install dependencies
        run: pip install openai google-generativeai

      - name: Run validator with failures log
        run: |
          python3 fix_verse_alignments_with_retry.py \
            --provider gemini \
            --api-key ${{ secrets.GEMINI_API_KEY }} \
            --translation es-navio \
            --failures-log logs/failures-es-navio.json

      - name: Upload failures log
        uses: actions/upload-artifact@v2
        if: failure()
        with:
          name: validation-failures
          path: logs/*.json

      - name: Check for failures
        run: |
          if [ -f "logs/failures-es-navio.json" ]; then
            FAILURES=$(cat logs/failures-es-navio.json | jq '.total_failures')
            if [ "$FAILURES" -gt "0" ]; then
              echo "❌ $FAILURES validation failures found"
              exit 1
            fi
          fi
```

## Best Practices

1. **Always use `--failures-log`** when processing new translations
2. **Review failures before moving to next translation** - patterns may indicate systematic issues
3. **Keep logs organized** by translation and date:
   ```
   logs/
   ├── 2025-12-07/
   │   ├── failures-es-navio.json
   │   └── failures-bn-bengali.json
   └── 2025-12-08/
       └── failures-de-bo.json
   ```
4. **Version control logs** to track improvements over time
5. **Set up alerts** for high failure rates (>10%)

## Troubleshooting

### No log file generated
**Issue:** Script completes but no log file created

**Causes:**
- No failures occurred (good!)
- Path doesn't exist and couldn't be created
- No write permissions

**Solution:**
```bash
# Check if directory exists
mkdir -p logs

# Verify permissions
ls -la logs/

# Run with explicit path
--failures-log "$(pwd)/logs/failures-test.json"
```

### JSON parsing errors
**Issue:** Can't read log file with jq or Python

**Cause:** Corrupted or incomplete write

**Solution:**
```bash
# Validate JSON
cat logs/failures-es-navio.json | jq '.'

# If invalid, check file size
ls -lh logs/failures-es-navio.json

# Re-run with fresh log file
rm logs/failures-es-navio.json
```

---

**Pro Tip:** Combine failures log with version control to track which corrections were applied manually vs. automatically:
```bash
# Before manual corrections
cp logs/failures-es-navio.json logs/failures-es-navio-ORIGINAL.json

# After manual fixes
git diff ksu-translations-formatted/es-navio/

# Document what was manually corrected
```

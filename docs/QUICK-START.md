# Quick Start Guide - Verse Alignment Validator

## TL;DR - Recommended Usage

### Option 1: Using Environment Variables (Recommended)
```bash
# Set API key once
export GEMINI_API_KEY="your-key-here"
# or for OpenAI
export OPENAI_API_KEY="sk-your-key-here"

# Run - failures are logged by default to logs/failures-{translation}.json
python3 fix_verse_alignments_with_retry.py \
  --provider gemini \
  --translation es-navio \
  --max-retries 2
```

### Option 2: Using Command Line Argument
```bash
python3 fix_verse_alignments_with_retry.py \
  --provider gemini \
  --api-key YOUR_GEMINI_KEY \
  --translation es-navio \
  --max-retries 2 \
  --failures-log "logs/failures-es-navio.json"
```

## What This Does

1. ✅ Finds verses with splits (yy > 0) in the translation
2. ✅ Redistributes words to match Arabic reference split points
3. ✅ Validates NO words are added/removed (only reordered)
4. ✅ Retries failed validations up to 2 times with enhanced prompts
5. ✅ Logs any remaining failures to JSON file for manual review
6. ✅ Applies only validated corrections to files

## Files Overview

| File | Purpose | When to Use |
|------|---------|-------------|
| `fix_verse_alignments_improved.py` | With validation, no retry | Testing/preview |
| `fix_verse_alignments_with_retry.py` | **With retry + logging** | **Production (recommended)** |
| `test_alignment_finder.py` | Test without API calls | Check which verses need fixing |
| `VALIDATOR-README.md` | Full documentation | Complete reference |
| `FAILURES-LOG-GUIDE.md` | Failures log usage | Manual review workflow |
| `RETRY-COMPARISON.md` | Feature comparison | Understanding differences |

## Environment Variables Setup

The script supports reading API keys from environment variables:

### For Gemini (Google)
```bash
export GEMINI_API_KEY="your-gemini-key"
# or
export GOOGLE_API_KEY="your-google-key"
```

### For OpenAI
```bash
export OPENAI_API_KEY="sk-your-openai-key"
```

### Permanent Setup (Optional)
Add to your `~/.bashrc` or `~/.zshrc`:
```bash
# For Gemini
echo 'export GEMINI_API_KEY="your-key-here"' >> ~/.bashrc
source ~/.bashrc

# For OpenAI
echo 'export OPENAI_API_KEY="sk-your-key-here"' >> ~/.bashrc
source ~/.bashrc
```

### Verify Environment Variable
```bash
# Check if set
echo $GEMINI_API_KEY
echo $OPENAI_API_KEY
```

## Step-by-Step First Run

### 1. Test Without API Calls
```bash
# See which verses need alignment
python3 test_alignment_finder.py
```

**Output:**
```
Found 142 misaligned verses:

1. Chapter 002, Verse 019_01
   Arabic: أَوۡ كَصَيِّبٖ مِّنَ ٱلسَّمَآءِ...
   Translation: El estampido del rayo...
```

### 2. Backup Your Data
```bash
# Always backup before running
cp -r ksu-translations-formatted ksu-translations-formatted.backup
```

### 3. Run on Single Translation
```bash
# Make sure GEMINI_API_KEY is set
export GEMINI_API_KEY="your-key-here"

# Run the validator
python3 fix_verse_alignments_with_retry.py \
  --provider gemini \
  --translation es-navio \
  --max-retries 2 \
  --failures-log "logs/failures-es-navio.json"
```

**Output:**
```
Finding verses with splits in es-navio...
Found 142 verse parts with splits
Processing 47 batches with max 2 retries per failure...

Batch 1/47...
  ✅ 002_019: Validated and corrected
  ❌ 002_020: Content validation failed: Words added: ['additional']
  🔄 002_020: Retry 1/2...
  ✅ 002_020: Retry successful!

============================================================
VALIDATION RESULTS:
  Successful corrections: 45
  Failed validations: 2
  Total retry attempts: 8
  Successful retries: 6
============================================================

📝 Failures log written to: logs/failures-es-navio.json
   Total failed verses: 2

✅ Applied 45 corrections to es-navio
```

### 4. Review Failures (If Any)
```bash
# View failures
cat logs/failures-es-navio.json | jq '.'

# Or use Python
python3 << EOF
import json
with open('logs/failures-es-navio.json', 'r') as f:
    data = json.load(f)
print(f"Failures: {data['total_failures']}")
for failure in data['failures']:
    print(f"\n{failure['verse_key']}: {failure['error']}")
    print(f"Text: {failure['combined_translation'][:100]}...")
EOF
```

### 5. Verify Changes
```bash
# See what changed
git diff ksu-translations-formatted/es-navio/002.txt

# Or compare with backup
diff ksu-translations-formatted.backup/es-navio/002.txt \
     ksu-translations-formatted/es-navio/002.txt
```

### 6. Manual Fix Failures (If Needed)
```bash
# Edit the file
nano ksu-translations-formatted/es-navio/002.txt

# Find the verse ID from failures log
# Manually redistribute text to match Arabic split
```

## Command Reference

### Required Parameters
- `--provider`: `openai` or `gemini`
- `--translation`: Language code (e.g., `es-navio`, `bn-bengali`)

### API Key (One Required)
- `--api-key`: Provide key via command line
- OR set environment variable:
  - `OPENAI_API_KEY` for OpenAI
  - `GEMINI_API_KEY` or `GOOGLE_API_KEY` for Gemini

### Optional Parameters
- `--max-retries 2`: Retry failed validations (default: 2)
- `--failures-log "path.json"`: Custom path for failures log (default: `logs/failures-{translation}.json`)
- `--no-failures-log`: Disable failures logging entirely
- `--batch-size 3`: Verses per API call (default: 3)
- `--delay 1.5`: Seconds between batches (default: 1.5)

**Note:** Failures are logged by default. Use `--no-failures-log` to disable.

## Common Scenarios

### Scenario 1: Process One Translation
```bash
# Set API key (do once)
export GEMINI_API_KEY="your-key"

# Run validator (failures auto-logged to logs/failures-es-navio.json)
python3 fix_verse_alignments_with_retry.py \
  --provider gemini \
  --translation es-navio \
  --max-retries 2
```

### Scenario 2: Process All Translations
```bash
# Set API key
export GEMINI_API_KEY="your-key"

# Create a script - each translation auto-logs to its own file
for LANG in es-navio bn-bengali de-bo id-indonesian; do
  echo "Processing $LANG..."
  python3 fix_verse_alignments_with_retry.py \
    --provider gemini \
    --translation $LANG \
    --max-retries 2
  # Failures logged to logs/failures-${LANG}.json automatically
done
```

### Scenario 3: High Failure Rate (>20%)
```bash
# Try different provider with more retries
export OPENAI_API_KEY="sk-your-key"

python3 fix_verse_alignments_with_retry.py \
  --provider openai \  # Try different provider
  --translation problematic-lang \
  --max-retries 3 \    # More retries
  --batch-size 2       # Smaller batches = better focus
  # Failures auto-logged to logs/failures-problematic-lang.json
```

### Scenario 4: Custom Log Path or Disable Logging
```bash
# Custom log path
python3 fix_verse_alignments_with_retry.py \
  --provider gemini \
  --translation es-navio \
  --failures-log "custom/path/my-failures.json"

# Disable logging entirely
python3 fix_verse_alignments_with_retry.py \
  --provider gemini \
  --translation es-navio \
  --no-failures-log
```

### Scenario 5: Just Testing (No Changes)
```bash
# Use test script (no API calls, no changes)
python3 test_alignment_finder.py
```

## Understanding Output

### Success Indicators
```
✅ 002_019: Validated and corrected
```
- Verse passed all validations
- Correction applied to file
- No manual intervention needed

### Retry Indicators
```
❌ 002_020: Content validation failed: Words added: ['extra']
🔄 002_020: Retry 1/2...
✅ 002_020: Retry successful!
```
- Initial attempt failed
- Retry with enhanced prompt succeeded
- Correction applied

### Failure Indicators
```
❌ 002_025: Failed after 2 retries
```
- All retry attempts exhausted
- Logged to failures file (if specified)
- Requires manual review

## Cost Estimates

| Translation | Verses | API Calls | Cost (Gemini) | Cost (OpenAI) |
|-------------|--------|-----------|---------------|---------------|
| es-navio    | 142    | ~47       | ~$0.02        | ~$0.08        |
| bn-bengali  | 138    | ~46       | ~$0.02        | ~$0.07        |
| All (14)    | ~2000  | ~667      | ~$0.30        | ~$1.00        |

**Note:** Costs include estimated retry overhead (~15% additional calls)

## Troubleshooting

### "Error: API key not found"
**Cause:** Neither `--api-key` provided nor environment variable set

**Action:**
```bash
# Option 1: Set environment variable
export GEMINI_API_KEY="your-key"
# or
export OPENAI_API_KEY="sk-your-key"

# Option 2: Use command line argument
--api-key "your-key"

# Verify environment variable is set
echo $GEMINI_API_KEY
```

### "No verses with splits found"
**Cause:** Translation already aligned, or no splits exist

**Action:** Check Arabic reference has splits: `grep "_01" chs-ar-final/002`

### "Validation failed: Words added"
**Cause:** LLM paraphrased instead of redistributing

**Action:** Retry will fix ~70% of cases. Check failures log for rest.

### "API rate limit exceeded"
**Cause:** Too many requests too fast

**Action:** Increase `--delay` to 2.0 or higher

### "Translation directory not found"
**Cause:** Wrong path or language code

**Action:** List available: `ls ksu-translations-formatted/`

## Best Practices

1. ✅ **Always backup first:** `cp -r ksu-translations-formatted{,.backup}`
2. ✅ **Test on one translation first** before batch processing
3. ✅ **Use failures log:** `--failures-log` for manual review tracking
4. ✅ **Review failures immediately** before processing next translation
5. ✅ **Use version control:** `git diff` to review all changes
6. ✅ **Keep logs organized:** `logs/YYYY-MM-DD/failures-*.json`

## Next Steps

1. Read [VALIDATOR-README.md](VALIDATOR-README.md) for complete documentation
2. Check [FAILURES-LOG-GUIDE.md](FAILURES-LOG-GUIDE.md) for manual review workflow
3. See [RETRY-COMPARISON.md](RETRY-COMPARISON.md) for feature comparison

---

**Quick Help:**
- Issues? Check logs: `cat logs/failures-*.json | jq '.total_failures'`
- Questions? Read VALIDATOR-README.md
- Feature comparison? Read RETRY-COMPARISON.md

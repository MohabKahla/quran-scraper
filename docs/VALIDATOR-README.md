# Quran Translation Verse Alignment Validator

## Overview

This tool fixes verse split misalignments between Quran translations and the Arabic reference text. It uses LLMs to semantically redistribute translation text to match Arabic verse splits **without modifying any words** - only reordering them.

## File Structure Understanding

### Verse ID Format: `xxx_yy`
- **xxx**: Verse number (001-286 depending on chapter)
- **yy**: Split number within the verse (00, 01, 02, etc.)

### Example
```
019_00  → Verse 19, first part (split 0)
019_01  → Verse 19, second part (split 1)
020_00  → Verse 20, complete (no split)
```

**Important**: Split IDs in translations MUST exactly match Arabic reference. If Arabic has `019_00` and `019_01`, the translation must have the exact same IDs.

## How It Works

### 1. Input Structure
- **Arabic Reference**: `chs-ar-final/` directory containing files `001` to `114`
- **Translations**: `ksu-translations-formatted/{lang}/` containing files `001.txt` to `114.txt`
- Each file contains tab-separated verses: `verse_id\tverse_text`

### 2. Process Flow

```
┌─────────────────────────────────────────────────┐
│ 1. FIND MISALIGNED VERSES                       │
│    - Load Arabic reference                      │
│    - Load translation                           │
│    - Find verses with splits (yy > 0)           │
└─────────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────┐
│ 2. BATCH PROCESSING                             │
│    - Group by complete verses                   │
│    - Create batches (default: 3 verses/batch)   │
└─────────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────┐
│ 3. LLM PROCESSING                               │
│    - Send verse groups to LLM                   │
│    - LLM redistributes words to match Arabic    │
│    - Returns JSON with corrected splits         │
└─────────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────┐
│ 4. VALIDATION (3 Checks)                        │
│    ✓ No words added/removed                     │
│    ✓ No sentence repetition across splits       │
│    ✓ Split IDs match Arabic exactly             │
└─────────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────┐
│ 5. APPLY CORRECTIONS                            │
│    - Only validated corrections applied         │
│    - Failed validations rejected & logged       │
└─────────────────────────────────────────────────┘
```

## Validation Rules

### Rule 1: ID Correspondence ✓
**Requirement**: Translation split IDs must EXACTLY match Arabic reference IDs.

**Example**:
```
Arabic:          Translation (CORRECT):
019_00 → ...     019_00 → ...
019_01 → ...     019_01 → ...

Translation (WRONG):
019_00 → ...
020_00 → ...  ❌ Missing 019_01
```

### Rule 2: No Content Modification ✓
**Requirement**: ZERO words added or removed. Only redistribute existing words.

**Validation Method**:
- Normalize text (lowercase, remove punctuation)
- Count word frequencies before/after
- Compare: `Counter(original_words) == Counter(corrected_words)`

**Example**:
```
Original: "The sky is blue. Birds fly high."
✓ VALID:   "The sky is blue." + "Birds fly high."
✗ INVALID: "The beautiful sky is blue." + "Birds fly high."  (added "beautiful")
✗ INVALID: "The sky." + "Birds fly high."  (removed "is blue")
```

### Rule 3: No Sentence Repetition ✓
**Requirement**: No duplicate sentences across splits within the same verse.

**Validation Method**:
- Split each part by sentence delimiters (. ! ?)
- Check for exact sentence overlap between splits
- Flag any duplicates

**Example**:
```
✓ VALID:
  019_00: "The storm has darkness and thunder."
  019_01: "Allah encompasses the disbelievers."

✗ INVALID:
  019_00: "The storm has darkness. Allah encompasses."
  019_01: "Allah encompasses the disbelievers."  (repeated "Allah encompasses")
```

## Usage

### Prerequisites
```bash
pip install openai google-generativeai aiohttp
```

### Basic Usage

#### Test Mode (No API Calls)
Check which verses need alignment without calling LLMs:
```bash
python3 test_alignment_finder.py
```

#### Fix Single Translation
```bash
python3 fix_verse_alignments_improved.py \
  --provider openai \
  --api-key sk-your-key-here \
  --translation es-navio \
  --batch-size 3 \
  --delay 1.5
```

#### Fix All Translations
```bash
python3 fix_all_translations.py \
  --provider gemini \
  --api-key YOUR_GEMINI_KEY \
  --batch-size 5 \
  --delay 2.0
```

### Command-Line Arguments

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--provider` | ✓ | - | LLM provider: `openai` or `gemini` |
| `--api-key` | ✓ | - | API key for chosen provider |
| `--translation` | ✓ | - | Language code (e.g., `es-navio`, `bn-bengali`) |
| `--batch-size` | ✗ | 3 | Number of verses per API call |
| `--delay` | ✗ | 1.5 | Seconds between API calls (rate limiting) |
| `--arabic-dir` | ✗ | `chs-ar-final` | Arabic reference directory |
| `--translations-dir` | ✗ | `ksu-translations-formatted` | Translations directory |

### Supported Providers

#### OpenAI
- Model: `gpt-4o-mini`
- API Key format: `sk-...`
- Rate limit: ~500 requests/minute

#### Google Gemini
- Model: `gemini-2.0-flash-exp`
- API Key: No specific format
- Rate limit: Varies by tier

## LLM Prompt Engineering

### Key Improvements in Improved Version

**Original Prompt Issues**:
- Verbose and repetitive
- Incorrect example IDs (showed 002_019 instead of verse-specific)
- Lacked precision on "no modification" rule

**Improved Prompt**:
```
CRITICAL RULES:
1. NEVER add, remove, or modify ANY words
2. ONLY redistribute existing words at SAME semantic boundary
3. Split IDs must EXACTLY match Arabic reference
4. Combine ALL translation parts, then split at same point as Arabic
5. Each split must contain complete semantic units

[Clear example with correct IDs]
[Verse-by-verse data with Arabic previews]
```

**Why This Works**:
- **Clarity**: Explicit "NEVER add/remove" instruction
- **Context**: Shows Arabic text length to guide split point
- **Structure**: JSON-only output reduces parsing errors
- **Examples**: Concrete before/after demonstration

## Output & Logging

### Console Output
```
Finding verses with splits in es-navio...
Found 142 verse parts with splits
Processing 47 batches...

Batch 1/47...
  ✅ 002_019: Validated and corrected
  ✅ 002_020: Validated and corrected
  ❌ 002_025: Content validation failed:
     - Words added: ['additional']

Batch 2/47...
  ⚠️  002_026: Repetition detected:
     - Repeated text between splits 0 and 1: {'Allah'}
  ✅ 002_026: Validated and corrected

⚠️  3 verses failed validation and were NOT corrected

✅ Applied 44 corrections to es-navio
```

### Validation Failure Handling
- Failed validations are **logged but NOT applied**
- Manual review required for failed verses
- Prevents corrupted data from entering translations

## Common Issues & Solutions

### Issue 1: Missing Split IDs
**Problem**: Translation has `019_00` but missing `019_01` which exists in Arabic.

**Solution**: Script detects this in `find_misaligned_verses()` and includes both IDs for correction.

### Issue 2: Extra Split IDs
**Problem**: Translation has `019_00, 019_01, 019_02` but Arabic only has `019_00, 019_01`.

**Detection**: `validate_split_ids()` flags extra IDs.

**Solution**: Manual review needed - likely indicates deeper structural issue.

### Issue 3: LLM Adds/Removes Words
**Problem**: Despite prompt, LLM modifies content.

**Protection**: `validate_no_content_change()` catches this using word frequency comparison.

**Action**: Correction rejected, logged as validation failure.

### Issue 4: Repeated Sentences
**Problem**: Same sentence appears in multiple splits.

**Detection**: `validate_no_repetition()` checks sentence overlap.

**Action**: Warning logged, but correction may still be applied if not severe.

## File Modifications

### Backup Strategy
**Important**: Always backup translations before running:
```bash
cp -r ksu-translations-formatted ksu-translations-formatted.backup
```

### What Gets Modified
- Only translation files in `ksu-translations-formatted/{lang}/`
- Arabic reference files are **never modified**
- Only successfully validated corrections are applied

## Performance Considerations

### API Costs
- **OpenAI (gpt-4o-mini)**: ~$0.15 per 1M input tokens, ~$0.60 per 1M output tokens
- **Gemini (2.0-flash-exp)**: Free tier available, then $0.075 per 1M tokens

**Estimated Cost for Full Translation** (142 verse parts):
- ~47 API calls at 3 verses/batch
- ~2,000 tokens per call
- Total: ~$0.05-$0.10 per translation (OpenAI), cheaper with Gemini

### Rate Limiting
- Default delay: 1.5 seconds between batches
- Adjust `--delay` if hitting rate limits
- Batch size affects total API calls: `calls = ceil(verses / batch_size)`

### Processing Time
- ~2-3 seconds per batch (API call + validation)
- 142 verses / 3 per batch = 47 batches
- Total: ~2-5 minutes per translation

## Verification After Processing

### Manual Spot Check
```bash
# Compare before/after for specific verse
diff ksu-translations-formatted.backup/es-navio/002.txt \
     ksu-translations-formatted/es-navio/002.txt
```

### Count Validation
```bash
# Ensure verse counts didn't change
wc -l ksu-translations-formatted.backup/es-navio/*.txt
wc -l ksu-translations-formatted/es-navio/*.txt
```

### Word Count Check
```python
# Verify no words added/removed across entire file
import re

def count_words(file):
    with open(file) as f:
        text = f.read()
    words = re.findall(r'\w+', text.lower())
    return len(words)

before = count_words('ksu-translations-formatted.backup/es-navio/002.txt')
after = count_words('ksu-translations-formatted/es-navio/002.txt')
assert before == after, f"Word count changed: {before} → {after}"
```

## Advanced Usage

### Dry Run Mode
To preview changes without applying:
1. Modify `_apply_corrections()` to print instead of write
2. Or use git to review diffs before committing

### Custom Validation
Add custom validators to `VerseValidator` class:
```python
@staticmethod
def validate_custom_rule(splits: List[str]) -> ValidationResult:
    errors = []
    # Your custom validation logic
    return ValidationResult(is_valid=len(errors)==0, errors=errors, warnings=[])
```

### Batch All Translations
```bash
# Process all available translations sequentially
python3 fix_all_translations.py --provider gemini --api-key YOUR_KEY
```

## Troubleshooting

### Error: "Translation directory not found"
**Cause**: Wrong `--translations-dir` or `--translation` parameter.
**Fix**: Verify path exists: `ls ksu-translations-formatted/`

### Error: "Arabic reference not found"
**Cause**: Missing Arabic files in `chs-ar-final/`.
**Fix**: Ensure Arabic reference files exist for all chapters.

### Error: "JSON parsing failed"
**Cause**: LLM returned malformed JSON.
**Fix**:
- Check API key validity
- Try different provider
- Reduce batch size to simplify prompts

### Warning: "Word count changed"
**Cause**: LLM added/removed words despite instructions.
**Action**: Validation automatically rejects this correction. No manual action needed.

## Contributing

### Adding New Providers
1. Add provider class in `LLMClient`
2. Implement `_call_{provider}()` method
3. Update argument choices in `argparse`

### Improving Validation
1. Add new validator method to `VerseValidator`
2. Call in `process_translation()` before applying corrections
3. Update this README with new validation rule

## License & Attribution

Part of the Quran Scraper project. See main README.md for details.

---

**Last Updated**: 2025-12-07
**Script Version**: 2.0 (Improved with comprehensive validation)

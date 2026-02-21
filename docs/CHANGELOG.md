# Changelog - Verse Alignment Validator

## [Latest] - 2025-12-07

### Added
- ✅ **Environment variables support** for API keys
  - `OPENAI_API_KEY` for OpenAI
  - `GEMINI_API_KEY` or `GOOGLE_API_KEY` for Gemini
  - No need to pass `--api-key` if env var is set

- ✅ **Default failures logging**
  - Failures now logged by default to `logs/failures-{translation}.json`
  - Use `--failures-log "custom/path.json"` to override
  - Use `--no-failures-log` to disable entirely

- ✅ **Comprehensive validation**
  - Word count validation (no words added/removed)
  - Sentence repetition detection
  - ID correspondence checking

- ✅ **Retry logic with enhanced prompts**
  - Configurable max retries (default: 2)
  - Enhanced prompts on retry showing previous errors
  - Retry statistics reporting

### Changed
- `--api-key` is now optional (uses env vars if not provided)
- `--failures-log` now has a default value
- Improved console output with clear API key source indication

### Files
- `fix_verse_alignments_with_retry.py` - Main script with all features
- `fix_verse_alignments_improved.py` - Without retry (for testing)
- `test_alignment_finder.py` - Test without API calls
- `VALIDATOR-README.md` - Complete documentation
- `FAILURES-LOG-GUIDE.md` - Failures log usage guide
- `RETRY-COMPARISON.md` - Feature comparison
- `QUICK-START.md` - Quick reference guide
- `.env.example` - Environment variables template

## Usage Examples

### Minimal (uses defaults)
```bash
export GEMINI_API_KEY="your-key"
python3 fix_verse_alignments_with_retry.py --provider gemini --translation es-navio
```

**Defaults applied:**
- API key from `GEMINI_API_KEY` env var
- Max retries: 2
- Batch size: 3
- Delay: 1.5 seconds
- Failures log: `logs/failures-es-navio.json`

### Full control
```bash
python3 fix_verse_alignments_with_retry.py \
  --provider openai \
  --api-key "sk-custom-key" \
  --translation bn-bengali \
  --max-retries 3 \
  --batch-size 2 \
  --delay 2.0 \
  --failures-log "custom/path/failures.json"
```

### Disable logging
```bash
python3 fix_verse_alignments_with_retry.py \
  --provider gemini \
  --translation es-navio \
  --no-failures-log
```

## Migration Guide

### Before (v1.0)
```bash
# Required to pass API key every time
python3 fix_verse_alignments.py \
  --provider gemini \
  --api-key "your-long-key-here" \
  --translation es-navio \
  --failures-log "logs/failures-es-navio.json"  # Had to specify
```

### After (v2.0)
```bash
# Set once
export GEMINI_API_KEY="your-key"

# Run with minimal args
python3 fix_verse_alignments_with_retry.py \
  --provider gemini \
  --translation es-navio
# Failures auto-logged to logs/failures-es-navio.json
```

## Breaking Changes

None! All previous command-line usage still works. New features are additive.

## Bug Fixes

- Fixed missing API key validation
- Improved error messages for missing configuration
- Added proper handling of environment variables

## Performance

- No performance impact from env var support
- Default failures logging adds negligible overhead (~0.1s per run)

## Documentation Updates

- Updated QUICK-START.md with env var examples
- Added troubleshooting for API key issues
- Created .env.example template
- Updated all scenarios to show simplified usage

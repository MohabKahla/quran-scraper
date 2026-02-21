# Translation Validation Report

**Generated:** 2026-02-21
**Validation Scope:** All ksu-translations-formatted vs ksu-translations (original)

## Summary

Total translations validated: **22 languages**
Total mismatches found: **3,757**
- **Formatting only** (>99% similarity): **3,475** (92.5%) - Can be ignored
- **Real issues** (<99% similarity): **282** (7.5%) - Require attention

## Breakdown by Language

| Language | Total Issues | Real Issues | Formatting Only |
|----------|--------------|-------------|-----------------|
| zh-jian | 980 | 81 | 899 |
| es-navio | 661 | 33 | 628 |
| bn-bengali | 132 | 30 | 102 |
| pt-elhayek | 468 | 21 | 447 |
| ha-gumi | 134 | 16 | 118 |
| it-piccardo | 49 | 16 | 33 |
| th-thai | 284 | 16 | 268 |
| bs-korkut | 108 | 15 | 93 |
| de-bo | 72 | 14 | 58 |
| id-indonesian | 75 | 14 | 61 |
| ml-abdulhameed | 36 | 10 | 26 |
| sq-nahi | 56 | 9 | 47 |
| nl-siregar | 81 | 2 | 79 |
| pr-tagi | 186 | 2 | 184 |
| ms-basmeih | 98 | 1 | 97 |
| ru-ku | 12 | 1 | 11 |
| sv-bernstrom | 62 | 1 | 61 |

## Categories of Real Issues

Based on analysis of the first 20 real issues:

### 1. **Split Boundary Errors** (Most Common)

**Problem:** Verses are split into parts, but the content is in wrong order or parts are misaligned with the Arabic reference.

**Example - bn-bengali ch002 v085:**
- Original (correct): "Then you kill each other... Do you believe in part of the book..."
- Formatted (wrong order): Starts with "Do you believe in part of the book..." and ends with "Then you kill each other..."
- Arabic reference: Has 4 parts (085_00 to 085_03)
- Bengali formatted: Has 4 parts but content is shuffled

**Languages affected:**
- bn-bengali: Multiple verses with shuffled content
- Likely affects other languages too

**Fix required:** Re-parse verse using OpenAI API to match Arabic split structure exactly.

### 2. **Character Changes / Typos**

**Problem:** Formatted version has slight character differences from original (not spacing).

**Example - bn-bengali ch002 v200:**
- Original: "অতঃপর যখন" (After then when)
- Formatted: "অতঃপর যারপর" (slight variation)

**Fix required:** Copy text from original translation (source of truth).

### 3. **Arabic Text Contamination**

**Problem:** Formatted version contains Arabic words mixed with translation.

**Example (from previous analysis):**
- ha-gumi ch041 v047: Contains `وَيَوۡمَ يُنَادِيهِمۡ`
- ha-gumi ch028 v025: Contains `FALAMMA JAA'AHU`

**Fix required:** Replace contaminated text with original translation.

### 4. **Truncation / Extra Content**

**Problem:** Formatted version is significantly shorter or longer than original.

**Examples:**
- bn-bengali ch006 v006: Formatted has -136 chars
- bn-bengali ch002 v196: Formatted has +282 chars

**Fix required:** Manual review to determine if this is intentional or error.

## Good News

**Successfully Fixed Previously:**
- ✅ ha-gumi ch003 v79
- ✅ ha-gumi ch027 v19

These are no longer in the mismatches list.

## Recommendations

### Priority 1: Split Boundary Errors
These are the most widespread issue affecting translation integrity.

**Action Required:**
1. For each language with split boundary errors:
   - Get Arabic reference structure from `data/chs-ar-final/`
   - Re-parse the verse using OpenAI API
   - Prompt: "Split this translation text to match the Arabic verse structure. Preserve exact wording, only add line breaks at same positions as Arabic."

**Estimated verses affected:** 100-200 across all languages

### Priority 2: Arabic Contamination
Straightforward fixes - replace with original.

**Action Required:**
Run auto-fix script to detect and replace Arabic-contaminated verses.

**Estimated verses affected:** 5-10

### Priority 3: Character Changes
Simple copy from original.

**Action Required:**
Run auto-fix script to copy text from original to formatted for verses with character differences.

**Estimated verses affected:** 50-100

### Priority 4: Truncations
Need manual review to determine if correct or error.

**Action Required:**
Manual inspection of verses with significant length differences (>50 chars).

**Estimated verses affected:** 20-30

## Scripts Created

1. **`scripts/validation/auto_fix_real_issues_v2.py`**
   - Detects Arabic contamination
   - Compares normalized texts
   - Can copy from original to formatted

2. **`logs/mismatches-all-languages.json`**
   - Detailed breakdown of all 3,757 mismatches
   - Includes similarity scores, original/formatted text

## Next Steps

1. **Immediate:** Run auto-fix script on all 282 real issues to fix:
   - Arabic contamination
   - Character changes

2. **Manual Review:** Review verses marked for manual review to categorize:
   - Split boundary errors (needs OpenAI re-parse)
   - Legitimate truncations (keep as-is)
   - Actual errors (fix manually)

3. **OpenAI Re-parse:** Batch process verses with split boundary errors using check_translation_splits.py with --provider openai

4. **Final Validation:** Re-run compare_formatted_vs_original.py to confirm all issues resolved

## Files Generated

- `logs/mismatches-all-languages.json` - Full validation data
- `logs/mismatches-ha-gumi-fresh.json` - ha-gumi specific
- `logs/validation-report.md` - This report

## Conclusion

**92.5%** of detected mismatches are just formatting improvements (spacing, punctuation) and can be safely ignored.

**7.5%** (282 verses) have real issues that need fixing. Most of these are split boundary errors that require re-parsing with OpenAI to match the Arabic reference structure.

**Translation integrity is generally good** - the original translation text is preserved in most cases, just needs re-organization to match Arabic verse splits.

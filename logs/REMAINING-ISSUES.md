# Remaining Issues - Actionable Fix List

**Generated:** 2026-02-21
**Status:** After automated fixes

---

## Summary

- **Total remaining issues:** 171
- **High priority (truncations):** 49 verses
- **Medium priority (content differences):** 11 verses
- **Low priority (spacing):** 111 verses (can ignore)

---

## High Priority Issues (49 verses)

These have significant content differences (<95% similarity). Many appear to be actual truncations where formatted version is missing content from original.

### How to Fix High Priority Issues

For each verse below:
1. Open the **original file** at the path shown
2. Find the verse (line number = verse number)
3. Copy the full text
4. Open the **formatted file**
5. Replace the verse parts with the original text
6. Split according to Arabic reference structure if needed

---

### es-navio (Spanish - 20 verses)

| Chapter | Verse | Similarity | Missing | Formatted Path | Original Path |
|---------|-------|------------|---------|----------------|---------------|
| 2 | 144 | 57.2% | 67 chars | `data/ksu-translations-formatted/es-navio/002.txt` | `data/old-translations/ksu-translations/es-navio/002.txt` |
| 2 | 233 | 47.6% | 7 chars | `data/ksu-translations-formatted/es-navio/002.txt` | `data/old-translations/ksu-translations/es-navio/002.txt` |
| 2 | 247 | 54.7% | 2 chars | `data/ksu-translations-formatted/es-navio/002.txt` | `data/old-translations/ksu-translations/es-navio/002.txt` |
| 2 | 267 | 55.7% | 49 chars | `data/ksu-translations-formatted/es-navio/002.txt` | `data/old-translations/ksu-translations/es-navio/002.txt` |
| 3 | 13 | 72.4% | 30 chars | `data/ksu-translations-formatted/es-navio/003.txt` | `data/old-translations/ksu-translations/es-navio/003.txt` |
| 5 | 5 | 90.9% | 34 chars | `data/ksu-translations-formatted/es-navio/005.txt` | `data/old-translations/ksu-translations/es-navio/005.txt` |
| 5 | 73 | 50.6% | +1 char | `data/ksu-translations-formatted/es-navio/005.txt` | `data/old-translations/ksu-translations/es-navio/005.txt` |
| 6 | 114 | 80.6% | 1 char | `data/ksu-translations-formatted/es-navio/006.txt` | `data/old-translations/ksu-translations/es-navio/006.txt` |
| 7 | 137 | 48.7% | 15 chars | `data/ksu-translations-formatted/es-navio/007.txt` | `data/old-translations/ksu-translations/es-navio/007.txt` |
| 9 | 7 | 74.5% | 97 chars | `data/ksu-translations-formatted/es-navio/009.txt` | `data/old-translations/ksu-translations/es-navio/009.txt` |
| 9 | 67 | 17.2% | 2 chars | `data/ksu-translations-formatted/es-navio/009.txt` | `data/old-translations/ksu-translations/es-navio/009.txt` |
| 11 | 84 | 70.0% | 3 chars | `data/ksu-translations-formatted/es-navio/011.txt` | `data/old-translations/ksu-translations/es-navio/011.txt` |
| 11 | 88 | 72.9% | 43 chars | `data/ksu-translations-formatted/es-navio/011.txt` | `data/old-translations/ksu-translations/es-navio/011.txt` |
| 12 | 55 | 89.5% | 15 chars | `data/ksu-translations-formatted/es-navio/012.txt` | `data/old-translations/ksu-translations/es-navio/012.txt` |
| 16 | 27 | 93.5% | 23 chars | `data/ksu-translations-formatted/es-navio/016.txt` | `data/old-translations/ksu-translations/es-navio/016.txt` |
| 17 | 98 | 85.1% | 32 chars | `data/ksu-translations-formatted/es-navio/017.txt` | `data/old-translations/ksu-translations/es-navio/017.txt` |
| 20 | 123 | 89.1% | 25 chars | `data/ksu-translations-formatted/es-navio/020.txt` | `data/old-translations/ksu-translations/es-navio/020.txt` |
| 24 | 35 | 89.0% | 13 chars | `data/ksu-translations-formatted/es-navio/024.txt` | `data/old-translations/ksu-translations/es-navio/024.txt` |
| 27 | 16 | 80.6% | 22 chars | `data/ksu-translations-formatted/es-navio/027.txt` | `data/old-translations/ksu-translations/es-navio/027.txt` |
| 27 | 44 | 82.2% | 2 chars | `data/ksu-translations-formatted/es-navio/027.txt` | `data/old-translations/ksu-translations/es-navio/027.txt` |

**Batch Fix Command for es-navio:**
```bash
# For example, to fix chapter 2 verse 144:
sed -n '144p' data/old-translations/ksu-translations/es-navio/002.txt
# Then manually update formatted file at line 144_00
```

---

### bs-korkut (Bosnian - 5 verses)

| Chapter | Verse | Similarity | Missing | Formatted Path | Original Path |
|---------|-------|------------|---------|----------------|---------------|
| 6 | 108 | 41.5% | 2 chars | `data/ksu-translations-formatted/bs-korkut/006.txt` | `data/old-translations/ksu-translations/bs-korkut/006.txt` |
| 12 | 6 | 81.4% | 3 chars | `data/ksu-translations-formatted/bs-korkut/012.txt` | `data/old-translations/ksu-translations/bs-korkut/012.txt` |
| 27 | 44 | 73.2% | 61 chars | `data/ksu-translations-formatted/bs-korkut/027.txt` | `data/old-translations/ksu-translations/bs-korkut/027.txt` |
| 38 | 71 | 94.8% | 5 chars | `data/ksu-translations-formatted/bs-korkut/038.txt` | `data/old-translations/ksu-translations/bs-korkut/038.txt` |
| 39 | 6 | 89.4% | 2 chars | `data/ksu-translations-formatted/bs-korkut/039.txt` | `data/old-translations/ksu-translations/bs-korkut/039.txt` |

---

### bn-bengali (Bengali - 2 verses)

| Chapter | Verse | Similarity | Missing | Formatted Path | Original Path |
|---------|-------|------------|---------|----------------|---------------|
| 7 | 27 | 91.4% | 1 char | `data/ksu-translations-formatted/bn-bengali/007.txt` | `data/old-translations/ksu-translations/bn-bengali/007.txt` |
| 42 | 48 | 79.6% | 0 chars* | `data/ksu-translations-formatted/bn-bengali/042.txt` | `data/old-translations/ksu-translations/bn-bengali/042.txt` |

*Note: Same length but different content - needs manual comparison

---

### de-bo (German - 2 verses)

| Chapter | Verse | Similarity | Missing | Formatted Path | Original Path |
|---------|-------|------------|---------|----------------|---------------|
| 7 | 164 | 56.6% | 1 char | `data/ksu-translations-formatted/de-bo/007.txt` | `data/old-translations/ksu-translations/de-bo/007.txt` |
| 65 | 2 | 71.4% | 1 char | `data/ksu-translations-formatted/de-bo/065.txt` | `data/old-translations/ksu-translations/de-bo/065.txt` |

---

### pt-elhayek (Portuguese - 3 verses)

| Chapter | Verse | Similarity | Missing | Formatted Path | Original Path |
|---------|-------|------------|---------|----------------|---------------|
| 2 | 61 | 94.4% | 11 chars | `data/ksu-translations-formatted/pt-elhayek/002.txt` | `data/old-translations/ksu-translations/pt-elhayek/002.txt` |
| 4 | 91 | 91.5% | 96 chars | `data/ksu-translations-formatted/pt-elhayek/004.txt` | `data/old-translations/ksu-translations/pt-elhayek/004.txt` |
| 12 | 23 | 94.5% | 19 chars | `data/ksu-translations-formatted/pt-elhayek/012.txt` | `data/old-translations/ksu-translations/pt-elhayek/012.txt` |

---

### ha-gumi (Hausa - 4 verses)

| Chapter | Verse | Similarity | Missing | Formatted Path | Original Path |
|---------|-------|------------|---------|----------------|---------------|
| 3 | 79 | 78.0% | 28 chars | `data/ksu-translations-formatted/ha-gumi/003.txt` | `data/old-translations/ksu-translations/ha-gumi/003.txt` |
| 27 | 40 | 77.0% | 237 chars | `data/ksu-translations-formatted/ha-gumi/027.txt` | `data/old-translations/ksu-translations/ha-gumi/027.txt` |
| 35 | 10 | 81.4% | 117 chars | `data/ksu-translations-formatted/ha-gumi/035.txt` | `data/old-translations/ksu-translations/ha-gumi/035.txt` |
| 3 | 164 | 86.9% | 76 chars | `data/ksu-translations-formatted/ha-gumi/003.txt` | `data/old-translations/ksu-translations/ha-gumi/003.txt` |

---

### th-thai (Thai - 3 verses)

| Chapter | Verse | Similarity | Missing | Formatted Path | Original Path |
|---------|-------|------------|---------|----------------|---------------|
| 2 | 49 | 93.3% | 36 chars | `data/ksu-translations-formatted/th-thai/002.txt` | `data/old-translations/ksu-translations/th-thai/002.txt` |
| 7 | 27 | 76.2% | 1 char | `data/ksu-translations-formatted/th-thai/007.txt` | `data/old-translations/ksu-translations/th-thai/007.txt` |
| 9 | 118 | 93.2% | 67 chars | `data/ksu-translations-formatted/th-thai/009.txt` | `data/old-translations/ksu-translations/th-thai/009.txt` |

---

### id-indonesian (Indonesian - 3 verses)

| Chapter | Verse | Similarity | Missing | Formatted Path | Original Path |
|---------|-------|------------|---------|----------------|---------------|
| 2 | 216 | 92.2% | 21 chars | `data/ksu-translations-formatted/id-indonesian/002.txt` | `data/old-translations/ksu-translations/id-indonesian/002.txt` |
| 3 | 47 | 89.0% | 9 chars | `data/ksu-translations-formatted/id-indonesian/003.txt` | `data/old-translations/ksu-translations/id-indonesian/003.txt` |
| 7 | 143 | 91.6% | 16 chars | `data/ksu-translations-formatted/id-indonesian/007.txt` | `data/old-translations/ksu-translations/id-indonesian/007.txt` |

---

### it-piccardo (Italian - 2 verses)

| Chapter | Verse | Similarity | Missing | Formatted Path | Original Path |
|---------|-------|------------|---------|----------------|---------------|
| 3 | 84 | 93.6% | 18 chars | `data/ksu-translations-formatted/it-piccardo/003.txt` | `data/old-translations/ksu-translations/it-piccardo/003.txt` |
| 20 | 123 | 90.3% | 25 chars | `data/ksu-translations-formatted/it-piccardo/020.txt` | `data/old-translations/ksu-translations/it-piccardo/020.txt` |

---

### Other languages (7 verses)

- **ml-abdulhameed:** ch2 v220 (81.8%, -113 chars)
- **sq-nahi:** ch2 v27 (88.0%, -47 chars)
- **nl-siregar:** ch7 v143 (86.9%, -57 chars)
- **sv-bernstrom:** ch5 v51 (90.1%, -16 chars)
- **ms-basmeih:** ch18 v19 (89.8%, -26 chars)
- **pr-tagi:** ch4 v36 (66.7%, -1 char)
- **ru-ku:** ch33 v35 (66.6%, -9 chars)

---

## Medium Priority Issues (11 verses)

These have minor content differences (95-98% similarity). Manual review needed to determine correct wording.

| Language | Ch | V | Similarity | Issue |
|----------|----|---|------------|-------|
| bn-bengali | 24 | 60 | 97.9% | Check wording |
| bs-korkut | 11 | 31 | 97.2% | Check wording |
| de-bo | 28 | 63 | 95.2% | Check wording |
| es-navio | 8 | 75 | 96.4% | Check wording |
| ha-gumi | 3 | 36 | 97.9% | Check wording |
| ml-abdulhameed | 4 | 173 | 97.6% | Check wording |
| pt-elhayek | 2 | 159 | 96.7% | Check wording |
| pt-elhayek | 3 | 179 | 97.8% | Check wording |
| pt-elhayek | 7 | 167 | 97.8% | Check wording |
| th-thai | 7 | 75 | 95.4% | Check wording |
| th-thai | 8 | 34 | 97.4% | Check wording |

---

## Low Priority Issues (111 verses)

**Status:** ✅ **Can Ignore**

These are spacing differences where formatted version has spaces after punctuation (intentional formatting improvements).

Example:
- Original: `word.Word`
- Formatted: `word. Word` ✅

**Languages affected:**
- zh-jian: 81 verses
- es-navio: 10 verses
- Other languages: scattered

**Action:** None needed - these are improvements, not errors

---

## Quick Reference Commands

### Check a specific verse:
```bash
# View original
sed -n '144p' data/old-translations/ksu-translations/es-navio/002.txt

# View formatted
grep "^144_" data/ksu-translations-formatted/es-navio/002.txt

# Check Arabic structure
grep "^144_" data/chs-ar-final/002
```

### Validate after fix:
```bash
python3 scripts/validation/compare_formatted_vs_original.py --language es-navio --chapter 2
```

### Batch process fixes:
```bash
# Create a fix script
for lang in es-navio bs-korkut bn-bengali; do
  echo "Processing $lang..."
  # Add your fix commands here
done
```

---

## Fix Progress Tracking

- [ ] es-navio: 20 verses
- [ ] bs-korkut: 5 verses
- [ ] bn-bengali: 2 verses
- [ ] de-bo: 2 verses
- [ ] pt-elhayek: 3 verses
- [ ] ha-gumi: 4 verses
- [ ] th-thai: 3 verses
- [ ] id-indonesian: 3 verses
- [ ] it-piccardo: 2 verses
- [ ] Other: 7 verses

**Total High Priority: 49 verses**

---

**Next Step:** Fix es-navio first (20 verses, most critical), then proceed to other languages.

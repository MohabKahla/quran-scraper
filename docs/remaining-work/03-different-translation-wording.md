# Different Translation Wording

## What Is This?

These verses have significantly different text between the original scraped version (`data/old-translations/ksu-translations/`) and the formatted version (`data/ksu-translations-formatted/`). Similarity is below 60%, meaning the AI reformatter likely pulled content from the wrong verse, merged verses incorrectly, or used a different edition.

Each case needs to be checked against the Arabic reference (`data/chs-ar-final/`) to determine which version is correct.

## How to Fix

1. Open both files side by side
2. Compare against the Arabic reference for the verse
3. Keep whichever translation is accurate, or re-translate if both are wrong
4. The formatted file's verse line format is `VVV_NN\ttext` in `data/ksu-translations-formatted/{lang}/{chapter}.txt`

---

## bn-bengali

| Chapter | Verse | Sim  | Issue |
|---------|-------|------|-------|
| 002     | 196   | 0.57 | Formatted has a different rendering of the Hajj verse — possible edition difference |
| 002     | 259   | 0.15 | Completely different content — formatted appears to be part of verse 260 (the donkey/food description) |
| 002     | 272   | 0.56 | Partial overlap — second half differs, possible verse boundary shift |
| 003     | 152   | 0.50 | Formatted has a different verse — possible off-by-one shift in verse numbering |

---

## de-bo

| Chapter | Verse | Sim  | Issue |
|---------|-------|------|-------|
| 009     | 112   | 0.24 | Formatted has only `und verkünde den Gläubigen frohe Botschaft.` — rest of the verse (the list of believers' qualities) is missing |
| 065     | 2     | 0.11 | Formatted starts mid-verse — the opening clause is missing, content begins from the middle |

---

## es-navio

| Chapter | Verse | Sim  | Issue |
|---------|-------|------|-------|
| 002     | 247   | 0.55 | Formatted has slightly different wording and a missing clause |
| 002     | 267   | 0.43 | Formatted has a different translation rendering — different edition likely |
| 004     | 64    | 0.51 | Formatted has the full verse but original is truncated — original may be missing its second half |
| 005     | 73    | 0.51 | Formatted has more content than original — check if original is truncated |

---

## ha-gumi

| Chapter | Verse | Sim  | Issue |
|---------|-------|------|-------|
| 007     | 157   | 0.56 | Minor wording difference — formatted omits opening `"` quote mark and has slightly different word order |

---

## it-piccardo

| Chapter | Verse | Sim  | Issue |
|---------|-------|------|-------|
| 065     | 6     | 0.45 | Formatted has the second half of the verse; original has only the first. Verse boundary may be split differently |

---

## ml-abdulhameed

| Chapter | Verse | Sim  | Issue |
|---------|-------|------|-------|
| 002     | 71    | 0.38 | Formatted has a different verse entirely (`അങ്ങനെ അവര്‍ അതിനെ അറുത്തു`) — likely verse 71b/72 boundary issue |
| 002     | 233   | 0.51 | Formatted is missing the second half of a long verse |
| 002     | 260   | 0.04 | **Critical:** Formatted contains Chinese characters mixed into Malayalam — source contamination. Content is completely wrong |
| 004     | 24    | 0.42 | Different verse section — possible off-by-one verse shift |

---

## ms-basmeih

| Chapter | Verse | Sim  | Issue |
|---------|-------|------|-------|
| 002     | 185   | 0.00 | **Critical:** Formatted contains the Arabic original text (`شَهۡرُ رَمَضَانَ...`) instead of the Malay translation — source contamination |

---

## pt-elhayek

| Chapter | Verse | Sim  | Issue |
|---------|-------|------|-------|
| 006     | 139   | 0.54 | Different rendering of second clause |
| 016     | 28    | 0.11 | **Critical:** Formatted contains Arabic text (`ٱلَّذِينَ تَتَوَفَّىٰهُمُ...`) instead of Portuguese — source contamination |
| 034     | 31    | 0.45 | Formatted has different second half of verse |

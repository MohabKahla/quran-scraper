# Char-Level Fixes Requiring Manual Review

## What Is This?

The automated `fix_char_changes.py` script could not resolve these entries because the changed text could not be located in any split part of the verse (the context was ambiguous or the diff spanned a part boundary). Each entry needs a targeted manual edit to the corresponding formatted file.

Files are in `data/ksu-translations-formatted/{language}/{chapter}.txt`.
Format per line: `VVV_NN\tverse text`

## How to Fix

For each entry:
1. Open the formatted file
2. Find the verse line(s) (`VVV_00`, `VVV_01`, etc.)
3. Apply the change shown — `[op]` means:
   - `[replace]` → swap `orig` text for `fmt` text in the formatted file
   - `[insert]` → the `fmt` text is extra in the formatted file, remove it
   - `[delete]` → the `orig` text is missing from the formatted file, add it back

---

## bs-korkut

| Chapter | Verse | Op | Orig | Fmt (current) |
|---------|-------|----|------|---------------|
| 002     | 101   | insert | *(nothing)* | ` kao da ne znaju.` — extra phrase appended |
| 003     | 49    | insert | *(nothing)* | `te ` — extra word inserted |
| 004     | 12    | insert | *(nothing)* | ` te` — extra word inserted |

---

## es-navio

| Chapter | Verse | Op | Notes |
|---------|-------|----|-------|
| 002     | 228   | insert | `p ` inserted in formatted |
| 002     | 253   | insert | `e qu` inserted in formatted |
| 006     | 60    | replace | Major reword (sim=0.740) — formatted has `Luego, es vuestro regreso; entonces, os informará de lo que...` but orig has `Y volveréis para que os haga saber lo que hacíais` |
| 040     | 56    | insert | `un ` inserted in formatted |
| 058     | 4     | replace | `es.` → ` es. ` (extra surrounding spaces) |

---

## ha-gumi

| Chapter | Verse | Op | Notes |
|---------|-------|----|-------|
| 059     | 23    | replace | Tamil character `ஸ` (`\u0b9b`) appears in Hausa text — likely source contamination. Orig: `astãwa` / Fmt: `ãstãwa,` |

---

## id-indonesian

| Chapter | Verse | Op | Notes |
|---------|-------|----|-------|
| 029     | 25    | replace | `; kemudian di hari kiam. ` in formatted vs ` kemudian di hari kiam` in orig — extra punctuation and trailing space |

---

## it-piccardo

| Chapter | Verse | Op | Notes |
|---------|-------|----|-------|
| 012     | 88    | insert | ` 88` inserted in formatted (verse number leaked into text) |
| 013     | 30    | insert | Full Italian sentence inserted: `Dì: Egli è il mio Signore, non c'è dio all'infuori di Lui...` — verify if this belongs here or if it's from the next verse |
| 031     | 29    | insert | Full Italian sentence inserted: `E che Allah è ben informato su ciò che fate.` — same check needed |

---

## ml-abdulhameed

| Chapter | Verse | Op | Notes |
|---------|-------|----|-------|
| 002     | 136   | replace | `എന്നിവര്‍ക്ക്` (orig) → `ഉള്‍പ്പെടെ` (fmt) — word substituted |
| 002     | 246   | replace | `പ്രമുഖര്‍` (orig) → `prominents` (fmt) — English word used instead of Malayalam |
| 003     | 64    | replace | `വഹിച്ചു` (orig) → `നൽകി` (fmt) — word substituted |
| 003     | 156   | replace | ` മരണ` (orig) → `死亡` (fmt) — **Chinese characters in Malayalam text** (source contamination) |

---

## pt-elhayek

| Chapter | Verse | Op | Notes |
|---------|-------|----|-------|
| 004     | 19    | insert | Full sentence inserted: `E se as detestardes, pode ser que Deus coloque nisto muito bem` — check if it belongs in this verse |
| 005     | 4     | replace | `es tivessem` → `as tiverem` — word form changed |
| 007     | 167   | replace | `é ao` → ` é ao ` (extra leading space) |
| 008     | 43    | replace | `nume` → `em número` — word split/expanded |
| 017     | 93    | replace | `apresentes` → ` apresente` (missing `s`, extra space) |
| 024     | 55    | insert | `; de` inserted in formatted |

---

## th-thai

| Chapter | Verse | Op | Notes |
|---------|-------|----|-------|
| 002     | 246   | replace | `ขากล่า` → ` ขากล่าว` — space inserted before word |

---

## Remaining Truncations (12 verses)

These verses still have content missing from the formatted version after `restore_missing_content.py` ran. The missing content could not be auto-restored (too dissimilar for the restoration heuristic).

| Language        | Chapter | Verse | Missing (~chars) |
|----------------|---------|-------|-----------------|
| `ha-gumi`      | 003     | 79    | ~28             |
| `ha-gumi`      | 027     | 19    | ~70             |
| `ha-gumi`      | 027     | 44    | ~130            |
| `ha-gumi`      | 029     | 38    | ~60             |
| `bs-korkut`    | 003     | 185   | ~61             |
| `bs-korkut`    | 004     | 36    | ~285            |
| `id-indonesian`| 017     | 59    | ~63             |
| `id-indonesian`| 017     | 110   | ~52             |
| `ml-abdulhameed`| 002    | 233   | ~582            |
| `ml-abdulhameed`| 004    | 91    | ~162            |
| `de-bo`        | 005     | 60    | ~26             |
| `th-thai`      | 002     | 49    | ~35             |

To fix: open the original file (`data/old-translations/ksu-translations/{lang}/{chapter}.txt`), find the verse, and append the missing tail text to the last split part (`VVV_NN`) of the formatted file.

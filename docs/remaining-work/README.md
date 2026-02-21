# Remaining Translation Fix Work

This directory documents the outstanding issues after the automated fix passes completed on 2026-02-21.

**Already done (automated):**
- `restore_missing_content.py --all` — restored 358 truncated verses across 20 languages
- `fix_char_changes.py` — fixed 143 char-level differences, 6 partial fixes

---

## Sections

### [01 — Split-Boundary Word Breaks](./01-split-boundary-fixes.md)
Mid-word splits where the alignment script cut a verse inside a word. Joining parts adds a spurious space.

| Language  | Issues |
|-----------|--------|
| `th-thai` | ~275   |

**Fix:** `python3 scripts/validation/check_translation_splits.py --provider openai --languages th-thai`

---

### [02 — Char Fixes Requiring Manual Edit](./02-char-fixes-manual.md)
Entries where the automated script could not locate the diff target in any verse part. Includes wrong words, inserted phrases, verse number leaks, and 12 remaining truncations.

| Language         | Entries |
|-----------------|---------|
| `pt-elhayek`    | 6       |
| `it-piccardo`   | 3       |
| `bs-korkut`     | 3       |
| `es-navio`      | 5       |
| `ml-abdulhameed`| 4       |
| `ha-gumi`       | 1       |
| `id-indonesian` | 1       |
| `th-thai`       | 1       |

Plus **12 remaining truncations** across: `ha-gumi`, `bs-korkut`, `id-indonesian`, `ml-abdulhameed`, `de-bo`, `th-thai`.

---

### [03 — Different Translation Wording](./03-different-translation-wording.md)
Verses where the formatted and original versions have significantly different wording (similarity < 60%). Requires comparison against the Arabic reference to determine which is correct.

| Language         | Verses |
|-----------------|--------|
| `ml-abdulhameed`| 4      |
| `bn-bengali`    | 4      |
| `es-navio`      | 4      |
| `pt-elhayek`    | 3      |
| `de-bo`         | 2      |
| `it-piccardo`   | 1      |
| `ha-gumi`       | 1      |
| `ms-basmeih`    | 1      |

**Total: 20 verses**

---

### [04 — Repetition & Source Contamination](./04-repetition-and-contamination.md)
Duplicated sentences in formatted files and critical contamination (Arabic or Chinese text appearing in non-Arabic translations).

| Issue                             | Language         | Location          |
|-----------------------------------|-----------------|-------------------|
| Duplicated sentence               | `de-bo`          | ch003 v21         |
| Arabic text instead of Malay      | `ms-basmeih`     | ch002 v185        |
| Arabic text instead of Portuguese | `pt-elhayek`     | ch016 v28         |
| Chinese text in Malayalam         | `ml-abdulhameed` | ch002 v260, ch003 v156 |
| Tamil char in Hausa               | `ha-gumi`        | ch059 v23         |

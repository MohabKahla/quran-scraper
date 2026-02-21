# Repetition Issues & Source Contamination

---

## Repetition in Formatted File (1 case)

### de-bo — Chapter 003, Verse 21

The formatted file has a sentence duplicated mid-verse. The original has it once.

**File:** `data/ksu-translations-formatted/de-bo/003.txt`

**Current formatted text (combined parts):**
> Diejenigen, die Allahs Zeichen verleugnen, die Propheten zu Unrecht töten und diejenigen unter den Menschen töten, die Gerechtigkeit befehlen, **und diejenigen unter den Menschen töten, die Gerechtigkeit befehlen**, so verkünde ihnen eine schmerzhafte Strafe.

**Should be (original):**
> Diejenigen, die Allahs Zeichen verleugnen, die Propheten zu Unrecht töten und diejenigen unter den Menschen töten, die Gerechtigkeit befehlen, denen verkünde eine schmerzhafte Strafe.

**Fix:** Find the `021_NN` lines in `003.txt`, locate the duplicated phrase `und diejenigen unter den Menschen töten, die Gerechtigkeit befehlen,` and remove the second occurrence.

---

## Source Contamination (Critical)

These are cases where the formatted file contains text from the wrong source — either Arabic original text or characters from a completely different language script. These must be fixed by replacing the contaminated text with the correct translation.

Reference the original scraped file or re-translate from the Arabic reference (`data/chs-ar-final/`).

### ms-basmeih — Chapter 002, Verse 185

**File:** `data/ksu-translations-formatted/ms-basmeih/002.txt`

The formatted verse contains the Arabic Quran text instead of the Malay translation:

| | Text |
|---|---|
| **Should be (Malay):** | `(Masa yang diwajibkan kamu berpuasa itu ialah) bulan Ramadan yang padanya diturunkan Al-Quran...` |
| **Currently (Arabic):** | `شَهۡرُ رَمَضَانَ ٱلَّذِيٓ أُنزِلَ فِيهِ ٱلۡقُرۡءَانُ...` |

---

### pt-elhayek — Chapter 016, Verse 28

**File:** `data/ksu-translations-formatted/pt-elhayek/016.txt`

The formatted verse contains Arabic text instead of Portuguese:

| | Text |
|---|---|
| **Should be (Portuguese):** | `De cujas almas os anjos se apossam, em estado de iniqüidade. Naquela hora submeter-se-ão e dirão: Nunca fizemos mal algum...` |
| **Currently (Arabic):** | `ٱلَّذِينَ تَتَوَفَّىٰهُمُ ٱلۡمَلَٰٓئِكَةُ ظَالِمِيٓ أَنفُسِهِمۡۖ...` |

---

### ml-abdulhameed — Chapter 002, Verse 260 & Chapter 003, Verse 156

**File:** `data/ksu-translations-formatted/ml-abdulhameed/002.txt` and `003.txt`

- **002 v260:** Formatted contains Chinese characters (`死亡者们你如何复活他们？...`) mixed into a Malayalam verse — the entire content is Chinese.
- **003 v156:** Formatted contains `死亡` (Chinese for "death") within a Malayalam sentence.

| | Text |
|---|---|
| **ml-abdulhameed 002 v260 (should be Malayalam):** | `എന്റെനാഥാ! മരണപ്പെട്ടവരെ നീ എങ്ങനെ ജീവിപ്പിക്കുന്നുവെന്ന് എനിക്ക് കാണിച്ചുതരേണമേ...` |
| **ml-abdulhameed 003 v156 (fix):** | Replace `死亡` with ` മരണ` |

---

### ha-gumi — Chapter 059, Verse 23

**File:** `data/ksu-translations-formatted/ha-gumi/059.txt`

A Tamil character `ஸ` (`U+0B9B`) appears inside a Hausa word:

| | Text |
|---|---|
| **Orig:** | `...astãwa` |
| **Fmt:** | `...ஸastãwa,` |

Fix: remove the Tamil character prefix from the word.

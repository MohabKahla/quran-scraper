# Split-Boundary Word Breaks

## What Is This?

During AI alignment, some verses were split into multiple parts at incorrect positions — cutting through a word instead of at a word boundary. When the comparison tool joins the parts back with a space, it creates an artificial gap inside a word.

**Example (`th-thai` ch002 v19):**
```
Part 019_00: "...เอานิ้วมือของพวก"   ← cut mid-word
Part 019_01: "เขาอุดหูไว้..."
Joined:      "...เอานิ้วมือของพวก เขาอุดหูไว้..."  ← "พวก เขา" should be "พวกเขา"
```

## Fix

Use `check_translation_splits.py` with OpenAI to detect and correct the split boundaries:

```bash
python3 scripts/validation/check_translation_splits.py --provider openai --languages th-thai
```

## Affected Languages

| Language     | Approx. Issues | Notes                                              |
|-------------|---------------|----------------------------------------------------|
| `th-thai`   | ~275          | Most are mid-word cuts in Thai (no natural spaces) |

> **Note:** Other languages (es-navio, zh-jian, ur-gl, sv-bernstrom, sw-barwani, tr-diyanet) show ~661/980/172/62/8/30 mismatches respectively in the comparison tool, but these are **intentional formatting improvements** (spaces added after sentence-ending punctuation, capitalisation fixes) — not split-boundary bugs. Do not attempt to revert those.

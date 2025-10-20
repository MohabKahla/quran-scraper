import fs from "node:fs/promises";
import path from "node:path";
import fetch from "node-fetch";

const OUT_ROOT = "ksu-translations";
const RETRY_TARGETS = [
  {
    id: "sv_bernstrom",
    label: "Swedish - Bernström",
    langCode: "sv",
    surahs: [16, 40]
  },
  {
    id: "th_thai",
    label: "Thai - King Fahad Complex",
    langCode: "th",
    surahs: [17, 36]
  }
];

// Verse counts for each surah (1-114)
const VERSE_COUNTS = [
  7, 286, 200, 176, 120, 165, 206, 75, 129, 109,
  123, 111, 43, 52, 99, 128, 111, 110, 98, 135,
  112, 78, 118, 64, 77, 227, 93, 88, 69, 60,
  34, 30, 73, 54, 45, 83, 182, 88, 75, 85,
  54, 53, 89, 59, 37, 35, 38, 29, 18, 45,
  60, 49, 62, 55, 78, 96, 29, 22, 24, 13,
  14, 11, 11, 18, 12, 12, 30, 52, 52, 44,
  28, 28, 20, 56, 40, 31, 50, 40, 46, 42,
  29, 19, 36, 25, 22, 17, 19, 26, 30, 20,
  15, 21, 11, 8, 8, 19, 5, 8, 8, 11,
  11, 8, 3, 9, 5, 4, 7, 3, 6, 3,
  5, 4, 5, 6
];

const MIN_DELAY_MS = 1500;
const BASE_URL = "https://quran.ksu.edu.sa/interface.php";

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

function buildTranslationMeta(entry) {
  return {
    ...entry,
    slug: entry.id.replace(/_/g, "-"),
    header: entry.header || `Quran Translation - ${entry.label}`,
    surahLabel: entry.surahLabel || "Surah"
  };
}

async function fetchTranslationData(translation, surahNo) {
  const verseCount = VERSE_COUNTS[surahNo - 1];
  const url = new URL(BASE_URL);
  const params = new URLSearchParams({
    ui: "pc",
    do: "tarjama",
    tafsir: translation.id,
    b_sura: surahNo.toString(),
    b_aya: "1",
    e_sura: surahNo < 114 ? (surahNo + 1).toString() : surahNo.toString(),
    e_aya: surahNo < 114 ? "1" : verseCount.toString()
  });
  url.search = params.toString();

  const response = await fetch(url.toString(), {
    headers: {
      Accept: "application/json, text/javascript, */*; q=0.01",
      "Accept-Language": "en-US,en;q=0.9",
      Connection: "keep-alive",
      DNT: "1",
      Referer: `https://quran.ksu.edu.sa/index.php?l=${translation.langCode}`,
      "Sec-Fetch-Dest": "empty",
      "Sec-Fetch-Mode": "cors",
      "Sec-Fetch-Site": "same-origin",
      "User-Agent":
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
      "X-Requested-With": "XMLHttpRequest"
    }
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`HTTP ${response.status} - ${response.statusText}\n${errorText}`);
  }

  const raw = await response.text();
  try {
    return JSON.parse(raw);
  } catch (err) {
    const sanitized = raw.replace(/[\u0000-\u001F]+/g, " ");
    return JSON.parse(sanitized);
  }
}

function extractVerses(translationData, surahNo) {
  const tafsirData = translationData.tafsir || translationData;
  const verseCount = VERSE_COUNTS[surahNo - 1];
  const verses = [];

  for (let i = 1; i <= verseCount; i++) {
    const key = `${surahNo}_${i}`;
    const text = tafsirData[key]?.text?.trim() ?? "";
    verses.push(text);
  }

  return verses;
}

async function writeSurahFiles(translation, surahNo, verses) {
  const outDir = path.join(OUT_ROOT, translation.slug);
  await fs.mkdir(outDir, { recursive: true });

  const fileName = `${String(surahNo).padStart(3, "0")}.txt`;
  const filePath = path.join(outDir, fileName);

  const formatted = verses.map((v, idx) => `${idx + 1}. ${v.replace(/\s+/g, " ").trim()}`);
  await fs.writeFile(filePath, formatted.join("\n"), "utf8");
}

async function rebuildCombinedFile(translation) {
  const outDir = path.join(OUT_ROOT, translation.slug);
  const combinedPath = path.join(outDir, `quran-${translation.id}.txt`);

  const entries = await fs.readdir(outDir);
  const chapterFiles = entries
    .filter((name) => /^\d{3}\.txt$/.test(name))
    .sort();

  let combinedContent = `${translation.header}\n\n`;
  let first = true;

  for (const name of chapterFiles) {
    const surahNo = parseInt(name, 10);
    const filePath = path.join(outDir, name);
    const content = await fs.readFile(filePath, "utf8");
    combinedContent += `${first ? "" : "\n\n"}${translation.surahLabel} ${surahNo}\n\n${content}`;
    first = false;
  }

  await fs.writeFile(combinedPath, combinedContent, "utf8");
}

async function processTranslation(entry) {
  const translation = buildTranslationMeta(entry);
  console.log(`\n=== Retrying ${translation.label} (${translation.id}) ===`);

  for (const surahNo of translation.surahs) {
    console.log(`  -> Surah ${surahNo}`);
    const start = Date.now();
    try {
      const data = await fetchTranslationData(translation, surahNo);
      const verses = extractVerses(data, surahNo);
      await writeSurahFiles(translation, surahNo, verses);
      console.log(`     ✓ Updated surah ${surahNo} (${verses.length} verses)`);
    } catch (error) {
      console.error(`     ✗ Failed surah ${surahNo}: ${error.message}`);
    }
    const elapsed = Date.now() - start;
    if (elapsed < MIN_DELAY_MS) {
      await sleep(MIN_DELAY_MS - elapsed);
    }
  }

  await rebuildCombinedFile(translation);
  console.log(`Finished ${translation.label}`);
}

async function main() {
  for (const entry of RETRY_TARGETS) {
    await processTranslation(entry);
  }
  console.log("\nRetry processing complete.");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});

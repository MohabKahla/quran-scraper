import fs from "node:fs/promises";
import path from "node:path";
import fetch from "node-fetch";

const OUT_ROOT = process.env.OUT_ROOT || "ksu-translations";
const BASE_URL = "https://quran.ksu.edu.sa/interface.php";

const TRANSLATIONS = [
  { id: "es_navio", label: "Spanish" },
  { id: "de_bo", label: "German" },
  { id: "it_piccardo", label: "Italian" },
  { id: "pt_elhayek", label: "Portuguese" },
  { id: "nl_siregar", label: "Dutch" },
  { id: "bs_korkut", label: "Bosnian" },
  { id: "sq_nahi", label: "Albanian" },
  { id: "sv_bernstrom", label: "Swedish" },
  { id: "tr_diyanet", label: "Turkish" },
  { id: "ru_ku", label: "Russian" },
  { id: "id_indonesian", label: "Indonesian" },
  { id: "ms_basmeih", label: "Malay" },
  { id: "ku_asan", label: "Kurdish" },
  { id: "pr_tagi", label: "Persian" },
  { id: "ur_gl", label: "Urdu" },
  { id: "ml_abdulhameed", label: "Malayalam" },
  { id: "bn_bengali", label: "Bengali" },
  { id: "ta_tamil", label: "Tamil" },
  { id: "th_thai", label: "Thai" },
  { id: "ha_gumi", label: "Hausa" },
  { id: "sw_barwani", label: "Swahili" },
  { id: "uz_sodik", label: "Uzbek" },
  { id: "zh_jian", label: "Chinese" }
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

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

const translationMap = new Map(
  TRANSLATIONS.map((t) => {
    const langCode = t.langCode || t.id.split("_")[0];
    return [
      t.id,
      {
        ...t,
        langCode,
        slug: t.slug || t.id.replace(/_/g, "-"),
        header: t.header || `Quran Translation - ${t.label}`,
        surahLabel: t.surahLabel || "Surah"
      }
    ];
  })
);

function printUsage() {
  console.log("Usage: node scrape_ksu_translations.mjs [options] [translation_id ...]");
  console.log("");
  console.log("Options:");
  console.log("  --list       Show available translation ids and exit");
  console.log("");
  console.log("Examples:");
  console.log("  node scrape_ksu_translations.mjs fr_ha en_sh");
  console.log("  node scrape_ksu_translations.mjs  # scrape all translations");
}

function listTranslations() {
  console.log("Available translations:");
  for (const { id, label } of TRANSLATIONS) {
    console.log(`  ${id.padEnd(15)} ${label}`);
  }
}

async function fetchSurahTranslation(translation, surahNo) {
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
      "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
      "X-Requested-With": "XMLHttpRequest"
    }
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`HTTP ${response.status} - ${response.statusText}\n${errorText}`);
  }

  const data = await response.json();
  const tafsirData = data.tafsir || data;
  const verses = [];

  for (let i = 1; i <= verseCount; i++) {
    const key = `${surahNo}_${i}`;
    const verse = tafsirData[key]?.text?.trim() ?? "";
    if (!verse) {
      console.warn(`Warning: missing verse ${key} for ${translation.id}`);
    }
    verses.push(verse);
  }

  return verses;
}

async function scrapeSurah(translation, surahNo) {
  try {
    const verses = await fetchSurahTranslation(translation, surahNo);
    if (verses.length === 0) {
      throw new Error("No verses found");
    }
    console.log(`  ✓ Surah ${surahNo} (${verses.length} verses)`);
    return verses;
  } catch (error) {
    console.error(`  ✗ Failed surah ${surahNo}: ${error.message}`);
    throw error;
  }
}

async function scrapeTranslation(translation) {
  console.log(`\n=== ${translation.label} (${translation.id}) ===`);
  const outDir = path.join(OUT_ROOT, translation.slug);
  await fs.mkdir(outDir, { recursive: true });

  const combinedPath = path.join(outDir, `quran-${translation.id}.txt`);
  await fs.writeFile(`${combinedPath}.tmp`, `${translation.header}\n\n`, "utf8");

  for (let i = 1; i <= 114; i++) {
    const start = Date.now();
    try {
      const verses = await scrapeSurah(translation, i);
      const fileName = `${String(i).padStart(3, "0")}.txt`;
      const filePath = path.join(outDir, fileName);

      const formattedVerses = verses.map((verse, idx) => `${idx + 1}. ${verse.replace(/\s+/g, " ").trim()}`);
      const content = formattedVerses.join("\n");

      await fs.writeFile(filePath, content, "utf8");

      const block = `${i > 1 ? "\n\n" : ""}${translation.surahLabel} ${i}\n\n${content}`;
      await fs.appendFile(`${combinedPath}.tmp`, block, "utf8");
    } catch (err) {
      console.error(`Skipping surah ${i} for ${translation.id}`);
    }

    const elapsed = Date.now() - start;
    const minDelay = 1500;
    if (elapsed < minDelay) {
      await sleep(minDelay - elapsed);
    }
  }

  await fs.rename(`${combinedPath}.tmp`, combinedPath);
  console.log(`Finished ${translation.label}. Files in ${outDir}`);
}

async function main() {
  const args = process.argv.slice(2);

  if (args.includes("--list")) {
    listTranslations();
    return;
  }

  const requested = args.filter((arg) => !arg.startsWith("-"));
  const targets = requested.length > 0 ? requested : [...translationMap.keys()];

  const translations = targets.map((id) => {
    const translation = translationMap.get(id);
    if (!translation) {
      throw new Error(`Unknown translation id: ${id}`);
    }
    return translation;
  });

  await fs.mkdir(OUT_ROOT, { recursive: true });

  for (const translation of translations) {
    try {
      await scrapeTranslation(translation);
    } catch (error) {
      console.error(`Failed ${translation.id}: ${error.message}`);
    }
  }

  console.log("\nAll requested translations processed.");
}

main().catch((error) => {
  console.error(error);
  printUsage();
  process.exit(1);
});

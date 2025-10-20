import fs from "node:fs/promises";
import path from "node:path";
import fetch from "node-fetch";

const OUT_DIR = "french";
const BASE_URL = "https://quran.ksu.edu.sa/interface.php";
const TRANSLATION_ID = "fr_ha"; // French translation ID

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

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function fetchSurahTranslation(surahNo) {
  const verseCount = VERSE_COUNTS[surahNo - 1];
  
  // Build the API URL
  // To get all verses of a surah, we need to request from current surah verse 1 
  // to next surah verse 1 (or for surah 114, just use a high verse number)
  const url = new URL(BASE_URL);
  const params = new URLSearchParams({
    ui: 'pc',
    do: 'tarjama',
    tafsir: TRANSLATION_ID,
    b_sura: surahNo.toString(),
    b_aya: '1',
    e_sura: surahNo < 114 ? (surahNo + 1).toString() : surahNo.toString(),
    e_aya: surahNo < 114 ? '1' : verseCount.toString()
  });
  
  url.search = params.toString();
  
  try {
    console.log(`Fetching surah ${surahNo} (${verseCount} verses)...`);
    
    const response = await fetch(url.toString(), {
      headers: {
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'en-US,en;q=0.9',
        'Connection': 'keep-alive',
        'DNT': '1',
        'Referer': 'https://quran.ksu.edu.sa/index.php?l=fr',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
        'X-Requested-With': 'XMLHttpRequest'
      }
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`HTTP ${response.status} - ${response.statusText}\n${errorText}`);
    }
    
    const data = await response.json();
    
    // Extract verses in order - they're nested under 'tafsir' key
    const tafsirData = data.tafsir || data;
    const verses = [];
    for (let i = 1; i <= verseCount; i++) {
      const key = `${surahNo}_${i}`;
      if (tafsirData[key] && tafsirData[key].text) {
        verses.push(tafsirData[key].text.trim());
      } else {
        console.warn(`Warning: Missing verse ${key}`);
        verses.push(''); // Add empty string to maintain verse numbering
      }
    }
    
    return verses;
    
  } catch (error) {
    console.error(`Error fetching surah ${surahNo}:`, error.message);
    throw error;
  }
}

async function scrapeSurah(i) {
  try {
    const verses = await fetchSurahTranslation(i);
    if (verses.length === 0) {
      throw new Error('No verses found');
    }
    console.log(`Found ${verses.length} verses for surah ${i}`);
    return { chapter: i.toString(), verses };
  } catch (error) {
    console.error(`Error processing surah ${i}:`, error.message);
    throw error;
  }
}

async function main() {
  await fs.mkdir(OUT_DIR, { recursive: true });
  const combinedPath = path.join(OUT_DIR, "quran-french.txt");
  await fs.writeFile(combinedPath, "Le Saint Coran - Traduction Française\n\n", "utf8");

  // Process surahs in order
  for (let i = 1; i <= 114; i++) {
    const startTime = Date.now();
    
    try {
      const { chapter, verses } = await scrapeSurah(i);
      const fileName = `${String(i).padStart(3, "0")}.txt`;
      const filePath = path.join(OUT_DIR, fileName);

      // Format verses with numbers
      const formattedVerses = verses.map((v, idx) => 
        `${idx + 1}. ${v.replace(/\s+/g, ' ').trim()}`
      );
      
      const content = formattedVerses.join('\n');
      
      // Write individual surah file
      await fs.writeFile(filePath, content, "utf8");

      // Append to the combined file with a blank line between surahs
      await fs.appendFile(
        combinedPath,
        (i > 1 ? "\n\n" : "") + `Sourate ${i}\n\n${content}`,
        "utf8"
      );

      console.log(`✓ [${i}/114] Processed surah ${i} (${verses.length} verses)`);
    } catch (err) {
      console.error(`✗ [${i}/114] Failed to process surah ${i}:`, err.message);
      // Continue with next surah instead of stopping
    }

    // Be nice to the server - ensure at least 1.5 seconds between requests
    const elapsed = Date.now() - startTime;
    const minDelay = 1500;
    if (elapsed < minDelay) {
      await sleep(minDelay - elapsed);
    }
  }

  console.log(`Done. Files written to ${OUT_DIR}/`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});

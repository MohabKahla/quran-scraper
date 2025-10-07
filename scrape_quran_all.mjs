import fs from "node:fs/promises";
import path from "node:path";
import fetch from "node-fetch";
import * as cheerio from "cheerio";

const OUT_DIR = "out";
const BASE_URL = "https://api.quran.com/api/v4/verses/by_chapter";
const TRANSLATION_ID = "153"; // Italian translation ID
const PER_PAGE = 300; // Should be enough for the longest surah

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const slugify = (s) =>
  s.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");

async function fetchHtml(url) {
  const res = await fetch(url, {
    headers: {
      "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " +
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
      Accept: "text/html,application/xhtml+xml",
      "Accept-Language": "en",
    },
  });
  if (!res.ok) throw new Error(`HTTP ${res.status} for ${url}`);
  return await res.text();
}

// We'll just use the surah number as the name
function getSurahName(surahNo) {
  return surahNo.toString();
}

async function fetchVerses(surahNo) {
  const url = new URL(BASE_URL);
  url.pathname += `/${surahNo}`;
  
  const params = new URLSearchParams({
    translations: TRANSLATION_ID,
    per_page: PER_PAGE,
    fields: 'text_uthmani',
    translation_fields: 'resource_name,language_id',
    word_translation_language: 'it',
    mushaf: '2',
    words: 'true'
  });
  
  url.search = params.toString();
  
  try {
    console.log(`Fetching surah ${surahNo}...`);
    
    // Use the public API endpoint with proper headers
    const response = await fetch(`https://api.quran.com/api/v4/verses/by_chapter/${surahNo}?translations=${TRANSLATION_ID}&language=it&words=true&word_fields=text_uthmani,text_indopak,code_v1,code_v2,page_number,line_number&word_translation_language=it&page=1&per_page=${PER_PAGE}`, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://quran.com/',
        'Origin': 'https://quran.com'
      }
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`HTTP ${response.status} - ${response.statusText}\n${errorText}`);
    }
    
    const data = await response.json();
    
    if (!data.verses || !Array.isArray(data.verses)) {
      throw new Error('Invalid response format');
    }
    
    // Extract and clean the Italian translations
    if (!data.verses || !Array.isArray(data.verses)) {
      throw new Error('Invalid response format: missing verses array');
    }

    const verses = [];
    for (const verse of data.verses) {
      if (verse.translations && verse.translations.length > 0) {
        // Clean up the translation text
        let translation = verse.translations[0].text
          .replace(/<\/?[a-z][^>]*(>|$)/gi, '') // Remove all HTML tags
          .replace(/\s*\[\d*\]\s*/g, '') // Remove footnote markers like [1], [2], etc.
          .replace(/\s*\([^)]*\)/g, '') // Remove text in parentheses
          .replace(/\s*\{[^}]*\}/g, '') // Remove text in curly braces
          .replace(/\s*\[[^\]]*\]/g, '') // Remove text in square brackets
          .replace(/[\u00A0\u1680\u180E\u2000-\u200F\u2028-\u202F\u205F\u3000\uFEFF]/g, ' ') // Remove various space characters
          .replace(/\s*\d+\s*/g, ' ') // Remove standalone numbers
          .replace(/\s*,\s*,/g, ',') // Fix double commas
          .replace(/\s+\./g, '.') // Fix spaces before periods
          .replace(/\.\.+/g, '.') // Fix multiple periods
          .replace(/\(\s*\)/g, '') // Remove empty parentheses
          .replace(/\s*\(/g, ' (') // Add space before opening parenthesis if missing
          .replace(/\)\./g, ')') // Remove period after closing parenthesis
          .replace(/\.\)/g, ')') // Fix period before closing parenthesis
          .replace(/\s*\//g, '') // Remove forward slashes
          .replace(/[\u2018\u2019]/g, "'") // Replace smart quotes with straight quotes
          .replace(/[\u201C\u201D]/g, '"')
          .replace(/\s{2,}/g, ' ') // Replace multiple spaces with single space
          .replace(/^\s*[\s\n]+|\s*[\s\n]+$/g, '') // Trim whitespace and newlines
          .replace(/^\s*[\.,;:!?]+/g, '') // Remove leading punctuation
          .replace(/[\.,;:!?]+\s*$/g, '.') // Ensure sentence ends with a single period
          .replace(/([.,;:!?])\1+/g, '$1') // Remove duplicate punctuation
          .replace(/([.,;:!?])\s*([.,;:!?])/g, '$1') // Remove adjacent punctuation
          .trim();
          
        if (translation) {
          verses.push(translation);
        }
      }
    }
    
    return verses;
    
  } catch (error) {
    console.error(`Error fetching surah ${surahNo}:`, error.message);
    return [];
  }
}

async function scrapeSurah(i) {
  try {
    const verses = await fetchVerses(i);
    if (verses.length === 0) {
      throw new Error('No verses found');
    }
    console.log(`Found ${verses.length} verses for surah ${i}`);
    return { chapter: i.toString(), verses };
  } catch (error) {
    console.error(`Error processing surah ${i}:`, error.message);
    return { chapter: i.toString(), verses: [] };
  }
}

async function main() {
  await fs.mkdir(OUT_DIR, { recursive: true });
  const combinedPath = path.join(OUT_DIR, "quran-italian.txt");
  await fs.writeFile(combinedPath, "Il Sacro Corano - Traduzione Italiana\n\n", "utf8");

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
        (i > 1 ? "\n\n" : "") + `Surah ${i}\n\n${content}`,
        "utf8"
      );

      console.log(`✓ [${i}/114] Processed surah ${i} (${verses.length} verses)`);
    } catch (err) {
      console.error(`✗ [${i}/114] Failed to process surah ${i}:`, err.message);
    }

    // Be nice to the server - ensure at least 1 second between requests
    const elapsed = Date.now() - startTime;
    if (elapsed < 1000) {
      await sleep(1000 - elapsed);
    }
  }

  console.log(`Done. Files written to ${OUT_DIR}/`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});


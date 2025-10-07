# Quran Scraper

A Node.js script to download and format Quran translations from the Quran.com API. This tool fetches the Italian translation by Hamza Roberto Piccardo and saves it in a clean, readable format.

## Features

- Downloads all 114 surahs of the Quran
- Cleans and formats the text for better readability
- Saves each surah in a separate file
- Creates a combined file with all surahs
- Docker support for easy deployment

## Prerequisites

- Node.js 18 or higher
- npm or yarn
- Docker (optional)

## Installation

### Without Docker

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/quran-scraper.git
   cd quran-scraper
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

### With Docker

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/quran-scraper.git
   cd quran-scraper
   ```

## Usage

### Without Docker

```bash
# Run the scraper
node scrape_quran_all.mjs
```

The output will be saved in the `out/` directory.

### With Docker

```bash
# Build and run the container
docker-compose up --build
```

Or to run in detached mode:

```bash
docker-compose up -d --build
```

The output will be available in the `out/` directory on your host machine.

## Output

- Individual surah files: `out/001.txt` to `out/114.txt`
- Combined file: `out/quran-italian.txt`

## Updating the Translation

To update the translation or change to a different language:

1. Open `scrape_quran_all.mjs`
2. Find the `TRANSLATION_ID` constant (line 8)
3. Update it with the desired translation ID:
   - `153`: Italian (Hamza Roberto Piccardo)
   - `20`: English (Saheeh International)
   - `31`: French (Muhammad Hamidullah)
   - `84`: Spanish (Muhammad Isa García)
   - (Find more IDs in the Quran.com API documentation)

## Customization

You can modify the following constants in `scrape_quran_all.mjs`:

- `OUT_DIR`: Output directory (default: 'out')
- `PER_PAGE`: Number of verses per request (default: 300)
- Text cleaning rules in the `fetchVerses` function

## Rate Limiting

The script includes a delay between requests to respect the server's rate limits. You can adjust the delay in the `main` function if needed.

## License

This project is open source and available under the [MIT License](LICENSE).

## Acknowledgments

- [Quran.com](https://quran.com) for providing the API
- Hamza Roberto Piccardo for the Italian translation

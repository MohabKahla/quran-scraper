import os
from pathlib import Path

def get_surah_name(surah_num):
    """Get surah name from surah number"""
    surah_names = {
        1: "Al-Fatiha", 2: "Al-Baqara", 3: "Al-Imran", 4: "An-Nisa",
        5: "Al-Ma'ida", 6: "Al-An'am", 7: "Al-A'raf", 8: "Al-Anfal",
        9: "At-Tawba", 10: "Yunus", 11: "Hud", 12: "Yusuf",
        13: "Ar-Ra'd", 14: "Ibrahim", 15: "Al-Hijr", 16: "An-Nahl",
        17: "Al-Isra", 18: "Al-Kahf", 19: "Maryam", 20: "Ta-Ha",
        21: "Al-Anbiya", 22: "Al-Hajj", 23: "Al-Mu'minun", 24: "An-Nur",
        25: "Al-Furqan", 26: "Ash-Shu'ara", 27: "An-Naml", 28: "Al-Qasas",
        29: "Al-Ankabut", 30: "Ar-Rum", 31: "Luqman", 32: "As-Sajda",
        33: "Al-Ahzab", 34: "Saba'", 35: "Fatir", 36: "Ya-Sin",
        37: "As-Saffat", 38: "Sad", 39: "Az-Zumar", 40: "Ghafir",
        41: "Fussilat", 42: "Ash-Shura", 43: "Az-Zukhruf", 44: "Ad-Dukhan",
        45: "Al-Jathiya", 46: "Al-Ahqaf", 47: "Muhammad", 48: "Al-Fath",
        49: "Al-Hujurat", 50: "Qaf", 51: "Adh-Dhariyat", 52: "At-Tur",
        53: "An-Najm", 54: "Al-Qamar", 55: "Ar-Rahman", 56: "Al-Waqi'a",
        57: "Al-Hadid", 58: "Al-Mujadila", 59: "Al-Hashr", 60: "Al-Mumtahana",
        61: "As-Saff", 62: "Al-Jumu'a", 63: "Al-Munafiqun", 64: "At-Taghabun",
        65: "At-Talaq", 66: "At-Tahrim", 67: "Al-Mulk", 68: "Al-Qalam",
        69: "Al-Haqqa", 70: "Al-Ma'arij", 71: "Nuh", 72: "Al-Jinn",
        73: "Al-Muzzammil", 74: "Al-Muddaththir", 75: "Al-Qiyamah", 76: "Al-Insan",
        77: "Al-Mursalat", 78: "An-Naba", 79: "An-Nazi'at", 80: "Abasa",
        81: "At-Takwir", 82: "Al-Infitar", 83: "Al-Mutaffifin", 84: "Al-Inshiqaq",
        85: "Al-Buruj", 86: "At-Tariq", 87: "Al-A'la", 88: "Al-Ghashiya",
        89: "Al-Fajr", 90: "Al-Balad", 91: "Ash-Shams", 92: "Al-Layl",
        93: "Ad-Duha", 94: "Ash-Sharh", 95: "At-Tin", 96: "Al-Alaq",
        97: "Al-Qadr", 98: "Al-Bayyina", 99: "Az-Zalzala", 100: "Al-Adiyat",
        101: "Al-Qari'a", 102: "At-Takathur", 103: "Al-Asr", 104: "Al-Humaza",
        105: "Al-Fil", 106: "Quraysh", 107: "Al-Ma'un", 108: "Al-Kawthar",
        109: "Al-Kafirun", 110: "An-Nasr", 111: "Al-Masad", 112: "Al-Ikhlas",
        113: "Al-Falaq", 114: "An-Nas"
    }
    return surah_names.get(surah_num, f"Surah-{surah_num}")

def read_surah_file(surah_num):
    """Read all verses from a surah file"""
    filepath = os.path.join("out", f"{surah_num:03d}.txt")
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"Warning: File not found for surah {surah_num}")
        return []

def build_quran_file():
    """Build the complete Quran file from individual surah files"""
    output_file = os.path.join("out", "whole-quran-italian.txt")
    total_verses = 0
    
    with open(output_file, 'w', encoding='utf-8') as outfile:
        # Add a header
        outfile.write("# Il Sacro Corano - Traduzione del significato in italiano\n\n")
        
        # Process each surah
        for surah_num in range(1, 115):  # 1 to 114
            verses = read_surah_file(surah_num)
            if not verses:
                print(f"Skipping surah {surah_num} - no verses found")
                continue
                
            # Write surah header
            surah_name = get_surah_name(surah_num)
            outfile.write(f"# {surah_num}. {surah_name}\n\n")
            
            # Write all verses with proper numbering
            for i, verse in enumerate(verses, 1):
                # Ensure the verse starts with a number
                if not verse[0].isdigit():
                    verse = f"{i}. {verse}"
                outfile.write(f"{verse}\n")
            
            total_verses += len(verses)
            print(f"Processed surah {surah_num}: {surah_name} ({len(verses)} verses)")
            
            # Add extra newline between surahs
            outfile.write("\n")
    
    print(f"Successfully created {output_file}")

if __name__ == "__main__":
    build_quran_file()

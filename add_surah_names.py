#!/usr/bin/env python3
"""
Script to add translated surah names to the top of formatted surah files.
"""

import os
from pathlib import Path

# Italian surah names from the first line of each file in the italian directory
ITALIAN_SURAH_NAMES = {
    1: "L'Aprente",
    2: "La Giovenca",
    3: "La Famiglia di Imran",
    4: "Le Donne",
    5: "La Tavola Imbandita",
    6: "Il Bestiame",
    7: "Le Alture",
    8: "Il Bottino",
    9: "Il Pentimento",
    10: "Giona",
    11: "Hud",
    12: "Giuseppe",
    13: "Il Tuono",
    14: "Abramo",
    15: "Al-Hijr",
    16: "L'Ape",
    17: "Il Viaggio Notturno",
    18: "La Caverna",
    19: "Maria",
    20: "Ta-Ha",
    21: "I Profeti",
    22: "Il Pellegrinaggio",
    23: "I Credenti",
    24: "La Luce",
    25: "Il Discrimine",
    26: "I Poeti",
    27: "La Formica",
    28: "Il Racconto",
    29: "Il Ragno",
    30: "I Romani",
    31: "Luqman",
    32: "La Prosternazione",
    33: "I Fazioni Nemiche",
    34: "Saba",
    35: "Il Creatore",
    36: "Ya-Sin",
    37: "I Ranghi",
    38: "Sad",
    39: "I Gruppi",
    40: "Il Perdonatore",
    41: "Esposti Chiaramente",
    42: "La Consultazione",
    43: "Gli Ornamenti d'Oro",
    44: "Il Fumo",
    45: "L'Inginocchiata",
    46: "Le Dune",
    47: "Maometto",
    48: "La Vittoria",
    49: "Le Stanze Intime",
    50: "Qaf",
    51: "I Venti di Polvere",
    52: "Il Monte",
    53: "La Stella",
    54: "La Luna",
    55: "Il Compassionevole",
    56: "L'Evento Ineluttabile",
    57: "Il Ferro",
    58: "La Disputante",
    59: "L'Esodo",
    60: "La Sottoposta a Esame",
    61: "Le File",
    62: "Il Venerdì",
    63: "Gli Ipocriti",
    64: "Il Reciproco Inganno",
    65: "Il Ripudio",
    66: "L'Interdizione",
    67: "La Sovranità",
    68: "Il Calamo",
    69: "L'Indiscutibile",
    70: "Le Vie dell'Ascesa",
    71: "Noè",
    72: "I Demoni",
    73: "L'Avvolto nel Mantello",
    74: "L'Avvolto nel Mantello",
    75: "La Resurrezione",
    76: "L'Uomo",
    77: "I Messaggeri",
    78: "L'Annuncio",
    79: "I Predatori",
    80: "Si Accigliò",
    81: "L'Oscuramento",
    82: "Lo Squarciarsi",
    83: "I Froddatori",
    84: "Lo Squarciarsi",
    85: "Le Costellazioni",
    86: "L'Astro Notturno",
    87: "L'Altissimo",
    88: "L'Avvolgente",
    89: "L'Alba",
    90: "La Città",
    91: "Il Sole",
    92: "La Notte",
    93: "La Luce del Mattino",
    94: "L'Apertura del Petto",
    95: "Il Fico",
    96: "L'Aderenza",
    97: "Il Destino",
    98: "La Prova Chiara",
    99: "Il Terremoto",
    100: "I Cavalli da Corsa",
    101: "Il Colpo Secco",
    102: "La Gara di Accrescimento",
    103: "Il Pomeriggio",
    104: "Il Diffamatore",
    105: "L'Elefante",
    106: "I Coreisciti",
    107: "Il Necessario",
    108: "L'Abbondanza",
    109: "I Miscredenti",
    110: "Il Soccorso",
    111: "Lo Spago Intrecciato",
    112: "Il Culto Sincero",
    113: "L'Alba Nascente",
    114: "Gli Uomini"
}

"""
ITALIAN_SURAH_NAMES = {
    1: "Al-Fātiḥah (L'Aprente)",
    2: "Al-Baqarah (La Giovenca)",
    3: "Āl ʿImrān (La Famiglia di Imran)",
    4: "An-Nisāʾ (Le Donne)",
    5: "Al-Māʾidah (La Tavola Imbandita)",
    6: "Al-Anʿām (Il Bestiame)",
    7: "Al-Aʿrāf (Le Alture)",
    8: "Al-Anfāl (Il Bottino)",
    9: "At-Tawbah (Il Pentimento)",
    10: "Yūnus (Giona)",
    11: "Hūd (Hud)",
    12: "Yūsuf (Giuseppe)",
    13: "Ar-Raʿd (Il Tuono)",
    14: "Ibrāhīm (Abramo)",
    15: "Al-Ḥijr (Al-Hijr)",
    16: "An-Naḥl (L'Ape)",
    17: "Al-Isrāʾ (Il Viaggio Notturno)",
    18: "Al-Kahf (La Caverna)",
    19: "Maryam (Maria)",
    20: "Ṭāʾ Hāʾ (Ta-Ha)",
    21: "Al-Anbiyāʾ (I Profeti)",
    22: "Al-Ḥajj (Il Pellegrinaggio)",
    23: "Al-Muʾminūn (I Credenti)",
    24: "An-Nūr (La Luce)",
    25: "Al-Furqān (Il Discrimine)",
    26: "Ash-Shuʿarāʾ (I Poeti)",
    27: "An-Naml (La Formica)",
    28: "Al-Qaṣaṣ (Il Racconto)",
    29: "Al-ʿAnkabūt (Il Ragno)",
    30: "Ar-Rūm (I Romani)",
    31: "Luqmān (Luqman)",
    32: "As-Sajdah (La Prosternazione)",
    33: "Al-Aḥzāb (I Fazioni Nemiche)",
    34: "Sabaʾ (Saba)",
    35: "Fāṭir (Il Creatore)",
    36: "Yāʾ Sīn (Ya-Sin)",
    37: "Aṣ-Ṣāffāt (I Ranghi)",
    38: "Ṣād (Sad)",
    39: "Az-Zumar (I Gruppi)",
    40: "Ghāfir (Il Perdonatore)",
    41: "Fuṣṣilat (Esposti Chiaramente)",
    42: "Ash-Shūrā (La Consultazione)",
    43: "Az-Zukhruf (Gli Ornamenti d'Oro)",
    44: "Ad-Dukhān (Il Fumo)",
    45: "Al-Jāthiyah (L'Inginocchiata)",
    46: "Al-Aḥqāf (Le Dune)",
    47: "Muḥammad (Maometto)",
    48: "Al-Fatḥ (La Vittoria)",
    49: "Al-Ḥujurāt (Le Stanze Intime)",
    50: "Qāf (Qaf)",
    51: "Adh-Dhāriyāt (I Venti di Polvere)",
    52: "Aṭ-Ṭūr (Il Monte)",
    53: "An-Najm (La Stella)",
    54: "Al-Qamar (La Luna)",
    55: "Ar-Raḥmān (Il Compassionevole)",
    56: "Al-Wāqiʿah (L'Evento Ineluttabile)",
    57: "Al-Ḥadīd (Il Ferro)",
    58: "Al-Mujādilah (La Disputante)",
    59: "Al-Ḥashr (L'Esodo)",
    60: "Al-Mumtaḥanah (La Sottoposta a Esame)",
    61: "Aṣ-Ṣaff (Le File)",
    62: "Al-Jumuʿah (Il Venerdì)",
    63: "Al-Munāfiqūn (Gli Ipocriti)",
    64: "At-Taghābun (Il Reciproco Inganno)",
    65: "Aṭ-Ṭalāq (Il Ripudio)",
    66: "At-Taḥrīm (L'Interdizione)",
    67: "Al-Mulk (La Sovranità)",
    68: "Al-Qalam (Il Calamo)",
    69: "Al-Ḥāqqah (L'Indiscutibile)",
    70: "Al-Maʿārij (Le Vie dell'Ascesa)",
    71: "Nūḥ (Noè)",
    72: "Al-Jinn (I Demoni)",
    73: "Al-Muzzammil (L'Avvolto nel Mantello)",
    74: "Al-Muddaththir (L'Avvolto nel Mantello)",
    75: "Al-Qiyāmah (La Resurrezione)",
    76: "Al-Insān (L'Uomo)",
    77: "Al-Mursalāt (I Messaggeri)",
    78: "An-Nabaʾ (L'Annuncio)",
    79: "An-Nāziʿāt (I Predatori)",
    80: "ʿAbasa (Si Accigliò)",
    81: "At-Takwīr (L'Oscuramento)",
    82: "Al-Infiṭār (Lo Squarciarsi)",
    83: "Al-Muṭaffifīn (I Froddatori)",
    84: "Al-Inshiqāq (Lo Squarciarsi)",
    85: "Al-Burūj (Le Costellazioni)",
    86: "Aṭ-Ṭāriq (L'Astro Notturno)",
    87: "Al-Aʿlā (L'Altissimo)",
    88: "Al-Ghāshiyah (L'Avvolgente)",
    89: "Al-Fajr (L'Alba)",
    90: "Al-Balad (La Città)",
    91: "Ash-Shams (Il Sole)",
    92: "Al-Layl (La Notte)",
    93: "Aḍ-Ḍuḥā (La Luce del Mattino)",
    94: "Ash-Sharḥ (L'Apertura del Petto)",
    95: "At-Tīn (Il Fico)",
    96: "Al-ʿAlaq (L'Aderenza)",
    97: "Al-Qadr (Il Destino)",
    98: "Al-Bayyinah (La Prova Chiara)",
    99: "Az-Zalzalah (Il Terremoto)",
    100: "Al-ʿĀdiyāt (I Cavalli da Corsa)",
    101: "Al-Qāriʿah (Il Colpo Secco)",
    102: "At-Takāthur (La Gara di Accrescimento)",
    103: "Al-ʿAṣr (Il Pomeriggio)",
    104: "Al-Humazah (Il Diffamatore)",
    105: "Al-Fīl (L'Elefante)",
    106: "Quraysh (I Coreisciti)",
    107: "Al-Māʿūn (Il Necessario)",
    108: "Al-Kawthar (L'Abbondanza)",
    109: "Al-Kāfirūn (I Miscredenti)",
    110: "An-Naṣr (Il Soccorso)",
    111: "Al-Masad (Lo Spago Intrecciato)",
    112: "Al-Ikhlāṣ (Il Culto Sincero)",
    113: "Al-Falaq (L'Alba Nascente)",
    114: "An-Nās (Gli Uomini)"
}
"""

def add_surah_name_to_file(file_path, surah_number):
    """Add surah name to the beginning of the file if not already present."""
    # Get the Italian surah name
    surah_name = ITALIAN_SURAH_NAMES.get(surah_number)
    if not surah_name:
        print(f"Warning: No Italian name found for surah {surah_number}")
        return
    
    # Read the current content
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if the surah name is already at the beginning
    if content.startswith(surah_name):
        print(f"Skipping {file_path.name}: Already has surah name")
        return
    
    # Add the surah name at the beginning
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(f"{surah_name}\n")
        f.write(content)
    
    print(f"Updated {file_path.name} with surah name: {surah_name}")

def main():
    # Directory containing the formatted surah files
    formatted_dir = Path("italian-formatted-gemini")
    
    if not formatted_dir.exists() or not formatted_dir.is_dir():
        print(f"Error: Directory not found: {formatted_dir}")
        return
    
    # Get all .txt files in the directory
    surah_files = sorted(formatted_dir.glob("*.txt"))
    
    if not surah_files:
        print(f"No .txt files found in {formatted_dir}")
        return
    
    print(f"Found {len(surah_files)} surah files to process")
    
    # Process each file
    for file_path in surah_files:
        try:
            # Extract surah number from filename (e.g., "001.txt" -> 1)
            surah_num = int(file_path.stem)
            add_surah_name_to_file(file_path, surah_num)
        except (ValueError, IndexError):
            print(f"Skipping {file_path.name}: Invalid filename format")
        except Exception as e:
            print(f"Error processing {file_path.name}: {e}")

if __name__ == "__main__":
    main()

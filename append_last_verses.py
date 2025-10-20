import os

# Configuration
OUTPUT_DIR = "out"
QURAN_FILE = os.path.join(OUTPUT_DIR, "quran-italian.txt")

def get_last_verse(filepath):
    """Read the last non-empty line from a file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]
        return lines[-1] if lines else ""

def clean_verse_in_line(line, verse_text):
    """Clean up a line to contain only the verse text"""
    # Find the verse number (e.g., "4." from "4. e nessuno è uguale a Lui».")
    verse_parts = verse_text.split('.', 1)
    if len(verse_parts) == 2:
        verse_num = verse_parts[0].strip()
        verse_content = verse_parts[1].strip()
        
        # Find the verse number in the line
        if verse_num + '.' in line:
            # Return just the verse number and content
            return f"{verse_num}. {verse_content}\n"
    return line

def update_quran_file(chapter_num, last_verse):
    """Clean up the last verse in the corresponding chapter in quran-italian.txt"""
    # Read the current content
    with open(QURAN_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find the verse number and content
    verse_parts = last_verse.split('.', 1)
    if len(verse_parts) != 2:
        print(f"Warning: Invalid verse format for chapter {chapter_num}")
        return
    
    verse_num = verse_parts[0].strip()
    verse_content = verse_parts[1].strip()
    
    # Create a pattern to find the verse (case insensitive)
    import re
    pattern = re.compile(fr'(\b{re.escape(verse_num)}\\.\s*)(.*?)(?=\n\d+\.|\n#|\Z)', 
                        re.IGNORECASE | re.DOTALL)
    
    # Replace the verse content while keeping the verse number
    new_content = pattern.sub(fr'\1{verse_content}', content)
    
    # Write the updated content back
    with open(QURAN_FILE, 'w', encoding='utf-8') as f:
        f.write(new_content)

def main():
    # Get all chapter files
    chapter_files = sorted([f for f in os.listdir(OUTPUT_DIR) 
                          if f.endswith('.txt') and f != 'quran-italian.txt' and f != '.DS_Store'])
    
    for chapter_file in chapter_files:
        try:
            chapter_num = os.path.splitext(chapter_file)[0]  # Get the number from '001.txt'
            print(f"Processing chapter {chapter_num}...")
            
            # Get the last verse
            filepath = os.path.join(OUTPUT_DIR, chapter_file)
            last_verse = get_last_verse(filepath)
            
            if last_verse:
                update_quran_file(chapter_num, last_verse)
                print(f"Updated chapter {chapter_num} in quran-italian.txt")
            else:
                print(f"No content found in {chapter_file}")
                
        except Exception as e:
            print(f"Error processing {chapter_file}: {str(e)}")
    
    print("\nAll chapters processed successfully!")

if __name__ == "__main__":
    main()

import os
import google.generativeai as genai
from pathlib import Path

# Configuration
OUTPUT_DIR = "out"
GEMINI_API_KEY = "AIzaSyAuyTO5D9bPD3tyTU5UDcc63VJ5kQPbnYE"  # Replace with your actual API key

def get_last_verse(filepath):
    """Read the last non-empty line from a file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]
        return lines[-1] if lines else None

def update_last_verse(filepath, new_content):
    """Replace the last non-empty line in a file with new content."""
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Find the last non-empty line
    last_non_empty = len(lines) - 1
    while last_non_empty >= 0 and not lines[last_non_empty].strip():
        last_non_empty -= 1
    
    if last_non_empty >= 0:
        lines[last_non_empty] = new_content + '\n'
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(lines)

def process_chapter(chapter_file):
    """Process a single chapter file."""
    filepath = os.path.join(OUTPUT_DIR, chapter_file)
    chapter_name = os.path.splitext(chapter_file)[0]
    
    # Get the last verse
    last_verse = get_last_verse(filepath)
    if not last_verse:
        print(f"Skipping {chapter_file}: No content found")
        return
    
    print(f"Processing {chapter_file}...")
    
    # Create the prompt (you can modify this as needed)
    prompt = f"""
    You are processing chapter {chapter_name} of the Quran.
    You have the italian translation of the Quran.
    I'll pass you the last verse of the chapter, appended to it some illustrations.
    Your task is to separate the verse from the illustrations and return only the verse.
    The last verse is: {last_verse}
    
    Return only the verse, without any additional text.
    """
    
    try:
        # Initialize Gemini
        genai.configure(api_key=GEMINI_API_KEY)
        
        # List available models for debugging
        print("\nAvailable models:")
        for m in genai.list_models():
            print(f"- {m.name}")
        
        # Try to use the first available model
        models = list(genai.list_models())
        if not models:
            raise Exception("No models available. Please check your API key and permissions.")
            
        # Try to find a suitable text generation model
        model_name = None
        preferred_models = [
            'gemini-2.5-pro',
            'gemini-2.0-pro',
            'gemini-pro-latest'
        ]
        
        # First try preferred models
        for pref_model in preferred_models:
            for m in models:
                if pref_model in m.name and 'generateContent' in m.supported_generation_methods:
                    model_name = m.name
                    break
            if model_name:
                break
                
        # If no preferred model found, try any model that supports generateContent
        if not model_name:
            for m in models:
                if 'generateContent' in m.supported_generation_methods and 'gemini' in m.name.lower():
                    model_name = m.name
                    break
                    
        if not model_name and models:
            model_name = models[0].name
            
        print(f"\nUsing model: {model_name}")
        model = genai.GenerativeModel(model_name)
        
        # Generate response
        response = model.generate_content(prompt)
        
        if response.text:
            update_last_verse(filepath, response.text.strip())
            print(f"Updated {chapter_file} successfully")
        else:
            print(f"No response from API for {chapter_file}")
            
    except Exception as e:
        print(f"Error processing {chapter_file}: {str(e)}")

def main():
    # Get all chapter files
    chapter_files = sorted([f for f in os.listdir(OUTPUT_DIR) if f.endswith('.txt') and f != 'quran-italian.txt'])
    
    # Process each chapter
    # for chapter_file in chapter_files:
    #     process_chapter(chapter_file)
    
    chapter_file = "003.txt"
    process_chapter(chapter_file)
    
    print("Processing complete!")

if __name__ == "__main__":
    main()

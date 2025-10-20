import os
from rebuild_quran_italian import get_surah_name

def rename_surah_files():
    """Rename all surah files to include both number and name"""
    # Directory containing the surah files
    directory = "out"
    
    # Get list of all .txt files in the directory
    files = [f for f in os.listdir(directory) 
             if f.endswith('.txt') and f != 'quran-italian.txt' and f != 'whole-quran-italian.txt']
    
    # Sort files to ensure correct order
    files.sort()
    
    # Rename each file
    for filename in files:
        try:
            # Extract the surah number from the filename
            surah_num = int(os.path.splitext(filename)[0])
            
            # Get the surah name
            surah_name = get_surah_name(surah_num)
            
            # Create the new filename
            new_filename = f"{surah_num:03d}-{surah_name}.txt"
            
            # Full paths
            old_path = os.path.join(directory, filename)
            new_path = os.path.join(directory, new_filename)
            
            # Rename the file
            os.rename(old_path, new_path)
            print(f"Renamed: {filename} -> {new_filename}")
            
        except (ValueError, IndexError) as e:
            print(f"Skipping {filename}: {str(e)}")
        except FileNotFoundError as e:
            print(f"File not found: {filename}")
        except Exception as e:
            print(f"Error processing {filename}: {str(e)}")

if __name__ == "__main__":
    print("Starting to rename surah files...")
    rename_surah_files()
    print("\nFile renaming completed!")

import os
import shutil
import csv
import subprocess
import multiprocessing
import re

# Configuration
USE_PATH_REPLACEMENT = True  # Set to False if you don't need to change the media path prefix
NETWORK_SHARE_PREFIX = "/music/"  # Prefix to replace
NEW_PREFIX = "V:/music/"  # Replace with actual mount point or new path
OUTPUT_DIR = "./out-new/"  # Destination for copied/converted files
CONVERT_TO_MP3 = True  # Set to True to convert to MP3 using ffmpeg
MAX_WORKERS = 10  # Number of files to process in parallel
CSV_FILE_PATH = "plex.csv"  # Configurable path to the CSV file
LAME_PRESET = "v0"  # Options: 'v0', 'v2', '320'

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

INVALID_CHARS = r'[\\/*?\":<>|]'


def check_ffmpeg():
    """Checks if ffmpeg is installed and accessible."""
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        print("ffmpeg is installed and working.")
    except subprocess.CalledProcessError:
        print("Error: ffmpeg is not installed or not working correctly.")
        exit(1)
    except FileNotFoundError:
        print("Error: ffmpeg is not installed or not found in PATH.")
        exit(1)


def format_filename(row):
    """Formats the filename based on CSV data, removing invalid characters."""
    artist = row.get("Audio Track Artist", "").strip()
    title = row.get("Title", "").strip()
    year = row.get("Album Year", "").strip()
    codec = f"MP3 {LAME_PRESET.upper()}" if CONVERT_TO_MP3 else row.get("Media Audio Codec", "").strip()
    
    if not artist or not title:
        return None
    
    filename = f"{artist} - {title} ({year}) [{codec}]"
    return re.sub(INVALID_CHARS, "_", filename)  # Remove invalid characters


def copy_and_convert(row):
    """Copies the file from the network share, renames it, and converts if needed."""
    file_path = row["Part File Combined"].strip()

    if USE_PATH_REPLACEMENT:
        new_path = file_path.replace(NETWORK_SHARE_PREFIX, NEW_PREFIX)
    else:
        new_path = file_path
    
    if not os.path.exists(new_path):
        print(f"File not found: {new_path}")
        return
    
    new_filename = format_filename(row)
    if new_filename:
        new_filename += os.path.splitext(new_path)[1]  # Preserve extension
    else:
        new_filename = os.path.basename(new_path)  # Use original filename
    
    output_file = os.path.join(OUTPUT_DIR, new_filename)
    
    if CONVERT_TO_MP3:
        mp3_output = os.path.splitext(output_file)[0] + ".mp3"
        try:
            print(f"Converting: {new_path} -> {mp3_output}")
            ffmpeg_cmd = ["ffmpeg", "-i", new_path, "-y"]
            
            if LAME_PRESET == "v0":
                ffmpeg_cmd.extend(["-q:a", "0"])
            elif LAME_PRESET == "v2":
                ffmpeg_cmd.extend(["-q:a", "2"])
            elif LAME_PRESET == "320":
                ffmpeg_cmd.extend(["-b:a", "320k"])
            
            ffmpeg_cmd.append(mp3_output)
            result = subprocess.run(ffmpeg_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            
            if result.returncode != 0:
                print(f"FFmpeg error for {new_path}: {result.stderr.decode().strip()}")
        except subprocess.CalledProcessError as e:
            print(f"Error processing {new_path}: {e}")
    else:
        print(f"Copying: {new_path} -> {output_file}")
        shutil.copy2(new_path, output_file)


def process_csv(csv_file):
    """Processes the CSV file and downloads/converts files using multiprocessing."""
    with open(csv_file, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='|')
        rows = [row for row in reader]
    
    with multiprocessing.Pool(processes=MAX_WORKERS) as pool:
        pool.map(copy_and_convert, rows)


if __name__ == "__main__":
    check_ffmpeg()
    process_csv(CSV_FILE_PATH)

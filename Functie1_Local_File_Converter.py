
#Functie 1 - Local File Converter
import subprocess
import os
import math
import numpy as np
from scipy.io import wavfile
import sqlite3
from datetime import datetime
# from pydub import AudioSegment

#Paths
FFMPEG_PATH = r"C:\Gegevens Nino\ffmpeg\bin\ffmpeg.exe"
RUBBERBAND_PATH = r"C:\Gegevens Nino\rubberband\rubberband.exe"
DB_PATH = "audio_converter.db"


#Functies
def run_subprocess(cmd, description="Processing"):
    """Run a subprocess and handle errors gracefully."""
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error during {description}:")
        print(e.stderr.decode('utf-8'))
        return False

def init_database():
    """Create database & tables if not exist."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS converted_files (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        input_path TEXT,
        output_path TEXT,
        detected_hz REAL,
        target_hz REAL,
        timestamp TEXT 
    )
    """)

    conn.commit()
    conn.close()

#   Saving to DB
def save_conversion_to_db(input_path, output_path, detected_hz, target_hz):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO converted_files (input_path, output_path, detected_hz, target_hz, timestamp) 
    VALUES (?, ?, ?, ?, ?)
    """, (input_path, output_path, detected_hz, target_hz, datetime.now().isoformat()))

    conn.commit()
    conn.close()

#   Show all converted
def list_all_converted():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT * FROM converted_files ORDER BY timestamp DESC")
    rows = cur.fetchall()
    conn.close()
    return rows

#   History DB
def show_history_menu():
    """Show all converted files stored in the database, with optional filter."""
    while True:
        print("\n--- Conversion History Filter ---")
        print("1 = Show all")
        print("2 = Filter by target Hz")
        print("3 = Filter by file type")
        print("4 = Back to main menu")
        choice = input("Your choice: ").strip()

        rows = list_all_converted()

        if choice == "1":
            pass
        elif choice == "2":
            try:
                hz_filter = float(input("Enter target Hz to filter by: "))
            except ValueError:
                print("Invalid input!")
                continue
            rows = [r for r in rows if abs(r[4] - hz_filter) < 0.01]
        elif choice == "3":
            ext_filter = input("Enter file extension (e.g., .mp3): ").lower()
            rows = [r for r in rows if r[2].lower().endswith(ext_filter)]
        elif choice == "4":
            return
        else:
            print("Invalid choice!")
            continue

        if not rows:
            print("\nNo conversions found for this filter. \n")
        else:
            for idx, row in enumerate(rows, 1):
                print(f"""

{idx})
ID:          {row[0]}
Input file:  {row[1]}
Output file: {row[2]}
Detected Hz: {row[3]}
Target Hz:   {row[4]}
Timestamp:   {row[5]}
-----------------------------""")
            input("\nPress Enter to continue...")

#   --------------------
#   Quality functies
#   --------------------

#   Kwaliteit kiezen
def choose_quality(output_format):
    """
    Biedt kwaliteitsopties aan en retourneert de ffmpeg-kwaliteit flags.
    Default is altijd high quality.
    """
    if output_format == ".wav":
        print("WAV is lossless. High quality wordt automatisch gebruikt.")
        return []
    elif output_format == ".flac":
        print("\nChoose FLAC quality (compression level 0-8, default = 8):")
        print("1 = Fast/low compression")
        print("2 = Medium compression")
        print("3 = High compression")
        choice = input("Your choice (press Enter for default high quality): ").strip()
        level_map = {"1": "0", "2": "5", "3": "8"}
        level = level_map.get(choice, "8")
        return ["-compression_level", level]
    elif output_format == ".mp3":
        print("\nChoose MP3 quality:")
        print("1 = Low (128 kbps)")
        print("2 = Medium (192 kbps)")
        print("3 = High (320 kbps, default)")
        choice = input("Your choice (press Enter for default high quality): ").strip()
        bitrate_map = {"1": "128", "2": "192", "3": "320"}
        bitrate = bitrate_map.get(choice, "320")
        return ["-b:a", bitrate]
    else:
        return []

#   --------------------
#   Audio Functies
#   --------------------

#   Sample analysis - 1
def extract_sample(input_file, duration=3):
    """Extract a short audio sample for analysis with a unique temp file."""
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    sample_file = f"temp_sample_{base_name}.wav"
    subprocess.run([
        FFMPEG_PATH, "-y",
        "-i", input_file,
        "-t", str(duration),
        "-ac", "1",
        "-ar", "44100",
        sample_file
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return sample_file

#   Sample analysis - 2
def estimate_tuning(sample_file):
    """Estimate average tuning frequency of audio (Hz)."""
    rate, data = wavfile.read(sample_file)
    if len(data.shape) > 1: # stereo -> mono
        data = data.mean(axis=1)
    #Take FFT
    fft = np.fft.rfft(data)
    freqs = np.fft.rfftfreq(len(data), 1/rate)
    magnitude = np.abs(fft)
    peak_idx = np.argmax(magnitude)
    fundamental = freqs[peak_idx]
    return fundamental

#   Validatie audio file
def validate_audio_file(input_file):
    """Check if the file exists and is valid audio."""
    if not os.path.exists(input_file):
        print("❌ Error: File does not exist.")
        return False

    print("Checking file validity...")
    result = subprocess.run([
        FFMPEG_PATH,
        "-v", "error",
        "-i", input_file,
        "-f", "null",
        "-"
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    if result.returncode != 0:
        print("❌ Error: File is not a valid audio file or is corrupted.")
        return False

    print("✔️ Audio file is valid.")
    return True

#   ------------------
#   Audio conversie functies
#   ------------------

#   Bereken aantal semitonen
def semitone_shift_for_target(target_hz, reference_hz=440.0):
    ratio = target_hz / reference_hz
    return 12 * math.log2(ratio)

#   Stap 1: Convert input -> WAV
def convert_to_wav(input_file, temp_wav="temp_input.wav"):
    """Convert any audio file to WAV using ffmpeg."""
    print("Converting input to WAV...")
    cmd = [
        FFMPEG_PATH, "-y",
        "-i", input_file,
        "-ac", "2",
        "-ar", "44100",
        temp_wav
    ]
    if not run_subprocess(cmd, "WAV conversion"):
        return None
    return temp_wav

#   Stap 2: Pitch Shift met Rubberband
def pitch_shift_wav(input_wav, output_wav="temp_shifted.wav", semitone_shift=0.0):
    """Pitch shift WAV using Rubberband CLI."""
    print(f"Applying pitch shift ({semitone_shift:+.6f} semitones)...")
    cmd = [
        RUBBERBAND_PATH, "--pitch",
        str(semitone_shift),
        input_wav, output_wav
    ]
    if not run_subprocess(cmd, "pitch shift"):
        return None
    return output_wav

#   Stap 3: WAV -> eindformat
def export_final(output_wav, output_file):
    """Convert WAV back into chosen format using ffmpeg with quality options."""
    print("Exporting final file:", output_file)
    quality_flags = choose_quality(os.path.splitext(output_file)[1].lower())
    cmd = [FFMPEG_PATH, "-y",
           "-i", output_wav
           ] + quality_flags + [output_file]
    if not run_subprocess(cmd, "final export"):
        print("⚠️ Export failed.")

#   Full conversion pipeline
def convert_audio_440_to_target(input_file, output_file, target_hz):
    print(f"Starting 440 Hz -> {target_hz} Hz conversion...")

    base_name = os.path.splitext(os.path.basename(input_file))[0]

    temp_wav = f"temp_{base_name}.wav"
    shifted_wav = f"temp_{base_name}_shifted.wav"

    try:
        # 1. Input naar WAV
        convert_to_wav(input_file, temp_wav)

        # 2. Pitch shift
        semitones = semitone_shift_for_target(target_hz)
        pitch_shift_wav(temp_wav, shifted_wav, semitone_shift=semitones)

        # 3. WAV naar eindbestand
        export_final(shifted_wav, output_file)

        print("Done! Converted file saved as:", output_file)

    finally:
        # 4. Opschonen
        for f in (temp_wav, shifted_wav):
            try:
                if f and os.path.exists(f):
                    os.remove(f)
            except:
                pass

#   Batch converting
def batch_convert_files(file_list, target_hz, output_folder, output_ext):
    """
    Convert multiple audio files to the target tuning. With progress display.

    Parameters:
         file_list: list of file paths
         target_hz: desired target frequency in Hz
         output_folder: folder where converted files will be saved
    """
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    total_files = len(file_list)
    for idx, file_path in enumerate(file_list, 1):
        print(f"\nProcessing {idx}/{total_files}: {file_path}")

        if not validate_audio_file(file_path):
            print(f"Skipping invalid file: {file_path}")
            continue

        sample_wav = extract_sample(file_path)
        detected_hz = estimate_tuning(sample_wav)
        if os.path.exists(sample_wav):
            os.remove(sample_wav)

        print(f"Detected approximate tuning: {detected_hz:.2f} Hz")

        if abs(detected_hz - target_hz) < 1.0:
            print(f"⚠️ File is already close to target ({detected_hz:.2f} Hz ~ {target_hz} Hz).")
            proceed = input("Do you still want to convert? (y/n): ").strip().lower()
            if proceed != "y":
                print("Skipping this file.")
                continue

        name, ext = os.path.splitext(os.path.basename(file_path))
        output_file = os.path.join(output_folder, f"{name}_{target_hz}Hz{output_ext}")

        convert_audio_440_to_target(file_path, output_file, target_hz)

        save_conversion_to_db(
            input_path=file_path,
            output_path=output_file,
            detected_hz=detected_hz,
            target_hz=target_hz,
        )

    print(f"\n✅ Batch conversion complete ({total_files} files processed).")

# -------------------------
#   Startpunt
# -------------------------
if __name__ == "__main__":
    # ------------------------
    #   Database runnen
    # ------------------------
    init_database()

    # ------------------------
    #   Main Menu
    # ------------------------
    while True:
        print("\n=== MAIN MENU ===")
        print("1 = Convert audio")
        print("2 = View conversion history")
        print("3 = Exit")

        menu_choice = input("Choose an option: ").strip()

        if menu_choice == "1":
            print("\nChoose target tuning:")
            print("1 = 432 Hz")
            print("2 = 528 Hz")
            print("3 = Custom frequency")
            choice = input("Your choice: ").strip()
            if choice == "1":
                target_hz = 432
            elif choice == "2":
                target_hz = 528
            elif choice == "3":
                try:
                    target_hz = float(input("Enter custom target frequency (Hz): (20-20000 Hz "))
                except ValueError:
                    print("Invalid input!")
                    continue
            else:
                print("Invalid choice!")
                continue

            # ------------------------
            #   Input/output format choice
            # ------------------------
            print("\nAllowed input formats:")
            print("1 = MP3 only")
            print("2 = WAV only")
            print("3 = FLAC only")
            print("4 = MP3 & WAV")
            print("5 = MP3, WAV & FLAC")
            fmt_choice = input("Your choice: ").strip()

            format_options = {
                "1": (".mp3",),
                "2": (".wav",),
                "3": (".flac",),
                "4": (".mp3", ".wav"),
                "5": (".mp3", ".wav", ".flac"),
            }
            allowed_inputs = format_options.get(fmt_choice)

            if not allowed_inputs:
                print("Invalid choice!")
                continue

            allowed_inputs = tuple(ext.lower() for ext in allowed_inputs)

            print("\nChoose output format:")
            print("1 = MP3")
            print("2 = WAV")
            print("3 = FLAC")
            out_choice = input("Your choice: ").strip()
            output_ext = {"1": ".mp3", "2": ".wav", "3": ".flac"}.get(out_choice)
            if not output_ext:
                print("Invalid choice!")
                continue

            date_str = datetime.now().strftime("%Y-%m-%d")
            default_output_folder = f"Converted_{target_hz}Hz_{date_str}"
            print(f"Default output folder: {default_output_folder}")
            folder_input = input("Press Enter to use default or type folder name: ").strip()
            output_folder = folder_input if folder_input else default_output_folder
            if not os.path.exists(output_folder):
                os.makedirs(output_folder)

            # ------------------------
            #   Mode keuze
            # ------------------------
            mode = input("Single file or batch mode? (s/b): ").strip().lower()

            #   Single Mode
            if mode == "s":
                input_path = input("Input file path to convert: ").strip()  # C:\Music\440hz_geluid.mp3

                if not validate_audio_file(input_path):
                    continue

                sample_wav = extract_sample(input_path)
                detected_hz = estimate_tuning(sample_wav)
                os.remove(sample_wav)

                print(f"Detected approximate tuning: {detected_hz:.2f} Hz")

                if abs(detected_hz - target_hz) < 1.0:
                    proceed = input("Do you still want to convert? (y/n): ").strip().lower()
                    if proceed != "y":
                        print("Conversion canceled.")
                        continue

                name = input(
                    "Output file name (without extension): ").strip()  # Geluid_432Hz.mp3  of  Geluid_528Hz.mp3
                output_path = os.path.join(output_folder, name + output_ext)
                convert_audio_440_to_target(input_path, output_path, target_hz)
                save_conversion_to_db(input_path, output_path, detected_hz, target_hz)
                print("✅ Conversion complete.")

            #   Batch Mode
            elif mode == "b":
                folder_path = input("Enter folder path containing files to convert: ").strip()  # C:\
                if not os.path.exists(folder_path):
                    print("Folder does not exist!")
                    continue
                file_list = [
                    os.path.join(folder_path, f)
                    for f in os.listdir(folder_path)
                    if f.lower().endswith(allowed_inputs)
                ]
                if not file_list:
                    print("No audio files found in folder.")
                    continue

                print(f"Found {len(file_list)} files. Starting batch conversion...")
                batch_convert_files(file_list, target_hz, output_folder, output_ext)
                print("\n✅ Batch conversion complete.")

            else:
                print("Invalid mode.")
                continue

        elif menu_choice == "2":
            show_history_menu()
        elif menu_choice == "3":
            print("Exiting program.")
            exit()
        else:
            print("Invalid choice, try again.")











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

def init_database()
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

#Functies
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

#   Batch converting
def batch_convert_files(file_list, target_hz, output_folder, output_ext):
    """
    Convert multiple audio files to the target tuning.

    Parameters:
         file_list: list of file paths
         target_hz: desired target frequency in Hz
         output_folder: folder where converted files will be saved
    """
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    for file_path in file_list:
        print(f"\nProcessing {file_path}")

        if not validate_audio_file(file_path):
            print(f"Skipping invalid file: {file_path}")
            continue

        sample_wav = extract_sample(file_path)
        detected_hz = estimate_tuning(sample_wav)
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

#   Bereken aantal semitonen
def semitone_shift_for_target(target_hz, reference_hz=440.0):
    ratio = target_hz / reference_hz
    return 12 * math.log2(ratio)

#   Stap 1: Convert input -> WAV
def convert_to_wav(input_file, temp_wav="temp_input.wav"):
    """Convert any audio file to WAV using ffmpeg."""
    print("Converting input to WAV...")
    subprocess.run([
        FFMPEG_PATH, "-y",
        "-i", input_file,
        "-ac", "2",             # stereo
        "-ar", "44100",         # sample rate
        temp_wav
    ], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    return temp_wav

#   Stap 2: Pitch Shift met Rubberband
def pitch_shift_wav(input_wav, output_wav="temp_shifted.wav", semitone_shift=0.0):
    """Pitch shift WAV using Rubberband CLI."""
    print(f"Applying pitch shift ({semitone_shift:+.6f}...)")
    subprocess.run([
        RUBBERBAND_PATH,
        "--pitch", str(semitone_shift),
        input_wav,
        output_wav
    ], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT, shell=True)
    return output_wav

#   Stap 3: WAV -> eindformat
def export_final(output_wav, output_file):
    """Convert WAV back into chosen format using ffmpeg."""
    print("Exporting final file:", output_file)
    subprocess.run([
        FFMPEG_PATH, "-y",
        "-i", output_wav,
        output_file
    ], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

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
            if os.path.exists(f):
                os.remove(f)


# -------------------------
#   Startpunt
# -------------------------
if __name__ == "__main__":
    # ------------------------
    #   Database runnen
    # ------------------------
    init_database()

    def save_conversion_to_db(input_path, output_path, detected_hz, target_hz):
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        cur.execute("""
        INSERT INTO converted_files (input_path, output_path, detected_hz, target_hz, timestamp) 
        VALUES (?, ?, ?, ?, ?) 
    # ------------------------
    #   Frequentie keuze
    # ------------------------
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
        target_hz = float(input("Enter custom target frequency (Hz): "))
    else:
        print("Invalid choice!")
        exit()

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

    if fmt_choice == "1":
        allowed_inputs = (".mp3",)
    elif fmt_choice == "2":
        allowed_inputs = (".wav",)
    elif fmt_choice == "3":
        allowed_inputs = (".flac")
    elif fmt_choice == "4":
        allowed_inputs = (".mp3", ".wav")
    elif fmt_choice == "5":
        allowed_inputs = (".mp3", ".wav", ".flac")
    else:
        print("Invalid choice!")
        exit()

    print("\nChoose output format:")
    print("1 = MP3")
    print("2 = WAV")
    print("3 = FLAC")
    out_choice = input("Your choice: ").strip()

    if out_choice == "1":
        output_ext = ".mp3"
    elif out_choice == "2":
        output_ext = ".wav"
    elif out_choice == "3":
        output_ext = ".flac"
    else:
        print("Invalid choice!")
        exit()

    # ------------------------
    #   Mode keuze
    # ------------------------
    mode = input("Single file or batch mode? (s/b): ").strip().lower()

    #   Single Mode
    if mode == "s":
        input_path = input("Input file path to convert: ")              # C:\Music\440hz_geluid.mp3

        if not validate_audio_file(input_path):
            exit()

        sample_wav = extract_sample(input_path)
        detected_hz = estimate_tuning(sample_wav)
        os.remove(sample_wav)

        print(f"Detected approximate tuning: {detected_hz:.2f} Hz")

        if abs(detected_hz - target_hz) < 1.0:
            print(f"⚠️ File is already close to target ({detected_hz:.2f} Hz ~ {target_hz} Hz).")
            proceed = input("Do you still want to convert? (y/n): ").strip().lower()
            if proceed != "y":
                print("Conversion canceled.")
                exit()

        name = input("Output file name (without extension): ").strip()  # Geluid_432Hz.mp3  of  Geluid_528Hz.mp3
        output_path = name + output_ext

        convert_audio_440_to_target(input_path, output_path, target_hz)
        print("Done.")

    #   Batch Mode
    elif mode == "b":
        folder_path = input("Enter folder path containing files to convert: ").strip()  # C:\
        output_path = input("Enter folder name for converted files: ").strip()          # Folder_Geluiden_432Hz.mp3

        if not os.path.exists(output_path):
            os.makedirs(output_path)

        file_list = [
            os.path.join(folder_path, f)
            for f in os.listdir(folder_path)
            if f.lower().endswith(allowed_inputs)
        ]

        if not file_list:
            print("No audio files found in folder.")
            exit()

        print(f"Found {len(file_list)} files. Starting batch conversion...")

        batch_convert_files(file_list, target_hz, output_path, output_ext)

        print("Batch conversion complete.")

    else:
        print("Invalid mode.")
        exit()




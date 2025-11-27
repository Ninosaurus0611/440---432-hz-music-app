
#Functie 1 - Local File Converter
import subprocess
import os
import math
import numpy as np
from scipy.io import wavfile
# from pydub import AudioSegment

#PATHS
FFMPEG_PATH = r"C:\Gegevens Nino\ffmpeg\bin\ffmpeg.exe"
RUBBERBAND_PATH = r"C:\Gegevens Nino\rubberband\rubberband.exe"

#Functies
#   Sample analysis - 1
def extract_sample(input_file, sample_file="temp_sample.wav", duration=3):
    """Extract a short audio sample for analysis."""
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
        "ffmpeg", "-y",
        "-i", output_wav,
        output_file
    ], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

#   Full conversion pipeline
def convert_audio_440_to_target(input_file, output_file, target_hz):
    print(f"Starting 440 Hz -> {target_hz} Hz conversion...")

    temp_wav = "temp_input.wav"
    shifted_wav = "temp_shifted.wav"

    # 1. Input naar WAV
    convert_to_wav(input_file, temp_wav)

    # 2. Pitch shift
    semitones = semitone_shift_for_target(target_hz)
    pitch_shift_wav(temp_wav, shifted_wav, semitone_shift=semitones)

    # 3. WAV naar eindbestand
    export_final(shifted_wav, output_file)

    # 4. Opschonen
    os.remove(temp_wav)
    os.remove(shifted_wav)

    print("Done! Converted file saved as:", output_file)

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

# -------------------------
#   Startpunt
# -------------------------
if __name__ == "__main__":
    input_path = input("Input file: ")                                  # C:\Music\440hz_geluid.mp3

    if not validate_audio_file(input_path):
        exit()

    output_path = input("Output file name (e.g., song_432.mp3): ")      # Geluid_432Hz.mp3  of  Geluid_528Hz.mp3


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

    convert_audio_440_to_target(input_path, output_path, target_hz)



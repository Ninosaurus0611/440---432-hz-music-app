
#Functie 1 - Local File Converter
import subprocess
import os
import math
# from pydub import AudioSegment

FFMPEG_PATH = r"C:\Gegevens Nino\ffmpeg\bin\ffmpeg.exe"


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

def semitone_shift_for_target(target_hz, reference_hz=440.0):
    ratio = target_hz / reference_hz
    return 12 * math.log2(ratio)

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

def pitch_shift_wav(input_wav, output_wav="temp_shifted.wav", semitone_shift=0.0):
    """Pitch shift WAV using Rubberband CLI."""
    print(f"Applying pitch shift ({semitone_shift:+.6f}...)")
    subprocess.run([
        "rubberband",
        "--pitch", str(semitone_shift),
        input_wav,
        output_wav
    ], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT, shell=True)
    return output_wav

def export_final(output_wav, output_file):
    """Convert WAV back into chosen format using ffmpeg."""
    print("Exporting final file:", output_file)
    subprocess.run([
        "ffmpeg", "-y",
        "-i", output_wav,
        output_file
    ], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

def convert_audio_440_to_target(input_file, output_file, target_hz):
    print(f"Starting 440 Hz -> {target_hz} Hz conversion...")

    temp_wav = "temp_input.wav"
    shifted_wav = "temp_shifted.wav"

    convert_to_wav(input_file, temp_wav)

    semitones = semitone_shift_for_target(target_hz)
    pitch_shift_wav(temp_wav, shifted_wav, semitone_shift=semitones)

    export_final(shifted_wav, output_file)

    os.remove(temp_wav)
    os.remove(shifted_wav)

    print("Done! Converted file saved as:", output_file)


#Example usage:
if __name__ == "__main__":
    input_path = input("Input file: ")                                  # C:\Music\440hz_geluid.mp3
    output_path = input("Output file name (e.g., song_432.mp3): ")      # Geluid_432Hz.mp3  of  Geluid_528Hz.mp3

    convert_audio_440_to_target(input_path, output_path, target_hz)


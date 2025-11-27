
#Functie 1 - Local File Converter
import subprocess
import os
# from pydub import AudioSegment

# Ratio 440 Hz -> 432 Hz
PITCH_RATIO_432 = 432 / 440

# Rubberband semitone shift (negative)
# A4 440 to 432 = about -0.316 semitones
SEMITONE_SHIFT = -0.316

FFMPEG_PATH = r"C:\Gegevens Nino\ffmpeg\bin\ffmpeg.exe"

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

def pitch_shift_wav(input_wav, output_wav="temp_shifted.wav"):
    """Pitch shift WAV using Rubberband CLI."""
    print("Applying pitch shift (440 -> 432 Hz)...")
    subprocess.run([
        "rubberband",
        "--pitch", str(SEMITONE_SHIFT),
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

def convert_audio_440_to_432(input_file, output_file):
    print("Starting 440 Hz -> 432 Hz conversion...")

    temp_wav = "temp_input.wav"
    shifted_wav = "temp_shifted.wav"

    # Pipeline steps
    convert_to_wav(input_file, temp_wav)
    pitch_shift_wav(temp_wav, shifted_wav)
    export_final(shifted_wav, output_file)

    # Clean up
    os.remove(temp_wav)
    os.remove(shifted_wav)

    print("Done! Converted file saved as:", output_file)

#Example usage:
if __name__ == "__main__":
    input_path = input("Input file: ")                                  # C:\Music\440hz_geluid.mp3
    output_path = input("Output file name (e.g., song_432.mp3): ")      # Geluid_432Hz.mp3

    convert_audio_440_to_432(input_path, output_path)


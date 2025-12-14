import tkinter as tk
from tkinter import ttk
import sounddevice as sd
import numpy as np
import pyrubberband as rb
import time

#######################
# GLOBAL VARS
#######################
running = False
stream = None
pitch_ratio = 432 / 440
latency_ms = 0
blocksize = 512  # buffer size
samplerate = 44100  # vaste sample rate voor VB-Cable + Speakers

# Device indices (Windows WASAPI)
input_idx = None
output_idx = None

# Zoek VB-Cable input en je speakers
for i, dev in enumerate(sd.query_devices()):
    if "CABLE Output" in dev['name']:
        input_idx = i
    if "Speakers" in dev['name'] and dev['max_output_channels'] > 0:
        output_idx = i

if input_idx is None or output_idx is None:
    raise RuntimeError("❌ Kan input of output device niet vinden.")

#######################
# DSP CALLBACK
#######################
def audio_callback(indata, outdata, frames, time_info, status):
    global pitch_ratio, latency_ms
    start = time.time()

    if status:
        if 'input overflow' in str(status).lower():
            pass # negeer input overflow
        else:
            print(status)

    # Stereo -> mono
    audio = np.mean(indata, axis=1).astype(np.float32)

    try:
        shifted = rb.pitch_shift(audio, samplerate, pitch_ratio)
    except Exception as e:
        print("❌ Rubberband error:", e)
        shifted = audio

    # Mono -> stereo
    shifted = np.repeat(shifted[:, np.newaxis], 2, axis=1)
    outdata[:len(outdata)] = shifted

    # Callback latency
    latency_ms = (time.time() - start) * 1000

#######################
# AUDIO CONTROL
#######################
def start_processing():
    global running, stream, pitch_ratio

    if running:
        return

    running = True

    # Bereken pitch ratio
    selection = tuning_choice.get()
    if selection == "432 Hz":
        pitch_ratio = 432 / 440
    elif selection == "528 Hz":
        pitch_ratio = 528 / 440
    else:
        try:
            pitch_ratio = float(custom_entry.get()) / 440
        except ValueError:
            status_label.config(text="❌ Ongeldige custom Hz")
            running = False
            return

    # Open stream
    try:
        stream = sd.Stream(
            device=(input_idx, output_idx),
            samplerate=samplerate,
            blocksize=blocksize,
            channels=(1, 2),
            dtype='float32',
            callback=audio_callback
        )
        stream.start()
    except Exception as e:
        status_label.config(text=f"❌ Stream error: {e}")
        running = False
        return

    # Disable controls tijdens DSP
    tuning_choice.config(state="disabled")
    custom_entry.config(state="disabled")
    toggle_btn.config(text="⏹ Disable DSP")
    status_label.config(text="🎵 Active (Processing)")

def stop_processing():
    global running, stream
    running = False

    if stream:
        try:
            stream.stop()
            stream.close()
        except Exception as e:
            print("❌ Error closing stream:", e)
        stream = None

    # Enable controls na stop
    tuning_choice.config(state="normal")
    custom_entry.config(state="normal")
    toggle_btn.config(text="▶ Enable DSP")
    status_label.config(text="⛔ Stopped")

#######################
# GUI
#######################
root = tk.Tk()
root.configure(bg="#1e1e1e")
root.title("Real-Time Pitch Shift DSP")
root.geometry("480x400")
root.resizable(False, False)

style = ttk.Style()
style.theme_use("clam")
style.configure("TLabel", background="#1e1e1e", foreground="white")
style.configure("TCombobox", fieldbackground="#2b2b2b", foreground="white")

tk.Label(root, text="Tuning Mode:", bg="#1e1e1e", fg="white").pack(pady=10)
tuning_choice = ttk.Combobox(root, values=["432 Hz", "528 Hz", "Custom"], width=20)
tuning_choice.set("432 Hz")
tuning_choice.pack()

custom_entry = tk.Entry(root)
custom_entry.insert(0, "440")
custom_entry.pack(pady=5)

toggle_btn = tk.Button(root, text="▶ Enable DSP", command=lambda: start_processing() if not running else stop_processing(),
                       font=("Arial", 14), bg="#2196F3", fg="white", width=20)
toggle_btn.pack(pady=20)

status_label = tk.Label(root, text="⛔ Stopped", font=("Arial", 14))
status_label.pack(pady=10)

latency_label = tk.Label(root, text="Latency: 0 ms", font=("Arial", 12))
latency_label.pack()

def update_latency_label():
    latency_label.config(text=f"Latency: {latency_ms:.1f} ms")
    root.after(100, update_latency_label)

update_latency_label()
root.mainloop()
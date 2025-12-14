import tkinter as tk
from tkinter import ttk
import sounddevice as sd
import numpy as np
import pyrubberband as rb
import threading
import time

#######################
# GLOBAL VARS
#######################

running = False
stream = None
pitch_ratio = 432 / 440     # default 432
latency_ms = 0
blocksize = 256             # buffer size, kan 128/256/512 zijn


#######################
# DSP CALLBACK
#######################

def audio_callback(indata, outdata, frames, time_info, status):
    global pitch_ratio, latency_ms

    start = time.time()

    if status:
        print(status)

    # stereo -> mono
    audio = np.mean(indata, axis=1).astype(np.float32)

    try:
        shifted = rb.pitch_shift(audio, samplerate, pitch_ratio, rbargs=["--realtime"])
    except Exception as e:
        print("❌ Rubberband error:", e)
        shifted = audio

    # mono -> stereo
    shifted = np.repeat(shifted[:, np.newaxis], 2, axis=1)

    outdata[:] = shifted[:len(outdata)]

    # Latency measurement
    latency_ms = (time.time() - start) * 1000
    # ⚠️ Echte system latency = callback latency + audio driver latency (+10-20ms)

#####################
# DEVICE HELPER
#####################

def find_device_index(name_substring):
    """Return index of audio device containing given name substring."""
    for idx, dev in enumerate(sd.query_devices()):
        if name_substring.lower() in dev["name"].lower():
            return idx
    return None


######################
# AUDIO CONTROL
######################

def start_processing():
    global running, stream, pitch_ratio, blocksize

    if running:
        return

    running = True

    # Compute pitch ratio based on current setting
    selection = tuning_choice.get()
    if selection == "432 Hz":
        pitch_ratio = 432 / 440
    elif selection == "528 Hz":
        pitch_ratio = 528 / 440
    else:
        try:
            pitch_ratio = float(custom_entry.get()) / 440
        except ValueError:
            status_label.config(text="❌ Invalid custom Hz")
            running = False
            return

    input_idx = 17      # CABLE Output (VB-Audio Virtual Cable) WASAPI
    output_idx = 16     # Speakers (Realtek) WASAPI

    if input_idx is None or output_idx is None:
        status_label.config(text="❌ Audio device is not found")
        running = False
        return

    # Haal samplerates op en update globale variabele
    global samplerate
    input_info = sd.query_devices(input_idx)
    output_info = sd.query_devices(output_idx)
    samplerate = min(input_info["default_samplerate"], output_info["default_samplerate"])

    # Open audio stream
    try:
        stream = sd.Stream(
            device=(input_idx, output_idx),
            samplerate=samplerate,   # match je VB-Cable samplerate
            blocksize=256,
            channels=(1, 2), # input=1, output=2
            dtype='float32',
            callback=audio_callback,
        )
        stream.start()
    except Exception as e:
        status_label.config(text=f"❌ Stream error: {e}")
        running = False
        return

    # Disable controls tijdens DSP
    tuning_choice.config(state="disabled")
    custom_entry.config(state="disabled")

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

    status_label.config(text="⛔ Stopped")


#######################
# GUI UPDATE LOOP
#######################

def update_latency_label():
    latency_label.config(text=f"Latency: {latency_ms:.1f} ms")
    root.after(100, update_latency_label)

def toggle_dsp():
    if running:
        stop_processing()
        toggle_btn.config(text="▶ Enable DSP")
    else:
        start_processing()
        toggle_btn.config(text="⏹ Disable DSP")

#######################
# GUI SETUP
#######################

root = tk.Tk()
root.configure(bg="#1e1e1e")

style = ttk.Style()
style.theme_use("clam")
style.configure("TLabel", background="#1e1e1e", foreground="white")
style.configure("TCombobox", fieldbackground="#2b2b2b", foreground="white")

root.title("Real-Time Pitch Shift DSP (432 / 528 / Custom)")
root.geometry("480x400")
root.resizable(False, False)


# Tuning selector
tk.Label(root, text="Tuning Mode:", bg="#1e1e1e", fg="white").pack(pady=10)

tuning_choice = ttk.Combobox(root, values=["432 Hz", "528 Hz", "Custom"], width=20)
tuning_choice.set("432 Hz")
tuning_choice.pack()

custom_entry = tk.Entry(root)
custom_entry.insert(0, "440") # default
custom_entry.pack(pady=5)

# Toggle DSP button
toggle_btn = tk.Button(
    root,
    text="▶ Enable DSP",
    command=toggle_dsp,
    font=("Arial", 14),
    bg="#2196F3",
    fg="white",
    width=20,
)
toggle_btn.pack(pady=20)

# Status + Latency
status_label = tk.Label(root, text="⛔ Stopped", font=("Arial", 14))
status_label.pack(pady=10)

latency_label = tk.Label(root, text="Latency: 0 ms", font=("Arial", 12))
latency_label.pack()

update_latency_label()

root.mainloop()













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


#######################
# DSP CALLBACK
#######################

def audio_callback(indata, outdata, frames, time_info, status):
    global pitch_ratio, latency_ms

    start = time.time()

    if status:
        print("Status:", status)

    audio = indata[:, 0]

    shifted = rb.pitch_shift(audio, 48000, pitch_ratio)

    # Match output size
    if len(shifted) < len(outdata):
        shifted = np.pad(shifted, (0, len(outdata) - len(shifted)))
    else:
        shifted = shifted[:len(outdata)]

    outdata[:] = shifted.reshape(-1, 1)

    # Latency measurement
    latency_ms = (time.time() - start) * 1000


######################
# AUDIO CONTROL
######################

def start_processing():
    global running, stream, pitch_ratio

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
        pitch_ratio = float(custom_entry.get()) / 440

    # Open audio stream
    stream = sd.Stream(
        device=(input_device_var.get(), output_device_var.get()),
        samplerate=48000,
        blocksize=1024,
        channels=1,
        dtype='float32',
        callback=audio_callback
    )
    stream.start()
    status_label.config(text="🎵 Active (Processing)")

def stop_processing():
    global running, stream
    running = False

    if stream:
        stream.stop()
        stream.close()
        stream = None

    status_label.config(text="⛔ Stopped")


#######################
# GUI UPDATE LOOP
#######################

def update_latency_label():
    latency_label.config(text=f"Latency: {latency_ms:.1f} ms")
    root.after(100, update_latency_label)


#######################
# GUI SETUP
#######################

root = tk.Tk()
root.title("Real-Time Pitch Shift DSP (432 / 528 / Custom)")
root.geometry("480x400")
root.resizable(False, False)

#######################
# Device Selector
#######################
tk.Label(root, text="Input Device (Virtual Cable):").pack(pady=5)

input_devices = [d['name'] for d in sd.query_devices()]
output_devices = input_devices.copy()

input_device_var = tk.StringVar()
output_device_var = tk.StringVar()

input_dropdown = ttk.Combobox(root, textvariable=input_device_var, values=input_devices, width=50)
output_dropdown = ttk.Combobox(root, textvariable=output_device_var, values=output_devices, width=50)

input_dropdown.pack(pady=2)
output_dropdown.pack(pady=2)

########################
# Tuning selector
########################
tk.Label(root, text="Tuning Mode:").pack(pady=10)

tuning_choice = ttk.Combobox(root, values=["432 Hz", "528 Hz", "Custom"], width=20)
tuning_choice.set("432 Hz")
tuning_choice.pack()

custom_entry = tk.Entry(root)
custom_entry.insert(0, "440") # default
custom_entry.pack(pady=5)

######################
# Buttons
######################

start_btn = tk.Button(root, text="Start DSP", command=start_processing, bg="#4CAF50", fg="white")
start_btn.pack(pady=10)

stop_btn = tk.Button(root, text="Stop DSP", command=stop_processing, bg="#F44336", fg="white")
stop_btn.pack(pady=5)

######################
# Status + Latency
######################

status_label = tk.Label(root, text="⛔ Stopped", font=("Arial", 14))
status_label.pack(pady=10)

latency_label = tk.Label(root, text="Latency: 0 ms", font=("Arial", 12))
latency_label.pack()

update_latency_label()

root.mainloop()













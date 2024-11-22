import tkinter as tk
from tkinter import ttk
import numpy as np
import sounddevice as sd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class SineWaveApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Waveform Generator")

        # GUI-Parameter
        self.frequency = tk.DoubleVar(value=440.0)
        self.mod_freq = tk.DoubleVar(value=5.0)
        self.mod_depth = tk.DoubleVar(value=0.5)
        self.volume = tk.DoubleVar(value=0.5)
        self.pan = tk.DoubleVar(value=0.5)
        self.waveform = tk.StringVar(value="sine")
        self.running = False

        self.create_gui()

    def create_gui(self):

        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill="both", expand=True)

        self.control_frame = ttk.Frame(self.main_frame)
        self.control_frame.pack(side="left", fill="y", padx=10, pady=10)

        self.plot_frame = ttk.Frame(self.main_frame)
        self.plot_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        font_large = ("Helvetica", 16)

        ttk.Label(self.control_frame, text="Lautstärke:", font=font_large).pack()
        self.volume_slider = ttk.Scale(self.control_frame, from_=0, to=1, variable=self.volume, orient="horizontal")
        self.volume_slider.pack(fill="x", pady=5)
        self.volume_value_label = ttk.Label(self.control_frame, text="0.5", font=font_large)
        self.volume_value_label.pack()

        ttk.Label(self.control_frame, text="Frequenz (Hz):", font=font_large).pack()
        self.freq_slider = ttk.Scale(self.control_frame, from_=20, to=2000, variable=self.frequency, orient="horizontal")
        self.freq_slider.pack(fill="x", pady=5)
        self.freq_value_label = ttk.Label(self.control_frame, text="440.0 Hz", font=font_large)
        self.freq_value_label.pack()

        ttk.Label(self.control_frame, text="Modulationsfrequenz (Hz):", font=font_large).pack()
        self.mod_freq_slider = ttk.Scale(self.control_frame, from_=0.1, to=50, variable=self.mod_freq, orient="horizontal")
        self.mod_freq_slider.pack(fill="x", pady=5)
        self.mod_freq_value_label = ttk.Label(self.control_frame, text="5.0 Hz", font=font_large)
        self.mod_freq_value_label.pack()

        ttk.Label(self.control_frame, text="Modulationstiefe:", font=font_large).pack()
        self.mod_depth_slider = ttk.Scale(self.control_frame, from_=0, to=1, variable=self.mod_depth, orient="horizontal")
        self.mod_depth_slider.pack(fill="x", pady=5)
        self.mod_depth_value_label = ttk.Label(self.control_frame, text="0.5", font=font_large)
        self.mod_depth_value_label.pack()

        ttk.Label(self.control_frame, text="Panning (L-R):", font=font_large).pack()
        self.pan_slider = ttk.Scale(self.control_frame, from_=0, to=1, variable=self.pan, orient="horizontal")
        self.pan_slider.pack(fill="x", pady=5)
        self.pan_value_label = ttk.Label(self.control_frame, text="0.5", font=font_large)
        self.pan_value_label.pack()

        ttk.Label(self.control_frame, text="Wellenform:", font=font_large).pack()
        self.waveform_combobox = ttk.Combobox(self.control_frame, textvariable=self.waveform, values=["sine", "square", "triangle", "sawtooth"], state='readonly')
        self.waveform_combobox.option_add('*TCombobox*Listbox.font', font_large)
        self.waveform_combobox.pack(fill="x", pady=5)

        self.start_button = ttk.Button(self.control_frame, text="Start", command=self.start, style='TButton')
        self.start_button.pack(side="left", padx=20, pady=20)
        self.start_button.config(width=10)

        self.stop_button = ttk.Button(self.control_frame, text="Stop", command=self.stop, style='TButton')
        self.stop_button.pack(side="right", padx=20, pady=20)
        self.stop_button.config(width=10)

        self.fig, self.ax = plt.subplots()
        self.line, = self.ax.plot([], [])
        self.ax.set_ylim(-1.5, 1.5)
        self.ax.set_xlim(0, 0.02)
        self.ax.set_xlabel("Zeit (s)", fontsize=14)
        self.ax.set_ylabel("Amplitude", fontsize=14)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.plot_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, pady=10)

        self.update_labels()
        self.update_plot()

    def update_labels(self):
        self.volume_value_label.config(text=f"{self.volume.get():.2f}")
        self.freq_value_label.config(text=f"{self.frequency.get():.1f} Hz")
        self.mod_freq_value_label.config(text=f"{self.mod_freq.get():.1f} Hz")
        self.mod_depth_value_label.config(text=f"{self.mod_depth.get():.2f}")
        self.pan_value_label.config(text=f"{self.pan.get():.2f}")
        self.root.after(50, self.update_labels)

    def update_plot(self):
        fs = 44100
        t = np.linspace(0, 0.02, int(0.02 * fs), endpoint=False)

        freq = self.frequency.get()
        mod_freq = self.mod_freq.get()
        mod_depth = self.mod_depth.get()
        volume = self.volume.get()

        modulator = 1 + mod_depth * np.sin(2 * np.pi * mod_freq * t)
        waveform = self.waveform.get()

        if waveform == "sine":
            wave = np.sin(2 * np.pi * freq * t) * modulator
        elif waveform == "square":
            wave = np.sign(np.sin(2 * np.pi * freq * t)) * modulator
        elif waveform == "triangle":
            wave = 2 * np.abs(2 * ((t * freq) % 1) - 1) - 1
            wave = wave * modulator
        elif waveform == "sawtooth":
            wave = 2 * (t * freq % 1) - 1
            wave = wave * modulator
        else:
            wave = np.sin(2 * np.pi * freq * t) * modulator

        self.line.set_data(t, wave)
        self.ax.set_xlim(t[0], t[-1])
        self.canvas.draw()

        self.root.after(50, self.update_plot)

    def on_waveform_change(self):
        if self.running:
            self.stop()
            self.start()

    def audio_callback(self, outdata, frames, time, status):
        if not self.running:
            outdata[:] = np.zeros((frames, 2))
            return

        fs = 44100
        t = (np.arange(frames) + self.sample_offset) / fs
        self.sample_offset += frames

        freq = self.frequency.get()
        mod_freq = self.mod_freq.get()
        mod_depth = self.mod_depth.get()
        pan = self.pan.get()
        volume = self.volume.get()

        modulator = 1 + mod_depth * np.sin(2 * np.pi * mod_freq * t)
        waveform = self.waveform.get()

        if waveform == "sine":
            wave = np.sin(2 * np.pi * freq * t) * modulator
        elif waveform == "square":
            wave = np.sign(np.sin(2 * np.pi * freq * t)) * modulator
        elif waveform == "triangle":
            wave = 2 * np.abs(2 * ((t * freq) % 1) - 1) - 1
            wave = wave * modulator
        elif waveform == "sawtooth":
            wave = 2 * (t * freq % 1) - 1
            wave = wave * modulator
        else:
            wave = np.sin(2 * np.pi * freq * t) * modulator

        left = wave * (1 - pan) * volume
        right = wave * pan * volume
        stereo_wave = np.vstack((left, right)).T

        # Audioausgabe
        outdata[:] = stereo_wave

    def start(self):
        if not self.running:
            self.running = True
            self.sample_offset = 0
            self.stream = sd.OutputStream(
                samplerate=44100,
                channels=2,
                callback=self.audio_callback,
                blocksize=1024
            )
            self.stream.start()

    def stop(self):
        if self.running:
            self.running = False
            self.stream.stop()
            self.stream.close()

root = tk.Tk()
app = SineWaveApp(root)
root.mainloop()

from PySide6 import QtWidgets, QtCore
import numpy as np
import sounddevice as sd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

class SineWaveApp(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Waveform Generator")

        # GUI Parameters
        self.frequency = 440.0
        self.mod_freq = 5.0
        self.mod_depth = 0.5
        self.volume = 0.5
        self.pan = 0.5
        self.waveform = "sine"
        self.running = False

        self.init_ui()

    def init_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)

        control_layout = QtWidgets.QHBoxLayout()
        slider_layout = QtWidgets.QFormLayout()
        dial_layout = QtWidgets.QHBoxLayout()
        self.freq_slider = self.create_slider(20, 2000, self.frequency, "Frequenz (Hz)")
        self.freq_label = QtWidgets.QLabel(f"{self.frequency} Hz")
        self.freq_slider.valueChanged.connect(lambda: self.freq_label.setText(f"{self.freq_slider.value()} Hz"))
        freq_layout = QtWidgets.QHBoxLayout()
        freq_layout.addWidget(self.freq_label)
        freq_layout.addWidget(self.freq_slider)
        slider_layout.addRow("Frequenz (Hz):", freq_layout)

        self.volume_dial = QtWidgets.QDial()
        self.volume_dial.setRange(0, 100)
        self.volume_dial.setValue(int(self.volume * 100))
        self.volume_label = QtWidgets.QLabel(f"{self.volume:.2f}")
        self.volume_dial.valueChanged.connect(lambda: self.volume_label.setText(f"{self.volume_dial.value() / 100:.2f}"))
        self.volume_dial.valueChanged.connect(self.update_plot)
        volume_layout = QtWidgets.QVBoxLayout()
        volume_label = QtWidgets.QLabel("Lautstärke:")
        volume_layout.addWidget(volume_label)
        volume_layout.addWidget(self.volume_label)
        volume_layout.addWidget(self.volume_dial)
        dial_layout.addLayout(volume_layout)

        self.mod_freq_slider = self.create_slider(0.1, 50, self.mod_freq, "Modulationsfrequenz (Hz)", decimals=1)
        self.mod_freq_label = QtWidgets.QLabel(f"{self.mod_freq} Hz")
        self.mod_freq_slider.valueChanged.connect(lambda: self.mod_freq_label.setText(f"{self.mod_freq_slider.value() / 10:.1f} Hz"))
        mod_freq_layout = QtWidgets.QHBoxLayout()
        mod_freq_layout.addWidget(self.mod_freq_label)
        mod_freq_layout.addWidget(self.mod_freq_slider)
        slider_layout.addRow("Modulationsfrequenz (Hz):", mod_freq_layout)

        self.mod_depth_slider = self.create_slider(0, 1, self.mod_depth, "Modulationstiefe", decimals=2)
        self.mod_depth_label = QtWidgets.QLabel(f"{self.mod_depth:.2f}")
        self.mod_depth_slider.valueChanged.connect(lambda: self.mod_depth_label.setText(f"{self.mod_depth_slider.value() / 100:.2f}"))
        mod_depth_layout = QtWidgets.QHBoxLayout()
        mod_depth_layout.addWidget(self.mod_depth_label)
        mod_depth_layout.addWidget(self.mod_depth_slider)
        slider_layout.addRow("Modulationstiefe:", mod_depth_layout)

        self.pan_dial = QtWidgets.QDial()
        self.pan_dial.setRange(0, 100)
        self.pan_dial.setValue(int(self.pan * 100))
        self.pan_label = QtWidgets.QLabel(f"{self.pan:.2f}")
        self.pan_dial.valueChanged.connect(lambda: self.pan_label.setText(f"{self.pan_dial.value() / 100:.2f}"))
        self.pan_dial.valueChanged.connect(self.update_plot)
        pan_layout = QtWidgets.QVBoxLayout()
        pan_label = QtWidgets.QLabel("Panning (L-R):")
        pan_layout.addWidget(pan_label)
        pan_layout.addWidget(self.pan_label)
        pan_layout.addWidget(self.pan_dial)
        dial_layout.addLayout(pan_layout)

        self.waveform_buttons = QtWidgets.QButtonGroup(self)
        self.waveform_layout = QtWidgets.QHBoxLayout()
        for waveform in ["sine", "square", "triangle", "sawtooth"]:
            button = QtWidgets.QRadioButton(waveform)
            if waveform == "sine":
                button.setChecked(True)
            self.waveform_buttons.addButton(button)
            self.waveform_layout.addWidget(button)
        self.waveform_buttons.buttonClicked.connect(lambda: [self.on_waveform_change(), self.update_plot()])
        slider_layout.addRow("Wellenform:", self.waveform_layout)

        # Start and Stop buttons
        button_layout = QtWidgets.QHBoxLayout()
        self.start_button = QtWidgets.QPushButton()
        self.start_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_MediaPlay))
        self.start_button.clicked.connect(self.start)
        button_layout.addWidget(self.start_button)

        self.stop_button = QtWidgets.QPushButton()
        self.stop_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_MediaStop))
        self.stop_button.clicked.connect(self.stop)
        button_layout.addWidget(self.stop_button)

        main_layout.addLayout(control_layout)
        control_layout.addLayout(slider_layout)
        control_layout.addLayout(dial_layout)
        main_layout.addLayout(button_layout)

        # Plotting
        self.fig, self.ax = plt.subplots()
        self.canvas = FigureCanvas(self.fig)
        self.line, = self.ax.plot([], [])
        self.ax.set_ylim(-1.5, 1.5)
        self.ax.set_xlim(0, 0.02)
        self.ax.set_xlabel("Zeit (s)")
        self.ax.set_ylabel("Amplitude")
        main_layout.addWidget(self.canvas)

        self.setLayout(main_layout)
        self.update_plot()

    def create_slider(self, min_val, max_val, initial_value, name, decimals=0):
        slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        slider.setRange(int(min_val * 10**decimals), int(max_val * 10**decimals))
        slider.setValue(int(initial_value * 10**decimals))
        slider.setSingleStep(1)
        slider.valueChanged.connect(self.update_plot)
        return slider

    def update_plot(self):
        fs = 44100
        t = np.linspace(0, 0.02, int(0.02 * fs), endpoint=False)

        freq = self.freq_slider.value()
        mod_freq = self.mod_freq_slider.value() / 10
        mod_depth = self.mod_depth_slider.value() / 100
        volume = self.volume_dial.value() / 100

        modulator = 1 + mod_depth * np.sin(2 * np.pi * mod_freq * t)
        waveform = self.waveform_buttons.checkedButton().text()

        if waveform == "sine":
            wave = np.sin(2 * np.pi * freq * t) * modulator * volume
        elif waveform == "square":
            wave = np.sign(np.sin(2 * np.pi * freq * t)) * modulator * volume
        elif waveform == "triangle":
            wave = (2 * np.abs(2 * ((t * freq) % 1) - 1) - 1) * modulator * volume
        elif waveform == "sawtooth":
            wave = (2 * (t * freq % 1) - 1) * modulator * volume
        else:
            wave = np.sin(2 * np.pi * freq * t) * modulator * volume

        self.line.set_data(t, wave)
        self.ax.set_xlim(t[0], t[-1])
        self.canvas.draw()

    def audio_callback(self, outdata, frames, time, status):
        if not self.running:
            outdata[:] = np.zeros((frames, 2))
            return

        fs = 44100
        t = (np.arange(frames) + self.sample_offset) / fs
        self.sample_offset += frames

        freq = self.freq_slider.value()
        mod_freq = self.mod_freq_slider.value() / 10
        mod_depth = self.mod_depth_slider.value() / 100
        pan = self.pan_dial.value() / 100
        volume = self.volume_dial.value() / 100

        modulator = 1 + mod_depth * np.sin(2 * np.pi * mod_freq * t)
        waveform = self.waveform_buttons.checkedButton().text()

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

    def on_waveform_change(self):
        if self.running:
            self.stop()
            self.start()

if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    window = SineWaveApp()
    window.show()
    app.exec()

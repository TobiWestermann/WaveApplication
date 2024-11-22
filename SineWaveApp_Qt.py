from PySide6 import QtWidgets, QtCore
import numpy as np
import sounddevice as sd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

class SineWaveApp(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dual Waveform Generator")

        # parameters 1
        self.frequency_1 = 440.0
        self.mod_freq_1 = 5.0
        self.mod_depth_1 = 0.5
        self.volume_1 = 0.5
        self.pan_1 = 0.5
        self.waveform_1 = "sine"

        # parameters 2
        self.frequency_2 = 220.0
        self.mod_freq_2 = 5.0
        self.mod_depth_2 = 0.5
        self.volume_2 = 0.5
        self.pan_2 = 0.5
        self.waveform_2 = "sine"

        self.running = False

        self.init_ui()

    def init_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)

        # control layouts
        self.signal_controls = {}
        controls_layout = QtWidgets.QHBoxLayout()
        self.add_signal_controls(controls_layout, 1)
        self.add_signal_controls(controls_layout, 2)
        main_layout.addLayout(controls_layout)

        # buttons layout
        button_layout = QtWidgets.QHBoxLayout()
        self.start_button = QtWidgets.QPushButton()
        self.start_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_MediaPlay))
        self.start_button.clicked.connect(self.start)
        button_layout.addWidget(self.start_button)

        self.stop_button = QtWidgets.QPushButton()
        self.stop_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_MediaStop))
        self.stop_button.clicked.connect(self.stop)
        button_layout.addWidget(self.stop_button)

        main_layout.addLayout(button_layout)

        # plot Layout
        self.fig, self.ax = plt.subplots()
        self.canvas = FigureCanvas(self.fig)
        self.line, = self.ax.plot([], [])
        self.ax.set_ylim(-1.5, 1.5)
        self.ax.set_xlim(0, 0.02)
        self.ax.set_xlabel("Time in s")
        self.ax.set_ylabel("Amplitude")
        main_layout.addWidget(self.canvas)

        self.setLayout(main_layout)
        self.update_plot()

    def add_signal_controls(self, layout, signal_number):
        control_group = QtWidgets.QGroupBox(f"Signal {signal_number} Einstellungen")
        control_layout = QtWidgets.QFormLayout()

        self.signal_controls[signal_number] = {}

        # freq Slider
        freq_slider = self.create_slider(20, 2000, getattr(self, f'frequency_{signal_number}'), decimals=0)
        freq_label = QtWidgets.QLabel(f"{getattr(self, f'frequency_{signal_number}')} Hz")
        freq_slider.valueChanged.connect(lambda value, lbl=freq_label: lbl.setText(f"{value} Hz"))
        freq_slider.valueChanged.connect(self.update_plot)
        control_layout.addRow(f"Frequenz {signal_number} (Hz):", self.wrap_widget_with_label(freq_label, freq_slider))
        self.signal_controls[signal_number]['freq_slider'] = freq_slider

        # mod freq Slider
        mod_freq_slider = self.create_slider(0.1, 50, getattr(self, f'mod_freq_{signal_number}'), decimals=1)
        mod_freq_label = QtWidgets.QLabel(f"{getattr(self, f'mod_freq_{signal_number}')} Hz")
        mod_freq_slider.valueChanged.connect(lambda value, lbl=mod_freq_label: lbl.setText(f"{value / 10:.1f} Hz"))
        mod_freq_slider.valueChanged.connect(self.update_plot)
        control_layout.addRow(f"Modulationsfrequenz {signal_number} (Hz):", self.wrap_widget_with_label(mod_freq_label, mod_freq_slider))
        self.signal_controls[signal_number]['mod_freq_slider'] = mod_freq_slider

        # mod_depth Slider
        mod_depth_slider = self.create_slider(0, 1, getattr(self, f'mod_depth_{signal_number}'), decimals=2)
        mod_depth_label = QtWidgets.QLabel(f"{getattr(self, f'mod_depth_{signal_number}'):.2f}")
        mod_depth_slider.valueChanged.connect(lambda value, lbl=mod_depth_label: lbl.setText(f"{value / 100:.2f}"))
        mod_depth_slider.valueChanged.connect(self.update_plot)
        control_layout.addRow(f"Modulationstiefe {signal_number}:", self.wrap_widget_with_label(mod_depth_label, mod_depth_slider))
        self.signal_controls[signal_number]['mod_depth_slider'] = mod_depth_slider

        # volume Dial
        volume_dial = QtWidgets.QDial()
        volume_dial.setRange(0, 100)
        volume_dial.setValue(int(getattr(self, f'volume_{signal_number}') * 100))
        volume_label = QtWidgets.QLabel(f"{getattr(self, f'volume_{signal_number}'):.2f}")
        volume_dial.valueChanged.connect(lambda value, lbl=volume_label: lbl.setText(f"{value / 100:.2f}"))
        volume_dial.valueChanged.connect(self.update_plot)
        control_layout.addRow(f"Lautstärke {signal_number}:", self.wrap_widget_with_label(volume_label, volume_dial))
        self.signal_controls[signal_number]['volume_dial'] = volume_dial

        # pan Dial
        pan_dial = QtWidgets.QDial()
        pan_dial.setRange(0, 100)
        pan_dial.setValue(int(getattr(self, f'pan_{signal_number}') * 100))
        pan_label = QtWidgets.QLabel(f"{getattr(self, f'pan_{signal_number}'):.2f}")
        pan_dial.valueChanged.connect(lambda value, lbl=pan_label: lbl.setText(f"{value / 100:.2f}"))
        pan_dial.valueChanged.connect(self.update_plot)
        control_layout.addRow(f"Panning {signal_number} (L-R):", self.wrap_widget_with_label(pan_label, pan_dial))
        self.signal_controls[signal_number]['pan_dial'] = pan_dial

        # waveform Selection
        waveform_buttons = QtWidgets.QButtonGroup(self)
        waveform_layout = QtWidgets.QHBoxLayout()
        for waveform in ["sine", "square", "triangle", "sawtooth"]:
            button = QtWidgets.QRadioButton(waveform)
            if waveform == "sine":
                button.setChecked(True)
            waveform_buttons.addButton(button)
            waveform_layout.addWidget(button)
        waveform_buttons.buttonClicked.connect(self.update_plot)
        control_layout.addRow(f"Wellenform {signal_number}:", waveform_layout)
        self.signal_controls[signal_number]['waveform_buttons'] = waveform_buttons

        control_group.setLayout(control_layout)
        layout.addWidget(control_group)

    def wrap_widget_with_label(self, label, widget):
        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(label)
        layout.addWidget(widget)
        return layout

    def create_slider(self, min_val, max_val, initial_value, decimals=0):
        slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        slider.setRange(int(min_val * 10**decimals), int(max_val * 10**decimals))
        slider.setValue(int(initial_value * 10**decimals))
        slider.setSingleStep(1)
        slider.valueChanged.connect(self.update_plot)
        return slider

    def update_plot(self):
        fs = 48000
        t = np.linspace(0, 0.02, int(0.02 * fs), endpoint=False)

        combined_wave = np.zeros_like(t)

        for signal_number in [1, 2]:
            controls = self.signal_controls[signal_number]
            freq = controls['freq_slider'].value()
            mod_freq = controls['mod_freq_slider'].value() / 10
            mod_depth = controls['mod_depth_slider'].value() / 100
            volume = controls['volume_dial'].value() / 100
            waveform = controls['waveform_buttons'].checkedButton().text()

            modulator = 1 + mod_depth * np.sin(2 * np.pi * mod_freq * t)
            if waveform == "sine":
                wave = np.sin(2 * np.pi * freq * t) * modulator
            elif waveform == "square":
                wave = np.sign(np.sin(2 * np.pi * freq * t)) * modulator
            elif waveform == "triangle":
                wave = (2 * np.abs(2 * ((t * freq) % 1) - 1) - 1) * modulator
            elif waveform == "sawtooth":
                wave = (2 * (t * freq % 1) - 1) * modulator
            else:
                wave = np.sin(2 * np.pi * freq * t) * modulator

            wave *= volume
            combined_wave += wave

        combined_wave = np.clip(combined_wave, -1, 1)

        self.line.set_data(t, combined_wave)
        self.ax.set_xlim(t[0], t[-1])
        self.canvas.draw()

    def audio_callback(self, outdata, frames, time, status):
        if not self.running:
            outdata[:] = np.zeros((frames, 2))
            return

        fs = 48000
        t = (np.arange(frames) + self.sample_offset) / fs
        self.sample_offset += frames

        left_channel = np.zeros_like(t)
        right_channel = np.zeros_like(t)

        for signal_number in [1, 2]:
            controls = self.signal_controls[signal_number]
            freq = controls['freq_slider'].value()
            mod_freq = controls['mod_freq_slider'].value() / 10
            mod_depth = controls['mod_depth_slider'].value() / 100
            volume = controls['volume_dial'].value() / 100
            pan = controls['pan_dial'].value() / 100
            waveform = controls['waveform_buttons'].checkedButton().text()

            modulator = 1 + mod_depth * np.sin(2 * np.pi * mod_freq * t)
            if waveform == "sine":
                wave = np.sin(2 * np.pi * freq * t) * modulator
            elif waveform == "square":
                wave = np.sign(np.sin(2 * np.pi * freq * t)) * modulator
            elif waveform == "triangle":
                wave = (2 * np.abs(2 * ((t * freq) % 1) - 1) - 1) * modulator
            elif waveform == "sawtooth":
                wave = (2 * (t * freq % 1) - 1) * modulator
            else:
                wave = np.sin(2 * np.pi * freq * t) * modulator

            wave *= volume
            left_channel += wave * (1 - pan)
            right_channel += wave * pan

        left_channel = np.clip(left_channel, -1, 1)
        right_channel = np.clip(right_channel, -1, 1)

        stereo_wave = np.vstack((left_channel, right_channel)).T

        outdata[:] = stereo_wave

    def start(self):
        if not self.running:
            self.running = True
            self.sample_offset = 0
            self.stream = sd.OutputStream(
                samplerate=48000,
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

if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    window = SineWaveApp()
    window.show()
    app.exec()

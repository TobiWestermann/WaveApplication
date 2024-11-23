from PySide6 import QtWidgets, QtCore, QtGui
import numpy as np
import sounddevice as sd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas


class SineWaveApp(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Waveform Generator with Tabs")
        self.sampling_rate = 48000
        self.max_signals = 5
        self.signal_controls = {}
        self.current_signal_count = 0
        self.running = False
        self.time_offset = 0

        self.init_ui()

    def init_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)

        # Tab Widget für Signale
        self.tab_widget = QtWidgets.QTabWidget()
        main_layout.addWidget(self.tab_widget)

        # Add Signal Button
        add_signal_button = QtWidgets.QPushButton("Add Signal")
        add_signal_button.clicked.connect(self.add_new_signal_tab)
        main_layout.addWidget(add_signal_button)

        # Playback Controls
        button_layout = QtWidgets.QHBoxLayout()
        self.start_button = QtWidgets.QPushButton("Start")
        self.start_button.clicked.connect(self.start)
        button_layout.addWidget(self.start_button)

        self.stop_button = QtWidgets.QPushButton("Stop")
        self.stop_button.clicked.connect(self.stop)
        button_layout.addWidget(self.stop_button)

        main_layout.addLayout(button_layout)

        # Plot für Wellenformen
        self.fig, self.ax = plt.subplots()
        self.canvas = FigureCanvas(self.fig)
        self.line, = self.ax.plot([], [])
        self.ax.set_ylim(-1.5, 1.5)
        self.ax.set_xlim(0, 0.05)
        self.ax.set_xlabel("Time in s")
        self.ax.set_ylabel("Amplitude")
        main_layout.addWidget(self.canvas)

        self.setLayout(main_layout)

    def add_new_signal_tab(self):
        if self.current_signal_count < self.max_signals:
            self.current_signal_count += 1
            signal_number = self.current_signal_count

            tab = QtWidgets.QWidget()
            layout = QtWidgets.QVBoxLayout(tab)

            # Signal Controls
            signal_group = QtWidgets.QGroupBox(f"Signal {signal_number} Settings")
            form_layout = QtWidgets.QFormLayout(signal_group)

            # Frequency Control
            freq_label = QtWidgets.QLabel("Frequency:")
            freq_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
            freq_slider.setRange(20, 20000)
            freq_slider.setValue(440)
            freq_spinbox = QtWidgets.QSpinBox()
            freq_spinbox.setRange(20, 20000)
            freq_spinbox.setValue(440)

            freq_slider.valueChanged.connect(freq_spinbox.setValue)
            freq_spinbox.valueChanged.connect(freq_slider.setValue)

            form_layout.addRow(freq_label, self.wrap_widget_with_slider_and_spinbox(freq_slider, freq_spinbox))

            # Volume Control
            vol_label = QtWidgets.QLabel("Volume:")
            vol_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
            vol_slider.setRange(0, 100)
            vol_slider.setValue(50)

            form_layout.addRow(vol_label, vol_slider)

            # Modulation Depth
            mod_label = QtWidgets.QLabel("Mod Depth:")
            mod_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
            mod_slider.setRange(0, 100)
            mod_slider.setValue(50)

            form_layout.addRow(mod_label, mod_slider)

            # Mute Button
            mute_button = QtWidgets.QPushButton("Mute")
            mute_button.setCheckable(True)
            form_layout.addRow("Mute:", mute_button)

            layout.addWidget(signal_group)
            tab.setLayout(layout)

            # Save controls
            self.signal_controls[signal_number] = {
                "freq_slider": freq_slider,
                "vol_slider": vol_slider,
                "mod_slider": mod_slider,
                "mute_button": mute_button,
            }

            # Add tab
            self.tab_widget.addTab(tab, f"Signal {signal_number}")
        else:
            QtWidgets.QMessageBox.warning(self, "Limit reached", "Maximum number of signals reached!")

    def wrap_widget_with_slider_and_spinbox(self, slider, spinbox):
        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(slider)
        layout.addWidget(spinbox)
        container = QtWidgets.QWidget()
        container.setLayout(layout)
        return container

    def start(self):
        if not self.running:
            self.running = True
            self.stream = sd.OutputStream(
                samplerate=self.sampling_rate,
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

    def audio_callback(self, outdata, frames, time, status):
        fs = self.sampling_rate
        t = np.linspace(0, frames / fs, frames, endpoint=False)
        combined_wave = np.zeros(frames)

        for signal_number, controls in self.signal_controls.items():
            if controls["mute_button"].isChecked():
                continue

            freq = controls["freq_slider"].value()
            volume = controls["vol_slider"].value() / 100.0
            mod_depth = controls["mod_slider"].value() / 100.0

            modulator = 1 + mod_depth * np.sin(2 * np.pi * 5 * t)  # Modulationsfrequenz = 5 Hz
            wave = np.sin(2 * np.pi * freq * t) * modulator * volume
            combined_wave += wave

        combined_wave = np.clip(combined_wave, -1, 1)
        outdata[:, 0] = combined_wave
        outdata[:, 1] = combined_wave

    def update_plot(self):
        fs = self.sampling_rate
        t = np.linspace(0, 0.05, int(0.05 * fs), endpoint=False)
        combined_wave = np.zeros_like(t)

        for signal_number, controls in self.signal_controls.items():
            if controls["mute_button"].isChecked():
                continue

            freq = controls["freq_slider"].value()
            volume = controls["vol_slider"].value() / 100.0
            mod_depth = controls["mod_slider"].value() / 100.0

            modulator = 1 + mod_depth * np.sin(2 * np.pi * 5 * t)
            wave = np.sin(2 * np.pi * freq * t) * modulator * volume
            combined_wave += wave

        combined_wave = np.clip(combined_wave, -1, 1)
        self.line.set_data(t, combined_wave)
        self.ax.set_xlim(t[0], t[-1])
        self.canvas.draw()


if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    window = SineWaveApp()
    window.show()
    app.exec()

from PySide6 import QtWidgets, QtCore, QtGui
import numpy as np
import sounddevice as sd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import time as pytime

class SineWaveApp(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dual Waveform Generator")

        self.sampling_rate = 48000

        # paramters 1
        self.frequency_1 = 440.0
        self.mod_freq_1 = 5.0
        self.mod_depth_1 = 0.5
        self.volume_1 = 0.5
        self.pan_1 = 0.5
        self.waveform_1 = "sine"
        self.mute_1 = False

        # parameters 2
        self.frequency_2 = 220.0
        self.mod_freq_2 = 5.0
        self.mod_depth_2 = 0.5
        self.volume_2 = 0.5
        self.pan_2 = 0.5
        self.waveform_2 = "sine"
        self.mute_2 = False

        self.running = False
        self.time_offset = 0
        self.scrolling_plot = False  # fixed plot default
        self.last_callback_time = None  # For latency measurement

        self.init_ui()

    def init_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)

        self.setStyleSheet("""
            background-color: #2b2b2b;
            color: #f0f0f0;
            QSlider::groove:horizontal { background: #444; }
            QSlider::handle:horizontal { background: #00bcd4; }
            QPushButton { background-color: #444; border: none; color: #00bcd4; }
            QPushButton#playButton, QPushButton#stopButton { color: #ffffff; }
            QGroupBox { border: 1px solid #00bcd4; margin-top: 10px; }
            QLabel { color: #f0f0f0; }
            QCheckBox { color: #f0f0f0; }
        """)

        # control layouts
        self.signal_controls = {}
        controls_layout = QtWidgets.QHBoxLayout()
        self.add_signal_controls(controls_layout, 1)
        self.add_signal_controls(controls_layout, 2)
        main_layout.addLayout(controls_layout)

        # buttons layout
        button_layout = QtWidgets.QHBoxLayout()
        self.start_button = QtWidgets.QPushButton()
        self.start_button.setObjectName("playButton")
        play_icon = self.style().standardIcon(QtWidgets.QStyle.SP_MediaPlay)
        play_pixmap = play_icon.pixmap(48, 48)
        painter = QtGui.QPainter(play_pixmap)
        painter.setCompositionMode(QtGui.QPainter.CompositionMode_SourceIn)
        painter.fillRect(play_pixmap.rect(), QtGui.QColor(255, 255, 255))
        painter.end()
        self.start_button.setIcon(QtGui.QIcon(play_pixmap))
        self.start_button.setToolTip("Start audio playback")
        self.start_button.clicked.connect(self.start)
        button_layout.addWidget(self.start_button)

        self.stop_button = QtWidgets.QPushButton()
        self.stop_button.setObjectName("stopButton")
        stop_icon = self.style().standardIcon(QtWidgets.QStyle.SP_MediaStop)
        stop_pixmap = stop_icon.pixmap(48, 48)
        painter = QtGui.QPainter(stop_pixmap)
        painter.setCompositionMode(QtGui.QPainter.CompositionMode_SourceIn)
        painter.fillRect(stop_pixmap.rect(), QtGui.QColor(255, 255, 255))
        painter.end()
        self.stop_button.setIcon(QtGui.QIcon(stop_pixmap))
        self.stop_button.setToolTip("Stop audio playback")
        self.stop_button.clicked.connect(self.stop)
        button_layout.addWidget(self.stop_button)

        self.toggle_plot_button = QtWidgets.QPushButton("Toggle Plot Mode")
        self.toggle_plot_button.setToolTip("Toggle between scrolling and fixed plot modes")
        self.toggle_plot_button.clicked.connect(self.toggle_plot_mode)
        button_layout.addWidget(self.toggle_plot_button)

        main_layout.addLayout(button_layout)

        # plot Layout
        self.fig, self.ax = plt.subplots()
        self.canvas = FigureCanvas(self.fig)
        self.line, = self.ax.plot([], [])
        self.ax.set_ylim(-1.5, 1.5)
        self.ax.set_xlim(0, 0.05)
        self.ax.set_xlabel("Time in s")
        self.ax.set_ylabel("Amplitude")
        main_layout.addWidget(self.canvas)

        # Latency label
        self.latency_label = QtWidgets.QLabel("Callback latency: N/A")
        main_layout.addWidget(self.latency_label)

        self.setLayout(main_layout)

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(30)  

    def add_signal_controls(self, layout, signal_number):
        control_group = QtWidgets.QGroupBox(f"Signal {signal_number} Einstellungen")
        control_layout = QtWidgets.QFormLayout()

        self.signal_controls[signal_number] = {}

        # Frequency Slider + SpinBox
        freq_slider = self.create_slider(20, 20000, getattr(self, f'frequency_{signal_number}'), decimals=0)
        freq_spinbox = QtWidgets.QSpinBox()
        freq_spinbox.setRange(20, 20000)
        freq_spinbox.setValue(int(getattr(self, f'frequency_{signal_number}')))
        freq_spinbox.setFixedWidth(80)
        freq_slider.setToolTip("Adjust the frequency of the signal")
        freq_spinbox.setToolTip("Set the frequency of the signal")
        freq_slider.valueChanged.connect(lambda value: freq_spinbox.setValue(value))
        freq_spinbox.valueChanged.connect(lambda value: freq_slider.setValue(value))
        freq_spinbox.valueChanged.connect(self.update_plot)
        control_layout.addRow(f"Frequenz {signal_number} (Hz):", self.wrap_widget_with_slider_and_spinbox(freq_slider, freq_spinbox))
        self.signal_controls[signal_number]['freq_slider'] = freq_slider

        # mod freq slider + SpinBox
        mod_freq_slider = self.create_slider(1, 500, getattr(self, f'mod_freq_{signal_number}'), decimals=1)
        mod_freq_spinbox = QtWidgets.QDoubleSpinBox()
        mod_freq_spinbox.setRange(0.1, 50.0)
        mod_freq_spinbox.setSingleStep(0.1)
        mod_freq_spinbox.setDecimals(1)
        mod_freq_spinbox.setFixedWidth(80)
        mod_freq_spinbox.setValue(getattr(self, f'mod_freq_{signal_number}'))
        mod_freq_slider.setToolTip("Adjust the modulation frequency of the signal")
        mod_freq_spinbox.setToolTip("Set the modulation frequency of the signal")
        mod_freq_slider.valueChanged.connect(lambda value: mod_freq_spinbox.setValue(value / 10))
        mod_freq_spinbox.valueChanged.connect(lambda value: mod_freq_slider.setValue(int(value * 10)))
        mod_freq_spinbox.valueChanged.connect(self.update_plot)
        control_layout.addRow(f"Modulationsfrequenz {signal_number} (Hz):", self.wrap_widget_with_slider_and_spinbox(mod_freq_slider, mod_freq_spinbox))
        self.signal_controls[signal_number]['mod_freq_slider'] = mod_freq_slider

        # mod depth slider + SpinBox
        mod_depth_slider = self.create_slider(0, 100, getattr(self, f'mod_depth_{signal_number}') * 100, decimals=0)
        mod_depth_spinbox = QtWidgets.QDoubleSpinBox()
        mod_depth_spinbox.setRange(0.0, 1.0)
        mod_depth_spinbox.setSingleStep(0.01)
        mod_depth_spinbox.setDecimals(2)
        mod_depth_spinbox.setFixedWidth(80)
        mod_depth_spinbox.setValue(getattr(self, f'mod_depth_{signal_number}'))
        mod_depth_slider.setToolTip("Adjust the modulation depth of the signal")
        mod_depth_spinbox.setToolTip("Set the modulation depth of the signal")
        mod_depth_slider.valueChanged.connect(lambda value: mod_depth_spinbox.setValue(value / 100))
        mod_depth_spinbox.valueChanged.connect(lambda value: mod_depth_slider.setValue(int(value * 100)))
        mod_depth_spinbox.valueChanged.connect(self.update_plot)
        control_layout.addRow(f"Modulationstiefe {signal_number}:", self.wrap_widget_with_slider_and_spinbox(mod_depth_slider, mod_depth_spinbox))
        self.signal_controls[signal_number]['mod_depth_slider'] = mod_depth_slider

        # volume knob
        volume_dial = QtWidgets.QDial()
        volume_dial.setRange(0, 100)
        volume_dial.setValue(int(getattr(self, f'volume_{signal_number}') * 100))
        volume_dial.setToolTip("Adjust the volume of the signal")
        volume_label = QtWidgets.QLabel(f"{getattr(self, f'volume_{signal_number}'):.2f}")
        volume_dial.valueChanged.connect(lambda value, lbl=volume_label: lbl.setText(f"{value / 100:.2f}"))
        volume_dial.valueChanged.connect(self.update_plot)
        control_layout.addRow(f"Lautstärke {signal_number}:", self.wrap_widget_with_label(volume_label, volume_dial))
        self.signal_controls[signal_number]['volume_dial'] = volume_dial

        # pan knob
        pan_dial = QtWidgets.QDial()
        pan_dial.setRange(0, 100)
        pan_dial.setValue(int(getattr(self, f'pan_{signal_number}') * 100))
        pan_dial.setToolTip("Adjust the panning of the signal between left and right")
        pan_label = QtWidgets.QLabel(f"{getattr(self, f'pan_{signal_number}'):.2f}")
        pan_dial.valueChanged.connect(lambda value, lbl=pan_label: lbl.setText(f"{value / 100:.2f}"))
        pan_dial.valueChanged.connect(self.update_plot)
        control_layout.addRow(f"Panning {signal_number} (L-R):", self.wrap_widget_with_label(pan_label, pan_dial))
        self.signal_controls[signal_number]['pan_dial'] = pan_dial

        # waveform selection
        waveform_buttons = QtWidgets.QButtonGroup(self)
        waveform_layout = QtWidgets.QHBoxLayout()
        for waveform in ["sine", "square", "triangle", "sawtooth"]:
            button = QtWidgets.QRadioButton(waveform)
            button.setToolTip(f"Select {waveform} waveform for signal {signal_number}")
            if waveform == "sine":
                button.setChecked(True)
            waveform_buttons.addButton(button)
            waveform_layout.addWidget(button)
        waveform_buttons.buttonClicked.connect(self.update_plot)
        control_layout.addRow(f"Wellenform {signal_number}:", waveform_layout)
        self.signal_controls[signal_number]['waveform_buttons'] = waveform_buttons

        # mute button
        mute_button = QtWidgets.QPushButton()
        mute_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_MediaVolumeMuted))
        mute_button.setToolTip("Mute/unmute the signal")
        mute_button.setCheckable(True)
        mute_button.toggled.connect(lambda state, sn=signal_number: self.toggle_mute(sn, state))
        control_layout.addRow(f"Mute {signal_number}:", mute_button)
        self.signal_controls[signal_number]['mute_checkbox'] = mute_button

        control_group.setLayout(control_layout)
        layout.addWidget(control_group)

    def wrap_widget_with_label(self, label, widget):
        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(label)
        layout.addWidget(widget)
        return layout

    def wrap_widget_with_slider_and_spinbox(self, slider, spinbox):
        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(slider)
        layout.addWidget(spinbox)
        return layout

    def create_slider(self, min_val, max_val, initial_value, decimals=0):
        slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        slider.setRange(int(min_val * 10**decimals), int(max_val * 10**decimals))
        slider.setValue(int(initial_value * 10**decimals))
        slider.setSingleStep(1)
        slider.valueChanged.connect(self.update_plot)
        return slider

    def generate_signal(self, t, signal_number):
        controls = self.signal_controls[signal_number]
        if controls['mute_checkbox'].isChecked():
            return np.zeros_like(t)

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

        return wave * volume

    def update_plot(self):
        fs = self.sampling_rate
        if self.scrolling_plot:
            t = np.linspace(self.time_offset, self.time_offset + 0.05, int(0.05 * fs), endpoint=False)
            self.time_offset += 0.0005  # for scrolling effect
        else:
            t = np.linspace(0, 0.05, int(0.05 * fs), endpoint=False)

        combined_wave = np.zeros_like(t)

        for signal_number in [1, 2]:
            combined_wave += self.generate_signal(t, signal_number)

        combined_wave = np.clip(combined_wave, -1, 1)

        self.line.set_data(t, combined_wave)
        self.ax.set_xlim(t[0], t[-1])
        self.canvas.draw()

    def toggle_plot_mode(self):
        self.scrolling_plot = not self.scrolling_plot
        if not self.scrolling_plot:
            self.time_offset = 0
        self.update_plot()

    def toggle_mute(self, signal_number, state):
        self.signal_controls[signal_number]['mute_checkbox'].setChecked(state)
        self.update_plot()

    def audio_callback(self, outdata, frames, time, status):
        if not self.running:
            outdata[:] = np.zeros((frames, 2))
            return

        fs = self.sampling_rate
        t = (np.arange(frames) + self.sample_offset) / fs
        self.sample_offset += frames

        current_time = pytime.time()
        if self.last_callback_time is not None:
            callback_interval = current_time - self.last_callback_time
            expected_interval = frames / self.sampling_rate
            latency = abs(callback_interval - expected_interval)
            self.latency_label.setText(f"Callback latency: {latency:.6f} s")
        self.last_callback_time = current_time

        left_channel = np.zeros_like(t)
        right_channel = np.zeros_like(t)

        for signal_number in [1, 2]:
            wave = self.generate_signal(t, signal_number)
            pan = self.signal_controls[signal_number]['pan_dial'].value() / 100
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

if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    window = SineWaveApp()
    window.show()
    app.exec()

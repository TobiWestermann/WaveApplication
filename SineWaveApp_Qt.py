from PySide6 import QtWidgets, QtCore, QtGui
import numpy as np
import sounddevice as sd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import os
import soundfile as sf

class SineWaveApp(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Waveform Generator")

        self.sampling_rate = 48000

        # sig params
        self.signal_parameters = {
            1: self.create_default_signal_parameters()
        }

        self.running = False
        self.time_offset = 0
        self.scrolling_plot = False  # fixed plot default
        self.recording = False
        self.recorded_frames = []

        self.init_ui()

    def init_ui(self):
        main_layout = QtWidgets.QHBoxLayout(self)

        # tab widget 
        self.tab_widget = QtWidgets.QTabWidget()
        self.signal_controls = {}
        for signal_number in self.signal_parameters.keys():
            self.add_signal_tab(signal_number)
        left_layout = QtWidgets.QVBoxLayout()
        left_layout.addWidget(self.tab_widget)
        main_layout.addLayout(left_layout)

        # buttons layout
        button_layout = QtWidgets.QHBoxLayout()
        self.start_button = QtWidgets.QPushButton()
        self.start_button.setObjectName("playButton")
        self.start_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_MediaPlay))
        self.start_button.setToolTip("Start audio playback")
        self.start_button.clicked.connect(self.start)
        button_layout.addWidget(self.start_button)

        self.stop_button = QtWidgets.QPushButton()
        self.stop_button.setObjectName("stopButton")
        self.stop_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_MediaStop))
        self.stop_button.setToolTip("Stop audio playback")
        self.stop_button.clicked.connect(self.stop)
        button_layout.addWidget(self.stop_button)

        self.record_button = QtWidgets.QPushButton("Record")
        self.record_button.setToolTip("Start/stop recording the audio")
        self.record_button.setCheckable(True)
        self.record_button.toggled.connect(self.toggle_recording)
        button_layout.addWidget(self.record_button)

        self.toggle_plot_button = QtWidgets.QPushButton("Toggle Plot Mode")
        self.toggle_plot_button.setToolTip("Toggle between scrolling and fixed plot modes")
        self.toggle_plot_button.clicked.connect(self.toggle_plot_mode)
        button_layout.addWidget(self.toggle_plot_button)

        add_tab_button = QtWidgets.QPushButton("+")
        add_tab_button.setToolTip("Add a new signal")
        add_tab_button.clicked.connect(self.add_new_signal)
        left_layout.insertWidget(0, add_tab_button)

        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.remove_signal_tab)

        left_layout.addLayout(button_layout)

        # plot Layout
        self.fig, self.ax = plt.subplots()
        self.canvas = FigureCanvas(self.fig)
        self.line, = self.ax.plot([], [])
        self.ax.set_ylim(-1.5, 1.5)
        self.ax.set_xlim(0, 0.05)
        self.ax.set_xlabel("Time in s")
        self.ax.set_ylabel("Amplitude")
        right_layout = QtWidgets.QVBoxLayout()
        right_layout.addWidget(self.canvas)
        main_layout.addLayout(right_layout)

        
        self.setLayout(main_layout)

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(30)  

    def add_signal_tab(self, signal_number):
        tab = QtWidgets.QWidget()
        control_layout = QtWidgets.QFormLayout()

        self.signal_controls[signal_number] = {}

        params = self.signal_parameters[signal_number]

        self.create_slider_and_spinbox(control_layout, "Frequenz", signal_number, 'frequency', 10, 20000, 1, "Hz", 0, params['frequency'])
        self.create_slider_and_spinbox(control_layout, "Modulationsfrequenz", signal_number, 'mod_freq', 0.1, 50, 0.1, "Hz", 1, params['mod_freq'])
        self.create_slider_and_spinbox(control_layout, "Modulationstiefe", signal_number, 'mod_depth', 0.0, 1.0, 0.01, "", 2, params['mod_depth'])
        
        volume_dial, volume_spinbox = self.create_dial_with_spinbox(0.0, 1.0, params['volume'], "Adjust the volume of the signal", 0.01)
        control_layout.addRow(f"Lautstärke {signal_number}:", self.wrap_widget_with_label(volume_spinbox, volume_dial))
        self.signal_controls[signal_number]['volume_dial'] = volume_dial

        pan_dial, pan_spinbox = self.create_dial_with_spinbox(0.0, 1.0, params['pan'], "Adjust the panning of the signal between left and right", 0.01)
        control_layout.addRow(f"Panning {signal_number} (L-R):", self.wrap_widget_with_label(pan_spinbox, pan_dial))
        self.signal_controls[signal_number]['pan_dial'] = pan_dial

        # waveform selection
        waveform_buttons = QtWidgets.QButtonGroup(self)
        waveform_layout = QtWidgets.QHBoxLayout()
        for waveform in ["sine", "square", "triangle", "sawtooth"]:
            button = QtWidgets.QRadioButton(waveform)
            button.setToolTip(f"Select {waveform} waveform for signal {signal_number}")
            if waveform == params['waveform']:
                button.setChecked(True)
            waveform_buttons.addButton(button)
            waveform_layout.addWidget(button)
        waveform_buttons.buttonClicked.connect(self.update_plot)
        control_layout.addRow(f"Wellenform {signal_number}:", waveform_layout)
        self.signal_controls[signal_number]['waveform_buttons'] = waveform_buttons

        # mute button
        mute_button = QtWidgets.QPushButton()
        if params['mute']:
            mute_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_MediaVolumeMuted))
        else:
            mute_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_MediaVolume))
        mute_button.setToolTip("Mute/unmute the signal")
        mute_button.setCheckable(True)
        mute_button.setChecked(params['mute'])
        mute_button.toggled.connect(lambda state, btn=mute_button: self.toggle_mute_button(state, btn))
        control_layout.addRow(f"Mute {signal_number}:", mute_button)
        self.signal_controls[signal_number]['mute_checkbox'] = mute_button

        tab.setLayout(control_layout)
        self.tab_widget.addTab(tab, f"Signal {signal_number}")

    def create_dial_with_spinbox(self, min_val, max_val, initial_value, tooltip, single_step, decimals=2):
        dial = QtWidgets.QDial()
        dial.setRange(int(min_val * 100), int(max_val * 100))
        dial.setValue(int(initial_value * 100))
        dial.setToolTip(tooltip)
        spinbox = QtWidgets.QDoubleSpinBox()
        spinbox.setRange(min_val, max_val)
        spinbox.setSingleStep(single_step)
        spinbox.setDecimals(decimals)
        spinbox.setFixedWidth(80)
        spinbox.setValue(initial_value)

        dial.valueChanged.connect(lambda value: spinbox.setValue(value / 100))
        spinbox.valueChanged.connect(lambda value: dial.setValue(int(value * 100)))
        spinbox.valueChanged.connect(self.update_plot)

        return dial, spinbox

    def create_slider_and_spinbox(self, layout, label, signal_number, param_name, min_val, max_val, single_step, unit, decimals, initial_value):
        slider = self.create_slider(min_val, max_val, initial_value, decimals)
        spinbox = QtWidgets.QDoubleSpinBox() if decimals > 0 else QtWidgets.QSpinBox()
        spinbox.setRange(min_val, max_val)
        spinbox.setSingleStep(single_step)
        spinbox.setDecimals(decimals) if decimals > 0 else None
        spinbox.setFixedWidth(80)
        spinbox.setValue(initial_value)
        slider.setToolTip(f"Adjust the {label.lower()} of the signal")
        spinbox.setToolTip(f"Set the {label.lower()} of the signal")
        slider.valueChanged.connect(lambda value: spinbox.setValue(value / (10 ** decimals)))
        spinbox.valueChanged.connect(lambda value: slider.setValue(int(value * (10 ** decimals))))
        spinbox.valueChanged.connect(self.update_plot)
        layout.addRow(f"{label} {signal_number} ({unit}):", self.wrap_widget_with_slider_and_spinbox(slider, spinbox))
        self.signal_controls[signal_number][f'{param_name}_slider'] = slider

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

        freq = controls['frequency_slider'].value()
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

        for signal_number in self.signal_parameters.keys():
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

    def toggle_mute_button(self, state, button):
        if state:
            button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_MediaVolumeMuted))
        else:
            button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_MediaVolume))
        self.update_plot()

    def audio_callback(self, outdata, frames, time, status):
        if not self.running:
            outdata[:] = np.zeros((frames, 2))
            return

        fs = self.sampling_rate
        t = (np.arange(frames) + self.sample_offset) / fs
        self.sample_offset += frames
        
        left_channel = np.zeros_like(t)
        right_channel = np.zeros_like(t)

        for signal_number in list(self.signal_parameters.keys()):
            wave = self.generate_signal(t, signal_number)
            pan = self.signal_controls[signal_number]['pan_dial'].value() / 100
            left_channel += wave * (1 - pan)
            right_channel += wave * pan

        left_channel = np.clip(left_channel, -1, 1)
        right_channel = np.clip(right_channel, -1, 1)

        stereo_wave = np.vstack((left_channel, right_channel)).T

        outdata[:] = stereo_wave

        if self.recording:
            self.recorded_frames.append(stereo_wave.copy())

    def toggle_recording(self, state):
        if state:
            self.recorded_frames = []
            self.recording = True
            self.record_button.setText("Stop Recording")
        else:
            self.recording = False
            self.record_button.setText("Record")
            if self.running:
                self.stop()
            if self.recorded_frames:
                self.save_recording()


    def save_recording(self):
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save Recording", os.getenv("HOME"), "WAV Files (*.wav)")
        if filename:
            data = np.concatenate(self.recorded_frames, axis=0)
            sf.write(filename, data, self.sampling_rate)

    def create_default_signal_parameters(self, frequency=220.0):
        return {
            'frequency': frequency,
            'mod_freq': 5.0,
            'mod_depth': 0.5,
            'volume': 0.5,
            'pan': 0.5,
            'waveform': 'sine',
            'mute': False
        }

    def add_new_signal(self):
        if len(self.signal_parameters) >= 8:
            QtWidgets.QMessageBox.warning(self, "Limit Reached", "You cannot add more than 8 signals.")
            return

        if self.signal_parameters:
            new_signal_number = max(self.signal_parameters.keys()) + 1
            new_frequency = 440.0 + (new_signal_number - 1) * 220.0
        else:
            new_signal_number = 1
            new_frequency = 440.0

        self.signal_parameters[new_signal_number] = self.create_default_signal_parameters(new_frequency)
        self.add_signal_tab(new_signal_number)

    def remove_signal_tab(self, index):
        signal_number = list(self.signal_parameters.keys())[index]
        del self.signal_parameters[signal_number]
        del self.signal_controls[signal_number]
        self.tab_widget.removeTab(index)

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
            if self.recording:
                self.toggle_recording(False)

    
if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    window = SineWaveApp()
    window.show()
    app.exec()

import sys
import pygame
import wave
import numpy as np
import sounddevice as sd
import librosa  # Added for MP3 file support
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QFileDialog, QLabel, QSlider, QMessageBox, 
                             QMenuBar, QMenu, QAction, QStatusBar, QGroupBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from scipy.signal import convolve, butter, lfilter
from scipy.signal import medfilt
import psola


class AudioApp(QMainWindow):
    def __init__(self):
        super().__init__()
        # Mono init attempt
        pygame.mixer.init(frequency=44100, size=-16, channels=1)

        self.audio_file = None
        self.current_effect = "Original"
        self.waveform_data = None
        self.fs = None

        self.recording = False
        self.record_paused = False
        self.recorded_frames = []
        self.record_fs = 44100
        self.record_channels = 1
        self.stream = None
        self.recorded_sound = None

        self.processed_data = None
        self.processed_sound = None

        # Play situation
        self.file_play_channel = None
        self.is_file_paused = False

        # Which resource has been used lastly? "file", "recording", or None
        self.last_source = None

        self.initUI()

    def initUI(self):
        self.setWindowTitle("Audio Effects Application")
        self.setGeometry(100, 100, 900, 600)

        # Dark Theme QSS
        dark_qss = """
        QMainWindow {
            background-color: #303030;
            color: #ffffff;
        }

        QWidget {
            background-color: #303030;
            color: #ffffff;
            font-size: 14px;
        }

        QMenuBar, QMenu {
            background-color: #404040;
            color: #ffffff;
        }

        QMenuBar::item:selected, QMenu::item:selected {
            background-color: #505050;
        }

        QStatusBar {
            background-color: #404040;
            color: #ffffff;
        }

        QGroupBox {
            font-weight: bold;
            border: 2px solid #8f8f91;
            border-radius: 5px;
            margin-top: 2ex;
            background-color: #404040;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 3px;
        }

        QPushButton {
            background-color: #505050;
            border: 1px solid #606060;
            border-radius: 3px;
            padding: 5px;
        }
        QPushButton:hover {
            background-color: #606060;
        }
        QPushButton:pressed {
            background-color: #707070;
        }
        QPushButton:disabled {
            background-color: #404040;
            color: #808080;
            border: 1px solid #505050;
        }

        QSlider::groove:horizontal {
            height: 6px;
            background: #505050;
            border-radius: 3px;
        }
        QSlider::handle:horizontal {
            background: #ffffff;
            width: 14px;
            margin: -4px 0; 
            border-radius: 7px;
        }
        QSlider::add-page:horizontal {
            background: #404040;
        }
        QSlider::sub-page:horizontal {
            background: #00b300;
        }

        QLabel {
            color: #ffffff;
        }

        QMessageBox {
            background-color: #303030;
            color: #ffffff;
        }
        """
        self.setStyleSheet(dark_qss)

        # Menu Bar
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("File")
        load_action = QAction("Load Audio", self)
        load_action.triggered.connect(self.load_audio_file)
        file_menu.addAction(load_action)

        effects_menu = menu_bar.addMenu("Effects")
        effects_menu.addAction("Original", self.reset_effects)
        effects_menu.addAction("Echo", self.apply_echo)
        effects_menu.addAction("Bass", self.apply_bass)
        effects_menu.addAction("Reverb", self.apply_reverb)

        help_menu = menu_bar.addMenu("Help")
        about_action = QAction("About", self)
        about_action.triggered.connect(lambda: QMessageBox.information(self, "About", "This application is designed to apply effects on audio files, record from microphone, and visualize their waveforms."))
        help_menu.addAction(about_action)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)

        # File Playback Controls ( top side)
        file_control_group = QGroupBox("Playback Controls")
        file_control_layout = QHBoxLayout()

        play_file_button = QPushButton("Play")
        play_file_button.clicked.connect(self.play)

        pause_file_button = QPushButton("Pause")
        pause_file_button.clicked.connect(self.pause)

        stop_file_button = QPushButton("Stop")
        stop_file_button.clicked.connect(self.stop)

        file_control_layout.addWidget(play_file_button)
        file_control_layout.addWidget(pause_file_button)
        file_control_layout.addWidget(stop_file_button)
        file_control_group.setLayout(file_control_layout)
        main_layout.addWidget(file_control_group)

        # in continuation left panel (Effect, Recording, File ops) and right panel (Waveform)
        top_layout = QHBoxLayout()

        # Left panel: Effects, Volume, Recording, File
        left_panel = QVBoxLayout()

        # Effect Selection
        effects_group = QGroupBox("Effect Selection")
        effects_layout = QVBoxLayout()
        
        default_effect_btn = QPushButton("Original")
        default_effect_btn.setFont(QFont('', weight=QFont.Bold))
        default_effect_btn.clicked.connect(self.reset_effects)

        echo_btn = QPushButton("Echo")
        echo_btn.clicked.connect(self.apply_echo)

        bass_btn = QPushButton("Bass")
        bass_btn.clicked.connect(self.apply_bass)

        reverb_btn = QPushButton("Reverb")
        reverb_btn.clicked.connect(self.apply_reverb)

        effects_layout.addWidget(default_effect_btn)
        effects_layout.addWidget(echo_btn)
        effects_layout.addWidget(bass_btn)
        effects_layout.addWidget(reverb_btn)

        effects_group.setLayout(effects_layout)

        # Volume Control
        volume_group = QGroupBox("Volume Control")
        volume_layout = QVBoxLayout()
        volume_label = QLabel("Volume:")
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(70)
        self.volume_slider.valueChanged.connect(self.change_volume)
        volume_layout.addWidget(volume_label)
        volume_layout.addWidget(self.volume_slider)
        volume_group.setLayout(volume_layout)

        # Current Effect
        self.effect_label = QLabel("Active Effect: Original")

        # Recording Controls (Start/Pause/Stop)
        record_group = QGroupBox("Recording Controls")
        record_layout = QVBoxLayout()
        
        start_record_btn = QPushButton("Start Recording")
        start_record_btn.clicked.connect(self.start_recording)

        pause_record_btn = QPushButton("Pause Recording")
        pause_record_btn.clicked.connect(self.pause_recording_func)

        stop_record_btn = QPushButton("Stop Recording")
        stop_record_btn.clicked.connect(self.stop_recording_func)

        record_layout.addWidget(start_record_btn)
        record_layout.addWidget(pause_record_btn)
        record_layout.addWidget(stop_record_btn)

        self.record_status_label = QLabel("Recording Status: None")
        record_layout.addWidget(self.record_status_label)
        record_group.setLayout(record_layout)

        # File Operations
        file_group = QGroupBox("File Operations")
        file_layout = QVBoxLayout()

        file_button = QPushButton("Load Audio File")
        file_button.clicked.connect(self.load_audio_file)
        self.file_label = QLabel("Loaded File: - ")

        file_layout.addWidget(file_button)
        file_layout.addWidget(self.file_label)
        file_group.setLayout(file_layout)

        left_panel.addWidget(effects_group)
        left_panel.addWidget(volume_group)
        left_panel.addWidget(self.effect_label)
        left_panel.addWidget(record_group)
        left_panel.addWidget(file_group)

        left_widget = QWidget()
        left_widget.setLayout(left_panel)
        top_layout.addWidget(left_widget)

        # Right panel - Waveform Visualization
        right_card = QGroupBox("Waveform Visualization")
        right_layout = QVBoxLayout()
        
        self.figure = Figure(facecolor='#303030')
        self.canvas = FigureCanvas(self.figure)
        right_layout.addWidget(self.canvas)

        # Matplotlib dark style for plot
        self.figure.patch.set_facecolor('#303030')
        ax = self.figure.add_subplot(111)
        ax.set_facecolor('#303030')
        ax.tick_params(colors='white', which='both') 
        ax.spines['bottom'].set_color('white')
        ax.spines['top'].set_color('white') 
        ax.spines['right'].set_color('white')
        ax.spines['left'].set_color('white')
        ax.xaxis.label.set_color('white')
        ax.yaxis.label.set_color('white')
        ax.title.set_color('white')

        # Graph buttons
        graph_buttons = {
            "Original": lambda: self.plot_graph("Original"),
            "Echo": lambda: self.plot_graph("Echo"),
            "Bass": lambda: self.plot_graph("Bass"),
            "Reverb": lambda: self.plot_graph("Reverb")
        }

        graph_layout = QHBoxLayout()
        for text, func in graph_buttons.items():
            btn = QPushButton(text)
            btn.setToolTip(f"Show {text}")
            btn.clicked.connect(func)
            graph_layout.addWidget(btn)

        right_layout.addLayout(graph_layout)
        right_card.setLayout(right_layout)
        top_layout.addWidget(right_card)

        main_layout.addLayout(top_layout)

    def load_audio_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Audio File", "", "Audio Files (*.wav *.mp3)")
        if file_path:
            self.audio_file = file_path
            self.file_label.setText(f"Loaded File: {file_path}")
            self.status_bar.showMessage("Audio file loaded.")
            pygame.mixer.music.load(file_path)

            if file_path.lower().endswith(".wav"):
                self.read_wav_file(file_path)
            elif file_path.lower().endswith(".mp3"):
                self.read_mp3_file(file_path)  # New function for MP3 file
            else:
                self.waveform_data = None
                self.fs = None
                self.status_bar.showMessage("Unsupported file format.")

            self.last_source = "file"
        else:
            self.audio_file = None
            self.waveform_data = None
            self.fs = None

    def read_wav_file(self, file_path):
        with wave.open(file_path, 'rb') as wf:
            n_channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            framerate = wf.getframerate()
            n_frames = wf.getnframes()
            data = wf.readframes(n_frames)

        if sampwidth == 2:
            dtype = np.int16
        elif sampwidth == 4:
            dtype = np.int32
        else:
            dtype = np.uint8

        waveform = np.frombuffer(data, dtype=dtype)
        if n_channels > 1:
            waveform = waveform[0::n_channels]
        self.waveform_data = waveform.astype(np.float32) / 32767.0
        self.fs = framerate
        self.status_bar.showMessage("WAV file waveform loaded for effects.")

    def read_mp3_file(self, file_path):
        # Let's obtain waweform and fs with librosa for the MP3 file.
        y, sr = librosa.load(file_path, sr=None, mono=False)
        #  If it is stereo turn it to mono. (Using mean function)
        if y.ndim > 1:
            y = np.mean(y, axis=0)
        self.waveform_data = y.astype(np.float32)
        self.fs = sr
        self.status_bar.showMessage("MP3 file waveform loaded for effects.")

    def play(self):
        if self.last_source is None:
            QMessageBox.information(self, "Info", " Upload an audio file or make a recording.")
            return

        if self.last_source == "recording":
            if self.is_file_paused:
                if self.processed_sound is not None and self.current_effect != "Original":
                    if self.file_play_channel is not None:
                        self.file_play_channel.unpause()
                        self.is_file_paused = False
                        self.status_bar.showMessage("Resumed recorded sound (processed).")
                        return
                else:
                    if self.recorded_sound is not None:
                        if self.file_play_channel is not None:
                            self.file_play_channel.unpause()
                            self.is_file_paused = False
                            self.status_bar.showMessage("Resumed recorded sound (original).")
                            return
            self.stop()
            if self.recorded_sound is None and self.waveform_data is None:
                QMessageBox.information(self, "Info", "No recorded audio available.")
                return

            if self.current_effect == "Original":
                if self.recorded_sound is not None:
                    self.file_play_channel = self.recorded_sound.play()
                    self.is_file_paused = False
                    self.status_bar.showMessage("Playing recorded sound (original).")
                else:
                    QMessageBox.information(self, "Info", "No recorded audio available.")
            else:
                if self.waveform_data is None:
                    QMessageBox.warning(self, "Warning", "Cannot apply effects to recording without waveform data.")
                    return
                self.apply_effect(self.current_effect)
                if self.processed_sound is not None:
                    self.file_play_channel = self.processed_sound.play()
                    self.is_file_paused = False
                    self.status_bar.showMessage(f"Playing recorded sound with {self.current_effect} effect.")
                else:
                    QMessageBox.warning(self, "Warning", "No processed sound for recording.")

        elif self.last_source == "file":
            if self.is_file_paused:
                if self.current_effect != "Original" and self.processed_sound is not None and self.file_play_channel is not None:
                    self.file_play_channel.unpause()
                    self.is_file_paused = False
                    self.status_bar.showMessage("Resumed processed file playback.")
                    return
                else:
                    pygame.mixer.music.unpause()
                    self.is_file_paused = False
                    self.status_bar.showMessage("Resumed original file playback.")
                    return

            self.stop()
            if self.audio_file is None:
                QMessageBox.information(self, "Info", "No audio file loaded.")
                return

            if self.current_effect == "Original":
                pygame.mixer.music.play()
                self.is_file_paused = False
                self.status_bar.showMessage("Playing original file...")
            else:
                if self.waveform_data is None:
                    QMessageBox.warning(self, "Warning", "Cannot apply effects without waveform data.")
                    return
                self.apply_effect(self.current_effect)
                if self.processed_sound is None:
                    QMessageBox.warning(self, "Warning", "No processed sound available.")
                    return
                self.file_play_channel = self.processed_sound.play()
                self.is_file_paused = False
                self.status_bar.showMessage(f"Playing {self.current_effect} effect on file...")

    def pause(self):
        if self.last_source is None:
            QMessageBox.information(self, "Info", "Upload an audio file or make a recording.")
            return

        if self.last_source == "recording":
            if self.current_effect != "Original" and self.processed_sound is not None and self.file_play_channel is not None:
                self.file_play_channel.pause()
                self.is_file_paused = True
                self.status_bar.showMessage("Paused recorded (processed) playback.")
            else:
                if self.file_play_channel is not None:
                    self.file_play_channel.pause()
                    self.is_file_paused = True
                    self.status_bar.showMessage("Paused recorded (original) playback.")
                else:
                    self.status_bar.showMessage("No recorded audio is playing.")
        else:
            if self.current_effect != "Original" and self.processed_sound is not None and self.file_play_channel is not None:
                self.file_play_channel.pause()
                self.is_file_paused = True
                self.status_bar.showMessage("Paused processed file playback.")
            else:
                pygame.mixer.music.pause()
                self.is_file_paused = True
                self.status_bar.showMessage("Paused original file playback.")

    def stop(self):
        if self.last_source is None:
            QMessageBox.information(self, "Info", "Upload an audio file or make a recording.")
            return

        if self.file_play_channel is not None:
            self.file_play_channel.stop()
            self.file_play_channel = None

        pygame.mixer.music.stop()
        pygame.mixer.music.rewind()
        self.is_file_paused = False

        if self.last_source == "recording":
            self.status_bar.showMessage("Stopped recorded audio playback.")
        else:
            self.status_bar.showMessage("Stopped file playback.")

    def audio_callback(self, indata, frames, time, status):
        if self.recording and not self.record_paused:
            self.recorded_frames.append(indata.copy())

    def start_recording(self):
        if self.recording:
            self.status_bar.showMessage("Already recording.")
            return

        if self.stream is None:
            self.stream = sd.InputStream(samplerate=self.record_fs, 
                                         channels=self.record_channels,
                                         callback=self.audio_callback)
        self.recorded_frames = []
        self.stream.start()
        self.recording = True
        self.record_paused = False
        self.record_status_label.setText("Recording Status: Recording...")
        self.status_bar.showMessage("Recording started.")

    def pause_recording_func(self):
        if self.recording and not self.record_paused:
            self.record_paused = True
            self.record_status_label.setText("Recording Status: Paused")
            self.status_bar.showMessage("Recording paused.")

    def stop_recording_func(self):
        if self.stream is not None and self.recording:
            self.stream.stop()
            self.stream.close()
            self.stream = None
            self.recording = False
            self.record_paused = False
            self.record_status_label.setText("Recording Status: Finished")
            self.status_bar.showMessage("Recording finished and processing.")

            if len(self.recorded_frames) > 0:
                recorded_data = np.concatenate(self.recorded_frames, axis=0)
                self.waveform_data = recorded_data.flatten().astype(np.float32)
                self.fs = self.record_fs
                self.recorded_frames = []
                int16_data = (self.waveform_data * 32767).astype(np.int16)

                freq, size, chans = pygame.mixer.get_init()
                if chans == 1:
                    sound_array = int16_data
                else:
                    sound_array = np.repeat(int16_data[:, np.newaxis], 2, axis=1)

                self.recorded_sound = pygame.sndarray.make_sound(sound_array)
                self.status_bar.showMessage("Recording completed and ready to play.")
                self.last_source = "recording"
            else:
                QMessageBox.information(self, "Info", "No recording data.")
                self.record_status_label.setText("Recording Status: None")
                self.status_bar.showMessage("No recording data.")

    def apply_effect(self, effect_name):
        self.current_effect = effect_name
        self.effect_label.setText("Active Effect: " + effect_name)
        if self.waveform_data is not None and self.fs is not None:
            processed_data = self.get_processed_data(effect_name)
            int16_data = (processed_data * 32767).astype(np.int16)
            freq, size, chans = pygame.mixer.get_init()
            if chans == 1:
                sound_array = int16_data
            else:
                sound_array = np.stack((int16_data, int16_data), axis=-1)
            self.processed_data = processed_data
            self.processed_sound = pygame.sndarray.make_sound(sound_array)
        else:
            self.processed_data = None
            self.processed_sound = None

    def reset_effects(self):
        pygame.mixer.music.set_volume(1.0)
        self.apply_effect("Original")

    def apply_echo(self):
        self.apply_effect("Echo")

    def apply_bass(self):
        self.apply_effect("Bass")

    def apply_reverb(self):
        self.apply_effect("Reverb")

    def apply_autotune(self):
        self.apply_effect("Autotune")

    def change_volume(self, value):
        volume = value / 100.0
        pygame.mixer.music.set_volume(volume)
        if self.processed_sound is not None:
            self.processed_sound.set_volume(volume)
        if self.recorded_sound is not None:
            self.recorded_sound.set_volume(volume)
        self.status_bar.showMessage(f"Volume: %{value}")

    def get_processed_data(self, effect_name):
        data = self.waveform_data.copy()
        if effect_name == "Original":
            return data
        elif effect_name == "Echo":
            delay_samples = int(0.2 * self.fs)
            ir = np.zeros(delay_samples+1)
            ir[0] = 1.0
            ir[-1] = 0.5
            processed = convolve(data, ir, mode='full')
            return processed[:len(data)]
        elif effect_name == "Bass":
            cutoff = 1000.0
            nyq = 0.5 * self.fs
            normal_cutoff = cutoff / nyq
            b, a = butter(4, normal_cutoff, btype='low', analog=False)
            processed = lfilter(b, a, data)
            return processed
        elif effect_name == "Reverb":
            # Reverb parameters
            ir_length = int(0.5 * self.fs)
            decay = 0.8
            dry_wet = 0.6
            
            ir = np.zeros(ir_length)
            ir[0] = 1.0
            for i in range(1, ir_length):
                ir[i] = ir[i-1] * decay + np.random.normal(0, 0.01)
            
            processed = convolve(data, ir, mode='full')
            output = dry_wet * processed[:len(data)] + (1 - dry_wet) * data
            return np.clip(output, -1, 1)
        else:
            return data

    def plot_graph(self, effect_name):
        if self.waveform_data is None or self.fs is None:
            QMessageBox.warning(self, "Warning", "Please load an audio file or make a recording first!")
            return

        try:
            # Get processed data and validate
            processed_data = self.get_processed_data(effect_name)
            if len(processed_data) == 0:
                QMessageBox.warning(self, "Error", "Processed data is empty!")
                return

            # Handle NaNs or Infs in processed data
            processed_data = np.nan_to_num(processed_data, nan=0.0, posinf=0.0, neginf=0.0)

            # Set up plotting
            self.figure.clear()
            ax = self.figure.add_subplot(111)
            ax.set_facecolor('#303030')
            ax.tick_params(colors='white', which='both')
            ax.spines['bottom'].set_color('white')
            ax.spines['top'].set_color('white')
            ax.spines['right'].set_color('white')
            ax.spines['left'].set_color('white')
            ax.xaxis.label.set_color('white')
            ax.yaxis.label.set_color('white')
            ax.title.set_color('white')

            # Generate time vector and downsample data
            t = np.linspace(0, len(processed_data) / self.fs, len(processed_data))
            sampled_factor = max(1, len(processed_data) // 1000)  # Keep at least 1000 points
            t_sampled = t[::sampled_factor]
            processed_downsampled = processed_data[::sampled_factor]

            # Plot waveform
            ax.plot(t_sampled, processed_downsampled, color='lime')
            ax.set_title(effect_name + " Waveform")
            ax.set_xlabel("Time (s)")
            ax.set_ylabel("Amplitude")
            ax.set_xlim(0, t_sampled[-1])
            ax.set_ylim(processed_data.min() - 0.1, processed_data.max() + 0.1)

            self.canvas.draw()
            self.status_bar.showMessage(f"Showing {effect_name} waveform...")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred while plotting the graph: {str(e)}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = AudioApp()
    ex.show()
    sys.exit(app.exec_())

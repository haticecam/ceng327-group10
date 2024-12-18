import sys
import pygame
import wave
import numpy as np
import sounddevice as sd
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QFrame, QPushButton, QFileDialog, QLabel, QSlider, QMessageBox, 
                             QMenuBar, QMenu, QAction, QStatusBar, QGroupBox, QGridLayout)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QFont, QPalette, QColor
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class AudioApp(QMainWindow):
    def __init__(self):
        super().__init__()
        # Attempt to initialize mixer in mono (if not supported, it may fallback to stereo)
        pygame.mixer.init(frequency=44100, size=-16, channels=1)

        self.audio_file = None
        self.is_paused = False
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

        self.initUI()

    def initUI(self):
        self.setWindowTitle("Audio Effects Application")
        self.setGeometry(100, 100, 900, 600)
        
        # Set Fusion style
        QApplication.setStyle("Fusion")

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

        # Main layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)

        # Playback Controls
        control_group = QGroupBox("Playback Controls")
        control_layout = QHBoxLayout()

        play_file_button = QPushButton()
        play_file_button.setIcon(self.style().standardIcon(self.style().SP_MediaPlay))
        play_file_button.setToolTip("Play the loaded file")
        play_file_button.clicked.connect(self.play_file)

        play_record_button = QPushButton()
        play_record_button.setIcon(self.style().standardIcon(self.style().SP_MediaPlay))
        play_record_button.setToolTip("Play the last recording")
        play_record_button.clicked.connect(self.play_recorded_sound)
        play_record_button.setEnabled(False)
        self.play_record_button = play_record_button

        pause_button = QPushButton()
        pause_button.setIcon(self.style().standardIcon(self.style().SP_MediaPause))
        pause_button.setToolTip("Pause playback")
        pause_button.clicked.connect(self.pause_audio)

        stop_button = QPushButton()
        stop_button.setIcon(self.style().standardIcon(self.style().SP_MediaStop))
        stop_button.setToolTip("Stop and rewind")
        stop_button.clicked.connect(self.stop_audio)

        control_layout.addWidget(play_file_button)
        control_layout.addWidget(play_record_button)
        control_layout.addWidget(pause_button)
        control_layout.addWidget(stop_button)
        control_group.setLayout(control_layout)
        main_layout.addWidget(control_group)

        top_layout = QHBoxLayout()

        # Left panel: Effects, Volume, Recording, File
        left_panel = QVBoxLayout()

        # Effect Selection
        effects_group = QGroupBox("Effect Selection")
        effects_layout = QVBoxLayout()
        
        default_effect_btn = QPushButton("Original")
        default_effect_btn.setFont(QFont('', weight=QFont.Bold))
        default_effect_btn.setToolTip("Play the original sound")
        default_effect_btn.clicked.connect(self.reset_effects)

        echo_btn = QPushButton("Echo")
        echo_btn.setToolTip("Apply Echo effect")
        echo_btn.clicked.connect(self.apply_echo)

        bass_btn = QPushButton("Bass")
        bass_btn.setToolTip("Apply Bass effect")
        bass_btn.clicked.connect(self.apply_bass)

        reverb_btn = QPushButton("Reverb")
        reverb_btn.setToolTip("Apply Reverb effect")
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
        self.volume_slider.setToolTip("Adjust volume")
        self.volume_slider.valueChanged.connect(self.change_volume)
        volume_layout.addWidget(volume_label)
        volume_layout.addWidget(self.volume_slider)
        volume_group.setLayout(volume_layout)

        # Current Effect
        self.effect_label = QLabel("Active Effect: Original")

        # Recording Controls
        record_group = QGroupBox("Recording Controls")
        record_layout = QVBoxLayout()
        
        start_record_btn = QPushButton("Start Recording")
        start_record_btn.setToolTip("Start recording from microphone")
        start_record_btn.clicked.connect(self.start_recording)

        pause_record_btn = QPushButton("Pause Recording")
        pause_record_btn.setToolTip("Temporarily pause recording")
        pause_record_btn.clicked.connect(self.pause_recording_func)

        stop_record_btn = QPushButton("Stop Recording")
        stop_record_btn.setToolTip("Stop recording and prepare recorded audio")
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
        file_button.setToolTip("Load an audio file (WAV/MP3)")
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
            else:
                # Cannot extract waveform from MP3
                self.waveform_data = None
                self.fs = None
                self.status_bar.showMessage("Cannot extract waveform from MP3.")
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
        self.waveform_data = waveform.astype(np.float32)
        self.fs = framerate
        self.status_bar.showMessage("WAV file waveform loaded.")

    def play_file(self):
        if self.audio_file:
            if self.is_paused:
                pygame.mixer.music.unpause()
            else:
                pygame.mixer.music.play()
            self.is_paused = False
            self.status_bar.showMessage("Playing file...")
        else:
            QMessageBox.information(self, "Info", "Please load an audio file first.")

    def play_recorded_sound(self):
        if self.recorded_sound is not None:
            self.recorded_sound.play()
            self.status_bar.showMessage("Playing recording...")
        else:
            QMessageBox.information(self, "Info", "No recording available.")

    def pause_audio(self):
        if self.audio_file and not self.is_paused:
            pygame.mixer.music.pause()
            self.is_paused = True
            self.status_bar.showMessage("Playback paused.")

    def stop_audio(self):
        if self.audio_file:
            pygame.mixer.music.stop()
            pygame.mixer.music.rewind()
            self.is_paused = False
            self.status_bar.showMessage("Playback rewound.")

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
        print("Recording started")

    def pause_recording_func(self):
        if self.recording and not self.record_paused:
            self.record_paused = True
            self.record_status_label.setText("Recording Status: Paused")
            self.status_bar.showMessage("Recording paused.")
            print("Recording paused")
        else:
            print("Recording is already paused or not started.")

    def stop_recording_func(self):
        if self.stream is not None and self.recording:
            self.stream.stop()
            self.stream.close()
            self.stream = None
            self.recording = False
            self.record_paused = False
            print("Recording stopped")
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
                self.play_record_button.setEnabled(True)
                self.status_bar.showMessage("Recording completed and ready to play.")
            else:
                print("No recording data.")
                QMessageBox.information(self, "Info", "No recording data.")
                self.record_status_label.setText("Recording Status: None")
                self.status_bar.showMessage("No recording data.")
        else:
            print("No ongoing recording to stop.")

    def apply_effect(self, effect_name):
        self.current_effect = effect_name
        self.effect_label.setText("Active Effect: " + effect_name)

    def reset_effects(self):
        pygame.mixer.music.set_volume(1.0)
        self.apply_effect("Original")

    def apply_echo(self):
        pygame.mixer.music.set_volume(0.7)
        self.apply_effect("Echo")

    def apply_bass(self):
        pygame.mixer.music.set_volume(0.8)
        self.apply_effect("Bass")

    def apply_reverb(self):
        pygame.mixer.music.set_volume(0.6)
        self.apply_effect("Reverb")

    def change_volume(self, value):
        volume = value / 100.0
        pygame.mixer.music.set_volume(volume)
        self.status_bar.showMessage(f"Volume: %{value}")

    def plot_graph(self, effect_name):
        if self.waveform_data is None or self.fs is None:
            QMessageBox.warning(self, "Warning", "Please load an audio file or make a recording first!")
            return

        data = self.waveform_data.copy()

        if effect_name == "Original":
            processed_data = data
            title = "Original Waveform"
        elif effect_name == "Echo":
            delay = int(0.05 * self.fs)
            echo_data = np.zeros_like(data)
            if delay < len(data):
                echo_data[delay:] = data[:-delay] * 0.5
            processed_data = data + echo_data
            title = "Echo Effect"
        elif effect_name == "Bass":
            kernel_size = int(0.01 * self.fs)
            if kernel_size < 1:
                kernel_size = 1
            cumsum = np.cumsum(np.insert(data, 0, 0))
            moving_avg = (cumsum[kernel_size:] - cumsum[:-kernel_size]) / kernel_size
            processed_data = np.zeros_like(data)
            processed_data[:len(moving_avg)] = moving_avg
            title = "Bass (Low-Pass Filter)"
        elif effect_name == "Reverb":
            processed_data = data.copy()
            delays = [int(0.03*self.fs), int(0.06*self.fs), int(0.09*self.fs)]
            gains = [0.5, 0.3, 0.2]
            for d, g in zip(delays, gains):
                rev_data = np.zeros_like(data)
                if d < len(data):
                    rev_data[d:] = processed_data[:-d] * g
                    processed_data += rev_data
            title = "Reverb Effect"
        else:
            processed_data = data
            title = "Unknown Effect"

        self.figure.clear()
        ax = self.figure.add_subplot(111)
        # Set plot background and text color again after clearing
        ax.set_facecolor('#303030')
        ax.tick_params(colors='white', which='both') 
        ax.spines['bottom'].set_color('white')
        ax.spines['top'].set_color('white') 
        ax.spines['right'].set_color('white')
        ax.spines['left'].set_color('white')
        ax.xaxis.label.set_color('white')
        ax.yaxis.label.set_color('white')
        ax.title.set_color('white')

        t = np.linspace(0, len(processed_data)/self.fs, len(processed_data))
        ax.plot(t, processed_data, color='lime')
        ax.set_title(title)
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Amplitude")

        self.canvas.draw()
        self.status_bar.showMessage(f"Showing {title}...")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = AudioApp()
    ex.show()
    sys.exit(app.exec_())

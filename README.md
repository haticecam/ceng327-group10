# ceng327-group10

# Real-Time Audio Effects Processing (Echo, Reverb) Application

This application demonstrates the principles of real-time audio effects processing on recorded or loaded audio files. By capturing audio from a microphone or loading an existing `.wav` or `.mp3` file, users can experiment with common effects such as Echo, Bass (low-pass filtering), and Reverb. The application also visually represents the waveform before and after applying these effects. While the effects in this current implementation are applied upon user request (not continuously manipulated during playback), the architecture and code structure provide a foundation that can be extended to handle more interactive, real-time processing scenarios.

## Key Features

### Real-Time Concepts
Although effects are triggered by the user, the architecture demonstrates how one might extend the code to handle actual real-time audio streams. Input is taken from a microphone in real-time, recorded, and processed after completion, mirroring the workflow needed for real-time FX chains.

### Common Audio Effects
- **Original:** Listen to the raw, unprocessed audio.
- **Echo:** Adds a simple delayed repetition of the sound.
- **Bass (Low-Pass Filtering):** Simulates a low-pass filter, emphasizing lower frequencies.
- **Reverb:** Simulates reflections of the sound as if it were in a room, adding spatial depth.

### Interactive GUI (PyQt5)
A user-friendly graphical interface built with PyQt5, featuring:
- Dark-themed, modern look for better visual focus.
- Menus for loading audio files and applying effects.
- Buttons to start, pause, and stop playback and recording.
- Slider to control playback volume.
- Real-time waveform visualization using Matplotlib.

### Recording and Playback
Users can record audio from their microphone and then immediately apply effects. This mimics a real-time capture scenario, easily modifiable to handle on-the-fly processing.

## Getting Started

### Prerequisites
Ensure you have Python 3.x and the following libraries installed:
```bash
pip install PyQt5 pygame sounddevice numpy matplotlib
```
### Running the Application
1. Clone the repository or download the proje.py file.
2. Install the required dependencies.
3. In the terminal, navigate to the directory containing proje.py.
4. Run the application:
```bash
python proje.py
```
### Loading and Recording Audio
Load Audio File: Use the "Load Audio" option under the "File" menu or the "Load Audio File" button to select a .wav or .mp3 file.
Note: Waveforms can only be visualized for .wav files due to direct PCM data access.

Recording Audio: Click "Start Recording" to capture audio from your microphone. "Pause Recording" and "Stop Recording" allow you to control the recording session. Once completed, the waveform can be visualized, and effects can be applied.

### Applying Effects
Select your desired effect from the "Effects" menu or via buttons on the left panel:

- **Original:** Resets to the raw audio signal.
- **Echo:** Adds a delayed repeat to the signal.
- **Bass:** Emphasizes lower frequencies (like applying a rudimentary low-pass filter).
- **Reverb:** Adds multiple delayed reflections, simulating a room-like acoustic space.
After selecting an effect, click the waveform visualization buttons ("Original", "Echo", "Bass", "Reverb") on the right panel to see the processed waveform.

### Towards Real-Time Processing
While the current application applies effects after loading or recording has completed, it serves as a blueprint for real-time processing. Future enhancements could:

- Continuously process audio buffers in the sounddevice callback, applying effects on-the-fly before playback.
- Update the waveform in near-real-time as the audio changes.
- Dynamically adjust effect parameters during playback.

These changes would transform the application from a post-processing tool into a true real-time effects processor.

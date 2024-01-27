import whisper
import pyaudio
import wave
import tempfile
from ctypes import *


class VoiceRecorder:
    def __init__(self):
        self.sample_rate = 16000
        self.bits_per_sample = 16
        self.chunk_size = 1024
        self.audio_format = pyaudio.paInt16
        self.channels = 1

        # Suppress ALSA warnings (https://stackoverflow.com/a/13453192)
        ERROR_HANDLER_FUNC = CFUNCTYPE(None, c_char_p, c_int, c_char_p, c_int, c_char_p)

        def py_error_handler(filename, line, function, err, fmt):
            return

        c_error_handler = ERROR_HANDLER_FUNC(py_error_handler)
        asound = cdll.LoadLibrary("libasound.so")
        asound.snd_lib_error_set_handler(c_error_handler)

        # Initialize PyAudio
        self.audio = pyaudio.PyAudio()

        self.model = whisper.load_model("base.en")

        self.temp_file = None

    def start_recording(self):
        self.temp_file = tempfile.NamedTemporaryFile(suffix=".wav")

        # Open the wave file for writing
        self.wav_file = wave.open(self.temp_file.name, "wb")
        self.wav_file.setnchannels(self.channels)
        self.wav_file.setsampwidth(self.bits_per_sample // 8)
        self.wav_file.setframerate(self.sample_rate)

        def callback(in_data, frame_count, time_info, status):
            self.wav_file.writeframes(in_data)
            return None, pyaudio.paContinue

        # Start recording audio
        self.stream = self.audio.open(
            format=self.audio_format,
            channels=self.channels,
            rate=self.sample_rate,
            input=True,
            frames_per_buffer=self.chunk_size,
            stream_callback=callback,
        )

    def stop_recording(self) -> str:
        # Stop and close the audio stream
        self.stream.stop_stream()
        self.stream.close()
        self.audio.terminate()

        # Close the wave file
        self.wav_file.close()

        # And transcribe the audio to text (suppressing warnings about running on a CPU)
        result = self.model.transcribe(self.temp_file.name, fp16=False)
        self.temp_file.close()

        return result["text"].strip()


if __name__ == "__main__":
    recorder = VoiceRecorder()
    recorder.start_recording()
    input("Press Enter to stop recording...")
    print(recorder.stop_recording())

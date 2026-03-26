"""
ai/live_transcriber.py
Real-time mic transcription: sounddevice + Whisper chunks every 5 seconds.
"""

import queue
import threading
import numpy as np

try:
    import sounddevice as sd
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    SOUNDDEVICE_AVAILABLE = False

from ai.transcriber import load_model

SAMPLE_RATE   = 16_000
CHUNK_SECONDS = 5
SILENCE_THRESH = 0.008
BLOCK_SIZE    = int(SAMPLE_RATE * 0.5)


class LiveTranscriber:
    def __init__(self, on_transcript=None, model_name: str = "base", language: str = "en"):
        if not SOUNDDEVICE_AVAILABLE:
            raise RuntimeError(
                "sounddevice is not installed.\n"
                "Run: pip install sounddevice\n"
                "Linux: sudo apt install libportaudio2"
            )
        self.on_transcript = on_transcript
        self.model_name    = model_name
        self.language      = language
        self._audio_queue  = queue.Queue()
        self._running      = False
        self._stream       = None
        self._thread       = None

    def start(self):
        self._model   = load_model(self.model_name)
        self._running = True
        self._thread  = threading.Thread(target=self._transcribe_loop, daemon=True)
        self._thread.start()
        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="float32",
            blocksize=BLOCK_SIZE,
            callback=self._audio_callback,
        )
        self._stream.start()

    def stop(self):
        self._running = False
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
        self._audio_queue.put(None)

    def _audio_callback(self, indata, frames, time_info, status):
        self._audio_queue.put(indata.copy().flatten())

    def _transcribe_loop(self):
        target_samples = SAMPLE_RATE * CHUNK_SECONDS
        while self._running:
            chunks, total = [], 0
            while total < target_samples and self._running:
                try:
                    block = self._audio_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                if block is None:
                    return
                chunks.append(block)
                total += len(block)

            if not chunks:
                continue

            audio = np.concatenate(chunks, axis=0)
            rms = float(np.sqrt(np.mean(audio ** 2)))
            if rms < SILENCE_THRESH:
                continue

            try:
                result = self._model.transcribe(
                    audio,
                    fp16=False,
                    language=self.language if self.language else None,
                    verbose=False,
                )
                text = result.get("text", "").strip()
                if text and self.on_transcript:
                    self.on_transcript(text)
            except Exception as exc:
                print(f"[LiveTranscriber] Error: {exc}")


def list_microphones() -> list[dict]:
    if not SOUNDDEVICE_AVAILABLE:
        return []
    devices = sd.query_devices()
    return [
        {"id": i, "name": d["name"], "channels": d["max_input_channels"]}
        for i, d in enumerate(devices)
        if d["max_input_channels"] > 0
    ]
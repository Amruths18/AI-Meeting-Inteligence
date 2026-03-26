"""
ai/live_transcriber.py
Real-time microphone transcription using sounddevice + OpenAI Whisper.

Architecture:
  - sounddevice InputStream captures mic audio continuously
  - Audio is buffered into a queue in ~0.5-second blocks
  - A background thread accumulates CHUNK_SECONDS of audio, then feeds Whisper
  - The resulting text is returned via on_transcript(text) callback
  - Silence detection skips Whisper on quiet segments (saves CPU)
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

SAMPLE_RATE    = 16_000   # Hz — Whisper requires 16 kHz
CHUNK_SECONDS  = 5        # seconds of audio per Whisper inference
SILENCE_THRESH = 0.008    # RMS below this = silence, skip transcription
BLOCK_SIZE     = int(SAMPLE_RATE * 0.5)   # 0.5-second capture blocks


class LiveTranscriber:
    """
    Captures the system microphone and streams transcribed text via callback.

    Usage:
        lt = LiveTranscriber(on_transcript=my_func)
        lt.start()
        ...
        lt.stop()
    """

    def __init__(
        self,
        on_transcript=None,
        model_name: str = "base",
        language: str = "en",
    ):
        if not SOUNDDEVICE_AVAILABLE:
            raise RuntimeError(
                "sounddevice is not installed.\n"
                "Run: pip install sounddevice\n"
                "Then on Linux: sudo apt install libportaudio2"
            )
        self.on_transcript = on_transcript
        self.model_name    = model_name
        self.language      = language

        self._audio_queue: queue.Queue = queue.Queue()
        self._running     = False
        self._stream      = None
        self._thread      = None

    # ── Public API ────────────────────────────────────────────────────────────

    def start(self):
        """Load Whisper model, open mic, start transcription thread."""
        self._model   = load_model(self.model_name)
        self._running = True

        self._thread = threading.Thread(
            target=self._transcribe_loop, daemon=True
        )
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
        """Stop capturing and transcribing."""
        self._running = False
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
        # Unblock the queue
        self._audio_queue.put(None)

    def is_running(self) -> bool:
        return self._running

    # ── Internal ──────────────────────────────────────────────────────────────

    def _audio_callback(self, indata, frames, time_info, status):
        """Called by sounddevice on each captured block."""
        self._audio_queue.put(indata.copy().flatten())

    def _transcribe_loop(self):
        """
        Continuously accumulates CHUNK_SECONDS of audio, runs Whisper,
        and calls on_transcript with the result.
        """
        target_samples = SAMPLE_RATE * CHUNK_SECONDS

        while self._running:
            chunks = []
            total  = 0

            # Collect audio until we have a full chunk
            while total < target_samples and self._running:
                try:
                    block = self._audio_queue.get(timeout=1.0)
                except queue.Empty:
                    continue

                if block is None:
                    return   # stop signal

                chunks.append(block)
                total += len(block)

            if not chunks:
                continue

            audio = np.concatenate(chunks, axis=0)

            # Skip silent audio
            rms = float(np.sqrt(np.mean(audio ** 2)))
            if rms < SILENCE_THRESH:
                continue

            # Run Whisper
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
                # Don't crash the loop on a bad chunk
                print(f"[LiveTranscriber] Whisper error: {exc}")


def list_microphones() -> list[dict]:
    """Return a list of available input devices."""
    if not SOUNDDEVICE_AVAILABLE:
        return []
    devices = sd.query_devices()
    return [
        {"id": i, "name": d["name"], "channels": d["max_input_channels"]}
        for i, d in enumerate(devices)
        if d["max_input_channels"] > 0
    ]

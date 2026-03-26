"""
ai/transcriber.py
Handles offline speech-to-text conversion using OpenAI Whisper.
Runs entirely on the local machine — no internet required.
"""

import os
from pathlib import Path


# Whisper model sizes: tiny | base | small | medium | large
# 'base' is a good balance of speed and accuracy for most meetings.
DEFAULT_MODEL = "base"

_model_cache: dict = {}


def load_model(model_name: str = DEFAULT_MODEL):
    """
    Load (and cache) a Whisper model by name.
    First call downloads the model (~74 MB for 'base'); subsequent calls are instant.
    """
    import whisper
    if model_name not in _model_cache:
        print(f"[Transcriber] Loading Whisper model: {model_name}")
        _model_cache[model_name] = whisper.load_model(model_name)
    return _model_cache[model_name]


def transcribe_audio(
    audio_path: str,
    model_name: str = DEFAULT_MODEL,
    language: str = "en",
    progress_callback=None
) -> dict:
    """
    Transcribe an audio file to text using Whisper.

    Args:
        audio_path:        Path to the audio file (.mp3, .wav, .m4a, .mp4, etc.)
        model_name:        Whisper model variant to use.
        language:          Language code (e.g. 'en', 'hi'). None = auto-detect.
        progress_callback: Optional callable(message: str) for UI status updates.

    Returns:
        {
            "text":     full transcript string,
            "segments": list of {start, end, text} dicts,
            "language": detected language code
        }
    """
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    if progress_callback:
        progress_callback("Loading AI model...")

    model = load_model(model_name)

    if progress_callback:
        progress_callback("Transcribing audio... (this may take a moment)")

    # decode_options: fp16=False ensures CPU compatibility
    result = model.transcribe(
        audio_path,
        language=language if language else None,
        fp16=False,
        verbose=False
    )

    if progress_callback:
        progress_callback("Transcription complete.")

    return {
        "text": result["text"].strip(),
        "segments": [
            {
                "start": round(seg["start"], 2),
                "end":   round(seg["end"], 2),
                "text":  seg["text"].strip()
            }
            for seg in result.get("segments", [])
        ],
        "language": result.get("language", "unknown")
    }


def format_transcript_with_timestamps(segments: list[dict]) -> str:
    """
    Convert Whisper segments into a readable timestamped transcript.

    Example output:
        [00:00] Hello everyone, welcome to the meeting.
        [00:05] Today we will discuss the project timeline...
    """
    lines = []
    for seg in segments:
        minutes = int(seg["start"] // 60)
        seconds = int(seg["start"] % 60)
        timestamp = f"[{minutes:02d}:{seconds:02d}]"
        lines.append(f"{timestamp} {seg['text']}")
    return "\n".join(lines)


SUPPORTED_FORMATS = {".mp3", ".wav", ".m4a", ".mp4", ".ogg", ".flac", ".webm"}


def is_supported_format(file_path: str) -> bool:
    """Return True if the file extension is supported by Whisper."""
    return Path(file_path).suffix.lower() in SUPPORTED_FORMATS

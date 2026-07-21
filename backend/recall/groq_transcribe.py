"""Groq Whisper transcription client (D28).

Accepts a local audio file path and returns a transcript string.
If the transcript is very short (< 25 chars) we return an empty string so
the caller can fall back to post caption / metadata text only.
"""

from __future__ import annotations

from pathlib import Path


# Minimum character count to treat a transcript as containing real speech.
_MIN_TRANSCRIPT_CHARS = 25


def transcribe_audio(audio_path: Path, *, api_key: str) -> str:
    """Send a local audio file to Groq's Whisper Large v3 API and return the transcript.

    Returns an empty string if the transcript is too short to be meaningful
    (music-only, silent, or no recognisable speech).

    Args:
        audio_path: Path to a local audio file (.m4a, .mp3, .wav, …).
        api_key: Groq API key (server-side credential, never from the client).

    Returns:
        Transcript text, or "" if no meaningful speech was detected.

    Raises:
        RuntimeError: If the Groq API call fails for reasons other than an
            empty transcript.
    """
    from groq import Groq  # imported lazily so the module loads even without groq installed

    client = Groq(api_key=api_key)

    with audio_path.open("rb") as f:
        result = client.audio.transcriptions.create(
            file=(audio_path.name, f),
            model="whisper-large-v3",
            response_format="text",
        )

    # Groq returns a plain string when response_format="text"
    transcript: str = result if isinstance(result, str) else getattr(result, "text", "")
    transcript = transcript.strip()

    if len(transcript) < _MIN_TRANSCRIPT_CHARS:
        return ""
    return transcript

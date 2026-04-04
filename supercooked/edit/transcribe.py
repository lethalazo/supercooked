"""Whisper transcription with word-level timestamps.

Extends the pattern from create/caption.py but returns structured
Transcript models instead of SRT files. Designed for the editing
engine's briefing pipeline.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from supercooked.config import load_config

from .models import Transcript, TranscriptSegment, Word


async def transcribe(
    audio_path: Path | str,
    language: str | None = None,
) -> Transcript:
    """Transcribe an audio file and return a structured Transcript.

    Parameters
    ----------
    audio_path:
        Path to audio file (WAV preferred for Whisper).
    language:
        Language code (e.g. "en"). None = auto-detect.

    Returns
    -------
    Transcript with word-level timestamps.
    """
    audio_path = Path(audio_path)
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    config = load_config()
    whisper_model_name = config.tools.whisper_model

    try:
        import whisper
    except ImportError as exc:
        raise RuntimeError(
            "openai-whisper is not installed. "
            "Install it with: pip install openai-whisper"
        ) from exc

    # Load and run Whisper in a thread (CPU-heavy)
    model = await asyncio.to_thread(whisper.load_model, whisper_model_name)

    transcribe_kwargs: dict = {
        "word_timestamps": True,
    }
    if language:
        transcribe_kwargs["language"] = language

    result = await asyncio.to_thread(
        model.transcribe,
        str(audio_path),
        **transcribe_kwargs,
    )

    detected_language = result.get("language", language or "en")
    raw_segments = result.get("segments", [])

    segments = []
    total_words = 0

    for seg in raw_segments:
        text = seg.get("text", "").strip()
        if not text:
            continue

        words = []
        for w in seg.get("words", []):
            words.append(Word(
                word=w.get("word", "").strip(),
                start=round(w.get("start", 0.0), 3),
                end=round(w.get("end", 0.0), 3),
                confidence=round(w.get("probability", 1.0), 3),
            ))

        total_words += len(text.split())
        segments.append(TranscriptSegment(
            start=round(seg["start"], 3),
            end=round(seg["end"], 3),
            text=text,
            words=words,
        ))

    return Transcript(
        language=detected_language,
        word_count=total_words,
        segments=segments,
    )

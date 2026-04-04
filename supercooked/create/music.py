"""Background music synthesis via numpy.

Generates simple synthesized background music tracks using numpy signal
processing. Produces WAV files suitable for layering under voice-over
and video content. No external API - pure numpy synthesis.
"""

from __future__ import annotations

import uuid
import wave
from pathlib import Path

import numpy as np

from supercooked.config import OUTPUT_DIR

SAMPLE_RATE = 44100


def _output_dir_music() -> Path:
    """Ensure and return a music output directory."""
    d = OUTPUT_DIR / "_music"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _note_freq(note: str) -> float:
    """Convert a note name (e.g. 'C4', 'A#3') to frequency in Hz."""
    note_names = {
        "C": -9, "C#": -8, "Db": -8,
        "D": -7, "D#": -6, "Eb": -6,
        "E": -5,
        "F": -4, "F#": -3, "Gb": -3,
        "G": -2, "G#": -1, "Ab": -1,
        "A": 0, "A#": 1, "Bb": 1,
        "B": 2,
    }
    # Parse note and octave
    if len(note) >= 2 and note[-1].isdigit():
        if len(note) >= 3 and note[-2].isdigit():
            name = note[:-2]
            octave = int(note[-2:])
        else:
            name = note[:-1]
            octave = int(note[-1])
    else:
        name = note
        octave = 4

    semitone = note_names.get(name, 0)
    # A4 = 440 Hz
    return 440.0 * (2.0 ** ((octave - 4) + semitone / 12.0))


def _sine_wave(freq: float, duration: float, amplitude: float = 0.3) -> np.ndarray:
    """Generate a sine wave."""
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    return amplitude * np.sin(2 * np.pi * freq * t)


def _triangle_wave(freq: float, duration: float, amplitude: float = 0.3) -> np.ndarray:
    """Generate a triangle wave."""
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    return amplitude * (2 * np.abs(2 * (t * freq - np.floor(t * freq + 0.5))) - 1)


def _apply_envelope(signal: np.ndarray, attack: float = 0.01, release: float = 0.05) -> np.ndarray:
    """Apply a simple attack-release envelope to avoid clicks."""
    n = len(signal)
    attack_samples = int(SAMPLE_RATE * attack)
    release_samples = int(SAMPLE_RATE * release)

    envelope = np.ones(n)
    if attack_samples > 0 and attack_samples < n:
        envelope[:attack_samples] = np.linspace(0, 1, attack_samples)
    if release_samples > 0 and release_samples < n:
        envelope[-release_samples:] = np.linspace(1, 0, release_samples)
    return signal * envelope


def _reverb(signal: np.ndarray, decay: float = 0.3, delay_ms: float = 50) -> np.ndarray:
    """Apply a simple reverb effect by mixing a delayed, attenuated copy."""
    delay_samples = int(SAMPLE_RATE * delay_ms / 1000)
    output = signal.copy()
    if delay_samples < len(signal):
        output[delay_samples:] += decay * signal[:-delay_samples]
    return np.clip(output, -1.0, 1.0)


# --- Style definitions ---

_CHILL_PROGRESSION = [
    ("C3", "E3", "G3"),   # Cmaj
    ("A2", "C3", "E3"),   # Am
    ("F2", "A2", "C3"),   # Fmaj
    ("G2", "B2", "D3"),   # Gmaj
]

_LOFI_PROGRESSION = [
    ("D3", "F3", "A3"),   # Dm
    ("G2", "B2", "D3"),   # Gmaj
    ("C3", "E3", "G3"),   # Cmaj
    ("A2", "C3", "E3"),   # Am
]

_UPBEAT_PROGRESSION = [
    ("G3", "B3", "D4"),   # Gmaj
    ("C3", "E3", "G3"),   # Cmaj
    ("D3", "F#3", "A3"),  # Dmaj
    ("E3", "G3", "B3"),   # Em
]

_DRAMATIC_PROGRESSION = [
    ("A2", "C3", "E3"),   # Am
    ("F2", "A2", "C3"),   # Fmaj
    ("D2", "F2", "A2"),   # Dm
    ("E2", "G#2", "B2"),  # Emaj
]

_STYLE_MAP = {
    "chill": {
        "progression": _CHILL_PROGRESSION,
        "wave_fn": _sine_wave,
        "bpm": 80,
        "amplitude": 0.15,
        "reverb_decay": 0.4,
    },
    "lofi": {
        "progression": _LOFI_PROGRESSION,
        "wave_fn": _triangle_wave,
        "bpm": 70,
        "amplitude": 0.12,
        "reverb_decay": 0.5,
    },
    "upbeat": {
        "progression": _UPBEAT_PROGRESSION,
        "wave_fn": _sine_wave,
        "bpm": 120,
        "amplitude": 0.2,
        "reverb_decay": 0.2,
    },
    "dramatic": {
        "progression": _DRAMATIC_PROGRESSION,
        "wave_fn": _sine_wave,
        "bpm": 60,
        "amplitude": 0.25,
        "reverb_decay": 0.6,
    },
}


def _generate_chord(
    notes: tuple[str, ...],
    duration: float,
    wave_fn: callable,
    amplitude: float,
) -> np.ndarray:
    """Generate a chord by summing sine waves for each note."""
    chord = np.zeros(int(SAMPLE_RATE * duration))
    per_note_amp = amplitude / len(notes)
    for note in notes:
        freq = _note_freq(note)
        wave = wave_fn(freq, duration, per_note_amp)
        chord[: len(wave)] += wave
    return _apply_envelope(chord)


def _synthesize_track(
    duration_seconds: float,
    style_config: dict,
) -> np.ndarray:
    """Synthesize a full background music track."""
    progression = style_config["progression"]
    wave_fn = style_config["wave_fn"]
    bpm = style_config["bpm"]
    amplitude = style_config["amplitude"]
    reverb_decay = style_config["reverb_decay"]

    # Each chord lasts 2 beats
    beat_duration = 60.0 / bpm
    chord_duration = beat_duration * 2

    total_samples = int(SAMPLE_RATE * duration_seconds)
    track = np.zeros(total_samples)

    # Loop the chord progression to fill the duration
    position = 0
    chord_idx = 0
    while position < total_samples:
        chord_notes = progression[chord_idx % len(progression)]
        chord = _generate_chord(chord_notes, chord_duration, wave_fn, amplitude)

        end = min(position + len(chord), total_samples)
        track[position:end] += chord[: end - position]

        position += len(chord)
        chord_idx += 1

    # Apply reverb
    track = _reverb(track, decay=reverb_decay)

    # Fade in/out for the whole track
    fade_samples = int(SAMPLE_RATE * 2)  # 2-second fades
    if fade_samples < len(track) // 2:
        track[:fade_samples] *= np.linspace(0, 1, fade_samples)
        track[-fade_samples:] *= np.linspace(1, 0, fade_samples)

    # Normalize to prevent clipping
    peak = np.max(np.abs(track))
    if peak > 0:
        track = track / peak * 0.8

    return track


def _save_wav(signal: np.ndarray, path: Path) -> None:
    """Save a numpy float array as a 16-bit WAV file."""
    # Convert float [-1, 1] to int16
    int_signal = np.int16(signal * 32767)

    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)  # Mono
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(int_signal.tobytes())


async def generate_background_music(
    duration_seconds: float,
    style: str = "chill",
    output_path: Path | str | None = None,
) -> Path:
    """Generate simple synthesized background music.

    Parameters
    ----------
    duration_seconds:
        Length of the music track in seconds.
    style:
        Music style - "chill", "lofi", "upbeat", or "dramatic".
    output_path:
        Optional explicit output path. If None, auto-generates under output/_music/.

    Returns
    -------
    Path to the saved .wav file.

    Raises
    ------
    RuntimeError
        If the requested style is unknown or synthesis fails.
    """
    if style not in _STYLE_MAP:
        available = ", ".join(sorted(_STYLE_MAP.keys()))
        raise RuntimeError(
            f"Unknown music style '{style}'. Available styles: {available}"
        )

    if duration_seconds <= 0:
        raise RuntimeError(f"Duration must be positive, got {duration_seconds}")

    style_config = _STYLE_MAP[style]

    # Run synthesis in a thread - it's CPU-bound
    import asyncio

    try:
        track = await asyncio.to_thread(_synthesize_track, duration_seconds, style_config)
    except Exception as exc:
        raise RuntimeError(f"Music synthesis failed: {exc}") from exc

    # Determine output path
    if output_path is not None:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
    else:
        file_id = uuid.uuid4().hex[:12]
        out = _output_dir_music() / f"music_{style}_{file_id}.wav"

    try:
        await asyncio.to_thread(_save_wav, track, out)
    except Exception as exc:
        raise RuntimeError(f"Failed to save WAV file: {exc}") from exc

    return out

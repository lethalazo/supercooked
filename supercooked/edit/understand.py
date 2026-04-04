"""Scene detection, smart frame extraction, and audio analysis.

Gives the AI "eyes and ears" - extracts the minimum set of keyframes
needed to visually understand the footage, detects scene boundaries,
and maps speech/silence regions.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from .ffmpeg import (
    detect_scenes,
    detect_silence,
    extract_frame,
    measure_loudness,
    probe_source_info,
)
from .models import (
    AudioAnalysis,
    AudioRegion,
    FrameInfo,
    Scene,
    TranscriptSegment,
)


# ── Scene Detection ───────────────────────────────────────────────


async def detect_scene_boundaries(
    video_path: Path | str,
    threshold: float = 0.3,
) -> list[Scene]:
    """Detect scene changes and return Scene objects with boundaries.

    Uses FFmpeg's scdet filter. Falls back to a single scene if no
    changes are detected (e.g., a single continuous shot).
    """
    video_path = Path(video_path)
    source_info = await probe_source_info(video_path)
    total_duration = source_info.duration_seconds

    raw_scenes = await detect_scenes(video_path, threshold=threshold)

    scenes = []
    prev_end = 0.0

    for i, sc in enumerate(raw_scenes):
        t = sc["timestamp"]
        if t <= prev_end:
            continue
        scenes.append(Scene(
            id=i + 1,
            start=round(prev_end, 3),
            end=round(t, 3),
            duration=round(t - prev_end, 3),
            score=round(sc["score"], 3),
        ))
        prev_end = t

    # Add final scene
    if prev_end < total_duration:
        scenes.append(Scene(
            id=len(scenes) + 1,
            start=round(prev_end, 3),
            end=round(total_duration, 3),
            duration=round(total_duration - prev_end, 3),
            score=0.0,
        ))

    # If no scenes detected, treat whole video as one scene
    if not scenes:
        scenes = [Scene(
            id=1,
            start=0.0,
            end=round(total_duration, 3),
            duration=round(total_duration, 3),
        )]

    return scenes


# ── Smart Frame Extraction ────────────────────────────────────────


async def extract_smart_frames(
    video_path: Path | str,
    output_dir: Path | str,
    scenes: list[Scene],
    transcript_segments: list[TranscriptSegment] | None = None,
    max_frames: int = 150,
    interval: float = 30.0,
    dedup_window: float = 2.0,
    width: int = 960,
    height: int = 540,
) -> list[FrameInfo]:
    """Extract keyframes using the three-tier strategy.

    Tier 1: One frame per scene change (highest priority)
    Tier 2: One frame every `interval` seconds within long scenes
    Tier 3: One frame at each new speech segment start

    Deduplicates within `dedup_window` seconds. Caps at `max_frames`.

    Returns list of FrameInfo sorted by timestamp.
    """
    video_path = Path(video_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Collect candidate timestamps with tiers
    candidates: list[tuple[float, str, int | None]] = []  # (time, tier, scene_id)

    # Tier 1: scene changes
    for scene in scenes:
        candidates.append((scene.start, "scene_change", scene.id))

    # Tier 2: interval sampling within long scenes
    for scene in scenes:
        if scene.duration > interval * 1.5:
            t = scene.start + interval
            while t < scene.end - dedup_window:
                candidates.append((t, "interval", scene.id))
                t += interval

    # Tier 3: speech segment starts
    if transcript_segments:
        for seg in transcript_segments:
            candidates.append((seg.start, "speech", None))

    # Sort by timestamp
    candidates.sort(key=lambda x: x[0])

    # Deduplicate within window
    deduped: list[tuple[float, str, int | None]] = []
    for ts, tier, scene_id in candidates:
        if not deduped or (ts - deduped[-1][0]) >= dedup_window:
            deduped.append((ts, tier, scene_id))

    # Cap at max_frames (prioritize: scene_change > interval > speech)
    if len(deduped) > max_frames:
        tier_priority = {"scene_change": 0, "interval": 1, "speech": 2}
        deduped.sort(key=lambda x: (tier_priority.get(x[1], 3), x[0]))
        deduped = deduped[:max_frames]
        deduped.sort(key=lambda x: x[0])  # re-sort by time

    # Extract frames concurrently (batch to avoid overwhelming FFmpeg)
    batch_size = 10
    frames: list[FrameInfo] = []

    for batch_start in range(0, len(deduped), batch_size):
        batch = deduped[batch_start:batch_start + batch_size]
        tasks = []

        for i, (ts, tier, scene_id) in enumerate(batch):
            idx = batch_start + i + 1
            fname = f"frame_{idx:04d}.jpg"
            fpath = output_dir / fname

            tasks.append(_extract_and_record(
                video_path, ts, fpath, width, height, tier, scene_id,
                f"frames/{fname}",
            ))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, FrameInfo):
                frames.append(result)

    frames.sort(key=lambda f: f.timestamp)
    return frames


async def _extract_and_record(
    video_path: Path,
    timestamp: float,
    output_path: Path,
    width: int,
    height: int,
    tier: str,
    scene_id: int | None,
    relative_path: str,
) -> FrameInfo:
    """Extract a single frame and return its metadata."""
    await extract_frame(video_path, timestamp, output_path, width, height)
    return FrameInfo(
        path=relative_path,
        timestamp=round(timestamp, 3),
        scene=scene_id,
        tier=tier,
    )


# ── Audio Analysis ────────────────────────────────────────────────


async def analyze_audio(
    audio_path: Path | str,
    transcript_segments: list[TranscriptSegment] | None = None,
    silence_noise_db: float = -30,
    silence_min_duration: float = 0.5,
) -> AudioAnalysis:
    """Analyze audio characteristics: speech regions, silence, loudness.

    If transcript segments are provided, uses them for speech regions
    (more accurate than energy-based detection). Otherwise falls back
    to inverting silence detection.
    """
    audio_path = Path(audio_path)

    # Run silence detection and loudness measurement concurrently
    silence_task = detect_silence(
        audio_path,
        noise_db=silence_noise_db,
        min_duration=silence_min_duration,
    )
    loudness_task = measure_loudness(audio_path)

    raw_silences, loudness = await asyncio.gather(silence_task, loudness_task)

    silence_regions = [
        AudioRegion(start=round(s["start"], 3), end=round(s["end"], 3))
        for s in raw_silences
    ]

    # Speech regions from transcript (preferred) or silence inversion
    speech_regions: list[AudioRegion] = []
    if transcript_segments:
        for seg in transcript_segments:
            speech_regions.append(AudioRegion(
                start=round(seg.start, 3),
                end=round(seg.end, 3),
            ))
    else:
        # Invert silence to get speech - rough approximation
        from .ffmpeg import probe_source_info

        info = await probe_source_info(audio_path)
        total_duration = info.duration_seconds

        prev_end = 0.0
        for silence in silence_regions:
            if silence.start > prev_end + 0.1:
                speech_regions.append(AudioRegion(
                    start=round(prev_end, 3),
                    end=round(silence.start, 3),
                ))
            prev_end = silence.end
        if prev_end < total_duration - 0.1:
            speech_regions.append(AudioRegion(
                start=round(prev_end, 3),
                end=round(total_duration, 3),
            ))

    return AudioAnalysis(
        speech_regions=speech_regions,
        silence_regions=silence_regions,
        loudness_integrated=round(loudness["integrated"], 1),
        loudness_range=round(loudness["range"], 1),
        peak_db=round(loudness["peak"], 1),
    )

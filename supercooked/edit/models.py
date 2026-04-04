"""Pydantic models for the video editing engine.

Covers: projects, transcripts, scenes, audio analysis, briefings, EDLs,
color grades, export profiles, and text overlay specs.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ── Enums ─────────────────────────────────────────────────────────


class ProjectState(str, Enum):
    INIT = "init"
    INGESTED = "ingested"
    EDL_READY = "edl_ready"
    ASSEMBLED = "assembled"
    RENDERED = "rendered"


class TransitionType(str, Enum):
    CUT = "cut"
    DISSOLVE = "dissolve"
    FADE_IN = "fade_in"
    FADE_OUT = "fade_out"
    FADE_BLACK = "fade_black"


class SegmentType(str, Enum):
    VIDEO = "video"
    IMAGE = "image"  # static image held for duration


class TextStyle(str, Enum):
    TITLE = "title"
    LOWER_THIRD = "lower_third"
    CAPTION = "caption"
    WATERMARK = "watermark"


class TextPosition(str, Enum):
    TOP_LEFT = "top_left"
    TOP_CENTER = "top_center"
    TOP_RIGHT = "top_right"
    CENTER = "center"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_CENTER = "bottom_center"
    BOTTOM_RIGHT = "bottom_right"


# ── Transcript ────────────────────────────────────────────────────


class Word(BaseModel):
    """A single word with precise timing."""

    word: str
    start: float
    end: float
    confidence: float = 1.0


class TranscriptSegment(BaseModel):
    """A speech segment (sentence or phrase) from Whisper."""

    start: float
    end: float
    text: str
    words: list[Word] = Field(default_factory=list)
    scene: int | None = None


class Transcript(BaseModel):
    """Full transcript of a video's audio track."""

    language: str = "en"
    word_count: int = 0
    segments: list[TranscriptSegment] = Field(default_factory=list)


# ── Scenes ────────────────────────────────────────────────────────


class Scene(BaseModel):
    """A detected scene (visual change boundary)."""

    id: int
    start: float
    end: float
    duration: float = 0.0
    frame: str = ""  # relative path to keyframe image
    transcript_preview: str = ""
    score: float = 0.0  # scene change confidence


# ── Audio Analysis ────────────────────────────────────────────────


class AudioRegion(BaseModel):
    """A time region in the audio track."""

    start: float
    end: float


class AudioAnalysis(BaseModel):
    """Audio characteristics of the source footage."""

    speech_regions: list[AudioRegion] = Field(default_factory=list)
    silence_regions: list[AudioRegion] = Field(default_factory=list)
    loudness_integrated: float = -23.0  # LUFS
    loudness_range: float = 0.0
    peak_db: float = 0.0


# ── Frames ────────────────────────────────────────────────────────


class FrameInfo(BaseModel):
    """Metadata for an extracted keyframe."""

    path: str  # relative to project dir
    timestamp: float
    scene: int | None = None
    tier: str = ""  # scene_change, interval, speech


# ── Briefing ──────────────────────────────────────────────────────


class SourceInfo(BaseModel):
    """Source footage metadata from ffprobe."""

    file: str
    duration: str = ""
    duration_seconds: float = 0.0
    resolution: str = ""
    fps: float = 0.0
    codec: str = ""
    audio_codec: str = ""
    audio_channels: int = 0
    audio_sample_rate: int = 0
    file_size_mb: float = 0.0


class Briefing(BaseModel):
    """The complete AI-readable briefing — everything about the footage."""

    source: SourceInfo = Field(default_factory=SourceInfo)
    transcript: Transcript = Field(default_factory=Transcript)
    scenes: list[Scene] = Field(default_factory=list)
    audio_map: AudioAnalysis = Field(default_factory=AudioAnalysis)
    frames: list[FrameInfo] = Field(default_factory=list)


# ── EDL (Edit Decision List) ─────────────────────────────────────


class Transition(BaseModel):
    """A transition between segments."""

    type: TransitionType = TransitionType.CUT
    duration: float = 0.5


class TextOverlay(BaseModel):
    """A text overlay on a segment."""

    content: str
    style: TextStyle = TextStyle.LOWER_THIRD
    position: TextPosition = TextPosition.BOTTOM_CENTER
    at: float = 0.0  # seconds from segment start
    duration: float = 3.0
    font_size: int | None = None
    color: str = "#FFFFFF"
    fade_in: float = 0.3  # seconds to fade text in
    fade_out: float = 0.3  # seconds to fade text out


class SegmentAudio(BaseModel):
    """Audio settings for a single segment."""

    mute: bool = False
    volume: float = 1.0


class Segment(BaseModel):
    """A single edit segment — a clip from the source.

    For video sources: uses in/out points to cut a time range.
    For image sources: set type="image" and hold=<seconds> for how
    long the still should display. Optional zoom for Ken Burns effect.
    """

    id: str
    type: SegmentType = SegmentType.VIDEO
    source: str = ""  # source file (defaults to project source)
    in_point: float = Field(alias="in", default=0.0)
    out_point: float = Field(alias="out", default=0.0)
    hold: float = 0.0  # duration for image segments (seconds)
    zoom: float = 0.0  # Ken Burns zoom amount (0 = none, 0.05 = subtle)
    label: str = ""
    speed: float = 1.0
    transition_in: Transition | None = None
    transition_out: Transition | None = None
    audio: SegmentAudio = Field(default_factory=SegmentAudio)
    text: list[TextOverlay] = Field(default_factory=list)

    model_config = {"populate_by_name": True}

    @property
    def duration(self) -> float:
        """Duration of the segment after speed adjustment."""
        if self.type == SegmentType.IMAGE:
            return self.hold if self.hold > 0 else 5.0
        raw = self.out_point - self.in_point
        return raw / self.speed if self.speed > 0 else raw


class MusicTrack(BaseModel):
    """Background music configuration."""

    source: str
    volume: float = 0.20
    duck_under_speech: bool = True
    duck_level: float = 0.08
    fade_in: float = 2.0
    fade_out: float = 3.0


class DialogueTrack(BaseModel):
    """Dialogue audio configuration."""

    source: str = "original"
    volume: float = 1.0


class SFXEntry(BaseModel):
    """A sound effect placed at a specific time."""

    at: float
    source: str
    volume: float = 0.7
    duration: float | None = None  # None = full clip length


class AudioMix(BaseModel):
    """Complete audio mix specification."""

    music: MusicTrack | None = None
    dialogue: DialogueTrack = Field(default_factory=DialogueTrack)
    sfx: list[SFXEntry] = Field(default_factory=list)


class WatermarkConfig(BaseModel):
    """Watermark overlay settings."""

    text: str = ""
    position: TextPosition = TextPosition.BOTTOM_RIGHT
    opacity: float = 0.5
    font_size: int = 20


class GradeConfig(BaseModel):
    """Color grading configuration."""

    preset: str = "neutral"  # maps to grades.yaml
    brightness: float | None = None
    contrast: float | None = None
    saturation: float | None = None
    gamma: float | None = None
    custom_filter: str | None = None  # raw FFmpeg filter string


class OutputConfig(BaseModel):
    """Output format specification."""

    resolution: str = "1920x1080"
    fps: int = 30
    quality: str = "high"  # maps to exports.yaml
    format: str = "mp4"


class EDL(BaseModel):
    """Edit Decision List — the complete edit specification."""

    project: str
    source: str = ""
    output: OutputConfig = Field(default_factory=OutputConfig)
    grade: GradeConfig = Field(default_factory=GradeConfig)
    segments: list[Segment] = Field(default_factory=list)
    audio: AudioMix = Field(default_factory=AudioMix)
    watermark: WatermarkConfig = Field(default_factory=WatermarkConfig)

    @property
    def total_duration(self) -> float:
        """Estimated total duration of the edit."""
        return sum(s.duration for s in self.segments)


# ── Project ───────────────────────────────────────────────────────


class Project(BaseModel):
    """Project manifest — tracks state and source files."""

    name: str
    state: ProjectState = ProjectState.INIT
    source_video: str = ""
    source_audio: str | None = None
    sfx_dir: str | None = None
    created: str = ""
    settings: dict[str, Any] = Field(default_factory=dict)


# ── Presets ───────────────────────────────────────────────────────


class GradePreset(BaseModel):
    """A named color grading preset."""

    name: str
    description: str = ""
    brightness: float = 0.0
    contrast: float = 1.0
    saturation: float = 1.0
    gamma: float = 1.0
    filter_chain: str = ""  # raw FFmpeg filter string


class ExportProfile(BaseModel):
    """A named export quality/format profile."""

    name: str
    description: str = ""
    resolution: str = "1920x1080"
    fps: int = 30
    codec: str = "libx264"
    crf: int = 18
    audio_codec: str = "aac"
    audio_bitrate: str = "192k"
    pixel_format: str = "yuv420p"
    max_bitrate: str | None = None

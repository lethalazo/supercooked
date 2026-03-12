"""Pydantic models for all Super Cooked YAML schemas."""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


# --- Identity Schema ---


class PlatformConfig(BaseModel):
    enabled: bool = False
    handle: str = ""


class Platforms(BaseModel):
    youtube_shorts: PlatformConfig = PlatformConfig()
    x: PlatformConfig = PlatformConfig()
    instagram: PlatformConfig = PlatformConfig()
    tiktok: PlatformConfig = PlatformConfig()
    twitch: PlatformConfig = PlatformConfig()


class VoiceTraits(BaseModel):
    traits: list[str] = Field(default_factory=list)


class Boundaries(BaseModel):
    rules: list[str] = Field(default_factory=list)


class Persona(BaseModel):
    archetype: str = ""
    age_presentation: str = ""
    tone: str = ""
    perspective: str = ""
    voice_traits: list[str] = Field(default_factory=list)
    boundaries: list[str] = Field(default_factory=list)


class SeriesConfig(BaseModel):
    name: str
    format: str
    frequency: str


class PostingFrequency(BaseModel):
    shorts: str = ""
    images: str = ""
    tweets: str = ""


class ContentStrategy(BaseModel):
    posting_frequency: PostingFrequency = PostingFrequency()
    series: list[SeriesConfig] = Field(default_factory=list)


class BeingInfo(BaseModel):
    slug: str
    name: str
    tagline: str = ""
    created: str = ""


class Identity(BaseModel):
    being: BeingInfo
    persona: Persona = Persona()
    platforms: Platforms = Platforms()
    content_strategy: ContentStrategy = ContentStrategy()


# --- Face Config ---


class FaceConfig(BaseModel):
    provider: str = "imagen"
    style: str = "photorealistic"
    base_prompt: str = ""
    negative_prompt: str = ""
    reference_images: list[str] = Field(default_factory=list)
    consistency_seed: int | None = None


# --- Voice Config ---


class VoiceConfig(BaseModel):
    provider: str = "elevenlabs"
    voice_id: str = ""
    model: str = "eleven_multilingual_v2"
    stability: float = Field(default=0.5, ge=0.0, le=1.0)
    similarity_boost: float = Field(default=0.75, ge=0.0, le=1.0)
    style: float = Field(default=0.0, ge=0.0, le=1.0)


# --- Content Ideas ---


class IdeaStatus(str, Enum):
    BACKLOG = "backlog"
    IN_PROGRESS = "in_progress"
    DRAFTED = "drafted"
    GENERATED = "generated"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class ContentIdea(BaseModel):
    id: str
    title: str
    concept: str = ""
    template: str = ""
    status: IdeaStatus = IdeaStatus.BACKLOG
    created: datetime = Field(default_factory=datetime.now)
    tags: list[str] = Field(default_factory=list)
    content_types: list[str] = Field(default_factory=list)


class IdeasFile(BaseModel):
    ideas: list[ContentIdea] = Field(default_factory=list)


# --- Action Log ---


class ActionEntry(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.now)
    action: str
    platform: str = ""
    details: dict[str, Any] = Field(default_factory=dict)
    result: str = ""
    error: str | None = None


class ActionLog(BaseModel):
    date: str
    entries: list[ActionEntry] = Field(default_factory=list)


# --- Memory ---


class MemoryEntry(BaseModel):
    category: str
    insight: str
    confidence: float = 0.5
    learned_at: datetime = Field(default_factory=datetime.now)
    evidence: list[str] = Field(default_factory=list)


class Memory(BaseModel):
    learnings: list[MemoryEntry] = Field(default_factory=list)


# --- Session History ---


class SessionSummary(BaseModel):
    session_id: str
    started: datetime
    ended: datetime | None = None
    summary: str = ""
    actions_taken: list[str] = Field(default_factory=list)
    insights_gained: list[str] = Field(default_factory=list)


# --- Strategy Log ---


class StrategyDecision(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.now)
    decision: str
    reasoning: str = ""
    outcome: str | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)


class StrategyLog(BaseModel):
    decisions: list[StrategyDecision] = Field(default_factory=list)


# --- Audience ---


class AudienceProfile(BaseModel):
    total_followers: dict[str, int] = Field(default_factory=dict)
    demographics: dict[str, Any] = Field(default_factory=dict)
    top_interests: list[str] = Field(default_factory=list)
    engagement_patterns: dict[str, Any] = Field(default_factory=dict)


# --- Analytics ---


class PlatformStats(BaseModel):
    platform: str
    followers: int = 0
    total_views: int = 0
    total_likes: int = 0
    total_comments: int = 0
    engagement_rate: float = 0.0
    last_updated: datetime | None = None


class ContentPerformance(BaseModel):
    content_id: str
    title: str = ""
    platform: str = ""
    published_at: datetime | None = None
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    engagement_rate: float = 0.0


# --- Location (Life) ---


class Location(BaseModel):
    current: str = "the cloud"
    history: list[dict[str, Any]] = Field(default_factory=list)


# --- Credentials (encrypted) ---


class PlatformCredential(BaseModel):
    handle: str = ""
    password: str = ""
    oauth_token: str = ""
    oauth_secret: str = ""
    api_key: str = ""
    extra: dict[str, str] = Field(default_factory=dict)


# --- Global Config ---


class ApiKeys(BaseModel):
    anthropic: str = ""
    gemini: str = ""
    elevenlabs: str = ""
    late: str = ""


class VideoDefaults(BaseModel):
    resolution: str = "1080x1920"
    fps: int = 30
    format: str = "mp4"


class ImageDefaults(BaseModel):
    resolution: str = "1080x1080"
    format: str = "png"


class VoiceDefaults(BaseModel):
    model: str = "eleven_multilingual_v2"


class CaptionDefaults(BaseModel):
    style: str = "capcut"
    font: str = "Montserrat-Bold"
    font_size: int = 48
    color: str = "#FFFFFF"
    stroke_color: str = "#000000"
    stroke_width: int = 3


class Defaults(BaseModel):
    video: VideoDefaults = VideoDefaults()
    image: ImageDefaults = ImageDefaults()
    voice: VoiceDefaults = VoiceDefaults()
    captions: CaptionDefaults = CaptionDefaults()


class Paths(BaseModel):
    identities: str = "identities"
    output: str = "output"
    assets: str = "assets"


class ToolPaths(BaseModel):
    ffmpeg: str = "ffmpeg"
    whisper_model: str = "base"
    blender: str = "blender"


class GlobalConfig(BaseModel):
    api_keys: ApiKeys = ApiKeys()
    defaults: Defaults = Defaults()
    paths: Paths = Paths()
    tools: ToolPaths = ToolPaths()

"""Content creation modules — one external tool per capability.

Each sub-module wraps exactly one external API or tool:
- video:     Veo 3.1 via Gemini API (google-genai) — with extension for 15-20s clips
- image:     Nano Banana 2 via Gemini API (google-genai)
- voice:     ElevenLabs TTS (elevenlabs)
- caption:   OpenAI Whisper transcription + FFmpeg overlay
- music:     numpy synthesis (no external API)
- compose:   MoviePy/FFmpeg assembly
- selfie:    Nano Banana 2 character selfies (google-genai)
- thumbnail: Nano Banana 2 thumbnails (google-genai)
"""

from supercooked.create.caption import generate_captions, overlay_captions
from supercooked.create.compose import compose_image_post, compose_short, compose_story_image
from supercooked.create.image import generate_character_image, generate_image, generate_images
from supercooked.create.music import generate_background_music
from supercooked.create.selfie import take_selfie
from supercooked.create.thumbnail import generate_thumbnail
from supercooked.create.video import generate_video
from supercooked.create.voice import synthesize_speech

__all__ = [
    # Video
    "generate_video",
    # Image
    "generate_image",
    "generate_images",
    "generate_character_image",
    # Voice
    "synthesize_speech",
    # Captions
    "generate_captions",
    "overlay_captions",
    # Music
    "generate_background_music",
    # Composition
    "compose_short",
    "compose_image_post",
    "compose_story_image",
    # Selfie
    "take_selfie",
    # Thumbnail
    "generate_thumbnail",
]

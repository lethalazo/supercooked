# Super Cooked - Project Conventions

## What This Is
Platform for spawning and managing AI digital beings that live on the human internet.

## Architecture
- **Python package** (`supercooked/`): Identity management, content creation, publishing, CLI
- **FastAPI backend** (`api/`): REST + WebSocket API for the web dashboard
- **Next.js frontend** (`web/`): Material UI light theme dashboard

## Code Style
- Python 3.11+, type hints everywhere
- Pydantic v2 for all data models
- YAML for config/state files, Pydantic for validation
- Click for CLI, Rich for terminal output
- One external tool per capability - no fallbacks, fail loudly
- `httpx` for all HTTP calls (async)

## Content Pipeline (3-stage)
- `supercooked draft <slug> <idea-id>` - Claude writes script from backlog idea → DRAFTED
- `supercooked generate <slug> <idea-id>` - Creates media per content_type → GENERATED
- `supercooked publish <slug> <idea-id>` - Pushes to platforms → PUBLISHED
- Pipeline files: `identities/<slug>/content/drafts/<id>/` (script.yaml, metadata.yaml, media files)
- Ideas stored in: `identities/<slug>/content/ideas.yaml` (file-locked reads/writes)

## Key Patterns
- Identities live in `identities/<slug>/` with full state dirs
- Credentials are Fernet-encrypted in `credentials/vault.yaml`
- Every being action is logged to `state/action_log/<date>.yaml`
- Claude API = being's brain (personality, writing). Gemini API = production (video, images)
- ElevenLabs = voice synthesis. NumPy = background music. Pillow = image composition.

## File Conventions
- Identity configs: `identity.yaml` (Pydantic-validated)
- State files: YAML with timestamps
- Content: `content/drafts/<id>/` during creation, `content/published/<id>/` after publish
- Config: `supercooked.yaml` at project root (API keys, defaults, paths, tools)

## API Ports
- Backend: `uvicorn api.main:app --port 8888`
- Frontend: `cd web && npx next dev --port 4444`
- CORS configured for localhost:3000, localhost:4444

## Testing
- `pytest` for unit tests
- Run: `cd /Users/arsalan/Workspace/supercooked && python -m pytest`

## CLI
- Entry point: `supercooked` (installed via pyproject.toml)
- Dev run: `python -m supercooked.cli`
- Pipeline: `supercooked draft <slug> <idea-id>` → `supercooked generate <slug> <idea-id>` → `supercooked publish <slug> <idea-id>`
- Ideas: `supercooked idea add <slug> <title> <concept> --types "video,image,audio"`
- Ideation: `supercooked ideate <slug>` (AI-generated ideas via Claude)

## Video Editing Engine (`supercooked/edit/`)

AI-assisted video editing - ingest raw footage, produce a structured briefing, write an EDL, render a polished video.

### Edit Commands
```bash
# Vlog editing (camera footage → polished video)
supercooked edit init <name> <video> [--audio <bg.mp3>] [--sfx <dir>]
supercooked edit ingest <name>          # Transcribe + scenes + frames + audio analysis
supercooked edit briefing <name>        # Display the structured briefing

# Compose (images + clips + text + audio → typography video, no voiceover)
supercooked edit compose <name> <file1> <file2> ... [--audio <bg.mp3>]

# Shared (both workflows)
supercooked edit run <name>             # Execute EDL → assembled video
supercooked edit preview <name> --seg 3 # Quick preview of one segment
supercooked edit render <name>          # Final quality render
supercooked edit status <name>          # Show project state
```

### Two Workflows

**Vlog editing** (`init` → `ingest` → write EDL → `run` → `render`):
For raw camera footage. Ingest gives you a briefing (transcript, scenes, frames).
You read the briefing, write an EDL selecting the best parts, and render.

**Compose** (`compose` → write EDL → `run` → `render`):
For typography/aesthetic videos from images, short clips, and background audio.
No voiceover, no ingest needed. You provide the sources, write an EDL with
image segments (`type: image`, `hold: 5.0`), text overlays, transitions,
and bg music. Think: IG reels, quote cards, product teasers.

### Edit Project Structure
```
output/edit/<project-name>/
  project.yaml                   # Manifest: sources, state
  sources/                       # Symlinks to raw footage / images / audio
  analysis/                      # (vlog workflow only)
    transcript.json              # Word-level timestamped transcript
    scenes.json                  # Scene boundaries
    audio_analysis.json          # Speech/silence/loudness map
    frames/                      # Keyframes (960x540 JPEG)
    frames_index.json            # Frame metadata
    briefing.yaml                # THE BRIEFING - everything AI needs
  edl.yaml                       # Edit Decision List (AI or hand-written)
  segments/                      # Intermediate rendered segments
  overlays/                      # Generated text overlay PNGs
  assembled.mp4                  # Cut + concat output
  final.mp4                      # Rendered output
```

### Key Concepts
- **Briefing**: Structured YAML giving AI complete understanding of footage (transcript, scenes, frames, audio map)
- **EDL**: Edit Decision List - validated YAML specifying cuts, speed, transitions, text, audio, grade
- **Image Segments**: `type: image` with `hold: <seconds>` - static image becomes video clip. Optional `zoom: 0.03` for Ken Burns effect
- **Text Overlays**: Titles, lower thirds, captions with per-overlay `fade_in`/`fade_out` control
- **Music Fade**: `fade_in`/`fade_out` on `MusicTrack` - music fades in/out smoothly
- **Smart Frames**: Three-tier extraction (scene changes → interval → speech starts), capped at ~150 frames
- **Grade Presets**: moody, warm, cinematic, clean, neutral (in `edit/presets/grades.yaml`)
- **Export Profiles**: youtube, youtube-4k, ig-reel, ig-story, tiktok, draft (in `edit/presets/exports.yaml`)

### EDL Example (Compose - typography video)
```yaml
project: my-reel
output:
  resolution: 1080x1920   # vertical for IG
  fps: 30

grade:
  preset: moody

segments:
  - id: bg1
    type: image
    source: sources/texture.jpg
    hold: 5.0
    zoom: 0.03
    text:
      - content: "In the name of Allah"
        style: title
        position: center
        at: 0.5
        duration: 4.0
        fade_in: 0.8
        fade_out: 0.5

  - id: clip1
    source: sources/nature.mp4
    in: 0
    out: 8
    speed: 0.5
    audio: {mute: true}
    transition_out: {type: dissolve, duration: 0.5}
    text:
      - content: "Seek knowledge"
        style: lower_third
        at: 1.0
        duration: 3.0

  - id: bg2
    type: image
    source: sources/marble.png
    hold: 4.0
    text:
      - content: "nooraana.uk"
        style: watermark
        position: bottom_right
        at: 0.0
        duration: 4.0

audio:
  music:
    source: sources/nasheed.mp3
    volume: 0.25
    fade_in: 2.0
    fade_out: 3.0
    duck_under_speech: false
  dialogue:
    source: none

watermark:
  text: "@nooraana"
  opacity: 0.4
```

### Workflow (POC - Claude Code as agent)
1. `edit init` or `edit compose` - create project, symlink sources
2. `edit ingest` - (vlog only) Whisper transcription, scene detection, frame extraction
3. Read the briefing + look at keyframes to understand the footage
4. Write `edl.yaml` - select segments, set transitions, text, grade
5. `edit run` - execute the EDL
6. `edit render` - final encode with export profile

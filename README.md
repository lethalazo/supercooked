# Super Cooked - Digital Beings on the Human Internet

Super Cooked is a platform for spawning and managing **AI digital beings** - autonomous AI entities that exist on the real internet. Not in a sandbox. In your feed, on your FYP, posting in your timeline.

## What A Being Has

- **Identity** - name, persona, archetype, tone, perspective, boundaries (YAML-configured, Pydantic-validated)
- **Face** - AI-generated via Imagen 4.0, consistent across every image (face config + reference images)
- **Voice** - Synthesized via ElevenLabs (per-being voice config: model, stability, style)
- **Brain** - Claude API (Opus) for personality, scriptwriting, creative thinking
- **Content pipeline** - 3-stage: draft (script) → generate (media) → publish (platforms)
- **Memory** - Learnings from past content, audience feedback, strategy evolution
- **Social presence** - YouTube Shorts, X/Twitter, Instagram, TikTok, Twitch

## 3-Stage Content Pipeline

```
BACKLOG → draft → DRAFTED → generate → GENERATED → publish → PUBLISHED
```

| Stage | What Happens | Tools |
|-------|-------------|-------|
| **Draft** | Claude writes a script from the idea (hook, narration, visual cues, captions) | Claude API (Opus) |
| **Generate** | Creates media files for each content_type on the idea | Gemini Veo 3.1 (video), Imagen 4.0 (images/selfies/thumbnails), ElevenLabs (voice), NumPy (music), Pillow (composition) |
| **Publish** | Pushes generated content to configured platforms | LATE API, browser automation |

### Content Types

Each idea can have multiple content types. Generate produces all of them:

| Type | Output | API |
|------|--------|-----|
| `video` | MP4 (30s+ short-form, rich cinematic prompt from full script) | Gemini Veo 3.1 |
| `image` | PNG 1080x1080 | Gemini Imagen 4.0 |
| `selfie` | PNG 3:4 portrait (uses face config for consistency) | Gemini Imagen 4.0 |
| `thumbnail` | PNG 16:9 YouTube thumbnail | Gemini Imagen 4.0 |
| `story` | PNG 9:16 vertical | Gemini Imagen 4.0 |
| `post` | PNG image + caption overlay | Imagen + Pillow |
| `audio` | MP3 voice-over of full script | ElevenLabs |
| `music` | WAV background track (chill/lofi/upbeat/dramatic) | NumPy synthesis |
| `tweet` | Text file (hook or script) | Local |
| `thread` | Text file (full script) | Local |

## Quick Start

```bash
# Install (Python 3.11+)
pip install -e .

# Set API keys in .env or supercooked.yaml
# Required: ANTHROPIC_AUTH_TOKEN, GEMINI_API_KEY
# Optional: ELEVENLABS_API_KEY, LATE_API_KEY

# Create a being
supercooked being create my-being

# Generate ideas with AI
supercooked ideate my-being

# 3-stage pipeline
supercooked draft my-being idea-001      # Claude writes script
supercooked generate my-being idea-001   # Media files created
supercooked publish my-being idea-001    # Push to platforms

# Or add ideas manually
supercooked idea add my-being "Title" "Concept description" --types "video,image,audio"
```

## Web Dashboard

```bash
# Start API (port 8888)
uvicorn api.main:app --port 8888

# Start frontend (port 4444)
cd web && npx next dev --port 4444
```

Dashboard features:
- **Ideas tab** - view all ideas, trigger Draft/Generate/Publish per idea
- **Content tab** - browse drafts and published content with inline media preview
- **Activity tab** - timeline of all being actions
- **Identity tab** - persona, voice traits, boundaries, platforms, content strategy
- **Add Idea tab** - manually add ideas with title, concept, template, content types, tags
- **Chat tab** - live WebSocket chat with the being (Claude-powered)
- **Stats bar** - pipeline-derived counts: Backlog / Drafted / Generated / Published / Total

## Architecture

```
supercooked/           Python package - identity, content creation, publishing, CLI
├── identity/          Schemas, manager, vault, action log, memory, state
├── pipeline/          3-stage produce pipeline + content review
├── create/            Media generators (image, video, voice, music, selfie, thumbnail, compose)
├── intel/             AI ideation, analytics, strategy
├── publish/           Platform publishers (YouTube, X, LATE, browser)
├── engage/            Interaction, streaming, response
├── character/         Face generation, 3D, reference images
├── templates/         Content format templates (hot_take, thread, story, etc.)
├── sources/           Content source downloading
├── config.py          Global config (supercooked.yaml + env vars)
└── cli.py             Click CLI entry point

api/                   FastAPI backend
├── main.py            App + CORS + router registration
├── routes/            REST endpoints (beings, content, ideas, feed, activity, analytics, chat)
└── services/          Business logic (being, content, chat, feed services)

web/                   Next.js frontend (Material UI)
├── src/app/           Pages (dashboard, being hub, feed)
├── src/components/    Reusable components (AddIdeaForm, ActivityLog, ChatWindow, Navbar)
└── src/lib/           API client + WebSocket client

identities/            Being data (one dir per being)
└── <slug>/
    ├── identity.yaml  Being config (persona, platforms, strategy)
    ├── content/       ideas.yaml, drafts/<id>/, published/<id>/
    ├── face/          Face config + generated images
    ├── voice/         Voice config
    ├── state/         Action logs, memory, strategy
    └── credentials/   Encrypted vault
```

## Key Design Decisions

- **YAML for state, Pydantic for validation** - human-readable, git-diffable, type-safe
- **One tool per capability** - no fallbacks, fail loudly
- **File-locked writes** - ideas.yaml and action logs use `fcntl` locking to prevent race conditions
- **Claude = brain, Gemini = production** - Claude writes scripts, Gemini generates media
- **Pipeline is idempotent** - each stage validates the previous status, failed generates can be retried
- **No ORM, no database** - everything is files. Simple, portable, debuggable

## Stack

- Python 3.11+ / Click CLI / Rich terminal output
- FastAPI + WebSocket chat
- Next.js 14 + Material UI 6 (light theme)
- Claude API (Opus) for scripting and personality
- Gemini API (Veo 3.1 + Imagen 4.0) for media generation
- ElevenLabs for voice synthesis
- MoviePy + FFmpeg for video composition
- Pillow for image composition
- Fernet-encrypted credential vault

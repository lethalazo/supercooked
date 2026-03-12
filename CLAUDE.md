# Super Cooked — Project Conventions

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
- One external tool per capability — no fallbacks, fail loudly
- `httpx` for all HTTP calls (async)

## Content Pipeline (3-stage)
- `supercooked draft <slug> <idea-id>` — Claude writes script from backlog idea → DRAFTED
- `supercooked generate <slug> <idea-id>` — Creates media per content_type → GENERATED
- `supercooked publish <slug> <idea-id>` — Pushes to platforms → PUBLISHED
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

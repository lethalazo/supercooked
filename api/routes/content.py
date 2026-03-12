"""Routes for content CRUD and render triggers."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from supercooked.config import IDENTITIES_DIR

from api.services.content_service import ContentService

router = APIRouter()
service = ContentService()


class CreateContentRequest(BaseModel):
    template: str
    title: str = ""
    concept: str = ""
    caption: str = ""


class AddIdeaRequest(BaseModel):
    title: str
    concept: str
    template: str = ""
    content_types: list[str] = []
    tags: list[str] = []


class GenerateIdeasRequest(BaseModel):
    count: int = 5
    focus: str | None = None


@router.get("/beings/{slug}/content")
async def list_content(slug: str):
    """List all content for a being."""
    try:
        return service.list_content(slug)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Being not found: {slug}")


@router.get("/beings/{slug}/content/{content_id}")
async def get_content(slug: str, content_id: str):
    """Get a specific content item."""
    try:
        return service.get_content(slug, content_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Content not found")


@router.post("/beings/{slug}/content/create", status_code=201)
async def create_content(slug: str, req: CreateContentRequest):
    """Trigger content creation for a being."""
    try:
        result = await service.create_content(
            slug=slug,
            template=req.template,
            title=req.title,
            concept=req.concept,
            caption=req.caption,
        )
        return result
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Being not found: {slug}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/beings/{slug}/ideas")
async def list_ideas(slug: str):
    """List content ideas for a being."""
    try:
        return service.list_ideas(slug)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Being not found: {slug}")


@router.post("/beings/{slug}/ideas", status_code=201)
async def add_idea(slug: str, req: AddIdeaRequest):
    """Manually add an idea to the backlog."""
    import uuid
    from datetime import datetime

    from supercooked.identity.schemas import ContentIdea

    try:
        idea = ContentIdea(
            id=f"idea-{uuid.uuid4().hex[:8]}",
            title=req.title,
            concept=req.concept,
            template=req.template,
            content_types=req.content_types,
            tags=req.tags,
            created=datetime.now(),
        )
        service.append_ideas(slug, [idea])
        return {"slug": slug, "idea": idea.model_dump(mode="json")}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Being not found: {slug}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/beings/{slug}/ideas/generate", status_code=201)
async def generate_ideas(slug: str, req: GenerateIdeasRequest):
    """Generate new content ideas using AI."""
    from supercooked.intel.ideate import generate_ideas as _generate

    try:
        ideas = await _generate(slug, count=req.count, focus=req.focus)
        # Save to ideas file
        service.append_ideas(slug, ideas)
        return {"slug": slug, "generated": len(ideas), "ideas": [i.model_dump(mode="json") for i in ideas]}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Being not found: {slug}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/beings/{slug}/ideas/{idea_id}/draft", status_code=201)
async def draft_idea(slug: str, idea_id: str):
    """Stage 1: Generate a script/draft from a backlog idea."""
    from supercooked.pipeline.produce import produce_content

    try:
        result = await produce_content(slug, idea_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/beings/{slug}/ideas/{idea_id}/generate", status_code=201)
async def generate_idea(slug: str, idea_id: str):
    """Stage 2: Generate media files from a drafted idea."""
    from supercooked.pipeline.produce import generate_content

    try:
        result = await generate_content(slug, idea_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/beings/{slug}/ideas/{idea_id}/regenerate", status_code=201)
async def regenerate_idea(slug: str, idea_id: str):
    """Re-generate media files for an already-generated idea."""
    from supercooked.pipeline.produce import regenerate_content

    try:
        result = await regenerate_content(slug, idea_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/beings/{slug}/ideas/{idea_id}/publish", status_code=201)
async def publish_idea(slug: str, idea_id: str):
    """Stage 3: Publish generated content to platforms."""
    from supercooked.pipeline.produce import publish_content

    try:
        result = await publish_content(slug, idea_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/beings/{slug}/face/generate", status_code=201)
async def generate_face(slug: str):
    """Generate a profile picture / face image for the being."""
    from supercooked.character.face import generate_face as _generate_face

    try:
        path = await _generate_face(slug)
        return {"slug": slug, "path": str(path), "filename": path.name}
    except (FileNotFoundError, RuntimeError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/beings/{slug}/face")
async def get_face(slug: str):
    """Get the latest generated face image for the being."""
    face_dir = IDENTITIES_DIR / slug / "face" / "generated"
    if not face_dir.exists():
        raise HTTPException(status_code=404, detail="No face images generated")

    images = sorted(
        [p for p in face_dir.iterdir() if p.suffix.lower() in (".png", ".jpg", ".jpeg")],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not images:
        raise HTTPException(status_code=404, detail="No face images generated")

    return FileResponse(images[0], media_type="image/png")


MEDIA_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".mp4": "video/mp4",
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".txt": "text/plain",
    ".srt": "text/plain",
}


@router.get("/beings/{slug}/content/{content_id}/files/{filename}")
async def serve_content_file(slug: str, content_id: str, filename: str):
    """Serve a media file from a content directory."""
    # Prevent path traversal
    safe_name = Path(filename).name
    if safe_name != filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    base = IDENTITIES_DIR / slug / "content"

    # Check published first (canonical), then drafts
    for subdir in ["published", "drafts"]:
        file_path = base / subdir / content_id / safe_name
        if file_path.is_file():
            suffix = file_path.suffix.lower()
            media_type = MEDIA_TYPES.get(suffix, "application/octet-stream")
            return FileResponse(file_path, media_type=media_type)

    raise HTTPException(status_code=404, detail="File not found")

"""3-stage content production pipeline.

Stage 1 (Draft):    backlog → drafted     - generate script via Claude
Stage 2 (Generate): drafted → generated   - create media files
Stage 3 (Publish):  generated → published - push to platforms
"""

from __future__ import annotations

import fcntl
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from supercooked.config import CLAUDE_MODEL, IDENTITIES_DIR, get_anthropic_client
from supercooked.create.prompt_gen import MediaPrompts, generate_media_prompts
from supercooked.identity.action_log import log_action
from supercooked.identity.manager import get_voice_md, load_identity
from supercooked.identity.schemas import ContentIdea, IdeaStatus, IdeasFile
from supercooked.pipeline.review import review_content

logger = logging.getLogger(__name__)


def _ideas_path(slug: str) -> Path:
    """Return the ideas file path for a given identity."""
    return IDENTITIES_DIR / slug / "content" / "ideas.yaml"


def _load_ideas(slug: str) -> IdeasFile:
    """Load content ideas file."""
    path = _ideas_path(slug)
    if not path.exists():
        return IdeasFile()
    with open(path) as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_SH)
        try:
            data = yaml.safe_load(f) or {}
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    return IdeasFile(**data)


def _save_ideas(slug: str, ideas_file: IdeasFile) -> None:
    """Save content ideas file with exclusive lock."""
    path = _ideas_path(slug)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            yaml.dump(ideas_file.model_dump(mode="json"), f, default_flow_style=False, sort_keys=False)
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def _get_idea_by_id(ideas_file: IdeasFile, idea_id: str) -> ContentIdea | None:
    """Find an idea by ID."""
    for idea in ideas_file.ideas:
        if idea.id == idea_id:
            return idea
    return None


def _update_idea_status(slug: str, idea_id: str, status: IdeaStatus) -> None:
    """Update the status of an idea."""
    ideas_file = _load_ideas(slug)
    for idea in ideas_file.ideas:
        if idea.id == idea_id:
            idea.status = status
            break
    _save_ideas(slug, ideas_file)


async def _generate_script(
    slug: str,
    idea: ContentIdea,
    voice_md: str,
    identity_name: str,
) -> dict[str, Any]:
    """Generate a content script using Claude API.

    Returns a dict with: script, visual_cues, duration_estimate, hook.
    """
    system_prompt = f"""You are the scriptwriter for {identity_name}, a digital being.

{voice_md}

Write content scripts in {identity_name}'s voice. Scripts should be
engaging, match the being's personality, and work for short-form content.

Return your script as JSON with this exact format:
{{
  "hook": "Opening hook line (first 3 seconds)",
  "script": "Full narration script",
  "visual_cues": ["Description of visual for each section"],
  "duration_estimate_seconds": 30,
  "captions_text": "Clean text for captions overlay"
}}

Return ONLY the JSON. No other text.
"""

    user_prompt = (
        f"Write a script for this content idea:\n"
        f"Title: {idea.title}\n"
        f"Concept: {idea.concept}\n"
        f"Template/Format: {idea.template}\n"
        f"Tags: {', '.join(idea.tags)}"
    )

    client = get_anthropic_client()
    response = await client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=2000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    raw = response.content[0].text.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start == -1 or end == 0:
            raise RuntimeError(f"Claude returned non-JSON script:\n{raw[:500]}")
        return json.loads(raw[start:end])


def _create_draft_dir(slug: str, idea_id: str) -> Path:
    """Create and return the draft directory for a content piece."""
    draft_dir = IDENTITIES_DIR / slug / "content" / "drafts" / idea_id
    draft_dir.mkdir(parents=True, exist_ok=True)
    return draft_dir


async def produce_content(
    slug: str,
    idea_id: str,
) -> dict[str, Any]:
    """Stage 1 - Draft: generate a script from a backlog idea.

    Args:
        slug: Identity slug.
        idea_id: ID of the content idea to draft.

    Returns:
        Dict with draft_dir, script, and review.

    Raises:
        ValueError: If idea not found or not in backlog status.
        RuntimeError: If script generation fails.
    """
    identity = load_identity(slug)
    voice_md = get_voice_md(slug)
    ideas_file = _load_ideas(slug)

    idea = _get_idea_by_id(ideas_file, idea_id)
    if idea is None:
        raise ValueError(
            f"Content idea '{idea_id}' not found for identity '{slug}'. "
            f"Generate ideas first with: supercooked ideate {slug}"
        )

    if idea.status not in (IdeaStatus.BACKLOG, IdeaStatus.IN_PROGRESS):
        raise ValueError(
            f"Idea '{idea_id}' is in '{idea.status.value}' status. "
            "Only backlog ideas can be drafted."
        )

    _update_idea_status(slug, idea_id, IdeaStatus.IN_PROGRESS)

    try:
        script_data = await _generate_script(
            slug, idea, voice_md, identity.being.name
        )

        draft_dir = _create_draft_dir(slug, idea_id)

        with open(draft_dir / "script.yaml", "w") as f:
            yaml.dump(script_data, f, default_flow_style=False, sort_keys=False)

        metadata = {
            "idea_id": idea_id,
            "title": idea.title,
            "concept": idea.concept,
            "template": idea.template,
            "tags": idea.tags,
            "content_types": idea.content_types,
            "created_at": datetime.now().isoformat(),
            "slug": slug,
            "status": "drafted",
            "script_generated": True,
            "hook": script_data.get("hook", ""),
            "duration_estimate": script_data.get("duration_estimate_seconds", 0),
        }
        with open(draft_dir / "metadata.yaml", "w") as f:
            yaml.dump(metadata, f, default_flow_style=False, sort_keys=False)

        captions_text = script_data.get("captions_text", script_data.get("script", ""))
        with open(draft_dir / "captions.txt", "w") as f:
            f.write(captions_text)

        review_result = review_content(slug, draft_dir)

        _update_idea_status(slug, idea_id, IdeaStatus.DRAFTED)

    except Exception:
        # Roll back to backlog so the idea isn't stuck in_progress
        _update_idea_status(slug, idea_id, IdeaStatus.BACKLOG)
        raise

    result = {
        "idea_id": idea_id,
        "title": idea.title,
        "draft_dir": str(draft_dir),
        "script": script_data,
        "review": review_result,
        "status": "drafted",
    }

    log_action(
        slug,
        action="draft_content",
        details={
            "idea_id": idea_id,
            "title": idea.title,
            "template": idea.template,
            "draft_dir": str(draft_dir),
        },
        result=f"Drafted script for '{idea.title}'",
    )

    return result


async def regenerate_content(
    slug: str,
    idea_id: str,
) -> dict[str, Any]:
    """Re-generate media files for an already-generated idea.

    Resets the idea status to DRAFTED, cleans old media files from the
    draft directory, then runs generate_content() again.
    """
    ideas_file = _load_ideas(slug)
    idea = _get_idea_by_id(ideas_file, idea_id)
    if idea is None:
        raise ValueError(f"Content idea '{idea_id}' not found for identity '{slug}'.")
    if idea.status not in (IdeaStatus.GENERATED, IdeaStatus.DRAFTED):
        raise ValueError(
            f"Idea '{idea_id}' is in '{idea.status.value}' status. "
            "Only drafted or generated ideas can be re-generated."
        )

    # Clean old media files from draft dir (keep script.yaml, metadata.yaml, captions.txt)
    draft_dir = IDENTITIES_DIR / slug / "content" / "drafts" / idea_id
    if draft_dir.exists():
        keep = {"script.yaml", "metadata.yaml", "captions.txt"}
        for f in draft_dir.iterdir():
            if f.is_file() and f.name not in keep:
                f.unlink()

    # Reset to drafted so generate_content() will accept it
    _update_idea_status(slug, idea_id, IdeaStatus.DRAFTED)

    return await generate_content(slug, idea_id)


async def generate_content(
    slug: str,
    idea_id: str,
) -> dict[str, Any]:
    """Generate media files from a drafted idea (Stage 2).

    Reads the draft's script.yaml for prompts, then loops through the idea's
    content_types calling the appropriate create module for each.

    Args:
        slug: Identity slug.
        idea_id: ID of the drafted content idea.

    Returns:
        Dict with generated files list and status.

    Raises:
        ValueError: If idea not found or not in drafted status.
    """
    ideas_file = _load_ideas(slug)
    idea = _get_idea_by_id(ideas_file, idea_id)
    if idea is None:
        raise ValueError(f"Content idea '{idea_id}' not found for identity '{slug}'.")
    if idea.status != IdeaStatus.DRAFTED:
        raise ValueError(
            f"Idea '{idea_id}' is in '{idea.status.value}' status, expected 'drafted'."
        )

    draft_dir = IDENTITIES_DIR / slug / "content" / "drafts" / idea_id
    script_path = draft_dir / "script.yaml"
    if not script_path.exists():
        raise ValueError(f"No script found at {script_path}. Run draft first.")

    with open(script_path) as f:
        script_data = yaml.safe_load(f) or {}

    content_types = idea.content_types
    if not content_types:
        raise ValueError(
            f"Idea '{idea_id}' has no content_types. "
            "Add content_types to the idea before generating."
        )

    # Generate optimized media prompts via Claude (or use cached)
    cached_prompts = script_data.get("media_prompts")
    if cached_prompts:
        media_prompts = MediaPrompts(**cached_prompts)
    else:
        media_prompts = await generate_media_prompts(
            slug, idea, script_data, content_types
        )
        # Cache prompts in script.yaml so regeneration doesn't re-call Claude
        script_data["media_prompts"] = media_prompts.model_dump()
        with open(script_path, "w") as f:
            yaml.dump(script_data, f, default_flow_style=False, sort_keys=False)

    generated_files: list[dict[str, str]] = []
    errors: list[dict[str, str]] = []

    for ctype in content_types:
        try:
            file_info = await _generate_for_type(
                ctype, slug, idea, script_data, draft_dir, media_prompts
            )
            if file_info:
                if isinstance(file_info, list):
                    generated_files.extend(file_info)
                else:
                    generated_files.append(file_info)
        except Exception as e:
            logger.error("Failed to generate %s for %s: %s", ctype, idea_id, e)
            errors.append({"content_type": ctype, "error": str(e)})

    # Update metadata with generated files
    meta_path = draft_dir / "metadata.yaml"
    if meta_path.exists():
        with open(meta_path) as f:
            metadata = yaml.safe_load(f) or {}
    else:
        metadata = {}

    metadata["files"] = generated_files
    metadata["errors"] = errors
    metadata["generated_at"] = datetime.now().isoformat()

    # Only advance to GENERATED if at least one file was produced
    if generated_files:
        metadata["status"] = "generated"
        with open(meta_path, "w") as f:
            yaml.dump(metadata, f, default_flow_style=False, sort_keys=False)
        _update_idea_status(slug, idea_id, IdeaStatus.GENERATED)
        final_status = "generated"
    else:
        # All types failed - stay in drafted so user can retry
        metadata["status"] = "drafted"
        with open(meta_path, "w") as f:
            yaml.dump(metadata, f, default_flow_style=False, sort_keys=False)
        final_status = "drafted"
        logger.error("All content types failed for %s, staying in drafted", idea_id)

    log_action(
        slug,
        action="generate_content",
        details={
            "idea_id": idea_id,
            "title": idea.title,
            "content_types": content_types,
            "files_generated": len(generated_files),
            "errors": len(errors),
        },
        result=f"Generated {len(generated_files)} files for '{idea.title}'",
    )

    return {
        "idea_id": idea_id,
        "title": idea.title,
        "status": final_status,
        "files": generated_files,
        "errors": errors,
        "draft_dir": str(draft_dir),
    }


async def _generate_for_type(
    content_type: str,
    slug: str,
    idea: ContentIdea,
    script_data: dict[str, Any],
    draft_dir: Path,
    media_prompts: MediaPrompts | None = None,
) -> dict[str, str] | list[dict[str, str]] | None:
    """Generate a single content type and return file info."""
    visual_cues = script_data.get("visual_cues", [])
    visual_prompt = visual_cues[0] if visual_cues else idea.concept
    script_text = script_data.get("script", "")
    hook = script_data.get("hook", "")
    captions_text = script_data.get("captions_text", script_text)
    duration = script_data.get("duration_estimate_seconds", 30)

    # Load face config for negative_prompt / style
    face_negative = ""
    face_style = ""
    try:
        from supercooked.config import IDENTITIES_DIR as _ID_DIR
        import yaml as _yaml
        _fc_path = _ID_DIR / slug / "face" / "config.yaml"
        if _fc_path.exists():
            with open(_fc_path) as _f:
                _fc = _yaml.safe_load(_f) or {}
            face_negative = _fc.get("negative_prompt", "")
            face_style = _fc.get("style", "")
    except Exception:
        pass

    if content_type == "image":
        from supercooked.create.image import generate_image

        prompt = (media_prompts.image_prompts[0] if media_prompts and media_prompts.image_prompts else visual_prompt)
        path = await generate_image(
            slug, prompt, style=face_style or None, negative_prompt=face_negative or None
        )
        dest = draft_dir / "image.png"
        _copy_file(path, dest)
        return {"type": "image", "file": "image.png", "path": str(dest)}

    elif content_type == "video":
        from supercooked.create.video import generate_video

        prompt = (media_prompts.video_prompt if media_prompts and media_prompts.video_prompt else visual_prompt)
        dur = max(duration, 30)
        path = await generate_video(
            slug, prompt, duration_seconds=dur, negative_prompt=face_negative or None
        )
        dest = draft_dir / "video.mp4"
        _copy_file(path, dest)
        return {"type": "video", "file": "video.mp4", "path": str(dest)}

    elif content_type == "post":
        from supercooked.create.image import generate_image
        from supercooked.create.compose import compose_image_post

        prompt = (media_prompts.post_prompt if media_prompts and media_prompts.post_prompt else visual_prompt)
        img_path = await generate_image(
            slug, prompt, style=face_style or None, negative_prompt=face_negative or None
        )
        caption = captions_text or hook
        path = await compose_image_post(slug, img_path, caption)
        dest = draft_dir / "post.png"
        _copy_file(path, dest)
        return {"type": "post", "file": "post.png", "path": str(dest)}

    elif content_type == "selfie":
        from supercooked.create.selfie import take_selfie

        path = await take_selfie(slug)
        dest = draft_dir / "selfie.png"
        _copy_file(path, dest)
        return {"type": "selfie", "file": "selfie.png", "path": str(dest)}

    elif content_type == "tweet":
        dest = draft_dir / "tweet.txt"
        text = hook or script_text
        with open(dest, "w") as f:
            f.write(text)
        return {"type": "tweet", "file": "tweet.txt", "path": str(dest)}

    elif content_type == "thread":
        dest = draft_dir / "thread.txt"
        with open(dest, "w") as f:
            f.write(script_text)
        return {"type": "thread", "file": "thread.txt", "path": str(dest)}

    elif content_type == "story":
        from supercooked.create.image import generate_image
        from supercooked.create.compose import compose_story_image

        prompt = (media_prompts.story_prompt if media_prompts and media_prompts.story_prompt else visual_prompt)
        img_path = await generate_image(
            slug, prompt, size="1080x1920",
            style=face_style or None, negative_prompt=face_negative or None,
        )
        # Add text overlay from hook or captions
        overlay_text = hook or captions_text
        if overlay_text:
            path = await compose_story_image(slug, img_path, overlay_text)
        else:
            path = img_path
        dest = draft_dir / "story.png"
        _copy_file(path, dest)
        return {"type": "story", "file": "story.png", "path": str(dest)}

    elif content_type == "carousel":
        from supercooked.create.image import generate_images

        prompts = (
            media_prompts.carousel_prompts
            if media_prompts and media_prompts.carousel_prompts
            else visual_cues or [visual_prompt]
        )
        paths = await generate_images(
            slug, prompts, style=face_style or None, negative_prompt=face_negative or None,
        )
        results = []
        for i, path in enumerate(paths, 1):
            filename = f"carousel_{i}.png"
            dest = draft_dir / filename
            _copy_file(path, dest)
            results.append({"type": "carousel", "file": filename, "path": str(dest)})
        return results

    elif content_type == "audio":
        from supercooked.create.voice import synthesize_speech

        dest = draft_dir / "audio.mp3"
        await synthesize_speech(slug, script_text, output_path=dest)
        return {"type": "audio", "file": "audio.mp3", "path": str(dest)}

    elif content_type == "music":
        from supercooked.create.music import generate_background_music

        dest = draft_dir / "music.wav"
        await generate_background_music(
            duration_seconds=float(duration), output_path=dest
        )
        return {"type": "music", "file": "music.wav", "path": str(dest)}

    elif content_type == "thumbnail":
        from supercooked.create.thumbnail import generate_thumbnail

        concept_prompt = (media_prompts.thumbnail_prompt if media_prompts and media_prompts.thumbnail_prompt else None)
        path = await generate_thumbnail(
            slug, idea.title,
            concept_prompt=concept_prompt,
            template=idea.template,
            visual_cues=visual_cues,
            concept=idea.concept,
        )
        dest = draft_dir / "thumbnail.png"
        _copy_file(path, dest)
        return {"type": "thumbnail", "file": "thumbnail.png", "path": str(dest)}

    else:
        logger.warning("Unknown content_type: %s", content_type)
        return None


def _copy_file(src: Path, dest: Path) -> None:
    """Copy a file to the draft directory."""
    import shutil

    if src != dest:
        shutil.copy2(src, dest)


async def publish_content(
    slug: str,
    idea_id: str,
) -> dict[str, Any]:
    """Stage 3 - Publish: copy generated content to published dir.

    Args:
        slug: Identity slug.
        idea_id: ID of the generated content idea.

    Returns:
        Dict with published_dir and files list.

    Raises:
        ValueError: If idea not found or not in generated status.
    """
    import shutil

    load_identity(slug)
    base = IDENTITIES_DIR / slug / "content"
    draft_dir = base / "drafts" / idea_id
    published_dir = base / "published" / idea_id

    if not draft_dir.exists():
        raise ValueError(f"No draft found for idea '{idea_id}'.")

    meta_path = draft_dir / "metadata.yaml"
    if meta_path.exists():
        with open(meta_path) as f:
            metadata = yaml.safe_load(f) or {}
    else:
        metadata = {}

    if metadata.get("status") != "generated":
        raise ValueError(
            f"Idea '{idea_id}' is in '{metadata.get('status', 'unknown')}' status, "
            "expected 'generated'. Run generate first."
        )

    # Copy draft dir to published dir
    published_dir.mkdir(parents=True, exist_ok=True)
    for item in draft_dir.iterdir():
        dest = published_dir / item.name
        if item.is_file():
            shutil.copy2(item, dest)

    # Update metadata in published dir
    pub_meta = published_dir / "metadata.yaml"
    metadata["status"] = "published"
    metadata["published_at"] = datetime.now().isoformat()
    with open(pub_meta, "w") as f:
        yaml.dump(metadata, f, default_flow_style=False, sort_keys=False)

    # Update idea status
    _update_idea_status(slug, idea_id, IdeaStatus.PUBLISHED)

    log_action(
        slug,
        action="publish_content",
        details={"idea_id": idea_id, "title": metadata.get("title", "")},
        result=f"Published content for '{metadata.get('title', idea_id)}'",
    )

    return {
        "idea_id": idea_id,
        "status": "published",
        "published_dir": str(published_dir),
        "files": metadata.get("files", []),
    }

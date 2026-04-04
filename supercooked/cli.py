"""Super Cooked CLI — manage digital beings on the human internet."""

from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from supercooked.config import IDENTITIES_DIR, OUTPUT_DIR

console = Console()


def run_async(coro):
    """Run an async function synchronously."""
    return asyncio.run(coro)


@click.group()
def cli():
    """Super Cooked — Digital beings on the human internet."""
    pass


# ── Being Management ──────────────────────────────────────────────


@cli.group()
def being():
    """Manage digital beings."""
    pass


@being.command("list")
def being_list():
    """List all digital beings."""
    from supercooked.identity.manager import list_identities

    identities = list_identities()
    if not identities:
        console.print("[dim]No beings found. Create one with: supercooked being create <slug>[/dim]")
        return

    table = Table(title="Digital Beings", show_header=True)
    table.add_column("Slug", style="cyan bold")
    table.add_column("Name", style="white")
    table.add_column("Tagline", style="dim")
    table.add_column("Created", style="green")

    for identity in identities:
        table.add_row(
            identity.being.slug,
            identity.being.name,
            identity.being.tagline,
            identity.being.created,
        )

    console.print(table)


@being.command("create")
@click.argument("slug")
@click.option("--name", prompt="Being name", help="Display name for the being")
@click.option("--tagline", default="", help="Short tagline")
@click.option("--archetype", default="", help="Persona archetype")
@click.option("--tone", default="", help="Voice tone")
def being_create(slug: str, name: str, tagline: str, archetype: str, tone: str):
    """Create a new digital being."""
    from supercooked.identity.manager import create_identity

    identity = create_identity(
        slug=slug,
        name=name,
        tagline=tagline,
        archetype=archetype,
        tone=tone,
    )
    console.print(
        Panel(
            f"[bold cyan]{identity.being.name}[/bold cyan]\n"
            f"[dim]{identity.being.tagline}[/dim]\n\n"
            f"Slug: [green]{identity.being.slug}[/green]\n"
            f"Dir: [dim]{IDENTITIES_DIR / slug}[/dim]",
            title="Being Created",
            border_style="green",
        )
    )


@being.command("status")
@click.argument("slug")
def being_status(slug: str):
    """Show full dashboard for a being."""
    from supercooked.identity.manager import load_identity
    from supercooked.identity.action_log import get_recent_actions
    from supercooked.identity.memory import load_memory

    try:
        identity = load_identity(slug)
    except FileNotFoundError:
        console.print(f"[red]Being not found: {slug}[/red]")
        return

    # Identity info
    console.print(
        Panel(
            f"[bold cyan]{identity.being.name}[/bold cyan]\n"
            f"[dim]{identity.being.tagline}[/dim]\n\n"
            f"Archetype: {identity.persona.archetype}\n"
            f"Tone: {identity.persona.tone}\n"
            f"Created: {identity.being.created}",
            title=f"Being: {slug}",
            border_style="cyan",
        )
    )

    # Platforms
    platforms = identity.platforms
    platform_table = Table(title="Platforms", show_header=True)
    platform_table.add_column("Platform", style="cyan")
    platform_table.add_column("Enabled", style="green")
    platform_table.add_column("Handle", style="white")

    for name, config in [
        ("YouTube Shorts", platforms.youtube_shorts),
        ("X/Twitter", platforms.x),
        ("Instagram", platforms.instagram),
        ("TikTok", platforms.tiktok),
        ("Twitch", platforms.twitch),
    ]:
        status = "[green]Yes[/green]" if config.enabled else "[dim]No[/dim]"
        platform_table.add_row(name, status, config.handle or "[dim]—[/dim]")

    console.print(platform_table)

    # Content strategy
    strategy = identity.content_strategy
    if strategy.series:
        series_table = Table(title="Content Series", show_header=True)
        series_table.add_column("Series", style="cyan")
        series_table.add_column("Format", style="white")
        series_table.add_column("Frequency", style="green")
        for s in strategy.series:
            series_table.add_row(s.name, s.format, s.frequency)
        console.print(series_table)

    # Recent actions
    actions = get_recent_actions(slug, days=3)
    if actions:
        action_table = Table(title="Recent Actions (3 days)", show_header=True)
        action_table.add_column("Time", style="dim")
        action_table.add_column("Action", style="white")
        action_table.add_column("Platform", style="cyan")
        action_table.add_column("Result", style="green")
        for a in actions[:10]:
            action_table.add_row(
                a.timestamp.strftime("%m/%d %H:%M"),
                a.action,
                a.platform or "—",
                a.result or "—",
            )
        console.print(action_table)

    # Memory
    memory = load_memory(slug)
    if memory.learnings:
        console.print(f"\n[bold]Memory:[/bold] {len(memory.learnings)} learnings stored")


# ── Content Creation ──────────────────────────────────────────────


@cli.group("create")
def create_group():
    """Create content for a being."""
    pass


@create_group.command("selfie")
@click.argument("slug")
@click.option("--location", default="", help="Location for the selfie")
@click.option("--mood", default="", help="Mood/expression")
def create_selfie(slug: str, location: str, mood: str):
    """Generate a 'selfie' of the being."""
    from supercooked.create.selfie import take_selfie

    console.print(f"[cyan]Taking selfie for {slug}...[/cyan]")
    path = run_async(take_selfie(slug, location=location, mood=mood))
    console.print(f"[green]Selfie saved:[/green] {path}")


@create_group.command("post")
@click.argument("slug")
@click.argument("caption")
def create_post(slug: str, caption: str):
    """Create an image post with caption."""
    from supercooked.create.image import generate_image
    from supercooked.identity.manager import load_identity

    console.print(f"[cyan]Creating post for {slug}...[/cyan]")
    identity = load_identity(slug)
    prompt = f"{identity.being.name} — {caption}"
    path = run_async(generate_image(slug, prompt))
    console.print(f"[green]Image saved:[/green] {path}")
    console.print(f"[dim]Caption:[/dim] {caption}")


@create_group.command("thread")
@click.argument("slug")
@click.argument("idea_id")
def create_thread(slug: str, idea_id: str):
    """Create an X thread from an idea."""
    from supercooked.templates import get_template

    console.print(f"[cyan]Creating thread for {slug} from {idea_id}...[/cyan]")
    template = get_template("thread")

    import yaml
    ideas_path = IDENTITIES_DIR / slug / "content" / "ideas.yaml"
    with open(ideas_path) as f:
        data = yaml.safe_load(f) or {}
    ideas = data.get("ideas", [])
    idea = next((i for i in ideas if i["id"] == idea_id), None)
    if not idea:
        console.print(f"[red]Idea not found: {idea_id}[/red]")
        return

    spec = run_async(template.generate_spec(slug, idea["title"], idea.get("concept", "")))
    console.print(f"[green]Thread generated:[/green] {spec.title}")
    for i, tweet in enumerate(spec.script.split("\n\n"), 1):
        console.print(f"  [cyan]{i}.[/cyan] {tweet.strip()}")


@create_group.command("story")
@click.argument("slug")
def create_story(slug: str):
    """Create an IG story."""
    from supercooked.create.image import generate_image

    console.print(f"[cyan]Creating story for {slug}...[/cyan]")
    path = run_async(generate_image(slug, f"Instagram story for {slug}", size="1080x1920"))
    console.print(f"[green]Story image saved:[/green] {path}")


# ── Ideas ─────────────────────────────────────────────────────────


@cli.group("idea")
def idea_group():
    """Manage content ideas."""
    pass


@idea_group.command("add")
@click.argument("slug")
@click.argument("title")
@click.argument("concept")
@click.option("--template", "tmpl", default="", help="Template type")
@click.option("--types", default="", help="Comma-separated content types (image,video,tweet,...)")
def idea_add(slug: str, title: str, concept: str, tmpl: str, types: str):
    """Add a content idea to the backlog."""
    import fcntl

    import yaml

    # Validate being exists
    identity_dir = IDENTITIES_DIR / slug
    if not identity_dir.exists():
        console.print(f"[red]Being not found: {slug}[/red]")
        return

    ideas_path = IDENTITIES_DIR / slug / "content" / "ideas.yaml"
    ideas_path.parent.mkdir(parents=True, exist_ok=True)

    content_types = [t.strip() for t in types.split(",") if t.strip()] if types else []

    # File-locked read-modify-write to prevent race conditions
    lock_path = ideas_path.with_suffix(".lock")
    with open(lock_path, "w") as lock_f:
        fcntl.flock(lock_f.fileno(), fcntl.LOCK_EX)
        try:
            data: dict = {"ideas": []}
            if ideas_path.exists():
                with open(ideas_path) as f:
                    data = yaml.safe_load(f) or {"ideas": []}

            ideas = data.get("ideas", [])
            new_id = f"idea-{len(ideas) + 1:03d}"
            ideas.append({
                "id": new_id,
                "title": title,
                "concept": concept,
                "template": tmpl,
                "status": "backlog",
                "tags": [],
                "content_types": content_types,
            })

            with open(ideas_path, "w") as f:
                yaml.dump({"ideas": ideas}, f, default_flow_style=False, sort_keys=False)
        finally:
            fcntl.flock(lock_f.fileno(), fcntl.LOCK_UN)

    console.print(f"[green]Added:[/green] {new_id} — {title}")
    if content_types:
        console.print(f"  [dim]Types: {', '.join(content_types)}[/dim]")


@idea_group.command("list")
@click.argument("slug")
def idea_list(slug: str):
    """Show content backlog."""
    import yaml

    ideas_path = IDENTITIES_DIR / slug / "content" / "ideas.yaml"
    if not ideas_path.exists():
        console.print(f"[red]Being not found: {slug}[/red]")
        return

    with open(ideas_path) as f:
        data = yaml.safe_load(f) or {}

    ideas = data.get("ideas", [])
    if not ideas:
        console.print("[dim]No ideas yet. Add one with: supercooked idea add <slug> <title> <concept>[/dim]")
        return

    table = Table(title=f"Content Ideas — {slug}", show_header=True)
    table.add_column("ID", style="cyan")
    table.add_column("Title", style="white")
    table.add_column("Template", style="dim")
    table.add_column("Types", style="dim")
    table.add_column("Status", style="green")

    status_colors = {
        "backlog": "dim",
        "in_progress": "yellow",
        "drafted": "blue",
        "generated": "magenta",
        "published": "green",
        "archived": "dim strikethrough",
    }

    for idea in ideas:
        status = idea.get("status", "backlog")
        color = status_colors.get(status, "white")
        ctypes = ", ".join(idea.get("content_types", [])) or "—"
        table.add_row(
            idea["id"],
            idea["title"],
            idea.get("template", "—"),
            ctypes,
            f"[{color}]{status}[/{color}]",
        )

    console.print(table)


# ── Pipeline (3-Stage) ────────────────────────────────────────────


@cli.command("draft")
@click.argument("slug")
@click.argument("idea_id")
def draft(slug: str, idea_id: str):
    """Stage 1: Generate a script/draft from a backlog idea."""
    from supercooked.pipeline.produce import produce_content

    console.print(f"[cyan]Drafting script for {slug} / {idea_id}...[/cyan]")
    result = run_async(produce_content(slug, idea_id))
    console.print(f"[green]Drafted:[/green] {result.get('title', idea_id)}")
    console.print(f"  [dim]Dir: {result.get('draft_dir', '')}[/dim]")
    if result.get("script", {}).get("hook"):
        console.print(f'  [bold]Hook:[/bold] "{result["script"]["hook"]}"')


@cli.command("generate")
@click.argument("slug")
@click.argument("idea_id")
def generate_cmd(slug: str, idea_id: str):
    """Stage 2: Generate media files from a drafted idea."""
    from supercooked.pipeline.produce import generate_content

    console.print(f"[cyan]Generating media for {slug} / {idea_id}...[/cyan]")
    result = run_async(generate_content(slug, idea_id))
    files = result.get("files", [])
    errors = result.get("errors", [])
    console.print(f"[green]Generated {len(files)} files[/green]")
    for f in files:
        console.print(f"  [green]✓[/green] {f['type']}: {f['file']}")
    for e in errors:
        console.print(f"  [red]✗[/red] {e['content_type']}: {e['error']}")


# ── Publishing ────────────────────────────────────────────────────


@cli.command("publish")
@click.argument("slug")
@click.argument("idea_id")
def publish(slug: str, idea_id: str):
    """Stage 3: Publish generated content to platforms."""
    from supercooked.pipeline.produce import publish_content

    console.print(f"[cyan]Publishing {idea_id} for {slug}...[/cyan]")
    result = run_async(publish_content(slug, idea_id))
    console.print(f"[green]Published:[/green] {result.get('idea_id', idea_id)}")
    files = result.get("files", [])
    for f in files:
        console.print(f"  [green]✓[/green] {f.get('type', '')}: {f.get('file', '')}")


@cli.command("schedule")
@click.argument("slug")
@click.argument("content_id")
@click.argument("time")
def schedule(slug: str, content_id: str, time: str):
    """Schedule content for later publishing."""
    from supercooked.publish.scheduler import schedule_content

    dt = datetime.fromisoformat(time)
    schedule_content(slug, content_id, dt)
    console.print(f"[green]Scheduled:[/green] {content_id} for {dt}")


# ── Intelligence ──────────────────────────────────────────────────


@cli.group("trend")
def trend_group():
    """Trend intelligence."""
    pass


@trend_group.command("scan")
@click.argument("slug")
def trend_scan(slug: str):
    """Find trending topics relevant to a being."""
    from supercooked.intel.trends import scan_trends

    console.print(f"[cyan]Scanning trends for {slug}...[/cyan]")
    trends = run_async(scan_trends())

    table = Table(title="Trending Topics", show_header=True)
    table.add_column("#", style="dim")
    table.add_column("Topic", style="cyan bold")
    table.add_column("Source", style="dim")

    for i, trend in enumerate(trends[:15], 1):
        table.add_row(str(i), trend.get("topic", ""), trend.get("source", ""))

    console.print(table)


@cli.command("ideate")
@click.argument("slug")
@click.option("--count", default=5, help="Number of ideas to generate")
@click.option("--focus", default=None, help="Focus area")
def ideate(slug: str, count: int, focus: str | None):
    """Generate content ideas using AI."""
    from supercooked.intel.ideate import generate_ideas

    console.print(f"[cyan]Generating {count} ideas for {slug}...[/cyan]")
    ideas = run_async(generate_ideas(slug, count=count, focus=focus))

    for i, idea in enumerate(ideas, 1):
        console.print(f"  [cyan]{i}.[/cyan] [bold]{idea.title}[/bold]")
        console.print(f"     [dim]{idea.concept}[/dim]")


# ── Sources ───────────────────────────────────────────────────────


@cli.command("download")
@click.argument("url")
@click.option("--output", default=None, help="Output directory")
def download(url: str, output: str | None):
    """Download video for reaction content."""
    from supercooked.sources.download import download_video

    console.print(f"[cyan]Downloading: {url}[/cyan]")
    output_dir = Path(output) if output else None
    path = run_async(download_video(url, output_dir=output_dir))
    console.print(f"[green]Downloaded:[/green] {path}")


# ── Live Streaming ────────────────────────────────────────────────


@cli.group("stream")
def stream_group():
    """Live streaming management."""
    pass


@stream_group.command("start")
@click.argument("slug")
def stream_start(slug: str):
    """Start a Twitch stream (Phase 2)."""
    from supercooked.engage.stream import start_stream

    console.print(f"[cyan]Starting stream for {slug}...[/cyan]")
    run_async(start_stream(slug))


# ── Video Editing Engine ─────────────────────────────────────────


@cli.group("edit")
def edit_group():
    """Video editing engine — ingest, understand, and assemble footage."""
    pass


@edit_group.command("init")
@click.argument("name")
@click.argument("video", type=click.Path(exists=True))
@click.option("--audio", default=None, type=click.Path(exists=True), help="Background music file")
@click.option("--sfx", default=None, type=click.Path(exists=True), help="SFX directory")
def edit_init(name: str, video: str, audio: str | None, sfx: str | None):
    """Initialize a new edit project from a video file."""
    from datetime import datetime

    from supercooked.edit.briefing import save_project
    from supercooked.edit.models import Project

    project_dir = OUTPUT_DIR / "edit" / name
    if project_dir.exists():
        console.print(f"[red]Project already exists: {name}[/red]")
        console.print(f"[dim]Dir: {project_dir}[/dim]")
        return

    # Create directory structure
    sources_dir = project_dir / "sources"
    analysis_dir = project_dir / "analysis" / "frames"
    segments_dir = project_dir / "segments"
    overlays_dir = project_dir / "overlays"
    for d in [sources_dir, analysis_dir, segments_dir, overlays_dir]:
        d.mkdir(parents=True, exist_ok=True)

    # Symlink source files
    video_path = Path(video).resolve()
    video_link = sources_dir / video_path.name
    video_link.symlink_to(video_path)

    audio_link_name = None
    if audio:
        audio_path = Path(audio).resolve()
        audio_link = sources_dir / audio_path.name
        audio_link.symlink_to(audio_path)
        audio_link_name = f"sources/{audio_path.name}"

    sfx_link_name = None
    if sfx:
        sfx_path = Path(sfx).resolve()
        sfx_link = sources_dir / "sfx"
        sfx_link.symlink_to(sfx_path)
        sfx_link_name = "sources/sfx"

    # Create project manifest
    project = Project(
        name=name,
        source_video=f"sources/{video_path.name}",
        source_audio=audio_link_name,
        sfx_dir=sfx_link_name,
        created=datetime.now().isoformat(timespec="seconds"),
    )
    save_project(project, project_dir)

    console.print(Panel(
        f"[bold cyan]{name}[/bold cyan]\n\n"
        f"Video: [green]{video_path.name}[/green]\n"
        f"Audio: [green]{Path(audio).name if audio else '—'}[/green]\n"
        f"SFX:   [green]{Path(sfx).name if sfx else '—'}[/green]\n\n"
        f"Dir:   [dim]{project_dir}[/dim]",
        title="Edit Project Created",
        border_style="green",
    ))
    console.print("[dim]Next: supercooked edit ingest " + name + "[/dim]")


@edit_group.command("ingest")
@click.argument("name")
@click.option("--language", default=None, help="Language code (e.g. en, ar). Auto-detect if omitted")
@click.option("--scene-threshold", default=0.3, help="Scene detection sensitivity (0-1)")
def edit_ingest(name: str, language: str | None, scene_threshold: float):
    """Ingest footage: transcribe, detect scenes, extract frames, analyze audio."""
    from supercooked.edit.briefing import (
        assemble_briefing,
        load_project,
        save_audio_analysis,
        save_briefing,
        save_frames_index,
        save_project,
        save_scenes,
        save_transcript,
    )
    from supercooked.edit.ffmpeg import extract_audio, probe_source_info
    from supercooked.edit.models import ProjectState
    from supercooked.edit.transcribe import transcribe
    from supercooked.edit.understand import (
        analyze_audio,
        detect_scene_boundaries,
        extract_smart_frames,
    )

    project_dir = OUTPUT_DIR / "edit" / name
    project = load_project(project_dir)
    video_path = project_dir / project.source_video

    async def _ingest():
        with console.status("[cyan]Probing source...[/cyan]"):
            source_info = await probe_source_info(video_path)
        console.print(
            f"  Source: {source_info.resolution} @ {source_info.fps}fps, "
            f"{source_info.duration} ({source_info.file_size_mb} MB)"
        )

        # Extract audio for Whisper
        audio_wav = project_dir / "analysis" / "audio.wav"
        with console.status("[cyan]Extracting audio...[/cyan]"):
            await extract_audio(video_path, audio_wav)
        console.print("  [green]Audio extracted[/green]")

        # Transcribe
        with console.status("[cyan]Transcribing (this may take a while)...[/cyan]"):
            transcript = await transcribe(audio_wav, language=language)
        console.print(
            f"  [green]Transcript:[/green] {transcript.word_count} words, "
            f"{len(transcript.segments)} segments ({transcript.language})"
        )
        save_transcript(transcript, project_dir / "analysis" / "transcript.json")

        # Scene detection
        with console.status("[cyan]Detecting scenes...[/cyan]"):
            scenes = await detect_scene_boundaries(video_path, threshold=scene_threshold)
        console.print(f"  [green]Scenes:[/green] {len(scenes)} detected")
        save_scenes(scenes, project_dir / "analysis" / "scenes.json")

        # Smart frame extraction
        frames_dir = project_dir / "analysis" / "frames"
        with console.status("[cyan]Extracting keyframes...[/cyan]"):
            frames = await extract_smart_frames(
                video_path, frames_dir, scenes, transcript.segments,
            )
        console.print(f"  [green]Frames:[/green] {len(frames)} keyframes extracted")
        save_frames_index(frames, project_dir / "analysis" / "frames_index.json")

        # Audio analysis
        with console.status("[cyan]Analyzing audio...[/cyan]"):
            audio_analysis = await analyze_audio(audio_wav, transcript.segments)
        console.print(
            f"  [green]Audio:[/green] {len(audio_analysis.speech_regions)} speech, "
            f"{len(audio_analysis.silence_regions)} silence regions, "
            f"{audio_analysis.loudness_integrated} LUFS"
        )
        save_audio_analysis(audio_analysis, project_dir / "analysis" / "audio_analysis.json")

        # Assemble and save briefing
        briefing = assemble_briefing(source_info, transcript, scenes, audio_analysis, frames)
        save_briefing(briefing, project_dir / "analysis" / "briefing.yaml")

        # Update project state
        project.state = ProjectState.INGESTED
        save_project(project, project_dir)

        console.print(
            Panel(
                f"[bold green]Ingest complete[/bold green]\n\n"
                f"Transcript: {transcript.word_count} words\n"
                f"Scenes: {len(scenes)}\n"
                f"Frames: {len(frames)}\n"
                f"Briefing: analysis/briefing.yaml",
                title=f"Edit: {name}",
                border_style="green",
            )
        )
        console.print("[dim]Next: supercooked edit briefing " + name + "[/dim]")

    run_async(_ingest())


@edit_group.command("briefing")
@click.argument("name")
@click.option("--export", "export_path", default=None, help="Export briefing to file")
def edit_briefing(name: str, export_path: str | None):
    """Display the structured briefing for a project."""
    from supercooked.edit.briefing import format_briefing_summary, load_briefing

    project_dir = OUTPUT_DIR / "edit" / name
    briefing_path = project_dir / "analysis" / "briefing.yaml"

    if not briefing_path.exists():
        console.print(f"[red]No briefing found. Run: supercooked edit ingest {name}[/red]")
        return

    briefing = load_briefing(briefing_path)
    summary = format_briefing_summary(briefing)

    console.print(Panel(summary, title=f"Briefing: {name}", border_style="cyan"))

    if export_path:
        Path(export_path).write_text(summary)
        console.print(f"[green]Exported to:[/green] {export_path}")


@edit_group.command("run")
@click.argument("name")
@click.option("--edl", "edl_path", default=None, help="Path to EDL file (defaults to project edl.yaml)")
def edit_run(name: str, edl_path: str | None):
    """Execute an EDL to assemble the video."""
    from supercooked.edit.assemble import execute_edl, load_edl
    from supercooked.edit.briefing import load_project, save_project
    from supercooked.edit.models import ProjectState

    project_dir = OUTPUT_DIR / "edit" / name
    project = load_project(project_dir)

    edl_file = Path(edl_path) if edl_path else project_dir / "edl.yaml"
    if not edl_file.exists():
        console.print(f"[red]EDL not found: {edl_file}[/red]")
        console.print("[dim]Write an edl.yaml in the project directory first.[/dim]")
        return

    edl = load_edl(edl_file)
    console.print(f"[cyan]Assembling {len(edl.segments)} segments...[/cyan]")

    async def _run():
        output = await execute_edl(edl, project_dir)
        project.state = ProjectState.ASSEMBLED
        save_project(project, project_dir)
        console.print(f"[green]Assembled:[/green] {output}")
        console.print(f"[dim]Duration: ~{edl.total_duration:.1f}s from {len(edl.segments)} segments[/dim]")

    run_async(_run())


@edit_group.command("preview")
@click.argument("name")
@click.option("--seg", "segment", required=True, type=int, help="Segment index (0-based)")
def edit_preview(name: str, segment: int):
    """Quick preview of a single segment."""
    from supercooked.edit.assemble import load_edl, preview_segment

    project_dir = OUTPUT_DIR / "edit" / name
    edl = load_edl(project_dir / "edl.yaml")

    console.print(f"[cyan]Rendering preview for segment {segment}...[/cyan]")

    async def _preview():
        output = await preview_segment(edl, project_dir, segment)
        console.print(f"[green]Preview:[/green] {output}")

    run_async(_preview())


@edit_group.command("render")
@click.argument("name")
@click.option("--profile", default="youtube", help="Export profile (youtube, ig-reel, tiktok, draft)")
@click.option("--output", "output_path", default=None, help="Output file path")
def edit_render(name: str, profile: str, output_path: str | None):
    """Final quality render with export profile."""
    from supercooked.edit.render import render_final

    project_dir = OUTPUT_DIR / "edit" / name
    out = Path(output_path) if output_path else None

    console.print(f"[cyan]Rendering with profile '{profile}'...[/cyan]")

    async def _render():
        final = await render_final(project_dir, profile_name=profile, output_path=out)
        console.print(f"[bold green]Final render:[/bold green] {final}")

    run_async(_render())


@edit_group.command("status")
@click.argument("name")
def edit_status(name: str):
    """Show project state and files."""
    from supercooked.edit.briefing import load_project

    project_dir = OUTPUT_DIR / "edit" / name

    if not project_dir.exists():
        console.print(f"[red]Project not found: {name}[/red]")
        return

    project = load_project(project_dir)

    # Check what exists
    has_briefing = (project_dir / "analysis" / "briefing.yaml").exists()
    has_edl = (project_dir / "edl.yaml").exists()
    has_assembled = (project_dir / "assembled.mp4").exists()
    has_final = (project_dir / "final.mp4").exists()

    state_colors = {
        "init": "yellow",
        "ingested": "cyan",
        "edl_ready": "blue",
        "assembled": "magenta",
        "rendered": "green",
    }
    color = state_colors.get(project.state.value, "white")

    table = Table(title=f"Edit Project: {name}", show_header=True)
    table.add_column("Component", style="white")
    table.add_column("Status", style="white")

    table.add_row("State", f"[{color}]{project.state.value}[/{color}]")
    table.add_row("Source", project.source_video)
    table.add_row("Audio", project.source_audio or "—")
    table.add_row("Briefing", "[green]ready[/green]" if has_briefing else "[dim]not yet[/dim]")
    table.add_row("EDL", "[green]ready[/green]" if has_edl else "[dim]not yet[/dim]")
    table.add_row("Assembled", "[green]ready[/green]" if has_assembled else "[dim]not yet[/dim]")
    table.add_row("Final", "[green]ready[/green]" if has_final else "[dim]not yet[/dim]")
    table.add_row("Directory", str(project_dir))

    console.print(table)


@edit_group.command("compose")
@click.argument("name")
@click.argument("sources", nargs=-1, required=True, type=click.Path(exists=True))
@click.option("--audio", default=None, type=click.Path(exists=True), help="Background audio track")
@click.option("--sfx", default=None, type=click.Path(exists=True), help="SFX directory")
def edit_compose(name: str, sources: tuple[str, ...], audio: str | None, sfx: str | None):
    """Initialize a compose project from images, clips, and audio.

    Unlike `edit init` (single video source), compose takes multiple
    source files (images + videos) that you'll arrange via edl.yaml.
    No ingest step needed — go straight to writing the EDL.

    Usage:
        supercooked edit compose my-reel bg1.jpg clip1.mp4 bg2.png --audio music.mp3
    """
    from datetime import datetime

    from supercooked.edit.briefing import save_project
    from supercooked.edit.models import Project

    project_dir = OUTPUT_DIR / "edit" / name
    if project_dir.exists():
        console.print(f"[red]Project already exists: {name}[/red]")
        return

    # Create directory structure
    sources_dir = project_dir / "sources"
    segments_dir = project_dir / "segments"
    overlays_dir = project_dir / "overlays"
    for d in [sources_dir, segments_dir, overlays_dir]:
        d.mkdir(parents=True, exist_ok=True)

    # Symlink all source files
    source_names = []
    for src in sources:
        src_path = Path(src).resolve()
        link = sources_dir / src_path.name
        if link.exists():
            # Handle duplicate filenames by prefixing
            link = sources_dir / f"{len(source_names)}_{src_path.name}"
        link.symlink_to(src_path)
        source_names.append(f"sources/{link.name}")

    audio_link_name = None
    if audio:
        audio_path = Path(audio).resolve()
        audio_link = sources_dir / audio_path.name
        audio_link.symlink_to(audio_path)
        audio_link_name = f"sources/{audio_path.name}"

    sfx_link_name = None
    if sfx:
        sfx_path = Path(sfx).resolve()
        sfx_link = sources_dir / "sfx"
        sfx_link.symlink_to(sfx_path)
        sfx_link_name = "sources/sfx"

    project = Project(
        name=name,
        source_video="",  # no single source — each segment has its own
        source_audio=audio_link_name,
        sfx_dir=sfx_link_name,
        created=datetime.now().isoformat(timespec="seconds"),
    )
    save_project(project, project_dir)

    # Print sources table
    source_table = Table(show_header=True, title="Sources")
    source_table.add_column("#", style="dim")
    source_table.add_column("File", style="cyan")
    source_table.add_column("Type", style="green")

    img_exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}
    for i, sname in enumerate(source_names):
        fname = sname.split("/", 1)[1]
        ftype = "image" if Path(fname).suffix.lower() in img_exts else "video"
        source_table.add_row(str(i), fname, ftype)

    console.print(Panel(
        f"[bold cyan]{name}[/bold cyan]\n\n"
        f"Audio: [green]{Path(audio).name if audio else '—'}[/green]\n"
        f"Dir:   [dim]{project_dir}[/dim]",
        title="Compose Project Created",
        border_style="green",
    ))
    console.print(source_table)
    console.print()
    console.print("[dim]Next: write edl.yaml then run: supercooked edit run " + name + "[/dim]")
    console.print("[dim]For images, use type: image and hold: <seconds> in your EDL segments[/dim]")


if __name__ == "__main__":
    cli()

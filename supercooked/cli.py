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
    import yaml

    # Validate being exists
    identity_dir = IDENTITIES_DIR / slug
    if not identity_dir.exists():
        console.print(f"[red]Being not found: {slug}[/red]")
        return

    ideas_path = IDENTITIES_DIR / slug / "content" / "ideas.yaml"
    ideas_path.parent.mkdir(parents=True, exist_ok=True)

    data: dict = {"ideas": []}
    if ideas_path.exists():
        with open(ideas_path) as f:
            data = yaml.safe_load(f) or {"ideas": []}

    content_types = [t.strip() for t in types.split(",") if t.strip()] if types else []

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


if __name__ == "__main__":
    cli()

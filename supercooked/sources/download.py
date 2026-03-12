"""Video downloading via yt-dlp.

Wraps the yt-dlp command-line tool to download videos from
YouTube, TikTok, Instagram, and other supported platforms.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from supercooked.config import OUTPUT_DIR


def _check_ytdlp() -> str:
    """Verify yt-dlp is installed and return its path."""
    try:
        result = subprocess.run(
            ["yt-dlp", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            raise RuntimeError("yt-dlp returned non-zero exit code")
        return "yt-dlp"
    except FileNotFoundError:
        raise RuntimeError(
            "yt-dlp is not installed or not on PATH. "
            "Install with: pip install yt-dlp\n"
            "Or: brew install yt-dlp (macOS)"
        )


def download_video(
    url: str,
    output_dir: str | Path | None = None,
    format: str = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
    max_filesize: str | None = "500M",
    extract_info_only: bool = False,
) -> Path:
    """Download a video from a URL using yt-dlp.

    Args:
        url: URL of the video to download (YouTube, TikTok, etc.).
        output_dir: Directory to save the downloaded file. Defaults to output/downloads/.
        format: yt-dlp format string. Defaults to best mp4.
        max_filesize: Maximum file size (e.g. "500M"). None for no limit.
        extract_info_only: If True, only extract metadata without downloading.

    Returns:
        Path to the downloaded video file.

    Raises:
        RuntimeError: If yt-dlp is not installed.
        subprocess.CalledProcessError: If the download fails.
        FileNotFoundError: If the downloaded file cannot be found.
    """
    ytdlp = _check_ytdlp()

    if output_dir is None:
        output_dir = OUTPUT_DIR / "downloads"
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    # Build yt-dlp command
    output_template = str(out_path / "%(title)s_%(id)s.%(ext)s")

    cmd = [
        ytdlp,
        url,
        "-o", output_template,
        "-f", format,
        "--no-playlist",
        "--write-info-json",
        "--restrict-filenames",
    ]

    if max_filesize:
        cmd.extend(["--max-filesize", max_filesize])

    if extract_info_only:
        cmd.append("--skip-download")

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=600,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"yt-dlp download failed for '{url}':\n"
            f"stderr: {result.stderr}\n"
            f"stdout: {result.stdout}"
        )

    # Find the downloaded file
    # yt-dlp writes a .info.json file alongside the video
    info_files = list(out_path.glob("*.info.json"))
    if not info_files:
        raise FileNotFoundError(
            f"Download appeared to succeed but no info.json found in {out_path}. "
            f"yt-dlp output: {result.stdout}"
        )

    # Sort by modification time, newest first
    info_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    latest_info = info_files[0]

    # Read info to get the actual filename
    with open(latest_info) as f:
        info = json.load(f)

    # Construct the expected video filename
    video_ext = info.get("ext", "mp4")
    video_name = latest_info.stem.replace(".info", "") + f".{video_ext}"
    video_path = out_path / video_name

    if not video_path.exists() and not extract_info_only:
        # Try to find any recently created video file
        video_extensions = {".mp4", ".webm", ".mkv", ".mov", ".avi", ".flv"}
        candidates = [
            f for f in out_path.iterdir()
            if f.suffix.lower() in video_extensions
        ]
        if candidates:
            candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            video_path = candidates[0]
        else:
            raise FileNotFoundError(
                f"Downloaded video file not found. Expected: {video_path}. "
                f"yt-dlp output: {result.stdout}"
            )

    return video_path


def get_video_info(url: str) -> dict:
    """Get video metadata without downloading.

    Args:
        url: URL of the video.

    Returns:
        Dict with video metadata (title, duration, description, etc.).

    Raises:
        RuntimeError: If yt-dlp is not installed or info extraction fails.
    """
    ytdlp = _check_ytdlp()

    result = subprocess.run(
        [
            ytdlp,
            url,
            "--dump-json",
            "--no-download",
            "--no-playlist",
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"yt-dlp info extraction failed for '{url}':\n{result.stderr}"
        )

    return json.loads(result.stdout)

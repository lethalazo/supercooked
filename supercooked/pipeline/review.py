"""Content quality review checks.

Validates content files meet minimum quality standards before publishing:
file existence, media duration, resolution, file size, and metadata completeness.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from supercooked.identity.action_log import log_action


def _check_file_exists(path: Path) -> dict[str, Any]:
    """Check that the file/directory exists."""
    return {
        "check": "file_exists",
        "passed": path.exists(),
        "message": f"{'Exists' if path.exists() else 'NOT FOUND'}: {path}",
    }


def _check_video_duration(video_path: Path, min_seconds: float = 3.0) -> dict[str, Any]:
    """Check video meets minimum duration using ffprobe."""
    if not video_path.exists():
        return {
            "check": "video_duration",
            "passed": False,
            "message": f"Video file not found: {video_path}",
        }

    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(video_path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            raise RuntimeError(f"ffprobe failed: {result.stderr}")

        duration = float(result.stdout.strip())
        passed = duration >= min_seconds
        return {
            "check": "video_duration",
            "passed": passed,
            "duration_seconds": round(duration, 2),
            "min_required": min_seconds,
            "message": (
                f"Duration: {duration:.1f}s (min: {min_seconds}s) — "
                f"{'PASS' if passed else 'FAIL: too short'}"
            ),
        }
    except FileNotFoundError:
        raise RuntimeError(
            "ffprobe not found. Install ffmpeg to enable video quality checks. "
            "brew install ffmpeg (macOS) or apt install ffmpeg (Linux)"
        )


def _check_video_resolution(
    video_path: Path,
    min_width: int = 720,
    min_height: int = 720,
) -> dict[str, Any]:
    """Check video resolution using ffprobe."""
    if not video_path.exists():
        return {
            "check": "video_resolution",
            "passed": False,
            "message": f"Video file not found: {video_path}",
        }

    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height",
                "-of", "csv=s=x:p=0",
                str(video_path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            raise RuntimeError(f"ffprobe failed: {result.stderr}")

        parts = result.stdout.strip().split("x")
        width, height = int(parts[0]), int(parts[1])
        passed = width >= min_width and height >= min_height
        return {
            "check": "video_resolution",
            "passed": passed,
            "width": width,
            "height": height,
            "min_width": min_width,
            "min_height": min_height,
            "message": (
                f"Resolution: {width}x{height} (min: {min_width}x{min_height}) — "
                f"{'PASS' if passed else 'FAIL: resolution too low'}"
            ),
        }
    except FileNotFoundError:
        raise RuntimeError(
            "ffprobe not found. Install ffmpeg to enable video quality checks."
        )


def _check_file_size(path: Path, max_mb: float = 500.0) -> dict[str, Any]:
    """Check file size is within limits."""
    if not path.exists():
        return {
            "check": "file_size",
            "passed": False,
            "message": f"File not found: {path}",
        }

    size_mb = path.stat().st_size / (1024 * 1024)
    passed = size_mb <= max_mb
    return {
        "check": "file_size",
        "passed": passed,
        "size_mb": round(size_mb, 2),
        "max_mb": max_mb,
        "message": (
            f"Size: {size_mb:.1f}MB (max: {max_mb}MB) — "
            f"{'PASS' if passed else 'FAIL: file too large'}"
        ),
    }


def _check_metadata_completeness(draft_dir: Path) -> dict[str, Any]:
    """Check that required metadata files exist in the draft directory."""
    required_files = ["metadata.yaml", "script.yaml"]
    optional_files = ["captions.txt"]

    missing_required: list[str] = []
    missing_optional: list[str] = []

    for f in required_files:
        if not (draft_dir / f).exists():
            missing_required.append(f)

    for f in optional_files:
        if not (draft_dir / f).exists():
            missing_optional.append(f)

    passed = len(missing_required) == 0
    parts = []
    if missing_required:
        parts.append(f"Missing required: {', '.join(missing_required)}")
    if missing_optional:
        parts.append(f"Missing optional: {', '.join(missing_optional)}")

    return {
        "check": "metadata_completeness",
        "passed": passed,
        "missing_required": missing_required,
        "missing_optional": missing_optional,
        "message": (
            "All required metadata present — PASS"
            if passed
            else f"FAIL: {'; '.join(parts)}"
        ),
    }


def review_content(
    slug: str,
    content_path: str | Path,
) -> dict[str, Any]:
    """Run quality checks on content before publishing.

    Checks performed:
    - File/directory existence
    - Metadata completeness (for draft directories)
    - Video duration (if .mp4/.mov file found)
    - Video resolution (if .mp4/.mov file found)
    - File size limits

    Args:
        slug: Identity slug.
        content_path: Path to the content file or draft directory.

    Returns:
        Dict with 'passed' (bool), 'checks' (list of check results),
        and 'summary' (human-readable summary).

    Raises:
        RuntimeError: If ffprobe is not installed and video checks are needed.
    """
    path = Path(content_path)
    checks: list[dict[str, Any]] = []

    # Basic existence check
    checks.append(_check_file_exists(path))

    if path.is_dir():
        # Draft directory review
        checks.append(_check_metadata_completeness(path))

        # Check for video files in the directory
        video_extensions = {".mp4", ".mov", ".webm", ".avi"}
        video_files = [
            f for f in path.iterdir()
            if f.suffix.lower() in video_extensions
        ]
        for vf in video_files:
            checks.append(_check_video_duration(vf))
            checks.append(_check_video_resolution(vf))
            checks.append(_check_file_size(vf))

    elif path.is_file():
        checks.append(_check_file_size(path))

        video_extensions = {".mp4", ".mov", ".webm", ".avi"}
        if path.suffix.lower() in video_extensions:
            checks.append(_check_video_duration(path))
            checks.append(_check_video_resolution(path))

    all_passed = all(c["passed"] for c in checks)
    failed_checks = [c for c in checks if not c["passed"]]

    summary_parts = [f"{len(checks)} checks run, {len(failed_checks)} failed."]
    for fc in failed_checks:
        summary_parts.append(f"  - {fc['check']}: {fc['message']}")

    result = {
        "passed": all_passed,
        "checks": checks,
        "total_checks": len(checks),
        "failed_count": len(failed_checks),
        "summary": "\n".join(summary_parts),
    }

    log_action(
        slug,
        action="review_content",
        details={
            "content_path": str(path),
            "total_checks": len(checks),
            "failed": len(failed_checks),
        },
        result=f"Review {'PASSED' if all_passed else 'FAILED'} ({len(failed_checks)} issues)",
    )

    return result

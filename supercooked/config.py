"""Global configuration loader."""

from __future__ import annotations

import os
from pathlib import Path

import yaml

from supercooked.identity.schemas import GlobalConfig

PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_PATH = PROJECT_ROOT / "supercooked.yaml"
IDENTITIES_DIR = PROJECT_ROOT / "identities"
OUTPUT_DIR = PROJECT_ROOT / "output"
EDIT_DIR = OUTPUT_DIR / "edit"
ASSETS_DIR = PROJECT_ROOT / "assets"

# Claude model — Haiku (OAuth tokens only support Haiku currently)
CLAUDE_MODEL = "claude-haiku-4-5-20251001"

# Env var → config key mapping (env vars take precedence over supercooked.yaml)
_ENV_MAP = {
    "anthropic": "ANTHROPIC_AUTH_TOKEN",
    "gemini": "GEMINI_API_KEY",
    "elevenlabs": "ELEVENLABS_API_KEY",
    "late": "LATE_API_KEY",
}


def _load_dotenv() -> None:
    """Load .env file from project root if it exists."""
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip()
                # Don't overwrite existing env vars
                if key not in os.environ:
                    os.environ[key] = value


# Load .env on import
_load_dotenv()


def load_config() -> GlobalConfig:
    """Load global config from supercooked.yaml."""
    if not CONFIG_PATH.exists():
        return GlobalConfig()
    with open(CONFIG_PATH) as f:
        data = yaml.safe_load(f) or {}
    return GlobalConfig(**data)


def get_api_key(service: str) -> str:
    """Get an API key from env var (preferred) or supercooked.yaml.

    For Anthropic: reads ANTHROPIC_AUTH_TOKEN (OAuth token from Claude Max).
    Same pattern as payproof and openclaw.
    """
    # Check env var first
    env_var = _ENV_MAP.get(service)
    if env_var:
        env_val = os.environ.get(env_var, "")
        if env_val:
            return env_val

    # Fall back to supercooked.yaml
    config = load_config()
    key = getattr(config.api_keys, service, "")
    if not key:
        env_hint = f" or set {env_var}" if env_var else ""
        raise RuntimeError(
            f"API key for '{service}' not configured. "
            f"Set it in {CONFIG_PATH} under api_keys.{service}{env_hint}"
        )
    return key


def get_anthropic_client():
    """Get an AsyncAnthropic client using OAuth token.

    Uses ANTHROPIC_AUTH_TOKEN env var (OAuth from Claude Max).
    Same auth pattern as payproof and openclaw — pure OAuth with beta header.
    """
    import anthropic

    # OAuth token from env (loaded from .env or set externally)
    token = os.environ.get("ANTHROPIC_AUTH_TOKEN", "")
    if token:
        return anthropic.AsyncAnthropic(
            auth_token=token,
            default_headers={"anthropic-beta": "oauth-2025-04-20"},
        )

    # Fall back to supercooked.yaml (also OAuth — same header needed)
    config = load_config()
    if config.api_keys.anthropic:
        return anthropic.AsyncAnthropic(
            auth_token=config.api_keys.anthropic,
            default_headers={"anthropic-beta": "oauth-2025-04-20"},
        )

    raise RuntimeError(
        "Anthropic auth token not configured. "
        "Set ANTHROPIC_AUTH_TOKEN in .env or supercooked.yaml"
    )

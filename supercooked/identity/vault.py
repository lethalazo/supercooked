"""Encrypted credential storage using Fernet symmetric encryption."""

from __future__ import annotations

import base64
import hashlib
from pathlib import Path

import yaml
from cryptography.fernet import Fernet, InvalidToken

from supercooked.config import IDENTITIES_DIR


def _derive_key(master_password: str) -> bytes:
    """Derive a Fernet key from a master password."""
    digest = hashlib.sha256(master_password.encode()).digest()
    return base64.urlsafe_b64encode(digest)


def _get_fernet(master_password: str) -> Fernet:
    return Fernet(_derive_key(master_password))


def _vault_path(slug: str) -> Path:
    return IDENTITIES_DIR / slug / "credentials" / "vault.yaml"


def store_credential(
    slug: str, platform: str, data: dict, master_password: str
) -> None:
    """Store encrypted credentials for a platform."""
    fernet = _get_fernet(master_password)
    vault_file = _vault_path(slug)
    vault_file.parent.mkdir(parents=True, exist_ok=True)

    # Load existing vault
    vault = {}
    if vault_file.exists():
        with open(vault_file) as f:
            vault = yaml.safe_load(f) or {}

    # Encrypt each value
    encrypted = {}
    for key, value in data.items():
        encrypted[key] = fernet.encrypt(str(value).encode()).decode()

    vault[platform] = encrypted
    with open(vault_file, "w") as f:
        yaml.dump(vault, f, default_flow_style=False)


def load_credential(slug: str, platform: str, master_password: str) -> dict:
    """Load and decrypt credentials for a platform."""
    fernet = _get_fernet(master_password)
    vault_file = _vault_path(slug)

    if not vault_file.exists():
        raise FileNotFoundError(f"No vault found for {slug}")

    with open(vault_file) as f:
        vault = yaml.safe_load(f) or {}

    if platform not in vault:
        raise KeyError(f"No credentials for platform '{platform}' in {slug}'s vault")

    decrypted = {}
    try:
        for key, value in vault[platform].items():
            decrypted[key] = fernet.decrypt(value.encode()).decode()
    except InvalidToken:
        raise ValueError(
            f"Wrong master password or corrupted credentials for '{platform}' in {slug}'s vault"
        )
    return decrypted


def list_platforms(slug: str) -> list[str]:
    """List platforms with stored credentials."""
    vault_file = _vault_path(slug)
    if not vault_file.exists():
        return []
    with open(vault_file) as f:
        vault = yaml.safe_load(f) or {}
    return list(vault.keys())


def delete_credential(slug: str, platform: str) -> None:
    """Remove credentials for a platform."""
    vault_file = _vault_path(slug)
    if not vault_file.exists():
        return
    with open(vault_file) as f:
        vault = yaml.safe_load(f) or {}
    vault.pop(platform, None)
    with open(vault_file, "w") as f:
        yaml.dump(vault, f, default_flow_style=False)

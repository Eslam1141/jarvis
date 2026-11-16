"""Secrets live in the macOS Keychain, never in files."""

import keyring
from keyring.errors import PasswordDeleteError

SERVICE = "jarvis"
ANTHROPIC_KEY = "anthropic_api_key"


def get_secret(name: str) -> str | None:
    return keyring.get_password(SERVICE, name)


def set_secret(name: str, value: str) -> None:
    keyring.set_password(SERVICE, name, value)


def delete_secret(name: str) -> None:
    try:
        keyring.delete_password(SERVICE, name)
    except PasswordDeleteError:
        pass

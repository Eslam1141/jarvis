"""Settings for Jarvis, read from environment variables or a .env file."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


def _default_data_dir() -> Path:
    """Where Jarvis keeps its memory and reminders on each OS."""
    if os.name == "nt":  # Windows: %APPDATA%\Jarvis
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        return base / "Jarvis"
    if os.uname().sysname == "Darwin":  # macOS
        return Path.home() / "Library" / "Application Support" / "Jarvis"
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "jarvis"


@dataclass
class Settings:
    model: str = "claude-opus-5-5"
    # low | medium | high | xhigh | max. Higher = smarter but slower and pricier.
    effort: str = "medium"
    max_tokens: int = 64000
    user_name: str = ""
    # "auto" replies in whatever language you write in (English or Arabic).
    language: str = "auto"
    web_search: bool = True
    data_dir: Path = field(default_factory=_default_data_dir)

    @classmethod
    def load(cls) -> "Settings":
        load_dotenv()
        s = cls()
        s.model = os.environ.get("JARVIS_MODEL", s.model)
        s.effort = os.environ.get("JARVIS_EFFORT", s.effort)
        s.max_tokens = int(os.environ.get("JARVIS_MAX_TOKENS", s.max_tokens))
        s.user_name = os.environ.get("JARVIS_USER_NAME", s.user_name)
        s.language = os.environ.get("JARVIS_LANGUAGE", s.language)
        s.web_search = os.environ.get("JARVIS_WEB_SEARCH", "true").lower() in ("1", "true", "yes")
        if os.environ.get("JARVIS_DATA_DIR"):
            s.data_dir = Path(os.environ["JARVIS_DATA_DIR"])
        s.data_dir.mkdir(parents=True, exist_ok=True)
        return s

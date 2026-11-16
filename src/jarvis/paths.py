"""Where Jarvis keeps his data: outside the repo, readable only by the owner."""

import os
from pathlib import Path


def data_dir() -> Path:
    """Return the data folder, creating it owner-only if needed."""
    override = os.environ.get("JARVIS_HOME")
    path = Path(override) if override else Path.home() / ".jarvis"
    path.mkdir(parents=True, exist_ok=True)
    path.chmod(0o700)
    return path

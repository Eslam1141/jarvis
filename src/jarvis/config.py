"""Settings read from config.toml in the data folder."""

import tomllib
from dataclasses import dataclass, fields
from pathlib import Path

from jarvis.paths import data_dir


@dataclass(frozen=True)
class Config:
    owner_name: str = "Sir"
    fast_model: str = "claude-sonnet-5-5"
    deep_model: str = "claude-fable-5-2"
    history_turns: int = 20


def config_path() -> Path:
    return data_dir() / "config.toml"


def load_config(path: Path | None = None) -> Config:
    path = path or config_path()
    if not path.exists():
        return Config()
    values = tomllib.loads(path.read_text(encoding="utf-8"))
    known = {f.name for f in fields(Config)}
    unknown = sorted(set(values) - known)
    if unknown:
        raise ValueError(f"Unknown setting(s) in {path}: {', '.join(unknown)}")
    return Config(**values)


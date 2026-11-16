"""Settings read from config.toml in the data folder."""

import tomllib
from dataclasses import dataclass, fields
from pathlib import Path

from jarvis.paths import data_dir


@dataclass(frozen=True)
class Config:
    owner_name: str = "Sir"
    fast_model: str = "claude-haiku-5-5"
    deep_model: str = "claude-opus-5-5"
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



def save_setting(key: str, value: str | int, path: Path | None = None) -> None:
    """Set one setting in config.toml, keeping the others."""
    if key not in {f.name for f in fields(Config)}:
        raise ValueError(f"Unknown setting: {key}")
    path = path or config_path()
    current = tomllib.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    current[key] = value
    lines = []
    for name, item in current.items():
        if isinstance(item, str):
            escaped = item.replace("\\", "\\\\").replace('"', '\\"')
            lines.append(f'{name} = "{escaped}"')
        else:
            lines.append(f"{name} = {item}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

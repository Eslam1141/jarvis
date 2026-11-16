"""SQLite store for conversation turns and the action log."""

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

Role = Literal["owner", "jarvis"]


@dataclass(frozen=True)
class Turn:
    role: Role
    text: str
    at: datetime


@dataclass(frozen=True)
class Action:
    kind: str
    summary: str
    detail: str
    at: datetime


class Store:
    def __init__(self, path: Path):
        self._db = sqlite3.connect(path, timeout=10)
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.executescript(
            """
            CREATE TABLE IF NOT EXISTS turns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL, text TEXT NOT NULL, at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT NOT NULL, summary TEXT NOT NULL,
                detail TEXT NOT NULL, at TEXT NOT NULL);
            """
        )
        self._db.commit()

    def add_turn(self, role: Role, text: str, at: datetime) -> None:
        with self._db:
            self._db.execute(
                "INSERT INTO turns (role, text, at) VALUES (?, ?, ?)",
                (role, text, at.isoformat()),
            )

    def recent_turns(self, limit: int) -> list[Turn]:
        rows = self._db.execute(
            "SELECT role, text, at FROM turns ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [Turn(r, t, datetime.fromisoformat(a)) for r, t, a in reversed(rows)]

    def log_action(self, kind: str, summary: str, detail: str, at: datetime) -> None:
        with self._db:
            self._db.execute(
                "INSERT INTO actions (kind, summary, detail, at) VALUES (?, ?, ?, ?)",
                (kind, summary, detail, at.isoformat()),
            )

    def actions(self, limit: int) -> list[Action]:
        rows = self._db.execute(
            "SELECT kind, summary, detail, at FROM actions ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [Action(k, s, d, datetime.fromisoformat(a)) for k, s, d, a in rows]

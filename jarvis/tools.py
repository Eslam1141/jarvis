"""Things Jarvis can do on your computer.

Each tool has a JSON schema (sent to Claude) and a Python handler (run locally).
To add a tool: write a handler, then add a Tool(...) entry in build_tools().
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
import webbrowser
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable
from urllib.parse import urlparse

from .storage import Memory, Reminders

# Asks the person "yes or no?" before Jarvis does something on their computer.
ConfirmFn = Callable[[str], bool]


@dataclass
class Tool:
    name: str
    description: str
    properties: dict[str, Any]
    required: list[str]
    handler: Callable[..., Any]

    def schema(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            # Stream tool input as it is generated; we validate it ourselves below.
            "eager_input_streaming": True,
            "input_schema": {
                "type": "object",
                "properties": self.properties,
                "required": self.required,
                "additionalProperties": False,
            },
        }

    def validate(self, args: Any) -> str | None:
        """Return an error message if the input doesn't match the schema."""
        if not isinstance(args, dict):
            return "input must be an object"
        for key in self.required:
            if key not in args:
                return f"missing required field '{key}'"
        for key, value in args.items():
            spec = self.properties.get(key)
            if spec is None:
                return f"unknown field '{key}'"
            expected = spec.get("type")
            ok = {
                "string": isinstance(value, str),
                "integer": isinstance(value, int) and not isinstance(value, bool),
                "boolean": isinstance(value, bool),
            }.get(expected, True)
            if not ok:
                return f"field '{key}' must be a {expected}"
            if "enum" in spec and value not in spec["enum"]:
                return f"field '{key}' must be one of {spec['enum']}"
        return None


class Toolbox:
    def __init__(self, memory: Memory, reminders: Reminders, confirm: ConfirmFn):
        self.memory = memory
        self.reminders = reminders
        self.confirm = confirm
        self.tools = {t.name: t for t in self._build_tools()}

    def schemas(self) -> list[dict[str, Any]]:
        # Sorted so the tool list is byte-identical every request (keeps the prompt cache warm).
        return [self.tools[name].schema() for name in sorted(self.tools)]

    def run(self, name: str, args: Any) -> tuple[str, bool]:
        """Run a tool. Returns (result_text, is_error)."""
        tool = self.tools.get(name)
        if tool is None:
            return f"Unknown tool: {name}", True
        problem = tool.validate(args)
        if problem:
            return json.dumps({"INVALID_INPUT": problem, "input": args}, ensure_ascii=False), True
        try:
            result = tool.handler(**args)
        except Exception as exc:  # report tool failures to Claude instead of crashing
            return f"{type(exc).__name__}: {exc}", True
        if isinstance(result, str):
            return result, False
        return json.dumps(result, ensure_ascii=False, default=str), False

    # ---- handlers -------------------------------------------------------

    def get_datetime(self) -> dict[str, Any]:
        now = datetime.now().astimezone()
        return {
            "local_time": now.isoformat(timespec="seconds"),
            "weekday": now.strftime("%A"),
            "timezone": str(now.tzinfo),
        }

    def remember(self, fact: str) -> dict[str, Any]:
        item = self.memory.add(fact=fact)
        return {"saved": True, "id": item["id"]}

    def recall(self, query: str = "") -> dict[str, Any]:
        matches = self.memory.search(query)
        return {"memories": [{"id": m["id"], "fact": m["fact"]} for m in matches]}

    def forget(self, id: int) -> dict[str, Any]:
        return {"deleted": self.memory.remove(id)}

    def add_reminder(self, text: str, when: str) -> dict[str, Any]:
        try:
            parsed = datetime.fromisoformat(when)
        except ValueError:
            raise ValueError("'when' must be an ISO 8601 date-time like 2026-10-21T18:30")
        item = self.reminders.add(text=text, when=parsed.isoformat(timespec="minutes"), done=False)
        return {"saved": True, "id": item["id"], "when": item["when"]}

    def list_reminders(self) -> dict[str, Any]:
        return {"reminders": [
            {"id": r["id"], "text": r["text"], "when": r["when"]} for r in self.reminders.pending()
        ]}

    def complete_reminder(self, id: int) -> dict[str, Any]:
        return {"updated": self.reminders.update(id, done=True) is not None}

    def open_website(self, url: str) -> str:
        if urlparse(url).scheme not in ("http", "https"):
            raise ValueError("only http and https links can be opened")
        if not self.confirm(f"Open {url} in your browser?"):
            return "The user declined."
        webbrowser.open(url)
        return f"Opened {url}"

    def open_app(self, name: str) -> str:
        if not self.confirm(f"Open the app '{name}'?"):
            return "The user declined."
        system = platform.system()
        if system == "Windows":
            # Same as typing the name into the Run box (e.g. notepad, calc, spotify:).
            os.startfile(name)  # type: ignore[attr-defined]
        elif system == "Darwin":
            subprocess.Popen(["open", "-a", name])
        else:
            exe = shutil.which(name)
            if not exe:
                raise FileNotFoundError(f"'{name}' not found on PATH")
            subprocess.Popen([exe])
        return f"Started {name}"

    def system_info(self) -> dict[str, Any]:
        total, used, free = shutil.disk_usage(os.path.expanduser("~"))
        gb = 1024 ** 3
        return {
            "os": f"{platform.system()} {platform.release()}",
            "machine": platform.machine(),
            "python": sys.version.split()[0],
            "home_disk_free_gb": round(free / gb, 1),
            "home_disk_total_gb": round(total / gb, 1),
        }

    # ---- registry -------------------------------------------------------

    def _build_tools(self) -> list[Tool]:
        s = {"type": "string"}
        i = {"type": "integer"}
        return [
            Tool("get_datetime", "Get the current local date, time, weekday and time zone. "
                 "Use it whenever the answer depends on today's date or the time.",
                 {}, [], self.get_datetime),
            Tool("remember", "Save a lasting fact about the user (preferences, people, plans) "
                 "so you can use it in future conversations. Write it as one short sentence.",
                 {"fact": s}, ["fact"], self.remember),
            Tool("recall", "Search saved facts about the user. An empty query returns all of them.",
                 {"query": s}, [], self.recall),
            Tool("forget", "Delete a saved fact by its id.", {"id": i}, ["id"], self.forget),
            Tool("add_reminder", "Create a reminder. 'when' is a local ISO 8601 date-time "
                 "(call get_datetime first to work out relative times like 'in 2 hours').",
                 {"text": s, "when": s}, ["text", "when"], self.add_reminder),
            Tool("list_reminders", "List reminders that are not done yet.", {}, [], self.list_reminders),
            Tool("complete_reminder", "Mark a reminder as done by its id.",
                 {"id": i}, ["id"], self.complete_reminder),
            Tool("open_website", "Open an http(s) link in the user's web browser. "
                 "The user is asked to confirm first.", {"url": s}, ["url"], self.open_website),
            Tool("open_app", "Start an application on the user's computer by name, e.g. "
                 "'notepad', 'calc', 'chrome'. The user is asked to confirm first.",
                 {"name": s}, ["name"], self.open_app),
            Tool("system_info", "Get basic facts about the user's computer: OS, free disk space.",
                 {}, [], self.system_info),
        ]

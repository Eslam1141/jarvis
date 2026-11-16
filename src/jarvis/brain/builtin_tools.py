"""Tools that let Jarvis remember facts and lessons, and forget them.

None of these change anything outside Jarvis, so they do not go through the
approval gate. They are owner-only: they refuse to run in a turn where
outside content (mail, comments...) has been read.
"""

import json
from collections.abc import Callable
from datetime import datetime

from jarvis.brain.tools import Tool, ToolRegistry, TurnState
from jarvis.memory.lessons import Lessons
from jarvis.memory.profile import Profile
from jarvis.memory.store import Store

_TEXT = {
    "type": "object",
    "properties": {"text": {"type": "string"}},
    "required": ["text"],
    "additionalProperties": False,
}
_NONE = {"type": "object", "properties": {}, "additionalProperties": False}
_ID = {
    "type": "object",
    "properties": {"lesson_id": {"type": "integer"}},
    "required": ["lesson_id"],
    "additionalProperties": False,
}


def _text_arg(args: dict) -> str:
    text = args.get("text")
    if not isinstance(text, str) or not text.strip():
        raise ValueError("'text' must be a non-empty string")
    return text


def register_memory_tools(
    registry: ToolRegistry,
    profile: Profile,
    lessons: Lessons,
    store: Store,
    clock: Callable[[], datetime],
) -> None:
    async def remember_fact(args: dict, state: TurnState) -> str:
        text = _text_arg(args)
        profile.add_fact(text, clock())
        store.log_action("profile.add", text, json.dumps(args, ensure_ascii=False), clock())
        return "saved"

    async def remember_lesson(args: dict, state: TurnState) -> str:
        lesson = lessons.add(_text_arg(args), "owner_said", clock())
        store.log_action(
            "lesson.add", f"L{lesson.id}: {lesson.text}",
            json.dumps(args, ensure_ascii=False), clock(),
        )
        return f"saved as L{lesson.id}"

    async def list_lessons(args: dict, state: TurnState) -> str:
        found = lessons.list()
        if not found:
            return "no lessons yet"
        return "\n".join(f"L{l.id} ({l.at.isoformat()}): {l.text}" for l in found)

    async def forget_lesson(args: dict, state: TurnState) -> str:
        lesson_id = args.get("lesson_id")
        if not isinstance(lesson_id, int) or isinstance(lesson_id, bool):
            raise ValueError("'lesson_id' must be a whole number")
        if not lessons.forget(lesson_id):
            return f"no lesson L{lesson_id}"
        store.log_action("lesson.forget", f"L{lesson_id}", json.dumps(args), clock())
        return "forgotten"

    registry.register(Tool(
        "remember_fact",
        "Save a durable fact about the owner (a preference, a person, a project). "
        "Use only for something the owner told you directly.",
        _TEXT, remember_fact, writes=False, owner_only=True))
    registry.register(Tool(
        "remember_lesson",
        "Save a rule for how you should behave from now on, when the owner "
        "corrects you or states a standing preference. One short sentence.",
        _TEXT, remember_lesson, writes=False, owner_only=True))
    registry.register(Tool(
        "list_lessons",
        "List the lessons you have learned, with their ids. Use when the owner "
        "asks what you have learned, or before forgetting one.",
        _NONE, list_lessons, writes=False))
    registry.register(Tool(
        "forget_lesson",
        "Remove one lesson by id when the owner asks you to forget it.",
        _ID, forget_lesson, writes=False, owner_only=True))

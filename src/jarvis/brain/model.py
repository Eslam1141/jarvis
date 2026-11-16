"""The model interface the brain talks to, and a scripted fake for tests."""

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol


@dataclass(frozen=True)
class Message:
    role: Literal["user", "assistant"]
    content: str | list[Any]


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_schema: dict


@dataclass(frozen=True)
class TextDelta:
    text: str


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    args: dict


@dataclass(frozen=True)
class Done:
    stop_reason: str
    # The assistant turn exactly as the model produced it. When the turn asked
    # for tools it must be sent back unchanged with the tool results.
    content: list[Any] | None = field(default=None, compare=False)


ModelEvent = TextDelta | ToolCall | Done


class ModelUnavailable(Exception):
    """The model could not be reached or could not answer right now."""


class ModelClient(Protocol):
    def stream(
        self, *, system: str, messages: list[Message], tools: list[ToolSpec], model: str
    ) -> AsyncIterator[ModelEvent]: ...


class FakeModel:
    """Plays one scripted list of events (or exceptions) per call."""

    def __init__(self, scripts: list[list[ModelEvent | Exception]]):
        self._scripts = list(scripts)
        self.calls: list[dict] = []

    async def stream(
        self, *, system: str, messages: list[Message], tools: list[ToolSpec], model: str
    ) -> AsyncIterator[ModelEvent]:
        self.calls.append(
            {"system": system, "messages": list(messages), "tools": list(tools), "model": model}
        )
        if not self._scripts:
            raise AssertionError("FakeModel was called more times than scripted")
        for item in self._scripts.pop(0):
            if isinstance(item, Exception):
                raise item
            yield item

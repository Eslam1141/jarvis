"""Tools the brain can call, and the rules for running them."""

import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from jarvis.brain.model import ToolSpec
from jarvis.gate import Gate

REFUSED_OWNER_ONLY = (
    "refused: this can only follow something the owner said, "
    "not content that was fetched"
)


@dataclass
class TurnState:
    """Tracks one owner message. A new one is created for each message."""

    saw_outside_content: bool = False


Handler = Callable[[dict, TurnState], Awaitable[str]]


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    input_schema: dict
    handler: Handler
    writes: bool  # changes something outside Jarvis: runs only through the gate
    outside_content: bool = False  # returns text written by other people
    owner_only: bool = False  # may not run after outside content was read
    describe: Callable[[dict], str] | None = None  # what the gate reads out


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool {tool.name!r} is already registered")
        if tool.writes and tool.describe is None:
            raise ValueError(f"Write tool {tool.name!r} needs a describe function")
        self._tools[tool.name] = tool

    def specs(self) -> list[ToolSpec]:
        return [ToolSpec(t.name, t.description, t.input_schema) for t in self._tools.values()]

    async def run(self, name: str, args: dict, state: TurnState, gate: Gate) -> str:
        tool = self._tools.get(name)
        if tool is None:
            return f"error: unknown tool {name}"
        if tool.owner_only and state.saw_outside_content:
            return REFUSED_OWNER_ONLY
        try:
            if tool.writes:
                description = tool.describe(args)
                detail = json.dumps(args, ensure_ascii=False)
                if not await gate.approve(name, description, detail):
                    return "declined by owner"
                result = await tool.handler(args, state)
                try:
                    gate.record(name, description, detail)
                except Exception:
                    # It happened. Saying "error" would invite doing it twice.
                    result += " (done, but it could not be logged)"
            else:
                result = await tool.handler(args, state)
        except Exception as e:
            return f"error: {e}"
        if tool.outside_content:
            state.saw_outside_content = True
        return result

"""The agent loop: owner text in, streamed reply out, tools in between."""

from collections.abc import AsyncIterator, Callable
from datetime import datetime

from jarvis.brain.model import (
    Done,
    Message,
    ModelClient,
    ModelUnavailable,
    TextDelta,
    ToolCall,
)
from jarvis.brain.prompt import build_system_prompt, load_personality
from jarvis.brain.tools import ToolRegistry, TurnState
from jarvis.config import Config
from jarvis.gate import Gate
from jarvis.memory.lessons import Lessons
from jarvis.memory.profile import Profile
from jarvis.memory.store import Store

MSG_EMPTY = "I didn't catch anything."
MSG_UNAVAILABLE = "I can't reach my brain right now. Try again in a moment."
MSG_REFUSED = "I can't help with that one."
MSG_TOO_MANY_STEPS = "I had to stop; that took too many steps."
MAX_TOOL_ROUNDS = 8
CUT_OFF = " […]"


class Brain:
    def __init__(
        self,
        model: ModelClient,
        registry: ToolRegistry,
        gate: Gate,
        store: Store,
        profile: Profile,
        lessons: Lessons,
        config: Config,
        clock: Callable[[], datetime],
        personality: str | None = None,
    ):
        self._model = model
        self._registry = registry
        self._gate = gate
        self._store = store
        self._profile = profile
        self._lessons = lessons
        self._config = config
        self._clock = clock
        self._personality = personality

    def _history(self) -> list[Message]:
        turns = self._store.recent_turns(self._config.history_turns)
        messages = [
            Message("user" if t.role == "owner" else "assistant", t.text) for t in turns
        ]
        # The model requires the conversation to open with the owner.
        while messages and messages[0].role == "assistant":
            messages.pop(0)
        return messages

    def _system(self) -> str:
        # Re-read every turn so a lesson saved a moment ago applies immediately.
        return build_system_prompt(
            self._personality if self._personality is not None else load_personality(),
            self._profile.read(),
            self._lessons.list(),
            self._clock(),
            self._config.owner_name,
        )

    async def respond(self, user_text: str) -> AsyncIterator[str]:
        if not user_text.strip():
            yield MSG_EMPTY
            return

        self._store.add_turn("owner", user_text.strip(), self._clock())
        messages = self._history()
        state = TurnState()
        said = ""

        try:
            for _ in range(MAX_TOOL_ROUNDS):
                calls: list[ToolCall] = []
                done: Done | None = None
                round_text = ""
                async for event in self._model.stream(
                    system=self._system(),
                    messages=messages,
                    tools=self._registry.specs(),
                    model=self._config.fast_model,
                ):
                    if isinstance(event, TextDelta):
                        round_text += event.text
                        said += event.text
                        yield event.text
                    elif isinstance(event, ToolCall):
                        calls.append(event)
                    elif isinstance(event, Done):
                        done = event

                if done is not None and done.stop_reason == "refusal":
                    said += MSG_REFUSED
                    yield MSG_REFUSED
                    break
                if not calls:
                    break

                messages.append(Message("assistant", _assistant_content(done, round_text, calls)))
                results = [
                    {
                        "type": "tool_result",
                        "tool_use_id": call.id,
                        "content": await self._registry.run(
                            call.name, call.args, state, self._gate
                        ),
                    }
                    for call in calls
                ]
                messages.append(Message("user", results))
            else:
                said += MSG_TOO_MANY_STEPS
                yield MSG_TOO_MANY_STEPS
        except ModelUnavailable:
            if said:
                self._store.add_turn("jarvis", said.rstrip() + CUT_OFF, self._clock())
            yield MSG_UNAVAILABLE
            return

        if said:
            self._store.add_turn("jarvis", said, self._clock())


def _assistant_content(done: Done | None, text: str, calls: list[ToolCall]) -> list:
    """The assistant turn to replay with the tool results, unchanged when known."""
    if done is not None and done.content is not None:
        return done.content
    blocks: list = [{"type": "text", "text": text}] if text else []
    blocks += [
        {"type": "tool_use", "id": c.id, "name": c.name, "input": c.args} for c in calls
    ]
    return blocks

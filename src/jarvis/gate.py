"""The approval gate: nothing that changes the outside world runs without a clear yes."""

import re
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Literal

from jarvis.memory.store import Store

Decision = Literal["yes", "no", "unclear"]
Ask = Callable[[str], Awaitable[str]]

_YES = [
    "yes", "yeah", "yep", "sure", "send it", "go ahead", "do it", "confirm",
    "approved", "ok", "okay",
    "أيوه", "ايوه", "آه", "اه", "نعم", "تمام", "ماشي", "ابعت", "ابعته", "اوكي",
]
_NO = [
    "no", "nope", "don't", "do not", "stop", "cancel", "wait", "not yet",
    "لا", "لأ", "استنى", "بلاش", "الغي", "مش دلوقتي",
]


def _tokens(text: str) -> list[str]:
    return re.findall(r"[\w']+", text.lower().replace("’", "'"))


def _contains(tokens: list[str], phrase: str) -> bool:
    words = _tokens(phrase)
    return any(tokens[i:i + len(words)] == words for i in range(len(tokens) - len(words) + 1))


def parse_decision(reply: str) -> Decision:
    """A 'no' anywhere wins. Anything that is not a clear yes is not a yes."""
    tokens = _tokens(reply)
    if any(_contains(tokens, phrase) for phrase in _NO):
        return "no"
    if any(_contains(tokens, phrase) for phrase in _YES):
        return "yes"
    return "unclear"


class Gate:
    def __init__(self, ask: Ask, store: Store, clock: Callable[[], datetime]):
        self._ask = ask
        self._store = store
        self._clock = clock

    async def approve(self, kind: str, description: str, detail: str) -> bool:
        """Ask the owner. Only an explicit yes returns True; one re-ask if unclear."""
        decision = parse_decision(await self._ask(f"{description} Shall I go ahead?"))
        if decision == "unclear":
            decision = parse_decision(
                await self._ask(f"Sorry, I need a clear yes or no. {description}")
            )
        return decision == "yes"

    def record(self, kind: str, description: str, detail: str) -> None:
        """Log an action that was actually carried out."""
        self._store.log_action(kind, description, detail, self._clock())

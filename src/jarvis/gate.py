"""The approval gate: nothing that changes the outside world runs without a clear yes."""

import re
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Literal

from jarvis.memory.store import Store

Decision = Literal["yes", "no", "unclear"]
Ask = Callable[[str], Awaitable[str]]

# A reply is a yes only when it is nothing but yes-phrases and politeness.
_YES = [
    "yes", "yeah", "yep", "sure", "send it", "go ahead", "do it", "confirm",
    "approved", "ok", "okay",
    "أيوه", "ايوه", "آه", "اه", "نعم", "تمام", "ماشي", "ابعت", "ابعته", "اوكي",
]
_FILLER = [
    "please", "thanks", "thank you", "jarvis", "sir",
    "يا", "جارفيس", "من فضلك", "لو سمحت", "شكرا",
]
# Any of these anywhere in the reply makes it a no.
_NO = [
    "no", "nope", "nah", "not", "never", "don't", "dont", "do not",
    "can't", "cant", "cannot", "won't", "wont", "isn't", "isnt",
    "stop", "cancel", "wait", "hold on", "later",
    "لا", "لأ", "مش", "استنى", "بلاش", "الغي",
]
# Egyptian negation wraps the verb: ما...ش (ماتبعتش, متبعتش).
_ARABIC_NEGATED = re.compile(r"^م\w{2,}ش$")


def _tokens(text: str) -> list[str]:
    return re.findall(r"[\w']+", text.lower().replace("’", "'"))


def _contains(tokens: list[str], phrase: str) -> bool:
    words = _tokens(phrase)
    return any(tokens[i:i + len(words)] == words for i in range(len(tokens) - len(words) + 1))


def _only_yes_and_filler(tokens: list[str]) -> bool:
    """True when every word belongs to a yes-phrase or politeness, with at least one yes."""
    yes = sorted((_tokens(p) for p in _YES), key=len, reverse=True)
    filler = sorted((_tokens(p) for p in _FILLER), key=len, reverse=True)
    i, saw_yes = 0, False
    while i < len(tokens):
        for words, is_yes in [(w, True) for w in yes] + [(w, False) for w in filler]:
            if tokens[i:i + len(words)] == words:
                i += len(words)
                saw_yes = saw_yes or is_yes
                break
        else:
            return False
    return saw_yes


def parse_decision(reply: str) -> Decision:
    """Any refusal word wins. A yes must be the whole reply, not a word inside it."""
    tokens = _tokens(reply)
    if any(_contains(tokens, phrase) for phrase in _NO):
        return "no"
    if any(_ARABIC_NEGATED.match(t) for t in tokens):
        return "no"
    if _only_yes_and_filler(tokens):
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

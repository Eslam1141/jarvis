"""Tests that run without an API key, using a fake Claude client."""

from datetime import datetime, timedelta
from types import SimpleNamespace as NS

import pytest

from jarvis.brain import Callbacks, Jarvis
from jarvis.config import Settings
from jarvis.storage import Memory, Reminders
from jarvis.tools import Toolbox


@pytest.fixture
def settings(tmp_path):
    return Settings(data_dir=tmp_path, user_name="Bassant")


# ---- fake Claude ---------------------------------------------------------

class FakeStream:
    def __init__(self, message):
        self.message = message

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def __iter__(self):
        for block in self.message.content:
            yield NS(type="content_block_start", content_block=block)
            if block.type == "text":
                yield NS(type="text", text=block.text)

    def get_final_message(self):
        return self.message


class FakeClient:
    """Returns the queued responses in order and records each request."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []
        self.beta = NS(messages=NS(stream=self._stream))

    def _stream(self, **kwargs):
        # Copy so later appends don't change what we recorded.
        self.requests.append({**kwargs, "messages": list(kwargs["messages"])})
        return FakeStream(self.responses.pop(0))


def text(t):
    return NS(type="text", text=t)


def tool_use(id, name, input):
    return NS(type="tool_use", id=id, name=name, input=input)


def msg(*content, stop="end_turn"):
    return NS(content=list(content), stop_reason=stop)


# ---- storage -------------------------------------------------------------

def test_memory_persists_arabic(tmp_path):
    m = Memory(tmp_path)
    m.add(fact="اسمي بسنت")
    m.add(fact="Likes coffee")
    again = Memory(tmp_path)
    assert [i["fact"] for i in again.items] == ["اسمي بسنت", "Likes coffee"]
    assert "بسنت" in (tmp_path / "memory.json").read_text(encoding="utf-8")
    assert [i["fact"] for i in again.search("coffee")] == ["Likes coffee"]


def test_reminders_due(tmp_path):
    r = Reminders(tmp_path)
    past = (datetime.now() - timedelta(minutes=1)).isoformat()
    future = (datetime.now() + timedelta(hours=1)).isoformat()
    r.add(text="call mom", when=past, done=False)
    r.add(text="later", when=future, done=False)
    assert [x["text"] for x in r.due()] == ["call mom"]
    r.update(1, notified=True)
    assert r.due() == []


# ---- tools ---------------------------------------------------------------

def test_tool_validation(tmp_path):
    box = Toolbox(Memory(tmp_path), Reminders(tmp_path), confirm=lambda q: True)
    out, err = box.run("remember", {})
    assert err and "missing" in out
    out, err = box.run("forget", {"id": "one"})
    assert err and "integer" in out
    out, err = box.run("remember", {"fact": "x", "extra": 1})
    assert err and "unknown" in out
    out, err = box.run("nope", {})
    assert err


def test_tools_need_confirmation(tmp_path, monkeypatch):
    opened = []
    monkeypatch.setattr("webbrowser.open", opened.append)
    box = Toolbox(Memory(tmp_path), Reminders(tmp_path), confirm=lambda q: False)
    out, err = box.run("open_website", {"url": "https://example.com"})
    assert "declined" in out and opened == []
    out, err = box.run("open_website", {"url": "file:///etc/passwd"})
    assert err


def test_add_reminder_rejects_bad_date(tmp_path):
    box = Toolbox(Memory(tmp_path), Reminders(tmp_path), confirm=lambda q: True)
    out, err = box.run("add_reminder", {"text": "x", "when": "tomorrow"})
    assert err and "ISO" in out
    out, err = box.run("add_reminder", {"text": "x", "when": "2030-01-01T09:00"})
    assert not err


def test_schemas_are_stable(tmp_path):
    box = Toolbox(Memory(tmp_path), Reminders(tmp_path), confirm=lambda q: True)
    assert box.schemas() == box.schemas()
    for s in box.schemas():
        assert s["input_schema"]["additionalProperties"] is False


# ---- brain ---------------------------------------------------------------

def test_simple_chat(settings):
    client = FakeClient([msg(text("At your service."))])
    j = Jarvis(settings, confirm=lambda q: True, client=client)
    seen = []
    assert j.chat("hello", Callbacks(on_text=seen.append)) == "At your service."
    assert seen == ["At your service."]
    req = client.requests[0]
    assert req["model"] == "claude-opus-5-5"
    assert req["fallbacks"] == "default"
    assert "Bassant" in req["system"]
    assert len(j.messages) == 2


def test_tool_loop(settings):
    client = FakeClient([
        msg(text("Noted."), tool_use("t1", "remember", {"fact": "Likes tea"}), stop="tool_use"),
        msg(text("I'll remember that.")),
    ])
    j = Jarvis(settings, confirm=lambda q: True, client=client)
    tools_called = []
    reply = j.chat("I like tea", Callbacks(on_tool=lambda n, a: tools_called.append(n)))
    assert reply == "Noted.\n\nI'll remember that."
    assert tools_called == ["remember"]
    assert j.memory.items[0]["fact"] == "Likes tea"
    results = client.requests[1]["messages"][-1]
    assert results["role"] == "user"
    assert results["content"][0]["tool_use_id"] == "t1"
    assert results["content"][0]["is_error"] is False


def test_failed_turn_is_rolled_back(settings):
    client = FakeClient([])  # pop from empty list -> IndexError mid-turn
    j = Jarvis(settings, confirm=lambda q: True, client=client)
    with pytest.raises(IndexError):
        j.chat("hi")
    assert j.messages == []


def test_memories_go_into_system_prompt(settings):
    Memory(settings.data_dir).add(fact="Lives in Cairo")
    j = Jarvis(settings, confirm=lambda q: True, client=FakeClient([]))
    assert "Lives in Cairo" in j.system

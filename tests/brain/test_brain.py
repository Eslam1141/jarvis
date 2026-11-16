import pytest
from conftest import NOW, replies

from jarvis.brain.brain import MAX_TOOL_ROUNDS, MSG_EMPTY, MSG_REFUSED, MSG_UNAVAILABLE, Brain
from jarvis.brain.builtin_tools import register_memory_tools
from jarvis.brain.model import Done, FakeModel, ModelUnavailable, TextDelta, ToolCall
from jarvis.brain.tools import ToolRegistry
from jarvis.config import Config
from jarvis.gate import Gate
from jarvis.memory.lessons import Lessons
from jarvis.memory.profile import Profile


@pytest.fixture
def make_brain(tmp_path, store):
    def make(scripts):
        profile, lessons = Profile(tmp_path / "profile.md"), Lessons(tmp_path / "lessons.md")
        registry = ToolRegistry()
        register_memory_tools(registry, profile, lessons, store, lambda: NOW)
        brain = Brain(
            model=FakeModel(scripts), registry=registry,
            gate=Gate(ask=replies(), store=store, clock=lambda: NOW),
            store=store, profile=profile, lessons=lessons,
            config=Config(), clock=lambda: NOW, personality="PERSONA")
        brain.model, brain.store, brain.lessons = brain._model, store, lessons
        return brain
    return make


async def say(brain, text):
    return [c async for c in brain.respond(text)]


async def test_plain_reply_is_streamed_and_saved(make_brain):
    b = make_brain([[TextDelta("Good "), TextDelta("morning."), Done("end_turn")]])
    assert await say(b, "hello") == ["Good ", "morning."]
    assert [(t.role, t.text) for t in b.store.recent_turns(10)] == [
        ("owner", "hello"), ("jarvis", "Good morning.")]


async def test_empty_input_makes_no_model_call(make_brain):
    b = make_brain([])
    assert await say(b, "   ") == [MSG_EMPTY]
    assert b.model.calls == [] and b.store.recent_turns(10) == []


async def test_tool_call_round_trip(make_brain):
    b = make_brain([
        [ToolCall("t1", "remember_lesson", {"text": "No meetings before 10"}), Done("tool_use")],
        [TextDelta("Noted: no meetings before 10."), Done("end_turn")],
    ])
    assert "".join(await say(b, "never book me before 10")) == "Noted: no meetings before 10."
    assert b.lessons.list()[0].text == "No meetings before 10"
    second = b.model.calls[1]["messages"]
    assert second[-2].role == "assistant" and second[-1].role == "user"
    assert second[-1].content == [
        {"type": "tool_result", "tool_use_id": "t1", "content": "saved as L1"}]


async def test_assistant_turn_is_replayed_unchanged_with_tool_results(make_brain):
    raw = [{"type": "thinking", "thinking": "", "signature": "sig"},
           {"type": "tool_use", "id": "t1", "name": "list_lessons", "input": {}}]
    b = make_brain([
        [ToolCall("t1", "list_lessons", {}), Done("tool_use", raw)],
        [TextDelta("None yet."), Done("end_turn")],
    ])
    await say(b, "what have you learned?")
    assert b.model.calls[1]["messages"][-2].content is raw


async def test_all_tool_results_go_back_in_one_message(make_brain):
    b = make_brain([
        [ToolCall("a", "list_lessons", {}), ToolCall("b", "list_lessons", {}), Done("tool_use")],
        [TextDelta("ok"), Done("end_turn")],
    ])
    await say(b, "go")
    assert [r["tool_use_id"] for r in b.model.calls[1]["messages"][-1].content] == ["a", "b"]


async def test_lesson_applies_on_the_next_turn(make_brain):
    b = make_brain([[TextDelta("ok"), Done("end_turn")]])
    b.lessons.add("Keep answers short", "owner_said", NOW)
    await say(b, "hi")
    assert "Keep answers short" in b.model.calls[0]["system"]
    assert "PERSONA" in b.model.calls[0]["system"]


async def test_model_failure_gives_plain_message_and_keeps_owner_turn(make_brain):
    b = make_brain([[TextDelta("Let me "), ModelUnavailable("down")]])
    assert (await say(b, "check"))[-1] == MSG_UNAVAILABLE
    turns = b.store.recent_turns(10)
    assert turns[0].text == "check" and turns[1].text == "Let me […]"


async def test_model_failure_before_any_text_saves_only_the_owner_turn(make_brain):
    b = make_brain([[ModelUnavailable("down")]])
    assert await say(b, "check") == [MSG_UNAVAILABLE]
    assert [t.role for t in b.store.recent_turns(10)] == ["owner"]


async def test_only_recent_turns_are_sent_and_history_starts_with_the_owner(make_brain):
    b = make_brain([[TextDelta("ok"), Done("end_turn")]])
    for i in range(50):
        b.store.add_turn("owner" if i % 2 == 0 else "jarvis", f"old{i}", NOW)
    await say(b, "now")
    sent = b.model.calls[0]["messages"]
    assert len(sent) == 19 and sent[0].role == "user" and sent[-1].content == "now"


async def test_tool_loop_is_bounded(make_brain):
    loop = [ToolCall("t", "list_lessons", {}), Done("tool_use")]
    b = make_brain([loop] * 20)
    assert "too many steps" in "".join(await say(b, "go"))
    assert len(b.model.calls) == MAX_TOOL_ROUNDS


async def test_refusal_is_reported_plainly(make_brain):
    b = make_brain([[Done("refusal")]])
    assert await say(b, "something") == [MSG_REFUSED]


async def test_uses_fast_model_and_offers_tools(make_brain):
    b = make_brain([[TextDelta("ok"), Done("end_turn")]])
    await say(b, "hi")
    call = b.model.calls[0]
    assert call["model"] == "claude-haiku-5-5"
    assert {t.name for t in call["tools"]} == {
        "remember_fact", "remember_lesson", "list_lessons", "forget_lesson"}


async def test_a_specific_failure_reason_reaches_the_owner(make_brain):
    b = make_brain([[ModelUnavailable("401", user_message="My API key was rejected. Run: jarvis setup")]])
    assert await say(b, "hi") == ["My API key was rejected. Run: jarvis setup"]

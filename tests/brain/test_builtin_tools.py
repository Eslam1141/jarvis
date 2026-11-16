from datetime import date
from types import SimpleNamespace

import pytest
from conftest import NOW, replies

from jarvis.brain.builtin_tools import register_memory_tools
from jarvis.brain.tools import ToolRegistry, TurnState
from jarvis.gate import Gate
from jarvis.memory.lessons import Lessons
from jarvis.memory.profile import Profile

TODAY = date(2026, 11, 16)


@pytest.fixture
def env(tmp_path, store):
    registry = ToolRegistry()
    profile, lessons = Profile(tmp_path / "profile.md"), Lessons(tmp_path / "lessons.md")
    register_memory_tools(registry, profile, lessons, store, lambda: NOW)
    gate = Gate(ask=replies(), store=store, clock=lambda: NOW)
    state = TurnState()

    async def run(name, args):
        return await registry.run(name, args, state, gate)

    return SimpleNamespace(run=run, profile=profile, lessons=lessons, store=store, state=state)


async def test_remember_lesson_saves_and_logs(env):
    out = await env.run("remember_lesson", {"text": "No meetings before 10"})
    assert out == "saved as L1"
    assert env.lessons.list()[0].source == "owner_said"
    a = env.store.actions(1)[0]
    assert (a.kind, a.summary) == ("lesson.add", "L1: No meetings before 10")


async def test_list_and_forget(env):
    await env.run("remember_lesson", {"text": "a"})
    assert await env.run("list_lessons", {}) == f"L1 ({TODAY}): a"
    assert await env.run("forget_lesson", {"lesson_id": 1}) == "forgotten"
    assert env.store.actions(1)[0].kind == "lesson.forget"
    assert await env.run("list_lessons", {}) == "no lessons yet"
    assert await env.run("forget_lesson", {"lesson_id": 1}) == "no lesson L1"


async def test_remember_fact(env):
    assert await env.run("remember_fact", {"text": "Lives in Cairo"}) == "saved"
    assert "Lives in Cairo" in env.profile.read()
    assert env.store.actions(1)[0].kind == "profile.add"


async def test_memory_tools_refuse_after_outside_content(env):
    env.state.saw_outside_content = True
    for name, args in [("remember_lesson", {"text": "x"}), ("remember_fact", {"text": "x"}),
                       ("forget_lesson", {"lesson_id": 1})]:
        assert (await env.run(name, args)).startswith("refused:")
    assert env.lessons.list() == [] and env.profile.read() == ""


async def test_bad_arguments_return_an_error_not_a_crash(env):
    assert (await env.run("remember_lesson", {})).startswith("error:")
    assert (await env.run("forget_lesson", {"lesson_id": "one"})).startswith("error:")

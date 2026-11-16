import pytest
from conftest import NOW, replies

from jarvis.brain.model import ToolSpec
from jarvis.brain.tools import Tool, ToolRegistry, TurnState
from jarvis.gate import Gate


def returns(value):
    async def handler(args, state):
        return value
    return handler


def write_tool(name, ran, fail=False):
    async def handler(args, state):
        if fail:
            raise RuntimeError("smtp down")
        ran.append(args)
        return "sent"
    return Tool(name, "d", {"type": "object"}, handler, writes=True,
                describe=lambda args: f"Send to {args.get('to', '?')}.")


@pytest.fixture
def registry():
    return ToolRegistry()


@pytest.fixture
def gate(store):
    return Gate(ask=replies(), store=store, clock=lambda: NOW)


async def test_read_tool_runs_without_asking(registry, gate):
    registry.register(Tool("look", "d", {}, returns("seen"), writes=False))
    assert await registry.run("look", {}, TurnState(), gate) == "seen"


async def test_write_tool_declined_does_not_run(registry, store):
    ran = []
    registry.register(write_tool("send", ran))
    out = await registry.run("send", {}, TurnState(), Gate(replies("no"), store, lambda: NOW))
    assert out == "declined by owner" and ran == [] and store.actions(10) == []


async def test_write_tool_approved_runs_and_is_logged(registry, store):
    ran, asked = [], []
    registry.register(write_tool("send", ran))
    g = Gate(replies("yes", record=asked), store, lambda: NOW)
    out = await registry.run("send", {"to": "Ali"}, TurnState(), g)
    assert out == "sent" and ran == [{"to": "Ali"}]
    assert asked[0].startswith("Send to Ali.")
    a = store.actions(10)[0]
    assert (a.kind, a.summary, a.detail) == ("send", "Send to Ali.", '{"to": "Ali"}')


async def test_write_tool_that_raises_is_not_logged(registry, store):
    registry.register(write_tool("send", [], fail=True))
    out = await registry.run("send", {}, TurnState(), Gate(replies("yes"), store, lambda: NOW))
    assert out == "error: smtp down" and store.actions(10) == []


async def test_read_tool_that_raises_returns_error(registry, gate):
    async def bad(args, state):
        raise ValueError("nope")
    registry.register(Tool("look", "d", {}, bad, writes=False))
    assert await registry.run("look", {}, TurnState(), gate) == "error: nope"


def test_write_tool_without_describe_cannot_be_registered(registry):
    with pytest.raises(ValueError):
        registry.register(Tool("x", "d", {}, returns(""), writes=True))


def test_duplicate_name_cannot_be_registered(registry):
    registry.register(Tool("x", "d", {}, returns(""), writes=False))
    with pytest.raises(ValueError):
        registry.register(Tool("x", "d", {}, returns(""), writes=False))


async def test_outside_content_blocks_owner_only_tools(registry, gate):
    registry.register(Tool("read_mail", "d", {}, returns("hi"), writes=False, outside_content=True))
    registry.register(Tool("remember_lesson", "d", {}, returns("saved"), writes=False, owner_only=True))
    st = TurnState()
    assert await registry.run("remember_lesson", {}, st, gate) == "saved"
    await registry.run("read_mail", {}, st, gate)
    assert st.saw_outside_content is True
    assert (await registry.run("remember_lesson", {}, st, gate)).startswith("refused:")


async def test_unknown_tool(registry, gate):
    assert await registry.run("nope", {}, TurnState(), gate) == "error: unknown tool nope"


def test_specs_list_registered_tools(registry):
    registry.register(Tool("look", "Look at it", {"type": "object"}, returns(""), writes=False))
    assert registry.specs() == [ToolSpec("look", "Look at it", {"type": "object"})]


async def test_action_that_ran_but_could_not_be_logged_is_still_reported_as_done(registry, store):
    ran = []
    registry.register(write_tool("send", ran))
    g = Gate(replies("yes"), store, lambda: NOW)

    def broken_record(*a):
        raise RuntimeError("database is locked")

    g.record = broken_record
    out = await registry.run("send", {"to": "Ali"}, TurnState(), g)
    assert ran == [{"to": "Ali"}]
    assert out.startswith("sent") and "not be logged" in out and not out.startswith("error")

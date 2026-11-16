import anthropic
import httpx2
import pytest

from jarvis.brain.anthropic_model import AnthropicModel
from jarvis.brain.model import Done, FakeModel, Message, ModelUnavailable, TextDelta


async def collect(stream):
    return [e async for e in stream]


async def test_fake_model_plays_scripts_in_order():
    m = FakeModel([[TextDelta("a"), Done("end_turn")], [TextDelta("b"), Done("end_turn")]])
    first = await collect(m.stream(system="s", messages=[], tools=[], model="x"))
    second = await collect(m.stream(system="s", messages=[], tools=[], model="x"))
    assert first[0] == TextDelta("a") and second[0] == TextDelta("b")
    assert len(m.calls) == 2
    assert set(m.calls[0]) == {"system", "messages", "tools", "model"}


async def test_fake_model_raises_scripted_exception():
    m = FakeModel([[TextDelta("par"), ModelUnavailable("down")]])
    with pytest.raises(ModelUnavailable):
        await collect(m.stream(system="s", messages=[], tools=[], model="x"))


async def test_fake_model_snapshots_messages():
    m = FakeModel([[Done("end_turn")]])
    msgs = [Message("user", "hi")]
    await collect(m.stream(system="s", messages=msgs, tools=[], model="x"))
    msgs.append(Message("assistant", "later"))
    assert len(m.calls[0]["messages"]) == 1


async def test_anthropic_model_maps_sdk_errors(monkeypatch):
    model = AnthropicModel(api_key="k")

    def boom(**kwargs):
        raise anthropic.APIConnectionError(
            request=httpx2.Request("POST", "https://api.anthropic.com/v1/messages"))

    monkeypatch.setattr(model._client.messages, "stream", boom)
    with pytest.raises(ModelUnavailable):
        await collect(model.stream(
            system="s", messages=[Message("user", "hi")], tools=[], model="claude-sonnet-5-5"))


class FakeStream:
    def __init__(self, events, final):
        self._events, self._final = events, final

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    def __aiter__(self):
        async def gen():
            for e in self._events:
                yield e
        return gen()

    async def get_final_message(self):
        return self._final


def ns(**kw):
    from types import SimpleNamespace
    return SimpleNamespace(**kw)


def patch_stream(monkeypatch, model, events, final):
    seen = {}

    def fake(**kwargs):
        seen.update(kwargs)
        return FakeStream(events, final)

    monkeypatch.setattr(model._client.messages, "stream", fake)
    return seen


async def test_anthropic_model_streams_text_and_sends_request_shape(monkeypatch):
    from jarvis.brain.model import ToolSpec
    model = AnthropicModel(api_key="k", thinking={"type": "between_tools"})
    final = ns(stop_reason="end_turn", content=[ns(type="text", text="Hello.")])
    seen = patch_stream(monkeypatch, model,
                        [ns(type="text", text="Hel"), ns(type="thinking"), ns(type="text", text="lo.")],
                        final)
    events = await collect(model.stream(
        system="SYS", messages=[Message("user", "hi")],
        tools=[ToolSpec("t", "d", {"type": "object"})], model="claude-sonnet-5-5"))
    assert events == [TextDelta("Hel"), TextDelta("lo."), Done("end_turn")]
    assert events[-1].content == final.content
    assert seen["model"] == "claude-sonnet-5-5" and seen["system"] == "SYS"
    assert seen["messages"] == [{"role": "user", "content": "hi"}]
    assert seen["tools"] == [{"name": "t", "description": "d", "input_schema": {"type": "object"}}]
    assert seen["output_config"] == {"effort": "low"}
    assert seen["thinking"] == {"type": "between_tools"}


async def test_anthropic_model_omits_tools_and_thinking_when_not_given(monkeypatch):
    model = AnthropicModel(api_key="k")
    seen = patch_stream(monkeypatch, model, [], ns(stop_reason="end_turn", content=[]))
    await collect(model.stream(system="s", messages=[], tools=[], model="m"))
    assert "tools" not in seen and "thinking" not in seen


async def test_anthropic_model_yields_tool_calls(monkeypatch):
    from jarvis.brain.model import ToolCall
    model = AnthropicModel(api_key="k")
    final = ns(stop_reason="tool_use", content=[
        ns(type="thinking"), ns(type="tool_use", id="tu1", name="list_lessons", input={})])
    patch_stream(monkeypatch, model, [], final)
    events = await collect(model.stream(system="s", messages=[], tools=[], model="m"))
    assert events == [ToolCall("tu1", "list_lessons", {}), Done("tool_use")]


async def test_anthropic_model_does_not_run_truncated_tool_calls(monkeypatch):
    model = AnthropicModel(api_key="k")
    final = ns(stop_reason="max_tokens", content=[
        ns(type="tool_use", id="tu1", name="send", input={"to": "a"})])
    patch_stream(monkeypatch, model, [], final)
    events = await collect(model.stream(system="s", messages=[], tools=[], model="m"))
    assert events == [Done("max_tokens")]

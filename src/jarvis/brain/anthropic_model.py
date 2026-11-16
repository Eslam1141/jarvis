"""Model client backed by the Anthropic API (streaming Messages)."""

from collections.abc import AsyncIterator

import anthropic

from jarvis.brain.model import (
    Done,
    Message,
    ModelEvent,
    ModelUnavailable,
    TextDelta,
    ToolCall,
    ToolSpec,
)

MAX_TOKENS = 16000


class AnthropicModel:
    def __init__(self, api_key: str, effort: str = "low", thinking: dict | None = None):
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._effort = effort
        self._thinking = thinking

    async def stream(
        self, *, system: str, messages: list[Message], tools: list[ToolSpec], model: str
    ) -> AsyncIterator[ModelEvent]:
        request = {
            "model": model,
            "max_tokens": MAX_TOKENS,
            "system": system,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "output_config": {"effort": self._effort},
        }
        if self._thinking:
            request["thinking"] = self._thinking
        if tools:
            request["tools"] = [
                {"name": t.name, "description": t.description, "input_schema": t.input_schema}
                for t in tools
            ]
        try:
            async with self._client.messages.stream(**request) as stream:
                async for event in stream:
                    if event.type == "text":
                        yield TextDelta(event.text)
                final = await stream.get_final_message()
        except anthropic.AuthenticationError as e:
            raise ModelUnavailable("The API key was rejected. Run: jarvis setup") from e
        except (anthropic.APIConnectionError, anthropic.APIStatusError) as e:
            raise ModelUnavailable(str(e)) from e

        # A reply cut off by the token limit can carry a half-written tool
        # request; it must not be run.
        if final.stop_reason == "tool_use":
            for block in final.content:
                if block.type == "tool_use":
                    yield ToolCall(block.id, block.name, dict(block.input))
        yield Done(final.stop_reason or "end_turn", list(final.content))

"""Jarvis's brain: sends the conversation to Claude, runs tools, streams replies.

This module doesn't print anything. The chat window (cli.py) — and later the
voice and mobile front ends — pass in callbacks to show what's happening.
"""

from __future__ import annotations

import platform
from dataclasses import dataclass
from typing import Any, Callable

import anthropic

from .config import Settings
from .storage import Memory, Reminders
from .tools import ConfirmFn, Toolbox

# Lets Claude's safety system retry a declined request on a suitable model.
FALLBACK_BETA = "server-side-fallback-2026-07-01"


@dataclass
class Callbacks:
    on_text: Callable[[str], None] = lambda text: None          # reply text, piece by piece
    on_thinking: Callable[[], None] = lambda: None              # Claude started thinking
    on_tool: Callable[[str, dict], None] = lambda name, args: None  # a tool is about to run
    on_search: Callable[[str], None] = lambda kind: None        # web search / fetch started


def build_system_prompt(settings: Settings, memory: Memory) -> str:
    name = settings.user_name or "the user"
    if settings.language == "ar":
        lang_rule = "Always reply in Arabic."
    elif settings.language == "en":
        lang_rule = "Always reply in English."
    else:
        lang_rule = (
            "Reply in the language the user writes in. If they write in Arabic, reply in "
            "Arabic, matching their dialect (for example Egyptian) when you can tell it."
        )
    facts = "\n".join(f"- {m['fact']}" for m in memory.items) or "- (nothing saved yet)"
    return f"""You are Jarvis, a personal AI assistant for {name}, inspired by J.A.R.V.I.S. from Iron Man: \
capable, calm, quietly witty, and loyal. Address the user as "{settings.user_name or 'sir'}" now and then, \
not in every message.

You are talking in a chat window on the user's {platform.system()} computer. Keep replies short and \
conversational unless the user asks for detail. Write plain text without Markdown symbols (no **, #, or tables), since your replies are shown in a terminal and will later be spoken aloud.

{lang_rule}

Use your tools when they help: check the date and time, save and look up facts about the user, \
manage reminders, open websites and apps, and search the web for current information. When the \
user tells you something worth remembering long-term (a preference, a name, a goal), save it with \
the remember tool without being asked. Don't make up results — if a tool fails, say so.

What you already know about the user (saved in earlier conversations):
{facts}"""


class Jarvis:
    def __init__(self, settings: Settings, confirm: ConfirmFn, client: anthropic.Anthropic | None = None):
        self.settings = settings
        self.client = client or anthropic.Anthropic()
        self.memory = Memory(settings.data_dir)
        self.reminders = Reminders(settings.data_dir)
        self.toolbox = Toolbox(self.memory, self.reminders, confirm)
        self.system = build_system_prompt(settings, self.memory)
        self.messages: list[dict[str, Any]] = []

    def reset(self) -> None:
        """Start a new conversation (saved memories and reminders are kept)."""
        self.system = build_system_prompt(self.settings, self.memory)
        self.messages = []

    def _tools(self) -> list[dict[str, Any]]:
        tools = self.toolbox.schemas()
        if self.settings.web_search:
            tools += [
                {"type": "web_search_20260209", "name": "web_search", "max_uses": 5},
                {"type": "web_fetch_20260209", "name": "web_fetch", "max_uses": 5},
            ]
        return tools

    def _stream_once(self, cb: Callbacks):
        with self.client.beta.messages.stream(
            model=self.settings.model,
            max_tokens=self.settings.max_tokens,
            system=self.system,
            messages=self.messages,
            tools=self._tools(),
            output_config={"effort": self.settings.effort},
            cache_control={"type": "ephemeral"},
            betas=[FALLBACK_BETA],
            fallbacks="default",
        ) as stream:
            for event in stream:
                if event.type == "text":
                    cb.on_text(event.text)
                elif event.type == "content_block_start":
                    block = event.content_block
                    if block.type == "thinking":
                        cb.on_thinking()
                    elif block.type == "server_tool_use":
                        cb.on_search(block.name)
            return stream.get_final_message()

    def chat(self, user_text: str, cb: Callbacks | None = None) -> str:
        """Send one user message and return Jarvis's full reply text."""
        cb = cb or Callbacks()
        # Put a blank line between text written before and after a tool call.
        printed = {"any": False, "need_break": False}
        user_on_text = cb.on_text

        def on_text(chunk: str) -> None:
            if printed["need_break"]:
                user_on_text("\n\n")
                printed["need_break"] = False
            printed["any"] = True
            user_on_text(chunk)

        cb = Callbacks(on_text=on_text, on_thinking=cb.on_thinking, on_tool=cb.on_tool, on_search=cb.on_search)
        start = len(self.messages)
        self.messages.append({"role": "user", "content": user_text})
        reply_parts: list[str] = []
        json_retries = 0
        try:
            while True:
                try:
                    response = self._stream_once(cb)
                    json_retries = 0
                except ValueError:
                    # The SDK couldn't parse a streamed tool input at all; ask again (bounded).
                    json_retries += 1
                    if json_retries > 2:
                        raise
                    continue

                reply_parts += [b.text for b in response.content if b.type == "text"]
                # Always keep the full content (including thinking blocks), unchanged.
                self.messages.append({"role": "assistant", "content": response.content})

                if response.stop_reason == "refusal":
                    note = "\n[Jarvis declined to answer that one.]"
                    cb.on_text(note)
                    reply_parts.append(note)
                    break
                if response.stop_reason == "pause_turn":
                    continue  # a long web search paused; let it carry on

                tool_uses = [b for b in response.content if b.type == "tool_use"]
                if not tool_uses:
                    break

                results = []
                for block in tool_uses:
                    if response.stop_reason == "max_tokens":
                        text, is_error = "Tool input was cut off (reply too long). Try again more briefly.", True
                    else:
                        cb.on_tool(block.name, block.input if isinstance(block.input, dict) else {})
                        text, is_error = self.toolbox.run(block.name, block.input)
                    results.append({"type": "tool_result", "tool_use_id": block.id,
                                    "content": text, "is_error": is_error})
                # All results go back together in one message.
                self.messages.append({"role": "user", "content": results})
                printed["need_break"] = printed["any"]
        except BaseException:
            # Drop this unfinished turn so the conversation stays valid for the next message.
            del self.messages[start:]
            raise
        return "\n\n".join(p for p in reply_parts if p.strip())

# 0001 — How the brain talks to the model

Date: 2026-11-16
Status: decided for Phase 0; numbers still to be measured

## Decision

Live conversation turns call the Anthropic Messages API directly, streaming,
through `jarvis.brain.anthropic_model.AnthropicModel`. The brain depends only
on the `ModelClient` interface, so the client can be swapped without touching
the loop.

The Claude Agent SDK is not used for live turns. It wraps the Claude Code
agent loop and its built-in file and shell tools, which Jarvis's conversation
does not need, and it can only add time on top of a direct call. It stays the
intended tool for long, multi-step coding work (roadmap task 7.4), and is
evaluated there.

This departs from the plan, which called for timing the Agent SDK next to the
direct call. The direct call is the faster of the two by construction, so the
measurement that matters is whether the direct call meets the budget.

## Settings chosen

- Fast model `claude-sonnet-5-5` at effort `low` for conversation.
- Deep model `claude-opus-5-5` for idea workshops and channel analysis
  (the plan said `claude-fable-5-2`; Opus 5.5 is the standard default, costs
  half as much, and has no data-retention precondition. Change `deep_model`
  in `~/.jarvis/config.toml` to use Fable).
- No automatic fallback model when a request is declined. Jarvis says he
  cannot help with that request. Server-side fallbacks can be added later.

## Still to measure

Run, after `uv run jarvis setup`:

    uv run python scripts/latency_probe.py

Budget: first full sentence within 1.0 s (median). Then apply:

| Result | Action |
|---|---|
| Sonnet, low effort, median <= 1.0 s | Keep the defaults |
| Only "thinking only between tools" meets it | Pass `thinking={"type": "between_tools"}` when constructing `AnthropicModel` in `jarvis.__main__.make_model` |
| Only Haiku meets it | Set `fast_model = "claude-haiku-5-5"` in config |
| None meets it | Stop and rethink before Phase 1 (shorter prompt, prompt caching, or a spoken acknowledgement while the answer forms) |

## Measured

| Option | Median | p90 |
|---|---|---|
| sonnet-5-5, low effort | not yet run | |
| sonnet-5-5, low effort, thinking only between tools | not yet run | |
| haiku-5-5, low effort | not yet run | |

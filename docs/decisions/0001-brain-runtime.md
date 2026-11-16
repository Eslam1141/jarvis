# 0001 — How the brain talks to the model

Date: 2026-11-16
Status: decided for Phase 0; measured 2026-11-17, budget not met, switched to Haiku (see Outcome)

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

- Fast model `claude-haiku-5-5` at effort `low` for conversation (was
  `claude-sonnet-5-5` until the measurement below).
- Deep model `claude-opus-5-5` for idea workshops and channel analysis
  (the plan said `claude-fable-5-2`; Opus 5.5 is the standard default, costs
  half as much, and has no data-retention precondition. Change `deep_model`
  in `~/.jarvis/config.toml` to use Fable).
- No automatic fallback model when a request is declined. Jarvis says he
  cannot help with that request. Server-side fallbacks can be added later.

## How to measure

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

2026-11-17, owner's Mac, 20 runs each, time to the first full sentence.

| Option | Median | p90 |
|---|---|---|
| sonnet-5-5, low effort | 2.13 s | 5.83 s |
| sonnet-5-5, low effort, thinking only between tools | 2.11 s | 5.24 s |
| haiku-5-5, low effort | 1.16 s | 1.31 s |

## Outcome

No option meets the 1.0 s budget, so the last row of the table applies:
rethink before Phase 1 code.

- Sonnet is about twice the budget and uneven (p90 over 5 s). It cannot be
  the voice of a 2-second assistant as configured.
- Turning thinking off between tools changes nothing, so thinking is not
  the cause.
- Haiku misses by 0.16 s and is steady (p90 1.31 s). With STT 0.7 s and TTS
  0.3 s that is about 2.2 s end to end against a goal of about 2 s.

Options considered:

1. Haiku for spoken turns (`fast_model = "claude-haiku-5-5"`), Sonnet or
   Opus only when a turn needs depth. Closest to the goal today.
2. Prompt caching for the system prompt (personality, profile, lessons),
   then measure again; it may bring either model down.
3. A short spoken acknowledgement while the answer forms, so a slower
   model still feels immediate.

Decided 2026-11-17 by the owner: option 1. `fast_model` now defaults to
`claude-haiku-5-5`. It still misses the budget by 0.16 s, so options 2 and 3
stay open for the Phase 1 plan, as does routing a turn that needs depth to
a stronger model (not built yet: every live turn uses `fast_model`).

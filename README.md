# Jarvis

A personal assistant in the spirit of Jarvis from Iron Man: you talk to him,
he talks back, and he acts as your agent across mail, calendar, ideas and
your YouTube channels. He learns from your corrections as you go.

**Status: Phase 0 of 8.** Today Jarvis is a terminal chat with a personality,
a memory, and lessons he learns from you. Voice, mail, calendar and the rest
are planned in the [roadmap](docs/superpowers/plans/2026-11-16-jarvis-roadmap.md).

## Run it

Needs macOS, Python 3.12 and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run jarvis setup   # asks your name and your Anthropic API key
uv run jarvis chat
```

The API key is typed hidden and stored in the macOS Keychain. It is never
written to a file.

Things to try:

- "Keep your answers to one sentence." He confirms the lesson and follows it,
  including after a restart.
- "What have you learned?" and "Forget that."
- Write in Egyptian Arabic; he answers in Arabic.

## Where his data lives

Everything Jarvis knows is on your Mac in `~/.jarvis/` (set `JARVIS_HOME` to
move it), in files you can read and edit:

| File | What it holds |
|---|---|
| `profile.md` | Facts he has learned about you |
| `lessons.md` | Rules you taught him, dated |
| `personality.md` | Optional. Create it to replace his built-in character |
| `config.toml` | Your name and which models he uses |
| `jarvis.db` | Conversation history and a log of what he did |

Nothing in that folder belongs in this repository, which is public.

## Settings

`~/.jarvis/config.toml`:

```toml
owner_name = "Sir"
fast_model = "claude-sonnet-5-5"   # live conversation
deep_model = "claude-opus-5-5"     # long thinking, used from Phase 4 on
history_turns = 20
```

## Development

```bash
uv run pytest
uv run python scripts/latency_probe.py   # real, billed API calls
```

- [Design](docs/superpowers/specs/2026-11-16-jarvis-design.md)
- [Roadmap](docs/superpowers/plans/2026-11-16-jarvis-roadmap.md)
- [Decisions](docs/decisions/)

Rules that hold in every phase: anything that changes the outside world
(sending mail, changing a calendar) runs only after an explicit yes; text
inside emails, invites and comments is never treated as an instruction; and
everything he learns stays readable and removable.

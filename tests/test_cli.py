import pytest

from jarvis.__main__ import main
from jarvis.brain.model import Done, FakeModel, ModelUnavailable, TextDelta, ToolCall
from jarvis.config import load_config
from jarvis.secrets import ANTHROPIC_KEY, get_secret, set_secret


def feed_input(monkeypatch, lines):
    queue = list(lines)

    def fake_input(prompt=""):
        if not queue:
            raise EOFError
        return queue.pop(0)

    monkeypatch.setattr("builtins.input", fake_input)


def use_model(monkeypatch, scripts):
    model = FakeModel(scripts)
    monkeypatch.setattr("jarvis.__main__.make_model", lambda key: model)
    return model


def test_chat_without_key_points_to_setup(memory_keyring, tmp_home, capsys):
    assert main(["chat"]) == 2
    assert "Run: jarvis setup" in capsys.readouterr().out


def test_setup_stores_key_and_name(memory_keyring, tmp_home, monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda _="": "Eslam")
    monkeypatch.setattr("getpass.getpass", lambda _="": "sk-test-123")
    monkeypatch.setattr("jarvis.__main__.filevault_is_on", lambda: True)
    assert main(["setup"]) == 0
    assert get_secret(ANTHROPIC_KEY) == "sk-test-123"
    assert load_config().owner_name == "Eslam"
    out = capsys.readouterr().out
    assert "sk-test-123" not in out and "Setup complete. Run: jarvis chat" in out
    assert "sk-test-123" not in (tmp_home / ".jarvis" / "config.toml").read_text()


def test_setup_warns_when_filevault_off(memory_keyring, tmp_home, monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda _="": "Eslam")
    monkeypatch.setattr("getpass.getpass", lambda _="": "sk-test-123")
    monkeypatch.setattr("jarvis.__main__.filevault_is_on", lambda: False)
    assert main(["setup"]) == 0 and "FileVault is off" in capsys.readouterr().out


def test_setup_keeps_existing_key_when_none_entered(memory_keyring, tmp_home, monkeypatch):
    set_secret(ANTHROPIC_KEY, "old")
    monkeypatch.setattr("builtins.input", lambda _="": "")
    monkeypatch.setattr("getpass.getpass", lambda _="": "")
    monkeypatch.setattr("jarvis.__main__.filevault_is_on", lambda: True)
    assert main(["setup"]) == 0
    assert get_secret(ANTHROPIC_KEY) == "old" and load_config().owner_name == "Sir"


def test_setup_without_any_key_fails(memory_keyring, tmp_home, monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda _="": "")
    monkeypatch.setattr("getpass.getpass", lambda _="": "")
    monkeypatch.setattr("jarvis.__main__.filevault_is_on", lambda: True)
    assert main(["setup"]) == 2 and "No API key" in capsys.readouterr().out


def test_chat_loop_with_fake_model(memory_keyring, tmp_home, monkeypatch, capsys):
    set_secret(ANTHROPIC_KEY, "k")
    use_model(monkeypatch, [[TextDelta("Hello."), Done("end_turn")]])
    feed_input(monkeypatch, ["hi", "exit"])
    assert main(["chat"]) == 0 and "jarvis> Hello." in capsys.readouterr().out


def test_chat_ends_cleanly_on_end_of_input(memory_keyring, tmp_home, monkeypatch):
    set_secret(ANTHROPIC_KEY, "k")
    use_model(monkeypatch, [])
    feed_input(monkeypatch, [])
    assert main(["chat"]) == 0


def test_chat_survives_model_failure_and_continues(memory_keyring, tmp_home, monkeypatch, capsys):
    set_secret(ANTHROPIC_KEY, "k")
    use_model(monkeypatch, [[ModelUnavailable("down")], [TextDelta("Back."), Done("end_turn")]])
    feed_input(monkeypatch, ["one", "two", "quit"])
    assert main(["chat"]) == 0
    out = capsys.readouterr().out
    assert "can't reach my brain" in out and "jarvis> Back." in out


def test_chat_remembers_a_lesson_across_restarts(memory_keyring, tmp_home, monkeypatch, capsys):
    set_secret(ANTHROPIC_KEY, "k")
    use_model(monkeypatch, [
        [ToolCall("t1", "remember_lesson", {"text": "One sentence answers"}), Done("tool_use")],
        [TextDelta("Noted."), Done("end_turn")],
    ])
    feed_input(monkeypatch, ["keep answers to one sentence", "exit"])
    assert main(["chat"]) == 0
    second = use_model(monkeypatch, [[TextDelta("Hi."), Done("end_turn")]])
    feed_input(monkeypatch, ["hello", "exit"])
    assert main(["chat"]) == 0
    assert "One sentence answers" in second.calls[0]["system"]
    assert "[L1]" in (tmp_home / ".jarvis" / "lessons.md").read_text()


def test_unknown_command_shows_usage(capsys):
    with pytest.raises(SystemExit):
        main(["dance"])


class LoopRecordingModel:
    """Records which event loop each call ran on; can interrupt the first call."""

    def __init__(self, interrupt_first=False):
        self.loops, self._interrupt = [], interrupt_first

    async def stream(self, *, system, messages, tools, model):
        import asyncio
        self.loops.append(asyncio.get_running_loop())
        if self._interrupt and len(self.loops) == 1:
            raise KeyboardInterrupt
        yield TextDelta("ok")
        yield Done("end_turn")


def test_every_turn_runs_on_the_same_event_loop(memory_keyring, tmp_home, monkeypatch):
    # The real API client keeps network connections tied to one event loop.
    set_secret(ANTHROPIC_KEY, "k")
    model = LoopRecordingModel()
    monkeypatch.setattr("jarvis.__main__.make_model", lambda key: model)
    feed_input(monkeypatch, ["one", "two", "exit"])
    assert main(["chat"]) == 0
    assert len(model.loops) == 2 and model.loops[0] is model.loops[1]


def test_ctrl_c_during_a_reply_returns_to_the_prompt(memory_keyring, tmp_home, monkeypatch, capsys):
    set_secret(ANTHROPIC_KEY, "k")
    model = LoopRecordingModel(interrupt_first=True)
    monkeypatch.setattr("jarvis.__main__.make_model", lambda key: model)
    feed_input(monkeypatch, ["one", "two", "exit"])
    assert main(["chat"]) == 0
    out = capsys.readouterr().out
    assert "(stopped)" in out and "jarvis> ok" in out

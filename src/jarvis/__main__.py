"""Command line: `jarvis setup` and `jarvis chat`."""

import argparse
import asyncio
import getpass
import subprocess
import sys
from datetime import datetime

from jarvis.brain.anthropic_model import AnthropicModel
from jarvis.brain.brain import Brain
from jarvis.brain.builtin_tools import register_memory_tools
from jarvis.brain.model import ModelClient
from jarvis.brain.tools import ToolRegistry
from jarvis.config import load_config, save_setting
from jarvis.gate import Gate
from jarvis.memory.lessons import Lessons
from jarvis.memory.profile import Profile
from jarvis.memory.store import Store
from jarvis.paths import data_dir
from jarvis.secrets import ANTHROPIC_KEY, get_secret, set_secret

FILEVAULT_WARNING = (
    "Warning: FileVault is off. Jarvis's data folder would be readable "
    "from a stolen disk."
)


def filevault_is_on() -> bool:
    try:
        result = subprocess.run(
            ["fdesetup", "status"], capture_output=True, text=True, timeout=10
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return "FileVault is On" in result.stdout


def make_model(key: str) -> ModelClient:
    return AnthropicModel(api_key=key)


def setup() -> int:
    folder = data_dir()
    print(f"Jarvis keeps his data in {folder}")
    if not filevault_is_on():
        print(FILEVAULT_WARNING)

    name = input("What should Jarvis call you? (Enter to keep the current name) ").strip()
    if name:
        save_setting("owner_name", name)

    key = getpass.getpass(
        "Anthropic API key (typing is hidden; Enter to keep the stored one): "
    ).strip()
    if key:
        set_secret(ANTHROPIC_KEY, key)
        print("API key stored in the macOS Keychain.")
    elif not get_secret(ANTHROPIC_KEY):
        print("No API key stored. Run jarvis setup again when you have one.")
        return 2

    print("Setup complete. Run: jarvis chat")
    return 0


async def _ask_in_terminal(question: str) -> str:
    print(f"\njarvis> {question}")
    try:
        return input("you> ")
    except EOFError:
        return ""


def build_brain(key: str) -> Brain:
    folder = data_dir()
    store = Store(folder / "jarvis.db")
    profile = Profile(folder / "profile.md")
    lessons = Lessons(folder / "lessons.md")
    registry = ToolRegistry()
    register_memory_tools(registry, profile, lessons, store, datetime.now)
    return Brain(
        model=make_model(key),
        registry=registry,
        gate=Gate(ask=_ask_in_terminal, store=store, clock=datetime.now),
        store=store,
        profile=profile,
        lessons=lessons,
        config=load_config(),
        clock=datetime.now,
    )


async def _reply(brain: Brain, text: str) -> None:
    print("jarvis> ", end="", flush=True)
    async for chunk in brain.respond(text):
        print(chunk, end="", flush=True)
    print()


def chat() -> int:
    key = get_secret(ANTHROPIC_KEY)
    if not key:
        print("No API key found. Run: jarvis setup")
        return 2
    try:
        brain = build_brain(key)
    except ValueError as e:  # a mistake in config.toml
        print(e)
        return 2

    print("Jarvis is listening. Type 'exit' to leave.")
    # One event loop for the whole chat: the API client's network connections
    # belong to the loop they were opened on.
    loop = asyncio.new_event_loop()
    try:
        while True:
            try:
                text = input("you> ")
            except (EOFError, KeyboardInterrupt):
                print()
                return 0
            if text.strip().lower() in {"exit", "quit"}:
                return 0
            task = loop.create_task(_reply(brain, text))
            try:
                loop.run_until_complete(task)
            except KeyboardInterrupt:
                task.cancel()
                loop.run_until_complete(asyncio.gather(task, return_exceptions=True))
                print("\n(stopped)")
    finally:
        loop.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="jarvis", description="Your personal assistant.")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("setup", help="store your API key and name")
    commands.add_parser("chat", help="talk to Jarvis in the terminal")
    args = parser.parse_args(argv)
    return setup() if args.command == "setup" else chat()


if __name__ == "__main__":
    sys.exit(main())

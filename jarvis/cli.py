"""The chat window: type to Jarvis in your terminal."""

from __future__ import annotations

import sys

import anthropic
from rich.console import Console
from rich.prompt import Confirm

from .brain import Callbacks, Jarvis
from .config import Settings

HELP = """Commands:
  /new        start a fresh conversation (memories and reminders are kept)
  /memory     show what Jarvis remembers about you
  /reminders  show pending reminders
  /help       show this help
  /quit       exit (or press Ctrl+C)"""


def _fix_windows_console() -> None:
    # Make Arabic and emoji print correctly in the Windows terminal.
    for stream in (sys.stdout, sys.stderr, sys.stdin):
        try:
            stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except (AttributeError, ValueError):
            pass


def main() -> None:
    _fix_windows_console()
    console = Console()
    settings = Settings.load()

    def confirm(question: str) -> bool:
        console.print()
        return Confirm.ask(f"[yellow]{question}[/yellow]", default=False)

    try:
        jarvis = Jarvis(settings, confirm=confirm)
    except anthropic.AnthropicError as exc:
        console.print(f"[red]Couldn't start Jarvis: {exc}[/red]")
        console.print("Put your API key in a file called .env:  ANTHROPIC_API_KEY=sk-ant-...")
        return

    greeting = f"Good day{', ' + settings.user_name if settings.user_name else ''}. Jarvis online."
    console.print(f"[bold cyan]{greeting}[/bold cyan]  [dim](/help for commands)[/dim]\n")

    while True:
        for r in jarvis.reminders.due():
            console.print(f"[bold magenta]⏰ Reminder:[/bold magenta] {r['text']}  [dim]({r['when']})[/dim]")
            jarvis.reminders.update(r["id"], notified=True)

        try:
            text = console.input("[bold green]You ›[/bold green] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[cyan]Goodbye.[/cyan]")
            return
        if not text:
            continue

        command = text.lower()
        if command in ("/quit", "/exit"):
            console.print("[cyan]Goodbye.[/cyan]")
            return
        if command == "/help":
            console.print(HELP)
            continue
        if command == "/new":
            jarvis.reset()
            console.print("[dim]New conversation started.[/dim]")
            continue
        if command == "/memory":
            for m in jarvis.memory.items or [{"id": "-", "fact": "Nothing saved yet."}]:
                console.print(f"  [dim]{m['id']}.[/dim] {m['fact']}")
            continue
        if command == "/reminders":
            for r in jarvis.reminders.pending() or [{"id": "-", "text": "No reminders.", "when": ""}]:
                console.print(f"  [dim]{r['id']}.[/dim] {r['text']} [dim]{r['when']}[/dim]")
            continue

        console.print("[bold cyan]Jarvis ›[/bold cyan] ", end="")
        status = console.status("[dim]thinking…[/dim]", spinner="dots")
        spinning = False

        def spin(message: str) -> None:
            nonlocal spinning
            status.update(message)
            if not spinning:
                status.start()
                spinning = True

        def stop_spin() -> None:
            nonlocal spinning
            if spinning:
                status.stop()
                spinning = False

        def on_text(chunk: str) -> None:
            stop_spin()
            console.print(chunk, end="", markup=False, highlight=False)

        def on_tool(name: str, args: dict) -> None:
            spin(f"[dim]using {name}…[/dim]")

        def on_search(kind: str) -> None:
            spin("[dim]searching the web…[/dim]" if kind == "web_search" else "[dim]reading a page…[/dim]")

        def pause_for_prompt(question: str) -> bool:
            stop_spin()
            return confirm(question)

        spin("[dim]thinking…[/dim]")
        jarvis.toolbox.confirm = pause_for_prompt
        try:
            jarvis.chat(text, Callbacks(on_text=on_text, on_tool=on_tool, on_search=on_search))
        except KeyboardInterrupt:
            console.print("\n[dim](stopped)[/dim]")
        except anthropic.AuthenticationError:
            console.print("\n[red]Your API key was rejected. Check ANTHROPIC_API_KEY in .env.[/red]")
        except anthropic.RateLimitError:
            console.print("\n[red]Too many requests right now. Wait a moment and try again.[/red]")
        except anthropic.APIStatusError as exc:
            console.print(f"\n[red]Claude API error {exc.status_code}: {exc.message}[/red]")
        except anthropic.APIConnectionError:
            console.print("\n[red]Can't reach Claude. Check your internet connection.[/red]")
        finally:
            stop_spin()
        console.print("\n")


if __name__ == "__main__":
    main()

# Jarvis

My personal assistant, inspired by J.A.R.V.I.S. from Iron Man and powered by Claude.

Version 0.1 is a chat window in your terminal. Jarvis can:

- hold a conversation in **English or Arabic** (it replies in the language you write in)
- **remember** things about you between sessions ("remember that my sister's name is Mona")
- set **reminders** ("remind me to call mom at 6pm"); they pop up when they're due while Jarvis is open
- **search the web** and read pages for current information
- **open websites and apps** on your computer (it asks you first)
- tell you the date and time, and basic facts about your computer

## Setup on Windows

1. Install **Python 3.10 or newer** from <https://www.python.org/downloads/>.
   During setup, tick **"Add python.exe to PATH"**.
2. Get an API key from the Anthropic Console: <https://console.anthropic.com/settings/keys>.
3. Download this repo (green **Code** button → **Download ZIP**, then unzip it), or `git clone` it.
4. Double-click **`run.bat`**.
   - The first time, it installs everything and opens a file called `.env` in Notepad.
   - Paste your key after `ANTHROPIC_API_KEY=`, put your name after `JARVIS_USER_NAME=`, and save.
   - Double-click `run.bat` again. Jarvis starts.

Use **Windows Terminal** (built into Windows 11) for the best display, especially for Arabic.

### Manual setup (any OS)

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # macOS / Linux
pip install -r requirements.txt
copy .env.example .env          # Windows  (macOS/Linux: cp .env.example .env)
# edit .env and add your API key
python -m jarvis
```

## Using it

Just type. Commands:

| Command      | What it does                                         |
|--------------|------------------------------------------------------|
| `/new`       | start a fresh conversation (memories are kept)       |
| `/memory`    | show what Jarvis remembers about you                 |
| `/reminders` | show pending reminders                               |
| `/help`      | list commands                                        |
| `/quit`      | exit (or Ctrl+C)                                     |

Settings live in `.env` (see `.env.example`): your name, language (`auto`, `en`, `ar`),
how hard Jarvis thinks (`JARVIS_EFFORT`, `low` is fastest and cheapest), and whether web search is on.

Memories and reminders are saved in `%APPDATA%\Jarvis` on Windows
(`~/Library/Application Support/Jarvis` on macOS).

## How it's built

```
jarvis/
  brain.py    talks to Claude, runs tools, streams the reply (no UI code, reused by every front end)
  tools.py    what Jarvis can do on your computer; add new abilities here
  storage.py  memory and reminders as JSON files
  config.py   settings from .env
  cli.py      the terminal chat window
tests/        tests that run without an API key (pytest)
```

It uses the Claude API (`claude-opus-5-5`) with streaming, tool use, Anthropic's web search tool,
and prompt caching. To add an ability, write a method in `tools.py` and register it in `_build_tools()`.

## Roadmap

- [x] **v0.1** Chat in the terminal on Windows, English and Arabic, memory, reminders, web search
- [ ] **v0.2** Voice in English: wake word "Jarvis", speech-to-text, spoken replies
- [ ] **v0.3** Voice in Arabic (Egyptian dialect)
- [ ] **v0.4** Desktop window app with chat history
- [ ] **v0.5** macOS support for app-launching and notifications
- [ ] **v1.0** iPhone app talking to a small Jarvis server

## Running the tests

```bash
pip install pytest
python -m pytest
```

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_gitignore_blocks_secrets():
    lines = (ROOT / ".gitignore").read_text().splitlines()
    for needed in [".env", "*.db", ".jarvis/", "client_secret*.json"]:
        assert needed in lines

from datetime import datetime

import keyring
import pytest
from keyring.backend import KeyringBackend
from keyring.errors import PasswordDeleteError

NOW = datetime(2026, 11, 16, 9, 30)


class MemoryKeyring(KeyringBackend):
    priority = 1

    def __init__(self):
        super().__init__()
        self.data = {}

    def get_password(self, service, username):
        return self.data.get((service, username))

    def set_password(self, service, username, password):
        self.data[(service, username)] = password

    def delete_password(self, service, username):
        if (service, username) not in self.data:
            raise PasswordDeleteError("not found")
        del self.data[(service, username)]


@pytest.fixture
def memory_keyring():
    previous = keyring.get_keyring()
    backend = MemoryKeyring()
    keyring.set_keyring(backend)
    yield backend
    keyring.set_keyring(previous)


@pytest.fixture
def tmp_home(tmp_path, monkeypatch):
    monkeypatch.delenv("JARVIS_HOME", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    return tmp_path


def replies(*answers, record=None):
    """An async `ask` that returns the given answers in order."""
    queue = list(answers)

    async def ask(question: str) -> str:
        if record is not None:
            record.append(question)
        return queue.pop(0)

    return ask


@pytest.fixture
def store(tmp_path):
    from jarvis.memory.store import Store
    return Store(tmp_path / "j.db")

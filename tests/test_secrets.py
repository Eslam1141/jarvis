import keyring

from jarvis.secrets import delete_secret, get_secret, set_secret


def test_roundtrip(memory_keyring):
    set_secret("k", "v")
    assert get_secret("k") == "v"


def test_missing_is_none(memory_keyring):
    assert get_secret("nope") is None


def test_delete(memory_keyring):
    set_secret("k", "v")
    delete_secret("k")
    assert get_secret("k") is None


def test_delete_missing_is_silent(memory_keyring):
    delete_secret("nope")


def test_stored_under_service_name(memory_keyring):
    set_secret("k", "v")
    assert keyring.get_password("jarvis", "k") == "v"

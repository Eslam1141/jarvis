from datetime import datetime

from jarvis.memory.profile import Profile


def test_read_missing_is_empty(tmp_path):
    assert Profile(tmp_path / "profile.md").read() == ""


def test_add_fact_appends_dated_line(tmp_path):
    p = Profile(tmp_path / "profile.md")
    p.add_fact("Lives in Cairo", datetime(2026, 11, 15, 9, 0))
    p.add_fact("Prefers short answers", datetime(2026, 11, 16, 9, 0))
    assert p.read().splitlines()[-1] == "- 2026-11-16 Prefers short answers"
    assert len(p.read().splitlines()) == 2

from datetime import datetime

import pytest

from jarvis.memory.lessons import Lessons

NOW = datetime(2026, 11, 16, 9, 30)


def test_add_assigns_increasing_ids(tmp_path):
    ls = Lessons(tmp_path / "lessons.md")
    a = ls.add("No meetings before 10", "owner_said", NOW)
    b = ls.add("Sign off with 'Regards'", "owner_edit", NOW)
    assert (a.id, b.id) == (1, 2)
    assert [l.text for l in ls.list()] == ["No meetings before 10", "Sign off with 'Regards'"]


def test_line_format(tmp_path):
    ls = Lessons(tmp_path / "lessons.md")
    ls.add("No meetings before 10", "owner_said", datetime(2026, 11, 16, 9, 0))
    assert "- [L1] 2026-11-16 (owner_said) No meetings before 10" in (
        tmp_path / "lessons.md").read_text()


def test_rejects_any_other_source(tmp_path):
    with pytest.raises(ValueError):
        Lessons(tmp_path / "lessons.md").add("x", "email", NOW)


def test_forget_removes_only_that_lesson(tmp_path):
    ls = Lessons(tmp_path / "lessons.md")
    ls.add("a", "owner_said", NOW)
    ls.add("b", "owner_said", NOW)
    assert ls.forget(1) is True and [l.text for l in ls.list()] == ["b"]
    assert ls.forget(99) is False


def test_ids_are_not_reused_after_forget(tmp_path):
    ls = Lessons(tmp_path / "lessons.md")
    ls.add("a", "owner_said", NOW)
    ls.add("b", "owner_said", NOW)
    ls.forget(2)
    assert ls.add("c", "owner_said", NOW).id == 3


def test_malformed_line_is_skipped_and_preserved(tmp_path):
    f = tmp_path / "lessons.md"
    f.write_text("- [L1] 2026-11-16 (owner_said) keep\nmy own note, not a lesson\n")
    ls = Lessons(f)
    assert [l.text for l in ls.list()] == ["keep"]
    ls.add("new", "owner_said", NOW)
    assert "my own note, not a lesson" in f.read_text()
    assert [l.id for l in ls.list()] == [1, 2]


def test_lesson_text_is_kept_on_one_line(tmp_path):
    ls = Lessons(tmp_path / "lessons.md")
    ls.add("first line\nsecond line", "owner_said", NOW)
    assert [l.text for l in ls.list()] == ["first line second line"]


def test_blank_lesson_is_rejected(tmp_path):
    with pytest.raises(ValueError):
        Lessons(tmp_path / "lessons.md").add("   ", "owner_said", NOW)

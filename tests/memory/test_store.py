from datetime import datetime, timedelta

from jarvis.memory.store import Store

T0 = datetime(2026, 11, 16, 9, 0)


def test_recent_turns_are_oldest_first_and_limited(tmp_path):
    s = Store(tmp_path / "j.db")
    for i in range(5):
        s.add_turn("owner", f"m{i}", T0 + timedelta(seconds=i))
    assert [t.text for t in s.recent_turns(3)] == ["m2", "m3", "m4"]


def test_turns_survive_reopen(tmp_path):
    Store(tmp_path / "j.db").add_turn("jarvis", "hello", T0)
    turn = Store(tmp_path / "j.db").recent_turns(10)[0]
    assert (turn.role, turn.text, turn.at) == ("jarvis", "hello", T0)


def test_actions_newest_first(tmp_path):
    s = Store(tmp_path / "j.db")
    s.log_action("lesson.add", "a", "{}", T0)
    s.log_action("lesson.forget", "b", "{}", T0 + timedelta(seconds=1))
    assert [a.summary for a in s.actions(10)] == ["b", "a"]


def test_two_stores_on_one_file_can_both_write(tmp_path):
    a, b = Store(tmp_path / "j.db"), Store(tmp_path / "j.db")
    a.add_turn("owner", "x", T0)
    b.add_turn("owner", "y", T0)
    assert len(a.recent_turns(10)) == 2

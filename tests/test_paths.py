from jarvis.paths import data_dir


def test_data_dir_uses_env(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path / "j"))
    d = data_dir()
    assert d == tmp_path / "j" and d.is_dir()
    assert (d.stat().st_mode & 0o777) == 0o700


def test_data_dir_default(monkeypatch, tmp_path):
    monkeypatch.delenv("JARVIS_HOME", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    assert data_dir() == tmp_path / ".jarvis"

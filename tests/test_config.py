import pytest

from jarvis.config import load_config


def test_defaults_when_file_missing(tmp_path):
    c = load_config(tmp_path / "config.toml")
    assert (c.owner_name, c.fast_model, c.deep_model, c.history_turns) == (
        "Sir", "claude-sonnet-5-5", "claude-opus-5-5", 20)


def test_file_overrides_defaults(tmp_path):
    p = tmp_path / "config.toml"
    p.write_text('owner_name = "Eslam"\n')
    c = load_config(p)
    assert c.owner_name == "Eslam" and c.fast_model == "claude-sonnet-5-5"


def test_unknown_key_is_an_error(tmp_path):
    p = tmp_path / "config.toml"
    p.write_text('ownr_name = "x"\n')
    with pytest.raises(ValueError, match="ownr_name"):
        load_config(p)

import pytest
from pathlib import Path
from drytrix_timetracker_mcp import config

BASE = {"TT_BASE_URL": "https://time.example.com", "TIMETRACKER_API_KEY": "tt_abc"}

def test_defaults():
    s = config.load_settings(environ=BASE, dotenv_values={})
    assert s.timeout == 30.0 and s.verify_ssl is True
    assert s.enable_write is False and s.per_page == 100

def test_alias_token():
    env = {"TT_BASE_URL": "https://x", "TT_API_TOKEN": "tt_alias"}
    assert config.load_settings(environ=env, dotenv_values={}).api_token == "tt_alias"

def test_missing_base_url_raises():
    with pytest.raises(config.ConfigError):
        config.load_settings(environ={"TIMETRACKER_API_KEY": "tt_abc"}, dotenv_values={})

def test_missing_token_raises():
    with pytest.raises(config.ConfigError):
        config.load_settings(environ={"TT_BASE_URL": "https://x"}, dotenv_values={})

def test_env_overrides_dotenv():
    s = config.load_settings(
        environ={"TT_BASE_URL": "https://env", "TIMETRACKER_API_KEY": "tt_env"},
        dotenv_values={"TT_BASE_URL": "https://dot"},
    )
    assert s.base_url == "https://env"

def test_dotenv_used_when_env_absent():
    s = config.load_settings(environ={}, dotenv_values=BASE)
    assert s.base_url == "https://time.example.com"

@pytest.mark.parametrize("raw,expected", [("1", True), ("true", True), ("YES", True), ("false", False), ("0", False)])
def test_enable_write_truthy(raw, expected):
    env = dict(BASE, TT_ENABLE_WRITE=raw)
    assert config.load_settings(environ=env, dotenv_values={}).enable_write is expected

def test_read_dotenv(tmp_path: Path):
    f = tmp_path / ".env"
    f.write_text('# comment\nA=1\nB="quoted"\n\nC=x=y\n')
    assert config.read_dotenv(f) == {"A": "1", "B": "quoted", "C": "x=y"}

def test_read_dotenv_missing_file(tmp_path: Path):
    assert config.read_dotenv(tmp_path / "nope") == {}

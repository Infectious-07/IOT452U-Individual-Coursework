from pathlib import Path

from digital_id.config.settings import DEFAULT_DB_PATH, load


def test_load_returns_defaults_when_file_missing(tmp_path: Path) -> None:
    settings = load(tmp_path / "missing.toml")
    assert settings.database_path == DEFAULT_DB_PATH


def test_load_reads_overrides(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text('[database]\npath = "custom/path.sqlite"\n')
    settings = load(config_path)
    assert settings.database_path == "custom/path.sqlite"


def test_load_uses_defaults_for_missing_keys(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text("")
    settings = load(config_path)
    assert settings.database_path == DEFAULT_DB_PATH

from pathlib import Path

from digital_id.config.settings import (
    DEFAULT_DB_PATH,
    DEFAULT_RETENTION_DAYS,
    load,
)


def test_load_returns_defaults_when_file_missing(tmp_path: Path) -> None:
    settings = load(tmp_path / "missing.toml")
    assert settings.database_path == DEFAULT_DB_PATH
    assert settings.audit_retention_days == DEFAULT_RETENTION_DAYS


def test_load_reads_overrides(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        "[database]\n"
        'path = "custom/path.sqlite"\n'
        "\n"
        "[audit]\n"
        "retention_days = 90\n"
    )
    settings = load(config_path)
    assert settings.database_path == "custom/path.sqlite"
    assert settings.audit_retention_days == 90


def test_load_handles_partial_file(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text('[database]\npath = "only/db.sqlite"\n')
    settings = load(config_path)
    assert settings.database_path == "only/db.sqlite"
    assert settings.audit_retention_days == DEFAULT_RETENTION_DAYS

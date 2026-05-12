from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

DEFAULT_DB_PATH = "data/digital_id.sqlite"
DEFAULT_RETENTION_DAYS = 365


@dataclass(frozen=True)
class Settings:
    database_path: str = DEFAULT_DB_PATH
    audit_retention_days: int = DEFAULT_RETENTION_DAYS


def load(config_path: str | Path = "config.toml") -> Settings:
    path = Path(config_path)
    if not path.exists():
        return Settings()
    with path.open("rb") as handle:
        raw = tomllib.load(handle)
    database = raw.get("database", {}) or {}
    audit = raw.get("audit", {}) or {}
    return Settings(
        database_path=str(database.get("path", DEFAULT_DB_PATH)),
        audit_retention_days=int(audit.get("retention_days", DEFAULT_RETENTION_DAYS)),
    )

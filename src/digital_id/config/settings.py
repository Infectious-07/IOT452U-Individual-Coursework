from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

DEFAULT_DB_PATH = "data/digital_id.sqlite"


@dataclass(frozen=True)
class Settings:
    database_path: str = DEFAULT_DB_PATH


def load(config_path: str | Path = "config.toml") -> Settings:
    path = Path(config_path)
    if not path.exists():
        return Settings()
    with path.open("rb") as handle:
        raw = tomllib.load(handle)
    database = raw.get("database", {}) or {}
    return Settings(database_path=str(database.get("path", DEFAULT_DB_PATH)))

"""Caricamento della configurazione (config/settings.yaml) e dei segreti.

I token vengono letti, in ordine, da: variabili d'ambiente / file `.env`,
poi dal vecchio file `psw/token.yml` (compatibilità con la prima versione del progetto).
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date
from functools import lru_cache
from pathlib import Path

import yaml

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - python-dotenv è opzionale
    load_dotenv = None

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"

# variabile d'ambiente -> chiave nel vecchio psw/token.yml
_SECRETS = {
    "FOOTBALL_DATA_TOKEN": "TOKEN FOOTBALL DATA",
    "API_FOOTBALL_KEY": "TOKEN API FOOTBALL",
}


@dataclass(frozen=True)
class Settings:
    seasons: list[int]
    raw_dir: Path
    clean_dir: Path
    reports_dir: Path
    database_url: str
    sources: dict
    match_source_priority: list[str]
    odds_source_priority: list[str]
    quality: dict
    team_aliases: dict[str, list[str]] = field(default_factory=dict)

    def source_enabled(self, name: str) -> bool:
        return bool(self.sources.get(name, {}).get("enabled", False))

    def source_option(self, name: str, key: str, default=None):
        return self.sources.get(name, {}).get(key, default)


def last_completed_seasons(n: int, today: date | None = None) -> list[int]:
    """Ultime n stagioni concluse: a ottobre 2026 -> [2022, 2023, 2024, 2025]."""
    today = today or date.today()
    last = today.year - 1 if today.month >= 7 else today.year - 2
    return list(range(last - n + 1, last + 1))


def _resolve(path: str) -> Path:
    p = Path(path)
    return p if p.is_absolute() else PROJECT_ROOT / p


def _database_url(configured: str) -> str:
    url = os.environ.get("DATABASE_URL", configured)
    prefix = "sqlite:///"
    if url.startswith(prefix) and not url.startswith(prefix + "/"):
        # percorso SQLite relativo -> relativo alla root del progetto
        url = prefix + str(_resolve(url[len(prefix):]))
    return url


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    if load_dotenv is not None:
        load_dotenv(PROJECT_ROOT / ".env")
    with open(CONFIG_DIR / "settings.yaml", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    with open(CONFIG_DIR / "team_aliases.yaml", encoding="utf-8") as f:
        aliases = yaml.safe_load(f) or {}

    seasons_env = os.environ.get("PIPELINE_SEASONS")
    if seasons_env:
        seasons = [int(s) for s in seasons_env.split(",")]
    elif cfg["seasons"] == "auto":
        seasons = last_completed_seasons(int(cfg.get("n_seasons", 4)))
    else:
        seasons = cfg["seasons"]

    return Settings(
        seasons=sorted(seasons),
        raw_dir=_resolve(cfg["paths"]["raw"]),
        clean_dir=_resolve(cfg["paths"]["clean"]),
        reports_dir=_resolve(cfg["paths"]["reports"]),
        database_url=_database_url(cfg["database"]["url"]),
        sources=cfg.get("sources", {}),
        match_source_priority=cfg.get("match_source_priority", []),
        odds_source_priority=cfg.get("odds_source_priority", []),
        quality=cfg.get("quality", {}),
        team_aliases=aliases,
    )


def get_secret(name: str) -> str | None:
    """Restituisce un token dalle variabili d'ambiente o da psw/token.yml."""
    get_settings()  # assicura che .env sia stato caricato
    value = os.environ.get(name)
    if value:
        return value
    legacy = PROJECT_ROOT / "psw" / "token.yml"
    if legacy.exists() and name in _SECRETS:
        with open(legacy, encoding="utf-8") as f:
            return (yaml.safe_load(f) or {}).get(_SECRETS[name])
    return None

"""Infrastruttura comune delle fonti dati.

Ogni fonte salva i dati grezzi in `data/raw/<fonte>/<dataset>_<stagione>.csv`,
senza trasformazioni: il cleaning è responsabilità dello step successivo.
Se il file esiste già viene riusato (cache) a meno di `refresh=True`.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd

from football_pipeline.config import get_settings
from football_pipeline.utils.http import ConnectionFailed
from football_pipeline.utils.logging import get_logger

log = get_logger(__name__)


class SourceUnavailable(RuntimeError):
    """La fonte non può essere interrogata (token mancante, dipendenza assente, ...)."""


@dataclass
class AcquisitionResult:
    source: str
    dataset: str
    season: int
    status: str  # downloaded | cached | skipped | failed
    rows: int = 0
    message: str = ""


def raw_path(source: str, dataset: str, season: int) -> Path:
    return get_settings().raw_dir / source / f"{dataset}_{season}.csv"


def read_raw(source: str, dataset: str, seasons: list[int] | None = None) -> pd.DataFrame:
    """Concatena i file raw disponibili di un dataset (tutto come stringa)."""
    seasons = seasons or get_settings().seasons
    frames = []
    for season in seasons:
        path = raw_path(source, dataset, season)
        if path.exists():
            df = pd.read_csv(path, dtype=str, keep_default_na=False, na_values=[""])
            if "season" not in df.columns:
                df["season"] = str(season)
            frames.append(df)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def current_season(today: date | None = None) -> int:
    today = today or date.today()
    return today.year if today.month >= 7 else today.year - 1


class Source:
    name: str = ""
    kind: str = ""          # api | scraping
    description: str = ""
    datasets: tuple[str, ...] = ()

    def fetch(self, dataset: str, season: int) -> pd.DataFrame:
        raise NotImplementedError

    def available_seasons(self, dataset: str, seasons: list[int]) -> list[int]:
        """Override per limitare le stagioni interrogabili (es. limiti del piano free)."""
        return seasons

    def run(self, seasons: list[int], refresh: bool = False) -> list[AcquisitionResult]:
        results = []
        for dataset in self.datasets:
            for season in seasons:
                path = raw_path(self.name, dataset, season)
                if path.exists() and not refresh:
                    results.append(AcquisitionResult(self.name, dataset, season, "cached"))
                    continue
                if season not in self.available_seasons(dataset, seasons):
                    results.append(AcquisitionResult(self.name, dataset, season, "skipped",
                                                     message="stagione non disponibile"))
                    continue
                try:
                    df = self.fetch(dataset, season)
                except (SourceUnavailable, ConnectionFailed) as exc:
                    log.warning("[%s] fonte non disponibile: %s", self.name, exc)
                    results.append(AcquisitionResult(self.name, dataset, season, "skipped", message=str(exc)))
                    # inutile ritentare le altre stagioni/dataset
                    return results
                except Exception as exc:  # noqa: BLE001 - una fonte non deve fermare la pipeline
                    log.error("[%s] %s %s fallito: %s", self.name, dataset, season, exc)
                    results.append(AcquisitionResult(self.name, dataset, season, "failed", message=str(exc)))
                    continue
                if df is None or df.empty:
                    results.append(AcquisitionResult(self.name, dataset, season, "failed", message="nessun dato"))
                    continue
                path.parent.mkdir(parents=True, exist_ok=True)
                df.to_csv(path, index=False)
                log.info("[%s] %s %s: %d righe -> %s", self.name, dataset, season, len(df), path.name)
                results.append(AcquisitionResult(self.name, dataset, season, "downloaded", rows=len(df)))
        return results

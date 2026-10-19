"""Step 1 - Data acquisition da API e web scraping."""
from __future__ import annotations

from football_pipeline.acquisition.api_football import ApiFootball
from football_pipeline.acquisition.base import AcquisitionResult, Source
from football_pipeline.acquisition.clubelo import ClubElo
from football_pipeline.acquisition.football_data_couk import FootballDataCoUk
from football_pipeline.acquisition.football_data_org import FootballDataOrg
from football_pipeline.acquisition.oddsportal import OddsPortal
from football_pipeline.acquisition.transfermarkt import Transfermarkt
from football_pipeline.acquisition.understat import Understat
from football_pipeline.config import get_settings
from football_pipeline.utils.logging import get_logger

log = get_logger(__name__)

SOURCES: dict[str, type[Source]] = {
    cls.name: cls
    for cls in (FootballDataOrg, ApiFootball, ClubElo, Transfermarkt,
                OddsPortal, FootballDataCoUk, Understat)
}


def run_acquisition(refresh: bool = False, only: list[str] | None = None) -> list[AcquisitionResult]:
    settings = get_settings()
    results: list[AcquisitionResult] = []
    for name, cls in SOURCES.items():
        if only and name not in only:
            continue
        if not only and not settings.source_enabled(name):
            log.info("[%s] disabilitata in config/settings.yaml", name)
            continue
        log.info("[%s] acquisizione (%s)", name, cls.kind)
        results.extend(cls().run(settings.seasons, refresh=refresh))
    return results

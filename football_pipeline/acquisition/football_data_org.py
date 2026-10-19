"""API football-data.org (v4) - risultati Serie A. Token gratuito richiesto."""
from __future__ import annotations

import pandas as pd

from football_pipeline.acquisition.base import Source, SourceUnavailable
from football_pipeline.config import get_secret
from football_pipeline.utils.http import HttpClient

URL = "https://api.football-data.org/v4/competitions/SA/matches"


def parse_matches(payload: dict, season: int) -> pd.DataFrame:
    rows = []
    for match in payload.get("matches", []):
        score = match.get("score", {})
        rows.append({
            "match_id": match["id"],
            "matchweek": match.get("matchday"),
            "season": season,
            "date": match["utcDate"].split("T")[0],
            "status": match.get("status"),
            "stage": match.get("stage"),
            "home_team": match["homeTeam"]["name"],
            "away_team": match["awayTeam"]["name"],
            "winner": score.get("winner"),
            "half_time_home_score": (score.get("halfTime") or {}).get("home"),
            "half_time_away_score": (score.get("halfTime") or {}).get("away"),
            "home_score": (score.get("fullTime") or {}).get("home"),
            "away_score": (score.get("fullTime") or {}).get("away"),
        })
    return pd.DataFrame(rows)


class FootballDataOrg(Source):
    name = "football_data_org"
    kind = "api"
    description = "football-data.org REST API v4 (risultati, primo/secondo tempo)"
    datasets = ("matches",)

    def fetch(self, dataset: str, season: int) -> pd.DataFrame:
        token = get_secret("FOOTBALL_DATA_TOKEN")
        if not token:
            raise SourceUnavailable("FOOTBALL_DATA_TOKEN non impostato")
        # piano free: 10 richieste/minuto
        client = HttpClient(headers={"X-Auth-Token": token}, delay=6.5)
        payload = client.get(URL, params={"season": season}).json()
        return parse_matches(payload, season)

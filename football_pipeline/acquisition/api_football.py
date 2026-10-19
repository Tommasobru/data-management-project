"""API-Football (api-sports.io v3) - risultati Serie A (league id 135). Chiave gratuita."""
from __future__ import annotations

import pandas as pd

from football_pipeline.acquisition.base import Source, SourceUnavailable
from football_pipeline.config import get_secret
from football_pipeline.utils.http import HttpClient

URL = "https://v3.football.api-sports.io/fixtures"
SERIE_A_ID = 135


def parse_fixtures(payload: dict, season: int) -> pd.DataFrame:
    errors = payload.get("errors")
    if errors:
        if isinstance(errors, dict) and ("token" in errors or "requests" in errors):
            # chiave non valida o quota giornaliera esaurita: inutile provare altre stagioni
            raise SourceUnavailable(f"API-Football: {errors}")
        raise RuntimeError(f"errore API-Football: {errors}")
    rows = []
    for match in payload.get("response", []):
        teams, score = match["teams"], match["score"]
        rows.append({
            "season": season,
            "date": match["fixture"]["date"].split("T")[0],
            "status": match["fixture"]["status"]["short"],
            "matchweek": match["league"]["round"],
            "home_team": teams["home"]["name"],
            "home_winner": teams["home"]["winner"],
            "away_team": teams["away"]["name"],
            "away_winner": teams["away"]["winner"],
            "home_goals": match["goals"]["home"],
            "away_goals": match["goals"]["away"],
            "home_goals_halftime": score["halftime"]["home"],
            "away_goals_halftime": score["halftime"]["away"],
        })
    return pd.DataFrame(rows)


class ApiFootball(Source):
    name = "api_football"
    kind = "api"
    description = "API-Football v3 (risultati, primo tempo)"
    datasets = ("fixtures",)

    def fetch(self, dataset: str, season: int) -> pd.DataFrame:
        key = get_secret("API_FOOTBALL_KEY")
        if not key:
            raise SourceUnavailable("API_FOOTBALL_KEY non impostata")
        client = HttpClient(headers={"x-apisports-key": key, "x-rapidapi-key": key}, delay=6.5)
        payload = client.get(URL, params={"league": SERIE_A_ID, "season": season}).json()
        return parse_fixtures(payload, season)

"""Understat - expected goals (xG) per partita. Scraping gratuito.

Understat espone i dati del campionato tramite l'endpoint usato dalla propria pagina
(`/getLeagueData/<lega>/<stagione>`); come ripiego si estrae il JSON incorporato
nell'HTML (`datesData = JSON.parse('...')`, formato storico del sito).
"""
from __future__ import annotations

import codecs
import json
import re

import pandas as pd

from football_pipeline.acquisition.base import Source
from football_pipeline.utils.http import BROWSER_HEADERS, FetchError, HttpClient

LEAGUE = "Serie_A"
DATA_URL = "https://understat.com/getLeagueData/{league}/{season}"
PAGE_URL = "https://understat.com/league/{league}/{season}"


def extract_embedded_json(html: str, variable: str) -> list | dict:
    match = re.search(rf"var\s+{variable}\s*=\s*JSON\.parse\('(.*?)'\)", html, re.S)
    if not match:
        raise ValueError(f"variabile {variable} non trovata nella pagina")
    return json.loads(codecs.decode(match.group(1), "unicode_escape"))


def parse_dates(dates: list[dict], season: int) -> pd.DataFrame:
    rows = []
    for m in dates:
        if not m.get("isResult"):
            continue
        forecast = m.get("forecast") or {}
        rows.append({
            "season": season,
            "understat_id": m["id"],
            "datetime": m["datetime"],
            "home_team": m["h"]["title"],
            "away_team": m["a"]["title"],
            "home_goals": m["goals"]["h"],
            "away_goals": m["goals"]["a"],
            "home_xg": m["xG"]["h"],
            "away_xg": m["xG"]["a"],
            "forecast_home": forecast.get("w"),
            "forecast_draw": forecast.get("d"),
            "forecast_away": forecast.get("l"),
        })
    return pd.DataFrame(rows)


class Understat(Source):
    name = "understat"
    kind = "scraping"
    description = "Understat (expected goals per partita)"
    datasets = ("matches",)

    def fetch(self, dataset: str, season: int) -> pd.DataFrame:
        client = HttpClient(headers=BROWSER_HEADERS, delay=2.0, max_attempts=3)
        try:
            response = client.get(
                DATA_URL.format(league=LEAGUE, season=season),
                headers={"X-Requested-With": "XMLHttpRequest",
                         "Referer": PAGE_URL.format(league=LEAGUE, season=season)},
            )
            dates = response.json()["dates"]
        except (FetchError, ValueError, KeyError):
            html = client.get(PAGE_URL.format(league=LEAGUE, season=season)).text
            dates = extract_embedded_json(html, "datesData")
        return parse_dates(dates, season)

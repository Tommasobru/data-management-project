"""ClubElo API - rating Elo delle squadre. Pubblica, gratuita, senza chiave.

Per ogni stagione si scaricano due istantanee della classifica Elo mondiale:
inizio stagione (1 agosto) e fine stagione (1 giugno successivo).
"""
from __future__ import annotations

import io

import pandas as pd

from football_pipeline.acquisition.base import Source
from football_pipeline.utils.http import HttpClient

URL = "http://api.clubelo.com/{date}"


def snapshot_dates(season: int) -> dict[str, str]:
    return {"start": f"{season}-08-01", "end": f"{season + 1}-06-01"}


def parse_snapshot(csv_text: str, season: int, snapshot: str, snapshot_date: str) -> pd.DataFrame:
    df = pd.read_csv(io.StringIO(csv_text))
    df = df[df["Country"] == "ITA"].copy()
    df["season"] = season
    df["snapshot"] = snapshot
    df["snapshot_date"] = snapshot_date
    return df


class ClubElo(Source):
    name = "clubelo"
    kind = "api"
    description = "ClubElo API (rating Elo a inizio e fine stagione)"
    datasets = ("elo",)

    def fetch(self, dataset: str, season: int) -> pd.DataFrame:
        client = HttpClient(delay=1.0)
        frames = [
            parse_snapshot(client.get(URL.format(date=d)).text, season, snap, d)
            for snap, d in snapshot_dates(season).items()
        ]
        return pd.concat(frames, ignore_index=True)

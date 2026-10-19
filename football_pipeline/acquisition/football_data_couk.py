"""football-data.co.uk - CSV open data con statistiche partita (tiri, falli, corner,
cartellini, arbitro) e quote 1X2 di più bookmaker. Gratuito, senza chiave."""
from __future__ import annotations

import io

import pandas as pd

from football_pipeline.acquisition.base import Source
from football_pipeline.utils.http import BROWSER_HEADERS, HttpClient

URL = "https://www.football-data.co.uk/mmz4281/{code}/I1.csv"


def season_code(season: int) -> str:
    return f"{season % 100:02d}{(season + 1) % 100:02d}"


def parse_csv(content: bytes, season: int) -> pd.DataFrame:
    for encoding in ("utf-8-sig", "latin-1"):
        try:
            text = content.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    df = pd.read_csv(io.StringIO(text), dtype=str)
    df = df.dropna(how="all")
    df = df.loc[:, ~df.columns.str.startswith("Unnamed")]
    df["season"] = season
    return df


class FootballDataCoUk(Source):
    name = "football_data_couk"
    kind = "scraping"
    description = "football-data.co.uk (statistiche partita e quote di mercato)"
    datasets = ("matches",)

    def fetch(self, dataset: str, season: int) -> pd.DataFrame:
        client = HttpClient(headers=BROWSER_HEADERS, delay=1.0)
        return parse_csv(client.get(URL.format(code=season_code(season))).content, season)

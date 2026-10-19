"""Transfermarkt - web scraping di rose, valori di mercato e marcatori.

Dataset prodotti (formato identico alla prima versione del progetto):
- teams:   squadra, link, dimensione rosa, età media, stranieri, valore rosa
- players: nome, ruolo, età, valore di mercato, squadra
- goals:   marcatore, minuto, risultato dopo il gol, per ogni giornata
"""
from __future__ import annotations

import pandas as pd
from bs4 import BeautifulSoup

from football_pipeline.acquisition.base import Source, raw_path
from football_pipeline.config import get_settings
from football_pipeline.utils.http import BROWSER_HEADERS, HttpClient
from football_pipeline.utils.logging import get_logger

log = get_logger(__name__)

BASE = "https://www.transfermarkt.it"
TEAMS_URL = BASE + "/serie-a/startseite/wettbewerb/IT1/plus/?saison_id={season}"
MATCHDAY_URL = BASE + "/serie-a/spieltag/wettbewerb/IT1/plus/?saison_id={season}&spieltag={matchday}"
MATCHDAYS = 38


def parse_teams(html: str, season: int) -> pd.DataFrame:
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", class_="items")
    if table is None:
        raise ValueError("tabella squadre non trovata")
    teams = []
    for row in table.find("tbody").find_all("tr"):
        team_cell = row.find("td", class_="hauptlink no-border-links")
        if team_cell is None or team_cell.a is None:
            continue
        centered = row.find_all("td", class_="zentriert")
        right = row.find_all("td", class_="rechts")
        teams.append({
            "team": team_cell.a.text.strip(),
            "link": BASE + team_cell.a["href"],
            "team_size": centered[1].text.strip(),
            "avg_age": centered[2].text.strip(),
            "n_foreigners": centered[3].text.strip(),
            "team_value": right[1].text.strip(),
            "season": season,
        })
    return pd.DataFrame(teams)


def parse_squad(html: str, team: str, season: int) -> pd.DataFrame:
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", class_="items")
    if table is None:
        return pd.DataFrame()
    players = []
    for row in table.find("tbody").find_all("tr", class_=["odd", "even"]):
        name_cell = row.find("td", class_="hauptlink")
        role_cell = row.find("td", class_="posrela")
        centered = row.find_all("td", class_="zentriert")
        value_cell = row.find("td", class_="rechts hauptlink")
        players.append({
            "name": name_cell.text.strip() if name_cell else None,
            # contiene anche il nome del giocatore: viene ripulito nel cleaning
            "role": role_cell.text.strip() if role_cell else None,
            "age": centered[1].text.strip() if len(centered) > 1 else None,
            "market_value": value_cell.text.strip() if value_cell else None,
            "team": team,
            "season": season,
        })
    return pd.DataFrame(players)


def _team_name(cell) -> str | None:
    if cell is None:
        return None
    for a in cell.find_all("a", href=True):
        if a.get("title") != "Discutere della giornata" and a.text.strip():
            return a.text.strip()
    return None


def parse_matchday(html: str, season: int, matchday: int) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    section = soup.find("div", class_="large-8 columns")
    if section is None:
        return []
    goals = []
    for box in section.find_all("div", class_="box"):
        if not box.find("span", class_="matchresult"):
            continue
        home = _team_name(box.find("td", class_="rechts hauptlink no-border-rechts hide-for-small spieltagsansicht-vereinsname"))
        away = _team_name(box.find("td", class_="hauptlink no-border-links no-border-rechts hide-for-small spieltagsansicht-vereinsname"))
        for tr in box.find_all("tr", class_="spieltagsansicht-aktionen"):
            player_span = tr.find("span", class_="hide-for-small")
            icon = tr.find("span", class_="icon-tor-formation") or tr.find("span", class_="icon-elfmeter-formation")
            if not (player_span and player_span.find("a") and icon and "title" in icon.attrs):
                continue  # non è un gol (es. cartellino, sostituzione)
            result_td = tr.find("td", class_="zentriert hauptlink")
            goals.append({
                "season": season,
                "matchweek": matchday,
                "home_team": home,
                "away_team": away,
                "goal_result": result_td.get_text(strip=True) if result_td else None,
                "scorer": player_span.find("a").text.strip(),
                "minute": icon["title"].split(".")[0],
            })
    return goals


class Transfermarkt(Source):
    name = "transfermarkt"
    kind = "scraping"
    description = "Transfermarkt (rose, valori di mercato, marcatori)"
    datasets = ("teams", "players", "goals")

    def __init__(self):
        delay = get_settings().source_option(self.name, "request_delay_seconds", 2.0)
        self.client = HttpClient(headers=BROWSER_HEADERS, delay=delay)

    def _teams(self, season: int) -> pd.DataFrame:
        path = raw_path(self.name, "teams", season)
        if path.exists():
            return pd.read_csv(path)
        return parse_teams(self.client.get(TEAMS_URL.format(season=season)).text, season)

    def fetch(self, dataset: str, season: int) -> pd.DataFrame:
        if dataset == "teams":
            return parse_teams(self.client.get(TEAMS_URL.format(season=season)).text, season)
        if dataset == "players":
            frames = []
            for _, team in self._teams(season).iterrows():
                log.info("[transfermarkt] rosa %s %s", team["team"], season)
                frames.append(parse_squad(self.client.get(team["link"]).text, team["team"], season))
            return pd.concat(frames, ignore_index=True)
        if dataset == "goals":
            goals = []
            for matchday in range(1, MATCHDAYS + 1):
                html = self.client.get(MATCHDAY_URL.format(season=season, matchday=matchday)).text
                goals.extend(parse_matchday(html, season, matchday))
            return pd.DataFrame(goals)
        raise ValueError(dataset)

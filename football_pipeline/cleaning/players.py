"""Associazione dei marcatori (pagine giornata) alle anagrafiche giocatori (pagine rosa)."""
from __future__ import annotations

import pandas as pd
from rapidfuzz import fuzz, process

from football_pipeline.utils.text import normalize_name


def match_scorers(goals: pd.DataFrame, players: pd.DataFrame, threshold: int = 85) -> pd.Series:
    """Restituisce il player_id per ogni gol (NaN se non trovato).

    goals: season_id, scoring_team_id, conceding_team_id, scorer_name
    players: season_id, team_id, player_id, player_name
    Ordine di ricerca: nome esatto nella squadra che segna, nella squadra che subisce
    (autogol), in tutta la stagione; poi fuzzy nella squadra e nella stagione.
    """
    players = players.assign(norm=players["player_name"].map(normalize_name))
    by_team = {k: dict(zip(g["norm"], g["player_id"])) for k, g in players.groupby(["season_id", "team_id"])}
    by_season = {k: dict(zip(g["norm"], g["player_id"])) for k, g in players.groupby("season_id")}

    def lookup(row) -> float:
        norm = normalize_name(row["scorer_name"])
        season = row["season_id"]
        candidates = [
            by_team.get((season, row["scoring_team_id"]), {}),
            by_team.get((season, row["conceding_team_id"]), {}),
            by_season.get(season, {}),
        ]
        for pool in candidates:
            if norm in pool:
                return pool[norm]
        for pool, min_score in ((candidates[0], threshold), (candidates[2], max(threshold, 92))):
            if pool:
                best = process.extractOne(norm, list(pool), scorer=fuzz.token_sort_ratio)
                if best and best[1] >= min_score:
                    return pool[best[0]]
        return float("nan")

    return goals.apply(lookup, axis=1)

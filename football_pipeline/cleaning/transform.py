"""Step 2 - Data cleaning: dai file raw eterogenei a un modello a stella omogeneo.

Fasi:
1. standardizzazione di ogni fonte verso uno schema comune (tipi, nomi colonna, risultati)
2. risoluzione dei nomi squadra verso il nome canonico (config/team_aliases.yaml)
3. scelta della fonte primaria dei risultati per stagione (`match_source_priority`)
4. collegamento di gol, quote, statistiche e xG alla partita (match_id)
5. scrittura delle tabelle in data/clean/ e delle tabelle di staging per la Data Quality
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from football_pipeline.acquisition.base import read_raw
from football_pipeline.cleaning.parsers import (
    parse_birth_and_age, parse_decimal_it, parse_money, parse_role, parse_score,
)
from football_pipeline.cleaning.players import match_scorers
from football_pipeline.cleaning.teams import TeamResolver
from football_pipeline.config import get_settings
from football_pipeline.utils.logging import get_logger
from football_pipeline.utils.text import normalize_name

log = get_logger(__name__)

MATCH_COLUMNS = [
    "season", "matchweek", "match_date", "stage", "home_team", "away_team",
    "home_goals", "away_goals", "home_goals_ht", "away_goals_ht", "provided_result", "source",
]
MATCH_KEY = ["season_id", "home_team_id", "away_team_id"]


class CleaningLog:
    def __init__(self):
        self.entries: list[dict] = []

    def add(self, table: str, action: str, rows: int, always: bool = False) -> None:
        if not rows and not always:
            return
        log.info("[cleaning] %s: %s (%d righe)", table, action, rows)
        self.entries.append({"table_name": table, "action": action, "rows_affected": int(rows)})

    def frame(self) -> pd.DataFrame:
        return pd.DataFrame(self.entries, columns=["table_name", "action", "rows_affected"])


def _num(series: pd.Series, kind: str = "float") -> pd.Series:
    out = pd.to_numeric(series, errors="coerce")
    return out.astype("Int64") if kind == "int" else out.astype(float)


def _result(home: pd.Series, away: pd.Series) -> pd.Series:
    res = np.select([home > away, home < away, home == away], ["H", "A", "D"], default=None)
    return pd.Series(res, index=home.index).where(home.notna() & away.notna())


def _mark_playoffs(df: pd.DataFrame, clog: CleaningLog, source: str) -> pd.DataFrame:
    """Stessa coppia casa/ospite due volte nella stessa stagione = spareggio
    (es. Spezia-Verona 2022/23): la partita più recente viene marcata PLAYOFF."""
    df = df.sort_values(["season", "match_date"], kind="stable")
    dup = df.duplicated(["season", "home_team", "away_team"], keep="first") & (df["stage"] == "REGULAR")
    df.loc[dup, "stage"] = "PLAYOFF"
    clog.add(f"match[{source}]", "partite di spareggio separate dalla stagione regolare", int(dup.sum()))
    return df


# --------------------------------------------------------------------------- fonti risultati

def _std_football_data_org(raw: pd.DataFrame) -> pd.DataFrame:
    if raw.empty:
        return pd.DataFrame(columns=MATCH_COLUMNS)
    df = pd.DataFrame({
        "season": _num(raw["season"], "int"),
        "matchweek": _num(raw["matchweek"], "int"),
        "match_date": pd.to_datetime(raw["date"], errors="coerce"),
        "stage": "REGULAR",
        "home_team": raw["home_team"],
        "away_team": raw["away_team"],
        "home_goals": _num(raw["home_score"], "int"),
        "away_goals": _num(raw["away_score"], "int"),
        "home_goals_ht": _num(raw["half_time_home_score"], "int"),
        "away_goals_ht": _num(raw["half_time_away_score"], "int"),
        "provided_result": raw["winner"].map({"HOME_TEAM": "H", "AWAY_TEAM": "A", "DRAW": "D"}),
        "source": "football_data_org",
    })
    if "stage" in raw:
        df.loc[raw["stage"].fillna("REGULAR_SEASON") != "REGULAR_SEASON", "stage"] = "PLAYOFF"
    if "status" in raw:
        df = df[raw["status"].fillna("FINISHED") == "FINISHED"]
    return df


def _std_api_football(raw: pd.DataFrame) -> pd.DataFrame:
    if raw.empty:
        return pd.DataFrame(columns=MATCH_COLUMNS)
    round_ = raw["matchweek"].fillna("")
    regular = round_.str.startswith("Regular Season")

    def flag(col):
        return raw[col].map({"True": True, "False": False}).fillna(False).astype(bool)

    home_win, away_win = flag("home_winner"), flag("away_winner")
    df = pd.DataFrame({
        "season": _num(raw["season"], "int"),
        "matchweek": _num(round_.str.extract(r"(\d+)$")[0], "int").where(regular),
        "match_date": pd.to_datetime(raw["date"], errors="coerce"),
        "stage": np.where(regular, "REGULAR", "PLAYOFF"),
        "home_team": raw["home_team"],
        "away_team": raw["away_team"],
        "home_goals": _num(raw["home_goals"], "int"),
        "away_goals": _num(raw["away_goals"], "int"),
        "home_goals_ht": _num(raw["home_goals_halftime"], "int"),
        "away_goals_ht": _num(raw["away_goals_halftime"], "int"),
        "provided_result": np.select([home_win & ~away_win, away_win & ~home_win], ["H", "A"], default="D"),
        "source": "api_football",
    })
    if "status" in raw:
        df = df[raw["status"].fillna("FT").isin(["FT", "AET", "PEN"])]
    return df


def _std_couk(raw: pd.DataFrame) -> pd.DataFrame:
    if raw.empty:
        return pd.DataFrame(columns=MATCH_COLUMNS)
    get = lambda col: raw[col] if col in raw else pd.Series(np.nan, index=raw.index)  # noqa: E731
    return pd.DataFrame({
        "season": _num(raw["season"], "int"),
        "matchweek": pd.array([pd.NA] * len(raw), dtype="Int64"),
        "match_date": pd.to_datetime(raw["Date"], dayfirst=True, errors="coerce", format="mixed"),
        "stage": "REGULAR",
        "home_team": raw["HomeTeam"],
        "away_team": raw["AwayTeam"],
        "home_goals": _num(raw["FTHG"], "int"),
        "away_goals": _num(raw["FTAG"], "int"),
        "home_goals_ht": _num(get("HTHG"), "int"),
        "away_goals_ht": _num(get("HTAG"), "int"),
        "provided_result": get("FTR"),
        "source": "football_data_couk",
    })


def _std_understat(raw: pd.DataFrame) -> pd.DataFrame:
    if raw.empty:
        return pd.DataFrame(columns=MATCH_COLUMNS)
    return pd.DataFrame({
        "season": _num(raw["season"], "int"),
        "matchweek": pd.array([pd.NA] * len(raw), dtype="Int64"),
        "match_date": pd.to_datetime(raw["datetime"], errors="coerce").dt.normalize(),
        "stage": "REGULAR",
        "home_team": raw["home_team"],
        "away_team": raw["away_team"],
        "home_goals": _num(raw["home_goals"], "int"),
        "away_goals": _num(raw["away_goals"], "int"),
        "home_goals_ht": pd.array([pd.NA] * len(raw), dtype="Int64"),
        "away_goals_ht": pd.array([pd.NA] * len(raw), dtype="Int64"),
        "provided_result": None,
        "source": "understat",
    })


# --------------------------------------------------------------------------- collegamento partite

def attach_match_id(df: pd.DataFrame, matches: pd.DataFrame, score_cols: tuple[str, str] | None = None) -> pd.Series:
    """match_id per ogni riga di df tramite (stagione, casa, ospite).

    Se la coppia ha più partite (spareggio) si sceglie quella con lo stesso
    punteggio (se disponibile), altrimenti quella di stagione regolare.
    """
    cand = matches[MATCH_KEY + ["match_id", "stage", "home_goals", "away_goals"]].rename(
        columns={"match_id": "_match_id", "stage": "_stage", "home_goals": "_hg", "away_goals": "_ag"})
    left = df[MATCH_KEY].copy()
    if score_cols:
        left["_src_hg"] = df[score_cols[0]].to_numpy()
        left["_src_ag"] = df[score_cols[1]].to_numpy()
    left["_rid"] = np.arange(len(left))
    merged = left.merge(cand, on=MATCH_KEY, how="left")
    rank = (merged["_stage"] != "REGULAR").astype(int)
    if score_cols:
        same_score = (merged["_src_hg"] == merged["_hg"]) & (merged["_src_ag"] == merged["_ag"])
        rank = rank + 2 * (~same_score.fillna(False)).astype(int)
    merged["_rank"] = rank
    merged = merged.sort_values(["_rid", "_rank"]).drop_duplicates("_rid")
    return pd.Series(merged["_match_id"].to_numpy(), index=df.index).astype("Int64")


# --------------------------------------------------------------------------- pipeline di cleaning

def run_cleaning() -> dict[str, pd.DataFrame]:
    settings = get_settings()
    seasons = settings.seasons
    clog = CleaningLog()
    resolver = TeamResolver(settings.team_aliases, settings.quality.get("fuzzy_threshold", 85))

    def resolve(df: pd.DataFrame, cols=("home_team", "away_team")) -> pd.DataFrame:
        for col in cols:
            df[col] = df[col].map(resolver.resolve)
        return df

    # ---- 1. risultati: tutte le fonti standardizzate (staging per i controlli incrociati)
    std = {
        "football_data_org": _std_football_data_org(read_raw("football_data_org", "matches")),
        "api_football": _std_api_football(read_raw("api_football", "fixtures")),
        "football_data_couk": _std_couk(read_raw("football_data_couk", "matches")),
        "understat": _std_understat(read_raw("understat", "matches")),
    }
    frames = []
    for source, df in std.items():
        if df.empty:
            continue
        before = len(df)
        df = df.dropna(subset=["home_goals", "away_goals"])
        clog.add(f"match[{source}]", "partite senza risultato scartate", before - len(df))
        df = _mark_playoffs(resolve(df), clog, source)
        frames.append(df)
    stg_matches = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=MATCH_COLUMNS)

    # ---- 2. scelta della fonte primaria per stagione
    primary_parts = []
    for season in seasons:
        for source in settings.match_source_priority:
            part = stg_matches[(stg_matches["season"] == season) & (stg_matches["source"] == source)]
            if not part.empty:
                primary_parts.append(part)
                clog.add("fact_match", f"stagione {season}: fonte primaria {source}", len(part))
                break
        else:
            clog.add("fact_match", f"stagione {season}: nessuna fonte disponibile", 0, always=True)
    matches = pd.concat(primary_parts, ignore_index=True) if primary_parts else stg_matches.iloc[0:0].copy()
    before = len(matches)
    matches = matches.drop_duplicates(["season", "home_team", "away_team", "stage"])
    clog.add("fact_match", "partite duplicate rimosse", before - len(matches))

    # ---- 3. altre fonti
    teams_raw = read_raw("transfermarkt", "teams")
    players_raw = read_raw("transfermarkt", "players")
    goals_raw = read_raw("transfermarkt", "goals")
    odds_raw = read_raw("oddsportal", "odds")
    couk_raw = read_raw("football_data_couk", "matches")
    xg_raw = read_raw("understat", "matches")
    elo_raw = read_raw("clubelo", "elo")

    if not teams_raw.empty:
        teams_raw["team"] = teams_raw["team"].map(resolver.resolve)
    if not players_raw.empty:
        players_raw["team"] = players_raw["team"].map(resolver.resolve)
    if not goals_raw.empty:
        goals_raw["_order"] = np.arange(len(goals_raw))
        resolve(goals_raw)
    if not odds_raw.empty:
        resolve(odds_raw)
    if not couk_raw.empty:
        couk_raw = resolve(couk_raw.rename(columns={"HomeTeam": "home_team", "AwayTeam": "away_team"}))
    if not xg_raw.empty:
        resolve(xg_raw)
    if not elo_raw.empty:
        # solo i club di prima divisione (ClubElo include anche la Serie B)
        elo_raw = elo_raw[elo_raw["Level"].astype(str) == "1"].copy()
        elo_raw["team"] = elo_raw["Club"].map(resolver.resolve)

    # ---- 4. dimensioni
    team_names = set(matches["home_team"]) | set(matches["away_team"])
    for df, col in ((teams_raw, "team"), (players_raw, "team")):
        if not df.empty:
            team_names |= set(df[col].dropna())
    team_ids = resolver.team_ids(team_names)
    dim_team = pd.DataFrame({"team_id": list(team_ids.values()), "team_name": list(team_ids.keys())})
    dim_season = pd.DataFrame({"season_id": seasons, "label": [f"{s}/{(s + 1) % 100:02d}" for s in seasons]})

    def ids(df: pd.DataFrame) -> pd.DataFrame:
        df = df.rename(columns={"season": "season_id"})
        df["season_id"] = _num(df["season_id"], "int")
        df["home_team_id"] = df["home_team"].map(team_ids).astype("Int64")
        df["away_team_id"] = df["away_team"].map(team_ids).astype("Int64")
        return df

    # ---- 5. fact_match
    matches = ids(matches)
    matches["match_id"] = (matches["season_id"] * 100000 + matches["home_team_id"] * 1000
                           + matches["away_team_id"] * 10 + (matches["stage"] == "PLAYOFF").astype(int))
    matches["result"] = _result(matches["home_goals"], matches["away_goals"])
    fact_match = matches[[
        "match_id", "season_id", "matchweek", "match_date", "stage", "home_team_id", "away_team_id",
        "home_goals", "away_goals", "home_goals_ht", "away_goals_ht", "result", "source",
    ]].sort_values(["season_id", "match_date", "match_id"]).reset_index(drop=True)

    stg_matches = ids(stg_matches)
    stg_matches["match_id"] = attach_match_id(stg_matches, fact_match, ("home_goals", "away_goals"))

    # ---- 6. squadre per stagione (Transfermarkt)
    fact_team_season = pd.DataFrame(columns=["season_id", "team_id", "squad_size", "avg_age", "n_foreigners", "squad_value_eur"])
    if not teams_raw.empty:
        fact_team_season = pd.DataFrame({
            "season_id": _num(teams_raw["season"], "int"),
            "team_id": teams_raw["team"].map(team_ids).astype("Int64"),
            "squad_size": _num(teams_raw["team_size"], "int"),
            "avg_age": teams_raw["avg_age"].map(parse_decimal_it),
            "n_foreigners": _num(teams_raw["n_foreigners"], "int"),
            "squad_value_eur": teams_raw["team_value"].map(parse_money),
        }).drop_duplicates(["season_id", "team_id"])

    # ---- 7. giocatori (Transfermarkt)
    dim_player = pd.DataFrame(columns=["player_id", "player_name", "birth_date"])
    fact_player_season = pd.DataFrame(columns=["season_id", "player_id", "team_id", "role", "role_group", "age", "market_value_eur"])
    if not players_raw.empty:
        p = players_raw.dropna(subset=["name"]).copy()
        clog.add("dim_player", "righe senza nome scartate", len(players_raw) - len(p))
        birth_age = p["age"].map(parse_birth_and_age)
        roles = [parse_role(r, n) for r, n in zip(p["role"], p["name"])]
        p["birth_date"] = [b for b, _ in birth_age]
        p["age_years"] = pd.array([a for _, a in birth_age], dtype="Int64")
        p["role_clean"] = [r for r, _ in roles]
        p["role_group"] = [g for _, g in roles]
        p["market_value_eur"] = p["market_value"].map(parse_money)
        clog.add("fact_player_season", "valori di mercato '-' convertiti in NULL (prima: 0)",
                 int(p["market_value_eur"].isna().sum()))
        p["player_key"] = p["name"].map(normalize_name) + "|" + p["birth_date"].astype(str)
        keys = (p.sort_values(["name", "birth_date"], key=lambda s: s.astype(str))
                 .drop_duplicates("player_key")[["player_key", "name", "birth_date"]])
        keys["player_id"] = np.arange(1, len(keys) + 1)
        dim_player = keys.rename(columns={"name": "player_name"})[["player_id", "player_name", "birth_date"]]
        p = p.merge(keys[["player_key", "player_id"]], on="player_key")
        fact_player_season = pd.DataFrame({
            "season_id": _num(p["season"], "int"),
            "player_id": p["player_id"],
            "team_id": p["team"].map(team_ids).astype("Int64"),
            "role": p["role_clean"],
            "role_group": p["role_group"],
            "age": p["age_years"],
            "market_value_eur": p["market_value_eur"],
        })
        before = len(fact_player_season)
        fact_player_season = fact_player_season.drop_duplicates(["season_id", "player_id", "team_id"])
        clog.add("fact_player_season", "righe duplicate rimosse", before - len(fact_player_season))

    # ---- 8. gol (Transfermarkt)
    fact_goal = pd.DataFrame(columns=[
        "goal_id", "match_id", "seq", "minute", "scoring_team_id", "conceding_team_id",
        "player_id", "scorer_name", "home_score_after", "away_score_after", "is_own_goal"])
    stg_goals = pd.DataFrame()
    if not goals_raw.empty:
        g = ids(goals_raw)
        g["match_id"] = attach_match_id(g, fact_match)
        g = g.sort_values("_order")
        g["seq"] = g.groupby(["season_id", "home_team", "away_team"]).cumcount() + 1
        scores = g["goal_result"].map(parse_score)
        g["home_score_after"] = pd.array([h for h, _ in scores], dtype="Int64")
        g["away_score_after"] = pd.array([a for _, a in scores], dtype="Int64")
        grp = g.groupby(["season_id", "home_team", "away_team"])
        prev_home = grp["home_score_after"].shift(1).fillna(0)
        prev_away = grp["away_score_after"].shift(1).fillna(0)
        home_scored = (g["home_score_after"] > prev_home).fillna(False).astype(bool)
        away_scored = (g["away_score_after"] > prev_away).fillna(False).astype(bool)
        g["scoring_team_id"] = g["home_team_id"].where(home_scored, g["away_team_id"].where(away_scored))
        g["conceding_team_id"] = g["away_team_id"].where(home_scored, g["home_team_id"].where(away_scored))
        g["minute"] = _num(g["minute"], "int")
        g["scorer_name"] = g["scorer"]
        stg_goals = g.copy()

        g["player_id"] = match_scorers(
            g, fact_player_season.merge(dim_player, on="player_id"),
            settings.quality.get("fuzzy_threshold", 85),
        ).astype("Int64")
        # autogol: il marcatore appartiene alla squadra che subisce il gol
        roster = set(zip(fact_player_season["season_id"], fact_player_season["player_id"], fact_player_season["team_id"]))
        g["is_own_goal"] = [
            pd.notna(pid) and (s, pid, conc) in roster and (s, pid, scor) not in roster
            for s, pid, scor, conc in zip(g["season_id"], g["player_id"], g["scoring_team_id"], g["conceding_team_id"])
        ]
        fact_goal = g.dropna(subset=["match_id"]).copy()
        clog.add("fact_goal", "gol non collegati a nessuna partita scartati", len(g) - len(fact_goal))
        fact_goal["goal_id"] = np.arange(1, len(fact_goal) + 1)
        fact_goal = fact_goal[[
            "goal_id", "match_id", "seq", "minute", "scoring_team_id", "conceding_team_id",
            "player_id", "scorer_name", "home_score_after", "away_score_after", "is_own_goal"]]

    # ---- 9. quote
    odds_frames = []
    stg_odds = pd.DataFrame()
    if not odds_raw.empty:
        o = ids(odds_raw)
        before = len(o)
        o = o.drop_duplicates(["season_id", "home_team", "away_team", "risultato", "quota_1", "quota_x", "quota_2"])
        clog.add("fact_odds[oddsportal]", "righe duplicate dallo scraping rimosse", before - len(o))
        score = o["risultato"].map(parse_score)
        o["home_goals"] = [h for h, _ in score]
        o["away_goals"] = [a for _, a in score]
        o["match_id"] = attach_match_id(o, fact_match, ("home_goals", "away_goals"))
        stg_odds = o.copy()
        odds_frames.append(pd.DataFrame({
            "match_id": o["match_id"], "source": "oddsportal", "bookmaker": "average",
            "odds_home": _num(o["quota_1"]), "odds_draw": _num(o["quota_x"]), "odds_away": _num(o["quota_2"]),
        }))

    fact_match_stats = pd.DataFrame(columns=["match_id", "referee"])
    if not couk_raw.empty:
        c = ids(couk_raw)
        c["FTHG"], c["FTAG"] = _num(c["FTHG"]), _num(c["FTAG"])
        c["match_id"] = attach_match_id(c, fact_match, ("FTHG", "FTAG"))
        c = c.dropna(subset=["match_id"])
        for bookmaker, cols in {
            "market_avg": [("AvgH", "AvgD", "AvgA"), ("BbAvH", "BbAvD", "BbAvA")],
            "bet365": [("B365H", "B365D", "B365A")],
            "pinnacle": [("PSH", "PSD", "PSA")],
        }.items():
            found = next((cs for cs in cols if all(col in c for col in cs)), None)
            if found:
                odds_frames.append(pd.DataFrame({
                    "match_id": c["match_id"], "source": "football_data_couk", "bookmaker": bookmaker,
                    "odds_home": _num(c[found[0]]), "odds_draw": _num(c[found[1]]), "odds_away": _num(c[found[2]]),
                }))
        stat_cols = {
            "Referee": "referee", "HS": "home_shots", "AS": "away_shots",
            "HST": "home_shots_on_target", "AST": "away_shots_on_target", "HF": "home_fouls", "AF": "away_fouls",
            "HC": "home_corners", "AC": "away_corners", "HY": "home_yellow", "AY": "away_yellow",
            "HR": "home_red", "AR": "away_red",
        }
        fact_match_stats = c[["match_id"] + [k for k in stat_cols if k in c]].rename(columns=stat_cols)
        for col in fact_match_stats.columns.difference(["match_id", "referee"]):
            fact_match_stats[col] = _num(fact_match_stats[col], "int")
        fact_match_stats = fact_match_stats.drop_duplicates("match_id")

    fact_odds = pd.concat(odds_frames, ignore_index=True) if odds_frames else pd.DataFrame(
        columns=["match_id", "source", "bookmaker", "odds_home", "odds_draw", "odds_away"])
    before = len(fact_odds)
    fact_odds = fact_odds.dropna(subset=["match_id"]).drop_duplicates(["match_id", "source", "bookmaker"])
    clog.add("fact_odds", "quote non collegate a partite o duplicate scartate", before - len(fact_odds))
    # quota "primaria" per partita secondo odds_source_priority
    primary_bookmaker = {"oddsportal": "average", "football_data_couk": "market_avg"}
    priority = {s: i for i, s in enumerate(settings.odds_source_priority)}
    fact_odds["_p"] = fact_odds["source"].map(priority).fillna(99)
    fact_odds["_b"] = (fact_odds["bookmaker"] != fact_odds["source"].map(primary_bookmaker)).astype(int)
    first = fact_odds.sort_values(["match_id", "_p", "_b"]).drop_duplicates("match_id").index
    fact_odds["is_primary"] = fact_odds.index.isin(first)
    fact_odds = fact_odds.drop(columns=["_p", "_b"])

    # ---- 10. expected goals (Understat)
    fact_match_xg = pd.DataFrame(columns=["match_id", "home_xg", "away_xg", "forecast_home", "forecast_draw", "forecast_away"])
    if not xg_raw.empty:
        x = ids(xg_raw)
        x["home_goals"], x["away_goals"] = _num(x["home_goals"]), _num(x["away_goals"])
        x["match_id"] = attach_match_id(x, fact_match, ("home_goals", "away_goals"))
        fact_match_xg = x.dropna(subset=["match_id"])[["match_id", "home_xg", "away_xg", "forecast_home", "forecast_draw", "forecast_away"]]
        for col in fact_match_xg.columns.difference(["match_id"]):
            fact_match_xg[col] = _num(fact_match_xg[col])
        fact_match_xg = fact_match_xg.drop_duplicates("match_id")

    # ---- 11. Elo (ClubElo)
    fact_team_elo = pd.DataFrame(columns=["season_id", "team_id", "snapshot", "snapshot_date", "elo"])
    if not elo_raw.empty:
        fact_team_elo = pd.DataFrame({
            "season_id": _num(elo_raw["season"], "int"),
            "team_id": elo_raw["team"].map(team_ids).astype("Int64"),
            "snapshot": elo_raw["snapshot"],
            "snapshot_date": pd.to_datetime(elo_raw["snapshot_date"]),
            "elo": _num(elo_raw["Elo"]),
        }).dropna(subset=["team_id"]).drop_duplicates(["season_id", "team_id", "snapshot"])

    # ---- risoluzione nomi (per la Data Quality)
    team_resolution = pd.DataFrame(
        [(raw, res, "fuzzy", score) for raw, (res, score) in resolver.fuzzy_matches.items()]
        + [(raw, None, "unresolved", None) for raw in sorted(resolver.unresolved)],
        columns=["raw_name", "canonical_name", "method", "score"],
    )

    tables = {
        "dim_season": dim_season,
        "dim_team": dim_team,
        "dim_player": dim_player,
        "fact_match": fact_match,
        "fact_match_stats": fact_match_stats,
        "fact_match_xg": fact_match_xg,
        "fact_odds": fact_odds,
        "fact_goal": fact_goal,
        "fact_team_season": fact_team_season,
        "fact_player_season": fact_player_season,
        "fact_team_elo": fact_team_elo,
    }
    staging = {
        "stg_match_sources": stg_matches.drop(columns=["home_team", "away_team"], errors="ignore"),
        "stg_goals": stg_goals.drop(columns=["home_team", "away_team", "_order"], errors="ignore"),
        "stg_odds": stg_odds.drop(columns=["home_team", "away_team"], errors="ignore"),
        "team_resolution": team_resolution,
        "cleaning_log": clog.frame(),
    }
    _write(tables, staging, settings)
    return {**tables, **staging}


def _write(tables: dict, staging: dict, settings) -> None:
    clean_dir = settings.clean_dir
    (clean_dir / "staging").mkdir(parents=True, exist_ok=True)
    for name, df in tables.items():
        df.to_csv(clean_dir / f"{name}.csv", index=False)
    for name, df in staging.items():
        df.to_csv(clean_dir / "staging" / f"{name}.csv", index=False)
    log.info("[cleaning] %d tabelle scritte in %s", len(tables), clean_dir)


DATE_COLUMNS = {"fact_match": ["match_date"], "dim_player": ["birth_date"], "fact_team_elo": ["snapshot_date"]}


def load_clean(include_staging: bool = True) -> dict[str, pd.DataFrame]:
    """Rilegge l'output del cleaning da disco (usato da quality e storage)."""
    clean_dir = get_settings().clean_dir
    if not clean_dir.exists():
        raise FileNotFoundError("Nessun dato pulito: eseguire prima lo step 'clean'")
    out = {}
    paths = list(clean_dir.glob("*.csv")) + (list((clean_dir / "staging").glob("*.csv")) if include_staging else [])
    for path in paths:
        name = path.stem
        out[name] = pd.read_csv(path, parse_dates=DATE_COLUMNS.get(name, []))
    return out

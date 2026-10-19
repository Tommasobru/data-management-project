"""Step 3 - Data Quality.

Ogni controllo misura una dimensione di qualità (completezza, unicità, validità,
consistenza tra fonti, integrità referenziale) e restituisce quante righe lo
violano. Lo stato è:
- PASS se le violazioni sono entro la tolleranza
- FAIL se il controllo è `critical` e la tolleranza è superata (blocca lo storage)
- WARN altrimenti
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Callable

import pandas as pd

from football_pipeline.config import get_settings

COMPLETENESS = "Completezza"
UNIQUENESS = "Unicità"
VALIDITY = "Validità"
CONSISTENCY = "Consistenza tra fonti"
INTEGRITY = "Integrità referenziale"

MATCHES_PER_SEASON = 380
MATCHES_PER_TEAM = 38


@dataclass
class CheckResult:
    check: str
    dimension: str
    table_name: str
    severity: str
    status: str
    failed: int
    total: int
    details: str = ""

    @property
    def failed_pct(self) -> float:
        return 100.0 * self.failed / self.total if self.total else 0.0


@dataclass
class Check:
    name: str
    dimension: str
    table: str
    severity: str  # critical | warning
    fn: Callable[[dict], tuple[int, int, str]]
    tolerance: float = 0.0  # frazione di righe in errore ammessa

    def run(self, t: dict) -> CheckResult:
        try:
            failed, total, details = self.fn(t)
        except Exception as exc:  # noqa: BLE001 - un controllo rotto è esso stesso un problema
            return CheckResult(self.name, self.dimension, self.table, self.severity, "FAIL", 1, 1,
                               f"errore nell'esecuzione del controllo: {exc}")
        if total == 0:
            status, details = "SKIP", details or "nessun dato da controllare"
        elif failed <= self.tolerance * total:
            status = "PASS"
        else:
            status = "FAIL" if self.severity == "critical" else "WARN"
        return CheckResult(self.name, self.dimension, self.table, self.severity, status,
                           int(failed), int(total), details)


def _examples(values, n: int = 5) -> str:
    values = list(values)
    if not values:
        return ""
    head = ", ".join(str(v) for v in values[:n])
    return f"es. {head}" + (f" (+{len(values) - n})" if len(values) > n else "")


def _team_names(t) -> dict:
    return dict(zip(t["dim_team"]["team_id"], t["dim_team"]["team_name"]))


def _regular(t) -> pd.DataFrame:
    m = t["fact_match"]
    return m[m["stage"] == "REGULAR"]


# --------------------------------------------------------------------------- completezza

def seasons_complete(t):
    seasons = get_settings().seasons
    counts = _regular(t).groupby("season_id").size().reindex(seasons, fill_value=0)
    bad = counts[counts != MATCHES_PER_SEASON]
    return len(bad), len(seasons), _examples(f"{s}: {n} partite" for s, n in bad.items())


def matches_per_team(t):
    m = _regular(t)
    per_team = pd.concat([
        m[["season_id", "home_team_id"]].rename(columns={"home_team_id": "team_id"}),
        m[["season_id", "away_team_id"]].rename(columns={"away_team_id": "team_id"}),
    ]).value_counts()
    bad = per_team[per_team != MATCHES_PER_TEAM]
    names = _team_names(t)
    return len(bad), len(per_team), _examples(f"{names.get(k[1])} {k[0]}: {n}" for k, n in bad.items())


def match_required_fields(t):
    m = t["fact_match"]
    cols = ["match_date", "home_team_id", "away_team_id", "home_goals", "away_goals", "result"]
    bad = m[m[cols].isna().any(axis=1)]
    return len(bad), len(m), _examples(bad["match_id"])


def halftime_present(t):
    m = t["fact_match"]
    bad = m[m[["home_goals_ht", "away_goals_ht"]].isna().any(axis=1)]
    return len(bad), len(m), "risultato del primo tempo mancante" if len(bad) else ""


def goals_coverage(t):
    m = _regular(t)
    scraped = t["fact_goal"].groupby("match_id").size()
    expected = (m["home_goals"] + m["away_goals"]).set_axis(m["match_id"])
    diff = expected - scraped.reindex(expected.index, fill_value=0)
    bad = diff[diff != 0]
    return len(bad), len(expected), (
        f"gol attesi {int(expected.sum())}, trovati {int(scraped.sum())}; " + _examples(bad.index)
    )


def odds_coverage(t):
    m = t["fact_match"]
    covered = set(t["fact_odds"].loc[t["fact_odds"]["is_primary"], "match_id"])
    missing = m[~m["match_id"].isin(covered)]
    return len(missing), len(m), _examples(missing["match_id"])


def team_profile_coverage(t):
    m = _regular(t)
    pairs = set(zip(m["season_id"], m["home_team_id"]))
    have = set(zip(t["fact_team_season"]["season_id"], t["fact_team_season"]["team_id"]))
    missing = sorted(pairs - have)
    names = _team_names(t)
    return len(missing), len(pairs), _examples(f"{names.get(tm)} {s}" for s, tm in missing)


def squad_size_consistency(t):
    declared = t["fact_team_season"].set_index(["season_id", "team_id"])["squad_size"]
    scraped = t["fact_player_season"].groupby(["season_id", "team_id"]).size()
    diff = (scraped.reindex(declared.index, fill_value=0) - declared).abs()
    bad = diff[diff > 3]
    names = _team_names(t)
    return len(bad), len(declared), _examples(
        f"{names.get(k[1])} {k[0]}: {int(scraped.get(k, 0))} giocatori vs {int(declared[k])} dichiarati" for k in bad.index)


def market_value_present(t):
    p = t["fact_player_season"]
    return int(p["market_value_eur"].isna().sum()), len(p), "giocatori senza valore di mercato"


# --------------------------------------------------------------------------- unicità

def unique_match_key(t):
    m = t["fact_match"]
    dup_id = m["match_id"].duplicated().sum()
    dup_key = m.duplicated(["season_id", "home_team_id", "away_team_id", "stage"]).sum()
    return int(dup_id + dup_key), len(m), ""


def unique_odds(t):
    o = t["fact_odds"]
    dup = o.duplicated(["match_id", "source", "bookmaker"]).sum()
    multi_primary = (o[o["is_primary"]].groupby("match_id").size() > 1).sum()
    return int(dup + multi_primary), len(o), ""


def raw_duplicates_removed(t):
    cl = t["cleaning_log"]
    rows = cl[cl["action"].str.contains("duplicat", case=False)]
    removed = int(rows["rows_affected"].sum())
    total = len(t["stg_odds"]) + removed if "stg_odds" in t else removed
    details = "; ".join(f"{r.table_name}: {r.rows_affected}" for r in rows.itertuples() if r.rows_affected)
    return removed, max(total, 1), details + (" (rimossi nel cleaning)" if removed else "")


def unique_player_season(t):
    p = t["fact_player_season"]
    return int(p.duplicated(["season_id", "player_id", "team_id"]).sum()), len(p), ""


# --------------------------------------------------------------------------- validità

def scores_valid(t):
    m = t["fact_match"]
    bad = m[(m["home_goals"] < 0) | (m["away_goals"] < 0)
            | (m["home_goals_ht"] > m["home_goals"]) | (m["away_goals_ht"] > m["away_goals"])]
    return len(bad), len(m), _examples(bad["match_id"])


def result_matches_score(t):
    s = t["stg_match_sources"].dropna(subset=["provided_result"])
    computed = pd.Series("D", index=s.index).mask(s["home_goals"] > s["away_goals"], "H").mask(
        s["home_goals"] < s["away_goals"], "A")
    bad = s[computed != s["provided_result"]]
    return len(bad), len(s), _examples(f"{r.source} {r.match_id}" for r in bad.itertuples())


def odds_valid(t):
    o = t["fact_odds"].dropna(subset=["odds_home", "odds_draw", "odds_away"])
    overround = 1 / o["odds_home"] + 1 / o["odds_draw"] + 1 / o["odds_away"]
    bad = o[(o[["odds_home", "odds_draw", "odds_away"]] <= 1).any(axis=1) | (overround < 0.97) | (overround > 1.25)]
    return len(bad), len(o), f"margine bookmaker medio {100 * (overround.mean() - 1):.1f}%" if len(o) else ""


def goal_minute_valid(t):
    g = t["fact_goal"]
    bad = g[g["minute"].isna() | (g["minute"] < 1) | (g["minute"] > 130)]
    return len(bad), len(g), _examples(bad["goal_id"])


def player_attributes_valid(t):
    p = t["fact_player_season"]
    bad = p[(p["age"].notna() & ((p["age"] < 15) | (p["age"] > 45))) | (p["market_value_eur"] < 0) | p["role_group"].isna()]
    return len(bad), len(p), _examples(bad["player_id"])


def match_date_in_season(t):
    m = t["fact_match"]
    start = pd.to_datetime(m["season_id"].astype(str) + "-07-15")
    end = pd.to_datetime((m["season_id"] + 1).astype(str) + "-07-15")
    bad = m[(m["match_date"] < start) | (m["match_date"] > end)]
    return len(bad), len(m), _examples(bad["match_id"])


# --------------------------------------------------------------------------- consistenza tra fonti

def odds_result_consistency(t):
    o = t["stg_odds"].dropna(subset=["match_id", "home_goals"])
    if o.empty:
        return 0, 0, ""
    m = t["fact_match"].set_index("match_id")
    merged = o.join(m[["home_goals", "away_goals"]], on="match_id", rsuffix="_api")
    bad = merged[(merged["home_goals"] != merged["home_goals_api"]) | (merged["away_goals"] != merged["away_goals_api"])]
    unmatched = int(t["stg_odds"]["match_id"].isna().sum())
    return len(bad) + unmatched, len(t["stg_odds"]), f"{unmatched} partite delle quote senza corrispondenza"


def odds_sources_agree(t):
    """Probabilità implicite di OddsPortal vs media di mercato di football-data.co.uk."""
    o = t["fact_odds"]
    a = o[(o["source"] == "oddsportal")].set_index("match_id")
    b = o[(o["source"] == "football_data_couk") & (o["bookmaker"] == "market_avg")].set_index("match_id")
    common = a.index.intersection(b.index)
    if common.empty:
        return 0, 0, "serve una seconda fonte di quote per il confronto"

    def probs(df):
        inv = 1 / df.loc[common, ["odds_home", "odds_draw", "odds_away"]]
        return inv.div(inv.sum(axis=1), axis=0).to_numpy()

    diff = pd.Series(abs(probs(a) - probs(b)).max(axis=1)).dropna()
    return int((diff > 0.10).sum()), len(diff), f"scarto medio delle probabilità {100 * diff.mean():.1f} punti percentuali"


def goals_final_score_consistency(t):
    g = t["fact_goal"].sort_values(["match_id", "seq"])
    last = g.groupby("match_id")[["home_score_after", "away_score_after"]].last()
    m = t["fact_match"].set_index("match_id").loc[last.index]
    bad = last[(last["home_score_after"] != m["home_goals"]) | (last["away_score_after"] != m["away_goals"])]
    return len(bad), len(last), _examples(bad.index)


def secondary_sources_agree(t):
    s = t["stg_match_sources"]
    primary = set(zip(t["fact_match"]["match_id"], t["fact_match"]["source"]))
    secondary = s[[(mid, src) not in primary for mid, src in zip(s["match_id"], s["source"])]]
    if secondary.empty:
        return 0, 0, "una sola fonte per stagione: nessun confronto possibile"
    m = t["fact_match"].set_index("match_id")
    linked = secondary.dropna(subset=["match_id"]).join(m[["home_goals", "away_goals"]], on="match_id", rsuffix="_p")
    bad = linked[(linked["home_goals"] != linked["home_goals_p"]) | (linked["away_goals"] != linked["away_goals_p"])]
    unlinked = int(secondary["match_id"].isna().sum())
    by_source = ", ".join(f"{k}: {v}" for k, v in secondary["source"].value_counts().items())
    return len(bad) + unlinked, len(secondary), f"righe confrontate per fonte -> {by_source}; non collegate {unlinked}"


def team_names_resolved(t):
    r = t["team_resolution"]
    unresolved = r[r["method"] == "unresolved"]
    fuzzy = r[r["method"] == "fuzzy"]
    details = _examples(unresolved["raw_name"])
    if len(fuzzy):
        details += " | risolti per similarità: " + _examples(f"{a}->{b}" for a, b in zip(fuzzy["raw_name"], fuzzy["canonical_name"]))
    return len(unresolved), len(t["dim_team"]) + len(unresolved), details


def scorers_linked(t):
    g = t["fact_goal"]
    missing = g[g["player_id"].isna()]
    return len(missing), len(g), _examples(missing["scorer_name"].value_counts().index)


def goals_side_determined(t):
    g = t["fact_goal"]
    bad = g[g["scoring_team_id"].isna()]
    return len(bad), len(g), _examples(bad["goal_id"])


# --------------------------------------------------------------------------- integrità referenziale

def foreign_keys(t):
    teams = set(t["dim_team"]["team_id"])
    seasons = set(t["dim_season"]["season_id"])
    matches = set(t["fact_match"]["match_id"])
    players = set(t["dim_player"]["player_id"])
    problems = {
        "fact_match.team": (~t["fact_match"]["home_team_id"].isin(teams) | ~t["fact_match"]["away_team_id"].isin(teams)).sum(),
        "fact_match.season": (~t["fact_match"]["season_id"].isin(seasons)).sum(),
        "fact_goal.match": (~t["fact_goal"]["match_id"].isin(matches)).sum(),
        "fact_goal.player": (t["fact_goal"]["player_id"].notna() & ~t["fact_goal"]["player_id"].isin(players)).sum(),
        "fact_odds.match": (~t["fact_odds"]["match_id"].isin(matches)).sum(),
        "fact_player_season.team": (~t["fact_player_season"]["team_id"].isin(teams)).sum(),
        "fact_team_season.team": (~t["fact_team_season"]["team_id"].isin(teams)).sum(),
    }
    total = len(t["fact_match"]) + len(t["fact_goal"]) * 2 + len(t["fact_odds"]) + len(t["fact_player_season"]) + len(t["fact_team_season"])
    bad = {k: int(v) for k, v in problems.items() if v}
    return sum(bad.values()), total, _examples(f"{k}: {v}" for k, v in bad.items())


CHECKS: list[Check] = [
    Check("Stagioni complete (380 partite)", COMPLETENESS, "fact_match", "warning", seasons_complete),
    Check("38 partite per squadra", COMPLETENESS, "fact_match", "critical", matches_per_team),
    Check("Campi obbligatori delle partite", COMPLETENESS, "fact_match", "critical", match_required_fields),
    Check("Risultato primo tempo presente", COMPLETENESS, "fact_match", "warning", halftime_present, 0.01),
    Check("Copertura gol per partita", COMPLETENESS, "fact_goal", "warning", goals_coverage, 0.05),
    Check("Copertura quote 1X2", COMPLETENESS, "fact_odds", "warning", odds_coverage, 0.02),
    Check("Profilo rosa per ogni squadra", COMPLETENESS, "fact_team_season", "warning", team_profile_coverage),
    Check("Giocatori estratti vs rosa dichiarata", COMPLETENESS, "fact_player_season", "warning", squad_size_consistency, 0.1),
    Check("Valore di mercato presente", COMPLETENESS, "fact_player_season", "warning", market_value_present, 0.05),
    Check("Chiave partita univoca", UNIQUENESS, "fact_match", "critical", unique_match_key),
    Check("Quote univoche per partita/bookmaker", UNIQUENESS, "fact_odds", "critical", unique_odds),
    Check("Giocatore univoco per stagione/squadra", UNIQUENESS, "fact_player_season", "critical", unique_player_season),
    Check("Duplicati nei dati raw", UNIQUENESS, "raw", "warning", raw_duplicates_removed),
    Check("Punteggi validi (FT >= HT >= 0)", VALIDITY, "fact_match", "critical", scores_valid),
    Check("Esito dichiarato coerente col punteggio", VALIDITY, "stg_match_sources", "critical", result_matches_score),
    Check("Quote valide (> 1, margine 0-25%)", VALIDITY, "fact_odds", "warning", odds_valid, 0.01),
    Check("Minuto del gol valido", VALIDITY, "fact_goal", "warning", goal_minute_valid),
    Check("Attributi giocatore validi", VALIDITY, "fact_player_season", "warning", player_attributes_valid, 0.01),
    Check("Data partita nella stagione", VALIDITY, "fact_match", "critical", match_date_in_season),
    Check("Risultato quote = risultato API", CONSISTENCY, "fact_odds", "warning", odds_result_consistency, 0.01),
    Check("Quote coerenti tra fonti (scarto < 10pp)", CONSISTENCY, "fact_odds", "warning", odds_sources_agree, 0.02),
    Check("Ultimo gol = risultato finale API", CONSISTENCY, "fact_goal", "warning", goals_final_score_consistency, 0.05),
    Check("Fonti secondarie concordano", CONSISTENCY, "stg_match_sources", "warning", secondary_sources_agree, 0.01),
    Check("Nomi squadra risolti", CONSISTENCY, "dim_team", "warning", team_names_resolved),
    Check("Marcatori collegati all'anagrafica", CONSISTENCY, "fact_goal", "warning", scorers_linked, 0.02),
    Check("Squadra che segna determinata", CONSISTENCY, "fact_goal", "warning", goals_side_determined, 0.01),
    Check("Chiavi esterne valide", INTEGRITY, "*", "critical", foreign_keys),
]


def run_checks(tables: dict) -> pd.DataFrame:
    results = [check.run(tables) for check in CHECKS]
    df = pd.DataFrame([asdict(r) | {"failed_pct": round(r.failed_pct, 2)} for r in results])
    return df

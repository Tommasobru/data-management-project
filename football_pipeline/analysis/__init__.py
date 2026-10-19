"""Step 5 - Analisi: funzioni che leggono le viste del data warehouse e calcolano
le metriche statistiche che non conviene esprimere in SQL (regressioni, calibrazione,
simulazioni di strategie di scommessa)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from football_pipeline.storage import read_sql

LATE_MINUTE = 85


def view(name: str, where: str = "", params: dict | None = None) -> pd.DataFrame:
    query = f"SELECT * FROM {name}" + (f" WHERE {where}" if where else "")
    return read_sql(query, params)


def linear_fit(x: pd.Series, y: pd.Series) -> dict:
    """Regressione lineare semplice: pendenza, intercetta, R² e previsioni."""
    mask = x.notna() & y.notna()
    if mask.sum() < 3:
        return {"slope": np.nan, "intercept": np.nan, "r2": np.nan, "pred": pd.Series(np.nan, index=x.index)}
    slope, intercept = np.polyfit(x[mask], y[mask], 1)
    pred = slope * x + intercept
    ss_res = ((y[mask] - pred[mask]) ** 2).sum()
    ss_tot = ((y[mask] - y[mask].mean()) ** 2).sum()
    return {"slope": slope, "intercept": intercept, "r2": 1 - ss_res / ss_tot, "pred": pred}


def value_vs_points(season_id: int | None = None) -> tuple[pd.DataFrame, dict]:
    """Punti vs log10(valore rosa): chi rende più (o meno) di quanto vale la rosa."""
    df = view("v_team_value_performance").dropna(subset=["squad_value_eur"])
    if season_id is not None:
        df = df[df["season_id"] == season_id]
    df = df.copy()
    df["value_m"] = df["squad_value_eur"] / 1e6
    df["log_value"] = np.log10(df["squad_value_eur"])
    fit = linear_fit(df["log_value"], df["points"])
    df["expected_by_value"] = fit["pred"]
    df["over_performance"] = df["points"] - df["expected_by_value"]
    return df, fit


def betting_strategies() -> pd.DataFrame:
    """Rendimento (ROI) di strategie semplici con puntata fissa di 1€ su ogni partita."""
    odds = view("v_match_odds")
    if odds.empty:
        return pd.DataFrame()
    picks = {
        "Sempre il favorito": odds["favourite"],
        "Sempre la sfavorita": np.where(odds["odds_home"] >= odds["odds_away"], "H", "A"),
        "Sempre la squadra di casa": "H",
        "Sempre il pareggio": "D",
        "Sempre la squadra in trasferta": "A",
    }
    price = {"H": odds["odds_home"], "D": odds["odds_draw"], "A": odds["odds_away"]}
    rows = []
    for name, pick in picks.items():
        pick = pd.Series(pick, index=odds.index)
        won = pick == odds["result"]
        paid = pd.concat([price[k].where(pick == k) for k in price], axis=1).bfill(axis=1).iloc[:, 0]
        profit = np.where(won, paid - 1, -1.0)
        for season, part in odds.assign(profit=profit, won=won).groupby("season"):
            rows.append({"strategia": name, "stagione": season, "partite": len(part),
                         "vinte_pct": 100 * part["won"].mean(), "profitto": part["profit"].sum(),
                         "roi_pct": 100 * part["profit"].mean()})
    return pd.DataFrame(rows)


def calibration(bins: int = 10) -> pd.DataFrame:
    """Probabilità implicita nelle quote vs frequenza osservata (affidabilità dei bookmaker)."""
    odds = view("v_match_odds")
    if odds.empty:
        return pd.DataFrame()
    long = pd.concat([
        pd.DataFrame({"esito": label, "p": odds[col], "hit": (odds["result"] == code).astype(int)})
        for code, col, label in (("H", "p_home", "1"), ("D", "p_draw", "X"), ("A", "p_away", "2"))
    ])
    long["bin"] = pd.cut(long["p"], np.linspace(0, 1, bins + 1), include_lowest=True)
    out = long.groupby("bin", observed=True).agg(prob_media=("p", "mean"), freq_reale=("hit", "mean"),
                                                 eventi=("hit", "size")).reset_index(drop=True)
    return out[out["eventi"] >= 10]


def biggest_upsets(n: int = 15) -> pd.DataFrame:
    odds = view("v_match_odds")
    if odds.empty:
        return odds
    paid = np.select([odds["result"] == "H", odds["result"] == "D"], [odds["odds_home"], odds["odds_draw"]], odds["odds_away"])
    odds = odds.assign(quota_esito=paid, prob_esito=1 / paid)
    return odds.sort_values("quota_esito", ascending=False).head(n)


def late_goal_points() -> pd.DataFrame:
    """Punti guadagnati/persi da ogni squadra con gol dall'85' in poi ("zona Cesarini").

    Si confronta il risultato prima del primo gol tardivo con quello finale.
    Si usano solo le partite in cui i gol estratti coincidono con il risultato finale
    (vedi controllo di Data Quality "Copertura gol per partita").
    """
    goals = view("v_goal_events")
    if goals.empty:
        return pd.DataFrame()
    per_match = goals.groupby("match_id").agg(n=("goal_id", "size"), hg=("home_goals", "first"), ag=("away_goals", "first"))
    complete = per_match[per_match["n"] == per_match["hg"] + per_match["ag"]].index
    goals = goals[goals["match_id"].isin(complete)].sort_values(["match_id", "seq"])

    rows = []
    for match_id, g in goals.groupby("match_id"):
        late = g[g["minute"] >= LATE_MINUTE]
        if late.empty:
            continue
        before = g[g["seq"] < late["seq"].min()]
        h0, a0 = (0, 0) if before.empty else (before["home_score_after"].iloc[-1], before["away_score_after"].iloc[-1])
        h1, a1 = g["home_goals"].iloc[0], g["away_goals"].iloc[0]
        pts = lambda x, y: 3 if x > y else (1 if x == y else 0)  # noqa: E731
        first = g.iloc[0]
        rows.append({"match_id": match_id, "season": first["season"], "team_id": first["home_team_id"],
                     "delta": pts(h1, a1) - pts(h0, a0)})
        rows.append({"match_id": match_id, "season": first["season"], "team_id": first["away_team_id"],
                     "delta": pts(a1, h1) - pts(a0, h0)})
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    teams = read_sql("SELECT team_id, team_name AS team FROM dim_team")
    df = df.merge(teams, on="team_id")
    out = df.groupby(["season", "team"]).agg(
        punti_guadagnati=("delta", lambda s: s[s > 0].sum()),
        punti_persi=("delta", lambda s: -s[s < 0].sum()),
    ).reset_index()
    out["saldo"] = out["punti_guadagnati"] - out["punti_persi"]
    return out


def age_value_curve() -> pd.DataFrame:
    df = read_sql("""
        SELECT age, role_group, market_value_eur FROM fact_player_season
        WHERE market_value_eur IS NOT NULL AND age BETWEEN 17 AND 38 AND role_group IS NOT NULL
    """)
    return (df.groupby(["role_group", "age"])["market_value_eur"]
              .agg(valore_mediano="median", giocatori="size").reset_index()
              .query("giocatori >= 8"))

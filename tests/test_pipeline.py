"""Test end-to-end: clean -> quality -> store sui dati di seed, più tre fonti
aggiuntive simulate (football-data.co.uk, Understat, ClubElo)."""
import shutil

import numpy as np
import pandas as pd

from football_pipeline.pipeline import run
from football_pipeline.storage import read_sql

SEASON = 2024
# nomi come li scrivono le varie fonti
COUK_NAMES = {"FC Internazionale Milano": "Inter", "AC Milan": "Milan", "Hellas Verona FC": "Verona"}
UNDERSTAT_NAMES = {"FC Internazionale Milano": "Inter", "AC Milan": "AC Milan", "Parma Calcio 1913": "Parma Calcio 1913"}


def _simulate_extra_sources(raw_dir):
    # si sostituiscono gli eventuali dati reali già scaricati con una sola stagione simulata
    for source in ("football_data_couk", "understat", "clubelo"):
        shutil.rmtree(raw_dir / source, ignore_errors=True)
    matches = pd.read_csv(raw_dir / "football_data_org" / f"matches_{SEASON}.csv")
    rng = np.random.default_rng(0)
    n = len(matches)

    couk = pd.DataFrame({
        "Div": "I1",
        "Date": pd.to_datetime(matches["date"]).dt.strftime("%d/%m/%Y"),
        "HomeTeam": matches["home_team"].replace(COUK_NAMES),
        "AwayTeam": matches["away_team"].replace(COUK_NAMES),
        "FTHG": matches["home_score"], "FTAG": matches["away_score"],
        "FTR": np.select([matches["home_score"] > matches["away_score"], matches["home_score"] < matches["away_score"]], ["H", "A"], "D"),
        "HTHG": matches["half_time_home_score"], "HTAG": matches["half_time_away_score"],
        "Referee": rng.choice(["Orsato D", "Guida M", "Mariani M"], n),
        "HS": rng.integers(5, 25, n), "AS": rng.integers(5, 25, n),
        "HST": rng.integers(1, 8, n), "AST": rng.integers(1, 8, n),
        "HF": 12, "AF": 13, "HC": 5, "AC": 4, "HY": 2, "AY": 3, "HR": 0, "AR": 0,
        "AvgH": 2.1, "AvgD": 3.3, "AvgA": 3.6, "B365H": 2.0, "B365D": 3.3, "B365A": 3.7,
        "season": SEASON,
    })
    (raw_dir / "football_data_couk").mkdir()
    couk.to_csv(raw_dir / "football_data_couk" / f"matches_{SEASON}.csv", index=False)

    understat = pd.DataFrame({
        "season": SEASON, "understat_id": range(n), "datetime": matches["date"] + " 18:00:00",
        "home_team": matches["home_team"].replace(UNDERSTAT_NAMES),
        "away_team": matches["away_team"].replace(UNDERSTAT_NAMES),
        "home_goals": matches["home_score"], "away_goals": matches["away_score"],
        "home_xg": rng.uniform(0.3, 3, n).round(2), "away_xg": rng.uniform(0.3, 3, n).round(2),
        "forecast_home": 0.4, "forecast_draw": 0.3, "forecast_away": 0.3,
    })
    (raw_dir / "understat").mkdir()
    understat.to_csv(raw_dir / "understat" / f"matches_{SEASON}.csv", index=False)

    teams = sorted(set(couk["HomeTeam"]))
    elo = pd.concat([
        pd.DataFrame({"Rank": range(len(teams)), "Club": teams, "Country": "ITA", "Level": 1,
                      "Elo": rng.uniform(1500, 1900, len(teams)), "From": "x", "To": "y",
                      "season": SEASON, "snapshot": snap, "snapshot_date": d})
        for snap, d in (("start", "2024-08-01"), ("end", "2025-06-01"))
    ] + [pd.DataFrame({"Rank": [99], "Club": ["Bari"], "Country": ["ITA"], "Level": [2], "Elo": [1400],
                       "From": "x", "To": "y", "season": SEASON, "snapshot": "start", "snapshot_date": "2024-08-01"})])
    (raw_dir / "clubelo").mkdir()
    elo.to_csv(raw_dir / "clubelo" / f"elo_{SEASON}.csv", index=False)


def test_seed_pipeline(sandbox):
    summary = run(steps=["clean", "quality", "store"])
    report = summary["quality"]
    assert not ((report["status"] == "FAIL")).any(), report[report["status"] == "FAIL"]

    standings = read_sql("SELECT season_id, team, points FROM v_standings WHERE position = 1 ORDER BY season_id")
    assert list(standings["team"]) == ["Napoli", "Inter", "Napoli", "Inter"]
    assert list(standings["points"]) == [90, 94, 82, 87]

    # le 400 quote duplicate del 2024 sono state rimosse: una quota primaria per partita
    dup = read_sql("SELECT COUNT(*) AS n FROM (SELECT match_id FROM fact_odds WHERE is_primary GROUP BY match_id HAVING COUNT(*) > 1) x")
    assert dup["n"][0] == 0
    # lo spareggio Spezia-Verona 2022 non entra in classifica
    assert read_sql("SELECT COUNT(*) AS n FROM fact_match WHERE stage = 'PLAYOFF'")["n"][0] == 1
    assert read_sql("SELECT SUM(played) AS n FROM v_standings WHERE season_id = 2022")["n"][0] == 760


def test_pipeline_with_extra_sources(sandbox):
    _simulate_extra_sources(sandbox.raw_dir)
    summary = run(steps=["clean", "quality", "store"])
    report = summary["quality"].set_index("check")

    assert report.loc["Fonti secondarie concordano", "status"] == "PASS"
    assert report.loc["Nomi squadra risolti", "status"] == "PASS"
    assert read_sql("SELECT COUNT(*) AS n FROM fact_match_stats")["n"][0] == 380
    assert read_sql("SELECT COUNT(*) AS n FROM fact_match_xg")["n"][0] == 380
    assert read_sql("SELECT COUNT(DISTINCT season_id) AS n FROM fact_match")["n"][0] == 4
    assert read_sql("SELECT COUNT(*) AS n FROM v_team_elo")["n"][0] == 20  # Serie B esclusa
    assert len(read_sql("SELECT * FROM v_team_xg")) == 20
    assert len(read_sql("SELECT * FROM v_referee_stats")) == 3
    # football-data.org resta la fonte primaria del 2024 secondo la priorità configurata
    assert read_sql("SELECT DISTINCT source FROM fact_match WHERE season_id = 2024")["source"].tolist() == ["football_data_org"]


def test_quality_gate_blocks_critical_failures(sandbox):
    import pytest

    from football_pipeline.quality import QualityGateError

    path = sandbox.raw_dir / "api_football" / "fixtures_2022.csv"
    df = pd.read_csv(path, dtype=str)
    df.loc[0, "home_winner"] = "False"   # esito dichiarato incoerente con il punteggio
    df.loc[0, "away_winner"] = "True"
    df.loc[0, "home_goals"] = "5"
    df.to_csv(path, index=False)
    with pytest.raises(QualityGateError):
        run(steps=["clean", "quality", "store"])


def test_storage_is_atomic(sandbox, monkeypatch):
    """Un errore a metà caricamento lascia il database com'era (anche su SQLite)."""
    import pytest

    from football_pipeline.storage import loader

    run(steps=["clean", "quality", "store"])
    before = read_sql("SELECT COUNT(*) AS n FROM fact_match")["n"][0]

    def broken(conn):
        raise RuntimeError("errore simulato durante la creazione delle viste")

    monkeypatch.setattr(loader, "create_views", broken)
    with pytest.raises(RuntimeError):
        run(steps=["store"])
    assert read_sql("SELECT COUNT(*) AS n FROM fact_match")["n"][0] == before
    assert len(read_sql("SELECT * FROM v_standings")) == 80

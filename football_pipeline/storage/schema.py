"""Schema a stella del data warehouse (SQLAlchemy Core: portabile SQLite/PostgreSQL)."""
from sqlalchemy import (
    Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, MetaData, String, Table, Text,
)

metadata = MetaData()

# ----------------------------------------------------------------- dimensioni
dim_season = Table(
    "dim_season", metadata,
    Column("season_id", Integer, primary_key=True, comment="anno di inizio stagione"),
    Column("label", String(7), nullable=False),
)

dim_team = Table(
    "dim_team", metadata,
    Column("team_id", Integer, primary_key=True),
    Column("team_name", String(60), nullable=False, unique=True),
)

dim_player = Table(
    "dim_player", metadata,
    Column("player_id", Integer, primary_key=True),
    Column("player_name", String(120), nullable=False),
    Column("birth_date", Date),
)

# ----------------------------------------------------------------- fatti
fact_match = Table(
    "fact_match", metadata,
    Column("match_id", Integer, primary_key=True),
    Column("season_id", Integer, ForeignKey("dim_season.season_id"), nullable=False),
    Column("matchweek", Integer),
    Column("match_date", Date, nullable=False),
    Column("stage", String(10), nullable=False, comment="REGULAR | PLAYOFF"),
    Column("home_team_id", Integer, ForeignKey("dim_team.team_id"), nullable=False),
    Column("away_team_id", Integer, ForeignKey("dim_team.team_id"), nullable=False),
    Column("home_goals", Integer, nullable=False),
    Column("away_goals", Integer, nullable=False),
    Column("home_goals_ht", Integer),
    Column("away_goals_ht", Integer),
    Column("result", String(1), nullable=False, comment="H | D | A"),
    Column("source", String(30), nullable=False),
)

fact_match_stats = Table(
    "fact_match_stats", metadata,
    Column("match_id", Integer, ForeignKey("fact_match.match_id"), primary_key=True),
    Column("referee", String(60)),
    *[Column(f"{side}_{stat}", Integer)
      for stat in ("shots", "shots_on_target", "fouls", "corners", "yellow", "red")
      for side in ("home", "away")],
)

fact_match_xg = Table(
    "fact_match_xg", metadata,
    Column("match_id", Integer, ForeignKey("fact_match.match_id"), primary_key=True),
    Column("home_xg", Float), Column("away_xg", Float),
    Column("forecast_home", Float), Column("forecast_draw", Float), Column("forecast_away", Float),
)

fact_odds = Table(
    "fact_odds", metadata,
    Column("match_id", Integer, ForeignKey("fact_match.match_id"), primary_key=True),
    Column("source", String(30), primary_key=True),
    Column("bookmaker", String(30), primary_key=True),
    Column("odds_home", Float), Column("odds_draw", Float), Column("odds_away", Float),
    Column("is_primary", Boolean, nullable=False),
)

fact_goal = Table(
    "fact_goal", metadata,
    Column("goal_id", Integer, primary_key=True),
    Column("match_id", Integer, ForeignKey("fact_match.match_id"), nullable=False),
    Column("seq", Integer, nullable=False),
    Column("minute", Integer),
    Column("scoring_team_id", Integer, ForeignKey("dim_team.team_id")),
    Column("conceding_team_id", Integer, ForeignKey("dim_team.team_id")),
    Column("player_id", Integer, ForeignKey("dim_player.player_id")),
    Column("scorer_name", String(120)),
    Column("home_score_after", Integer),
    Column("away_score_after", Integer),
    Column("is_own_goal", Boolean, nullable=False),
)

fact_team_season = Table(
    "fact_team_season", metadata,
    Column("season_id", Integer, ForeignKey("dim_season.season_id"), primary_key=True),
    Column("team_id", Integer, ForeignKey("dim_team.team_id"), primary_key=True),
    Column("squad_size", Integer),
    Column("avg_age", Float),
    Column("n_foreigners", Integer),
    Column("squad_value_eur", Float),
)

fact_player_season = Table(
    "fact_player_season", metadata,
    Column("season_id", Integer, ForeignKey("dim_season.season_id"), primary_key=True),
    Column("player_id", Integer, ForeignKey("dim_player.player_id"), primary_key=True),
    Column("team_id", Integer, ForeignKey("dim_team.team_id"), primary_key=True),
    Column("role", String(40)),
    Column("role_group", String(20)),
    Column("age", Integer),
    Column("market_value_eur", Float),
)

fact_team_elo = Table(
    "fact_team_elo", metadata,
    Column("season_id", Integer, ForeignKey("dim_season.season_id"), primary_key=True),
    Column("team_id", Integer, ForeignKey("dim_team.team_id"), primary_key=True),
    Column("snapshot", String(5), primary_key=True, comment="start | end"),
    Column("snapshot_date", Date),
    Column("elo", Float),
)

# ----------------------------------------------------------------- metadati della pipeline
dq_results = Table(
    "dq_results", metadata,
    Column("run_id", String(20), primary_key=True),
    Column("check_name", String(80), primary_key=True),
    Column("dimension", String(40)),
    Column("table_name", String(40)),
    Column("severity", String(10)),
    Column("status", String(4)),
    Column("failed", Integer),
    Column("total", Integer),
    Column("failed_pct", Float),
    Column("details", Text),
)

etl_run_log = Table(
    "etl_run_log", metadata,
    Column("run_id", String(20), primary_key=True),
    Column("started_at", DateTime),
    Column("finished_at", DateTime),
    Column("steps", String(80)),
    Column("status", String(10)),
    Column("message", Text),
)

etl_table_stats = Table(
    "etl_table_stats", metadata,
    Column("run_id", String(20), primary_key=True),
    Column("table_name", String(40), primary_key=True),
    Column("rows", Integer),
)

cleaning_log = Table(
    "cleaning_log", metadata,
    Column("run_id", String(20), primary_key=True),
    Column("seq", Integer, primary_key=True),
    Column("table_name", String(60)),
    Column("action", Text),
    Column("rows_affected", Integer),
)

# ordine di caricamento (rispetta le chiavi esterne)
DATA_TABLES = [
    "dim_season", "dim_team", "dim_player", "fact_match", "fact_match_stats", "fact_match_xg",
    "fact_odds", "fact_goal", "fact_team_season", "fact_player_season", "fact_team_elo",
]

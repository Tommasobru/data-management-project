"""Step 4 - Data storage nel data warehouse (SQLite di default, PostgreSQL opzionale)."""
from football_pipeline.storage.db import get_engine, read_sql, table_exists
from football_pipeline.storage.loader import run_storage

__all__ = ["get_engine", "read_sql", "run_storage", "table_exists"]

from __future__ import annotations

from functools import lru_cache

import pandas as pd
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.engine import Engine

from football_pipeline.config import get_settings


@lru_cache(maxsize=4)
def get_engine(url: str | None = None) -> Engine:
    url = url or get_settings().database_url
    if url.startswith("sqlite:///"):
        from pathlib import Path
        Path(url[len("sqlite:///"):]).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(url, future=True)
    if engine.dialect.name == "sqlite":
        _transactional_ddl(engine)
    return engine


def _transactional_ddl(engine: Engine) -> None:
    """Il driver sqlite3 esegue DROP/CREATE fuori dalla transazione: con un BEGIN esplicito
    l'intero caricamento diventa atomico (ricetta della documentazione SQLAlchemy)."""
    @event.listens_for(engine, "connect")
    def _no_implicit_transactions(dbapi_connection, _record):
        dbapi_connection.isolation_level = None

    @event.listens_for(engine, "begin")
    def _explicit_begin(conn):
        conn.exec_driver_sql("BEGIN")


def read_sql(query: str, params: dict | None = None, url: str | None = None) -> pd.DataFrame:
    with get_engine(url).connect() as conn:
        return pd.read_sql_query(text(query), conn, params=params)


def table_exists(name: str, url: str | None = None) -> bool:
    insp = inspect(get_engine(url))
    return name in insp.get_table_names() or name in insp.get_view_names()

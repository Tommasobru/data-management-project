"""Step 4 - Data storage: caricamento completo (full reload) del data warehouse.

1. elimina viste e tabelle dati esistenti
2. ricrea lo schema a stella (chiavi primarie ed esterne)
3. inserisce le tabelle pulite
4. ricrea le viste analitiche (storage/views/*.sql)
Le tabelle di metadati (dq_results, etl_run_log, ...) mantengono lo storico delle esecuzioni.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd
from sqlalchemy import Date, DateTime, inspect, text

from football_pipeline.cleaning import load_clean
from football_pipeline.storage.db import get_engine
from football_pipeline.storage.schema import DATA_TABLES, metadata
from football_pipeline.utils.logging import get_logger

log = get_logger(__name__)

VIEWS_DIR = Path(__file__).parent / "views"


def view_files() -> list[Path]:
    return sorted(VIEWS_DIR.glob("*.sql"))


def _view_name(path: Path) -> str:
    return path.stem.split("_", 1)[1]


def _records(df: pd.DataFrame, table) -> list[dict]:
    df = df[[c.name for c in table.columns if c.name in df.columns]].copy()
    for col in table.columns:
        if col.name not in df:
            continue
        if isinstance(col.type, Date) and not isinstance(col.type, DateTime):
            df[col.name] = pd.to_datetime(df[col.name], errors="coerce").map(
                lambda v: v.date() if pd.notna(v) else None)
        elif isinstance(col.type, DateTime):
            df[col.name] = pd.to_datetime(df[col.name], errors="coerce").map(
                lambda v: v.to_pydatetime() if pd.notna(v) else None)
    df = df.astype(object).where(df.notna(), None)
    return df.to_dict("records")


def _insert(conn, table, df: pd.DataFrame) -> int:
    records = _records(df, table)
    if records:
        conn.execute(table.insert(), records)
    return len(records)


def drop_views(conn) -> None:
    existing = set(inspect(conn).get_view_names())
    for path in reversed(view_files()):
        name = _view_name(path)
        if name in existing:
            conn.execute(text(f"DROP VIEW {name}"))


def create_views(conn) -> None:
    for path in view_files():
        conn.execute(text(path.read_text(encoding="utf-8")))


def run_storage(tables: dict | None = None, quality_report: pd.DataFrame | None = None,
                run_id: str | None = None) -> dict[str, int]:
    tables = tables or load_clean()
    run_id = run_id or datetime.now().strftime("%Y%m%d-%H%M%S")
    engine = get_engine()
    counts: dict[str, int] = {}
    with engine.begin() as conn:
        drop_views(conn)
        metadata.drop_all(conn, tables=[metadata.tables[n] for n in DATA_TABLES])
        metadata.create_all(conn)
        for name in DATA_TABLES:
            counts[name] = _insert(conn, metadata.tables[name], tables.get(name, pd.DataFrame()))
            log.info("[storage] %-20s %6d righe", name, counts[name])
        create_views(conn)
        log.info("[storage] %d viste analitiche create", len(view_files()))

        stats = pd.DataFrame({"run_id": run_id, "table_name": list(counts), "rows": list(counts.values())})
        _insert(conn, metadata.tables["etl_table_stats"], stats)
        if "cleaning_log" in tables:
            cl = tables["cleaning_log"].assign(run_id=run_id)
            cl["seq"] = range(1, len(cl) + 1)
            _insert(conn, metadata.tables["cleaning_log"], cl)
        if quality_report is not None:
            dq = quality_report.rename(columns={"check": "check_name"}).assign(run_id=run_id)
            _insert(conn, metadata.tables["dq_results"], dq)
    log.info("[storage] data warehouse aggiornato: %s", engine.url.render_as_string(hide_password=True))
    return counts

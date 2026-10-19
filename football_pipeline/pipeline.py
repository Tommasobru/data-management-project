"""Orchestratore: esegue gli step in sequenza, ognuno leggendo l'output del precedente.

    acquire -> clean -> quality -> store

Ogni step è eseguibile anche da solo (legge da disco l'output dello step precedente),
ma `run()` li concatena in un unico flusso e registra l'esecuzione in `etl_run_log`.
"""
from __future__ import annotations

import time
from datetime import datetime

import pandas as pd

from football_pipeline.acquisition import run_acquisition
from football_pipeline.cleaning import run_cleaning
from football_pipeline.quality import QualityGateError, run_quality
from football_pipeline.storage import get_engine, run_storage
from football_pipeline.storage.schema import etl_run_log, metadata
from football_pipeline.utils.logging import get_logger

log = get_logger(__name__)

STEPS = ("acquire", "clean", "quality", "store")


def _log_run(run_id: str, started: datetime, steps: list[str], status: str, message: str) -> None:
    try:
        engine = get_engine()
        with engine.begin() as conn:
            metadata.create_all(conn, tables=[etl_run_log])
            conn.execute(etl_run_log.insert(), [{
                "run_id": run_id, "started_at": started, "finished_at": datetime.now(),
                "steps": ",".join(steps), "status": status, "message": message[:2000],
            }])
    except Exception as exc:  # noqa: BLE001 - il log non deve mascherare l'errore originale
        log.warning("impossibile registrare l'esecuzione: %s", exc)


def run(steps: list[str] | None = None, refresh: bool = False, sources: list[str] | None = None,
        force: bool = False) -> dict:
    steps = [s for s in STEPS if s in (steps or STEPS)]
    run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    started = datetime.now()
    summary: dict = {"run_id": run_id}
    tables = report = None
    log.info("=== pipeline %s: %s ===", run_id, " -> ".join(steps))
    try:
        for step in steps:
            t0 = time.perf_counter()
            log.info("--- step: %s ---", step)
            if step == "acquire":
                results = run_acquisition(refresh=refresh, only=sources)
                summary["acquisition"] = pd.DataFrame([r.__dict__ for r in results])
            elif step == "clean":
                tables = run_cleaning()
            elif step == "quality":
                report = run_quality(tables, force=force)
                summary["quality"] = report
            elif step == "store":
                if report is None:
                    report = run_quality(tables, force=force)
                summary["storage"] = run_storage(tables, report, run_id=run_id)
            log.info("--- step %s completato in %.1fs ---", step, time.perf_counter() - t0)
    except QualityGateError as exc:
        _log_run(run_id, started, steps, "BLOCKED", str(exc))
        raise
    except Exception as exc:
        _log_run(run_id, started, steps, "FAILED", repr(exc))
        raise
    _log_run(run_id, started, steps, "SUCCESS", "")
    return summary

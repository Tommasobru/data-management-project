"""Punto di ingresso unico della pipeline.

Esempi:
    python main.py run                      # tutti gli step (acquisizione con cache)
    python main.py run --offline            # salta l'acquisizione, usa i dati raw esistenti
    python main.py run --refresh            # riscarica tutto dalle fonti
    python main.py run --steps clean,quality
    python main.py acquire --sources clubelo,understat
    python main.py status                   # stato dei dati raw e del database
    streamlit run app/Home.py               # dashboard
"""
from __future__ import annotations

import argparse
import sys

from football_pipeline import pipeline
from football_pipeline.quality import QualityGateError
from football_pipeline.utils.logging import setup_logging


def _status() -> None:
    import pandas as pd

    from football_pipeline.acquisition import SOURCES
    from football_pipeline.config import get_settings
    from football_pipeline.storage import read_sql, table_exists

    settings = get_settings()
    rows = []
    for name, cls in SOURCES.items():
        for dataset in cls.datasets:
            present = [s for s in settings.seasons if (settings.raw_dir / name / f"{dataset}_{s}.csv").exists()]
            rows.append({"fonte": name, "tipo": cls.kind, "dataset": dataset,
                         "abilitata": settings.source_enabled(name),
                         "stagioni presenti": ", ".join(map(str, present)) or "-"})
    print(pd.DataFrame(rows).to_string(index=False))
    print(f"\nDatabase: {settings.database_url}")
    if table_exists("etl_run_log"):
        print(read_sql("SELECT run_id, steps, status FROM etl_run_log ORDER BY run_id DESC LIMIT 5").to_string(index=False))
    else:
        print("nessuna esecuzione registrata: lanciare `python main.py run`")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Pipeline dati Serie A")
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="esegue la pipeline completa (o alcuni step)")
    run_p.add_argument("--steps", default=",".join(pipeline.STEPS),
                       help=f"step separati da virgola tra: {', '.join(pipeline.STEPS)}")
    run_p.add_argument("--offline", action="store_true", help="salta l'acquisizione")
    run_p.add_argument("--refresh", action="store_true", help="ignora la cache dei file raw")
    run_p.add_argument("--sources", help="limita l'acquisizione a queste fonti")
    run_p.add_argument("--force", action="store_true", help="carica anche se un controllo critico fallisce")

    for step in pipeline.STEPS:
        p = sub.add_parser(step, help=f"esegue solo lo step '{step}'")
        if step == "acquire":
            p.add_argument("--refresh", action="store_true")
            p.add_argument("--sources")
        if step in ("quality", "store"):
            p.add_argument("--force", action="store_true")

    sub.add_parser("status", help="mostra lo stato di dati raw e database")

    args = parser.parse_args(argv)
    setup_logging()

    if args.command == "status":
        _status()
        return 0

    if args.command == "run":
        steps = [s.strip() for s in args.steps.split(",")]
        if args.offline:
            steps = [s for s in steps if s != "acquire"]
    else:
        steps = [args.command]
        if args.command == "store":
            steps = ["quality", "store"]

    sources = getattr(args, "sources", None)
    try:
        pipeline.run(
            steps=steps,
            refresh=getattr(args, "refresh", False),
            sources=[s.strip() for s in sources.split(",")] if sources else None,
            force=getattr(args, "force", False),
        )
    except QualityGateError as exc:
        print(f"\n[BLOCCATO] {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())

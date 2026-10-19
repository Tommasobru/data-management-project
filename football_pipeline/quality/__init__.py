"""Step 3 - Data Quality: controlli sulle tabelle pulite prima dello storage."""
from __future__ import annotations

from datetime import datetime

import pandas as pd

from football_pipeline.cleaning import load_clean
from football_pipeline.config import get_settings
from football_pipeline.quality.checks import CHECKS, run_checks
from football_pipeline.utils.logging import get_logger

log = get_logger(__name__)

__all__ = ["CHECKS", "QualityGateError", "run_quality", "run_checks"]

ICONS = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌", "SKIP": "➖"}


class QualityGateError(RuntimeError):
    pass


def _markdown(report: pd.DataFrame) -> str:
    lines = [
        f"# Report Data Quality — {datetime.now():%Y-%m-%d %H:%M}",
        "",
        " · ".join(f"{ICONS[s]} {s}: {n}" for s, n in report["status"].value_counts().items()),
        "",
        "| Stato | Dimensione | Controllo | Tabella | Violazioni | Dettagli |",
        "|---|---|---|---|---|---|",
    ]
    for r in report.itertuples():
        lines.append(f"| {ICONS[r.status]} {r.status} | {r.dimension} | {r.check} | `{r.table_name}` "
                     f"| {r.failed}/{r.total} ({r.failed_pct}%) | {r.details} |")
    return "\n".join(lines) + "\n"


def run_quality(tables: dict | None = None, force: bool = False) -> pd.DataFrame:
    settings = get_settings()
    tables = tables or load_clean()
    report = run_checks(tables)
    settings.reports_dir.mkdir(parents=True, exist_ok=True)
    report.to_csv(settings.reports_dir / "quality_report.csv", index=False)
    (settings.reports_dir / "quality_report.md").write_text(_markdown(report), encoding="utf-8")

    for r in report.itertuples():
        level = {"PASS": 20, "SKIP": 20, "WARN": 30, "FAIL": 40}[r.status]
        log.log(level, "[quality] %-5s %-40s %d/%d %s", r.status, r.check, r.failed, r.total, r.details[:120])

    critical = report[(report["status"] == "FAIL") & (report["severity"] == "critical")]
    if len(critical) and settings.quality.get("block_on_critical", True) and not force:
        raise QualityGateError(
            f"{len(critical)} controlli critici falliti: {', '.join(critical['check'])}. "
            "Vedi data/reports/quality_report.md (usa --force per caricare comunque)."
        )
    return report

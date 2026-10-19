# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Serie A data pipeline (master's Data Management project): acquire data from APIs and web scraping → clean/integrate → Data Quality checks → load into a star-schema warehouse → Streamlit dashboard. Code comments, logs, UI text and docs are in **Italian**; keep new user-facing text in Italian. Full docs live in `docs/` (pipeline, data model, DQ checks, dashboard, configuration).

## Commands

```bash
pip install -r requirements.txt
python main.py run                     # acquire (only missing raw files) -> clean -> quality -> store
python main.py run --offline           # skip network; rebuild DB from data/raw
python main.py run --refresh           # re-download even cached raw files
python main.py run --steps clean,quality
python main.py acquire --sources oddsportal,understat
python main.py quality                 # writes data/reports/quality_report.md
python main.py status                  # raw coverage per source/season + last runs
streamlit run app/Home.py              # dashboard

pytest                                 # all tests (pytest.ini sets pythonpath=.)
pytest tests/test_pipeline.py::test_seed_pipeline
pytest -k oddsportal
```

Exit codes of `main.py`: 0 ok, 2 storage blocked by a critical DQ failure (`--force` overrides).

## Architecture

Each step reads the previous step's output **from disk**, so steps run independently; `football_pipeline/pipeline.py` chains them and logs every run to `etl_run_log`.

1. **Acquisition** (`football_pipeline/acquisition/`): one `Source` subclass per source, registered in `SOURCES` (`acquisition/__init__.py`). Output is written untransformed to `data/raw/<source>/<dataset>_<season>.csv`; an existing file is a cache hit unless `--refresh`. `SourceUnavailable` / `ConnectionFailed` (from `utils/http.py`) abort the whole source; other errors fail only that season. `data/raw/` is versioned in git and is the offline seed.
2. **Cleaning** (`cleaning/transform.py::run_cleaning`): standardizes every results source into one schema, resolves team names via `config/team_aliases.yaml` + rapidfuzz (`cleaning/teams.py`), picks a primary results source per season using `match_source_priority`, and links goals/odds/stats/xG to matches with `attach_match_id` (season, home, away; score disambiguates the playoff). Writes star tables to `data/clean/*.csv` and DQ staging tables (`stg_match_sources`, `stg_odds`, `stg_goals`, `team_resolution`, `cleaning_log`) to `data/clean/staging/`. `load_clean()` reads them back.
3. **Quality** (`quality/checks.py`): `CHECKS` list of `Check(name, dimension, table, severity, fn, tolerance)`; `fn(tables) -> (failed, total, details)`. A `critical` check over tolerance raises `QualityGateError` and blocks storage.
4. **Storage** (`storage/`): schema in `schema.py` (SQLAlchemy Core; `DATA_TABLES` = load order). `loader.run_storage` is a full reload in one transaction: drop views + data tables, recreate, insert, then execute `storage/views/*.sql` in filename order (later views depend on earlier ones, e.g. everything builds on `v_team_match`). Metadata tables (`dq_results`, `cleaning_log`, `etl_run_log`, `etl_table_stats`) are append-only history. `storage/db.py` forces explicit `BEGIN` on SQLite so DDL rolls back too.
5. **Analysis / app**: `football_pipeline/analysis/` holds pandas-side metrics (regressions, odds calibration, betting ROI, late-goal points). `app/common.py` puts the repo root on `sys.path`, auto-builds the DB on first launch (`ensure_database`), caches queries, and defines the chart palette; every page starts with `setup_page(...)`.

## Conventions and gotchas

- **Seasons** are the start year (2025 = 2025/26). `seasons: auto` in `config/settings.yaml` = last `n_seasons` *completed* seasons (`config.last_completed_seasons`, rollover on 1 July), so the analysed window depends on today's date. `PIPELINE_SEASONS=2023,2024` overrides it.
- `match_id = season*100000 + home_team_id*1000 + away_team_id*10 + is_playoff`; team ids come from the sorted canonical names in `team_aliases.yaml`, so editing that file can renumber ids (fine, because storage is a full reload).
- A repeated home/away pair in one season is marked `stage='PLAYOFF'` (Spezia–Verona 2022/23); all views filter `stage = 'REGULAR'`.
- `result` is always recomputed from the score; a source's own winner field is only used by the DQ check "Esito dichiarato coerente col punteggio".
- View SQL must stay portable between SQLite and PostgreSQL (`DATABASE_URL`): use `1.0 *` for decimal division, `CASE WHEN` instead of `FILTER`, no `::` casts, no `ROUND` inside views, and avoid reserved words as aliases.
- Transfermarkt changes formats between seasons (Italian-month vs numeric birth dates, new role names). Update `ROLE_MAP` / parsers in `cleaning/parsers.py`; the "Attributi giocatore validi" DQ check is what surfaces these.
- OddsPortal (`acquisition/oddsportal.py`) needs Selenium plus Chrome (or Firefox via `browser: firefox`). Headless Chrome needs the anti-automation flags already set there or the site serves a bot page. Pages must be changed by **clicking** the pagination buttons; navigating via `#/page/N/` is unreliable. `parse_match_text` handles both the current and the pre-2025 row layout.
- Secrets come from `.env` (`FOOTBALL_DATA_TOKEN`, `API_FOOTBALL_KEY`) or the legacy `psw/token.yml`; both are gitignored. football-data.org's free tier rejects 2022 with HTTP 403.
- Tests use the `sandbox` fixture (`tests/conftest.py`). It copies `data/raw` to a tmp dir, pins seasons to 2022–2025 and monkeypatches `get_settings` in `config`, `acquisition.base`, `cleaning.transform`, `quality.checks` and `storage.db`. Any new module that calls `get_settings` must be added there, or tests will write to the real `data/`.
- `legacy/` holds the original notebooks and SQL. Reference only; it is not used by the pipeline.

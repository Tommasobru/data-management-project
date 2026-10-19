import dataclasses
import shutil

import pytest

from football_pipeline import config
from football_pipeline.acquisition import base
from football_pipeline.cleaning import transform
from football_pipeline.quality import checks
from football_pipeline.storage import db, loader


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    """Copia i dati raw di seed in una cartella temporanea con un database SQLite dedicato."""
    real = config.get_settings()
    shutil.copytree(real.raw_dir, tmp_path / "raw")
    settings = dataclasses.replace(
        real,
        seasons=[2022, 2023, 2024, 2025],  # fisse: i test non dipendono dalla data odierna
        raw_dir=tmp_path / "raw",
        clean_dir=tmp_path / "clean",
        reports_dir=tmp_path / "reports",
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
    )
    for module in (config, base, transform, checks):
        monkeypatch.setattr(module, "get_settings", lambda: settings)
    monkeypatch.setattr(db, "get_settings", lambda: settings)
    db.get_engine.cache_clear()
    yield settings
    db.get_engine.cache_clear()

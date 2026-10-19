"""Funzioni condivise dalle pagine Streamlit."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from football_pipeline import analysis  # noqa: E402
from football_pipeline.storage import read_sql, table_exists  # noqa: E402

# Palette categoriale validata (ordine fisso, mai ciclato) + colori di contesto.
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
CONTEXT = "#c3c2b7"
POSITIVE, NEGATIVE = "#2a78d6", "#e34948"  # coppia divergente blu/rosso
STATUS = {"PASS": "#0ca30c", "WARN": "#fab219", "FAIL": "#d03b3b", "SKIP": "#898781"}
STATUS_ICON = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌", "SKIP": "➖"}
ROLE_ORDER = ["Portiere", "Difensore", "Centrocampista", "Attaccante"]


def setup_page(title: str, icon: str = "⚽") -> None:
    st.set_page_config(page_title=f"{title} · Serie A Data Hub", page_icon=icon, layout="wide")
    ensure_database()


def ensure_database() -> None:
    """Se il database non esiste lo costruisce dai dati raw (pipeline offline)."""
    if table_exists("v_standings"):
        return
    with st.spinner("Primo avvio: costruisco il data warehouse dai dati raw (clean → quality → store)…"):
        from football_pipeline.pipeline import run
        run(steps=["clean", "quality", "store"], force=True)
    st.cache_data.clear()


@st.cache_data(show_spinner=False)
def query(sql: str) -> pd.DataFrame:
    return read_sql(sql)


@st.cache_data(show_spinner=False)
def load_view(name: str) -> pd.DataFrame:
    return analysis.view(name)


@st.cache_data(show_spinner=False)
def cached(fn_name: str, *args):
    return getattr(analysis, fn_name)(*args)


def seasons() -> pd.DataFrame:
    return query("SELECT season_id, label FROM dim_season ORDER BY season_id")


def season_selector(key: str = "season", sidebar: bool = True, include_all: bool = False) -> tuple[int | None, str]:
    s = seasons()
    labels = list(s["label"])
    options = (["Tutte le stagioni"] if include_all else []) + labels[::-1]
    container = st.sidebar if sidebar else st
    choice = container.selectbox("Stagione", options, key=key)
    if choice == "Tutte le stagioni":
        return None, choice
    return int(s.loc[s["label"] == choice, "season_id"].iloc[0]), choice


def eur_m(value: float) -> str:
    return "-" if pd.isna(value) else f"€{value / 1e6:,.1f} mln".replace(",", "X").replace(".", ",").replace("X", ".")


def style_fig(fig, height: int = 420):
    has_title = bool(fig.layout.title.text)
    fig.update_layout(
        height=height, margin=dict(l=10, r=10, t=90 if has_title else 40, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0, title_text=""),
        hoverlabel=dict(namelength=-1),
    )
    if has_title:
        fig.update_layout(title=dict(y=0.98, yanchor="top", x=0, xanchor="left"))
    fig.update_xaxes(showgrid=False)
    return fig


def empty_state(source: str, command: str) -> None:
    st.info(
        f"Nessun dato da **{source}** nel database. "
        f"Per acquisirlo: `{command}` (richiede connessione internet), poi ricarica la pagina.",
        icon="ℹ️",
    )


def linear_fit_text(x: pd.Series, y: pd.Series) -> str:
    fit = analysis.linear_fit(x, y)
    if pd.isna(fit["r2"]):
        return "dati insufficienti"
    return f"R² = {fit['r2']:.2f}, pendenza {fit['slope']:.3f}"

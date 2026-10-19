import io
import logging

import pandas as pd
import streamlit as st

from common import setup_page
from football_pipeline.acquisition import SOURCES
from football_pipeline.config import get_secret, get_settings
from football_pipeline.quality import QualityGateError

setup_page("Aggiorna dati", "⚙️")
st.title("⚙️ Aggiorna dati")
st.caption("Lancia la pipeline dalla dashboard: acquisizione da API e web scraping, cleaning, "
           "Data Quality e caricamento nel database.")

settings = get_settings()
labels = [f"{s}/{(s + 1) % 100:02d}" for s in settings.seasons]
st.markdown(f"**Stagioni analizzate:** {', '.join(labels)} "
            "(configurabili in `config/settings.yaml`; con `seasons: auto` sono le ultime stagioni concluse).")

TOKENS = {"football_data_org": "FOOTBALL_DATA_TOKEN", "api_football": "API_FOOTBALL_KEY"}
rows = []
for name, cls in SOURCES.items():
    for dataset in cls.datasets:
        present = [s for s in settings.seasons if (settings.raw_dir / name / f"{dataset}_{s}.csv").exists()]
        token = TOKENS.get(name)
        rows.append({
            "Fonte": name,
            "Tipo": "API" if cls.kind == "api" else "Scraping",
            "Dataset": dataset,
            "Abilitata": "✅" if settings.source_enabled(name) else "➖",
            "Credenziali": ("✅" if get_secret(token) else "❌ manca " + token) if token else "non servono",
            "Stagioni in cache": f"{len(present)}/{len(settings.seasons)}",
            "Mancanti": ", ".join(str(s) for s in settings.seasons if s not in present) or "—",
        })
st.subheader("Stato delle fonti")
st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")

st.subheader("Esegui")
enabled = [n for n in SOURCES if settings.source_enabled(n)]
with st.form("run"):
    sources = st.multiselect("Fonti da interrogare", list(SOURCES), default=enabled)
    refresh = st.checkbox("Riscarica anche le stagioni già in cache", value=False,
                          help="Senza questa opzione vengono scaricate solo le stagioni mancanti.")
    force = st.checkbox("Carica anche se un controllo critico fallisce", value=False)
    skip_acquire = st.checkbox("Solo cleaning + quality + storage (nessuna richiesta di rete)", value=False)
    submitted = st.form_submit_button("▶️ Avvia pipeline", type="primary")

st.caption("Lo scraping completo di una stagione richiede alcuni minuti: Transfermarkt ~2 min "
           "(pause tra le richieste), OddsPortal ~1 min con il browser in background.")

if submitted:
    from football_pipeline.pipeline import run

    buffer = io.StringIO()
    handler = logging.StreamHandler(buffer)
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)-7s | %(message)s", "%H:%M:%S"))
    root = logging.getLogger()
    root.addHandler(handler)
    root.setLevel(logging.INFO)
    steps = ["clean", "quality", "store"] if skip_acquire else ["acquire", "clean", "quality", "store"]
    try:
        with st.status("Pipeline in esecuzione…", expanded=True) as status:
            st.write(" → ".join(steps))
            summary = run(steps=steps, refresh=refresh, sources=sources or None, force=force)
            status.update(label="Pipeline completata", state="complete")
        if "acquisition" in summary and not summary["acquisition"].empty:
            acq = summary["acquisition"]
            st.markdown("**Esito acquisizione**")
            st.dataframe(acq.rename(columns={"source": "Fonte", "dataset": "Dataset", "season": "Stagione",
                                             "status": "Esito", "rows": "Righe", "message": "Messaggio"}),
                         hide_index=True, width="stretch")
        st.success("Database aggiornato. Le altre pagine mostrano già i nuovi dati.")
        st.cache_data.clear()
    except QualityGateError as exc:
        st.error(f"Caricamento bloccato dalla Data Quality: {exc}")
    except Exception as exc:  # noqa: BLE001 - mostrato all'utente
        st.error(f"Errore: {exc}")
    finally:
        root.removeHandler(handler)
    with st.expander("Log dell'esecuzione"):
        st.code(buffer.getvalue() or "(vuoto)", language="text")

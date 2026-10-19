import plotly.express as px
import streamlit as st

from common import STATUS, STATUS_ICON, query, setup_page, style_fig

setup_page("Data Quality", "🧪")
st.title("🧪 Data Quality e lineage")

runs = query("SELECT DISTINCT run_id FROM dq_results ORDER BY run_id DESC")
if runs.empty:
    st.warning("Nessun report di qualità: lanciare `python main.py run`.")
    st.stop()
run_id = st.sidebar.selectbox("Esecuzione", runs["run_id"])
dq = query(f"SELECT * FROM dq_results WHERE run_id = '{run_id}'")

counts = dq["status"].value_counts()
cols = st.columns(4)
for col, status, label in zip(cols, ["PASS", "WARN", "FAIL", "SKIP"], ["Superati", "Avvisi", "Falliti", "Non applicabili"]):
    col.metric(f"{STATUS_ICON[status]} {label}", int(counts.get(status, 0)))

st.markdown(
    "Ogni controllo misura una dimensione di qualità e conta le righe che la violano. "
    "I controlli **critical** che falliscono bloccano il caricamento nel database; "
    "gli altri producono un avviso e vengono documentati qui."
)

by_dim = dq.groupby(["dimension", "status"]).size().reset_index(name="controlli")
fig = px.bar(by_dim, x="controlli", y="dimension", color="status", orientation="h",
             color_discrete_map=STATUS, category_orders={"status": ["PASS", "WARN", "FAIL", "SKIP"]},
             labels={"dimension": "", "controlli": "Numero di controlli", "status": "Esito"})
fig.update_traces(hovertemplate="%{y}: %{x} controlli<extra></extra>")
st.plotly_chart(style_fig(fig, 280), width="stretch")

dim = st.multiselect("Filtra per dimensione", sorted(dq["dimension"].unique()))
view = dq[dq["dimension"].isin(dim)] if dim else dq
view = view.assign(esito=view["status"].map(lambda s: f"{STATUS_ICON[s]} {s}"),
                   ordine=view["status"].map({"FAIL": 0, "WARN": 1, "PASS": 2, "SKIP": 3}))
st.dataframe(
    view.sort_values(["ordine", "dimension"])[["esito", "dimension", "check_name", "table_name", "severity",
                                              "failed", "total", "failed_pct", "details"]]
        .rename(columns={"esito": "Esito", "dimension": "Dimensione", "check_name": "Controllo",
                         "table_name": "Tabella", "severity": "Severità", "failed": "Violazioni",
                         "total": "Righe", "failed_pct": "%", "details": "Dettagli"}),
    hide_index=True, width="stretch",
    column_config={"%": st.column_config.NumberColumn(format="%.2f%%"),
                   "Dettagli": st.column_config.TextColumn(width="large")},
)

c1, c2 = st.columns(2)
with c1:
    st.subheader("Log del cleaning")
    log = query(f"SELECT table_name, action, rows_affected FROM cleaning_log WHERE run_id = '{run_id}' ORDER BY seq")
    st.dataframe(log.rename(columns={"table_name": "Tabella", "action": "Operazione", "rows_affected": "Righe"}),
                 hide_index=True, width="stretch")
with c2:
    st.subheader("Righe caricate per tabella")
    stats = query(f"SELECT table_name, rows FROM etl_table_stats WHERE run_id = '{run_id}' ORDER BY rows DESC")
    st.dataframe(stats.rename(columns={"table_name": "Tabella", "rows": "Righe"}), hide_index=True, width="stretch")

st.subheader("Storico delle esecuzioni")
history = query("SELECT run_id, started_at, finished_at, steps, status, message FROM etl_run_log ORDER BY run_id DESC LIMIT 20")
st.dataframe(history, hide_index=True, width="stretch")

with st.expander("Modello dati (schema a stella)"):
    st.graphviz_chart("""
    digraph {
        rankdir=LR; bgcolor="transparent";
        node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=10];
        node [fillcolor="#cde2fb", color="#2a78d6"]; dim_season; dim_team; dim_player;
        node [fillcolor="#f0efec", color="#898781"];
        fact_match; fact_goal; fact_odds; fact_match_stats; fact_match_xg; fact_team_season; fact_player_season; fact_team_elo;
        dim_season -> fact_match; dim_team -> fact_match;
        fact_match -> fact_goal; fact_match -> fact_odds; fact_match -> fact_match_stats; fact_match -> fact_match_xg;
        dim_player -> fact_goal; dim_team -> fact_goal;
        dim_season -> fact_team_season; dim_team -> fact_team_season;
        dim_season -> fact_player_season; dim_team -> fact_player_season; dim_player -> fact_player_season;
        dim_season -> fact_team_elo; dim_team -> fact_team_elo;
    }
    """)

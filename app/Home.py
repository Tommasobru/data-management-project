import pandas as pd
import streamlit as st

from common import query, setup_page
from football_pipeline.quality import CHECKS

setup_page("Home", "⚽")

st.title("⚽ Serie A Data Hub")
st.caption(
    "Progetto di Data Management: dati di più fonti (API e web scraping) integrati in un unico "
    "data warehouse, verificati con controlli di Data Quality e analizzati in questa dashboard."
)

kpi = query("""
    SELECT (SELECT COUNT(*) FROM dim_season) AS seasons,
           (SELECT COUNT(*) FROM fact_match) AS matches,
           (SELECT COUNT(*) FROM fact_goal) AS goals,
           (SELECT COUNT(*) FROM dim_player) AS players,
           (SELECT COUNT(*) FROM dim_team) AS teams,
           (SELECT COUNT(*) FROM fact_odds) AS odds
""").iloc[0]
cols = st.columns(6)
for col, (label, value) in zip(cols, [
    ("Stagioni", kpi.seasons), ("Partite", kpi.matches), ("Gol tracciati", kpi.goals),
    ("Giocatori", kpi.players), ("Squadre", kpi.teams), ("Quote 1X2", kpi.odds),
]):
    col.metric(label, f"{int(value):,}".replace(",", "."))

st.subheader("Albo d'oro del periodo")
champions = query("""
    SELECT s.season, s.team AS campione, s.points AS punti,
           r.team AS seconda, r.points AS punti_seconda,
           sc.scorer AS capocannoniere, sc.goals AS gol
    FROM v_standings s
    JOIN v_standings r ON r.season_id = s.season_id AND r.position = 2
    LEFT JOIN (
        SELECT season_id, scorer, goals,
               ROW_NUMBER() OVER (PARTITION BY season_id ORDER BY goals DESC) AS rn
        FROM v_top_scorers
    ) sc ON sc.season_id = s.season_id AND sc.rn = 1
    WHERE s.position = 1
    ORDER BY s.season_id DESC
""")
champions.columns = ["Stagione", "Campione", "Punti", "Seconda", "Punti seconda", "Capocannoniere", "Gol"]
st.dataframe(champions, hide_index=True, width="stretch")
st.caption("Punti calcolati sul campo: eventuali penalizzazioni (es. Juventus 2022/23, −10) non sono incluse.")

st.subheader("Architettura della pipeline")
st.graphviz_chart("""
    digraph {
        rankdir=LR; bgcolor="transparent"; nodesep=0.15; ranksep=0.5;
        node [shape=box, style="rounded,filled", fillcolor="#cde2fb", color="#2a78d6", fontname="Helvetica", fontsize=13];
        edge [color="#898781"];
        subgraph cluster_src { label="1 · Acquisizione"; fontname="Helvetica"; color="#c3c2b7";
            api1 [label="football-data.org\\n(API)"]; api2 [label="API-Football\\n(API)"]; api3 [label="ClubElo\\n(API)"];
            sc1 [label="Transfermarkt\\n(scraping)"]; sc2 [label="OddsPortal\\n(scraping)"];
            sc3 [label="football-data.co.uk\\n(open data)"]; sc4 [label="Understat\\n(scraping)"]; }
        raw [label="data/raw\\nCSV per fonte/stagione", fillcolor="#f0efec", color="#898781"];
        clean [label="2 · Cleaning\\nnomi canonici, tipi,\\ndeduplica, match_id"];
        dq [label="3 · Data Quality\\n%d controlli", fillcolor="#fde7c0", color="#eda100"];
        dwh [label="4 · Storage\\nschema a stella\\n+ 16 viste SQL", fillcolor="#b7d3f6"];
        app [label="5 · Analisi\\nStreamlit", fillcolor="#d4f2e6", color="#1baf7a"];
        {api1 api2 api3 sc1 sc2 sc3 sc4} -> raw -> clean -> dq -> dwh -> app;
    }
    """ % len(CHECKS))
st.subheader("Fonti dati")
sources = query("""
    SELECT 'football-data.org' AS fonte, 'API' AS tipo, 'Risultati e primo tempo' AS contenuto
    UNION ALL SELECT 'API-Football', 'API', 'Risultati e primo tempo'
    UNION ALL SELECT 'ClubElo', 'API', 'Rating Elo'
    UNION ALL SELECT 'Transfermarkt', 'Scraping', 'Rose, valori, marcatori'
    UNION ALL SELECT 'OddsPortal', 'Scraping', 'Quote 1X2'
    UNION ALL SELECT 'football-data.co.uk', 'Open data', 'Tiri, cartellini, arbitri, quote'
    UNION ALL SELECT 'Understat', 'Scraping', 'Expected goals (xG)'
""")
loaded = query("""
    SELECT 'ClubElo' AS fonte, COUNT(*) AS righe FROM fact_team_elo
    UNION ALL SELECT 'football-data.co.uk', COUNT(*) FROM fact_match_stats
    UNION ALL SELECT 'Understat', COUNT(*) FROM fact_match_xg
    UNION ALL SELECT 'OddsPortal', COUNT(*) FROM fact_odds WHERE source = 'oddsportal'
    UNION ALL SELECT 'Transfermarkt', COUNT(*) FROM fact_player_season
    UNION ALL SELECT 'API-Football', COUNT(*) FROM fact_match WHERE source = 'api_football'
    UNION ALL SELECT 'football-data.org', COUNT(*) FROM fact_match WHERE source = 'football_data_org'
""")
sources = sources.merge(loaded, on="fonte", how="left")
sources["stato"] = sources["righe"].map(lambda n: "✅ caricata" if n else "➖ da acquisire")
st.dataframe(sources[["fonte", "tipo", "contenuto", "stato"]]
             .rename(columns={"fonte": "Fonte", "tipo": "Tipo", "contenuto": "Contenuto", "stato": "Stato"}),
             hide_index=True, width="stretch")

st.subheader("Cosa trovi nella dashboard")
st.markdown("""
| Pagina | Domande a cui risponde |
|---|---|
| 🏆 **Classifiche** | Chi ha vinto e come? Quanto pesa il fattore campo? |
| ⏱️ **Gol e momenti** | Chi rimonta nel secondo tempo? Quando si segna? Chi decide le partite nel finale? |
| 💰 **Valore di mercato** | Spendere di più significa vincere di più? Quali squadre e giocatori si sono rivalutati? |
| 🎲 **Quote e pronostici** | Quanto sono affidabili i bookmaker? Quali squadre hanno sorpreso? Esiste una strategia che vince? |
| 📈 **Statistiche avanzate** | xG, rating Elo, tiri e arbitri (fonti aggiuntive) |
| 🧪 **Data Quality** | Esito dei controlli, log del cleaning e storico delle esecuzioni |
| ⚙️ **Aggiorna dati** | Stato delle fonti e avvio della pipeline (API + web scraping) dalla dashboard |
""")

last = query("SELECT run_id, status, finished_at FROM etl_run_log ORDER BY run_id DESC LIMIT 1")
if not last.empty:
    r = last.iloc[0]
    st.caption(f"Ultima esecuzione della pipeline: `{r.run_id}` — {r.status} ({pd.to_datetime(r.finished_at):%d/%m/%Y %H:%M})")

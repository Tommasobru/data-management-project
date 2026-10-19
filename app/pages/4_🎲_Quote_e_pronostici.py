import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from common import CONTEXT, NEGATIVE, POSITIVE, SERIES, cached, load_view, season_selector, setup_page, style_fig

setup_page("Quote e pronostici", "🎲")
season_id, label = season_selector(include_all=True)
st.title(f"🎲 Quote e pronostici — {label}")

odds = load_view("v_match_odds")
if season_id is not None:
    odds = odds[odds["season_id"] == season_id]
if odds.empty:
    st.warning("Nessuna quota disponibile per la selezione.")
    st.stop()

fav_rate = (odds["favourite"] == odds["result"]).mean()
c1, c2, c3, c4 = st.columns(4)
c1.metric("Partite con quote", len(odds))
c2.metric("Il favorito vince", f"{100 * fav_rate:.1f}%")
c3.metric("Probabilità media del favorito", f"{100 * odds[['p_home', 'p_draw', 'p_away']].max(axis=1).mean():.1f}%")
c4.metric("Margine medio bookmaker", f"{100 * odds['margin'].mean():.1f}%")

# ---------------------------------------------------------------- calibrazione
st.subheader("Le quote sono affidabili?")
cal = cached("calibration")
fig = go.Figure()
fig.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode="lines", line=dict(color=CONTEXT, dash="dash"),
                         name="Calibrazione perfetta", hoverinfo="skip"))
fig.add_trace(go.Scatter(x=cal["prob_media"], y=cal["freq_reale"], mode="lines+markers", name="Quote",
                         line=dict(color=SERIES[0], width=2), marker=dict(size=10, line=dict(width=2, color="white")),
                         customdata=cal["eventi"],
                         hovertemplate="Probabilità implicita %{x:.0%}<br>Frequenza reale %{y:.0%}<br>%{customdata} esiti<extra></extra>"))
fig.update_xaxes(title="Probabilità implicita nella quota", tickformat=".0%", range=[0, 1])
fig.update_yaxes(title="Frequenza osservata", tickformat=".0%", range=[0, 1])
c1, c2 = st.columns([3, 2])
c1.plotly_chart(style_fig(fig, 420), width="stretch")
c2.markdown(
    "Ogni punto raggruppa gli esiti (1, X, 2) di tutte le partite con probabilità implicita simile, "
    "calcolata come `1/quota` normalizzata per togliere il margine del bookmaker.\n\n"
    "Se i punti stanno sulla diagonale le quote sono **ben calibrate**: un evento quotato al 40% "
    "accade davvero circa 4 volte su 10."
)
c2.caption("Grafico calcolato su tutte le stagioni.")

# ---------------------------------------------------------------- punti attesi
st.subheader("Sorprese e delusioni rispetto alle attese dei bookmaker")
xp = load_view("v_team_expected_points")
if season_id is not None:
    xp = xp[xp["season_id"] == season_id]
xp = xp.assign(etichetta=xp["team"] + (" " + xp["season"].str[-5:] if season_id is None else ""))
xp = xp.sort_values("points_over_expected")
show = xp if season_id is not None else xp.iloc[list(range(8)) + list(range(len(xp) - 8, len(xp)))]
fig = px.bar(show, x="points_over_expected", y="etichetta", orientation="h",
             color=show["points_over_expected"].map(lambda v: "Meglio delle attese" if v >= 0 else "Peggio delle attese"),
             color_discrete_map={"Meglio delle attese": POSITIVE, "Peggio delle attese": NEGATIVE},
             custom_data=["expected_points", "points"],
             labels={"points_over_expected": "Punti reali − punti attesi dalle quote", "etichetta": ""})
fig.update_traces(hovertemplate="%{y}<br>Attesi %{customdata[0]:.1f} · reali %{customdata[1]}<br>Differenza %{x:+.1f}<extra></extra>")
st.plotly_chart(style_fig(fig, max(400, 22 * len(show))), width="stretch")
st.caption("Punti attesi per partita = 3 × P(vittoria) + 1 × P(pareggio), con le probabilità implicite nelle quote di chiusura.")

# ---------------------------------------------------------------- strategie
st.subheader("Esiste una strategia che batte il bookmaker?")
strat = cached("betting_strategies")
if season_id is not None:
    strat = strat[strat["stagione"] == label]
summary = strat.groupby("strategia", as_index=False).agg(partite=("partite", "sum"), profitto=("profitto", "sum"))
summary["roi_pct"] = 100 * summary["profitto"] / summary["partite"]
summary = summary.sort_values("roi_pct")
fig = px.bar(summary, x="roi_pct", y="strategia", orientation="h",
             color=summary["roi_pct"].map(lambda v: "Guadagno" if v >= 0 else "Perdita"),
             color_discrete_map={"Guadagno": POSITIVE, "Perdita": NEGATIVE},
             custom_data=["profitto", "partite"], labels={"roi_pct": "ROI %", "strategia": ""})
fig.update_traces(hovertemplate="%{y}<br>ROI %{x:.1f}%<br>Profitto €%{customdata[0]:.0f} su %{customdata[1]} puntate da 1€<extra></extra>")
c1, c2 = st.columns([3, 2])
c1.plotly_chart(style_fig(fig, 320), width="stretch")
c2.markdown("Simulazione con puntata fissa di **1 €** su ogni partita. Un ROI negativo vicino al margine "
            "del bookmaker indica che il mercato è efficiente: nessuna regola semplice è profittevole nel lungo periodo.")

st.subheader("Le sorprese più grandi")
up = cached("biggest_upsets", 5000)
if season_id is not None:
    up = up[up["season_id"] == season_id]
up = up.head(15)
up = up.assign(partita=up["home_team"] + " – " + up["away_team"],
               risultato=up["home_goals"].astype(str) + "-" + up["away_goals"].astype(str))
st.dataframe(
    up[["season", "match_date", "partita", "risultato", "quota_esito", "prob_esito"]]
      .rename(columns={"season": "Stagione", "match_date": "Data", "partita": "Partita", "risultato": "Risultato",
                       "quota_esito": "Quota dell'esito", "prob_esito": "Probabilità implicita"}),
    hide_index=True, width="stretch",
    column_config={"Probabilità implicita": st.column_config.NumberColumn(format="percent"),
                   "Data": st.column_config.DateColumn(format="DD/MM/YYYY")},
)

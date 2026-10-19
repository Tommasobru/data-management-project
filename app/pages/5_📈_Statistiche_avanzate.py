import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from common import CONTEXT, NEGATIVE, POSITIVE, SERIES, empty_state, linear_fit_text, load_view, season_selector, setup_page, style_fig

setup_page("Statistiche avanzate", "📈")
season_id, label = season_selector()
st.title(f"📈 Statistiche avanzate — {label}")
st.caption("Dati dalle fonti aggiuntive gratuite: Understat (xG), ClubElo (rating) e football-data.co.uk "
           "(tiri, cartellini, arbitri).")

tab_xg, tab_elo, tab_stats = st.tabs(["Expected goals", "Rating Elo", "Tiri e disciplina"])

with tab_xg:
    xg = load_view("v_team_xg").query("season_id == @season_id")
    if xg.empty:
        empty_state("Understat", "python main.py acquire --sources understat && python main.py run --offline")
    else:
        xg = xg.assign(xg_diff=xg["xg_for"] - xg["xg_against"],
                       finishing=xg["goals_for"] - xg["xg_for"],
                       keeping=xg["xg_against"] - xg["goals_against"])
        fig = go.Figure()
        lo, hi = xg[["xg_for", "goals_for"]].min().min() * 0.9, xg[["xg_for", "goals_for"]].max().max() * 1.05
        fig.add_trace(go.Scatter(x=[lo, hi], y=[lo, hi], mode="lines", line=dict(color=CONTEXT, dash="dash"),
                                 name="Gol = xG", hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=xg["xg_for"], y=xg["goals_for"], mode="markers+text", text=xg["team"],
                                 textposition="top center", name="Squadre",
                                 marker=dict(size=10, color=SERIES[0], line=dict(width=2, color="white")),
                                 hovertemplate="%{text}<br>xG %{x:.1f} · gol %{y}<extra></extra>"))
        fig.update_xaxes(title="Expected goals (xG) prodotti")
        fig.update_yaxes(title="Gol segnati")
        st.plotly_chart(style_fig(fig, 480), width="stretch")
        st.caption("Sopra la diagonale: squadre che hanno finalizzato meglio della qualità delle occasioni create.")
        fit = linear_fit_text(xg["xg_diff"], xg["points"])
        st.markdown(f"**Differenza xG vs punti in classifica** — {fit}")
        st.dataframe(xg.sort_values("points", ascending=False)[
            ["team", "points", "goals_for", "xg_for", "goals_against", "xg_against", "finishing", "keeping"]]
            .rename(columns={"team": "Squadra", "points": "Punti", "goals_for": "GF", "xg_for": "xG",
                             "goals_against": "GS", "xg_against": "xGA", "finishing": "GF − xG", "keeping": "xGA − GS"}),
            hide_index=True, width="stretch",
            column_config={c: st.column_config.NumberColumn(format="%.1f") for c in ["xG", "xGA", "GF − xG", "xGA − GS"]})

with tab_elo:
    elo = load_view("v_team_elo").query("season_id == @season_id")
    if elo.empty:
        empty_state("ClubElo", "python main.py acquire --sources clubelo && python main.py run --offline")
    else:
        fig = px.scatter(elo, x="elo_start", y="points", text="team", color_discrete_sequence=[SERIES[0]],
                         labels={"elo_start": "Elo a inizio stagione", "points": "Punti finali"})
        fig.update_traces(textposition="top center", marker=dict(size=10, line=dict(width=2, color="white")),
                          hovertemplate="%{text}<br>Elo %{x:.0f} · %{y} punti<extra></extra>")
        st.plotly_chart(style_fig(fig, 460), width="stretch")
        st.markdown(f"**Elo iniziale vs punti** — {linear_fit_text(elo['elo_start'], elo['points'])}")
        change = elo.dropna(subset=["elo_change"]).sort_values("elo_change")
        fig = px.bar(change, x="elo_change", y="team", orientation="h",
                     color=change["elo_change"].map(lambda v: "Crescita" if v >= 0 else "Calo"),
                     color_discrete_map={"Crescita": POSITIVE, "Calo": NEGATIVE},
                     labels={"elo_change": "Variazione Elo nella stagione", "team": ""})
        st.plotly_chart(style_fig(fig, max(400, 22 * len(change))), width="stretch")

with tab_stats:
    stats = load_view("v_team_match_stats").query("season_id == @season_id")
    if stats.empty:
        empty_state("football-data.co.uk", "python main.py acquire --sources football_data_couk && python main.py run --offline")
    else:
        stats = stats.assign(conversion=100 * stats["goals_for"] / stats["shots"],
                             accuracy=100 * stats["shots_on_target"] / stats["shots"])
        fig = px.scatter(stats, x="shots", y="goals_for", text="team", color_discrete_sequence=[SERIES[0]],
                         labels={"shots": "Tiri totali", "goals_for": "Gol"})
        fig.update_traces(textposition="top center", marker=dict(size=10, line=dict(width=2, color="white")),
                          hovertemplate="%{text}<br>%{x} tiri · %{y} gol<extra></extra>")
        st.plotly_chart(style_fig(fig, 440), width="stretch")
        st.dataframe(stats.sort_values("points", ascending=False)[
            ["team", "points", "shots", "shots_on_target", "accuracy", "conversion", "corners", "fouls", "yellow_cards", "red_cards"]]
            .rename(columns={"team": "Squadra", "points": "Punti", "shots": "Tiri", "shots_on_target": "In porta",
                             "accuracy": "% in porta", "conversion": "% conversione", "corners": "Corner",
                             "fouls": "Falli", "yellow_cards": "Gialli", "red_cards": "Rossi"}),
            hide_index=True, width="stretch",
            column_config={c: st.column_config.NumberColumn(format="%.1f%%") for c in ["% in porta", "% conversione"]})
        st.subheader("Arbitri")
        refs = load_view("v_referee_stats").query("matches >= 10").sort_values("yellow_per_match", ascending=False)
        st.dataframe(refs.rename(columns={"referee": "Arbitro", "matches": "Partite", "yellow_per_match": "Gialli/partita",
                                          "red_per_match": "Rossi/partita", "fouls_per_match": "Falli/partita",
                                          "home_win_pct": "% vittorie casa"}),
                     hide_index=True, width="stretch",
                     column_config={c: st.column_config.NumberColumn(format="%.2f") for c in ["Gialli/partita", "Rossi/partita", "Falli/partita"]}
                     | {"% vittorie casa": st.column_config.NumberColumn(format="%.1f%%")})
        st.caption("Arbitri con almeno 10 partite, su tutte le stagioni caricate.")

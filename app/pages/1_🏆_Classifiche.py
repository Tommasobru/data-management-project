import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from common import CONTEXT, SERIES, load_view, season_selector, setup_page, style_fig

setup_page("Classifiche", "🏆")
season_id, label = season_selector()

st.title(f"🏆 Classifica Serie A {label}")

standings = load_view("v_standings").query("season_id == @season_id").sort_values("position")
table = standings[["position", "team", "points", "played", "wins", "draws", "losses",
                   "goals_for", "goals_against", "goal_difference", "home_points", "away_points"]]
table.columns = ["Pos", "Squadra", "Pt", "G", "V", "N", "P", "GF", "GS", "DR", "Pt casa", "Pt trasf."]
st.dataframe(
    table, hide_index=True, width="stretch", height=740,
    column_config={"Pt": st.column_config.ProgressColumn("Pt", format="%d", min_value=0,
                                                        max_value=int(table["Pt"].max()))},
)

st.subheader("Andamento dei punti giornata per giornata")
progression = load_view("v_points_progression").query("season_id == @season_id")
top3 = list(standings["team"].head(3))
highlight = st.multiselect("Squadre evidenziate (max 4)", sorted(progression["team"].unique()),
                           default=top3, max_selections=4)
fig = go.Figure()
for team, g in progression.groupby("team"):
    if team in highlight:
        continue
    fig.add_trace(go.Scatter(x=g["game_no"], y=g["cumulative_points"], mode="lines", name=team,
                             line=dict(color=CONTEXT, width=1), opacity=0.6, showlegend=False,
                             hovertemplate=f"{team}<br>Partita %{{x}}: %{{y}} pt<extra></extra>"))
for i, team in enumerate(highlight):
    g = progression[progression["team"] == team]
    fig.add_trace(go.Scatter(
        x=g["game_no"], y=g["cumulative_points"], mode="lines", name=team,
        line=dict(color=SERIES[i], width=2.5),
        customdata=g[["opponent", "venue", "outcome"]],
        hovertemplate=f"<b>{team}</b><br>Partita %{{x}} vs %{{customdata[0]}} (%{{customdata[1]}}): "
                      "%{customdata[2]}<br>Punti: %{y}<extra></extra>",
    ))
fig.update_xaxes(title="Partite giocate", range=[0, 39])
fig.update_yaxes(title="Punti cumulati")
st.plotly_chart(style_fig(fig, 480), width="stretch")

st.subheader("Fattore campo")
c1, c2 = st.columns(2)
home = load_view("v_home_advantage")
long = home.melt(id_vars="season", value_vars=["home_win_pct", "draw_pct", "away_win_pct"],
                 var_name="esito", value_name="pct")
long["esito"] = long["esito"].map({"home_win_pct": "Vittoria casa", "draw_pct": "Pareggio",
                                   "away_win_pct": "Vittoria trasferta"})
fig = px.bar(long, x="season", y="pct", color="esito", barmode="group",
             color_discrete_sequence=SERIES, labels={"season": "Stagione", "pct": "% partite"},
             title="Esiti per stagione")
fig.update_traces(hovertemplate="%{x}: %{y:.1f}%<extra></extra>")
c1.plotly_chart(style_fig(fig, 380), width="stretch")

split = standings.assign(diff=standings["home_points"] - standings["away_points"]).sort_values("diff")
fig = px.bar(split, x="diff", y="team", orientation="h",
             color=split["diff"].map(lambda d: "Più forte in casa" if d >= 0 else "Più forte in trasferta"),
             color_discrete_map={"Più forte in casa": SERIES[0], "Più forte in trasferta": SERIES[1]},
             labels={"diff": "Punti casa − punti trasferta", "team": ""},
             title=f"Dipendenza dal fattore campo {label}")
fig.update_traces(hovertemplate="%{y}: %{x:+d} pt<extra></extra>")
c2.plotly_chart(style_fig(fig, 520), width="stretch")
h = home.query("season_id == @season_id").iloc[0]
st.caption(f"Nel {label} la squadra di casa ha vinto il {h.home_win_pct:.1f}% delle partite "
           f"(trasferta {h.away_win_pct:.1f}%), con {h.avg_total_goals:.2f} gol medi a partita.")

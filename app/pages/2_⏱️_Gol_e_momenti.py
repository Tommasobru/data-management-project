import plotly.express as px
import streamlit as st

from common import NEGATIVE, POSITIVE, SERIES, cached, load_view, season_selector, setup_page, style_fig

setup_page("Gol e momenti", "⏱️")
season_id, label = season_selector(include_all=True)
st.title(f"⏱️ Gol e momenti della partita — {label}")

def by_season(df):
    return df if season_id is None else df[df["season_id"] == season_id]

# ---------------------------------------------------------------- primo vs secondo tempo
st.subheader("Se le partite finissero all'intervallo…")
st.caption("Punti reali meno punti che ogni squadra avrebbe ottenuto con il risultato del primo tempo: "
           "valori positivi = squadre che crescono nella ripresa.")
hf = by_season(load_view("v_half_vs_full"))
agg = hf.groupby("team", as_index=False)[["points_if_ht", "points", "second_half_delta",
                                         "comeback_wins", "comeback_draws", "leads_lost"]].sum()
agg = agg.sort_values("second_half_delta")
fig = px.bar(agg, x="second_half_delta", y="team", orientation="h",
             color=agg["second_half_delta"].map(lambda d: "Guadagna nel 2° tempo" if d >= 0 else "Perde nel 2° tempo"),
             color_discrete_map={"Guadagna nel 2° tempo": POSITIVE, "Perde nel 2° tempo": NEGATIVE},
             custom_data=["points_if_ht", "points"],
             labels={"second_half_delta": "Punti guadagnati/persi nel secondo tempo", "team": ""})
fig.update_traces(hovertemplate="%{y}: %{x:+d} pt<br>Classifica all'intervallo: %{customdata[0]} → reale: %{customdata[1]}<extra></extra>")
c1, c2 = st.columns([3, 2])
c1.plotly_chart(style_fig(fig, max(420, 22 * len(agg))), width="stretch")
c2.markdown("**Rimonte e vantaggi sprecati**")
c2.dataframe(
    agg.sort_values("comeback_wins", ascending=False)[["team", "comeback_wins", "comeback_draws", "leads_lost"]]
       .rename(columns={"team": "Squadra", "comeback_wins": "Rimonte vinte", "comeback_draws": "Rimonte al pari",
                        "leads_lost": "Vantaggi sprecati"}),
    hide_index=True, width="stretch", height=max(420, 22 * len(agg)),
)

# ---------------------------------------------------------------- distribuzione minuti
st.subheader("Quando si segna")
goals = by_season(load_view("v_goal_events"))
bands = goals.groupby("minute_band").size().reset_index(name="gol")
fig = px.bar(bands, x="minute_band", y="gol", color_discrete_sequence=[SERIES[0]],
             labels={"minute_band": "Fascia di minuti", "gol": "Gol"})
fig.update_traces(hovertemplate="%{x}': %{y} gol<extra></extra>")
c1, c2 = st.columns(2)
c1.plotly_chart(style_fig(fig, 360), width="stretch")
c1.caption("Le fasce 31-45+ e 76-90+ includono il recupero.")

late = cached("late_goal_points")
if season_id is not None and not late.empty:
    late = late[late["season"] == label]
if late.empty:
    c2.info("Nessun gol dall'85' disponibile per la selezione.")
    st.stop()
late = late.groupby("team", as_index=False)[["punti_guadagnati", "punti_persi", "saldo"]].sum().sort_values("saldo")
fig = px.bar(late, x="saldo", y="team", orientation="h",
             color=late["saldo"].map(lambda d: "Saldo positivo" if d >= 0 else "Saldo negativo"),
             color_discrete_map={"Saldo positivo": POSITIVE, "Saldo negativo": NEGATIVE},
             custom_data=["punti_guadagnati", "punti_persi"],
             labels={"saldo": "Saldo punti con gol dall'85'", "team": ""}, title="Zona Cesarini")
fig.update_traces(hovertemplate="%{y}: saldo %{x:+d}<br>guadagnati %{customdata[0]}, persi %{customdata[1]}<extra></extra>")
c2.plotly_chart(style_fig(fig, max(360, 20 * len(late))), width="stretch")

# ---------------------------------------------------------------- marcatori
st.subheader("Classifica marcatori")
scorers = by_season(load_view("v_top_scorers"))
top = (scorers.groupby(["scorer", "team"], as_index=False)
              .agg(goals=("goals", "sum"), market_value_eur=("market_value_eur", "max"), role=("role", "first"))
              .sort_values("goals", ascending=False).head(20))
top["value_per_goal"] = top["market_value_eur"] / top["goals"] / 1e6
top["market_value_eur"] = top["market_value_eur"] / 1e6
st.dataframe(
    top.rename(columns={"scorer": "Giocatore", "team": "Squadra", "goals": "Gol", "role": "Ruolo",
                        "market_value_eur": "Valore di mercato", "value_per_goal": "Valore per gol"}),
    hide_index=True, width="stretch",
    column_config={
        "Gol": st.column_config.ProgressColumn("Gol", format="%d", min_value=0, max_value=int(top["goals"].max())),
        "Valore di mercato": st.column_config.NumberColumn(format="€%.1f M"),
        "Valore per gol": st.column_config.NumberColumn(format="€%.2f M"),
    },
)
st.caption("Fonte: Transfermarkt (marcatori per giornata). Autogol esclusi. Il controllo di Data Quality "
           "'Copertura gol per partita' indica quanti gol mancano nello scraping.")

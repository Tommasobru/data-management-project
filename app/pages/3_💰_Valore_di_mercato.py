import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from common import (
    CONTEXT, NEGATIVE, POSITIVE, ROLE_ORDER, SERIES, cached, load_view, season_selector,
    setup_page, style_fig,
)

setup_page("Valore di mercato", "💰")
season_id, label = season_selector(include_all=True)
st.title(f"💰 Valore di mercato e rendimento — {label}")

# ---------------------------------------------------------------- valore vs punti
df, fit = cached("value_vs_points", season_id)
st.subheader("Spendere di più significa vincere di più?")
c1, c2, c3 = st.columns(3)
c1.metric("R² punti ~ log(valore rosa)", f"{fit['r2']:.2f}")
c2.metric("Punti in più ogni raddoppio del valore", f"{fit['slope'] * np.log10(2):.1f}")
c3.metric("Squadre analizzate", len(df))
st.caption("Un R² vicino a 1 indica che il valore della rosa spiega quasi tutta la classifica. "
           "Si usa il logaritmo del valore perché il rendimento cresce meno che proporzionalmente.")

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=df["value_m"], y=df["points"], mode="markers",
    marker=dict(size=10, color=SERIES[0], line=dict(width=2, color="white")),
    customdata=df[["team", "season", "position", "expected_by_value"]],
    hovertemplate="<b>%{customdata[0]}</b> %{customdata[1]}<br>Valore rosa: €%{x:.0f} mln<br>"
                  "Punti: %{y} (%{customdata[2]}° posto)<br>Attesi dal valore: %{customdata[3]:.0f}<extra></extra>",
    name="Squadra-stagione",
))
xs = np.linspace(df["log_value"].min(), df["log_value"].max(), 50)
fig.add_trace(go.Scatter(x=10 ** xs / 1e6, y=fit["slope"] * xs + fit["intercept"], mode="lines",
                         line=dict(color=CONTEXT, width=2, dash="dash"), name="Tendenza", hoverinfo="skip"))
for _, r in df.reindex(df["over_performance"].abs().sort_values(ascending=False).index).head(6).iterrows():
    fig.add_annotation(x=np.log10(r["value_m"]), y=r["points"], text=f"{r['team']} {r['season'][-5:]}",
                       showarrow=False, yshift=12, font=dict(size=11))
ticks = [20, 50, 100, 200, 500, 1000]
fig.update_xaxes(type="log", title="Valore rosa (milioni €, scala log)", tickvals=ticks, ticktext=[f"€{t}M" for t in ticks])
fig.update_yaxes(title="Punti")
st.plotly_chart(style_fig(fig, 480), width="stretch")

over = df.sort_values("over_performance")
over["etichetta"] = over["team"] + " " + over["season"].str[-5:]
show = over if season_id is not None else over.iloc[np.r_[0:8, -8:0]]
fig = px.bar(show, x="over_performance", y="etichetta", orientation="h",
             color=show["over_performance"].map(lambda v: "Sopra le attese" if v >= 0 else "Sotto le attese"),
             color_discrete_map={"Sopra le attese": POSITIVE, "Sotto le attese": NEGATIVE},
             labels={"over_performance": "Punti reali − punti attesi dal valore della rosa", "etichetta": ""},
             title="Chi ha fatto meglio (o peggio) di quanto valeva la rosa")
fig.update_traces(hovertemplate="%{y}: %{x:+.1f} pt<extra></extra>")
st.plotly_chart(style_fig(fig, max(380, 22 * len(show))), width="stretch")

# ---------------------------------------------------------------- crescita valore rose
st.subheader("Rivalutazione delle rose")
growth = load_view("v_squad_value_growth").query("seasons >= 2").sort_values("growth_pct")
fig = px.bar(growth, x="growth_pct", y="team", orientation="h",
             color=growth["growth_pct"].map(lambda v: "Crescita" if v >= 0 else "Calo"),
             color_discrete_map={"Crescita": POSITIVE, "Calo": NEGATIVE},
             custom_data=["first_season", "last_season", "first_value", "last_value"],
             labels={"growth_pct": "Variazione % valore rosa", "team": ""})
fig.update_traces(hovertemplate="%{y}: %{x:+.1f}%<br>%{customdata[0]}: €%{customdata[2]:,.0f}<br>"
                                "%{customdata[1]}: €%{customdata[3]:,.0f}<extra></extra>")
st.plotly_chart(style_fig(fig, max(400, 22 * len(growth))), width="stretch")
st.caption("Confronto tra la prima e l'ultima stagione in Serie A nel periodo analizzato (almeno due stagioni).")

# ---------------------------------------------------------------- giocatori
st.subheader("Giocatori: chi si è rivalutato di più")
pg = load_view("v_player_value_growth")
c1, c2 = st.columns([1, 3])
roles = c1.multiselect("Ruolo", ROLE_ORDER, default=ROLE_ORDER)
min_value = c1.slider("Valore iniziale minimo (mln €)", 0.0, 20.0, 1.0, 0.5)
sort = c1.radio("Ordina per", ["Crescita assoluta (€)", "Crescita %"])
pg = pg[pg["role_group"].isin(roles) & (pg["first_value"] >= min_value * 1e6)]
pg = pg.sort_values("value_delta" if sort.startswith("Crescita assoluta") else "growth_pct", ascending=False)
pg = pg.assign(**{c: pg[c] / 1e6 for c in ["first_value", "last_value", "value_delta"]})
c2.dataframe(
    pg.head(25)[["player_name", "role", "first_team", "last_team", "first_season", "last_season",
                 "first_age", "first_value", "last_value", "value_delta", "growth_pct"]]
      .rename(columns={"player_name": "Giocatore", "role": "Ruolo", "first_team": "Squadra iniziale",
                       "last_team": "Squadra finale", "first_season": "Da", "last_season": "A",
                       "first_age": "Età iniziale", "first_value": "Valore iniziale",
                       "last_value": "Valore finale", "value_delta": "Δ valore", "growth_pct": "Δ %"}),
    hide_index=True, width="stretch",
    column_config={c: st.column_config.NumberColumn(format="€%.1f M") for c in ["Valore iniziale", "Valore finale", "Δ valore"]}
    | {"Δ %": st.column_config.NumberColumn(format="%.0f%%"), "Da": st.column_config.NumberColumn(format="%d"),
       "A": st.column_config.NumberColumn(format="%d")},
)

st.subheader("Curva età–valore per ruolo")
curve = cached("age_value_curve")
curve = curve.assign(valore_mediano=curve["valore_mediano"] / 1e6)
fig = px.line(curve, x="age", y="valore_mediano", color="role_group", category_orders={"role_group": ROLE_ORDER},
              color_discrete_sequence=SERIES, markers=True, custom_data=["giocatori"],
              labels={"age": "Età", "valore_mediano": "Valore mediano (milioni €)", "role_group": "Ruolo"})
fig.update_traces(line=dict(width=2), marker=dict(size=8),
                  hovertemplate="%{fullData.name}, %{x} anni<br>Valore mediano: €%{y:.1f}M<br>%{customdata[0]} giocatori<extra></extra>")
st.plotly_chart(style_fig(fig, 420), width="stretch")
peak = curve.loc[curve.groupby("role_group")["valore_mediano"].idxmax()]
st.caption("Età di picco del valore mediano: " + ", ".join(
    f"{r.role_group} {r.age} anni (€{r.valore_mediano:.1f}M)" for r in peak.itertuples()))

-- Valore della rosa (Transfermarkt) vs rendimento in campionato.
CREATE VIEW v_team_value_performance AS
SELECT st.season_id, st.season, st.team_id, st.team, st.position, st.points, st.goal_difference,
       ts.squad_value_eur, ts.avg_age, ts.squad_size, ts.n_foreigners,
       1.0 * ts.n_foreigners / NULLIF(ts.squad_size, 0) AS foreigners_share,
       RANK() OVER (PARTITION BY st.season_id ORDER BY ts.squad_value_eur DESC) AS value_rank,
       st.points / NULLIF(ts.squad_value_eur / 10000000.0, 0) AS points_per_10m
FROM v_standings st
LEFT JOIN fact_team_season ts ON ts.season_id = st.season_id AND ts.team_id = st.team_id;

-- Rating Elo a inizio/fine stagione (ClubElo) vs classifica.
CREATE VIEW v_team_elo AS
SELECT st.season_id, st.season, st.team_id, st.team, st.position, st.points,
       es.elo AS elo_start, ee.elo AS elo_end, ee.elo - es.elo AS elo_change
FROM v_standings st
JOIN fact_team_elo es ON es.season_id = st.season_id AND es.team_id = st.team_id AND es.snapshot = 'start'
LEFT JOIN fact_team_elo ee ON ee.season_id = st.season_id AND ee.team_id = st.team_id AND ee.snapshot = 'end';

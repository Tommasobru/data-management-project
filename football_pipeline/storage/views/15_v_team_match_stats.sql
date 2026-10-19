-- Statistiche di gioco (football-data.co.uk) aggregate per squadra e stagione.
CREATE VIEW v_team_match_stats AS
SELECT tm.season_id, tm.season, tm.team_id, tm.team,
       COUNT(*) AS matches,
       SUM(CASE WHEN tm.venue = 'Casa' THEN fs.home_shots ELSE fs.away_shots END) AS shots,
       SUM(CASE WHEN tm.venue = 'Casa' THEN fs.home_shots_on_target ELSE fs.away_shots_on_target END) AS shots_on_target,
       SUM(CASE WHEN tm.venue = 'Casa' THEN fs.away_shots ELSE fs.home_shots END) AS shots_against,
       SUM(CASE WHEN tm.venue = 'Casa' THEN fs.home_corners ELSE fs.away_corners END) AS corners,
       SUM(CASE WHEN tm.venue = 'Casa' THEN fs.home_fouls ELSE fs.away_fouls END) AS fouls,
       SUM(CASE WHEN tm.venue = 'Casa' THEN fs.home_yellow ELSE fs.away_yellow END) AS yellow_cards,
       SUM(CASE WHEN tm.venue = 'Casa' THEN fs.home_red ELSE fs.away_red END) AS red_cards,
       SUM(tm.goals_for) AS goals_for,
       SUM(tm.points) AS points
FROM v_team_match tm
JOIN fact_match_stats fs ON fs.match_id = tm.match_id
GROUP BY tm.season_id, tm.season, tm.team_id, tm.team;

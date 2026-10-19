-- Expected goals (Understat) vs gol reali per squadra e stagione.
CREATE VIEW v_team_xg AS
SELECT tm.season_id, tm.season, tm.team_id, tm.team,
       COUNT(*) AS matches,
       SUM(CASE WHEN tm.venue = 'Casa' THEN x.home_xg ELSE x.away_xg END) AS xg_for,
       SUM(CASE WHEN tm.venue = 'Casa' THEN x.away_xg ELSE x.home_xg END) AS xg_against,
       SUM(tm.goals_for) AS goals_for,
       SUM(tm.goals_against) AS goals_against,
       SUM(tm.points) AS points
FROM v_team_match tm
JOIN fact_match_xg x ON x.match_id = tm.match_id
GROUP BY tm.season_id, tm.season, tm.team_id, tm.team;

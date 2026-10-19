-- Fattore campo per stagione.
CREATE VIEW v_home_advantage AS
SELECT m.season_id, s.label AS season,
       COUNT(*) AS matches,
       100.0 * SUM(CASE WHEN result = 'H' THEN 1 ELSE 0 END) / COUNT(*) AS home_win_pct,
       100.0 * SUM(CASE WHEN result = 'D' THEN 1 ELSE 0 END) / COUNT(*) AS draw_pct,
       100.0 * SUM(CASE WHEN result = 'A' THEN 1 ELSE 0 END) / COUNT(*) AS away_win_pct,
       1.0 * SUM(home_goals) / COUNT(*) AS avg_home_goals,
       1.0 * SUM(away_goals) / COUNT(*) AS avg_away_goals,
       1.0 * SUM(home_goals + away_goals) / COUNT(*) AS avg_total_goals
FROM fact_match m
JOIN dim_season s ON s.season_id = m.season_id
WHERE m.stage = 'REGULAR'
GROUP BY m.season_id, s.label;

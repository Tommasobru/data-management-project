-- Classifica "a fine primo tempo" vs classifica reale: chi rimonta e chi si fa rimontare.
CREATE VIEW v_half_vs_full AS
SELECT season_id, season, team_id, team,
       SUM(points_ht) AS points_if_ht,
       SUM(points) AS points,
       SUM(points) - SUM(points_ht) AS second_half_delta,
       SUM(CASE WHEN points_ht = 0 AND points = 3 THEN 1 ELSE 0 END) AS comeback_wins,
       SUM(CASE WHEN points_ht = 0 AND points = 1 THEN 1 ELSE 0 END) AS comeback_draws,
       SUM(CASE WHEN points_ht = 3 AND points < 3 THEN 1 ELSE 0 END) AS leads_lost
FROM v_team_match
WHERE points_ht IS NOT NULL
GROUP BY season_id, season, team_id, team;

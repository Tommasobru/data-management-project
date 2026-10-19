-- Punti attesi secondo i bookmaker (3*P(vittoria) + P(pareggio)) vs punti reali.
CREATE VIEW v_team_expected_points AS
SELECT season_id, season, team_id, team,
       COUNT(*) AS matches,
       SUM(expected_points) AS expected_points,
       SUM(points) AS points,
       SUM(points) - SUM(expected_points) AS points_over_expected
FROM (
    SELECT season_id, season, home_team_id AS team_id, home_team AS team,
           3 * p_home + p_draw AS expected_points,
           CASE result WHEN 'H' THEN 3 WHEN 'D' THEN 1 ELSE 0 END AS points
    FROM v_match_odds
    UNION ALL
    SELECT season_id, season, away_team_id, away_team,
           3 * p_away + p_draw,
           CASE result WHEN 'A' THEN 3 WHEN 'D' THEN 1 ELSE 0 END
    FROM v_match_odds
) x
GROUP BY season_id, season, team_id, team;

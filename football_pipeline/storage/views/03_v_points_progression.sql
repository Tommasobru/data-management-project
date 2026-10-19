-- Punti cumulati partita dopo partita (corsa scudetto / salvezza).
CREATE VIEW v_points_progression AS
SELECT season_id, season, team_id, team, match_date, opponent, venue, outcome,
       ROW_NUMBER() OVER (PARTITION BY season_id, team_id ORDER BY match_date, match_id) AS game_no,
       SUM(points) OVER (PARTITION BY season_id, team_id ORDER BY match_date, match_id
                         ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS cumulative_points
FROM v_team_match;

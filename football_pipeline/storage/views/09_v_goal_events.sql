-- Gol arricchiti: fascia di minuto, squadre, marcatore.
CREATE VIEW v_goal_events AS
SELECT g.goal_id, g.match_id, m.season_id, s.label AS season, m.matchweek, g.seq, g.minute,
       CASE WHEN g.minute <= 15 THEN '01-15'
            WHEN g.minute <= 30 THEN '16-30'
            WHEN g.minute <= 45 THEN '31-45+'
            WHEN g.minute <= 60 THEN '46-60'
            WHEN g.minute <= 75 THEN '61-75'
            ELSE '76-90+' END AS minute_band,
       g.scoring_team_id, st.team_name AS scoring_team,
       g.conceding_team_id, ct.team_name AS conceding_team,
       g.player_id, COALESCE(p.player_name, g.scorer_name) AS scorer,
       g.is_own_goal, g.home_score_after, g.away_score_after,
       m.home_goals, m.away_goals, m.home_team_id, m.away_team_id
FROM fact_goal g
JOIN fact_match m ON m.match_id = g.match_id
JOIN dim_season s ON s.season_id = m.season_id
LEFT JOIN dim_team st ON st.team_id = g.scoring_team_id
LEFT JOIN dim_team ct ON ct.team_id = g.conceding_team_id
LEFT JOIN dim_player p ON p.player_id = g.player_id;

-- Marcatori per stagione con valore di mercato e costo per gol.
CREATE VIEW v_top_scorers AS
SELECT x.season_id, x.season, x.player_id, x.scorer, x.team, x.goals,
       ps.role, ps.age, ps.market_value_eur,
       ps.market_value_eur / x.goals AS value_per_goal
FROM (
    SELECT season_id, season, player_id, scorer, scoring_team_id, scoring_team AS team, COUNT(*) AS goals
    FROM v_goal_events
    WHERE NOT is_own_goal
    GROUP BY season_id, season, player_id, scorer, scoring_team_id, scoring_team
) x
LEFT JOIN fact_player_season ps
       ON ps.season_id = x.season_id AND ps.player_id = x.player_id AND ps.team_id = x.scoring_team_id;

-- Classifica finale per stagione (a parità di punti: differenza reti, gol fatti).
CREATE VIEW v_standings AS
SELECT season_id, season, team_id, team, played, wins, draws, losses,
       goals_for, goals_against, goals_for - goals_against AS goal_difference, points,
       home_points, away_points,
       RANK() OVER (PARTITION BY season_id
                    ORDER BY points DESC, goals_for - goals_against DESC, goals_for DESC) AS position
FROM (
    SELECT season_id, season, team_id, team,
           COUNT(*) AS played,
           SUM(CASE WHEN outcome = 'V' THEN 1 ELSE 0 END) AS wins,
           SUM(CASE WHEN outcome = 'N' THEN 1 ELSE 0 END) AS draws,
           SUM(CASE WHEN outcome = 'P' THEN 1 ELSE 0 END) AS losses,
           SUM(goals_for) AS goals_for,
           SUM(goals_against) AS goals_against,
           SUM(points) AS points,
           SUM(CASE WHEN venue = 'Casa' THEN points ELSE 0 END) AS home_points,
           SUM(CASE WHEN venue = 'Trasferta' THEN points ELSE 0 END) AS away_points
    FROM v_team_match
    GROUP BY season_id, season, team_id, team
) agg;

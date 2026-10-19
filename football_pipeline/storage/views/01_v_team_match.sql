-- Una riga per squadra per partita (stagione regolare): base di quasi tutte le analisi.
CREATE VIEW v_team_match AS
SELECT m.match_id, m.season_id, s.label AS season, m.matchweek, m.match_date,
       'Casa' AS venue, m.home_team_id AS team_id, t.team_name AS team,
       m.away_team_id AS opponent_id, o.team_name AS opponent,
       m.home_goals AS goals_for, m.away_goals AS goals_against,
       m.home_goals_ht AS goals_for_ht, m.away_goals_ht AS goals_against_ht,
       CASE m.result WHEN 'H' THEN 'V' WHEN 'D' THEN 'N' ELSE 'P' END AS outcome,
       CASE m.result WHEN 'H' THEN 3 WHEN 'D' THEN 1 ELSE 0 END AS points,
       CASE WHEN m.home_goals_ht IS NULL THEN NULL
            WHEN m.home_goals_ht > m.away_goals_ht THEN 3
            WHEN m.home_goals_ht = m.away_goals_ht THEN 1 ELSE 0 END AS points_ht
FROM fact_match m
JOIN dim_season s ON s.season_id = m.season_id
JOIN dim_team t ON t.team_id = m.home_team_id
JOIN dim_team o ON o.team_id = m.away_team_id
WHERE m.stage = 'REGULAR'
UNION ALL
SELECT m.match_id, m.season_id, s.label, m.matchweek, m.match_date,
       'Trasferta', m.away_team_id, t.team_name,
       m.home_team_id, o.team_name,
       m.away_goals, m.home_goals,
       m.away_goals_ht, m.home_goals_ht,
       CASE m.result WHEN 'A' THEN 'V' WHEN 'D' THEN 'N' ELSE 'P' END,
       CASE m.result WHEN 'A' THEN 3 WHEN 'D' THEN 1 ELSE 0 END,
       CASE WHEN m.away_goals_ht IS NULL THEN NULL
            WHEN m.away_goals_ht > m.home_goals_ht THEN 3
            WHEN m.away_goals_ht = m.home_goals_ht THEN 1 ELSE 0 END
FROM fact_match m
JOIN dim_season s ON s.season_id = m.season_id
JOIN dim_team t ON t.team_id = m.away_team_id
JOIN dim_team o ON o.team_id = m.home_team_id
WHERE m.stage = 'REGULAR';

-- Quote primarie per partita con probabilità implicite normalizzate (senza margine).
CREATE VIEW v_match_odds AS
SELECT q.*,
       q.inv_home / q.book_sum AS p_home,
       q.inv_draw / q.book_sum AS p_draw,
       q.inv_away / q.book_sum AS p_away,
       q.book_sum - 1 AS margin,
       CASE WHEN q.odds_home <= q.odds_draw AND q.odds_home <= q.odds_away THEN 'H'
            WHEN q.odds_away <= q.odds_draw THEN 'A' ELSE 'D' END AS favourite
FROM (
    SELECT m.match_id, m.season_id, s.label AS season, m.match_date, m.matchweek,
           hmt.team_name AS home_team, awt.team_name AS away_team,
           m.home_team_id, m.away_team_id, m.home_goals, m.away_goals, m.result,
           o.source AS odds_source, o.odds_home, o.odds_draw, o.odds_away,
           1.0 / o.odds_home AS inv_home, 1.0 / o.odds_draw AS inv_draw, 1.0 / o.odds_away AS inv_away,
           1.0 / o.odds_home + 1.0 / o.odds_draw + 1.0 / o.odds_away AS book_sum
    FROM fact_match m
    JOIN fact_odds o ON o.match_id = m.match_id AND o.is_primary
    JOIN dim_season s ON s.season_id = m.season_id
    JOIN dim_team hmt ON hmt.team_id = m.home_team_id
    JOIN dim_team awt ON awt.team_id = m.away_team_id
    WHERE m.stage = 'REGULAR'
) q;

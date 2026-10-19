-- Variazione del valore di mercato tra la prima e l'ultima stagione disponibile.
CREATE VIEW v_player_value_growth AS
WITH pv AS (
    SELECT player_id, season_id, MAX(market_value_eur) AS value, MAX(age) AS age,
           MAX(role) AS role, MAX(role_group) AS role_group, MIN(team_id) AS team_id
    FROM fact_player_season
    WHERE market_value_eur IS NOT NULL
    GROUP BY player_id, season_id
), bounds AS (
    SELECT player_id, MIN(season_id) AS first_season, MAX(season_id) AS last_season
    FROM pv GROUP BY player_id
)
SELECT p.player_id, p.player_name, b.first_season, b.last_season,
       f.age AS first_age, l.age AS last_age, l.role, l.role_group,
       tf.team_name AS first_team, tl.team_name AS last_team,
       f.value AS first_value, l.value AS last_value,
       l.value - f.value AS value_delta,
       100.0 * (l.value - f.value) / NULLIF(f.value, 0) AS growth_pct
FROM bounds b
JOIN pv f ON f.player_id = b.player_id AND f.season_id = b.first_season
JOIN pv l ON l.player_id = b.player_id AND l.season_id = b.last_season
JOIN dim_player p ON p.player_id = b.player_id
JOIN dim_team tf ON tf.team_id = f.team_id
JOIN dim_team tl ON tl.team_id = l.team_id
WHERE b.first_season < b.last_season;

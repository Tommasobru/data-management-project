-- Variazione del valore della rosa tra la prima e l'ultima stagione in Serie A del periodo.
CREATE VIEW v_squad_value_growth AS
WITH bounds AS (
    SELECT team_id, MIN(season_id) AS first_season, MAX(season_id) AS last_season, COUNT(*) AS seasons
    FROM fact_team_season WHERE squad_value_eur IS NOT NULL GROUP BY team_id
)
SELECT t.team_name AS team, b.first_season, b.last_season, b.seasons,
       f.squad_value_eur AS first_value, l.squad_value_eur AS last_value,
       100.0 * (l.squad_value_eur - f.squad_value_eur) / NULLIF(f.squad_value_eur, 0) AS growth_pct,
       f.avg_age AS first_avg_age, l.avg_age AS last_avg_age
FROM bounds b
JOIN fact_team_season f ON f.team_id = b.team_id AND f.season_id = b.first_season
JOIN fact_team_season l ON l.team_id = b.team_id AND l.season_id = b.last_season
JOIN dim_team t ON t.team_id = b.team_id;

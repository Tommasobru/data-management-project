create view ftb.point_half_vs_full_time
as
-- calcola punti in casa nel primo tempo
WITH half_home_points AS (
    SELECT
        tab2.season,
        tab2.home_team,
        SUM(tab2.home_point) AS tot_home_point
    FROM (
        SELECT
            tab.giornata,
            tab.season,
            tab.home_team,
            tab.half_time_winner,
            CASE 
                WHEN tab.half_time_winner = 'home winner' THEN 3 
                WHEN tab.half_time_winner = 'away winner' THEN 0
                ELSE 1
            END AS home_point
        FROM (
            SELECT 
                m.giornata,
                m.season,
                m.home_team,
                m.half_time_home_score,
                m.half_time_away_score,
                CASE
                    WHEN m.half_time_home_score > m.half_time_away_score THEN 'home winner'
                    WHEN m.half_time_home_score < m.half_time_away_score THEN 'away winner'
                    ELSE 'draw'
                END AS half_time_winner
            FROM stg.fact_matches m
        ) AS tab
    ) AS tab2
    GROUP BY tab2.home_team, tab2.season
),

-- calcola punti fuori casa nel primo tempo 
half_away_points AS (
    SELECT
        tab2.season,
        tab2.away_team,
        SUM(tab2.away_point) AS tot_away_point
    FROM (
        SELECT
            tab.giornata,
            tab.season,
            tab.away_team,
            tab.half_time_winner,
            CASE 
                WHEN tab.half_time_winner = 'home winner' THEN 0 
                WHEN tab.half_time_winner = 'away winner' THEN 3
                ELSE 1
            END AS away_point
        FROM (
            SELECT 
                m.giornata,
                m.season,
                m.away_team,
                m.half_time_home_score,
                m.half_time_away_score,
                CASE
                    WHEN m.half_time_home_score > m.half_time_away_score THEN 'home winner'
                    WHEN m.half_time_home_score < m.half_time_away_score THEN 'away winner'
                    ELSE 'draw'
                END AS half_time_winner
            FROM stg.fact_matches m
        ) AS tab
    ) AS tab2
    GROUP BY tab2.away_team, tab2.season
)

-- unisci le tabelle

,tot_half_points as ( 
SELECT
    home.season,
    home.home_team AS team,
    home.tot_home_point,
    away.tot_away_point,
    home.tot_home_point + away.tot_away_point  as tot_point
FROM half_home_points AS home
LEFT JOIN half_away_points AS away
    ON home.home_team = away.away_team
    AND home.season = away.season)
 
-- calcola punti in casa in tutta la partita
,full_home_points AS (
    SELECT
        tab2.season,
        tab2.home_team,
        SUM(tab2.home_point) AS tot_home_point
    FROM (
        SELECT
            tab.giornata,
            tab.season,
            tab.home_team,
            tab.full_time_winner,
            CASE 
                WHEN tab.full_time_winner = 'home winner' THEN 3 
                WHEN tab.full_time_winner = 'away winner' THEN 0
                ELSE 1
            END AS home_point
        FROM (
            SELECT 
                m.giornata,
                m.season,
                m.home_team,
                m.home_score,
                m.away_score,
                CASE
                    WHEN m.home_score > m.away_score THEN 'home winner'
                    WHEN m.home_score < m.away_score THEN 'away winner'
                    ELSE 'draw'
                END AS full_time_winner
            FROM stg.fact_matches m
        ) AS tab
    ) AS tab2
    GROUP BY tab2.home_team, tab2.season
),

-- calcola punti fuori casa in tutta la partita 
full_away_points AS (
    SELECT
        tab2.season,
        tab2.away_team,
        SUM(tab2.away_point) AS tot_away_point
    FROM (
        SELECT
            tab.giornata,
            tab.season,
            tab.away_team,
            tab.full_time_winner,
            CASE 
                WHEN tab.full_time_winner = 'home winner' THEN 0 
                WHEN tab.full_time_winner = 'away winner' THEN 3
                ELSE 1
            END AS away_point
        FROM (
            SELECT 
                m.giornata,
                m.season,
                m.away_team,
                m.home_score,
                m.away_score,
                CASE
                    WHEN m.home_score > m.away_score THEN 'home winner'
                    WHEN m.home_score < m.away_score THEN 'away winner'
                    ELSE 'draw'
                END AS full_time_winner
            FROM stg.fact_matches m
        ) AS tab
    ) AS tab2
    GROUP BY tab2.away_team, tab2.season
)

-- unisci le tabelle

,tot_full_points as ( 
SELECT
    home.season,
    home.home_team AS team,
    home.tot_home_point,
    away.tot_away_point,
    home.tot_home_point + away.tot_away_point  as tot_point
FROM full_home_points AS home
LEFT JOIN full_away_points AS away
    ON home.home_team = away.away_team
    AND home.season = away.season)
 

select 
	tot.season
	,tot.team
	,tot.tot_point as half_tot_point
	,tot_full.tot_point as tot_point
	,row_number() over(partition by tot.season order by tot.tot_point desc) as ranking_half
	,row_number() over(partition by tot.season order by tot_full.tot_point desc) as ranking_full 
from tot_half_points as tot
left join tot_full_points as tot_full
on tot_full.season = tot.season and tot.team = tot_full.team
order by tot.season asc, half_tot_point desc;
 
  

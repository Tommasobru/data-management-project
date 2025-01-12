create view avg_points_vs_market_value
as

with home_matches as(
 SELECT 
 		m.season
        ,m.home_team
        ,count(*) 		as n_home_matches
  FROM ftb.matches m
  inner join ftb.matches_details md
  on md.match_id = m.match_id
  where winner is not null
  group by m.season, home_team 
)

,away_matches as(
 SELECT 
 		m.season
        ,m.away_team
        ,count(*) 		as n_away_matches
  FROM ftb.matches m
  inner join ftb.matches_details md
  on md.match_id = m.match_id
  where winner is not null
  group by m.season, away_team 
)

,all_matches as(
select
	h.season 
	,h.home_team 						as team
	,h.n_home_matches + a.n_away_matches 	as tot_matches
from home_matches h
left join away_matches a
on h.home_team = a.away_team and h.season = a.season
)

,punti_in_casa as(
select 
	m.season
	,m.home_team		as team
	,sum(case when md.winner = 'HOME_TEAM' then 3
			 when md.winner = 'AWAY_TEAM' then 0
			 else 1 end) as home_point
FROM ftb.matches m
inner join ftb.matches_details md
  on md.match_id = m.match_id
 group by m.season,m.home_team)

,punti_fuori_casa as(
select 
	m.season
	,m.away_team  	as team
	,sum(case when md.winner = 'HOME_TEAM' then 0
			 when md.winner = 'AWAY_TEAM' then 3
			 else 1 end) as away_point
FROM ftb.matches m
inner join ftb.matches_details md
  on md.match_id = m.match_id
 group by m.season,m.away_team)
 
 ,all_points as (
 select 
 	c.season
 	,c.team
 	,c.home_point + f.away_point as tot_point
 from punti_in_casa as c
 inner join punti_fuori_casa f
 on c.season = f.season and c.team = f.team
 )
 
 select 
 	m.season
 	,m.team
 	,m.tot_matches 
 	,p.tot_point
 	,round((p.tot_point*1.0)/m.tot_matches, 2)		as media_punti
 	,lt."Valore Rosa" 							as valore_rosa
 	,lt."Età Media"  							as eta_media
 from all_matches m
 inner join all_points p
 on m.season = p.season and m.team = p.team
 left join ftb.list_team lt 
 on lt."Squadra" = m.team and lt."Stagione" = m.season
 
 

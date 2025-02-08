create view ftb.players_draw_matches
as
--we want to analyze which players draw matches most often 

with goal_draw as(
select
	m.season 
	,m.home_team 
	,m.away_team 
	,m.home_score 
	,m.away_score 
	,m.winner 
	,agsa.scorer
	,agsa.numero_goal_partita 
	,agsa.goal
from stg.fact_matches m
left join stg.fact_all_goal_serie_a agsa 
	on agsa.home_team = m.home_team and agsa.away_team = m.away_team and m.season = agsa.anno  
where m.winner = 'DRAW' and scorer is not null)

,last_goal_draw as(
	select 
		season
		,home_team
		,away_team
		,home_score
		,away_score
		,max(numero_goal_partita) as last_goal
	from goal_draw
	group by season,home_team,away_team,home_score,away_score)
	
,last_scorer as(
	select 
		lgd.season
		,lgd.home_team
		,lgd.away_team
		,lgd.home_score
		,lgd.away_score
		,agsa.goal
		,agsa.scorer
	from last_goal_draw lgd
	inner join stg.fact_all_goal_serie_a agsa 
		on lgd.season = agsa.anno and lgd.home_team = agsa.home_team and lgd.away_team = agsa.away_team
		and agsa.numero_goal_partita = lgd.last_goal
)

,scorer_market_value as (
	select 		
		season
		,home_team
		,away_team
		,home_score
		,away_score
		,scorer
		,goal
		,pt.market_value as market_value
	from last_scorer ls
	left join stg.dim_player_team pt 
	on pt.name = ls.scorer
	order by season asc, pt.market_value)


select 
	season
	,scorer
	,count(*) 			as number_draw_goals	
	,max(market_value) 	as market_value
from scorer_market_value
group by season,scorer
order by season asc, count(*) desc, avg(market_value) asc





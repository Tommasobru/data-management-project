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
	,md.winner 
	,agsa.scorer
	,agsa.numero_goal_partita 
	,agsa.goal
from ftb.matches m
inner join ftb.matches_details md 
	on md.match_id = m.match_id	
left join ftb.all_goal_serie_a agsa 
	on agsa."Home Team" = m.home_team and agsa."Away Team" = m.away_team and m.season = agsa.anno  
where md.winner = 'DRAW' and scorer is not null)

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
	inner join ftb.all_goal_serie_a agsa 
		on lgd.season = agsa.anno and lgd.home_team = agsa."Home Team" and lgd.away_team = agsa."Away Team" 
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
		,pt."Market Value" as market_value
	from last_scorer ls
	left join ftb.player_team pt 
	on pt."Name" = ls.scorer
	order by season asc, pt."Market Value")


select 
	season
	,scorer
	,count(*) as number_draw_goals	
	,max(market_value) as market_value
from scorer_market_value
group by season,scorer
order by season asc, count(*) desc, avg(market_value) asc





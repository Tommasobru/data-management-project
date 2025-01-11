create view ftb.players_goal_victory 
as
-- we want to find the players who scored the most decisive goals 

with diff_goals_tab as(
	select
		m.season 
		,m.home_team 
		,m.away_team 
		,m.home_score 
		,m.away_score 
		,md.winner 
		,case 
			when md.winner = 'HOME_TEAM' then m.home_score - m.away_score 
			else m.away_score - m.home_score 
		end diff_goals
	from ftb.matches m
	inner join ftb.matches_details md 
		on md.match_id = m.match_id	
	where md.winner <> 'DRAW')

		
, all_match_with_draw as (
	select 
		sub.season 
		,sub.home_team 
		,sub.away_team 
		,sub.home_score 
		,sub.away_score 
		,sub.winner
		,sub.scorer
		,sub.goal
		,sub.numero_goal_partita
		,sub.goal_home
		,sub.goal_away
		,sub.draw_goal
		,sub.diff_goals
		,sub.team_goal
		,sub.n_goal_match
		,sub.at_least_one_draw
		,sum(case when sub.draw_goal = 'NO DRAW' and sub.numero_goal_partita = n_goal_match  then 1 else 0 end)
			over(partition by sub.season,sub.home_team,sub.away_team order by sub.numero_goal_partita) as victory_goal
	from(
	select 
		season 
		,home_team 
		,away_team 
		,home_score 
		,away_score 
		,winner
		,agsa.scorer
		,agsa.goal
		,agsa.numero_goal_partita
		,agsa.goal_home
		,agsa.goal_away
		,case
			when goal_home = goal_away then 'DRAW'
			else 'NO DRAW'
		end as draw_goal
		,dgt.diff_goals
		,agsa.team_goal
		,max(numero_goal_partita) over(partition by season,home_team,away_team) as n_goal_match
		,sum(case when agsa.goal_home = agsa.goal_away then 1 else 0 end) over(partition by season,home_team,away_team) as at_least_one_draw
	from diff_goals_tab dgt
	inner join ftb.all_goal_serie_a agsa
	on agsa.anno = dgt.season and agsa."Home Team" = dgt.home_team and agsa."Away Team" = dgt.away_team
	where dgt.diff_goals = 1 and scorer is not null) sub
	where sub.at_least_one_draw <> 0 

)

select 
	season
	,squadra_giocatore
	,name
	,role
	,max(market_value) as market_value
	,count(*) as number_victory_goals
from(
	select 
		amwd.season
		,amwd.home_team 
		,amwd.away_team
		,pt."Name" as name
		,pt."Squadra"  as squadra_giocatore
		,pt."Market Value" as market_value
		,pt."Role" as role
	from all_match_with_draw amwd
	left join ftb.player_team pt 
		on pt."Name" = amwd.scorer and pt."Season" = amwd.season
	where victory_goal = 1) as sub
group by season, squadra_giocatore, name, role
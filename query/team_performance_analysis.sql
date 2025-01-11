create view ftb.team_performance_analysis 
as
with home_team_performance_analysis as (
select 
	season
	,home_team as team
	,sum(home_score) as goal_fatti_giocando_in_casa
	,sum(away_score) as goal_subiti_giocando_in_casa
	,sum(half_time_home_goal) as goal_fatti_giocando_in_casa_nel_primo_tempo
	,sum(half_time_away_goal) as goal_subiti_giocando_in_casa_nel_primo_tempo
	,round(sum(half_time_home_goal)::numeric/sum(home_score)::numeric,2) as goal_primo_tempo_su_goal
	,round(sum(half_time_away_goal)::numeric/sum(away_score)::numeric,2) as goal_subiti_primo_tempo_su_goal
from(
	select 
		m.match_id
		,m.giornata
		,m.season
		,m.home_team
		,m.away_team
		,m.home_score
		,m.away_score
		,d.winner
		,d."halfTimeHomeGoal" as half_time_home_goal
		,d."halfTimeAwayGoal" as half_time_away_goal
	from ftb.matches as m
	left join ftb.matches_details as d
		on d.match_id = m.match_id
) as tab
group by tab.season,tab.home_team 
order by sum(home_score) desc)

,away_team_performance_analysis as (
	select 
		season
		,away_team as team
		,sum(home_score) as goal_subiti_giocando_fuori_casa
		,sum(away_score) as goal_fatti_giocando_in_fuori_casa
		,sum(half_time_home_goal) as goal_subiti_giocando_fuori_casa_nel_primo_tempo
		,sum(half_time_away_goal) as goal_fatti_giocando_fuori_casa_nel_primo_tempo
		,round(sum(half_time_home_goal)::numeric/sum(home_score)::numeric,2) as goal_subiti_tempo_su_goal_fuori_casa
		,round(sum(half_time_away_goal)::numeric/sum(away_score)::numeric,2) as goal_fatti_primo_tempo_su_goal_fuori_casa
	from(
		select 
			m.match_id
			,m.giornata
			,m.season
			,m.home_team
			,m.away_team
			,m.home_score
			,m.away_score
			,d.winner
			,d."halfTimeHomeGoal" as half_time_home_goal
			,d."halfTimeAwayGoal" as half_time_away_goal
		from ftb.matches as m
		left join ftb.matches_details as d
			on d.match_id = m.match_id
	) as tab
	group by tab.season,tab.away_team 
	order by sum(away_score) desc
	)

select 
	home.season
	,home.team
	,goal_fatti_giocando_in_casa
	,goal_subiti_giocando_in_casa
	,goal_fatti_giocando_in_casa_nel_primo_tempo
	,goal_subiti_giocando_in_casa_nel_primo_tempo
	,goal_primo_tempo_su_goal
	,goal_subiti_primo_tempo_su_goal
	,goal_subiti_giocando_fuori_casa
	,goal_fatti_giocando_in_fuori_casa
	,goal_subiti_giocando_fuori_casa_nel_primo_tempo
	,goal_fatti_giocando_fuori_casa_nel_primo_tempo
	,goal_subiti_tempo_su_goal_fuori_casa
	,goal_fatti_primo_tempo_su_goal_fuori_casa
from home_team_performance_analysis home
inner join away_team_performance_analysis away
	on home.season = away.season and home.team = away.team
	
select 
	season
	,home_team as team
	,sum(home_score) as goal_fatti_giocando_in_casa
	,sum(away_score) as goal_subiti_goal_subiti_giocando_in_casa
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
	from fact.matches as m
	left join fact.matches_details as d
		on d.match_id = m.match_id
) as tab
group by tab.season,tab.home_team 
order by sum(home_score) desc
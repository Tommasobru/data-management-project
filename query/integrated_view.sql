create view ftb.integrated_view 
as 
select 	
	g.anno
	,g.giornata
	,g."Home Team"
	,g."Away Team"
	,g.scorer
	,p."Role"
	,p."Market Value"
	,th."Giocatori in Rosa" as giocatori_in_rosa_home_team
	,th."Stranieri" as stranieri_home_team
	,th."Età Media" as eta_media_home_team
	,th."Valore Rosa" as valore_rosa_home_team
	,ta."Giocatori in Rosa" as giocatori_in_rosa_away_team
	,ta."Stranieri" as stranieri_away_team
	,ta."Età Media" as eta_media_away_team
	,ta."Valore Rosa" as valore_rosa_away_team
from ftb.all_goal_serie_a as g
left join(
	select 
		m.match_id
		,m.giornata
		,m.season
		,m.home_team
		,m.away_team
		,m.home_score
		,m.away_score
		,d.winner
		,d."fullTimeHomeGoal"
		,d."fullTimeAwayGoal"
		,d."halfTimeHomeGoal"
		,d."halfTimeAwayGoal"
	from ftb.matches as m
	inner join ftb.matches_details as d
	on d.match_id = m.match_id
) as match
on match.season = g.anno and match.giornata = g.giornata 
	and match.home_team = g."Home Team"
left join ftb.player_team as p
on  p."Name" = g.scorer and p."Season" = g.anno
left join ftb.list_team as th
on th."Squadra" = g."Home Team" and th."Stagione" = g.anno
left join ftb.list_team as ta
on ta."Squadra" = g."Away Team" and ta."Stagione" = g.anno
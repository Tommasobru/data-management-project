create view ftb.risultati_reali_vs_risultati_odds
as
select 
	home.season 
	,home.home_team
	,vittorie_teoriche_casa
	,vittorie_reali_casa
	,percentuale_casa
	,vittorie_teoriche_trasferta
	,vittorie_reali_trasferta
	,percentuale_trasferta
	,vittorie_teoriche_casa + vittorie_teoriche_trasferta vittorie_totali_teoriche
	,vittorie_reali_casa + vittorie_reali_trasferta vittorie_reali_teoriche
	,round(
	100*(vittorie_reali_casa + vittorie_reali_trasferta)/(vittorie_teoriche_casa + vittorie_teoriche_trasferta)
	,2)  percentuale_vittorie_totale
	,sconfitte_teoriche_casa
	,sconfitte_reali_casa
	,percentuale_sconfitte_casa
	,sconfitte_teoriche_trasferta
	,sconfitte_reali_trasferta
	,percentuale_sconfitte_trasferta
	,sconfitte_teoriche_casa + sconfitte_teoriche_trasferta  sconfitte_totali_teoriche
	,sconfitte_reali_casa + sconfitte_reali_trasferta  sconfitte_totali_reali
	,round(
	100*(sconfitte_reali_casa + sconfitte_reali_trasferta )/(sconfitte_teoriche_casa + sconfitte_teoriche_trasferta)
	,2) percentuale_sconfitte_totale
	
from(
select
	season
	,home_team
	,count(*) filter (where theorical_result = 'HOME_WINNER') vittorie_teoriche_casa
	,count(*) filter (where winner = 'HOME_WINNER') vittorie_reali_casa
	,round(
	100.0 * (count(*) filter (where winner = 'HOME_WINNER'))/(count(*) filter (where theorical_result = 'HOME_WINNER'))
	,2) percentuale_casa

from(
select 
	odds.season
	,odds.home_team
	,odds.away_team
	,case 
		when quota_1 < quota_x and quota_1 < quota_2 then 'HOME_WINNER' 	
		when quota_2 < quota_x and quota_2 < quota_1 then 'AWAY_WINNER'
		else 'DRAW' 
	end theorical_result
	,matches.winner 
from ftb.fact_matches_odds_details odds

inner join ftb.fact_matches matches
	on odds.season = matches.season 
	and odds.home_team = matches."home team"
	and odds.away_team = matches."away team") as mat
group by 
	season
	,home_team) home

left join (
select
	season
	,away_team
	,count(*) filter (where theorical_result = 'AWAY_WINNER') vittorie_teoriche_trasferta
	,count(*) filter (where winner = 'AWAY_WINNER') vittorie_reali_trasferta
	,round(
	100.0 * (count(*) filter (where winner = 'AWAY_WINNER'))/nullif(count(*) filter (where theorical_result = 'AWAY_WINNER'),0)
	,2) percentuale_trasferta

from(
select 
	odds.season
	,odds.home_team
	,odds.away_team
	,case 
		when quota_1 < quota_x and quota_1 < quota_2 then 'HOME_WINNER' 	
		when quota_2 < quota_x and quota_2 < quota_1 then 'AWAY_WINNER'
		else 'DRAW' 
	end theorical_result
	,matches.winner 
from ftb.fact_matches_odds_details odds

inner join ftb.fact_matches matches
	on odds.season = matches.season 
	and odds.home_team = matches."home team"
	and odds.away_team = matches."away team") as mat
group by 
	season
	,away_team) away

on home.home_team = away.away_team and home.season = away.season 


left join (
select
	season
	,home_team
	,count(*) filter (where theorical_result = 'AWAY_WINNER') sconfitte_teoriche_casa
	,count(*) filter (where winner = 'AWAY_WINNER') sconfitte_reali_casa
	,round(
	100.0 * (count(*) filter (where winner = 'AWAY_WINNER'))/nullif(count(*) filter (where theorical_result = 'AWAY_WINNER'),0)
	,2) percentuale_sconfitte_casa

from(
select 
	odds.season
	,odds.home_team
	,odds.away_team
	,case 
		when quota_1 < quota_x and quota_1 < quota_2 then 'HOME_WINNER' 	
		when quota_2 < quota_x and quota_2 < quota_1 then 'AWAY_WINNER'
		else 'DRAW' 
	end theorical_result
	,matches.winner 
from ftb.fact_matches_odds_details odds

inner join ftb.fact_matches matches
	on odds.season = matches.season 
	and odds.home_team = matches."home team"
	and odds.away_team = matches."away team") as mat
group by 
	season
	,home_team
) homesc
on home.home_team = homesc.home_team and home.season = homesc.season

left join(
select
	season
	,away_team
	,count(*) filter (where theorical_result = 'AWAY_WINNER') sconfitte_teoriche_trasferta
	,count(*) filter (where winner = 'AWAY_WINNER') sconfitte_reali_trasferta
	,round(
	100.0 * (count(*) filter (where winner = 'AWAY_WINNER'))/nullif(count(*) filter (where theorical_result = 'AWAY_WINNER'),0)
	,2) percentuale_sconfitte_trasferta

from(
select 
	odds.season
	,odds.home_team
	,odds.away_team
	,case 
		when quota_1 < quota_x and quota_1 < quota_2 then 'HOME_WINNER' 	
		when quota_2 < quota_x and quota_2 < quota_1 then 'AWAY_WINNER'
		else 'DRAW' 
	end theorical_result
	,matches.winner 
from ftb.fact_matches_odds_details odds

inner join ftb.fact_matches matches
	on odds.season = matches.season 
	and odds.home_team = matches."home team"
	and odds.away_team = matches."away team") as mat
group by 
	season
	,away_team
) awaysc

on awaysc.season = home.season  and home.home_team = awaysc.away_team


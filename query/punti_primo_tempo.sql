select *
from
(select 
	tab2.home_team
	,sum(tab2.home_point)
from (
select *
	,case 
		when tab.half_time_winner = 'home winner' then 3 
		when tab.half_time_winner = 'away winner' then 0
		else 1
	end home_point
	,case 
		when tab.half_time_winner = 'home winner' then 0 
		when tab.half_time_winner = 'away winner' then 3
		else 1
	end away_point
	
from(
select 
	m.giornata 
	,m.season 
	,m.home_team 
	,m.away_team 
	,md.winner 
	,md."fullTimeHomeGoal" 
	,md."halfTimeAwayGoal"
	,case
		when md."fullTimeHomeGoal" > md."halfTimeAwayGoal" then 'home winner'
		when md."fullTimeHomeGoal" < md."halfTimeAwayGoal" then 'away winner'
		else 'draw'
	end as half_time_winner
	
from ftb.matches m
inner join ftb.matches_details md 
		on m.match_id = md.match_id
where m.season = 2022 ) as tab) as tab2
group by home_team) as home

inner join(
select 
	tab2.away_team 
	,sum(tab2.away_point)
from (
select *
	,case 
		when tab.half_time_winner = 'home winner' then 3 
		when tab.half_time_winner = 'away winner' then 0
		else 1
	end home_point
	,case 
		when tab.half_time_winner = 'home winner' then 0 
		when tab.half_time_winner = 'away winner' then 3
		else 1
	end away_point
	
from(
select 
	m.giornata 
	,m.season 
	,m.home_team 
	,m.away_team 
	,md.winner 
	,md."fullTimeHomeGoal" 
	,md."halfTimeAwayGoal"
	,case
		when md."fullTimeHomeGoal" > md."halfTimeAwayGoal" then 'home winner'
		when md."fullTimeHomeGoal" < md."halfTimeAwayGoal" then 'away winner'
		else 'draw'
	end as half_time_winner
	
from ftb.matches m
inner join ftb.matches_details md 
		on m.match_id = md.match_id
where m.season = 2022 ) as tab) as tab2
group by away_team) as away
on away.away_team = home.home_team
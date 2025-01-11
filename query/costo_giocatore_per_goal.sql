create view ftb.costo_giocatore_per_goal 
as
-- find the cost of each player per goal scored 
with scorer as ( 
select 
	g.anno
	,g.giornata
	,g."Home Team" 
	,g."Away Team"
	,g.scorer 
	,p."Squadra" as squadra_marcatore
	,p."Market Value" as valore_mercato
	,g.numero_goal_partita
	
from ftb.all_goal_serie_a as g
left join ftb.player_team as p
	on g.anno = p."Season"  and g.scorer = p."Name"     
where scorer is not null
),

tot_goal_scorer as (
select 
	anno
	,squadra_marcatore as squadra
	,scorer as giocatore
	,count(*) as numero_goal 
from scorer 
group by anno,squadra_marcatore ,scorer) 


select 
	s.anno
	,s.squadra
	,s.giocatore
	,s.numero_goal
	,p."Market Value" as valore_mercato
	,round(cast(p."Market Value" as numeric)/nullif(cast(s.numero_goal as numeric), 0), 4) as costo_per_goal
from tot_goal_scorer as s
left join ftb.player_team as p
	on s.anno = p."Season" and s.giocatore = p."Name"  
	
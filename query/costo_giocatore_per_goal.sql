create view ftb.costo_giocatore_per_goal 
as
-- find the cost of each player per goal scored 
with scorer as ( 
select 
	g.anno
	,g.giornata
	,g.home_team 
	,g.away_team
	,g.scorer 
	,p.squadra as squadra_marcatore
	,p.market_value as valore_mercato
	,g.numero_goal_partita
	
from stg.fact_all_goal_serie_a as g
left join stg.dim_player_team as p
	on g.anno = p.stagione  and g.scorer = p.name     
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
	,p.market_value as valore_mercato
	,round(cast(p.market_value as numeric)/nullif(cast(s.numero_goal as numeric), 0), 4) as costo_per_goal
from tot_goal_scorer as s
left join stg.dim_player_team as p
	on s.anno = p.stagione and s.giocatore = p.name  
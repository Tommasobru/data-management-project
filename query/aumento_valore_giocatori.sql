create view ftb.aumento_valore_giocatori
as
select 
    tab.name
    ,tab.eta_iniziale
    ,tab.eta_finale
    ,tab.squadra_iniziale
    ,tab.squadra_finale
    ,tab.ruolo
    ,tab.market_value_iniziale
    ,tab.market_value_finale
    ,round(tab.crescita::int,2)
from(
select 
    dimstart.name
    ,dimstart.eta  as eta_iniziale
    ,dimfin.eta    as eta_finale
    ,dimstart.market_value as market_value_iniziale
    ,dimfin.market_value as market_value_finale
    ,dimstart.squadra as squadra_iniziale
    ,dimfin.squadra as squadra_finale
    ,dimfin.role as ruolo
    ,((dimfin.market_value-dimstart.market_value)/NULLIF(dimstart.market_value,0)*100) as crescita
from ftb.dim_player dimstart

left join (
    select *
    from ftb.dim_player
    where stagione = 2024) dimfin
    on dimfin.name = dimstart.name
where dimstart.stagione = 2021) as tab 
where market_value_iniziale is not null and market_value_finale is not null
order by crescita desc
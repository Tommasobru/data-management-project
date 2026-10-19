create view ftb.aumento_valore_giocatori
as

select 
    tab.name
    ,tab.start_age
    ,tab.final_age
    ,tab.start_team
    ,tab.final_team
    ,tab.role
    ,tab.start_market_value
    ,tab.final_market_value
    ,round(tab.crescita::int,2)
from(
select 
    dimstart.name
    ,dimstart.age  as start_age
    ,dimfin.age    as final_age
    ,dimstart.market_value as start_market_value
    ,dimfin.market_value as final_market_value
    ,dimstart.team as start_team
    ,dimfin.team as final_team
    ,dimfin.role as role
    ,((dimfin.market_value-dimstart.market_value)/NULLIF(dimstart.market_value,0)*100) as crescita
from ftb.dim_player dimstart

left join (
    select *
    from ftb.dim_player
    where season = 2024) dimfin
    on dimfin.name = dimstart.name
where dimstart.season = 2021) as tab 
where start_market_value is not null and final_market_value is not null
order by crescita desc


create view aumento_valore_rosa
as
select 
    dimstart.squadra
    ,dimstart.eta_media                                                                 as eta_media_iniziale
    ,dimfin.eta_media                                                                   as eta_media_finale
    ,dimstart.valore_rosa                                                               as valore_rosa_inziale
    ,dimfin.valore_rosa                                                                 as valore_rosa_finale        
    ,dimstart.giocatori_in_rosa                                                         as giocatori_in_rosa_iniziale
    ,dimfin.giocatori_in_rosa                                                           as giocatori_in_rosa_finale 
    ,dimstart.stranieri                                                                 as numero_stranieri_iniziale
    ,dimfin.stranieri                                                                   as numero_stranieri_finale  
    ,(dimfin.valore_rosa - dimstart.valore_rosa) / (dimstart.valore_rosa) * 100         as incremento_valore_rosa
    ,dimstart.giocatori_in_rosa::int - dimstart.stranieri::int                          as numero_giocatori_italiani_iniziali
    ,dimfin.giocatori_in_rosa::int- dimfin.stranieri::int                               as numero_giocatori_italiani_alla_fine
from ftb.dim_team dimstart
left join (
    select
        squadra
        ,eta_media
        ,valore_rosa
        ,giocatori_in_rosa
        ,stranieri
    from ftb.dim_team 
    where stagione = (select  min(stagione) from ftb.dim_team)
) dimfin
on dimstart.squadra = dimfin.squadra
where dimstart.stagione = (select  max(stagione) from ftb.dim_team) and dimfin.valore_rosa  is not null


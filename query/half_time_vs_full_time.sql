
create view half_time_vs_full_time
as
select 
    dteam.season
    ,team
    ,hteam.tot_pt_half_time_home
    ,hteam.tot_pt_full_time_home
    ,ateam.tot_pt_half_time_away
    ,ateam.tot_pt_full_time_away
    ,hteam.tot_pt_half_time_home + ateam.tot_pt_half_time_away as tot_pt_half_time
    ,hteam.tot_pt_full_time_home + ateam.tot_pt_full_time_away as tot_pt_full_time
from ftb.dim_team dteam
left join(
    select 
        season
        ,home_team
        ,sum(pt_half_time_home) as tot_pt_half_time_home
        ,sum(pt_full_time_home) as tot_pt_full_time_home
    from (
    select 
        season
        ,home_team
        ,away_team
        ,case
            when home_goals_halftime > away_goals_halftime then 3
            when home_goals_halftime < away_goals_halftime then 0
            else 1
        end pt_half_time_home
        ,case
            when winner = 'HOME_WINNER' then 3
            when winner = 'AWAY_WINNER' then 0
            else 1
        end pt_full_time_home
    from ftb.fact_matches matc)
    group by season, home_team) as hteam 
    on dteam.team = hteam.home_team and dteam.season = hteam.season
    
    left join (
    select 
        season
        ,away_team
        ,sum(pt_half_time_away) as tot_pt_half_time_away
        ,sum(pt_full_time_away) as tot_pt_full_time_away
    from (
    select 
        season
        ,home_team
        ,away_team
        ,case
            when home_goals_halftime > away_goals_halftime then 0
            when home_goals_halftime < away_goals_halftime then 3
            else 1
        end pt_half_time_away
        ,case
            when winner = 'HOME_WINNER' then 0
            when winner = 'AWAY_WINNER' then 3
            else 1
        end pt_full_time_away

    from ftb.fact_matches matc)
    group by season, away_team) as ateam
    on ateam.away_team = dteam.team and ateam.season = dteam.season
    
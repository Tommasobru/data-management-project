import yaml
import sqlalchemy as sql
from sqlalchemy import text
import pandas as pd

with open('psw/db.yml', 'r') as f:
    db_file = yaml.safe_load(f)

db_username = db_file['username']
db_psw = db_file['psw']

db_url = f"postgresql+psycopg2://{db_username}:{db_psw}@localhost:5432/STG_football_data"
engine = sql.create_engine(db_url)

with engine.connect() as connection:
    connection.execute(text("DROP VIEW IF EXISTS ftb.integrated_view;"))
    connection.commit()  

player_file = "dataset/clean-player-team.csv"
player_team = pd.read_csv(player_file)
player_team.to_sql('player_team', engine, schema='ftb', if_exists='replace', index=False)

list_team_file = "dataset/clean-list-team.csv"
list_team = pd.read_csv(list_team_file)
list_team.to_sql('list_team', engine, schema='ftb', if_exists='replace', index=False)

calendar_file = "dataset/calendar.csv"
calendar = pd.read_csv(calendar_file)
calendar.to_sql('calendar', engine, schema='ftb', if_exists='replace', index=False)

goal_file = "dataset/clean-serie-a-matches-all-goal.csv"
goal_matches = pd.read_csv(goal_file)
goal_matches.to_sql('all_goal_serie_a', engine, schema='ftb', if_exists='replace', index=False)

scorers_file = "dataset/scorers.csv"
scorers = pd.read_csv(scorers_file)
scorers.to_sql('scorers', engine, schema='ftb', if_exists='replace', index=False)

matches_file = "dataset/matches.csv"
matches = pd.read_csv(matches_file)
matches.to_sql('matches', engine, schema='ftb', if_exists='replace', index=False)

matches_details_file = "dataset/matches_details.csv"
matches_details = pd.read_csv(matches_details_file)
matches_details.to_sql('matches_details', engine, schema='ftb', if_exists='replace', index=False)


with engine.connect() as connection:
    connection.execute(text("""
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
        ,g.numero_goal_partita
        ,g.team_goal
        ,g.goal
        ,g.assist
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

        """

    ))
    connection.commit()

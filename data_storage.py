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

with open('query/conf/query.yml', 'r') as q:
    query = yaml.safe_load(q)
    for item in query['query']:
        for keys, values in item.items():
            with engine.connect() as connection:
                connection.execute(text(f"DROP VIEW IF EXISTS ftb.{keys};"))
                connection.commit()  

player_file = "dataset/clean-player-team.csv"
player_team = pd.read_csv(player_file)
player_team.to_sql('dim_player_team', engine, schema='stg', if_exists='replace', index=False)

list_team_file = "dataset/clean-list-team.csv"
list_team = pd.read_csv(list_team_file)
list_team.to_sql('dim_list_team', engine, schema='stg', if_exists='replace', index=False)

calendar_file = "dataset/calendar.csv"
calendar = pd.read_csv(calendar_file)
calendar.to_sql('dim_calendar', engine, schema='stg', if_exists='replace', index=False)

goal_file = "dataset/clean-serie-a-matches-all-goal.csv"
goal_matches = pd.read_csv(goal_file)
goal_matches.to_sql('fact_all_goal_serie_a', engine, schema='stg', if_exists='replace', index=False)

matches_file = "dataset/matches.csv"
matches = pd.read_csv(matches_file)
matches.to_sql('fact_matches', engine, schema='stg', if_exists='replace', index=False)



'''
with open('query/conf/query.yml', 'r') as q:
    query = yaml.safe_load(q)
    for item in query['query']:
        for keys, values in item.items():
            with open(f'query/{values}', 'r') as sql_file:
                sql_query = sql_file.read()
            with engine.connect() as connection:
                connection.execute(text(sql_query))
                connection.commit()
'''
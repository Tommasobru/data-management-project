import yaml
import sqlalchemy as sql
import pandas as pd

with open('psw/db.yml', 'r') as f:
    db_file = yaml.safe_load(f)

db_username = db_file['username']
db_psw = db_file['psw']

db_url = f"postgresql+psycopg2://{db_username}:{db_psw}@localhost:5432/STG_football_data"
engine = sql.create_engine(db_url)

file = "dataset/clean-player-team.csv"
player_team = pd.read_csv(file)
player_team.to_sql('player_team', engine, schema='dim', if_exists='replace', index=False)
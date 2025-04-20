import yaml
import sqlalchemy as sql
from sqlalchemy import text
import pandas as pd

with open('psw/db.yml', 'r') as f:
    db_file = yaml.safe_load(f)

with open('query/conf/storage.yml', 'r') as l:
    db_storage = yaml.safe_load(l)

db_username = db_file['username']
db_psw = db_file['psw']

db_url = f"postgresql+psycopg2://{db_username}:{db_psw}@localhost:5432/DWH_football"
engine = sql.create_engine(db_url)



with open('query/conf/query.yml', 'r') as q:
    query = yaml.safe_load(q)
    for item in query['query']:
        for keys, values in item.items():
            with engine.connect() as connection:
                connection.execute(text(f"DROP VIEW IF EXISTS ftb.{keys};"))
                connection.commit()  


for file in db_storage['df']:
    for keys,value in file.items():
        df_file = pd.read_csv(f'dataset/clean dataset/{keys}')
        df_file.to_sql(f'{value}', engine, schema = 'ftb', if_exists='replace', index=False)





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
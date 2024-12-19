import requests
import json
import pandas as pd
import yaml 

with open('psw/token.yml', 'r') as f:
    token_file = yaml.safe_load(f)

TOKEN = token_file['TOKEN']



url = 'http://api.football-data.org/v4/competitions/SA/scorers'
headers = { 'X-Auth-Token': TOKEN }

years = ['2022']

for year in years:

    params = {'season':year}
    response = requests.get(url, headers=headers, params=params)    
    if response.status_code != 200:
        print(f"Errore nella richiesta: {response.status_code}")
    

    data = response.json()
    scorers = data.get('scorers',[])

    scorers_data = []

    for scorer in scorers:
        id = scorer['player']['id']
        name = scorer['player']['name']
        date_of_birth = scorer['player']['dateOfBirth']
        nationalaity = scorer['player']['nationality']
        position = scorer['player']['position']
        team_id = scorer['team']['id']
        team = scorer['team']['name']
        goals = scorer['goals']
        assist = scorer['assists']
        penalties = scorer['penalties']
        
        scorers_data.append({
            'id': id,
            'name': name,
            'date_of_birth': date_of_birth,
            'nationality': nationalaity,
            'position': position,
            'team_id': team_id,
            'team': team,
            'goals': goals,
            'assist': assist,
            'penalties': penalties
        })
    

scorers_df = pd.DataFrame(scorers_data)

print(scorers_df)
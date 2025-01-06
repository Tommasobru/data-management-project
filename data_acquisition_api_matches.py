import requests
import json
import pandas as pd
import yaml 

with open('psw/token.yml', 'r') as f:
    token_file = yaml.safe_load(f)

TOKEN = token_file['TOKEN']



url = 'https://api.football-data.org/v4/competitions/SA/matches'
headers = { 'X-Auth-Token': TOKEN }


#params = { 'dateFrom': '2023-01-01', 'dateTo': '2023-12-31' }
years = [2022,2023,2024]

matches_data = []
goals_data =[]

for year in years:
    params = {'season':year}
    response = requests.get(url, headers=headers, params=params)

    if response.status_code != 200:
        print(f"Errore nella richiesta: {response.status_code}")


    data = response.json()
    matches = data.get('matches',[])


    for match in matches:
        match_id = match['id']
        season = year
        date = match['utcDate'].split("T")[0]
        home_team = match['homeTeam']['name']
        away_team = match['awayTeam']['name']
        home_score = match['score']['fullTime']['home']
        away_score = match['score']['fullTime']['away']

        matches_data.append({
            "match_id": match_id,
            "season": season,
            "home_team": home_team,
            "away_team": away_team,
            "home_score": home_score,
            "away_score": away_score
        })

        goal = match.get('score', [])
        winner = goal['winner']
        duration = goal['duration']
        fullTimeHomeGoal = goal['fullTime']['home']
        fullTimeAwayGoal = goal['fullTime']['away']
        halfTimeHomeGoal = goal['halfTime']['home']
        halfTimeAwayGoal = goal['halfTime']['away']

        goals_data.append({
            "match_id" : match_id,
            "season": season,
            "date" : date,
            "winner" : winner,
            "fullTimeHomeGoal" : fullTimeHomeGoal,
            "fullTimeAwayGoal" : fullTimeAwayGoal,
            "halfTimeHomeGoal" : halfTimeHomeGoal,
            "halfTimeAwayGoal" : halfTimeAwayGoal 
        })


    # Crea DataFrame dai dati estratti
    matches_df = pd.DataFrame(matches_data)
    goals_df = pd.DataFrame(goals_data)

# Salva i DataFrame in file CSV (opzionale)
matches_df.to_csv("dataset/matches.csv", index=False)
goals_df.to_csv("dataset/matches_details.csv", index=False)



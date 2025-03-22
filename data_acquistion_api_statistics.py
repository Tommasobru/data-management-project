import requests
import json
import pandas as pd
import yaml 
import time

with open('psw/token.yml', 'r') as f:
    token_file = yaml.safe_load(f)

TOKEN = token_file['TOKEN API FOOTBALL']



url = 'https://v3.football.api-sports.io/fixtures'
url_stat = "https://v3.football.api-sports.io/teams/statistics"
headers = { 'x-rapidapi-key': TOKEN }


#params = { 'dateFrom': '2023-01-01', 'dateTo': '2023-12-31' }
years = [2021,2022,2023]

matches_data = []
stat_data = []
formations_data = []
requests_count = 0

for year in years:
    params = {'season':year
              ,'league': 135}
    response = requests.get(url, headers=headers, params=params)
    requests_count += 1

    if requests_count % 10 == 0:
        time.sleep(60)

    if response.status_code != 200:
        print(f"Errore nella richiesta: {response.status_code}")

    data = response.json()
    matches = data.get('response',[])
    
    diz_id = {}
    for match in matches:
        date = match["fixture"]["date"]
        home_team = match["teams"]["home"]["name"]
        away_team = match["teams"]["away"]["name"]
        home_goals = match["goals"]["home"]
        away_goals = match["goals"]["away"]
        home_goals_halftime = match["score"]["halftime"]["home"]
        away_goals_halftime = match["score"]["halftime"]["away"]
        penalty_home = match["score"]["penalty"]["home"]
        penalty_away = match["score"]["penalty"]["away"]
        id_home = match["teams"]["home"]["id"]


        if id_home not in diz_id:
            diz_id[id_home] = home_team

        matches_data.append({
            "season": year,
            "date": date,
            "home team": home_team,
            "away team":away_team,
            "home goals": home_goals,
            "away goals": away_goals,
            "home goals halftime": home_goals_halftime,
            "away goald halftime": away_goals_halftime,
            "penalty home": penalty_home,
            "penalty away": penalty_away
        })


    for key,value in diz_id.items():
        params_stat = {'season':year
                  ,'league': 135
                  ,'team':key}
        response_stat = requests.get(url_stat, headers=headers, params=params_stat)
        
        requests_count += 1

        if requests_count % 10 == 0:
            time.sleep(60)
        
        if response.status_code != 200:
            print(f"Errore nella richiesta: {response.status_code}")
        
        data_stat = response_stat.json()
        team_stat = data_stat.get('response',[])

        # Estrazione dati
        team_name = team_stat["team"]["name"]
        league = team_stat["league"]["name"]
        country = team_stat["league"]["country"]
        form = team_stat["form"]

        # Partite giocate
        matches = {k: team_stat["fixtures"]["played"][k] for k in ["home", "away", "total"]}
        wins = {k: team_stat["fixtures"]["wins"][k] for k in ["home", "away", "total"]}
        draws = {k: team_stat["fixtures"]["draws"][k] for k in ["home", "away", "total"]}
        loses = {k: team_stat["fixtures"]["loses"][k] for k in ["home", "away", "total"]}

        # Gol segnati e subiti
        goals_for = {k: team_stat["goals"]["for"]["total"][k] for k in ["home", "away", "total"]}
        goals_against = {k: team_stat["goals"]["against"]["total"][k] for k in ["home", "away", "total"]}
        avg_goals_for = {k: team_stat["goals"]["for"]["average"][k] for k in ["home", "away", "total"]}
        avg_goals_against = {k: team_stat["goals"]["against"]["average"][k] for k in ["home", "away", "total"]}

        # Gol e cartellini per minuto
        goal_minutes_for = {k: team_stat["goals"]["for"]["minute"][k]["total"] or 0 for k in team_stat["goals"]["for"]["minute"]}
        goal_minutes_against = {k: team_stat["goals"]["against"]["minute"][k]["total"] or 0 for k in team_stat["goals"]["against"]["minute"]}
        yellow_cards = {k: team_stat["cards"]["yellow"].get(k, {}).get("total", 0) for k in team_stat["cards"]["yellow"]}
        red_cards = {k: team_stat["cards"]["red"].get(k, {}).get("total", 0) for k in team_stat["cards"]["red"]}

        # Under/Over
        over_for = {k: team_stat["goals"]["for"]["under_over"][k]["over"] for k in team_stat["goals"]["for"]["under_over"]}
        under_for = {k: team_stat["goals"]["for"]["under_over"][k]["under"] for k in team_stat["goals"]["for"]["under_over"]}
        over_against = {k: team_stat["goals"]["against"]["under_over"][k]["over"] for k in team_stat["goals"]["against"]["under_over"]}
        under_against = {k: team_stat["goals"]["against"]["under_over"][k]["under"] for k in team_stat["goals"]["against"]["under_over"]}

        # Serie risultati
        streaks = {k: team_stat["biggest"]["streak"][k] for k in team_stat["biggest"]["streak"]}

        # Vittorie e sconfitte più grandi
        biggest_wins = {k: team_stat["biggest"]["wins"].get(k, "N/A") for k in ["home", "away"]}
        biggest_loses = {k: team_stat["biggest"]["loses"].get(k, "N/A") for k in ["home", "away"]}
        biggest_goals_for = {k: team_stat["biggest"]["goals"]["for"].get(k, 0) for k in ["home", "away"]}
        biggest_goals_against = {k: team_stat["biggest"]["goals"]["against"].get(k, 0) for k in ["home", "away"]}

        # Clean sheet e mancati gol
        clean_sheet = {k: team_stat["clean_sheet"][k] for k in ["home", "away", "total"]}
        failed_to_score = {k: team_stat["failed_to_score"][k] for k in ["home", "away", "total"]}

        # Rigori
        penalties = {
            "penalties scored": team_stat["penalty"]["scored"]["total"],
            "penalties missed": team_stat["penalty"]["missed"]["total"],
            "total penalties": team_stat["penalty"]["total"]
        }


        # Creazione riga dati
        row = {
            "season": year,
            "league": league,
            "country": country,
            "team": team_name,
            "form": form,
            **{f"matches_{k}": v for k, v in matches.items()},
            **{f"wins_{k}": v for k, v in wins.items()},
            **{f"draws_{k}": v for k, v in draws.items()},
            **{f"loses_{k}": v for k, v in loses.items()},
            **{f"goals_for_{k}": v for k, v in goals_for.items()},
            **{f"goals_against_{k}": v for k, v in goals_against.items()},
            **{f"avg_goals_for_{k}": v for k, v in avg_goals_for.items()},
            **{f"avg_goals_against_{k}": v for k, v in avg_goals_against.items()},
            **{f"goal_minutes_for_{k}": v for k, v in goal_minutes_for.items()},
            **{f"goal_minutes_against_{k}": v for k, v in goal_minutes_against.items()},
            **{f"yellow_cards_{k}": v for k, v in yellow_cards.items()},
            **{f"red_cards_{k}": v for k, v in red_cards.items()},
            **{f"over_for_{k}": v for k, v in over_for.items()},
            **{f"under_for_{k}": v for k, v in under_for.items()},
            **{f"over_against_{k}": v for k, v in over_against.items()},
            **{f"under_against_{k}": v for k, v in under_against.items()},
            **{f"streaks_{k}": v for k, v in streaks.items()},
            **{f"biggest_wins_{k}": v for k, v in biggest_wins.items()},
            **{f"biggest_loses_{k}": v for k, v in biggest_loses.items()},
            **{f"biggest_goals_for_{k}": v for k, v in biggest_goals_for.items()},
            **{f"biggest_goals_against_{k}": v for k, v in biggest_goals_against.items()},
            **{f"clean_sheet_{k}": v for k, v in clean_sheet.items()},
            **{f"failed_to_score_{k}": v for k, v in failed_to_score.items()},
            **penalties
        }
        stat_data.append(row)
        # create a table with all the formations used by the teams 
        formations = {formation["formation"]: formation["played"] for formation in team_stat["lineups"]}

        for formation in team_stat["lineups"]:
            
            row_formations = {
                "year": year,
                "team": value,
                "formation": formation['formation'],
                "played": formation['played']    
            }
            formations_data.append(row_formations)

        
df_matches = pd.DataFrame(matches_data)
df_stat_team = pd.DataFrame(stat_data)
df_formations = pd.DataFrame(formations_data)
print(match)

print(response)





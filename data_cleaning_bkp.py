import pandas as pd
import difflib  
import numpy as np


def convert_string(string):
    # removes symbols "€" and replace "," with "."
    clean_string = string.replace("€", "").strip().replace(",", ".")

    # check if string contains mln or mila and remove them 
    if "mln" in clean_string:
        # remove "mln" and convert the value to millions
        return float(clean_string.replace("mln", "").strip()) * 1000000
    elif "mila" in clean_string:
        # remove "mila" and convert the value to thousans
        return float(clean_string.replace("mila", "").strip()) * 1000
    elif "-" in clean_string:
        return 0
    else:
        return float(clean_string)

def cleaning_player_data(file):
    # leggi il file 
    df = pd.read_csv(file)

    
    for index, row in df.iterrows():
        name = row['name'].strip().split()
        role = row["role"].strip().split()

        if len(name) + 1 == len(role):
            role_clean = " ".join(role[-1:])
            df.at[index,"role"] = role_clean
        elif len(name) + 2 == len(role):
            role_clean = " ".join(role[-2:])
            df.at[index,"role"] = role_clean
        else:
            role_clean = " ".join(role[-3:])
            df.at[index,"role"] = role_clean
            
    #  apply the function to the whole column
    df['market_value'] = df["market_value"].apply(convert_string)


    return df




def lower_string(word):
    # converts everything to lower case
    word = word.lower()
    return word

def distance_between_string(string1 , string2):
    # converts string to lower case
    lower_string1 = lower_string(string1)
    lower_string2 = lower_string(string2)

    # calculate the difference between string
    d = difflib.Differ()
    diff = list(d.compare(lower_string1,lower_string2))

    # count the number of insertion, deletion or replacement operations
    #distance_count = sum(1 for sim in diff if sim.startswith('-') or sim.startswith('+'))
    distance_count = 0
    # calculate max length between the string
    max_length = max(len(lower_string1), len(lower_string2))

    for i, sim in enumerate(diff):
        if sim.startswith('-') or sim.startswith('+'):  # Modifica, inserzione o cancellazione
            weight = 1.5 if i < 5 else 1  # Pesa di più i primi 3 caratteri
            distance_count += weight  

    # calculate EOD normalized
    normalized_eod = distance_count/max_length 

    return normalized_eod

# find closest string 
def find_closest_string(name, target_string_list):
    if not target_string_list:
        return None
    
    min_normalized = float('inf')
    closest_string = None  

    for name_target in target_string_list:
        normalized_eod = distance_between_string(name,name_target)

        if normalized_eod < min_normalized:
            min_normalized = normalized_eod
            closest_string = name_target

    return closest_string

# function that replaces a team name with the team name taken from the API data
def find_and_replace_name(team_target, diz):
    team = diz[team_target] 

    return team

# function that extract assist-man from details string
def extract_assist_man(details):
    
    if pd.isna(details):
        return None
     
    if "Assist" in details:
        return details.split("Assist:")[1].split(",")[0].strip()
    
    else:
        return None

def create_diz(df, name_column, target_name, split = False,):
    diz = {}
    if split:
        df[['home_team','away_team']] = df[name_column].str.split('-', expand = True)
        for index,row in df.iterrows():
            home_team = row['home_team'].strip()
            team = find_closest_string(home_team, target_name)
            if home_team not in diz:
                diz[home_team] = team

    else:
        for index,row in df.iterrows():
            home_team = row[name_column]

            team = find_closest_string(home_team, target_name)
            if home_team not in diz:
                diz[home_team] = team
    
    return diz

file_player_data = 'dataset/player-team.csv'
file_matches = 'dataset/matches.csv'
file_matches_history = 'dataset/matches_history.csv'
file_serie_a_matches_goal = 'dataset/serie_a_matches_all_goal.csv'
file_lista_team = 'dataset/list-team.csv'
file_odds_per_match = 'dataset/odds_per_match.csv'


df_lista_team = pd.read_csv(file_lista_team)
serie_a_matches_goal  = pd.read_csv(file_serie_a_matches_goal, sep=";")
screaping_team = pd.read_csv(file_player_data)
odds_per_match = pd.read_csv(file_odds_per_match, sep = ";")
matches  = pd.read_csv(file_matches)
matches_history = pd.read_csv(file_matches_history)

# we derive the list of team names taken from the odds data
nomi_squadre = odds_per_match['home_team'].unique().tolist()

# we create a dictionary for each dataframe derived from web scraping where for each team we associate the respective API name, so as to standardize the names 
diz_serie_a_matches_goal = create_diz(serie_a_matches_goal, name_column='partita', target_name=nomi_squadre, split= True)

diz_squadre_player = create_diz(screaping_team, name_column='squadra', target_name=nomi_squadre)

diz_lista_squadre = create_diz(df_lista_team, name_column='squadra', target_name=nomi_squadre)

diz_matches = create_diz(matches,name_column='home_team',target_name=nomi_squadre)

diz_matches_history = create_diz(matches_history, name_column="home team", target_name=nomi_squadre)

# replace all names with names taken from API

serie_a_matches_goal[['home_team','away_team']] = serie_a_matches_goal['partita'].str.split('-', expand=True)
serie_a_matches_goal['home_team'] = serie_a_matches_goal['home_team'].str.strip()
serie_a_matches_goal['away_team'] = serie_a_matches_goal['away_team'].str.strip()
serie_a_matches_goal.drop(columns=['partita'], inplace=True)
serie_a_matches_goal['home_team'] = serie_a_matches_goal['home_team'].apply(lambda team_target: find_and_replace_name(team_target, diz = diz_serie_a_matches_goal)) 
serie_a_matches_goal['away_team'] = serie_a_matches_goal['away_team'].apply(lambda team_target: find_and_replace_name(team_target,diz=diz_serie_a_matches_goal))
serie_a_matches_goal = serie_a_matches_goal.drop_duplicates(subset=['anno', 'giornata', 'home_team','scorer', 'details'])
serie_a_matches_goal['details'] = serie_a_matches_goal['details'].apply(extract_assist_man) 
serie_a_matches_goal = serie_a_matches_goal.rename(columns={'details': 'assist'})
serie_a_matches_goal[['goal_home','goal_away']] = serie_a_matches_goal['goal'].str.split(':', expand=True)
serie_a_matches_goal['goal_home'] = serie_a_matches_goal['goal_home'].astype(float)
serie_a_matches_goal['goal_away'] = serie_a_matches_goal['goal_away'].astype(float)
serie_a_matches_goal = serie_a_matches_goal[['anno','giornata','home_team', 'away_team', 'scorer', 'numero_goal_partita', 'team_goal', 'goal','goal_home','goal_away','assist']]
serie_a_matches_goal.to_csv('dataset/clean dataset/clean_serie_a_matches_all_goal.csv')

df_player_data = cleaning_player_data(file_player_data)
df_player_data['squadra'] = df_player_data['squadra'].apply(lambda team_target: find_and_replace_name(team_target, diz=diz_squadre_player))
df_player_data['eta'] = df_player_data['age'].str.extract(r'\((\d+)\)').astype(int)
df_player_data = df_player_data.drop(columns=['age'])
df_player_data.to_csv('dataset/clean dataset/clean_player_team.csv')


df_lista_team['squadra'] = df_lista_team['squadra'].apply(lambda team_target: find_and_replace_name(team_target, diz=diz_lista_squadre))
df_lista_team['valore_rosa'] = df_lista_team['valore_rosa'].apply(convert_string)
df_lista_team = df_lista_team.drop('link', axis=1)
df_lista_team.to_csv('dataset/clean dataset/clean_list_team.csv')

matches['home_team'] = matches['home_team'].apply(lambda team_target: find_and_replace_name(team_target, diz=diz_matches))
matches['away_team'] = matches['away_team'].apply(lambda team_target: find_and_replace_name(team_target, diz=diz_matches))
matches.dropna(subset=['winner'], inplace = True)
#matches.to_csv('dataset/clean dataset/clean_matches.csv')


matches_history['home team'] = matches_history['home team'].apply(lambda team_target: find_and_replace_name(team_target, diz=diz_matches_history))
matches_history['away team'] = matches_history['away team'].apply(lambda team_target: find_and_replace_name(team_target, diz=diz_matches_history))
matches_history[["round","giornata"]] = matches_history["giornata"].str.split("-", expand=True)
matches_history["home winner"] = matches_history["home winner"].fillna(False) 
matches_history["away winner"] = matches_history["away winner"].fillna(False) 

# Definizione delle condizioni
conditions = [
    (matches_history["home winner"] == True) & (matches_history["away winner"] == False),  # Home vince
    (matches_history["home winner"] == False) & (matches_history["away winner"] == True),  # Away vince
    (matches_history["home winner"] == False) & (matches_history["away winner"] == False)  # Pareggio
]

# Valori da assegnare per ogni condizione
values = ["HOME_WINNER", "AWAY_WINNER", "DRAW"]

# Creazione della nuova colonna 'winner'
matches_history["winner"] = np.select(conditions, values, default="UNKNOWN")  # Se ci sono valori mancanti, restituisce NaN
matches_history = matches_history[["giornata", "season","date","home team", "away team", "winner", "home goals halftime", "away goals halftime", "home goals", "away goals"]]

matches = matches.rename(columns={"home_team":"home team", "away_team":"away team", "half_time_home_score":"home goals halftime", "half_time_away_score": "away goals halftime", "home_score": "home goals", "away_score": "away goals"})

matches = matches[["giornata", "season","date","home team", "away team", "winner", "home goals halftime", "away goals halftime", "home goals", "away goals"]]

matches_all = pd.concat([matches_history,matches], ignore_index=True)
matches_all.to_csv('dataset/clean dataset/clean_matches.csv')

odds_per_match[["home goals", "away goals"]] = odds_per_match['risultato'].str.split('-', expand=True)
odds_per_match[['season', 'hours', 'home_team', 'away_team', 'home goals', 'away goals', 'quota_1','quota_x', 'quota_2']]
odds_per_match.to_csv('dataset/clean dataset/clean_odds_per_match.csv')


print(serie_a_matches_goal)
print(df_player_data)
print(df_lista_team)
#print(diz)


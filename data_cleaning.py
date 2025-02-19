import pandas as pd
import difflib  

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
    distance_count = sum(1 for sim in diff if sim.startswith('-') or sim.startswith('+'))

    # calculate max length between the string
    max_length = max(len(lower_string1), len(lower_string2))

    # calculate EOD normalized
    normalized_eod = distance_count/max_length 

    return normalized_eod

# find closest string 
def find_closest_string(target, string_list):
    if not string_list:
        return None
    
    min_normalized = float('inf')
    closest_string = None  

    for word in string_list:
        normalized_eod = distance_between_string(target,word)

        if normalized_eod < min_normalized:
            min_normalized = normalized_eod
            closest_string = word

    return closest_string

# function that replaces a team name with the team name taken from the API data
def find_and_replace_name(team_target, diz):
    team_api = diz[team_target] 

    return team_api

# function that extract assist-man from details string
def extract_assist_man(details):
    
    if pd.isna(details):
        return None
     
    if "Assist" in details:
        return details.split("Assist:")[1].split(",")[0].strip()
    
    else:
        return None


file_player_data = 'dataset/player-team.csv'
file_matches = 'dataset/matches.csv'
file_serie_a_matches_goal = 'dataset/serie_a_matches_all_goal.csv'
file_lista_team = 'dataset/list-team.csv'

df_lista_team = pd.read_csv(file_lista_team)
squadre_goal  = pd.read_csv(file_serie_a_matches_goal, sep=";")
screaping_team = pd.read_csv(file_player_data)

# we derive the list of team names taken from the api data
api  = pd.read_csv(file_matches)
squadre_api= api['home_team'].unique().tolist()

# we create a dictionary for each dataframe derived from web scraping where for each team we associate the respective API name, so as to standardize the names 
diz_squadre = {}
for index,row in squadre_goal.iterrows():
    squadre = row['partita'].split('-')
    squadra_casa = squadre[0].strip()
    squadra_trasferta = squadre[1].strip()
    

    squadra_api = find_closest_string(squadra_casa,squadre_api)
    if squadra_casa not in diz_squadre:
        diz_squadre[squadra_casa] = squadra_api

diz_squadre_player = {}
for index,row in screaping_team.iterrows():
    squadra_casa_player = row['squadra']
    
    squadra_api_player = find_closest_string(squadra_casa_player,squadre_api)
    if squadra_casa_player not in diz_squadre_player:
        diz_squadre_player[squadra_casa_player] = squadra_api_player

diz_lista_squadre = {}
for index,row in df_lista_team.iterrows():
    team = row['squadra']

    
    squadra_api_team_list = find_closest_string(team,squadre_api)
    if team not in diz_lista_squadre:
        diz_lista_squadre[team] = squadra_api_team_list


# replace all names with names taken from API

squadre_goal[['home_team','away_team']] = squadre_goal['partita'].str.split('-', expand=True)
squadre_goal['home_team'] = squadre_goal['home_team'].str.strip()
squadre_goal['away_team'] = squadre_goal['away_team'].str.strip()
squadre_goal.drop(columns=['partita'], inplace=True)
squadre_goal['home_team'] = squadre_goal['home_team'].apply(lambda team_target: find_and_replace_name(team_target, diz = diz_squadre)) 
squadre_goal['away_team'] = squadre_goal['away_team'].apply(lambda team_target: find_and_replace_name(team_target,diz=diz_squadre))
squadre_goal = squadre_goal.drop_duplicates(subset=['anno', 'giornata', 'home_team','scorer', 'details'])
squadre_goal['details'] = squadre_goal['details'].apply(extract_assist_man) 
squadre_goal = squadre_goal.rename(columns={'details': 'assist'})
squadre_goal[['goal_home','goal_away']] = squadre_goal['goal'].str.split(':', expand=True)
squadre_goal['goal_home'] = squadre_goal['goal_home'].astype(float)
squadre_goal['goal_away'] = squadre_goal['goal_away'].astype(float)
squadre_goal = squadre_goal[['anno','giornata','home_team', 'away_team', 'scorer', 'numero_goal_partita', 'team_goal', 'goal','goal_home','goal_away','assist']]
squadre_goal.to_csv('dataset/clean-serie-a-matches-all-goal.csv')

df_player_data = cleaning_player_data(file_player_data)
df_player_data['squadra'] = df_player_data['squadra'].apply(lambda team_target: find_and_replace_name(team_target, diz=diz_squadre_player))
df_player_data.to_csv('dataset/clean-player-team.csv')


df_lista_team['squadra'] = df_lista_team['squadra'].apply(lambda team_target: find_and_replace_name(team_target, diz=diz_lista_squadre))
df_lista_team['valore_rosa'] = df_lista_team['valore_rosa'].apply(convert_string)
df_lista_team = df_lista_team.drop('link', axis=1)
df_lista_team.to_csv('dataset/clean-list-team.csv')


print(squadre_goal)
print(df_player_data)
print(df_lista_team)
#print(diz)
print(squadre_api)

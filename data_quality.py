import pandas as pd
import difflib  

def lower_string(word):
    # Controlla se il valore è una stringa, altrimenti restituisce una stringa vuota
    if isinstance(word, str):
        return word.lower().strip()
    else:
        return ""


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

    # calculate ED normalized
    normalized_ed = distance_count/max_length 

    return normalized_ed


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

    return closest_string,min_normalized

def unique_id(column):
    if column.is_unique:
        print("Gli ID sono unici.")
    else:
        print("Gli ID non sono unici.")

def count_nulls_per_column(df):
    """
    Calcola il numero di valori nulli per ogni colonna in un DataFrame.

    Parametri:
        df (pd.DataFrame): Il DataFrame da analizzare.

    Ritorna:
        pd.DataFrame: DataFrame con due colonne: 'Column' e 'Null Count',
                      che mostrano il nome della colonna e il numero di valori nulli.
    """
    null_counts = df.isnull().sum()
    result = pd.DataFrame({'Column': null_counts.index, 'Null Count': null_counts.values})
    print(result)
    return result


file_player_team = 'dataset/player-team.csv'
file_matches = 'dataset/matches.csv'
file_matches_details = 'dataset/matches_details.csv'
file_serie_a_matches_goal = 'dataset/serie_a_matches_all_goal.csv'
file_lista_team = 'dataset/list-team.csv'

api_matches = pd.read_csv(file_matches)
api_matches_details = pd.read_csv(file_matches_details)
scraping_serie_a_matches_goal = pd.read_csv(file_serie_a_matches_goal, sep=";")
scraping_lista_team = pd.read_csv(file_lista_team)
scraping_player_team = pd.read_csv(file_player_team)

scraping_serie_a_matches_goal[['Home Team','Away Team']] = scraping_serie_a_matches_goal['partita'].str.split('-', expand=True)

unique_id(api_matches['match_id'])
unique_id(api_matches_details['match_id'])

count_nulls_per_column(api_matches)
count_nulls_per_column(api_matches_details)
count_nulls_per_column(scraping_serie_a_matches_goal)
count_nulls_per_column(scraping_lista_team)
count_nulls_per_column(scraping_player_team)

scraping_team = scraping_serie_a_matches_goal['Home Team'].unique().tolist()
api_team = api_matches['home_team'].unique().tolist()
for team in scraping_team:
    team_api, dist = find_closest_string(team, api_team)
    print("##########################")
    print("")
    print(team)
    print("")
    print(team_api) 
    print("")
    print(f"distanza:  {dist}")
    print("")


scraping_player = scraping_player_team['Name'].unique().tolist()
scraping_scorer = scraping_serie_a_matches_goal['scorer'].unique().tolist()

for player in scraping_scorer:
    if player != "NaN":
        player_closest, dist_player = find_closest_string(player, scraping_player)
        print("##########################")
        print("")
        print(player)
        print("")
        print(player_closest) 
        print("")
        print(f"distanza:  {dist_player}")
        print("")


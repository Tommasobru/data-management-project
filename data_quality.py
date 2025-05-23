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


file_player_team = 'dataset/clean dataset/clean_player_team.csv'
file_matches = 'dataset/clean dataset/clean_matches.csv'
file_lista_team = 'dataset/clean dataset/clean_list_team.csv'
file_odds_team = 'dataset/clean dataset/clean_odds_per_match.csv'

api_matches = pd.read_csv(file_matches)
scraping_lista_team = pd.read_csv(file_lista_team)
scraping_player_team = pd.read_csv(file_player_team)
scraping_odds_team = pd.read_csv(file_odds_team)
#scraping_serie_a_matches_goal[['home_team','away_team']] = scraping_serie_a_matches_goal['partita'].str.split('-', expand=True)

##### CONSISTENCY
#unique_id(api_matches['match_id'])



##### COMPLETENESS
count_nulls_per_column(api_matches) 
# null value are the matches that have yet to be played 


# null values are for games in which no goals were scored
count_nulls_per_column(scraping_lista_team)
count_nulls_per_column(scraping_player_team)

#### SYNTACTIC ACCURACY
scraping_team = scraping_lista_team['team'].unique().tolist()
api_teams = api_matches['home_team'].unique().tolist()

for team in scraping_team:
    team_api, dist = find_closest_string(team, api_teams)
    print("##########################")
    print("")
    print(team)
    print("")
    print(team_api) 
    print("")
    print(f"distanza:  {dist}")
    print("")


odds_team = scraping_odds_team['home_team'].unique().tolist()
for team in odds_team:
    team_api, dist = find_closest_string(team, api_teams) 
    print("##########################")
    print("")
    print(team)
    print("")
    print(team_api) 
    print("")
    print(f"distanza:  {dist}")
    print("")









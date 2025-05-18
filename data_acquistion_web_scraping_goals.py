import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

# URL della pagina
url = "https://www.transfermarkt.it/spielbericht/index/spielbericht/4374060"

# Headers per simulare un browser
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

# funzione per ottenere il link relativo alla pagina "calendario per competizione" per ogni squadra e per ogni anno
def url_calendario_per_competizione(url):
    
    segments = url.split('/')
    index_verein = segments.index('verein')
    id = segments[index_verein+1]
    anno = segments[-1]
    url_calendario = f'https://www.transfermarkt.it/inter-mailand/spielplan/verein/{id}/saison_id/{anno}'
    return url_calendario


def check_miss_match(df):
    anni = [2021,2022,2023,2024]
    partite_mancanti = []
    for anno in anni:
        for giornata in range(1,39):
            n_partite = df[(df['year'] == anno) & (df['matchday']==giornata)].groupby(['year','matchday']).size().reset_index(name='conteggio')
            if n_partite != 10:
                partite_mancanti.append({'year':anno,'matchday':giornata})
            else:
                continue

# funzione per estrarre i goal di ogni giornata 
def extract_match_goals(match_url, giornata, anno, home_team, away_team, check = False, lista_check = None):

    # Richiesta alla pagina
    response = requests.get(match_url, headers=headers)
    if check == False:
        # Controllo del successo della richiesta
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, "html.parser")

            # Trovare la sezione dei gol
            goal_section = soup.find("div", id="sb-tore")
            if goal_section:
                goals = []
                numero_goal_partita = 0 # inizializzo il contatore dei goal
                for goal in goal_section.find_all("li", class_=["sb-aktion-heim", "sb-aktion-gast"]):
                    try:
                        if "sb-aktion-heim" in goal['class']:
                            team_goal = "home"
                        elif "sb-aktion-gast" in goal['class']:    
                            team_goal = "away"
                        
                        numero_goal_partita +=1
                        # Estrarre il marcatore
                        scorer = goal.find("a", class_="wichtig").get_text(strip=True)
                        # Goal segnato
                        numero_goal = goal.find("div", class_="sb-aktion-spielstand").get_text(strip = True)
                        # Estrarre il tipo di azione (es. rigore, tiro, ecc.)
                        action_details = goal.find("div", class_="sb-aktion-aktion").get_text(strip=True)
                        # Aggiungere alla lista
                        goals.append({"year": anno,"matchday": giornata, "home_team": home_team,"away_team":away_team ,"scorer": scorer,"n_goal":numero_goal_partita,"team_goal":team_goal ,"goal":numero_goal, "details": action_details})
                    except AttributeError:
                        continue
                
            else:
                goals = [{"year": anno,"matchday": giornata, "home_team": home_team,"away_team":away_team ,"scorer": scorer,"n_goal":numero_goal_partita,"team_goal":team_goal ,"goal":numero_goal, "details": action_details}]
            
            return goals
        else:
            print(f"Errore nel caricamento della pagina, codice: {response.status_code}")
    else:
        for diz in lista_check:
            



def estrazione_url_match(url):
    response = requests.get(url,headers=headers)
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, "html.parser")
        table = soup.find('div', class_='responsive-table')
        return table
    else:
        print(f"Errore nella richiesta: {response.status_code} per {url}")
        return None


all_goals = []
anni = [2021,2022,2023,2024]

url_base = 'https://www.transfermarkt.it'
for anno in anni:

    for giornata in range(1,39):
       #time.sleep(5)
       url_giornata = f"https://www.transfermarkt.it/serie-a/spieltagtabelle/wettbewerb/IT1?saison_id={anno}&spieltag={giornata}"
       table = estrazione_url_match(url_giornata)
       rows = table.find_all("tr")
        # salta le righe di intestazione
       for row in rows:
            if row.find("th"):
                continue
    
            # Estrai squadra di casa
            td_casa = row.find('td', class_='text-right no-border-rechts no-border-links hauptlink hide-for-small')
            squadra_casa = td_casa.find('a').text.strip() if td_casa and td_casa.find('a') else "N/D"

            # Estrai squadra ospite
            td_trasferta = row.find('td', class_='no-border-links no-border-rechts hauptlink hide-for-small')
            squadra_trasferta = td_trasferta.find('a').text.strip() if td_trasferta and td_trasferta.find('a') else "N/D"

            td = row.find('td', class_='zentriert hauptlink ergebnis')
            if td is None:
                continue  # Salta righe che non hanno quella colonna
            a_tag = td.find('a')
            risultato = td.find(class_="matchresult finished")
            if a_tag is None:
                continue  # Se il link non esiste, salta
            print(squadra_casa)
            print(squadra_trasferta)
            url_part = a_tag['href']
            url = url_base+url_part
            all_goals.extend(extract_match_goals(url,giornata,anno,squadra_casa,squadra_trasferta))

all_goals_df = pd.DataFrame(all_goals)
all_goals_df.to_csv("dataset/serie_a_matches_all_goal_prova.csv", index= False, sep = ';')

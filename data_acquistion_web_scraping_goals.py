import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random


# Headers per simulare un browser
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://www.google.com/"
}
url = 'https://fbref.com/it/comp/11/calendario/Risultati-e-partite-di-Serie-A'
# Funzione di richiesta sicura con retry
def safe_request_loop(url, headers):
    attempt = 0
    while True:
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                print('Nessun errore')
                return response
            else:
                print(f"Errore {response.status_code} - ritento...")
        except Exception as e:
            print(f"Eccezione nella richiesta: {e} - ritento...")

        # Attendi prima di riprovare
        wait_time = min(60, 2 ** attempt + random.uniform(0, 2))
        print(f"Aspetto {wait_time:.2f} secondi prima del tentativo successivo...")
        time.sleep(wait_time)
        attempt += 1


# Inserisci il tuo HTML in questa variabile (come stringa)
html = """[INCOLLA QUI IL TUO HTML]"""

soup = BeautifulSoup(html, 'html.parser')

# Estrazione squadre e risultato
teams = soup.find_all("a", title=True)
team_home = teams[0].text.strip()
team_away = teams[2].text.strip()

# Risultato finale
result = soup.find("span", class_="matchresult").text.strip()

# DataFrame per la partita
match_df = pd.DataFrame([{
    'Squadra Casa': team_home,
    'Squadra Trasferta': team_away,
    'Risultato Finale': result
}])

# Estrazione eventi gol
goal_rows = soup.find_all("tr", class_="spieltagsansicht-aktionen")

goal_data = []

for row in goal_rows:
    tds = row.find_all("td")
    if len(tds) < 5:
        continue
    
    minute = tds[1].text.strip().replace("'", "")
    goal_result = tds[2].text.strip()

    # Chi ha segnato
    scorer_tag = row.find("a", href=True)
    if not scorer_tag:
        continue
    scorer = scorer_tag.text.strip()

    # Determina squadra in base a posizione del nome
    if tds[0].text.strip():  # Nome a sinistra
        scoring_team = team_home
    elif tds[4].text.strip():  # Nome a destra
        scoring_team = team_away
    else:
        scoring_team = "Sconosciuta"

    goal_data.append({
        'Giocatore': scorer,
        'Minuto': int(minute),
        'Squadra': scoring_team,
        'Risultato Goal': goal_result
    })

# DataFrame per i gol
goals_df = pd.DataFrame(goal_data)

# Output
print("Dati partita:")
print(match_df)
print("\nEventi gol:")
print(goals_df)


def extract_match_goals(match_url, giornata, anno, partita):

    # Richiesta alla pagina
    response = requests.get(match_url, headers=headers)

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
                    goals.append({"anno": anno,"giornata": giornata, "partita": partita ,"scorer": scorer,"numero_goal_partita":numero_goal_partita,"team_goal":team_goal ,"goal":numero_goal, "details": action_details})
                except AttributeError:
                    continue
            
        else:
            goals = [{"anno": anno, 'giornata': giornata, "partita": partita, "scorer": "NaN","numero_goal_partita":"NaN", "team_goal" : "NaN","goal":"NaN", "details": "NaN"}]
        
        return goals
    else:
        print(f"Errore nel caricamento della pagina, codice: {response.status_code}")
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

response = safe_request_loop(url, headers)
soup = BeautifulSoup(response.text, "html.parser")
table = soup.find("table", class_ = "stats_table sortable min_width now_sortable")

rows = table.find("tbody").find_all("tr")
report_links = []
for row in rows:
    cell = row.find("td", {"data-stat": "match_report"})
    if cell and cell.a:
        href = cell.a.get("href")
        full_url = requests.compat.urljoin(url, href)
        report_links.append(full_url)



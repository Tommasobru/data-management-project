import requests
from bs4 import BeautifulSoup
import pandas as pd
from scraping import link_squadre
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

# funzione per estrarre i goal di ogni giornata 
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
            for goal in goal_section.find_all("li", class_=["sb-aktion-heim", "sb-aktion-gast"]):
                try:
                    # Estrarre il marcatore
                    scorer = goal.find("a", class_="wichtig").get_text(strip=True)
                    # Estrarre il tipo di azione (es. rigore, tiro, ecc.)
                    action_details = goal.find("div", class_="sb-aktion-aktion").get_text(strip=True)
                    # Aggiungere alla lista
                    goals.append({"anno": anno,"giornata": giornata, "partita": partita ,"scorer": scorer, "details": action_details})
                except AttributeError:
                    continue
            
        else:
            goals = [{"anno": anno, 'giornata': giornata, "partita": partita, "scorer": "NAN", "details": "NAN"}]
        
        return goals
    else:
        print(f"Errore nel caricamento della pagina, codice: {response.status_code}")


# Funzione per estrarre i link delle partite giocate (solo Serie A con conferma dal contesto)
def get_serie_a_matches_links(base_url, squadra,anno):
    response = requests.get(base_url, headers=headers)
    serie_a_matches = []
    lista_diz =[]
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, "html.parser")
        # Trova la sezione Serie A
        serie_a_section = soup.find("a", {"name": "IT1"})
        if serie_a_section:
            table = serie_a_section.find_next("div", class_="responsive-table")
            if table:
                rows = table.find_all("tr")
                for row in rows:
                    # salta le righe di intestazione
                    if row.find("th"):
                        continue
                    # Trova il numero della giornata
                    giornata_cell = row.find("td", class_="zentriert")
                    luogo = row.find('td', class_='zentriert hauptlink').get_text(strip = True)  # Trova il <td> con la classe specificata
                    avversario = row.find('td', class_='no-border-links hauptlink').get_text(strip = True)
                    avversario = avversario.split('(')[0].strip() 

                    # creiamo il campo partita                    
                    if luogo == "C":
                        partita = squadra + " - " + avversario
                    else:
                        partita = avversario + " - " + squadra
                    
                    if giornata_cell:
                        giornata_link = giornata_cell.find("a")
                        if giornata_link and giornata_link.text.isdigit():
                            numero_giornata = int(giornata_link.text)  # Converti il numero in intero
                        else:
                            numero_giornata = None

                    # Trova il link della partita
                    match = row.find("a", class_="ergebnis-link")
                    if match:
                        match_href = match.get("href")
                        if match_href:
                            full_url = "https://www.transfermarkt.it" + match_href
                            serie_a_matches.append(full_url)
                            # Aggiungi giornata e link a un dizionario
                            lista_diz.append({"anno": anno,"giornata": numero_giornata, "partita": partita, "link": full_url})

    

    urls_df = pd.DataFrame(lista_diz)
    return lista_diz, urls_df


all_goals = []
anni = [2022,2023,2024]

for anno in anni:

    df_link_squadre = link_squadre(anno)

    
    for index, row in df_link_squadre.iterrows():
        squadra = row['Squadra'] 
        url = row["Link"]
        url_calendario_partite = url_calendario_per_competizione(url)
        anno = row['Stagione']
        lista_diz, urls_df = get_serie_a_matches_links(url_calendario_partite, squadra, anno)
        for index,row in urls_df.iterrows():
            all_goals.extend(extract_match_goals(row['link'], row['giornata'], row['anno'], row['partita']))

all_goals_df = pd.DataFrame(all_goals)
all_goals_df.to_csv("serie_a_matches_link.csv", index= False, sep = ';')
lista_df = pd.DataFrame(lista_diz)
lista_df.to_csv("lista.csv", index= False, sep = ';')
print(all_goals_df)
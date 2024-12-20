import requests
from bs4 import BeautifulSoup
import pandas as pd


def link_squadre(anno):
    # URL della pagina della Serie A
    #url = "https://www.transfermarkt.it/serie-a/startseite/wettbewerb/IT1"

    url = f"https://www.transfermarkt.it/serie-a/startseite/wettbewerb/IT1/plus/?saison_id={anno}"
    # Headers per simulare una richiesta da browser
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    # Effettua la richiesta HTTP
    response = requests.get(url, headers=headers)

    # Controlla se la richiesta è andata a buon fine
    if response.status_code != 200:
        print(f"Errore nel caricamento della pagina: {response.status_code}")
        exit()

    # Parsing del contenuto HTML
    soup = BeautifulSoup(response.text, 'html.parser')

    # Trova la tabella delle squadre
    table = soup.find("table", class_="items")

    # Controlla se la tabella è stata trovata
    if not table:
        print("Tabella non trovata.")
        exit()

    # Trova tutte le righe della tabella
    rows = table.find("tbody").find_all("tr")

    # Lista per salvare i dati delle squadre
    teams = []

    # Itera sulle righe della tabella
    for row in rows:
        try:
            # Nome della squadra e link
            team_cell = row.find("td", class_="hauptlink no-border-links")
            team_name = team_cell.a.text.strip()
            team_link = f"https://www.transfermarkt.it{team_cell.a['href']}"

            # Numero di giocatori in rosa
            squad_size = row.find_all("td", class_="zentriert")[1].text.strip()

            # Età media
            avg_age = row.find_all("td", class_="zentriert")[2].text.strip()

            # Numero di stranieri
            foreigners = row.find_all("td", class_="zentriert")[3].text.strip()

            # Valore della rosa
            squad_value = row.find_all("td", class_="rechts")[1].text.strip()

            # Aggiungi i dati alla lista
            teams.append({
                "Squadra": team_name,
                "Link": team_link,
                "Giocatori in Rosa": squad_size,
                "Età Media": avg_age,
                "Stranieri": foreigners,
                "Valore Rosa": squad_value
            })
        except Exception as e:
            print(f"Errore nell'elaborazione di una riga: {e}")

    # Salva i risultati in un file CSV
    df = pd.DataFrame(teams)
    #df.to_csv("squadre_serie_a_completo.csv", index=False)
    return df



years = [2022,2023,2024]

for year in years:
    df_link = link_squadre(year)


    df_list = []
    for index, row in df_link.iterrows(): 
        # Headers per simulare una richiesta da un browser
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        url = row['Link']

        squadra = row['Squadra']
        # Effettua la richiesta HTTP
        response = requests.get(url, headers=headers)

        # Controlla se la richiesta ha avuto successo
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')

            # Trova la tabella dei giocatori
            table = soup.find('table', {"class": "items"})

            # Lista per salvare i dati
            players = []

            if table:
                rows = table.find('tbody').find_all('tr', class_=["odd", "even"])  # Righe pari e dispari
                for row in rows:
                    # Nome del giocatore
                    name_cell = row.find('td', {"class": "hauptlink"})
                    name = name_cell.text.strip() if name_cell else None

                    # Ruolo del giocatore
                    role_cell = row.find('td', {"class": "posrela"})
                    role = role_cell.text.strip() if role_cell else None

                    # Valore di mercato
                    market_value_cell = row.find('td', {"class": "rechts hauptlink"})
                    market_value = market_value_cell.text.strip() if market_value_cell else None

                    # Aggiungi i dati alla lista
                    players.append({
                        "Name": name,
                        "Role": role,
                        "Market Value": market_value
                    })

                # Creazione di un DataFrame
                df = pd.DataFrame(players)

                df['Squadra'] = squadra 
                df_list.append(df)           


            else:
                print("Tabella dei giocatori non trovata.")
        else:
            print(f"Errore nella richiesta: {response.status_code}")

    # Salva i dati in un file CSV
    df = pd.concat(df_list)
    nome_file = f"player_data-{year}.csv"
    #df.to_csv(nome_file, index=False)
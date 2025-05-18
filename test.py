import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Referer": "https://www.google.com/",
    "Connection": "keep-alive"
}


anni = [2021,2022,2023,2024]


def estrazione_url_match(url):
    response = requests.get(url,headers=headers)
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, "html.parser")
        table = soup.find('div', class_='responsive-table')
        return table
    else:
        print(f"Errore nella richiesta: {response.status_code} per {url}")
        return None

for anno in anni:

    for giornata in range(1,39):
       time.sleep(5)
       url_giornata = f"https://www.transfermarkt.it/serie-a/spieltagtabelle/wettbewerb/IT1?saison_id={anno}&spieltag={giornata}"
       table = estrazione_url_match(url_giornata)
       rows = table.find_all("tr")
        # salta le righe di intestazione
       for row in rows:
            if row.find("th"):
                continue
            
            td = row.find('td', class_='zentriert hauptlink ergebnis')
            if td is None:
                continue  # Salta righe che non hanno quella colonna
            a_tag = td.find('a')
            risultato = td.find(class_="matchresult finished")
            if a_tag is None:
                continue  # Se il link non esiste, salta

            url_part = a_tag['href']

       print(table)
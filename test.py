import requests
from bs4 import BeautifulSoup
import pandas as pd
from data_acquisition_web_scraping import link_squadre
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
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, "html.parser")
        table = soup.find('div', class_='responsive-table')
        return table
    else:
        print(f"Errore nella richiesta: {response.status_code} per {url}")
        return None

for anno in anni:
    print(1)
    for giornata in range(1,39):
       time.sleep(5)
       url_giornata = f"https://www.transfermarkt.it/serie-a/spieltagtabelle/wettbewerb/IT1?saison_id={anno}&spieltag={giornata}"
       table = estrazione_url_match(url_giornata)
       print(table)
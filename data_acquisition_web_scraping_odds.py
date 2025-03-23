from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import time

diz_anni = {
    2024: 'serie-a',
    2023: 'serie-a-2023-2024',
    2022: 'serie-a-2022-2023',
    2021: 'serie-a-2021-2022'
}

lista_quote = []

def estrazione_dati(container,body,wait,season):
    try:
        #container = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-v-b8d70024]")))
        # Scroll della pagina per caricare tutti i match
        for _ in range(5):  # Scrolla 5 volte per caricare tutti i contenuti
            body.send_keys(Keys.PAGE_DOWN)
            time.sleep(2)
        partite = container.find_elements(By.CSS_SELECTOR,".group.flex")
        
        for partita in partite:
            diz ={}
            print(partita.text)
            righe = partita.text.split('\n')
            if len(righe) >= 7:
                hours = righe[0]
                home_team = righe[1]
                away_team = righe[5]
                risultato = righe[2] + '-' + righe[4]
                quota_1 = righe[6]
                quota_x = righe[7]
                quota_2 = righe[8]

            diz = {
                'season' : season,
                'hours' : hours,
                'home_team': home_team,
                'away_team': away_team,
                'risultato': risultato,
                'quota_1' : quota_1,
                'quota_x' : quota_x,
                'quota_2' : quota_2
            }
            lista_quote.append(diz)

    except Exception as e:
        print(f"errore durante l'estrazione dei dati: {e}")

def navigazione_e_estrazione(diz_anni):  
    driver = webdriver.Firefox()

    diz_quote = {}
    for key,value in diz_anni.items():    

        driver.get(f"https://www.oddsportal.com/it/football/italy/{value}/results/#/page/1/")

        time.sleep(10)


        wait = WebDriverWait(driver,15)
        #container = driver.find_element(By.CSS_SELECTOR, "div[data-v-0ba76030]")
        
        container = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR,  "div.min-h-\\[80vh\\]")))

        # Trova il body per inviare comandi di scrolling
        body = driver.find_element(By.TAG_NAME, "body")

        try:
            wait = WebDriverWait(driver, 10)
            reject_button = wait.until(EC.element_to_be_clickable((By.ID, "onetrust-reject-all-handler")))
            reject_button.click()
            print("Bottone cliccato con successo!")
        except Exception as e:
            print("Errore nel cliccare il bottone:", e)



        pagination_links = driver.find_elements(By.CSS_SELECTOR, ".pagination-link[data-number]")



        for i in range(len(pagination_links)):
            try:
                if "active" not in pagination_links[i].get_attribute("class"):
                    driver.execute_script("arguments[0].scrollIntoView();", pagination_links[i])
                    time.sleep(1)

                                # Attendi che l'elemento sia effettivamente cliccabile
                    WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable(pagination_links[i]))

                    # Clicca sulla pagina successiva
                    pagination_links[i].click()
                    time.sleep(5) 

                    
                # Aggiorna la lista degli elementi della paginazione (potrebbero cambiare dopo il clic)
                pagination_links = driver.find_elements(By.CSS_SELECTOR, ".pagination-link[data-number]")


                #driver.execute_script("arguments[0].scrollIntoView();", pagination_links[i])
                #time.sleep(1)
                ## Clicca sulla pagina successiva
                #pagination_links[i].click()
                #time.sleep(5)  # Attendi il caricamento della nuova pagina

                print(f"🔄 Estrazione dati dalla pagina {i + 1}")
                estrazione_dati(container,body,wait,key)
            except Exception as e:
                print(f"Errore nel cambio pagina {i + 1}: {e}")

        # Stampa tutti i dati estratti
        for match, info in diz_quote.items():
            print(match, info)

    # Chiudi il browser
    driver.quit()

navigazione_e_estrazione(diz_anni)

df_quote = pd.DataFrame(lista_quote)
df_quote.to_csv("dataset/odds_per_match.csv", index= False, sep = ';')
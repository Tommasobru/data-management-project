from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import time

driver = webdriver.Firefox()

driver.get("https://www.oddsportal.com/it/football/italy/serie-a/results/#/page/1/")

time.sleep(10)


diz_quote = {}
wait = WebDriverWait(driver,15)
container = driver.find_element(By.CSS_SELECTOR, "div[data-v-b8d70024]")

# Trova il body per inviare comandi di scrolling
body = driver.find_element(By.TAG_NAME, "body")

try:
    wait = WebDriverWait(driver, 10)
    reject_button = wait.until(EC.element_to_be_clickable((By.ID, "onetrust-reject-all-handler")))
    reject_button.click()
    print("Bottone cliccato con successo!")
except Exception as e:
    print("Errore nel cliccare il bottone:", e)



partite = container.find_elements(By.CSS_SELECTOR,".group.flex")
for partita in partite:
    print(partita.text)


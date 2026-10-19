"""OddsPortal - web scraping delle quote 1X2 (media dei bookmaker) con Selenium.

La pagina dei risultati è un'applicazione JavaScript: le partite delle pagine 2..N
arrivano tramite chiamate AJAX cifrate, quindi serve un browser vero.
Dall'Italia OddsPortal reindirizza al mirror centroquote.it (stessa struttura).

Requisiti: `pip install selenium` e Google Chrome (default) oppure Firefox
(`browser: firefox` in config/settings.yaml). Il driver viene scaricato
automaticamente da Selenium Manager.
"""
from __future__ import annotations

import re
import time

import pandas as pd

from football_pipeline.acquisition.base import Source, SourceUnavailable, current_season
from football_pipeline.config import get_settings
from football_pipeline.utils.logging import get_logger

log = get_logger(__name__)

URL = "https://www.oddsportal.com/it/football/italy/{path}/results/#/page/{page}/"
MAX_PAGES = 10
USER_AGENT = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36")
# riga partita = contenitore che include il link alla pagina head-to-head
ROW_XPATH = ("//a[contains(@href,'/h2h/') or contains(@href,'/football/italy/')]"
             "/ancestor::div[contains(@class,'items-stretch') and contains(@class,'border-b')][1]")
DASHES = {"-", "–", "—"}
_TIME = re.compile(r"^\d{1,2}:\d{2}$")
_ODDS = re.compile(r"^\d+(\.\d+)?$")


def season_path(season: int) -> str:
    return "serie-a" if season == current_season() else f"serie-a-{season}-{season + 1}"


def parse_match_text(text: str, season: int) -> dict | None:
    """Interpreta il testo di una riga partita. Gestisce i due layout del sito:

    - attuale:  'Finita | 0 | Cremonese | - | Torino | 0 | 2.95 | 3.20 | 2.65'
    - 2024/25:  '20:45 | Atalanta | 2 | – | 3 | Como | 1.50 | 4.47 | 6.18'
    """
    tokens = [t.strip() for t in text.split("\n") if t.strip()]
    dash = next((i for i, t in enumerate(tokens) if t in DASHES), None)
    if dash is None or dash < 2 or dash + 2 >= len(tokens):
        return None
    odds = [t for t in tokens[dash + 1:] if _ODDS.match(t) and "." in t][-3:]
    if len(odds) != 3:
        return None
    if tokens[dash - 1].isdigit():   # layout 2024/25: casa, gol, -, gol, ospite
        home, hg, ag, away = tokens[dash - 2], tokens[dash - 1], tokens[dash + 1], tokens[dash + 2]
    else:                             # layout attuale: gol, casa, -, ospite, gol
        hg, home, away, ag = tokens[dash - 2], tokens[dash - 1], tokens[dash + 1], tokens[dash + 2]
    if not (hg.isdigit() and ag.isdigit()):
        return None  # partita rinviata/annullata o senza risultato
    return {
        "season": season,
        "hours": next((t for t in tokens[:dash] if _TIME.match(t)), None),
        "home_team": home,
        "away_team": away,
        "risultato": f"{hg}-{ag}",
        "quota_1": odds[0],
        "quota_x": odds[1],
        "quota_2": odds[2],
    }


def _driver(browser: str):
    try:
        from selenium import webdriver
    except ImportError as exc:
        raise SourceUnavailable("selenium non installato (pip install selenium)") from exc
    try:
        if browser == "firefox":
            opts = webdriver.FirefoxOptions()
            opts.add_argument("-headless")
            opts.set_preference("general.useragent.override", USER_AGENT)
            return webdriver.Firefox(options=opts)
        opts = webdriver.ChromeOptions()
        opts.add_argument("--headless=new")
        opts.add_argument("--window-size=1400,3000")
        opts.add_argument(f"--user-agent={USER_AGENT}")
        # senza queste opzioni il sito serve una pagina anti-bot a Chrome headless
        opts.add_argument("--disable-blink-features=AutomationControlled")
        opts.add_experimental_option("excludeSwitches", ["enable-automation"])
        return webdriver.Chrome(options=opts)
    except Exception as exc:  # noqa: BLE001 - browser assente o driver non scaricabile
        raise SourceUnavailable(f"impossibile avviare {browser}: {exc}") from exc


def _accept_cookies(driver) -> None:
    from selenium.webdriver.common.by import By
    for element_id in ("onetrust-reject-all-handler", "onetrust-accept-btn-handler"):
        try:
            driver.find_element(By.ID, element_id).click()
            return
        except Exception:  # noqa: BLE001 - banner già chiuso o assente
            continue


def _rows(driver) -> list[tuple[str, str]]:
    """(id evento, testo) di ogni riga partita visibile."""
    from selenium.webdriver.common.by import By

    out = []
    for row in driver.find_elements(By.XPATH, ROW_XPATH):
        try:
            href = row.find_element(By.TAG_NAME, "a").get_attribute("href") or ""
            out.append((href.rsplit("#", 1)[-1] if "#" in href else href, row.text))
        except Exception:  # noqa: BLE001 - riga rimossa dal DOM durante la lettura
            continue
    return out


def _load_all_rows(driver) -> list[tuple[str, str]]:
    """Scorre la pagina finché il numero di righe smette di crescere (lazy loading)."""
    previous = -1
    for _ in range(15):
        rows = _rows(driver)
        if len(rows) == previous:
            return rows
        previous = len(rows)
        driver.execute_script("window.scrollBy(0, 2500)")
        time.sleep(1.0)
    return _rows(driver)


def _go_to_page(driver, page: int, previous_ids: set[str], timeout: float = 20) -> bool:
    """Clicca il pulsante della pagina e attende che la lista cambi.
    (Navigare cambiando solo '#/page/N/' nell'URL restituisce a volte la pagina sbagliata.)"""
    from selenium.webdriver.common.by import By

    buttons = driver.find_elements(
        By.XPATH, f"//nav[@aria-label='Pagination']//*[normalize-space(text())='{page}']")
    if not buttons:
        return False
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'}); arguments[0].click();", buttons[0])
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        time.sleep(1.0)
        ids = {event_id for event_id, text in _rows(driver) if text}
        if ids and len(ids & previous_ids) < len(ids) / 2:
            return True
    return False


class OddsPortal(Source):
    name = "oddsportal"
    kind = "scraping"
    description = "OddsPortal (quote 1X2 medie, Selenium)"
    datasets = ("odds",)

    def fetch(self, dataset: str, season: int) -> pd.DataFrame:
        settings = get_settings()
        browser = settings.source_option(self.name, "browser", "chrome")
        wait = settings.source_option(self.name, "page_wait_seconds", 6)
        driver = _driver(browser)
        rows: dict[str, dict] = {}
        try:
            driver.get(URL.format(path=season_path(season), page=1))
            time.sleep(wait)
            _accept_cookies(driver)
            for page in range(1, MAX_PAGES + 1):
                if page > 1:
                    if not _go_to_page(driver, page, {event_id for event_id, _ in found}):
                        break  # nessuna pagina successiva
                found = _load_all_rows(driver)
                new = 0
                for event_id, text in found:
                    parsed = parse_match_text(text, season)
                    if parsed and event_id not in rows:
                        rows[event_id] = parsed
                        new += 1
                log.info("[oddsportal] %s pagina %d: %d righe, %d nuove", season, page, len(found), new)
        finally:
            driver.quit()
        return pd.DataFrame(list(rows.values()))

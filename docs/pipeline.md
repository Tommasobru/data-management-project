# 2. Pipeline dei dati

La pipeline è composta da quattro step più l'analisi. L'orchestratore
(`football_pipeline/pipeline.py`) li esegue in ordine:

```
acquire  ──▶  clean  ──▶  quality  ──▶  store
```

Ogni esecuzione riceve un identificativo (`run_id`, es. `20261019-232530`) e viene registrata nella tabella
`etl_run_log` con esito `SUCCESS`, `FAILED` oppure `BLOCKED` (bloccata dalla Data Quality).

---

## Stagioni analizzate

In `config/settings.yaml`:

```yaml
seasons: auto
n_seasons: 4
```

`auto` significa: le ultime 4 stagioni **concluse** rispetto alla data di esecuzione. Una stagione si
considera conclusa dal 1° luglio dell'anno in cui termina:

| Data di esecuzione | Stagioni analizzate |
|---|---|
| 1 maggio 2026 | 2021/22 – 2024/25 (la 2025/26 è ancora in corso) |
| 19 ottobre 2026 | 2022/23 – 2025/26 |
| 1 luglio 2027 | 2023/24 – 2026/27 |

La finestra si sposta da sola ogni anno: alla prima esecuzione dopo il 1° luglio la pipeline
scarica la stagione appena conclusa. Si può anche indicare una lista fissa, es. `seasons: [2021, 2022, 2023, 2024]`.

---

## Step 1 — Acquisizione

Cartella `football_pipeline/acquisition/`. Ogni fonte è una classe che eredita da `Source` (`base.py`) e
dichiara il suo tipo (`api` o `scraping`), i dataset che produce e il metodo `fetch(dataset, stagione)`.

### Fonti e disponibilità gratuita

| Fonte | Tipo | Dataset → file raw | Contenuto | Stagioni gratuite |
|---|---|---|---|---|
| **football-data.org** | API REST | `matches_<s>.csv` | Risultati finali e del primo tempo, giornata | Piano free: dalla 2023/24 in poi (la 2022/23 restituisce HTTP 403) |
| **API-Football** | API REST | `fixtures_<s>.csv` | Risultati finali e del primo tempo | Piano free limitato a poche stagioni e 100 richieste/giorno |
| **ClubElo** | API CSV | `elo_<s>.csv` | Rating Elo al 1° agosto e al 1° giugno | Tutte, senza chiave |
| **Transfermarkt** | Scraping HTML | `teams_<s>.csv`, `players_<s>.csv`, `goals_<s>.csv` | Rose (valore, età media, stranieri), giocatori (ruolo, età, valore), marcatori per giornata | Tutte |
| **OddsPortal** | Scraping dinamico (Selenium) | `odds_<s>.csv` | Quote 1X2 medie e risultato | Tutte |
| **football-data.co.uk** | Open data CSV | `matches_<s>.csv` | Tiri, tiri in porta, falli, corner, cartellini, arbitro, quote di Bet365/Pinnacle/media di mercato | Tutte, senza chiave |
| **Understat** | Scraping (JSON nella pagina) | `matches_<s>.csv` | Expected goals (xG) e probabilità del modello Understat | Tutte |

Per la tabella dei risultati ogni stagione usa la prima fonte disponibile nell'ordine
`match_source_priority` (default: football-data.org → API-Football → football-data.co.uk → Understat).
Con i dati attuali:

| Stagione | Fonte primaria dei risultati | Fonti di controllo |
|---|---|---|
| 2022/23 | API-Football (dati della prima versione del progetto) | football-data.co.uk, Understat |
| 2023/24 | football-data.org | API-Football, football-data.co.uk, Understat |
| 2024/25 | football-data.org | API-Football, football-data.co.uk, Understat |
| 2025/26 | football-data.org | football-data.co.uk, Understat |

### Come funziona la cache

I file raw sono salvati **così come arrivano dalla fonte** in `data/raw/<fonte>/<dataset>_<stagione>.csv`.
Prima di ogni richiesta la pipeline controlla se il file esiste già:

- esiste → viene riusato (`cached`), nessuna richiesta di rete;
- non esiste → viene scaricato (`downloaded`);
- `--refresh` → viene riscaricato comunque.

Così una nuova esecuzione scarica solo la stagione mancante, e lo scraping non ripete migliaia di
richieste a ogni avvio.

### Gestione degli errori

Il client HTTP condiviso (`utils/http.py`):

- rispetta una pausa minima tra le richieste (`request_delay_seconds` per Transfermarkt, 6,5 s per le API con limite di 10 richieste/minuto);
- ritenta fino a 4 volte con backoff esponenziale sugli errori temporanei (429, 5xx), rispettando `Retry-After`;
- se il server è irraggiungibile o non risponde dopo i tentativi, la fonte viene **saltata per intero** (inutile provare le altre stagioni);
- gli errori definitivi (es. 403 "stagione non inclusa nel piano") interrompono solo quella stagione.

Una fonte che fallisce non ferma la pipeline: l'esito di ogni richiesta (`downloaded`, `cached`,
`skipped`, `failed`) è riportato nel log e nella pagina **⚙️ Aggiorna dati**.

### Dettagli sugli scraper

**Transfermarkt** (`transfermarkt.py`, `requests` + BeautifulSoup)
1. pagina del campionato → elenco squadre con link, rosa, età media, stranieri, valore della rosa;
2. pagina di ogni squadra → giocatori con ruolo, data di nascita, valore di mercato;
3. pagina di ognuna delle 38 giornate → per ogni gol: marcatore, minuto e risultato dopo il gol.

Una stagione completa richiede circa 60 richieste distanziate di 2 secondi (~2 minuti).

**OddsPortal** (`oddsportal.py`, Selenium)

La pagina dei risultati è un'applicazione JavaScript: la prima pagina è nell'HTML, le successive arrivano
con chiamate AJAX cifrate, quindi serve un browser reale. Lo scraper:
1. avvia Chrome headless (o Firefox, `browser: firefox`) con user-agent realistico, perché in modalità
   automatizzata "pura" il sito mostra una pagina anti-bot;
2. apre la stagione (dall'Italia il sito reindirizza al mirror `centroquote.it`, con struttura identica);
3. scorre la pagina finché il numero di righe smette di crescere (caricamento progressivo);
4. passa alla pagina successiva **cliccando** il pulsante di paginazione e aspetta che la lista cambi
   (cambiare solo `#/page/N/` nell'URL a volte restituisce la pagina sbagliata);
5. interpreta ogni riga (`parse_match_text`), riconoscendo sia il layout attuale
   (`Finita | 0 | Cremonese | - | Torino | 0 | 2.95 | 3.20 | 2.65`) sia quello usato fino al 2024/25;
6. deduplica per identificativo della partita.

Una stagione (8 pagine, 380 partite) richiede circa un minuto. Lo scraping live del 2022/23 restituisce
le stesse 381 partite dei dati originali, con quote correlate a 0,999; le quote differiscono in media del
3% perché il sito oggi mostra una media con margine più basso (2,6% contro 5,3%).

**Understat** (`understat.py`)
interroga l'endpoint che la pagina stessa usa (`/getLeagueData/Serie_A/<stagione>`); come ripiego estrae il
JSON incorporato nell'HTML (`datesData = JSON.parse('...')`).

**football-data.co.uk** (`football_data_couk.py`)
scarica il CSV della stagione (`/mmz4281/2526/I1.csv`), gestendo encoding UTF-8 e Latin-1.

---

## Step 2 — Cleaning

File principale `football_pipeline/cleaning/transform.py`. Trasforma i file raw eterogenei in tabelle
omogenee (vedi [modello dati](modello-dati.md)).

1. **Standardizzazione dei risultati.** Ogni fonte di risultati viene convertita nello stesso schema
   (stagione, giornata, data, squadre, gol finali e del primo tempo, esito dichiarato dalla fonte).
   L'esito (`H`/`D`/`A`) viene sempre **ricalcolato dal punteggio**; quello dichiarato dalla fonte
   serve solo come controllo. Le partite senza risultato (rinviate) vengono scartate.
2. **Nomi squadra canonici** (`teams.py`). Ogni fonte scrive i nomi in modo diverso
   (`FC Internazionale Milano`, `Inter`, `Internazionale`). Il nome viene normalizzato (minuscolo, senza
   accenti né sigle come FC/AC/SSC/Calcio) e cercato nel dizionario `config/team_aliases.yaml`; se non c'è,
   si usa la similarità testuale (rapidfuzz, soglia 85). I nomi non risolti vengono segnalati dalla Data Quality.
3. **Spareggi.** Se la stessa coppia casa/ospite compare due volte nella stessa stagione, la partita più
   recente è uno spareggio (es. Spezia–Verona 2022/23) e viene marcata `PLAYOFF`, così non entra in classifica.
4. **Fonte primaria.** Per ogni stagione si sceglie la fonte dei risultati secondo la priorità configurata;
   tutte le fonti restano nella tabella di staging `stg_match_sources` per il controllo incrociato.
5. **Identificativo partita.** `match_id = stagione·100000 + id_casa·1000 + id_ospite·10 + spareggio`:
   è deterministico, quindi la stessa partita ha lo stesso id in ogni esecuzione.
6. **Collegamento delle altre fonti.** Gol, quote, statistiche e xG vengono agganciati alla partita tramite
   (stagione, casa, ospite); se la coppia è ambigua (spareggio) si sceglie la partita con lo stesso punteggio.
7. **Giocatori** (`parsers.py`). Dalla cella ruolo di Transfermarkt (che contiene anche il nome) si tiene
   solo il ruolo, ricondotto a un macro-ruolo (Portiere, Difensore, Centrocampista, Attaccante); data di
   nascita ed età vengono lette sia nel formato `18/apr/1990 (32)` sia in quello attuale `18/04/1990 (32)`;
   i valori `642,50 mln €`, `400 mila €`, `1,05 mld €` diventano numeri; il valore mancante `-` resta NULL.
   Un giocatore è identificato da nome normalizzato + data di nascita.
8. **Gol** (`players.py`). Dal risultato dopo ogni gol (`1:2`) si ricava quale squadra ha segnato. Il marcatore
   viene associato all'anagrafica giocatori cercando, in ordine: nella squadra che segna, in quella che subisce
   (autogol), in tutta la stagione, poi per similarità. Se il marcatore appartiene alla squadra che subisce il
   gol, è un autogol.
9. **Quote.** Le righe duplicate dello scraping vengono rimosse; per ogni partita una quota è marcata
   `is_primary` secondo `odds_source_priority` (default OddsPortal, poi media di mercato di football-data.co.uk).

Output: `data/clean/*.csv` (tabelle del modello) e `data/clean/staging/*.csv` (tabelle di supporto per la
Data Quality: `stg_match_sources`, `stg_goals`, `stg_odds`, `team_resolution`, `cleaning_log`).
Ogni operazione che modifica o scarta righe viene scritta nel **log del cleaning**.

---

## Step 3 — Data Quality

Vedi [data-quality.md](data-quality.md). In sintesi: 27 controlli sulle tabelle pulite; se un controllo
`critical` fallisce, lo storage non viene eseguito (salvo `--force`). Il report viene scritto in
`data/reports/quality_report.md` / `.csv` e salvato nella tabella `dq_results`.

---

## Step 4 — Storage

File `football_pipeline/storage/loader.py`. Il caricamento è un **full reload** dentro un'unica transazione:

1. elimina le viste e le tabelle dati esistenti;
2. ricrea lo schema (`schema.py`, con chiavi primarie ed esterne);
3. inserisce le tabelle pulite rispettando l'ordine delle chiavi esterne;
4. ricrea le 16 viste analitiche eseguendo i file `storage/views/*.sql` in ordine;
5. aggiunge alle tabelle di metadati (che **non** vengono svuotate) il report di qualità, il log del cleaning
   e il numero di righe caricate per tabella.

Se qualcosa fallisce, la transazione viene annullata e il database resta nello stato precedente.

Il database di default è SQLite (`data/football.db`); con la variabile `DATABASE_URL` si usa PostgreSQL
senza modificare il codice: schema e viste usano solo SQL compatibile con entrambi.

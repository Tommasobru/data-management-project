# ⚽ Serie A Data Hub

Progetto di Data Management (master in Data Science): dati sulle **ultime 4 stagioni concluse** della Serie A
(oggi 2022/23–2025/26) raccolti da **API** e **web scraping**, uniformati, verificati con controlli di
**Data Quality**, salvati in un unico **data warehouse** a stella e analizzati in una dashboard **Streamlit**.

📖 **Documentazione completa: [`docs/`](docs/README.md)** — pipeline, modello dati, controlli di qualità,
guida alla dashboard, configurazione.

```
 1 Acquisizione        2 Cleaning              3 Data Quality         4 Storage               5 Analisi
 API + scraping  ──▶   nomi canonici, tipi, ──▶ 27 controlli su    ──▶ schema a stella      ──▶ dashboard
 data/raw/             deduplica, match_id     5 dimensioni           + 16 viste SQL          Streamlit
```

## Avvio rapido

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python main.py run --offline     # clean -> quality -> store sui dati raw già presenti nel repo
streamlit run app/Home.py        # dashboard su http://localhost:8501
```

Il repository contiene già i dati raw delle stagioni analizzate, quindi la dashboard funziona anche senza
token né connessione. Se il database non esiste la dashboard lo costruisce da sola al primo avvio.
Dalla pagina **⚙️ Aggiorna dati** della dashboard si possono lanciare acquisizione (API e scraping) e pipeline.

## Comandi

| Comando | Cosa fa |
|---|---|
| `python main.py run` | Pipeline completa. L'acquisizione scarica solo i file raw mancanti (cache per fonte e stagione) |
| `python main.py run --offline` | Salta l'acquisizione |
| `python main.py run --refresh` | Riscarica tutto dalle fonti |
| `python main.py run --steps clean,quality` | Esegue solo alcuni step |
| `python main.py acquire --sources understat,clubelo` | Acquisisce solo da alcune fonti |
| `python main.py quality` | Esegue solo i controlli di qualità e scrive `data/reports/quality_report.md` |
| `python main.py status` | Mostra quali stagioni sono presenti per ogni fonte e le ultime esecuzioni |
| `pytest` | Test: parser, risoluzione nomi, parsing delle API, pipeline end-to-end |

Con `seasons: auto` (default) la pipeline analizza le ultime 4 stagioni concluse: dal 1° luglio di ogni anno
la finestra si sposta e `python main.py run` scarica la stagione appena terminata.

## Fonti dati (tutte gratuite)

| Fonte | Tipo | Dati | Chiave |
|---|---|---|---|
| [football-data.org](https://www.football-data.org) | API REST | Risultati, primo tempo (piano free: dal 2023/24) | Token gratuito (`FOOTBALL_DATA_TOKEN`) |
| [API-Football](https://www.api-football.com) | API REST | Risultati, primo tempo (2022/23 dai dati originali) | Chiave gratuita (`API_FOOTBALL_KEY`) |
| [ClubElo](http://clubelo.com/API) | API CSV | Rating Elo a inizio e fine stagione | Nessuna |
| [Transfermarkt](https://www.transfermarkt.it) | Scraping HTML | Rose, età, ruoli, valori di mercato, marcatori per giornata | Nessuna |
| [OddsPortal](https://www.oddsportal.com) | Scraping dinamico (Selenium + Chrome/Firefox) | Quote 1X2 | Nessuna |
| [football-data.co.uk](https://www.football-data.co.uk) | Open data CSV | Tiri, falli, corner, cartellini, arbitro, quote di più bookmaker | Nessuna |
| [Understat](https://understat.com) | Scraping (JSON nella pagina) | Expected goals (xG) per partita | Nessuna |

I token si inseriscono in un file `.env` (vedi `.env.example`); per compatibilità viene letto anche il vecchio
`psw/token.yml`. Le fonti senza token vengono saltate senza bloccare la pipeline.

Per ogni stagione la tabella dei risultati usa la prima fonte disponibile secondo `match_source_priority`;
le altre servono da **controllo incrociato** (oggi tutte le fonti concordano su ogni risultato confrontato).

## Struttura

```
config/
  settings.yaml          stagioni, fonti abilitate, priorità, database
  team_aliases.yaml      nome canonico di ogni squadra e varianti usate dalle fonti
football_pipeline/
  acquisition/           step 1 - una classe per fonte, output in data/raw/<fonte>/<dataset>_<stagione>.csv
  cleaning/              step 2 - parser, risoluzione nomi squadra/giocatore, modello a stella
  quality/               step 3 - controlli di qualità con soglie e severità
  storage/               step 4 - schema SQLAlchemy, loader, viste SQL (storage/views/*.sql)
  analysis/              step 5 - metriche statistiche usate dalla dashboard
  pipeline.py            orchestratore che concatena gli step e registra le esecuzioni
app/                     dashboard Streamlit (Home + 7 pagine)
docs/                    documentazione
data/raw/                dati grezzi versionati
data/clean/, data/reports/, data/football.db   output rigenerabili (non versionati)
tests/                   test pytest
legacy/                  notebook e query della prima versione del progetto
main.py                  CLI unica
```

## Modello dati

Schema a stella, portabile tra SQLite (default) e PostgreSQL (`DATABASE_URL=postgresql+psycopg2://...`).

- **Dimensioni**: `dim_season`, `dim_team`, `dim_player`
- **Fatti**: `fact_match`, `fact_goal`, `fact_odds`, `fact_match_stats`, `fact_match_xg`,
  `fact_team_season`, `fact_player_season`, `fact_team_elo`
- **Metadati**: `dq_results`, `cleaning_log`, `etl_run_log`, `etl_table_stats` (storico di ogni esecuzione)
- **Viste analitiche**: classifiche, andamento punti, primo vs secondo tempo, fattore campo, valore vs rendimento,
  probabilità implicite e punti attesi dalle quote, gol per fascia di minuto, marcatori, crescita del valore di
  giocatori e rose, xG, Elo, statistiche di gioco, arbitri.

## Data Quality

27 controlli su cinque dimensioni, eseguiti a ogni run e salvati nel database:

- **Completezza**: 380 partite per stagione, 38 per squadra, campi obbligatori, copertura di gol, quote e rose
- **Unicità**: chiave partita, quote per partita e bookmaker, duplicati nei dati raw
- **Validità**: punteggi (FT ≥ HT ≥ 0), esito coerente col punteggio, quote e margine del bookmaker, minuti, età
- **Consistenza tra fonti**: risultati tra API, scraping e open data; quote tra OddsPortal e football-data.co.uk;
  ultimo gol estratto = risultato finale; nomi squadra e marcatori risolti
- **Integrità referenziale**: tutte le chiavi esterne

I controlli `critical` che falliscono bloccano lo storage (`--force` per caricare comunque).
Il report è in `data/reports/quality_report.md` e nella pagina **🧪 Data Quality** della dashboard.

## Cosa è cambiato rispetto alla prima versione

- Un'unica pipeline (`main.py`) al posto di 9 notebook da eseguire a mano; i notebook originali sono in `legacy/`.
- **Bug corretti**:
  - le quote 2024 contenevano 400 righe duplicate (780 invece di 380): le viste sulle quote contavano più volte le stesse partite;
  - `winner` mescolava `HOME_TEAM` (football-data.org, 2024) e `HOME_WINNER` (API-Football): le query sui punti sbagliavano tutto il 2024;
  - lo spareggio salvezza Spezia–Verona 2022/23 era conteggiato come partita di campionato;
  - i valori di mercato mancanti (`-`) diventavano 0, falsando medie e crescite;
  - il retry HTTP era un ciclo infinito.
- Nomi squadra risolti con un dizionario di alias esplicito più similarità (rapidfuzz), invece del confronto con i nomi delle quote.
- Database SQLite di default (zero configurazione), PostgreSQL ancora supportato; viste SQL portabili.
- Tre nuove fonti gratuite: football-data.co.uk, Understat, ClubElo.
- Data Quality strutturata con stato, severità e storico, invece di stampe a schermo.
- Dashboard Streamlit e test automatici.

## Note

- I punti sono calcolati sul campo: penalizzazioni come il −10 alla Juventus nel 2022/23 non sono incluse.
- Lo scraping va usato con moderazione: le richieste sono distanziate (`request_delay_seconds`) e i dati vengono
  salvati in cache per non ripetere download inutili.

# Documentazione — Serie A Data Hub

Questa cartella descrive come funziona l'applicazione: da dove arrivano i dati, come vengono
trasformati e controllati, come sono salvati e come leggere le analisi della dashboard.

| Documento | Contenuto |
|---|---|
| [1. Panoramica e avvio](#panoramica) | Cos'è l'app, requisiti, primo avvio (questa pagina) |
| [2. Pipeline dei dati](pipeline.md) | I quattro step (acquisizione, cleaning, data quality, storage), le fonti e la loro disponibilità gratuita |
| [3. Modello dati](modello-dati.md) | Schema a stella, tabelle, colonne, viste SQL |
| [4. Data Quality](data-quality.md) | I 27 controlli: cosa misurano, soglie, severità, come leggere il report |
| [5. Guida alla dashboard](dashboard.md) | Le 8 pagine Streamlit, cosa mostra ogni grafico e con quale metodo è calcolato |
| [6. Configurazione e comandi](configurazione.md) | `settings.yaml`, token, CLI, PostgreSQL, come estendere il progetto, problemi frequenti |

---

## Panoramica

Serie A Data Hub raccoglie dati sulle **ultime 4 stagioni concluse** della Serie A
(a ottobre 2026: 2022/23, 2023/24, 2024/25, 2025/26) da sette fonti gratuite, li integra in un unico
data warehouse e li presenta in una dashboard.

```
┌──────────────────────────┐   ┌─────────────┐   ┌──────────────┐   ┌─────────────┐   ┌────────────┐
│ 1. ACQUISIZIONE          │   │ 2. CLEANING │   │ 3. DATA      │   │ 4. STORAGE  │   │ 5. ANALISI │
│ API: football-data.org,  │──▶│ tipi, nomi  │──▶│    QUALITY   │──▶│ schema a    │──▶│ Streamlit  │
│      API-Football,ClubElo│   │ canonici,   │   │ 27 controlli │   │ stella +    │   │ 8 pagine   │
│ Scraping: Transfermarkt, │   │ deduplica,  │   │ blocca se    │   │ 16 viste    │   │            │
│  OddsPortal, Understat,  │   │ match_id    │   │ critico      │   │ SQL         │   │            │
│  football-data.co.uk     │   │             │   │              │   │             │   │            │
└──────────────────────────┘   └─────────────┘   └──────────────┘   └─────────────┘   └────────────┘
   data/raw/<fonte>/            data/clean/        data/reports/      data/football.db
```

Ogni step legge da disco l'output dello step precedente, quindi può essere eseguito da solo;
`python main.py run` li concatena in un'unica esecuzione e la registra nel database.

### Requisiti

- Python 3.11 o superiore
- Google Chrome (o Firefox) solo per lo scraping di OddsPortal
- Token gratuiti per football-data.org e API-Football (facoltativi: senza token le due API vengono saltate)

### Primo avvio

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env        # inserire i token (facoltativo)

python main.py run          # scarica ciò che manca, pulisce, controlla, carica
streamlit run app/Home.py   # apre la dashboard su http://localhost:8501
```

I dati raw delle stagioni analizzate sono già nel repository: `python main.py run --offline`
ricostruisce il database senza fare richieste di rete, e la dashboard lo costruisce da sola
se al primo avvio il database non esiste.

### Struttura del repository

```
main.py                      CLI unica della pipeline
config/settings.yaml         stagioni, fonti, priorità, database
config/team_aliases.yaml     nome canonico di ogni squadra e sue varianti
football_pipeline/
  acquisition/               step 1: una classe per fonte
  cleaning/                  step 2: parser, risoluzione nomi, modello a stella
  quality/                   step 3: controlli di qualità
  storage/                   step 4: schema, caricamento, viste SQL (storage/views/)
  analysis/                  metriche statistiche usate dalla dashboard
  pipeline.py                orchestratore
app/                         dashboard Streamlit (Home.py + pages/)
data/raw/                    dati grezzi (versionati)
data/clean/                  output del cleaning (rigenerato)
data/reports/                report di Data Quality (rigenerato)
data/football.db             data warehouse SQLite (rigenerato)
tests/                       test automatici (pytest)
legacy/                      notebook e query della prima versione
docs/                        questa documentazione
```

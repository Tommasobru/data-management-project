# 6. Configurazione e comandi

> **In breve.** Per vedere la dashboard non serve configurare nulla. I token servono solo per scaricare
> risultati aggiornati dalle due API; tutto il resto (stagioni, fonti, database) si regola in
> `config/settings.yaml`.

**Indice:** [Token](#token-delle-api) · [settings.yaml](#configsettingsyaml) · [Comandi](#comandi) ·
[Client SQL](#aprire-il-database-con-un-client-sql) · [PostgreSQL](#usare-postgresql) ·
[Estendere il progetto](#estendere-il-progetto) · [Problemi frequenti](#problemi-frequenti)

## Token delle API

Copiare `.env.example` in `.env` e inserire i token (entrambi gratuiti):

```
FOOTBALL_DATA_TOKEN=...   # https://www.football-data.org/client/register
API_FOOTBALL_KEY=...      # https://dashboard.api-football.com/register
```

Per compatibilità con la prima versione del progetto viene letto anche `psw/token.yml`
(chiavi `TOKEN FOOTBALL DATA` e `TOKEN API FOOTBALL`). `.env` e `psw/` sono esclusi da git.

Senza token, o con un token non valido, la fonte viene saltata con un avviso e la pipeline prosegue
con le altre.

## `config/settings.yaml`

| Chiave | Default | Significato |
|---|---|---|
| `seasons` | `auto` | `auto` = ultime `n_seasons` stagioni concluse; oppure lista esplicita `[2022, 2023]` |
| `n_seasons` | `4` | Numero di stagioni con `seasons: auto` |
| `paths.raw` / `clean` / `reports` | `data/...` | Cartelle di lavoro |
| `database.url` | `sqlite:///data/football.db` | Database (sovrascrivibile con la variabile `DATABASE_URL`) |
| `sources.<nome>.enabled` | `true` | Se `false`, la fonte non viene interrogata (i file raw già presenti restano in uso) |
| `sources.transfermarkt.request_delay_seconds` | `2.0` | Pausa tra le richieste a Transfermarkt |
| `sources.oddsportal.browser` | `chrome` | `chrome` oppure `firefox` |
| `sources.oddsportal.page_wait_seconds` | `6` | Attesa dopo l'apertura della pagina |
| `match_source_priority` | org → API-Football → co.uk → Understat | Ordine di scelta della fonte dei risultati |
| `odds_source_priority` | OddsPortal → co.uk | Ordine di scelta della quota primaria |
| `quality.block_on_critical` | `true` | Blocca lo storage se un controllo critico fallisce |
| `quality.fuzzy_threshold` | `85` | Soglia di similarità (0–100) per nomi squadra e marcatori |

La variabile d'ambiente `PIPELINE_SEASONS=2023,2024` sovrascrive le stagioni per una singola esecuzione.

## Comandi

| Comando | Effetto |
|---|---|
| `python main.py run` | Pipeline completa; scarica solo ciò che manca |
| `python main.py run --offline` | Senza acquisizione (nessuna richiesta di rete) |
| `python main.py run --refresh` | Riscarica anche le stagioni in cache |
| `python main.py run --steps clean,quality` | Solo gli step indicati |
| `python main.py run --force` | Carica anche se un controllo critico fallisce |
| `python main.py acquire --sources oddsportal,understat` | Solo acquisizione, solo da alcune fonti |
| `python main.py clean` / `quality` / `store` | Un singolo step (`store` riesegue anche `quality`) |
| `python main.py status` | Stagioni presenti per ogni fonte e ultime esecuzioni |
| `streamlit run app/Home.py` | Dashboard |
| `pytest` | Test automatici |

Codici di uscita: `0` successo, `2` caricamento bloccato dalla Data Quality, `1` altri errori.

## Aprire il database con un client SQL

Il database è il file `data/football.db`. In `settings.yaml` è indicato come `sqlite:///data/football.db`,
ma quella è la stringa di connessione di SQLAlchemy (Python). I client come **DBeaver** o DataGrip usano
invece un URL JDBC con il **percorso assoluto**:

```
jdbc:sqlite:/percorso/assoluto/data-management-project/data/football.db
```

Con DBeaver è più semplice: *Nuova connessione → SQLite → Path → Sfoglia* e selezionare il file.

| Problema | Soluzione |
|---|---|
| `Invalid JDBC URL: sqlite:///...` | Manca il prefisso `jdbc:`: usare il formato indicato sopra |
| `[SQLITE_CANTOPEN] Unable to open the database file` | Percorso errato oppure, su macOS, DBeaver non ha accesso alla cartella Documenti: *Impostazioni di Sistema → Privacy e sicurezza → Accesso completo al disco*, aggiungere DBeaver e riavviarlo |
| `database is locked` durante `python main.py run` | DBeaver ha una transazione aperta: disconnettersi (o fare commit/rollback) prima di rilanciare la pipeline |

Dopo ogni esecuzione della pipeline il database viene ricaricato: in DBeaver premere F5 per aggiornare.

## Usare PostgreSQL

```bash
pip install psycopg2-binary
export DATABASE_URL=postgresql+psycopg2://utente:password@localhost:5432/DWH_football
python main.py run --offline
```

Schema e viste usano SQL compatibile con entrambi i database: non serve altro.

## Aggiornamento automatico

Per tenere i dati aggiornati basta eseguire periodicamente la pipeline, ad esempio ogni lunedì con cron:

```
0 6 * * 1  cd /percorso/data-management-project && .venv/bin/python main.py run >> data/reports/cron.log 2>&1
```

Con `seasons: auto`, dal 1° luglio la finestra si sposta e viene scaricata la stagione appena conclusa.

## Estendere il progetto

**Nuova fonte.** Creare una classe in `football_pipeline/acquisition/` che eredita da `Source`, implementa
`fetch(dataset, season)` e restituisce un DataFrame; registrarla in `SOURCES`
(`acquisition/__init__.py`) e aggiungerla a `config/settings.yaml`. Poi standardizzarla in
`cleaning/transform.py`, aggiungere eventuali tabelle in `storage/schema.py` (e in `DATA_TABLES`) e
almeno un controllo di qualità.

**Nuova squadra o nuovo nome.** Aggiungere la variante in `config/team_aliases.yaml`. Se un nome non viene
riconosciuto, il controllo "Nomi squadra risolti" lo elenca.

**Nuova analisi.** Aggiungere un file `storage/views/NN_v_nome.sql` con `CREATE VIEW ...` (SQL portabile:
`1.0 *` per le divisioni decimali, niente `::` né `FILTER`), poi leggerla in una pagina con
`load_view("v_nome")`.

**Nuova pagina.** Creare `app/pages/N_<emoji>_Nome.py` iniziando con `setup_page("Nome", "<emoji>")`;
Streamlit la aggiunge da solo al menu.

## Problemi frequenti

| Sintomo | Causa e soluzione |
|---|---|
| `football_data_org ... 2022 fallito: HTTP 403` | La stagione non è inclusa nel piano gratuito. Per quella stagione si usano i dati API-Football già presenti |
| `API-Football: {'token': 'Error/Missing application key...'}` | Chiave non valida, scaduta o account sospeso: verificarla su dashboard.api-football.com |
| `[clubelo] fonte non disponibile ... HTTP 502` | Il server ClubElo non risponde (o la rete lo blocca). La scheda Elo resta vuota; riprovare più tardi |
| `[oddsportal] impossibile avviare chrome` | Installare Google Chrome oppure impostare `browser: firefox`; serve `pip install selenium` |
| OddsPortal restituisce 0 righe | Il sito ha cambiato struttura: aggiornare `ROW_XPATH` e `parse_match_text` in `oddsportal.py` (i test in `tests/test_acquisition_parsers.py` aiutano a verificarlo) |
| `[BLOCCATO] N controlli critici falliti` | Aprire `data/reports/quality_report.md`, correggere la causa o rilanciare con `--force` |
| La dashboard mostra dati vecchi | Rilanciare la pipeline dalla pagina ⚙️ Aggiorna dati, oppure premere `C` in Streamlit per svuotare la cache |

# 4. Data Quality

Lo step di Data Quality (`football_pipeline/quality/checks.py`) gira sulle tabelle pulite **prima** del
caricamento nel database. Ogni controllo conta quante righe violano una regola e confronta il risultato con
una soglia di tolleranza.

## Esiti e severità

| Esito | Significato |
|---|---|
| ✅ `PASS` | Violazioni entro la tolleranza |
| ⚠️ `WARN` | Tolleranza superata per un controllo di severità `warning`: i dati vengono caricati e il problema documentato |
| ❌ `FAIL` | Tolleranza superata per un controllo `critical`: **lo storage viene bloccato** (la pipeline termina con esito `BLOCKED`) |
| ➖ `SKIP` | Nessun dato da controllare (es. manca la seconda fonte per un confronto) |

Per caricare comunque dati con errori critici: `python main.py run --force` (o la casella corrispondente
nella pagina ⚙️ Aggiorna dati). L'opzione `quality.block_on_critical: false` in `settings.yaml` disattiva il
blocco in modo permanente.

## I 27 controlli

Tolleranza = percentuale massima di righe in violazione con cui il controllo risulta ancora `PASS`.

### Completezza — i dati attesi ci sono tutti?

| Controllo | Severità | Toll. | Regola |
|---|---|---|---|
| Stagioni complete (380 partite) | warning | 0% | Ogni stagione configurata ha 380 partite di campionato |
| 38 partite per squadra | **critical** | 0% | Ogni squadra gioca 38 partite per stagione |
| Campi obbligatori delle partite | **critical** | 0% | Data, squadre, gol ed esito non sono mai nulli |
| Risultato primo tempo presente | warning | 1% | Il punteggio all'intervallo è disponibile |
| Copertura gol per partita | warning | 5% | Il numero di gol estratti da Transfermarkt è uguale ai gol del risultato finale |
| Copertura quote 1X2 | warning | 2% | Ogni partita ha una quota primaria |
| Profilo rosa per ogni squadra | warning | 0% | Ogni squadra-stagione ha valore, età media e stranieri |
| Giocatori estratti vs rosa dichiarata | warning | 10% | I giocatori estratti differiscono al massimo di 3 dal numero dichiarato nella pagina del campionato |
| Valore di mercato presente | warning | 5% | I giocatori hanno un valore di mercato |

### Unicità — ci sono duplicati?

| Controllo | Severità | Toll. | Regola |
|---|---|---|---|
| Chiave partita univoca | **critical** | 0% | `match_id` e (stagione, casa, ospite, fase) sono unici |
| Quote univoche per partita/bookmaker | **critical** | 0% | Una sola quota per partita, fonte e bookmaker; una sola quota primaria per partita |
| Giocatore univoco per stagione/squadra | **critical** | 0% | Nessun giocatore ripetuto nella stessa rosa |
| Duplicati nei dati raw | warning | 0% | Segnala i duplicati trovati (e rimossi) dal cleaning nei file raw |

### Validità — i valori sono plausibili?

| Controllo | Severità | Toll. | Regola |
|---|---|---|---|
| Punteggi validi (FT ≥ HT ≥ 0) | **critical** | 0% | Gol non negativi, gol del primo tempo non superiori a quelli finali |
| Esito dichiarato coerente col punteggio | **critical** | 0% | L'esito fornito da ogni fonte (es. `HOME_TEAM`) corrisponde al punteggio |
| Quote valide (> 1, margine 0–25%) | warning | 1% | Quote maggiori di 1 e somma delle probabilità implicite tra 0,97 e 1,25 |
| Minuto del gol valido | warning | 0% | Minuto tra 1 e 130 |
| Attributi giocatore validi | warning | 1% | Età tra 15 e 45, valore non negativo, ruolo riconosciuto |
| Data partita nella stagione | **critical** | 0% | Data tra il 15 luglio dell'anno di inizio e il 15 luglio successivo |

### Consistenza tra fonti — fonti diverse dicono la stessa cosa?

| Controllo | Severità | Toll. | Regola |
|---|---|---|---|
| Risultato quote = risultato API | warning | 1% | Il risultato riportato da OddsPortal coincide con quello della fonte primaria |
| Quote coerenti tra fonti (scarto < 10pp) | warning | 2% | Le probabilità implicite di OddsPortal e della media di mercato di football-data.co.uk differiscono meno di 10 punti percentuali |
| Ultimo gol = risultato finale API | warning | 5% | Il punteggio dopo l'ultimo gol estratto coincide con il risultato finale |
| Fonti secondarie concordano | warning | 1% | Tutte le fonti di risultati non primarie (API-Football, football-data.co.uk, Understat) danno lo stesso punteggio |
| Nomi squadra risolti | warning | 0% | Ogni nome squadra di ogni fonte è stato ricondotto a un nome canonico |
| Marcatori collegati all'anagrafica | warning | 2% | I marcatori sono stati associati a un giocatore delle rose |
| Squadra che segna determinata | warning | 1% | Per ogni gol si sa quale squadra ha segnato |

### Integrità referenziale

| Controllo | Severità | Toll. | Regola |
|---|---|---|---|
| Chiavi esterne valide | **critical** | 0% | Ogni riferimento a stagione, squadra, partita e giocatore esiste nella tabella collegata |

## Esito attuale (2022/23–2025/26)

25 controlli superati, 2 avvisi, nessun errore critico:

- ⚠️ **Copertura gol per partita**: 115 partite su 1.520 hanno meno gol estratti del risultato finale
  (3.745 trovati su 3.861 attesi, −3%). È un limite delle pagine giornata di Transfermarkt; le analisi
  basate sui minuti dei gol ("zona Cesarini") usano solo le partite complete.
- ⚠️ **Duplicati nei dati raw**: i dati originali di OddsPortal 2024/25 contenevano 400 righe ripetute
  (780 invece di 380), rimosse dal cleaning. Lo scraper attuale deduplica già in fase di acquisizione.

Da segnalare tra i controlli superati: **le 4 fonti di risultati concordano su tutte le partite confrontate**
e tutti i nomi squadra sono stati risolti.

## Problemi reali intercettati

I controlli hanno già individuato cambiamenti nelle fonti che altrimenti sarebbero passati inosservati:

| Problema | Controllo che l'ha rilevato | Correzione |
|---|---|---|
| Quote duplicate nello scraping 2024/25 | Duplicati nei dati raw / Quote univoche | Deduplica nel cleaning e nello scraper |
| Transfermarkt 2025/26 ha introdotto nuovi nomi di ruolo ("Centrocampista", "Esterno di destra") | Attributi giocatore validi (141 violazioni) | Nuove voci in `ROLE_MAP` |
| Transfermarkt 2025/26 scrive le date di nascita in formato numerico | — (rilevato in fase di test) | Parser con entrambi i formati |

## Dove leggere il report

- `data/reports/quality_report.md`: tabella leggibile dell'ultima esecuzione;
- `data/reports/quality_report.csv`: stessi dati in formato tabellare;
- tabella `dq_results` nel database: storico di tutte le esecuzioni;
- pagina **🧪 Data Quality** della dashboard: riepilogo, filtri per dimensione, log del cleaning,
  righe caricate e storico delle esecuzioni.

## Aggiungere un controllo

Un controllo è una funzione che riceve il dizionario delle tabelle pulite e restituisce
`(violazioni, totale, dettagli)`; va registrato nella lista `CHECKS`:

```python
def no_matches_on_same_day(t):
    m = t["fact_match"]
    teams = pd.concat([m[["match_date", "home_team_id"]].set_axis(["d", "t"], axis=1),
                       m[["match_date", "away_team_id"]].set_axis(["d", "t"], axis=1)])
    dup = teams.duplicated().sum()
    return int(dup), len(teams), ""

CHECKS.append(Check("Una partita al giorno per squadra", VALIDITY, "fact_match", "critical", no_matches_on_same_day))
```

# 7. Glossario

I termini usati nella dashboard e nella documentazione, in ordine alfabetico per area.

## Calcio e statistiche

| Termine | Significato |
|---|---|
| **Differenza reti (DR)** | Gol fatti meno gol subiti. In classifica decide a parità di punti |
| **Elo (rating)** | Punteggio di forza di una squadra, aggiornato dopo ogni partita: sale se vinci, di più se batti una squadra forte. Fonte: ClubElo |
| **Expected goals (xG)** | Quanti gol "valeva" un'occasione, in base a posizione e tipo di tiro: un rigore vale circa 0,76 xG, un tiro da 30 metri circa 0,03. La somma sulla partita dice quanti gol una squadra avrebbe dovuto segnare. Fonte: Understat |
| **xGA** | Expected goals *concessi*: la qualità delle occasioni lasciate agli avversari |
| **GF − xG** | Gol segnati meno xG. Positivo = la squadra ha finalizzato meglio della media |
| **Fattore campo** | Il vantaggio di giocare in casa, misurato come differenza tra vittorie in casa e in trasferta |
| **Rimonta** | Partita in svantaggio all'intervallo e poi vinta (rimonta vinta) o pareggiata (rimonta al pari) |
| **Spareggio** | Partita extra a fine stagione per decidere una retrocessione (es. Spezia–Verona 2022/23). È esclusa dalla classifica |
| **Valore di mercato** | Stima di Transfermarkt del prezzo di un giocatore. Il valore della rosa è la somma dei suoi giocatori |
| **Zona Cesarini** | Gol segnati negli ultimi minuti (qui: dall'85' in poi) |

## Quote e scommesse

| Termine | Significato |
|---|---|
| **Quota 1X2** | Quanto paga il bookmaker per ogni euro puntato su vittoria in casa (1), pareggio (X) o vittoria in trasferta (2). Quota 2,00 = vinci 2 € per 1 € puntato |
| **Probabilità implicita** | La probabilità "nascosta" in una quota: `1 / quota`, poi normalizzata per togliere il margine. Quota 2,00 ≈ 50% |
| **Margine del bookmaker** | Di quanto la somma delle tre probabilità implicite supera il 100%. È il guadagno del bookmaker: con un margine del 5%, chi scommette perde in media circa il 5% |
| **Favorito** | L'esito con la quota più bassa, cioè quello che il bookmaker considera più probabile |
| **Calibrazione** | Quanto le probabilità dichiarate corrispondono alla realtà. Quote ben calibrate: gli eventi quotati al 30% accadono il 30% delle volte |
| **Punti attesi** | Punti che una squadra "dovrebbe" fare secondo le quote: `3 × P(vittoria) + 1 × P(pareggio)`, sommati su tutte le partite |
| **ROI** | Return on investment: guadagno (o perdita) diviso per il totale puntato. ROI −5% = persi 5 centesimi per ogni euro |

## Statistica

| Termine | Significato |
|---|---|
| **Regressione lineare** | Retta che approssima la relazione tra due grandezze, es. valore della rosa e punti |
| **R²** | Quanta parte delle differenze tra squadre la retta riesce a spiegare: da 0 (per niente) a 1 (perfettamente) |
| **Scala logaritmica** | Asse in cui ogni tacca moltiplica il valore (100, 200, 400…) invece di sommare. Usata per il valore della rosa perché raddoppiare da 100 a 200 M€ conta quanto da 400 a 800 M€ |
| **Mediana** | Il valore centrale: metà dei casi sta sopra, metà sotto. Meno sensibile della media ai valori estremi |

## Data engineering

| Termine | Significato |
|---|---|
| **Pipeline / ETL** | Sequenza di step che estrae i dati dalle fonti (Extract), li trasforma (Transform) e li carica nel database (Load) |
| **Dati raw** | I dati così come arrivano dalla fonte, senza modifiche. Sono in `data/raw/` |
| **Web scraping** | Estrarre dati da pagine web pensate per essere lette da persone. *Statico*: si legge l'HTML. *Dinamico*: serve un browser vero (Selenium) perché la pagina si costruisce con JavaScript |
| **API** | Interfaccia che un servizio mette a disposizione per ottenere dati in formato strutturato (JSON, CSV) |
| **Cache** | Copia locale dei dati già scaricati, per non richiederli di nuovo |
| **Risoluzione delle entità** | Riconoscere che nomi diversi indicano la stessa cosa (`FC Internazionale Milano` = `Inter`) |
| **Fuzzy matching** | Confronto "approssimato" tra testi, che tollera piccole differenze di scrittura. Qui con la libreria rapidfuzz |
| **Data Quality** | Verifica che i dati siano completi, unici, validi, coerenti tra fonti e collegati correttamente |
| **Quality gate** | Controllo che blocca il caricamento se un problema grave non è risolto |
| **Data warehouse** | Database organizzato per l'analisi, invece che per l'operatività quotidiana |
| **Schema a stella** | Modello del data warehouse: al centro le tabelle dei **fatti** (eventi misurabili: partite, gol, quote), intorno le **dimensioni** (chi, quando: squadre, giocatori, stagioni) |
| **Vista SQL** | Query salvata nel database con un nome, interrogabile come una tabella |
| **Chiave esterna** | Colonna che punta a una riga di un'altra tabella (es. `fact_goal.match_id` → `fact_match`) |
| **Full reload** | A ogni caricamento le tabelle vengono svuotate e riempite di nuovo da zero |
| **Transazione** | Gruppo di operazioni eseguite "tutte o nessuna": se una fallisce, il database torna com'era |
| **Idempotente** | Eseguire la stessa operazione più volte produce lo stesso risultato |
| **Lineage** | Traccia di da dove viene un dato e quali trasformazioni ha subito |

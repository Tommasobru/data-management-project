# 3. Modello dati

> **In breve.** Il database è uno *schema a stella*: le tabelle dei **fatti** registrano gli eventi (partite,
> gol, quote, statistiche), le tabelle delle **dimensioni** descrivono chi e quando (squadre, giocatori,
> stagioni). Sopra ci sono 16 **viste** già pronte per l'analisi: per la maggior parte delle domande basta
> interrogare quelle, senza scrivere join.

Il data warehouse è uno **schema a stella**: tre dimensioni (stagione, squadra, giocatore) e otto tabelle
dei fatti, più quattro tabelle di metadati che conservano lo storico delle esecuzioni.
Lo schema è definito in `football_pipeline/storage/schema.py` (SQLAlchemy Core) e funziona sia su
SQLite sia su PostgreSQL.

```
                    dim_season ─────────┬──────────────┬──────────────────┐
                        │               │              │                  │
 fact_match_stats ──┐   ▼               ▼              ▼                  ▼
 fact_match_xg ─────┼─▶ fact_match   fact_team_season  fact_player_season  fact_team_elo
 fact_odds ─────────┤      ▲  ▲           ▲               ▲   ▲              ▲
 fact_goal ─────────┘      │  │           │               │   │              │
     │   │                 dim_team ──────┴───────────────┘   │              │
     │   └─────────────────▶ (squadra che segna/subisce)       │              │
     └─────────────────────▶ dim_player ──────────────────────┘
```

Con i dati attuali (2022/23–2025/26): 1.521 partite, 3.745 gol, 6.081 quote, 1.520 partite con statistiche
e xG, 1.640 giocatori, 27 squadre.

## Dimensioni

| Tabella | Chiave | Colonne | Note |
|---|---|---|---|
| `dim_season` | `season_id` | `label` | `season_id` è l'anno di inizio (2025 = 2025/26) |
| `dim_team` | `team_id` | `team_name` | Nome canonico definito in `config/team_aliases.yaml` |
| `dim_player` | `player_id` | `player_name`, `birth_date` | Un giocatore = nome normalizzato + data di nascita |

## Fatti

| Tabella | Grana (una riga per…) | Colonne principali | Fonte |
|---|---|---|---|
| `fact_match` | partita | `season_id`, `matchweek`, `match_date`, `stage` (REGULAR/PLAYOFF), `home_team_id`, `away_team_id`, `home_goals`, `away_goals`, `home_goals_ht`, `away_goals_ht`, `result` (H/D/A), `source` | API (fonte primaria della stagione) |
| `fact_goal` | gol | `match_id`, `seq` (ordine nella partita), `minute`, `scoring_team_id`, `conceding_team_id`, `player_id`, `scorer_name`, `home_score_after`, `away_score_after`, `is_own_goal` | Transfermarkt |
| `fact_odds` | partita × fonte × bookmaker | `odds_home`, `odds_draw`, `odds_away`, `is_primary` | OddsPortal (`average`), football-data.co.uk (`market_avg`, `bet365`, `pinnacle`) |
| `fact_match_stats` | partita | `referee`, `home/away_shots`, `_shots_on_target`, `_fouls`, `_corners`, `_yellow`, `_red` | football-data.co.uk |
| `fact_match_xg` | partita | `home_xg`, `away_xg`, `forecast_home/draw/away` | Understat |
| `fact_team_season` | squadra × stagione | `squad_size`, `avg_age`, `n_foreigners`, `squad_value_eur` | Transfermarkt |
| `fact_player_season` | giocatore × squadra × stagione | `role`, `role_group`, `age`, `market_value_eur` | Transfermarkt |
| `fact_team_elo` | squadra × stagione × istantanea | `snapshot` (start/end), `snapshot_date`, `elo` | ClubElo |

`match_id` è deterministico: `stagione·100000 + id_casa·1000 + id_ospite·10 + (1 se spareggio)`.

## Metadati della pipeline

Queste tabelle non vengono svuotate dal caricamento: ogni esecuzione aggiunge le proprie righe.

| Tabella | Contenuto |
|---|---|
| `etl_run_log` | Un record per esecuzione: `run_id`, inizio, fine, step eseguiti, esito, messaggio d'errore |
| `dq_results` | Esito di ogni controllo di qualità per esecuzione |
| `cleaning_log` | Operazioni del cleaning che hanno modificato o scartato righe |
| `etl_table_stats` | Righe caricate per tabella per esecuzione |

## Viste analitiche

Definite in `football_pipeline/storage/views/` e ricreate a ogni caricamento, nell'ordine del prefisso
numerico (alcune viste si basano sulle precedenti). Le partite di spareggio sono escluse.

| Vista | Contenuto | Usata in |
|---|---|---|
| `v_team_match` | Una riga per squadra per partita (casa e trasferta "srotolate"), con gol fatti/subiti, punti reali e punti a fine primo tempo. È la base di quasi tutte le altre | — |
| `v_standings` | Classifica: partite, V/N/P, gol, differenza reti, punti, punti in casa e in trasferta, posizione (a parità di punti: differenza reti, poi gol fatti) | Home, Classifiche |
| `v_points_progression` | Punti cumulati dopo ogni partita | Classifiche |
| `v_half_vs_full` | Punti "se la partita finisse all'intervallo" contro punti reali, rimonte vinte/pareggiate, vantaggi sprecati | Gol e momenti |
| `v_home_advantage` | % vittorie casa/pareggi/trasferta e gol medi per stagione | Classifiche |
| `v_team_value_performance` | Punti e posizione accanto a valore della rosa, età media, quota di stranieri, punti per 10 M€ | Valore di mercato |
| `v_match_odds` | Quote primarie con probabilità implicite normalizzate, margine del bookmaker, favorito | Quote e pronostici |
| `v_team_expected_points` | Punti attesi dalle quote contro punti reali | Quote e pronostici |
| `v_goal_events` | Gol con fascia di minuto, squadre e marcatore | Gol e momenti |
| `v_top_scorers` | Gol per giocatore e stagione (autogol esclusi), valore di mercato, valore per gol | Home, Gol e momenti |
| `v_player_value_growth` | Valore di mercato del giocatore nella prima e nell'ultima stagione disponibile | Valore di mercato |
| `v_squad_value_growth` | Valore della rosa nella prima e nell'ultima stagione in Serie A del periodo | Valore di mercato |
| `v_team_xg` | xG prodotti e concessi contro gol reali | Statistiche avanzate |
| `v_team_elo` | Elo a inizio e fine stagione contro classifica | Statistiche avanzate |
| `v_team_match_stats` | Tiri, tiri in porta, corner, falli, cartellini per squadra | Statistiche avanzate |
| `v_referee_stats` | Cartellini, falli e % vittorie casalinghe per arbitro | Statistiche avanzate |

### Esempio di interrogazione

```sql
-- Le 3 squadre che hanno fatto più punti rispetto alle attese dei bookmaker
SELECT season, team, ROUND(expected_points, 1) AS attesi, points, ROUND(points_over_expected, 1) AS scarto
FROM v_team_expected_points
ORDER BY points_over_expected DESC
LIMIT 3;
```

Il database si può aprire con qualunque client SQLite (es. DB Browser for SQLite) o da Python:

```python
from football_pipeline.storage import read_sql
read_sql("SELECT * FROM v_standings WHERE season_id = 2025 ORDER BY position")
```

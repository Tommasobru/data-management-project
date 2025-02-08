-- ftb.integrated_view source

CREATE OR REPLACE VIEW ftb.integrated_view
AS 
SELECT g.anno,
    g.giornata,
    g.home_team,
    g.away_team,
    g.scorer,
    p.role,
    p.market_value ,
    g.numero_goal_partita,		
    g.team_goal,
    g.goal,
    g.assist,
    th.giocatori_in_rosa 		AS giocatori_in_rosa_home_team,
    th.stranieri 				AS stranieri_home_team,
    th.eta_media			 	AS eta_media_home_team,
    th.valore_rosa 				AS valore_rosa_home_team,
    ta.giocatori_in_rosa 		AS giocatori_in_rosa_away_team,
    ta.stranieri 				AS stranieri_away_team,
    ta.eta_media 				AS eta_media_away_team,
    ta.valore_rosa	 			AS valore_rosa_away_team
   FROM stg.fact_all_goal_serie_a g
     LEFT JOIN stg.fact_matches match ON match.season = g.anno AND match.giornata = g.giornata AND match.home_team = g.home_team
     LEFT JOIN stg.dim_player_team p ON p.name = g.scorer AND p.stagione = g.anno
     LEFT JOIN stg.dim_list_team th ON th.squadra = g.home_team AND th.stagione = g.anno
     LEFT JOIN stg.dim_list_team ta ON ta.squadra = g.away_team AND ta.stagione = g.anno;
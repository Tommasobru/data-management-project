-- ftb.integrated_view source

CREATE OR REPLACE VIEW ftb.integrated_view
AS SELECT g.anno,
    g.giornata,
    g."Home Team" 				as home_team,
    g."Away Team" 				as away_team,
    g.scorer,
    p."Role" 					as role,
    p."Market Value" 			as market_value ,
    g.numero_goal_partita,		
    g.team_goal,
    g.goal,
    g.assist,
    th."Giocatori in Rosa" 		AS giocatori_in_rosa_home_team,
    th."Stranieri" 				AS stranieri_home_team,
    th."Età Media"			 	AS eta_media_home_team,
    th."Valore Rosa" 			AS valore_rosa_home_team,
    ta."Giocatori in Rosa" 		AS giocatori_in_rosa_away_team,
    ta."Stranieri" 				AS stranieri_away_team,
    ta."Età Media" 				AS eta_media_away_team,
    ta."Valore Rosa" 			AS valore_rosa_away_team
   FROM ftb.all_goal_serie_a g
     LEFT JOIN ( SELECT m.match_id,
            m.giornata,
            m.season,
            m.home_team,
            m.away_team,
            m.home_score,
            m.away_score,
            d.winner,
            d."fullTimeHomeGoal",
            d."fullTimeAwayGoal",
            d."halfTimeHomeGoal",
            d."halfTimeAwayGoal"
           FROM ftb.matches m
             JOIN ftb.matches_details d ON d.match_id = m.match_id) match ON match.season = g.anno AND match.giornata = g.giornata AND match.home_team = g."Home Team"
     LEFT JOIN ftb.player_team p ON p."Name" = g.scorer AND p."Season" = g.anno
     LEFT JOIN ftb.list_team th ON th."Squadra" = g."Home Team" AND th."Stagione" = g.anno
     LEFT JOIN ftb.list_team ta ON ta."Squadra" = g."Away Team" AND ta."Stagione" = g.anno;
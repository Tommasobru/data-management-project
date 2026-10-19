-- Arbitri: cartellini medi ed esiti.
CREATE VIEW v_referee_stats AS
SELECT fs.referee,
       COUNT(*) AS matches,
       1.0 * SUM(fs.home_yellow + fs.away_yellow) / COUNT(*) AS yellow_per_match,
       1.0 * SUM(fs.home_red + fs.away_red) / COUNT(*) AS red_per_match,
       1.0 * SUM(fs.home_fouls + fs.away_fouls) / COUNT(*) AS fouls_per_match,
       100.0 * SUM(CASE WHEN m.result = 'H' THEN 1 ELSE 0 END) / COUNT(*) AS home_win_pct
FROM fact_match_stats fs
JOIN fact_match m ON m.match_id = fs.match_id
WHERE fs.referee IS NOT NULL
GROUP BY fs.referee;

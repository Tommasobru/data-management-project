import json

from football_pipeline.acquisition.api_football import parse_fixtures
from football_pipeline.acquisition.clubelo import parse_snapshot
from football_pipeline.acquisition.football_data_couk import parse_csv, season_code
from football_pipeline.acquisition.football_data_org import parse_matches
from football_pipeline.acquisition.oddsportal import parse_match_text
from football_pipeline.acquisition.transfermarkt import parse_matchday
from football_pipeline.acquisition.understat import extract_embedded_json, parse_dates


def test_football_data_org():
    payload = {"matches": [{
        "id": 1, "matchday": 1, "utcDate": "2024-08-17T16:30:00Z", "status": "FINISHED", "stage": "REGULAR_SEASON",
        "homeTeam": {"name": "Genoa CFC"}, "awayTeam": {"name": "FC Internazionale Milano"},
        "score": {"winner": "DRAW", "fullTime": {"home": 2, "away": 2}, "halfTime": {"home": 1, "away": 1}},
    }]}
    df = parse_matches(payload, 2024)
    assert df.loc[0, "date"] == "2024-08-17" and df.loc[0, "home_score"] == 2


def test_api_football():
    payload = {"errors": [], "response": [{
        "fixture": {"date": "2021-08-21T16:30:00+00:00", "status": {"short": "FT"}},
        "league": {"round": "Regular Season - 1"},
        "teams": {"home": {"name": "Inter", "winner": True}, "away": {"name": "Genoa", "winner": False}},
        "goals": {"home": 4, "away": 0},
        "score": {"halftime": {"home": 2, "away": 0}},
    }]}
    df = parse_fixtures(payload, 2021)
    assert df.loc[0, "matchweek"] == "Regular Season - 1" and df.loc[0, "home_goals"] == 4


def test_clubelo_keeps_only_italy():
    csv = "Rank,Club,Country,Level,Elo,From,To\n1,Inter,ITA,1,1950.5,2024-07-01,2024-08-05\n2,Real Madrid,ESP,1,1990,2024-07-01,2024-08-05\n"
    df = parse_snapshot(csv, 2024, "start", "2024-08-01")
    assert list(df["Club"]) == ["Inter"] and df.iloc[0]["snapshot"] == "start"


def test_football_data_couk():
    assert season_code(2024) == "2425" and season_code(2099) == "9900"
    content = "Div,Date,HomeTeam,AwayTeam,FTHG,FTAG,FTR\nI1,17/08/2024,Genoa,Inter,2,2,D\n,,,,,,\n".encode()
    df = parse_csv(content, 2024)
    assert len(df) == 1 and df.loc[0, "season"] == 2024


def test_understat_embedded_json():
    data = [{"id": "1", "isResult": True, "datetime": "2024-08-17 18:30:00",
             "h": {"title": "Genoa"}, "a": {"title": "Inter"}, "goals": {"h": "2", "a": "2"},
             "xG": {"h": "1.1", "a": "2.3"}, "forecast": {"w": "0.2", "d": "0.25", "l": "0.55"}},
            {"id": "2", "isResult": False}]
    escaped = json.dumps(data).encode("unicode_escape").decode().replace('"', "\\x22")
    html = f"<script>var datesData = JSON.parse('{escaped}');</script>"
    df = parse_dates(extract_embedded_json(html, "datesData"), 2024)
    assert len(df) == 1 and df.loc[0, "away_xg"] == "2.3"


def test_oddsportal_row_layouts():
    # layout usato fino al 2024/25
    old = parse_match_text("20:45\nAtalanta\n2\n–\n3\nComo\n1.50\n4.47\n6.18", 2024)
    assert (old["home_team"], old["away_team"], old["risultato"], old["quota_2"]) == ("Atalanta", "Como", "2-3", "6.18")
    # layout attuale: il gol di casa precede il nome della squadra
    new = parse_match_text("Finita\n0\nCremonese\n-\nTorino\n0\n2.95\n3.20\n2.65", 2025)
    assert (new["home_team"], new["away_team"], new["risultato"], new["quota_1"]) == ("Cremonese", "Torino", "0-0", "2.95")
    assert parse_match_text("Rinv.\nLazio\n-\nRoma\n2.10\n3.10\n3.40", 2025) is None
    assert parse_match_text("incompleta", 2024) is None


def test_transfermarkt_matchday():
    html = """
    <div class="large-8 columns"><div class="box">
      <span class="matchresult">2:3</span>
      <table><tr>
        <td class="rechts hauptlink no-border-rechts hide-for-small spieltagsansicht-vereinsname"><a href="/v" title="Verona">Verona</a></td>
        <td class="hauptlink no-border-links no-border-rechts hide-for-small spieltagsansicht-vereinsname"><a href="/s">Sassuolo</a></td>
      </tr>
      <tr class="spieltagsansicht-aktionen">
        <td class="zentriert hauptlink">0:1</td>
        <td><span class="hide-for-small"><a href="/p">Giacomo Raspadori</a></span>
            <span class="icon-tor-formation" title="32. min: gol"></span></td>
      </tr></table>
    </div></div>"""
    goals = parse_matchday(html, 2021, 1)
    assert goals == [{"season": 2021, "matchweek": 1, "home_team": "Verona", "away_team": "Sassuolo",
                      "goal_result": "0:1", "scorer": "Giacomo Raspadori", "minute": "32"}]

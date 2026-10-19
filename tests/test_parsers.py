from datetime import date

import pytest

from football_pipeline.cleaning.parsers import (
    parse_birth_and_age, parse_decimal_it, parse_money, parse_role, parse_score,
)
from football_pipeline.cleaning.teams import TeamResolver
from football_pipeline.config import get_settings


@pytest.mark.parametrize("raw, expected", [
    ("642,50 mln €", 642_500_000.0),
    ("400 mila €", 400_000.0),
    ("1,05 mld €", 1_050_000_000.0),
    ("-", None),
    (None, None),
])
def test_parse_money(raw, expected):
    assert parse_money(raw) == expected


def test_parse_birth_and_age():
    assert parse_birth_and_age("18/apr/1990 (32)") == (date(1990, 4, 18), 32)
    assert parse_birth_and_age("04/gen/2003 (19)") == (date(2003, 1, 4), 19)
    assert parse_birth_and_age("27/05/1998 (28)") == (date(1998, 5, 27), 28)  # formato 2025/26


def test_parse_role_strips_name():
    raw = "Weston McKennie            \n\n\n\n\n            Centrale"
    assert parse_role(raw, "Weston McKennie") == ("Centrocampista centrale", "Centrocampista")
    assert parse_role("Manuel Locatelli\xa0 \n\n  Mediano") == ("Mediano", "Centrocampista")


def test_parse_score_and_decimal():
    assert parse_score("2-3") == (2, 3)
    assert parse_score("1:0") == (1, 0)
    assert parse_score("rinviata") == (None, None)
    assert parse_decimal_it("25,5") == 25.5


@pytest.mark.parametrize("raw, canonical", [
    ("FC Internazionale Milano", "Inter"),
    ("AC Milan", "Milan"),
    ("Hellas Verona FC", "Verona"),
    ("Parma Calcio 1913", "Parma"),
    ("US Salernitana 1919", "Salernitana"),
    ("Atalanta BC", "Atalanta"),
    ("Juventus", "Juventus"),
])
def test_team_resolver(raw, canonical):
    resolver = TeamResolver(get_settings().team_aliases)
    assert resolver.resolve(raw) == canonical
    assert not resolver.unresolved


def test_team_resolver_tracks_unknown():
    resolver = TeamResolver(get_settings().team_aliases)
    assert resolver.resolve("Real Madrid") == "Real Madrid"
    assert resolver.unresolved == {"Real Madrid"}


def test_new_transfermarkt_roles():
    assert parse_role("Luis Henrique   \n\n   Esterno di destra") == ("Centrocampista di destra", "Centrocampista")
    assert parse_role("X   \n\n   Centrocampista") == ("Centrocampista centrale", "Centrocampista")


@pytest.mark.parametrize("today, expected", [
    (date(2026, 10, 19), [2022, 2023, 2024, 2025]),
    (date(2026, 5, 1), [2021, 2022, 2023, 2024]),   # 2025/26 non ancora conclusa
    (date(2026, 7, 1), [2022, 2023, 2024, 2025]),
])
def test_last_completed_seasons(today, expected):
    from football_pipeline.config import last_completed_seasons
    assert last_completed_seasons(4, today) == expected

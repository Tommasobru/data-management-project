"""Parser per i formati testuali delle fonti di scraping (Transfermarkt è in italiano)."""
from __future__ import annotations

import math
import re
from datetime import date

ITALIAN_MONTHS = {
    "gen": 1, "feb": 2, "mar": 3, "apr": 4, "mag": 5, "giu": 6,
    "lug": 7, "ago": 8, "set": 9, "ott": 10, "nov": 11, "dic": 12,
}

MONEY_MULTIPLIERS = {"mld": 1e9, "mln": 1e6, "mila": 1e3}

# ruolo Transfermarkt -> (ruolo esteso, macro-ruolo)
ROLE_MAP = {
    "Portiere": ("Portiere", "Portiere"),
    "Difensore centrale": ("Difensore centrale", "Difensore"),
    "Terzino destro": ("Terzino destro", "Difensore"),
    "Terzino sinistro": ("Terzino sinistro", "Difensore"),
    "Centrale": ("Centrocampista centrale", "Centrocampista"),
    "Centrocampista centrale": ("Centrocampista centrale", "Centrocampista"),
    "Mediano": ("Mediano", "Centrocampista"),
    "Trequartista": ("Trequartista", "Centrocampista"),
    "Centrocampista di destra": ("Centrocampista di destra", "Centrocampista"),
    "Centrocampista di sinistra": ("Centrocampista di sinistra", "Centrocampista"),
    # nomi introdotti da Transfermarkt nel 2025/26
    "Centrocampista": ("Centrocampista centrale", "Centrocampista"),
    "Esterno di destra": ("Centrocampista di destra", "Centrocampista"),
    "Esterno di sinistra": ("Centrocampista di sinistra", "Centrocampista"),
    "Ala destra": ("Ala destra", "Attaccante"),
    "Ala sinistra": ("Ala sinistra", "Attaccante"),
    "Punta centrale": ("Punta centrale", "Attaccante"),
    "Seconda punta": ("Seconda punta", "Attaccante"),
}


def _is_missing(value) -> bool:
    return value is None or (isinstance(value, float) and math.isnan(value))


def parse_money(value) -> float | None:
    """'642,50 mln €' -> 642500000.0; '400 mila €' -> 400000.0; '-' -> None.

    Un valore mancante resta NULL (la prima versione lo convertiva in 0,
    falsando medie e crescite percentuali).
    """
    if _is_missing(value):
        return None
    text = str(value).replace("€", "").replace("\xa0", " ").strip().lower()
    if text in {"", "-", "?"}:
        return None
    multiplier = 1.0
    for unit, mult in MONEY_MULTIPLIERS.items():
        if unit in text:
            multiplier = mult
            text = text.replace(unit, "").strip()
            break
    text = text.replace(".", "").replace(",", ".")
    try:
        return float(text) * multiplier
    except ValueError:
        return None


def parse_decimal_it(value) -> float | None:
    """'25,5' -> 25.5"""
    if _is_missing(value):
        return None
    try:
        return float(str(value).replace(",", ".").strip())
    except ValueError:
        return None


def parse_birth_and_age(value) -> tuple[date | None, int | None]:
    """'18/apr/1990 (32)' oppure '18/04/1990 (32)' -> (date(1990, 4, 18), 32)

    Transfermarkt è passato dal mese abbreviato in italiano al formato numerico."""
    if _is_missing(value):
        return None, None
    text = str(value)
    age_match = re.search(r"\((\d+)\)", text)
    age = int(age_match.group(1)) if age_match else None
    birth = None
    date_match = re.search(r"(\d{1,2})/([a-z]{3}|\d{1,2})/(\d{4})", text.lower())
    if date_match:
        day, month, year = date_match.groups()
        month_num = int(month) if month.isdigit() else ITALIAN_MONTHS.get(month)
        try:
            birth = date(int(year), month_num, int(day)) if month_num else None
        except ValueError:
            birth = None
    return birth, age


def parse_role(raw_role, name=None) -> tuple[str | None, str | None]:
    """La cella ruolo di Transfermarkt contiene 'Nome   \\n\\n  Ruolo': si tiene l'ultima riga."""
    if _is_missing(raw_role):
        return None, None
    role = str(raw_role).replace("\xa0", " ").split("\n")[-1].strip()
    if name and role.startswith(str(name)):
        role = role[len(str(name)):].strip()
    return ROLE_MAP.get(role, (role or None, None))


def parse_score(value) -> tuple[int | None, int | None]:
    """'2-3' / '2:3' -> (2, 3)"""
    if _is_missing(value):
        return None, None
    match = re.match(r"^\s*(\d+)\s*[-:]\s*(\d+)\s*$", str(value))
    if not match:
        return None, None
    return int(match.group(1)), int(match.group(2))

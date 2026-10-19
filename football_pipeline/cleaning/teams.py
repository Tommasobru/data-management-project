"""Risoluzione dei nomi squadra verso un nome canonico unico per tutte le fonti.

La prima versione usava come riferimento i nomi delle quote e una distanza
ad hoc basata su difflib: qui si usa un dizionario di alias esplicito
(config/team_aliases.yaml) con fallback fuzzy e tracciamento dei nomi non risolti.
"""
from __future__ import annotations

import re

from rapidfuzz import fuzz, process

from football_pipeline.utils.text import normalize_name

# token che non aiutano a distinguere le squadre
_NOISE = re.compile(
    r"\b(fc|ac|as|ss|ssc|us|uc|acf|cfc|bc|sc|calcio|hellas|1907|1909|1913|1919)\b"
)


def _key(name: str) -> str:
    key = _NOISE.sub(" ", normalize_name(name))
    return re.sub(r"\s+", " ", key).strip() or normalize_name(name)


class TeamResolver:
    def __init__(self, aliases: dict[str, list[str]], threshold: int = 85):
        self.threshold = threshold
        self.canonical = sorted(aliases)
        self._lookup: dict[str, str] = {}
        for canonical, variants in aliases.items():
            for variant in [canonical, *(variants or [])]:
                self._lookup[normalize_name(variant)] = canonical
                self._lookup[_key(variant)] = canonical
        self.fuzzy_matches: dict[str, tuple[str, float]] = {}
        self.unresolved: set[str] = set()
        self._cache: dict[str, str] = {}

    def resolve(self, name) -> str | None:
        if name is None or (isinstance(name, float) and name != name):
            return None
        name = str(name).strip()
        if name in self._cache:
            return self._cache[name]
        resolved = self._lookup.get(normalize_name(name)) or self._lookup.get(_key(name))
        if resolved is None:
            match = process.extractOne(_key(name), list(self._lookup), scorer=fuzz.WRatio)
            if match and match[1] >= self.threshold:
                resolved = self._lookup[match[0]]
                self.fuzzy_matches[name] = (resolved, round(match[1], 1))
            else:
                self.unresolved.add(name)
                resolved = name  # si tiene il nome originale: lo segnala la Data Quality
        self._cache[name] = resolved
        return resolved

    def team_ids(self, names) -> dict[str, int]:
        """ID stabili: prima le squadre canoniche (ordine alfabetico), poi le altre."""
        ordered = self.canonical + sorted(set(names) - set(self.canonical))
        return {name: i + 1 for i, name in enumerate(ordered) if name in set(names)}

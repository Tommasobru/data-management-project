"""Client HTTP condiviso: retry con backoff esponenziale, numero massimo di tentativi
e pausa tra le richieste (la prima versione usava un loop infinito)."""
from __future__ import annotations

import random
import time

import requests

from football_pipeline.utils.logging import get_logger

log = get_logger(__name__)

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
}

RETRY_STATUS = {429, 500, 502, 503, 504}


class FetchError(RuntimeError):
    pass


class ConnectionFailed(FetchError):
    """Host irraggiungibile (DNS, rete assente, connessione rifiutata): inutile insistere."""


CONNECTION_ATTEMPTS = 2


class HttpClient:
    def __init__(self, headers: dict | None = None, delay: float = 0.0,
                 max_attempts: int = 4, timeout: float = 30.0):
        self.session = requests.Session()
        self.session.headers.update(headers or {})
        self.delay = delay
        self.max_attempts = max_attempts
        self.timeout = timeout
        self._last_request = 0.0

    def _throttle(self) -> None:
        wait = self.delay - (time.monotonic() - self._last_request)
        if wait > 0:
            time.sleep(wait)
        self._last_request = time.monotonic()

    def get(self, url: str, **kwargs) -> requests.Response:
        kwargs.setdefault("timeout", self.timeout)
        last_error = None
        for attempt in range(self.max_attempts):
            self._throttle()
            try:
                response = self.session.get(url, **kwargs)
                if response.status_code == 200:
                    return response
                if response.status_code not in RETRY_STATUS:
                    raise FetchError(f"HTTP {response.status_code} per {url}")
                last_error = f"HTTP {response.status_code}"
                retry_after = response.headers.get("Retry-After")
                wait = float(retry_after) if retry_after and retry_after.isdigit() else None
            except requests.ConnectionError as exc:
                if attempt + 1 >= CONNECTION_ATTEMPTS:
                    raise ConnectionFailed(f"{url} irraggiungibile: {exc}") from exc
                last_error = str(exc)
                wait = None
            except requests.RequestException as exc:
                last_error = str(exc)
                wait = None
            wait = wait or min(60.0, 2 ** attempt + random.uniform(0, 1))
            log.warning("Tentativo %d/%d fallito (%s): attendo %.1fs",
                        attempt + 1, self.max_attempts, last_error, wait)
            time.sleep(wait)
        raise ConnectionFailed(f"Impossibile scaricare {url} dopo {self.max_attempts} tentativi: {last_error}")

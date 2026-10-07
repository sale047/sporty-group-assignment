"""Thin wrapper around the betting API.

Endpoint methods return the raw `requests.Response` so tests own their assertions
(status codes and error bodies are often the thing under test). The `fetch_*`
helpers are for setup/verification steps and fail fast on unexpected responses.
"""

from decimal import Decimal
from typing import Any

import requests

from framework.api.models import Match, Selection
from framework.utils.money import to_money


class BettingApiClient:
    def __init__(self, base_url: str, user_id: str, timeout: float) -> None:
        self._base_url = base_url
        self._timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({"x-user-id": user_id, "Accept": "application/json"})

    def close(self) -> None:
        self._session.close()

    def get_matches(self) -> requests.Response:
        return self._request("GET", "/api/matches")

    def get_balance(self) -> requests.Response:
        return self._request("GET", "/api/balance")

    def reset_balance(self) -> requests.Response:
        return self._request("POST", "/api/reset-balance")

    def place_bet(self, match_id: str, selection: Selection | str, stake: Any) -> requests.Response:
        selection_value = selection.value if isinstance(selection, Selection) else selection
        return self.place_bet_raw({"matchId": match_id, "selection": selection_value, "stake": stake})

    def place_bet_raw(self, payload: Any) -> requests.Response:
        return self._request("POST", "/api/place-bet", json=payload)

    def fetch_matches(self) -> list[Match]:
        response = self.get_matches()
        response.raise_for_status()
        return [Match.from_api(item) for item in response.json()]

    def fetch_balance(self) -> Decimal:
        response = self.get_balance()
        response.raise_for_status()
        return to_money(response.json()["balance"])

    def _request(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        return self._session.request(method, f"{self._base_url}{path}", timeout=self._timeout, **kwargs)

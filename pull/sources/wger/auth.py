from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib.request import Request, urlopen

from .endpoints import TOKEN, TOKEN_REFRESH, TOKEN_VERIFY


@dataclass(frozen=True)
class WgerTokens:
    access: str
    refresh: str


@dataclass
class WgerAuth:
    base_url: str
    username: str
    password: str
    timeout_seconds: float = 15.0

    def obtain_tokens(self) -> WgerTokens:
        payload = self._post_json(TOKEN, {"username": self.username, "password": self.password})
        return WgerTokens(access=payload["access"], refresh=payload["refresh"])

    def refresh_tokens(self, refresh_token: str) -> WgerTokens:
        payload = self._post_json(TOKEN_REFRESH, {"refresh": refresh_token})
        return WgerTokens(access=payload["access"], refresh=payload.get("refresh", refresh_token))

    def verify_access(self, access_token: str) -> dict[str, Any]:
        return self._post_json(TOKEN_VERIFY, {"token": access_token})

    def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        request = Request(
            f"{self.base_url}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"content-type": "application/json", "accept": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=self.timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))

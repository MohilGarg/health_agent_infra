from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .auth import HevyAuth
from .endpoints import BASE_URL, USER_INFO, WORKOUT_DETAIL, WORKOUT_EVENTS


@dataclass
class HevyClient:
    auth: HevyAuth
    timeout_seconds: float = 15.0

    def get_user_info(self) -> dict[str, Any]:
        return self._get_json(USER_INFO)

    def get_workout_events(self, *, since: str, page: int = 1, page_size: int = 10) -> dict[str, Any]:
        query = urlencode({"since": since, "page": page, "pageSize": page_size})
        return self._get_json(f"{WORKOUT_EVENTS}?{query}")

    def get_workout_detail(self, workout_id: str) -> dict[str, Any]:
        return self._get_json(WORKOUT_DETAIL.format(workout_id=workout_id))

    def _get_json(self, path: str) -> dict[str, Any]:
        request = Request(
            f"{BASE_URL}{path}",
            headers={**self.auth.headers(), "accept": "application/json"},
            method="GET",
        )
        with urlopen(request, timeout=self.timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))

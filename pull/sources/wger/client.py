from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .endpoints import DELETION_LOG, EXERCISEINFO, ROUTINE, ROUTINE_STRUCTURE, WORKOUTLOG, WORKOUTSESSION


@dataclass
class WgerClient:
    base_url: str
    access_token: str
    timeout_seconds: float = 15.0

    def get_exerciseinfo(self, *, page: int = 1, page_size: int = 50) -> dict[str, Any]:
        return self._get_json(EXERCISEINFO, page=page, limit=page_size)

    def get_deletion_log(self) -> dict[str, Any]:
        return self._get_json(DELETION_LOG)

    def get_workoutsession(self, *, date_from: str, page: int = 1, page_size: int = 50) -> dict[str, Any]:
        return self._get_json(WORKOUTSESSION, page=page, limit=page_size, date_after=date_from)

    def get_workoutlog(self, *, date_from: str, page: int = 1, page_size: int = 50) -> dict[str, Any]:
        return self._get_json(WORKOUTLOG, page=page, limit=page_size, date_after=date_from)

    def get_routines(self) -> dict[str, Any]:
        return self._get_json(ROUTINE)

    def get_routine_structure(self, routine_id: int) -> dict[str, Any]:
        return self._get_json(ROUTINE_STRUCTURE.format(routine_id=routine_id))

    def _get_json(self, path: str, **params: Any) -> dict[str, Any]:
        query = urlencode({key: value for key, value in params.items() if value is not None})
        url = f"{self.base_url}{path}"
        if query:
            url = f"{url}?{query}"
        request = Request(
            url,
            headers={"accept": "application/json", "authorization": f"Bearer {self.access_token}"},
            method="GET",
        )
        with urlopen(request, timeout=self.timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))

from __future__ import annotations

from dataclasses import dataclass
from os import getenv


API_KEY_ENV_VAR = "HEVY_API_KEY"


@dataclass(frozen=True)
class HevyAuth:
    api_key: str

    @classmethod
    def from_env(cls) -> "HevyAuth | None":
        api_key = getenv(API_KEY_ENV_VAR)
        if not api_key:
            return None
        return cls(api_key=api_key)

    def headers(self) -> dict[str, str]:
        return {"api-key": self.api_key}

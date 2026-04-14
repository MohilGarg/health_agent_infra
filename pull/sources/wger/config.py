from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WgerConfig:
    base_url: str
    username: str
    password: str
    page_size: int = 50
    training_overlap_days: int = 14
    parser_version: str = "wger_v1"

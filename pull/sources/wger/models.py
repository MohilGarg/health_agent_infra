from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class WgerExercise:
    id: int
    uuid: str
    last_update_global: str
    category: str
    name: str
    aliases: tuple[str, ...]
    equipment: tuple[str, ...]
    primary_muscles: tuple[str, ...]
    secondary_muscles: tuple[str, ...]

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "WgerExercise":
        translation = payload.get("translations", [{}])[0]
        return cls(
            id=payload["id"],
            uuid=payload["uuid"],
            last_update_global=payload["last_update_global"],
            category=payload.get("category", {}).get("name", "unknown"),
            name=translation.get("name", payload.get("uuid", "unknown")),
            aliases=tuple(alias["alias"] for alias in payload.get("aliases", [])),
            equipment=tuple(item["name"] for item in payload.get("equipment", [])),
            primary_muscles=tuple(item["name"] for item in payload.get("muscles", [])),
            secondary_muscles=tuple(item["name"] for item in payload.get("muscles_secondary", [])),
        )


@dataclass(frozen=True)
class WgerRoutine:
    id: int
    name: str
    start: str | None
    end: str | None


@dataclass(frozen=True)
class WgerWorkoutSession:
    id: int
    routine: int
    day: int | None
    date: str
    notes: str | None
    time_start: str | None
    time_end: str | None


@dataclass(frozen=True)
class WgerWorkoutLog:
    id: int
    session: int
    exercise_id: int
    exercise_name: str
    repetitions: int | None
    weight: float | None
    weight_unit: str | None
    rir: float | None
    created: str

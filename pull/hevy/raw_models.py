from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class HevySet:
    index: int
    type: str
    reps: int | None = None
    weight_kg: float | None = None
    rpe: float | None = None
    duration_seconds: int | None = None
    distance_meters: float | None = None
    custom_metric: str | None = None


@dataclass(frozen=True)
class HevyExercise:
    index: int
    title: str
    exercise_template_id: str | None
    notes: str | None = None
    supersets_id: str | None = None
    sets: tuple[HevySet, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class HevyWorkout:
    id: str
    title: str | None
    description: str | None
    start_time: str
    end_time: str | None
    created_at: str | None
    updated_at: str
    exercises: tuple[HevyExercise, ...] = field(default_factory=tuple)

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "HevyWorkout":
        exercises: list[HevyExercise] = []
        for exercise in payload.get("exercises", []):
            sets = tuple(
                HevySet(
                    index=item["index"],
                    type=item.get("type", "normal"),
                    reps=item.get("reps"),
                    weight_kg=item.get("weight_kg"),
                    rpe=item.get("rpe"),
                    duration_seconds=item.get("duration_seconds"),
                    distance_meters=item.get("distance_meters"),
                    custom_metric=item.get("custom_metric"),
                )
                for item in exercise.get("sets", [])
            )
            exercises.append(
                HevyExercise(
                    index=exercise["index"],
                    title=exercise["title"],
                    exercise_template_id=exercise.get("exercise_template_id"),
                    notes=exercise.get("notes"),
                    supersets_id=exercise.get("supersets_id"),
                    sets=sets,
                )
            )
        return cls(
            id=payload["id"],
            title=payload.get("title"),
            description=payload.get("description"),
            start_time=payload["start_time"],
            end_time=payload.get("end_time"),
            created_at=payload.get("created_at"),
            updated_at=payload["updated_at"],
            exercises=tuple(exercises),
        )

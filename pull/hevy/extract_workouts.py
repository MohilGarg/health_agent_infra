from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any


@dataclass
class SourceRecord:
    artifact_family: str = "source_record"
    source_record_id: str = ""
    source_name: str = ""
    source_type: str = ""
    entry_lane: str = ""
    raw_location: str = ""
    raw_format: str = ""
    effective_date: str | None = None
    collected_at: str | None = None
    ingested_at: str | None = None
    hash_or_version: str | None = None
    native_record_type: str | None = None
    native_record_id: str | None = None


@dataclass
class ProvenanceRecord:
    artifact_family: str = "provenance_record"
    provenance_record_id: str = ""
    source_record_id: str = ""
    derivation_method: str = ""
    supporting_refs: list[str] | None = None
    parser_version: str | None = None
    conflict_status: str = "none"


@dataclass
class TrainingSession:
    artifact_family: str = "training_session"
    session_id: str = ""
    date: str = ""
    session_type: str = ""
    source: str = ""
    training_session_id: str | None = None
    source_name: str | None = None
    source_record_id: str | None = None
    provenance_record_id: str | None = None
    confidence_label: str | None = None
    conflict_status: str = "none"
    start_time_local: str | None = None
    duration_sec: float | None = None
    session_title: str | None = None
    notes: str | None = None
    lift_focus: str | None = None
    exercise_count: int | None = None
    total_sets: int | None = None
    total_reps: int | None = None
    total_load_kg: float | None = None


@dataclass
class GymExerciseSet:
    artifact_family: str = "gym_exercise_set"
    set_id: str = ""
    session_id: str = ""
    training_session_id: str | None = None
    gym_exercise_set_id: str | None = None
    date: str = ""
    exercise_name: str = ""
    source_name: str | None = None
    source_record_id: str | None = None
    provenance_record_id: str | None = None
    confidence_label: str | None = None
    conflict_status: str = "none"
    set_number: int | None = None
    reps: int | None = None
    weight_kg: float | None = None
    rpe: float | None = None
    completed_bool: bool | None = None
    note: str | None = None

from .incremental import advance_watermark, dedupe_event_page
from .raw_models import HevyWorkout
from .source_ids import gym_exercise_set_id, training_session_id, workout_source_record_id
from .tombstones import tombstone_record

PARSER_VERSION = "hevy_v1"


@dataclass
class HevyExtractionResult:
    source_record: dict[str, Any]
    provenance_record: dict[str, Any]
    training_session: dict[str, Any]
    gym_exercise_sets: list[dict[str, Any]]


def extract_training_payloads(*, account_id: str, workout_payload: dict[str, Any], raw_location: str) -> HevyExtractionResult:
    workout = HevyWorkout.from_payload(workout_payload)
    source_record_id = workout_source_record_id(account_id, workout.id)
    provenance_record_id = f"provenance:{source_record_id}"
    session_id = training_session_id(account_id, workout.id)
    session_date = workout.start_time.split("T", 1)[0]

    total_sets = 0
    total_reps = 0
    total_load_kg = 0.0
    gym_sets: list[dict[str, Any]] = []

    for exercise in workout.exercises:
        for hevy_set in exercise.sets:
            total_sets += 1
            total_reps += hevy_set.reps or 0
            total_load_kg += (hevy_set.reps or 0) * (hevy_set.weight_kg or 0.0)
            gym_sets.append(
                asdict(
                    GymExerciseSet(
                        set_id=gym_exercise_set_id(account_id, workout.id, exercise.index, hevy_set.index),
                        training_session_id=session_id,
                        gym_exercise_set_id=gym_exercise_set_id(account_id, workout.id, exercise.index, hevy_set.index),
                        date=session_date,
                        session_id=session_id,
                        exercise_name=exercise.title,
                        source_name="hevy",
                        source_record_id=source_record_id,
                        provenance_record_id=provenance_record_id,
                        confidence_label="high",
                        set_number=hevy_set.index,
                        reps=hevy_set.reps,
                        weight_kg=hevy_set.weight_kg,
                        rpe=hevy_set.rpe,
                        note=exercise.notes,
                        completed_bool=True,
                    )
                )
            )

    start_dt = datetime.fromisoformat(workout.start_time.replace("Z", "+00:00"))
    end_dt = datetime.fromisoformat((workout.end_time or workout.start_time).replace("Z", "+00:00"))
    duration_sec = max((end_dt - start_dt).total_seconds(), 0.0)

    source_record = SourceRecord(
        source_record_id=source_record_id,
        source_name="hevy",
        source_type="wearable",
        entry_lane="pull",
        raw_location=raw_location,
        raw_format="json",
        effective_date=session_date,
        collected_at=workout.updated_at,
        ingested_at=workout.updated_at,
        hash_or_version=workout.updated_at,
        native_record_type="workout",
        native_record_id=workout.id,
    )
    provenance_record = ProvenanceRecord(
        provenance_record_id=provenance_record_id,
        source_record_id=source_record_id,
        derivation_method="wearable_normalization",
        supporting_refs=[raw_location],
        parser_version=PARSER_VERSION,
        conflict_status="none",
    )
    training_session = TrainingSession(
        session_id=session_id,
        training_session_id=session_id,
        date=session_date,
        session_type="gym",
        source="hevy",
        source_name="hevy",
        source_record_id=source_record_id,
        provenance_record_id=provenance_record_id,
        confidence_label="high",
        conflict_status="none",
        start_time_local=workout.start_time,
        duration_sec=duration_sec,
        session_title=workout.title,
        notes=workout.description,
        lift_focus=workout.title,
        exercise_count=len(workout.exercises),
        total_sets=total_sets,
        total_reps=total_reps,
        total_load_kg=total_load_kg,
    )

    return HevyExtractionResult(
        source_record=asdict(source_record),
        provenance_record=asdict(provenance_record),
        training_session=asdict(training_session),
        gym_exercise_sets=gym_sets,
    )


def process_event_page(*, account_id: str, since: str, events_payload: dict[str, Any]) -> dict[str, Any]:
    deduped_events = dedupe_event_page(events_payload.get("events", []))
    updated_ids = [event["workout"]["id"] for event in deduped_events if event["type"] == "updated"]
    tombstones = [
        tombstone_record(account_id, event["id"], event["deleted_at"])
        for event in deduped_events
        if event["type"] == "deleted"
    ]
    return {
        "ordered_events": deduped_events,
        "updated_workout_ids": updated_ids,
        "tombstones": tombstones,
        "next_watermark": advance_watermark(since, deduped_events),
        "webhook_dependency": False,
    }

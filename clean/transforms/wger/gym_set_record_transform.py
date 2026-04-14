from __future__ import annotations

from .ids import exercise_catalog_id, gym_set_record_id, source_record_id, training_session_id
from .provenance import build_provenance
from .units import to_kg


def transform_gym_set_record(*, instance: str, workoutlog: dict, raw_location: str, parser_version: str) -> tuple[dict, dict, dict]:
    log_id = workoutlog["id"]
    record_id = source_record_id(instance, "workoutlog", str(log_id))
    provenance = build_provenance(record_id, raw_location, parser_version)
    row = {
        "artifact_family": "gym_set_record",
        "gym_set_record_id": gym_set_record_id(instance, log_id),
        "training_session_id": training_session_id(instance, workoutlog["session"]),
        "date": workoutlog["date"],
        "exercise_catalog_id": exercise_catalog_id(instance, workoutlog["exercise_uuid"]),
        "exercise_alias_id": None,
        "source_name": "wger",
        "source_record_id": record_id,
        "provenance_record_id": provenance["provenance_record_id"],
        "conflict_status": "none",
        "set_number": workoutlog.get("set_number", log_id),
        "reps": workoutlog.get("repetitions"),
        "weight_kg": to_kg(workoutlog.get("weight"), workoutlog.get("weight_unit")),
        "rir": workoutlog.get("rir"),
        "rpe": None,
        "completed_bool": True,
        "set_type": "working",
        "note": workoutlog.get("notes"),
    }
    source = {
        "artifact_family": "source_record",
        "source_record_id": record_id,
        "source_name": "wger",
        "source_type": "resistance_training_platform",
        "entry_lane": "pull",
        "raw_location": raw_location,
        "raw_format": "json",
        "effective_date": workoutlog["date"],
        "collected_at": workoutlog["date"],
        "ingested_at": workoutlog["date"],
        "hash_or_version": workoutlog["date"],
        "native_record_type": "workoutlog",
        "native_record_id": str(log_id),
    }
    return source, provenance, row

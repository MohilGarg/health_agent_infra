from __future__ import annotations

from datetime import datetime

from .ids import source_record_id, training_session_id
from .provenance import build_provenance


def transform_training_session(*, instance: str, workoutsession: dict, workoutlogs: list[dict], raw_location: str, parser_version: str) -> tuple[dict, dict, dict]:
    session_native_id = workoutsession["id"]
    record_id = source_record_id(instance, "workoutsession", str(session_native_id))
    provenance = build_provenance(record_id, raw_location, parser_version)
    start = workoutsession.get("time_start")
    end = workoutsession.get("time_end")
    duration_sec = None
    if start and end:
        duration_sec = max((datetime.fromisoformat(end) - datetime.fromisoformat(start)).total_seconds(), 0.0)
    total_reps = sum(log.get("repetitions") or 0 for log in workoutlogs)
    total_sets = len(workoutlogs)
    total_load_kg = sum((log.get("repetitions") or 0) * float(log.get("weight") or 0.0) for log in workoutlogs)
    row = {
        "artifact_family": "training_session",
        "training_session_id": training_session_id(instance, session_native_id),
        "session_id": training_session_id(instance, session_native_id),
        "date": workoutsession["date"],
        "session_type": "resistance_training",
        "source": "wger",
        "source_name": "wger",
        "source_record_id": record_id,
        "provenance_record_id": provenance["provenance_record_id"],
        "conflict_status": "none",
        "start_time_local": start,
        "duration_sec": duration_sec,
        "session_title": workoutsession.get("routine_name") or f"Routine {workoutsession.get('routine')}",
        "notes": workoutsession.get("notes"),
        "lift_focus": workoutsession.get("routine_name"),
        "exercise_count": len({log.get("exercise") for log in workoutlogs}),
        "total_sets": total_sets,
        "total_reps": total_reps,
        "total_load_kg": total_load_kg,
    }
    source = {
        "artifact_family": "source_record",
        "source_record_id": record_id,
        "source_name": "wger",
        "source_type": "resistance_training_platform",
        "entry_lane": "pull",
        "raw_location": raw_location,
        "raw_format": "json",
        "effective_date": workoutsession["date"],
        "collected_at": workoutsession.get("date"),
        "ingested_at": workoutsession.get("date"),
        "hash_or_version": workoutsession.get("date"),
        "native_record_type": "workoutsession",
        "native_record_id": str(session_native_id),
    }
    return source, provenance, row

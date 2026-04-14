from __future__ import annotations

from .ids import exercise_catalog_id, source_record_id
from .provenance import build_provenance


def transform_exercise_catalog(*, instance: str, exercise: dict, raw_location: str, parser_version: str) -> tuple[dict, dict, dict]:
    exercise_uuid = exercise["uuid"]
    record_id = source_record_id(instance, "exercise", exercise_uuid)
    provenance = build_provenance(record_id, raw_location, parser_version)
    translation = exercise.get("translations", [{}])[0]
    row = {
        "artifact_family": "exercise_catalog",
        "exercise_catalog_id": exercise_catalog_id(instance, exercise_uuid),
        "canonical_exercise_name": translation.get("name", exercise_uuid),
        "movement_pattern": exercise.get("category", {}).get("name", "unknown"),
        "equipment": [item["name"] for item in exercise.get("equipment", [])],
        "primary_muscle_groups": [item["name"] for item in exercise.get("muscles", [])],
        "secondary_muscle_groups": [item["name"] for item in exercise.get("muscles_secondary", [])],
        "source_name": "wger",
        "source_record_id": record_id,
        "provenance_record_id": provenance["provenance_record_id"],
        "conflict_status": "none",
    }
    source = {
        "artifact_family": "source_record",
        "source_record_id": record_id,
        "source_name": "wger",
        "source_type": "resistance_training_platform",
        "entry_lane": "pull",
        "raw_location": raw_location,
        "raw_format": "json",
        "effective_date": None,
        "collected_at": exercise.get("last_update_global"),
        "ingested_at": exercise.get("last_update_global"),
        "hash_or_version": exercise.get("last_update_global"),
        "native_record_type": "exerciseinfo",
        "native_record_id": exercise_uuid,
    }
    return source, provenance, row

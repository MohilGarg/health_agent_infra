from __future__ import annotations

from .ids import exercise_alias_id, exercise_catalog_id, source_record_id
from .provenance import build_provenance


def _slug(value: str) -> str:
    return value.lower().replace(" ", "-")


def transform_exercise_aliases(*, instance: str, exercise: dict, raw_location: str, parser_version: str) -> tuple[dict, list[dict]]:
    exercise_uuid = exercise["uuid"]
    record_id = source_record_id(instance, "exercise", exercise_uuid)
    provenance = build_provenance(record_id, raw_location, parser_version)
    rows = []
    translation = exercise.get("translations", [{}])[0]
    names = [translation.get("name")] + [item.get("alias") for item in exercise.get("aliases", [])]
    for alias_name in [name for name in names if name]:
        rows.append(
            {
                "artifact_family": "exercise_alias",
                "exercise_alias_id": exercise_alias_id(instance, exercise_uuid, _slug(alias_name)),
                "exercise_catalog_id": exercise_catalog_id(instance, exercise_uuid),
                "alias_name": alias_name,
                "source_name": "wger",
                "source_record_id": record_id,
                "provenance_record_id": provenance["provenance_record_id"],
                "source_native_exercise_id": exercise_uuid,
                "normalization_rule": "wger_translation_or_alias",
                "conflict_status": "none",
            }
        )
    return provenance, rows

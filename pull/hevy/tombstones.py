from __future__ import annotations


def tombstone_record(account_id: str, workout_id: str, deleted_at: str) -> dict[str, str]:
    source_record_id = f"hevy:{account_id}:workout:{workout_id}"
    return {
        "artifact_family": "source_record_tombstone",
        "source_name": "hevy",
        "source_record_id": source_record_id,
        "native_record_id": workout_id,
        "deleted_at": deleted_at,
        "status": "deleted",
    }

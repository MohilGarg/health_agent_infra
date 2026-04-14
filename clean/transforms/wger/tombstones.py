from __future__ import annotations


def apply_deletion_log(entries: list[dict]) -> list[dict]:
    rows = []
    for entry in entries:
        rows.append(
            {
                "source_name": "wger",
                "native_model_type": entry["model_type"],
                "source_native_uuid": entry["uuid"],
                "replaced_by": entry.get("replaced_by"),
                "timestamp": entry["timestamp"],
                "status": "deleted",
            }
        )
    return rows

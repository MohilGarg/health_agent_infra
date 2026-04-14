from __future__ import annotations

import hashlib
import json

from .ids import program_block_id, source_record_id
from .provenance import build_provenance


def transform_program_block(*, instance: str, routine: dict, structure: dict, raw_location: str, parser_version: str) -> tuple[dict, dict, dict]:
    routine_id = routine["id"]
    record_id = source_record_id(instance, "routine", str(routine_id))
    provenance = build_provenance(record_id, raw_location, parser_version)
    structure_hash = hashlib.sha256(json.dumps(structure, sort_keys=True).encode("utf-8")).hexdigest()[:12]
    row = {
        "artifact_family": "program_block",
        "program_block_id": program_block_id(instance, routine_id, structure_hash),
        "source_name": "wger",
        "source_record_id": record_id,
        "provenance_record_id": provenance["provenance_record_id"],
        "conflict_status": "none",
        "start_date": routine.get("start") or structure.get("start"),
        "end_date": routine.get("end") or structure.get("end"),
        "block_name": routine.get("name"),
        "goal": structure.get("goal"),
        "split_type": structure.get("split_type"),
        "planned_frequency": len(structure.get("days", [])),
        "adherence_status": "unknown",
        "structure_hash": structure_hash,
    }
    source = {
        "artifact_family": "source_record",
        "source_record_id": record_id,
        "source_name": "wger",
        "source_type": "resistance_training_platform",
        "entry_lane": "pull",
        "raw_location": raw_location,
        "raw_format": "json",
        "effective_date": routine.get("start"),
        "collected_at": routine.get("start"),
        "ingested_at": routine.get("start"),
        "hash_or_version": row["structure_hash"],
        "native_record_type": "routine",
        "native_record_id": str(routine_id),
    }
    return source, provenance, row

from __future__ import annotations


def provenance_record_id(source_record_id: str) -> str:
    return f"provenance:{source_record_id}"


def build_provenance(source_record_id: str, raw_location: str, parser_version: str) -> dict:
    return {
        "artifact_family": "provenance_record",
        "provenance_record_id": provenance_record_id(source_record_id),
        "source_record_id": source_record_id,
        "derivation_method": "wearable_normalization",
        "supporting_refs": [raw_location],
        "parser_version": parser_version,
        "conflict_status": "none",
    }

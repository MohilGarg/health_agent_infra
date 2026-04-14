from __future__ import annotations


def source_record_id(instance: str, record_type: str, native_id: str) -> str:
    return f"wger:{instance}:{record_type}:{native_id}"


def exercise_catalog_id(instance: str, exercise_uuid: str) -> str:
    return f"exercise_catalog:wger:{instance}:exercise:{exercise_uuid}"


def exercise_alias_id(instance: str, exercise_uuid: str, alias_slug: str) -> str:
    return f"exercise_alias:wger:{instance}:exercise:{exercise_uuid}:alias:{alias_slug}"


def training_session_id(instance: str, session_id: int) -> str:
    return f"training_session:wger:{instance}:session:{session_id}"


def gym_set_record_id(instance: str, log_id: int) -> str:
    return f"gym_set_record:wger:{instance}:log:{log_id}"


def program_block_id(instance: str, routine_id: int, structure_hash: str) -> str:
    return f"program_block:wger:{instance}:routine:{routine_id}:structure:{structure_hash}"

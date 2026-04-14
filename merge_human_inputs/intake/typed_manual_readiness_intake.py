from __future__ import annotations

from typing import Any, Mapping

from health_model.manual_logging import build_manual_source_artifact
from health_model.shared_input_backbone import ConfidenceLabel, ConflictStatus, ExtractionStatus

from .voice_note_intake import subjective_provenance_record_id, subjective_source_record_id


DEFAULT_SOURCE_NAME = "manual_structured_readiness"
DEFAULT_READINESS_INPUT_TYPE = "typed_manual_readiness_v1"

__all__ = [
    "build_typed_manual_readiness_source_artifact",
    "build_subjective_daily_entry_from_typed_manual_readiness",
    "build_typed_manual_readiness_intake_bundle",
    "canonicalize_typed_manual_readiness_payload",
]


def build_typed_manual_readiness_source_artifact(
    *,
    artifact_id: str,
    user_id: str,
    collected_at: str,
    ingested_at: str,
    raw_location: str,
    source_name: str = DEFAULT_SOURCE_NAME,
    raw_format: str = "json",
    source_record_id: str | None = None,
    hash_or_version: str | None = None,
    parser_version: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    return build_manual_source_artifact(
        artifact_id=artifact_id,
        user_id=user_id,
        source_name=source_name,
        collected_at=collected_at,
        ingested_at=ingested_at,
        raw_location=raw_location,
        raw_format=raw_format,
        source_record_id=source_record_id,
        hash_or_version=hash_or_version,
        parser_version=parser_version,
        notes=notes,
    )


def build_subjective_daily_entry_from_typed_manual_readiness(
    *,
    entry_id: str,
    user_id: str,
    date: str,
    source_artifact_id: str,
    source_name: str = DEFAULT_SOURCE_NAME,
    free_text_summary: str,
    extraction_status: str,
    confidence_score: float,
    conflict_status: str = "none",
    energy_self_rating: int | None = None,
    stress_self_rating: int | None = None,
    mood_self_rating: int | None = None,
    perceived_sleep_quality: int | None = None,
    illness_or_soreness_flag: bool | None = None,
    soreness_today_1_to_5: int | None = None,
    training_intent_today: str | None = None,
    unusual_constraints_or_stressors: str | None = None,
    readiness_input_type: str = DEFAULT_READINESS_INPUT_TYPE,
    derived_soreness_flag_rule: str | None = None,
) -> dict[str, Any]:
    source_record_id = subjective_source_record_id(source_artifact_id=source_artifact_id, date=date)
    return _drop_none_values(
        {
            "entry_id": entry_id,
            "user_id": user_id,
            "date": date,
            "source_name": source_name,
            "source_record_id": source_record_id,
            "provenance_record_id": subjective_provenance_record_id(source_record_id=source_record_id),
            "conflict_status": ConflictStatus(conflict_status).value,
            "energy_self_rating": energy_self_rating,
            "stress_self_rating": stress_self_rating,
            "mood_self_rating": mood_self_rating,
            "perceived_sleep_quality": perceived_sleep_quality,
            "illness_or_soreness_flag": illness_or_soreness_flag,
            "soreness_today_1_to_5": soreness_today_1_to_5,
            "training_intent_today": training_intent_today,
            "unusual_constraints_or_stressors": unusual_constraints_or_stressors,
            "free_text_summary": free_text_summary,
            "extraction_status": ExtractionStatus(extraction_status).value,
            "source_artifact_ids": [source_artifact_id],
            "confidence_label": _confidence_label_for_score(confidence_score),
            "confidence_score": confidence_score,
            "readiness_input_type": readiness_input_type,
            "derived_soreness_flag_rule": derived_soreness_flag_rule,
        }
    )


def build_typed_manual_readiness_intake_bundle(
    *,
    source_artifact: dict[str, Any],
    subjective_daily_entry: dict[str, Any],
) -> dict[str, Any]:
    return {
        "source_artifacts": [_drop_none_values(source_artifact)],
        "input_events": [],
        "subjective_daily_entries": [_drop_none_values(subjective_daily_entry)],
        "manual_log_entries": [],
    }


def canonicalize_typed_manual_readiness_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    readiness = payload["manual_readiness"]
    source_name = readiness.get("source_name", DEFAULT_SOURCE_NAME)
    artifact = build_typed_manual_readiness_source_artifact(
        artifact_id=payload["artifact_id"],
        user_id=payload["user_id"],
        source_name=source_name,
        collected_at=readiness["collected_at"],
        ingested_at=readiness["ingested_at"],
        raw_location=readiness["raw_location"],
        raw_format=readiness.get("raw_format", "json"),
        source_record_id=readiness.get("source_record_id"),
        hash_or_version=readiness.get("hash_or_version"),
        parser_version=payload.get("parser_version") or readiness.get("parser_version"),
        notes=readiness.get("notes"),
    )

    entry = payload["subjective_entry"]
    soreness_today_1_to_5 = entry.get("soreness_today_1_to_5")
    illness_or_soreness_flag = entry.get("illness_or_soreness_flag")
    derived_soreness_flag_rule = None
    if illness_or_soreness_flag is None and soreness_today_1_to_5 is not None:
        illness_or_soreness_flag = int(soreness_today_1_to_5) >= 3
        derived_soreness_flag_rule = "soreness_today_1_to_5 >= 3"

    subjective_entry = build_subjective_daily_entry_from_typed_manual_readiness(
        entry_id=entry["entry_id"],
        user_id=payload["user_id"],
        date=entry["date"],
        source_artifact_id=artifact["artifact_id"],
        source_name=entry.get("source_name", source_name),
        free_text_summary=_free_text_summary(entry),
        extraction_status=entry["extraction_status"],
        confidence_score=entry["confidence_score"],
        conflict_status=entry.get("conflict_status", "none"),
        energy_self_rating=entry.get("energy_self_rating"),
        stress_self_rating=entry.get("stress_self_rating"),
        mood_self_rating=entry.get("mood_self_rating"),
        perceived_sleep_quality=entry.get("perceived_sleep_quality"),
        illness_or_soreness_flag=illness_or_soreness_flag,
        soreness_today_1_to_5=soreness_today_1_to_5,
        training_intent_today=entry.get("training_intent_today"),
        unusual_constraints_or_stressors=entry.get("unusual_constraints_or_stressors"),
        readiness_input_type=entry.get("readiness_input_type", DEFAULT_READINESS_INPUT_TYPE),
        derived_soreness_flag_rule=entry.get("derived_soreness_flag_rule", derived_soreness_flag_rule),
    )

    return build_typed_manual_readiness_intake_bundle(
        source_artifact=artifact,
        subjective_daily_entry=subjective_entry,
    )


def _free_text_summary(entry: Mapping[str, Any]) -> str:
    explicit_summary = entry.get("free_text_summary")
    if explicit_summary is not None:
        return str(explicit_summary)

    parts = [
        str(entry["training_intent_today"])
        for key in ("training_intent_today",)
        if entry.get(key)
    ]
    if entry.get("unusual_constraints_or_stressors"):
        parts.append(str(entry["unusual_constraints_or_stressors"]))
    return " | ".join(parts)


def _confidence_label_for_score(score: float) -> str:
    if score >= 0.8:
        return ConfidenceLabel.HIGH.value
    if score >= 0.5:
        return ConfidenceLabel.MEDIUM.value
    return ConfidenceLabel.LOW.value


def _drop_none_values(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if value is not None}

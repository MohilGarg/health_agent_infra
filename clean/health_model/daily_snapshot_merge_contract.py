from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

POLICY_VERSION = "daily-health-snapshot-merge-contract-v1"
TRUTHFUL_OUTCOMES = {
    "blocked": "snapshot_blocked",
    "partial": "snapshot_emitted_partial_truthful",
    "complete": "snapshot_emitted_complete_for_declared_lanes",
}
LANE_STATES = {"ready", "missing", "stale", "blocked"}

FIELD_OWNERSHIP = {
    "sleep_duration_hours": "garmin",
    "sleep_score": "garmin",
    "sleep_awake_count": "garmin",
    "resting_hr": "garmin",
    "hrv_status": "garmin",
    "body_battery_or_readiness": "garmin",
    "readiness_label": "garmin",
    "running_sessions_count": "garmin",
    "running_volume_m": "garmin",
    "food_logged_bool": "cronometer",
    "calories_kcal": "cronometer",
    "protein_g": "cronometer",
    "carbs_g": "cronometer",
    "fat_g": "cronometer",
    "hydration_ml": "cronometer",
    "gym_sessions_count": "resistance_training",
    "gym_total_sets": "resistance_training",
    "gym_total_reps": "resistance_training",
    "gym_total_load_kg": "resistance_training",
    "subjective_energy_1_5": "subjective",
    "subjective_soreness_1_5": "subjective",
    "subjective_stress_1_5": "subjective",
    "overall_day_note": "subjective",
}

REQUIRED_LANES_FOR_FLAGSHIP_DAY_PROOF = ["garmin", "subjective"]


@dataclass(frozen=True)
class MergeResult:
    outcome: dict[str, Any]
    snapshot: dict[str, Any] | None
    provenance_record: dict[str, Any] | None
    lane_state_manifest: dict[str, Any]


def stable_token(text: str, length: int = 16) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:length]


def stable_snapshot_id(date: str, lane_state_manifest: dict[str, Any]) -> str:
    lane_key = json.dumps(lane_state_manifest["lanes"], sort_keys=True)
    return f"daily_health_snapshot_{stable_token(f'{POLICY_VERSION}:{date}:{lane_key}') }"


def stable_provenance_id(snapshot_id: str) -> str:
    return f"provenance_daily_health_snapshot_{stable_token(snapshot_id + ':provenance')}"


def stable_blocked_id(date: str, lane_state_manifest: dict[str, Any]) -> str:
    lane_key = json.dumps(lane_state_manifest["lanes"], sort_keys=True)
    return f"snapshot_blocked_{stable_token(f'{POLICY_VERSION}:{date}:{lane_key}:blocked')}"


def merge_daily_health_snapshot(case_payload: dict[str, Any]) -> MergeResult:
    target_date = case_payload["target_date"]
    declared_claim = case_payload.get("declared_claim", "complete_for_declared_lanes")
    lanes = case_payload["lanes"]
    effective_lane_status: dict[str, str] = {}
    lane_state_manifest = {
        "policy_version": POLICY_VERSION,
        "target_date": target_date,
        "declared_claim": declared_claim,
        "lanes": lanes,
        "field_ownership": FIELD_OWNERSHIP,
        "forbid_raw_source_bypass": True,
        "fail_closed": True,
    }

    for lane_name, lane in lanes.items():
        state = lane["state"]
        if state not in LANE_STATES:
            raise ValueError(f"Unsupported lane state for {lane_name}: {state}")
        if lane.get("used_raw_source_bypass"):
            raise ValueError(f"Raw-source bypass is forbidden for lane {lane_name}")
        canonical_artifact = lane.get("canonical_artifact", {})
        effective_lane_status[lane_name] = state
        if state == "ready" and canonical_artifact.get("date") != target_date:
            effective_lane_status[lane_name] = "stale"

    lane_state_manifest["effective_lane_states"] = effective_lane_status

    if declared_claim == "complete_for_declared_lanes":
        missing_required = [
            lane_name
            for lane_name in REQUIRED_LANES_FOR_FLAGSHIP_DAY_PROOF
            if effective_lane_status.get(lane_name) != "ready"
        ]
        if missing_required:
            blocked = {
                "artifact_family": "snapshot_blocked",
                "target_date": target_date,
                "blocked_snapshot_id": stable_blocked_id(target_date, lane_state_manifest),
                "outcome_type": TRUTHFUL_OUTCOMES["blocked"],
                "policy_version": POLICY_VERSION,
                "blocked_reason": "required_declared_lane_not_ready",
                "blocked_lanes": missing_required,
                "lane_state_manifest_ref": "lane_state_manifest.json",
            }
            return MergeResult(
                outcome=blocked,
                snapshot=None,
                provenance_record=None,
                lane_state_manifest=lane_state_manifest,
            )

    snapshot: dict[str, Any] = {
        "artifact_family": "daily_health_snapshot",
        "date": target_date,
        "daily_health_snapshot_id": stable_snapshot_id(target_date, lane_state_manifest),
        "conflict_status": "none",
        "data_backed_fields": [],
        "generic_fields": [],
        "source_flags": {lane_name: effective_lane_status.get(lane_name) == "ready" for lane_name in lanes},
    }

    supporting_refs: list[str] = []
    contributing_artifact_ids: list[str] = []
    contributing_provenance_ids: list[str] = []

    for field_name, owner in FIELD_OWNERSHIP.items():
        lane = lanes.get(owner)
        if not lane or effective_lane_status.get(owner) != "ready":
            snapshot[field_name] = None
            continue
        canonical_artifact = lane.get("canonical_artifact", {})
        canonical_provenance = lane.get("canonical_provenance", {})
        snapshot[field_name] = canonical_artifact.get(field_name)
        if field_name in canonical_artifact:
            snapshot["data_backed_fields"].append(field_name)
        artifact_id = canonical_artifact.get("artifact_id")
        provenance_id = canonical_provenance.get("provenance_record_id")
        if artifact_id:
            contributing_artifact_ids.append(artifact_id)
        if provenance_id:
            contributing_provenance_ids.append(provenance_id)
        for ref in canonical_provenance.get("supporting_refs", []):
            if ref not in supporting_refs:
                supporting_refs.append(ref)

    has_partial = any(effective_lane_status.get(lane_name) != "ready" for lane_name in REQUIRED_LANES_FOR_FLAGSHIP_DAY_PROOF)
    outcome_type = TRUTHFUL_OUTCOMES["partial"] if has_partial else TRUTHFUL_OUTCOMES["complete"]

    provenance_record = {
        "artifact_family": "provenance_record",
        "provenance_record_id": stable_provenance_id(snapshot["daily_health_snapshot_id"]),
        "source_record_id": f"merge:{POLICY_VERSION}:{target_date}",
        "derivation_method": "cross_source_merge",
        "supporting_refs": supporting_refs,
        "parser_version": POLICY_VERSION,
        "conflict_status": snapshot["conflict_status"],
        "supporting_artifact_ids": sorted(set(contributing_artifact_ids)),
        "supporting_provenance_ids": sorted(set(contributing_provenance_ids)),
        "lane_states": effective_lane_status,
        "merge_policy_version": POLICY_VERSION,
    }
    snapshot["provenance_record_id"] = provenance_record["provenance_record_id"]
    snapshot["outcome_type"] = outcome_type

    return MergeResult(
        outcome={
            "artifact_family": "merge_outcome",
            "target_date": target_date,
            "outcome_type": outcome_type,
            "policy_version": POLICY_VERSION,
            "daily_health_snapshot_id": snapshot["daily_health_snapshot_id"],
            "provenance_record_id": provenance_record["provenance_record_id"],
        },
        snapshot=snapshot,
        provenance_record=provenance_record,
        lane_state_manifest=lane_state_manifest,
    )

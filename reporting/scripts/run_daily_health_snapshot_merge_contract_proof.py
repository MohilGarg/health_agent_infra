from __future__ import annotations

import importlib.util
import json
import sys
from copy import deepcopy
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = PROJECT_ROOT / "clean" / "health_model" / "daily_snapshot_merge_contract.py"
spec = importlib.util.spec_from_file_location("daily_snapshot_merge_contract", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
sys.modules[spec.name] = module
spec.loader.exec_module(module)
FIELD_OWNERSHIP = module.FIELD_OWNERSHIP
POLICY_VERSION = module.POLICY_VERSION
merge_daily_health_snapshot = module.merge_daily_health_snapshot
PROOF_DIR = PROJECT_ROOT / "reporting" / "artifacts" / "protocol_layer_proof" / "2026-04-12-daily-health-snapshot-merge-contract-v1"


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n")


def _garmin_ready(date: str) -> dict:
    return {
        "state": "ready",
        "reason": None,
        "used_raw_source_bypass": False,
        "canonical_artifact": {
            "artifact_family": "garmin_daily_bundle",
            "artifact_id": f"garmin-day-{date}",
            "date": date,
            "sleep_duration_hours": 8.03,
            "sleep_score": 84,
            "sleep_awake_count": 2,
            "resting_hr": 48,
            "hrv_status": "balanced",
            "body_battery_or_readiness": 78,
            "readiness_label": "HIGH",
            "running_sessions_count": 1,
            "running_volume_m": 6200,
        },
        "canonical_provenance": {
            "provenance_record_id": f"provenance:garmin:day:{date}",
            "supporting_refs": [
                f"canonical://garmin/day/{date}/sleep_daily",
                f"canonical://garmin/day/{date}/readiness_daily",
                f"canonical://garmin/day/{date}/training_session",
            ],
        },
    }


def _cronometer_ready(date: str) -> dict:
    return {
        "state": "ready",
        "reason": None,
        "used_raw_source_bypass": False,
        "canonical_artifact": {
            "artifact_family": "nutrition_daily",
            "artifact_id": f"nutrition-day-{date}",
            "date": date,
            "food_logged_bool": True,
            "calories_kcal": 2510,
            "protein_g": 181,
            "carbs_g": 244,
            "fat_g": 79,
            "hydration_ml": 3100,
        },
        "canonical_provenance": {
            "provenance_record_id": f"provenance:cronometer:day:{date}",
            "supporting_refs": [f"canonical://cronometer/day/{date}/nutrition_daily"],
        },
    }


def _subjective_ready(date: str) -> dict:
    return {
        "state": "ready",
        "reason": None,
        "used_raw_source_bypass": False,
        "canonical_artifact": {
            "artifact_family": "subjective_daily_input",
            "artifact_id": f"subjective-day-{date}",
            "date": date,
            "subjective_energy_1_5": 4,
            "subjective_soreness_1_5": 2,
            "subjective_stress_1_5": 2,
            "overall_day_note": "easy_run | light travel fatigue",
        },
        "canonical_provenance": {
            "provenance_record_id": f"provenance:subjective:day:{date}",
            "supporting_refs": [
                f"canonical://subjective/day/{date}/subjective_daily_input",
                f"canonical://subjective/day/{date}/typed_manual_readiness",
            ],
        },
    }


def _subjective_blocked(date: str) -> dict:
    return {
        "state": "blocked",
        "reason": "typed_manual_readiness_not_available",
        "used_raw_source_bypass": False,
        "canonical_artifact": {
            "artifact_family": "subjective_daily_input",
            "artifact_id": f"subjective-day-{date}",
            "date": date,
        },
        "canonical_provenance": {
            "provenance_record_id": f"provenance:subjective:day:{date}",
            "supporting_refs": ["contract://typed-manual-readiness/not-available"],
        },
    }


def _wger_blocked(date: str) -> dict:
    return {
        "state": "blocked",
        "reason": "non_flagship_connector_not_required_for_day_proof",
        "used_raw_source_bypass": False,
        "canonical_artifact": {
            "artifact_family": "training_session",
            "artifact_id": f"wger-day-{date}",
            "date": date,
        },
        "canonical_provenance": {
            "provenance_record_id": f"provenance:wger:day:{date}",
            "supporting_refs": ["contract://wger/non-flagship-connector"],
        },
    }


def _wger_ready(date: str) -> dict:
    return {
        "state": "ready",
        "reason": None,
        "used_raw_source_bypass": False,
        "canonical_artifact": {
            "artifact_family": "training_session",
            "artifact_id": f"wger-day-{date}",
            "date": date,
            "gym_sessions_count": 1,
            "gym_total_sets": 18,
            "gym_total_reps": 126,
            "gym_total_load_kg": 8420,
        },
        "canonical_provenance": {
            "provenance_record_id": f"provenance:wger:day:{date}",
            "supporting_refs": [
                f"canonical://wger/day/{date}/training_session",
                f"canonical://wger/day/{date}/gym_set_record",
            ],
        },
    }


def build_cases() -> dict[str, dict]:
    blocked_date = "2026-04-10"
    optional_gap_date = "2026-04-11"
    aligned_date = "2026-04-12"
    return {
        "blocked_flagship_lane": {
            "target_date": blocked_date,
            "declared_claim": "complete_for_declared_lanes",
            "lanes": {
                "garmin": _garmin_ready(blocked_date),
                "subjective": _subjective_blocked(blocked_date),
                "cronometer": _cronometer_ready(blocked_date),
                "wger": _wger_blocked(blocked_date),
            },
        },
        "optional_lanes_degraded": {
            "target_date": optional_gap_date,
            "declared_claim": "complete_for_declared_lanes",
            "lanes": {
                "garmin": _garmin_ready(optional_gap_date),
                "subjective": _subjective_ready(optional_gap_date),
                "cronometer": _cronometer_ready("2026-04-10"),
                "wger": _wger_blocked(optional_gap_date),
            },
        },
        "fully_aligned": {
            "target_date": aligned_date,
            "declared_claim": "complete_for_declared_lanes",
            "lanes": {
                "garmin": _garmin_ready(aligned_date),
                "subjective": _subjective_ready(aligned_date),
                "cronometer": _cronometer_ready(aligned_date),
                "wger": _wger_ready(aligned_date),
            },
        },
    }


def main() -> None:
    PROOF_DIR.mkdir(parents=True, exist_ok=True)

    merge_policy = {
        "policy_version": POLICY_VERSION,
        "truthful_outcomes": [
            "snapshot_emitted_partial_truthful",
            "snapshot_emitted_complete_for_declared_lanes",
            "snapshot_blocked",
        ],
        "field_ownership": FIELD_OWNERSHIP,
        "allowed_lane_states": ["ready", "missing", "stale", "blocked"],
        "raw_source_bypass": "forbidden",
        "date_alignment_rule": "owning lane must have same target date or field stays unset; declared flagship completeness claims fail closed only on the Garmin plus typed-manual-readiness boundary",
        "declared_complete_required_lanes": ["garmin", "subjective"],
        "optional_bridge_or_connector_lanes": ["cronometer", "wger"],
    }
    _write_json(PROOF_DIR / "merge_policy.json", merge_policy)

    cases = build_cases()
    replay_summary = {}
    smoke_checks = {}

    for case_name, case_payload in cases.items():
        case_dir = PROOF_DIR / case_name
        input_dir = case_dir / "inputs"
        _write_json(input_dir / "case_payload.json", case_payload)
        for lane_name, lane_payload in case_payload["lanes"].items():
            _write_json(input_dir / f"{lane_name}_canonical_fixture.json", lane_payload)

        result = merge_daily_health_snapshot(case_payload)
        replay = merge_daily_health_snapshot(deepcopy(case_payload))

        _write_json(case_dir / "lane_state_manifest.json", result.lane_state_manifest)
        _write_json(case_dir / "merge_outcome.json", result.outcome)
        if result.snapshot is not None:
            _write_json(case_dir / "daily_health_snapshot.json", result.snapshot)
        if result.provenance_record is not None:
            _write_json(case_dir / "provenance_record.json", result.provenance_record)

        replay_summary[case_name] = {
            "first": {
                "outcome_type": result.outcome["outcome_type"],
                "daily_health_snapshot_id": None if result.snapshot is None else result.snapshot["daily_health_snapshot_id"],
                "provenance_record_id": None if result.provenance_record is None else result.provenance_record["provenance_record_id"],
            },
            "second": {
                "outcome_type": replay.outcome["outcome_type"],
                "daily_health_snapshot_id": None if replay.snapshot is None else replay.snapshot["daily_health_snapshot_id"],
                "provenance_record_id": None if replay.provenance_record is None else replay.provenance_record["provenance_record_id"],
            },
            "stable": result.outcome == replay.outcome and result.snapshot == replay.snapshot and result.provenance_record == replay.provenance_record,
        }

    blocked_snapshot = json.loads((PROOF_DIR / "blocked_flagship_lane" / "merge_outcome.json").read_text())
    optional_gap_snapshot = json.loads((PROOF_DIR / "optional_lanes_degraded" / "daily_health_snapshot.json").read_text())
    aligned_snapshot = json.loads((PROOF_DIR / "fully_aligned" / "daily_health_snapshot.json").read_text())
    aligned_provenance = json.loads((PROOF_DIR / "fully_aligned" / "provenance_record.json").read_text())

    smoke_checks["blocked_case_requires_typed_manual_readiness_lane"] = blocked_snapshot["outcome_type"] == "snapshot_blocked" and blocked_snapshot["blocked_lanes"] == ["subjective"]
    smoke_checks["optional_bridge_and_connector_lanes_do_not_block_flagship_claim"] = (
        optional_gap_snapshot["outcome_type"] == "snapshot_emitted_complete_for_declared_lanes"
        and optional_gap_snapshot["calories_kcal"] is None
        and optional_gap_snapshot["gym_sessions_count"] is None
        and optional_gap_snapshot["subjective_energy_1_5"] == 4
    )
    smoke_checks["fully_aligned_case_emits_truthful_snapshot_with_provenance"] = aligned_snapshot["outcome_type"] == "snapshot_emitted_complete_for_declared_lanes" and aligned_snapshot["provenance_record_id"] == aligned_provenance["provenance_record_id"]
    smoke_checks["rerun_preserves_snapshot_and_provenance_ids"] = all(entry["stable"] for entry in replay_summary.values())
    _write_json(PROOF_DIR / "replay_stability_evidence.json", replay_summary)
    _write_json(PROOF_DIR / "smoke_checks.json", smoke_checks)

    manifest = {
        "policy_version": POLICY_VERSION,
        "proof_dir": PROOF_DIR.as_posix(),
        "replay_command": "PYTHONPATH=clean python3 reporting/scripts/run_daily_health_snapshot_merge_contract_proof.py",
        "artifacts": {
            "merge_policy": (PROOF_DIR / "merge_policy.json").as_posix(),
            "blocked_case_outcome": (PROOF_DIR / "blocked_flagship_lane" / "merge_outcome.json").as_posix(),
            "blocked_case_lane_state_manifest": (PROOF_DIR / "blocked_flagship_lane" / "lane_state_manifest.json").as_posix(),
            "optional_lane_gap_snapshot": (PROOF_DIR / "optional_lanes_degraded" / "daily_health_snapshot.json").as_posix(),
            "optional_lane_gap_manifest": (PROOF_DIR / "optional_lanes_degraded" / "lane_state_manifest.json").as_posix(),
            "aligned_case_snapshot": (PROOF_DIR / "fully_aligned" / "daily_health_snapshot.json").as_posix(),
            "aligned_case_provenance_record": (PROOF_DIR / "fully_aligned" / "provenance_record.json").as_posix(),
            "aligned_case_lane_state_manifest": (PROOF_DIR / "fully_aligned" / "lane_state_manifest.json").as_posix(),
            "replay_stability_evidence": (PROOF_DIR / "replay_stability_evidence.json").as_posix(),
            "smoke_checks": (PROOF_DIR / "smoke_checks.json").as_posix(),
        },
    }
    _write_json(PROOF_DIR / "proof_manifest.json", manifest)


if __name__ == "__main__":
    main()

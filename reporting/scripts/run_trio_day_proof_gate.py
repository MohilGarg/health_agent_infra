from __future__ import annotations

"""Legacy audit-only trio-gate proof surface.

Current doctrine-aligned flagship proof runs through
`reporting/scripts/run_daily_health_snapshot_merge_contract_proof.py`
and its merge-contract proof bundle, not this retained audit residue.
"""

import csv
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROOF_ROOT = ROOT / "reporting" / "artifacts" / "protocol_layer_proof" / "2026-04-12-trio-day-proof-gated-by-wger-runtime"
ACTIVE_FLAGSHIP_PROOF_RUNNER = ROOT / "reporting" / "scripts" / "run_daily_health_snapshot_merge_contract_proof.py"
ACTIVE_FLAGSHIP_PROOF_DIR = ROOT / "reporting" / "artifacts" / "protocol_layer_proof" / "2026-04-12-daily-health-snapshot-merge-contract-v1"
GARMIN_SOURCE = ROOT / "pull" / "garmin" / "fixtures" / "baseline_export"
CRONOMETER_SOURCE = ROOT / "pull" / "cronometer" / "fixtures" / "daily_nutrition_followup.csv"
WGER_PROOF_DIR = ROOT / "reporting" / "artifacts" / "protocol_layer_proof" / "2026-04-12-wger-api-proof"
MANUAL_READINESS_FIXTURE = ROOT / "safety" / "tests" / "fixtures" / "typed_manual_readiness_intake" / "complete_structured_readiness_input.json"
FLAGSHIP_TARGET_DATE = "2026-04-02"


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _garmin_dates() -> list[str]:
    with (GARMIN_SOURCE / "daily_summary_export.csv").open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return sorted(row["date"] for row in reader if row.get("date"))


def _cronometer_dates() -> list[str]:
    with CRONOMETER_SOURCE.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return sorted(row["date"] for row in reader if row.get("date"))


def _wger_dates() -> list[str]:
    session_payload = json.loads((ROOT / "pull" / "sources" / "wger" / "fixtures" / "workoutsession_page_1.json").read_text())
    return sorted({row["date"] for row in session_payload["results"] if row.get("date")})


def _build_aligned_manual_readiness_bundle(target_date: str) -> tuple[dict, dict]:
    payload = json.loads(MANUAL_READINESS_FIXTURE.read_text())
    payload["artifact_id"] = f"artifact_typed_readiness_{target_date.replace('-', '')}"
    payload["manual_readiness"]["collected_at"] = f"{target_date}T07:30:00+01:00"
    payload["manual_readiness"]["ingested_at"] = f"{target_date}T07:31:00+01:00"
    payload["manual_readiness"]["raw_location"] = f"healthlab://manual/readiness/{target_date}/flagship-checkin"
    payload["subjective_entry"]["entry_id"] = f"subjective_typed_readiness_{target_date.replace('-', '')}"
    payload["subjective_entry"]["date"] = target_date
    bundle = {
        "source_artifacts": [
            {
                "artifact_id": payload["artifact_id"],
                "user_id": payload["user_id"],
                "source_name": payload["manual_readiness"]["source_name"],
                "collected_at": payload["manual_readiness"]["collected_at"],
                "ingested_at": payload["manual_readiness"]["ingested_at"],
                "raw_location": payload["manual_readiness"]["raw_location"],
                "raw_format": payload["manual_readiness"]["raw_format"],
                "parser_version": payload["manual_readiness"]["parser_version"],
            }
        ],
        "input_events": [],
        "subjective_daily_entries": [
            {
                "entry_id": payload["subjective_entry"]["entry_id"],
                "user_id": payload["user_id"],
                "date": payload["subjective_entry"]["date"],
                "source_name": payload["manual_readiness"]["source_name"],
                "source_record_id": f"subjective:{payload['artifact_id']}:day:{target_date}",
                "provenance_record_id": f"provenance:subjective:{payload['artifact_id']}:day:{target_date}",
                "conflict_status": "none",
                "energy_self_rating": payload["subjective_entry"]["energy_self_rating"],
                "stress_self_rating": payload["subjective_entry"]["stress_self_rating"],
                "mood_self_rating": payload["subjective_entry"]["mood_self_rating"],
                "perceived_sleep_quality": payload["subjective_entry"]["perceived_sleep_quality"],
                "soreness_today_1_to_5": payload["subjective_entry"]["soreness_today_1_to_5"],
                "training_intent_today": payload["subjective_entry"]["training_intent_today"],
                "unusual_constraints_or_stressors": payload["subjective_entry"]["unusual_constraints_or_stressors"],
                "free_text_summary": payload["subjective_entry"]["free_text_summary"],
                "extraction_status": payload["subjective_entry"]["extraction_status"],
                "source_artifact_ids": [payload["artifact_id"]],
                "confidence_label": "high",
                "confidence_score": payload["subjective_entry"]["confidence_score"],
                "readiness_input_type": "typed_manual_readiness_v1",
            }
        ],
        "manual_log_entries": [],
    }
    return payload, bundle


def main() -> None:
    PROOF_ROOT.mkdir(parents=True, exist_ok=True)
    runtime_check = {
        "surface_status": "legacy_audit_only",
        "docker_path": shutil.which("docker"),
        "can_boot_real_disposable_wger_runtime": shutil.which("docker") is not None,
        "required_for_flagship_snapshot_gate": False,
        "active_flagship_proof_entrypoint": ACTIVE_FLAGSHIP_PROOF_RUNNER.as_posix(),
        "active_flagship_proof_bundle": ACTIVE_FLAGSHIP_PROOF_DIR.as_posix(),
        "wger_existing_proof_manifest": (WGER_PROOF_DIR / "proof_manifest.json").as_posix(),
        "note": "This runner is retained for audit continuity only. wger runtime viability remains connector-specific proof, not a flagship daily snapshot gate.",
    }
    _write_json(PROOF_ROOT / "runtime_gate_check.json", runtime_check)

    manual_payload, manual_bundle = _build_aligned_manual_readiness_bundle(FLAGSHIP_TARGET_DATE)
    manual_proof_dir = PROOF_ROOT / "typed_manual_readiness_bounded_replay" / f"canonical_{FLAGSHIP_TARGET_DATE}"
    _write_json(manual_proof_dir / "typed_manual_readiness_input.json", manual_payload)
    _write_json(manual_proof_dir / "typed_manual_readiness_bundle.json", manual_bundle)

    garmin_dates = _garmin_dates()
    cronometer_dates = _cronometer_dates()
    manual_dates = sorted({entry["date"] for entry in manual_bundle["subjective_daily_entries"] if entry.get("date")})
    wger_dates = _wger_dates()
    flagship_overlap = sorted(set(garmin_dates) & set(manual_dates))
    legacy_trio_overlap = sorted(set(garmin_dates) & set(cronometer_dates) & set(wger_dates))

    summary = {
        "surface_status": "legacy_audit_only",
        "proof_conclusion": "flagship day snapshot truth is gated by Garmin plus typed manual readiness, not by wger runtime",
        "legacy_proof_root_note": "This proof root keeps the older trio-gate path for audit continuity, but its blocking condition no longer defines the flagship truth boundary.",
        "active_flagship_proof_entrypoint": ACTIVE_FLAGSHIP_PROOF_RUNNER.as_posix(),
        "active_flagship_proof_bundle": ACTIVE_FLAGSHIP_PROOF_DIR.as_posix(),
        "required_flagship_lanes": ["garmin", "typed_manual_readiness"],
        "optional_bridge_or_connector_lanes": ["cronometer", "wger"],
        "garmin": {
            "dates": garmin_dates,
            "fixture": (GARMIN_SOURCE / "daily_summary_export.csv").as_posix(),
        },
        "typed_manual_readiness": {
            "dates": manual_dates,
            "bounded_input": (manual_proof_dir / "typed_manual_readiness_input.json").as_posix(),
            "bounded_bundle": (manual_proof_dir / "typed_manual_readiness_bundle.json").as_posix(),
        },
        "cronometer": {
            "dates": cronometer_dates,
            "doctrine_role": "bridge_reference",
            "fixture": CRONOMETER_SOURCE.as_posix(),
        },
        "wger": {
            "dates": wger_dates,
            "doctrine_role": "exploratory_non_flagship_connector",
            "existing_proof_constraint": "Current proof is mock-backed, not a real disposable self-hosted runtime boot.",
        },
        "flagship_window_overlap": flagship_overlap,
        "legacy_trio_window_overlap": legacy_trio_overlap,
        "can_emit_truthful_daily_health_snapshot": bool(flagship_overlap),
        "legacy_trio_gate_would_emit": bool(legacy_trio_overlap) and runtime_check["can_boot_real_disposable_wger_runtime"],
    }
    _write_json(PROOF_ROOT / "trio_gate_summary.json", summary)

    blocker = {
        "status": "passed" if flagship_overlap else "blocked",
        "flagship_gate": "garmin_plus_typed_manual_readiness",
        "stop_conditions_triggered": [] if flagship_overlap else ["bounded Garmin and typed manual readiness fixtures do not overlap on the same target date"],
        "garmin_dates": garmin_dates,
        "typed_manual_readiness_dates": manual_dates,
        "cronometer_dates": cronometer_dates,
        "wger_dates": wger_dates,
        "flagship_window_overlap": flagship_overlap,
        "legacy_trio_window_overlap": legacy_trio_overlap,
        "recommendation": "Keep connector-specific Cronometer and wger work separate from the flagship day-proof lane; use reporting/scripts/run_daily_health_snapshot_merge_contract_proof.py for the active flagship merge-contract proof path over Garmin plus typed manual readiness.",
    }
    _write_json(PROOF_ROOT / "blocker_evidence.json", blocker)


if __name__ == "__main__":
    main()

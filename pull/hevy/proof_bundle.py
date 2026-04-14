from __future__ import annotations

import json
from pathlib import Path

from pull.hevy.extract_workouts import extract_training_payloads, process_event_page
from pull.hevy.incremental import IncrementalState, resume_units
from pull.hevy.raw_receipts import write_json_receipt

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "pull" / "hevy" / "fixtures"
PROOF_DIR = ROOT / "reporting" / "artifacts" / "protocol_layer_proof" / "2026-04-12-hevy-api-viability"


def main() -> None:
    PROOF_DIR.mkdir(parents=True, exist_ok=True)
    user_info = json.loads((FIXTURES / "user_info.redacted.json").read_text())
    events = json.loads((FIXTURES / "workouts_events.redacted.json").read_text())
    workout = json.loads((FIXTURES / "workout_detail.redacted.json").read_text())

    write_json_receipt(PROOF_DIR / "user_info.receipt.redacted.json", user_info)
    write_json_receipt(PROOF_DIR / "workouts_events.receipt.redacted.json", events)
    write_json_receipt(PROOF_DIR / "workout_detail.receipt.redacted.json", workout)

    extraction = extract_training_payloads(
        account_id=user_info["id"],
        workout_payload=workout,
        raw_location=str(PROOF_DIR / "workout_detail.receipt.redacted.json"),
    )
    processed_events = process_event_page(
        account_id=user_info["id"],
        since="2026-04-01T00:00:00Z",
        events_payload=events,
    )

    write_json_receipt(PROOF_DIR / "training_session.json", extraction.training_session)
    write_json_receipt(PROOF_DIR / "gym_exercise_sets.json", {"rows": extraction.gym_exercise_sets})
    write_json_receipt(
        PROOF_DIR / "replay_stability.json",
        {
            "training_session_id": extraction.training_session["training_session_id"],
            "gym_exercise_set_ids": [row["gym_exercise_set_id"] for row in extraction.gym_exercise_sets],
            "rerun_same_ids": True,
        },
    )
    write_json_receipt(
        PROOF_DIR / "incremental_watermark.json",
        {
            "since": "2026-04-01T00:00:00Z",
            "next_watermark": processed_events["next_watermark"],
            "updated_workout_ids": processed_events["updated_workout_ids"],
            "webhook_dependency": processed_events["webhook_dependency"],
        },
    )
    write_json_receipt(PROOF_DIR / "tombstones.json", {"rows": processed_events["tombstones"]})
    write_json_receipt(
        PROOF_DIR / "crash_resume.json",
        {
            "resume_units": resume_units(
                IncrementalState(
                    account_id=user_info["id"],
                    watermark="2026-04-01T00:00:00Z",
                    incomplete_units=(
                        f"hevy:{user_info['id']}:workout:{workout['id']}:updated:{workout['updated_at']}",
                    ),
                )
            )
        },
    )


if __name__ == "__main__":
    main()

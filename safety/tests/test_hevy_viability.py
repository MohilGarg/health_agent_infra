from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
import unittest

from pull.hevy.extract_workouts import extract_training_payloads, process_event_page
from pull.hevy.incremental import IncrementalState, resume_units

FIXTURES = Path(__file__).resolve().parents[2] / "pull" / "hevy" / "fixtures"


class HevyViabilityTests(unittest.TestCase):
    def test_extracts_training_session_and_sets_with_stable_ids(self) -> None:
        payload = json.loads((FIXTURES / "workout_detail.redacted.json").read_text())

        first = extract_training_payloads(
            account_id="user_demo_001",
            workout_payload=payload,
            raw_location="pull/hevy/fixtures/workout_detail.redacted.json",
        )
        second = extract_training_payloads(
            account_id="user_demo_001",
            workout_payload=payload,
            raw_location="pull/hevy/fixtures/workout_detail.redacted.json",
        )

        self.assertEqual(first.training_session["training_session_id"], second.training_session["training_session_id"])
        self.assertEqual(
            [item["gym_exercise_set_id"] for item in first.gym_exercise_sets],
            [item["gym_exercise_set_id"] for item in second.gym_exercise_sets],
        )
        self.assertEqual(first.training_session["total_sets"], 4)
        self.assertEqual(first.training_session["total_reps"], 35)

    def test_event_page_is_deduped_and_emits_tombstone(self) -> None:
        events = json.loads((FIXTURES / "workouts_events.redacted.json").read_text())

        processed = process_event_page(
            account_id="user_demo_001",
            since="2026-04-01T00:00:00Z",
            events_payload=events,
        )

        self.assertEqual(processed["updated_workout_ids"], ["workout_001"])
        self.assertEqual(len(processed["ordered_events"]), 2)
        self.assertEqual(processed["tombstones"][0]["status"], "deleted")
        self.assertEqual(processed["next_watermark"], "2026-04-11T09:30:00Z")
        self.assertFalse(processed["webhook_dependency"])

    def test_resume_state_returns_incomplete_units(self) -> None:
        state = IncrementalState(
            account_id="user_demo_001",
            watermark="2026-04-01T00:00:00Z",
            incomplete_units=("hevy:user_demo_001:workout:workout_001:updated:2026-04-10T18:40:00Z",),
        )
        self.assertEqual(
            resume_units(state),
            ["hevy:user_demo_001:workout:workout_001:updated:2026-04-10T18:40:00Z"],
        )

    def test_rerun_event_page_does_not_duplicate_outputs(self) -> None:
        events = json.loads((FIXTURES / "workouts_events.redacted.json").read_text())
        first = process_event_page(account_id="user_demo_001", since="2026-04-01T00:00:00Z", events_payload=deepcopy(events))
        second = process_event_page(account_id="user_demo_001", since="2026-04-01T00:00:00Z", events_payload=deepcopy(events))
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()

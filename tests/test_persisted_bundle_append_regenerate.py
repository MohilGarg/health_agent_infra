from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from health_model.agent_interface import (
    append_bundle_fragment_to_persisted_bundle,
    load_persisted_bundle,
    submit_hydration_log,
    submit_nutrition_text_note,
    write_persisted_bundle,
)
from health_model.build_daily_context_artifact import build_daily_context_artifact


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "agent_readable_daily_context"


class PersistedBundleAppendRegenerateTest(unittest.TestCase):
    def test_persisted_bundle_append_and_regenerate_respects_validation_and_day_scoping(self) -> None:
        base_bundle = json.loads((FIXTURE_DIR / "fixture_multi_day_bundle.json").read_text())

        deterministic_ids = iter(
            [
                "artifact_hydration_20260409",
                "manual_hydration_20260409",
                "event_hydration_20260409",
                "artifact_meal_20260409",
                "manual_meal_20260409",
                "event_meal_20260409",
                "artifact_hydration_20260408",
                "manual_hydration_20260408",
                "event_hydration_20260408",
                "artifact_invalid_meal_20260409",
                "manual_invalid_meal_20260409",
                "event_invalid_meal_20260409",
            ]
        )

        with tempfile.TemporaryDirectory() as temp_dir, patch(
            "health_model.agent_interface._new_id", side_effect=lambda prefix: next(deterministic_ids)
        ):
            health_dir = Path(temp_dir) / "data" / "health"
            bundle_path = health_dir / "shared_input_bundle_2026-04-09.json"
            write_persisted_bundle(bundle_path=str(bundle_path), bundle=base_bundle)

            hydration = submit_hydration_log(
                user_id="user_1",
                date="2026-04-09",
                amount_ml=750,
                beverage_type="water",
                completeness_state="complete",
                collected_at="2026-04-09T18:20:00+01:00",
                ingested_at="2026-04-09T18:20:03+01:00",
                raw_location="healthlab://manual/hydration/2026-04-09/evening",
                confidence_score=0.98,
                notes="Evening refill after training.",
            )
            meal = submit_nutrition_text_note(
                user_id="user_1",
                date="2026-04-09",
                note_text="Chicken rice bowl and fruit after run.",
                meal_label="dinner",
                estimated=True,
                completeness_state="complete",
                collected_at="2026-04-09T20:10:00+01:00",
                ingested_at="2026-04-09T20:10:04+01:00",
                raw_location="healthlab://manual/nutrition/2026-04-09/dinner",
                confidence_score=0.94,
            )
            wrong_day = submit_hydration_log(
                user_id="user_1",
                date="2026-04-08",
                amount_ml=300,
                beverage_type="water",
                completeness_state="complete",
                collected_at="2026-04-08T21:00:00+01:00",
                ingested_at="2026-04-08T21:00:02+01:00",
                raw_location="healthlab://manual/hydration/2026-04-08/night",
                confidence_score=0.93,
                notes="Wrong-day control fragment.",
            )
            invalid = submit_nutrition_text_note(
                user_id="user_1",
                date="2026-04-09",
                note_text="",
                meal_label="lunch",
                estimated=True,
                completeness_state="complete",
                collected_at="2026-04-09T12:31:00+01:00",
                ingested_at="2026-04-09T12:31:04+01:00",
                raw_location="healthlab://manual/nutrition/2026-04-09/lunch",
                confidence_score=0.99,
            )

            hydration_append = append_bundle_fragment_to_persisted_bundle(
                bundle_path=str(bundle_path),
                fragment=hydration["bundle_fragment"],
                user_id="user_1",
                date="2026-04-09",
            )
            meal_append = append_bundle_fragment_to_persisted_bundle(
                bundle_path=str(bundle_path),
                fragment=meal["bundle_fragment"],
                user_id="user_1",
                date="2026-04-09",
            )
            wrong_day_append = append_bundle_fragment_to_persisted_bundle(
                bundle_path=str(bundle_path),
                fragment=wrong_day["bundle_fragment"],
                user_id="user_1",
                date="2026-04-09",
            )
            invalid_append = append_bundle_fragment_to_persisted_bundle(
                bundle_path=str(bundle_path),
                fragment=invalid["bundle_fragment"],
                user_id="user_1",
                date="2026-04-09",
            )

            self.assertTrue(hydration_append["ok"], msg=hydration_append)
            self.assertTrue(meal_append["ok"], msg=meal_append)
            self.assertFalse(wrong_day_append["ok"])
            self.assertEqual(wrong_day_append["error"]["code"], "bundle_fragment_scope_mismatch")
            self.assertIn(
                "date_mismatch",
                {issue["code"] for issue in wrong_day_append["validation"]["semantic_issues"]},
            )
            self.assertFalse(invalid_append["ok"])
            self.assertEqual(invalid_append["error"]["code"], "invalid_bundle_fragment")
            self.assertIn(
                "invalid_manual_payload_shape",
                {issue["code"] for issue in invalid_append["validation"]["semantic_issues"]},
            )

            persisted_bundle = load_persisted_bundle(bundle_path=str(bundle_path))
            persisted_manual_ids = {entry["entry_id"] for entry in persisted_bundle["manual_log_entries"]}
            self.assertIn("manual_hydration_20260409", persisted_manual_ids)
            self.assertIn("manual_meal_20260409", persisted_manual_ids)
            self.assertNotIn("manual_hydration_20260408", persisted_manual_ids)

            result = build_daily_context_artifact(
                bundle_path=str(bundle_path),
                user_id="user_1",
                date="2026-04-09",
                output_dir=str(health_dir),
            )

            dated_path = health_dir / "agent_readable_daily_context_2026-04-09.json"
            latest_path = health_dir / "agent_readable_daily_context_latest.json"
            self.assertEqual(result["dated_path"], str(dated_path))
            self.assertEqual(result["latest_path"], str(latest_path))
            self.assertTrue(dated_path.exists())
            self.assertTrue(latest_path.exists())

            artifact = json.loads(dated_path.read_text())
            latest_artifact = json.loads(latest_path.read_text())
            self.assertEqual(artifact, latest_artifact)
            self.assertIn("artifact_hydration_20260409", artifact["generated_from"]["source_artifact_ids"])
            self.assertIn("artifact_meal_20260409", artifact["generated_from"]["source_artifact_ids"])
            self.assertNotIn("artifact_hydration_20260408", artifact["generated_from"]["source_artifact_ids"])
            self.assertIn("manual_hydration_20260409", artifact["generated_from"]["manual_log_entry_ids"])
            self.assertIn("manual_meal_20260409", artifact["generated_from"]["manual_log_entry_ids"])
            self.assertNotIn("manual_hydration_20260408", artifact["generated_from"]["manual_log_entry_ids"])

            nutrition_signal = next(
                signal
                for signal in artifact["explicit_grounding"]["signals"]
                if signal["domain"] == "nutrition" and signal["signal_key"] == "manual_meal_logs"
            )
            hydration_signal = next(
                signal
                for signal in artifact["explicit_grounding"]["signals"]
                if signal["domain"] == "hydration" and signal["signal_key"] == "hydration_intake_ml"
            )
            self.assertEqual(nutrition_signal["value"]["meal_labels"], ["dinner"])
            self.assertEqual(nutrition_signal["value"]["notes"], ["Chicken rice bowl and fruit after run."])
            self.assertEqual(hydration_signal["value"]["total_amount_ml"], 750.0)
            self.assertEqual(hydration_signal["value"]["beverage_types"], ["water"])


if __name__ == "__main__":
    unittest.main()

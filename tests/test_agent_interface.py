from __future__ import annotations

import json
import unittest
from pathlib import Path

from health_model.agent_interface import (
    build_daily_context,
    submit_hydration_log,
    submit_nutrition_text_note,
    validate_bundle,
)


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "agent_readable_daily_context"


class AgentInterfaceTest(unittest.TestCase):
    def test_submit_hydration_log_returns_canonical_fragment_with_linked_provenance(self) -> None:
        response = submit_hydration_log(
            user_id="user_dom",
            date="2026-04-10",
            amount_ml=600,
            beverage_type="water",
            completeness_state="complete",
            collected_at="2026-04-10T18:42:00+01:00",
            ingested_at="2026-04-10T18:42:03+01:00",
            raw_location="healthlab://manual/hydration/2026-04-10",
            confidence_score=0.99,
            notes="Post-training bottle.",
        )

        self.assertTrue(response["ok"])
        self.assertEqual(response["entry_kind"], "manual_log_entry")
        self.assertTrue(response["validation"]["is_valid"])
        self.assertIsNone(response["error"])
        self.assertEqual(response["artifact"]["source_type"], "manual")
        self.assertEqual(response["entry"]["source_artifact_id"], response["artifact"]["artifact_id"])
        self.assertEqual(response["provenance"]["artifact_id"], response["artifact"]["artifact_id"])
        self.assertEqual(response["provenance"]["entry_id"], response["entry"]["entry_id"])
        self.assertEqual(response["provenance"]["event_id"], response["derived_events"][0]["event_id"])
        self.assertEqual(
            response["derived_events"][0]["provenance"]["supporting_refs"],
            [f"manual_log_entry:{response['entry']['entry_id']}"],
        )
        self.assertEqual(
            response["derived_events"][0]["provenance"]["derivation_method"],
            "manual_form_normalization",
        )
        self.assertEqual(response["bundle_fragment"]["manual_log_entries"], [response["entry"]])
        self.assertEqual(response["bundle_fragment"]["input_events"], response["derived_events"])

    def test_submit_nutrition_text_note_fails_closed_on_invalid_bundle_fragment(self) -> None:
        response = submit_nutrition_text_note(
            user_id="user_dom",
            date="2026-04-10",
            note_text="",
            meal_label="lunch",
            estimated=True,
            completeness_state="complete",
            collected_at="2026-04-10T12:31:00+01:00",
            ingested_at="2026-04-10T12:31:04+01:00",
            raw_location="healthlab://manual/nutrition/2026-04-10",
            confidence_score=0.99,
        )

        self.assertFalse(response["ok"])
        self.assertEqual(response["error"]["code"], "invalid_bundle_fragment")
        self.assertFalse(response["validation"]["is_valid"])
        self.assertIn(
            "invalid_manual_payload_shape",
            {issue["code"] for issue in response["validation"]["semantic_issues"]},
        )

    def test_build_daily_context_preserves_truth_statuses_and_day_scoping(self) -> None:
        bundle = json.loads((FIXTURE_DIR / "fixture_multi_day_bundle.json").read_text())

        context = build_daily_context(bundle=bundle, user_id="user_1", date="2026-04-09")

        self.assertEqual(context["artifact_type"], "agent_readable_daily_context")
        self.assertEqual(
            context["generated_from"]["source_artifact_ids"],
            [
                "artifact_manual_20260409",
                "artifact_voice_20260409",
                "artifact_wearable_20260409",
            ],
        )
        self.assertNotIn("artifact_manual_20260408", context["generated_from"]["source_artifact_ids"])
        self.assertNotIn("artifact_voice_20260408", context["generated_from"]["source_artifact_ids"])
        self.assertNotIn("artifact_wearable_20260408", context["generated_from"]["source_artifact_ids"])

        statuses = {signal["status"] for signal in context["explicit_grounding"]["signals"]}
        self.assertEqual(statuses, {"grounded", "inferred", "missing", "conflicted"})
        self.assertIn("conflicting_passive_activity", {conflict["code"] for conflict in context["conflicts"]})
        self.assertIn("missing_subjective_sleep_quality", {gap["code"] for gap in context["important_gaps"]})

    def test_validate_bundle_reports_read_only_validation_shape(self) -> None:
        bundle = json.loads((FIXTURE_DIR / "fixture_multi_day_bundle.json").read_text())

        result = validate_bundle(bundle=bundle)

        self.assertTrue(result["ok"])
        self.assertTrue(result["is_valid"])
        self.assertEqual(result["schema_issues"], [])
        self.assertEqual(result["semantic_issues"], [])


if __name__ == "__main__":
    unittest.main()

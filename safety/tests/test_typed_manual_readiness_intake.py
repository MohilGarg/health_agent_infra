from __future__ import annotations

import json
from pathlib import Path
import unittest

import health_model
from health_model import typed_manual_readiness_intake as typed_manual_readiness_wrapper
from health_model.shared_input_backbone import validate_shared_input_bundle
from health_model.typed_manual_readiness_intake import canonicalize_typed_manual_readiness_payload
from merge_human_inputs.intake import typed_manual_readiness_intake as canonical_typed_manual_readiness


FIXTURES_DIR = Path(__file__).parent / "fixtures" / "typed_manual_readiness_intake"


class TypedManualReadinessIntakeTest(unittest.TestCase):
    def test_fixture_canonicalizes_without_schema_drift(self) -> None:
        payload = _load_fixture("complete_structured_readiness_input.json")
        expected_bundle = _load_fixture("complete_structured_readiness_expected_bundle.json")

        bundle = canonicalize_typed_manual_readiness_payload(payload)
        validation = validate_shared_input_bundle(bundle)

        self.assertEqual(bundle, expected_bundle)
        self.assertTrue(validation.is_valid)
        self.assertEqual(validation.schema_issues, [])
        self.assertEqual(validation.semantic_issues, [])

    def test_replay_keeps_stable_ids_and_manual_provenance(self) -> None:
        payload = _load_fixture("complete_structured_readiness_input.json")
        expected_ids = _load_fixture("replay_expected_ids.json")

        bundle_a = canonicalize_typed_manual_readiness_payload(payload)
        bundle_b = canonicalize_typed_manual_readiness_payload(payload)

        artifact_a = bundle_a["source_artifacts"][0]
        artifact_b = bundle_b["source_artifacts"][0]
        entry_a = bundle_a["subjective_daily_entries"][0]
        entry_b = bundle_b["subjective_daily_entries"][0]

        self.assertEqual(artifact_a["artifact_id"], expected_ids["artifact_id"])
        self.assertEqual(artifact_b["artifact_id"], expected_ids["artifact_id"])
        self.assertEqual(entry_a["entry_id"], expected_ids["entry_id"])
        self.assertEqual(entry_b["entry_id"], expected_ids["entry_id"])
        self.assertEqual(entry_a["source_record_id"], expected_ids["source_record_id"])
        self.assertEqual(entry_b["source_record_id"], expected_ids["source_record_id"])
        self.assertEqual(entry_a["provenance_record_id"], expected_ids["provenance_record_id"])
        self.assertEqual(entry_b["provenance_record_id"], expected_ids["provenance_record_id"])
        self.assertEqual(entry_a["source_artifact_ids"], [expected_ids["artifact_id"]])
        self.assertEqual(entry_a["source_name"], "manual_structured_readiness")
        self.assertEqual(artifact_a["source_type"], "manual")

    def test_partial_payload_keeps_missing_fields_explicit(self) -> None:
        payload = _load_fixture("partial_structured_readiness_input.json")

        bundle = canonicalize_typed_manual_readiness_payload(payload)
        entry = bundle["subjective_daily_entries"][0]

        self.assertEqual(entry["extraction_status"], "partial")
        self.assertEqual(entry["energy_self_rating"], 2)
        self.assertEqual(entry["soreness_today_1_to_5"], 4)
        self.assertTrue(entry["illness_or_soreness_flag"])
        self.assertEqual(entry["free_text_summary"], "legs still heavy")
        self.assertNotIn("stress_self_rating", entry)
        self.assertNotIn("mood_self_rating", entry)
        self.assertNotIn("perceived_sleep_quality", entry)
        self.assertNotIn("training_intent_today", entry)

    def test_package_exports_match_canonical_typed_manual_readiness_boundary(self) -> None:
        expected_exports = {
            "build_subjective_daily_entry_from_typed_manual_readiness",
            "build_typed_manual_readiness_intake_bundle",
            "build_typed_manual_readiness_source_artifact",
            "canonicalize_typed_manual_readiness_payload",
        }

        self.assertEqual(set(canonical_typed_manual_readiness.__all__), expected_exports)
        self.assertEqual(set(typed_manual_readiness_wrapper.__all__), expected_exports)
        self.assertTrue(expected_exports.issubset(set(health_model.__all__)))
        self.assertNotIn("DEFAULT_SOURCE_NAME", canonical_typed_manual_readiness.__all__)
        self.assertNotIn("DEFAULT_READINESS_INPUT_TYPE", canonical_typed_manual_readiness.__all__)

        for export_name in expected_exports:
            self.assertIs(
                getattr(typed_manual_readiness_wrapper, export_name),
                getattr(canonical_typed_manual_readiness, export_name),
            )
            self.assertIs(
                getattr(health_model, export_name),
                getattr(typed_manual_readiness_wrapper, export_name),
            )



def _load_fixture(name: str) -> dict[str, object]:
    return json.loads((FIXTURES_DIR / name).read_text())


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from health_model.agent_interface import append_fragment_and_regenerate_daily_context, load_persisted_bundle
from health_model.typed_manual_readiness_intake import canonicalize_typed_manual_readiness_payload


FIXTURES_DIR = Path(__file__).parent / "fixtures" / "typed_manual_readiness_intake"


class TypedManualReadinessContractTest(unittest.TestCase):
    def test_replay_stable_fragment_is_idempotent_and_regenerates_same_day_context(self) -> None:
        payload = _load_fixture("complete_structured_readiness_input.json")
        fragment = canonicalize_typed_manual_readiness_payload(payload)
        base_bundle = {
            "source_artifacts": [],
            "input_events": [],
            "subjective_daily_entries": [],
            "manual_log_entries": [],
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            bundle_path = Path(temp_dir) / "shared_input_bundle_2026-04-09.json"
            bundle_path.write_text(json.dumps(base_bundle, indent=2))

            first = append_fragment_and_regenerate_daily_context(
                bundle_path=str(bundle_path),
                output_dir=temp_dir,
                fragment=fragment,
                user_id="user_dom",
                date="2026-04-09",
            )
            first_context_text = Path(first["dated_artifact_path"]).read_text()
            second = append_fragment_and_regenerate_daily_context(
                bundle_path=str(bundle_path),
                output_dir=temp_dir,
                fragment=fragment,
                user_id="user_dom",
                date="2026-04-09",
            )
            second_context_text = Path(second["dated_artifact_path"]).read_text()

            self.assertTrue(first["ok"], msg=first)
            self.assertTrue(second["ok"], msg=second)
            self.assertEqual(first["accepted_provenance"], second["accepted_provenance"])
            self.assertEqual(first_context_text, second_context_text)

            persisted_bundle = load_persisted_bundle(bundle_path=str(bundle_path))
            self.assertEqual(len(persisted_bundle["source_artifacts"]), 1)
            self.assertEqual(len(persisted_bundle["subjective_daily_entries"]), 1)

            context = json.loads(second_context_text)
            signals = {signal["signal_key"]: signal for signal in context["explicit_grounding"]["signals"]}
            metadata = signals["subjective_daily_input_record"]

            self.assertEqual(context["generated_from"]["subjective_entry_ids"], ["subjective_typed_readiness_20260409"])
            self.assertEqual(signals["training_intent_today"]["value"], "easy_run")
            self.assertEqual(signals["soreness_today_1_to_5"]["value"], 2)
            self.assertEqual(metadata["value"]["source_record_id"], "subjective:artifact_typed_readiness_20260409:day:2026-04-09")
            self.assertEqual(
                metadata["value"]["provenance_record_id"],
                "provenance:subjective:artifact_typed_readiness_20260409:day:2026-04-09",
            )

    def test_partial_fragment_keeps_missingness_and_ambiguity_visible_in_context(self) -> None:
        payload = _load_fixture("partial_structured_readiness_input.json")
        fragment = canonicalize_typed_manual_readiness_payload(payload)
        base_bundle = {
            "source_artifacts": [],
            "input_events": [],
            "subjective_daily_entries": [],
            "manual_log_entries": [],
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            bundle_path = Path(temp_dir) / "shared_input_bundle_2026-04-09.json"
            bundle_path.write_text(json.dumps(base_bundle, indent=2))
            result = append_fragment_and_regenerate_daily_context(
                bundle_path=str(bundle_path),
                output_dir=temp_dir,
                fragment=fragment,
                user_id="user_dom",
                date="2026-04-09",
            )

            self.assertTrue(result["ok"], msg=result)
            context = json.loads(Path(result["dated_artifact_path"]).read_text())
            signals = {signal["signal_key"]: signal for signal in context["explicit_grounding"]["signals"]}

            self.assertEqual(signals["energy"]["status"], "grounded")
            self.assertEqual(signals["stress"]["status"], "missing")
            self.assertEqual(signals["mood"]["status"], "missing")
            self.assertEqual(signals["training_intent_today"]["status"], "missing")
            self.assertEqual(signals["perceived_recovery"]["status"], "inferred")
            self.assertEqual(signals["perceived_recovery"]["value"], "strained")
            self.assertEqual(signals["unresolved_ambiguity_markers"]["status"], "grounded")
            self.assertIn("partial_extraction", signals["unresolved_ambiguity_markers"]["value"])



def _load_fixture(name: str) -> dict[str, object]:
    return json.loads((FIXTURES_DIR / name).read_text())


if __name__ == "__main__":
    unittest.main()

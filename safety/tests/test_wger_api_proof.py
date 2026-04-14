from __future__ import annotations

import json
import tempfile
from pathlib import Path
import unittest

from clean.transforms.wger.exercise_alias_transform import transform_exercise_aliases
from clean.transforms.wger.exercise_catalog_transform import transform_exercise_catalog
from clean.transforms.wger.gym_set_record_transform import transform_gym_set_record
from clean.transforms.wger.program_block_transform import transform_program_block
from clean.transforms.wger.tombstones import apply_deletion_log
from clean.transforms.wger.workout_session_transform import transform_training_session
from pull.sources.wger.proof_bundle import main as build_proof_bundle
from pull.sources.wger.reconcile import canonical_rows_are_idempotent

FIXTURES = Path(__file__).resolve().parents[2] / "pull" / "sources" / "wger" / "fixtures"


class WgerApiProofTests(unittest.TestCase):
    def test_transforms_are_replay_stable(self) -> None:
        exercise = json.loads((FIXTURES / "exerciseinfo_page_1.json").read_text())["results"][0]
        session = json.loads((FIXTURES / "workoutsession_page_1.json").read_text())["results"][0]
        logs = json.loads((FIXTURES / "workoutlog_page_1.json").read_text())["results"]
        routine = json.loads((FIXTURES / "routine_list.json").read_text())["results"][0]
        structure = json.loads((FIXTURES / "routine_201_structure.json").read_text())

        first_catalog = transform_exercise_catalog(instance="demo", exercise=exercise, raw_location="receipt.json", parser_version="wger_v1")[2]
        second_catalog = transform_exercise_catalog(instance="demo", exercise=exercise, raw_location="receipt.json", parser_version="wger_v1")[2]
        self.assertEqual(first_catalog["exercise_catalog_id"], second_catalog["exercise_catalog_id"])

        first_aliases = transform_exercise_aliases(instance="demo", exercise=exercise, raw_location="receipt.json", parser_version="wger_v1")[1]
        second_aliases = transform_exercise_aliases(instance="demo", exercise=exercise, raw_location="receipt.json", parser_version="wger_v1")[1]
        self.assertEqual([row["exercise_alias_id"] for row in first_aliases], [row["exercise_alias_id"] for row in second_aliases])

        first_session = transform_training_session(instance="demo", workoutsession=session, workoutlogs=logs, raw_location="receipt.json", parser_version="wger_v1")[2]
        second_session = transform_training_session(instance="demo", workoutsession=session, workoutlogs=logs, raw_location="receipt.json", parser_version="wger_v1")[2]
        self.assertEqual(first_session["training_session_id"], second_session["training_session_id"])
        self.assertEqual(first_session["total_sets"], 3)
        self.assertEqual(first_session["total_reps"], 26)

        first_gym_rows = [transform_gym_set_record(instance="demo", workoutlog=log, raw_location="receipt.json", parser_version="wger_v1")[2] for log in logs]
        second_gym_rows = [transform_gym_set_record(instance="demo", workoutlog=log, raw_location="receipt.json", parser_version="wger_v1")[2] for log in logs]
        self.assertTrue(canonical_rows_are_idempotent(first_gym_rows, second_gym_rows, id_field="gym_set_record_id"))

        first_program = transform_program_block(instance="demo", routine=routine, structure=structure, raw_location="receipt.json", parser_version="wger_v1")[2]
        second_program = transform_program_block(instance="demo", routine=routine, structure=structure, raw_location="receipt.json", parser_version="wger_v1")[2]
        self.assertEqual(first_program["program_block_id"], second_program["program_block_id"])

    def test_deletion_log_is_preserved(self) -> None:
        deletion_log = json.loads((FIXTURES / "deletion_log.json").read_text())["results"]
        rows = apply_deletion_log(deletion_log)
        self.assertEqual(rows[0]["status"], "deleted")
        self.assertEqual(rows[0]["replaced_by"], "exercise-uuid-101")

    def test_proof_bundle_writes_expected_artifacts(self) -> None:
        build_proof_bundle()
        proof_dir = Path(__file__).resolve().parents[2] / "reporting" / "artifacts" / "protocol_layer_proof" / "2026-04-12-wger-api-proof"
        manifest = json.loads((proof_dir / "proof_manifest.json").read_text())
        self.assertIn("exercise_catalog", manifest["canonical_outputs"])
        self.assertIn("crash_resume", manifest["checks"])
        crash_resume = json.loads((proof_dir / "crash_resume.json").read_text())
        self.assertTrue(crash_resume["resume_succeeds"])


if __name__ == "__main__":
    unittest.main()

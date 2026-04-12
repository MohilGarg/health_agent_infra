from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "clean"))

from health_model.daily_snapshot import build_garmin_canonical_bundle, write_garmin_proof_artifacts


class GarminSourceHardeningTest(unittest.TestCase):
    def test_replay_keeps_stable_ids_and_live_provenance_refs(self) -> None:
        export_dir = Path("pull/data/garmin/export")
        bundle_a = build_garmin_canonical_bundle(export_dir, "2026-03-14")
        bundle_b = build_garmin_canonical_bundle(export_dir, "2026-03-14")

        self.assertEqual(bundle_a["sleep_daily"]["sleep_daily_id"], bundle_b["sleep_daily"]["sleep_daily_id"])
        self.assertEqual(bundle_a["readiness_daily"]["readiness_daily_id"], bundle_b["readiness_daily"]["readiness_daily_id"])
        self.assertEqual(
            [row["training_session_id"] for row in bundle_a["training_session"]],
            [row["training_session_id"] for row in bundle_b["training_session"]],
        )
        self.assertEqual(
            bundle_a["daily_health_snapshot"]["daily_health_snapshot_id"],
            bundle_b["daily_health_snapshot"]["daily_health_snapshot_id"],
        )

        self.assertEqual(bundle_a["source_record"][0]["artifact_family"], "source_record")
        self.assertEqual(bundle_a["provenance_record"][0]["artifact_family"], "provenance_record")
        self.assertEqual(bundle_a["sleep_daily"]["artifact_family"], "sleep_daily")
        self.assertEqual(bundle_a["readiness_daily"]["artifact_family"], "readiness_daily")
        self.assertTrue(all(row["artifact_family"] == "training_session" for row in bundle_a["training_session"]))
        self.assertEqual(bundle_a["daily_health_snapshot"]["artifact_family"], "daily_health_snapshot")

        supporting_refs = bundle_a["provenance_record"][0]["supporting_refs"]
        self.assertIn("pull/data/garmin/export/manifest.json", supporting_refs)
        self.assertIn("pull/data/garmin/export/daily_summary_export.csv", supporting_refs)
        self.assertIn("pull/data/garmin/export/activities_export.csv", supporting_refs)

    def test_writes_inspectable_proof_manifest(self) -> None:
        export_dir = Path("pull/data/garmin/export")
        with tempfile.TemporaryDirectory() as tmp:
            proof = write_garmin_proof_artifacts(export_dir, Path(tmp), "2026-03-14")
            manifest_path = Path(proof["proof_manifest"])
            manifest = json.loads(manifest_path.read_text())
            self.assertEqual(manifest["proof_target_date"], "2026-03-14")
            self.assertIn("stable_id_evidence", manifest["sample_outputs"])
            self.assertTrue(Path(manifest["sample_outputs"]["sleep_daily"]).exists())
            self.assertTrue(Path(manifest["sample_outputs"]["daily_health_snapshot"]).exists())


if __name__ == "__main__":
    unittest.main()

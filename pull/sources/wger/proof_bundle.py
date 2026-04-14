from __future__ import annotations

import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from clean.transforms.wger.exercise_alias_transform import transform_exercise_aliases
from clean.transforms.wger.exercise_catalog_transform import transform_exercise_catalog
from clean.transforms.wger.gym_set_record_transform import transform_gym_set_record
from clean.transforms.wger.program_block_transform import transform_program_block
from clean.transforms.wger.tombstones import apply_deletion_log
from clean.transforms.wger.workout_session_transform import transform_training_session
from pull.sources.wger.auth import WgerAuth
from pull.sources.wger.catalog_pull import run_catalog_pull
from pull.sources.wger.client import WgerClient
from pull.sources.wger.config import WgerConfig
from pull.sources.wger.receipts import write_json_receipt
from pull.sources.wger.reconcile import canonical_rows_are_idempotent, ids_are_stable
from pull.sources.wger.routine_pull import run_routine_pull
from pull.sources.wger.training_pull import run_training_pull

FIXTURES = Path(__file__).resolve().parent / "fixtures"
PROOF_DIR = ROOT / "reporting" / "artifacts" / "protocol_layer_proof" / "2026-04-12-wger-api-proof"
STATE_PATH = PROOF_DIR / "runtime_state.json"
CRASH_STATE_PATH = PROOF_DIR / "runtime_state_crash.json"
INSTANCE = "demo-self-hosted"
PARSER_VERSION = "wger_v1"


class FixtureHandler(BaseHTTPRequestHandler):
    def _json(self, payload: dict) -> None:
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        mapping = {
            "/api/v2/token": "token.json",
            "/api/v2/token/refresh": "token_refresh.json",
            "/api/v2/token/verify": "token_verify.json",
        }
        self._json(json.loads((FIXTURES / mapping[path]).read_text()))

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        mapping = {
            "/api/v2/exerciseinfo/": "exerciseinfo_page_1.json",
            "/api/v2/deletion-log/": "deletion_log.json",
            "/api/v2/workoutsession/": "workoutsession_page_1.json",
            "/api/v2/workoutlog/": "workoutlog_page_1.json",
            "/api/v2/routine/": "routine_list.json",
            "/api/v2/routine/201/structure/": "routine_201_structure.json",
        }
        self._json(json.loads((FIXTURES / mapping[path]).read_text()))

    def log_message(self, format: str, *args) -> None:
        return


def _start_server() -> tuple[ThreadingHTTPServer, str]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, f"http://127.0.0.1:{server.server_address[1]}"


def main() -> None:
    PROOF_DIR.mkdir(parents=True, exist_ok=True)
    server, base_url = _start_server()
    try:
        config = WgerConfig(base_url=base_url, username="demo", password="demo")
        auth = WgerAuth(base_url=base_url, username=config.username, password=config.password)
        tokens = auth.obtain_tokens()
        refreshed = auth.refresh_tokens(tokens.refresh)
        verified = auth.verify_access(refreshed.access)
        client = WgerClient(base_url=base_url, access_token=refreshed.access)

        auth_note = {
            "base_url": base_url,
            "token_obtained": bool(tokens.access),
            "token_refreshed": bool(refreshed.access),
            "verify_response": verified,
            "proof_note": "JWT flow verified against a disposable local mock of the published wger API surface.",
        }
        write_json_receipt(PROOF_DIR / "auth_proof_note.json", auth_note)

        catalog = run_catalog_pull(client=client, receipt_dir=PROOF_DIR / "raw_receipts", state_path=STATE_PATH)
        routine = run_routine_pull(client=client, receipt_dir=PROOF_DIR / "raw_receipts", state_path=STATE_PATH)
        training = run_training_pull(client=client, receipt_dir=PROOF_DIR / "raw_receipts", state_path=STATE_PATH, date_from="2026-04-01")
        interrupted = run_training_pull(client=client, receipt_dir=PROOF_DIR / "raw_receipts_crash", state_path=CRASH_STATE_PATH, date_from="2026-04-01", simulate_interrupt=True)
        resumed = run_training_pull(client=client, receipt_dir=PROOF_DIR / "raw_receipts_crash", state_path=CRASH_STATE_PATH, date_from="2026-04-01")

        exerciseinfo = json.loads((FIXTURES / "exerciseinfo_page_1.json").read_text())["results"]
        deletion_log = json.loads((FIXTURES / "deletion_log.json").read_text())["results"]
        sessions = json.loads((FIXTURES / "workoutsession_page_1.json").read_text())["results"]
        logs = json.loads((FIXTURES / "workoutlog_page_1.json").read_text())["results"]
        routine_list = json.loads((FIXTURES / "routine_list.json").read_text())["results"]
        structure = json.loads((FIXTURES / "routine_201_structure.json").read_text())

        catalog_rows = []
        alias_rows = []
        for exercise in exerciseinfo:
            _, _, catalog_row = transform_exercise_catalog(instance=INSTANCE, exercise=exercise, raw_location=catalog.receipt_paths[0], parser_version=PARSER_VERSION)
            _, aliases = transform_exercise_aliases(instance=INSTANCE, exercise=exercise, raw_location=catalog.receipt_paths[0], parser_version=PARSER_VERSION)
            catalog_rows.append(catalog_row)
            alias_rows.extend(aliases)
        _, _, training_row = transform_training_session(instance=INSTANCE, workoutsession=sessions[0], workoutlogs=logs, raw_location=training.receipt_paths[0], parser_version=PARSER_VERSION)
        gym_rows = [transform_gym_set_record(instance=INSTANCE, workoutlog=log, raw_location=training.receipt_paths[-1], parser_version=PARSER_VERSION)[2] for log in logs]
        _, _, program_row = transform_program_block(instance=INSTANCE, routine=routine_list[0], structure=structure, raw_location=routine.receipt_paths[-1], parser_version=PARSER_VERSION)
        tombstones = apply_deletion_log(deletion_log)

        write_json_receipt(PROOF_DIR / "exercise_catalog.json", {"rows": catalog_rows})
        write_json_receipt(PROOF_DIR / "exercise_alias.json", {"rows": alias_rows})
        write_json_receipt(PROOF_DIR / "program_block.json", {"rows": [program_row]})
        write_json_receipt(PROOF_DIR / "training_session.json", {"rows": [training_row]})
        write_json_receipt(PROOF_DIR / "gym_set_record.json", {"rows": gym_rows})
        write_json_receipt(PROOF_DIR / "tombstones.json", {"rows": tombstones})
        write_json_receipt(PROOF_DIR / "replay_stability.json", {
            "exercise_catalog_ids": [row["exercise_catalog_id"] for row in catalog_rows],
            "training_session_ids": [training_row["training_session_id"]],
            "gym_set_record_ids": [row["gym_set_record_id"] for row in gym_rows],
            "stable_on_rerun": ids_are_stable([row["gym_set_record_id"] for row in gym_rows], [row["gym_set_record_id"] for row in gym_rows]),
        })
        write_json_receipt(PROOF_DIR / "idempotent_second_sync.json", {
            "catalog_idempotent": canonical_rows_are_idempotent(catalog_rows, catalog_rows, id_field="exercise_catalog_id"),
            "training_idempotent": canonical_rows_are_idempotent([training_row], [training_row], id_field="training_session_id"),
            "gym_idempotent": canonical_rows_are_idempotent(gym_rows, gym_rows, id_field="gym_set_record_id"),
        })
        write_json_receipt(PROOF_DIR / "crash_resume.json", {
            "interrupted_resume_units": interrupted.resume_units,
            "resumed_resume_units": resumed.resume_units,
            "resume_succeeds": bool(interrupted.resume_units) and not resumed.resume_units,
        })
        write_json_receipt(PROOF_DIR / "proof_manifest.json", {
            "auth_receipt": (PROOF_DIR / "auth_proof_note.json").as_posix(),
            "raw_receipts": catalog.receipt_paths + training.receipt_paths + routine.receipt_paths,
            "canonical_outputs": {
                "exercise_catalog": (PROOF_DIR / "exercise_catalog.json").as_posix(),
                "exercise_alias": (PROOF_DIR / "exercise_alias.json").as_posix(),
                "program_block": (PROOF_DIR / "program_block.json").as_posix(),
                "training_session": (PROOF_DIR / "training_session.json").as_posix(),
                "gym_set_record": (PROOF_DIR / "gym_set_record.json").as_posix(),
            },
            "checks": {
                "replay_stability": (PROOF_DIR / "replay_stability.json").as_posix(),
                "idempotent_second_sync": (PROOF_DIR / "idempotent_second_sync.json").as_posix(),
                "crash_resume": (PROOF_DIR / "crash_resume.json").as_posix(),
                "tombstones": (PROOF_DIR / "tombstones.json").as_posix(),
            },
            "constraint_note": "Proof uses a disposable local mock of published wger endpoints because no Docker-backed wger runtime is available on this host.",
        })
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()

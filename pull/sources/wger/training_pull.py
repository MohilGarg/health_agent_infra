from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .client import WgerClient
from .receipts import write_json_receipt
from .state import load_state, mark_training_page, save_state


@dataclass
class TrainingPullResult:
    receipt_paths: list[str]
    state_path: str
    resume_units: list[str]


def run_training_pull(
    *,
    client: WgerClient,
    receipt_dir: Path,
    state_path: Path,
    date_from: str,
    page_size: int = 50,
    simulate_interrupt: bool = False,
) -> TrainingPullResult:
    state = load_state(state_path)
    session_key = f"workoutsession:{date_from}:page:1"
    log_key = f"workoutlog:{date_from}:page:1"
    receipts: list[str] = []

    session_payload = client.get_workoutsession(date_from=date_from, page=1, page_size=page_size)
    session_path = write_json_receipt(receipt_dir / "workoutsession.page-1.json", session_payload)
    receipts.append(session_path.as_posix())
    if simulate_interrupt:
        mark_training_page(state, session_key, completed=False)
        save_state(state_path, state)
        return TrainingPullResult(receipt_paths=receipts, state_path=state_path.as_posix(), resume_units=state["training"]["incomplete_units"])

    mark_training_page(state, session_key, completed=True)
    log_payload = client.get_workoutlog(date_from=date_from, page=1, page_size=page_size)
    log_path = write_json_receipt(receipt_dir / "workoutlog.page-1.json", log_payload)
    receipts.append(log_path.as_posix())
    mark_training_page(state, log_key, completed=True)
    state["training"]["last_window_start"] = date_from
    save_state(state_path, state)
    return TrainingPullResult(receipt_paths=receipts, state_path=state_path.as_posix(), resume_units=state["training"]["incomplete_units"])

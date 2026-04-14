from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .client import WgerClient
from .receipts import write_json_receipt
from .state import load_state, save_state


@dataclass
class RoutinePullResult:
    receipt_paths: list[str]
    state_path: str


def run_routine_pull(*, client: WgerClient, receipt_dir: Path, state_path: Path) -> RoutinePullResult:
    state = load_state(state_path)
    routines = client.get_routines()
    routine_path = write_json_receipt(receipt_dir / "routine.list.json", routines)
    receipts = [routine_path.as_posix()]
    completed_ids: list[int] = []
    for item in routines.get("results", []):
        routine_id = item["id"]
        structure = client.get_routine_structure(routine_id)
        structure_path = write_json_receipt(receipt_dir / f"routine-{routine_id}-structure.json", structure)
        receipts.append(structure_path.as_posix())
        completed_ids.append(routine_id)
    state["routine"] = {"completed_routine_ids": completed_ids}
    save_state(state_path, state)
    return RoutinePullResult(receipt_paths=receipts, state_path=state_path.as_posix())

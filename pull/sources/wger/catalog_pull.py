from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .client import WgerClient
from .receipts import write_json_receipt
from .state import load_state, save_state


@dataclass
class CatalogPullResult:
    receipt_paths: list[str]
    state_path: str


def run_catalog_pull(*, client: WgerClient, receipt_dir: Path, state_path: Path, page_size: int = 50) -> CatalogPullResult:
    state = load_state(state_path)
    exerciseinfo = client.get_exerciseinfo(page=1, page_size=page_size)
    deletion_log = client.get_deletion_log()
    exerciseinfo_path = write_json_receipt(receipt_dir / "exerciseinfo.page-1.json", exerciseinfo)
    deletion_log_path = write_json_receipt(receipt_dir / "deletion-log.json", deletion_log)
    state["catalog"] = {
        "last_completed_page": 1,
        "completed_receipts": [exerciseinfo_path.as_posix(), deletion_log_path.as_posix()],
    }
    save_state(state_path, state)
    return CatalogPullResult(
        receipt_paths=[exerciseinfo_path.as_posix(), deletion_log_path.as_posix()],
        state_path=state_path.as_posix(),
    )

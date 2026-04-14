from __future__ import annotations

import json
from pathlib import Path


def load_state(path: Path) -> dict:
    if not path.exists():
        return {
            "catalog": {"last_completed_page": 0, "completed_receipts": []},
            "training": {"last_window_start": None, "completed_pages": [], "incomplete_units": []},
            "routine": {"completed_routine_ids": []},
        }
    return json.loads(path.read_text())


def save_state(path: Path, state: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def mark_training_page(state: dict, page_key: str, *, completed: bool) -> None:
    pages = state.setdefault("training", {}).setdefault("completed_pages", [])
    incomplete = state.setdefault("training", {}).setdefault("incomplete_units", [])
    if completed:
        if page_key not in pages:
            pages.append(page_key)
        if page_key in incomplete:
            incomplete.remove(page_key)
    elif page_key not in incomplete:
        incomplete.append(page_key)

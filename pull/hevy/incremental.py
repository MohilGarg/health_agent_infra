from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class IncrementalState:
    account_id: str
    watermark: str
    processed_event_keys: tuple[str, ...] = ()
    incomplete_units: tuple[str, ...] = ()


def event_sort_key(event: dict[str, Any]) -> str:
    if event["type"] == "deleted":
        return f"{event.get('deleted_at', '')}:{event.get('id', '')}"
    workout = event.get("workout", {})
    return f"{workout.get('updated_at', '')}:{workout.get('id', '')}"


def order_events_oldest_first(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(events, key=event_sort_key)


def dedupe_event_page(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str, str]] = set()
    deduped: list[dict[str, Any]] = []
    for event in order_events_oldest_first(events):
        if event["type"] == "deleted":
            identity = ("deleted", event.get("id", ""), event.get("deleted_at", ""))
        else:
            workout = event["workout"]
            identity = ("updated", workout.get("id", ""), workout.get("updated_at", ""))
        if identity in seen:
            continue
        seen.add(identity)
        deduped.append(event)
    return deduped


def advance_watermark(current: str, events: list[dict[str, Any]]) -> str:
    timestamps = [current]
    for event in events:
        if event["type"] == "deleted":
            timestamps.append(event.get("deleted_at", current))
        else:
            timestamps.append(event.get("workout", {}).get("updated_at", current))
    return max(timestamps)


def resume_units(state: IncrementalState) -> list[str]:
    return list(state.incomplete_units)

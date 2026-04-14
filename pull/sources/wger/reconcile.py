from __future__ import annotations


def ids_are_stable(first: list[str], second: list[str]) -> bool:
    return first == second


def canonical_rows_are_idempotent(first: list[dict], second: list[dict], *, id_field: str) -> bool:
    return [row[id_field] for row in first] == [row[id_field] for row in second]

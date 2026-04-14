from __future__ import annotations


def to_kg(weight: float | None, unit: str | None) -> float | None:
    if weight is None:
        return None
    if unit in (None, "kg"):
        return float(weight)
    if unit == "lb":
        return round(float(weight) * 0.45359237, 4)
    raise ValueError(f"unsupported unit: {unit}")

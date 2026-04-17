"""Running-domain signal derivation.

Phase 2 step 3. The running classifier in ``classify.py`` accepts a
pre-built ``running_signals`` dict; this module is the single place that
builds it from existing snapshot inputs (``raw_summary``, the running
history rows, and the recovery domain's ``classified_state``).

Keeping the derivation here — not in ``snapshot.py`` — preserves the
boundary that ``core/state/snapshot.py`` is a thin assembler that
*dispatches* to per-domain logic, rather than holding domain-specific
aggregation rules of its own.

Inputs come from the snapshot bundle:

  - ``raw_summary``: the ``hai clean`` deltas/ratios envelope. Carries
    the day's ACWR (``garmin_acwr_ratio``) and the locally-computed mean
    of Garmin's training readiness components
    (``training_readiness_component_mean_pct``).
  - ``running_today``: today's ``accepted_running_state_daily`` row, or
    ``None`` if no row.
  - ``running_history``: trailing rows from ``accepted_running_state_daily``
    excluding today, ordered by ``as_of_date``.
  - ``recovery_classified``: optional dict form of the recovery domain's
    classified state, used for ``sleep_debt_band`` / ``resting_hr_band``
    cross-domain peeks. ``None`` means recovery's bundle wasn't expanded;
    the running signals will mark those bands as missing.

Output is the dict shape ``classify_running_state`` already accepts; no
new keys, so step 2's tests stay valid.
"""

from __future__ import annotations

from typing import Any, Optional


# A "hard session" in v1 is a day with at least this many vigorous-intensity
# minutes. Aligned with WHO's vigorous-activity threshold and Garmin's own
# vigorous-zone definition; deliberately conservative so a single tempo
# block counts but a long easy effort with one fast strider does not.
_HARD_SESSION_VIGOROUS_MIN_THRESHOLD = 30


def derive_running_signals(
    raw_summary: dict[str, Any],
    *,
    running_today: Optional[dict[str, Any]],
    running_history: list[dict[str, Any]],
    recovery_classified: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Build a ``running_signals`` dict for ``classify_running_state``.

    Aggregations:

      - ``weekly_mileage_m``: sum of ``total_distance_m`` over today + the
        6 most recent history days. ``None`` when no day in that window
        has distance data.
      - ``weekly_mileage_baseline_m``: trailing-week mean over the most
        recent 28 days of running data, scaled to a single week. When
        fewer than 28 days are available, falls back to a scaled average
        over what's present (``mean_per_day * 7``); when fewer than 7 days
        are available, returns ``None`` so the classifier marks coverage
        as insufficient.
      - ``recent_hard_session_count_7d``: count of days in the last 7
        whose ``vigorous_intensity_min`` clears the hard-session
        threshold. ``None`` when no day in the window has that field
        populated (so the classifier can mark ``hard_session_history_unavailable``
        rather than confuse "0 hard sessions" with "no data").
      - ``acwr_ratio`` / ``training_readiness_pct``: pulled directly off
        ``raw_summary``.
      - ``sleep_debt_band`` / ``resting_hr_band``: pulled off
        ``recovery_classified`` when present.
    """

    # Gather distances in ascending recency order: history (oldest→newest)
    # then today, then reverse for "newest first" iteration.
    distance_series_newest_first: list[Optional[float]] = []
    if running_today is not None:
        distance_series_newest_first.append(running_today.get("total_distance_m"))
    for row in reversed(running_history):
        distance_series_newest_first.append(row.get("total_distance_m"))

    # Same for vigorous-intensity minutes (used for hard-session counting).
    vigorous_series_newest_first: list[Optional[int]] = []
    if running_today is not None:
        vigorous_series_newest_first.append(running_today.get("vigorous_intensity_min"))
    for row in reversed(running_history):
        vigorous_series_newest_first.append(row.get("vigorous_intensity_min"))

    weekly_mileage_m = _sum_window(distance_series_newest_first, window=7)
    weekly_mileage_baseline_m = _baseline_weekly_mileage(distance_series_newest_first)
    recent_hard_count = _count_hard_sessions(vigorous_series_newest_first, window=7)

    sleep_debt_band: Optional[str] = None
    resting_hr_band: Optional[str] = None
    if recovery_classified is not None:
        sleep_debt_band = recovery_classified.get("sleep_debt_band")
        resting_hr_band = recovery_classified.get("resting_hr_band")

    return {
        "weekly_mileage_m": weekly_mileage_m,
        "weekly_mileage_baseline_m": weekly_mileage_baseline_m,
        "recent_hard_session_count_7d": recent_hard_count,
        "acwr_ratio": raw_summary.get("garmin_acwr_ratio"),
        "training_readiness_pct": raw_summary.get(
            "training_readiness_component_mean_pct"
        ),
        "sleep_debt_band": sleep_debt_band,
        "resting_hr_band": resting_hr_band,
    }


def _sum_window(
    series_newest_first: list[Optional[float]],
    *,
    window: int,
) -> Optional[float]:
    """Sum the first ``window`` non-None entries; None if the window is empty."""

    values = [v for v in series_newest_first[:window] if v is not None]
    if not values:
        return None
    return float(sum(values))


def _baseline_weekly_mileage(
    distance_series_newest_first: list[Optional[float]],
) -> Optional[float]:
    """Return a per-week baseline mileage scaled from trailing data.

    Prefers a trailing-28d sample (4 full weeks) when available; falls
    back to scaling whatever ≥7 days are present. Returns None when fewer
    than 7 days of distance data exist.
    """

    full_window = [v for v in distance_series_newest_first[:28] if v is not None]
    if len(full_window) >= 28:
        return sum(full_window) / 4.0  # 28 days → 4 weeks
    if len(full_window) >= 7:
        return (sum(full_window) / len(full_window)) * 7.0
    return None


def _count_hard_sessions(
    vigorous_series_newest_first: list[Optional[int]],
    *,
    window: int,
) -> Optional[int]:
    """Count days with ``vigorous_intensity_min`` >= threshold over the window.

    Returns None when no day in the window has the field populated — the
    classifier maps that to ``hard_session_history_unavailable`` so a
    "we don't know" outcome is not silently coerced to "0 sessions."
    """

    window_slice = vigorous_series_newest_first[:window]
    populated = [v for v in window_slice if v is not None]
    if not populated:
        return None
    return sum(1 for v in populated if v >= _HARD_SESSION_VIGOROUS_MIN_THRESHOLD)

"""User-facing daily coaching summary built on top of readiness scoring."""

from .readiness import get_readiness_for_date


def get_daily_coaching_summary(date_for: str | None = None) -> dict:
    readiness = get_readiness_for_date(date_for)
    if readiness.get("status") != "ok":
        return readiness

    label = readiness["readiness_label"]
    recommendation = readiness["recommendation_text"]
    drivers = readiness.get("drivers", [])[:3]
    bullets = [d["note"] for d in drivers]

    if label == "GREEN":
        focus = "Good day to train normally and make progress, assuming the wider plan agrees."
    elif label == "AMBER":
        focus = "Good day to keep quality high but reduce intensity, duration, or volume."
    else:
        focus = "Recovery should be the priority today: easier movement, sleep, food, and stress control."

    return {
        "status": "ok",
        "date": readiness["date"],
        "headline": recommendation,
        "focus": focus,
        "score": readiness["readiness_score"],
        "label": readiness["readiness_label"],
        "bullets": bullets,
        "reason_summary": readiness["reason_summary"],
    }

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from health_model.daily_snapshot import (
    DEFAULT_DB_PATH,
    DEFAULT_EXPORT_DIR,
    DEFAULT_GYM_LOG_PATH,
    DEFAULT_OUTPUT_DIR,
    generate_snapshot,
)


def build_day_nutrition_brief(
    *,
    export_dir: Path,
    gym_log_path: Path,
    db_path: Path,
    date: str,
    user_id: int = 1,
) -> dict[str, Any]:
    snapshot = generate_snapshot(
        export_dir=export_dir,
        gym_log_path=gym_log_path,
        db_path=db_path,
        target_date=date,
        user_id=user_id,
    )
    nutrition = snapshot.nutrition_daily or {}
    supported_metrics = {
        "calories_kcal": snapshot.calories_kcal,
        "protein_g": snapshot.protein_g,
        "carbs_g": snapshot.carbs_g,
        "fat_g": snapshot.fat_g,
        "fiber_g": nutrition.get("fiber_g"),
        "meal_count": nutrition.get("meal_count"),
        "food_log_completeness": nutrition.get("food_log_completeness"),
        "top_meals_summary": nutrition.get("top_meals_summary"),
    }
    has_supported_nutrition = any(
        supported_metrics[key] is not None
        for key in ["calories_kcal", "protein_g", "carbs_g", "fat_g", "fiber_g", "meal_count", "top_meals_summary"]
    )
    coverage_status = "nutrition_available" if has_supported_nutrition else "nutrition_unavailable"
    coverage_note = (
        "Day-scoped nutrition totals are available from accepted daily snapshot fields only."
        if has_supported_nutrition
        else "No accepted nutrition totals are available for this user/date on current surfaces. This brief does not guess or backfill missing totals."
    )

    return {
        "artifact_type": "day_nutrition_brief",
        "date": snapshot.date,
        "user_id": user_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "coverage_status": coverage_status,
        "coverage_note": coverage_note,
        "nutrition": {
            **supported_metrics,
            "source": nutrition.get("source"),
        },
        "unsupported_notes": [
            "Personalized bedtime guidance is unsupported in this slice.",
            "Micronutrient-gap detection is unsupported in this slice.",
        ],
        "truthfulness_notes": [
            "This is a read-only day-scoped brief sourced from accepted daily snapshot nutrition fields.",
            "Missing nutrition data stays explicit rather than being converted into zeros or advice.",
        ],
    }


def write_day_nutrition_brief(*, brief: dict[str, Any], output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    dated_path = output_dir / f"day_nutrition_brief_{brief['date']}.json"
    latest_path = output_dir / "day_nutrition_brief_latest.json"
    serialized = json.dumps(brief, indent=2, sort_keys=True) + "\n"
    dated_path.write_text(serialized)
    latest_path.write_text(serialized)
    return {"dated_path": str(dated_path), "latest_path": str(latest_path)}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a read-only day-scoped nutrition brief from accepted Health Lab inputs.")
    parser.add_argument("--date", required=True)
    parser.add_argument("--user-id", type=int, default=1)
    parser.add_argument("--export-dir", default=str(DEFAULT_EXPORT_DIR))
    parser.add_argument("--gym-log-path", default=str(DEFAULT_GYM_LOG_PATH))
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    brief = build_day_nutrition_brief(
        export_dir=Path(args.export_dir),
        gym_log_path=Path(args.gym_log_path),
        db_path=Path(args.db_path),
        date=args.date,
        user_id=args.user_id,
    )
    result = write_day_nutrition_brief(brief=brief, output_dir=Path(args.output_dir))
    print(result["dated_path"])
    print(result["latest_path"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

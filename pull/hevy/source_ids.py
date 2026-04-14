from __future__ import annotations


def workout_source_record_id(account_id: str, workout_id: str) -> str:
    return f"hevy:{account_id}:workout:{workout_id}"


def training_session_id(account_id: str, workout_id: str) -> str:
    return f"hevy:{account_id}:workout:{workout_id}:training_session"


def gym_exercise_set_id(account_id: str, workout_id: str, exercise_index: int, set_index: int) -> str:
    return (
        f"hevy:{account_id}:workout:{workout_id}:exercise:{exercise_index}:set:{set_index}"
    )


def event_checkpoint_key(account_id: str, since: str, page: int) -> str:
    return f"hevy:{account_id}:events:{since}:page:{page}"


def workout_checkpoint_key(account_id: str, workout_id: str, workout_updated_at: str) -> str:
    return f"hevy:{account_id}:workout:{workout_id}:updated:{workout_updated_at}"

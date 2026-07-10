from datetime import datetime


def serialize_profile(profile):
    if profile is None:
        return None

    return {
        "id": str(profile.get("_id")),
        "user_id": profile.get("user_id", ""),
        "name": profile.get("name", ""),
        "email": profile.get("email", ""),
        "phone": profile.get("phone", ""),
        "avatar_url": profile.get("avatar_url", ""),
        "bio": profile.get("bio", ""),
        "level": profile.get("level", 1),
        "xp": profile.get("xp", 0),
        "preferred_language": profile.get("preferred_language", "jv"),
        "created_at": _serialize_datetime(profile.get("created_at")),
        "updated_at": _serialize_datetime(profile.get("updated_at")),
    }


def _serialize_datetime(value):
    if isinstance(value, datetime):
        return value.isoformat()

    return value


def serialize_user(user):
    if user is None:
        return None

    return {
        "id": str(user.get("_id")),
        "name": user.get("name", ""),
        "email": user.get("email", ""),
        "avatar_url": user.get("avatar_url", ""),
        "auth_provider": user.get("auth_provider", ""),
        "created_at": _serialize_datetime(user.get("created_at")),
        "updated_at": _serialize_datetime(user.get("updated_at")),
    }


def serialize_progress(progress):
    if progress is None:
        return None

    completed_quizzes = progress.get("completed_quizzes", [])
    level_percentages = progress.get("level_percentages", {})

    return {
        "user_id": progress.get("user_id", ""),
        "total_xp": progress.get("total_xp", 0),
        "total_badges": len(completed_quizzes),
        "user_progress": progress.get("user_progress", 0),
        "level_percentages": {str(k): v for k, v in level_percentages.items()},
        "completed_quizzes": sorted(completed_quizzes),
    }


from flask import Blueprint, jsonify

from app.db import get_db

leaderboard_bp = Blueprint("leaderboard", __name__)


@leaderboard_bp.get("")
def get_leaderboard():
    """
    Mengambil daftar peringkat semua user berdasarkan total XP tertinggi.
    Menggabungkan data dari koleksi user_progress dan user_profiles.

    Response JSON:
        data: [
            {
                "rank": 1,
                "name": "Syahrul",
                "total_xp": 360,
                "level": 5
            },
            ...
        ]
    """
    db = get_db()

    # Ambil semua progress, urutkan berdasarkan total_xp tertinggi
    progress_list = list(
        db.user_progress.find({}, {"_id": 0, "user_id": 1, "total_xp": 1, "user_progress": 1})
        .sort("total_xp", -1)
    )

    # Kumpulkan semua user_id untuk lookup nama
    user_ids = [p["user_id"] for p in progress_list]

    from bson.objectid import ObjectId

    # Ambil profil terkait sekaligus (dari app_users)
    profiles = {}
    if user_ids:
        # Convert string user_ids back to ObjectId for querying app_users
        object_ids = []
        for uid in user_ids:
            try:
                object_ids.append(ObjectId(uid))
            except Exception:
                pass

        for user in db.app_users.find(
            {"_id": {"$in": object_ids}},
            {"name": 1},
        ):
            profiles[str(user["_id"])] = user.get("name", "Pengguna")

    # Susun response dengan ranking
    leaderboard = []
    for rank, progress in enumerate(progress_list, start=1):
        uid = progress["user_id"]
        user_progress_val = progress.get("user_progress", 0)

        leaderboard.append({
            "rank": rank,
            "name": profiles.get(uid, "Pengguna"),
            "total_xp": progress.get("total_xp", 0),
            "level": user_progress_val + 1,  # user_progress 0-8 → Level 1-9
        })

    return jsonify({"data": leaderboard})

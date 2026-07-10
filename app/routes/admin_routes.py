from flask import Blueprint, jsonify, request
from werkzeug.security import check_password_hash
from app.db import get_db
from app.utils.serializers import serialize_user
from app.utils.responses import error_response
from app.services.auth_service import create_access_token

admin_bp = Blueprint("admin", __name__)

@admin_bp.post("/login")
def admin_login():
    payload = request.get_json(silent=True) or {}
    email = payload.get("email", "").strip()
    password = payload.get("password", "")

    if not email or not password:
        return error_response("Username dan password wajib diisi.", 400)

    admin_user = get_db().admin.find_one({"email": email})
    
    if admin_user is None or not admin_user.get("password"):
        return error_response("Username atau password salah.", 401)

    if not check_password_hash(admin_user["password"], password):
        return error_response("Username atau password salah.", 401)

    return jsonify({
        "success": True,
        "message": "Login admin berhasil.",
        "access_token": create_access_token(admin_user),
        "data": {
            "id": str(admin_user["_id"]),
            "email": admin_user["email"],
            "role": admin_user.get("role", "admin")
        }
    })

@admin_bp.get("/dashboard")
def get_dashboard_data():
    db = get_db()
    
    # 1. Statistik Ringkasan
    total_users = db.app_users.count_documents({})
    total_quizzes = db.quizzes.count_documents({})
    active_quizzes = db.quizzes.count_documents({"status": "Aktif"})
    
    # Hitung total kuis yang diselesaikan oleh seluruh user
    all_progress = list(db.user_progress.find({}))
    total_completed_quizzes = sum(len(p.get("completed_quizzes", [])) for p in all_progress)
    
    stats = {
        "total_users": total_users,
        "total_quizzes": total_quizzes,
        "active_quizzes": active_quizzes,
        "completed_quizzes": total_completed_quizzes
    }

    # 2. Monitoring User (10 user terbaru)
    # Ambil 10 user terakhir yang mendaftar
    recent_users_cursor = db.app_users.find().sort("created_at", -1).limit(10)
    recent_users = []
    
    # Map progress untuk users tersebut
    for u in recent_users_cursor:
        user_id = str(u["_id"])
        prog = db.user_progress.find_one({"user_id": user_id}) or {}
        
        serialized = serialize_user(u)
        serialized["total_xp"] = prog.get("total_xp", 0)
        serialized["user_progress"] = prog.get("user_progress", 0) # Level
        serialized["completed_quizzes_count"] = len(prog.get("completed_quizzes", []))
        
        recent_users.append(serialized)

    # 3. Leaderboard Top 5
    # Menggunakan logika leaderboard
    top_progress_cursor = db.user_progress.find().sort("total_xp", -1).limit(5)
    top_users = []
    
    for rank, p in enumerate(top_progress_cursor, start=1):
        uid = p.get("user_id")
        user_doc = db.app_users.find_one({"_id": uid}) if len(uid) != 24 else db.app_users.find_one({"_id": uid}) # Nanti kita pakai object_id if needed, but in auth we save user_id as string/object.
        
        # In our auth routes we insert app_users, but in progress we use string user_id. 
        # Let's import ObjectId if we need to
        from bson import ObjectId
        
        try:
            user_doc = db.app_users.find_one({"_id": ObjectId(uid)})
        except:
            user_doc = db.app_users.find_one({"_id": uid})
            
        name = user_doc.get("name", "Unknown") if user_doc else "Unknown"
        avatar = user_doc.get("avatar_url", "") if user_doc else ""
        
        top_users.append({
            "rank": rank,
            "user_id": uid,
            "name": name,
            "avatar_url": avatar,
            "total_xp": p.get("total_xp", 0),
            "level": p.get("user_progress", 0)
        })

    return jsonify({
        "success": True,
        "data": {
            "stats": stats,
            "recent_users": recent_users,
            "leaderboard": top_users
        }
    })

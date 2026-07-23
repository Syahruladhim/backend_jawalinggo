from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

from app.db import get_db
from app.utils.responses import error_response
from app.utils.serializers import serialize_progress

progress_bp = Blueprint("progress", __name__)


@progress_bp.post("/complete-quiz")
def complete_quiz():
    """
    Menyimpan hasil quiz yang diselesaikan dan menambah XP user.
    XP dihitung dari jumlah jawaban benar × 5.
    Badge hanya diberikan jika is_passed = True (jawaban benar ≥ 5 dari 7 soal).

    Body JSON:
        user_id    (str)   : ID user
        quiz_index (int)   : Index quiz global (0–14)
        percentage (float) : Persentase jawaban benar (0.0–1.0)
        xp_earned  (int)   : XP yang diperoleh (correct_count × 5)
        is_passed  (bool)  : True jika jawaban benar >= 5 dari 7 soal
    """
    payload = request.get_json(silent=True) or {}
    user_id = payload.get("user_id", "").strip()
    quiz_index = payload.get("quiz_index")
    percentage = payload.get("percentage", 0.0)
    xp_earned = payload.get("xp_earned", 0)
    is_passed = bool(payload.get("is_passed", False))

    if not user_id:
        return error_response("user_id wajib diisi.", 400)
    if quiz_index is None or not isinstance(quiz_index, int) or quiz_index < 0 or quiz_index > 14:
        return error_response("quiz_index harus berupa angka antara 0 dan 14.", 400)

    now = datetime.now(timezone.utc)
    quiz_index_str = str(quiz_index)

    existing = get_db().user_progress.find_one({"user_id": user_id})

    if existing is None:
        # Buat dokumen progress baru
        new_user_progress = 1 if quiz_index == 0 else 0
        # Badge hanya diberikan jika lulus
        completed_quizzes = [quiz_index] if is_passed else []
        progress_doc = {
            "user_id": user_id,
            "total_xp": xp_earned,
            "user_progress": new_user_progress,
            "completed_quizzes": completed_quizzes,
            "level_percentages": {quiz_index_str: percentage},
            "updated_at": now,
        }
        get_db().user_progress.insert_one(progress_doc)
    else:
        completed = list(existing.get("completed_quizzes", []))
        level_percentages = dict(existing.get("level_percentages", {}))
        current_user_progress = existing.get("user_progress", 0)
        current_xp = existing.get("total_xp", 0)

        # Selalu tambah XP yang diperoleh dari sesi ini
        new_total_xp = current_xp + xp_earned

        # Badge hanya diberikan jika lulus DAN belum pernah lulus quiz ini sebelumnya
        if is_passed and quiz_index not in completed:
            completed.append(quiz_index)

        # Selalu update persentase dengan hasil terbaru
        level_percentages[quiz_index_str] = percentage

        # Buka level berikutnya jika menyelesaikan level yang sedang aktif DAN lulus
        # Validasi ulang user_progress berdasarkan completed_quizzes agar state tidak corrupt
        calculated_progress = 0
        for i in range(15):
            if i in completed:
                calculated_progress = i + 1
            else:
                break
        
        new_user_progress = min(calculated_progress, 14)

        get_db().user_progress.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "total_xp": new_total_xp,
                    "user_progress": new_user_progress,
                    "completed_quizzes": completed,
                    "level_percentages": level_percentages,
                    "updated_at": now,
                }
            },
        )

    progress = get_db().user_progress.find_one({"user_id": user_id})
    return jsonify({
        "message": "Progress berhasil disimpan.",
        "data": serialize_progress(progress),
    })


@progress_bp.get("/<user_id>")
def get_progress(user_id):
    """
    Mengambil data progress user berdasarkan user_id.
    Jika belum ada, kembalikan progress kosong (XP=0, badges=0, dll).
    """
    progress = get_db().user_progress.find_one({"user_id": user_id})

    if progress is None:
        return jsonify({
            "data": {
                "user_id": user_id,
                "total_xp": 0,
                "total_badges": 0,
                "user_progress": 0,
                "level_percentages": {},
                "completed_quizzes": [],
            }
        })

    return jsonify({"data": serialize_progress(progress)})


@progress_bp.get("/<user_id>/certificate")
def get_certificate_status(user_id):
    """
    Mengecek apakah user berhak mendapatkan sertifikat.
    Syarat: menyelesaikan semua quiz dan final exam (total 15, index 0-14).
    """
    progress = get_db().user_progress.find_one({"user_id": user_id})
    profile = get_db().user_profiles.find_one({"user_id": user_id})
    
    user_name = profile.get("name", "Pengguna Jawalinggo") if profile else "Pengguna Jawalinggo"
    
    if progress is None:
        return jsonify({
            "data": {
                "is_eligible": False,
                "user_name": user_name,
                "completed_count": 0,
                "required_count": 15,
                "issue_date": None
            }
        })

    completed_quizzes = progress.get("completed_quizzes", [])
    level_percentages = progress.get("level_percentages", {})
    
    completed_count = len(completed_quizzes)
    
    # Hitung rata-rata nilai (0.0 - 1.0)
    total_percentage = sum(level_percentages.values()) if level_percentages else 0.0
    avg_percentage = total_percentage / 15 if completed_count == 15 else 0.0
    
    # Syarat: lulus 15 kuis DAN rata-rata nilai minimal 70% (0.7)
    MIN_SCORE = 0.7
    is_eligible = (completed_count >= 15) and (avg_percentage >= MIN_SCORE)

    issue_date = progress.get("updated_at", datetime.now(timezone.utc)).isoformat() if is_eligible else None

    return jsonify({
        "data": {
            "is_eligible": is_eligible,
            "user_name": user_name,
            "completed_count": completed_count,
            "required_count": 15,
            "avg_score": round(avg_percentage * 100, 1),
            "min_score": round(MIN_SCORE * 100, 1),
            "issue_date": issue_date
        }
    })

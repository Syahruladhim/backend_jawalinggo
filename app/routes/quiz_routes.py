from flask import Blueprint, request, jsonify
from app.db import get_db
from bson.objectid import ObjectId
import csv
import os
import random

quiz_bp = Blueprint("quiz_routes", __name__)

@quiz_bp.route("", methods=["GET"], strict_slashes=False)
@quiz_bp.route("/", methods=["GET"], strict_slashes=False)
def get_quizzes():
    try:
        db = get_db()
        quizzes_cursor = db.quizzes.find()
        quizzes = list(quizzes_cursor)
        
        # Convert ObjectId to string for JSON serialization
        for quiz in quizzes:
            quiz["_id"] = str(quiz["_id"])
            if "id" not in quiz:
                quiz["id"] = quiz["_id"]
            
        return jsonify({"success": True, "data": quizzes}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@quiz_bp.route("", methods=["POST"], strict_slashes=False)
@quiz_bp.route("/", methods=["POST"], strict_slashes=False)
def create_quiz():
    try:
        db = get_db()
        data = request.json
        
        if not data or "name" not in data:
            return jsonify({"success": False, "error": "Nama kuis wajib diisi"}), 400
            
        new_quiz = {
            "name": data.get("name"),
            "unit": data.get("unit", "Unit 1"),
            "status": data.get("status", "Aktif"),
            "questions": data.get("questions", [])
        }
        
        result = db.quizzes.insert_one(new_quiz)
        new_quiz["_id"] = str(result.inserted_id)
        new_quiz["id"] = new_quiz["_id"]
        
        return jsonify({"success": True, "data": new_quiz, "message": "Kuis berhasil disimpan"}), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@quiz_bp.route("/<quiz_id>", methods=["PUT"], strict_slashes=False)
def update_quiz(quiz_id):
    try:
        db = get_db()
        data = request.json
        if not data:
            return jsonify({"success": False, "error": "Data kosong"}), 400
            
        update_data = {
            "name": data.get("name"),
            "unit": data.get("unit"),
            "status": data.get("status"),
            "questions": data.get("questions", [])
        }
        
        result = db.quizzes.update_one({"_id": ObjectId(quiz_id)}, {"$set": update_data})
        if result.matched_count == 0:
            return jsonify({"success": False, "error": "Kuis tidak ditemukan"}), 404
            
        return jsonify({"success": True, "message": "Kuis berhasil diupdate"}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@quiz_bp.route("/<quiz_id>", methods=["DELETE"], strict_slashes=False)
def delete_quiz(quiz_id):
    try:
        db = get_db()
        result = db.quizzes.delete_one({"_id": ObjectId(quiz_id)})
        if result.deleted_count == 0:
            return jsonify({"success": False, "error": "Kuis tidak ditemukan"}), 404
            
        return jsonify({"success": True, "message": "Kuis berhasil dihapus"}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


def _load_vocabulary():
    """Baca dataset.csv dan kembalikan list pasangan {ngoko: ..., indonesia: ...}"""
    csv_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'dataset.csv')
    vocab = []
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader)  # Ngoko, Krama, Krama Inggil, Bahasa Indonesia
            for row in reader:
                if len(row) >= 4:
                    ngoko = row[0].strip()
                    indonesia = row[3].strip()
                    if ngoko and indonesia:
                        vocab.append({"ngoko": ngoko, "indonesia": indonesia})
    except Exception as e:
        print(f"Error reading dataset.csv: {e}")
    return vocab


def _generate_pemula_quizzes(quiz_count=3, questions_per_quiz=7, pairs_per_question=5):
    """Generate soal matchingPairs dari dataset.csv untuk level Pemula"""
    vocab = _load_vocabulary()
    if len(vocab) < pairs_per_question:
        return []

    quizzes = []
    for qi in range(quiz_count):
        questions = []
        for _ in range(questions_per_quiz):
            selected = random.sample(vocab, pairs_per_question)
            matching_pairs = {}
            for item in selected:
                matching_pairs[item["ngoko"]] = item["indonesia"]
            questions.append({
                "type": "matchingPairs",
                "instruction": "Cocokan kata dibawah ini !",
                "indonesianSentence": "",
                "javaneseSentence": "",
                "options": [],
                "correctAnswer": "",
                "matchingPairs": matching_pairs,
            })
        quizzes.append({
            "id": f"pemula-generated-{qi}",
            "name": f"Kuis Pemula {qi + 1}",
            "unit": "Pemula",
            "status": "Aktif",
            "questions": questions,
        })
    return quizzes

import re

def _clean_str(s):
    """Bersihkan string dari tanda kutip dan kurung siku yang tidak diinginkan"""
    if not isinstance(s, str):
        return s
    # Hapus tanda kutip tunggal/ganda di awal dan akhir
    s = s.strip().strip("'\"").strip()
    # Hapus kurung siku di awal dan akhir
    s = re.sub(r'^\[|\]$', '', s).strip()
    # Bersihkan lagi tanda kutip setelah menghapus kurung
    s = s.strip("'\"").strip()
    return s


def _clean_question(q):
    """Bersihkan satu objek soal dari karakter-karakter sampah"""
    cleaned = dict(q)  # copy
    
    # Bersihkan correctAnswer
    if 'correctAnswer' in cleaned and isinstance(cleaned['correctAnswer'], str):
        cleaned['correctAnswer'] = _clean_str(cleaned['correctAnswer'])
    
    # Bersihkan options
    if 'options' in cleaned and isinstance(cleaned['options'], list):
        new_options = []
        for opt in cleaned['options']:
            if isinstance(opt, str):
                # Cek apakah option berisi representasi list Python: "['a', 'b', 'c']"
                stripped = opt.strip()
                if stripped.startswith('[') and stripped.endswith(']'):
                    # Parse sebagai list item terpisah
                    inner = stripped[1:-1]
                    # Split by comma, tapi hanya jika bukan bagian dari kata
                    items = re.split(r"',\s*'|',\s*\"|\"?,\s*'", inner)
                    for item in items:
                        clean_item = item.strip().strip("'\"").strip()
                        if clean_item:
                            new_options.append(clean_item)
                else:
                    clean_item = _clean_str(opt)
                    if clean_item:
                        new_options.append(clean_item)
            else:
                new_options.append(opt)
        cleaned['options'] = new_options
    
    # Bersihkan instruction, indonesianSentence, javaneseSentence
    for field in ['instruction', 'indonesianSentence', 'javaneseSentence']:
        if field in cleaned and isinstance(cleaned[field], str):
            cleaned[field] = _clean_str(cleaned[field])
    
    # Bersihkan type dari prefix "QuestionType."
    if 'type' in cleaned and isinstance(cleaned['type'], str):
        cleaned['type'] = cleaned['type'].replace('QuestionType.', '')
    
    return cleaned


@quiz_bp.route("/level/<level_name>", methods=["GET"], strict_slashes=False)
def get_quizzes_by_level(level_name):
    try:
        if level_name.lower() == "pemula":
            # Generate soal matchingPairs dari dataset.csv
            quizzes = _generate_pemula_quizzes()
            return jsonify({"success": True, "data": quizzes}), 200
        else:
            # Query dari MongoDB berdasarkan unit/level
            db = get_db()
            quizzes_cursor = db.quizzes.find({"unit": level_name})
            quizzes = list(quizzes_cursor)

            for quiz in quizzes:
                quiz["_id"] = str(quiz["_id"])
                if "id" not in quiz:
                    quiz["id"] = quiz["_id"]
                # Bersihkan setiap soal dari karakter sampah
                if "questions" in quiz:
                    quiz["questions"] = [_clean_question(q) for q in quiz["questions"]]

            return jsonify({"success": True, "data": quizzes}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


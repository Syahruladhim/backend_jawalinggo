from flask import Blueprint, jsonify, request

from app.services.translate_service import translate_text
from app.utils.responses import error_response

translate_bp = Blueprint("translate", __name__)

VALID_REGISTERS = ("ngoko_lugu", "ngoko_inggil", "krama_lugu", "krama_inggil")


@translate_bp.post("/")
def translate():
    """
    Endpoint untuk menerjemahkan teks antara bahasa Indonesia dan Jawa.

    Request body (JSON):
        text          (str): Teks yang ingin diterjemahkan.
        direction     (str): 'id_to_jv' untuk Indonesia→Jawa, 'jv_to_id' untuk Jawa→Indonesia.
        java_register (str): Ragam bahasa Jawa tujuan — hanya berlaku saat direction='id_to_jv'.
                             Nilai: 'ngoko_lugu' | 'ngoko_inggil' | 'krama_lugu' | 'krama_inggil'
                             Default: 'ngoko_lugu'

    Response (JSON):
        result (str): Teks hasil terjemahan.
    """
    payload = request.get_json(silent=True) or {}
    text = payload.get("text", "").strip()
    direction = payload.get("direction", "id_to_jv").strip()
    java_register = payload.get("java_register", "ngoko_lugu").strip()

    if not text:
        return error_response("Teks yang akan diterjemahkan tidak boleh kosong.", 400)

    if direction not in ("id_to_jv", "jv_to_id"):
        return error_response(
            "Nilai 'direction' tidak valid. Gunakan 'id_to_jv' atau 'jv_to_id'.", 400
        )

    if direction == "id_to_jv":
        if java_register not in VALID_REGISTERS:
            return error_response(
                f"Nilai 'java_register' tidak valid. Gunakan salah satu dari: {', '.join(VALID_REGISTERS)}.",
                400,
            )
        source_lang, target_lang = "Indonesia", "Jawa"
    else:
        # Saat Jawa → Indonesia, ragam tidak relevan
        java_register = None
        source_lang, target_lang = "Jawa", "Indonesia"

    try:
        result = translate_text(text, source_lang, target_lang, java_register=java_register)
    except RuntimeError as exc:
        return error_response(str(exc), 502)

    return jsonify({"result": result})

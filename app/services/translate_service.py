import logging
import os
import json
import time
import hashlib
import functools
import requests

from app.services.dataset_service import extract_glossary

logger = logging.getLogger(__name__)

# Ganti ke gemini-2.5-flash: lebih ringan, limit lebih longgar, lebih murah
GEMINI_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.5-flash:generateContent"
)

# ─── Simple in-memory cache ───────────────────────────────────────────────────
# Menyimpan hasil terjemahan yang sudah pernah dibuat supaya tidak memanggil
# API lagi untuk teks yang sama. Cache hilang saat server restart (by design).
_cache: dict[str, str] = {}


def _cache_key(text: str, source_lang: str, target_lang: str, java_register: str | None = None) -> str:
    raw = f"{source_lang}|{target_lang}|{java_register or ''}|{text}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


# ─── Exponential backoff helper ───────────────────────────────────────────────
def _post_with_retry(url: str, payload: dict, max_retries: int = 3) -> requests.Response:
    """
    Melakukan POST request dengan exponential backoff saat mendapat 429.

    Delays: 5s → 15s → 45s (×3 faktor)
    Jika setelah max_retries masih 429, lempar HTTPError ke caller.
    """
    delay = 5  # detik awal
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(url, json=payload, timeout=30)
        except requests.exceptions.Timeout:
            logger.error("Gemini API timeout setelah 30 detik (attempt %d).", attempt)
            raise RuntimeError("Permintaan ke Gemini API timeout. Coba lagi.")
        except requests.exceptions.RequestException as exc:
            logger.error("Gemini API request error: %s", exc)
            raise RuntimeError(f"Gagal menghubungi Gemini API: {exc}")

        if response.status_code == 429:
            if attempt < max_retries:
                logger.warning(
                    "Gemini 429 – tunggu %ds sebelum retry (attempt %d/%d).",
                    delay, attempt, max_retries,
                )
                time.sleep(delay)
                delay *= 3  # exponential: 5 → 15 → 45
            else:
                logger.error("Gemini 429 – sudah %d kali retry, menyerah.", max_retries)
                response.raise_for_status()
        elif response.status_code >= 400:
            response.raise_for_status()
        else:
            return response

    # Seharusnya tidak sampai sini, tapi untuk keamanan:
    raise RuntimeError("Gagal menghubungi Gemini API setelah beberapa percobaan.")


# ─── Label ragam bahasa Jawa ─────────────────────────────────────────────────
_REGISTER_LABELS: dict[str, str] = {
    "ngoko_lugu":  "Ngoko Lugu (bahasa Jawa sehari-hari, santai, digunakan antara teman sebaya)",
    "ngoko_inggil": "Ngoko Inggil (ngoko dengan beberapa kosakata krama untuk menghormati lawan bicara)",
    "krama_lugu":  "Krama Lugu (bahasa Jawa sopan/madya, digunakan kepada orang yang lebih tua atau dihormati)",
    "krama_inggil": "Krama Inggil (bahasa Jawa paling halus dan formal, digunakan kepada orang yang sangat dihormati)",
}


# ─── Fungsi utama ─────────────────────────────────────────────────────────────
def translate_text(
    text: str,
    source_lang: str,
    target_lang: str,
    java_register: str | None = None,
) -> str:
    """
    Menerjemahkan teks menggunakan Google AI Studio (Gemini API).

    Args:
        text: Teks yang ingin diterjemahkan.
        source_lang: Bahasa sumber, contoh: 'Indonesia' atau 'Jawa'.
        target_lang: Bahasa tujuan, contoh: 'Jawa' atau 'Indonesia'.
        java_register: Ragam bahasa Jawa — hanya relevan saat target_lang='Jawa'.
                       Nilai: 'ngoko_lugu' | 'ngoko_inggil' | 'krama_lugu' | 'krama_inggil'

    Returns:
        Teks hasil terjemahan.

    Raises:
        RuntimeError: Jika API key tidak ditemukan atau permintaan gagal.
    """
    api_key = os.getenv("GOOGLE_AI_API_KEY", "")
    if not api_key:
        raise RuntimeError("GOOGLE_AI_API_KEY belum dikonfigurasi di server.")

    # ── Cek cache dulu sebelum memanggil API ──
    key = _cache_key(text, source_lang, target_lang, java_register)
    if key in _cache:
        logger.info("Cache hit untuk teks: '%s...'", text[:50])
        return _cache[key]

    # ── Ekstrak glosarium dari dataset ──
    glossary = extract_glossary(text, source_lang, java_register if target_lang == "Jawa" else None)
    glossary_text = ""
    if glossary:
        glossary_lines = [f"- {k} = {v}" for k, v in glossary.items()]
        glossary_text = (
            "\n\n[PENTING] Kamu WAJIB menggunakan kamus/glosarium berikut untuk menerjemahkan kata-kata di bawah ini:\n"
            + "\n".join(glossary_lines)
        )
        logger.info(f"Menggunakan {len(glossary)} kata dari dataset kustom.")

    # ── Bangun prompt sesuai ragam bahasa (jika ada) ──
    if target_lang == "Jawa" and java_register and java_register in _REGISTER_LABELS:
        register_desc = _REGISTER_LABELS[java_register]
        prompt = (
            f"Kamu adalah penerjemah ahli bahasa Jawa yang memahami unggah-ungguh (tingkat tutur) bahasa Jawa. "
            f"Terjemahkan teks berikut dari bahasa {source_lang} ke bahasa Jawa ragam {register_desc}. "
            f"Berikan HANYA hasil terjemahan tanpa penjelasan, catatan, atau teks tambahan apapun."
            f"{glossary_text}\n\n"
            f"Teks: {text}"
        )
    else:
        prompt = (
            f"Kamu adalah penerjemah ahli bahasa {source_lang} dan {target_lang}. "
            f"Terjemahkan teks berikut dari bahasa {source_lang} ke bahasa {target_lang}. "
            f"Berikan HANYA hasil terjemahan tanpa penjelasan, catatan, atau teks tambahan apapun."
            f"{glossary_text}\n\n"
            f"Teks: {text}"
        )

    payload = {
        "contents": [
            {
                "parts": [{"text": prompt}]
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 1024,
        },
    }

    logger.info("Mengirim request translate ke Gemini: '%s...'", text[:50])

    try:
        response = _post_with_retry(f"{GEMINI_API_URL}?key={api_key}", payload)
    except requests.exceptions.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "?"
        body = exc.response.text[:300] if exc.response is not None else ""
        logger.error("Gemini API HTTP error %s: %s", status, body)
        if status == 429:
            raise RuntimeError(
                "Kuota Gemini API habis. Tunggu beberapa menit lalu coba lagi."
            )
        raise RuntimeError(f"Gemini API error {status}.")

    try:
        data = response.json()
        logger.debug("Gemini API raw response: %s", json.dumps(data, ensure_ascii=False)[:500])

        candidates = data.get("candidates", [])
        if not candidates:
            # Cek apakah ada promptFeedback (blokir safety filter)
            feedback = data.get("promptFeedback", {})
            block_reason = feedback.get("blockReason", "")
            if block_reason:
                logger.warning("Gemini memblokir request, alasan: %s", block_reason)
                raise RuntimeError(f"Teks diblokir oleh filter keamanan Gemini: {block_reason}.")
            logger.error("Gemini tidak mengembalikan candidates. Response: %s", data)
            raise RuntimeError("Gemini tidak menghasilkan terjemahan. Coba lagi.")

        candidate = candidates[0]
        finish_reason = candidate.get("finishReason", "")
        if finish_reason == "SAFETY":
            logger.warning("Gemini menghentikan generasi karena SAFETY filter.")
            raise RuntimeError("Teks diblokir oleh filter keamanan Gemini.")

        result_text = candidate["content"]["parts"][0]["text"].strip()

        if not result_text:
            logger.warning("Gemini mengembalikan teks kosong.")
            raise RuntimeError("Hasil terjemahan kosong. Coba dengan teks lain.")

        # ── Simpan ke cache ──
        _cache[key] = result_text
        logger.info("Translate berhasil (disimpan ke cache): '%s...'", result_text[:50])
        return result_text

    except (KeyError, IndexError) as exc:
        logger.error("Gagal parse response Gemini: %s | Data: %s", exc, data)
        raise RuntimeError(f"Respons Gemini API tidak valid: {exc}")
    except json.JSONDecodeError as exc:
        logger.error("Response Gemini bukan JSON valid: %s", exc)
        raise RuntimeError("Respons dari Gemini tidak dapat dibaca.")

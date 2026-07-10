import csv
import logging
import os
import string

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET_PATH = os.path.join(BASE_DIR, "data", "dataset.csv")

_dataset: list[dict[str, str]] = []
_is_loaded = False

def load_dataset():
    global _dataset, _is_loaded
    if _is_loaded:
        return
    
    if not os.path.exists(DATASET_PATH):
        logger.warning(f"Dataset file not found at {DATASET_PATH}")
        return
        
    try:
        with open(DATASET_PATH, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            # Headers di file: Ngoko, Krama, Krama Inggil, Bahasa Indonesia
            for row in reader:
                # Bersihkan spasi kosong di header dan value
                cleaned_row = {k.strip(): str(v).strip() for k, v in row.items() if k and v}
                if cleaned_row:
                    _dataset.append(cleaned_row)
        _is_loaded = True
        logger.info(f"Berhasil memuat {len(_dataset)} entri dari dataset CSV.")
    except Exception as e:
        logger.error(f"Gagal memuat dataset: {e}")

def extract_glossary(text: str, source_lang: str, target_register: str | None) -> dict[str, str]:
    """
    Mencari kata-kata dari input text yang ada di dataset.
    Mengembalikan dictionary: { "kata_asli": "terjemahan_sesuai_ragam" }
    """
    load_dataset()
    if not _dataset or not target_register:
        return {}

    # Pemetaan dari target_register ke nama kolom CSV
    if target_register in ("ngoko_lugu", "ngoko_inggil"):
        target_col = "Ngoko"
    elif target_register == "krama_lugu":
        target_col = "Krama"
    elif target_register == "krama_inggil":
        target_col = "Krama Inggil"
    else:
        return {}
        
    source_col = "Bahasa Indonesia" if source_lang == "Indonesia" else "Ngoko"

    # Bersihkan input text dari tanda baca (kecuali strip untuk kata ulang) untuk pencarian presisi
    # Tambahkan spasi di awal dan akhir agar bisa mencari whole word dengan mudah
    chars_to_remove = string.punctuation.replace('-', '')
    translator = str.maketrans('', '', chars_to_remove)
    text_clean = f" {text.lower().translate(translator)} "
    
    glossary = {}
    
    for row in _dataset:
        src_word_raw = row.get(source_col, "")
        tgt_word = row.get(target_col, "")
        
        if not src_word_raw or not tgt_word:
            continue
            
        # Bersihkan kata dari dataset dengan cara yang sama
        src_clean = src_word_raw.lower().translate(translator)
        
        # Cari kata dengan spasi di sekelilingnya (exact whole word match)
        if f" {src_clean} " in text_clean:
            glossary[src_word_raw] = tgt_word

    return glossary

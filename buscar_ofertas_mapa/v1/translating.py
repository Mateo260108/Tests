import json
import os
from deep_translator import GoogleTranslator

UNIVERSAL_TERMS_FILE = "universal_terms.json"
CACHE_FILE = "translation_cache.json"


def _load_json_dict(path):
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_json_dict(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


UNIVERSAL_TERMS = _load_json_dict(UNIVERSAL_TERMS_FILE)
translation_cache = _load_json_dict(CACHE_FILE)


def _normalize_langs(langs):
    if isinstance(langs, str):
        raw = [langs]
    elif isinstance(langs, (list, tuple, set)):
        raw = list(langs)
    else:
        raw = []

    normalized = []
    for item in raw:
        code = str(item or "").strip().lower()
        if code and code not in normalized:
            normalized.append(code)
    return normalized


def get_universal_terms(group_name, langs=None, ordered_keys=None):
    """
    Busca términos en universal_terms.json ('discard_terms' o 'max_priority_terms')
    únicamente para los idiomas indicados en `langs`.
    """
    group_data = UNIVERSAL_TERMS.get(group_name, {})
    if not isinstance(group_data, dict):
        return []

    target_langs = _normalize_langs(langs) or ["en"]
    keys = [str(k).strip().lower() for k in (ordered_keys or []) if str(k).strip()]
    if not keys:
        keys = list(group_data.keys())

    terms = []
    seen = set()

    def _add(val):
        clean = str(val or "").strip().lower()
        if clean and clean not in seen:
            seen.add(clean)
            terms.append(clean)

    for key in keys:
        entry = group_data.get(key)
        if isinstance(entry, dict):
            for lang in target_langs:
                if lang in entry:
                    _add(entry[lang])
        elif key in group_data:
            _add(key)

    return terms


def get_email_terms_for_langs(langs):
    """Devuelve (discard_terms, max_priority_terms) para la lista de idiomas del país."""
    discard = get_universal_terms("discard_terms", langs=langs)
    priority = get_universal_terms("max_priority_terms", langs=langs)
    return discard, priority


def translate_term(term, source_lang, target_lang):
    clean_term = str(term or "").strip().lower()
    src = str(source_lang or "").strip().lower()
    dst = str(target_lang or "").strip().lower()

    if not clean_term or not dst or src == dst:
        return clean_term

    cache_key = f"{src}|{dst}|{clean_term}"
    if cache_key in translation_cache:
        return translation_cache[cache_key]

    try:
        translated = GoogleTranslator(source=src or "auto", target=dst).translate(clean_term)
        result = str(translated or clean_term).strip().lower()
    except Exception:
        result = clean_term

    translation_cache[cache_key] = result
    _save_json_dict(CACHE_FILE, translation_cache)
    return result


def expand_keywords(raw_keywords, input_lang="en", local_langs=None):
    """
    Expande las keywords introducidas por el usuario al idioma de entrada
    y a los idiomas configurados para el territorio (`local_langs`).
    """
    if not raw_keywords:
        return []

    source = str(input_lang or "en").strip().lower() or "en"
    territory_langs = _normalize_langs(local_langs)

    target_langs = []
    for lang in ([source] + territory_langs):
        if lang and lang not in target_langs:
            target_langs.append(lang)

    expanded = []
    seen = set()

    def _add(val):
        clean = str(val or "").strip().lower()
        if clean and clean not in seen:
            seen.add(clean)
            expanded.append(clean)

    for raw_kw in raw_keywords:
        term = str(raw_kw or "").strip().lower()
        if not term:
            continue

        _add(term)
        for lang in target_langs:
            if lang == source:
                continue
            tr = translate_term(term, source, lang)
            _add(tr)

    return expanded
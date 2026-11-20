from deep_translator import GoogleTranslator

translation_cache = {}
def translate_term(term, source_lang, target_lang):
    clean_term = term.strip().lower()
    if not clean_term or not source_lang or not target_lang or source_lang == target_lang:
        return clean_term

    cache_key = (clean_term, source_lang, target_lang)
    if cache_key in translation_cache:
        return translation_cache[cache_key]

    try:
        translated = GoogleTranslator(source=source_lang, target=target_lang).translate(clean_term)
        result = (translated or clean_term).strip().lower()
    except Exception:
        result = clean_term

    translation_cache[cache_key] = result
    return result

def translate_from_en(term, target_lang):
    return translate_term(term, "en", target_lang)

def build_lang_terms(terms_en, local_lang):
    combined = []
    seen = set()

    for term in terms_en:
        base = term.strip().lower()
        if base and base not in seen:
            seen.add(base)
            combined.append(base)

        if local_lang and local_lang != "en":
            translated = translate_from_en(base, local_lang)
            if translated and translated not in seen:
                seen.add(translated)
                combined.append(translated)

    return combined

def expand_keywords(raw_keywords, input_lang="en", local_lang="en"):
    if not raw_keywords:
        return []

    source = (input_lang or "en").strip().lower()
    target_langs = []
    for lang in (source, "en", (local_lang or "").strip().lower()):
        if lang and lang not in target_langs:
            target_langs.append(lang)

    expanded = []
    seen = set()

    for keyword in raw_keywords:
        term = keyword.strip().lower()
        if not term:
            continue

        if term not in seen:
            seen.add(term)
            expanded.append(term)

        for lang in target_langs:
            if lang == source:
                continue
            tr = translate_term(term, source, lang)
            if tr and tr not in seen:
                seen.add(tr)
                expanded.append(tr)

    return expanded

        

        
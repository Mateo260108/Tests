from deep_translator import GoogleTranslator

translation_cache = {}
def translate_from_en(term, target_lang):
    clean_term = term.strip().lower()
    if not clean_term or target_lang=="en":
        return clean_term

    cache_key = (clean_term, target_lang)
    if cache_key in translation_cache:
        return translation_cache[cache_key]

    try:
        translated = GoogleTranslator(source="en", target=target_lang).translate(clean_term)
        result = (translated or clean_term).strip().lower()
    except Exception:
        result = clean_term

    translation_cache[cache_key] = result
    return result

def build_lang_terms(terms_en, local_lang):
    print("Translating terms...")
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

    print("Finished translating terms.")
    return combined
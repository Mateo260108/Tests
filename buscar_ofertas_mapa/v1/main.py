import time
from dotenv import load_dotenv
load_dotenv()

from utils import (
    email_terms_translated, expand_keywords,
    separate_unique_and_chains, save_chains_to_json,
    lambda_km
)
from core import (
    data,
    scrape_and_merge,
    order_by_relevance_and_proximity, filtering_output, save_to_csv
)

default_tokens = ["1", "2"]

token_to_fields = {
    "1": ["name"],
    "2": ["category"],
    "3": ["web"],
    "4": ["email"],
    "5": ["phone"],
    "6a": ["instagram"],
    "6b": ["facebook"],
    "6c": ["linkedin"],
    "7": ["lat", "lon"],
    "8a": ["score_s"],
    "8b": ["score_s"],
}

def parse_column_selection(raw_input):
    selected_tokens = list(default_tokens)
    use_proximity = False
    mode = "rural"

    tokens = [t.strip().lower() for t in (raw_input or "").split(",") if t.strip()]
    for token in tokens:
        if token.endswith("x"):
            base = token[:-1]
            if base in selected_tokens:
                selected_tokens.remove(base)
            if base in ("8a", "8b"):
                use_proximity = False
        elif token in token_to_fields:
            if token == "8a":
                selected_tokens = [t for t in selected_tokens if t != "8b"]
                use_proximity = True
                mode = "rural"
            elif token == "8b":
                selected_tokens = [t for t in selected_tokens if t != "8a"]
                use_proximity = True
                mode = "urban"

            if token not in selected_tokens:
                selected_tokens.append(token)

    columns = []
    for token in selected_tokens:
        for field in token_to_fields[token]:
            if field not in columns:
                columns.append(field)

    return columns, use_proximity, mode


if __name__ == "__main__":
    total_start = time.perf_counter()
    timings = {}

    # 1. Idioma de input + territorio fijado
    t0 = time.perf_counter()
    input_lang = input("Input language code (e.g. es, en, is) [default: en]: ").strip().lower() or "en"

    country_name = "Switzerland"
    country_info = data["countries"][country_name]
    iso = country_info["iso"]
    local_langs = [str(l).strip().lower() for l in country_info.get("lang", ["en"]) if str(l).strip()]
    phone_prefix = str(country_info.get("prefix") or "").strip()

    discard_terms, priority_terms = email_terms_translated(langs=local_langs)
    timings["resolve_country_and_email_terms"] = time.perf_counter() - t0
    print(f"Input lang: {input_lang} | Fixed country: {country_name} ({iso}) | Local langs: {local_langs}")
    print(f"Loaded {len(discard_terms)} discard terms and {len(priority_terms)} priority terms.")

    # 2. Keywords del usuario. Buenas y malas
    raw_keywords_input = input("Priority keywords (comma-separated, leave empty for none): ").strip()
    raw_negative_keywords_input = input("Negative / irrelevant keywords (comma-separated, leave empty for none): ").strip()

    user_keywords = []
    negative_keywords = []

    if raw_keywords_input or raw_negative_keywords_input:
        t0 = time.perf_counter()
        if raw_keywords_input:
            user_keywords = expand_keywords(
                raw_keywords_input.split(","),
                input_lang=input_lang,
                local_langs=local_langs,
            )
        if raw_negative_keywords_input:
            negative_keywords = expand_keywords(
                raw_negative_keywords_input.split(","),
                input_lang=input_lang,
                local_langs=local_langs,
            )
        timings["translate_keywords"] = time.perf_counter() - t0

    has_keyword_filter = bool(user_keywords or negative_keywords)

    # 3. Columnas de output y filtro rural/urbano 
    print(
        "\nSelect the output rows:\n"
        "---\n"
        "1. name (by default, 1x if not wanted)\n"
        "2. type (by default, 2x if not wanted)\n"
        "3. web\n"
        "4. email\n"
        "5. phone number\n"
        "6. social media:\n"
        "|--- 6a. Instagram link\n"
        "|--- 6b. Facebook link\n"
        "|--- 6c. Linkedin link\n"
        "7. coordinates\n"
        "8. proximity filter (score_s):\n"
        "|--- 8a. Rural mode\n"
        "|--- 8b. Urban mode\n"
        "---"
    )
    raw_cols = input("(if you want more than one, separate the numbers with commas. e.g. 2x, 3, 6a, 8a): ")
    selected_columns, use_proximity, mode = parse_column_selection(raw_cols)
    if has_keyword_filter and "relevance" not in selected_columns:
        selected_columns.append("relevance")

    need_socials = any(col in selected_columns for col in ("instagram", "facebook", "linkedin"))

    # 4. Extracción Overpass + scraping + merge
    t0 = time.perf_counter()
    final_places, all_places = scrape_and_merge(
        iso,
        relevant_keywords=user_keywords,
        irrelevant_keywords=negative_keywords,
        local_langs=local_langs,
        phone_prefix=phone_prefix,
        max_workers=64
    )
    timings["scrape_and_merge"] = time.perf_counter() - t0

    # 5. Ordenar por vecinos y relevancia 
    t0 = time.perf_counter()
    final_places = order_by_relevance_and_proximity(
        final_places,
        all_places,
        use_proximity=use_proximity,
        mode=mode,
        decay_km=lambda_km,
    )
    timings["proximity_order"] = time.perf_counter() - t0

    export_chains = input("Export chains to a separate JSON file? (y/n): ").strip().lower() == "y"

    unique_places, chains_payload = separate_unique_and_chains(
        final_places,
        selected_columns=selected_columns,
        local_langs=local_langs,
    )

    if export_chains:
        save_chains_to_json(chains_payload, output_path=f"output/chains_{iso}.json")

    # 6. Filtrar vacíos y guardar en CSV (solo sitios únicos)
    empty_ans = input("Show results with empty selected columns? (y/n): ").strip().lower()
    allow_empty = empty_ans != "n"

    t0 = time.perf_counter()
    exported_rows = filtering_output(unique_places, selected_columns, allow_empty=allow_empty)
    save_to_csv(exported_rows, output_path=f"output/email_list_{iso}.csv")
    timings["save_csv"] = time.perf_counter() - t0

    # Conteo final
    total_elapsed = time.perf_counter() - total_start

    print("\n--- Runtime breakdown ---")
    for phase, elapsed in timings.items():
        pct = (elapsed / total_elapsed * 100) if total_elapsed > 0 else 0
        print(f"{phase}: {elapsed:.2f}s ({pct:.1f}%)")
    print(f"Total runtime: {total_elapsed:.2f}s")
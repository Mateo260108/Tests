import csv
import json
import time
from dotenv import load_dotenv
load_dotenv()

from translating import expand_keywords
from filter_and_merge import email_lists, scrape_and_merge
from neighbours import order_by_relevance_and_proximity, lambda_km

with open("config.json", "r", encoding="utf-8") as file:
    config = json.load(file)

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
    "8": ["score_s"],
}


def select_country(countries_dict):
    country_names = list(countries_dict.keys())
    print("Available countries:")
    for idx, name in enumerate(country_names, 1):
        info = countries_dict[name]
        langs_str = ", ".join(info.get("lang", []))
        print(f"  {idx}. {name} ({info.get('iso', '')}) [{langs_str}]")

    raw_choice = input("Select country by number or name (default Iceland): ").strip()
    if not raw_choice:
        chosen_name = "Iceland" if "Iceland" in countries_dict else country_names[0]
    elif raw_choice.isdigit():
        idx = int(raw_choice) - 1
        chosen_name = country_names[idx] if 0 <= idx < len(country_names) else country_names[0]
    else:
        matched = next((n for n in country_names if n.lower() == raw_choice.lower()), None)
        chosen_name = matched or country_names[0]

    info = countries_dict[chosen_name]
    langs = info.get("lang", ["en"])
    if isinstance(langs, str):
        langs = [langs]
    langs = [str(l).strip().lower() for l in langs if str(l).strip()]
    return chosen_name, info["iso"], langs


def parse_column_selection(raw_input):
    selected_tokens = list(default_tokens)
    tokens = [t.strip().lower() for t in (raw_input or "").split(",") if t.strip()]
    for token in tokens:
        if token.endswith("x"):
            base = token[:-1]
            if base in selected_tokens:
                selected_tokens.remove(base)
        elif token in token_to_fields and token not in selected_tokens:
            selected_tokens.append(token)

    columns = []
    for token in selected_tokens:
        for field in token_to_fields[token]:
            if field not in columns:
                columns.append(field)

    return columns


def filtering_output(rows, columns, allow_empty=True):
    if not rows or not columns:
        return []

    output = []
    for row in rows:
        if not allow_empty:
            has_all = all(str(row.get(col) or "").strip() != "" for col in columns)
            if not has_all:
                continue

        projected = {col: row.get(col, "") for col in columns}
        output.append(projected)

    return output


def save_to_csv(rows, output_path="email_list.csv"):
    print("Saving to CSV format file...")
    if not rows:
        print("No data to save.")
        return

    fieldnames = list(rows[0].keys())
    with open(output_path, "w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)

    print(f"Saved {len(rows)} rows to {output_path}")


if __name__ == "__main__":
    total_start = time.perf_counter()
    timings = {}

    # 1. Primer input: selección de país e idiomas del territorio
    t0 = time.perf_counter()
    country_name, iso, local_langs = select_country(config["countries"])
    discard_terms, priority_terms = email_lists(local_langs=local_langs)
    timings["resolve_country_and_email_terms"] = time.perf_counter() - t0
    print(f"Country: {country_name} | ISO: {iso} | Langs: {local_langs}")
    print(f"Loaded {len(discard_terms)} discard terms and {len(priority_terms)} priority terms.")

    # 2. Keywords del usuario
    raw_keywords_input = input("Priority keywords (comma-separated, leave empty for none): ").strip()
    user_keywords = []
    if raw_keywords_input:
        default_input_lang = local_langs[0] if local_langs else "en"
        input_lang = input(f"Keywords language code (default {default_input_lang}): ").strip().lower() or default_input_lang
        t0 = time.perf_counter()
        user_keywords = expand_keywords(
            raw_keywords_input.split(","),
            input_lang=input_lang,
            local_langs=local_langs,
        )
        timings["translate_keywords"] = time.perf_counter() - t0

    # 3. Columnas de output
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
        "8. score_s\n"
        "---"
    )
    raw_cols = input("(if you want more than one, separate the numbers with commas. e.g. 2x, 3, 6a, 7): ")
    selected_columns = parse_column_selection(raw_cols)
    need_socials = any(col in selected_columns for col in ("instagram", "facebook", "linkedin"))

    # 4. Extracción Overpass + scraping + merge
    t0 = time.perf_counter()
    final_places, all_places = scrape_and_merge(
        iso,
        relevant_keywords=user_keywords,
        need_socials=need_socials,
        local_langs=local_langs,
    )
    timings["scrape_and_merge"] = time.perf_counter() - t0

    # 5. Ordenar por vecinos y relevancia
    use_function = input("Apply rural/urban filtering to the data? (y/n): ").strip().lower()
    use_proximity = use_function == "y"
    mode = "rural"
    if use_proximity:
        mode_input = input("(Modes: 'u' for urban, 'r' for rural) [answer]: ").strip().lower()
        mode = "urban" if mode_input == "u" else "rural"

    t0 = time.perf_counter()
    final_places = order_by_relevance_and_proximity(
        final_places,
        all_places,
        use_proximity=use_proximity,
        mode=mode,
        decay_km=lambda_km,
    )
    timings["proximity_order"] = time.perf_counter() - t0

    # 6. Filtrar vacíos y guardar en CSV
    empty_ans = input("Show results with empty selected columns? (y/n): ").strip().lower()
    allow_empty = empty_ans != "n"

    t0 = time.perf_counter()
    exported_rows = filtering_output(final_places, selected_columns, allow_empty=allow_empty)
    save_to_csv(exported_rows, output_path=f"email_list_{iso}.csv")
    timings["save_csv"] = time.perf_counter() - t0

    # Conteo final
    total_elapsed = time.perf_counter() - total_start

    print("\n--- Runtime breakdown ---")
    for phase, elapsed in timings.items():
        pct = (elapsed / total_elapsed * 100) if total_elapsed > 0 else 0
        print(f"{phase}: {elapsed:.2f}s ({pct:.1f}%)")
    print(f"Total runtime: {total_elapsed:.2f}s")
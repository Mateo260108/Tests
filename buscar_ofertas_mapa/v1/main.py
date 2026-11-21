import csv
import json
import time
from dotenv import load_dotenv
load_dotenv()

from translating import expand_keywords
from overpass_pull import pull_list_from_api
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
}

def parse_column_selection(raw_input):
    selected_tokens = list(default_tokens)
    tokens = [t.strip() for t in (raw_input or "").split(",") if t.strip()]
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
    iso = config["countries"]["Norway"]["iso"]
    local_lang = config["countries"]["Norway"]["lang"]
    
    raw_keywords_input = input("Priority keywords (comma-separated, leave empty for none): ")
    user_keywords = []

    # 1. Traducción de keywords
    if raw_keywords_input:
        input_lang = input("Keywords language code (e.g. es, en, is): ").strip().lower() or "en"
        t0 = time.perf_counter()
        user_keywords = expand_keywords(
            raw_keywords_input.split(","),
            input_lang=input_lang,
            local_lang=local_lang,
        )
        timings["translate_keywords"] = time.perf_counter() - t0

    # 2. Traducción de keywords para emails
    t0 = time.perf_counter()
    email_lists()
    timings["translate_email_keywords"] = time.perf_counter() - t0

    # 3. Pedir columnas de output
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
            "---"
        )
    raw_cols = input("(if you want more than one, separate the numbers with commas. e.g. 2x, 3, 6a, 7): ")
    selected_columns = parse_column_selection(raw_cols)
    need_socials = any(col in selected_columns for col in ("instagram", "facebook", "linkedin"))

    # 4. Extracción Overpass + scraping + merge
    t0 = time.perf_counter()
    final_places, all_places = scrape_and_merge(iso, relevant_keywords=user_keywords, need_socials=need_socials)
    timings["scrape_and_merge"] = time.perf_counter() - t0

    # 5. Ordenar por vecinos y relevancia
    use_function = input("Apply rural/urban filtering to the data? (y/n)").strip().lower()
    use_proximity = use_function == "y"
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

    # 6. Guardar en CSV
    empty_ans = input("Show results with empty selected columns? (y/n): ").strip().lower()
    allow_empty = empty_ans != "n"

    t0 = time.perf_counter()
    exported_rows = filtering_output(final_places, selected_columns, allow_empty=allow_empty)
    save_to_csv(exported_rows, output_path=f"email_list_{iso}.csv")
    timings["save_csv"] = time.perf_counter() - t0

    #Conteo final
    total_elapsed = time.perf_counter() - total_start

    print("\n--- Runtime breakdown ---")
    for phase, elapsed in timings.items():
        pct = (elapsed / total_elapsed * 100) if total_elapsed > 0 else 0
        print(f"{phase}: {elapsed:.2f}s ({pct:.1f}%)")
    print(f"Total runtime: {total_elapsed:.2f}s")


    


        
            







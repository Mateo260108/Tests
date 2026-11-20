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
    iso = "IS"
    local_lang = config["countries"]["Iceland"]["lang"]
    
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
    timings["translate_mail_keywords"] = time.perf_counter() - t0

    # 3. Extracción Overpass + scraping + merge
    t0 = time.perf_counter()
    final_places, all_places = scrape_and_merge(iso, relevant_keywords=user_keywords)
    timings["scrape_and_merge"] = time.perf_counter() - t0

    # 4. Ordenar por vecinos y relevancia
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
            mode="rural",
            decay_km=lambda_km,
        )
        timings["proximity_order"] = time.perf_counter() - t0

    # 5. Guardar en CSV
    t0 = time.perf_counter()
    save_to_csv(final_places, output_path=f"email_list_{iso}.csv")
    timings["save_csv"] = time.perf_counter() - t0

    #Conteo final
    total_elapsed = time.perf_counter() - total_start

    print("\n--- Runtime breakdown ---")
    for phase, elapsed in timings.items():
        pct = (elapsed / total_elapsed * 100) if total_elapsed > 0 else 0
        print(f"{phase}: {elapsed:.2f}s ({pct:.1f}%)")
    print(f"Total runtime: {total_elapsed:.2f}s")


    


        
            







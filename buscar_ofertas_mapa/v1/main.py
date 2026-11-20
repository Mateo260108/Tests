import csv
import time
from dotenv import load_dotenv
load_dotenv()

from translating import build_lang_terms
from overpass_pull import pull_list_from_api
from filter_and_merge import email_lists, scrape_and_merge
from neighbours import apply_proximity_order, lambda_km

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

    # 1. Traducción 
    t0 = time.perf_counter()
    email_lists()
    timings["translation_init"] = time.perf_counter() - t0

    # 2. Extracción Overpass + scraping + merge
    t0 = time.perf_counter()
    final_places, all_places = scrape_and_merge(iso)
    timings["scrape_and_merge"] = time.perf_counter() - t0

    # 3. Ordenar por vecinos
    use_function = input("Apply rural/urban filtering to the data? (y/n)").strip().lower()
    if use_function == "y":
        mode_input = input("(Modes: 'u' for urban, 'r' for rural) [answer]: ").strip().lower()
        mode = "urban" if mode_input == "u" else "rural"

        t0 = time.perf_counter()
        final_places = apply_proximity_order(final_places, all_places, mode, decay_km=lambda_km)
        timings["proximity_order"] = time.perf_counter() - t0

    # 4. Guardar en CSV
    t0 = time.perf_counter()
    save_to_csv(final_places, output_path=f"email_list_{iso}.csv")
    timings["save_csv"] = time.perf_counter() - t0

    total_elapsed = time.perf_counter() - total_start

    print("\n--- Runtime breakdown ---")
    for phase, elapsed in timings.items():
        pct = (elapsed / total_elapsed * 100) if total_elapsed > 0 else 0
        print(f"{phase}: {elapsed:.2f}s ({pct:.1f}%)")
    print(f"Total runtime: {total_elapsed:.2f}s")


    


        
            







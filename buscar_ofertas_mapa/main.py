import time
from overpass_extractor import search_hotels, countries
from filter_results import filter_lines, save_to_csv


if __name__ == "__main__":
    for country in countries:
        print(f"Searching hotels in {country}...")
        search_hotels(countries[country])

        print("Moving to filtering.")
        country_raw = f"hotels_{countries[country]}.csv"
        print(f"Filtering {country_raw}...")
        categories = filter_lines(country_raw, countries[country])  

        save_to_csv(f"email_list_{countries[country]}.csv", categories[0], countries[country])
        save_to_csv(f"web_list_{countries[country]}.csv", categories[1], countries[country])
        save_to_csv(f"nothing_list_{countries[country]}.csv", categories[2], countries[country])
        time.sleep(10)
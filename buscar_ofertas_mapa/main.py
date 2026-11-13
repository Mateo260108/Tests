import time
from overpass_extractor import search_hotels, countries
from filter_results import filter_lines, save_to_csv
from web_and_mail_search import process_webs_by_country


if __name__ == "__main__":
    for country in countries:
        iso_code = countries[country]
        print(f"Searching hotels in {country}...")
        search_hotels(iso_code)

        print("Moving to filtering.")
        country_raw = f"hotels_{iso_code}.csv"
        print(f"Filtering {country_raw}...")
        categories = filter_lines(country_raw, iso_code)  

        save_to_csv(f"email_list_{iso_code}.csv", categories[0], iso_code)
        save_to_csv(f"web_list_{iso_code}.csv", categories[1], iso_code)
        save_to_csv(f"nothing_list_{iso_code}.csv", categories[2], iso_code)

        process_webs_by_country(iso_code)
        time.sleep(10)
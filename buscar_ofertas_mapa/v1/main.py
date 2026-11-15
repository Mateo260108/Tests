import time
from overpass_extractor import search_hotels, countries
from filter_results import filter_lines, save_to_csv
from web_and_mail_search import process_webs_by_country
from merge_emails import final_email_list
from rural_filtering import processing_filter


if __name__ == "__main__":
    for country in countries:
        iso_code = countries[country]
        print(f"Searching hotels in {country}...")
        search_hotels(iso_code)

        country_raw = f"hotels_{iso_code}.csv"
        categories = filter_lines(country_raw)  

        save_to_csv(f"email_list_{iso_code}.csv", categories[0], iso_code)
        save_to_csv(f"web_list_{iso_code}.csv", categories[1], iso_code)

        process_webs_by_country(iso_code)
        final_email_list(iso_code)

        processing_filter(iso_code)
        print(f"{country} donde. Moving on to the next one...")
        time.sleep(5)

    print("Done!")
        
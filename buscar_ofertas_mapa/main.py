import time
from overpass_extractor import search_hotels

if __name__ == "__main__":
    countries = ["IS", "NO", "SE", "FI", "DK", "EE", "LV", "LT", "CH"]
    for country in countries:
        print(f"Searching hotels in {country}...")
        search_hotels(country)
        time.sleep(1)  
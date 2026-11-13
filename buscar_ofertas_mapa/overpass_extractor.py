import requests
import time
import os
from dotenv import load_dotenv

load_dotenv()
contact_email = os.getenv("USER_EMAIL", "generic_user@example.com")

countries = {"Iceland": "IS", "Norway": "NO", "Sweden": "SE", "Finland": "FI", "Denmark": "DK",
             "Estonia": "EE", "Latvia": "LV", "Lithuania": "LT", "Switzerland": "CH"}

def search_hotels(iso_code:str):
    url = "https://overpass-api.de/api/interpreter"
    query = f"""[out:csv(::id,::type,"name", ::lat, ::lon,"tourism","contact:website","website","email","contact:email")];
    area["ISO3166-1"="{iso_code}"][admin_level=2]->.searchArea;
    (
    nwr(area.searchArea)["tourism"="hostel"];
    nwr(area.searchArea)["tourism"="hotel"];
    nwr(area.searchArea)["tourism"="guest_house"];
    );
    out;"""

    headers = {
        'User-Agent': 'BuscadorHoteles/1.0 ({contact_email})'
    }

    tries = 0
    while tries < 5:
        try:
            response = requests.post(url, data={'data': query}, headers=headers)
            if response.status_code == 200:
                print("Request successful!")

                with open(f'hotels_{iso_code}.csv', 'w', encoding="utf-8") as file:
                    file.write(response.text)
                break

            elif response.status_code in [429, 502, 503, 504]:
                print(f"Request failed with status code {response.status_code}. Retrying in 30 seconds...")
                time.sleep(30)
                tries += 1

            else:
                print(f"Request failed with status code {response.status_code}. No retry.")
                break

        except requests.exceptions.RequestException as e:
            print(f"Request failed with exception: {e}. Retrying in 30 seconds...")
            time.sleep(30)
            tries += 1

    if tries == 3:
        print(f"Failed to retrieve data for {iso_code} after 3 attempts.")
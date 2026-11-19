import csv
import json
import os
import random
import re
import time
from dotenv import load_dotenv
import requests

load_dotenv()
contact_email = os.getenv("USER_EMAIL", "generic_user@example.com")

with open("config.json", "r", encoding="utf-8") as file:
    config = json.load(file)

false_ends = tuple(x.lower() for x in config.get("false_ends", []))
headers_web = config.get("HEADERS", {"User-Agent": "Mozilla/5.0"})
email_max_priority = [x.lower() for x in config.get("max_priority", [])]
email_discard_terms = tuple(x.lower() for x in config.get("discard_terms", []))

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")


def pull_list_from_api(iso_code):
    url = "https://overpass-api.de/api/interpreter"
    query = f"""
    [out:json][timeout:60];
    area["ISO3166-1"="{iso_code.upper()}"][admin_level=2]->.searchArea;
    (
      nwr(area.searchArea)["tourism"="hostel"];
      nwr(area.searchArea)["tourism"="hotel"];
      nwr(area.searchArea)["tourism"="guest_house"];
    );
    out center;
    """
    headers = {
        "User-Agent": f"BuscadorHoteles/1.1 ({contact_email})"
    }

    for tries in range(5):
        try:
            response = requests.post(url, data={"data": query}, headers=headers, timeout=65)
            if response.status_code == 200:
                print("Request completed successfully. Pulling data...")
                elements = response.json().get("elements", [])
                results = []

                for el in elements:
                    tags = el.get("tags", {})
                    center = el.get("center", {})
                    lat = el.get("lat") if el.get("lat") is not None else center.get("lat", "")
                    lon = el.get("lon") if el.get("lon") is not None else center.get("lon", "")

                    results.append({
                        "id": f"{el.get('type', '')}/{el.get('id', '')}",
                        "name": tags.get("name", ""),
                        "lat": lat,
                        "lon": lon,
                        "category": tags.get("tourism", ""),
                        "web": tags.get("contact:website") or tags.get("website") or "",
                        "email": tags.get("contact:email") or tags.get("email") or "",
                        "phone": tags.get("contact:phone") or tags.get("phone") or "",
                    })
                return results

            if response.status_code in (429, 502, 503, 504):
                wait_time = 30 + (tries * 10)
                print(f"Status {response.status_code}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"Request failed with status code {response.status_code}. No retry.")
                break

        except (requests.exceptions.RequestException, ValueError) as e:
            wait_time = 30 + (tries * 10)
            print(f"Request error ({e}). Retrying in {wait_time}s...")
            time.sleep(wait_time)

    print("Server was too busy or failed after retries.")
    return []


def filter_results(all_places):
    web_included = []
    email_included = []
    phone_included = []

    for place in all_places:
        web = (place.get("web") or "").strip()
        email = (place.get("email") or "").strip()
        phone = (place.get("phone") or "").strip()

        if web:
            web_included.append(place)
        if email:
            email_included.append(place)
        if phone:
            phone_included.append(place)

    return web_included, email_included, phone_included


def choose_email(candidates):
    for prefix in email_max_priority:
        for email in candidates:
            local_part = email.split("@", 1)[0]
            if local_part == prefix or local_part.startswith(prefix):
                return email
    return candidates[0]


def scrape_and_merge(iso_code):
    all_places = pull_list_from_api(iso_code)
    if not all_places:
        return []

    webs, clean_emails, _ = filter_results(all_places)
    scraped_list = []

    for i, place in enumerate(webs, 1):
        url = (place.get("web") or "").strip()
        if url and not url.startswith(("http://", "https://")):
            url = "https://" + url

        name = (place.get("name") or "").strip()
        print(f"[{i}/{len(webs)}] {name} -> {url} ...", end=" ")

        try:
            resp = requests.get(url, headers=headers_web, timeout=15)
        except requests.exceptions.RequestException as e:
            print(f"Error ({e})")
            continue

        if resp.status_code != 200:
            print(f"HTTP {resp.status_code}")
            continue

        raw_matches = {m.lower() for m in EMAIL_REGEX.findall(resp.text)}
        filtered_ends = [
            e for e in raw_matches
            if not e.endswith(false_ends) and not any(f in e for f in false_ends)
        ]
        valid = [e for e in filtered_ends if not e.startswith(email_discard_terms)]

        if not valid:
            print("No valid emails found")
            continue

        place_copy = dict(place)
        place_copy["email"] = choose_email(valid)
        scraped_list.append(place_copy)
        print(f"OK -> {place_copy['email']}")
        time.sleep(random.uniform(0.5, 1.5))

    seen_emails = set()
    seen_ids = set()
    finals = []

    for place in (clean_emails + scraped_list):
        place_id = (place.get("id") or "").strip()
        best_email = (place.get("email") or "").strip().lower()

        if place_id and place_id in seen_ids:
            continue
        if best_email and best_email in seen_emails:
            continue

        if place_id:
            seen_ids.add(place_id)
        if best_email:
            seen_emails.add(best_email)

        finals.append(place)

    return finals


def save_to_csv(iso_code, output_path="email_list.csv"):
    list_to_save = scrape_and_merge(iso_code)
    if not list_to_save:
        print("No data to save.")
        return

    fieldnames = list(list_to_save[0].keys())
    with open(output_path, "w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(list_to_save)

    print(f"Saved {len(list_to_save)} rows to {output_path}")

if __name__ == "__main__":
    save_to_csv("IS")


        
            







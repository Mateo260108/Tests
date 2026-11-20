import random
import requests
import time
import json
import re

from translating import build_lang_terms
from overpass_pull import pull_list_from_api


with open("config.json", "r", encoding="utf-8") as file:
    config = json.load(file)

country_info = config["countries"]["Iceland"]
local_lang = country_info["lang"]

def email_lists():
    email_discard_terms = tuple(build_lang_terms(config["discard_terms_EN"], local_lang))
    email_max_priority = build_lang_terms(config["max_priority_EN"], local_lang)
    return email_discard_terms, email_max_priority

false_ends = tuple(x.lower() for x in config.get("false_ends", []))
headers_web = config.get("HEADERS", {"User-Agent": "Mozilla/5.0"})

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

def has_relevant_match(html_text, keywords):
    if not html_text:
        return False
    text_lower = html_text.lower()
    return any(keyword in text_lower for keyword in keywords)

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
    _ , max_priority = email_lists()
    for prefix in max_priority:
        for email in candidates:
            local_part = email.split("@", 1)[0]
            if local_part == prefix or local_part.startswith(prefix):
                return email
    return candidates[0]


def scrape_and_merge(iso_code, relevant_keywords=None):
    keyword_list = [k.strip().lower() for k in (relevant_keywords or []) if k and k.strip()]
    discard_terms, _ = email_lists()
    all_places = pull_list_from_api(iso_code)
    if not all_places:
        return [], []

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
        valid = [e for e in filtered_ends if not e.startswith(discard_terms)]

        if not valid:
            print("No valid emails found")
            continue

        place_copy = dict(place)
        place_copy["email"] = choose_email(valid)
        place_copy["relevance"] = "relevant" if has_relevant_match(resp.text, keyword_list) else "regular"
        scraped_list.append(place_copy)
        print(f"OK -> {place_copy['email']} [{place_copy['relevance']}]")
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

        item = dict(place)
        item.setdefault("relevance", "regular")
        finals.append(item)

    return finals, all_places
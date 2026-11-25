import json
import random
import re
import time
import requests
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter

from translating import get_email_terms_for_langs
from overpass_pull import pull_list_from_api

print_lock = threading.Lock()

with open("config.json", "r", encoding="utf-8") as file:
    config = json.load(file)

default_country = config["countries"].get("Iceland", next(iter(config["countries"].values())))
DEFAULT_LOCAL_LANGS = list(default_country.get("lang", ["en"]))

false_ends = tuple(str(x).lower() for x in config.get("false_ends", []))
headers_web = config.get("HEADERS", {"User-Agent": "Mozilla/5.0"})

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_REGEX = re.compile(r"(?:\+?\d[\d\s().-]{6,}\d)")
INSTAGRAM_REGEX = re.compile(r"https?://(?:www\.)?instagram\.com/[A-Za-z0-9._-]+/?", re.IGNORECASE)
FACEBOOK_REGEX = re.compile(r"https?://(?:www\.|m\.)?facebook\.com/[A-Za-z0-9._-]+/?", re.IGNORECASE)
LINKEDIN_REGEX = re.compile(r"https?://(?:[a-z]{2,3}\.)?linkedin\.com/(?:company|in)/[A-Za-z0-9._-]+/?", re.IGNORECASE)

def _build_session(pool_size=64):
    session = requests.Session()
    adapter = HTTPAdapter(pool_connections=pool_size, pool_maxsize=pool_size)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update(headers_web)
    return session

def email_lists(local_langs=None):
    langs = local_langs if local_langs else DEFAULT_LOCAL_LANGS
    discard_terms, max_priority = get_email_terms_for_langs(langs)
    return tuple(discard_terms), max_priority


def has_relevant_match(html_text, keywords):
    if not html_text:
        return False
    text_lower = html_text.lower()
    return any(keyword in text_lower for keyword in keywords)


def filter_results(all_places, need_socials=False):
    web_included = []
    email_included = []
    phone_included = []
    to_scrape = []
    already_with_contact = []

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

        has_contact = bool(email or phone)
        if web and (not has_contact or need_socials):
            to_scrape.append(place)
        elif has_contact:
            already_with_contact.append(place)

    return {
        "web_included": web_included,
        "email_included": email_included,
        "phone_included": phone_included,
        "to_scrape": to_scrape,
        "already_with_contact": already_with_contact,
    }


def extract_phone_number(html_text):
    if not html_text:
        return ""
    for match in PHONE_REGEX.findall(html_text):
        cleaned = re.sub(r"[^\d+]", "", match)
        digits = re.sub(r"\D", "", cleaned)
        if 7 <= len(digits) <= 15:
            return cleaned
    return ""


def extract_social_links(html_text):
    if not html_text:
        return {"instagram": "", "facebook": "", "linkedin": ""}

    ig_matches = INSTAGRAM_REGEX.findall(html_text)
    fb_matches = FACEBOOK_REGEX.findall(html_text)
    li_matches = LINKEDIN_REGEX.findall(html_text)

    ig = next((u for u in ig_matches if "/p/" not in u and "/reel/" not in u), ig_matches[0] if ig_matches else "")
    fb = next((u for u in fb_matches if "/sharer" not in u), fb_matches[0] if fb_matches else "")
    li = li_matches[0] if li_matches else ""

    return {"instagram": ig, "facebook": fb, "linkedin": li}


def choose_email(candidates, local_langs=None):
    _, max_priority = email_lists(local_langs=local_langs)
    for prefix in max_priority:
        for email in candidates:
            local_part = email.split("@", 1)[0]
            if local_part == prefix or local_part.startswith(prefix):
                return email
    return candidates[0]

def _scrape_single_place(session, place, idx, total, discard_terms, keyword_list, local_langs):
    url = (place.get("web") or "").strip()
    if url and not url.startswith(("http://", "https://")):
        url = "https://" + url

    name = (place.get("name") or "").strip()

    try:
        resp = session.get(url, timeout=12)
    except requests.exceptions.RequestException as e:
        with print_lock:
            print(f"[{idx}/{total}] {name} -> {url} ... Error ({e})")
        return None

    if resp.status_code != 200:
        with print_lock:
            print(f"[{idx}/{total}] {name} -> {url} ... HTTP {resp.status_code}")
        return None

    had_contact = bool((place.get("email") or "").strip() or (place.get("phone") or "").strip())

    raw_matches = {m.lower() for m in EMAIL_REGEX.findall(resp.text)}
    filtered_ends = [
        e for e in raw_matches
        if not e.endswith(false_ends) and not any(f in e for f in false_ends)
    ]
    valid_emails = [e for e in filtered_ends if not e.startswith(discard_terms)]
    found_email = choose_email(valid_emails, local_langs=local_langs) if valid_emails else ""
    found_phone = extract_phone_number(resp.text)
    socials = extract_social_links(resp.text)

    has_any_data = any([
        had_contact,
        found_email,
        found_phone,
        socials["instagram"],
        socials["facebook"],
        socials["linkedin"],
    ])
    if not has_any_data:
        with print_lock:
            print(f"[{idx}/{total}] {name} -> {url} ... No contacts or socials found.")
        return None

    place_copy = dict(place)
    if found_email:
        place_copy["email"] = found_email
    if found_phone and not (place_copy.get("phone") or ""):
        place_copy["phone"] = found_phone
    place_copy.update(socials)
    place_copy["relevance"] = "relevant" if has_relevant_match(resp.text, keyword_list) else "regular"

    with print_lock:
        print(
            f"[{idx}/{total}] {name} -> {url} ... OK -> "
            f"email={place_copy.get('email') or '-'}, "
            f"phone={place_copy.get('phone') or '-'}, "
            f"ig={'yes' if socials['instagram'] else 'no'}, "
            f"fb={'yes' if socials['facebook'] else 'no'}, "
            f"li={'yes' if socials['linkedin'] else 'no'} "
            f"[{place_copy['relevance']}]"
        )

    time.sleep(random.uniform(0.1, 0.4))
    return place_copy


def scrape_and_merge(
    iso_code,
    relevant_keywords=None,
    need_socials=False,
    local_langs=None,
    max_workers=64,
):
    keyword_list = [k.strip().lower() for k in (relevant_keywords or []) if k and k.strip()]
    discard_terms, _ = email_lists(local_langs=local_langs)
    all_places = pull_list_from_api(iso_code)
    if not all_places:
        return [], []

    grouped = filter_results(all_places, need_socials=need_socials)
    to_scrape = grouped["to_scrape"]
    already_with_contact = grouped["already_with_contact"]
    scraped_list = []

    total = len(to_scrape)
    workers = max(1, min(max_workers, 64, total)) if total > 0 else 1

    if total > 0:
        session = _build_session(pool_size=workers)
        try:
            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures = [
                    executor.submit(
                        _scrape_single_place,
                        session,
                        place,
                        idx,
                        total,
                        discard_terms,
                        keyword_list,
                        local_langs,
                    )
                    for idx, place in enumerate(to_scrape, 1)
                ]
                for future in as_completed(futures):
                    result = future.result()
                    if result is not None:
                        scraped_list.append(result)
        finally:
            session.close()

    seen_emails = set()
    seen_ids = set()
    finals = []

    for place in (already_with_contact + scraped_list):
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
        item.setdefault("instagram", "")
        item.setdefault("facebook", "")
        item.setdefault("linkedin", "")
        item.setdefault("relevance", "regular")
        finals.append(item)

    return finals, all_places
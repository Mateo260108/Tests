import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import random
import re
import time
import requests
from requests.adapters import HTTPAdapter

from utils import email_terms_translated
from .save_and_order import classify_relevance
from api import pull_list_from_api
from .config import (
    social_blacklist, generic_email_domains, headers,
    false_ends, mailto_regex, email_regex, phone_regex, tel_regex, ig_regex, fb_regex, li_regex,
)

print_lock = threading.Lock()

#-----------------------------------------------

def extract_clean_email(html_text, local_langs):
    if not html_text:
        return ""

    mailto_candidates = mailto_regex.findall(html_text)
    email_candidates = email_regex.findall(html_text)
    candidates = mailto_candidates if mailto_candidates else email_candidates

    discard_terms, max_priority = email_terms_translated(langs=local_langs)
    valid_candidates = []

    for email in candidates:
        email = email.strip().lower()
        if "@" not in email:
            continue
        prefix, domain = email.split("@", 1)
        end = f".{domain.rsplit('.', 1)[-1]}" if "." in domain else ""
        if (
            prefix not in discard_terms
            and domain not in generic_email_domains
            and end not in false_ends
        ):
            valid_candidates.append(email)

    for term in max_priority:
        term_clean = term.strip().lower()
        for email in valid_candidates:
            prefix = email.split("@", 1)[0]
            if prefix == term_clean or prefix.startswith(term_clean):
                return email

    return valid_candidates[0] if valid_candidates else ""

def extract_phone_number(html_text, phone_prefix=""):
    if not html_text:
        return ""

    normalized_prefix = ""
    if phone_prefix:
        p = re.sub(r"[^\d+]", "", str(phone_prefix).strip())
        if p and not p.startswith("+"):
            p = "+" + p
        normalized_prefix = p

    tel_candidates = tel_regex.findall(html_text)
    candidates = tel_candidates if tel_candidates else phone_regex.findall(html_text)

    for match in candidates:
        cleaned = re.sub(r"[^\d+]", "", match)
        digits = re.sub(r"\D", "", cleaned)
        if not (7 <= len(digits) <= 15):
            continue

        if normalized_prefix:
            if not cleaned.startswith(normalized_prefix):
                continue

        return cleaned

    return ""

def extract_clean_socials(html_text):
    ig_matches = [
        u for u in ig_regex.findall(html_text)
        if u not in social_blacklist
    ]
    fb_matches = [
        u for u in fb_regex.findall(html_text)
        if u not in social_blacklist
    ]
    li_matches = [
        u for u in li_regex.findall(html_text)
        if u not in social_blacklist
    ]

    ig = ig_matches[0] if ig_matches else ""
    fb = fb_matches[0] if fb_matches else ""
    li = li_matches[0] if li_matches else ""
    
    return {"instagram": ig, "facebook": fb, "linkedin": li}
#-----------------------------------------------------------

#------------------------------
def filter_results(all_places):
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
            to_scrape.append(place)
        if email:
            email_included.append(place)
        if phone:
            phone_included.append(place)

        has_contact = bool(email or phone)
        if has_contact:
            already_with_contact.append(place)

    return {
        "web_included": web_included,
        "email_included": email_included,
        "phone_included": phone_included,
        "to_scrape": to_scrape,
        "already_with_contact": already_with_contact,
    }

def scrape_place(session, place, idx, total, keyword_list, negative_keyword_list, local_langs, phone_prefix):

    url = (place.get("web") or "").strip()
    if url and not url.startswith(("http://", "https://")):
        url = "https://" + url

    name = (place.get("name") or "").strip()

    try:
        resp = session.get(url, timeout=30)
    except requests.exceptions.RequestException as e:
        with print_lock:
            print(f"[{idx}/{total}] {name} -> {url} ... Error ({e})")
        return None

    if resp.status_code != 200:
        with print_lock:
            print(f"[{idx}/{total}] {name} -> {url} ... HTTP {resp.status_code}")
        return None

    had_contact = bool((place.get("email") or "").strip() or (place.get("phone") or "").strip())

    email = extract_clean_email(resp.text, local_langs)
    phone = extract_phone_number(resp.text, phone_prefix=phone_prefix)
    socials = extract_clean_socials(resp.text)

    has_any_data = any([
        had_contact,
        email,
        phone,
        socials["instagram"],
        socials["facebook"],
        socials["linkedin"],
    ])

    if not has_any_data:
        with print_lock:
            print(f"[{idx}/{total}] {name} -> {url} ... No contacts or socials found.")
        return None

    place_copy = dict(place)
    if email:
        place_copy["email"] = email
    if phone and not (place_copy.get("phone") or ""):
        place_copy["phone"] = phone
    place_copy.update(socials)
    place_copy["relevance"] = classify_relevance(resp.text, keyword_list, negative_keyword_list)

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
#--------------------

#-------------------------------
def build_session(pool_size=64):
    session = requests.Session()
    adapter = HTTPAdapter(pool_connections=pool_size, pool_maxsize=pool_size)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update(headers)
    return session

def scrape_and_merge(
    iso_code,
    relevant_keywords=None,
    irrelevant_keywords=None,
    local_langs=None,
    phone_prefix=None,
    max_workers=64,
):
    keyword_list = [k.strip().lower() for k in (relevant_keywords or []) if k and k.strip()]
    negative_keyword_list = [k.strip().lower() for k in (irrelevant_keywords or []) if k and k.strip()]
    all_places = pull_list_from_api(iso_code)
    if not all_places:
        return [], []

    grouped = filter_results(all_places)
    to_scrape = grouped["to_scrape"]
    already_with_contact = grouped["already_with_contact"]
    scraped_list = []

    total = len(to_scrape)
    workers = max(1, min(max_workers, 64, total)) if total > 0 else 1

    if total > 0:
        session = build_session(pool_size=workers)
        try:
            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures = [
                    executor.submit(
                        scrape_place,
                        session,
                        place,
                        idx,
                        total,
                        keyword_list,
                        negative_keyword_list,
                        local_langs,
                        phone_prefix=phone_prefix
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
#----------------------------
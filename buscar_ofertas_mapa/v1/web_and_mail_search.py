import os
import csv
import time
import random
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def scrape_emails_html(html):
            patron = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
            results = set(re.findall(patron, html))
            false_ends = ('.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.js', '.css', 'wixpress.com', 'sentry.io', 'example.com')

            return [
                email.lower() for email in results
                if not email.lower().endswith(false_ends) and not any(f in email.lower() for f in false_ends)
            ]

def search_emails_in_web(url):
    if not url:
        return None

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return None

        emails = scrape_emails_html(resp.text)
        if emails:
            return emails[0]
        soup = BeautifulSoup(resp.text, 'html.parser')
        keywords = ['contact', 'kontakt', 'about', 'yhteystiedot', 'kontaktid', 'jobs', 'career', 'work', 'email', 'mail']

        for link in soup.find_all('a', href=True):
            href = link['href'].lower()
            text = link.get_text().lower()
            if any(word in href or word in text for word in keywords):
                url_contact = urljoin(url, link['href'])
                contact_query = requests.get(url_contact, headers=HEADERS, timeout=15)
                if contact_query.status_code == 200:
                    emails_sub = scrape_emails_html(contact_query.text)
                    if emails_sub:
                        return emails_sub[0]
                break

    except Exception:
        pass 
        return None

def process_webs_by_country(iso_code):
    folder_name = f"{iso_code}_filtered"
    input_path = os.path.join(folder_name, f"web_list_{iso_code}.csv")
    output_path = os.path.join(folder_name, f"scraped_emails_{iso_code}.csv")

    if not os.path.exists(input_path):
        print(f"{input_path} is not available")
        return

    with open(input_path, mode="r", encoding="utf-8") as file:
        rows = list(csv.DictReader(file, delimiter="\t"))

    email_results =[]

    for i, row in enumerate(rows, 1):
        url = row.get('web') or next((v for v in row.values() if v and 'http' in v), '')
        values = list(row.values())
        name = values[1] if len(values) > 1 else 'Sin nombre'

        print(f"[{i}/{len(rows)}] {name} -> {url} ...", end=" ")

        emails_found_1 = []
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code == 200:
                emails_found_1 = scrape_emails_html(resp.text)
        except Exception:
            pass

        email_results_2 = search_emails_in_web(url)
        emails_found_2 = [email_results_2] if isinstance(email_results_2, str) else (email_results_2 or [])

        all_the_emails = [
            e.strip().lower() 
            for e in (emails_found_1 + emails_found_2) 
            if e and e.strip()
        ]
        emails = list(dict.fromkeys(all_the_emails))

        if emails:
            final_emails = ", ".join(emails)
            print(f"{final_emails}")
            row['email'] = final_emails 
            email_results.append(row)
        else:
            print("Email not found")

        time.sleep(random.uniform(0.5, 1.5))

    if email_results:
        fieldnames = email_results[0].keys()
        with open(output_path, mode="w", encoding="utf-8", newline="") as out_file:
            writer = csv.DictWriter(out_file, fieldnames=fieldnames, delimiter="\t")
            writer.writeheader()
            writer.writerows(email_results)



if __name__ == "__main__":
    process_webs_by_country("IS")
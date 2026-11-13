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
        return

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
    
if __name__ == "__main__":
    emails1 = scrape_emails_html("https://akureyrihostel.com/")
    emails2 = search_emails_in_web("https://akureyrihostel.com/")
    print(emails1)
    print(emails2)